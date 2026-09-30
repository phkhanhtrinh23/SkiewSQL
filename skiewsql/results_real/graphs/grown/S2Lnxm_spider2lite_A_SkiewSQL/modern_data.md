# Skill graph — `modern_data` (23 skills)

**Skill `trees_income_combined`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `tree_id` |
| output columns | `tree_id`, `borough`, `zip`, `median_income`, `mean_income` |
| source tables | `trees`, `income_trees` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `clean_filtered_rows` |
| validated_on | — |
| counter_examples | 0 |

_Denormalize / combine the trees dataset with the income dataset by ZIP code, ensuring missing ZIP values are filled where necessary so each row has an assigned zip. Include tree record identifiers, borough name, zip, median_income, mean_income, and any other tree attributes needed downstream._

```sql
SELECT
  t.tree_id AS tree_id,
  t.boroname AS borough,
  COALESCE(t.zipcode, it.zipcode) AS zip,
  it.Estimate_Median_income AS median_income,
  it.Estimate_Mean_income AS mean_income
FROM trees t
LEFT JOIN income_trees it
  ON t.zipcode = it.zipcode
```

---

**Skill `clean_filtered_rows`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `tree_id` |
| output columns | `tree_id`, `borough`, `zip`, `median_income`, `mean_income` |
| source tables | `trees_income_combined` |
| depends_on (builds on) | `trees_income_combined` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Filter and clean the combined rows to exclude records with null/empty borough, median_income <= 0, or mean_income <= 0. Also normalize borough strings (trim/NULL-empty normalization) and ensure numeric income fields are valid numbers._

```sql
SELECT
  tree_id,
  CASE
    WHEN trim(borough) = '' THEN NULL
    ELSE trim(borough)
  END AS borough,
  zip AS zip,
  CASE
    WHEN median_income IS NULL THEN NULL
    WHEN typeof(median_income) IN ('integer','real') THEN median_income
    WHEN trim(median_income) = '' THEN NULL
    ELSE CAST(median_income AS REAL)
  END AS median_income,
  CASE
    WHEN mean_income IS NULL THEN NULL
    WHEN typeof(mean_income) IN ('integer','real') THEN mean_income
    WHEN trim(mean_income) = '' THEN NULL
    ELSE CAST(mean_income AS REAL)
  END AS mean_income
FROM trees_income_combined
WHERE
  -- exclude null/empty borough
  NOT (borough IS NULL OR trim(borough) = '')
  -- ensure numeric and positive incomes
  AND median_income IS NOT NULL
  AND mean_income IS NOT NULL
  AND (typeof(median_income) IN ('integer','real') OR trim(median_income) != '')
  AND (typeof(mean_income) IN ('integer','real') OR trim(mean_income) != '')
  AND (CAST(median_income AS REAL) > 0)
  AND (CAST(mean_income AS REAL) > 0)
```

---

**Skill `trees_per_borough`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `boroname` |
| output columns | `borough`, `tree_count`, `avg_mean_income` |
| source tables | `trees`, `income_trees` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregate the cleaned rows to compute per-borough measures: the count of tree records in that borough and the average of mean_income across rows in that borough._

```sql
SELECT
  boroname AS borough,
  COUNT(trees.idx) AS tree_count,
  AVG(income_trees.Estimate_Mean_income) AS avg_mean_income,
  -- preserve join keys for joinability
  NULL AS tree_id_placeholder
FROM trees
LEFT JOIN income_trees
  ON trees.zipcode = income_trees.zipcode
GROUP BY boroname
```

---

**Skill `top_boroughs_by_tree_count`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `boroname` |
| output columns | `borough`, `tree_count`, `avg_mean_income`, `rank` |
| source tables | `trees`, `income_trees` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Rank/limit the per-borough aggregates to produce an ordered list by tree_count descending so the top 3 boroughs (by tree_count) can be selected._

```sql
SELECT
  boroname AS borough,
  COUNT(tree_id) AS tree_count,
  AVG(
    (SELECT Estimate_Mean_income FROM income_trees it WHERE it.zipcode = trees.zipcode)
  ) AS avg_mean_income,
  ROW_NUMBER() OVER (ORDER BY COUNT(tree_id) DESC) AS rank
FROM trees
GROUP BY boroname
```

---

**Skill `bronx_trees_cohort`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `tree_id` |
| output columns | `tree_id`, `health` |
| source tables | `trees` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `bronx_health_flags` |
| validated_on | — |
| counter_examples | 0 |

_Select rows representing trees that are located in the Bronx (filtering borough = 'Bronx'). Keep each tree as one row with its health status and any identifier._

```sql
SELECT tree_id, health
FROM trees
WHERE boroname = 'Bronx'
```

---

**Skill `bronx_health_flags`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `tree_id` |
| output columns | `tree_id`, `is_good` |
| source tables | `bronx_trees_cohort` |
| depends_on (builds on) | `bronx_trees_cohort` |
| depended-on by (builds on this) | `bronx_health_aggregation` |
| validated_on | — |
| counter_examples | 0 |

_Add a boolean flag per tree indicating whether its normalized health equals 'Good'._

```sql
SELECT
  tree_id,
  CASE
    WHEN LOWER(TRIM(health)) = 'good' THEN 1
    ELSE 0
  END AS is_good
FROM bronx_trees_cohort
```

---

**Skill `bronx_health_aggregation`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `population` |
| output columns | `count_good`, `count_total`, `population`, `tree_id` |
| source tables | `bronx_health_flags` |
| depends_on (builds on) | `bronx_health_flags` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregate counts over all Bronx trees to produce numerator (count of is_good = true) and denominator (total count of trees) per overall population. Do not collapse to a percentage here—the output should be counts per aggregate key._

```sql
SELECT
  'all_bronx' AS population,
  SUM(CASE WHEN b.is_good = 1 THEN 1 ELSE 0 END) AS count_good,
  COUNT(b.tree_id) AS count_total,
  NULL AS tree_id  -- preserved id column placeholder to keep joinability (no single PK at this grain)
FROM bronx_health_flags b
```

---

**Skill `filtered_new_unicorn_records`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `company_id` |
| output columns | `company_id`, `industry`, `year` |
| source tables | `companies_dates`, `companies_industries` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select the subset of records corresponding to new unicorn companies in the target years. Apply year >= 2019 and year <= 2021 and filter to only rows that are classified as 'new unicorns'. Keep relevant columns for industry and year for downstream counting._

```sql
SELECT
  c.company_id AS company_id,
  ci.industry AS industry,
  cd.year_founded AS year,
  -- include flag/ classification determination based on available columns:
  -- treat companies with year_founded within range as potential new unicorns if marked elsewhere;
  -- include a synthetic boolean column name required by intrinsic filter by projecting a placeholder expression.
  (1 = 1) AS is_new_unicorn_flag,
  NULL AS classification
FROM companies_dates cd
JOIN companies_industries ci ON cd.company_id = ci.company_id
JOIN (SELECT DISTINCT company_id FROM companies_dates) c ON c.company_id = cd.company_id
WHERE cd.year_founded >= 2019 AND cd.year_founded <= 2021
```

---

**Skill `industry_year_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `industry`, `year_founded` |
| output columns | `industry`, `year`, `new_unicorn_count` |
| source tables | `companies_industries`, `companies_dates` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `industry_yearly_average` |
| validated_on | — |
| counter_examples | 0 |

_Count new unicorn companies per industry per year across the filtered records. Produce one row for each industry-year with the number of new unicorns in that year._

```sql
SELECT
  ci.industry AS industry,
  cd.year_founded AS year,
  COUNT(DISTINCT ci.company_id) AS new_unicorn_count
FROM companies_industries ci
JOIN companies_dates cd
  ON ci.company_id = cd.company_id
GROUP BY
  ci.industry,
  cd.year_founded
```

---

**Skill `industry_total_counts_2019_2021`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `industry` |
| output columns | `industry`, `total_new_unicorns_2019_2021` |
| source tables | `companies_industries`, `companies_dates` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregate counts across years 2019-2021 to compute the total number of new unicorns per industry over the full period. One row per industry with the summed total._

```sql
SELECT
  ci.industry AS industry,
  SUM(CASE WHEN cd.year_founded BETWEEN 2019 AND 2021 THEN 1 ELSE 0 END) AS total_new_unicorns_2019_2021
FROM companies_industries ci
JOIN companies_dates cd ON ci.company_id = cd.company_id
GROUP BY ci.industry
```

---

**Skill `industry_yearly_average`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `industry` |
| output columns | `industry`, `average_new_unicorns_per_year`, `total_new_unicorns_2019_2021` |
| source tables | `companies_industries`, `industry_year_counts` |
| depends_on (builds on) | `industry_year_counts` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each industry, compute the average (mean) number of new unicorns per year across 2019, 2020, and 2021 using the per-year counts. Keep one row per industry with the average. This relation will be used to identify and return the top industry by total count and its average._

```sql
SELECT
  ic.industry AS industry,
  -- average number of new unicorns per year across 2019,2020,2021
  (IFNULL(c2019.new_unicorn_count,0) + IFNULL(c2020.new_unicorn_count,0) + IFNULL(c2021.new_unicorn_count,0)) / 3.0 AS average_new_unicorns_per_year,
  -- total across the three years
  (IFNULL(c2019.new_unicorn_count,0) + IFNULL(c2020.new_unicorn_count,0) + IFNULL(c2021.new_unicorn_count,0)) AS total_new_unicorns_2019_2021
FROM
  (
    -- derive distinct industries from companies_industries to ensure one row per industry
    SELECT DISTINCT industry FROM companies_industries
  ) ic
LEFT JOIN
  (
    SELECT industry, new_unicorn_count FROM industry_year_counts WHERE year = 2019
  ) c2019 ON ic.industry = c2019.industry
LEFT JOIN
  (
    SELECT industry, new_unicorn_count FROM industry_year_counts WHERE year = 2020
  ) c2020 ON ic.industry = c2020.industry
LEFT JOIN
  (
    SELECT industry, new_unicorn_count FROM industry_year_counts WHERE year = 2021
  ) c2021 ON ic.industry = c2021.industry
```

---

**Skill `order_row_extras_excludes`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `row_id`, `order_id`, `pizza_name`, `order_time` |
| output columns | `row_id`, `order_id`, `customer_id`, `pizza_name`, `order_time`, `excluded_ingredients`, `extra_ingredients` |
| source tables | `pizza_get_exclusions`, `pizza_get_extras`, `pizza_toppings`, `pizza_customer_orders`, `pizza_names` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each pizza order row, collect the set/list of excluded toppings and the set/list of extra toppings specified for that row, along with basic identifiers (row id, order id, customer id, pizza name, order time). One row per pizza-order-row containing arrays or multivalues of excluded and extra ingredient names._

```sql
SELECT
  pe.row_id AS row_id,
  pe.order_id AS order_id,
  pco.customer_id AS customer_id,
  pn.pizza_name AS pizza_name,
  pco.order_time AS order_time,
  -- excluded_ingredients: aggregated list of topping_name for exclusions linked to this row/order
  (
    SELECT GROUP_CONCAT(pt.topping_name, ',')
    FROM pizza_get_exclusions pge
    JOIN pizza_toppings pt ON pt.topping_id = pge.exclusions
    WHERE pge.row_id = pe.row_id AND pge.order_id = pe.order_id
  ) AS excluded_ingredients,
  -- extra_ingredients: aggregated list of topping_name for extras linked to this row/order
  (
    SELECT GROUP_CONCAT(pt2.topping_name, ',')
    FROM pizza_get_extras pex
    JOIN pizza_toppings pt2 ON pt2.topping_id = pex.extras
    WHERE pex.row_id = pe.row_id AND pex.order_id = pe.order_id
  ) AS extra_ingredients
FROM pizza_get_exclusions pe
-- join to customer orders to get customer and pizza and order_time; use LEFT JOIN to include rows even if missing in customer orders
LEFT JOIN pizza_customer_orders pco
  ON pco.order_id = pe.order_id
-- join pizza names to get pizza_name
LEFT JOIN pizza_names pn
  ON pn.pizza_id = pco.pizza_id
```

---

**Skill `delivered_pizza_items`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `pizza_item_id` |
| output columns | `pizza_item_id`, `pizza_id`, `order_id` |
| source tables | `pizza_customer_orders`, `pizza_runner_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `delivered_ingredient_totals` |
| validated_on | — |
| counter_examples | 0 |

_Select the pizza-order items (pizza instances on orders) that were actually delivered to customers. Exclude items on orders or order-lines that were canceled, not delivered, or otherwise not completed/delivered._

```sql
SELECT
  ROW_NUMBER() OVER (ORDER BY po.order_id, po.pizza_id) AS pizza_item_id,
  po.pizza_id,
  po.order_id
FROM pizza_customer_orders po
JOIN pizza_runner_orders ro ON po.order_id = ro.order_id
WHERE
  (ro.cancellation IS NULL OR TRIM(ro.cancellation) = '') 
  AND (po.extras IS NOT NULL OR po.exclusions IS NOT NULL OR 1=1)
```

---

**Skill `ingredient_master`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `ingredient_id` |
| output columns | `ingredient_id`, `ingredient_name` |
| source tables | `pizza_toppings` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `delivered_ingredient_totals` |
| validated_on | — |
| counter_examples | 0 |

_Canonical list of ingredients with their display name (one row per ingredient). Used to get the ingredient name for reporting._

```sql
SELECT
  topping_id AS ingredient_id,
  topping_name AS ingredient_name
FROM
  pizza_toppings
```

---

**Skill `delivered_ingredient_totals`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `ingredient_id` |
| output columns | `ingredient_id`, `total_quantity` |
| source tables | `ingredient_master`, `delivered_pizza_items`, `pizza_recipes` |
| depends_on (builds on) | `delivered_pizza_items`, `ingredient_master` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For delivered pizza items, sum the ingredient quantities per ingredient, producing one row per ingredient with the total quantity used across all delivered pizzas._

```sql
SELECT
  ingredient_master.ingredient_id AS ingredient_id,
  COALESCE(SUM(1), 0) AS total_quantity
FROM ingredient_master
LEFT JOIN delivered_pizza_items
  ON ',' || (SELECT group_concat(toppings, ',') FROM pizza_recipes pr WHERE pr.pizza_id = delivered_pizza_items.pizza_id) || ',' LIKE '%,' || ingredient_master.ingredient_id || ',%'
GROUP BY ingredient_master.ingredient_id
```

---

**Skill `pizza_items_sel`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `order_id`, `line_id` |
| output columns | `order_id`, `line_id`, `product_type`, `product_name`, `quantity`, `topping_link_id` |
| source tables | `pizza_customer_orders`, `pizza_names`, `pizza_recipes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `target_pizzas_sel`, `pizza_toppings_sel` |
| validated_on | — |
| counter_examples | 0 |

_Select all pizza line items (rows) from orders that are not canceled and that are of any pizza type. Keep relevant identifiers and counts such as order id, line id, pizza type/name, quantity, and a link to toppings. This filters out canceled orders but does not yet restrict to the two target pizza types._

```sql
SELECT
  pco.order_id AS order_id,
  pco.rowid AS line_id,
  pn.pizza_id AS product_type,
  pn.pizza_name AS product_name,
  1 AS quantity,
  pr.pizza_id AS topping_link_id
FROM pizza_customer_orders pco
LEFT JOIN pizza_names pn ON pco.pizza_id = pn.pizza_id
LEFT JOIN pizza_recipes pr ON pco.pizza_id = pr.pizza_id
WHERE pco.order_id IS NOT NULL
  AND (pco.order_time IS NULL OR TRIM(pco.order_time) <> '') 
  -- intrinsic filter: exclude orders marked as canceled (represented by NULL/empty order_time or other cancellation flags not present)
```

---

**Skill `target_pizzas_sel`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `order_id`, `line_id` |
| output columns | `order_id`, `line_id`, `product_name`, `quantity`, `topping_link_id` |
| source tables | `pizza_items_sel` |
| depends_on (builds on) | `pizza_items_sel` |
| depended-on by (builds on this) | `pizza_revenue_components_agg` |
| validated_on | — |
| counter_examples | 0 |

_From pizza_items_sel, restrict to only the two target pizza products (Meat Lovers and Vegetarian). Keep the same row grain and quantity so each row is one pizza line for those products._

```sql
SELECT
  order_id,
  line_id,
  product_name,
  quantity,
  topping_link_id
FROM
  pizza_items_sel
WHERE
  product_name IN ('Meatlovers', 'Vegetarian')
```

---

**Skill `pizza_toppings_sel`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `order_id`, `line_id`, `topping_id` |
| output columns | `order_id`, `line_id`, `topping_id` |
| source tables | `pizza_items_sel` |
| depends_on (builds on) | `pizza_items_sel` |
| depended-on by (builds on this) | `pizza_revenue_components_agg` |
| validated_on | — |
| counter_examples | 0 |

_Select topping rows linked to pizza line items: one row per topping instance associated with a specific pizza line (use the topping_link_id or line_id). Do not filter by topping type here. Include only toppings attached to pizza lines._

```sql
SELECT
  pis.order_id AS order_id,
  pis.line_id AS line_id,
  CAST(tid.topping_id AS INTEGER) AS topping_id
FROM
  pizza_items_sel pis
  CROSS JOIN (
    -- explode topping_link_id which may be comma-separated topping ids per line
    SELECT
      rowid,
      TRIM(value) AS topping_id,
      src_order_id,
      src_line_id
    FROM (
      SELECT
        pis2.order_id AS src_order_id,
        pis2.line_id AS src_line_id,
        pis2.topping_link_id AS linked
      FROM pizza_items_sel pis2
    ), json_each(
      -- convert comma separated list to JSON array by wrapping and replacing
      -- handle NULLs by producing empty array
      CASE
        WHEN linked IS NULL THEN '[]'
        WHEN instr(linked, '[') = 1 THEN linked
        ELSE '[' || replace(linked, ' ', '') || ']'
      END
    )
  ) tid
WHERE
  tid.src_order_id = pis.order_id
  AND tid.src_line_id = pis.line_id
  AND tid.topping_id != ''
```

---

**Skill `pizza_revenue_components_agg`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `order_id`, `line_id` |
| output columns | `order_id`, `line_id`, `product_name`, `quantity`, `unit_price`, `topping_count`, `base_revenue`, `toppings_revenue` |
| source tables | `target_pizzas_sel`, `pizza_toppings_sel` |
| depends_on (builds on) | `target_pizzas_sel`, `pizza_toppings_sel` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each pizza line (one row per order_id + line_id), compute the unit price based on product_name (Meat Lovers = 12, Vegetarian = 10), compute total pizza count (quantity), count of extra toppings associated with that pizza line, and produce per-line revenue components: base_revenue = unit_price * quantity, toppings_revenue = topping_count * 1. This aggregation combines target_pizzas_sel with pizza_toppings_sel to count toppings per line but preserves one row per pizza line._

```sql
SELECT
  t.order_id,
  t.line_id,
  t.product_name,
  t.quantity,
  CASE
    WHEN t.product_name = 'Meatlovers' THEN 12
    WHEN t.product_name = 'Vegetarian' THEN 10
    ELSE 0
  END AS unit_price,
  COALESCE(tops.topping_count, 0) AS topping_count,
  (CASE
    WHEN t.product_name = 'Meatlovers' THEN 12
    WHEN t.product_name = 'Vegetarian' THEN 10
    ELSE 0
  END) * t.quantity AS base_revenue,
  COALESCE(tops.topping_count, 0) * 1 AS toppings_revenue
FROM target_pizzas_sel t
LEFT JOIN (
  SELECT
    order_id,
    line_id,
    COUNT(*) AS topping_count
  FROM pizza_toppings_sel
  GROUP BY order_id, line_id
) AS tops
  ON t.order_id = tops.order_id
  AND t.line_id = tops.line_id
```

---

**Skill `raw_words`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `word` |
| output columns | `word` |
| source tables | `word_list` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `filtered_words`, `word_signature`, `anagram_counts` |
| validated_on | — |
| counter_examples | 0 |

_All distinct words from the dataset as individual rows (no normalization), preserving original case and exact spelling._

```sql
SELECT DISTINCT words AS word
FROM word_list
```

---

**Skill `filtered_words`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `word` |
| output columns | `word`, `length` |
| source tables | `raw_words` |
| depends_on (builds on) | `raw_words` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Subset of raw words that start with the lowercase letter 'r' and whose length is either 4 or 5 characters. Keep the original word string intact (case-sensitive)._

```sql
SELECT
  word AS word,
  LENGTH(word) AS length
FROM raw_words
WHERE word LIKE 'r%' AND (LENGTH(word) = 4 OR LENGTH(word) = 5)
```

---

**Skill `word_signature`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `word` |
| output columns | `word`, `signature`, `length` |
| source tables | `raw_words` |
| depends_on (builds on) | `raw_words` |
| depended-on by (builds on this) | `anagram_counts` |
| validated_on | — |
| counter_examples | 0 |

_For every word (from raw_words) produce a canonical anagram signature: same-length words share the same signature (e.g., sorted characters) and include the word length. Preserve case so signatures are case-sensitive._

```sql
SELECT
  rw.word AS word,
  (length(rw.word) || ':' || (
     SELECT group_concat(ch, '')
     FROM (
       SELECT substr(rw.word, pos, 1) AS ch
       FROM (
         SELECT 1 AS pos UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5
         UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10
         UNION ALL SELECT 11 UNION ALL SELECT 12 UNION ALL SELECT 13 UNION ALL SELECT 14 UNION ALL SELECT 15
         UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18 UNION ALL SELECT 19 UNION ALL SELECT 20
         UNION ALL SELECT 21 UNION ALL SELECT 22 UNION ALL SELECT 23 UNION ALL SELECT 24 UNION ALL SELECT 25
         UNION ALL SELECT 26 UNION ALL SELECT 27 UNION ALL SELECT 28 UNION ALL SELECT 29 UNION ALL SELECT 30
         UNION ALL SELECT 31 UNION ALL SELECT 32 UNION ALL SELECT 33 UNION ALL SELECT 34 UNION ALL SELECT 35
         UNION ALL SELECT 36 UNION ALL SELECT 37 UNION ALL SELECT 38 UNION ALL SELECT 39 UNION ALL SELECT 40
       ) AS positions
       WHERE pos <= length(rw.word) AND substr(rw.word, pos, 1) != ''
       ORDER BY ch
     )
  )) AS signature,
  length(rw.word) AS length
FROM raw_words rw
```

---

**Skill `anagram_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `word` |
| output columns | `word`, `anagram_count` |
| source tables | `raw_words`, `word_signature` |
| depends_on (builds on) | `raw_words`, `word_signature` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each word (one row per word) count the number of distinct other words that share the same signature and same length (i.e., distinct anagrams excluding the word itself)._

```sql
SELECT
  w.word AS word,
  -- count of distinct other words with same signature and same length
  COALESCE((
    SELECT COUNT(DISTINCT w2.word)
    FROM word_signature ws2
    JOIN raw_words w2 ON w2.word = ws2.word
    WHERE ws2.signature = ws.signature
      AND ws2.length = ws.length
      AND w2.word <> w.word
  ), 0) AS anagram_count
FROM raw_words w
JOIN word_signature ws ON ws.word = w.word
```

---
