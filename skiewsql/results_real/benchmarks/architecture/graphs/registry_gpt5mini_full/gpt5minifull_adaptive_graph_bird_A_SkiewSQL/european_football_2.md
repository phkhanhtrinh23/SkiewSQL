# Skill graph — `european_football_2` (24 skills)

## Skill `player_max_overall_rating`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | — (scalar) |
| status / version | active / v1 |
| skill id | sk_ff56dbf00f027003 |
| output columns | `max_overall_rating` |
| source tables | `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each dataset, the maximum overall_rating value across all players (can be joined back to players to find those with that rating).

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [],
    "contract_version": 2,
    "grain_basis": "scalar_aggregate",
    "lineage": [
      "Player_Attributes"
    ],
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1020",
    "question": "Which player has the highest overall rating? Indicate the player's api id.",
    "rewrite": "Task: Find the player (api id) whose overall_rating equals the maximum overall_rating value in the dataset.\nRequired outputs: api id of the player whose overall_rating is MAX(overall_rating)\nFilters: overall_rating = MAX(overall_rating)",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:00:58+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:01:01+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "max_overall_rating"
    ],
    "row_count": 1,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View returns exactly one row (scalar) — detect if view returns 0 or more than 1 rows",
        "sql": "SELECT ABS((SELECT COUNT(*) FROM player_max_overall_rating) - 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "max_overall_rating is equal to the MAX(overall_rating) computed from the base table (measure reconciliation)",
        "sql": "SELECT CASE WHEN (SELECT max_overall_rating FROM player_max_overall_rating) IS (SELECT MAX(overall_rating) FROM Player_Attributes) THEN 0 ELSE 1 END",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "max_overall_rating is not NULL (since MAX over any non-empty numeric column should be NULL only if there are no rows or all NULLs)",
        "sql": "SELECT CASE WHEN (SELECT max_overall_rating FROM player_max_overall_rating) IS NULL THEN 1 ELSE 0 END",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT MAX(overall_rating) AS max_overall_rating
FROM Player_Attributes
```

---

## Skill `league_match_goal_totals_by_season`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `league_name`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_f5a1e1b0ea543b12 |
| output columns | `league_id`, `league_name`, `season`, `total_goals` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-league total goals per season computed as the sum of home and away goals across all matches in that league and season (one row per league-season).

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [
      "'2015/2016'"
    ],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Match",
      "League"
    ],
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3",
      "league": "72cd1678e1e9160e"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1025",
    "question": "Which league had the most goals in the 2016 season?",
    "rewrite": "Task: Find the league (competition) whose matches in the 2015/2016 season had the highest total number of goals, where total goals for a league equals the sum over all its matches of (home_team_goal + away_team_goal).\nRequired outputs: league (identifier/name of the competition); total_goals (numeric sum of home_team_goal + away_team_goal across all matches in that league for the specified season)\nFilters: season = '2015/2016'; only include matches from that season; aggregate matches by league/competition before comparing totals\nSort/limit: order by total_goals desc limit 1",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:01:34+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:01:37+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "league_id",
      "league_name",
      "season",
      "total_goals"
    ],
    "row_count": 88,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Match.league_id=League.id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "View has one row per league-season (no duplicate league_id, league_name, season)",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, league_name, season, COUNT(*) AS c FROM league_match_goal_totals_by_season GROUP BY league_id, league_name, season HAVING c > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "total_goals equals sum of home_team_goal + away_team_goal from Match for that league and season",
        "sql": "SELECT COUNT(*) FROM league_match_goal_totals_by_season v LEFT JOIN (SELECT M.league_id AS league_id, L.name AS league_name, M.season AS season, SUM(M.home_team_goal + M.away_team_goal) AS expected_total FROM Match M JOIN League L ON M.league_id = L.id GROUP BY M.league_id, L.name, M.season) s ON v.league_id = s.league_id AND v.league_name = s.league_name AND v.season = s.season WHERE (s.expected_total IS NULL AND (v.total_goals IS NOT NULL)) OR (s.expected_total IS NOT NULL AND v.total_goals IS NULL) OR (s.expected_total IS NOT NULL AND v.total_goals <> s.expected_total)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys league_id, league_name, season are NOT NULL",
        "sql": "SELECT COUNT(*) FROM league_match_goal_totals_by_season WHERE league_id IS NULL OR league_name IS NULL OR season IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT L.id AS league_id, L.name AS league_name, M.season AS season, SUM(M.home_team_goal + M.away_team_goal) AS total_goals
FROM Match M
JOIN League L ON M.league_id = L.id
GROUP BY L.id, L.name, M.season
```

---

## Skill `home_match_loss_counts_by_team_and_season`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `season`, `team_api_id`, `team_long_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_c55b38a95c77efdc |
| output columns | `season`, `team_api_id`, `team_long_name`, `home_losses` |
| source tables | `Match`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-team counts of home-match losses (matches where home_team_goal - away_team_goal < 0) for each season, keyed by team identifier and season

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [
      "'2015/2016'"
    ],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Match",
      "Team"
    ],
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3",
      "team": "a19728cad815ec8a"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1026",
    "question": "Which home team had lost the fewest matches in the 2016 season?",
    "rewrite": "Task: Find the home team (team name) that had the fewest number of home match losses during the 2015/2016 season, where a home match loss is defined as matches in that season with (home_team_goal - away_team_goal) < 0.\nRequired outputs: home_team (the name or identifier of the team that played at home); home_losses (the integer count of matches in the 2015/2016 season where home_team_goal - away_team_goal < 0 for that home_team)\nFilters: season = '2015/2016'; consider only matches where (home_team_goal - away_team_goal) < 0 when counting losses; group counts by home_team\nSort/limit: order results by home_losses ascending and return the top 1 (the home_team with the minimum home_losses); if multiple teams tie, return all tied teams (no further tie-breaker)",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:01:46+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:01:49+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "season",
      "team_api_id",
      "team_long_name",
      "home_losses"
    ],
    "row_count": 1434,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Match.home_team_api_id=Team.team_api_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "Each row's home_losses equals the count of Match rows in that season where that team was the home team and lost (home_team_goal - away_team_goal < 0). Detects aggregation or join errors.",
        "sql": "SELECT COUNT(*) FROM (SELECT v.season AS season, v.team_api_id AS team_api_id, v.home_losses AS reported, COALESCE(calculated.cnt,0) AS expected FROM home_match_loss_counts_by_team_and_season v LEFT JOIN (SELECT m.season AS season, m.home_team_api_id AS team_api_id, COUNT(m.id) AS cnt FROM \"Match\" m WHERE (m.home_team_goal - m.away_team_goal) < 0 GROUP BY m.season, m.home_team_api_id) calculated ON calculated.season = v.season AND calculated.team_api_id = v.team_api_id WHERE reported != expected) as _violations",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No NULLs in key columns (season, team_api_id, team_long_name).",
        "sql": "SELECT COUNT(*) FROM home_match_loss_counts_by_team_and_season WHERE season IS NULL OR team_api_id IS NULL OR team_long_name IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View contains no duplicate keys (season, team_api_id, team_long_name) — ensures grain is respected.",
        "sql": "SELECT COUNT(*) FROM (SELECT season, team_api_id, team_long_name, COUNT(*) AS cnt FROM home_match_loss_counts_by_team_and_season GROUP BY season, team_api_id, team_long_name HAVING cnt > 1) as dup",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT m.season, t.team_api_id AS team_api_id, t.team_long_name AS team_long_name, COUNT(m.id) AS home_losses FROM Match m JOIN Team t ON m.home_team_api_id = t.team_api_id WHERE (m.home_team_goal - m.away_team_goal) < 0 GROUP BY m.season, t.team_api_id, t.team_long_name
```

---

## Skill `away_team_season_league_win_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `season`, `away_team_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_dec04e8252fe6752 |
| output columns | `league_id`, `season`, `away_team_api_id`, `away_wins_count` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Counts of away match wins per away_team_api_id for each league and season (one row per away team / league / season) where an away win is when away_team_goal > home_team_goal.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [
      "Scotland Premier League",
      "2009/2010"
    ],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Match"
    ],
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1028",
    "question": "In Scotland Premier League, which away team won the most during the 2010 season?",
    "rewrite": "Task: Find which away_team_api_id had the most away match wins in matches from the Scotland Premier League during the 2009/2010 season.\nRequired outputs: away_team_api_id (the ID of the away team); away_wins_count (the number of away matches that team won in that season and league)\nFilters: League.name = 'Scotland Premier League'; season = '2009/2010'; A match counts as an away win when (away_team_goal - home_team_goal) > 0\nSort/limit: order by away_wins_count DESC limit 1",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:02:02+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:02:06+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "league_id",
      "season",
      "away_team_api_id",
      "away_wins_count"
    ],
    "row_count": 1463,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "Grain uniqueness: ensure there are no duplicate rows for the declared grain (league_id, season, away_team_api_id) in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, season, away_team_api_id, COUNT(*) AS cnt FROM away_team_season_league_win_counts GROUP BY league_id, season, away_team_api_id HAVING cnt > 1) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Measure correctness: each view row's away_wins_count equals the number of Match rows for that league/season/away_team where away_team_goal > home_team_goal",
        "sql": "SELECT COUNT(*) FROM away_team_season_league_win_counts v LEFT JOIN (SELECT league_id, season, away_team_api_id, COUNT(*) AS calc_count FROM Match WHERE (away_team_goal - home_team_goal) > 0 GROUP BY league_id, season, away_team_api_id) m ON v.league_id = m.league_id AND v.season = m.season AND v.away_team_api_id = m.away_team_api_id WHERE COALESCE(m.calc_count,0) != COALESCE(v.away_wins_count,0)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Key not NULL: ensure no nulls in any of the declared key columns (league_id, season, away_team_api_id) in the view",
        "sql": "SELECT COUNT(*) FROM away_team_season_league_win_counts WHERE league_id IS NULL OR season IS NULL OR away_team_api_id IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  m.league_id,
  m.season,
  m.away_team_api_id,
  COUNT(*) AS away_wins_count
FROM Match m
WHERE (m.away_team_goal - m.home_team_goal) > 0
GROUP BY m.league_id, m.season, m.away_team_api_id
```

---

## Skill `team_max_buildup_play_speed`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `team_api_id`, `team_long_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_a1fd90be5c81b922 |
| output columns | `team_api_id`, `team_long_name`, `max_buildUpPlaySpeed` |
| source tables | `Team_Attributes`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-team maximum recorded buildUpPlaySpeed, joined to team identifier for reuse in comparisons or ranking tasks.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [
      "4",
      "ORDER BY buildUpPlaySpeed DESC",
      "LIMIT 4"
    ],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Team_Attributes",
      "Team"
    ],
    "table_fingerprints": {
      "team_attributes": "a8661cb8da0875ec",
      "team": "a19728cad815ec8a"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1029",
    "question": "What are the speed in which attacks are put together of the top 4 teams with the highest build Up Play Speed?",
    "rewrite": "Task: Find the buildUpPlaySpeed values for the top 4 teams ranked by their maximum buildUpPlaySpeed.\nRequired outputs: team_name (the team identifier/name); buildUpPlaySpeed (the speed in which attacks are put together)\nFilters: Consider each team's maximum buildUpPlaySpeed value (i.e., MAX(buildUpPlaySpeed) per team).; Return only the teams with the four highest MAX(buildUpPlaySpeed) values.\nSort/limit: Order results by buildUpPlaySpeed descending and limit to 4 rows",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:02:12+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:02:18+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "team_api_id",
      "team_long_name",
      "max_buildUpPlaySpeed"
    ],
    "row_count": 288,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Team_Attributes.team_api_id=Team.team_api_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (team_api_id, team_long_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT team_api_id, team_long_name, COUNT(*) AS cnt FROM team_max_buildup_play_speed GROUP BY team_api_id, team_long_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "max_buildUpPlaySpeed equals MAX(buildUpPlaySpeed) computed from Team_Attributes joined to Team for each team",
        "sql": "SELECT COUNT(*) FROM (SELECT v.team_api_id, v.team_long_name FROM team_max_buildup_play_speed v LEFT JOIN (SELECT t.team_api_id, t.team_long_name, MAX(ta.buildUpPlaySpeed) AS expected_max FROM Team_Attributes ta JOIN Team t ON ta.team_api_id = t.team_api_id GROUP BY t.team_api_id, t.team_long_name) e ON v.team_api_id = e.team_api_id AND v.team_long_name = e.team_long_name WHERE (v.max_buildUpPlaySpeed IS NOT e.expected_max) OR (v.max_buildUpPlaySpeed IS NULL AND e.expected_max IS NOT NULL) OR (v.max_buildUpPlaySpeed IS NOT NULL AND e.expected_max IS NULL))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL (team_api_id and team_long_name must be present)",
        "sql": "SELECT COUNT(*) FROM team_max_buildup_play_speed WHERE team_api_id IS NULL OR team_long_name IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT t.team_api_id, t.team_long_name, MAX(ta.buildUpPlaySpeed) AS max_buildUpPlaySpeed FROM Team_Attributes ta JOIN Team t ON ta.team_api_id = t.team_api_id GROUP BY t.team_api_id, t.team_long_name
```

---

## Skill `matches_per_league`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `league_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_4418731eea45375b |
| output columns | `league_id`, `league_name`, `match_count` |
| source tables | `League`, `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each league, the total number of matches played (count of matches grouped by league), keeping league id and name for joins or display.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "League",
      "Match"
    ],
    "table_fingerprints": {
      "league": "72cd1678e1e9160e",
      "match": "a56b9117c06fb4c3"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1032",
    "question": "Give the name of the league with the highest matches of all time and how many matches were played in the said league.",
    "rewrite": "Task: Find the league name that has the maximum total number of matches played across all time and report that league's name together with the total number of matches played in that league.\nRequired outputs: League.name — the name of the league that has the highest count of matches; match_count — the total number of matches played in that league (i.e., COUNT of matches where match.league_id = league.id)\nFilters: Consider all matches in the matches table (no date or other filtering unless schema requires); Aggregate matches by league_id to compute COUNT(league_id) per league; Select the league (League.name) whose COUNT(league_id) is equal to the maximum COUNT(league_id) over all leagues\nSort/limit: Order by match_count descending and limit to 1 (return a single league with the highest match count)",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:02:40+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:02:42+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "league_id",
      "league_name",
      "match_count"
    ],
    "row_count": 11,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Match.league_id=League.id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "Each row in the view has non-NULL league_id and league_name (keys must not be NULL).",
        "sql": "SELECT COUNT(*) FROM matches_per_league WHERE league_id IS NULL OR league_name IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No duplicate grain rows: there should be at most one row per (league_id, league_name).",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, league_name, COUNT(*) AS cnt FROM matches_per_league GROUP BY league_id, league_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "match_count reconciles with base tables: match_count equals the number of Match rows with that league_id (detect mismatches).",
        "sql": "SELECT COUNT(*) FROM matches_per_league v LEFT JOIN (SELECT league_id AS l_id, COUNT(id) AS expected_count FROM \"Match\" GROUP BY league_id) b ON v.league_id = b.l_id WHERE COALESCE(b.expected_count,0) != COALESCE(v.match_count,0)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT L.id AS league_id, L.name AS league_name, COUNT(M.id) AS match_count FROM League L JOIN "Match" M ON M.league_id = L.id GROUP BY L.id, L.name
```

---

## Skill `players_cohort`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `id` (keyed) |
| status / version | active / v1 |
| skill id | sk_31efe8e5190803ba |
| output columns | `id`, `height`, `birthday` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Select the set of player rows whose birthday is within the given date range (inclusive lower bound, exclusive upper bound). Keep each player row with id and height.

### Semantic filters

```json
{
  "birthday": ">=1990-01-01 00:00:00;<1996-01-01 00:00:00"
}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "subgoal",
    "subgoal": {
      "want_name": "players_cohort",
      "category": "SEL",
      "required_outputs": [
        "id",
        "height",
        "birthday"
      ],
      "required_grain": [
        "player_id"
      ],
      "required_filters": {
        "birthday": ">= '1990-01-01 00:00:00' AND < '1996-01-01 00:00:00'"
      },
      "text": "Select the set of player rows whose birthday is within the given date range (inclusive lower bound, exclusive upper bound). Keep each player row with id and height.",
      "source_tables": [],
      "depends_on": [],
      "join_keys": [],
      "relationship": "independent",
      "may_read_base_tables": true,
      "holistic": false,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "primary_key",
    "lineage": [
      "Player"
    ],
    "table_fingerprints": {
      "player": "032b398bb82740dc"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1033",
    "question": "What is the average height of players born between 1990 and 1995?",
    "rewrite": "Task: Compute the average height of players whose birthday is on or after 1990-01-01 00:00:00 and before 1996-01-01 00:00:00, using average height = DIVIDE(SUM(height), COUNT(id)).\nRequired outputs: average_height: a single numeric value equal to DIVIDE(SUM(height), COUNT(id)) for the selected players\nFilters: birthday >= '1990-01-01 00:00:00'; birthday < '1996-01-01 00:00:00'",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:03:08+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:03:10+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "id",
      "height",
      "birthday"
    ],
    "row_count": 3360,
    "grain_check": "pass",
    "filter_checks": {
      "birthday": "pass"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate ids (view grain is id). Fails if the view contains the same id more than once.",
        "sql": "SELECT COUNT(*) FROM (SELECT id, COUNT(*) AS c FROM players_cohort GROUP BY id HAVING c > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows satisfy intrinsic birthday filter (birthday >= '1990-01-01' AND birthday < '1996-01-01'). Fails if any row is outside the inclusive lower / exclusive upper bounds or has NULL birthday.",
        "sql": "SELECT COUNT(*) FROM players_cohort WHERE NOT (birthday >= '1990-01-01 00:00:00' AND birthday < '1996-01-01 00:00:00')",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each view row corresponds to an existing Player row with matching id and height (detects accidental modification of values or phantom rows). Fails if any view row has no matching base table row or mis",
        "sql": "SELECT COUNT(*) FROM players_cohort pc LEFT JOIN Player p ON pc.id = p.id WHERE p.id IS NULL OR (p.height IS NOT pc.height) OR (pc.birthday IS NOT p.birthday)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  id AS id,
  height AS height,
  birthday AS birthday
FROM Player
WHERE birthday >= '1990-01-01 00:00:00' AND birthday < '1996-01-01 00:00:00'
```

---

## Skill `league_total_goals`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `league_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_80d588fd285e85ae |
| output columns | `league_id`, `league_name`, `total_goals` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Total goals scored per league across all matches (sum of home and away goals) with league identifiers for joining.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Match",
      "League"
    ],
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3",
      "league": "72cd1678e1e9160e"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1038",
    "question": "List the top 5 leagues in ascending order of the number of goals made in all seasons combined.",
    "rewrite": "Task: Compute the total number of goals scored across all seasons for each league (where total goals = SUM(home_team_goal + away_team_goal) aggregated over all matches in all seasons), then list the top 5 leagues with the smallest totals (ascending order of total goals).\nRequired outputs: league (identifier or name of the league); total_goals (integer equal to the sum over all matches of home_team_goal + away_team_goal for that league across all seasons)\nFilters: Include all matches from all seasons (no season or date filtering).; Only include leagues that have at least one match (i.e., sum is computed over existing match records).\nSort/limit: ORDER BY total_goals ASC LIMIT 5",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:04:40+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:04:43+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "league_id",
      "league_name",
      "total_goals"
    ],
    "row_count": 11,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Match.league_id=League.id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows per grain (league_id, league_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, league_name, COUNT(*) AS cnt FROM league_total_goals GROUP BY league_id, league_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "total_goals equals sum of home_team_goal + away_team_goal from Match for that league (detect mismatches or NULLs)",
        "sql": "SELECT COUNT(*) FROM league_total_goals v LEFT JOIN (SELECT league_id AS lid, SUM(home_team_goal + away_team_goal) AS expected_total FROM Match GROUP BY league_id) m ON v.league_id = m.lid WHERE (m.expected_total IS NULL AND v.total_goals IS NOT NULL) OR (m.expected_total IS NOT NULL AND v.total_goals IS NULL) OR (m.expected_total IS NOT NULL AND v.total_goals IS NOT NULL AND v.total_goals != m.expected_total)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys league_id and league_name are not NULL",
        "sql": "SELECT COUNT(*) FROM league_total_goals WHERE league_id IS NULL OR league_name IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT League.id AS league_id, League.name AS league_name, SUM(Match.home_team_goal + Match.away_team_goal) AS total_goals FROM Match JOIN League ON Match.league_id = League.id GROUP BY League.id, League.name HAVING SUM(Match.home_team_goal + Match.away_team_goal) IS NOT NULL
```

---

## Skill `player_rows_sel`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `id` (keyed) |
| status / version | active / v1 |
| skill id | sk_ac6348a31621a17a |
| output columns | `player_name`, `player_fifa_api_id`, `long_shots`, `id`, `player_id`, `player_api_id` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Select all raw rows for the player(s) matching the player name filter. Keep the player identifier and the long_shots value for each source row.

### Semantic filters

```json
{
  "player_name": "Ahmed Samir Farag"
}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "subgoal",
    "subgoal": {
      "want_name": "player_rows_sel",
      "category": "SEL",
      "required_outputs": [
        "player_name",
        "player_fifa_api_id",
        "long_shots"
      ],
      "required_grain": [
        "row"
      ],
      "required_filters": {
        "player_name": "equals 'Ahmed Samir Farag'"
      },
      "text": "Select all raw rows for the player(s) matching the player name filter. Keep the player identifier and the long_shots value for each source row.",
      "source_tables": [],
      "depends_on": [],
      "join_keys": [],
      "relationship": "independent",
      "may_read_base_tables": true,
      "holistic": false,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "Player",
      "Player_Attributes"
    ],
    "table_fingerprints": {
      "player": "032b398bb82740dc",
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {
      "player": "11060:11075",
      "player_attributes": "183978:183978"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1039",
    "question": "Find the average number of long-shot done by Ahmed Samir Farag.",
    "rewrite": "Task: Compute the average number of long_shots for the player with name 'Ahmed Samir Farag', where average is defined as SUM(long_shots) divided by COUNT(player_fifa_api_id).\nRequired outputs: average_long_shot: numeric value equal to DIVIDE(SUM(long_shots), COUNT(player_fifa_api_id))\nFilters: player_name = 'Ahmed Samir Farag' (limit aggregation to rows for this player)",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:05:10+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:05:13+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_name",
      "player_fifa_api_id",
      "long_shots",
      "id",
      "player_id",
      "player_api_id"
    ],
    "row_count": 7,
    "grain_check": "pass",
    "filter_checks": {
      "player_name": "pass"
    },
    "join_cardinality": [
      {
        "join": "Player_Attributes.player_api_id=Player.player_api_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "Every row in the view should have player_name equal to the intrinsic filter 'Ahmed Samir Farag'.",
        "sql": "SELECT COUNT(*) FROM player_rows_sel WHERE NOT (player_name = 'Ahmed Samir Farag')",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No NULLs allowed for the view's key 'id'.",
        "sql": "SELECT COUNT(*) FROM player_rows_sel WHERE id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each row in the view must correspond to a source Player_Attributes row joined to a Player with matching player_api_id — detect view rows whose player_api_id and id combination does not exist in the ba",
        "sql": "SELECT COUNT(*) FROM player_rows_sel v LEFT JOIN Player p ON v.player_id = p.id LEFT JOIN Player_Attributes pa ON v.id = pa.id WHERE NOT (p.player_name = 'Ahmed Samir Farag' AND pa.player_api_id = p.player_api_id)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "included": 1
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  p.player_name AS player_name,
  p.player_fifa_api_id AS player_fifa_api_id,
  pa.long_shots AS long_shots,
  pa.id AS id,
  p.id AS player_id,
  pa.player_api_id AS player_api_id
FROM Player p
JOIN Player_Attributes pa
  ON pa.player_api_id = p.player_api_id
WHERE p.player_name = 'Ahmed Samir Farag'
```

---

## Skill `player_long_shot_by_player_fifa_api_id`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `player_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_02bc3157a3be39e4 |
| output columns | `player_fifa_api_id`, `player_attributes_id`, `player_api_id`, `long_shots_norm` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player_fifa_api_id normalized long_shots values (one row per Player_Attributes record) with empty-string treated as NULL and long_shots cast to integer, keeping keys to join to player and attributes.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [
      "'Ahmed Samir Farag'"
    ],
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "Player",
      "Player_Attributes"
    ],
    "table_fingerprints": {
      "player": "032b398bb82740dc",
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {
      "player": "11060:11075",
      "player_attributes": "183978:183978"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1039",
    "question": "Find the average number of long-shot done by Ahmed Samir Farag.",
    "rewrite": "Task: Compute the average number of long_shots for the player with name 'Ahmed Samir Farag', where average is defined as SUM(long_shots) divided by COUNT(player_fifa_api_id).\nRequired outputs: average_long_shot: numeric value equal to DIVIDE(SUM(long_shots), COUNT(player_fifa_api_id))\nFilters: player_name = 'Ahmed Samir Farag' (limit aggregation to rows for this player)",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:05:15+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:05:18+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_fifa_api_id",
      "player_attributes_id",
      "player_api_id",
      "long_shots_norm"
    ],
    "row_count": 183978,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Player_Attributes.player_api_id=Player.player_api_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "View has one row per Player_Attributes.id (no missing or duplicate player_attributes_id).",
        "sql": "SELECT (SELECT COUNT(*) FROM Player_Attributes) - (SELECT COUNT(DISTINCT player_attributes_id) FROM player_long_shot_by_player_fifa_api_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row corresponds to an existing Player_Attributes record and the keys are preserved (player_attributes_id matches an id and player_api_id matches that row).",
        "sql": "SELECT COUNT(*) FROM player_long_shot_by_player_fifa_api_id v LEFT JOIN Player_Attributes pa ON v.player_attributes_id = pa.id WHERE pa.id IS NULL OR (v.player_api_id IS NOT NULL AND v.player_api_id != pa.player_api_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "long_shots_norm is either NULL when source long_shots is empty/blank or equals CAST(long_shots AS INTEGER) from Player_Attributes.",
        "sql": "SELECT COUNT(*) FROM player_long_shot_by_player_fifa_api_id v JOIN Player_Attributes pa ON v.player_attributes_id = pa.id WHERE NOT ( (trim(pa.long_shots) = '' AND v.long_shots_norm IS NULL) OR (trim(pa.long_shots) != '' AND v.long_shots_norm = CAST(pa.long_shots AS INTEGER)) OR (pa.long_shots IS NULL AND v.long_shots_norm IS NULL) )",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT p.player_fifa_api_id AS player_fifa_api_id, pa.id AS player_attributes_id, pa.player_api_id AS player_api_id, CASE WHEN trim(pa.long_shots) = '' THEN NULL ELSE CAST(pa.long_shots AS INTEGER) END AS long_shots_norm FROM Player p JOIN Player_Attributes pa ON pa.player_api_id = p.player_api_id
```

---

## Skill `team_avg_chancecreationpassing_by_date_and_dribbling`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `team_id`, `team_long_name`, `attribute_date` (keyed) |
| status / version | active / v1 |
| skill id | sk_67353af0c2f1e5f2 |
| output columns | `team_id`, `team_long_name`, `attribute_date`, `avg_chanceCreationPassing` |
| source tables | `Team_Attributes`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-team average chanceCreationPassing for team attribute records filtered by date range and buildUpPlayDribblingClass, including team identifiers and date of the attribute record to allow joins or further filtering.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [
      "2014-01-01 00:00:00",
      "2014-01-31 00:00:00",
      "Normal"
    ],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Team_Attributes",
      "Team"
    ],
    "table_fingerprints": {
      "team_attributes": "a8661cb8da0875ec",
      "team": "a19728cad815ec8a"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1041",
    "question": "For the teams with normal build-up play dribbling class in 2014, List the names of the teams with less than average chance creation passing, in descending order of chance creation passing.",
    "rewrite": "Task: From the records in 2014 for teams whose buildUpPlayDribblingClass is 'Normal', return the team_long_name values for those teams whose average chanceCreationPassing is less than the overall average chanceCreationPassing, listing them in descending order of their average chanceCreationPassing.\nRequired outputs: team_long_name; average_chanceCreationPassing\nFilters: date >= '2014-01-01 00:00:00' AND date <= '2014-01-31 00:00:00'; buildUpPlayDribblingClass = 'Normal'\nSort/limit: ORDER BY average_chanceCreationPassing DESC",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:06:24+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:06:28+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "team_id",
      "team_long_name",
      "attribute_date",
      "avg_chanceCreationPassing"
    ],
    "row_count": 1457,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Team_Attributes.team_api_id=Team.team_api_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (team_id, team_long_name, attribute_date)",
        "sql": "SELECT COUNT(*) FROM (\n  SELECT team_id, team_long_name, attribute_date, COUNT(*) AS cnt\n  FROM team_avg_chancecreationpassing_by_date_and_dribbling\n  GROUP BY team_id, team_long_name, attribute_date\n  HAVING cnt > 1\n)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "avg_chanceCreationPassing equals AVG(chanceCreationPassing) computed from base tables for the same grouping (detects aggregation or join errors)",
        "sql": "SELECT COUNT(*) FROM (\n  SELECT v.team_id, v.team_long_name, v.attribute_date\n  FROM team_avg_chancecreationpassing_by_date_and_dribbling v\n  LEFT JOIN (\n    SELECT TA.team_api_id AS team_id, T.team_long_name AS team_long_name, TA.date AS attribute_date, AVG(TA.chanceCreationPassing) AS computed_avg\n    FROM Team_Attributes TA\n    JOIN Team T ON TA.team_api_id = T.team_api_id\n    GROUP BY TA.team_api_id, T.team_long_name, TA.date\n  ) b ON v.team_id = b.team_id AND v.team_long_name = b.team_long_name AND v.attribute_date = b.attribute_date\n  WHERE b.computed_avg IS NULL OR (ABS(v.avg_chanceCreationPassing - b.computed_avg) > 0.000001)\n)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL (team_id, team_long_name, attribute_date must be present)",
        "sql": "SELECT (COALESCE(\n  (SELECT COUNT(*) FROM team_avg_chancecreationpassing_by_date_and_dribbling WHERE team_id IS NULL),0) +\n  COALESCE((SELECT COUNT(*) FROM team_avg_chancecreationpassing_by_date_and_dribbling WHERE team_long_name IS NULL),0) +\n  COALESCE((SELECT COUNT(*) FROM team_avg_chancecreationpassing_by_date_and_dribbling WHERE attribute_date IS NULL),0)\n) AS violations",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT TA.team_api_id AS team_id, T.team_long_name AS team_long_name, TA.date AS attribute_date, AVG(TA.chanceCreationPassing) AS avg_chanceCreationPassing
FROM Team_Attributes TA
JOIN Team T ON TA.team_api_id = T.team_api_id
GROUP BY TA.team_api_id, T.team_long_name, TA.date
```

---

## Skill `league_season_home_away_avg_goals`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `league_name`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_bef9783c038726c8 |
| output columns | `league_id`, `league_name`, `season`, `avg_home_goal`, `avg_away_goal` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per league and season average goals scored by home teams and by away teams (one row per league-season with avg_home_goal and avg_away_goal)

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [
      "'2009/2010'"
    ],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Match",
      "League"
    ],
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3",
      "league": "72cd1678e1e9160e"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1042",
    "question": "List the name of leagues in which the average goals by the home team is higher than the away team in the 2009/2010 season.",
    "rewrite": "Task: Find the names of leagues for the 2009/2010 season where the average goals scored by the home team is greater than the average goals scored by the away team.\nRequired outputs: League.name (the league name)\nFilters: season = '2009/2010'; AVG(home_team_goal) > AVG(away_team_goal) per league",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:06:35+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:06:39+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "league_id",
      "league_name",
      "season",
      "avg_home_goal",
      "avg_away_goal"
    ],
    "row_count": 88,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Match.league_id=League.id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "View has one row per league_id, league_name, season (no duplicate keys)",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, league_name, season, COUNT(*) AS cnt FROM league_season_home_away_avg_goals GROUP BY league_id, league_name, season HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "avg_home_goal and avg_away_goal match averages recomputed from base Match table for the same league and season",
        "sql": "SELECT COUNT(*) FROM league_season_home_away_avg_goals v LEFT JOIN (SELECT league_id, season, AVG(home_team_goal) AS exp_avg_home, AVG(away_team_goal) AS exp_avg_away FROM \"Match\" GROUP BY league_id, season) m ON v.league_id = m.league_id AND v.season = m.season WHERE NOT ((m.exp_avg_home IS NULL AND v.avg_home_goal IS NULL) OR (m.exp_avg_home IS NOT NULL AND ABS(v.avg_home_goal - m.exp_avg_home) < 1e-9)) OR NOT ((m.exp_avg_away IS NULL AND v.avg_away_goal IS NULL) OR (m.exp_avg_away IS NOT NULL AND ABS(v.avg_away_goal - m.exp_avg_away) < 1e-9))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys league_id, league_name, season are never NULL",
        "sql": "SELECT COUNT(*) FROM league_season_home_away_avg_goals WHERE league_id IS NULL OR league_name IS NULL OR season IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT M.league_id, L.name AS league_name, M.season, AVG(M.home_team_goal) AS avg_home_goal, AVG(M.away_team_goal) AS avg_away_goal FROM Match M JOIN League L ON M.league_id = L.id GROUP BY M.league_id, L.name, M.season
```

---

## Skill `player_avg_finishing_by_height`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_id`, `player_name`, `height` (keyed) |
| status / version | active / v1 |
| skill id | sk_859db6daec2cade3 |
| output columns | `player_id`, `player_name`, `height`, `avg_finishing`, `finishing_count` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player average finishing and height: one row per player with their id, name, height, average finishing and count of finishing observations

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Player",
      "Player_Attributes"
    ],
    "table_fingerprints": {
      "player": "032b398bb82740dc",
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1058",
    "question": "Who has the highest average finishing rate between the highest and shortest football player?",
    "rewrite": "Task: Compare the average finishing rates of the tallest football player and the shortest football player, and return which of the two has the higher average finishing rate (or both if tied).\nRequired outputs: player_identifier for the tallest player (enough to identify the player, e.g., id or name); height of the tallest player; average_finishing of the tallest player (AVG(finishing)); player_identifier for the shortest player (e.g., id or name); height of the shortest player; average_finishing of the shortest player (AVG(finishing)); winner_indicator specifying which player has the higher average finishing rate or 'tie'\nFilters: tallest player: rows where height = MAX(height) across all players; shortest player: rows where height = MIN(height) across all players",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:09:15+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:09:19+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "player_name",
      "height",
      "avg_finishing",
      "finishing_count"
    ],
    "row_count": 11060,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Player_Attributes.player_api_id=Player.player_api_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "View has one row per player key (no duplicate rows for same player_id, player_name, height)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_id, player_name, height, COUNT(*) AS cnt FROM player_avg_finishing_by_height GROUP BY player_id, player_name, height HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "avg_finishing equals AVG(finishing) computed from base tables for that player",
        "sql": "SELECT COUNT(*) FROM player_avg_finishing_by_height v LEFT JOIN (SELECT PA.player_api_id AS player_id, AVG(PA.finishing) AS expected_avg FROM Player_Attributes PA WHERE PA.finishing IS NOT NULL GROUP BY PA.player_api_id) b ON v.player_id = b.player_id WHERE (b.expected_avg IS NULL AND v.avg_finishing IS NOT NULL) OR (b.expected_avg IS NOT NULL AND ABS(v.avg_finishing - b.expected_avg) > 1e-6)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "finishing_count equals COUNT(finishing) from Player_Attributes for that player (respecting non-null filter)",
        "sql": "SELECT COUNT(*) FROM player_avg_finishing_by_height v LEFT JOIN (SELECT PA.player_api_id AS player_id, COUNT(PA.finishing) AS expected_count FROM Player_Attributes PA WHERE PA.finishing IS NOT NULL GROUP BY PA.player_api_id) b ON v.player_id = b.player_id WHERE (b.expected_count IS NULL AND v.finishing_count != 0) OR (b.expected_count IS NOT NULL AND v.finishing_count != b.expected_count)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT P.player_api_id AS player_id, P.player_name AS player_name, P.height AS height, AVG(PA.finishing) AS avg_finishing, COUNT(PA.finishing) AS finishing_count FROM Player AS P JOIN Player_Attributes AS PA ON PA.player_api_id = P.player_api_id WHERE PA.finishing IS NOT NULL GROUP BY P.player_api_id, P.player_name, P.height
```

---

## Skill `team_buildup_speed`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `team_api_id`, `team_long_name`, `buildUpPlaySpeedClass` (keyed) |
| status / version | active / v1 |
| skill id | sk_2f5fe17896b3d78d |
| output columns | `team_api_id`, `team_long_name`, `buildUpPlaySpeedClass` |
| source tables | `Team`, `Team_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Distinct teams with their build-up play speed class, useful for filtering teams by buildUpPlaySpeedClass

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [
      "'Fast'"
    ],
    "contract_version": 2,
    "grain_basis": "distinct",
    "lineage": [
      "Team",
      "Team_Attributes"
    ],
    "table_fingerprints": {
      "team": "a19728cad815ec8a",
      "team_attributes": "a8661cb8da0875ec"
    },
    "data_fingerprints": {
      "team": "299:51606",
      "team_attributes": "1458:1458"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1065",
    "question": "Please list all team names which the speed class is fast.",
    "rewrite": "Task: Select all distinct team_long_name values for teams whose buildUpPlaySpeedClass equals 'Fast'.\nRequired outputs: team_long_name\nFilters: buildUpPlaySpeedClass = 'Fast'",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:10:18+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:10:21+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "team_api_id",
      "team_long_name",
      "buildUpPlaySpeedClass"
    ],
    "row_count": 466,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Team.team_api_id=Team_Attributes.team_api_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "No NULLs in key columns (team_api_id, team_long_name, buildUpPlaySpeedClass) — the view's grain keys must be present",
        "sql": "SELECT COUNT(*) FROM team_buildup_speed WHERE team_api_id IS NULL OR team_long_name IS NULL OR buildUpPlaySpeedClass IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view must correspond to an existing Team joined to Team_Attributes (i.e., no rows whose team_api_id is missing from base tables)",
        "sql": "SELECT COUNT(*) FROM team_buildup_speed v LEFT JOIN Team t ON v.team_api_id = t.team_api_id LEFT JOIN Team_Attributes ta ON v.team_api_id = ta.team_api_id WHERE t.team_api_id IS NULL OR ta.team_api_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View contains only distinct rows at its declared grain (no duplicates of the key triple)",
        "sql": "SELECT COUNT(*) FROM (SELECT team_api_id, team_long_name, buildUpPlaySpeedClass, COUNT(*) AS cnt FROM team_buildup_speed GROUP BY team_api_id, team_long_name, buildUpPlaySpeedClass HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT DISTINCT t.team_api_id, t.team_long_name, ta.buildUpPlaySpeedClass
FROM Team t
JOIN Team_Attributes ta ON t.team_api_id = ta.team_api_id
```

---

## Skill `league_with_country`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `league_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_527d441f725c07bb |
| output columns | `league_id`, `league_name`, `country_id`, `country_name` |
| source tables | `League`, `Country` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

A denormalized relation linking leagues to their countries, listing each league and the country it belongs to

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [
      "'Belgium Jupiler League'"
    ],
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "League",
      "Country"
    ],
    "table_fingerprints": {
      "league": "72cd1678e1e9160e",
      "country": "a556b33684a1aaf5"
    },
    "data_fingerprints": {
      "league": "11:24558",
      "country": "11:24558"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1081",
    "question": "Which country is the Belgium Jupiler League from?",
    "rewrite": "Task: Find the country (Country.name) of the league whose League.name equals 'Belgium Jupiler League'.\nRequired outputs: Country.name\nFilters: League.name = 'Belgium Jupiler League'",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:12:09+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:12:11+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "league_id",
      "league_name",
      "country_id",
      "country_name"
    ],
    "row_count": 11,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "League.country_id=Country.id",
        "left_unique": true,
        "right_unique": true,
        "relationship": "one_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate leagues: each league_id appears at most once in the view (grain uniqueness)",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, COUNT(*) AS cnt FROM league_with_country GROUP BY league_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every league in the view must reference an existing Country (country_id matches a Country row)",
        "sql": "SELECT COUNT(*) FROM league_with_country l WHERE NOT EXISTS (SELECT 1 FROM Country c WHERE c.id = l.country_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "League-level data matches base tables: league_name and country_id correspond to the League row for that league_id",
        "sql": "SELECT COUNT(*) FROM league_with_country v JOIN League L ON v.league_id = L.id WHERE (v.league_name IS NOT L.name) OR (v.country_id IS NOT L.country_id)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT League.id AS league_id, League.name AS league_name, Country.id AS country_id, Country.name AS country_name
FROM League
JOIN Country ON League.country_id = Country.id
```

---

## Skill `matches_count_by_league_season`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_486a5d6e2b5455a4 |
| output columns | `league_id`, `season`, `matches_count` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each league and season, the total number of matches played (one row per league-season)

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [
      "'2008/2009'"
    ],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Match"
    ],
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1092",
    "question": "Which league had the most matches in the 2008/2009 season?",
    "rewrite": "Task: Find the league identifier that has the maximum number of matches in the 2008/2009 season.\nRequired outputs: league_id (the identifier of the league that had the most matches in season '2008/2009'); matches_count (the number of matches in that league during season '2008/2009')\nFilters: season = '2008/2009' (only consider matches played in the 2008/2009 season)\nSort/limit: order by matches_count desc limit 1",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:13:24+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:13:26+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "league_id",
      "season",
      "matches_count"
    ],
    "row_count": 88,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "Each row in the view should be unique per grain (league_id, season) — detect duplicate league_id+season combinations in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, season, COUNT(*) AS cnt FROM matches_count_by_league_season GROUP BY league_id, season HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "matches_count must equal the number of Match rows for that league and season (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM matches_count_by_league_season v LEFT JOIN (SELECT league_id, season, COUNT(*) AS expected_count FROM \"Match\" GROUP BY league_id, season) b ON v.league_id IS b.league_id AND v.season IS b.season WHERE v.matches_count IS NOT b.expected_count OR (b.expected_count IS NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys league_id and season must not be NULL in the view",
        "sql": "SELECT COUNT(*) FROM matches_count_by_league_season WHERE league_id IS NULL OR season IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT league_id, season, COUNT(*) AS matches_count FROM "Match" GROUP BY league_id, season
```

---

## Skill `team_chance_creation_passing_max_per_team`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `team_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_92393fa738ee56e0 |
| output columns | `team_api_id`, `max_chanceCreationPassing` |
| source tables | `Team_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each team, the maximum chanceCreationPassing value observed in Team_Attributes along with the associated chanceCreationPassingClass for that maximum value (keys to join: team_api_id and chanceCreationPassing).

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [
      "'Ajax'"
    ],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Team_Attributes"
    ],
    "table_fingerprints": {
      "team_attributes": "a8661cb8da0875ec"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1098",
    "question": "What is Ajax's highest chance creation passing score and what is it classified as?",
    "rewrite": "Task: Find the maximum value of chanceCreationPassing for the team whose team_long_name is 'Ajax', and report that maximum along with the associated chanceCreationPassingClass for Ajax.\nRequired outputs: chanceCreationPassing: the maximum numeric value of chanceCreationPassing for team_long_name = 'Ajax'; chanceCreationPassingClass: the classification label corresponding to that maximum chanceCreationPassing value for team_long_name = 'Ajax'\nFilters: team_long_name = 'Ajax'",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:14:58+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:15:01+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "team_api_id",
      "max_chanceCreationPassing"
    ],
    "row_count": 288,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No NULL keys: every row in the view must have a non-NULL team_api_id",
        "sql": "SELECT COUNT(*) FROM team_chance_creation_passing_max_per_team WHERE team_api_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Max measure correctness: for each team_api_id, the view's max_chanceCreationPassing equals the MAX(chanceCreationPassing) computed from Team_Attributes",
        "sql": "SELECT COUNT(*) FROM team_chance_creation_passing_max_per_team v LEFT JOIN (SELECT team_api_id, MAX(chanceCreationPassing) AS expected_max FROM Team_Attributes GROUP BY team_api_id) t ON v.team_api_id = t.team_api_id WHERE (v.max_chanceCreationPassing IS NOT t.expected_max) OR (v.max_chanceCreationPassing IS NULL AND t.expected_max IS NOT NULL) OR (v.max_chanceCreationPassing IS NOT NULL AND t.expected_max IS NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "One row per team: there are no duplicate team_api_id values in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT team_api_id, COUNT(*) AS c FROM team_chance_creation_passing_max_per_team GROUP BY team_api_id HAVING c <> 1)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT ta.team_api_id, MAX(ta.chanceCreationPassing) AS max_chanceCreationPassing
FROM Team_Attributes ta
GROUP BY ta.team_api_id
```

---

## Skill `player_max_overall_rating_17`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_api_id`, `player_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_9d1eb4de3d555303 |
| output columns | `player_api_id`, `player_name`, `max_overall_rating` |
| source tables | `Player_Attributes`, `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player maximum overall_rating across Player_Attributes, joined to Player to map player_api_id to player_name.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [
      "'Dorlan Pabon'"
    ],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Player_Attributes",
      "Player"
    ],
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203",
      "player": "032b398bb82740dc"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1100",
    "question": "What is the highest overall rating received by Dorlan Pabon?",
    "rewrite": "Task: Compute the maximum overall_rating value for rows where T2.player_name = 'Dorlan Pabon'.\nRequired outputs: MAX(overall_rating)\nFilters: T2.player_name = 'Dorlan Pabon'",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:15:13+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:15:17+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
      "player_name",
      "max_overall_rating"
    ],
    "row_count": 11060,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View rows have non-NULL keys (player_api_id, player_name)",
        "sql": "SELECT COUNT(*) FROM player_max_overall_rating_17 WHERE player_api_id IS NULL OR player_name IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "max_overall_rating equals MAX(overall_rating) computed from Player_Attributes for that player_api_id (recomputed using both join keys as in view)",
        "sql": "SELECT COUNT(*) FROM player_max_overall_rating_17 vm WHERE (SELECT MAX(pa.overall_rating) FROM Player_Attributes pa JOIN Player p ON pa.player_api_id = p.player_api_id OR pa.player_fifa_api_id = p.player_fifa_api_id WHERE p.player_api_id = vm.player_api_id) IS NOT vm.max_overall_rating AND NOT ( (SELECT MAX(pa.overall_rating) FROM Player_Attributes pa JOIN Player p ON pa.player_api_id = p.player_api_id OR pa.player_fifa_api_id = p.player_fifa_api_id WHERE p.player_api_id = vm.player_api_id) IS NULL AND vm.max_overall_rating IS NULL )",
        "result": "inconclusive",
        "violations": null,
        "error": "timeout"
      },
      {
        "purpose": "No duplicate rows per grain (player_api_id, player_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_api_id, player_name, COUNT(*) AS cnt FROM player_max_overall_rating_17 GROUP BY player_api_id, player_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT p.player_api_id, p.player_name, MAX(pa.overall_rating) AS max_overall_rating
FROM Player_Attributes pa
JOIN Player p ON pa.player_api_id = p.player_api_id OR pa.player_fifa_api_id = p.player_fifa_api_id
GROUP BY p.player_api_id, p.player_name
```

---

## Skill `away_team_goals_by_match_in_country`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `match_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_90e5a1c53b6909d6 |
| output columns | `match_api_id`, `away_team_api_id`, `home_team_api_id`, `country_id`, `away_team_goal` |
| source tables | `Match`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-match records of away team goals with keys to join team and country so you can compute aggregates (e.g., averages) for any away team and country.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [
      "'Parma'",
      "'Italy'"
    ],
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "Match",
      "Team"
    ],
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3",
      "team": "a19728cad815ec8a"
    },
    "data_fingerprints": {
      "match": "25979:25979",
      "team": "299:51606"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1101",
    "question": "What is the average number of goals made by Parma as the away team while playing in Italy?",
    "rewrite": "Task: Compute the average number of goals scored by the team 'Parma' when Parma is the away team and the match takes place in Italy.\nRequired outputs: average_away_goals: the value AVG(away_team_goal) computed over all matches that meet the filters\nFilters: team_long_name = 'Parma' applied to the away team (i.e., away_team_long_name = 'Parma'); country = 'Italy' (match taking place in Italy)",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:15:35+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:15:37+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "match_api_id",
      "away_team_api_id",
      "home_team_api_id",
      "country_id",
      "away_team_goal"
    ],
    "row_count": 25979,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Match.away_team_api_id=Team.team_api_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain match_api_id (each match_api_id appears at most once)",
        "sql": "SELECT COUNT(*) FROM (SELECT match_api_id, COUNT(*) AS cnt FROM away_team_goals_by_match_in_country GROUP BY match_api_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view corresponds to an existing Match row (join didn't create extra rows)",
        "sql": "SELECT COUNT(*) FROM away_team_goals_by_match_in_country v LEFT JOIN \"Match\" m ON v.match_api_id = m.match_api_id WHERE m.match_api_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "away_team_goal in the view equals the source Match.away_team_goal for each match_api_id (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM away_team_goals_by_match_in_country v JOIN \"Match\" m ON v.match_api_id = m.match_api_id WHERE (v.away_team_goal IS NOT m.away_team_goal) OR (v.away_team_goal IS NULL AND m.away_team_goal IS NOT NULL) OR (v.away_team_goal IS NOT NULL AND m.away_team_goal IS NULL)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT m.match_api_id, m.away_team_api_id, m.home_team_api_id, m.country_id, m.away_team_goal
FROM "Match" m
JOIN "Team" t ON m.away_team_api_id = t.team_api_id
```

---

## Skill `player_max_overall_rating_19`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_32e9e1760e5a3c24 |
| output columns | `player_api_id`, `max_overall_rating` |
| source tables | `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player maximum overall rating across all attribute records, useful to rank or filter players by their peak overall_rating.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [
      "10",
      "ORDER BY",
      "LIMIT"
    ],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Player_Attributes"
    ],
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1122",
    "question": "State 10 names of the strongest players.",
    "rewrite": "Task: Return the names of the 10 players with the highest overall_rating (MAX(overall_rating) per player).\nRequired outputs: player_name (the player's name); overall_rating (that player's overall rating)\nFilters: Consider each player's overall_rating value; select players with the highest overall_rating values.; If multiple players share the same overall_rating that places them within the top 10 by rating, include them according to the ordering rule below (stable tie handling defined by sort).\nSort/limit: order by overall_rating DESC limit 10",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:19:26+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:19:29+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
      "max_overall_rating"
    ],
    "row_count": 11060,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View has one row per player_api_id (no duplicate player_api_id)",
        "sql": "SELECT COUNT(*) FROM player_max_overall_rating_19 v GROUP BY player_api_id HAVING COUNT(*)>1 LIMIT 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's max_overall_rating equals the max overall_rating computed from Player_Attributes for that player_api_id",
        "sql": "SELECT COUNT(*) FROM player_max_overall_rating_19 v LEFT JOIN (SELECT player_api_id, MAX(overall_rating) AS expected_max FROM Player_Attributes GROUP BY player_api_id) p ON v.player_api_id = p.player_api_id WHERE p.player_api_id IS NULL OR (v.max_overall_rating IS NOT p.expected_max AND NOT (v.max_overall_rating IS NULL AND p.expected_max IS NULL))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "player_api_id is never NULL in the view (key present)",
        "sql": "SELECT COUNT(*) FROM player_max_overall_rating_19 WHERE player_api_id IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT player_api_id, MAX(overall_rating) AS max_overall_rating FROM Player_Attributes GROUP BY player_api_id
```

---

## Skill `players_with_high_vision_from_player_attributes`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `player_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_d7c41d2fc7a81da4 |
| output columns | `id`, `player_api_id`, `player_name`, `player_fifa_api_id`, `player_attributes_id`, `date`, `vision` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Each row represents a Player joined to one of their Player_Attributes records where that attributes record has vision > 89; columns are player fields from Player and the linked Player_Attributes id, date, and vision.

### Semantic filters

```json
{
  "vision": ">89"
}
```

### Learned skill parameters

```json
{
  "description": "Each row represents a Player joined to one of their Player_Attributes records where that attributes record has vision > 89; columns are player fields from Player and the linked Player_Attributes id, date, and vision.",
  "when_to_use": "To get all Player_Attributes records (and basic Player info) for players whose specific attributes record has a very high vision score (>89). | As a starting set when you need player identity (id, player_api_id, player_name, player_fifa_api_id) together with the attributes record id, date, and vision for high-vision attribute snapshots. | When joining to other tables keyed by Player.id or Player_Attributes.id for analyses focused on these attribute rows.",
  "when_not_to_use": "When you need one row per player regardless of how many high-vision attribute records they have — the view keeps one row per Player_Attributes record (grain = player_attributes_id), so players with multiple qualifying records appear multiple times. | When you need the latest (or earliest) attribute record per player — the view does not filter or aggregate by date, so it does not enforce any time-window or selection of a single snapshot. | When you need players who never have vision >89 — those players are excluded by the WHERE filter on pa.vision. | When you expect attributes joined by player_fifa_api_id instead of player_api_id — the join path is specifically ON pa.player_api_id = p.player_api_id and would miss matches that only align on player_fifa_api_id. | When you need aggregated statistics (counts, averages, max/min) across attribute records — this view exposes raw rows with no aggregation. | When you need a different vision threshold or a range — the intrinsic filter pa.vision > 89 is hard-coded and will produce incomplete results for other thresholds or inclusive bounds."
}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "av_chunk",
    "subgoal": {
      "want_name": "chunk_view_0",
      "category": "SEL",
      "required_outputs": [],
      "required_grain": [],
      "required_filters": {},
      "text": "Task: Find all players whose vision score is 90 or higher and report each player's country.\nRequired outputs: player identifier or name; country\nFilters: vision > 89",
      "source_tables": [
        "Player",
        "Player_Attributes"
      ],
      "depends_on": [],
      "join_keys": [],
      "relationship": "",
      "may_read_base_tables": true,
      "holistic": true,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "Player",
      "Player_Attributes"
    ],
    "table_fingerprints": {
      "player": "032b398bb82740dc",
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {
      "player": "11060:11075",
      "player_attributes": "183978:183978"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1127",
    "question": "Locate players with vision scores of 90 and above, state the country of these players.",
    "rewrite": "Task: Find all players whose vision score is 90 or higher and report each player's country.\nRequired outputs: player identifier or name; country\nFilters: vision > 89",
    "route": "av_nx1_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:20:23+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:20:26+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "id",
      "player_api_id",
      "player_name",
      "player_fifa_api_id",
      "player_attributes_id",
      "date",
      "vision"
    ],
    "row_count": 412,
    "grain_check": "pass",
    "filter_checks": {
      "vision": "pass"
    },
    "join_cardinality": [
      {
        "join": "Player_Attributes.player_api_id=Player.player_api_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the view grain (player_attributes_id should be unique)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_attributes_id, COUNT(*) AS cnt FROM chunk_view_0 GROUP BY player_attributes_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows satisfy the intrinsic filter vision > 89",
        "sql": "SELECT COUNT(*) FROM chunk_view_0 WHERE NOT (vision > 89)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row's player_api_id matches a Player row (join did not invent player_api_id) and is not NULL",
        "sql": "SELECT COUNT(*) FROM chunk_view_0 v LEFT JOIN Player p ON v.player_api_id = p.player_api_id WHERE v.player_api_id IS NULL OR p.player_api_id IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
    p.id,
    p.player_api_id,
    p.player_name,
    p.player_fifa_api_id,
    pa.id AS player_attributes_id,
    pa.date,
    pa.vision
FROM
    Player p
JOIN
    Player_Attributes pa
    ON pa.player_api_id = p.player_api_id
WHERE
    pa.vision > 89
```

---

## Skill `player_with_country`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `id` (keyed) |
| status / version | active / v1 |
| skill id | sk_b7820b972bf630a6 |
| output columns | `player_id`, `height`, `id`, `player_api_id`, `player_name`, `player_fifa_api_id`, `birthday`, `height:1`, `weight`, `country_id`, `country_name`, `id:1`, `name` |
| source tables | `Player`, `Country` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Denormalized relation joining players with their country's attributes so queries can filter or aggregate players by country.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [
      "'Italy'"
    ],
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "Player",
      "Country"
    ],
    "table_fingerprints": {
      "player": "032b398bb82740dc",
      "country": "a556b33684a1aaf5"
    },
    "data_fingerprints": {
      "player": "11060:11075",
      "country": "11:24558"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1131",
    "question": "What is the average heights of Italy players?",
    "rewrite": "Task: Compute the average height (Avg(height)) of players whose country name is 'Italy'.\nRequired outputs: average_height: a single numeric value representing the average of the height field for the selected players\nFilters: country = 'Italy'; include all rows that represent players (no additional row-type filtering specified)",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:20:57+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:21:01+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "height",
      "id",
      "player_api_id",
      "player_name",
      "player_fifa_api_id",
      "birthday",
      "height:1",
      "weight",
      "country_id",
      "country_name",
      "id:1",
      "name"
    ],
    "row_count": 5,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Country.id=Player.id",
        "left_unique": true,
        "right_unique": true,
        "relationship": "one_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (player_with_country.id should be unique). Counts number of player_id values that appear more than once in the view.",
        "sql": "SELECT COUNT(*) FROM (SELECT player_id, COUNT(*) AS cnt FROM player_with_country GROUP BY player_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each view row should reference an existing Player: detect rows whose player_id does not match any Player.id (join accidentally dropped/mismatched).",
        "sql": "SELECT COUNT(*) FROM player_with_country v WHERE NOT EXISTS (SELECT 1 FROM Player p WHERE p.id = v.player_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Country fields should be consistent with the Country table: detect rows where country_id is not NULL but the corresponding country_name disagrees with Country.name (join misaligned or duplicated colum",
        "sql": "SELECT COUNT(*) FROM player_with_country v JOIN Country c ON c.id = v.country_id WHERE v.country_name IS NOT NULL AND v.country_name != c.name",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "included": 1
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT Player.id AS player_id, Player.height, Player.* , Country.id AS country_id, Country.name AS country_name, Country.* FROM Player JOIN Country ON Country.id = Player.id
```

---

## Skill `players_base`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_b338edfc10d7bdb8 |
| output columns | `player_id`, `crossing`, `preferred_foot` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Select base player rows with their crossing value and preferred foot. One row per player.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "subgoal",
    "subgoal": {
      "want_name": "players_base",
      "category": "SEL",
      "required_outputs": [
        "player_id",
        "crossing",
        "preferred_foot"
      ],
      "required_grain": [
        "player_id"
      ],
      "required_filters": {},
      "text": "Select base player rows with their crossing value and preferred foot. One row per player.",
      "source_tables": [],
      "depends_on": [],
      "join_keys": [],
      "relationship": "one_to_one",
      "may_read_base_tables": true,
      "holistic": false,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Player",
      "Player_Attributes"
    ],
    "table_fingerprints": {
      "player": "032b398bb82740dc",
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1136",
    "question": "How many players had the highest potential score for crossing that preferred to use their left foots while attacking?",
    "rewrite": "Task: Count how many players have the maximum value of crossing (i.e., crossing equals MAX(crossing)) among all players and whose preferred_foot is 'left'.\nRequired outputs: an integer count of players meeting the conditions\nFilters: preferred_foot = 'left'; crossing = MAX(crossing)  -- the player's crossing equals the global maximum crossing value across all players",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:21:50+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:21:52+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "crossing",
      "preferred_foot"
    ],
    "row_count": 11060,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Player.player_api_id=Player_Attributes.player_api_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate player_id rows (view should be one row per player_id).",
        "sql": "SELECT COUNT(*) FROM (SELECT player_id, COUNT(*) AS cnt FROM players_base GROUP BY player_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view must join to an existing Player_Attributes row (PA.id IS NOT NULL condition): ensure no NULL preferred_foot/crossing when there is no matching attribute.",
        "sql": "SELECT COUNT(*) FROM players_base pb WHERE NOT EXISTS (SELECT 1 FROM Player_Attributes pa WHERE pa.player_api_id = pb.player_id)",
        "result": "inconclusive",
        "violations": null,
        "error": "timeout"
      },
      {
        "purpose": "player_id is not NULL (key must be present).",
        "sql": "SELECT COUNT(*) FROM players_base WHERE player_id IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "included": 1
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  P.player_api_id AS player_id,
  PA.crossing AS crossing,
  PA.preferred_foot AS preferred_foot
FROM Player P
LEFT JOIN Player_Attributes PA
  ON P.player_api_id = PA.player_api_id
WHERE PA.id IS NOT NULL
GROUP BY P.player_api_id
```

---

## Skill `team_game_counts_by_season`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `season`, `team_api_id`, `team_long_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_86b19b4044da4f29 |
| output columns | `season`, `team_api_id`, `team_long_name`, `game_count` |
| source tables | `Match`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-team counts of matches played in each season (counts matches where the team appears as home team), useful for season-team level game counts.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [
      "'2015/2016'"
    ],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Match",
      "Team"
    ],
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3",
      "team": "a19728cad815ec8a"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1145",
    "question": "Which league had the most games in the 2015–2016 season?",
    "rewrite": "Task: Find the league (team_long_name) that had the largest number of games (count of id) during the 2015–2016 season (season = '2015/2016').\nRequired outputs: team_long_name: the league name that has the maximum game count; game_count: the number of games (COUNT(id)) for that league in the 2015/2016 season\nFilters: season = '2015/2016' (only consider rows from the 2015–2016 season)\nSort/limit: order by game_count desc limit 1",
    "route": "av_nx1_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:24:03+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T00:24:06+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "season",
      "team_api_id",
      "team_long_name",
      "game_count"
    ],
    "row_count": 1481,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Team.team_api_id=Match.home_team_api_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (season, team_api_id, team_long_name).",
        "sql": "SELECT COUNT(*) FROM (SELECT season, team_api_id, team_long_name, COUNT(*) AS cnt FROM team_game_counts_by_season GROUP BY season, team_api_id, team_long_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each view row's game_count equals the number of Match rows where that team is the home team in that season (measure reconciliation).",
        "sql": "SELECT COUNT(*) FROM team_game_counts_by_season v LEFT JOIN (SELECT m.season, m.home_team_api_id AS team_api_id, COUNT(m.id) AS expected_count FROM Match m GROUP BY m.season, m.home_team_api_id) b ON v.season = b.season AND v.team_api_id = b.team_api_id WHERE (b.expected_count IS NULL AND v.game_count IS NOT NULL) OR (b.expected_count IS NOT NULL AND v.game_count != b.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys that define the grain are not NULL (season, team_api_id, team_long_name).",
        "sql": "SELECT COUNT(*) FROM team_game_counts_by_season WHERE season IS NULL OR team_api_id IS NULL OR team_long_name IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT m.season, t.team_api_id, t.team_long_name, COUNT(m.id) AS game_count FROM Match m JOIN Team t ON t.team_api_id = m.home_team_api_id GROUP BY m.season, t.team_api_id, t.team_long_name
```

---
