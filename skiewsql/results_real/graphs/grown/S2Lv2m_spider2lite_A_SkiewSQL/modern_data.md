# Skill graph — `modern_data` (6 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `trees`, `income_trees` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: From the combined dataset that unifies the trees data with the income data by ZIP code (after filling missing ZIP values where necessary), identify the three boroughs with the largest number of _

```sql
SELECT
  t.idx,
  t.tree_id,
  t.zipcode AS tree_zipcode,
  t.boroname AS borough,
  t.latitude,
  t.longitude,
  i.Estimate_Median_income,
  i.Estimate_Mean_income
FROM trees t
LEFT JOIN income_trees i
  ON t.zipcode = i.zipcode
WHERE 1=1
  -- keep rows where income values are present and positive (filters noted in task)
  AND (i.Estimate_Median_income IS NOT NULL AND i.Estimate_Median_income > 0)
  AND (i.Estimate_Mean_income IS NOT NULL AND i.Estimate_Mean_income > 0)
  -- keep only non-null, non-empty borough names
  AND t.boroname IS NOT NULL
  AND trim(t.boroname) <> ''
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `trees` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute the percentage of trees located in the Bronx whose health status is 'Good'. Required outputs: percentage: a single numeric value representing (number of trees in the Bronx with health st_

```sql
SELECT
  tree_id,
  status,
  health,
  boroname,
  zipcode,
  idx
FROM
  trees
WHERE
  boroname = 'Bronx'
```

---

**Skill `chunk_view_0_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `companies_industries`, `companies_dates` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute the average number of new unicorn companies per year, for each industry, over the period 2019 through 2021, and return the industry that has the highest average (the top industry) along _

```sql
SELECT
  companies_industries.company_id,
  companies_industries.industry,
  companies_dates.year_founded
FROM companies_industries
LEFT JOIN companies_dates
  ON companies_industries.company_id = companies_dates.company_id
WHERE companies_dates.year_founded IN (2019, 2020, 2021)
```

---

**Skill `chunk_view_0_3`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `pizza_clean_customer_orders`, `pizza_names`, `pizza_recipes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: For each pizza order row, produce one result row containing the row ID, order ID, customer ID, pizza name, and a single-string representation of the final ingredients computed by starting from t_

```sql
SELECT
  pco.order_id,
  pco.customer_id,
  pco.pizza_id,
  pn.pizza_name,
  pr.toppings,
  pco.exclusions AS order_exclusions,
  pco.extras AS order_extras,
  pco.order_time,
  pco.order_id AS row_id_candidate
FROM pizza_clean_customer_orders pco
LEFT JOIN pizza_names pn ON pco.pizza_id = pn.pizza_id
LEFT JOIN pizza_recipes pr ON pco.pizza_id = pr.pizza_id
```

---

**Skill `chunk_view_0_4`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `pizza_runner_orders`, `pizza_customer_orders`, `pizza_names`, `pizza_get_extras`, `pizza_get_exclusions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute the total revenue earned by Pizza Runner from all non-canceled orders comprised of Meat Lovers pizzas priced at $12 and Vegetarian pizzas priced at $10, including $1 extra per extra topp_

```sql
SELECT
  r.order_id,
  r.runner_id,
  r.cancellation,
  co.customer_id,
  co.pizza_id,
  pn.pizza_name,
  co.extras AS extras_text,
  get_extras.extras AS extras_code,
  get_extras.extras_count,
  get_exclusions.exclusions AS exclusions_code,
  get_exclusions.total_exclusions,
  -- keep raw order_time / pickup_time for potential time filters or joins
  co.order_time,
  r.pickup_time
FROM pizza_runner_orders AS r
JOIN pizza_customer_orders AS co ON co.order_id = r.order_id
LEFT JOIN pizza_names AS pn ON pn.pizza_id = co.pizza_id
LEFT JOIN pizza_get_extras AS get_extras ON get_extras.order_id = r.order_id
LEFT JOIN pizza_get_exclusions AS get_exclusions ON get_exclusions.order_id = r.order_id
```

---

**Skill `chunk_view_0_5`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `word_list` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Find words that are 4 or 5 characters long, start with the lowercase letter 'r', and for which there exists at least one other distinct anagram of the same length (case-sensitive). Return the fi_

```sql
SELECT
  w.words AS word
FROM
  word_list w
WHERE
  (length(w.words) = 4 OR length(w.words) = 5)
  AND w.words LIKE 'r%'
```

---
