# Skill graph — `european_football_2` (18 skills)

## Skill `player_max_crossing`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_cee5eff8c8eed3e0 |
| output columns | `player_id`, `max_crossing` |
| source tables | `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player maximum 'crossing' attribute value computed from Player_Attributes for players that have at least one crossing value.

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
      "5",
      "LIMIT 5"
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
    "question_id": "bird_dev_1024",
    "question": "Who are the top 5 players who perform better in crossing actions? Indicate their player id.",
    "rewrite": "Task: Find the top 5 players (by player id) whose maximum value of the 'crossing' metric is highest.\nRequired outputs: player id; max(crossing)\nFilters: Consider all players with at least one crossing value (no additional row filters).; Use the maximum crossing value per player (MAX(crossing)).\nSort/limit: Order results by MAX(crossing) in descending order and return the top 5 rows (limit 5).",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:11:25+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:11:28+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "max_crossing"
    ],
    "row_count": 11060,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View grain: one row per player_id (no duplicate player_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_id, COUNT(*) AS cnt FROM player_max_crossing GROUP BY player_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "max_crossing matches MAX(crossing) computed from base table for players that have at least one non-NULL crossing",
        "sql": "SELECT COUNT(*) FROM player_max_crossing pmc LEFT JOIN (SELECT player_api_id AS player_id, MAX(crossing) AS expected_max FROM Player_Attributes WHERE crossing IS NOT NULL GROUP BY player_api_id) src ON pmc.player_id = src.player_id WHERE src.player_id IS NULL OR (pmc.max_crossing IS NOT src.expected_max AND NOT (pmc.max_crossing IS NULL AND src.expected_max IS NULL))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL (player_id must be present)",
        "sql": "SELECT COUNT(*) FROM player_max_crossing WHERE player_id IS NULL",
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
SELECT player_api_id AS player_id, MAX(crossing) AS max_crossing FROM Player_Attributes WHERE crossing IS NOT NULL GROUP BY player_api_id
```

---

## Skill `match_goals_by_league_season`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `league_name`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_24e290775801f384 |
| output columns | `league_id`, `league_name`, `season`, `total_goals` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-league per-season total goals summed from matches (sum of home_team_goal + away_team_goal) with only matches having non-null goal counts

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
    "rewrite": "Task: Find the league (competition) that had the highest total number of goals scored across all matches in the 2015/2016 season, where goals in a match are counted as home_team_goal + away_team_goal and totals are summed per league.\nRequired outputs: league (the league/competition identifier or name); total_goals (the sum of home_team_goal + away_team_goal for all matches in that league during the 2015/2016 season)\nFilters: season = '2015/2016'; only include matches with non-null home_team_goal and away_team_goal\nSort/limit: order by total_goals desc limit 1",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:11:36+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:11:40+00:00",
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
        "purpose": "No duplicate rows per grain (league_id, league_name, season)",
        "sql": "SELECT COUNT(*) FROM match_goals_by_league_season v JOIN (SELECT league_id, league_name, season, COUNT(*) AS cnt FROM match_goals_by_league_season GROUP BY league_id, league_name, season HAVING cnt > 1) d USING (league_id, league_name, season) WHERE 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's total_goals equals the sum computed from Match rows that have non-null goal counts for that league and season",
        "sql": "SELECT COUNT(*) FROM match_goals_by_league_season v WHERE v.total_goals != (SELECT COALESCE(SUM(m.home_team_goal + m.away_team_goal),0) FROM \"Match\" m JOIN League l ON m.league_id = l.id WHERE m.home_team_goal IS NOT NULL AND m.away_team_goal IS NOT NULL AND l.id = v.league_id AND l.name = v.league_name AND m.season = v.season)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys league_id, league_name, season are NOT NULL in the view",
        "sql": "SELECT COUNT(*) FROM match_goals_by_league_season WHERE league_id IS NULL OR league_name IS NULL OR season IS NULL",
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
WHERE M.home_team_goal IS NOT NULL AND M.away_team_goal IS NOT NULL
GROUP BY L.id, L.name, M.season
```

---

## Skill `team_home_loss_counts_by_season`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `team_api_id`, `team_long_name`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_3cb5b343b992b70b |
| output columns | `team_api_id`, `team_long_name`, `season`, `home_losses_count` |
| source tables | `Match`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per team and season counts of matches lost at home (matches where home_team_goal - away_team_goal < 0).

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
    "rewrite": "Task: Find which home team(s) had the smallest number of home losses during the 2015/2016 season, where a home loss is a match in that season with (home_team_goal - away_team_goal) < 0.\nRequired outputs: home_team; home_losses_count\nFilters: season = '2015/2016'; (home_team_goal - away_team_goal) < 0  -- counts as a home loss; group results by home_team and count only matches satisfying the home loss condition\nSort/limit: order by home_losses_count asc limit 1  -- return the home team(s) with the fewest home losses",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:11:50+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:11:55+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "team_api_id",
      "team_long_name",
      "season",
      "home_losses_count"
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
        "purpose": "No duplicate rows per grain (team_api_id, team_long_name, season).",
        "sql": "SELECT COUNT(*) FROM (SELECT team_api_id, team_long_name, season, COUNT(*) AS cnt FROM team_home_loss_counts_by_season GROUP BY team_api_id, team_long_name, season HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every output row's home_losses_count equals the number of Match rows for that team/season where home_team_goal - away_team_goal < 0 (measure reconciliation).",
        "sql": "SELECT COUNT(*) FROM team_home_loss_counts_by_season v LEFT JOIN (SELECT t.team_api_id AS team_api_id, t.team_long_name AS team_long_name, m.season AS season, COUNT(m.id) AS expected_count FROM Match m JOIN Team t ON m.home_team_api_id = t.team_api_id WHERE (m.home_team_goal - m.away_team_goal) < 0 GROUP BY t.team_api_id, t.team_long_name, m.season) b ON v.team_api_id = b.team_api_id AND v.team_long_name = b.team_long_name AND v.season = b.season WHERE (v.home_losses_count IS NOT b.expected_count) OR (v.home_losses_count IS NULL AND b.expected_count IS NOT NULL) OR (b.expected_count IS NULL AND v.home_losses_count IS NOT NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Primary key columns are not NULL (team_api_id, team_long_name, season).",
        "sql": "SELECT COUNT(*) FROM team_home_loss_counts_by_season WHERE team_api_id IS NULL OR team_long_name IS NULL OR season IS NULL",
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
SELECT t.team_api_id, t.team_long_name, m.season, COUNT(m.id) AS home_losses_count
FROM Match m
JOIN Team t ON m.home_team_api_id = t.team_api_id
WHERE (m.home_team_goal - m.away_team_goal) < 0
GROUP BY t.team_api_id, t.team_long_name, m.season
```

---

## Skill `league_season_away_wins_by_team`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `season`, `away_team_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_b86c5a18134d0a91 |
| output columns | `league_id`, `season`, `away_team_api_id`, `away_wins_count` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-league, per-season count of away wins by away_team_api_id (away win: away_team_goal > home_team_goal)

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
    "rewrite": "Task: Find the away team (identified by away_team_api_id) in the Scotland Premier League that had the highest number of away match wins during the 2010 season ('2009/2010'), where an away win is any match with away_team_goal > home_team_goal.\nRequired outputs: away_team_api_id; away_wins_count\nFilters: League.name = 'Scotland Premier League'; season = '2009/2010'; Count only matches where away_team_goal > home_team_goal (these count as away wins)\nSort/limit: order by away_wins_count desc limit 1",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:12:12+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:12:16+00:00",
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
        "purpose": "No duplicate rows for the declared grain (league_id, season, away_team_api_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, season, away_team_api_id, COUNT(*) AS cnt FROM league_season_away_wins_by_team GROUP BY league_id, season, away_team_api_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows in the view correspond to actual away wins in the base Match table (away_team_goal > home_team_goal)",
        "sql": "SELECT COUNT(*) FROM league_season_away_wins_by_team v WHERE NOT EXISTS (SELECT 1 FROM Match m WHERE m.league_id = v.league_id AND m.season = v.season AND m.away_team_api_id = v.away_team_api_id AND m.away_team_goal > m.home_team_goal)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "away_wins_count matches the count of qualifying matches in the base table for each key",
        "sql": "SELECT COUNT(*) FROM (SELECT v.league_id, v.season, v.away_team_api_id FROM league_season_away_wins_by_team v LEFT JOIN (SELECT league_id, season, away_team_api_id, COUNT(*) AS expected_count FROM Match WHERE away_team_goal > home_team_goal GROUP BY league_id, season, away_team_api_id) b ON v.league_id = b.league_id AND v.season = b.season AND v.away_team_api_id = b.away_team_api_id WHERE (b.expected_count IS NULL) OR (v.away_wins_count IS NULL) OR (v.away_wins_count != b.expected_count))",
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
SELECT m.league_id, m.season, m.away_team_api_id, COUNT(*) AS away_wins_count FROM "Match" m WHERE m.away_team_goal > m.home_team_goal GROUP BY m.league_id, m.season, m.away_team_api_id
```

---

## Skill `team_max_build_up_play_speed`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `team_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_48dbd4942bf40120 |
| output columns | `team_api_id`, `max_buildUpPlaySpeed` |
| source tables | `Team_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-team maximum recorded buildUpPlaySpeed from Team_Attributes, with team identifier for joining.

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
      "ORDER BY",
      "LIMIT"
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
    "question_id": "bird_dev_1029",
    "question": "What are the speed in which attacks are put together of the top 4 teams with the highest build Up Play Speed?",
    "rewrite": "Task: Return the buildUpPlaySpeed values for the top 4 teams ranked by their highest buildUpPlaySpeed (i.e., the teams with the largest MAX(buildUpPlaySpeed)).\nRequired outputs: team (team identifier or name as provided in the data); buildUpPlaySpeed (the buildUpPlaySpeed value corresponding to each team)\nFilters: Consider each team's maximum buildUpPlaySpeed value (MAX(buildUpPlaySpeed)) when ranking teams; Select only the top 4 teams by that MAX(buildUpPlaySpeed); If ties occur around the 4th position, include teams only up to the 4 highest MAX(buildUpPlaySpeed) values (limit to 4 rows total)\nSort/limit: order by MAX(buildUpPlaySpeed) descending; limit 4",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:12:29+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:12:31+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "team_api_id",
      "max_buildUpPlaySpeed"
    ],
    "row_count": 288,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows per grain: ensure view has at most one row per team_api_id",
        "sql": "SELECT COUNT(*) FROM team_max_build_up_play_speed t WHERE (SELECT COUNT(*) FROM team_max_build_up_play_speed t2 WHERE t2.team_api_id = t.team_api_id) > 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Measure correctness: max_buildUpPlaySpeed equals MAX(buildUpPlaySpeed) computed from Team_Attributes for that team_api_id (handles NULLs by treating them as absent)",
        "sql": "SELECT COUNT(*) FROM team_max_build_up_play_speed v LEFT JOIN (SELECT team_api_id, MAX(buildUpPlaySpeed) AS expected_max FROM Team_Attributes GROUP BY team_api_id) src ON v.team_api_id = src.team_api_id WHERE NOT ( (v.max_buildUpPlaySpeed IS NULL AND src.expected_max IS NULL) OR (v.max_buildUpPlaySpeed = src.expected_max) )",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Key non-null: team_api_id in the view must not be NULL",
        "sql": "SELECT COUNT(*) FROM team_max_build_up_play_speed WHERE team_api_id IS NULL",
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
SELECT team_api_id, MAX(buildUpPlaySpeed) AS max_buildUpPlaySpeed FROM Team_Attributes GROUP BY team_api_id
```

---

## Skill `league_season_draw_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `league_name`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_3bd4dbc4277bb474 |
| output columns | `league_id`, `league_name`, `season`, `draw_count` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-league, per-season counts of matches that ended in a draw (home_team_goal = away_team_goal), with league id and optional league name for joining.

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
    "question_id": "bird_dev_1030",
    "question": "Which League had the most matches end as draw in the 2016 season?",
    "rewrite": "Task: Find the league (League) whose matches in the 2015/2016 season had the highest number of games that ended in a draw (where a match is a draw when home_team_goal = away_team_goal).\nRequired outputs: League (the league identifier or name); draw_count (the total number of matches in that league and season where home_team_goal = away_team_goal)\nFilters: season = '2015/2016'; a match is counted as a draw when home_team_goal = away_team_goal\nSort/limit: order by draw_count desc limit 1",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:12:39+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:12:43+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "league_id",
      "league_name",
      "season",
      "draw_count"
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
        "purpose": "View rows must be unique on the declared grain (league_id, league_name, season).",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, league_name, season, COUNT(*) AS cnt FROM league_season_draw_counts GROUP BY league_id, league_name, season HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row's draw_count must equal the number of matches in Match for that league_id and season where home_team_goal = away_team_goal (recomputed from base table).",
        "sql": "SELECT COUNT(*) FROM league_season_draw_counts v LEFT JOIN (SELECT m.league_id, m.season, COUNT(*) AS expected_draw_count FROM \"Match\" m WHERE m.home_team_goal = m.away_team_goal GROUP BY m.league_id, m.season) b ON (v.league_id IS b.league_id OR (v.league_id IS NULL AND b.league_id IS NULL)) AND v.season = b.season WHERE (b.expected_draw_count IS NULL AND v.draw_count != 0) OR (b.expected_draw_count IS NOT NULL AND v.draw_count != b.expected_draw_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys that define the grain (league_id, season) must not be NULL (league_name is optional so not tested here).",
        "sql": "SELECT COUNT(*) FROM league_season_draw_counts WHERE league_id IS NULL OR season IS NULL",
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
SELECT m.league_id, l.name AS league_name, m.season, COUNT(*) AS draw_count FROM Match m LEFT JOIN League l ON m.league_id = l.id WHERE m.home_team_goal = m.away_team_goal GROUP BY m.league_id, l.name, m.season
```

---

## Skill `matches_per_league`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_f528ec084802aebb |
| output columns | `league_id`, `match_count` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-league counts of matches (one row per league_id with total match count) for use in aggregation or joining to League metadata.

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
      "Match"
    ],
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1032",
    "question": "Give the name of the league with the highest matches of all time and how many matches were played in the said league.",
    "rewrite": "Task: Find the League.name value for the single league that has the largest total number of matches (i.e., the maximum count of matches grouped by league_id) and return that league's name together with the corresponding match count.\nRequired outputs: league_name: the League.name for the league with the highest number of matches; match_count: the integer count of matches played in that league (COUNT of rows grouped by league_id)\nFilters: Consider all matches in the Matches table (no additional date or status filters).; Group matches by league_id and compute COUNT(match_id) or COUNT(*) per league_id.; Select the league_id whose COUNT is equal to the maximum COUNT across all league_id values.; Join that league_id to League to obtain League.name.\nSort/limit: Order by match_count DESC and limit to 1 (return the single top league).",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:13:02+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:13:05+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "league_id",
      "match_count"
    ],
    "row_count": 11,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View has exactly one row per league_id (no duplicate league_id keys)",
        "sql": "SELECT COUNT(*) FROM matches_per_league m1 WHERE (SELECT COUNT(*) FROM matches_per_league m2 WHERE m2.league_id = m1.league_id) > 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every league_id in the view is not NULL (keys must be present)",
        "sql": "SELECT COUNT(*) FROM matches_per_league WHERE league_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "match_count equals the count of Match rows per league_id in the base table",
        "sql": "SELECT COUNT(*) FROM matches_per_league v LEFT JOIN (SELECT league_id, COUNT(*) AS expected_count FROM \"Match\" GROUP BY league_id) b ON (v.league_id = b.league_id) WHERE (b.expected_count IS NULL AND v.match_count IS NOT NULL) OR (b.expected_count IS NOT NULL AND v.match_count != b.expected_count)",
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
SELECT league_id, COUNT(*) AS match_count FROM "Match" GROUP BY league_id
```

---

## Skill `players_cohort`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `id` (keyed) |
| status / version | active / v1 |
| skill id | sk_d87e0a133bcfcfa3 |
| output columns | `id`, `birthday`, `height` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `players_height_normalized` |

### Description

Select the subset of player rows whose birthday is on or after 1990-01-01 00:00:00 and before 1996-01-01 00:00:00. Keep raw height and id for each player.

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
        "birthday",
        "height"
      ],
      "required_grain": [
        "player_id"
      ],
      "required_filters": {
        "birthday": ">= '1990-01-01 00:00:00' AND < '1996-01-01 00:00:00'"
      },
      "text": "Select the subset of player rows whose birthday is on or after 1990-01-01 00:00:00 and before 1996-01-01 00:00:00. Keep raw height and id for each player.",
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
    "rewrite": "Task: Compute the average height of players whose birthday is on or after 1990-01-01 00:00:00 and before 1996-01-01 00:00:00, using average height = DIVIDE(SUM(height), COUNT(id)).\nRequired outputs: average_height (a single numeric value computed as DIVIDE(SUM(height), COUNT(id)))\nFilters: birthday >= '1990-01-01 00:00:00'; birthday < '1996-01-01 00:00:00'",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:13:33+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:13:36+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "id",
      "birthday",
      "height"
    ],
    "row_count": 3360,
    "grain_check": "pass",
    "filter_checks": {
      "birthday": "pass"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No rows in the view fall outside the birthday filter (birthday must be >= 1990-01-01 and < 1996-01-01).",
        "sql": "SELECT COUNT(*) FROM players_cohort WHERE NOT (birthday >= '1990-01-01 00:00:00' AND birthday < '1996-01-01 00:00:00')",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View has the same set of player ids as selecting from base table with the same filter (no missing or extra ids).",
        "sql": "SELECT COUNT(*) FROM (SELECT id FROM players_cohort EXCEPT SELECT id FROM Player WHERE birthday >= '1990-01-01 00:00:00' AND birthday < '1996-01-01 00:00:00' UNION SELECT id FROM Player WHERE birthday >= '1990-01-01 00:00:00' AND birthday < '1996-01-01 00:00:00' EXCEPT SELECT id FROM players_cohort)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No NULL ids in the view (id is the declared grain key and must be present).",
        "sql": "SELECT COUNT(*) FROM players_cohort WHERE id IS NULL",
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
  birthday AS birthday,
  height AS height
FROM Player
WHERE birthday >= '1990-01-01 00:00:00' AND birthday < '1996-01-01 00:00:00'
```

---

## Skill `players_height_normalized`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `id` (keyed) |
| status / version | active / v1 |
| skill id | sk_d976646cda7a1fe8 |
| output columns | `id`, `height_numeric` |
| source tables | — |
| depends_on (builds on) | `players_cohort` |
| depended-on by (builds on this) | `cohort_average_height` |

### Description

Normalize/clean the height values for the selected players (cast heights to numeric, handle NULLs). Preserve one row per player id.

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
      "want_name": "players_height_normalized",
      "category": "NORM",
      "required_outputs": [
        "id",
        "height_numeric"
      ],
      "required_grain": [
        "player_id"
      ],
      "required_filters": {},
      "text": "Normalize/clean the height values for the selected players (cast heights to numeric, handle NULLs). Preserve one row per player id.",
      "source_tables": [],
      "depends_on": [
        "players_cohort"
      ],
      "join_keys": [
        "id"
      ],
      "relationship": "one_to_one",
      "may_read_base_tables": false,
      "holistic": false,
      "inherited_filters": {
        "birthday": ">= '1990-01-01 00:00:00' AND < '1996-01-01 00:00:00'"
      }
    },
    "inherited_filters": {
      "birthday": ">=1990-01-01 00:00:00;<1996-01-01 00:00:00"
    },
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "Player"
    ],
    "table_fingerprints": {
      "player": "032b398bb82740dc"
    },
    "data_fingerprints": {
      "player": "11060:11075"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1033",
    "question": "What is the average height of players born between 1990 and 1995?",
    "rewrite": "Task: Compute the average height of players whose birthday is on or after 1990-01-01 00:00:00 and before 1996-01-01 00:00:00, using average height = DIVIDE(SUM(height), COUNT(id)).\nRequired outputs: average_height (a single numeric value computed as DIVIDE(SUM(height), COUNT(id)))\nFilters: birthday >= '1990-01-01 00:00:00'; birthday < '1996-01-01 00:00:00'",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:13:36+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:13:39+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "id",
      "height_numeric"
    ],
    "row_count": 3360,
    "grain_check": "pass",
    "filter_checks": {
      "birthday": "n/a"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows per player id (grain enforcement)",
        "sql": "SELECT COUNT(*) FROM (SELECT id, COUNT(*) AS cnt FROM players_height_normalized GROUP BY id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows in the view correspond to players satisfying the intrinsic birthday filter",
        "sql": "SELECT COUNT(*) FROM players_height_normalized v LEFT JOIN Player p ON v.id = p.id WHERE p.id IS NULL OR NOT (p.birthday >= '1990-01-01 00:00:00' AND p.birthday < '1996-01-01 00:00:00')",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "height_numeric equals CAST(height AS REAL) when source height is non-NULL and not empty (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM players_height_normalized v JOIN Player p ON v.id = p.id WHERE NOT (p.height IS NULL) AND trim(CAST(p.height AS TEXT)) <> '' AND (v.height_numeric IS NULL OR abs(v.height_numeric - CAST(p.height AS REAL)) > 1e-9)",
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
  pc.id AS id,
  CASE
    WHEN pc.height IS NULL THEN NULL
    WHEN trim(pc.height) = '' THEN NULL
    ELSE CAST(pc.height AS REAL)
  END AS height_numeric
FROM players_cohort pc
```

---

## Skill `cohort_average_height`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | — (scalar) |
| status / version | active / v1 |
| skill id | sk_4efe34eece9406a2 |
| output columns | `sum_height`, `count_players` |
| source tables | — |
| depends_on (builds on) | `players_height_normalized` |
| depended-on by (builds on this) | — |

### Description

Compute aggregate measures SUM(height_numeric) and COUNT(id) across the normalized cohort rows (one row per cohort summary). Do not collapse player-level grain until this aggregation. Final average will be DIVIDE(SUM, COUNT).

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
      "want_name": "cohort_average_height",
      "category": "AGG",
      "required_outputs": [
        "sum_height",
        "count_players"
      ],
      "required_grain": [
        "cohort"
      ],
      "required_filters": {},
      "text": "Compute aggregate measures SUM(height_numeric) and COUNT(id) across the normalized cohort rows (one row per cohort summary). Do not collapse player-level grain until this aggregation. Final average will be DIVIDE(SUM, COUNT).",
      "source_tables": [],
      "depends_on": [
        "players_height_normalized"
      ],
      "join_keys": [],
      "relationship": "aggregate_input",
      "may_read_base_tables": false,
      "holistic": false,
      "inherited_filters": {
        "birthday": ">= '1990-01-01 00:00:00' AND < '1996-01-01 00:00:00'"
      }
    },
    "inherited_filters": {
      "birthday": ">=1990-01-01 00:00:00;<1996-01-01 00:00:00"
    },
    "contract_version": 2,
    "grain_basis": "scalar_aggregate",
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
    "rewrite": "Task: Compute the average height of players whose birthday is on or after 1990-01-01 00:00:00 and before 1996-01-01 00:00:00, using average height = DIVIDE(SUM(height), COUNT(id)).\nRequired outputs: average_height (a single numeric value computed as DIVIDE(SUM(height), COUNT(id)))\nFilters: birthday >= '1990-01-01 00:00:00'; birthday < '1996-01-01 00:00:00'",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:13:39+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:13:43+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "sum_height",
      "count_players"
    ],
    "row_count": 1,
    "grain_check": "pass",
    "filter_checks": {
      "birthday": "n/a"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No NULL keys in the normalized rows that are being aggregated (each source row must have a non-NULL id)",
        "sql": "SELECT COUNT(*) FROM players_height_normalized WHERE id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows contributing to the aggregation satisfy the intrinsic birthday filter (birthday between 1990-01-01 inclusive and 1996-01-01 exclusive)",
        "sql": "SELECT COUNT(*) FROM players_height_normalized WHERE NOT (birthday >= '1990-01-01 00:00:00' AND birthday < '1996-01-01 00:00:00')",
        "result": "inconclusive",
        "violations": null,
        "error": "OperationalError: no such column: birthday"
      },
      {
        "purpose": "SUM(height_numeric) and COUNT(id) in the view match recomputing aggregates directly from the Player base table after applying normalization and filters (detects if the view collapsed player-level grai",
        "sql": "SELECT CASE WHEN v.sum_height IS NULL AND p.sum_height IS NULL AND v.count_players IS NULL AND p.count_players IS NULL THEN 0 WHEN v.sum_height = p.sum_height AND v.count_players = p.count_players THEN 0 ELSE 1 END FROM (SELECT SUM(height_numeric) AS sum_height, COUNT(id) AS count_players FROM players_height_normalized) v CROSS JOIN (SELECT SUM(height) AS sum_height, COUNT(id) AS count_players FROM Player WHERE birthday >= '1990-01-01 00:00:00' AND birthday < '1996-01-01 00:00:00') p",
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
  SUM(height_numeric) AS sum_height,
  COUNT(id) AS count_players
FROM players_height_normalized
```

---

## Skill `players_in_birth_range`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_653c0946efc8140e |
| output columns | `player_id`, `birthday`, `preferred_foot` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `left_foot_flag` |

### Description

Select the cohort of players whose birthday is between 1987-01-01 00:00:00 and 1992-12-31 00:00:00 (inclusive). Keep each player as one row with their preferred_foot and birthday.

### Semantic filters

```json
{
  "birthday": ">=1987-01-01 00:00:00;<=1992-12-31 00:00:00"
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
      "want_name": "players_in_birth_range",
      "category": "SEL",
      "required_outputs": [
        "player_id",
        "birthday",
        "preferred_foot"
      ],
      "required_grain": [
        "player_id"
      ],
      "required_filters": {
        "birthday": "BETWEEN '1987-01-01 00:00:00' AND '1992-12-31 00:00:00'"
      },
      "text": "Select the cohort of players whose birthday is between 1987-01-01 00:00:00 and 1992-12-31 00:00:00 (inclusive). Keep each player as one row with their preferred_foot and birthday.",
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
    "question_id": "bird_dev_1037",
    "question": "Calculate the percentage of players who prefer left foot, who were born between 1987 and 1992.",
    "rewrite": "Task: Compute the percentage of players whose preferred_foot = 'left' among all players born between 1987-01-01 00:00:00 and 1992-12-31 00:00:00.\nRequired outputs: percentage_left: a numeric value equal to 100 * (number of players with preferred_foot = 'left' and birthday BETWEEN '1987-01-01 00:00:00' AND '1992-12-31 00:00:00') / (total number of players with birthday BETWEEN '1987-01-01 00:00:00' AND '1992-12-31 00:00:00')\nFilters: birthday BETWEEN '1987-01-01 00:00:00' AND '1992-12-31 00:00:00'; preferred_foot = 'left' (applies only to the numerator; denominator includes all preferred_foot values for the same birthday range)",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:15:02+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:15:05+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "birthday",
      "preferred_foot"
    ],
    "row_count": 4285,
    "grain_check": "pass",
    "filter_checks": {
      "birthday": "pass"
    },
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
        "purpose": "No duplicate player_id rows (view should be keyed by player_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_id, COUNT(*) AS c FROM players_in_birth_range GROUP BY player_id HAVING c > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All birthdays in the view fall within the inclusive range 1987-01-01 00:00:00 to 1992-12-31 00:00:00",
        "sql": "SELECT COUNT(*) FROM players_in_birth_range WHERE NOT (birthday >= '1987-01-01 00:00:00' AND birthday <= '1992-12-31 00:00:00')",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every player_id in the view exists in the Player table and birthday matches Player.birthday (detects incorrect joins or mismatched rows)",
        "sql": "SELECT COUNT(*) FROM players_in_birth_range v LEFT JOIN Player p ON v.player_id = p.player_api_id WHERE p.player_api_id IS NULL OR (v.birthday IS NOT p.birthday AND NOT (v.birthday IS NULL AND p.birthday IS NULL))",
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
  Player.player_api_id AS player_id,
  Player.birthday AS birthday,
  Player_Attributes.preferred_foot AS preferred_foot
FROM Player
LEFT JOIN Player_Attributes
  ON Player.player_api_id = Player_Attributes.player_api_id
WHERE Player.birthday BETWEEN '1987-01-01 00:00:00' AND '1992-12-31 00:00:00'
GROUP BY Player.player_api_id
```

---

## Skill `left_foot_flag`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `player_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_96b46a8e356e0fd2 |
| output columns | `player_id`, `birthday`, `preferred_foot`, `is_left` |
| source tables | — |
| depends_on (builds on) | `players_in_birth_range` |
| depended-on by (builds on this) | `percentage_left_in_cohort` |

### Description

Normalize/canonicalize preferred_foot into a flag indicating whether the player's preferred_foot is 'left'. Operates on the cohort from players_in_birth_range.

### Semantic filters

```json
{
  "birthday": ">=1987-01-01 00:00:00;<=1992-12-31 00:00:00"
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
      "want_name": "left_foot_flag",
      "category": "NORM",
      "required_outputs": [
        "player_id",
        "birthday",
        "preferred_foot",
        "is_left"
      ],
      "required_grain": [
        "player_id"
      ],
      "required_filters": {},
      "text": "Normalize/canonicalize preferred_foot into a flag indicating whether the player's preferred_foot is 'left'. Operates on the cohort from players_in_birth_range.",
      "source_tables": [],
      "depends_on": [
        "players_in_birth_range"
      ],
      "join_keys": [
        "player_id"
      ],
      "relationship": "one_to_one",
      "may_read_base_tables": false,
      "holistic": false,
      "inherited_filters": {
        "birthday": "BETWEEN '1987-01-01 00:00:00' AND '1992-12-31 00:00:00'"
      }
    },
    "inherited_filters": {
      "birthday": ">=1987-01-01 00:00:00;<=1992-12-31 00:00:00"
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
    "question_id": "bird_dev_1037",
    "question": "Calculate the percentage of players who prefer left foot, who were born between 1987 and 1992.",
    "rewrite": "Task: Compute the percentage of players whose preferred_foot = 'left' among all players born between 1987-01-01 00:00:00 and 1992-12-31 00:00:00.\nRequired outputs: percentage_left: a numeric value equal to 100 * (number of players with preferred_foot = 'left' and birthday BETWEEN '1987-01-01 00:00:00' AND '1992-12-31 00:00:00') / (total number of players with birthday BETWEEN '1987-01-01 00:00:00' AND '1992-12-31 00:00:00')\nFilters: birthday BETWEEN '1987-01-01 00:00:00' AND '1992-12-31 00:00:00'; preferred_foot = 'left' (applies only to the numerator; denominator includes all preferred_foot values for the same birthday range)",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:15:06+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:15:09+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "birthday",
      "preferred_foot",
      "is_left"
    ],
    "row_count": 4285,
    "grain_check": "pass",
    "filter_checks": {
      "birthday": "pass"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View grain: no duplicate player_id rows (each player_id appears at most once)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_id, COUNT(*) AS cnt FROM left_foot_flag GROUP BY player_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Intrinsic filter: all rows are within the birthday range 1987-01-01 .. 1992-12-31",
        "sql": "SELECT COUNT(*) FROM left_foot_flag WHERE NOT (birthday >= '1987-01-01 00:00:00' AND birthday <= '1992-12-31 00:00:00')",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "is_left correctness: is_left = 1 exactly when lower(preferred_foot) = 'left' (and 0 otherwise)",
        "sql": "SELECT COUNT(*) FROM left_foot_flag WHERE (CASE WHEN lower(preferred_foot) = 'left' THEN 1 ELSE 0 END) != is_left",
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
  player_id,
  birthday,
  preferred_foot,
  CASE
    WHEN lower(preferred_foot) = 'left' THEN 1
    ELSE 0
  END AS is_left
FROM players_in_birth_range
```

---

## Skill `percentage_left_in_cohort`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `cohort` (keyed) |
| status / version | active / v1 |
| skill id | sk_8c123459639be71a |
| output columns | `cohort`, `count_left`, `count_total`, `percentage_left` |
| source tables | — |
| depends_on (builds on) | `left_foot_flag` |
| depended-on by (builds on this) | — |

### Description

Compute counts within the birth-range cohort and produce the percentage of players whose is_left flag is true: 100 * (count_left / count_total).

### Semantic filters

```json
{
  "birthday": ">=1987-01-01 00:00:00;<=1992-12-31 00:00:00"
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
      "want_name": "percentage_left_in_cohort",
      "category": "AGG",
      "required_outputs": [
        "count_left",
        "count_total",
        "percentage_left"
      ],
      "required_grain": [
        "cohort"
      ],
      "required_filters": {},
      "text": "Compute counts within the birth-range cohort and produce the percentage of players whose is_left flag is true: 100 * (count_left / count_total).",
      "source_tables": [],
      "depends_on": [
        "left_foot_flag"
      ],
      "join_keys": [],
      "relationship": "aggregate_input",
      "may_read_base_tables": false,
      "holistic": false,
      "inherited_filters": {
        "birthday": "BETWEEN '1987-01-01 00:00:00' AND '1992-12-31 00:00:00'"
      }
    },
    "inherited_filters": {
      "birthday": ">=1987-01-01 00:00:00;<=1992-12-31 00:00:00"
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
    "question_id": "bird_dev_1037",
    "question": "Calculate the percentage of players who prefer left foot, who were born between 1987 and 1992.",
    "rewrite": "Task: Compute the percentage of players whose preferred_foot = 'left' among all players born between 1987-01-01 00:00:00 and 1992-12-31 00:00:00.\nRequired outputs: percentage_left: a numeric value equal to 100 * (number of players with preferred_foot = 'left' and birthday BETWEEN '1987-01-01 00:00:00' AND '1992-12-31 00:00:00') / (total number of players with birthday BETWEEN '1987-01-01 00:00:00' AND '1992-12-31 00:00:00')\nFilters: birthday BETWEEN '1987-01-01 00:00:00' AND '1992-12-31 00:00:00'; preferred_foot = 'left' (applies only to the numerator; denominator includes all preferred_foot values for the same birthday range)",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:15:10+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:15:15+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "cohort",
      "count_left",
      "count_total",
      "percentage_left"
    ],
    "row_count": 6,
    "grain_check": "pass",
    "filter_checks": {
      "birthday": "n/a"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No NULL cohort keys (cohort is the view grain)",
        "sql": "SELECT COUNT(*) FROM percentage_left_in_cohort WHERE cohort IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Intrinsic filter: all rows correspond to players whose birthday is between 1987-01-01 and 1992-12-31 (view rows should only include players in the birth-range cohort)",
        "sql": "SELECT COUNT(*) FROM percentage_left_in_cohort v JOIN Player p ON date(strftime('%Y-01-01', p.birthday)) = v.cohort WHERE NOT (p.birthday >= '1987-01-01 00:00:00' AND p.birthday <= '1992-12-31 00:00:00')",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "percentage_left matches recomputed aggregate 100 * (sum(is_left) / count) from base table grouped by cohort",
        "sql": "SELECT COUNT(*) FROM percentage_left_in_cohort v LEFT JOIN (SELECT date(strftime('%Y-01-01', birthday)) AS cohort, 100.0 * SUM(CASE WHEN is_left = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(player_id),0) AS expected_pct FROM left_foot_flag WHERE birthday >= '1987-01-01 00:00:00' AND birthday <= '1992-12-31 00:00:00' GROUP BY cohort) b USING (cohort) WHERE (b.expected_pct IS NULL AND v.percentage_left IS NOT NULL) OR (b.expected_pct IS NOT NULL AND ABS(v.percentage_left - b.expected_pct) > 1e-6)",
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
  date(strftime('%Y-01-01', birthday)) AS cohort,
  SUM(CASE WHEN is_left = 1 THEN 1 ELSE 0 END) AS count_left,
  COUNT(player_id) AS count_total,
  100.0 * SUM(CASE WHEN is_left = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(player_id),0) AS percentage_left
FROM left_foot_flag
GROUP BY cohort
```

---

## Skill `league_total_goals_all_matches`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `league_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_a5684c4787d1c31f |
| output columns | `league_id`, `league_name`, `total_goals` |
| source tables | `League`, `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-league total goals aggregated across all matches, treating NULL goals as zero

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
    "question_id": "bird_dev_1038",
    "question": "List the top 5 leagues in ascending order of the number of goals made in all seasons combined.",
    "rewrite": "Task: Compute the top 5 leagues ranked by the total number of goals scored across all seasons, where total goals for a league = SUM(home_team_goal + away_team_goal) over all matches belonging to that league.\nRequired outputs: league_id or league name (identify the league); total_goals (integer): sum of home_team_goal and away_team_goal across all seasons for that league\nFilters: Include all matches for each league across all seasons (no additional date or season filtering).; Exclude matches with NULL values for home_team_goal or away_team_goal only if that prevents summation; otherwise treat NULL as 0 if the database semantics require explicit handling (i.e., total_goals must be the sum of available numeric goal values).\nSort/limit: Order results by total_goals in ascending order and return only the top 5 leagues with the smallest total_goals (LIMIT 5).",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:15:28+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:15:32+00:00",
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
        "purpose": "View has one row per league (no duplicate league_id, league_name pairs)",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, league_name, COUNT(*) AS cnt FROM league_total_goals_all_matches GROUP BY league_id, league_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "total_goals equals sum of (home + away) per league treating NULL as zero (recomputed from base tables)",
        "sql": "SELECT COUNT(*) FROM league_total_goals_all_matches v LEFT JOIN League L ON L.id = v.league_id WHERE v.total_goals != (SELECT COALESCE(SUM(COALESCE(M.home_team_goal,0) + COALESCE(M.away_team_goal,0)),0) FROM \"Match\" M WHERE M.league_id = v.league_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys league_id and league_name are not NULL and correspond to an existing League row",
        "sql": "SELECT COUNT(*) FROM league_total_goals_all_matches v WHERE v.league_id IS NULL OR v.league_name IS NULL OR NOT EXISTS (SELECT 1 FROM League L WHERE L.id = v.league_id AND L.name = v.league_name)",
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
SELECT L.id AS league_id, L.name AS league_name, COALESCE(SUM(COALESCE(M.home_team_goal, 0) + COALESCE(M.away_team_goal, 0)), 0) AS total_goals FROM League L LEFT JOIN "Match" M ON M.league_id = L.id GROUP BY L.id, L.name
```

---

## Skill `player_rows_sel`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_28adc41e9e369094 |
| output columns | `player_name`, `player_fifa_api_id`, `long_shots`, `player_id`, `player_attributes_id` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `player_long_shot_metrics_agg` |

### Description

Select all raw rows for the player with name 'Ahmed Samir Farag', keeping the original long_shots and player_fifa_api_id values. Exclude rows where both long_shots and player_fifa_api_id are NULL (but keep rows where one is NULL because sum/count exclude NULLs later).

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
      "text": "Select all raw rows for the player with name 'Ahmed Samir Farag', keeping the original long_shots and player_fifa_api_id values. Exclude rows where both long_shots and player_fifa_api_id are NULL (but keep rows where one is NULL because sum/count exclude NULLs later).",
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
    "rewrite": "Task: Compute the average number of long-shot values for the player named 'Ahmed Samir Farag' by dividing the sum of that player's long_shots by the count of that player's player_fifa_api_id entries.\nRequired outputs: average_long_shot (numeric): sum(long_shots for Ahmed Samir Farag) divided by count(player_fifa_api_id for Ahmed Samir Farag)\nFilters: player_name = 'Ahmed Samir Farag'; include all rows/records for that player when summing long_shots and counting player_fifa_api_id; exclude NULL long_shots from the sum and exclude NULL player_fifa_api_id from the count",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:16:00+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:16:04+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_name",
      "player_fifa_api_id",
      "long_shots",
      "player_id",
      "player_attributes_id"
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
        "purpose": "View respects intrinsic filter: all rows must have player_name = 'Ahmed Samir Farag'",
        "sql": "SELECT COUNT(*) FROM player_rows_sel WHERE player_name IS NULL OR player_name <> 'Ahmed Samir Farag'",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Grain uniqueness: player_attributes_id is the key so there must be no duplicate player_attributes_id rows",
        "sql": "SELECT COUNT(*) FROM (SELECT player_attributes_id, COUNT(*) AS cnt FROM player_rows_sel GROUP BY player_attributes_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Intrinsic exclusion: view must not include rows where both long_shots and player_fifa_api_id are NULL",
        "sql": "SELECT COUNT(*) FROM player_rows_sel WHERE long_shots IS NULL AND player_fifa_api_id IS NULL",
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
  p.player_name AS player_name,
  pa.player_fifa_api_id AS player_fifa_api_id,
  pa.long_shots AS long_shots,
  p.id AS player_id,
  pa.id AS player_attributes_id
FROM Player p
LEFT JOIN Player_Attributes pa
  ON pa.player_api_id = p.player_api_id
WHERE p.player_name = 'Ahmed Samir Farag'
  AND NOT (pa.long_shots IS NULL AND pa.player_fifa_api_id IS NULL)
```

---

## Skill `player_long_shot_metrics_agg`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_e14b92546b04d0f4 |
| output columns | `player_name`, `sum_long_shots`, `count_player_fifa_api_id`, `player_id`, `player_attributes_id` |
| source tables | — |
| depends_on (builds on) | `player_rows_sel` |
| depended-on by (builds on this) | `average_long_shot_calc` |

### Description

Aggregate the selected player rows to produce the sum of non-NULL long_shots and the count of non-NULL player_fifa_api_id for that player. One row per player (player_name).

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
      "want_name": "player_long_shot_metrics_agg",
      "category": "AGG",
      "required_outputs": [
        "player_name",
        "sum_long_shots",
        "count_player_fifa_api_id"
      ],
      "required_grain": [
        "player_name"
      ],
      "required_filters": {},
      "text": "Aggregate the selected player rows to produce the sum of non-NULL long_shots and the count of non-NULL player_fifa_api_id for that player. One row per player (player_name).",
      "source_tables": [],
      "depends_on": [
        "player_rows_sel"
      ],
      "join_keys": [],
      "relationship": "aggregate_input",
      "may_read_base_tables": false,
      "holistic": false,
      "inherited_filters": {
        "player_name": "equals 'Ahmed Samir Farag'"
      }
    },
    "inherited_filters": {
      "player_name": "Ahmed Samir Farag"
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
    "question_id": "bird_dev_1039",
    "question": "Find the average number of long-shot done by Ahmed Samir Farag.",
    "rewrite": "Task: Compute the average number of long-shot values for the player named 'Ahmed Samir Farag' by dividing the sum of that player's long_shots by the count of that player's player_fifa_api_id entries.\nRequired outputs: average_long_shot (numeric): sum(long_shots for Ahmed Samir Farag) divided by count(player_fifa_api_id for Ahmed Samir Farag)\nFilters: player_name = 'Ahmed Samir Farag'; include all rows/records for that player when summing long_shots and counting player_fifa_api_id; exclude NULL long_shots from the sum and exclude NULL player_fifa_api_id from the count",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:16:05+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:16:07+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_name",
      "sum_long_shots",
      "count_player_fifa_api_id",
      "player_id",
      "player_attributes_id"
    ],
    "row_count": 1,
    "grain_check": "pass",
    "filter_checks": {
      "player_name": "pass"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View should contain exactly one row per player_name (no duplicate player_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_name FROM player_long_shot_metrics_agg GROUP BY player_name HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "sum_long_shots must equal SUM(long_shots) over the selected rows (rows in player_rows_sel) for that player_name, treating NULLs correctly",
        "sql": "SELECT COUNT(*) FROM player_long_shot_metrics_agg AS v WHERE v.sum_long_shots IS NOT (SELECT SUM(prs.long_shots) FROM player_rows_sel prs WHERE prs.player_name = v.player_name)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "count_player_fifa_api_id must equal COUNT(player_fifa_api_id) over the selected rows (non-NULL) for that player_name",
        "sql": "SELECT COUNT(*) FROM player_long_shot_metrics_agg AS v WHERE v.count_player_fifa_api_id IS NOT (SELECT COUNT(prs.player_fifa_api_id) FROM player_rows_sel prs WHERE prs.player_name = v.player_name)",
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
  prs.player_name AS player_name,
  SUM(prs.long_shots) AS sum_long_shots,
  COUNT(prs.player_fifa_api_id) AS count_player_fifa_api_id,
  NULL AS player_id,
  NULL AS player_attributes_id
FROM player_rows_sel prs
GROUP BY prs.player_name
```

---

## Skill `average_long_shot_calc`

Category: `SEM`

| field | value |
|---|---|
| grain (one row per) | `player_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_97c562ad905b4141 |
| output columns | `player_name`, `average_long_shot` |
| source tables | — |
| depends_on (builds on) | `player_long_shot_metrics_agg` |
| depended-on by (builds on this) | — |

### Description

Compute the average_long_shot as sum_long_shots divided by count_player_fifa_api_id for the player. Preserve numeric semantics; handle division-by-zero by producing NULL or appropriate DB-specific behavior.

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
      "want_name": "average_long_shot_calc",
      "category": "SEM",
      "required_outputs": [
        "player_name",
        "average_long_shot"
      ],
      "required_grain": [
        "player_name"
      ],
      "required_filters": {},
      "text": "Compute the average_long_shot as sum_long_shots divided by count_player_fifa_api_id for the player. Preserve numeric semantics; handle division-by-zero by producing NULL or appropriate DB-specific behavior.",
      "source_tables": [],
      "depends_on": [
        "player_long_shot_metrics_agg"
      ],
      "join_keys": [],
      "relationship": "one_to_one",
      "may_read_base_tables": false,
      "holistic": false,
      "inherited_filters": {
        "player_name": "equals 'Ahmed Samir Farag'"
      }
    },
    "inherited_filters": {
      "player_name": "Ahmed Samir Farag"
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
    "rewrite": "Task: Compute the average number of long-shot values for the player named 'Ahmed Samir Farag' by dividing the sum of that player's long_shots by the count of that player's player_fifa_api_id entries.\nRequired outputs: average_long_shot (numeric): sum(long_shots for Ahmed Samir Farag) divided by count(player_fifa_api_id for Ahmed Samir Farag)\nFilters: player_name = 'Ahmed Samir Farag'; include all rows/records for that player when summing long_shots and counting player_fifa_api_id; exclude NULL long_shots from the sum and exclude NULL player_fifa_api_id from the count",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:16:08+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:16:12+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_name",
      "average_long_shot"
    ],
    "row_count": 1,
    "grain_check": "pass",
    "filter_checks": {
      "player_name": "pass"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View contains only the filtered player_name 'Ahmed Samir Farag' (intrinsic filter)",
        "sql": "SELECT COUNT(*) FROM average_long_shot_calc WHERE player_name IS NULL OR player_name <> 'Ahmed Samir Farag'",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "average_long_shot is NULL when count_player_fifa_api_id = 0, otherwise equals sum_long_shots / count_player_fifa_api_id (numeric semantics & division-by-zero handling). Compares view to recomputation ",
        "sql": "SELECT COUNT(*) FROM average_long_shot_calc v JOIN player_long_shot_metrics_agg s USING(player_name) WHERE (s.count_player_fifa_api_id = 0 AND v.average_long_shot IS NOT NULL) OR (s.count_player_fifa_api_id <> 0 AND (v.average_long_shot IS NULL OR ABS(v.average_long_shot - (CAST(s.sum_long_shots AS REAL) / s.count_player_fifa_api_id)) > 1e-9))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "player_name is not NULL (key not NULL)",
        "sql": "SELECT COUNT(*) FROM average_long_shot_calc WHERE player_name IS NULL",
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
  player_name,
  CASE
    WHEN count_player_fifa_api_id = 0 THEN NULL
    ELSE CAST(sum_long_shots AS REAL) / count_player_fifa_api_id
  END AS average_long_shot
FROM player_long_shot_metrics_agg
```

---

## Skill `player_long_shot_metrics_agg_17`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_name`, `player_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_6c9313de635cf6f1 |
| output columns | `player_name`, `sum_long_shots`, `count_player_fifa_api_id`, `player_id` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player aggregation that computes the sum of non-NULL long_shots and the count of non-NULL player_fifa_api_id across Player_Attributes rows joined to Player

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
    "question_id": "bird_dev_1039",
    "question": "Find the average number of long-shot done by Ahmed Samir Farag.",
    "rewrite": "Task: Compute the average number of long-shot values for the player named 'Ahmed Samir Farag' by dividing the sum of that player's long_shots by the count of that player's player_fifa_api_id entries.\nRequired outputs: average_long_shot (numeric): sum(long_shots for Ahmed Samir Farag) divided by count(player_fifa_api_id for Ahmed Samir Farag)\nFilters: player_name = 'Ahmed Samir Farag'; include all rows/records for that player when summing long_shots and counting player_fifa_api_id; exclude NULL long_shots from the sum and exclude NULL player_fifa_api_id from the count",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:16:15+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-09-30T15:16:20+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_name",
      "sum_long_shots",
      "count_player_fifa_api_id",
      "player_id"
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
        "purpose": "View has no duplicate rows for its declared grain (player_name, player_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_name, player_id, COUNT(*) AS cnt FROM player_long_shot_metrics_agg_17 GROUP BY player_name, player_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "sum_long_shots equals SUM of pa.long_shots over joined Player_Attributes rows (treating NULLs as not contributing) for each player",
        "sql": "SELECT COUNT(*) FROM (SELECT v.player_id FROM player_long_shot_metrics_agg_17 v LEFT JOIN Player p ON p.id = v.player_id LEFT JOIN Player_Attributes pa ON pa.player_api_id = p.player_api_id GROUP BY v.player_id HAVING v.sum_long_shots IS NULL AND SUM(pa.long_shots) IS NOT NULL OR v.sum_long_shots IS NOT NULL AND COALESCE(v.sum_long_shots,0) != COALESCE(SUM(pa.long_shots),0))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "count_player_fifa_api_id equals count of non-NULL pa.player_fifa_api_id rows joined to the player",
        "sql": "SELECT COUNT(*) FROM (SELECT v.player_id FROM player_long_shot_metrics_agg_17 v LEFT JOIN Player p ON p.id = v.player_id LEFT JOIN Player_Attributes pa ON pa.player_api_id = p.player_api_id GROUP BY v.player_id HAVING v.count_player_fifa_api_id IS NULL AND COUNT(pa.player_fifa_api_id) IS NOT NULL OR v.count_player_fifa_api_id IS NOT NULL AND v.count_player_fifa_api_id != COUNT(pa.player_fifa_api_id))",
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
SELECT p.player_name AS player_name, SUM(pa.long_shots) AS sum_long_shots, COUNT(pa.player_fifa_api_id) AS count_player_fifa_api_id, p.id AS player_id FROM Player p LEFT JOIN Player_Attributes pa ON pa.player_api_id = p.player_api_id WHERE NOT (pa.long_shots IS NULL AND pa.player_fifa_api_id IS NULL) GROUP BY p.player_name, p.id
```

---
