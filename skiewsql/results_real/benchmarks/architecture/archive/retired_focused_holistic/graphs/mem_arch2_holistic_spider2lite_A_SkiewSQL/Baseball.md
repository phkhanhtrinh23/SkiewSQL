# Skill graph — `Baseball` (1 skills)

**Skill `focused_whole_view`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `player`, `batting_postseason` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Identify the baseball players with the maximum combined values of games played, runs, hits, and home runs, along with their respective scores. Required outputs: A list of baseball player names. _

```sql
SELECT
  p.name_first,
  p.name_last,
  SUM(bp.g) AS total_games,
  SUM(bp.r) AS total_runs,
  SUM(bp.h) AS total_hits,
  SUM(bp.hr) AS total_hr
FROM player AS p
JOIN batting_postseason AS bp
  ON p.player_id = bp.player_id
GROUP BY
  p.player_id,
  p.name_first,
  p.name_last
ORDER BY
  total_games DESC
LIMIT 1
```

---
