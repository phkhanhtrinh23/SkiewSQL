# Skill graph — `european_football_2` (35 skills)

## Skill `player_max_height`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `id` (keyed) |
| status / version | active / v1 |
| skill id | sk_5be082e5e7b41daa |
| output columns | `id`, `player_api_id`, `player_fifa_api_id`, `player_name`, `height` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player rows for players whose height equals the maximum height present in the Player table (identifies tallest player(s)); useful to find tallest player(s) without hard-coded constants.

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
    "contract_version": 3,
    "grain_basis": "primary_key",
    "lineage": [
      "Player"
    ],
    "source_columns": [
      "Player.id",
      "Player.player_api_id",
      "Player.player_fifa_api_id",
      "Player.player_name",
      "Player.height"
    ],
    "output_lineage": {
      "id": [
        "Player.id"
      ],
      "player_api_id": [
        "Player.player_api_id"
      ],
      "player_fifa_api_id": [
        "Player.player_fifa_api_id"
      ],
      "player_name": [
        "Player.player_name"
      ],
      "height": [
        "Player.height"
      ]
    },
    "operators": [
      "filter",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player": "032b398bb82740dc"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1021",
    "question": "What is the height of the tallest player? Indicate his name.",
    "rewrite": "Task: Find the maximum height value among all players and report the name of the player who has that maximum height.\nRequired outputs: name; height\nFilters: height = MAX(height)\nSort/limit: ''",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:25:45+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:25:47+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "id",
      "player_api_id",
      "player_fifa_api_id",
      "player_name",
      "height"
    ],
    "row_count": 1,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View respects its declared grain: id is unique in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT id, COUNT(*) AS cnt FROM player_max_height GROUP BY id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's height equals the maximum non-NULL Player.height in the base table",
        "sql": "SELECT COUNT(*) FROM player_max_height v WHERE v.height IS NULL OR v.height <> (SELECT MAX(height) FROM Player WHERE height IS NOT NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View contains only players that exist in the base Player table with matching key and attributes",
        "sql": "SELECT COUNT(*) FROM player_max_height v LEFT JOIN Player p ON v.id = p.id WHERE p.id IS NULL OR v.player_api_id <> p.player_api_id OR v.player_fifa_api_id <> p.player_fifa_api_id OR v.player_name <> p.player_name OR (v.height IS NOT p.height AND NOT (v.height IS NULL AND p.height IS NULL))",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 4,
    "selected": 1,
    "included": 1,
    "referenced": 1,
    "executed": 1,
    "inconclusive": 1,
    "negative": 1,
    "negative_subgoals": [
      "Task: Find the player(s) who have the maximum value in the height column (i.e., the tallest player(s)).\nRequired outputs: player (the player's identifier/name as stored); height (the player's height value)\nFilters: height IS NOT NULL\nSort/limit: order by height DESC limit 1 (or return all rows tied for MAX(height))"
    ],
    "last_used": "bird_dev_1079"
  }
}
```

### Validated on (0)

—

### Counter-examples (1)

- Which player is the tallest?

### Executable SQL body

```sql
SELECT id, player_api_id, player_fifa_api_id, player_name, height FROM Player WHERE height IS NOT NULL AND height = (SELECT MAX(height) FROM Player WHERE height IS NOT NULL)
```

---

## Skill `player_min_potential`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_cfe017460292ba69 |
| output columns | `player_attributes_id`, `player_api_id`, `player_fifa_api_id`, `date`, `potential`, `preferred_foot` |
| source tables | `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

All players whose potential equals the minimum potential value across all players (keeps identifiers and potential and preferred_foot for reuse).

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
    "contract_version": 3,
    "grain_basis": "primary_key",
    "lineage": [
      "Player_Attributes"
    ],
    "source_columns": [
      "Player_Attributes.player_api_id",
      "Player_Attributes.player_fifa_api_id",
      "Player_Attributes.date",
      "Player_Attributes.potential",
      "Player_Attributes.preferred_foot",
      "Player_Attributes.id"
    ],
    "output_lineage": {
      "player_attributes_id": [
        "Player_Attributes.id"
      ],
      "player_api_id": [
        "Player_Attributes.player_api_id"
      ],
      "player_fifa_api_id": [
        "Player_Attributes.player_fifa_api_id"
      ],
      "date": [
        "Player_Attributes.date"
      ],
      "potential": [
        "Player_Attributes.potential"
      ],
      "preferred_foot": [
        "Player_Attributes.preferred_foot"
      ]
    },
    "operators": [
      "filter",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1022",
    "question": "What is the preferred foot when attacking of the player with the lowest potential?",
    "rewrite": "Task: Find the preferred_foot value for the player(s) whose potential equals the minimum potential across all players.\nRequired outputs: preferred_foot\nFilters: potential = MIN(potential) across all rows",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:26:03+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:26:05+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "player_attributes_id",
      "player_api_id",
      "player_fifa_api_id",
      "date",
      "potential",
      "preferred_foot"
    ],
    "row_count": 2,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View only contains rows whose potential equals the minimum potential across Player_Attributes",
        "sql": "SELECT COUNT(*) FROM player_min_potential v WHERE v.potential <> (SELECT MIN(potential) FROM Player_Attributes)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All base rows with the minimum potential appear in the view (no missing rows): every Player_Attributes row whose potential is the global minimum should be present",
        "sql": "SELECT COUNT(*) FROM Player_Attributes pa WHERE pa.potential = (SELECT MIN(potential) FROM Player_Attributes) AND NOT EXISTS (SELECT 1 FROM player_min_potential v WHERE v.player_attributes_id = pa.id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "player_attributes_id is unique and not NULL in the view (ensures grain and no duplicates)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_attributes_id, COUNT(*) AS cnt FROM player_min_potential GROUP BY player_attributes_id HAVING player_attributes_id IS NULL OR cnt <> 1)",
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
    "negative": 1,
    "negative_subgoals": [
      "Task: Find the top three football player IDs among players who have the minimum possible 'potential' value and whose 'preferred_foot' equals 'right'.\nRequired outputs: player_id\nFilters: potential = MIN(potential) across the entire players table; preferred_foot = 'right'\nSort/limit: return up to 3 player_id values; no additional ordering specified beyond selecting the top three (limit 3)"
    ],
    "last_used": "bird_dev_1135"
  }
}
```

### Validated on (0)

—

### Counter-examples (1)

- Please provide top three football players' IDs who are among the lowest potential players and prefer to use the right foot when attacking.

### Executable SQL body

```sql
SELECT id AS player_attributes_id, player_api_id, player_fifa_api_id, date, potential, preferred_foot FROM Player_Attributes WHERE potential = (SELECT MIN(potential) FROM Player_Attributes)
```

---

## Skill `player_max_crossing`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_b5441fd432371201 |
| output columns | `player_api_id`, `max_crossing`, `crossing_count` |
| source tables | `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each player (by player_api_id), the maximum recorded crossing value and count of non-null crossing measurements across Player_Attributes

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Player_Attributes"
    ],
    "source_columns": [
      "Player_Attributes.player_api_id",
      "Player_Attributes.crossing"
    ],
    "output_lineage": {
      "player_api_id": [
        "Player_Attributes.player_api_id"
      ],
      "max_crossing": [
        "Player_Attributes.crossing"
      ],
      "crossing_count": [
        "Player_Attributes.crossing"
      ]
    },
    "operators": [
      "filter",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1024",
    "question": "Who are the top 5 players who perform better in crossing actions? Indicate their player id.",
    "rewrite": "Task: Find the top 5 players (by player id) with the highest maximum value of crossing actions, i.e. players ranked by MAX(crossing) in descending order.\nRequired outputs: player id; max(crossing) value for each player\nFilters: consider all players with any crossing values (exclude players with NULL crossing if NULLs are not comparable)\nSort/limit: order by MAX(crossing) DESC limit 5",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:26:45+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:26:50+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
      "max_crossing",
      "crossing_count"
    ],
    "row_count": 11060,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View has exactly one row per player_api_id present in Player_Attributes with any non-null crossing (no missing or extra keys)",
        "sql": "SELECT (SELECT COUNT(DISTINCT pa.player_api_id) FROM Player_Attributes pa WHERE pa.crossing IS NOT NULL) - (SELECT COUNT(*) FROM player_max_crossing) AS cnt_violations",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "max_crossing equals the maximum crossing computed from base table for that player_api_id",
        "sql": "SELECT COUNT(*) FROM player_max_crossing vmc LEFT JOIN (SELECT pa.player_api_id, MAX(pa.crossing) AS expected_max FROM Player_Attributes pa WHERE pa.crossing IS NOT NULL GROUP BY pa.player_api_id) b ON vmc.player_api_id = b.player_api_id WHERE (b.expected_max IS NULL AND vmc.max_crossing IS NOT NULL) OR (b.expected_max IS NOT NULL AND vmc.max_crossing IS NULL) OR (b.expected_max IS NOT NULL AND vmc.max_crossing != b.expected_max)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "crossing_count equals the count of non-null crossing values for that player_api_id in the base table",
        "sql": "SELECT COUNT(*) FROM player_max_crossing vmc LEFT JOIN (SELECT pa.player_api_id, COUNT(pa.crossing) AS expected_count FROM Player_Attributes pa WHERE pa.crossing IS NOT NULL GROUP BY pa.player_api_id) b ON vmc.player_api_id = b.player_api_id WHERE (b.expected_count IS NULL AND vmc.crossing_count != 0) OR (b.expected_count IS NOT NULL AND vmc.crossing_count != b.expected_count)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 1,
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
SELECT pa.player_api_id AS player_api_id, MAX(pa.crossing) AS max_crossing, COUNT(pa.crossing) AS crossing_count FROM Player_Attributes pa WHERE pa.crossing IS NOT NULL GROUP BY pa.player_api_id
```

---

## Skill `matches_with_match_goals`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `match_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_77a5a7d3320460db |
| output columns | `match_id`, `league_id`, `league_name`, `season`, `home_team_goal`, `away_team_goal`, `match_goals` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-match rows including league and season and a computed match_goals column equal to home_team_goal + away_team_goal; useful for season- and league-level aggregations of goals

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
      "'2015/2016'",
      "LIMIT 1",
      "ORDER BY total_goals DESC"
    ],
    "contract_version": 3,
    "grain_basis": "verified_unique",
    "lineage": [
      "Match",
      "League"
    ],
    "source_columns": [
      "Match.league_id",
      "Match.season",
      "Match.home_team_goal",
      "Match.away_team_goal",
      "Match.id",
      "League.name",
      "League.id"
    ],
    "output_lineage": {
      "match_id": [
        "Match.id"
      ],
      "league_id": [
        "Match.league_id"
      ],
      "league_name": [
        "League.name"
      ],
      "season": [
        "Match.season"
      ],
      "home_team_goal": [
        "Match.home_team_goal"
      ],
      "away_team_goal": [
        "Match.away_team_goal"
      ],
      "match_goals": [
        "Match.home_team_goal",
        "Match.away_team_goal"
      ]
    },
    "operators": [
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3",
      "league": "72cd1678e1e9160e"
    },
    "data_fingerprints": {
      "match": "25979:25979",
      "league": "11:24558"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1025",
    "question": "Which league had the most goals in the 2016 season?",
    "rewrite": "Task: Find which league had the largest total number of goals scored across all matches in the 2015/2016 season, where match goals are counted as home_team_goal + away_team_goal and the league's total is the sum of those goals for matches in that season.\nRequired outputs: league (identifier or name of the league); total_goals (the sum of home_team_goal and away_team_goal for all matches in that league during the specified season)\nFilters: season = '2015/2016'; consider only matches from that season; for each match, use goals = home_team_goal + away_team_goal\nSort/limit: order by total_goals desc limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:27:10+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:27:12+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "match_id",
      "league_id",
      "league_name",
      "season",
      "home_team_goal",
      "away_team_goal",
      "match_goals"
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
        "purpose": "View grain uniqueness: no duplicate match_id rows",
        "sql": "SELECT COUNT(*) FROM (SELECT match_id, COUNT(*) AS cnt FROM matches_with_match_goals GROUP BY match_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Computed measure correctness: match_goals equals COALESCE(home_team_goal,0)+COALESCE(away_team_goal,0)",
        "sql": "SELECT COUNT(*) FROM matches_with_match_goals WHERE match_goals IS NOT (COALESCE(home_team_goal,0) + COALESCE(away_team_goal,0))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Join completeness: every Match row with a non-NULL league_id appears in the view (no matches lost by the JOIN)",
        "sql": "SELECT COUNT(*) FROM Match m WHERE m.league_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM matches_with_match_goals v WHERE v.match_id = m.id)",
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
  Match.id AS match_id,
  Match.league_id,
  League.name AS league_name,
  Match.season,
  Match.home_team_goal,
  Match.away_team_goal,
  (COALESCE(Match.home_team_goal,0) + COALESCE(Match.away_team_goal,0)) AS match_goals
FROM Match
JOIN League ON Match.league_id = League.id
```

---

## Skill `home_team_season_home_loss_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `home_team_api_id`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_5ab93ae347639c67 |
| output columns | `home_team_api_id`, `season`, `home_losses_count` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-team counts of home losses in a given season (matches where home_team_goal - away_team_goal < 0), keyed by home_team_api_id and season.

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
      "2015/2016"
    ],
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Match"
    ],
    "source_columns": [
      "Match.home_team_api_id",
      "Match.season",
      "Match.home_team_goal",
      "Match.away_team_goal"
    ],
    "output_lineage": {
      "home_team_api_id": [
        "Match.home_team_api_id"
      ],
      "season": [
        "Match.season"
      ],
      "home_losses_count": []
    },
    "operators": [
      "filter",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1026",
    "question": "Which home team had lost the fewest matches in the 2016 season?",
    "rewrite": "Task: Find which home team(s) in the 2015/2016 season had the smallest number of home losses, where a home loss is any match in that season with home_team_goal - away_team_goal < 0.\nRequired outputs: home_team (the team name); home_losses_count (the count of matches in 2015/2016 where home_team_goal - away_team_goal < 0 for that home_team)\nFilters: season = '2015/2016'; count only matches where (home_team_goal - away_team_goal) < 0; group counts by home_team\nSort/limit: order by home_losses_count ascending limit to the minimum value (i.e., return all home_team rows whose home_losses_count equals the smallest such count)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:27:36+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:27:38+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "home_team_api_id",
      "season",
      "home_losses_count"
    ],
    "row_count": 1434,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View has correct grain: no duplicate (home_team_api_id, season) pairs",
        "sql": "SELECT COUNT(*) FROM home_team_season_home_loss_counts t1 JOIN (SELECT home_team_api_id, season, COUNT(*) AS cnt FROM home_team_season_home_loss_counts GROUP BY home_team_api_id, season HAVING cnt > 1) dup ON t1.home_team_api_id = dup.home_team_api_id AND t1.season = dup.season",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "home_losses_count matches count of Match rows where home_team_goal - away_team_goal < 0 grouped by keys",
        "sql": "SELECT COUNT(*) FROM home_team_season_home_loss_counts v LEFT JOIN (SELECT home_team_api_id, season, COUNT(*) AS expected_count FROM Match WHERE (home_team_goal - away_team_goal) < 0 GROUP BY home_team_api_id, season) m ON v.home_team_api_id = m.home_team_api_id AND v.season = m.season WHERE (m.expected_count IS NULL) OR (v.home_losses_count != m.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL",
        "sql": "SELECT COUNT(*) FROM home_team_season_home_loss_counts WHERE home_team_api_id IS NULL OR season IS NULL",
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
  home_team_api_id,
  season,
  COUNT(*) AS home_losses_count
FROM Match
WHERE (home_team_goal - away_team_goal) < 0
GROUP BY home_team_api_id, season
```

---

## Skill `player_max_penalties`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_882d6a9ca79c34cf |
| output columns | `player_api_id`, `max_penalties` |
| source tables | `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each player (by player_api_id) the maximum recorded penalties value from Player_Attributes (one row per player)

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Player_Attributes"
    ],
    "source_columns": [
      "Player_Attributes.player_api_id",
      "Player_Attributes.penalties"
    ],
    "output_lineage": {
      "player_api_id": [
        "Player_Attributes.player_api_id"
      ],
      "max_penalties": [
        "Player_Attributes.penalties"
      ]
    },
    "operators": [
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1027",
    "question": "Indicate the full names of the top 10 players with the highest number of penalties.",
    "rewrite": "Task: Retrieve the full names of the top 10 players who have the highest penalties values (using the penalties value MAX for ranking).\nRequired outputs: player_name (full name)\nFilters: Consider all players; no additional WHERE filters.; When penalties are tied, include tie-breaking only by the penalties value (no other implicit tie-breaker).\nSort/limit: Order results by penalties in descending order and return the top 10 rows (limit 10).",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:28:02+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:28:05+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
      "max_penalties"
    ],
    "row_count": 11060,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows per grain: ensure each player_api_id appears at most once in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT player_api_id, COUNT(*) AS cnt FROM player_max_penalties GROUP BY player_api_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each view row's max_penalties equals the MAX(penalties) computed from the base table for that player_api_id",
        "sql": "SELECT COUNT(*) FROM player_max_penalties v LEFT JOIN (SELECT player_api_id, MAX(penalties) AS expected_max FROM Player_Attributes GROUP BY player_api_id) b ON v.player_api_id = b.player_api_id WHERE (v.max_penalties IS NOT b.expected_max) OR (v.max_penalties IS NULL AND b.expected_max IS NOT NULL) OR (v.max_penalties IS NOT NULL AND b.expected_max IS NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL: every row in the view has a non-NULL player_api_id",
        "sql": "SELECT COUNT(*) FROM player_max_penalties WHERE player_api_id IS NULL",
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
SELECT player_api_id, MAX(penalties) AS max_penalties
FROM Player_Attributes
GROUP BY player_api_id
```

---

## Skill `team_max_buildup_play_speed`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `team_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_06502975d9b9cd45 |
| output columns | `team_api_id`, `max_buildUpPlaySpeed` |
| source tables | `Team_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-team maximum buildUpPlaySpeed from Team_Attributes for use in ranking or comparisons

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Team_Attributes"
    ],
    "source_columns": [
      "Team_Attributes.team_api_id",
      "Team_Attributes.buildUpPlaySpeed"
    ],
    "output_lineage": {
      "team_api_id": [
        "Team_Attributes.team_api_id"
      ],
      "max_buildUpPlaySpeed": [
        "Team_Attributes.buildUpPlaySpeed"
      ]
    },
    "operators": [
      "filter",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "team_attributes": "a8661cb8da0875ec"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1029",
    "question": "What are the speed in which attacks are put together of the top 4 teams with the highest build Up Play Speed?",
    "rewrite": "Task: Return the buildUpPlaySpeed values for the top 4 teams by buildUpPlaySpeed (i.e., the teams with the highest buildUpPlaySpeed), showing each team's name and their buildUpPlaySpeed.\nRequired outputs: team_name; buildUpPlaySpeed\nFilters: Only include rows for teams ranked in the top 4 by buildUpPlaySpeed (highest values).; If multiple teams tie at the cutoff, include only enough teams to make exactly 4 rows — break ties by team_name ascending.\nSort/limit: ORDER BY buildUpPlaySpeed DESC, team_name ASC LIMIT 4",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:28:44+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:28:47+00:00",
    "contract_version": 3,
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
        "purpose": "No duplicate rows per grain (each team_api_id appears at most once)",
        "sql": "SELECT COUNT(*) FROM (SELECT team_api_id, COUNT(*) AS cnt FROM team_max_buildup_play_speed GROUP BY team_api_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each max_buildUpPlaySpeed equals the maximum buildUpPlaySpeed in the base table for that team (recomputed max)",
        "sql": "SELECT COUNT(*) FROM team_max_buildup_play_speed v LEFT JOIN (SELECT team_api_id, MAX(buildUpPlaySpeed) AS recomputed_max FROM Team_Attributes WHERE buildUpPlaySpeed IS NOT NULL GROUP BY team_api_id) b ON v.team_api_id = b.team_api_id WHERE NOT (v.max_buildUpPlaySpeed IS b.recomputed_max OR (v.max_buildUpPlaySpeed IS NULL AND b.recomputed_max IS NULL))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL (team_api_id must be present for every row)",
        "sql": "SELECT COUNT(*) FROM team_max_buildup_play_speed WHERE team_api_id IS NULL",
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
SELECT team_api_id, MAX(buildUpPlaySpeed) AS max_buildUpPlaySpeed FROM Team_Attributes WHERE buildUpPlaySpeed IS NOT NULL GROUP BY team_api_id
```

---

## Skill `league_draw_counts_by_season`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `league_name`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_fb9907c6e38546a5 |
| output columns | `league_id`, `league_name`, `season`, `draw_count` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each league and season, counts of matches that ended in a draw (home_team_goal = away_team_goal).

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
      "'2015/2016' (season filter)"
    ],
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Match",
      "League"
    ],
    "source_columns": [
      "Match.league_id",
      "Match.season",
      "League.name",
      "League.id",
      "Match.home_team_goal",
      "Match.away_team_goal"
    ],
    "output_lineage": {
      "league_id": [
        "Match.league_id"
      ],
      "league_name": [
        "League.name"
      ],
      "season": [
        "Match.season"
      ],
      "draw_count": []
    },
    "operators": [
      "filter",
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3",
      "league": "72cd1678e1e9160e"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1030",
    "question": "Which League had the most matches end as draw in the 2016 season?",
    "rewrite": "Task: Find which League had the largest number of matches whose result was a draw during the 2015/2016 season, where a match is a draw when home_team_goal = away_team_goal.\nRequired outputs: league (identifier or name for the League); draw_count (integer count of matches in that League during season '2015/2016' where home_team_goal = away_team_goal)\nFilters: season = '2015/2016'; match is counted only if home_team_goal = away_team_goal; grouping is by League\nSort/limit: order by draw_count desc limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:29:03+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:29:06+00:00",
    "contract_version": 3,
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
        "purpose": "No duplicate rows for the grain (league_id, league_name, season)",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, league_name, season, COUNT(*) AS cnt FROM league_draw_counts_by_season GROUP BY league_id, league_name, season HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's draw_count equals the number of Match rows for that league_id and season where home_team_goal = away_team_goal",
        "sql": "SELECT COUNT(*) FROM league_draw_counts_by_season v WHERE v.draw_count != (SELECT COUNT(*) FROM \"Match\" m WHERE m.league_id = v.league_id AND m.season = v.season AND m.home_team_goal = m.away_team_goal)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys league_id, league_name, season are not NULL",
        "sql": "SELECT COUNT(*) FROM league_draw_counts_by_season WHERE league_id IS NULL OR league_name IS NULL OR season IS NULL",
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
SELECT M.league_id, L.name AS league_name, M.season, COUNT(*) AS draw_count FROM "Match" M JOIN League L ON M.league_id = L.id WHERE M.home_team_goal = M.away_team_goal GROUP BY M.league_id, L.name, M.season
```

---

## Skill `players_with_high_sprint_speed_records`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_api_id`, `player_name`, `birthday` (keyed) |
| status / version | active / v1 |
| skill id | sk_638845e0b0af4662 |
| output columns | `player_api_id`, `player_name`, `birthday` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Players who have at least one Player_Attributes record meeting a sprint_speed threshold within a date range (keeps player id for joins and birthdate for age calculations).

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
      "sprint_speed >= 97",
      "date >= '2013-01-01 00:00:00'",
      "date <= '2015-12-31 00:00:00'"
    ],
    "contract_version": 3,
    "grain_basis": "distinct",
    "lineage": [
      "Player",
      "Player_Attributes"
    ],
    "source_columns": [
      "Player_Attributes.player_api_id",
      "Player.player_name",
      "Player.birthday",
      "Player.player_api_id"
    ],
    "output_lineage": {
      "player_api_id": [
        "Player_Attributes.player_api_id"
      ],
      "player_name": [
        "Player.player_name"
      ],
      "birthday": [
        "Player.birthday"
      ]
    },
    "operators": [
      "filter",
      "join",
      "project",
      "distinct"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player": "032b398bb82740dc",
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {
      "player": "11060:11075",
      "player_attributes": "183978:183978"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1031",
    "question": "At present, calculate for the player's age who have a sprint speed of no less than 97 between 2013 to 2015.",
    "rewrite": "Task: Compute the current ages of players who have a sprint speed of at least 97 on records dated between 2013-01-01 00:00:00 and 2015-12-31 00:00:00 inclusive, where current age is defined as the difference between the current datetime and the player's birthday.\nRequired outputs: player identifier (e.g., player id or name as available in schema); current age (computed as DATETIME() - birthday; expressed in years or as the exact interval — specify numeric years if schema requires)\nFilters: sprint_speed >= 97; date >= '2013-01-01 00:00:00' AND date <= '2015-12-31 00:00:00'",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:29:29+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:29:32+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
      "player_name",
      "birthday"
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
        "purpose": "View rows must match actual join: every row in the view should have at least one matching Player_Attributes row with the same player_api_id",
        "sql": "SELECT COUNT(*) FROM players_with_high_sprint_speed_records v WHERE NOT EXISTS (SELECT 1 FROM Player_Attributes pa WHERE pa.player_api_id = v.player_api_id)",
        "result": "inconclusive",
        "violations": null,
        "error": "timeout"
      },
      {
        "purpose": "No NULLs in key columns of the view (player_api_id, player_name, birthday) — grain keys must be present",
        "sql": "SELECT COUNT(*) FROM players_with_high_sprint_speed_records v WHERE v.player_api_id IS NULL OR v.player_name IS NULL OR v.birthday IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View should not contain duplicates at its declared grain (player_api_id, player_name, birthday)",
        "sql": "SELECT COUNT(*) FROM (SELECT v.player_api_id, v.player_name, v.birthday, COUNT(*) c FROM players_with_high_sprint_speed_records v GROUP BY v.player_api_id, v.player_name, v.birthday HAVING c > 1)",
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
SELECT DISTINCT pa.player_api_id, p.player_name, p.birthday
FROM Player p
JOIN Player_Attributes pa ON pa.player_api_id = p.player_api_id
WHERE p.birthday IS NOT NULL
```

---

## Skill `matches_per_league`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_14d348e13a9cd7a0 |
| output columns | `league_id`, `match_count` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Total number of matches aggregated per league (one row per league_id with its match count), useful for league-level match-count analyses and joins.

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Match"
    ],
    "source_columns": [
      "Match.league_id"
    ],
    "output_lineage": {
      "league_id": [
        "Match.league_id"
      ],
      "match_count": []
    },
    "operators": [
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1032",
    "question": "Give the name of the league with the highest matches of all time and how many matches were played in the said league.",
    "rewrite": "Task: Find the league (by League.name) that has the largest total number of matches across all time, and return that league's name together with the total number of matches played in that league.\nRequired outputs: League.name — the name of the league that has the maximum total matches; match_count — the total number of matches played in that league (COUNT of matches where match.league_id = League.id)\nFilters: Consider all matches in the matches table (no date or other temporal filters).; Aggregate matches by league_id to compute the total MATCH count per league.; Select the league(s) whose aggregated match count equals the maximum aggregated count across all leagues.\nSort/limit: Order by match_count DESC and limit to the top 1 result (if multiple leagues tie, return the one row with the maximum count; implementation may return any one of the tied leagues)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:30:00+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:30:03+00:00",
    "contract_version": 3,
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
        "purpose": "View has one row per league_id (no duplicate league_id rows)",
        "sql": "SELECT COUNT(*) FROM matches_per_league AS v GROUP BY league_id HAVING COUNT(*)>1 LIMIT 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "match_count equals the count of Match rows for that league_id",
        "sql": "SELECT COUNT(*) FROM matches_per_league v LEFT JOIN (SELECT league_id, COUNT(*) AS expected_count FROM \"Match\" GROUP BY league_id) m ON v.league_id = m.league_id WHERE (m.expected_count IS NULL AND (v.match_count IS NOT NULL AND v.match_count<>0)) OR (m.expected_count IS NOT NULL AND v.match_count<>m.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "league_id key is never NULL in the view",
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
SELECT m.league_id, COUNT(*) AS match_count FROM "Match" AS m GROUP BY m.league_id
```

---

## Skill `league_total_goals`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `league` (keyed) |
| status / version | active / v1 |
| skill id | sk_86eed0e66d4d3145 |
| output columns | `league_id`, `league`, `total_goals` |
| source tables | `League`, `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-league total goals across all matches computed as the sum of home_team_goal plus away_team_goal (treating NULL goals as 0).

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
      "top_5",
      "ORDER BY total_goals ASC",
      "LIMIT 5"
    ],
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "League",
      "Match"
    ],
    "source_columns": [
      "League.id",
      "League.name",
      "Match.league_id",
      "Match.home_team_goal",
      "Match.away_team_goal"
    ],
    "output_lineage": {
      "league_id": [
        "League.id"
      ],
      "league": [
        "League.name"
      ],
      "total_goals": [
        "Match.home_team_goal",
        "Match.away_team_goal"
      ]
    },
    "operators": [
      "filter",
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "league": "72cd1678e1e9160e",
      "match": "a56b9117c06fb4c3"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1038",
    "question": "List the top 5 leagues in ascending order of the number of goals made in all seasons combined.",
    "rewrite": "Task: Compute each league's total number of goals across all seasons by summing home_team_goal and away_team_goal for every match, then list the top 5 leagues with the smallest total goals (ascending order).\nRequired outputs: league (identifier/name as provided in the schema); total_goals (integer = SUM(home_team_goal + away_team_goal) across all matches for that league)\nFilters: Include all matches from all seasons (no season-based filtering).; Aggregate goals per league by summing home_team_goal and away_team_goal for every match belonging to that league.; Exclude leagues with NULL or missing league identifier or where goal values are NULL such that they cannot contribute to the sum (treat NULL goals as 0 if appropriate per schema handling).\nSort/limit: ORDER BY total_goals ASC LIMIT 5",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:36:31+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:36:34+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "league_id",
      "league",
      "total_goals"
    ],
    "row_count": 11,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "League.id=Match.league_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "View grain uniqueness: no duplicate rows per (league_id, league).",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, league, COUNT(*) AS cnt FROM league_total_goals GROUP BY league_id, league HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "total_goals matches recomputation from base tables (treating NULL goals as 0).",
        "sql": "SELECT COUNT(*) FROM league_total_goals v LEFT JOIN League l ON v.league_id = l.id WHERE (SELECT SUM(COALESCE(m.home_team_goal,0)+COALESCE(m.away_team_goal,0)) FROM Match m WHERE m.league_id = v.league_id) IS NOT NULL AND v.total_goals <> (SELECT SUM(COALESCE(m.home_team_goal,0)+COALESCE(m.away_team_goal,0)) FROM Match m WHERE m.league_id = v.league_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL: league_id and league should be present.",
        "sql": "SELECT COUNT(*) FROM league_total_goals WHERE league_id IS NULL OR league IS NULL",
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
SELECT League.id AS league_id, League.name AS league, SUM(COALESCE(Match.home_team_goal,0) + COALESCE(Match.away_team_goal,0)) AS total_goals FROM League JOIN Match ON League.id = Match.league_id WHERE League.id IS NOT NULL AND Match.league_id IS NOT NULL GROUP BY League.id, League.name
```

---

## Skill `player_avg_heading_accuracy_by_player_fifa_id`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_fifa_api_id`, `player_api_id`, `player_id`, `player_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_af7ac54c5c3e4a2d |
| output columns | `player_fifa_api_id`, `player_api_id`, `player_id`, `player_name`, `average_heading_accuracy` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player average heading accuracy computed from Player_Attributes, keyed by player_fifa_api_id along with player identifiers for joins

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
      "height > 180",
      "heading_accuracy IS NOT NULL",
      "player_fifa_api_id IS NOT NULL",
      "ORDER BY",
      "LIMIT",
      "top-10"
    ],
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Player",
      "Player_Attributes"
    ],
    "source_columns": [
      "Player.player_fifa_api_id",
      "Player.player_api_id",
      "Player.player_name",
      "Player.id",
      "Player_Attributes.player_fifa_api_id",
      "Player_Attributes.heading_accuracy"
    ],
    "output_lineage": {
      "player_fifa_api_id": [
        "Player.player_fifa_api_id"
      ],
      "player_api_id": [
        "Player.player_api_id"
      ],
      "player_id": [
        "Player.id"
      ],
      "player_name": [
        "Player.player_name"
      ],
      "average_heading_accuracy": [
        "Player_Attributes.player_fifa_api_id",
        "Player_Attributes.heading_accuracy"
      ]
    },
    "operators": [
      "filter",
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player": "032b398bb82740dc",
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1040",
    "question": "List the top 10 players' names whose heights are above 180 in descending order of average heading accuracy.",
    "rewrite": "Task: Compute the top 10 players (by name) whose heights are greater than 180, ranked in descending order by their average heading accuracy, where average heading accuracy is defined as SUM(heading_accuracy) divided by COUNT(player_fifa_api_id).\nRequired outputs: player_name (the player's name); average_heading_accuracy (the value computed as DIVIDE(SUM(heading_accuracy), COUNT(player_fifa_api_id)))\nFilters: height > 180; consider only rows where heading_accuracy is not NULL and player_fifa_api_id is not NULL\nSort/limit: ORDER BY average_heading_accuracy DESC LIMIT 10",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:37:20+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:37:23+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "player_fifa_api_id",
      "player_api_id",
      "player_id",
      "player_name",
      "average_heading_accuracy"
    ],
    "row_count": 11060,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Player_Attributes.player_fifa_api_id=Player.player_fifa_api_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No NULLs in key columns of the view (player_fifa_api_id, player_api_id, player_id, player_name)",
        "sql": "SELECT COUNT(*) FROM player_avg_heading_accuracy_by_player_fifa_id WHERE player_fifa_api_id IS NULL OR player_api_id IS NULL OR player_id IS NULL OR player_name IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "average_heading_accuracy equals the average of heading_accuracy from Player_Attributes for that player_fifa_api_id (recomputed from base tables)",
        "sql": "SELECT COUNT(*) FROM player_avg_heading_accuracy_by_player_fifa_id v LEFT JOIN Player_Attributes pa ON pa.player_fifa_api_id = v.player_fifa_api_id AND pa.heading_accuracy IS NOT NULL GROUP BY v.player_fifa_api_id HAVING ABS(v.average_heading_accuracy - (SUM(pa.heading_accuracy)*1.0/COUNT(pa.player_fifa_api_id))) > 1e-9 LIMIT 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View does not introduce duplicate rows for the declared grain (player_fifa_api_id, player_api_id, player_id, player_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_fifa_api_id, player_api_id, player_id, player_name, COUNT(*) AS cnt FROM player_avg_heading_accuracy_by_player_fifa_id GROUP BY player_fifa_api_id, player_api_id, player_id, player_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 1,
    "selected": 1,
    "included": 1,
    "referenced": 1,
    "executed": 1,
    "inconclusive": 1,
    "negative": 1,
    "negative_subgoals": [
      "Task: Retrieve the heading accuracy statistic/value for the player named 'Ariel Borysiuk'.\nRequired outputs: player name (must be 'Ariel Borysiuk'); heading accuracy (the value or percentage representing heading accuracy for that player)\nFilters: player name equals 'Ariel Borysiuk'; only return the heading accuracy metric associated with that player"
    ],
    "last_used": "bird_dev_1086"
  }
}
```

### Validated on (0)

—

### Counter-examples (1)

- What's the heading accuracy of Ariel Borysiuk?

### Executable SQL body

```sql
SELECT p.player_fifa_api_id, p.player_api_id, p.id AS player_id, p.player_name, SUM(pa.heading_accuracy) * 1.0 / COUNT(pa.player_fifa_api_id) AS average_heading_accuracy FROM Player p JOIN Player_Attributes pa ON pa.player_fifa_api_id = p.player_fifa_api_id WHERE pa.heading_accuracy IS NOT NULL AND pa.player_fifa_api_id IS NOT NULL GROUP BY p.player_fifa_api_id, p.player_api_id, p.id, p.player_name
```

---

## Skill `league_season_avg_home_away_goals`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_7073ae1b15cb397d |
| output columns | `league_id`, `season`, `avg_home_goals`, `avg_away_goals` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per league and season average goals scored by home and away teams (one row per league-season) to compare home vs away scoring

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
      "2009/2010"
    ],
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Match"
    ],
    "source_columns": [
      "Match.league_id",
      "Match.season",
      "Match.home_team_goal",
      "Match.away_team_goal"
    ],
    "output_lineage": {
      "league_id": [
        "Match.league_id"
      ],
      "season": [
        "Match.season"
      ],
      "avg_home_goals": [
        "Match.home_team_goal"
      ],
      "avg_away_goals": [
        "Match.away_team_goal"
      ]
    },
    "operators": [
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1042",
    "question": "List the name of leagues in which the average goals by the home team is higher than the away team in the 2009/2010 season.",
    "rewrite": "Task: Return the names of leagues for the 2009/2010 season where the average goals scored by the home team is greater than the average goals scored by the away team.\nRequired outputs: League.name (the league name)\nFilters: season = '2009/2010'; only include leagues where AVG(home_team_goal) > AVG(away_team_goal) computed across all matches in that league and season",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:38:14+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:38:17+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "league_id",
      "season",
      "avg_home_goals",
      "avg_away_goals"
    ],
    "row_count": 88,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View has one row per (league_id, season) — detect duplicate league-season keys",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, season, COUNT(*) AS cnt FROM league_season_avg_home_away_goals GROUP BY league_id, season HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Averaged measures match recomputation from base table (avg_home_goals)",
        "sql": "SELECT COUNT(*) FROM (SELECT v.league_id, v.season FROM league_season_avg_home_away_goals v LEFT JOIN (SELECT league_id, season, AVG(home_team_goal) AS recomputed FROM \"Match\" GROUP BY league_id, season) b ON v.league_id = b.league_id AND v.season = b.season WHERE (b.recomputed IS NULL AND v.avg_home_goals IS NOT NULL) OR (b.recomputed IS NOT NULL AND ABS(v.avg_home_goals - b.recomputed) > 1e-6))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Averaged measures match recomputation from base table (avg_away_goals)",
        "sql": "SELECT COUNT(*) FROM (SELECT v.league_id, v.season FROM league_season_avg_home_away_goals v LEFT JOIN (SELECT league_id, season, AVG(away_team_goal) AS recomputed FROM \"Match\" GROUP BY league_id, season) b ON v.league_id = b.league_id AND v.season = b.season WHERE (b.recomputed IS NULL AND v.avg_away_goals IS NOT NULL) OR (b.recomputed IS NOT NULL AND ABS(v.avg_away_goals - b.recomputed) > 1e-6))",
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
SELECT Match.league_id, Match.season, AVG(Match.home_team_goal) AS avg_home_goals, AVG(Match.away_team_goal) AS avg_away_goals FROM "Match" GROUP BY Match.league_id, Match.season
```

---

## Skill `players_with_max_potential`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_628d28aac4b53db0 |
| output columns | `player_id`, `player_api_id`, `player_name`, `player_fifa_api_id`, `birthday`, `height`, `weight`, `player_attributes_id`, `pa_player_api_id`, `pa_player_fifa_api_id`, `attributes_date`, `overall_rating`, `potential`, `preferred_foot`, `attacking_work_rate`, `defensive_work_rate`, `crossing`, `finishing`, `heading_accuracy`, `short_passing`, `volleys`, `dribbling`, `curve`, `free_kick_accuracy`, `long_passing`, `ball_control`, `acceleration`, `sprint_speed`, `agility`, `reactions`, `balance`, `shot_power`, `jumping`, `stamina`, `strength`, `long_shots`, `aggression`, `interceptions`, `positioning`, `vision`, `penalties`, `marking`, `standing_tackle`, `sliding_tackle`, `gk_diving`, `gk_handling`, `gk_kicking`, `gk_positioning`, `gk_reflexes` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

All players (with their attributes) whose potential equals the maximum potential value across the Player_Attributes table.

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
    "contract_version": 3,
    "grain_basis": "verified_unique",
    "lineage": [
      "Player",
      "Player_Attributes"
    ],
    "source_columns": [
      "Player.player_api_id",
      "Player.player_name",
      "Player.player_fifa_api_id",
      "Player.birthday",
      "Player.height",
      "Player.weight",
      "Player_Attributes.overall_rating",
      "Player_Attributes.potential",
      "Player_Attributes.preferred_foot",
      "Player_Attributes.attacking_work_rate",
      "Player_Attributes.defensive_work_rate",
      "Player_Attributes.crossing",
      "Player_Attributes.finishing",
      "Player_Attributes.heading_accuracy",
      "Player_Attributes.short_passing",
      "Player_Attributes.volleys",
      "Player_Attributes.dribbling",
      "Player_Attributes.curve",
      "Player_Attributes.free_kick_accuracy",
      "Player_Attributes.long_passing",
      "Player_Attributes.ball_control",
      "Player_Attributes.acceleration",
      "Player_Attributes.sprint_speed",
      "Player_Attributes.agility",
      "Player_Attributes.reactions",
      "Player_Attributes.balance",
      "Player_Attributes.shot_power",
      "Player_Attributes.jumping",
      "Player_Attributes.stamina",
      "Player_Attributes.strength",
      "Player_Attributes.long_shots",
      "Player_Attributes.aggression",
      "Player_Attributes.interceptions",
      "Player_Attributes.positioning",
      "Player_Attributes.vision",
      "Player_Attributes.penalties",
      "Player_Attributes.marking",
      "Player_Attributes.standing_tackle",
      "Player_Attributes.sliding_tackle",
      "Player_Attributes.gk_diving",
      "Player_Attributes.gk_handling",
      "Player_Attributes.gk_kicking",
      "Player_Attributes.gk_positioning",
      "Player_Attributes.gk_reflexes",
      "Player.id",
      "Player_Attributes.id",
      "Player_Attributes.player_api_id",
      "Player_Attributes.player_fifa_api_id",
      "Player_Attributes.date"
    ],
    "output_lineage": {
      "player_id": [
        "Player.id"
      ],
      "player_api_id": [
        "Player.player_api_id"
      ],
      "player_name": [
        "Player.player_name"
      ],
      "player_fifa_api_id": [
        "Player.player_fifa_api_id"
      ],
      "birthday": [
        "Player.birthday"
      ],
      "height": [
        "Player.height"
      ],
      "weight": [
        "Player.weight"
      ],
      "player_attributes_id": [
        "Player_Attributes.id"
      ],
      "pa_player_api_id": [
        "Player_Attributes.player_api_id"
      ],
      "pa_player_fifa_api_id": [
        "Player_Attributes.player_fifa_api_id"
      ],
      "attributes_date": [
        "Player_Attributes.date"
      ],
      "overall_rating": [
        "Player_Attributes.overall_rating"
      ],
      "potential": [
        "Player_Attributes.potential"
      ],
      "preferred_foot": [
        "Player_Attributes.preferred_foot"
      ],
      "attacking_work_rate": [
        "Player_Attributes.attacking_work_rate"
      ],
      "defensive_work_rate": [
        "Player_Attributes.defensive_work_rate"
      ],
      "crossing": [
        "Player_Attributes.crossing"
      ],
      "finishing": [
        "Player_Attributes.finishing"
      ],
      "heading_accuracy": [
        "Player_Attributes.heading_accuracy"
      ],
      "short_passing": [
        "Player_Attributes.short_passing"
      ],
      "volleys": [
        "Player_Attributes.volleys"
      ],
      "dribbling": [
        "Player_Attributes.dribbling"
      ],
      "curve": [
        "Player_Attributes.curve"
      ],
      "free_kick_accuracy": [
        "Player_Attributes.free_kick_accuracy"
      ],
      "long_passing": [
        "Player_Attributes.long_passing"
      ],
      "ball_control": [
        "Player_Attributes.ball_control"
      ],
      "acceleration": [
        "Player_Attributes.acceleration"
      ],
      "sprint_speed": [
        "Player_Attributes.sprint_speed"
      ],
      "agility": [
        "Player_Attributes.agility"
      ],
      "reactions": [
        "Player_Attributes.reactions"
      ],
      "balance": [
        "Player_Attributes.balance"
      ],
      "shot_power": [
        "Player_Attributes.shot_power"
      ],
      "jumping": [
        "Player_Attributes.jumping"
      ],
      "stamina": [
        "Player_Attributes.stamina"
      ],
      "strength": [
        "Player_Attributes.strength"
      ],
      "long_shots": [
        "Player_Attributes.long_shots"
      ],
      "aggression": [
        "Player_Attributes.aggression"
      ],
      "interceptions": [
        "Player_Attributes.interceptions"
      ],
      "positioning": [
        "Player_Attributes.positioning"
      ],
      "vision": [
        "Player_Attributes.vision"
      ],
      "penalties": [
        "Player_Attributes.penalties"
      ],
      "marking": [
        "Player_Attributes.marking"
      ],
      "standing_tackle": [
        "Player_Attributes.standing_tackle"
      ],
      "sliding_tackle": [
        "Player_Attributes.sliding_tackle"
      ],
      "gk_diving": [
        "Player_Attributes.gk_diving"
      ],
      "gk_handling": [
        "Player_Attributes.gk_handling"
      ],
      "gk_kicking": [
        "Player_Attributes.gk_kicking"
      ],
      "gk_positioning": [
        "Player_Attributes.gk_positioning"
      ],
      "gk_reflexes": [
        "Player_Attributes.gk_reflexes"
      ]
    },
    "operators": [
      "filter",
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player": "032b398bb82740dc",
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {
      "player": "11060:11075",
      "player_attributes": "183978:183978"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1051",
    "question": "List all the football player with the highest potential score.",
    "rewrite": "Task: Return every football player whose potential equals the maximum potential value in the dataset.\nRequired outputs: player (all columns/attributes for each player) or at minimum the player's identifying columns such as name and id and the potential value\nFilters: potential = MAX(potential) across all players (i.e., only include rows where potential is equal to the highest potential value present in the table)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:41:18+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:41:20+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "player_api_id",
      "player_name",
      "player_fifa_api_id",
      "birthday",
      "height",
      "weight",
      "player_attributes_id",
      "pa_player_api_id",
      "pa_player_fifa_api_id",
      "attributes_date",
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
    "row_count": 6,
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
        "purpose": "View contains only rows whose pa.potential equals the global maximum potential from Player_Attributes",
        "sql": "SELECT COUNT(*) FROM players_with_max_potential v WHERE v.potential IS DISTINCT FROM (SELECT MAX(potential) FROM Player_Attributes)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "player_attributes_id is unique in the view (no duplicate rows at the declared grain)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_attributes_id, COUNT(*) AS cnt FROM players_with_max_potential GROUP BY player_attributes_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row corresponds to an existing Player_Attributes row (no phantom rows) and values match by id",
        "sql": "SELECT COUNT(*) FROM players_with_max_potential v LEFT JOIN Player_Attributes pa ON pa.id = v.player_attributes_id WHERE pa.id IS NULL OR (pa.player_api_id IS NOT v.pa_player_api_id OR pa.player_fifa_api_id IS NOT v.pa_player_fifa_api_id OR pa.date IS NOT v.attributes_date OR pa.overall_rating IS NOT v.overall_rating OR pa.potential IS NOT v.potential)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 2,
    "selected": 1,
    "included": 1,
    "referenced": 1,
    "executed": 1,
    "inconclusive": 1,
    "positive": 1,
    "positive_subgoals": [
      "Task: Find the name(s) of the player(s) whose potential equals the maximum potential value (MAX(potential)).\nRequired outputs: name (the player's name)\nFilters: potential = MAX(potential) across all players (i.e., select rows where the player's potential equals the global maximum potential value)"
    ],
    "last_used": "bird_dev_1123"
  }
}
```

### Validated on (1)

- What is the name of players with the highest potential?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT p.id AS player_id, p.player_api_id, p.player_name, p.player_fifa_api_id, p.birthday, p.height, p.weight, pa.id AS player_attributes_id, pa.player_api_id AS pa_player_api_id, pa.player_fifa_api_id AS pa_player_fifa_api_id, pa.date AS attributes_date, pa.overall_rating, pa.potential, pa.preferred_foot, pa.attacking_work_rate, pa.defensive_work_rate, pa.crossing, pa.finishing, pa.heading_accuracy, pa.short_passing, pa.volleys, pa.dribbling, pa.curve, pa.free_kick_accuracy, pa.long_passing, pa.ball_control, pa.acceleration, pa.sprint_speed, pa.agility, pa.reactions, pa.balance, pa.shot_power, pa.jumping, pa.stamina, pa.strength, pa.long_shots, pa.aggression, pa.interceptions, pa.positioning, pa.vision, pa.penalties, pa.marking, pa.standing_tackle, pa.sliding_tackle, pa.gk_diving, pa.gk_handling, pa.gk_kicking, pa.gk_positioning, pa.gk_reflexes FROM Player p JOIN Player_Attributes pa ON pa.player_api_id = p.player_api_id WHERE pa.potential = (SELECT MAX(potential) FROM Player_Attributes)
```

---

## Skill `player_latest_attributes_with_player_info`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `player_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_543d6239b3382e2b |
| output columns | `player_id`, `player_api_id`, `player_fifa_api_id`, `player_name`, `birthday`, `player_attributes_id`, `overall_rating`, `attributes_date` |
| source tables | `Player_Attributes`, `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player attributes joined to player basic info (one row per player-attributes record) including birthday and overall_rating to support queries about players and their attribute values.

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
      "MAX(overall_rating)"
    ],
    "contract_version": 3,
    "grain_basis": "verified_unique",
    "lineage": [
      "Player_Attributes",
      "Player"
    ],
    "source_columns": [
      "Player.player_api_id",
      "Player.player_fifa_api_id",
      "Player.player_name",
      "Player.birthday",
      "Player_Attributes.overall_rating",
      "Player.id",
      "Player_Attributes.id",
      "Player_Attributes.date",
      "Player_Attributes.player_api_id"
    ],
    "output_lineage": {
      "player_id": [
        "Player.id"
      ],
      "player_api_id": [
        "Player.player_api_id"
      ],
      "player_fifa_api_id": [
        "Player.player_fifa_api_id"
      ],
      "player_name": [
        "Player.player_name"
      ],
      "birthday": [
        "Player.birthday"
      ],
      "player_attributes_id": [
        "Player_Attributes.id"
      ],
      "overall_rating": [
        "Player_Attributes.overall_rating"
      ],
      "attributes_date": [
        "Player_Attributes.date"
      ]
    },
    "operators": [
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203",
      "player": "032b398bb82740dc"
    },
    "data_fingerprints": {
      "player_attributes": "183978:183978",
      "player": "11060:11075"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1055",
    "question": "When is the birthday of the football player who has the highest overall rating?",
    "rewrite": "Task: Return the birthdate (birthday) of the football player whose overall_rating is the maximum value in the dataset.\nRequired outputs: birthday (the player's birthdate)\nFilters: overall_rating = MAX(overall_rating)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:42:35+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:42:38+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "player_api_id",
      "player_fifa_api_id",
      "player_name",
      "birthday",
      "player_attributes_id",
      "overall_rating",
      "attributes_date"
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
        "purpose": "No duplicate rows per grain: player_attributes_id should be unique in the view",
        "sql": "SELECT COUNT(*) FROM player_latest_attributes_with_player_info v JOIN (SELECT player_attributes_id FROM player_latest_attributes_with_player_info GROUP BY player_attributes_id HAVING COUNT(*)>1) d USING (player_attributes_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row corresponds to an existing Player_Attributes row (no phantom rows introduced by the join)",
        "sql": "SELECT COUNT(*) FROM player_latest_attributes_with_player_info v LEFT JOIN Player_Attributes pa ON v.player_attributes_id = pa.id WHERE pa.id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "overall_rating in the view matches the value in the base Player_Attributes table",
        "sql": "SELECT COUNT(*) FROM player_latest_attributes_with_player_info v JOIN Player_Attributes pa ON v.player_attributes_id = pa.id WHERE (v.overall_rating IS NOT pa.overall_rating) OR (v.overall_rating IS NULL AND pa.overall_rating IS NOT NULL) OR (v.overall_rating IS NOT NULL AND pa.overall_rating IS NULL)",
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
SELECT P.id AS player_id, P.player_api_id, P.player_fifa_api_id, P.player_name, P.birthday, PA.id AS player_attributes_id, PA.overall_rating, PA.date AS attributes_date FROM Player_Attributes PA JOIN Player P ON PA.player_api_id = P.player_api_id
```

---

## Skill `players_with_birthday`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_e21198fd5549a454 |
| output columns | `player_id`, `player_api_id`, `player_fifa_api_id`, `player_name`, `birthday` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

All players with their id, FIFA ids, name, and birthday (for filtering or joining by birth year)

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
      "'1990'"
    ],
    "contract_version": 3,
    "grain_basis": "primary_key",
    "lineage": [
      "Player"
    ],
    "source_columns": [
      "Player.player_api_id",
      "Player.player_fifa_api_id",
      "Player.player_name",
      "Player.birthday",
      "Player.id"
    ],
    "output_lineage": {
      "player_id": [
        "Player.id"
      ],
      "player_api_id": [
        "Player.player_api_id"
      ],
      "player_fifa_api_id": [
        "Player.player_fifa_api_id"
      ],
      "player_name": [
        "Player.player_name"
      ],
      "birthday": [
        "Player.birthday"
      ]
    },
    "operators": [
      "filter",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player": "032b398bb82740dc"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1060",
    "question": "How many players were born after 1990?",
    "rewrite": "Task: Count the number of players whose birthday is after the year 1990.\nRequired outputs: count\nFilters: players where strftime('%Y', birthday) > '1990' (i.e., birth year strictly greater than 1990)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:44:34+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:44:36+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "player_api_id",
      "player_fifa_api_id",
      "player_name",
      "birthday"
    ],
    "row_count": 11060,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View rows must have non-NULL player_id (primary key of the grain)",
        "sql": "SELECT COUNT(*) FROM players_with_birthday WHERE player_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view must correspond to a Player row with the same id and a non-NULL birthday (i.e., the view should not introduce rows or miss the WHERE condition)",
        "sql": "SELECT COUNT(*) FROM players_with_birthday v LEFT JOIN Player p ON v.player_id = p.id WHERE p.id IS NULL OR p.birthday IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "There must be no duplicate player_id values in the view (grain uniqueness)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_id, COUNT(*) AS cnt FROM players_with_birthday GROUP BY player_id HAVING cnt > 1)",
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
SELECT Player.id AS player_id, Player.player_api_id, Player.player_fifa_api_id, Player.player_name, Player.birthday FROM Player WHERE Player.birthday IS NOT NULL
```

---

## Skill `team_build_up_play_passing`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `team_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_7292dbae15eed3fb |
| output columns | `team_api_id`, `team_id`, `team_short_name`, `date`, `buildUpPlayPassing`, `team_attributes_id` |
| source tables | `Team`, `Team_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-team build up play passing values from Team_Attributes joined to Team identifiers and short name, useful for filtering or joining teams by their buildUpPlayPassing metric.

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
      "> 70"
    ],
    "contract_version": 3,
    "grain_basis": "verified_unique",
    "lineage": [
      "Team",
      "Team_Attributes"
    ],
    "source_columns": [
      "Team.team_api_id",
      "Team.team_short_name",
      "Team_Attributes.date",
      "Team_Attributes.buildUpPlayPassing",
      "Team.id",
      "Team_Attributes.id",
      "Team_Attributes.team_api_id"
    ],
    "output_lineage": {
      "team_api_id": [
        "Team.team_api_id"
      ],
      "team_id": [
        "Team.id"
      ],
      "team_short_name": [
        "Team.team_short_name"
      ],
      "date": [
        "Team_Attributes.date"
      ],
      "buildUpPlayPassing": [
        "Team_Attributes.buildUpPlayPassing"
      ],
      "team_attributes_id": [
        "Team_Attributes.id"
      ]
    },
    "operators": [
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "team": "a19728cad815ec8a",
      "team_attributes": "a8661cb8da0875ec"
    },
    "data_fingerprints": {
      "team": "299:51606",
      "team_attributes": "1458:1458"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1067",
    "question": "Which teams have build up play passing more than 70? Please list their short names.",
    "rewrite": "Task: Return the short names of teams whose build up play passing value is greater than 70.\nRequired outputs: team_short_name\nFilters: buildUpPlayPassing > 70",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:47:50+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:47:52+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "team_api_id",
      "team_id",
      "team_short_name",
      "date",
      "buildUpPlayPassing",
      "team_attributes_id"
    ],
    "row_count": 1458,
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
        "purpose": "No duplicate rows at the declared grain team_attributes_id (each team_attributes_id should appear at most once)",
        "sql": "SELECT COUNT(*) FROM (SELECT team_attributes_id, COUNT(*) AS cnt FROM team_build_up_play_passing GROUP BY team_attributes_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All key columns from the view that come from base tables are NOT NULL (team_attributes_id and team_id should not be NULL)",
        "sql": "SELECT COUNT(*) FROM team_build_up_play_passing WHERE team_attributes_id IS NULL OR team_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "buildUpPlayPassing in the view matches the value in Team_Attributes for the same team_attributes_id",
        "sql": "SELECT COUNT(*) FROM team_build_up_play_passing v LEFT JOIN Team_Attributes t ON v.team_attributes_id = t.id WHERE (t.id IS NULL) OR (v.buildUpPlayPassing IS NOT t.buildUpPlayPassing AND NOT (v.buildUpPlayPassing IS NULL AND t.buildUpPlayPassing IS NULL))",
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
SELECT Team.team_api_id, Team.id AS team_id, Team.team_short_name, Team_Attributes.date, Team_Attributes.buildUpPlayPassing, Team_Attributes.id AS team_attributes_id FROM Team JOIN Team_Attributes ON Team.team_api_id = Team_Attributes.team_api_id
```

---

## Skill `player_attributes_with_player_demographics`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `player_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_885a29bd524829ff |
| output columns | `player_attributes_id`, `player_api_id`, `player_fifa_api_id_attributes`, `attribute_date`, `overall_rating`, `player_id`, `player_name`, `player_player_api_id`, `player_fifa_api_id_player`, `height`, `weight` |
| source tables | `Player_Attributes`, `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Denormalized join of Player_Attributes with Player to associate attribute records with player demographic fields (height, weight) and player identifiers for downstream filtering and aggregation.

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
      "strftime('%Y', pa.date) BETWEEN '2010' AND '2015'",
      "p.height > 170",
      "pa.overall_rating IS NOT NULL"
    ],
    "contract_version": 3,
    "grain_basis": "verified_unique",
    "lineage": [
      "Player_Attributes",
      "Player"
    ],
    "source_columns": [
      "Player_Attributes.player_api_id",
      "Player_Attributes.overall_rating",
      "Player.player_name",
      "Player.height",
      "Player.weight",
      "Player_Attributes.id",
      "Player_Attributes.player_fifa_api_id",
      "Player_Attributes.date",
      "Player.id",
      "Player.player_api_id",
      "Player.player_fifa_api_id"
    ],
    "output_lineage": {
      "player_attributes_id": [
        "Player_Attributes.id"
      ],
      "player_api_id": [
        "Player_Attributes.player_api_id"
      ],
      "player_fifa_api_id_attributes": [
        "Player_Attributes.player_fifa_api_id"
      ],
      "attribute_date": [
        "Player_Attributes.date"
      ],
      "overall_rating": [
        "Player_Attributes.overall_rating"
      ],
      "player_id": [
        "Player.id"
      ],
      "player_name": [
        "Player.player_name"
      ],
      "player_player_api_id": [
        "Player.player_api_id"
      ],
      "player_fifa_api_id_player": [
        "Player.player_fifa_api_id"
      ],
      "height": [
        "Player.height"
      ],
      "weight": [
        "Player.weight"
      ]
    },
    "operators": [
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203",
      "player": "032b398bb82740dc"
    },
    "data_fingerprints": {
      "player_attributes": "183978:183978",
      "player": "11060:11075"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1068",
    "question": "From 2010 to 2015, what was the average overall rating of players who are higher than 170?",
    "rewrite": "Task: Compute the average overall rating of players whose height is greater than 170 for records dated between 2010 and 2015 inclusive.\nRequired outputs: average_overall_rating (numeric): the average of the overall rating values for the filtered records\nFilters: strftime('%Y', date) BETWEEN '2010' AND '2015'; height > 170",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:48:11+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:48:14+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "player_attributes_id",
      "player_api_id",
      "player_fifa_api_id_attributes",
      "attribute_date",
      "overall_rating",
      "player_id",
      "player_name",
      "player_player_api_id",
      "player_fifa_api_id_player",
      "height",
      "weight"
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
        "purpose": "View grain uniqueness: no two rows in the view share the same player_attributes_id",
        "sql": "SELECT COUNT(*) FROM (SELECT player_attributes_id, COUNT(*) AS cnt FROM player_attributes_with_player_demographics GROUP BY player_attributes_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows in the view must correspond to an existing Player_Attributes record (no spurious rows)",
        "sql": "SELECT COUNT(*) FROM player_attributes_with_player_demographics v LEFT JOIN Player_Attributes pa ON v.player_attributes_id = pa.id WHERE pa.id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Join did not change attribute measures: overall_rating in the view must match overall_rating in Player_Attributes for that id",
        "sql": "SELECT COUNT(*) FROM player_attributes_with_player_demographics v JOIN Player_Attributes pa ON v.player_attributes_id = pa.id WHERE (v.overall_rating IS NOT pa.overall_rating) AND NOT (v.overall_rating IS NULL AND pa.overall_rating IS NULL)",
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
  pa.id AS player_attributes_id,
  pa.player_api_id,
  pa.player_fifa_api_id AS player_fifa_api_id_attributes,
  pa.date AS attribute_date,
  pa.overall_rating,
  p.id AS player_id,
  p.player_name,
  p.player_api_id AS player_player_api_id,
  p.player_fifa_api_id AS player_fifa_api_id_player,
  p.height,
  p.weight
FROM Player_Attributes pa
JOIN Player p
  ON pa.player_api_id = p.player_api_id
```

---

## Skill `player_min_height`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_8e35cc89a28d5257 |
| output columns | `player_id`, `player_api_id`, `player_name`, `player_fifa_api_id`, `height` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Players whose height equals the minimum non-null player height in the Player table (returns player identifiers and height).

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
    "contract_version": 3,
    "grain_basis": "primary_key",
    "lineage": [
      "Player"
    ],
    "source_columns": [
      "Player.player_api_id",
      "Player.player_name",
      "Player.player_fifa_api_id",
      "Player.height",
      "Player.id"
    ],
    "output_lineage": {
      "player_id": [
        "Player.id"
      ],
      "player_api_id": [
        "Player.player_api_id"
      ],
      "player_name": [
        "Player.player_name"
      ],
      "player_fifa_api_id": [
        "Player.player_fifa_api_id"
      ],
      "height": [
        "Player.height"
      ]
    },
    "operators": [
      "filter",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player": "032b398bb82740dc"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1069",
    "question": "Which football player has the shortest height?",
    "rewrite": "Task: Find the football player(s) whose height equals the minimum height value in the dataset.\nRequired outputs: player (or player identifier) and height\nFilters: height = MIN(height)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:48:33+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:48:35+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "player_api_id",
      "player_name",
      "player_fifa_api_id",
      "height"
    ],
    "row_count": 1,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate player_id in the view (grain uniqueness)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_id, COUNT(*) AS cnt FROM player_min_height GROUP BY player_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view has height equal to the minimum non-null height in Player",
        "sql": "SELECT COUNT(*) FROM player_min_height WHERE height IS NULL OR height <> (SELECT MIN(height) FROM Player WHERE height IS NOT NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "The view did not omit any player who has the minimum non-null height (completeness)",
        "sql": "SELECT COUNT(*) FROM Player p WHERE p.height IS NOT NULL AND p.height = (SELECT MIN(height) FROM Player WHERE height IS NOT NULL) AND NOT EXISTS (SELECT 1 FROM player_min_height v WHERE v.player_id = p.id)",
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
SELECT id AS player_id, player_api_id, player_name, player_fifa_api_id, height
FROM Player
WHERE height IS NOT NULL
  AND height = (SELECT MIN(height) FROM Player WHERE height IS NOT NULL)
```

---

## Skill `player_attributes_latest_balance_potential`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `player_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_f9063bcc5c5c85df |
| output columns | `player_id`, `player_api_id`, `player_name`, `player_attributes_id`, `player_fifa_api_id`, `date`, `potential`, `balance` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Denormalized join of players with their player_attributes rows including potential and balance, useful to filter or aggregate players by attribute values like potential or balance.

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
      "61",
      "MAX(balance)"
    ],
    "contract_version": 3,
    "grain_basis": "verified_unique",
    "lineage": [
      "Player",
      "Player_Attributes"
    ],
    "source_columns": [
      "Player.player_api_id",
      "Player.player_name",
      "Player_Attributes.player_fifa_api_id",
      "Player_Attributes.date",
      "Player_Attributes.potential",
      "Player_Attributes.balance",
      "Player.id",
      "Player_Attributes.id",
      "Player_Attributes.player_api_id"
    ],
    "output_lineage": {
      "player_id": [
        "Player.id"
      ],
      "player_api_id": [
        "Player.player_api_id"
      ],
      "player_name": [
        "Player.player_name"
      ],
      "player_attributes_id": [
        "Player_Attributes.id"
      ],
      "player_fifa_api_id": [
        "Player_Attributes.player_fifa_api_id"
      ],
      "date": [
        "Player_Attributes.date"
      ],
      "potential": [
        "Player_Attributes.potential"
      ],
      "balance": [
        "Player_Attributes.balance"
      ]
    },
    "operators": [
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player": "032b398bb82740dc",
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {
      "player": "11060:11075",
      "player_attributes": "183978:183978"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1075",
    "question": "List all the football player with the highest balance score and potential score of 61.",
    "rewrite": "Task: Return all football players (rows) whose potential score equals 61 and whose balance score equals the maximum balance value among all players.\nRequired outputs: player identifier (e.g., name or id) and any other requested player attributes; must include at least the player's balance score and potential score\nFilters: potential = 61; balance = MAX(balance)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:50:45+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:50:48+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "player_api_id",
      "player_name",
      "player_attributes_id",
      "player_fifa_api_id",
      "date",
      "potential",
      "balance"
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
        "purpose": "View grain: player_attributes_id must be unique (no duplicate rows for same player_attributes_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_attributes_id, COUNT(*) AS cnt FROM player_attributes_latest_balance_potential GROUP BY player_attributes_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Join completeness: every row in Player_Attributes that has a matching player_api_id in Player should appear in the view (no unexpected drops) — count Player_Attributes rows with matching Player but mi",
        "sql": "SELECT COUNT(*) FROM Player_Attributes pa JOIN Player p ON pa.player_api_id = p.player_api_id WHERE NOT EXISTS (SELECT 1 FROM player_attributes_latest_balance_potential v WHERE v.player_attributes_id = pa.id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Measure reconciliation: potential and balance in the view must match the source Player_Attributes values for the same player_attributes_id",
        "sql": "SELECT COUNT(*) FROM player_attributes_latest_balance_potential v LEFT JOIN Player_Attributes pa ON pa.id = v.player_attributes_id WHERE pa.id IS NULL OR ( (pa.potential IS NOT v.potential) OR (pa.balance IS NOT v.balance) )",
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
SELECT p.id AS player_id, p.player_api_id, p.player_name, pa.id AS player_attributes_id, pa.player_fifa_api_id, pa.date, pa.potential, pa.balance FROM Player p JOIN Player_Attributes pa ON pa.player_api_id = p.player_api_id
```

---

## Skill `player_ball_control_by_attribute_record`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_affb2e81ff7b8a67 |
| output columns | `player_id`, `player_api_id`, `player_fifa_api_id`, `player_name`, `player_attributes_id`, `date`, `ball_control` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player per-player_attributes-record ball_control values (ties player to specific Player_Attributes records) useful for computing player-level averages and comparisons

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
      "'Abdou Diallo'",
      "'Aaron Appindangoye'"
    ],
    "contract_version": 3,
    "grain_basis": "verified_unique",
    "lineage": [
      "Player",
      "Player_Attributes"
    ],
    "source_columns": [
      "Player.player_api_id",
      "Player.player_fifa_api_id",
      "Player.player_name",
      "Player_Attributes.date",
      "Player_Attributes.ball_control",
      "Player.id",
      "Player_Attributes.id",
      "Player_Attributes.player_api_id"
    ],
    "output_lineage": {
      "player_id": [
        "Player.id"
      ],
      "player_api_id": [
        "Player.player_api_id"
      ],
      "player_fifa_api_id": [
        "Player.player_fifa_api_id"
      ],
      "player_name": [
        "Player.player_name"
      ],
      "player_attributes_id": [
        "Player_Attributes.id"
      ],
      "date": [
        "Player_Attributes.date"
      ],
      "ball_control": [
        "Player_Attributes.ball_control"
      ]
    },
    "operators": [
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player": "032b398bb82740dc",
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {
      "player": "11060:11075",
      "player_attributes": "183978:183978"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1076",
    "question": "What is the difference of the average ball control score between Abdou Diallo and Aaron Appindangoye\n?",
    "rewrite": "Task: Compute the difference between the average ball control score for player 'Abdou Diallo' and the average ball control score for player 'Aaron Appindangoye'.\nRequired outputs: difference: numeric value equal to AVG(ball_control WHERE player_name = 'Abdou Diallo') - AVG(ball_control WHERE player_name = 'Aaron Appindangoye')\nFilters: player_name = 'Abdou Diallo' for the first average; player_name = 'Aaron Appindangoye' for the second average",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:51:04+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:51:06+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "player_api_id",
      "player_fifa_api_id",
      "player_name",
      "player_attributes_id",
      "date",
      "ball_control"
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
        "purpose": "View grain uniqueness: each player_attributes_id should appear at most once in the view (no duplicate rows for the declared grain).",
        "sql": "SELECT COUNT(*) FROM (SELECT player_attributes_id, COUNT(*) AS cnt FROM player_ball_control_by_attribute_record GROUP BY player_attributes_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Ball_control value matches source Player_Attributes.ball_control for the joined player_attributes record (measure reconciliation).",
        "sql": "SELECT COUNT(*) FROM player_ball_control_by_attribute_record v LEFT JOIN Player_Attributes pa ON pa.id = v.player_attributes_id WHERE NOT ( (pa.ball_control IS NULL AND v.ball_control IS NULL) OR (pa.ball_control = v.ball_control) )",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Join integrity: every row's player_api_id in the view must match the Player table row for the linked player_attributes' player_api_id (no mismatched join between Player and Player_Attributes).",
        "sql": "SELECT COUNT(*) FROM player_ball_control_by_attribute_record v LEFT JOIN Player_Attributes pa ON pa.id = v.player_attributes_id LEFT JOIN Player p ON p.player_api_id = pa.player_api_id WHERE NOT (p.id = v.player_id AND p.player_api_id = v.player_api_id)",
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
SELECT p.id AS player_id, p.player_api_id, p.player_fifa_api_id, p.player_name, pa.id AS player_attributes_id, pa.date, pa.ball_control FROM Player p JOIN Player_Attributes pa ON pa.player_api_id = p.player_api_id
```

---

## Skill `player_max_overall_rating_per_player`

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

For each player (by player_api_id), the maximum overall_rating observed in Player_Attributes, with player identifiers to join back to Player.

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Player_Attributes"
    ],
    "source_columns": [
      "Player_Attributes.player_api_id",
      "Player_Attributes.overall_rating"
    ],
    "output_lineage": {
      "player_api_id": [
        "Player_Attributes.player_api_id"
      ],
      "max_overall_rating": [
        "Player_Attributes.overall_rating"
      ]
    },
    "operators": [
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1083",
    "question": "Which player has the strongest overall strength?",
    "rewrite": "Task: Find the player(s) whose overall_rating equals the maximum overall_rating across all players.\nRequired outputs: player identifier (e.g., player_name or player_id); overall_rating (the maximum overall_rating)\nFilters: overall_rating = MAX(overall_rating) over all rows (i.e., select rows where overall_rating equals the global maximum)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:53:16+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:53:19+00:00",
    "contract_version": 3,
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
        "purpose": "No NULL keys: ensure every row in the view has a non-NULL player_api_id (grain key not null).",
        "sql": "SELECT COUNT(*) FROM player_max_overall_rating_per_player WHERE player_api_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Aggregation correctness: each view row's max_overall_rating equals the MAX(overall_rating) computed from Player_Attributes for that player_api_id.",
        "sql": "SELECT COUNT(*) FROM player_max_overall_rating_per_player v LEFT JOIN (SELECT player_api_id, MAX(overall_rating) AS expected_max FROM Player_Attributes GROUP BY player_api_id) a ON v.player_api_id = a.player_api_id WHERE (v.max_overall_rating IS NOT a.expected_max) OR (v.max_overall_rating IS NULL AND a.expected_max IS NOT NULL) OR (v.max_overall_rating IS NOT NULL AND a.expected_max IS NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No extra rows: every player_api_id present in Player_Attributes appears exactly once in the view (no missing or duplicate player groups).",
        "sql": "SELECT (SELECT COUNT(DISTINCT player_api_id) FROM Player_Attributes) - (SELECT COUNT(*) FROM player_max_overall_rating_per_player) + (SELECT SUM(cnt-1) FROM (SELECT player_api_id, COUNT(*) AS cnt FROM player_max_overall_rating_per_player GROUP BY player_api_id) WHERE cnt>1)",
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
SELECT player_api_id, MAX(overall_rating) AS max_overall_rating FROM Player_Attributes GROUP BY player_api_id
```

---

## Skill `player_max_attribute_by_api_id`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_4077a6677cee7cb1 |
| output columns | `player_api_id`, `max_crossing` |
| source tables | `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each player_api_id, the maximum value observed for a numeric player attribute (crossing) from Player_Attributes, keeping keys to join to Player.

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
      "'Alexis'",
      "'Ariel Borysiuk'",
      "'Arouna Kone'",
      "crossing IS NOT NULL",
      "ORDER BY",
      "LIMIT",
      "specific attribute name occurrences"
    ],
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Player_Attributes"
    ],
    "source_columns": [
      "Player_Attributes.player_api_id",
      "Player_Attributes.crossing"
    ],
    "output_lineage": {
      "player_api_id": [
        "Player_Attributes.player_api_id"
      ],
      "max_crossing": [
        "Player_Attributes.crossing"
      ]
    },
    "operators": [
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1085",
    "question": "Which of these players performs the best in crossing actions, Alexis, Ariel Borysiuk or Arouna Kone?",
    "rewrite": "Task: Return which of the three players (Alexis, Ariel Borysiuk, Arouna Kone) has the maximum value for crossing (i.e., which player performs best in crossing actions) and that player's crossing value.\nRequired outputs: player name; crossing value (numeric)\nFilters: player name IN ('Alexis','Ariel Borysiuk','Arouna Kone')\nSort/limit: order by crossing DESC limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:53:58+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:54:01+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
      "max_crossing"
    ],
    "row_count": 11060,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View grain: each player_api_id appears at most once (no duplicate rows for the key).",
        "sql": "SELECT COUNT(*) FROM (SELECT player_api_id, COUNT(*) AS cnt FROM player_max_attribute_by_api_id GROUP BY player_api_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Measure correctness: max_crossing equals the MAX(crossing) computed from base table for that player_api_id.",
        "sql": "SELECT COUNT(*) FROM player_max_attribute_by_api_id v LEFT JOIN (SELECT player_api_id, MAX(crossing) AS expected_max FROM Player_Attributes GROUP BY player_api_id) b USING(player_api_id) WHERE (v.max_crossing IS NOT b.expected_max) OR (v.max_crossing IS NULL AND b.expected_max IS NOT NULL) OR (v.max_crossing IS NOT NULL AND b.expected_max IS NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys not NULL: player_api_id must not be NULL in the view (so rows are joinable to Player).",
        "sql": "SELECT COUNT(*) FROM player_max_attribute_by_api_id WHERE player_api_id IS NULL",
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
SELECT player_api_id, MAX(crossing) AS max_crossing
FROM Player_Attributes
GROUP BY player_api_id
```

---

## Skill `player_latest_attributes`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `player_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_3dc54fb9ca3ff7dd |
| output columns | `player_id`, `player_api_id`, `player_fifa_api_id`, `player_name`, `player_attributes_id`, `date`, `volleys`, `dribbling`, `overall_rating`, `potential` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Latest player attributes per player including key skill ratings (volleys, dribbling, overall_rating, potential) and attribute record id and date, joined to Player id and names for easy lookup.

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
    "contract_version": 3,
    "grain_basis": "verified_unique",
    "lineage": [
      "Player",
      "Player_Attributes"
    ],
    "source_columns": [
      "Player.player_api_id",
      "Player.player_fifa_api_id",
      "Player.player_name",
      "Player_Attributes.date",
      "Player_Attributes.volleys",
      "Player_Attributes.dribbling",
      "Player_Attributes.overall_rating",
      "Player_Attributes.potential",
      "Player.id",
      "Player_Attributes.id",
      "Player_Attributes.player_api_id"
    ],
    "output_lineage": {
      "player_id": [
        "Player.id"
      ],
      "player_api_id": [
        "Player.player_api_id"
      ],
      "player_fifa_api_id": [
        "Player.player_fifa_api_id"
      ],
      "player_name": [
        "Player.player_name"
      ],
      "player_attributes_id": [
        "Player_Attributes.id"
      ],
      "date": [
        "Player_Attributes.date"
      ],
      "volleys": [
        "Player_Attributes.volleys"
      ],
      "dribbling": [
        "Player_Attributes.dribbling"
      ],
      "overall_rating": [
        "Player_Attributes.overall_rating"
      ],
      "potential": [
        "Player_Attributes.potential"
      ]
    },
    "operators": [
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player": "032b398bb82740dc",
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {
      "player": "11060:11075",
      "player_attributes": "183978:183978"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1088",
    "question": "Please list the names of the players whose volley score and dribbling score are over 70.",
    "rewrite": "Task: Return the names of players who have both volley score greater than 70 and dribbling score greater than 70.\nRequired outputs: player name\nFilters: volley score > 70; dribbling score > 70",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:54:57+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:55:00+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "player_api_id",
      "player_fifa_api_id",
      "player_name",
      "player_attributes_id",
      "date",
      "volleys",
      "dribbling",
      "overall_rating",
      "potential"
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
        "purpose": "No duplicate rows at the declared grain (player_attributes_id should be unique)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_attributes_id, COUNT(*) AS cnt FROM player_latest_attributes GROUP BY player_attributes_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's player_api_id and player_name must match a Player row (join did not create rows with no matching player)",
        "sql": "SELECT COUNT(*) FROM player_latest_attributes pla LEFT JOIN Player p ON pla.player_api_id = p.player_api_id WHERE p.id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Measures pulled from Player_Attributes (volleys, dribbling, overall_rating, potential, date) should match the source table for the given player_attributes_id",
        "sql": "SELECT COUNT(*) FROM player_latest_attributes pla LEFT JOIN Player_Attributes pa ON pla.player_attributes_id = pa.id WHERE pa.id IS NOT NULL AND (pla.volleys IS NOT pa.volleys OR pla.dribbling IS NOT pa.dribbling OR pla.overall_rating IS NOT pa.overall_rating OR pla.potential IS NOT pa.potential OR pla.date IS NOT pa.date)",
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
SELECT p.id AS player_id, p.player_api_id, p.player_fifa_api_id, p.player_name, pa.id AS player_attributes_id, pa.date, pa.volleys, pa.dribbling, pa.overall_rating, pa.potential FROM Player p JOIN Player_Attributes pa ON pa.player_api_id = p.player_api_id
```

---

## Skill `player_with_attributes_by_player_api_id`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `id` (keyed) |
| status / version | active / v1 |
| skill id | sk_b00d544eb2b18704 |
| output columns | `player_api_id`, `player_name`, `birthday`, `player_fifa_api_id`, `pa_id`, `attribute_date`, `long_passing`, `id`, `player_fifa_api_id:1`, `player_api_id:1`, `date`, `overall_rating`, `potential`, `preferred_foot`, `attacking_work_rate`, `defensive_work_rate`, `crossing`, `finishing`, `heading_accuracy`, `short_passing`, `volleys`, `dribbling`, `curve`, `free_kick_accuracy`, `long_passing:1`, `ball_control`, `acceleration`, `sprint_speed`, `agility`, `reactions`, `balance`, `shot_power`, `jumping`, `stamina`, `strength`, `long_shots`, `aggression`, `interceptions`, `positioning`, `vision`, `penalties`, `marking`, `standing_tackle`, `sliding_tackle`, `gk_diving`, `gk_handling`, `gk_kicking`, `gk_positioning`, `gk_reflexes` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Denormalized relation joining players to their attribute records keyed by player_api_id, providing player identifiers, name, birthdate, and attribute fields for reuse in analyses (e.g., per-player attribute history or latest attribute)

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
    "contract_version": 3,
    "grain_basis": "verified_unique",
    "lineage": [
      "Player",
      "Player_Attributes"
    ],
    "source_columns": [
      "Player.player_api_id",
      "Player.player_name",
      "Player.birthday",
      "Player.player_fifa_api_id",
      "Player_Attributes.long_passing",
      "Player_Attributes.id",
      "Player_Attributes.date",
      "Player_Attributes.player_api_id"
    ],
    "output_lineage": {
      "player_api_id": [
        "Player.player_api_id"
      ],
      "player_name": [
        "Player.player_name"
      ],
      "birthday": [
        "Player.birthday"
      ],
      "player_fifa_api_id": [
        "Player.player_fifa_api_id"
      ],
      "pa_id": [
        "Player_Attributes.id"
      ],
      "attribute_date": [
        "Player_Attributes.date"
      ],
      "long_passing": [
        "Player_Attributes.long_passing"
      ],
      "id": [
        "Player_Attributes.id"
      ],
      "player_fifa_api_id:1": [],
      "player_api_id:1": [],
      "date": [
        "Player_Attributes.date"
      ],
      "overall_rating": [],
      "potential": [],
      "preferred_foot": [],
      "attacking_work_rate": [],
      "defensive_work_rate": [],
      "crossing": [],
      "finishing": [],
      "heading_accuracy": [],
      "short_passing": [],
      "volleys": [],
      "dribbling": [],
      "curve": [],
      "free_kick_accuracy": [],
      "long_passing:1": [],
      "ball_control": [],
      "acceleration": [],
      "sprint_speed": [],
      "agility": [],
      "reactions": [],
      "balance": [],
      "shot_power": [],
      "jumping": [],
      "stamina": [],
      "strength": [],
      "long_shots": [],
      "aggression": [],
      "interceptions": [],
      "positioning": [],
      "vision": [],
      "penalties": [],
      "marking": [],
      "standing_tackle": [],
      "sliding_tackle": [],
      "gk_diving": [],
      "gk_handling": [],
      "gk_kicking": [],
      "gk_positioning": [],
      "gk_reflexes": []
    },
    "operators": [
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player": "032b398bb82740dc",
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {
      "player": "11060:11075",
      "player_attributes": "183978:183978"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1090",
    "question": "What is the long passing score of the oldest player?",
    "rewrite": "Task: Find the long_passing value for the player who has the earliest (oldest) birth date.\nRequired outputs: long_passing\nFilters: player.birthdate is the minimum (earliest) date across all players\nSort/limit: order by player.birthdate asc limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:55:46+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:55:48+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
      "player_name",
      "birthday",
      "player_fifa_api_id",
      "pa_id",
      "attribute_date",
      "long_passing",
      "id",
      "player_fifa_api_id:1",
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
      "long_passing:1",
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
        "purpose": "No NULLs in the view's declared primary key 'id' (grain = ['id']) — ensures each row has an id",
        "sql": "SELECT COUNT(*) FROM player_with_attributes_by_player_api_id WHERE id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view originates from a Player row (join didn't create spurious player_api_id values) — check that player_api_id in the view exists in Player table",
        "sql": "SELECT COUNT(*) FROM player_with_attributes_by_player_api_id v WHERE NOT EXISTS (SELECT 1 FROM Player p WHERE p.player_api_id = v.player_api_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No duplicate rows per declared grain 'id' — ensures view respects uniqueness by id",
        "sql": "SELECT COUNT(*) FROM (SELECT id, COUNT(*) AS cnt FROM player_with_attributes_by_player_api_id GROUP BY id HAVING cnt > 1)",
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
SELECT Player.player_api_id, Player.player_name, Player.birthday, Player.player_fifa_api_id, Player_Attributes.id AS pa_id, Player_Attributes.date AS attribute_date, Player_Attributes.long_passing, Player_Attributes.* FROM Player LEFT JOIN Player_Attributes ON Player.player_api_id = Player_Attributes.player_api_id
```

---

## Skill `matches_per_league_season`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_d3678bbb56ceccc3 |
| output columns | `league_id`, `season`, `matches` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-league count of matches for each season (number of matches grouped by league and season).

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Match"
    ],
    "source_columns": [
      "Match.league_id",
      "Match.season"
    ],
    "output_lineage": {
      "league_id": [
        "Match.league_id"
      ],
      "season": [
        "Match.season"
      ],
      "matches": []
    },
    "operators": [
      "filter",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1092",
    "question": "Which league had the most matches in the 2008/2009 season?",
    "rewrite": "Task: Find the league that had the maximum number of matches in the season '2008/2009'.\nRequired outputs: league_id: the identifier of the league with the most matches in season '200/2009'; matches: the number of matches played by that league in season '200/2009'\nFilters: season = '2008/2009'; consider only rows where matches is defined (non-null) for that league in that season\nSort/limit: order by matches DESC limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:56:24+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:56:26+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "league_id",
      "season",
      "matches"
    ],
    "row_count": 88,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows per grain (league_id, season) in the view",
        "sql": "SELECT COUNT(*) FROM matches_per_league_season v WHERE (SELECT COUNT(*) FROM matches_per_league_season v2 WHERE v2.league_id = v.league_id AND v2.season = v.season) > 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows in the view have non-NULL keys league_id and season (view respects WHERE filters)",
        "sql": "SELECT COUNT(*) FROM matches_per_league_season WHERE league_id IS NULL OR season IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Reported matches equals count of base Match rows per (league_id, season)",
        "sql": "SELECT COUNT(*) FROM matches_per_league_season v LEFT JOIN (SELECT league_id, season, COUNT(*) AS expected_matches FROM \"Match\" WHERE league_id IS NOT NULL AND season IS NOT NULL GROUP BY league_id, season) b ON v.league_id = b.league_id AND v.season = b.season WHERE b.expected_matches IS NULL OR v.matches <> b.expected_matches",
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
SELECT league_id, season, COUNT(*) AS matches FROM "Match" WHERE league_id IS NOT NULL AND season IS NOT NULL GROUP BY league_id, season
```

---

## Skill `players_with_attributes_and_birthyear`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `player_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_00bfa6ba7ee671d4 |
| output columns | `player_id`, `player_name`, `birthday`, `player_attributes_id`, `player_api_id`, `player_fifa_api_id`, `overall_rating` |
| source tables | `Player_Attributes`, `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Denormalized join of players to their attributes including birthday and overall_rating for use in cohort filters by birth year or attribute-based aggregations.

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
      "'1986'"
    ],
    "contract_version": 3,
    "grain_basis": "verified_unique",
    "lineage": [
      "Player_Attributes",
      "Player"
    ],
    "source_columns": [
      "Player.player_name",
      "Player.birthday",
      "Player_Attributes.player_api_id",
      "Player_Attributes.player_fifa_api_id",
      "Player_Attributes.overall_rating",
      "Player.id",
      "Player_Attributes.id",
      "Player.player_api_id"
    ],
    "output_lineage": {
      "player_id": [
        "Player.id"
      ],
      "player_name": [
        "Player.player_name"
      ],
      "birthday": [
        "Player.birthday"
      ],
      "player_attributes_id": [
        "Player_Attributes.id"
      ],
      "player_api_id": [
        "Player_Attributes.player_api_id"
      ],
      "player_fifa_api_id": [
        "Player_Attributes.player_fifa_api_id"
      ],
      "overall_rating": [
        "Player_Attributes.overall_rating"
      ]
    },
    "operators": [
      "filter",
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203",
      "player": "032b398bb82740dc"
    },
    "data_fingerprints": {
      "player_attributes": "183978:183978",
      "player": "11060:11075"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1093",
    "question": "What is the average overall rating of the players born before the year 1986?",
    "rewrite": "Task: Compute the average overall rating for all players whose birthday year is before 1986, using average overall rating = SUM(overall_rating) / COUNT(id).\nRequired outputs: average_overall_rating: a single numeric value equal to DIVIDE(SUM(overall_rating), COUNT(id)) computed over the filtered rows\nFilters: Include only rows where strftime('%Y', birthday) < '1986' (i.e., players born before the year 1986).; Include only rows with non-null overall_rating and non-null id so they are counted and summed correctly.",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:56:47+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:56:49+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "player_name",
      "birthday",
      "player_attributes_id",
      "player_api_id",
      "player_fifa_api_id",
      "overall_rating"
    ],
    "row_count": 183142,
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
        "purpose": "View grain uniqueness: player_attributes_id should be unique (no duplicate rows per grain).",
        "sql": "SELECT COUNT(*) FROM (SELECT player_attributes_id, COUNT(*) AS cnt FROM players_with_attributes_and_birthyear GROUP BY player_attributes_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Join completeness: every row in the view must correspond to an existing Player_Attributes row (no spurious rows), and key not NULL.",
        "sql": "SELECT COUNT(*) FROM players_with_attributes_and_birthyear v LEFT JOIN Player_Attributes pa ON v.player_attributes_id = pa.id WHERE pa.id IS NULL OR v.player_attributes_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Measure/column reconciliation: overall_rating in the view must match the value in Player_Attributes for the same player_attributes_id.",
        "sql": "SELECT COUNT(*) FROM players_with_attributes_and_birthyear v JOIN Player_Attributes pa ON v.player_attributes_id = pa.id WHERE (v.overall_rating IS NOT pa.overall_rating) OR (v.overall_rating IS NULL AND pa.overall_rating IS NOT NULL) OR (v.overall_rating IS NOT NULL AND pa.overall_rating IS NULL)",
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
SELECT p.id AS player_id, p.player_name, p.birthday, pa.id AS player_attributes_id, pa.player_api_id, pa.player_fifa_api_id, pa.overall_rating
FROM "Player_Attributes" pa
JOIN "Player" p ON pa.player_api_id = p.player_api_id
WHERE pa.id IS NOT NULL
  AND pa.overall_rating IS NOT NULL
  AND p.birthday IS NOT NULL
```

---

## Skill `team_build_up_play_speed_avg`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `team_api_id`, `team_long_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_bab7ea2bd6fb91ed |
| output columns | `team_api_id`, `team_long_name`, `average_build_up_play_speed` |
| source tables | `Team_Attributes`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Average build up play speed per team (one row per team_api_id and team_long_name) computed from Team_Attributes

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
      "Heart of Midlothian"
    ],
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Team_Attributes",
      "Team"
    ],
    "source_columns": [
      "Team_Attributes.team_api_id",
      "Team.team_long_name",
      "Team_Attributes.buildUpPlaySpeed",
      "Team.team_api_id"
    ],
    "output_lineage": {
      "team_api_id": [
        "Team_Attributes.team_api_id"
      ],
      "team_long_name": [
        "Team.team_long_name"
      ],
      "average_build_up_play_speed": [
        "Team_Attributes.buildUpPlaySpeed"
      ]
    },
    "operators": [
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "team_attributes": "a8661cb8da0875ec",
      "team": "a19728cad815ec8a"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1095",
    "question": "How much is the average build up play speed of the Heart of Midlothian team?",
    "rewrite": "Task: Compute the average build up play speed (AVG(buildUpPlaySpeed)) for the team whose team_long_name is 'Heart of Midlothian'.\nRequired outputs: average_build_up_play_speed: numeric value equal to AVG(buildUpPlaySpeed) for the selected team\nFilters: team_long_name = 'Heart of Midlothian'",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:57:28+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:57:31+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "team_api_id",
      "team_long_name",
      "average_build_up_play_speed"
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
        "sql": "SELECT COUNT(*) FROM (SELECT team_api_id, team_long_name, COUNT(*) AS cnt FROM team_build_up_play_speed_avg GROUP BY team_api_id, team_long_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "average_build_up_play_speed equals AVG(buildUpPlaySpeed) computed from Team_Attributes joined to Team (reconciliation of measure)",
        "sql": "SELECT COUNT(*) FROM (SELECT v.team_api_id, v.team_long_name, v.average_build_up_play_speed AS view_avg, AVG(ta.buildUpPlaySpeed) AS base_avg FROM team_build_up_play_speed_avg v LEFT JOIN Team_Attributes ta ON ta.team_api_id = v.team_api_id LEFT JOIN Team t ON t.team_api_id = ta.team_api_id AND t.team_long_name = v.team_long_name GROUP BY v.team_api_id, v.team_long_name HAVING (view_avg IS NULL AND base_avg IS NOT NULL) OR (view_avg IS NOT NULL AND ABS(view_avg - base_avg) > 0.0001))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys team_api_id and team_long_name are not NULL",
        "sql": "SELECT COUNT(*) FROM team_build_up_play_speed_avg WHERE team_api_id IS NULL OR team_long_name IS NULL",
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
SELECT ta.team_api_id, t.team_long_name, AVG(ta.buildUpPlaySpeed) AS average_build_up_play_speed
FROM Team_Attributes ta
JOIN Team t ON ta.team_api_id = t.team_api_id
GROUP BY ta.team_api_id, t.team_long_name
```

---

## Skill `team_chance_creation_passing_latest`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `team_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_628bdd470d656cab |
| output columns | `team_api_id`, `date`, `team_attributes_id`, `chanceCreationPassing`, `chanceCreationPassingClass` |
| source tables | `Team_Attributes`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-team Team_Attributes records with chanceCreationPassing and its class (one row per Team_Attributes entry) to support queries about teams' chance-creation-by-passing metrics

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
    "contract_version": 3,
    "grain_basis": "verified_unique",
    "lineage": [
      "Team_Attributes",
      "Team"
    ],
    "source_columns": [
      "Team_Attributes.team_api_id",
      "Team_Attributes.date",
      "Team_Attributes.chanceCreationPassing",
      "Team_Attributes.chanceCreationPassingClass",
      "Team_Attributes.id",
      "Team.team_api_id"
    ],
    "output_lineage": {
      "team_api_id": [
        "Team_Attributes.team_api_id"
      ],
      "date": [
        "Team_Attributes.date"
      ],
      "team_attributes_id": [
        "Team_Attributes.id"
      ],
      "chanceCreationPassing": [
        "Team_Attributes.chanceCreationPassing"
      ],
      "chanceCreationPassingClass": [
        "Team_Attributes.chanceCreationPassingClass"
      ]
    },
    "operators": [
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "team_attributes": "a8661cb8da0875ec",
      "team": "a19728cad815ec8a"
    },
    "data_fingerprints": {
      "team_attributes": "1458:1458",
      "team": "299:51606"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1098",
    "question": "What is Ajax's highest chance creation passing score and what is it classified as?",
    "rewrite": "Task: Find the maximum value of chanceCreationPassing for the team whose team_long_name equals 'Ajax', and report that maximum together with its corresponding chanceCreationPassingClass.\nRequired outputs: chanceCreationPassing (the maximum numeric value for team_long_name = 'Ajax'); chanceCreationPassingClass (the classification associated with that maximum value)\nFilters: team_long_name = 'Ajax'\nSort/limit: order by chanceCreationPassing desc limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:58:27+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:58:30+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "team_api_id",
      "date",
      "team_attributes_id",
      "chanceCreationPassing",
      "chanceCreationPassingClass"
    ],
    "row_count": 1458,
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
        "purpose": "View has one row per Team_Attributes entry (no missing Team_Attributes rows due to the JOIN to Team). Counts Team_Attributes rows whose id is not present in the view.",
        "sql": "SELECT COUNT(*) FROM Team_Attributes ta WHERE NOT EXISTS (SELECT 1 FROM team_chance_creation_passing_latest v WHERE v.team_attributes_id = ta.id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View does not introduce duplicate rows for the declared grain (team_attributes_id must be unique). Counts team_attributes_id values that appear more than once in the view.",
        "sql": "SELECT COUNT(*) FROM (SELECT team_attributes_id, COUNT(*) AS c FROM team_chance_creation_passing_latest GROUP BY team_attributes_id HAVING c > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Values in the view match the source columns from Team_Attributes (measures and keys not altered). Counts rows where any output differs from the corresponding Team_Attributes row.",
        "sql": "SELECT COUNT(*) FROM team_chance_creation_passing_latest v JOIN Team_Attributes ta ON ta.id = v.team_attributes_id WHERE (ta.team_api_id IS NOT v.team_api_id) OR (ta.date IS NOT v.date) OR (ta.chanceCreationPassing IS NOT v.chanceCreationPassing) OR (ta.chanceCreationPassingClass IS NOT v.chanceCreationPassingClass)",
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
SELECT ta.team_api_id, ta.date, ta.id AS team_attributes_id, ta.chanceCreationPassing, ta.chanceCreationPassingClass
FROM Team_Attributes ta
JOIN Team t ON t.team_api_id = ta.team_api_id
```

---

## Skill `team_match_away_stats_by_country`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `team_api_id`, `country_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_514cb156c107909c |
| output columns | `team_api_id`, `country_id`, `matches_away_count`, `avg_away_goals`, `sum_away_goals` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-team, per-country aggregation of away-match statistics (counts and averages) for matches played in each country.

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Match"
    ],
    "source_columns": [
      "Match.away_team_api_id",
      "Match.country_id",
      "Match.away_team_goal"
    ],
    "output_lineage": {
      "team_api_id": [
        "Match.away_team_api_id"
      ],
      "country_id": [
        "Match.country_id"
      ],
      "matches_away_count": [],
      "avg_away_goals": [
        "Match.away_team_goal"
      ],
      "sum_away_goals": [
        "Match.away_team_goal"
      ]
    },
    "operators": [
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1101",
    "question": "What is the average number of goals made by Parma as the away team while playing in Italy?",
    "rewrite": "Task: Compute the average number of goals scored by Parma when Parma is the away team in matches played in Italy.\nRequired outputs: average_away_goals_by_Parma: a single numeric value equal to AVG(away_team_goal) over all matching rows\nFilters: away_team = 'Parma' (team_long_name = 'Parma'); country = 'Italy' (matches played in Italy)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:59:40+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T14:59:44+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "team_api_id",
      "country_id",
      "matches_away_count",
      "avg_away_goals",
      "sum_away_goals"
    ],
    "row_count": 299,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View rows should be unique per (team_api_id, country_id) — detect duplicate keys in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT team_api_id, country_id, COUNT(*) AS cnt FROM team_match_away_stats_by_country GROUP BY team_api_id, country_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "matches_away_count must equal the count of Match rows for that away team and country",
        "sql": "SELECT COUNT(*) FROM team_match_away_stats_by_country v WHERE v.matches_away_count <> (SELECT COUNT(*) FROM \"Match\" m WHERE m.away_team_api_id = v.team_api_id AND m.country_id = v.country_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "sum_away_goals and avg_away_goals must reconcile with base table: sum_away_goals equals SUM(away_team_goal) and avg_away_goals equals AVG(away_team_goal) (allowing NULL handling) — find rows where eit",
        "sql": "SELECT COUNT(*) FROM team_match_away_stats_by_country v WHERE v.sum_away_goals IS NOT (SELECT SUM(m.away_team_goal) FROM \"Match\" m WHERE m.away_team_api_id = v.team_api_id AND m.country_id = v.country_id) OR (v.avg_away_goals IS NOT (SELECT AVG(m.away_team_goal) FROM \"Match\" m WHERE m.away_team_api_id = v.team_api_id AND m.country_id = v.country_id))",
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
SELECT m.away_team_api_id AS team_api_id, m.country_id AS country_id, COUNT(*) AS matches_away_count, AVG(m.away_team_goal) AS avg_away_goals, SUM(m.away_team_goal) AS sum_away_goals
FROM "Match" m
GROUP BY m.away_team_api_id, m.country_id
```

---

## Skill `team_attributes_by_team_and_date`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `team_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_800ff0f84a241ecc |
| output columns | `team_api_id`, `team_fifa_api_id`, `team_long_name`, `team_short_name`, `date`, `chanceCreationPassing`, `chance_creation_passing_class`, `team_attributes_id` |
| source tables | `Team`, `Team_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-team attributes for a given date, including chanceCreationPassing and its class, keyed by team and date for reuse across team/date-specific questions.

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
      "'PEC Zwolle'",
      "'2013-09-20 00:00:00'"
    ],
    "contract_version": 3,
    "grain_basis": "verified_unique",
    "lineage": [
      "Team",
      "Team_Attributes"
    ],
    "source_columns": [
      "Team.team_api_id",
      "Team.team_fifa_api_id",
      "Team.team_long_name",
      "Team.team_short_name",
      "Team_Attributes.date",
      "Team_Attributes.chanceCreationPassing",
      "Team_Attributes.chanceCreationPassingClass",
      "Team_Attributes.id",
      "Team_Attributes.team_api_id",
      "Team_Attributes.team_fifa_api_id"
    ],
    "output_lineage": {
      "team_api_id": [
        "Team.team_api_id"
      ],
      "team_fifa_api_id": [
        "Team.team_fifa_api_id"
      ],
      "team_long_name": [
        "Team.team_long_name"
      ],
      "team_short_name": [
        "Team.team_short_name"
      ],
      "date": [
        "Team_Attributes.date"
      ],
      "chanceCreationPassing": [
        "Team_Attributes.chanceCreationPassing"
      ],
      "chance_creation_passing_class": [
        "Team_Attributes.chanceCreationPassingClass"
      ],
      "team_attributes_id": [
        "Team_Attributes.id"
      ]
    },
    "operators": [
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "team": "a19728cad815ec8a",
      "team_attributes": "a8661cb8da0875ec"
    },
    "data_fingerprints": {
      "team": "299:51606",
      "team_attributes": "1458:1458"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1111",
    "question": "State the chance creation passing class for \"PEC Zwolle\" on 2013/9/20.",
    "rewrite": "Task: Retrieve the chance creation passing class for the team whose team_long_name is 'PEC Zwolle' on the date '2013-09-20 00:00:00'.\nRequired outputs: chance_creation_passing_class (the value of the chance creation passing class for that team and date)\nFilters: team_long_name = 'PEC Zwolle'; date = '2013-09-20 00:00:00'",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T15:03:37+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T15:03:40+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "team_api_id",
      "team_fifa_api_id",
      "team_long_name",
      "team_short_name",
      "date",
      "chanceCreationPassing",
      "chance_creation_passing_class",
      "team_attributes_id"
    ],
    "row_count": 1458,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Team.team_api_id=Team_Attributes.team_api_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      },
      {
        "join": "Team.team_fifa_api_id=Team_Attributes.team_fifa_api_id",
        "left_unique": false,
        "right_unique": false,
        "relationship": "many_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "View rows are unique per declared grain team_attributes_id (no duplicate team_attributes_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT team_attributes_id FROM team_attributes_by_team_and_date GROUP BY team_attributes_id HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All team_attributes_id (the declared key) are NOT NULL",
        "sql": "SELECT COUNT(*) FROM team_attributes_by_team_and_date WHERE team_attributes_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "chanceCreationPassing in the view matches Team_Attributes.chanceCreationPassing from the base table for the corresponding team_attributes_id (no mismatch)",
        "sql": "SELECT COUNT(*) FROM team_attributes_by_team_and_date v LEFT JOIN Team_Attributes t ON v.team_attributes_id = t.id WHERE (v.chanceCreationPassing IS NOT t.chanceCreationPassing) OR (v.chanceCreationPassing IS NULL AND t.chanceCreationPassing IS NOT NULL) OR (v.chanceCreationPassing IS NOT NULL AND t.chanceCreationPassing IS NULL)",
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
SELECT Team.team_api_id, Team.team_fifa_api_id, Team.team_long_name, Team.team_short_name, Team_Attributes.date, Team_Attributes.chanceCreationPassing, Team_Attributes.chanceCreationPassingClass AS chance_creation_passing_class, Team_Attributes.id AS team_attributes_id FROM Team JOIN Team_Attributes ON Team.team_api_id = Team_Attributes.team_api_id AND Team.team_fifa_api_id = Team_Attributes.team_fifa_api_id
```

---

## Skill `player_weights`

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

Per-player weight values for all players (player identifier with their weight), useful for finding heaviest players or filtering by weight.

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
    "contract_version": 3,
    "grain_basis": "verified_unique",
    "lineage": [
      "Player"
    ],
    "source_columns": [
      "Player.player_api_id",
      "Player.weight"
    ],
    "output_lineage": {
      "player_api_id": [
        "Player.player_api_id"
      ],
      "weight": [
        "Player.weight"
      ]
    },
    "operators": [
      "filter",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player": "032b398bb82740dc"
    },
    "data_fingerprints": {
      "player": "11060:11075"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1117",
    "question": "What are the player api id of 10 heaviest players?",
    "rewrite": "Task: Return the player api id values for the 10 players with the greatest weight (heaviest players), resolving ties by including the players with the top weights as needed but only return up to 10 player api ids.\nRequired outputs: player api id\nFilters: select rows corresponding to players with the largest weight values (heaviest players); limit results to at most 10 player api ids\nSort/limit: order by weight descending, limit 10",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T15:05:47+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T15:05:49+00:00",
    "contract_version": 3,
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
        "purpose": "No duplicate player_api_id in the view (grain holds): count rows in view that have a player_api_id appearing more than once",
        "sql": "SELECT COUNT(*) FROM player_weights pw WHERE (SELECT COUNT(*) FROM player_weights pw2 WHERE pw2.player_api_id = pw.player_api_id) > 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view corresponds to a base table row with the same player_api_id and weight (view not containing spurious rows)",
        "sql": "SELECT COUNT(*) FROM player_weights pw LEFT JOIN Player p ON pw.player_api_id = p.player_api_id AND pw.weight = p.weight WHERE p.player_api_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No NULL player_api_id in the view (key must be present)",
        "sql": "SELECT COUNT(*) FROM player_weights WHERE player_api_id IS NULL",
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
SELECT player_api_id, weight FROM Player WHERE weight IS NOT NULL
```

---

## Skill `player_max_attributes`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_e7558f524b64a965 |
| output columns | `player_api_id`, `max_strength`, `max_stamina` |
| source tables | `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player maximum observed attribute values (e.g., strength, stamina) computed from Player_Attributes to provide a single row per player for joins and cohort calculations.

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Player_Attributes"
    ],
    "source_columns": [
      "Player_Attributes.player_api_id",
      "Player_Attributes.strength",
      "Player_Attributes.stamina"
    ],
    "output_lineage": {
      "player_api_id": [
        "Player_Attributes.player_api_id"
      ],
      "max_strength": [
        "Player_Attributes.strength"
      ],
      "max_stamina": [
        "Player_Attributes.stamina"
      ]
    },
    "operators": [
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1137",
    "question": "What percentage of players have a strength and stamina score of more than 80?",
    "rewrite": "Task: Compute the percentage of players whose strength > 80 AND stamina > 80 out of all players.\nRequired outputs: percentage: numeric value representing (count of players with strength > 80 and stamina > 80) / (total count of players) * 100\nFilters: Include only rows where strength > 80; Include only rows where stamina > 80; Denominator is total count of all players (no additional filters unless specified)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T15:13:44+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T15:13:48+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
      "max_strength",
      "max_stamina"
    ],
    "row_count": 11060,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View has exactly one row per player_api_id present in Player_Attributes (no missing or extra player groups).",
        "sql": "SELECT (SELECT COUNT(DISTINCT player_api_id) FROM Player_Attributes) - (SELECT COUNT(*) FROM player_max_attributes)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "max_strength equals MAX(strength) computed from Player_Attributes for each player_api_id (detect mismatches or NULL/extra rows).",
        "sql": "SELECT COUNT(*) FROM player_max_attributes v LEFT JOIN (SELECT player_api_id, MAX(strength) AS expected_max_strength FROM Player_Attributes GROUP BY player_api_id) b ON v.player_api_id = b.player_api_id WHERE (v.max_strength IS NOT b.expected_max_strength) OR (v.max_strength IS NULL AND b.expected_max_strength IS NOT NULL) OR (v.max_strength IS NOT NULL AND b.expected_max_strength IS NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "max_stamina equals MAX(stamina) computed from Player_Attributes for each player_api_id (detect mismatches or NULL/extra rows).",
        "sql": "SELECT COUNT(*) FROM player_max_attributes v LEFT JOIN (SELECT player_api_id, MAX(stamina) AS expected_max_stamina FROM Player_Attributes GROUP BY player_api_id) b ON v.player_api_id = b.player_api_id WHERE (v.max_stamina IS NOT b.expected_max_stamina) OR (v.max_stamina IS NULL AND b.expected_max_stamina IS NOT NULL) OR (v.max_stamina IS NOT NULL AND b.expected_max_stamina IS NULL)",
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
SELECT player_api_id, MAX(strength) AS max_strength, MAX(stamina) AS max_stamina FROM Player_Attributes GROUP BY player_api_id
```

---

## Skill `team_game_counts_by_season`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `season`, `team_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_365068f0b3bf4aa8 |
| output columns | `season`, `team_api_id`, `game_count` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-team counts of matches (games) played in each season, with keys to join to team info

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Match"
    ],
    "source_columns": [
      "season",
      "team_api_id",
      "Match.season",
      "Match.home_team_api_id",
      "Match.away_team_api_id"
    ],
    "output_lineage": {
      "season": [
        "season"
      ],
      "team_api_id": [
        "team_api_id"
      ],
      "game_count": []
    },
    "operators": [
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1145",
    "question": "Which league had the most games in the 2015–2016 season?",
    "rewrite": "Task: Find which league (team_long_name) had the largest number of games (count of id) during the 2015/2016 season.\nRequired outputs: team_long_name; game_count\nFilters: season = '2015/2016'\nSort/limit: order by game_count desc limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T15:16:12+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T15:16:14+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "season",
      "team_api_id",
      "game_count"
    ],
    "row_count": 1481,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No NULLs in key columns (season, team_api_id) — view should be keyed by these and therefore not have NULLs",
        "sql": "SELECT COUNT(*) FROM team_game_counts_by_season WHERE season IS NULL OR team_api_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "game_count equals count of appearances in Match as home or away for that season/team (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM team_game_counts_by_season v LEFT JOIN (SELECT season, team_api_id, game_count FROM team_game_counts_by_season) vv ON v.season=vv.season AND v.team_api_id=vv.team_api_id WHERE v.game_count != (SELECT COUNT(*) FROM (SELECT season, home_team_api_id AS team_api_id FROM \"Match\" UNION ALL SELECT season, away_team_api_id AS team_api_id FROM \"Match\") m WHERE m.season = v.season AND m.team_api_id = v.team_api_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View has no duplicate rows for its declared grain (season, team_api_id) — duplicates would violate the grain",
        "sql": "SELECT COUNT(*) FROM (SELECT season, team_api_id, COUNT(*) AS cnt FROM team_game_counts_by_season GROUP BY season, team_api_id HAVING cnt > 1)",
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
SELECT season, team_api_id, COUNT(*) AS game_count
FROM (
  SELECT season, home_team_api_id AS team_api_id
  FROM "Match"
  UNION ALL
  SELECT season, away_team_api_id AS team_api_id
  FROM "Match"
) m
GROUP BY season, team_api_id
```

---

## Skill `team_max_away_goals_per_team`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `away_team_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_9c7b13dc01165234 |
| output columns | `away_team_api_id`, `max_away_team_goal` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each away team (by away_team_api_id), the maximum number of away goals that team has scored in any single match; includes the team identifier to allow joins to Team.

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Match"
    ],
    "source_columns": [
      "Match.away_team_api_id",
      "Match.away_team_goal"
    ],
    "output_lineage": {
      "away_team_api_id": [
        "Match.away_team_api_id"
      ],
      "max_away_team_goal": [
        "Match.away_team_goal"
      ]
    },
    "operators": [
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1146",
    "question": "Please provide the full name of the away team that scored the most goals.",
    "rewrite": "Task: Find the full name (team_long_name) of the away team (identified by away_team_api_id) that scored the maximum number of away goals (MAX(away_team_goal)) in the dataset.\nRequired outputs: team_long_name: the full name of the team corresponding to the away_team_api_id that has the highest recorded away_team_goal; away_team_api_id: the identifier of that away team; away_team_goal: the maximum away_team_goal value (MAX(away_team_goal)) associated with that away_team_api_id\nFilters: Consider all match rows; no additional row-level filters unless multiple teams tie for the same maximum away_team_goal; If multiple away_team_api_id values have the same MAX(away_team_goal), return all corresponding team_long_name values (i.e., include every team whose maximum away_team_goal equals the global maximum)\nSort/limit: order by away_team_goal DESC; no limit (return all teams tied for the top value)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T15:16:34+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T15:16:37+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "away_team_api_id",
      "max_away_team_goal"
    ],
    "row_count": 299,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View has one row per away_team_api_id (no duplicates on the key)",
        "sql": "SELECT COUNT(*) FROM (SELECT away_team_api_id FROM team_max_away_goals_per_team GROUP BY away_team_api_id HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each view row's max_away_team_goal equals the MAX(away_team_goal) computed from Match for that away_team_api_id",
        "sql": "SELECT COUNT(*) FROM team_max_away_goals_per_team v LEFT JOIN (SELECT away_team_api_id, MAX(away_team_goal) AS expected_max FROM Match GROUP BY away_team_api_id) m ON v.away_team_api_id = m.away_team_api_id WHERE (m.expected_max IS NULL AND v.max_away_team_goal IS NOT NULL) OR (m.expected_max IS NOT NULL AND v.max_away_team_goal IS NULL) OR (m.expected_max IS NOT NULL AND v.max_away_team_goal != m.expected_max)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "away_team_api_id (the key) is never NULL in the view",
        "sql": "SELECT COUNT(*) FROM team_max_away_goals_per_team WHERE away_team_api_id IS NULL",
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
SELECT away_team_api_id, MAX(away_team_goal) AS max_away_team_goal FROM Match GROUP BY away_team_api_id
```

---
