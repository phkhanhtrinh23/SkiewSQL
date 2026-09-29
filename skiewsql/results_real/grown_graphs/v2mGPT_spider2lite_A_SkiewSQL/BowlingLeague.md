# Skill graph — `BowlingLeague` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Bowler_Scores`, `Bowlers`, `Match_Games`, `Tourney_Matches`, `Tournaments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Return the specific game records for bowlers who have won games with a handicap score of 190 or less at all three venues Thunderbird Lanes, Totem Lanes, and Bolero Lanes; for each qualifying gam_

```sql
SELECT
  b."BowlerID" AS bowler_id,
  b."BowlerFirstName" AS first_name,
  b."BowlerLastName" AS last_name,
  bs."MatchID" AS match_number,
  bs."GameNumber" AS game_number,
  bs."HandiCapScore" AS handicap_score,
  t."TourneyDate" AS tournament_date,
  t."TourneyLocation" AS location
FROM "Bowler_Scores" bs
JOIN "Bowlers" b
  ON bs."BowlerID" = b."BowlerID"
JOIN "Match_Games" mg
  ON bs."MatchID" = mg."MatchID"
  AND bs."GameNumber" = mg."GameNumber"
JOIN "Tourney_Matches" tm
  ON mg."MatchID" = tm."MatchID"
JOIN "Tournaments" t
  ON tm."TourneyID" = t."TourneyID"
WHERE
  bs."WonGame" = TRUE
  AND bs."HandiCapScore" <= 190
  AND t."TourneyLocation" IN ('Thunderbird Lanes', 'Totem Lanes', 'Bolero Lanes')
```

---
