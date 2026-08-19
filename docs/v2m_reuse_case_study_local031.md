# v2m Reuse Case Study — v2m reuses a whole view and is correct (Spider2-lite `local031`), + why v2m's reuse works and N×M's does not

Third in the case-study series. The previous two covered AV-SQL's skill-graph (reuse **helping** on `local050`, **hurting** on BEAVER `dw_real_113`). This one documents **our v2m** (SkiewSQL N×1 + memory) reusing a whole-question view and answering correctly, contrasts it with **AV-SQL + LSH + skill-graph** on the same question, and analyses **why v2m's reuse lands correct answers (7/7) while N×M's never does (0/5)**.

- **Systems:** (a) **our v2m** — one whole-question view per schema chunk + memory reuse (`skiewsql/realrun.py`, `--nx1`, config A); (b) **AV-SQL + LSH + skill-graph**. Model `gpt-5-mini`; Spider2-lite local (SQLite); official CSV execution-match scorer.

**Honest scope up front.** There is **no** Spider2-lite question where our reuse fires *and* wins *and* AV-SQL is wrong — all **7** v2m reuse-correct questions are ones AV-SQL **also** solves (`local004, 031, 078, 195, 197, 228, 274`). So this is a *"v2m reuse works"* showcase, **not** a differentiating win. The genuinely differentiating result is the *mechanism* comparison in §5 (why v2m reuse ≠ N×M reuse).

---

## 1. Context

**Question (`local031`, DB `Brazilian_E_Commerce`):**
> What is the highest monthly delivered orders volume in the year with the lowest annual delivered orders volume among 2016, 2017, and 2018?

**Relevant schema:** one table, `olist_orders` (`order_id`, `order_status`, `order_delivered_customer_date`).

**Logic required:** filter to *delivered* orders in 2016–2018 → count delivered orders per (year, month) and per year → find the year with the **lowest annual** volume → within that year, return the **highest monthly** volume.

Both systems produce the correct answer; they differ in **how the reusable "delivered orders in scope" building block is obtained**.

---

## 2. Views generated / reused

### 2a. Our v2m — **reused 1 whole view, generated 0** (`reused=1, used_reuse=True, generated=0`)
v2m retrieved a **whole-question view** — `delivered` — from memory (deposited by an earlier `Brazilian_E_Commerce` question) and built the answer on top of it. The reused view is **load-bearing** (referenced 4× downstream), and `generated=0` means *nothing new was generated* — the entire scoped building block came from the graph:

```sql
-- REUSED view (from the skill/view graph; generated=0):
`delivered` AS (
  SELECT order_id,
         CAST(strftime('%Y', order_delivered_customer_date) AS INTEGER) AS delivered_year,
         CAST(strftime('%m', order_delivered_customer_date) AS INTEGER) AS delivered_month
  FROM olist_orders
  WHERE order_status = 'delivered'
    AND order_delivered_customer_date IS NOT NULL
    AND CAST(strftime('%Y', order_delivered_customer_date) AS INTEGER) IN (2016,2017,2018)
)
```

### 2b. AV-SQL + LSH + skill-graph — **6 CTEs generated from scratch** (reuse fired but produced fresh chunks)
AV-SQL built the same idea from scratch as a 6-CTE chain: `delivered_orders → monthly_counts → annual_counts → min_annual → min_years → monthly_in_min_year`. Its skill-graph reuse fired but the surviving structure is freshly generated CTEs, not a wholesale reused view.

### 2c. Full generated SQL — verbatim, as executed and scored

**Our v2m — ✅ correct** (reused `delivered`, composed on top):
```sql
WITH delivered AS (                       -- << REUSED whole-question view (generated=0)
  SELECT order_id,
         CAST(strftime('%Y', order_delivered_customer_date) AS INTEGER) AS delivered_year,
         CAST(strftime('%m', order_delivered_customer_date) AS INTEGER) AS delivered_month
  FROM olist_orders
  WHERE order_status = 'delivered'
    AND order_delivered_customer_date IS NOT NULL
    AND CAST(strftime('%Y', order_delivered_customer_date) AS INTEGER) IN (2016,2017,2018)
),
annual AS (
  SELECT delivered_year AS year, COUNT(DISTINCT order_id) AS annual_delivered_orders_volume
  FROM delivered GROUP BY delivered_year
),
monthly AS (
  SELECT delivered_year AS year, delivered_month AS month,
         COUNT(DISTINCT order_id) AS monthly_delivered_orders_volume
  FROM delivered GROUP BY delivered_year, delivered_month
),
annual_with_max_monthly AS (
  SELECT a.year, a.annual_delivered_orders_volume,
         COALESCE(MAX(m.monthly_delivered_orders_volume), 0) AS highest_monthly_delivered_orders_volume
  FROM annual a
  LEFT JOIN monthly m ON a.year = m.year
  GROUP BY a.year, a.annual_delivered_orders_volume
)
SELECT
  year AS year_with_lowest_annual_delivered_orders_volume,
  annual_delivered_orders_volume AS annual_delivered_orders_volume_for_that_year,
  highest_monthly_delivered_orders_volume AS highest_monthly_delivered_orders_volume_in_that_year
FROM annual_with_max_monthly
WHERE annual_delivered_orders_volume = (
  SELECT MIN(annual_delivered_orders_volume) FROM annual_with_max_monthly
)
```

**AV-SQL + LSH + skill-graph — ✅ also correct** (6 fresh CTEs):
```sql
WITH delivered_orders AS (
    SELECT `order_id`, `order_status`, `order_delivered_customer_date`
    FROM `olist_orders`
    WHERE `order_status` = 'delivered'
      AND `order_delivered_customer_date` IS NOT NULL
      AND STRFTIME('%Y', `order_delivered_customer_date`) IN ('2016','2017','2018')
),
monthly_counts AS (
    SELECT STRFTIME('%Y', `order_delivered_customer_date`) AS `year`,
           STRFTIME('%m', `order_delivered_customer_date`) AS `month`,
           COUNT(DISTINCT `order_id`) AS `delivered_orders_count`
    FROM delivered_orders GROUP BY `year`, `month`
),
annual_counts AS (
    SELECT `year`, SUM(`delivered_orders_count`) AS `annual_delivered_orders`
    FROM monthly_counts GROUP BY `year`
),
min_annual AS (
    SELECT MIN(`annual_delivered_orders`) AS `min_annual_delivered_orders` FROM annual_counts
),
min_years AS (
    SELECT a.`year` FROM annual_counts a
    INNER JOIN min_annual m ON a.`annual_delivered_orders` = m.`min_annual_delivered_orders`
),
monthly_in_min_year AS (
    SELECT mc.`year`, mc.`month`, mc.`delivered_orders_count`
    FROM monthly_counts mc INNER JOIN min_years my ON mc.`year` = my.`year`
)
SELECT MAX(`delivered_orders_count`) AS `highest_monthly_delivered_orders`
FROM monthly_in_min_year;
```

Both return the same answer. The point of interest is not the outcome (a tie) but the **route**: v2m got its scoped building block *for free* from memory (`generated=0`); AV-SQL re-derived everything.

---

## 3. How composition works
- **v2m (ours):** retrieve the best-matching whole-question view for the chunk (cosine over view embeddings), and if a reuse-verifier accepts it, **use it as the query's base CTE**; the composer (`compose_sql`) then writes the aggregation/ranking on top. Here `delivered` is the reused base; `annual`/`monthly`/`annual_with_max_monthly` are the composed answer.
- **AV-SQL:** per-chunk exploratory CTE → planner → SQL agent assembles CTEs into `WITH … SELECT` → ReviseSQL fixes on error (≤5). Reuse (skill-graph) seeds the CTE prompt but the surviving CTEs here are freshly written.

---

## 4. Result
| | reused | generated | correct |
|---|---|---|---|
| **v2m (ours)** | **1 (whole view `delivered`)** | **0** | ✅ |
| AV-SQL + LSH + skill-graph | reuse fired | 6 CTEs | ✅ |

Both correct (verified by the official scorer). No divergence on this question — see the scope note in the header.

---

## 5. Why v2m's reuse is correct and N×M's is not — the mechanism (the real finding)

This is the differentiating result, and it is **quantitative and structural**, not anecdotal.

**The numbers:**

| our method | questions where reuse fired | of those, **correct** | signature |
|---|---|---|---|
| **v2m** (N×1 + memory) | 7 | **7 / 7 (100%)** | every one is **`reuse=1, gen=0, ok=1`** |
| **N×M** (decompose + memory) | 5 | **0 / 5 (0%)** | every one is **`reuse=1, gen=3, ok=0`** |

The `gen` column is the whole story:

- **v2m reuses a *whole-question view* (`gen=0`).** In N×1, each chunk holds *one view that answers the whole question for that chunk*. The reused artifact is therefore a **complete, self-contained, already-executed sub-result** (`delivered` = "delivered orders in 2016–2018, with year/month"). Reusing it is **low-risk and high-leverage**: the composer just wraps a final `SELECT` around a block that is known to run and known to be correct on a sibling question. Nothing else has to be generated (`gen=0`), so there are **no other pieces that can go wrong**. Result: reuse never breaks correctness → **7/7**.

- **N×M reuses a *sub-goal fragment* (`gen=3`).** In N×M the question is split into M sub-goals; a reused view is **one fragment of a multi-part plan**, and the run still has to **generate 3 more** sub-goal views (`gen=3`) and then **compose all of them**. Correctness is now **conjunctive** — it needs (right decomposition) × (each of the 3 fresh views right) × (the reused fragment *fitting this* decomposition) × (compose right). A fragment proven on a *different* question's decomposition often does not slot cleanly into the current one, and even when it does, the other 3 generated pieces or the composition can fail. Result: the reused fragment is a minority contributor to a fragile multi-part query → **0/5**.

**In one line:** v2m reuses a **finished answer-skeleton**; N×M reuses a **loose part** that must survive a conjunction of other parts. Whole-view reuse is *composition-safe*; fragment reuse is *composition-fragile*. This is the same "conjunctive fan-in" that makes N×M lose on Spider2-lite overall (14% vs v2m 33%) — reuse inherits the architecture's fragility.

**Caveat (honesty):** v2m's 7/7 does **not** mean reuse *caused* 7 wins — these are easy questions solvable without memory too (AV-SQL also solves them). The correct reading is **v2m reuse is *harmless-to-helpful* (never breaks a solvable question), N×M reuse is *harmful* (its fragment-reuse questions are all wrong)**. Neither *systematically raises* accuracy on these benchmarks, but they fail very differently, and that difference is exactly the whole-view-vs-fragment mechanism above.

---

## 6. How the skill-graph / view-memory is built
Same mechanism family as the earlier docs: an offline-growing, per-DB store of accepted views keyed by a 384-d MiniLM embedding of the question; **deposit** each accepted view; **retrieve** cosine-similar same-DB views before generating, and (v2m) accept via a reuse-verifier or (AV-SQL) inject as a CTE hint. v2m stores/reuses **whole-question views**; N×M stores/reuses **sub-goal views** — the storage granularity is precisely what §5 shows to be decisive. See `docs/skill_graph_case_study_local050.md` §5 for the AV-SQL skill-graph internals (`av_sql/skill_graph.py`); the SkiewSQL view-graph is `skiewsql/core.py` (`ViewGraph`).

---

## 7. Statistics

**This question (`local031`):**

| metric | v2m (ours) | AV-SQL + LSH + skill-graph |
|---|---|---|
| views reused | **1** (`delivered`, whole view) | reuse fired (hint) |
| views generated | **0** | 6 CTEs |
| reused view load-bearing? | **yes** (referenced 4×) | — |
| final SQL executes | yes | yes |
| **correct** | **yes** ✅ | **yes** ✅ |

**Aggregate (Spider2-lite):**

| our method | reuse-fired qs | reuse-correct | signature | benchmark accuracy |
|---|---|---|---|---|
| **v2m** | 7 | **7/7** | `reuse=1, gen=0, ok=1` | 33.1% (121) |
| **N×M** | 5 | **0/5** | `reuse=1, gen=3, ok=0` | 14.0% (121) |

*(Reuse never coincides with an AV-SQL loss, so no v2m-reuse-differentiating win exists; the meaningful contrast is v2m-reuse-safe vs N×M-reuse-fragile.)*

---

## Reproduction
- v2m result + pred: `skiewsql/results_real/S2Lv2m_spider2lite_A_SkiewSQL.json` (`local031`)
- AV-SQL+skill-graph logs: `~/skiew_together/avsql_s2local/logs_reuse/local031/0/`
- Saved SQL: `~/skiew_together/avsql_s2local/local031_{v2m,avsql}.sql`
- v2m vs N×M reuse signatures: `~/skiew_together/logs/s2l_v2m.log`, `s2l_nxm.log` (`grep 'reuse=[1-9]'`)
- Code: `skiewsql/realrun.py` (`--nx1` v2m, `--nxm` N×M), `skiewsql/core.py` (ViewGraph)
