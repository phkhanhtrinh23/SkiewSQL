# Skill graph — `european_football_2` (12 skills)

## Skill `player_heights`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_api_id`, `player_name`, `height` |
| output columns | `player_api_id`, `player_name`, `height` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `league_goals_2015_2016` |

### Description

Selects player height and player name.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
    p.player_api_id,
    p.player_name,
    p.height
FROM
    Player AS p
```

---

## Skill `league_goals_2015_2016`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `name` |
| output columns | `league_name`, `total_goals` |
| source tables | `Match`, `League` |
| depends_on (builds on) | `player_heights` |
| depended-on by (builds on this) | `match_league_goals` |

### Description

Calculate total goals scored by each league in the 2015/2016 season.

### Semantic filters

```json
{
  "column": "season"
}
```

### Learned skill parameters

```json
{}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
    l.name AS league_name,
    SUM(m.goal) AS total_goals
FROM
    Match m
JOIN
    League l ON m.league_id = l.id
WHERE
    STRFTIME('%Y', m.date) = '2015' AND STRFTIME('%Y', m.date) = '2016'
GROUP BY
    l.name
```

---

## Skill `match_league_goals`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `name` |
| output columns | `league_name`, `home_team_goals`, `away_team_goals` |
| source tables | `Match`, `League` |
| depends_on (builds on) | `league_goals_2015_2016` |
| depended-on by (builds on this) | — |

### Description

Aggregate goals scored by each league in each match.

### Semantic filters

```json
{
  "season": "2015/2016"
}
```

### Learned skill parameters

```json
{}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

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

## Skill `away_wins`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `team_api_id` |
| output columns | `away_team`, `win_count` |
| source tables | `Match`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Aggregates wins for away teams based on the match data.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  T2.team_api_id AS `away_team`,
  COUNT(T1.id) AS `win_count`
FROM "Match" AS T1
JOIN "Team" AS T2
  ON T1.away_team_api_id = T2.team_api_id
WHERE
  T1.home_team_goal < T1.away_team_goal
GROUP BY
  T2.team_api_id
```

---

## Skill `team_buildUpPlaySpeed`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `team_name` |
| output columns | `buildUpPlaySpeed` |
| source tables | — |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Selects the buildUpPlaySpeed for each team.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  t.buildUpPlaySpeed
FROM Team_Attributes AS t
```

---

## Skill `top_4_teams_buildUpPlaySpeed`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `buildUpPlaySpeed` |
| output columns | `buildUpPlaySpeed` |
| source tables | `Team_Attributes`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Selects the buildUpPlaySpeed of the top 4 teams based on their ranked buildUpPlaySpeed.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT T2.buildUpPlaySpeed AS buildUpPlaySpeed
FROM Team_Attributes AS T2
INNER JOIN Team AS T1 ON T1.team_api_id = T2.team_api_id
ORDER BY T2.buildUpPlaySpeed DESC
LIMIT 4
```

---

## Skill `player_age`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `player_api_id` |
| output columns | `player_id`, `current_age` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Calculate the current age of each player.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  p.player_api_id AS player_id,
  STRFTIME('%Y', '2024-05-03') - STRFTIME('%Y', p.birthday) AS current_age
FROM "Player" AS p
```

---

## Skill `player_heights_7`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `player_id`, `height` |
| output columns | `player_id`, `height` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Projects the height of players.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  p.id AS player_id,
  p.height AS height
FROM Player AS p
```

---

## Skill `filter_buildUpPlaySpeed`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `team_fifa_api_id` |
| output columns | `team_fifa_api_id` |
| source tables | `Team_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Select teams where buildUpPlaySpeed falls between 51 and 59 inclusive.

### Semantic filters

```json
{
  "column": "buildUpPlaySpeed",
  "operator": "BETWEEN",
  "values": "[51, 59]"
}
```

### Learned skill parameters

```json
{}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT T1.team_fifa_api_id
FROM Team_Attributes AS T1
WHERE T1.buildUpPlaySpeed BETWEEN 51 AND 59
```

---

## Skill `league_goals_per_season`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `name` |
| output columns | `league_name`, `total_goals` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Calculate the total goals scored by each league across all seasons.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
    l.name AS league_name,
    SUM(m.home_team_goal + m.away_team_goal) AS total_goals
FROM "Match" AS m
JOIN League AS l ON m.league_id = l.id
GROUP BY l.name
```

---

## Skill `player_events`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `event_id`, `event_type`, `event_value`, `player_name` |
| output columns | `event_id`, `event_type`, `event_value`, `player_name` |
| source tables | `Match`, `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Select events for a specific player.

### Semantic filters

```json
{
  "column": "player_name",
  "value": "Ahmed Samir Farag",
  "player_name": "Ahmed Samir Farag"
}
```

### Learned skill parameters

```json
{}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
    m.id AS event_id,
    'event' AS event_type,
    1 AS event_value,
    p.player_name AS player_name
FROM
    Match AS m
JOIN
    Player AS p ON m.away_player_11 = p.player_api_id
WHERE
    p.player_name = 'Ahmed Samir Farag'
```

---

## Skill `average_long_shot`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `average_event_value` |
| output columns | `average_event_value` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Calculate the average value of long-shot events.

### Semantic filters

```json
{
  "column": "B365H",
  "goal": "1"
}
```

### Learned skill parameters

```json
{}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  AVG(
    Match."B365H"
  ) AS "average_event_value"
FROM Match
WHERE
  Match."goal" = '1'
  AND Match."shoton" != '0'
LIMIT 1000
```

---
