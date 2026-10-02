# Skill graph — `european_football_2` (2 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Player_Attributes`, `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 4 |

_Task: Identify the player with the maximum overall rating and return their API ID. Required outputs: The API ID of the player with the highest overall rating. Filters: The overall rating must be maxim_

```sql
SELECT
  T1.player_api_id
FROM Player_Attributes AS T1
INNER JOIN Player AS T2
  ON T1.player_api_id = T2.player_api_id
ORDER BY
  T1.overall_rating DESC
LIMIT 1
```

---

**Skill `chunk_view_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Team`, `Team_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Identify the player with the maximum overall rating and return their API ID. Required outputs: The API ID of the player with the highest overall rating. Filters: The overall rating must be maxim_

```sql
SELECT
  T.team_api_id
FROM Team AS T
JOIN Team_Attributes AS TA
  ON T.team_api_id = TA.team_api_id
ORDER BY TA.buildUpPlaySpeed DESC
LIMIT 1
```

---
