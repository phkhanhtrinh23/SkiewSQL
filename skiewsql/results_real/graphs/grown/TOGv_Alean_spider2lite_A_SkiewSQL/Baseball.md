# Skill graph — `Baseball` (2 skills)

**Skill `player_career_dates`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `debut_date`, `final_game_date` |
| source tables | `player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `player_career_spans` |
| validated_on | — |
| counter_examples | 0 |

_For each baseball player, determine their earliest debut date and latest final game date across all recorded games._

```sql
SELECT player_id, debut AS debut_date, final_game AS final_game_date FROM player
```

---

**Skill `player_career_spans`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `career_span_years` |
| source tables | `player_career_dates` |
| depends_on (builds on) | `player_career_dates` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Compute each player's career span in decimal years by calculating the absolute differences in years, months, and days between debut and final dates, dividing months by 12 and days by 365, rounding each component to two decimal places, and summing them._

```sql
SELECT
    player_id,
    ROUND(ABS(CAST(SUBSTR(debut_date, 1, 4) AS INTEGER) - CAST(SUBSTR(final_game_date, 1, 4) AS INTEGER)), 2) +
    ROUND(ABS(CAST(SUBSTR(debut_date, 6, 2) AS INTEGER) - CAST(SUBSTR(final_game_date, 6, 2) AS INTEGER)) / 12.0, 2) +
    ROUND(ABS(CAST(SUBSTR(debut_date, 10, 2) AS INTEGER) - CAST(SUBSTR(final_game_date, 10, 2) AS INTEGER)) / 365.0, 2) AS career_span_years
FROM player_career_dates
```

---
