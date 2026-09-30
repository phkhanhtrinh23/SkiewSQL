# Skill graph — `european_football_2` (14 skills)

**Skill `player_ratings`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id`, `player_fifa_api_id` |
| output columns | `player_id`, `overall_rating` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `player_heights`, `player_crossing_performance`, `team_buildUpPlaySpeed` |
| validated_on | — |
| counter_examples | 0 |

_Selects player ratings from the player table._

```sql
SELECT
  p.id AS player_id,
  p.player_fifa_api_id AS overall_rating
FROM Player AS p
```

---

**Skill `player_heights`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id`, `height`, `player_name` |
| output columns | `height`, `player_name` |
| source tables | `Player` |
| depends_on (builds on) | `player_ratings` |
| depended-on by (builds on this) | `team_buildUpPlaySpeed` |
| validated_on | — |
| counter_examples | 0 |

_Selects player height and player name._

```sql
SELECT
  p.height,
  p.player_name
FROM Player AS p
```

---

**Skill `player_crossing_performance`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id`, `crossing` |
| output columns | `player_id` |
| source tables | `player_ratings`, `player_attributes` |
| depends_on (builds on) | `player_ratings` |
| depended-on by (builds on this) | `team_buildUpPlaySpeed` |
| validated_on | — |
| counter_examples | 0 |

_Selects players based on their crossing action performance._

```sql
SELECT
  T1.player_id
FROM player_ratings AS T1
JOIN player_attributes AS T2
  ON T1.player_id = T2.player_api_id
WHERE
  T2.crossing > 0
```

---

**Skill `league_goals_2015_2016`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `name` |
| output columns | `league_name`, `total_goals` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `match_league_goals`, `team_buildUpPlaySpeed`, `league_goals_per_season` |
| validated_on | — |
| counter_examples | 0 |

_Calculate total goals scored by each league in the 2015/2016 season._

```sql
SELECT
    l.name AS league_name,
    SUM(m.home_team_goal + m.away_team_goal) AS total_goals
FROM Match AS m
JOIN League AS l ON m.league_id = l.id
WHERE l.name = 'England Premier League'
AND strftime('%Y', m.date) = '2015'
GROUP BY l.name
```

---

**Skill `match_league_goals`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `name` |
| output columns | `league_name`, `home_team_goals`, `away_team_goals` |
| source tables | `Match`, `League` |
| depends_on (builds on) | `league_goals_2015_2016` |
| depended-on by (builds on this) | `team_buildUpPlaySpeed` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate goals scored by each league in each match._

```sql
SELECT
    l.name AS league_name,
    SUM(m.home_team_goal) AS home_team_goals,
    SUM(m.away_team_goal) AS away_team_goals
FROM Match AS m
JOIN League AS l
    ON m.league_id = l.id
WHERE m.season = '2015/2016'
GROUP BY l.name
```

---

**Skill `game_events`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `game_id` |
| output columns | `game_id`, `season`, `home_team`, `away_team`, `home_team_goal`, `away_team_goal` |
| source tables | `Match`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `goal_difference`, `team_buildUpPlaySpeed` |
| validated_on | — |
| counter_examples | 0 |

_Selects all game events for the specified season._

```sql
SELECT
  m.id AS game_id,
  m.season AS season,
  t1.team_short_name AS home_team,
  t2.team_short_name AS away_team,
  m.home_team_goal AS home_team_goal,
  m.away_team_goal AS away_team_goal
FROM "Match" AS m
JOIN Team AS t1
  ON m.home_team_api_id = t1.team_api_id
JOIN Team AS t2
  ON m.away_team_api_id = t2.team_api_id
WHERE
  m.season = '2015/2016'
```

---

**Skill `goal_difference`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `game_id` |
| output columns | `game_id`, `goal_difference` |
| source tables | `game_events` |
| depends_on (builds on) | `game_events` |
| depended-on by (builds on this) | `team_buildUpPlaySpeed` |
| validated_on | — |
| counter_examples | 0 |

_Calculates the goal difference for each game._

```sql
SELECT
  e.game_id AS game_id,
  e.home_team_goal - e.away_team_goal AS goal_difference
FROM game_events AS e
```

---

**Skill `team_buildUpPlaySpeed`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `team_name` |
| output columns | `buildUpPlaySpeed` |
| source tables | `Team_Attributes`, `Team` |
| depends_on (builds on) | `player_ratings`, `player_heights`, `player_crossing_performance`, `league_goals_2015_2016`, `match_league_goals`, `game_events`, `goal_difference` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Selects the buildUpPlaySpeed for each team._

```sql
SELECT
  t.buildUpPlaySpeed AS buildUpPlaySpeed
FROM Team_Attributes AS t
JOIN Team AS t2
  ON t2.team_api_id = t.team_api_id
```

---

**Skill `top_4_teams_buildUpPlaySpeed`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `buildUpPlaySpeed` |
| output columns | `buildUpPlaySpeed` |
| source tables | `Team`, `Team_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Selects the buildUpPlaySpeed of the top 4 teams based on their ranked buildUpPlaySpeed._

```sql
SELECT
  T2.buildUpPlaySpeed AS buildUpPlaySpeed
FROM Team AS T1
JOIN Team_Attributes AS T2
  ON T1.team_api_id = T2.team_api_id
ORDER BY T2.buildUpPlaySpeed DESC
LIMIT 4
```

---

**Skill `league_match_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id` |
| output columns | `league_id`, `match_count` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculate the number of matches played for each league._

```sql
SELECT league_id, COUNT(*) AS match_count
FROM Match
GROUP BY league_id
```

---

**Skill `average_height`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `average_height` |
| output columns | `average_height` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculates the average height of the filtered players._

```sql
SELECT
  CAST(AVG(P.height) AS REAL) AS average_height
FROM Player AS P
```

---

**Skill `team_stats_2012`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `team_long_name` |
| output columns | `team_long_name`, `buildUpPlayPassing`, `total_buildUpPlayPassing` |
| source tables | `Team`, `Team_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculate team statistics for the year 2012._

```sql
SELECT
  T1.team_long_name AS team_long_name,
  T2.buildUpPlayPassing AS buildUpPlayPassing,
  SUM(T2.buildUpPlayPassing) AS total_buildUpPlayPassing
FROM Team AS T1
JOIN Team_Attributes AS T2
  ON T1.team_api_id = T2.team_api_id
WHERE strftime('%Y', T2.date) = '2012'
GROUP BY T1.team_long_name
```

---

**Skill `league_goals_per_season`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `name` |
| output columns | `league_name`, `total_goals` |
| source tables | `Match`, `League` |
| depends_on (builds on) | `league_goals_2015_2016` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculate the total goals scored by each league across all seasons._

```sql
SELECT
    l.name AS league_name,
    SUM(m.home_team_goal + m.away_team_goal) AS total_goals
FROM "Match" AS m
JOIN League AS l ON m.league_id = l.id
GROUP BY l.name
```

---

**Skill `top_leagues_by_goals`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `name` |
| output columns | `league_name`, `total_goals` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Rank leagues by total goals scored, returning the top 5._

```sql
SELECT
    l.name AS league_name,
    SUM(m.home_team_goal + m.away_team_goal) AS total_goals
FROM Match AS m
JOIN League AS l ON m.league_id = l.id
GROUP BY l.name
ORDER BY total_goals DESC
LIMIT 5
```

---
