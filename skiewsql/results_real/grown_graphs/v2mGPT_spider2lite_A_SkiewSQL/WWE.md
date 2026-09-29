# Skill graph — `WWE` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Matches`, `Belts`, `Wrestlers`, `Cards`, `Promotions`, `Locations` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Find the two wrestler names who fought in the shortest-duration NXT title match, excluding any NXT title matches that were marked with 'title change'.
Required outputs: wrestler1_name; wrestler2_

```sql
SELECT
  Matches.id AS match_id,
  Matches.card_id,
  Matches.winner_id,
  Matches.loser_id,
  Matches.win_type,
  Matches.duration,
  Matches.title_id,
  Matches.title_change,
  Belts.id AS belt_id,
  Belts.name AS belt_name,
  Wrestlers_winner.id AS winner_wrestler_id,
  Wrestlers_winner.name AS winner_wrestler_name,
  Wrestlers_loser.id AS loser_wrestler_id,
  Wrestlers_loser.name AS loser_wrestler_name,
  Cards.event_date,
  Cards.event_id,
  Cards.promotion_id,
  Promotions.name AS promotion_name,
  Cards.location_id,
  Locations.name AS location_name
FROM Matches
LEFT JOIN Belts ON Matches.title_id = Belts.id
LEFT JOIN Wrestlers AS Wrestlers_winner ON Matches.winner_id = Wrestlers_winner.id
LEFT JOIN Wrestlers AS Wrestlers_loser ON Matches.loser_id = Wrestlers_loser.id
LEFT JOIN Cards ON Matches.card_id = Cards.id
LEFT JOIN Promotions ON Cards.promotion_id = Promotions.id
LEFT JOIN Locations ON Cards.location_id = Locations.id
WHERE Belts.name LIKE '%NXT%'
  AND (Matches.title_change IS NULL OR Matches.title_change = 0)
```

---
