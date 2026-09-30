# Skill graph — `WWE` (2 skills)

**Skill `nxt_title_matches`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `match_id` |
| output columns | `match_id`, `wrestler1_name`, `wrestler2_name`, `match_duration` |
| source tables | `Matches`, `Wrestlers` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `matches_ranked_by_duration` |
| validated_on | — |
| counter_examples | 0 |

_Denormalized match records joined with participant wrestler records to retrieve competitor names, restricted to title matches and excluding matches with title change indicators._

```sql
SELECT m.id AS match_id, w1.name AS wrestler1_name, w2.name AS wrestler2_name, m.duration AS match_duration FROM Matches m JOIN Wrestlers w1 ON m.winner_id = w1.id JOIN Wrestlers w2 ON m.loser_id = w2.id WHERE m.title_id IS NOT NULL AND m.title_change = 0
```

---

**Skill `matches_ranked_by_duration`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `match_id` |
| output columns | `match_id`, `wrestler1_name`, `wrestler2_name`, `match_duration`, `duration_rank` |
| source tables | `nxt_title_matches` |
| depends_on (builds on) | `nxt_title_matches` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Assigns a sequential rank to each valid match ordered by match duration in ascending order to identify the shortest match._

```sql
SELECT match_id, wrestler1_name, wrestler2_name, match_duration, ROW_NUMBER() OVER (ORDER BY match_duration ASC) AS duration_rank FROM nxt_title_matches
```

---
