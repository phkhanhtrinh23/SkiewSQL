# Skill graph — `city_legislation` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `cities` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Find, among database records for Chinese cities (country_code_2 = 'cn') during July 2021, the shortest and the longest streaks of consecutive dates present; for each date in those two streaks, r_

```sql
SELECT
  c.city_id,
  c.city_name,
  c.country_code_2,
  c.insert_date
FROM cities c
WHERE c.country_code_2 = 'cn'
  AND c.insert_date >= '2021-07-01'
  AND c.insert_date <= '2021-07-31'
```

---
