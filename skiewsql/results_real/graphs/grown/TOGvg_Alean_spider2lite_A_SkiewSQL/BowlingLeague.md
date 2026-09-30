# Skill graph — `BowlingLeague` (2 skills)

**Skill `bowler_venue_qualifying_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `BowlerID`, `TourneyLocation` |
| output columns | `bowler_id`, `venue`, `qualifying_win_count` |
| source tables | `Bowler_Scores`, `Tourney_Matches`, `Tournaments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_counts qualifying wins per bowler per venue_

```sql
SELECT bs.BowlerID AS bowler_id, t.TourneyLocation AS venue, COUNT(*) AS qualifying_win_count
FROM Bowler_Scores bs
JOIN Tourney_Matches tm ON bs.MatchID = tm.MatchID
JOIN Tournaments t ON tm.TourneyID = t.TourneyID
WHERE bs.WonGame = 1
GROUP BY bs.BowlerID, t.TourneyLocation
```

---

**Skill `qualifying_game_records`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `bowler_id`, `match_number`, `game_number` |
| output columns | `bowler_id`, `bowler_first_name`, `bowler_last_name`, `match_number`, `game_number`, `handicap_score`, `tournament_date`, `location` |
| source tables | `Bowlers`, `Bowler_Scores`, `Match_Games`, `Tourney_Matches`, `Tournaments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_joins qualifying bowlers back to detailed game records, filtering for specific venues and win conditions_

```sql
SELECT 
    B.BowlerID AS bowler_id,
    B.BowlerFirstName AS bowler_first_name,
    B.BowlerLastName AS bowler_last_name,
    TM.MatchID AS match_number,
    MG.GameNumber AS game_number,
    BS.HandiCapScore AS handicap_score,
    T.TourneyDate AS tournament_date,
    T.TourneyLocation AS location
FROM Bowlers B
JOIN Bowler_Scores BS ON B.BowlerID = BS.BowlerID
JOIN Match_Games MG ON BS.MatchID = MG.MatchID
JOIN Tourney_Matches TM ON MG.MatchID = TM.MatchID
JOIN Tournaments T ON TM.TourneyID = T.TourneyID
```

---
