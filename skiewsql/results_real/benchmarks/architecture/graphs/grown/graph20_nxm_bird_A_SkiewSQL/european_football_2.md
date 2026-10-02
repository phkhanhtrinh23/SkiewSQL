# Skill graph — `european_football_2` (17 skills)

**Skill `player_ratings`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id`, `player_fifa_api_id` |
| output columns | `player_id`, `overall_rating` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `player_heights` |
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
| depended-on by (builds on this) | — |
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

**Skill `league_goals_2015_2016`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `name` |
| output columns | `league_name`, `total_goals` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `match_league_goals` |
| validated_on | — |
| counter_examples | 0 |

_Calculate total goals scored by each league in the 2015/2016 season._

```sql
SELECT
    l.name AS league_name,
    SUM(m.goal) AS total_goals
FROM
    Match AS m
JOIN
    League AS l ON m.league_id = l.id
WHERE
    STRFTIME('%Y', m.date) = '2015' AND STRFTIME('%Y', m.date) = '2015'
GROUP BY
    l.name
```

---

**Skill `match_league_goals`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `name` |
| output columns | `league_name`, `home_team_goals`, `away_team_goals` |
| source tables | `Match`, `League` |
| depends_on (builds on) | `league_goals_2015_2016` |
| depended-on by (builds on this) | — |
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
| grain (one row per) | `match_api_id` |
| output columns | `match_api_id`, `home_team`, `away_team`, `home_team_goal`, `away_team_goal`, `season` |
| source tables | `Match`, `Team`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `goal_difference` |
| validated_on | — |
| counter_examples | 0 |

_Selects all game events for the specified season._

```sql
SELECT
    m."match_api_id" AS match_api_id,
    t1."team_api_id" AS home_team,
    t2."team_api_id" AS away_team,
    m."home_team_goal" AS home_team_goal,
    m."away_team_goal" AS away_team_goal,
    m."season" AS season
FROM
    Match AS m
JOIN
    Team AS t1 ON m."away_team_api_id" = t1."team_api_id"
JOIN
    Team AS t2 ON m."home_team_api_id" = t2."team_api_id"
WHERE
    m."season" = '2015/2016'
```

---

**Skill `goal_difference`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `game_id` |
| output columns | `game_id`, `goal_difference` |
| source tables | `Match` |
| depends_on (builds on) | `game_events` |
| depended-on by (builds on this) | `losses_by_team` |
| validated_on | — |
| counter_examples | 0 |

_Calculates the goal difference for each game._

```sql
SELECT
    m.id AS game_id,
    (m.home_team_goal - m.away_team_goal) AS goal_difference
FROM
    Match AS m
```

---

**Skill `losses_by_team`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `team_short_name` |
| output columns | `team_name`, `loss_count` |
| source tables | `Team`, `Match`, `Goal_difference` |
| depends_on (builds on) | `goal_difference` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Counts the number of losses (negative goal difference) for each team._

```sql
SELECT
    t.team_short_name AS team_name,
    COUNT(CASE WHEN g.goal_difference < 0 THEN 1 ELSE NULL END) AS loss_count
FROM Team AS t
JOIN Match AS m
    ON t.team_api_id = m.home_team_api_id OR t.team_api_id = m.away_team_api_id
JOIN Goal_difference AS g
    ON m.id = g.game_id
GROUP BY t.team_short_name
```

---

**Skill `player_penalties`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_name` |
| output columns | `player_name`, `penalty_count` |
| source tables | `Player`, `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregates penalty counts for each player._

```sql
SELECT
  p.player_name,
  COUNT(CASE WHEN m.goal = '1' THEN 1 ELSE NULL END) AS penalty_count
FROM Player AS p
JOIN Match AS m
  ON p.player_api_id = m.home_player_X1
GROUP BY
  p.player_name
```

---

**Skill `team_buildUpPlaySpeed`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `team_api_id` |
| output columns | `buildUpPlaySpeed` |
| source tables | `team_attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Selects the buildUpPlaySpeed for each team._

```sql
SELECT
  tba.buildUpPlaySpeed
FROM team_attributes AS tba
```

---

**Skill `league_match_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id` |
| output columns | `league_id`, `match_count` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `aggregate_match_counts` |
| validated_on | — |
| counter_examples | 0 |

_Calculate the number of matches played for each league._

```sql
SELECT league_id, count(*) AS match_count
FROM "Match"
GROUP BY league_id
```

---

**Skill `aggregate_match_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id` |
| output columns | `league_id`, `match_count` |
| source tables | `Match` |
| depends_on (builds on) | `league_match_counts` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Determine the league with the maximum match count._

```sql
SELECT
  T1.league_id,
  COUNT(*) AS match_count
FROM Match AS T1
GROUP BY
  T1.league_id
ORDER BY
  match_count DESC
LIMIT 1
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
  AVG(CAST(Player.height AS REAL)) AS average_height
FROM Player
```

---

**Skill `filter_buildUpPlaySpeed`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `team_fifa_api_id` |
| output columns | `team_fifa_api_id` |
| source tables | `Team_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select teams where buildUpPlaySpeed falls between 51 and 59 inclusive._

```sql
SELECT t.team_fifa_api_id
FROM Team_Attributes AS t
WHERE t.buildUpPlaySpeed BETWEEN 51 AND 59
```

---

**Skill `players_filtered`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id`, `preferred_foot`, `birthday` |
| output columns | `player_id`, `preferred_foot`, `birthday` |
| source tables | `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Filters players based on preferred_foot and birthday._

```sql
SELECT
  p.id AS player_id,
  p.preferred_foot,
  p.date AS birthday
FROM Player_Attributes AS p
WHERE
  p.preferred_foot = 'left' AND p.date BETWEEN '1987-01-01' AND '1992-12-31'
```

---

**Skill `league_goals_per_season`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `name` |
| output columns | `league_name`, `total_goals` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculate the total goals scored by each league across all seasons._

```sql
SELECT
    l.name AS league_name,
    SUM(m.home_team_goal + m.away_team_goal) AS total_goals
FROM
    Match m
JOIN
    League l ON m.league_id = l.id
GROUP BY
    l.name
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
  SUM(m.goal) AS total_goals
FROM Match AS m
JOIN League AS l
  ON m.league_id = l.id
GROUP BY
  l.name
ORDER BY
  total_goals DESC
LIMIT 5
```

---

**Skill `average_long_shot`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `average_event_value` |
| output columns | `average_event_value` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculate the average value of long-shot events._

```sql
SELECT
  AVG(
    Match."shoton"
  ) AS "average_event_value"
FROM Match
WHERE
  Match."shoton" IS NOT NULL
```

---
