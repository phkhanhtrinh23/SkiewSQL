# Skill graph — `IPL` (2 skills)

**Skill `over_runs`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `over_id` |
| output columns | `match_id`, `over`, `over_runs` |
| source tables | `batsman_scored`, `extra_runs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `max_run_over_bowlers` |
| validated_on | — |
| counter_examples | 0 |

_Total runs conceded per over within each match._

```sql
SELECT 
    match_id,
    over_id AS over,
    SUM(runs) AS over_runs
FROM (
    SELECT match_id, over_id, runs_scored AS runs FROM batsman_scored
    UNION ALL
    SELECT match_id, over_id, extra_runs AS runs FROM extra_runs
)
GROUP BY match_id, over_id
```

---

**Skill `max_run_over_bowlers`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `over`, `player_id` |
| output columns | `match_id`, `over`, `bowler_id`, `bowler_name`, `match_name`, `over_runs` |
| source tables | `over_runs`, `ball_by_ball`, `player`, `match` |
| depends_on (builds on) | `over_runs` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Joins overs with the maximum run total per match to their bowler and match details._

```sql
SELECT o.match_id, o.over, p.player_id AS bowler_id, p.player_name AS bowler_name, m.venue AS match_name, o.over_runs
FROM over_runs o
JOIN ball_by_ball b ON o.match_id = b.match_id AND o.over = b.over_id
JOIN player p ON b.bowler = p.player_id
JOIN match m ON o.match_id = m.match_id
GROUP BY o.match_id, o.over, p.player_id
```

---
