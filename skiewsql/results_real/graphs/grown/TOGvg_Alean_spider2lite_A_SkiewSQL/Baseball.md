# Skill graph — `Baseball` (2 skills)

**Skill `player_career_spans`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `debut_date`, `final_date`, `career_span_years` |
| source tables | `player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `average_career_span` |
| validated_on | — |
| counter_examples | 0 |

_one row per baseball player containing debut date, final game date, and the computed career span in years derived from the absolute difference in years, months, and days_

```sql
SELECT player_id, debut AS debut_date, final_game AS final_date, CAST(ABS(julianday(final_game) - julianday(debut)) / 365.25 AS INTEGER) AS career_span_years FROM player
```

---

**Skill `average_career_span`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | `average_career_span_years` |
| source tables | `player_career_spans` |
| depends_on (builds on) | `player_career_spans` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_single-row aggregate computing the mean of the career span values across all players_

```sql
SELECT AVG(career_span_years) AS average_career_span_years FROM player_career_spans
```

---
