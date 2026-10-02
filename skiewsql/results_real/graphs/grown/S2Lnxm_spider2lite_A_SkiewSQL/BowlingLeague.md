# Skill graph — `BowlingLeague` (3 skills)

**Skill `bowling_game_records`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `bowler_id`, `match_number`, `game_number` |
| output columns | `bowler_id`, `bowler_first_name`, `bowler_last_name`, `match_number`, `game_number`, `handicap_score`, `tournament_date`, `location`, `game_result` |
| source tables | `Bowler_Scores`, `Bowlers`, `Tourney_Matches`, `Tournaments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `winning_games_at_three_venues` |
| validated_on | — |
| counter_examples | 1 |

_All game-level records for bowlers with relevant identifying and match fields (bowler id, first/last name, match number, game number, handicap score, tournament date, location, and game result). This is the base cohort from which wins, locations, and handicap filters will be applied._

```sql
SELECT
  Bowler_Scores.BowlerID AS bowler_id,
  Bowlers.BowlerFirstName AS bowler_first_name,
  Bowlers.BowlerLastName AS bowler_last_name,
  Bowler_Scores.MatchID AS match_number,
  Bowler_Scores.GameNumber AS game_number,
  Bowler_Scores.HandiCapScore AS handicap_score,
  Tournaments.TourneyDate AS tournament_date,
  Tournaments.TourneyLocation AS location,
  Bowler_Scores.WonGame AS game_result
FROM Bowler_Scores
JOIN Bowlers ON Bowler_Scores.BowlerID = Bowlers.BowlerID
LEFT JOIN Tourney_Matches ON Bowler_Scores.MatchID = Tourney_Matches.MatchID
LEFT JOIN Tournaments ON Tourney_Matches.TourneyID = Tournaments.TourneyID
```

---

**Skill `winning_games_at_three_venues`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `bowler_id`, `match_number`, `game_number` |
| output columns | `bowler_id`, `bowler_first_name`, `bowler_last_name`, `match_number`, `game_number`, `handicap_score`, `tournament_date`, `location` |
| source tables | `bowling_game_records` |
| depends_on (builds on) | `bowling_game_records` |
| depended-on by (builds on this) | `bowlers_with_all_three_venues` |
| validated_on | — |
| counter_examples | 0 |

_Subset of winning_games further restricted to only rows whose location is one of the three target venues (Thunderbird Lanes, Totem Lanes, Bolero Lanes). Each row remains a single winning-game record at one of those venues._

```sql
SELECT
  bgr.bowler_id AS bowler_id,
  bgr.bowler_first_name AS bowler_first_name,
  bgr.bowler_last_name AS bowler_last_name,
  bgr.match_number AS match_number,
  bgr.game_number AS game_number,
  bgr.handicap_score AS handicap_score,
  bgr.tournament_date AS tournament_date,
  bgr.location AS location
FROM bowling_game_records bgr
WHERE bgr.game_result = 'W'
  AND bgr.location IN ('Thunderbird Lanes', 'Totem Lanes', 'Bolero Lanes')
```

---

**Skill `bowlers_with_all_three_venues`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `bowler_id` |
| output columns | `bowler_id`, `qualifying_venue_count` |
| source tables | `winning_games_at_three_venues` |
| depends_on (builds on) | `winning_games_at_three_venues` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Identify bowlers who have at least one qualifying winning game (handicap <=190) at each of the three specific venues by counting distinct qualifying venues per bowler from winning_games_at_three_venues. This produces the set of bowlers eligible for final output._

```sql
SELECT
  w.bowler_id AS bowler_id,
  COUNT(DISTINCT w.location) AS qualifying_venue_count
FROM
  winning_games_at_three_venues AS w
GROUP BY
  w.bowler_id
```

---
