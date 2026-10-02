# Skill graph — `Baseball` (1 skills)

**Skill `focused_whole_view`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `player`, `batting` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Identify the baseball players with the maximum combined values of games played, runs, hits, and home runs, along with their respective scores. Required outputs: A list of baseball player names. _

```sql
SELECT
  p.name_first,
  p.name_last,
  SUM(CASE WHEN b.year = (SELECT MAX(year) FROM batting) THEN b.g ELSE 0 END) AS games_played,
  SUM(CASE WHEN b.year = (SELECT MAX(year) FROM batting) THEN b.r ELSE 0 END) AS runs,
  SUM(CASE WHEN b.year = (SELECT MAX(year) FROM batting) THEN b.h ELSE 0 END) AS hits,
  SUM(CASE WHEN b.year = (SELECT MAX(year) FROM batting) THEN b.hr ELSE 0 END) AS home_runs
FROM batting AS b
JOIN player AS p
  ON b.player_id = p.player_id
GROUP BY
  p.player_id
ORDER BY
  SUM(CASE WHEN b.year = (SELECT MAX(year) FROM batting) THEN b.g ELSE 0 END) DESC
LIMIT 1
```

---
