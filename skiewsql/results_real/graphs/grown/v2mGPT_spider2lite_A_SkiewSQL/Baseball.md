# Skill graph — `Baseball` (1 skills)

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

_Task: Compute the average single career span value in years for all baseball players by, for each player, computing the absolute difference between their debut date and final game date expressed as ye_

```sql
SELECT
  player.player_id,
  player.debut,
  player.final_game
FROM player
WHERE player.debut IS NOT NULL
  AND player.final_game IS NOT NULL
```

---
