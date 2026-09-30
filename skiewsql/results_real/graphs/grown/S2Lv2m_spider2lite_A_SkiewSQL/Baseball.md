# Skill graph — `Baseball` (2 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute the average single-player career span in years for all baseball players by computing, for each player, the difference between their debut date and final game date expressed as years + mo_

```sql
SELECT
  player_id,
  debut,
  final_game
FROM player
WHERE debut IS NOT NULL
  AND final_game IS NOT NULL
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `batting`, `player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Find the baseball player given names for players who have the maximum value in each of these four statistics: games played, runs, hits, and home runs. Return the given name and the corresponding_

```sql
SELECT
  'games played' AS stat_name,
  b.player_id,
  p.name_given AS given_name,
  b.g AS stat_value
FROM batting b
JOIN player p USING(player_id)
WHERE b.g = (SELECT MAX(g) FROM batting)

UNION ALL

SELECT
  'runs' AS stat_name,
  b.player_id,
  p.name_given AS given_name,
  b.r AS stat_value
FROM batting b
JOIN player p USING(player_id)
WHERE b.r = (SELECT MAX(r) FROM batting)

UNION ALL

SELECT
  'hits' AS stat_name,
  b.player_id,
  p.name_given AS given_name,
  b.h AS stat_value
FROM batting b
JOIN player p USING(player_id)
WHERE b.h = (SELECT MAX(h) FROM batting)

UNION ALL

SELECT
  'home runs' AS stat_name,
  b.player_id,
  p.name_given AS given_name,
  b.hr AS stat_value
FROM batting b
JOIN player p USING(player_id)
WHERE b.hr = (SELECT MAX(hr) FROM batting)
```

---
