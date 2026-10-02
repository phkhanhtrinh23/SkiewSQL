# Skill graph — `modern_data` (2 skills)

**Skill `trees_income_joined`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `tree_record` |
| output columns | `tree_record`, `borough`, `median_income`, `mean_income` |
| source tables | `trees`, `income_trees` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `borough_aggregates` |
| validated_on | — |
| counter_examples | 0 |

_Joins trees and income datasets on ZIP code, filling missing ZIP values, and retains only records with a valid borough name and strictly positive median and mean incomes._

```sql
SELECT t.idx AS tree_record, t.boroname AS borough, i.Estimate_Median_income AS median_income, i.Estimate_Mean_income AS mean_income FROM trees t LEFT JOIN income_trees i ON t.zipcode = i.zipcode WHERE t.boroname IS NOT NULL AND t.boroname != '' AND i.Estimate_Median_income > 0 AND i.Estimate_Mean_income > 0
```

---

**Skill `borough_aggregates`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `borough` |
| output columns | `borough`, `total_trees`, `average_mean_income` |
| source tables | `trees_income_joined` |
| depends_on (builds on) | `trees_income_joined` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Groups the filtered tree records by borough to compute the total number of trees and the average mean income per borough._

```sql
SELECT borough, COUNT(*) AS total_trees, AVG(mean_income) AS average_mean_income FROM trees_income_joined GROUP BY borough
```

---
