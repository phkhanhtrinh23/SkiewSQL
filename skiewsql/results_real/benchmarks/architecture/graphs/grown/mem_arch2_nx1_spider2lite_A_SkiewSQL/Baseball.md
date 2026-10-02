# Skill graph — `Baseball` (2 skills)

**Skill `chunk_view_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Calculate the average career span in years for all baseball players, considering the difference between their debut and final game dates, rounded to two decimal places for each component and the_

```sql
SELECT
  CAST(
    (
      JULIANDAY(
        'final_game'
      ) - JULIANDAY('debut')
    ) / 365.25 AS NUMERIC(10, 2)
) AS avg_career_span
FROM player
```

---

**Skill `chunk_view_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Calculate the average career span in years for all baseball players, considering the difference between their debut and final game dates, rounded to two decimal places for each component and the_

```sql
SELECT
  T1.year AS year1,
  T2.year AS year2
FROM team AS T1
INNER JOIN team AS T2
  ON T1.year = T2.year
WHERE
  T1.year < T2.year
LIMIT 0
```

---
