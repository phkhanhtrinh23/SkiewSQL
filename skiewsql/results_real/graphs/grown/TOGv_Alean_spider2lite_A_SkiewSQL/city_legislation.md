# Skill graph — `city_legislation` (2 skills)

**Skill `city_date_cohort`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `city`, `date` |
| output columns | `city`, `date` |
| source tables | `cities`, `legislation_date_dim` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `filtered_streak_dates` |
| validated_on | — |
| counter_examples | 0 |

_Base cohort of daily records per city, restricted to the specified country and month range._

```sql
SELECT cities.city_name AS city, legislation_date_dim.date FROM cities, legislation_date_dim
```

---

**Skill `filtered_streak_dates`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `city`, `date` |
| output columns | `date`, `city_name` |
| source tables | `city_date_cohort`, `cities` |
| depends_on (builds on) | `city_date_cohort` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Analytic window relation that detects consecutive date sequences per city, calculates each streak's length, and filters to retain specified sequence lengths per city._

```sql
WITH cte AS (
    SELECT
        cd.city,
        cd.date,
        c.city_name,
        LAG(cd.date) OVER (PARTITION BY cd.city ORDER BY cd.date) AS prev_date
    FROM city_date_cohort cd
    JOIN cities c ON cd.city = c.city_id
),
streaks AS (
    SELECT
        city,
        date,
        city_name,
        SUM(CASE WHEN prev_date IS NULL OR date != prev_date + ' 1 day' THEN 1 ELSE 0 END) OVER (PARTITION BY city ORDER BY date) AS streak_id
    FROM cte
)
SELECT date, city_name
FROM streaks
```

---
