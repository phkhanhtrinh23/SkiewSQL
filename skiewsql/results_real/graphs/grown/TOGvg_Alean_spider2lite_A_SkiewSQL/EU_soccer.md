# Skill graph — `EU_soccer` (2 skills)

**Skill `team_max_season_goals`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `team_id` |
| output columns | `team_id`, `max_season_goals` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `median_of_team_max` |
| validated_on | — |
| counter_examples | 0 |

_For each team, compute the highest total goals scored in any single season across the dataset._

```sql
SELECT team_id, MAX(season_goals) AS max_season_goals
FROM (
    SELECT home_team_api_id AS team_id, season, SUM(home_team_goal) AS season_goals
    FROM Match
    GROUP BY home_team_api_id, season
    UNION ALL
    SELECT away_team_api_id AS team_id, season, SUM(away_team_goal) AS season_goals
    FROM Match
    GROUP BY away_team_api_id, season
)
GROUP BY team_id
```

---

**Skill `median_of_team_max`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | `median_value` |
| source tables | `team_max_season_goals` |
| depends_on (builds on) | `team_max_season_goals` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Compute the median value of the per-team maximum season goals derived from the previous step._

```sql
SELECT AVG(max_season_goals) AS median_value
FROM (
  SELECT max_season_goals,
         ROW_NUMBER() OVER (ORDER BY max_season_goals) as rn,
         COUNT(*) OVER () as total
  FROM team_max_season_goals
)
WHERE rn IN ((total + 1) / 2, (total + 2) / 2)
```

---
