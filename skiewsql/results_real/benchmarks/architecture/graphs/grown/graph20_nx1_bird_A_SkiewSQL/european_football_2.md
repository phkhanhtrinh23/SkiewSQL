# Skill graph — `european_football_2` (2 skills)

**Skill `chunk_view_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Team_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | Which league had the most goals in the 2016 season?. What is the average height of players born between 1990 and 1995?. List the players' api id who had the highest above average overall ratings in 2010.. List the top 5 leagues in ascending order of the number of goals made in all seasons combined.. |
| counter_examples | 0 |

_Task: Identify the player with the maximum overall rating and return their API ID. Required outputs: The API ID of the player with the highest overall rating._

```sql
SELECT
  T.team_api_id
FROM Team_Attributes AS T
LIMIT 1
```

---

**Skill `chunk_view_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Identify the player with the maximum overall rating and return their API ID. Required outputs: The API ID of the player with the highest overall rating._

```sql
SELECT
  "home_player_X1"
FROM "Match"
ORDER BY
  "B365H" DESC
LIMIT 1
```

---
