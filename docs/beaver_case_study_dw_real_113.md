# BEAVER Case Study — Our N×M correct, AV-SQL + LSH + skill-graph wrong (`dw_real_113`)

Companion to the Spider2-lite case study. Here the result **reverses**: on BEAVER's huge warehouse schema, **our N×M decomposition is correct** and **AV-SQL + full-scan LSH + skill-graph is wrong**. This documents one full example end-to-end, the cross-benchmark reason for the reversal, and a **quantitative** analysis of whether LSH helps.

- **Systems:** (a) **our N×M** — SkiewSQL decompose-the-question-into-M-sub-goals × N-schema-chunks, align, compose (`skiewsql/beaver_method.py`, `--nxm`); (b) **AV-SQL + LSH + skill-graph** — real AV-SQL pipeline (rephrase → per-chunk CTE → planner → SQL → revise-5-fix) + AV-SQL native full-scan MinHash-LSH value retrieval + our skill-graph CTE reuse.
- **Model:** `gpt-5-mini`, both. **DB:** BEAVER `dw` (MariaDB, **97 tables, 1530 columns**). **Scorer:** execution-match (`skiewsql/beaver_method.score`, order-insensitive multiset).

**Headline numbers (BEAVER, 108 gold-executable):** our N×M **12.0%** (13/108), v2m **11.1%**; AV-SQL+LSH+skill-graph **2.8%** (3/108) = AV-SQL+LSH+CHESS **2.8%** = AV-SQL **no-LSH 2.8%**.

---

## 0. Why the reversal? (BEAVER vs Spider2-lite) — architecture × schema-scale

| | Spider2-lite | BEAVER |
|---|---|---|
| schema size | small (avg 13.7 tables; AV-SQL splits into **1 chunk**) | huge (**97 tables / 1530 cols**; **~3 chunks of ~500 cols**) |
| dominant difficulty | **analytical logic** (medians, windows, grain) | **schema navigation + literal faithfulness** on a sprawling schema |
| AV-SQL + LSH (+skill-graph) | **~38%** ✅ | **2.8%** ❌ |
| our N×M | 14% ❌ | **12.0%** ✅ |

Both benchmarks are hard (ceilings ~38% vs ~12% — BEAVER is *harder for everyone*). What flips is **which kind of difficulty dominates**, and each architecture is strong at one and weak at the other:

- **Spider2-lite (small schema):** finding the right tables is trivial; the challenge is analytical reasoning. AV-SQL's holistic read + **5-attempt execution-feedback revise loop** nails it. N×M's question-decomposition is pure overhead (conjunctive failure, no schema-navigation payoff) → it loses.
- **BEAVER (huge schema):** AV-SQL's elaborate per-chunk-CTE pipeline **over-engineers** — its exploratory CTEs and reused patterns add joins/filters/NULL-handling the question never asked for, and on 1530 look-alike columns it also mis-selects. Evidence: on BEAVER **119 of its queries execute successfully but only 3/108 are correct** — the failures are **semantic** (runnable-but-wrong), not crashes. N×M's literal decompose-and-compose stays faithful to the question → it wins.

The example below is a textbook instance of AV-SQL's BEAVER failure: right tables, but **two spurious semantic decorations** (a cancelled-filter and a NULL→0 coalesce), one of them injected by **reuse**.

---

## 1. Context

**Question (`dw_real_113`, DB `dw`):**
> For each IAP category, list the category name, the sponsor name, the number of activities offered, and the average fee per activity, sorted by the number of activities in descending order.

**Domain knowledge:** *"Independent Activities Period" is abbreviated "IAP".*

**Relevant schema (3 tables out of 97):**

| table | key columns |
|---|---|
| `IAP_SUBJECT_DETAIL` | `IAP_SUBJECT_SESSION_KEY`, `IAP_SUBJECT_CATEGORY_KEY`, `IAP_SUBJECT_SPONSOR_KEY`, `FEE`, `IS_CANCELLED` |
| `IAP_SUBJECT_CATEGORY` | `IAP_SUBJECT_CATEGORY_KEY`, `IAP_CATEGORY_NAME` |
| `IAP_SUBJECT_SPONSOR` | `IAP_SUBJECT_SPONSOR_KEY`, `SPONSOR_NAME` |

**Gold SQL** (246 rows):
```sql
SELECT isc.IAP_CATEGORY_NAME AS CATEGORY_NAME, iss.SPONSOR_NAME,
       COUNT(isd.IAP_SUBJECT_CATEGORY_KEY) AS ACTIVITY_COUNT,
       AVG(isd.FEE) AS AVG_FEE_PER_ACTIVITY
FROM IAP_SUBJECT_DETAIL isd
JOIN IAP_SUBJECT_CATEGORY isc ON isd.IAP_SUBJECT_CATEGORY_KEY = isc.IAP_SUBJECT_CATEGORY_KEY
JOIN IAP_SUBJECT_SPONSOR  iss ON isd.IAP_SUBJECT_SPONSOR_KEY  = iss.IAP_SUBJECT_SPONSOR_KEY
GROUP BY isc.IAP_CATEGORY_NAME, iss.SPONSOR_NAME
ORDER BY ACTIVITY_COUNT DESC;
```
Note what gold does **not** do: no `IS_CANCELLED` filter, and it keeps `AVG(FEE)` as `NULL` when all fees are null.

---

## 2. Views generated — ours vs. AV-SQL, and what was reused

### 2a. Our N×M — decompose-and-compose, **0 persisted views**
For this question N×M ran its decompose-align pipeline (split the question into sub-goals, align to schema chunks) and **composed the answer directly**: `generated=0`, `reused=0`, `used_reuse=False` (graph had 38 accumulated views from earlier questions, none used). On BEAVER this is the norm — across the 108 questions N×M persists ~0.4 views/question and **reuses on essentially none**; it wins by *faithful direct composition*, not by memory. The composed final query is a single flat `SELECT` (see §2c).

### 2b. AV-SQL + LSH + skill-graph — 3 CTE chunks + **reuse fired 3×**
AV-SQL split `dw` into **3 schema chunks**, ran a CTE agent per chunk, and the **skill-graph injected 3 reuse hints** (proven CTEs from earlier IAP questions on `dw`). The surviving CTE in the final SQL is `filtered_details` — and it carries an **`IS_CANCELLED` filter** that the reused IAP CTEs used legitimately (for questions that *asked* to exclude cancelled activities) but which is **wrong here**. This is reuse **transplanting** a sibling question's logic where it does not belong.

### 2c. Full generated SQL — verbatim, as executed and scored

**Our N×M — 246 rows — ✅ matches gold**
```sql
SELECT
  c.IAP_CATEGORY_NAME AS category_name,
  s.SPONSOR_NAME AS sponsor_name,
  COUNT(d.IAP_SUBJECT_SESSION_KEY) AS activity_count,
  AVG(d.FEE) AS avg_fee_per_activity
FROM iap_subject_category c
JOIN iap_subject_detail d
  ON d.IAP_SUBJECT_CATEGORY_KEY = c.IAP_SUBJECT_CATEGORY_KEY
LEFT JOIN iap_subject_sponsor s
  ON s.IAP_SUBJECT_SPONSOR_KEY = d.IAP_SUBJECT_SPONSOR_KEY
GROUP BY
  c.IAP_SUBJECT_CATEGORY_KEY,
  c.IAP_CATEGORY_NAME,
  s.IAP_SUBJECT_SPONSOR_KEY,
  s.SPONSOR_NAME
ORDER BY activity_count DESC
```

**AV-SQL + LSH + skill-graph — 245 rows — ❌ wrong**
```sql
WITH `filtered_details` AS (
  SELECT
    `IAP_SUBJECT_SESSION_KEY`,
    `IAP_SUBJECT_CATEGORY_KEY`,
    `IAP_SUBJECT_SPONSOR_KEY`,
    `ACTIVITY_TITLE`,
    `FEE`,
    `IS_CANCELLED`
  FROM `dw`.`iap_subject_detail`
  WHERE `IS_CANCELLED` IS NULL
     OR UPPER(TRIM(`IS_CANCELLED`)) <> 'Y'      -- << spurious filter (not in the question)
)
SELECT
  c.`IAP_CATEGORY_NAME`,
  s.`SPONSOR_NAME`,
  COUNT(DISTINCT d.`IAP_SUBJECT_SESSION_KEY`) AS `number_of_activities`,
  COALESCE(ROUND(AVG(d.`FEE`), 2), 0) AS `average_fee_per_activity`   -- << NULL turned into 0
FROM `filtered_details` d
INNER JOIN `dw`.`iap_subject_category` c
  ON d.`IAP_SUBJECT_CATEGORY_KEY` = c.`IAP_SUBJECT_CATEGORY_KEY`
INNER JOIN `dw`.`iap_subject_sponsor` s
  ON d.`IAP_SUBJECT_SPONSOR_KEY` = s.`IAP_SUBJECT_SPONSOR_KEY`
GROUP BY
  c.`IAP_SUBJECT_CATEGORY_KEY`, c.`IAP_CATEGORY_NAME`,
  s.`IAP_SUBJECT_SPONSOR_KEY`, s.`SPONSOR_NAME`
ORDER BY `number_of_activities` DESC, c.`IAP_CATEGORY_NAME` ASC;
```

---

## 3. How composition works (the two systems differ here)

- **N×M (ours):** the question is decomposed into sub-goals; each sub-goal is aligned to the relevant schema chunk; candidate views are generated and (optionally) verified; the **composer** (`compose_sql`) stitches sub-goals into one query. When a question needs no reusable intermediate (as here), it composes a single flat `SELECT` directly — no `WITH`, no defensive scaffolding.
- **AV-SQL:** each schema chunk yields an exploratory CTE (here seeded by 3 reused CTEs); the **SQL agent** assembles the surviving CTE(s) as a `WITH` prefix and writes the answer `SELECT`; **ReviseSQL** runs it and fixes on error/empty (≤5 attempts). The revise loop only checks *executability*, so a runnable-but-semantically-wrong query passes through unchanged.

---

## 4. Where AV-SQL goes wrong and N×M stays right (evidence)

Executing all three on `dw`:

| | rows | Mathematics/Mathematics | Athletics category avg fee |
|---|---|---|---|
| **GOLD** | **246** | count **8**, avg `NULL` | `NULL` |
| **N×M (ours)** | **246** ✅ | count **8**, avg `NULL` | `NULL` |
| **AV-SQL + LSH + skill-graph** | **245** ❌ | count **7**, avg `0.00` | `0.00` |

Two independent semantic bugs, both absent from the question:

1. **Spurious `IS_CANCELLED` filter** (from the reused IAP CTE) drops activities the question wanted counted → 245 rows instead of 246, and Mathematics count 7 instead of 8.
2. **`COALESCE(AVG(FEE), 0)`** converts `NULL` average fees (categories where every fee is null) into `0.00` → every such row mismatches gold's `NULL`.

N×M's query has **neither** decoration: it counts all activities and lets `AVG(FEE)` be `NULL`, exactly as gold does. This is the BEAVER pattern in miniature — **AV-SQL over-engineers on the large schema (partly driven by reuse), N×M stays literal to the question.**

---

## 5. How the skill-graph is built — and why it did **not** help here (it hurt)

Mechanism (identical to the Spider2-lite study; code `av_sql/skill_graph.py`, hook in `av_sql/question.py`): per-DB store of `{question, tables, cte_sql, emb(384-d MiniLM)}`; **deposit** each accepted CTE; before generating, **retrieve** cosine-≥0.5 same-DB CTEs (table-overlap ranked, top-2) and inject them as "reuse verbatim or lightly adapt" hints.

On `dw_real_113` it **fired 3×** and the retrieved IAP CTEs carried an `IS_CANCELLED` filter appropriate to *their* questions. The model transplanted that filter here — so **reuse actively introduced bug #1**. This is the mirror image of the Spider2-lite `local050` win (where reuse transplanted a *correct* grain). Net effect of the skill-graph on BEAVER: **0** (2.8% with and without it, same as Spider2-lite's net-neutral) — it helps when a *relevant* prior CTE exists and hurts when an *irrelevant-but-similar* one is forced, and on these benchmarks those roughly cancel.

**Take-away:** the skill-graph is a double-edged transplant — it does not systematically help on either benchmark with this model.

---

## 6. Statistics

**This question (`dw_real_113`):**

| metric | N×M (ours) | AV-SQL + LSH + skill-graph |
|---|---|---|
| schema chunks | decompose-align (question sub-goals) | **3** CTE chunks |
| views/CTEs persisted | **0** (direct compose) | 1 surviving CTE (`filtered_details`) |
| reuse hints injected | 0 (memory unused) | **3** |
| rows returned | **246** | 245 |
| final SQL executes | yes | yes |
| **correct** | **yes** ✅ | **no** ❌ |

**Whole BEAVER runs (108 gold-executable):**

| system | correct | notes |
|---|---|---|
| our N×M | **13/108 = 12.0%** | ~0.4 views/q persisted, reuse ≈ 0 |
| our v2m | 12/108 = 11.1% | |
| AV-SQL + LSH + skill-graph | 3/108 = 2.8% | 121 dirs; **119 queries execute, 3 correct** (semantic failures) |
| AV-SQL + LSH + CHESS-linker | 3/108 = 2.8% | |
| AV-SQL + LSH (baseline) | ≈2.8% (in progress) | |
| AV-SQL (no LSH) | 3/108 = 2.8% | |

---

## 7. Does LSH help? — quantitative analysis

**Answer: on BEAVER, no — it fires constantly and changes correctness by 0.**

| evidence | value |
|---|---|
| LSH index built over `dw` (full scan) | **222 MB + 532 MB** pkl (every distinct string value) |
| value literals looked up (BEAVER run) | **408** |
| lookups that returned candidates ("Relevant stored values" injected) | **384** (**94%** hit rate) |
| **correctness with LSH** (AV-SQL+LSH+skill-graph) | **3/108 = 2.8%** |
| **correctness without LSH** (AV-SQL no value_manager) | **3/108 = 2.8%** |
| **net gain from LSH** | **+0.0 points** |

So LSH was *extremely active* — it injected real stored DB values into 384 CTE-fix prompts — yet moved accuracy by nothing. **Why:**

- **LSH corrects value *spelling/casing* of filter literals** (e.g. mapping `'History'` → the stored `'History Department'`). That is orthogonal to BEAVER's failure mode.
- **BEAVER's failures are semantic *logic* errors** — wrong joins, spurious filters (`IS_CANCELLED`), wrong NULL handling (`COALESCE`), wrong aggregation — not mistyped filter values. The `dw_real_113` example uses **no string literal at all** in its filters, so LSH has nothing to fix; its bug is pure logic. Quantitatively, the whole-run signature confirms it: **119/108 predicted queries execute** (syntactically valid, valid columns) but only **3 are correct** → the gap is result-correctness, which value-spelling cannot touch.
- LSH only pays off when the *sole* remaining error is a mistyped filter literal — rare on analytical/aggregation questions, and swamped on BEAVER by logic errors.

**Contrast with Spider2-lite:** LSH also fired heavily there (159 lookups, 150 injections) and the AV-SQL+LSH system scored ~38%, but we did **not** run an AV-SQL-*without*-LSH Spider2-lite ablation, so we cannot isolate LSH's contribution there from these runs. (Open follow-up: run AV-SQL Spider2-lite with `value_manager` off to quantify LSH's small-schema gain — expected to be modest, since those questions are analytically-hard rather than value-spelling-hard.)

**Bottom line on LSH:** it is a *precision-of-literals* tool. It helps only to the extent that a benchmark's errors are mistyped values. On BEAVER, essentially none are, so the 754 MB index and 384 injections buy exactly **0** — the accuracy bottleneck is semantic query construction, which is why **decomposition (N×M), not value retrieval, is what moves the needle** on large schemas.

---

## Reproduction
- N×M result + pred: `skiewsql/results_real/BV108_NxM_beaver.json` (`instance_id=dw_real_113`)
- AV-SQL+skill-graph logs: `~/skiew_together/avsql_beaver/logs_reuse/mysql_dw_real_113/0/`
- Saved SQL: `~/skiew_together/avsql_beaver/dw_real_113_{GOLD,NxM,AVSQL}.sql`
- LSH index: `~/skiew_together/avsql_beaver/lsh_output/dw/lsh_index/*.pkl`; skill-graph: `~/skiew_together/avsql_beaver/graph_reuse.json`
- Configs: `configs/beaver/gpt5mini_lsh.yaml` (LSH baseline), `gpt5mini_reuse.yaml` (LSH+skill-graph); N×M via `skiewsql.beaver_method --nxm 1`
- Code: `av_sql/skill_graph.py`, `av_sql/lsh_index.py` (MySQL branch + lifted 50k guard), `skiewsql/beaver_method.py`
