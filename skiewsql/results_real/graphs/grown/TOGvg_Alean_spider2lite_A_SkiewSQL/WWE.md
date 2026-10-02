# Skill graph — `WWE` (2 skills)

**Skill `filtered_matches`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `match_id` |
| output columns | `match_id`, `duration`, `wrestler1_id`, `wrestler2_id` |
| source tables | `Matches` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `named_matches` |
| validated_on | — |
| counter_examples | 0 |

_Matches restricted to specific event types and result conditions._

```sql
SELECT "id" AS "match_id", "duration" AS "duration", "winner_id" AS "wrestler1_id", "loser_id" AS "wrestler2_id" FROM "Matches"
```

---

**Skill `named_matches`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `wrestler_id` |
| output columns | `match_id`, `duration`, `wrestler_id`, `wrestler_name` |
| source tables | `Wrestlers` |
| depends_on (builds on) | `filtered_matches` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Denormalized relation linking matches to competitor records to retrieve names._

```sql
SELECT m.match_id, m.duration, m.wrestler1_id AS wrestler_id, w.name AS wrestler_name
FROM filtered_matches m
JOIN Wrestlers w ON m.wrestler1_id = w.id
UNION ALL
SELECT m.match_id, m.duration, m.wrestler2_id AS wrestler_id, w.name AS wrestler_name
FROM filtered_matches m
JOIN Wrestlers w ON m.wrestler2_id = w.id
```

---
