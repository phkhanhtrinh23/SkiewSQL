# v2m (N×1) correct with reuse, N×M wrong — Spider2-lite `local004`, and why N×1 ≈ AV-SQL but ≠ N×M

Fourth in the case-study series. Here **our v2m** (N×1 whole-question view + memory) answers correctly **with reuse activated**, and **our N×M** (decompose-into-sub-goals) is **wrong** — on the same question, with **AV-SQL + LSH + skill-graph** landing the *exact same correct answer as v2m*. This is the cleanest demonstration of a key structural point:

> **v2m and AV-SQL are both N×1** — one holistic whole-question query — so they behave the same and get it right. **N×M is the odd one out**: decomposing the question into sub-goals makes each sub-goal join the same table independently, and composing them **double-counts**. The failure is caused by decomposition, not by the model or the values.

- **Systems:** v2m (`skiewsql/realrun.py --nx1`, memory ON), N×M (`--nxm`, memory ON), AV-SQL+LSH+skill-graph. Model `gpt-5-mini`; Spider2-lite local (SQLite); official CSV execution-match scorer.

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
`order_payments` is touched **once** (inside the reused `order_payments_total`); installment orders are collapsed to a single total before averaging. Correct.

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

**v2m and AV-SQL are the same *family* (N×1): one holistic whole-question query.** Both independently arrive at the only grain-correct shape — *pre-aggregate payments to one total per order, then average per customer* — and touch `order_payments` **exactly once**. Their outputs are byte-identical. Whether the per-order-total block is **reused from memory** (v2m's `order_payments_total`, `gen=0`) or **freshly generated** (AV-SQL's `payments_per_order`) does not matter — the N×1 *shape* is what makes it correct. This is exactly your observation: **v2m and AV-SQL are "the same right"; the real variable is N×1 vs N×M.**

**N×M is wrong because decomposition breaks the join structure.** Splitting into sub-goals means:
- one sub-goal ("gather each customer's orders and payments") joins `order_payments`;
- a *later* sub-goal ("compute per-customer stats") **joins `order_payments` again**, because in isolation it re-reads the payments table to aggregate.

Neither fragment is wrong on its own, but **composing them multiplies the join** — the classic decomposition hazard. On a table with 1-to-many children (installments), independent per-sub-goal joins fan out and inflate `SUM`. The N×1 systems never hit this because they build the whole computation in one place and pre-aggregate before joining.

**Why reuse didn't save N×M** (and rarely does): N×M's memory stores **sub-goal fragments**, not whole answers, so a reused fragment still has to be composed with freshly-generated siblings — inheriting the same fan-out risk. Across Spider2-lite, **N×M reuse is `reuse=1, gen=3, ok=0` on all 5 of its reuse questions (0/5 correct)**, whereas **v2m reuse is `reuse=1, gen=0, ok=1` on all 7 (7/7 correct)** — v2m reuses a *whole* view and composes nothing fragile around it. Same "conjunctive fan-in" that makes N×M lose overall (14% vs v2m 33% on Spider2-lite).

**One-line takeaway:** the correct answer needs `order_payments` joined **once**; N×1 (v2m *and* AV-SQL) does exactly that; N×M's decomposition joins it **twice** and inflates the installment orders. It is a *decomposition* failure, cleanly isolated — v2m and AV-SQL are interchangeable here, N×M is the outlier.

---

## 6. Statistics

| metric | v2m (ours) | AV-SQL + LSH + skill-graph | N×M (ours) |
|---|---|---|---|
| family | N×1 | N×1 | N×M (decompose) |
| views reused | **1** (`order_payments_total`, whole, load-bearing) | skill-graph hint | 0 |
| views/CTEs generated | **0** | ~3 (fresh) | **4 sub-goals** |
| `order_payments` join count | **1** | **1** | **2 (fan-out)** |
| top-3 correct? | **✅** | **✅ (identical to v2m)** | **❌** |

**Aggregate reuse signatures (Spider2-lite):** v2m reuse **7/7 correct** (`reuse=1,gen=0`); N×M reuse **0/5** (`reuse=1,gen=3`). Benchmark accuracy: v2m 33.1%, N×M 14.0% (common-121).

---

## Reproduction
- Preds: `skiewsql/results_real/S2Lv2m_spider2lite_A_SkiewSQL.json` and `S2Lnxm_..._A_SkiewSQL.json` (`local004`)
- AV-SQL logs: `~/skiew_together/avsql_s2local/logs_reuse/local004/0/`
- Saved SQL: `~/skiew_together/avsql_s2local/local004_{v2m,nxm,avsql}.sql`
- Installment fan-out fact: 2,961/99,440 orders have >1 `order_payments` row
- Code: `skiewsql/realrun.py` (`--nx1` v2m / `--nxm` N×M), `skiewsql/core.py` (ViewGraph); AV-SQL `av_sql/` + `av_sql/skill_graph.py`
