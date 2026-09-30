# Skill graph — `european_football_2` (1 skills)

**Skill `player_heights`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id`, `height`, `player_name` |
| output columns | `height`, `player_name` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Selects player height and player name._

```sql
SELECT
    p.height,
    p.player_name
FROM
    "Player" AS p
```

---
