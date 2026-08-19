# Skill-Graph Reuse — Case Study (Spider2-lite `local050`)

**A question that AV-SQL + LSH + skill-graph answers correctly and AV-SQL + LSH (original) gets wrong**, documented end-to-end: context, views generated vs. reused, composition, the exact failure/success step, how the skill-graph is built, and statistics.

- **System under test:** the real AV-SQL codebase (rephrase → per-chunk CTE → planner → SQL → revise-with-5-execution-fix-attempts) + AV-SQL's native full-scan MinHash-LSH value retrieval.
- **Our addition (the only change):** a persistent **skill-graph** at the CTE step — retrieve embedding-similar CTEs proven on the same DB and offer them for reuse; deposit each accepted CTE. Code: `av_sql/skill_graph.py`, wired in `av_sql/question.py`.
- **Model:** `gpt-5-mini` for every step, both runs. **Benchmark:** Spider2-lite local (SQLite). **Scorer:** Spider2 official execution-match (`skiewsql/spider2lite.py`).

On the common 121-question set: **original 38.0% (46/121)** vs **+skill-graph 38.8% (47/121)**. This is one of the questions behind that difference.

---

## 1. Context

**Question (`local050`, DB `complex_oracle`):**
> What is the **median of the average monthly projected sales in USD for France in 2021**, calculated by using the monthly sales data from 2019 and 2020 (filtered by `promo_total_id=1` and `channel_total_id=1`), applying the growth rate from 2019 to 2020 to project 2021, converting to USD based on the currency table, and then determining the monthly averages before finding their median?

**External knowledge:** `projection_calculation.md` (a projection recipe: project 2021 = 2020 × (1 + YoY growth), per the standard Oracle SH sample-schema task).

**Relevant schema (complex_oracle, Oracle "Sales History" style):**

| table | key columns used |
|---|---|
| `sales` | `prod_id`, `cust_id`, `promo_id`, `channel_id`, `time_id`, `amount_sold` |
| `times` | `time_id`, `calendar_year`, `calendar_month_number` |
| `promotions` | `promo_id`, `promo_total_id` |
| `channels` | `channel_id`, `channel_total_id` |
| `customers` | `cust_id`, `country_id` |
| `countries` | `country_id`, `country_name` |
| `currency` | `country`, `year`, `month`, `to_us` |
| `products` | `prod_id` (grain key) |

**The critical modelling requirement:** the projection must be computed **per product** (`prod_id`) — sales are summed per `prod_id`/month, growth is per product, projection is per product — and only **after** projecting are the products aggregated into a monthly average, whose **median** is the answer. Getting the *grain* right is the whole difficulty.

---

## 2. Views (CTEs) generated — original vs. ours, and what was reused

### 2a. Original (AV-SQL + LSH) — 6 CTEs built from scratch, **wrong grain**
The CTE step generated a single-chunk pipeline (N=1 schema part):

| # | CTE | what it does | grain |
|---|---|---|---|
| 1 | `sales_filtered` | join sales→country/promo/channel/times, filter France + flags + years | **row-level, no `prod_id` kept** |
| 2 | `monthly_avg` | `AVG(amount_sold)` grouped by `year, month` | **month-level (products collapsed too early)** |
| 3 | `monthly_pair` | self-join 2019↔2020 monthly averages | month |
| 4 | `monthly_projection_local` | growth = (2020−2019)/2019; project 2021 | month |
| 5 | `monthly_projected_usd` | × `currency.to_us` | month |
| 6 | `ordered` | `ROW_NUMBER()` for a median pick | month |

→ Final scalar **median = `59.66511…`**  ❌

### 2b. Skill-graph run — reused a proven pipeline, **correct grain**
Before generating, the skill-graph retrieved and **injected** this reuse hint (top-2 by embedding similarity on `complex_oracle`). The injected CTE block (verbatim, truncated) — note it is grouped **per `prod_id`**:

```sql
WITH `filtered_sales` AS (
    SELECT sales.prod_id, sales.time_id, sales.channel_id, sales.promo_id,
           sales.cust_id, sales.quantity_sold, sales.amount_sold,
           times.calendar_year, times.calendar_month_number
    FROM sales
    INNER JOIN promotions ... INNER JOIN channels ... INNER JOIN customers ...
    INNER JOIN countries ... INNER JOIN times ...
    WHERE promotions.promo_total_id = 1 AND channels.channel_total_id = 1
      AND countries.country_name = 'France' AND times.calendar_year IN (2019,2020)
      AND sales.amount_sold IS NOT NULL
),
`monthly_product_sales` AS (        -- << keeps prod_id grain
    SELECT prod_id, calendar_year AS year, calendar_month_number AS month,
           SUM(amount_sold) AS monthly_sales
    FROM filtered_sales GROUP BY prod_id, year, month
),
`sales_2019` AS (SELECT prod_id, month, monthly_sales FROM monthly_product_sales WHERE year=2019),
`sales_2020` AS (SELECT prod_id, month, monthly_sales FROM monthly_product_sales WHERE year=2020),
`growth`     AS ( ... (2020-2019)/2019 growth_rate PER prod_id, month ... ),
...
```

**Where the reused CTE came from:** a *sibling* question earlier in the same run —
> *"What is the **average** projected monthly sales in USD for France in 2021, considering only product sales with promotions where `promo_total_id = 1` and `channel_total_id = 1` …"*

i.e. **the same projection pipeline, differing only in the final aggregation (average vs. median).** The skill-graph had deposited that pipeline's CTE; on `local050` it retrieved it (cosine ≥ 0.5) and offered it back.

The skill-graph run's generated CTEs (9), adapting the reused pipeline:

| # | CTE | grain |
|---|---|---|
| 1 | `filtered_sales` (keeps `prod_id`) | row |
| 2 | `monthly_product_sales` = `SUM(amount_sold)` by **`prod_id`, year, month** | **product-month** ✅ |
| 3–4 | `sales_2019`, `sales_2020` | product-month |
| 5 | `growth` (per product-month) | product-month |
| 6 | `projected_2021` = 2020 × (1+growth) | product-month |
| 7 | `currency_2021` (France, 2021) | month |
| 8 | `projected_usd` = projected × `to_us` | product-month |
| 9 | `monthly_average` = `AVG(projected_usd)` by **month** (across products) | month |

→ then median over the 12 monthly averages = **`2552.6959…`**  ✅ (matches gold)

**Reused CTE names that survive into the final SQL:** `filtered_sales`, `monthly_product_sales`, `sales_2019`, `sales_2020`, `growth`, `projected_2021`, `currency_2021`, `projected_usd`, `monthly_average` — essentially the entire skeleton was reused and lightly adapted.

---

## 3. How composition works

Both runs use AV-SQL's composition unchanged:

1. **Schema split → CTE agent(s).** complex_oracle fits one chunk (N=1), so one CTE agent runs. In the skill-graph run, its prompt is `schema_text + previous_cte_str + reuse_cte_str`, where `reuse_cte_str` is the injected "PROVEN REUSABLE CTEs" block (empty in the original run).
2. **CTE agent** emits a `WITH … ` exploratory CTE + a JSON of selected columns; AV-SQL executes it (5 fix-attempts on error/empty).
3. **Planner** turns the schema + accepted CTE text into a natural-language plan.
4. **SQL agent** writes the final query, *reusing the CTE definitions as the `WITH` prefix* and appending the answer `SELECT` (here, the median computation).
5. **ReviseSQL** runs the final SQL against SQLite; on error/empty it revises (≤5 attempts). The result table is what we score.

So the skill-graph's only leverage point is **step 1** — it seeds the CTE agent with a proven sub-pipeline; steps 2–5 are identical AV-SQL machinery.

---

## 4. The exact step where the original fails and we succeed

**Single root cause: output grain.**

- **Original** collapsed products too early: `monthly_avg = AVG(amount_sold) GROUP BY year, month`. It computes a *row-level average of individual sales per month*, never forming per-product monthly totals. Growth and projection then operate on the wrong quantity, so the final median (**59.67**) is off by ~40×.
- **Skill-graph** inherited the correct grain from the reused CTE: `monthly_product_sales = SUM(amount_sold) GROUP BY prod_id, year, month`, then projects **per product**, and only aggregates to a monthly average **after** projection. Median = **2552.70**, matching gold.

Both queries **executed successfully** (no crash) — this is a **semantic** win, not a structural one. The revise/fix loop cannot catch it (the wrong query runs and returns a number). The only thing that supplied the correct grain was the **reused pipeline** from the sibling question. The original, generating from scratch, chose a plausible-but-wrong aggregation.

| | original | +skill-graph | gold |
|---|---|---|---|
| grain of monthly sales | `AVG` by month (no product) | `SUM` by **prod_id**, month | per product |
| final median | **59.67** ❌ | **2552.70** ✅ | 2552.70 |

---

## 5. How the skill-graph is built (and how it helps)

Code: `av_sql/skill_graph.py`; hook: `av_sql/question.py` (CTE loop). Enabled only when the config has a `skill_graph:` block, so base AV-SQL is untouched. Runs `n_processes: 1` so the graph grows sequentially with no write races.

**Data model.** Per DB, a list of entries `{question, tables, cte_sql, emb}`; `emb` is a 384-dim `all-MiniLM-L6-v2` (CPU) embedding of the question text. Persisted as one JSON (`graph_reuse.json`).

**Deposit** (after each accepted CTE, `SkillGraph.deposit`):
- key by `db_id`; store the generated `cte_sql_query`, the tables it used (`filtered_schema_dict.keys()`), the question, and its embedding;
- dedupe on exact SQL; append + atomic-save.

**Retrieve + inject** (before generating a chunk's CTE, `render_hints` → `retrieve`):
1. embed the current question;
2. over the same DB's entries, keep those with cosine ≥ `threshold` (0.5);
3. rank: entries whose stored tables overlap the current chunk's tables first, then by similarity;
4. take top-`k` (2), format as a "PROVEN REUSABLE CTEs … REUSE verbatim or lightly adapt … do not force an irrelevant one" block, appended to the CTE prompt via `reuse_cte_str`.

**How it helps (mechanism):** it turns *"generate a correct multi-step SQL skeleton from scratch"* into *"adapt a skeleton that already executed correctly on a similar question on this DB."* On `local050` that skeleton carried the **hard-won grain decision** (per-product SUM) that the from-scratch model got wrong. This is exactly the intended benefit: **memory transfers a proven sub-computation between near-duplicate questions.**

**Honest scope (important):** this benefit is *narrow* in our results. Across the full 135, +skill-graph and original scored **identically (both 36.3%)**; on the common-121 it was 47 vs 46 (net **+1**). Reuse fired on **63/135** questions but net-flipped very few, because (a) it only helps when a *genuinely relevant* prior CTE exists (sibling questions), and (b) the prompt correctly declines to force irrelevant hints (e.g. on `local023` a bowling CTE was offered for a batting question and ignored — that win was generation variance, not reuse). So `local050` is a *clean, real* reuse win, but the aggregate signal is **neutral**: skill-graph does not systematically beat plain AV-SQL+LSH on this benchmark with this model.

---

## 6. Statistics

**This question (`local050`):**

| metric | original | +skill-graph |
|---|---|---|
| CTE parts (schema chunks) | 1 | 1 |
| CTEs in final SQL | 6 | 9 (8 reused/adapted) |
| reuse hints injected | 0 | **1** (top-2 candidates, 1 block) |
| reused CTE names surviving to final SQL | — | **9** |
| est. tokens (all logged prompts+responses) | ~32.4k | ~35.7k (**+3.3k, ≈ +10%** for the reuse block) |
| logged LLM turns | ~4 | ~4 |
| final SQL executes | yes | yes |
| **correct** | **no (59.67)** | **yes (2552.70)** |

**Whole skill-graph run (135 questions, Spider2-lite):**

| metric | value |
|---|---|
| graph size at end | **135 CTEs** across **30 DBs** |
| questions where reuse was injected | **63 / 135** |
| questions won vs. original (skill-graph right, orig wrong) | 6 (5 of them had reuse fired) |
| questions lost vs. original | 6 |
| net accuracy change | +1 on common-121 (47 vs 46); 0 on full-135 (49 vs 49) |
| accuracy | 36.3% (135) / **38.8%** (121) |
| baseline (AV-SQL+LSH, no skill-graph) | 36.3% (135) / **38.0%** (121) |

*Token counts are estimates: AV-SQL does not log usage natively, so tokens are approximated as (characters of all logged prompt+response content)/4. Reuse adds ~10% prompt tokens per fired question (the injected CTE block).*

---

## Reproduction

- Original run logs: `~/skiew_together/avsql_s2local/logs/local050/0/`
- Skill-graph run logs: `~/skiew_together/avsql_s2local/logs_reuse/local050/0/`
- Skill-graph store: `~/skiew_together/avsql_s2local/graph_reuse.json` (key `complex_oracle`)
- Configs: `configs/spider2local/gpt5mini_config.yaml` (original), `configs/spider2local/gpt5mini_reuse.yaml` (skill-graph)
- Divergence set: `~/skiew_together/avsql_s2local/diff.json` (all 6 wins / 6 losses)
- Code: `av_sql/skill_graph.py`, hook in `av_sql/question.py` (`schema_split_type` CTE loop)
