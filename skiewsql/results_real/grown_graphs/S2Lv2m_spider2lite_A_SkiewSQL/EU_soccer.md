# Skill graph — `EU_soccer` (5 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Team`, `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute the median value of each team's 'highest season goals' across all teams.
Required outputs: median_highest_season_goals — a single numeric value representing the median of the highest sea_

```sql
SELECT
  Team.team_api_id,
  Team.team_fifa_api_id,
  Team.team_long_name,
  Team.team_short_name,
  Match.season,
  Match.home_team_goal,
  Match.away_team_goal,
  -- compute total goals for this team in this match depending on home/away
  CASE
    WHEN Match.home_team_api_id = Team.team_api_id THEN Match.home_team_goal
    WHEN Match.away_team_api_id = Team.team_api_id THEN Match.away_team_goal
    ELSE NULL
  END AS goals_in_match
FROM Team
LEFT JOIN "Match" ON (Match.home_team_api_id = Team.team_api_id OR Match.away_team_api_id = Team.team_api_id)
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Match`, `League`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each league, across all seasons, find the single team that has the fewest total match wins when wins are determined by comparing home and away goals for each match (home goals > away goals m_

```sql
SELECT
  League.id AS league_id,
  Team.team_api_id AS team_api_id,
  Match.id AS match_id,
  Match.home_team_api_id AS home_team_api_id,
  Match.away_team_api_id AS away_team_api_id,
  Match.home_team_goal AS home_team_goal,
  Match.away_team_goal AS away_team_goal
FROM Match
JOIN League ON Match.league_id = League.id
JOIN Team ON (Team.team_api_id = Match.home_team_api_id OR Team.team_api_id = Match.away_team_api_id)
```

---

**Skill `chunk_view_0_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Team`, `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Return the top 10 teams across the entire league ranked by total number of wins, showing each team and its total wins.
Required outputs: team identifier (team name or id as represented in the sc_

```sql
SELECT
  Team.id AS team_id,
  Team.team_api_id,
  Team.team_long_name,
  Match.id AS match_id,
  Match.home_team_api_id,
  Match.away_team_api_id,
  Match.home_team_goal,
  Match.away_team_goal
FROM Team
LEFT JOIN Match
  ON Team.team_api_id IN (Match.home_team_api_id, Match.away_team_api_id)
```

---

**Skill `chunk_view_0_3`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Player`, `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each player, count how many matches they participated in that their team won and how many matches they participated in that their team lost; then report the player with the maximum count of _

```sql
SELECT
  p.player_api_id,
  p.player_name,
  m.id AS match_id,
  m.match_api_id,
  m.date AS match_date,
  m.home_team_api_id,
  m.away_team_api_id,
  m.home_team_goal,
  m.away_team_goal,
  -- participation: any of the home_player_* or away_player_* columns that equals this player's player_api_id
  m.home_player_1, m.home_player_2, m.home_player_3, m.home_player_4, m.home_player_5,
  m.home_player_6, m.home_player_7, m.home_player_8, m.home_player_9, m.home_player_10, m.home_player_11,
  m.away_player_1, m.away_player_2, m.away_player_3, m.away_player_4, m.away_player_5,
  m.away_player_6, m.away_player_7, m.away_player_8, m.away_player_9, m.away_player_10, m.away_player_11
FROM
  Player p
JOIN
  Match m
-- join condition will allow later logic to determine whether p participated in m by matching p.player_api_id to any home/away player column
ON
  (
    m.home_player_1 = p.player_api_id OR m.home_player_2 = p.player_api_id OR m.home_player_3 = p.player_api_id OR
    m.home_player_4 = p.player_api_id OR m.home_player_5 = p.player_api_id OR m.home_player_6 = p.player_api_id OR
    m.home_player_7 = p.player_api_id OR m.home_player_8 = p.player_api_id OR m.home_player_9 = p.player_api_id OR
    m.home_player_10 = p.player_api_id OR m.home_player_11 = p.player_api_id OR
    m.away_player_1 = p.player_api_id OR m.away_player_2 = p.player_api_id OR m.away_player_3 = p.player_api_id OR
    m.away_player_4 = p.player_api_id OR m.away_player_5 = p.player_api_id OR m.away_player_6 = p.player_api_id OR
    m.away_player_7 = p.player_api_id OR m.away_player_8 = p.player_api_id OR m.away_player_9 = p.player_api_id OR
    m.away_player_10 = p.player_api_id OR m.away_player_11 = p.player_api_id
  )
```

---

**Skill `chunk_view_0_4`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Match`, `Team`, `League`, `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each combination of country, league, and season present in the dataset, compute each team's total points using 3 points per win, 1 point per tie, and 0 points per loss, and return the team w_

```sql
SELECT
  Match.country_id,
  Match.league_id,
  Match.season,
  Match.match_api_id,
  Match.date,
  Match.home_team_api_id,
  Match.away_team_api_id,
  Match.home_team_goal,
  Match.away_team_goal,
  Match.home_player_1,
  Match.home_player_2,
  Match.home_player_3,
  Match.home_player_4,
  Match.home_player_5,
  Match.home_player_6,
  Match.home_player_7,
  Match.home_player_8,
  Match.home_player_9,
  Match.home_player_10,
  Match.home_player_11,
  Match.away_player_1,
  Match.away_player_2,
  Match.away_player_3,
  Match.away_player_4,
  Match.away_player_5,
  Match.away_player_6,
  Match.away_player_7,
  Match.away_player_8,
  Match.away_player_9,
  Match.away_player_10,
  Match.away_player_11,
  Team.team_api_id AS team_api_id,
  Team.team_long_name,
  Team.team_short_name,
  League.name AS league_name,
  League.country_id AS league_country_id,
  Player.player_api_id,
  Player.player_name,
  Player.player_fifa_api_id
FROM
  "Match"
LEFT JOIN "Team" ON Team.team_api_id IN (Match.home_team_api_id, Match.away_team_api_id)
LEFT JOIN "League" ON League.id = Match.league_id
LEFT JOIN "Player" ON Player.player_api_id IN (
  Match.home_player_1, Match.home_player_2, Match.home_player_3, Match.home_player_4, Match.home_player_5,
  Match.home_player_6, Match.home_player_7, Match.home_player_8, Match.home_player_9, Match.home_player_10, Match.home_player_11,
  Match.away_player_1, Match.away_player_2, Match.away_player_3, Match.away_player_4, Match.away_player_5,
  Match.away_player_6, Match.away_player_7, Match.away_player_8, Match.away_player_9, Match.away_player_10, Match.away_player_11
)
```

---
