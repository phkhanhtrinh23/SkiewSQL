# Skill graph — `city_legislation` (1 skills)

**Skill `city_dates_july_2021`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `city`, `date` |
| output columns | `city`, `date` |
| source tables | `cities`, `legislation_date_dim` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Filter base events to the target country and month, retaining city and date._

```sql
SELECT c.city_name AS city, d.date FROM cities c, legislation_date_dim d
```

---
