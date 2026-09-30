# Skill graph — `EU_soccer` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Team`, `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute the median value of the highest season goals for each team, where each team's 'highest season goals' is considered as a single numeric value and the median is calculated across those per_

```sql
SELECT
  Team.team_api_id,
  Team.team_long_name,
  "Match".season,
  -- include match goals for the team both as home and away contexts
  "Match".home_team_goal,
  "Match".away_team_goal
FROM "Team"
JOIN "Match"
  ON Team.team_api_id IN ("Match".home_team_api_id, "Match".away_team_api_id)
```

---
