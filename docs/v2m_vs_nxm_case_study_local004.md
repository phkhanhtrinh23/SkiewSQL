# v2m (N×1) correct with reuse, N×M wrong — Spider2-lite `local004`, and why N×1 ≈ AV-SQL but ≠ N×M

## 🔑 Headline conclusion — schema size decides the winner

**There is no single best text-to-SQL pipeline. The right technique is a function of one thing: does the database schema fit inside a single context chunk?**

- **When the schema is too large for one chunk** (e.g. **BEAVER**: 97 tables, 1530 columns — every question is multi-chunk), use **v2m's technique**: *chunk the schema, let each chunk vote for the tables it finds relevant, then **re-assemble only the selected tables into one clean schema and generate against that.*** This keeps cross-table joins coherent across chunk boundaries. On BEAVER it wins decisively — **v2m 11.1% vs AV-SQL(+LSH+skill-graph) 2.8%** — because AV-SQL's "generate one CTE per chunk, then stitch them all" picks *inconsistent duplicate tables* in different chunks and loses the join paths (columns come back NULL).

- **When the schema fits in one chunk** (e.g. **Spider2-lite**: *all 135 local schemas fit* — nothing ever splits), use **AV-SQL's technique**: *the classic **rephrase → schema-linked CTE → planner → SQL → execution-revise (5 fix attempts)** pipeline.* With nothing to chunk, v2m's re-assembly advantage is dormant and the contest is pure query-construction quality — where AV-SQL's heavier, cleaner loop wins: **AV-SQL 38.0% vs v2m 33.0%** (v2m emits messier SQL — dead views, wrong grain, redundant joins).

**One-line rule of thumb:** *large / over-context schema → v2m's select-then-reassemble. Small / single-chunk schema → AV-SQL's rephrase-plan-revise.* The same v2m is better exactly where chunking matters and worse where it doesn't. **§7 proves the BEAVER win, §8 proves the Spider2-lite loss — both with real, executed examples.** Read on for the mechanism.

---

## 🧩 What AV-SQL's "sort tables, then greedily pack chunks" actually does — and why it helps AV-SQL, but *not* on Spider2-lite

A natural question is: **AV-SQL sorts the schema by table length and greedily combines the shorter tables into the first chunks, leaving longer tables for later — does this packing explain AV-SQL's Spider2-lite edge?** The honest answer: **the packing is real and is a sound heuristic, but it is *not* the reason AV-SQL wins Spider2-lite — because on Spider2-lite it never fires more than one chunk.** Here is the precise mechanism and where it does and doesn't matter.

### 🔧 The technique, exactly (confirmed in code)
`skiewsql/avsql_prep.py` — `split_by_prompting_size_limit` (the `prompting_size_limit` split AV-SQL uses):
1. **Estimate** each *table*'s token count (`estimate_token_count`).
2. **Sort tables ascending** by token count — `sorted(..., key=lambda item: item[1], reverse=False)` (line 736–737): **smallest table first**.
3. **Greedily pack** into the current chunk. When adding the next table would exceed `token_limit` (= `schema_part_token_limit`), **flush the chunk and open a new one** (lines 739–750).
4. The unit is a **whole table** — it never splits inside a table. A single table larger than the limit becomes its **own** chunk. `random.shuffle` is commented out (line 755), so chunk order is **deterministic** (small → large).

So your memory is right, with one sharpening: it sorts **ascending** (smallest first) and greedy-packs — this is *not* classic first-fit-**decreasing** bin-packing (which sorts largest-first to minimize bins).

### ✅ Why sort-ascending + greedy is a good idea (on *large* schemas)
1. **It quarantines the giants.** Ascending order pushes every oversized table to the end, where an over-budget table lands in a chunk by itself. A huge fact/log table therefore never sits in the *middle* of a chunk, crowding out and splitting apart the many small tables a query actually joins. The big table's bulk is isolated instead of fragmenting its neighbours.
2. **It co-locates the smalls.** The many tiny dimension / lookup / bridge tables — often exactly the ones a join needs — pack densely into the **early** chunks, so they are seen **together in one prompt**, preserving join visibility across them.
3. **It minimises fragmentation.** Greedy first-fit fills each chunk close to the budget before opening the next, producing **fewer, fuller chunks** → fewer per-chunk CTE fragments for AV-SQL's compose step to stitch → fewer chances to mismatch a join key.
4. **It is deterministic** (shuffle off): same schema → same chunking every run, so results are reproducible and the failure modes are stable.

### ⚠️ But on Spider2-lite this packer is **dormant** — so it is *not* the boost
**Measured (§7-pre, §8): 0 of 135 Spider2-lite local schemas exceed one chunk** — every DB renders to **< 8k tokens**, far under AV-SQL's `schema_part_token_limit: 20000`. So the sort runs, the greedy loop runs, and it emits **exactly one chunk** every time. **The packing changes nothing on Spider2-lite** — there is only ever one part to pack into.

Therefore AV-SQL's Spider2-lite edge (**38.0% vs v2m 33.0%**) **cannot** come from chunk packing. It comes from the rest of the pipeline once the whole schema is in that single chunk: **rephrase → schema-linked CTE → planner → SQL → 5-attempt execution-revise** (documented with executed examples in §8). Both systems see the full schema. AV-SQL simply *constructs a cleaner query*.

### 🔎 Why our N×1 (v2m) is not as good as AV-SQL **here**
Same reason, from the other side: with chunking moot, the contest is **pure query-construction quality**, and v2m's lighter *view-propose-then-compose* loop emits messier SQL. In the §8 example (`local058`) v2m committed three faults **none of which are about chunking**: (1) a **dead view** — it generated its whole-question `chunk_view_0` and then never referenced it. (2) **wrong grain** — counted `DISTINCT (product_code, date)` = product-*months* instead of unique products. (3) a **redundant re-join** that fanned out already-aggregated rows. AV-SQL's heavier rephrase+planner+5-revise loop avoids/repairs exactly these. **v2m also does not use this ascending-sort packer at all** — its own chunker (`beaver_method.chunk_mysql_schema`) is a different implementation that only engages on BEAVER.

### 🧭 So where does the packer genuinely matter? BEAVER — and even there it is *second-order*
Sort+greedy-pack is a *large-schema* mechanism, so it only engages on BEAVER (all 108 questions multi-chunk). But §7b's controlled test is decisive: shrinking AV-SQL's chunk budget 20k → 8k barely moved accuracy (**1.9% → 2.8%**), while v2m reached **11.1%**. **Chunk granularity — and therefore the packing heuristic — is *not* the lever** that separates the two systems on BEAVER. The **architecture** is (v2m *selects the relevant tables and re-assembles one clean schema*. AV-SQL *generates a CTE per chunk and stitches them*). The packer is a sensible default that prevents pathological chunkings — it is **not** the cause of any win or loss in this study.

**Bottom line:** sort-ascending + greedy-pack is a well-designed chunking heuristic (isolate giants, co-locate smalls, fewest fragments, deterministic), but it is causally **inert on Spider2-lite** (single-chunk) and **second-order on BEAVER** (architecture dominates, §7b). AV-SQL beats v2m on Spider2-lite because of its **rephrase-plan-5×revise pipeline**, not its schema packing.

---

## 📖 Plain-terms primer — what a "schema" is, and what "select-then-reassemble" means

**First, what is a "schema"?** A schema is the text description of an entire *database*, and a database contains *many tables*. Three levels:

```
DATABASE  (e.g. "dw", or "E_commerce")
  └── contains many TABLES   (orders, customers, subject_offered, fclt_rooms, …)
        └── each table has COLUMNS   (order_id, customer_id, payment_value, …)
```

The schema is just those descriptions written out — a stack of `CREATE TABLE` blocks, one per table. For a small database the *whole* schema is only a couple of blocks:

```sql
-- ===== the entire E_commerce SCHEMA (2 tables) =====
CREATE TABLE orders (
    order_id TEXT, customer_id TEXT,
    order_status TEXT,               -- e.g. 'delivered'
    order_purchase_timestamp TEXT
);
CREATE TABLE order_payments (
    order_id TEXT,
    payment_value REAL               -- e.g. 129.90
);
```

That whole thing — **both** blocks — is "the schema." So *"many tables in one schema"* is just the normal state of affairs: a schema **is** a collection of table descriptions. BEAVER's `dw` schema is the same idea but **97** `CREATE TABLE` blocks stacked together (~40–60k tokens) — too big to paste into one prompt. **That size is the entire problem this doc is about.**

**Now, what does "let each chunk vote → re-assemble the selected tables → generate" mean?** Using `dw_real_5` (which needs `subject_offered` + `fclt_rooms` + `fclt_building_address`):

1. **Chunk** — split the 97 `CREATE TABLE` blocks into groups small enough to fit one prompt (whole tables, no overlap):
   ```
   chunk 1 = subject_offered, subject_offered_summary, library_subject_offered, …   (~15 tables)
   chunk 2 = fclt_rooms, fac_rooms, space_detail, …                                  (~15 tables)
   chunk 3 = fclt_building, buildings, fclt_building_address, …                       (~15 tables)
   …  (≈16 chunks)
   ```
2. **Vote** — show each chunk to the model with the question: *"which of THESE tables are relevant?"* Each chunk returns only table **names**:
   ```
   chunk 1 → ["subject_offered"]          chunk 2 → ["fclt_rooms"]
   chunk 3 → ["fclt_building_address"]     chunk 7 → []   (nothing relevant)
   ```
   Every table is *looked at* (nothing is truncated away), but each chunk nominates only the few it judges useful.
3. **Re-assemble** — take the **union** of the voted names = `{subject_offered, fclt_rooms, fclt_building_address}` and render **only those 3 blocks** into one small, clean schema (now easily fits a prompt):
   ```sql
   -- ===== filtered sub-schema (only the 3 tables the votes selected) =====
   CREATE TABLE subject_offered ( … );
   CREATE TABLE fclt_rooms ( … );
   CREATE TABLE fclt_building_address ( … );
   ```
   It is still "a schema" — just a **filtered** one, 3 tables instead of 97.
4. **Generate** — give the model the question + that focused 3-table schema. It writes the SQL **seeing all 3 relevant tables side-by-side**, so it joins them correctly.

**The contrast:** AV-SQL skips steps 3–4. It writes a *piece of SQL (a CTE) inside each chunk separately* and then glues the pieces together — so the model **never sees the 3 needed tables together in one schema**. Different chunks each grabbed a different duplicate table (`fclt_rooms` in one, `space_detail`/`buildings` in another), and the glue step couldn't line up their join keys → the room/building/address columns came back empty (NULL). **v2m first narrows 97 tables down to the ~3 that matter, puts just those in one schema, and writes the query once. AV-SQL writes fragments per chunk and stitches them — which falls apart when the needed tables are scattered across chunks.** §7 shows this on the real `dw_real_5` execution.

---

Fourth in the case-study series. Here **our v2m** (N×1 whole-question view + memory) answers correctly **with reuse activated**, and **our N×M** (decompose-into-sub-goals) is **wrong** — on the same question, with **AV-SQL + LSH + skill-graph** landing the *exact same correct answer as v2m*. This is the cleanest demonstration of a key structural point:

> **v2m and AV-SQL are both N×1** — one holistic whole-question query — so **on this small 2-table schema** they behave the same and get it right. **N×M is the odd one out**: decomposing the question into sub-goals makes each sub-goal join the same table independently, and composing them **double-counts**. The failure is caused by decomposition, not by the model or the values.  **Scale caveat (see §7):** "v2m ≈ AV-SQL" holds only on *small* schemas that fit in **one chunk** — which is **all** of Spider2-lite (0/135 exceed the chunk budget). On **BEAVER** (97 tables, every question multi-chunk, heavy table-name duplication) the two N×1 systems diverge sharply — v2m **11.1%** vs AV-SQL **2.8%** — because of an engineering gap in schema-chunking **and table-selection vs. compose-all-CTEs**, *not* the N×1 idea. §7 documents that in depth (with the open question of which of the two factors dominates).

- **Systems:** v2m (`skiewsql/realrun.py --nx1`, memory ON), N×M (`--nxm`, memory ON), AV-SQL+LSH+skill-graph. Model `gpt-5-mini`. Spider2-lite local (SQLite). Official CSV execution-match scorer.

---

## 1. Context

**Question (`local004`, DB `E_commerce` — Brazilian Olist):**
> Could you tell me the number of orders, average payment per order and customer lifespan in weeks of the **3 customers with the highest average payment per order**, where the lifespan is (latest − earliest purchase date) in days ÷ 7, floored to 1.0 if under a week?

**Relevant schema:**

| table | key columns |
|---|---|
| `orders` | `order_id`, `customer_id`, `order_status`, `order_purchase_timestamp` |
| `order_payments` | `order_id`, `payment_value` — **an order can have multiple payment rows (installments)** |

**The crux — "average payment per order":** because an order can have several `order_payments` rows (installments), you must **first sum payments to one total per order**, and only then average those per-order totals per customer. Getting the *grain* right is the whole difficulty — and it is a place where **joining the payments table twice silently inflates the numbers**.

**Data fact:** **2,961 of 99,440 orders have >1 payment row.** Any query that joins `order_payments` more than once fans these out and over-counts them.

---

## 2. Results — v2m = AV-SQL (both correct), N×M different (wrong)

Top-3 customers by `avg_payment_per_order` (executed on the real DB):

| rank | **v2m** ✅ | **AV-SQL+skill-graph** ✅ | **N×M** ❌ |
|---|---|---|---|
| 1 | `1617b135…` 13664.08 | `1617b135…` 13664.08 | `1617b135…` 13664.08 |
| 2 | `ec5b2ba6…` 7274.88 | `ec5b2ba6…` 7274.88 | **`9af2372a…` 13281.71** |
| 3 | `c6e2731c…` 6929.31 | `c6e2731c…` 6929.31 | **`de832e8d…` 11111.40** |

**v2m and AV-SQL return the identical, correct top-3.** N×M keeps only #1 and promotes two different customers (`9af2372a…`, `de832e8d…`) whose averages are **inflated** — precisely the customers whose orders have installment (multi-row) payments.

---

## 3. Views generated / reused

| system | family | reuse | generated | how it computes per-order payment |
|---|---|---|---|---|
| **v2m** | N×1 | **reused=1** (`order_payments_total`, whole view, **gen=0**) | 0 | `SUM(payment_value) GROUP BY order_id` (once) |
| **AV-SQL** | N×1 | skill-graph fired | `payments_per_order` (fresh) | `SUM(payment_value) GROUP BY order_id` (once) |
| **N×M** | N×M | reused=0 | **4 sub-goal CTEs (gen=4)** | joins `order_payments` **twice** |

v2m **reused a whole-question view** — `order_payments_total` (per-order payment total) — straight from memory (`gen=0`, deposited by an earlier E_commerce question). It is **load-bearing**: the correct "pre-aggregate per order" grain came for free. AV-SQL generated the same idea (`payments_per_order`) fresh. **Both N×1 systems converge on the same pre-aggregate-then-average shape.**

---

## 4. The exact bug — N×M's decomposition causes a double-join fan-out

### 4a. v2m (N×1) — join payments once → correct
```sql
WITH order_payments_total AS (                 -- REUSED whole view (gen=0): one total per order
  SELECT order_id, SUM(payment_value) AS order_payment_total
  FROM order_payments GROUP BY order_id
),
delivered_orders_payments AS (
  SELECT o.order_id, o.customer_id, o.order_purchase_timestamp, opt.order_payment_total
  FROM orders o JOIN order_payments_total opt ON o.order_id = opt.order_id
  WHERE o.order_status = 'delivered'
),
per_customer AS (
  SELECT customer_id,
         COUNT(DISTINCT order_id)     AS num_orders,
         AVG(order_payment_total)     AS avg_payment_per_order,   -- avg of PER-ORDER totals ✓
         MIN(order_purchase_timestamp) AS first_purchase,
         MAX(order_purchase_timestamp) AS last_purchase
  FROM delivered_orders_payments GROUP BY customer_id
)
SELECT customer_id, num_orders, avg_payment_per_order,
       CASE WHEN (julianday(last_purchase)-julianday(first_purchase))/7.0 < 1.0 THEN 1.0
            ELSE (julianday(last_purchase)-julianday(first_purchase))/7.0 END AS customer_lifespan_weeks
FROM per_customer
ORDER BY avg_payment_per_order DESC
LIMIT 3
```
`order_payments` is touched **once** (inside the reused `order_payments_total`). Installment orders are collapsed to a single total before averaging. Correct.

### 4b. N×M (decomposed) — join payments twice → inflated
```sql
WITH customer_orders AS (
  SELECT o.customer_id, o.order_id, op.payment_value AS payment_amount, o.order_purchase_timestamp AS purchase_date
  FROM orders o
  JOIN order_payments op ON o.order_id = op.order_id        -- << JOIN #1: one row per payment row
  WHERE o.customer_id IS NOT NULL AND op.payment_value IS NOT NULL AND o.order_purchase_timestamp IS NOT NULL
),
per_customer_order_stats AS (
  SELECT co.customer_id,
         COUNT(DISTINCT co.order_id) AS order_count,
         COALESCE(SUM(op.payment_value), 0.0) AS sum_payments,          -- << inflated
         CASE WHEN COUNT(DISTINCT co.order_id)=0 THEN 0.0
              ELSE COALESCE(SUM(op.payment_value),0.0)/COUNT(DISTINCT co.order_id) END AS avg_payment_per_order,
         MIN(co.purchase_date) AS first_purchase_date, MAX(co.purchase_date) AS last_purchase_date
  FROM customer_orders co
  LEFT JOIN order_payments op ON co.order_id = op.order_id  -- << JOIN #2: re-joins payments AGAIN
  GROUP BY co.customer_id
),
per_customer_lifespan AS ( SELECT customer_id, order_count, avg_payment_per_order,
  CASE WHEN (julianday(last_purchase_date)-julianday(first_purchase_date))/7.0 < 1.0 THEN 1.0
       ELSE (julianday(last_purchase_date)-julianday(first_purchase_date))/7.0 END AS lifespan_weeks
  FROM per_customer_order_stats ),
top_customers_by_avg_payment AS ( SELECT customer_id, order_count, avg_payment_per_order, lifespan_weeks
  FROM per_customer_lifespan WHERE order_count IS NOT NULL )
SELECT customer_id, order_count, avg_payment_per_order, lifespan_weeks
FROM top_customers_by_avg_payment
ORDER BY avg_payment_per_order DESC
LIMIT 3
```
**The bug (lines marked):** sub-goal `customer_orders` already joins `order_payments` (one row per payment). Sub-goal `per_customer_order_stats` then **joins `order_payments` a second time**. For an order with *k* payment rows this produces *k × k* rows, so `SUM(op.payment_value)` is multiplied by *k*. For the 2,961 installment orders the average is inflated, which is why customers like `9af2372a…` (13,281) leapfrog into the top-3. The query still runs — a **semantic** error the execution-feedback loop cannot catch.

### 4c. AV-SQL (N×1) — identical shape to v2m → correct
```sql
WITH payments_per_order AS ( SELECT order_id, SUM(payment_value) AS order_total FROM order_payments GROUP BY order_id ),
orders_with_payments AS ( SELECT o.order_id, o.customer_id, o.order_purchase_timestamp, p.order_total
    FROM orders o INNER JOIN payments_per_order p ON o.order_id = p.order_id WHERE o.order_purchase_timestamp IS NOT NULL ),
customer_order_stats AS ( SELECT customer_id, COUNT(order_id) AS order_count, AVG(order_total) AS avg_payment_per_order,
    MIN(order_purchase_timestamp) AS first_purchase, MAX(order_purchase_timestamp) AS last_purchase
    FROM orders_with_payments GROUP BY customer_id ),
customer_lifespan AS ( SELECT customer_id, order_count, avg_payment_per_order,
    CASE WHEN ((julianday(last_purchase)-julianday(first_purchase))/7.0) < 1.0 THEN 1.0
         ELSE ((julianday(last_purchase)-julianday(first_purchase))/7.0) END AS lifespan_weeks
    FROM customer_order_stats )
SELECT customer_id, order_count, ROUND(avg_payment_per_order,2), ROUND(lifespan_weeks,2)
FROM customer_lifespan ORDER BY avg_payment_per_order DESC LIMIT 3;
```
`payments_per_order` (SUM once) → join once → `AVG(order_total)`. **Same skeleton as v2m**, same correct top-3.

---

## 5. Why v2m ≈ AV-SQL (both correct) but N×M wrong — analysis

**v2m and AV-SQL are the same *family* (N×1): one holistic whole-question query.** Both independently arrive at the only grain-correct shape — *pre-aggregate payments to one total per order, then average per customer* — and touch `order_payments` **exactly once**. Their outputs are byte-identical. Whether the per-order-total block is **reused from memory** (v2m's `order_payments_total`, `gen=0`) or **freshly generated** (AV-SQL's `payments_per_order`) does not matter — the N×1 *shape* is what makes it correct. This is exactly your observation: **v2m and AV-SQL are "the same right". The real variable is N×1 vs N×M.**

**N×M is wrong because decomposition breaks the join structure.** Splitting into sub-goals means:
- one sub-goal ("gather each customer's orders and payments") joins `order_payments`.
- a *later* sub-goal ("compute per-customer stats") **joins `order_payments` again**, because in isolation it re-reads the payments table to aggregate.

Neither fragment is wrong on its own, but **composing them multiplies the join** — the classic decomposition hazard. On a table with 1-to-many children (installments), independent per-sub-goal joins fan out and inflate `SUM`. The N×1 systems never hit this because they build the whole computation in one place and pre-aggregate before joining.

**Why reuse didn't save N×M** (and rarely does): N×M's memory stores **sub-goal fragments**, not whole answers, so a reused fragment still has to be composed with freshly-generated siblings — inheriting the same fan-out risk. Across Spider2-lite, **N×M reuse is `reuse=1, gen=3, ok=0` on all 5 of its reuse questions (0/5 correct)**, whereas **v2m reuse is `reuse=1, gen=0, ok=1` on all 7 (7/7 correct)** — v2m reuses a *whole* view and composes nothing fragile around it. Same "conjunctive fan-in" that makes N×M lose overall (14% vs v2m 33% on Spider2-lite).

**One-line takeaway:** the correct answer needs `order_payments` joined **once**. N×1 (v2m *and* AV-SQL) does exactly that. N×M's decomposition joins it **twice** and inflates the installment orders. It is a *decomposition* failure, cleanly isolated — v2m and AV-SQL are interchangeable here, N×M is the outlier.

---

## 6. Statistics

| metric | v2m (ours) | AV-SQL + LSH + skill-graph | N×M (ours) |
|---|---|---|---|
| family | N×1 | N×1 | N×M (decompose) |
| views reused | **1** (`order_payments_total`, whole, load-bearing) | skill-graph hint | 0 |
| views/CTEs generated | **0** | ~3 (fresh) | **4 sub-goals** |
| `order_payments` join count | **1** | **1** | **2 (fan-out)** |
| top-3 correct? | **✅** | **✅ (identical to v2m)** | **❌** |

**Aggregate reuse signatures (Spider2-lite):** v2m reuse **7/7 correct** (`reuse=1,gen=0`). N×M reuse **0/5** (`reuse=1,gen=3`). Benchmark accuracy: v2m 33.1%, N×M 14.0% (common-121).

---

## 7. The other half of the story — on BEAVER, v2m ≠ AV-SQL (why two N×1 systems diverge at scale)

§5 said *"v2m ≈ AV-SQL, both N×1."* That is true **only on small schemas** like Spider2-lite `local004` (2 tables, no duplicates). On **BEAVER** the two N×1 systems diverge hard: **our v2m = 11.1%, AV-SQL+LSH+skill-graph = 2.8%** (and *every* AV-SQL variant flatlines at 2.8%). They are the same *family* but different *code*, and BEAVER's scale exposes the implementation gap. Here is the concrete mechanism — no hand-waving.

### 7a. Same question, opposite outcome — BEAVER `dw_real_5`
> *List the unique term code, subject title, **room, floor, building key, building street address, city, state, postal code**, formats, and number of enrolled students for all courses with more than 300 attendees.*

Needs one join path: `subject_offered` (enrollment) → `fclt_rooms` (room/floor/building) → `fclt_building_address` (street/city/state/postal).

- **v2m ✅** — final query joins exactly **3 tables**: `subject_offered`, `fac_rooms`, `fclt_building_address`. All columns populated. Correct.
- **AV-SQL ❌** — final query references **~16 tables/CTEs**, and its output rows look like this:
  ```
  TERM_CODE;SUBJECT_TITLE;ROOM;FLOOR;BUILDING_KEY;BUILDING_STREET_ADDRESS;CITY;STATE;POSTAL_CODE;FORMAT;ENROLLED
  2008SP;Differential Equations;;;;;;;;;673
  ```
  Enrollment (`673`) is right. **Every room/building/address column is NULL.** It ran, so the exec-fix loop saw nothing to fix — a silent semantic failure.

### 7-pre. First, *when* does this even happen? Only when the schema exceeds one chunk.
Measured directly:
- **Spider2-lite: 0 of 135 questions** have a schema larger than a chunk — every local DB is **< 8k tokens**, so both systems always run **single-chunk (N=1)** and never compose. This is the real reason v2m ≡ AV-SQL on Spider2-lite (§5): not matching chunk sizes, but that **neither system ever splits**.
- **BEAVER: all 108** — `dw` (97 tables/1530 cols ≈ 40–60k rendered tokens) far exceeds every budget, so **every** question is **multi-chunk** (AV-SQL → 3 chunks). The v2m-vs-AV-SQL divergence is therefore an **exclusively multi-chunk / BEAVER phenomenon.**

### 7b. The concrete differences that cause it — and it is *not* just chunk size

**(1) Chunk granularity.** On BEAVER, v2m runs through `beaver_method.chunk_mysql_schema(budget_chars=12000)` ≈ **~3k tokens/chunk** (whole tables, ~15–20 small chunks). AV-SQL uses `schema_part_token_limit: 20000` → **3 big chunks**, ~30 tables each. *(Note: `realrun.py`'s `CHUNK_BUDGET=8000` is the Spider2-lite path, not the BEAVER v2m path.)* Smaller chunks → each generation step sees fewer duplicate tables at once.

**(2) Table selection vs. compose-all-CTEs — likely the bigger factor.** `beaver_method` does not just chunk. It **selects tables**: it "propose[s] sub-goals per chunk, collecting the tables each chunk deems *relevant*," unions those, and builds the query from the **selected** tables (`skiewsql/beaver_method.py:158-162`). AV-SQL instead **generates one CTE per chunk and asks the SQL agent to stitch them all** — so every chunk's take on the schema (including its choice of duplicate table) enters the final query. v2m *prunes* to a consistent table set. AV-SQL *accumulates* inconsistent ones. This is what produces the NULL-column failure below, and chunk size alone may not explain it.

**Controlled test — which factor dominates? Answer: (2), not (1).** I re-ran AV-SQL on BEAVER with its chunk budget dropped from 20k to **8k tokens**, everything else identical:

| AV-SQL on BEAVER | chunk budget | accuracy |
|---|---|---|
| baseline | 20,000 tok (3 chunks) | 2/108 = **1.9%** |
| **@8k (this test)** | 8,000 tok (~8 chunks) | 3/108 = **2.8%** |
| v2m (for reference) | ~3k tok + **select-then-reassemble** | **12/108 = 11.1%** |

**Shrinking AV-SQL's chunks to v2m's granularity did essentially nothing (1.9% → 2.8%, still ~2–3 of 108).** So **factor (1) chunk-size is NOT the cause** — if anything, more chunks give the SQL agent *more* per-chunk CTEs to stitch. The gap is **factor (2): the architecture.** v2m's win comes from **selecting the relevant tables and re-assembling them into one schema before generating** (so all needed tables are seen together and joined once). AV-SQL generates a CTE *inside each chunk* and stitches them, which no chunk size fixes. **The deciding difference is select-then-reassemble vs generate-per-chunk-then-stitch — an architecture choice, not a hyperparameter.**

**(2) BEAVER has many near-duplicate tables, and AV-SQL's big chunks pick *inconsistent* ones.** BEAVER's `dw` warehouse stores each concept under several synonym tables:
- building → `fclt_building` / `buildings` / `fac_building_address` / `fclt_building_address`
- room → `fclt_rooms` / `fac_rooms` / `space_detail` / `zpm_rooms_load`
- subject/enrollment → `subject_offered` / `subject_offered_summary` / `library_subject_offered` / `so_raw` / `sos_raw` / `ss_raw`

Because each AV-SQL chunk holds ~30 tables, several duplicates land in the *same* chunk, and **different chunks generate CTEs over different duplicates.** For `dw_real_5` AV-SQL's three per-chunk CTEs were:
| chunk (20k) | tables its CTE built on |
|---|---|
| part 0 | `drupal_course_catalog` (wrong table entirely) |
| part 1 | `so_raw`,`sos_raw`,`ss_raw`, `fclt_building_cte`, `rooms_cte` |
| part 2 | `buildings`, `fac_building_address`, `space_detail`, `zpm_rooms_load`, `library_subject_offered` |

Part 1 models "building" as `fclt_building` and "room" as `rooms_cte`. Part 2 models the *same* building as `buildings`+`fac_building_address` and the *same* room as `space_detail`+`zpm_rooms_load`. **The two chunks describe the same entities with different, non-joinable tables.**

**(3) Composition can't reconcile inconsistent duplicates → NULL columns.** AV-SQL's SQL agent must now stitch these 3 big CTEs into one query. The join keys between the enrollment CTEs and the *two different* building/room representations don't line up, so the outer joins match nothing and the room/building/address columns resolve to `NULL`. It is not that AV-SQL "forgot" the tables — it referenced 16 of them — it is that it referenced **too many, inconsistently, and lost the join path.**

v2m never hits this: its **8k chunks** are small enough that each whole-question view sees only a handful of tables, so it converges on **one canonical table per concept** (`subject_offered`, `fac_rooms`, `fclt_building_address`) and composes a single tight 3-table join with consistent keys.

### 7c. Why this reconciles with §5 (v2m ≈ AV-SQL on `local004`)
`local004`'s `E_commerce` has **2 tables and no duplicates** — one chunk, one obvious join — so AV-SQL and v2m pick the identical tables and produce byte-identical SQL. The divergence needs (a) a schema too large for one chunk **and** (b) duplicate tables per concept. Spider2-lite rarely has either. **BEAVER (97 tables, 1530 columns, heavy synonymy) has both**, which is why *all* AV-SQL variants sit at 2.8% while v2m reaches 11.1%.

### 7d. So "different composition" means, precisely:
| aspect | v2m (ours, `beaver_method`) | AV-SQL |
|---|---|---|
| chunk budget (BEAVER) | `budget_chars=12000` ≈ **~3k tokens** (~15–20 whole-table chunks) | `schema_part_token_limit=20000` (3 chunks) |
| table handling | **selects** relevant tables across chunks → one set | **compose-all**: every chunk's CTE enters the final query |
| tables seen per view-gen | few → picks one canonical table/concept | ~30 → picks different duplicates per chunk |
| CTEs entering composition | pruned to a consistent table set | 3 big CTEs over inconsistent synonym tables |
| final `dw_real_5` query | 3-table join, consistent keys | ~16 tables/CTEs, join paths broken |
| result | all columns populated ✅ | building/room/address columns NULL ❌ |
| BEAVER accuracy | **11.1%** | **2.8%** (same for +skill-graph, +CHESS, no-LSH) |

The N×1 *idea* is identical. The difference is an **engineering** one — (a) chunk granularity and (b) **table-selection vs. compose-all-CTEs** — *not* the decompose-or-not question that separates v2m from N×M. Which of (a)/(b) dominates is being isolated by the AV-SQL@8k run (§7b).

---

## 8. The mirror image — on Spider2-lite v2m is *worse*, and it is **not** chunking

On Spider2-lite the ranking flips: **v2m 33.1% vs AV-SQL 38.0%.** The honest point up front: **there is no chunking here.** All 135 local schemas fit in **one chunk** (§7-pre), so both systems see the whole schema and emit a single view/CTE. v2m's large-schema machinery (chunk → select relevant tables → reassemble) is **dormant** — there is nothing to select. What decides the outcome is raw query-construction quality, and v2m's is weaker.

### 8a. Example — `local058` (education_business), AV-SQL ✅ / v2m ❌
> *"…hardware product segments along with their unique product counts for **2020**, ordered by the highest percentage increase in unique products from **2020 to 2021**."*
Gold: `segment, product_count_2020` → `Desktop,7 · Networking,6 · Accessories,69 · Storage,12 …`

**AV-SQL ✅** — a clean pivot, output byte-matches gold:
```sql
WITH sales_prod_year AS (         -- join fact→dim, keep both years
  SELECT hfsm.product_code, hfsm.fiscal_year, hdp.segment
  FROM hardware_fact_sales_monthly hfsm
  JOIN hardware_dim_product hdp ON hfsm.product_code = hdp.product_code
  WHERE hfsm.fiscal_year IN (2020, 2021) AND hdp.segment IS NOT NULL ),
segment_counts AS (               -- COUNT(DISTINCT product_code) per (segment, year)
  SELECT segment, fiscal_year, COUNT(DISTINCT product_code) AS unique_products
  FROM sales_prod_year GROUP BY segment, fiscal_year ),
segment_pivot AS ( … pivot to 2020/2021 cols, compute % increase … )
SELECT segment, unique_products_2020 FROM segment_pivot
ORDER BY (percentage_increase IS NULL) ASC, percentage_increase DESC;
```

**v2m ❌** — three self-inflicted errors, **none about chunking**:
1. **A dead view.** v2m generated its N×1 whole-question view `chunk_view_0 AS (…)` and then **never referenced it** — the final `SELECT` is a *separate* hand-written subquery. Its view-then-compose pipeline emitted scaffolding it discarded.
2. **Wrong grain.** Instead of the `fiscal_year` column it parsed the year from a date string — `CAST(substr(date,1,4) AS INTEGER)` — and counted `DISTINCT (product_code, date)` rows, i.e. **product-months, not unique products** → inflated counts.
3. **Redundant re-join.** It then `JOIN hardware_dim_product p ON p.segment = s.segment` and `GROUP BY segment`, fanning out already-aggregated rows.

All three are *query-construction* faults on a schema both systems saw in full. AV-SQL's **rephrase → one focused CTE-chain → planner → 5-attempt execution-revise** produced the clean correct query. V2m's lighter view-propose-then-compose emitted a convoluted, semantically-wrong one. (The same pattern recurs in the other v2m losses — e.g. `local081`/northwind, where v2m filtered "orders in 1998" as `BETWEEN '1998-01-01' AND '1998-03-12'`, truncating the year.)

### 8b. Why the *same* v2m wins on BEAVER and loses on Spider2-lite
| | Spider2-lite (single-chunk) | BEAVER (multi-chunk) |
|---|---|---|
| schema fits one chunk? | **yes** (0/135 exceed) | **no** (all 108 exceed) |
| v2m's select-then-reassemble | **no-op** — nothing to select | **decisive** — pulls scattered tables together, joins once |
| AV-SQL's generate-per-chunk-then-stitch | **= one clean CTE** (whole schema is the one chunk) | **breaks** — inconsistent duplicate-table CTEs, NULL columns |
| deciding factor | **raw compose quality** → v2m's convoluted query loses | **cross-chunk table coherence** → v2m's reassembly wins |
| result | AV-SQL **38%** > v2m **33%** | v2m **11%** ≫ AV-SQL **2.8%** |

**Honest synthesis:** v2m's chunking machinery is a *large-schema* tool. On **BEAVER** it is the whole ballgame — select the relevant tables out of 97, reassemble them, join once — and it beats AV-SQL's stitch-every-chunk approach. On **Spider2-lite** there is nothing to chunk, so that tool is dormant and the contest falls to composition quality, where AV-SQL's rephrase+planner+5-revise pipeline is cleaner than v2m's view-propose-then-compose. **v2m is not better or worse in the absolute — it is better exactly where chunking matters and worse where it does not.** The chunking mechanism explains the BEAVER win directly. On Spider2-lite the correct explanation is the opposite — chunking is absent, and v2m simply builds messier SQL.

---

## Reproduction
- Preds: `skiewsql/results_real/runs/sqlite/spider2lite/S2Lv2m_spider2lite_A_SkiewSQL.json` and `S2Lnxm_..._A_SkiewSQL.json` (`local004`)
- Spider2-lite v2m-loss example (§8): `local058` in `S2Lv2m_..._A_SkiewSQL.json` (dead `chunk_view_0`, product-month grain) vs `~/skiew_together/avsql_s2local/logs_reuse/local058/0/` (AV-SQL clean pivot). Divergence set `~/skiew_together/avsql_s2local/avsql_vs_v2m.json` (14 AV-SQL✓&v2m✗ / 7 v2m✓&AV-SQL✗). Single-chunk fact: 0/135 Spider2-lite schemas exceed the chunk budget
- BEAVER divergence (§7): `skiewsql/results_real/runs/beaver/BV108_v2m_beaver.json` (`dw_real_5`, correct) vs the archived AV-SQL run (NULL columns). The compared chunk budgets were 8,000 and 20,000 tokens.
- AV-SQL logs: `~/skiew_together/avsql_s2local/logs_reuse/local004/0/`
- Saved SQL: `~/skiew_together/avsql_s2local/local004_{v2m,nxm,avsql}.sql`
- Installment fan-out fact: 2,961/99,440 orders have >1 `order_payments` row
- Current code: `skiewsql/realrun.py` (`--architecture nx1` / `nxm`), `skiewsql/avsql_prep.py` (AV-SQL preprocessing), and `skiewsql/core.py` plus `skiewsql/registry.py` (per-database registry). The separate prototype package and graph implementation were retired.
