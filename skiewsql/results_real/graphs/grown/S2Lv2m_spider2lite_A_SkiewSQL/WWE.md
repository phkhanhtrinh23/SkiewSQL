# Skill graph — `WWE` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Matches`, `Cards`, `Promotions`, `Belts` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Find the NXT championship match (a match for an NXT title) that had the shortest match duration, excluding any matches that include the phrase "title change" in their match description, and retu_

```sql
SELECT
  Matches.id AS match_id,
  Matches.card_id,
  Matches.winner_id,
  Matches.loser_id,
  Matches.duration,
  Matches.title_id,
  Matches.title_change
FROM Matches
JOIN Cards ON Cards.id = Matches.card_id
JOIN Promotions ON Promotions.id = Cards.promotion_id
JOIN Belts ON Belts.id = Matches.title_id
WHERE Belts.name LIKE '%NXT%' 
  AND LOWER(Matches.win_type || ' ' || COALESCE(Matches.win_type, '')) NOT LIKE '%title change%'
  OR LOWER(COALESCE(Matches.win_type, '')) NOT LIKE '%title change%'
```

---
