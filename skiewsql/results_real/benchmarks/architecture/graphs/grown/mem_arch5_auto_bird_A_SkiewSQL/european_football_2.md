# Skill graph — `european_football_2` (3 skills)

**Skill `player_ratings`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id`, `player_fifa_api_id` |
| output columns | `player_id`, `overall_rating` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `player_heights`, `player_crossing_performance` |
| validated_on | — |
| counter_examples | 0 |

_Selects player ratings from the player table._

```sql
SELECT
  p.id AS player_id,
  p.player_fifa_api_id AS overall_rating
FROM Player AS p
```

---

**Skill `player_heights`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_api_id` |
| output columns | `height`, `player_name` |
| source tables | `player` |
| depends_on (builds on) | `player_ratings` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Selects player height and player name._

```sql
SELECT
  p.height,
  p.player_name
FROM player AS p
```

---

**Skill `player_crossing_performance`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id`, `crossing` |
| output columns | `player_id` |
| source tables | `Player_Attributes`, `player_ratings` |
| depends_on (builds on) | `player_ratings` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Selects players based on their crossing action performance._

```sql
SELECT
  p.player_id
FROM player_ratings AS p
JOIN Player_Attributes AS a
  ON p.player_id = a.player_api_id
WHERE
  a.crossing > 0
```

---
