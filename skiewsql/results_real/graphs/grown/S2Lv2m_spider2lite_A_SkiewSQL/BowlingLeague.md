# Skill graph — `BowlingLeague` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Bowler_Scores`, `Bowlers`, `Tourney_Matches`, `Tournaments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Find all individual game records for bowlers who have won games with a handicap score of 190 or less at each of the three venues Thunderbird Lanes, Totem Lanes, and Bolero Lanes, and return thos_

```sql
SELECT
  bs."BowlerID",
  b."BowlerFirstName",
  b."BowlerLastName",
  bs."MatchID",
  bs."GameNumber",
  bs."HandiCapScore",
  t."TourneyDate",
  t."TourneyLocation"
FROM "Bowler_Scores" bs
JOIN "Bowlers" b
  ON bs."BowlerID" = b."BowlerID"
JOIN "Tourney_Matches" tm
  ON bs."MatchID" = tm."MatchID"
JOIN "Tournaments" t
  ON tm."TourneyID" = t."TourneyID"
WHERE bs."WonGame" = 1
  AND bs."HandiCapScore" <= 190
  AND t."TourneyLocation" IN ('Thunderbird Lanes', 'Totem Lanes', 'Bolero Lanes')
```

---
