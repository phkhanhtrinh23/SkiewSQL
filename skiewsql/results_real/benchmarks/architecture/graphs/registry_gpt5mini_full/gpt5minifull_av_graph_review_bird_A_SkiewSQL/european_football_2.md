# Skill graph — `european_football_2` (21 skills)

## Skill `player_min_potential`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `id` (keyed) |
| status / version | active / v1 |
| skill id | sk_23e8065a1dd215cb |
| output columns | `id`, `player_fifa_api_id`, `player_api_id`, `date`, `overall_rating`, `potential`, `preferred_foot`, `attacking_work_rate`, `defensive_work_rate`, `crossing`, `finishing`, `heading_accuracy`, `short_passing`, `volleys`, `dribbling`, `curve`, `free_kick_accuracy`, `long_passing`, `ball_control`, `acceleration`, `sprint_speed`, `agility`, `reactions`, `balance`, `shot_power`, `jumping`, `stamina`, `strength`, `long_shots`, `aggression`, `interceptions`, `positioning`, `vision`, `penalties`, `marking`, `standing_tackle`, `sliding_tackle`, `gk_diving`, `gk_handling`, `gk_kicking`, `gk_positioning`, `gk_reflexes` |
| source tables | `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Relation of players whose potential equals the minimum potential across all players (returns player attributes for those with global min potential).

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
    "grain_basis": "verified_unique",
    "lineage": [
      "Player_Attributes"
    ],
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {
      "player_attributes": "183978:183978"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1022",
    "question": "What is the preferred foot when attacking of the player with the lowest potential?",
    "rewrite": "Task: Find the preferred_foot value for the player(s) whose potential is equal to the minimum potential across all players.\nRequired outputs: preferred_foot\nFilters: potential = MIN(potential) across all rows",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T05:54:46+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T05:54:49+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "id",
      "player_fifa_api_id",
      "player_api_id",
      "date",
      "overall_rating",
      "potential",
      "preferred_foot",
      "attacking_work_rate",
      "defensive_work_rate",
      "crossing",
      "finishing",
      "heading_accuracy",
      "short_passing",
      "volleys",
      "dribbling",
      "curve",
      "free_kick_accuracy",
      "long_passing",
      "ball_control",
      "acceleration",
      "sprint_speed",
      "agility",
      "reactions",
      "balance",
      "shot_power",
      "jumping",
      "stamina",
      "strength",
      "long_shots",
      "aggression",
      "interceptions",
      "positioning",
      "vision",
      "penalties",
      "marking",
      "standing_tackle",
      "sliding_tackle",
      "gk_diving",
      "gk_handling",
      "gk_kicking",
      "gk_positioning",
      "gk_reflexes"
    ],
    "row_count": 2,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows for the declared grain 'id' (each id appears at most once in the view).",
        "sql": "SELECT COUNT(*) FROM (SELECT id, COUNT(*) AS cnt FROM player_min_potential GROUP BY id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view has potential equal to the global minimum potential in the base table Player_Attributes.",
        "sql": "SELECT COUNT(*) FROM player_min_potential v WHERE v.potential <> (SELECT MIN(potential) FROM Player_Attributes) OR v.potential IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "The view did not introduce rows whose id does not exist in the base table Player_Attributes (every id in view must exist in base).",
        "sql": "SELECT COUNT(*) FROM player_min_potential v WHERE NOT EXISTS (SELECT 1 FROM Player_Attributes p WHERE p.id = v.id)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 2
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT *
FROM Player_Attributes
WHERE potential = (SELECT MIN(potential) FROM Player_Attributes)
```

---

## Skill `player_max_crossing`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_4f02a960f65e1c25 |
| output columns | `player_id`, `crossing` |
| source tables | `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player maximum crossing attribute value across all entries in Player_Attributes, useful for ranking players by their best observed crossing ability.

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
      "Player_Attributes"
    ],
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1024",
    "question": "Who are the top 5 players who perform better in crossing actions? Indicate their player id.",
    "rewrite": "Task: Find the top 5 players (by player id) who have the highest value of crossing, where 'perform better in crossing actions' is defined as the maximum crossing value.\nRequired outputs: player id; crossing (the crossing value used to rank players)\nFilters: consider all players in the dataset (no other row filters)\nSort/limit: order by crossing descending, limit 5",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T05:55:15+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T05:55:18+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "crossing"
    ],
    "row_count": 11060,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate player_id rows in the view (view grain is player_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_id FROM player_max_crossing GROUP BY player_id HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each view row's crossing equals the MAX(crossing) computed from Player_Attributes for that player_id",
        "sql": "SELECT COUNT(*) FROM player_max_crossing v LEFT JOIN (SELECT player_api_id AS player_id, MAX(crossing) AS expected_crossing FROM Player_Attributes GROUP BY player_api_id) b ON v.player_id = b.player_id WHERE (b.expected_crossing IS NULL AND v.crossing IS NOT NULL) OR (b.expected_crossing IS NOT NULL AND v.crossing IS NULL) OR (b.expected_crossing IS NOT NULL AND v.crossing <> b.expected_crossing)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every player_id in the view exists in Player_Attributes (no dangling keys)",
        "sql": "SELECT COUNT(*) FROM player_max_crossing v WHERE NOT EXISTS (SELECT 1 FROM Player_Attributes p WHERE p.player_api_id = v.player_id)",
        "result": "inconclusive",
        "violations": null,
        "error": "timeout"
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 2,
    "selected": 1,
    "included": 1,
    "referenced": 1
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT player_api_id AS player_id, MAX(crossing) AS crossing FROM Player_Attributes GROUP BY player_api_id
```

---

## Skill `league_total_goals_per_season`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `league_name`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_f7bd19413ca2cc6b |
| output columns | `league_id`, `league_name`, `season`, `total_goals` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-league total goals in a season computed as the sum of home and away goals across all matches belonging to the league (one row per league per season).

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
    "rewrite": "Task: Find which league (i.e., the league identifier/name) had the highest total number of goals scored in all matches during the 2015/2016 season, where total goals for a league is computed as the sum across its matches of (home_team_goal + away_team_goal).\nRequired outputs: league (identifier or name as available in the schema); total_goals (the sum of home_team_goal + away_team_goal across all matches in that league for the specified season)\nFilters: season = '2015/2016'; only include matches that belong to a league (as per schema relationship between matches and leagues)\nSort/limit: order by total_goals DESC limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T05:55:47+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T05:55:50+00:00",
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
        "purpose": "View has one row per league_id, league_name, season (no duplicate keys).",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, league_name, season, COUNT(*) AS cnt FROM league_total_goals_per_season GROUP BY league_id, league_name, season HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "total_goals equals the sum of home + away goals aggregated from Match for that league and season.",
        "sql": "SELECT COUNT(*) FROM league_total_goals_per_season v LEFT JOIN (SELECT M.league_id AS league_id, M.season AS season, SUM(COALESCE(M.home_team_goal,0) + COALESCE(M.away_team_goal,0)) AS expected_total FROM Match M GROUP BY M.league_id, M.season) s ON v.league_id = s.league_id AND v.season = s.season WHERE (s.expected_total IS NULL AND v.total_goals IS NOT NULL) OR (s.expected_total IS NOT NULL AND (v.total_goals IS NULL OR v.total_goals != s.expected_total))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys league_id, league_name, season are not NULL in the view.",
        "sql": "SELECT COUNT(*) FROM league_total_goals_per_season WHERE league_id IS NULL OR league_name IS NULL OR season IS NULL",
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
SELECT L.id AS league_id, L.name AS league_name, M.season AS season, SUM(COALESCE(M.home_team_goal,0) + COALESCE(M.away_team_goal,0)) AS total_goals FROM Match M JOIN League L ON M.league_id = L.id GROUP BY L.id, L.name, M.season
```

---

## Skill `home_team_season_home_loss_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `season`, `home_team_api_id`, `home_team_long_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_ab963314ec3d5222 |
| output columns | `season`, `home_team_api_id`, `home_team_long_name`, `home_losses` |
| source tables | `Match`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Counts of home losses per home team for each season (number of matches where home_team_goal - away_team_goal < 0), keeping team identifiers for joins

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
    "rewrite": "Task: Find the home team (team name) that had the fewest number of losses in home matches during the 2015/2016 season, where a home loss is defined as home_team_goal - away_team_goal < 0.\nRequired outputs: home_team (the name/identifier of the home team); home_losses (the count of matches in that season where home_team_goal - away_team_goal < 0 for that home_team)\nFilters: season = '2015/2016'; consider only matches where home_team_goal - away_team_goal < 0 for counting a home loss\nSort/limit: order by home_losses asc limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T05:56:19+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T05:56:22+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "season",
      "home_team_api_id",
      "home_team_long_name",
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
        "purpose": "No duplicate rows at the view grain (season, home_team_api_id, home_team_long_name).",
        "sql": "SELECT COUNT(*) FROM home_team_season_home_loss_counts v WHERE (SELECT COUNT(*) FROM home_team_season_home_loss_counts v2 WHERE v2.season = v.season AND v2.home_team_api_id = v.home_team_api_id AND v2.home_team_long_name = v.home_team_long_name) > 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "home_losses equals the number of Match rows for that season/team where home_team_goal - away_team_goal < 0 (measure reconciles with base table).",
        "sql": "SELECT COUNT(*) FROM home_team_season_home_loss_counts v LEFT JOIN (SELECT m.season, m.home_team_api_id, t.team_long_name AS home_team_long_name, COUNT(m.id) AS expected_home_losses FROM \"Match\" m JOIN \"Team\" t ON m.home_team_api_id = t.team_api_id WHERE (m.home_team_goal - m.away_team_goal) < 0 GROUP BY m.season, m.home_team_api_id, t.team_long_name) b ON v.season = b.season AND v.home_team_api_id = b.home_team_api_id AND v.home_team_long_name = b.home_team_long_name WHERE (b.expected_home_losses IS NULL AND v.home_losses IS NOT NULL) OR (b.expected_home_losses IS NOT NULL AND v.home_losses != b.expected_home_losses)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys (season, home_team_api_id, home_team_long_name) are not NULL.",
        "sql": "SELECT COUNT(*) FROM home_team_season_home_loss_counts v WHERE v.season IS NULL OR v.home_team_api_id IS NULL OR v.home_team_long_name IS NULL",
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
SELECT m.season, m.home_team_api_id AS home_team_api_id, t.team_long_name AS home_team_long_name, COUNT(m.id) AS home_losses FROM "Match" m JOIN "Team" t ON m.home_team_api_id = t.team_api_id WHERE (m.home_team_goal - m.away_team_goal) < 0 GROUP BY m.season, m.home_team_api_id, t.team_long_name
```

---

## Skill `matches_per_league`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_8820ad3052b82165 |
| output columns | `league_id`, `match_count` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Total number of Match rows grouped by league (one row per league with league_id and match count), useful for ranking or filtering leagues by match volume.

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
    "rewrite": "Task: Find the league (League.name) that has the largest total number of matches (count of Match rows grouped by league_id) and return that league's name and the corresponding match count.\nRequired outputs: league_name: the League.name value for the league with the maximum total matches; match_count: an integer equal to the total number of Match rows that have that league's id\nFilters: Consider all Match rows (no additional WHERE conditions); group matches by Match.league_id; Count matches per league using COUNT(Match.*) or COUNT(*) for each league_id; Select the league_id whose count equals the maximum count across all leagues: COUNT(Match) = MAX(COUNT(Match) over each league); Join to League on League.id = Match.league_id to obtain League.name\nSort/limit: order results by match_count DESC and limit to 1 (return the single league with the highest match_count)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T05:58:33+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T05:58:35+00:00",
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
        "purpose": "View has one row per league_id (no duplicate league_id values)",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, COUNT(*) AS cnt FROM matches_per_league GROUP BY league_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "match_count equals actual number of Match rows per league_id",
        "sql": "SELECT COUNT(*) FROM matches_per_league v LEFT JOIN (SELECT league_id, COUNT(*) AS expected_count FROM \"Match\" GROUP BY league_id) b ON v.league_id = b.league_id WHERE b.expected_count IS NULL OR v.match_count <> b.expected_count",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "league_id (the key) is never NULL in the view",
        "sql": "SELECT COUNT(*) FROM matches_per_league WHERE league_id IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 1
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT m.league_id AS league_id, COUNT(*) AS match_count FROM Match m GROUP BY m.league_id
```

---

## Skill `league_total_goals`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `league_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_dba4767ea67c9e1b |
| output columns | `league_id`, `league_name`, `total_goals` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-league total goals aggregated across all matches by summing home and away goals for matches with non-null goal values and valid league ids.

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
      "ORDER BY total_goals ASC",
      "LIMIT 5"
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
    "question_id": "bird_dev_1038",
    "question": "List the top 5 leagues in ascending order of the number of goals made in all seasons combined.",
    "rewrite": "Task: Compute each league's total number of goals across all seasons by summing home_team_goal and away_team_goal for every match, then return the top 5 leagues with the smallest total goals (ascending order).\nRequired outputs: league (identifier/name as provided in the data); total_goals (integer) — the sum over all seasons of home_team_goal + away_team_goal for matches in that league\nFilters: Include all matches from all seasons (no season filtering).; Aggregate by league.; Exclude leagues with null or missing league identifier or where goal values are null in a way that prevents accurate summation (only include matches with non-null numeric home_team_goal and away_team_goal).\nSort/limit: Order by total_goals ASC (ascending). Limit to 5 rows.",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:00:52+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T06:00:55+00:00",
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
        "purpose": "No NULL keys: league_id or league_name should never be NULL in the view",
        "sql": "SELECT COUNT(*) FROM league_total_goals WHERE league_id IS NULL OR league_name IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Aggregation correctness: total_goals equals sum of home_team_goal+away_team_goal from Match for matches with non-null goals and matching league",
        "sql": "SELECT COUNT(*) FROM league_total_goals LTG LEFT JOIN (SELECT M.league_id AS league_id, SUM(M.home_team_goal + M.away_team_goal) AS expected_total FROM Match M JOIN League L ON M.league_id = L.id WHERE M.home_team_goal IS NOT NULL AND M.away_team_goal IS NOT NULL AND L.id IS NOT NULL GROUP BY M.league_id) AS S ON LTG.league_id = S.league_id WHERE (S.expected_total IS NULL AND (LTG.total_goals IS NOT NULL AND LTG.total_goals<>0)) OR (S.expected_total IS NOT NULL AND (LTG.total_goals IS NULL OR LTG.total_goals<>S.expected_total))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No duplicate grains: there should be at most one row per (league_id, league_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, league_name, COUNT(*) AS cnt FROM league_total_goals GROUP BY league_id, league_name HAVING cnt>1)",
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
SELECT L.id AS league_id, L.name AS league_name, SUM(M.home_team_goal + M.away_team_goal) AS total_goals
FROM Match M
JOIN League L ON M.league_id = L.id
WHERE M.home_team_goal IS NOT NULL
  AND M.away_team_goal IS NOT NULL
  AND L.id IS NOT NULL
GROUP BY L.id, L.name
```

---

## Skill `player_average_heading_accuracy`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_fifa_api_id`, `player_name`, `height` (keyed) |
| status / version | active / v1 |
| skill id | sk_3896a6c44a9c123c |
| output columns | `player_fifa_api_id`, `player_name`, `height`, `average_heading_accuracy` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player average heading accuracy computed from Player_Attributes joined to Player, for players with any heading_accuracy records and including player identifiers and height for filtering/joins.

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
      "180",
      "10"
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
    "question_id": "bird_dev_1040",
    "question": "List the top 10 players' names whose heights are above 180 in descending order of average heading accuracy.",
    "rewrite": "Task: Return the top 10 players whose heights are greater than 180, ranked by their average heading accuracy in descending order; average heading accuracy is defined as SUM(heading_accuracy) divided by COUNT(player_fifa_api_id).\nRequired outputs: player_name; average_heading_accuracy (numeric computed as DIVIDE(SUM(heading_accuracy), COUNT(player_fifa_api_id)))\nFilters: height > 180; Include only players for whom heading_accuracy values exist (i.e., COUNT(player_fifa_api_id) > 0)\nSort/limit: ORDER BY average_heading_accuracy DESC LIMIT 10",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:01:25+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T06:01:29+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_fifa_api_id",
      "player_name",
      "height",
      "average_heading_accuracy"
    ],
    "row_count": 11060,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Player.player_fifa_api_id=Player_Attributes.player_fifa_api_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (player_fifa_api_id, player_name, height).",
        "sql": "SELECT COUNT(*) FROM (SELECT player_fifa_api_id, player_name, height, COUNT(*) AS cnt FROM player_average_heading_accuracy GROUP BY player_fifa_api_id, player_name, height HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "average_heading_accuracy matches recomputed average from Player_Attributes for each player (only consider rows where base has non-NULL heading_accuracy).",
        "sql": "SELECT COUNT(*) FROM player_average_heading_accuracy v LEFT JOIN (SELECT pa.player_fifa_api_id, AVG(pa.heading_accuracy * 1.0) AS recomputed_avg FROM Player_Attributes pa WHERE pa.heading_accuracy IS NOT NULL GROUP BY pa.player_fifa_api_id) r ON v.player_fifa_api_id = r.player_fifa_api_id WHERE (r.recomputed_avg IS NULL AND v.average_heading_accuracy IS NOT NULL) OR (r.recomputed_avg IS NOT NULL AND ABS(v.average_heading_accuracy - r.recomputed_avg) > 1e-6)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row corresponds to an existing Player and the join did not introduce NULL keys: player_fifa_api_id, player_name, height must be non-NULL and player must exist in Player.",
        "sql": "SELECT COUNT(*) FROM player_average_heading_accuracy v LEFT JOIN Player p ON v.player_fifa_api_id = p.player_fifa_api_id WHERE v.player_fifa_api_id IS NULL OR v.player_name IS NULL OR v.height IS NULL OR p.player_fifa_api_id IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 1,
    "selected": 1,
    "negative": 1,
    "negative_subgoals": [
      "Task: Compute Ariel Borysiuk's heading accuracy — the percentage (or fraction) of his headed attempts that were successful (i.e., headed shots/goals completed) as recorded in the dataset.\nRequired outputs: player_name: the player name (Ariel Borysiuk); heading_accuracy: a numeric value representing heading accuracy (percentage or fraction) as stored in the data, with units if applicable\nFilters: player_name = 'Ariel Borysiuk'; only consider records/statistics that measure heading accuracy or fields that represent headed attempts and successful headers (use the table/columns that represent heading accuracy or the numerator/denominator for headers)"
    ]
  }
}
```

### Validated on (0)

—

### Counter-examples (1)

- What's the heading accuracy of Ariel Borysiuk?

### Executable SQL body

```sql
SELECT p.player_fifa_api_id, p.player_name, p.height, SUM(pa.heading_accuracy) * 1.0 / COUNT(pa.player_fifa_api_id) AS average_heading_accuracy
FROM Player p
JOIN Player_Attributes pa
  ON p.player_fifa_api_id = pa.player_fifa_api_id
WHERE pa.heading_accuracy IS NOT NULL
GROUP BY p.player_fifa_api_id, p.player_name, p.height
```

---

## Skill `league_season_home_away_goal_averages`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `league_name`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_791eca05b7128166 |
| output columns | `league_id`, `league_name`, `season`, `avg_home_goals`, `avg_away_goals` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Average home and away goals per league per season (one row per league-season) to compare scoring rates by venue.

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
    "rewrite": "Task: Find all League.name values for leagues where, considering matches in the 2009/2010 season, the average of home_team_goal is greater than the average of away_team_goal.\nRequired outputs: League.name\nFilters: season = '2009/2010'; AVG(home_team_goal) > AVG(away_team_goal) computed over matches in the same league and season",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:02:07+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T06:02:11+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "league_id",
      "league_name",
      "season",
      "avg_home_goals",
      "avg_away_goals"
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
        "purpose": "No duplicate league-season rows (view grain is one row per league_id, league_name, season).",
        "sql": "SELECT COUNT(*) FROM league_season_home_away_goal_averages t WHERE (t.league_id, t.league_name, t.season) IN (SELECT league_id, league_name, season FROM league_season_home_away_goal_averages GROUP BY league_id, league_name, season HAVING COUNT(*)>1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "avg_home_goals matches AVG(home_team_goal) computed from Match for that league-season.",
        "sql": "SELECT COUNT(*) FROM league_season_home_away_goal_averages v LEFT JOIN (SELECT league_id, season, AVG(home_team_goal) AS exp_avg_home FROM \"Match\" GROUP BY league_id, season) m ON v.league_id = m.league_id AND v.season = m.season WHERE (m.exp_avg_home IS NULL AND v.avg_home_goals IS NOT NULL) OR (m.exp_avg_home IS NOT NULL AND ABS(v.avg_home_goals - m.exp_avg_home) > 1e-6)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "avg_away_goals matches AVG(away_team_goal) computed from Match for that league-season.",
        "sql": "SELECT COUNT(*) FROM league_season_home_away_goal_averages v LEFT JOIN (SELECT league_id, season, AVG(away_team_goal) AS exp_avg_away FROM \"Match\" GROUP BY league_id, season) m ON v.league_id = m.league_id AND v.season = m.season WHERE (m.exp_avg_away IS NULL AND v.avg_away_goals IS NOT NULL) OR (m.exp_avg_away IS NOT NULL AND ABS(v.avg_away_goals - m.exp_avg_away) > 1e-6)",
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
SELECT M.league_id, L.name AS league_name, M.season, AVG(M.home_team_goal) AS avg_home_goals, AVG(M.away_team_goal) AS avg_away_goals
FROM "Match" M
JOIN League L ON M.league_id = L.id
GROUP BY M.league_id, L.name, M.season
```

---

## Skill `team_chance_creation_passing_class`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `team_api_id`, `team_short_name`, `chanceCreationPassingClass` (keyed) |
| status / version | active / v1 |
| skill id | sk_50d70a80beb51707 |
| output columns | `team_api_id`, `team_short_name`, `chanceCreationPassingClass` |
| source tables | `Team`, `Team_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Mapping of teams to their chance creation passing classification from team attributes, usable to filter teams by their chanceCreationPassingClass

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
      "'Risky'"
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
    "question_id": "bird_dev_1053",
    "question": "List the football teams that has a chance creation passing class of Risky. Inidcate its short name only.",
    "rewrite": "Task: Return the short names of all football teams whose chance creation passing class is Risky.\nRequired outputs: team_short_name (short name of the team)\nFilters: chanceCreationPassingClass = 'Risky'",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:05:43+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T06:05:46+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "team_api_id",
      "team_short_name",
      "chanceCreationPassingClass"
    ],
    "row_count": 428,
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
        "purpose": "No duplicate rows at the declared grain (team_api_id, team_short_name, chanceCreationPassingClass).",
        "sql": "SELECT COUNT(*) FROM (SELECT team_api_id, team_short_name, chanceCreationPassingClass, COUNT(*) AS cnt FROM team_chance_creation_passing_class GROUP BY team_api_id, team_short_name, chanceCreationPassingClass HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view matches a join pair that actually exists in the base tables (no phantom rows).",
        "sql": "SELECT COUNT(*) FROM team_chance_creation_passing_class v LEFT JOIN Team t ON v.team_api_id = t.team_api_id LEFT JOIN Team_Attributes ta ON v.team_api_id = ta.team_api_id AND v.chanceCreationPassingClass = ta.chanceCreationPassingClass WHERE t.team_api_id IS NULL OR ta.team_api_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys from Team (team_api_id, team_short_name) are not NULL in the view.",
        "sql": "SELECT COUNT(*) FROM team_chance_creation_passing_class WHERE team_api_id IS NULL OR team_short_name IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 3,
    "selected": 1,
    "included": 1,
    "referenced": 1,
    "executed": 1,
    "inconclusive": 1,
    "positive": 1,
    "positive_subgoals": [
      "Task: Select the team short names for teams whose chanceCreationPassingClass is 'Safe'.\nRequired outputs: team_short_name\nFilters: chanceCreationPassingClass = 'Safe'"
    ],
    "last_used": "bird_dev_1130"
  }
}
```

### Validated on (1)

- What are the short name of team who played safe while creating chance of passing?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT DISTINCT t.team_api_id, t.team_short_name, ta.chanceCreationPassingClass
FROM Team t
JOIN Team_Attributes ta
  ON t.team_api_id = ta.team_api_id
```

---

## Skill `league_by_country`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `league_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_5f29d488f8b1d5c2 |
| output columns | `league_id`, `league_name`, `country_id`, `country_name` |
| source tables | `League`, `Country` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

All leagues with their associated country ids and country names to support queries that need leagues filtered or joined by country.

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
      "Netherlands"
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
    "question_id": "bird_dev_1056",
    "question": "What is the name of the football league in the country of Netherlands?",
    "rewrite": "Task: Find the name of the football league (League.name) that is located in the country with the name 'Netherlands'.\nRequired outputs: League.name\nFilters: Country.name = 'Netherlands'; League.country_id matches Country.id",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:06:40+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T06:06:42+00:00",
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
        "purpose": "No duplicate league_id in the view (ensures grain keyed by league_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, COUNT(*) AS cnt FROM league_by_country GROUP BY league_id HAVING cnt <> 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row's country_id matches an existing Country and the country_name matches that Country (checks join correctness)",
        "sql": "SELECT COUNT(*) FROM league_by_country v LEFT JOIN Country c ON v.country_id = c.id WHERE c.id IS NULL OR (v.country_name IS NOT NULL AND v.country_name <> c.name) OR (v.country_name IS NULL AND c.name IS NOT NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No NULL league_id or NULL country_id in the view (keys and required foreign key must be present)",
        "sql": "SELECT COUNT(*) FROM league_by_country WHERE league_id IS NULL OR country_id IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 1,
    "selected": 1,
    "negative": 1,
    "negative_subgoals": [
      "Task: Find the country associated with the league whose name is 'Italy Serie A'.\nRequired outputs: country (the country that the league 'Italy Serie A' is from)\nFilters: League.name = 'Italy Serie A'"
    ]
  }
}
```

### Validated on (0)

—

### Counter-examples (1)

- Which country is the league Italy Serie A from?

### Executable SQL body

```sql
SELECT League.id AS league_id, League.name AS league_name, League.country_id AS country_id, Country.name AS country_name
FROM League
JOIN Country ON League.country_id = Country.id
```

---

## Skill `player_min_height`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_42709196d019516d |
| output columns | `player_api_id`, `player_name`, `height` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-dataset relation listing player identifiers with the minimum non-null height value in the Player table (shortest players).

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
    "question_id": "bird_dev_1069",
    "question": "Which football player has the shortest height?",
    "rewrite": "Task: Find the football player record(s) whose height is the minimum height value (i.e., the shortest height) in the dataset.\nRequired outputs: player identifier (e.g., player name or id) as present in the schema; height\nFilters: height IS NOT NULL; height = MIN(height) over the entire table (i.e., equal to the smallest numeric height value present)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:12:41+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T06:12:43+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
      "player_name",
      "height"
    ],
    "row_count": 1,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No NULL keys: player_api_id must not be NULL in the view",
        "sql": "SELECT COUNT(*) FROM player_min_height WHERE player_api_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows correspond to players whose height equals the global non-NULL minimum height in Player",
        "sql": "SELECT COUNT(*) FROM player_min_height pmh WHERE pmh.height IS NULL OR pmh.height <> (SELECT MIN(height) FROM Player WHERE height IS NOT NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View rows are a subset of Player rows with matching player_api_id and player_name and height (no spurious rows or mismatched attributes)",
        "sql": "SELECT COUNT(*) FROM player_min_height pmh LEFT JOIN Player p ON p.player_api_id = pmh.player_api_id AND (p.height = pmh.height AND p.player_name = pmh.player_name) WHERE p.player_api_id IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 2
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT player_api_id, player_name, height FROM Player WHERE height IS NOT NULL AND height = (SELECT MIN(height) FROM Player WHERE height IS NOT NULL)
```

---

## Skill `team_home_goal_join`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `match_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_98fedc8a06bb4de8 |
| output columns | `team_api_id`, `team_short_name`, `match_api_id`, `home_team_api_id`, `home_team_goal` |
| source tables | `Team`, `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Join of teams to matches giving each team's short name with the corresponding match's home team goal and ids to allow filtering by goal or joining to match details

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
      "10"
    ],
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "Team",
      "Match"
    ],
    "table_fingerprints": {
      "team": "a19728cad815ec8a",
      "match": "a56b9117c06fb4c3"
    },
    "data_fingerprints": {
      "team": "299:51606",
      "match": "25979:25979"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1074",
    "question": "List all the short name of the football team that had a home team goal of 10?",
    "rewrite": "Task: Select the team_short_name values for all football teams whose home_team_goal equals 10.\nRequired outputs: team_short_name\nFilters: home_team_goal = 10",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:14:06+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T06:14:08+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "team_api_id",
      "team_short_name",
      "match_api_id",
      "home_team_api_id",
      "home_team_goal"
    ],
    "row_count": 25979,
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
        "purpose": "View rows must be keyed by match_api_id (no duplicate match_api_id in the view)",
        "sql": "SELECT COUNT(*) FROM (SELECT match_api_id, COUNT(*) AS cnt FROM team_home_goal_join GROUP BY match_api_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row's home_team_api_id and home_team_goal must match the Match table for the same match_api_id (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM team_home_goal_join v LEFT JOIN \"Match\" m ON v.match_api_id = m.match_api_id WHERE NOT (m.home_team_api_id IS v.home_team_api_id OR (m.home_team_api_id IS NULL AND v.home_team_api_id IS NULL)) OR NOT (m.home_team_goal IS v.home_team_goal OR (m.home_team_goal IS NULL AND v.home_team_goal IS NULL))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Join should not produce rows with NULL match_api_id (key not NULL)",
        "sql": "SELECT COUNT(*) FROM team_home_goal_join WHERE match_api_id IS NULL",
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
SELECT t.team_api_id, t.team_short_name, m.match_api_id, m.home_team_api_id, m.home_team_goal
FROM Team t
JOIN "Match" m ON m.home_team_api_id = t.team_api_id
```

---

## Skill `matches_per_league_season`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_1eb18233d0f9c145 |
| output columns | `league_id`, `season`, `match_count` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Count of matches per league for each season (one row per league-season with match count), usable to compare or rank leagues by match totals in a season.

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
    "rewrite": "Task: Find which league had the largest number of matches in the 2008/2009 season by returning the league identifier(s) with the maximum match count for that season.\nRequired outputs: league_id (the identifier of the league); match_count (the number of matches in that league during the 2008/2009 season)\nFilters: season = '2008/2009'; consider only matches that are counted toward a league's match total (no additional match-type filtering specified)\nSort/limit: order by match_count DESC limit 1 (return the league(s) with the maximum match_count for the specified season)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:22:38+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T06:22:40+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "league_id",
      "season",
      "match_count"
    ],
    "row_count": 88,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View has one row per league_id+season (no duplicate league-season keys)",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, season, COUNT(*) AS cnt FROM matches_per_league_season GROUP BY league_id, season HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "match_count equals the number of Match rows for that league_id and season (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM matches_per_league_season v LEFT JOIN (SELECT league_id, season, COUNT(*) AS expected_count FROM \"Match\" GROUP BY league_id, season) b ON v.league_id = b.league_id AND v.season = b.season WHERE b.expected_count IS NULL OR v.match_count != b.expected_count",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys league_id and season are NOT NULL in the view",
        "sql": "SELECT COUNT(*) FROM matches_per_league_season WHERE league_id IS NULL OR season IS NULL",
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
SELECT league_id, season, COUNT(*) AS match_count FROM "Match" GROUP BY league_id, season
```

---

## Skill `player_average_overall_rating`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_api_id`, `player_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_3e52ed117a219ba2 |
| output columns | `player_api_id`, `player_name`, `average_overall_rating` |
| source tables | `Player_Attributes`, `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player average of overall_rating from Player_Attributes joined to Player, useful for questions asking about a player's mean overall rating across records.

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
      "'Pietro Marino'"
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
    "question_id": "bird_dev_1096",
    "question": "Calculate the average overall rating of Pietro Marino.",
    "rewrite": "Task: Compute the average overall rating for the player named 'Pietro Marino'.\nRequired outputs: average_overall_rating: a single numeric value equal to AVG(T1.overall_rating) for rows matching the filters\nFilters: player_name = 'Pietro Marino'",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:26:19+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T06:26:22+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
      "player_name",
      "average_overall_rating"
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
        "purpose": "No duplicate rows at the declared grain (player_api_id, player_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_api_id, player_name, COUNT(*) AS cnt FROM player_average_overall_rating GROUP BY player_api_id, player_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "average_overall_rating equals AVG(overall_rating) computed from the base tables for that player",
        "sql": "SELECT COUNT(*) FROM (SELECT v.player_api_id, v.player_name FROM player_average_overall_rating v LEFT JOIN (SELECT p.player_api_id, p.player_name, AVG(pa.overall_rating) AS recomputed_avg FROM Player_Attributes pa JOIN Player p ON pa.player_api_id = p.player_api_id GROUP BY p.player_api_id, p.player_name) b ON v.player_api_id = b.player_api_id AND v.player_name = b.player_name WHERE (v.average_overall_rating IS NULL AND b.recomputed_avg IS NOT NULL) OR (v.average_overall_rating IS NOT NULL AND b.recomputed_avg IS NULL) OR (v.average_overall_rating IS NOT NULL AND b.recomputed_avg IS NOT NULL AND ABS(v.average_overall_rating - b.recomputed_avg) > 1e-6))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys player_api_id and player_name are not NULL in the view",
        "sql": "SELECT COUNT(*) FROM player_average_overall_rating WHERE player_api_id IS NULL OR player_name IS NULL",
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
SELECT p.player_api_id, p.player_name, AVG(pa.overall_rating) AS average_overall_rating
FROM Player_Attributes pa
JOIN Player p ON pa.player_api_id = p.player_api_id
GROUP BY p.player_api_id, p.player_name
```

---

## Skill `players_with_weights`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_15c1d51ec21bb109 |
| output columns | `player_api_id`, `weight` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

All players with their weight (for use in filtering, ranking, or joining to identify heavy players), excluding rows with NULL weight.

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
    "question_id": "bird_dev_1117",
    "question": "What are the player api id of 10 heaviest players?",
    "rewrite": "Task: Return the player API IDs for the 10 players with the greatest weight values (ties may be broken arbitrarily unless further specified).\nRequired outputs: player api id (the player API ID value for each returned player)\nFilters: include only players ordered by weight descending (highest weight first); limit results to 10 rows\nSort/limit: ORDER BY weight DESC LIMIT 10",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:37:44+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T06:37:46+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
      "weight"
    ],
    "row_count": 11060,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No NULL weights: view should exclude rows where weight IS NULL",
        "sql": "SELECT COUNT(*) FROM players_with_weights WHERE weight IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View has one row per player_api_id (no duplicate player_api_id)",
        "sql": "SELECT COUNT(*) - COUNT(DISTINCT player_api_id) FROM players_with_weights",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in view corresponds to a Player with the same weight (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM players_with_weights v LEFT JOIN Player p ON v.player_api_id = p.player_api_id WHERE p.player_api_id IS NULL OR v.weight != p.weight",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 1
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT player_api_id, weight FROM Player WHERE weight IS NOT NULL
```

---

## Skill `player_with_attributes`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `id` (keyed) |
| status / version | active / v1 |
| skill id | sk_946ad485f069e56a |
| output columns | `player_api_id`, `player_name`, `id`, `player_fifa_api_id`, `player_api_id:1`, `date`, `overall_rating`, `potential`, `preferred_foot`, `attacking_work_rate`, `defensive_work_rate`, `crossing`, `finishing`, `heading_accuracy`, `short_passing`, `volleys`, `dribbling`, `curve`, `free_kick_accuracy`, `long_passing`, `ball_control`, `acceleration`, `sprint_speed`, `agility`, `reactions`, `balance`, `shot_power`, `jumping`, `stamina`, `strength`, `long_shots`, `aggression`, `interceptions`, `positioning`, `vision`, `penalties`, `marking`, `standing_tackle`, `sliding_tackle`, `gk_diving`, `gk_handling`, `gk_kicking`, `gk_positioning`, `gk_reflexes` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Denormalized relation joining players to their attributes so queries can access player identifying info together with attribute fields.

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
    "question_id": "bird_dev_1123",
    "question": "What is the name of players with the highest potential?",
    "rewrite": "Task: Return the name(s) of the player(s) whose potential equals the maximum potential value (MAX(potential)).\nRequired outputs: name\nFilters: potential = MAX(potential) across all rows (i.e., potential equals the highest potential value present in the table)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:41:31+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T06:41:33+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
      "player_name",
      "id",
      "player_fifa_api_id",
      "player_api_id:1",
      "date",
      "overall_rating",
      "potential",
      "preferred_foot",
      "attacking_work_rate",
      "defensive_work_rate",
      "crossing",
      "finishing",
      "heading_accuracy",
      "short_passing",
      "volleys",
      "dribbling",
      "curve",
      "free_kick_accuracy",
      "long_passing",
      "ball_control",
      "acceleration",
      "sprint_speed",
      "agility",
      "reactions",
      "balance",
      "shot_power",
      "jumping",
      "stamina",
      "strength",
      "long_shots",
      "aggression",
      "interceptions",
      "positioning",
      "vision",
      "penalties",
      "marking",
      "standing_tackle",
      "sliding_tackle",
      "gk_diving",
      "gk_handling",
      "gk_kicking",
      "gk_positioning",
      "gk_reflexes"
    ],
    "row_count": 183978,
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
        "purpose": "View should have same number of rows as join of Player and Player_Attributes (no accidental row loss/duplication by view definition). Counts rows where the view row count differs from the explicit joi",
        "sql": "SELECT (SELECT COUNT(*) FROM player_with_attributes) - (SELECT COUNT(*) FROM Player p JOIN Player_Attributes pa ON p.player_api_id = pa.player_api_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view must reference an existing Player (player_api_id non-NULL and matches Player). Finds view rows whose player_api_id is NULL or does not join to Player.",
        "sql": "SELECT COUNT(*) FROM player_with_attributes v LEFT JOIN Player p ON v.player_api_id = p.player_api_id WHERE v.player_api_id IS NULL OR p.player_api_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "The view's id column must match the Player_Attributes.id it denormalizes (no mismatch between view.id and base Player_Attributes). Counts rows where view.id is not present in Player_Attributes or wher",
        "sql": "SELECT COUNT(*) FROM player_with_attributes v LEFT JOIN Player_Attributes pa ON v.id = pa.id WHERE pa.id IS NULL OR (pa.player_api_id IS NOT NULL AND v.player_api_id IS NOT NULL AND pa.player_api_id != v.player_api_id)",
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
SELECT p.player_api_id, p.player_name, pa.*
FROM Player p
JOIN Player_Attributes pa ON p.player_api_id = pa.player_api_id
```

---

## Skill `country_player_average_weight`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `country_id`, `country_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_8966ccc3aec54783 |
| output columns | `country_id`, `country_name`, `average_weight` |
| source tables | `Country`, `Match`, `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-country average player weight computed by associating players who appeared in matches for that country (one row per country with average weight).

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
      "Country",
      "Match",
      "Player"
    ],
    "table_fingerprints": {
      "country": "a556b33684a1aaf5",
      "match": "a56b9117c06fb4c3",
      "player": "032b398bb82740dc"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1128",
    "question": "Which country's players have the heaviest average weights?",
    "rewrite": "Task: Compute which country or countries have the highest average player weight, where 'heaviest average weights' is defined as the maximum of the average weights grouped by country.\nRequired outputs: country (the country name or identifier); average_weight (the average weight of players from that country)\nFilters: Include only rows grouped by country (one row per country).; Compute average_weight as AVG(weight) for all players associated with that country.; Consider all players in the dataset (no additional row-level filters unless the schema dictates NULL handling).; Exclude countries with no players (i.e., only consider groups where AVG(weight) is defined).\nSort/limit: Return only the country or countries whose average_weight equals the maximum average_weight across all countries (i.e., WHERE AVG(weight) = MAX(AVG(weight)) over countries).",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:46:27+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T06:46:32+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "country_id",
      "country_name",
      "average_weight"
    ],
    "row_count": 11,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Match.country_id=Country.id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "View has one row per country key (no duplicate country_id, country_name pairs)",
        "sql": "SELECT COUNT(*) FROM (SELECT country_id, country_name, COUNT(*) AS cnt FROM country_player_average_weight GROUP BY country_id, country_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "average_weight is the AVG of player weights for players who appeared in matches for that country (recomputed from base tables)",
        "sql": "SELECT COUNT(*) FROM country_player_average_weight v WHERE EXISTS (SELECT 1 FROM (SELECT c.id AS country_id, AVG(p.weight) AS recomputed_avg FROM Country c JOIN \"Match\" m ON m.country_id = c.id JOIN Player p ON p.player_api_id IN (m.home_player_1, m.home_player_2, m.home_player_3, m.home_player_4, m.home_player_5, m.home_player_6, m.home_player_7, m.home_player_8, m.home_player_9, m.home_player_10, m.home_player_11, m.away_player_1, m.away_player_2, m.away_player_3, m.away_player_4, m.away_player_5, m.away_player_6, m.away_player_7, m.away_player_8, m.away_player_9, m.away_player_10, m.away_player_11) GROUP BY c.id) r WHERE r.country_id = v.country_id AND ( (r.recomputed_avg IS NULL AND v.average_weight IS NOT NULL) OR (r.recomputed_avg IS NOT NULL AND (ABS(r.recomputed_avg - v.average_wei",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys country_id and country_name are not NULL in the view",
        "sql": "SELECT COUNT(*) FROM country_player_average_weight WHERE country_id IS NULL OR country_name IS NULL",
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
SELECT c.id AS country_id,
       c.name AS country_name,
       AVG(p.weight) AS average_weight
FROM Country c
JOIN "Match" m ON m.country_id = c.id
JOIN Player p ON p.player_api_id IN (
    m.home_player_1, m.home_player_2, m.home_player_3, m.home_player_4, m.home_player_5,
    m.home_player_6, m.home_player_7, m.home_player_8, m.home_player_9, m.home_player_10, m.home_player_11,
    m.away_player_1, m.away_player_2, m.away_player_3, m.away_player_4, m.away_player_5,
    m.away_player_6, m.away_player_7, m.away_player_8, m.away_player_9, m.away_player_10, m.away_player_11
)
GROUP BY c.id, c.name
HAVING AVG(p.weight) IS NOT NULL
```

---

## Skill `player_max_crossing_17`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_7161d10545233a44 |
| output columns | `player_id`, `max_crossing` |
| source tables | `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Each player's maximum observed crossing attribute value across all their Player_Attributes records

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
      "Player_Attributes"
    ],
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1136",
    "question": "How many players had the highest potential score for crossing that preferred to use their left foots while attacking?",
    "rewrite": "Task: Count the number of players whose maximum crossing potential equals the overall maximum crossing potential and whose preferred foot is 'left'.\nRequired outputs: count of players (integer) matching the criteria\nFilters: player's preferred_foot = 'left'; player's crossing potential = MAX(crossing) over all players",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:48:56+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T06:48:58+00:00",
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
        "purpose": "View has one row per player_id (no duplicate player_id)",
        "sql": "SELECT COUNT(*) FROM player_max_crossing_17 t1 WHERE (SELECT COUNT(*) FROM player_max_crossing_17 t2 WHERE t2.player_id = t1.player_id) > 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "max_crossing equals the MAX(crossing) computed from Player_Attributes for that player_id",
        "sql": "SELECT COUNT(*) FROM player_max_crossing_17 v LEFT JOIN (SELECT player_api_id AS player_id, MAX(crossing) AS expected_max FROM Player_Attributes GROUP BY player_api_id) b ON v.player_id = b.player_id WHERE NOT ( (v.max_crossing IS NULL AND b.expected_max IS NULL) OR (v.max_crossing = b.expected_max) )",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every player_id in the view is NOT NULL and corresponds to at least one Player_Attributes row",
        "sql": "SELECT COUNT(*) FROM player_max_crossing_17 v LEFT JOIN Player_Attributes p ON v.player_id = p.player_api_id WHERE v.player_id IS NULL OR p.player_api_id IS NULL",
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
SELECT player_api_id AS player_id, MAX(crossing) AS max_crossing FROM Player_Attributes GROUP BY player_api_id
```

---

## Skill `matches_per_league_season_30`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_f8b36651e2672440 |
| output columns | `league_id`, `season`, `matches_played` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Total number of matches per league and season (one row per league-season with match count).

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
      "Italian Serie A",
      "2015/2016"
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
    "question_id": "bird_dev_1142",
    "question": "In the 2015–2016 season, how many games were played in the Italian Serie A league?",
    "rewrite": "Task: Compute the total number of games played in the Italian Serie A league during the 2015/2016 season.\nRequired outputs: league: the string 'Italian Serie A' or equivalent league identifier; season: the string '2015/2016'; games_played: an integer equal to the total number of games played in that league for that season\nFilters: league equals 'Italian Serie A' (or the database's corresponding league identifier for Italy's top division); season equals '2015/2016' (representing the 2015–2016 season)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:51:09+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T06:51:12+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "league_id",
      "season",
      "matches_played"
    ],
    "row_count": 88,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View has one row per league_id+season (no duplicate league-season combinations)",
        "sql": "SELECT COUNT(*) FROM matches_per_league_season_30 v JOIN (SELECT league_id, season, COUNT(*) AS cnt FROM matches_per_league_season_30 GROUP BY league_id, season HAVING cnt > 1) d USING (league_id, season)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "matches_played matches the count of Match rows for that league_id and season",
        "sql": "SELECT COUNT(*) FROM matches_per_league_season_30 v LEFT JOIN (SELECT league_id, season, COUNT(*) AS expected_matches FROM \"Match\" GROUP BY league_id, season) m ON v.league_id = m.league_id AND v.season = m.season WHERE (m.expected_matches IS NULL AND v.matches_played IS NOT NULL) OR (m.expected_matches IS NOT NULL AND v.matches_played != m.expected_matches)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys league_id and season are not NULL in the view (grain keys must be present)",
        "sql": "SELECT COUNT(*) FROM matches_per_league_season_30 WHERE league_id IS NULL OR season IS NULL",
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
SELECT M.league_id AS league_id, M.season AS season, COUNT(*) AS matches_played FROM Match M GROUP BY M.league_id, M.season
```

---

## Skill `matches_with_league_and_home_goals`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `match_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_a8194622f90aea8a |
| output columns | `match_id`, `league_id`, `league_name`, `home_team_goal` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-match rows including league name and home team goals to support league-filtered aggregations (e.g., max/min/avg home goals per league or further joins).

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
      "Netherlands Eredivisie"
    ],
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "Match",
      "League"
    ],
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3",
      "league": "72cd1678e1e9160e"
    },
    "data_fingerprints": {
      "match": "25979:25979",
      "league": "11:24558"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1143",
    "question": "What was the highest score of the home team in the Netherlands Eredivisie league?",
    "rewrite": "Task: Compute the maximum number of goals scored by the home team in matches played in the Netherlands Eredivisie league (i.e., find MAX(home_team_goal) for rows where league = 'Netherlands Eredivisie').\nRequired outputs: max_home_team_goal: a single numeric value equal to the highest home_team_goal among the filtered matches\nFilters: league = 'Netherlands Eredivisie' (include only rows for the Netherlands Eredivisie league)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:51:35+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T06:51:38+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "match_id",
      "league_id",
      "league_name",
      "home_team_goal"
    ],
    "row_count": 25979,
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
        "purpose": "view has one row per Match.id (no duplicate match_id)",
        "sql": "SELECT COUNT(*) FROM matches_with_league_and_home_goals mv GROUP BY mv.match_id HAVING COUNT(*)>1 LIMIT 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "every view row matches a base Match joined to League (no unmatched rows) — detect rows in view whose match_id doesn't exist in Match or whose league_id/name don't match",
        "sql": "SELECT COUNT(*) FROM matches_with_league_and_home_goals mv LEFT JOIN \"Match\" M ON mv.match_id = M.id LEFT JOIN \"League\" L ON M.league_id = L.id WHERE M.id IS NULL OR mv.league_id IS NULL OR mv.league_id != M.league_id OR mv.league_name IS NOT L.name",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "home_team_goal in view equals Match.home_team_goal (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM matches_with_league_and_home_goals mv JOIN \"Match\" M ON mv.match_id = M.id WHERE (mv.home_team_goal IS NOT M.home_team_goal) OR (mv.home_team_goal IS NULL AND M.home_team_goal IS NOT NULL) OR (mv.home_team_goal IS NOT NULL AND M.home_team_goal IS NULL)",
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
SELECT M.id AS match_id, M.league_id, L.name AS league_name, M.home_team_goal FROM "Match" M JOIN "League" L ON M.league_id = L.id
```

---

## Skill `match_count_per_league_season`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `team_long_name`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_47c6255809535bfc |
| output columns | `league_id`, `team_long_name`, `season`, `game_count` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Counts number of matches per league for each season (per-league, per-season match counts) useful for comparing league activity across seasons.

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
    "question_id": "bird_dev_1145",
    "question": "Which league had the most games in the 2015–2016 season?",
    "rewrite": "Task: Find the league (team_long_name) that had the largest number of games (count of id) during the 2015/2016 season.\nRequired outputs: team_long_name (the league name); game_count (the count of id for that league in the specified season)\nFilters: season = '2015/2016'; group rows by team_long_name and count ids for each team_long_name\nSort/limit: order by game_count DESC limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:52:23+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T06:52:26+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "league_id",
      "team_long_name",
      "season",
      "game_count"
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
        "purpose": "No duplicate rows at the declared grain (league_id, team_long_name, season). Ensure view has at most one row per key combination.",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, team_long_name, season, COUNT(*) AS cnt FROM match_count_per_league_season GROUP BY league_id, team_long_name, season HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "game_count matches count of Match rows for that league_id and season (recomputed from base table). Detects aggregation or join mistakes where counts differ.",
        "sql": "SELECT COUNT(*) FROM match_count_per_league_season v LEFT JOIN (SELECT league_id, season, COUNT(id) AS expected_count FROM \"Match\" GROUP BY league_id, season) m ON v.league_id = m.league_id AND v.season = m.season WHERE (m.expected_count IS NULL AND v.game_count IS NOT NULL) OR (m.expected_count IS NOT NULL AND v.game_count != m.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys league_id, team_long_name, and season are not NULL (view grain keys must be present).",
        "sql": "SELECT COUNT(*) FROM match_count_per_league_season WHERE league_id IS NULL OR team_long_name IS NULL OR season IS NULL",
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
SELECT M.league_id, L.name AS team_long_name, M.season, COUNT(M.id) AS game_count FROM Match M JOIN League L ON M.league_id = L.id GROUP BY M.league_id, L.name, M.season
```

---
