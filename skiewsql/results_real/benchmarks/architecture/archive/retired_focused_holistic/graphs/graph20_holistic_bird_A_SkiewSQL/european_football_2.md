# Skill graph — `european_football_2` (1 skills)

**Skill `focused_whole_view`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | What is the height of the tallest player? Indicate his name.. What is the average height of players born between 1990 and 1995?. Find the average number of long-shot done by Ahmed Samir Farag. |
| counter_examples | 0 |

_Task: Identify the player with the maximum overall rating and return their API ID. Required outputs: The API ID of the player with the highest overall rating._

```sql
SELECT
  T1."player_api_id"
FROM Player_Attributes AS T1
ORDER BY
  T1."overall_rating" DESC
LIMIT 1
```

---
