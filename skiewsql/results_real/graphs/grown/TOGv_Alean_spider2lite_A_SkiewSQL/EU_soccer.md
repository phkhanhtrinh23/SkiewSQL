# Skill graph — `EU_soccer` (1 skills)

**Skill `team_max_season_goals`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `team_api_id`, `team_long_name` |
| output columns | `team`, `max_season_goals` |
| source tables | `Match`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_maximum goals scored by each team in any single season_

```sql
SELECT
    t.team_long_name AS team,
    MAX(sub.season_goals) AS max_season_goals
FROM Team t
JOIN (
    SELECT
        t2.team_api_id,
        SUM(CASE WHEN m.home_team_api_id = t2.team_api_id THEN m.home_team_goal ELSE m.away_team_goal END) AS season_goals
    FROM Match m
    JOIN Team t2 ON m.home_team_api_id = t2.team_api_id OR m.away_team_api_id = t2.team_api_id
    GROUP BY t2.team_api_id, m.season
) sub ON t.team_api_id = sub.team_api_id
GROUP BY t.team_api_id, t.team_long_name
```

---
