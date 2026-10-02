# Skill graph — `modern_data` (1 skills)

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

_Task: From the combined dataset (which unifies the trees data with the income data by ZIP code, after filling missing ZIP values where necessary), identify the three boroughs that have the largest cou_

```sql
SELECT
  t.idx,
  t.tree_id,
  t.zipcode AS tree_zipcode,
  t.boroname AS borough,
  it.Estimate_Median_income,
  it.Estimate_Mean_income
FROM trees t
LEFT JOIN income_trees it
  ON t.zipcode = it.zipcode
WHERE 1=1
  -- keep rows where borough is present (may be filtered later)
  -- and income filters will be applied in later chunks/queries
```

---
