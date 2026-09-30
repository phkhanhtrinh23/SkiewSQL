# Skill graph — `modern_data` (2 skills)

**Skill `joined_zip_records`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `zip_code` |
| output columns | `zip_code`, `borough_name`, `median_income`, `mean_income`, `tree_id` |
| source tables | `trees`, `income_trees` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `top_boroughs` |
| validated_on | — |
| counter_examples | 0 |

_merges tree and income datasets on ZIP code to produce a wide relation containing both tree and income attributes_

```sql
SELECT t.zipcode AS zip_code, t.boroname AS borough_name, i.Estimate_Median_income AS median_income, i.Estimate_Mean_income AS mean_income, t.tree_id AS tree_id
FROM trees t
JOIN income_trees i ON t.zipcode = i.zipcode
```

---

**Skill `top_boroughs`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `borough_name` |
| output columns | `borough_name`, `total_trees`, `average_mean_income` |
| source tables | `joined_zip_records` |
| depends_on (builds on) | `joined_zip_records` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_aggregates joined records by borough to compute total tree counts and average mean incomes, then applies ranking and limiting to return the top results_

```sql
SELECT borough_name, COUNT(tree_id) AS total_trees, AVG(mean_income) AS average_mean_income FROM joined_zip_records GROUP BY borough_name
```

---
