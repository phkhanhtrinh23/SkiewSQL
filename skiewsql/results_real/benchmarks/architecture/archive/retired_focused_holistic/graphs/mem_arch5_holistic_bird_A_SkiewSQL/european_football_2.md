# Skill graph — `european_football_2` (1 skills)

**Skill `focused_whole_view`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 4 |

_Task: Identify the player with the maximum overall rating and return their API ID. Required outputs: The API ID of the player with the highest overall rating._

```sql
SELECT
  P.id
FROM Player AS P
JOIN Player_Attributes AS PA
  ON P.player_fifa_api_id = PA.player_fifa_api_id
ORDER BY
  PA.overall_rating DESC
LIMIT 1
```

---
