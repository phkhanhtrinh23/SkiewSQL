# Skill-Graph Reuse — Case Study (Spider2-lite `local050`)

> Historical experiment. The graph prototype described here has been removed. The maintained pipeline uses the flat per-database registry in `skiewsql/core.py` and `skiewsql/registry.py`; AV-SQL preprocessing is consolidated in `skiewsql/avsql_prep.py`.

**A question that AV-SQL + LSH + skill-graph answers correctly and AV-SQL + LSH (original) gets wrong**, documented end-to-end: context, views generated vs. reused, composition, the exact failure/success step, how the skill-graph is built, and statistics.

- **System under test:** the real AV-SQL codebase (rephrase → per-chunk CTE → planner → SQL → revise-with-5-execution-fix-attempts) + AV-SQL's native full-scan MinHash-LSH value retrieval.
- **Historical addition (the only change):** a persistent **skill-graph** at the CTE step — retrieve embedding-similar CTEs proven on the same DB and offer them for reuse, then deposit each accepted CTE. This implementation was retired in favor of the indexed registry.
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
| 4 | `monthly_projection_local` | growth = (2020−2019)/2019. Project 2021 | month |
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

i.e. **the same projection pipeline, differing only in the final aggregation (average vs. median).** The skill-graph had deposited that pipeline's CTE. On `local050` it retrieved it (cosine ≥ 0.5) and offered it back.

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

### 2c. Full generated SQL — verbatim, exactly as executed and scored

#### Original (AV-SQL + LSH) — result `59.66511217365958` ❌
```sql
WITH
`sales_filtered` AS (
  SELECT
    `s`.`amount_sold`,
    `t`.`calendar_year` AS `year`,
    `t`.`calendar_month_number` AS `month`
  FROM `sales` AS `s`
  INNER JOIN `customers` AS `c` ON `s`.`cust_id` = `c`.`cust_id`
  INNER JOIN `countries` AS `co` ON `c`.`country_id` = `co`.`country_id`
  INNER JOIN `promotions` AS `p` ON `s`.`promo_id` = `p`.`promo_id`
  INNER JOIN `channels` AS `ch` ON `s`.`channel_id` = `ch`.`channel_id`
  INNER JOIN `times` AS `t` ON `s`.`time_id` = `t`.`time_id`
  WHERE `co`.`country_name` = 'France'
    AND `t`.`calendar_year` IN (2019, 2020)
    AND `p`.`promo_total_id` = 1
    AND `ch`.`channel_total_id` = 1
    AND `s`.`amount_sold` IS NOT NULL
),
`monthly_avg` AS (
  SELECT
    `year`,
    `month`,
    AVG(`amount_sold`) AS `avg_amount_sold`
  FROM `sales_filtered`
  GROUP BY `year`, `month`
),
`monthly_pair` AS (
  SELECT
    m19.`month` AS `month`,
    m19.`avg_amount_sold` AS `avg_2019_m`,
    m20.`avg_amount_sold` AS `avg_2020_m`
  FROM `monthly_avg` AS m19
  INNER JOIN `monthly_avg` AS m20
    ON m19.`month` = m20.`month`
  WHERE m19.`year` = 2019
    AND m20.`year` = 2020
    AND m19.`avg_amount_sold` IS NOT NULL
    AND m19.`avg_amount_sold` != 0
),
`monthly_projection_local` AS (
  SELECT
    `month`,
    `avg_2019_m`,
    `avg_2020_m`,
    ( (`avg_2020_m` - `avg_2019_m`) / NULLIF(`avg_2019_m`, 0) ) AS `growth_rate_m`,
    `avg_2020_m` * (1.0 + ( (`avg_2020_m` - `avg_2019_m`) / NULLIF(`avg_2019_m`, 0) )) AS `projected_avg_2021_local`
  FROM `monthly_pair`
),
`monthly_projected_usd` AS (
  SELECT
    mpl.`month`,
    mpl.`projected_avg_2021_local`,
    cur.`to_us` AS `to_us`,
    mpl.`projected_avg_2021_local` * cur.`to_us` AS `projected_avg_2021_usd`
  FROM `monthly_projection_local` AS mpl
  INNER JOIN `currency` AS cur
    ON cur.`country` = 'France'
   AND cur.`year` = 2021
   AND cur.`month` = mpl.`month`
  WHERE cur.`to_us` IS NOT NULL
),
`ordered` AS (
  SELECT
    `projected_avg_2021_usd`,
    ROW_NUMBER() OVER (ORDER BY `projected_avg_2021_usd`) AS rn,
    COUNT(*) OVER () AS total
  FROM `monthly_projected_usd`
)
SELECT
  CASE
    WHEN (SELECT total FROM `ordered` LIMIT 1) = 0 THEN NULL
    WHEN (SELECT total FROM `ordered` LIMIT 1) % 2 = 1 THEN
      (SELECT `projected_avg_2021_usd`
       FROM `ordered`
       WHERE rn = ((SELECT total FROM `ordered` LIMIT 1) + 1) / 2
       LIMIT 1)
    ELSE
      (SELECT AVG(`projected_avg_2021_usd`)
       FROM `ordered`
       WHERE rn IN ((SELECT total FROM `ordered` LIMIT 1) / 2,
                    (SELECT total FROM `ordered` LIMIT 1) / 2 + 1))
  END AS `median_projected_avg_2021_usd`;
```

> **Grain bug (line-level):** `sales_filtered` never selects `prod_id`, and `monthly_avg` does `AVG(amount_sold) GROUP BY year, month`. Every downstream CTE therefore works on a *month-level average of individual sale rows*, not on per-product monthly totals. The projection and median are computed on the wrong quantity → `59.67`.

#### Ours (AV-SQL + LSH + skill-graph) — result `2552.6959807204075` ✅
```sql
WITH
`filtered_sales` AS (
    SELECT
        `s`.`prod_id`,
        `s`.`amount_sold`,
        `t`.`calendar_year`,
        `t`.`calendar_month_number`
    FROM `sales` AS `s`
    INNER JOIN `promotions` AS `p` ON `s`.`promo_id` = `p`.`promo_id`
    INNER JOIN `channels` AS `ch` ON `s`.`channel_id` = `ch`.`channel_id`
    INNER JOIN `customers` AS `cu` ON `s`.`cust_id` = `cu`.`cust_id`
    INNER JOIN `countries` AS `co` ON `cu`.`country_id` = `co`.`country_id`
    INNER JOIN `times` AS `t` ON `s`.`time_id` = `t`.`time_id`
    WHERE
        `p`.`promo_total_id` = 1
        AND `ch`.`channel_total_id` = 1
        AND `co`.`country_name` = 'France'
        AND `t`.`calendar_year` IN (2019, 2020)
        AND `s`.`amount_sold` IS NOT NULL
),
`monthly_product_sales` AS (
    SELECT
        `prod_id`,
        `calendar_year` AS `year`,
        `calendar_month_number` AS `month`,
        SUM(`amount_sold`) AS `monthly_sales`
    FROM `filtered_sales`
    GROUP BY
        `prod_id`, `year`, `month`
),
`sales_2019` AS (
    SELECT `prod_id`, `month`, `monthly_sales`
    FROM `monthly_product_sales`
    WHERE `year` = 2019
),
`sales_2020` AS (
    SELECT `prod_id`, `month`, `monthly_sales`
    FROM `monthly_product_sales`
    WHERE `year` = 2020
),
`growth` AS (
    SELECT
        `s20`.`prod_id`,
        `s20`.`month`,
        `s19`.`monthly_sales` AS `sales_2019`,
        `s20`.`monthly_sales` AS `sales_2020`,
        ((`s20`.`monthly_sales` - `s19`.`monthly_sales`) * 1.0) / `s19`.`monthly_sales` AS `growth_rate`
    FROM `sales_2020` AS `s20`
    INNER JOIN `sales_2019` AS `s19`
        ON `s20`.`prod_id` = `s19`.`prod_id`
        AND `s20`.`month` = `s19`.`month`
    WHERE
        `s19`.`monthly_sales` IS NOT NULL
        AND `s19`.`monthly_sales` <> 0
),
`projected_2021` AS (
    SELECT
        `prod_id`,
        `month`,
        `sales_2020` * (1.0 + `growth_rate`) AS `projected_2021_amount`
    FROM `growth`
),
`currency_2021` AS (
    SELECT
        `country`,
        `year`,
        `month`,
        `to_us`
    FROM `currency`
    WHERE
        `country` = 'France'
        AND `year` = 2021
),
`projected_usd` AS (
    SELECT
        `p`.`prod_id`,
        `p`.`month`,
        `p`.`projected_2021_amount`,
        `c`.`to_us`,
        `p`.`projected_2021_amount` * `c`.`to_us` AS `projected_2021_usd`
    FROM `projected_2021` AS `p`
    INNER JOIN `currency_2021` AS `c`
        ON `p`.`month` = `c`.`month`
),
`monthly_average` AS (
    SELECT
        `month`,
        AVG(`projected_2021_usd`) AS `monthly_avg`
    FROM `projected_usd`
    GROUP BY `month`
),
`monthly_avg_ranked` AS (
    SELECT
        `monthly_avg`,
        ROW_NUMBER() OVER (ORDER BY `monthly_avg`) AS `rn`,
        COUNT(*) OVER () AS `cnt`
    FROM `monthly_average`
)
SELECT
    AVG(`monthly_avg`) AS `median_of_monthly_averages_usd`
FROM `monthly_avg_ranked`
WHERE `rn` IN (
    CAST((`cnt` + 1) / 2 AS INTEGER),
    CAST((`cnt` + 2) / 2 AS INTEGER)
);
```

> **Correct grain (from the reused pipeline):** `filtered_sales` keeps `prod_id`. `monthly_product_sales` does `SUM(amount_sold) GROUP BY prod_id, year, month`. `growth` / `projected_2021` are per product. Only `monthly_average` collapses to a per-month `AVG` across products. Median over those monthly averages → `2552.70` (matches gold).

The two queries share the *same* skeleton shape (filter → monthly aggregate → 2019/2020 pair → growth → project → USD → median), but differ in the one decision that matters: **the reused version aggregates `SUM` per `prod_id`, the from-scratch version `AVG`s straight to month.**

---

## 3. How composition works

Both runs use AV-SQL's composition unchanged:

1. **Schema split → CTE agent(s).** complex_oracle fits one chunk (N=1), so one CTE agent runs. In the skill-graph run, its prompt is `schema_text + previous_cte_str + reuse_cte_str`, where `reuse_cte_str` is the injected "PROVEN REUSABLE CTEs" block (empty in the original run).
2. **CTE agent** emits a `WITH … ` exploratory CTE + a JSON of selected columns. AV-SQL executes it (5 fix-attempts on error/empty).
3. **Planner** turns the schema + accepted CTE text into a natural-language plan.
4. **SQL agent** writes the final query, *reusing the CTE definitions as the `WITH` prefix* and appending the answer `SELECT` (here, the median computation).
5. **ReviseSQL** runs the final SQL against SQLite. On error/empty it revises (≤5 attempts). The result table is what we score.

So the skill-graph's only leverage point is **step 1** — it seeds the CTE agent with a proven sub-pipeline. Steps 2–5 are identical AV-SQL machinery.

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

The retired prototype enabled this only when its config had a `skill_graph:` block, so base AV-SQL was untouched. It ran one process so memory grew sequentially with no write races.

**Data model.** Per DB, a list of entries `{question, tables, cte_sql, emb}`. `emb` is a 384-dim `all-MiniLM-L6-v2` (CPU) embedding of the question text. Persisted as one JSON (`graph_reuse.json`).

**Deposit** (after each accepted CTE, `SkillGraph.deposit`):
- key by `db_id`. Store the generated `cte_sql_query`, the tables it used (`filtered_schema_dict.keys()`), the question, and its embedding.
- dedupe on exact SQL. Append + atomic-save.

**Retrieve + inject** (before generating a chunk's CTE, `render_hints` → `retrieve`):
1. embed the current question.
2. over the same DB's entries, keep those with cosine ≥ `threshold` (0.5).
3. rank: entries whose stored tables overlap the current chunk's tables first, then by similarity.
4. take top-`k` (2), format as a "PROVEN REUSABLE CTEs … REUSE verbatim or lightly adapt … do not force an irrelevant one" block, appended to the CTE prompt via `reuse_cte_str`.

**How it helps (mechanism):** it turns *"generate a correct multi-step SQL skeleton from scratch"* into *"adapt a skeleton that already executed correctly on a similar question on this DB."* On `local050` that skeleton carried the **hard-won grain decision** (per-product SUM) that the from-scratch model got wrong. This is exactly the intended benefit: **memory transfers a proven sub-computation between near-duplicate questions.**

**Honest scope (important):** this benefit is *narrow* in our results. Across the full 135, +skill-graph and original scored **identically (both 36.3%)**. On the common-121 it was 47 vs 46 (net **+1**). Reuse fired on **63/135** questions but net-flipped very few, because (a) it only helps when a *genuinely relevant* prior CTE exists (sibling questions), and (b) the prompt correctly declines to force irrelevant hints (e.g. on `local023` a bowling CTE was offered for a batting question and ignored — that win was generation variance, not reuse). So `local050` is a *clean, real* reuse win, but the aggregate signal is **neutral**: skill-graph does not systematically beat plain AV-SQL+LSH on this benchmark with this model.

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
| net accuracy change | +1 on common-121 (47 vs 46). 0 on full-135 (49 vs 49) |
| accuracy | 36.3% (135) / **38.8%** (121) |
| baseline (AV-SQL+LSH, no skill-graph) | 36.3% (135) / **38.0%** (121) |

*Token counts are estimates: AV-SQL does not log usage natively, so tokens are approximated as (characters of all logged prompt+response content)/4. Reuse adds ~10% prompt tokens per fired question (the injected CTE block).*

---

## 7. Impact of the LSH value retrieval

Both runs in this study have AV-SQL's native MinHash-LSH value retrieval **ON** (full-scan). This section isolates what LSH actually contributes — on this example and in aggregate — since it is the value layer we deliberately enabled.

**What LSH does.** When the CTE agent emits a literal (e.g. a `WHERE` filter value), the value manager MinHash-queries the database's distinct string values and injects the closest *real* stored values back into the fix prompt (`Relevant stored values for 'X': …`), so the model can correct spelling / casing / format. It fires per literal. Numeric literals are skipped.

**On `local050` specifically.** The only text literal in either query is `'France'` (the `country_name` filter). Everything else is numeric (`promo_total_id=1`, `channel_total_id=1`, years 2019–2021). `'France'` is already spelled and cased correctly in **both** the original and the skill-graph SQL, so LSH simply confirmed it and changed nothing. **LSH is therefore not the differentiator on `local050`** — the win is entirely attributable to the skill-graph's reused pipeline. (Across the whole 135-question run, the value manager issued **477** value lookups.)

**Measured aggregate impact (BEAVER — the one place AV-SQL was run *with and without* LSH):**

| AV-SQL on BEAVER (108 gold-scored) | value layer | accuracy |
|---|---|---|
| AV-SQL (no LSH) | — | **2.8%** (3/108) |
| AV-SQL + full-scan LSH + skill-graph | 558 MB full-scan index | **2.8%** (3/108) |
| AV-SQL + full-scan LSH + CHESS linker | 558 MB full-scan index | **2.8%** (3/108) |
| AV-SQL + full-scan LSH only (baseline) | 558 MB full-scan index | *finishing. ≈2.8% expected* |

→ **Full-scan LSH moved BEAVER accuracy by 0 points.** Building a 558 MB MinHash index over all distinct string values of 97 tables / 1530 columns changed nothing: AV-SQL's bottleneck on BEAVER is *composing 11+ schema chunks*, not value spelling.

*(Spider2-lite caveat: only the LSH-**on** configuration was run there — 38.0% on common-121 — a matched LSH-**off** ablation was not executed, so the Spider2-lite LSH delta is unmeasured. Known gap. Can be run.)*

**Why LSH is (here) essentially neutral.** `gpt-5-mini` already sees each column's example values in the schema prompt and copies them faithfully, so it rarely mis-spells a filter literal — the exact error LSH exists to fix. LSH's benefit concentrates on (a) weaker models that hallucinate value spellings and (b) questions filtering on dirty/abbreviated values *not* shown as examples. Neither dominates these gpt-5-mini benchmarks, so LSH is close to inert — the same verdict we reach for the skill-graph. **On this model and these benchmarks, accuracy is driven by schema handling and decomposition, not by value retrieval.**

---

## Reproduction

- Original run logs: `~/skiew_together/avsql_s2local/logs/local050/0/`
- Skill-graph run logs: `~/skiew_together/avsql_s2local/logs_reuse/local050/0/`
- Skill-graph store: `~/skiew_together/avsql_s2local/graph_reuse.json` (key `complex_oracle`)
- Historical configurations: original AV-SQL and the retired skill-graph variant; their obsolete YAML files are not part of the maintained pipeline.
- Divergence set: `~/skiew_together/avsql_s2local/diff.json` (all 6 wins / 6 losses)
- Historical implementation: retired graph hook in the prototype CTE loop; current retrieval is in `skiewsql/registry.py`.
