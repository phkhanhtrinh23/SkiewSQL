# Skill graph — `BowlingLeague` (2 skills)

**Skill `qualifying_game_records`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `match_number`, `game_number` |
| output columns | `bowler_id`, `bowler_first_name`, `bowler_last_name`, `match_number`, `game_number`, `handicap_score`, `tournament_date`, `location` |
| source tables | `Bowler_Scores`, `Bowlers`, `Tourney_Matches`, `Tournaments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `final_game_records` |
| validated_on | — |
| counter_examples | 0 |

_game records where the bowler won and the handicap score is within the target threshold, restricted to the specified venues_

```sql
SELECT B.BowlerID AS bowler_id,
       B.BowlerFirstName AS bowler_first_name,
       B.BowlerLastName AS bowler_last_name,
       BS.MatchID AS match_number,
       BS.GameNumber AS game_number,
       BS.HandiCapScore AS handicap_score,
       T.TourneyDate AS tournament_date,
       T.TourneyLocation AS location
FROM Bowler_Scores BS
JOIN Bowlers B ON BS.BowlerID = B.BowlerID
JOIN Tourney_Matches TM ON BS.MatchID = TM.MatchID
JOIN Tournaments T ON TM.TourneyID = T.TourneyID
```

---

**Skill `final_game_records`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `match_number`, `game_number` |
| output columns | `bowler_id`, `bowler_first_name`, `bowler_last_name`, `match_number`, `game_number`, `handicap_score`, `tournament_date`, `location` |
| source tables | `qualifying_game_records` |
| depends_on (builds on) | `qualifying_game_records` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_joins qualifying game records with bowlers who have achieved at least one qualifying win at each of the three venues_

```sql
SELECT bowler_id, bowler_first_name, bowler_last_name, match_number, game_number, handicap_score, tournament_date, location FROM qualifying_game_records
```

---
