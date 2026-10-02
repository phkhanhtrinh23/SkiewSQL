# Skill graph — `city_legislation` (2 skills)

**Skill `chinese_city_dates_july2021`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `city_name`, `date` |
| output columns | `date`, `city_name` |
| source tables | `cities`, `legislation_date_dim` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `city_date_streaks` |
| validated_on | — |
| counter_examples | 0 |

_Daily records for Chinese cities in July 2021 with city name capitalized._

```sql
SELECT
    d.date,
    upper(substr(c.city_name, 1, 1)) || lower(substr(c.city_name, 2)) AS city_name
FROM cities AS c
JOIN legislation_date_dim AS d
    ON 1 = 1
WHERE c.country_code_2 = 'cn'
  AND date(REPLACE(d.date, '/', '-')) BETWEEN '2021-07-01' AND '2021-07-31'
```

---

**Skill `city_date_streaks`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `city_name`, `date` |
| output columns | `date`, `city_name`, `streak_id`, `streak_length` |
| source tables | — |
| depends_on (builds on) | `chinese_city_dates_july2021` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Consecutive date streaks per city with streak identifier and streak length._

```sql
SELECT
    normalized_date AS date,
    city_name,
    DENSE_RANK() OVER (PARTITION BY city_name ORDER BY grp) AS streak_id,
    COUNT(*) OVER (PARTITION BY city_name, grp) AS streak_length
FROM (
    SELECT
        normalized_date,
        city_name,
        julianday(normalized_date) - ROW_NUMBER() OVER (PARTITION BY city_name ORDER BY normalized_date) AS grp
    FROM (
        SELECT
            date(REPLACE(date, '/', '-')) AS normalized_date,
            city_name
        FROM chinese_city_dates_july2021
    )
)
```

---
