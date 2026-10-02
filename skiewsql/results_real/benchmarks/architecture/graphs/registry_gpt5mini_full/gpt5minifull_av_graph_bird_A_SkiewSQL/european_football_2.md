# Skill graph — `european_football_2` (29 skills)

## Skill `player_potential_min_cohort`

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

Cohort of player rows whose potential equals the global minimum potential value

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
    "rewrite": "Task: Find the preferred_foot value for the player(s) whose potential is the minimum (lowest) among all players.\nRequired outputs: preferred_foot\nFilters: Select rows where potential = MIN(potential) across the entire table",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:01:24+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:01:30+00:00",
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
        "purpose": "No row in the view has potential different from the global minimum potential in Player_Attributes",
        "sql": "SELECT COUNT(*) FROM player_potential_min_cohort v WHERE v.potential <> (SELECT MIN(potential) FROM Player_Attributes)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View has one row per id (no duplicate ids)",
        "sql": "SELECT COUNT(*) FROM (SELECT id, COUNT(*) AS cnt FROM player_potential_min_cohort GROUP BY id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view exists in Player_Attributes with identical values (detects accidental extra rows or mismatched columns)",
        "sql": "SELECT COUNT(*) FROM player_potential_min_cohort v LEFT JOIN Player_Attributes p ON v.id = p.id WHERE p.id IS NULL OR (v.player_fifa_api_id IS NOT p.player_fifa_api_id OR v.player_api_id IS NOT p.player_api_id OR v.date IS NOT p.date OR v.overall_rating IS NOT p.overall_rating OR v.potential IS NOT p.potential OR v.preferred_foot IS NOT p.preferred_foot OR v.attacking_work_rate IS NOT p.attacking_work_rate OR v.defensive_work_rate IS NOT p.defensive_work_rate OR v.crossing IS NOT p.crossing OR v.finishing IS NOT p.finishing OR v.heading_accuracy IS NOT p.heading_accuracy OR v.short_passing IS NOT p.short_passing OR v.volleys IS NOT p.volleys OR v.dribbling IS NOT p.dribbling OR v.curve IS NOT p.curve OR v.free_kick_accuracy IS NOT p.free_kick_accuracy OR v.long_passing IS NOT p.long_passin",
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
SELECT * FROM Player_Attributes WHERE potential = (SELECT MIN(potential) FROM Player_Attributes)
```

---

## Skill `league_season_total_goals`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_c0f7641eda7359c4 |
| output columns | `league_id`, `season`, `total_goals` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-league total goals for each season, summing home_team_goal and away_team_goal across matches in that season.

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
      "Match"
    ],
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1025",
    "question": "Which league had the most goals in the 2016 season?",
    "rewrite": "Task: Find which league (league identifier) had the highest total number of goals across all matches in the 2015/2016 season, where total goals per match = home_team_goal + away_team_goal and per-league total = sum of those match totals for matches in that season.\nRequired outputs: league (identifier of the league); total_goals (the sum of home_team_goal + away_team_goal for all matches in that league during the season '2015/2016')\nFilters: season = '2015/2016'; consider all matches in that season (no other row exclusions)\nSort/limit: order by total_goals desc limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:02:07+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:02:15+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "league_id",
      "season",
      "total_goals"
    ],
    "row_count": 88,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows for the declared grain (league_id, season). Each (league_id, season) should appear at most once in the view.",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, season, COUNT(*) AS cnt FROM league_season_total_goals GROUP BY league_id, season HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "total_goals equals the sum of home_team_goal + away_team_goal from Match for that league_id and season (recompute and find mismatches).",
        "sql": "SELECT COUNT(*) FROM league_season_total_goals v LEFT JOIN (SELECT m.league_id AS league_id, m.season AS season, SUM(COALESCE(m.home_team_goal,0)+COALESCE(m.away_team_goal,0)) AS expected_total FROM Match m GROUP BY m.league_id, m.season) s ON v.league_id = s.league_id AND v.season = s.season WHERE (v.total_goals IS NOT s.expected_total) OR (v.total_goals IS NULL AND s.expected_total IS NOT NULL) OR (v.total_goals IS NOT NULL AND s.expected_total IS NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No rows in the view with NULL keys (league_id or season) — the grain keys must be present.",
        "sql": "SELECT COUNT(*) FROM league_season_total_goals WHERE league_id IS NULL OR season IS NULL",
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
      "Task: Compute the total number of goals scored (sum of home_team_goal and away_team_goal across all seasons) for each league, and return the top 5 leagues with the smallest totals (ascending order).\nRequired outputs: league (identifier/name as provided in the schema); total_goals (SUM(home_team_goal + away_team_goal) across all seasons for that league)\nFilters: Include all seasons available in the data (no season-based filtering).; Aggregate goals per league across every match/row: total_goals = SUM(home_team_goal + away_team_goal).; Exclude leagues with NULL total_goals if any (i.e., only include leagues with a computable numeric total).\nSort/limit: Order by total_goals ascending; limit to 5 rows (the five leagues with the lowest total_goals)."
    ],
    "last_used": "bird_dev_1038"
  }
}
```

### Validated on (1)

- List the top 5 leagues in ascending order of the number of goals made in all seasons combined.

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT m.league_id AS league_id, m.season AS season, SUM(COALESCE(m.home_team_goal, 0) + COALESCE(m.away_team_goal, 0)) AS total_goals
FROM Match m
GROUP BY m.league_id, m.season
```

---

## Skill `home_team_season_home_loss_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `home_team_api_id`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_9c65a590e8a0cd94 |
| output columns | `home_team_api_id`, `season`, `home_losses_count` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each team acting as home team in a season, the count of matches they lost at home (home_team_goal - away_team_goal < 0) along with keys to join to team and season.

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
      "ORDER BY",
      "LIMIT",
      "team_long_name presentation"
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
    "question_id": "bird_dev_1026",
    "question": "Which home team had lost the fewest matches in the 2016 season?",
    "rewrite": "Task: Find which home team(s) in the 2015/2016 season had the smallest number of home-match losses, where a home-match loss is defined as matches for which home_team_goal - away_team_goal < 0.\nRequired outputs: home_team (identifier/name); home_losses_count (integer count of matches where home_team_goal - away_team_goal < 0 during the specified season)\nFilters: season = '2015/2016'; consider only matches played as the home team for each home_team; count only matches where (home_team_goal - away_team_goal) < 0 as losses\nSort/limit: order by home_losses_count ASC limit 1 (return the home_team(s) tied for the minimum home_losses_count)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:02:33+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:02:35+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "home_team_api_id",
      "season",
      "home_losses_count"
    ],
    "row_count": 1481,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows per grain (home_team_api_id, season)",
        "sql": "SELECT COUNT(*) FROM (SELECT home_team_api_id, season, COUNT(*) AS c FROM home_team_season_home_loss_counts GROUP BY home_team_api_id, season HAVING c > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "home_losses_count equals count of matches with home loss computed from base table",
        "sql": "SELECT COUNT(*) FROM home_team_season_home_loss_counts h LEFT JOIN (SELECT m.home_team_api_id AS home_team_api_id, m.season AS season, COUNT(*) AS expected_home_losses FROM \"Match\" m WHERE (m.home_team_goal - m.away_team_goal) < 0 GROUP BY m.home_team_api_id, m.season) b ON h.home_team_api_id = b.home_team_api_id AND h.season = b.season WHERE COALESCE(h.home_losses_count,0) != COALESCE(b.expected_home_losses,0)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys (home_team_api_id, season) are not NULL",
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
SELECT m.home_team_api_id AS home_team_api_id,
       m.season AS season,
       COUNT(*) FILTER (WHERE m.home_team_goal - m.away_team_goal < 0) AS home_losses_count
FROM "Match" m
GROUP BY m.home_team_api_id, m.season
```

---

## Skill `player_max_penalties`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_5a976a45425d5cd5 |
| output columns | `player_api_id`, `max_penalties` |
| source tables | `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player maximum recorded penalties value aggregated from player attributes (one row per player_id with its max penalties)

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
    "question_id": "bird_dev_1027",
    "question": "Indicate the full names of the top 10 players with the highest number of penalties.",
    "rewrite": "Task: Return the full names of the top 10 players who have the highest penalties (using the players' player_name field and the penalties value).\nRequired outputs: player_name (full name of player); penalties (numeric value of penalties for each player)\nFilters: Include only players with a penalties value (non-null).; Select players ordered by penalties in descending order.; If multiple players have the same penalties, include them ordered arbitrarily but still limited to the top 10 by penalties value.\nSort/limit: ORDER BY penalties DESC LIMIT 10",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:02:49+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:02:51+00:00",
    "contract_version": 2,
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
        "purpose": "No duplicate rows per grain: ensure player_api_id is unique in the view",
        "sql": "SELECT COUNT(*) FROM player_max_penalties v WHERE (SELECT COUNT(*) FROM player_max_penalties v2 WHERE v2.player_api_id = v.player_api_id) > 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "max_penalties equals the MAX(penalties) computed from Player_Attributes for that player (including handling NULLs)",
        "sql": "SELECT COUNT(*) FROM player_max_penalties v LEFT JOIN (SELECT player_api_id, MAX(penalties) AS exp_max FROM Player_Attributes WHERE penalties IS NOT NULL GROUP BY player_api_id) pa ON v.player_api_id = pa.player_api_id WHERE NOT ( (v.max_penalties IS NULL AND pa.exp_max IS NULL) OR (v.max_penalties = pa.exp_max) )",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL: every row must have a non-NULL player_api_id",
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
SELECT player_api_id, MAX(penalties) AS max_penalties FROM Player_Attributes WHERE penalties IS NOT NULL GROUP BY player_api_id
```

---

## Skill `matches_with_outcomes_by_league_season`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `match_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_75286966951468e3 |
| output columns | `match_id`, `season`, `league_id`, `league_name`, `home_team_api_id`, `away_team_api_id`, `home_team_goal`, `away_team_goal` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

All matches (with home and away goals and team ids) joined to their league name for a given league and season, filtered to rows where goal columns are not null and optionally filtered to a particular outcome; useful as a base for computing per-team counts or aggregates by outcome.

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
      "League.name = 'Scotland Premier League'",
      "Match.season = '2009/2010'"
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
    "question_id": "bird_dev_1028",
    "question": "In Scotland Premier League, which away team won the most during the 2010 season?",
    "rewrite": "Task: Find which away team (by away_team_api_id) had the most away wins in the Scotland Premier League during the 2009/2010 season, where an away win is a match with away_team_goal > home_team_goal.\nRequired outputs: away_team_api_id; away_wins_count\nFilters: League.name = 'Scotland Premier League'; season = '2009/2010'; Consider only matches where away_team_goal and home_team_goal are not null; Define an away win as (away_team_goal > home_team_goal)\nSort/limit: Order by away_wins_count DESC, limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:03:06+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:03:09+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "match_id",
      "season",
      "league_id",
      "league_name",
      "home_team_api_id",
      "away_team_api_id",
      "home_team_goal",
      "away_team_goal"
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
        "purpose": "View rows must have non-NULL home and away goals (intrinsic filter preserved): count rows in the view where either goal is NULL",
        "sql": "SELECT COUNT(*) FROM matches_with_outcomes_by_league_season v WHERE v.home_team_goal IS NULL OR v.away_team_goal IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View should not introduce duplicate match_id rows (grain uniqueness): count match_ids that appear more than once in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT match_id, COUNT(*) AS cnt FROM matches_with_outcomes_by_league_season GROUP BY match_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Join to League should not drop matches that have non-NULL goals and matching league: every match in Match with non-NULL goals and existing league should appear in the view",
        "sql": "SELECT COUNT(*) FROM Match m WHERE m.home_team_goal IS NOT NULL AND m.away_team_goal IS NOT NULL AND EXISTS (SELECT 1 FROM League l WHERE l.id = m.league_id) AND NOT EXISTS (SELECT 1 FROM matches_with_outcomes_by_league_season v WHERE v.match_id = m.id)",
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
SELECT m.id AS match_id, m.season, l.id AS league_id, l.name AS league_name, m.home_team_api_id, m.away_team_api_id, m.home_team_goal, m.away_team_goal FROM "Match" m JOIN "League" l ON m.league_id = l.id WHERE m.home_team_goal IS NOT NULL AND m.away_team_goal IS NOT NULL
```

---

## Skill `matches_per_league_season_draws`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `league_id`, `league_name`, `season` (keyed) |
| status / version | active / v1 |
| skill id | sk_51eec64665bcaa5d |
| output columns | `league_id`, `league_name`, `season`, `draw_count` |
| source tables | `Match`, `League` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-league, per-season counts of matches that ended in a draw (home_team_goal = away_team_goal).

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
    "rewrite": "Task: Find which league(s) had the highest number of matches that ended in a draw during the 2015/2016 season, where a match is a draw when home_team_goal = away_team_goal.\nRequired outputs: league_id or league name (identify the league); draw_count (the number of matches in that league and season where home_team_goal = away_team_goal)\nFilters: season = '2015/2016'; match is counted as draw when home_team_goal = away_team_goal\nSort/limit: order by draw_count desc limit 1 (if multiple leagues tie for the maximum, return all tied leagues)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:03:35+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:03:38+00:00",
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
        "purpose": "No duplicate rows per grain (league_id, league_name, season)",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, league_name, season, COUNT(*) AS cnt FROM matches_per_league_season_draws GROUP BY league_id, league_name, season HAVING cnt > 1) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every reported row corresponds to actual draw matches in Match (draw_count equals number of Match rows with home_team_goal = away_team_goal for that league and season)",
        "sql": "SELECT COUNT(*) FROM matches_per_league_season_draws v WHERE v.draw_count <> (SELECT COUNT(*) FROM \"Match\" m WHERE m.league_id = v.league_id AND m.season = v.season AND m.home_team_goal = m.away_team_goal)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys league_id, league_name, season are not NULL",
        "sql": "SELECT COUNT(*) FROM matches_per_league_season_draws WHERE league_id IS NULL OR league_name IS NULL OR season IS NULL",
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
SELECT m.league_id, l.name AS league_name, m.season, COUNT(*) AS draw_count
FROM Match m
JOIN League l ON m.league_id = l.id
WHERE m.home_team_goal = m.away_team_goal
GROUP BY m.league_id, l.name, m.season
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

Per-league counts of matches (one row per league_id with total matches for that league).

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
    "rewrite": "Task: Find the league name that has the largest total number of matches (i.e., the league_id that appears in the matches table the most) and report that league's name along with the count of matches.\nRequired outputs: League.name — the name of the league with the maximum total matches; match_count — the total number of matches played in that league (COUNT of matches where matches.league_id = league.id)\nFilters: Consider all rows in the matches table (no date/team filters).; Group matches by matches.league_id and compute COUNT(*) per league_id.; Select the league_id whose COUNT(*) is maximum (MAX(COUNT(matches.league_id))).; Join that league_id to League to obtain League.name.\nSort/limit: order the grouped results by match_count DESC and limit to 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:04:09+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:04:12+00:00",
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
        "purpose": "View should have one row per league_id (no duplicate league_id keys).",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, COUNT(*) AS cnt FROM matches_per_league GROUP BY league_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "match_count must equal the count of Match rows for that league_id (measure reconciliation).",
        "sql": "SELECT COUNT(*) FROM (SELECT v.league_id FROM matches_per_league v LEFT JOIN (SELECT league_id, COUNT(*) AS expected_count FROM \"Match\" GROUP BY league_id) b ON v.league_id = b.league_id WHERE (b.expected_count IS NULL AND v.match_count IS NOT NULL) OR (b.expected_count IS NOT NULL AND v.match_count != b.expected_count))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "league_id (key) must not be NULL in the view.",
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
SELECT league_id, COUNT(*) AS match_count
FROM "Match"
GROUP BY league_id
```

---

## Skill `player_average_heading_accuracy_by_player`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_api_id`, `player_fifa_api_id`, `player_name`, `height` (keyed) |
| status / version | active / v1 |
| skill id | sk_a892206158e781bb |
| output columns | `player_api_id`, `player_fifa_api_id`, `player_name`, `height`, `average_heading_accuracy` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player average heading accuracy computed from Player joined to Player_Attributes, including keys for joins and player height for filtering.

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
      "> 180",
      "10",
      "player_name"
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
    "rewrite": "Task: Return the top 10 players (by player name) whose heights are greater than 180, ranked in descending order by their average heading accuracy, where average heading accuracy is computed as SUM(heading_accuracy) / COUNT(player_fifa_api_id) for each player.\nRequired outputs: player_name: the player's name; average_heading_accuracy: numeric value computed as SUM(heading_accuracy)/COUNT(player_fifa_api_id) for that player\nFilters: height > 180 (strictly greater than 180)\nSort/limit: ORDER BY average_heading_accuracy DESC LIMIT 10",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:07:37+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:07:42+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
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
        "join": "Player.player_api_id=Player_Attributes.player_api_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (player_api_id, player_fifa_api_id, player_name, height).",
        "sql": "SELECT COUNT(*) FROM player_average_heading_accuracy_by_player v JOIN (SELECT player_api_id, player_fifa_api_id, player_name, height, COUNT(*) AS cnt FROM player_average_heading_accuracy_by_player GROUP BY player_api_id, player_fifa_api_id, player_name, height HAVING cnt > 1) dup USING (player_api_id, player_fifa_api_id, player_name, height) WHERE 1=1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "average_heading_accuracy equals sum(heading_accuracy)/count of non-null heading_accuracy computed from base tables for that player.",
        "sql": "SELECT COUNT(*) FROM player_average_heading_accuracy_by_player v LEFT JOIN (SELECT pa.player_api_id, (SUM(pa.heading_accuracy) * 1.0) / COUNT(pa.heading_accuracy) AS expected_avg FROM Player_Attributes pa WHERE pa.heading_accuracy IS NOT NULL GROUP BY pa.player_api_id) calc ON v.player_api_id = calc.player_api_id WHERE (v.average_heading_accuracy IS NOT NULL AND calc.expected_avg IS NULL) OR (v.average_heading_accuracy IS NULL AND calc.expected_avg IS NOT NULL) OR (v.average_heading_accuracy IS NOT NULL AND calc.expected_avg IS NOT NULL AND ABS(v.average_heading_accuracy - calc.expected_avg) > 1e-6)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Join keys in the view are not NULL and match an existing Player row (player_api_id and player_fifa_api_id must exist in Player table paired with the same player_name and height).",
        "sql": "SELECT COUNT(*) FROM player_average_heading_accuracy_by_player v LEFT JOIN Player p ON v.player_api_id = p.player_api_id AND v.player_fifa_api_id = p.player_fifa_api_id AND v.player_name = p.player_name AND (v.height IS NOT NULL AND p.height = v.height) WHERE v.player_api_id IS NULL OR v.player_fifa_api_id IS NULL OR v.player_name IS NULL OR v.height IS NULL OR p.player_api_id IS NULL",
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
      "Task: Compute the heading accuracy of the player Ariel Borysiuk.\nRequired outputs: player_name: the player's full name (Ariel Borysiuk); heading_accuracy: the player's heading accuracy value (percentage or decimal as stored)\nFilters: player_name = 'Ariel Borysiuk'"
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
SELECT p.player_api_id, p.player_fifa_api_id, p.player_name, p.height, SUM(pa.heading_accuracy) * 1.0 / COUNT(pa.player_fifa_api_id) AS average_heading_accuracy FROM Player p JOIN Player_Attributes pa ON p.player_api_id = pa.player_api_id WHERE pa.heading_accuracy IS NOT NULL GROUP BY p.player_api_id, p.player_fifa_api_id, p.player_name, p.height
```

---

## Skill `team_latest_attributes`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `id` (keyed) |
| status / version | active / v1 |
| skill id | sk_66e7b20ff492771d |
| output columns | `team_api_id`, `team_long_name`, `date`, `buildUpPlayPositioningClass`, `id`, `team_fifa_api_id`, `team_api_id:1`, `date:1`, `buildUpPlaySpeed`, `buildUpPlaySpeedClass`, `buildUpPlayDribbling`, `buildUpPlayDribblingClass`, `buildUpPlayPassing`, `buildUpPlayPassingClass`, `buildUpPlayPositioningClass:1`, `chanceCreationPassing`, `chanceCreationPassingClass`, `chanceCreationCrossing`, `chanceCreationCrossingClass`, `chanceCreationShooting`, `chanceCreationShootingClass`, `chanceCreationPositioningClass`, `defencePressure`, `defencePressureClass`, `defenceAggression`, `defenceAggressionClass`, `defenceTeamWidth`, `defenceTeamWidthClass`, `defenceDefenderLineClass` |
| source tables | `Team`, `Team_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Latest attributes per team combining team identity with their most recent Team_Attributes row (keeps keys for joins and attribute columns such as buildUpPlayPositioningClass).

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
      "'ADO Den Haag'",
      "team_long_name filter"
    ],
    "contract_version": 2,
    "grain_basis": "verified_unique",
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
    "question_id": "bird_dev_1046",
    "question": "What is the ADO Den Haag team freedom of movement in the 1st two thirds of the pitch?",
    "rewrite": "Task: Retrieve the value of ADO Den Haag's freedom of movement in the first two thirds of the pitch (buildUpPlayPositioningClass) for the team whose long name is 'ADO Den Haag'.\nRequired outputs: team_long_name - literal 'ADO Den Haag' to identify the team; buildUpPlayPositioningClass - the team's freedom of movement classification for the first two thirds of the pitch\nFilters: team_long_name = 'ADO Den Haag'",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:09:06+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:09:09+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "team_api_id",
      "team_long_name",
      "date",
      "buildUpPlayPositioningClass",
      "id",
      "team_fifa_api_id",
      "team_api_id:1",
      "date:1",
      "buildUpPlaySpeed",
      "buildUpPlaySpeedClass",
      "buildUpPlayDribbling",
      "buildUpPlayDribblingClass",
      "buildUpPlayPassing",
      "buildUpPlayPassingClass",
      "buildUpPlayPositioningClass:1",
      "chanceCreationPassing",
      "chanceCreationPassingClass",
      "chanceCreationCrossing",
      "chanceCreationCrossingClass",
      "chanceCreationShooting",
      "chanceCreationShootingClass",
      "chanceCreationPositioningClass",
      "defencePressure",
      "defencePressureClass",
      "defenceAggression",
      "defenceAggressionClass",
      "defenceTeamWidth",
      "defenceTeamWidthClass",
      "defenceDefenderLineClass"
    ],
    "row_count": 289,
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
        "purpose": "No duplicate rows per declared grain 'id' (each id appears at most once in the view)",
        "sql": "SELECT COUNT(*) FROM (SELECT id, COUNT(*) AS cnt FROM team_latest_attributes GROUP BY id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's team_api_id and team_long_name match the Team table (join didn't change team identity)",
        "sql": "SELECT COUNT(*) FROM team_latest_attributes tla LEFT JOIN Team t ON tla.team_api_id = t.team_api_id WHERE t.team_api_id IS NULL OR tla.team_long_name IS NULL OR tla.team_long_name != t.team_long_name",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each view row uses the latest Team_Attributes.date for that team_api_id (date equals max date in Team_Attributes)",
        "sql": "SELECT COUNT(*) FROM team_latest_attributes tla LEFT JOIN (SELECT team_api_id, MAX(date) AS max_date FROM Team_Attributes GROUP BY team_api_id) ta_max ON tla.team_api_id = ta_max.team_api_id WHERE ta_max.team_api_id IS NULL OR tla.date != ta_max.max_date",
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
SELECT t.team_api_id, t.team_long_name, ta.date, ta.buildUpPlayPositioningClass, ta.*
FROM Team t
JOIN Team_Attributes ta
  ON t.team_api_id = ta.team_api_id
WHERE ta.date = (
  SELECT MAX(ta2.date)
  FROM Team_Attributes ta2
  WHERE ta2.team_api_id = ta.team_api_id
)
```

---

## Skill `player_max_overall_attributes`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_e30f27ebf4ee5bf3 |
| output columns | `player_attributes_id`, `player_api_id`, `player_fifa_api_id`, `date`, `overall_rating`, `potential` |
| source tables | `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Attributes rows for player(s) whose overall_rating equals the global maximum overall_rating in Player_Attributes (keeps player id keys and attribute fields for reuse)

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
    "grain_basis": "primary_key",
    "lineage": [
      "Player_Attributes"
    ],
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1055",
    "question": "When is the birthday of the football player who has the highest overall rating?",
    "rewrite": "Task: Find the birthday (date of birth) of the football player whose overall_rating value equals the maximum overall_rating among all players.\nRequired outputs: birthday (date of birth) of the player(s) with overall_rating = MAX(overall_rating)\nFilters: overall_rating = MAX(overall_rating) across the entire players table (i.e., select rows where overall_rating equals the global maximum)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:12:03+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:12:07+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_attributes_id",
      "player_api_id",
      "player_fifa_api_id",
      "date",
      "overall_rating",
      "potential"
    ],
    "row_count": 12,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No rows in the view have overall_rating different from the global maximum overall_rating in Player_Attributes",
        "sql": "SELECT COUNT(*) FROM player_max_overall_attributes v WHERE v.overall_rating <> (SELECT MAX(overall_rating) FROM Player_Attributes)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view corresponds to an existing Player_Attributes row with matching id and all attribute fields equal (detects projection or join mistakes)",
        "sql": "SELECT COUNT(*) FROM player_max_overall_attributes v LEFT JOIN Player_Attributes pa ON pa.id = v.player_attributes_id WHERE pa.id IS NULL OR pa.player_api_id <> v.player_api_id OR pa.player_fifa_api_id <> v.player_fifa_api_id OR pa.date <> v.date OR (pa.overall_rating IS NOT v.overall_rating) OR (pa.potential IS NOT v.potential)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View respects declared grain: player_attributes_id is unique and not NULL",
        "sql": "SELECT COUNT(*) FROM (SELECT player_attributes_id, COUNT(*) AS cnt FROM player_max_overall_attributes GROUP BY player_attributes_id HAVING player_attributes_id IS NULL OR cnt <> 1)",
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
      "Task: Find the player(s) whose overall_rating is equal to the maximum overall_rating in the dataset.\nRequired outputs: player identifier (e.g., player_id or player_name) as provided by the schema; overall_rating (the overall strength value) equal to the maximum overall_rating\nFilters: overall_rating IS NOT NULL; overall_rating = MAX(overall_rating) over all rows"
    ],
    "last_used": "bird_dev_1083"
  }
}
```

### Validated on (0)

—

### Counter-examples (1)

- Which player has the strongest overall strength?

### Executable SQL body

```sql
SELECT pa.id AS player_attributes_id, pa.player_api_id, pa.player_fifa_api_id, pa.date, pa.overall_rating, pa.potential FROM Player_Attributes pa WHERE pa.overall_rating = (SELECT MAX(overall_rating) FROM Player_Attributes)
```

---

## Skill `leagues_with_country`

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

All leagues with their country id and country name for joining or filtering by country

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
    "rewrite": "Task: Return the name(s) of the football league(s) whose country is 'Netherlands'.\nRequired outputs: League.name\nFilters: League.country = 'Netherlands'",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:12:14+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:12:17+00:00",
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
        "purpose": "No duplicate league rows: each league_id appears at most once in the view (ensures grain = league_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, COUNT(*) AS cnt FROM leagues_with_country GROUP BY league_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every league row has a non-NULL key league_id (keys are not NULL)",
        "sql": "SELECT COUNT(*) FROM leagues_with_country WHERE league_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "country_name in the view matches Country.name for the referenced country_id (measure reconciliation / join correctness)",
        "sql": "SELECT COUNT(*) FROM leagues_with_country lwc LEFT JOIN Country c ON lwc.country_id = c.id WHERE (c.name IS NULL AND lwc.country_name IS NOT NULL) OR (c.name IS NOT NULL AND lwc.country_name IS NULL) OR (c.name IS NOT NULL AND lwc.country_name IS NOT NULL AND c.name != lwc.country_name)",
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
    "positive": 1,
    "positive_subgoals": [
      "Task: Return all leagues that are located in the country whose name is 'Germany'.\nRequired outputs: league names (one row per league)\nFilters: Country.name = 'Germany'; Only leagues that are associated/located in that country"
    ],
    "last_used": "bird_dev_1082"
  }
}
```

### Validated on (1)

- Please list the leagues from Germany.

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT League.id AS league_id, League.name AS league_name, League.country_id AS country_id, Country.name AS country_name
FROM League
JOIN Country ON League.country_id = Country.id
```

---

## Skill `player_avg_finishing_by_player`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_ebedac3e11815781 |
| output columns | `player_api_id`, `avg_finishing` |
| source tables | `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player average finishing computed from Player_Attributes, with player identifiers to join to Player or other tables.

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
    "question_id": "bird_dev_1058",
    "question": "Who has the highest average finishing rate between the highest and shortest football player?",
    "rewrite": "Task: Compare the average finishing rates of the tallest football player (player(s) with maximum height) and the shortest football player (player(s) with minimum height) and report which of these two has the higher average finishing rate.\nRequired outputs: identifier(s) of the tallest player(s) and/or shortest player(s) needed to explain result (e.g., player id or name); average finishing rate for the tallest player(s) as AVG(finishing); average finishing rate for the shortest player(s) as AVG(finishing); which group has the higher average finishing rate or indicate tie\nFilters: restrict one group to player(s) whose height = maximum height across all players; restrict the other group to player(s) whose height = minimum height across all players",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:12:48+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:12:52+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
      "avg_finishing"
    ],
    "row_count": 11060,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows per grain: ensure player_api_id is unique in the view",
        "sql": "SELECT COUNT(*) FROM player_avg_finishing_by_player v GROUP BY player_api_id HAVING COUNT(*)>1 LIMIT 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "avg_finishing matches AVG(finishing) computed from Player_Attributes for each player_api_id (NULL-safe)",
        "sql": "SELECT COUNT(*) FROM player_avg_finishing_by_player v LEFT JOIN (SELECT player_api_id, AVG(finishing) AS calc_avg FROM Player_Attributes GROUP BY player_api_id) t ON v.player_api_id = t.player_api_id WHERE (v.avg_finishing IS NULL AND t.calc_avg IS NOT NULL) OR (v.avg_finishing IS NOT NULL AND t.calc_avg IS NULL) OR (v.avg_finishing IS NOT NULL AND t.calc_avg IS NOT NULL AND ABS(v.avg_finishing - t.calc_avg) > 1e-6)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL: player_api_id in the view must be present (non-NULL)",
        "sql": "SELECT COUNT(*) FROM player_avg_finishing_by_player WHERE player_api_id IS NULL",
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
SELECT pa.player_api_id, AVG(pa.finishing) AS avg_finishing
FROM Player_Attributes pa
GROUP BY pa.player_api_id
```

---

## Skill `player_with_attributes`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `player_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_b7aaef2e34f3e40b |
| output columns | `player_id`, `player_api_id`, `player_name`, `player_fifa_api_id`, `player_attributes_id`, `pa_player_api_id`, `date`, `preferred_foot`, `overall_rating`, `potential` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Denormalized relation joining players with their attributes (one row per player-attributes record) including identifiers, name, date, preferred foot, and ratings to support various player-level filters and analyses.

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
      "'left'"
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
    "question_id": "bird_dev_1064",
    "question": "List out of players whose preferred foot is left.",
    "rewrite": "Task: Return all players whose preferred foot is 'left'.\nRequired outputs: player (the player identifier or name as present in the schema)\nFilters: preferred_foot = 'left'",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:14:20+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:14:25+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "player_api_id",
      "player_name",
      "player_fifa_api_id",
      "player_attributes_id",
      "pa_player_api_id",
      "date",
      "preferred_foot",
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
        "purpose": "Grain uniqueness: each player_attributes_id should appear exactly once in the view (no duplicates of the declared grain).",
        "sql": "SELECT COUNT(*) FROM (SELECT player_attributes_id FROM player_with_attributes GROUP BY player_attributes_id HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Join integrity: every row in the view should correspond to an existing Player_Attributes row (no rows whose player_attributes_id is missing from base table).",
        "sql": "SELECT COUNT(*) FROM player_with_attributes v WHERE NOT EXISTS (SELECT 1 FROM Player_Attributes pa WHERE pa.id = v.player_attributes_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Measure reconciliation / field provenance: ratings and preferred_foot in the view must match the Player_Attributes source for that player_attributes_id.",
        "sql": "SELECT COUNT(*) FROM player_with_attributes v JOIN Player_Attributes pa ON pa.id = v.player_attributes_id WHERE ( (v.overall_rating IS NOT pa.overall_rating) OR (v.potential IS NOT pa.potential) OR ( (v.preferred_foot IS NOT pa.preferred_foot) AND NOT (v.preferred_foot IS NULL AND pa.preferred_foot IS NULL) ) )",
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
SELECT p.id AS player_id, p.player_api_id, p.player_name, p.player_fifa_api_id, pa.id AS player_attributes_id, pa.player_api_id AS pa_player_api_id, pa.date, pa.preferred_foot, pa.overall_rating, pa.potential FROM "Player" p JOIN "Player_Attributes" pa ON pa.player_api_id = p.player_api_id
```

---

## Skill `team_attributes_with_fast_buildup_and_team_info`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `id` (keyed) |
| status / version | active / v1 |
| skill id | sk_3ecea395ffc2a1b1 |
| output columns | `id`, `team_fifa_api_id`, `team_api_id`, `date`, `buildUpPlaySpeed`, `buildUpPlaySpeedClass`, `team_long_name`, `team_short_name`, `team_id` |
| source tables | `Team_Attributes`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Rows of Team_Attributes that have buildUpPlaySpeedClass = 'Fast', enriched with matching Team row (team_long_name, team_short_name, Team.id as team_id) joined by team_api_id; one row per Team_Attributes.id.

### Semantic filters

```json
{
  "buildUpPlaySpeedClass": "Fast"
}
```

### Learned skill parameters

```json
{
  "description": "Rows of Team_Attributes that have buildUpPlaySpeedClass = 'Fast', enriched with matching Team row (team_long_name, team_short_name, Team.id as team_id) joined by team_api_id; one row per Team_Attributes.id.",
  "when_to_use": "Filter or list Team_Attributes records whose buildUpPlaySpeedClass is exactly 'Fast'. | Enrich Team_Attributes rows with basic Team metadata (team_long_name, team_short_name, Team.id) when matching on team_api_id. | Inspect buildUpPlaySpeed values and dates for attributes classified as Fast along with team identifiers.",
  "when_not_to_use": "When you need Team_Attributes rows with buildUpPlaySpeedClass other than 'Fast' (the view intrinsically filters to 'Fast'). | When you need a different grain than Team_Attributes.id (the view is keyed by TA.id and returns one row per that id). | When you need all Team columns or additional Team_Attributes columns not selected here (only the listed columns are present). | When you require inner-join semantics to exclude Team_Attributes without matching Team rows (the view uses LEFT JOIN and will keep TA rows even if Team is missing). | When you rely on a different join path or matching key (this view joins only on TA.team_api_id = T.team_api_id; it does not use team_fifa_api_id). | When you need aggregation over groups, time-windowed summaries, or deduplication beyond the TA.id uniqueness (no aggregation is performed). | When temporal alignment or a specific date range is required (the view exposes the TA.date field but applies no time filter)."
}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "av_chunk",
    "subgoal": {
      "want_name": "chunk_view_1",
      "category": "SEL",
      "required_outputs": [],
      "required_grain": [],
      "required_filters": {},
      "text": "Task: Return all team_long_name values for teams whose buildUpPlaySpeedClass is 'Fast'.\nRequired outputs: team_long_name\nFilters: buildUpPlaySpeedClass = 'Fast'",
      "source_tables": [
        "Country",
        "League",
        "Team",
        "Team_Attributes"
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
      "Team_Attributes",
      "Team"
    ],
    "table_fingerprints": {
      "team_attributes": "a8661cb8da0875ec",
      "team": "a19728cad815ec8a"
    },
    "data_fingerprints": {
      "team_attributes": "1458:1458",
      "team": "299:51606"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1065",
    "question": "Please list all team names which the speed class is fast.",
    "rewrite": "Task: Return all team_long_name values for teams whose buildUpPlaySpeedClass is 'Fast'.\nRequired outputs: team_long_name\nFilters: buildUpPlaySpeedClass = 'Fast'",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:14:34+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:14:38+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "id",
      "team_fifa_api_id",
      "team_api_id",
      "date",
      "buildUpPlaySpeed",
      "buildUpPlaySpeedClass",
      "team_long_name",
      "team_short_name",
      "team_id"
    ],
    "row_count": 172,
    "grain_check": "pass",
    "filter_checks": {
      "buildUpPlaySpeedClass": "pass"
    },
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
        "purpose": "No row in view violates the intrinsic filter buildUpPlaySpeedClass = 'Fast'",
        "sql": "SELECT COUNT(*) FROM chunk_view_1 WHERE buildUpPlaySpeedClass IS NULL OR buildUpPlaySpeedClass <> 'Fast'",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View preserves 1:1 correspondence with Team_Attributes rows for the filtered set (no lost or duplicated TA rows) — count of TA rows with Fast that are missing or duplicated in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT TA.id, COUNT(v.id) AS view_count FROM Team_Attributes AS TA LEFT JOIN chunk_view_1 AS v ON TA.id = v.id WHERE TA.buildUpPlaySpeedClass = 'Fast' GROUP BY TA.id HAVING view_count <> 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row's team_id (joined Team.id) either matches Team.team_api_id linkage or is NULL only when no Team matches (i.e., no unexpected mismatches) — find view rows where a matching Team exists bu",
        "sql": "SELECT COUNT(*) FROM chunk_view_1 v JOIN Team t ON v.team_api_id = t.team_api_id WHERE v.team_id IS NULL OR v.team_id <> t.id",
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
  TA.id,
  TA.team_fifa_api_id,
  TA.team_api_id,
  TA.date,
  TA.buildUpPlaySpeed,
  TA.buildUpPlaySpeedClass,
  T.team_long_name,
  T.team_short_name,
  T.id AS team_id
FROM
  "Team_Attributes" AS TA
LEFT JOIN
  "Team" AS T
ON
  TA.team_api_id = T.team_api_id
WHERE
  TA.buildUpPlaySpeedClass = 'Fast'
```

---

## Skill `team_attributes_buildup_and_team_info`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `id` (keyed) |
| status / version | active / v1 |
| skill id | sk_d0a17839b586b1af |
| output columns | `id`, `team_fifa_api_id`, `team_api_id`, `date`, `buildUpPlaySpeed`, `buildUpPlaySpeedClass`, `team_long_name`, `team_short_name`, `team_id` |
| source tables | `Team_Attributes`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Team_Attributes rows joined with Team info (team_long_name, team_short_name, team_id) including buildUpPlaySpeed and buildUpPlaySpeedClass, one row per Team_Attributes.id.

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
    "grain_basis": "verified_unique",
    "lineage": [
      "Team_Attributes",
      "Team"
    ],
    "table_fingerprints": {
      "team_attributes": "a8661cb8da0875ec",
      "team": "a19728cad815ec8a"
    },
    "data_fingerprints": {
      "team_attributes": "1458:1458",
      "team": "299:51606"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1065",
    "question": "Please list all team names which the speed class is fast.",
    "rewrite": "Task: Return all team_long_name values for teams whose buildUpPlaySpeedClass is 'Fast'.\nRequired outputs: team_long_name\nFilters: buildUpPlaySpeedClass = 'Fast'",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:14:44+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:14:48+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "id",
      "team_fifa_api_id",
      "team_api_id",
      "date",
      "buildUpPlaySpeed",
      "buildUpPlaySpeedClass",
      "team_long_name",
      "team_short_name",
      "team_id"
    ],
    "row_count": 1458,
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
        "purpose": "View should have exactly one row per Team_Attributes.id (no missing or duplicate ids). Checks that every id in Team_Attributes appears exactly once in the view.",
        "sql": "SELECT COUNT(*) FROM (SELECT TA.id, COUNT(v.id) AS cnt FROM Team_Attributes TA LEFT JOIN team_attributes_buildup_and_team_info v ON TA.id = v.id GROUP BY TA.id) WHERE cnt <> 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Joined Team fields come from matching Team rows: team_id in the view should be NULL only when there is no Team with that team_api_id (i.e., view didn't falsely populate team_id). This test counts rows",
        "sql": "SELECT COUNT(*) FROM team_attributes_buildup_and_team_info v LEFT JOIN Team T ON v.team_id = T.id WHERE v.team_id IS NOT NULL AND T.id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys from source are preserved: id and team_api_id in the view must not be NULL (grain key id must exist and join preserves team_api_id). Counts rows in the view where id or team_api_id is NULL.",
        "sql": "SELECT COUNT(*) FROM team_attributes_buildup_and_team_info WHERE id IS NULL OR team_api_id IS NULL",
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
SELECT TA.id, TA.team_fifa_api_id, TA.team_api_id, TA.date, TA.buildUpPlaySpeed, TA.buildUpPlaySpeedClass, T.team_long_name, T.team_short_name, T.id AS team_id FROM "Team_Attributes" AS TA LEFT JOIN "Team" AS T ON TA.team_api_id = T.team_api_id
```

---

## Skill `player_min_height`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `id` (keyed) |
| status / version | active / v1 |
| skill id | sk_78bfb31608ebc560 |
| output columns | `id`, `player_api_id`, `player_name`, `height` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each dataset, the minimal non-null player height and the player(s) having that height (player id, name, and height) to identify shortest players.

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
    "grain_basis": "primary_key",
    "lineage": [
      "Player"
    ],
    "table_fingerprints": {
      "player": "032b398bb82740dc"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1069",
    "question": "Which football player has the shortest height?",
    "rewrite": "Task: Find the football player(s) who has the minimum value of the height column (i.e., the shortest height).\nRequired outputs: player identifier (e.g., player name or id) and the height value for that player\nFilters: height = MIN(height) across all rows (shortest height)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:15:38+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:15:40+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "id",
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
        "purpose": "Each row in the view must correspond to an existing Player id (no phantom ids)",
        "sql": "SELECT COUNT(*) FROM player_min_height v LEFT JOIN Player p ON v.id = p.id WHERE p.id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's height must equal the global minimal non-null Player.height",
        "sql": "SELECT COUNT(*) FROM player_min_height v WHERE v.height IS NULL OR v.height <> (SELECT MIN(height) FROM Player WHERE height IS NOT NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No duplicate player ids in the view (grain = id)",
        "sql": "SELECT COUNT(*) FROM (SELECT id, COUNT(*) AS ct FROM player_min_height GROUP BY id HAVING ct > 1)",
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
SELECT p.id, p.player_api_id, p.player_name, p.height
FROM Player p
WHERE p.height IS NOT NULL
  AND p.height = (SELECT MIN(height) FROM Player WHERE height IS NOT NULL)
```

---

## Skill `player_ball_control_avg`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_api_id`, `player_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_8624f479cbf8d922 |
| output columns | `player_api_id`, `player_name`, `avg_ball_control` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Average ball_control per player (one row per player) computed from Player joined to Player_Attributes, excluding NULL ball_control values.

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
    "question_id": "bird_dev_1076",
    "question": "What is the difference of the average ball control score between Abdou Diallo and Aaron Appindangoye\n?",
    "rewrite": "Task: Compute the difference between the average ball control score for player 'Abdou Diallo' and the average ball control score for player 'Aaron Appindangoye'.\nRequired outputs: difference: numeric value equal to AVG(ball_control WHERE player_name = 'Abdou Diallo') - AVG(ball_control WHERE player_name = 'Aaron Appindangoye')\nFilters: player_name = 'Abdou Diallo' for the first average; player_name = 'Aaron Appindangoye' for the second average; include all rows where ball_control is not NULL for each player",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:17:08+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:17:11+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
      "player_name",
      "avg_ball_control"
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
        "purpose": "View has one row per player key (no duplicate player_api_id/player_name pairs)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_api_id, player_name, COUNT(*) AS cnt FROM player_ball_control_avg GROUP BY player_api_id, player_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "avg_ball_control equals AVG(ball_control) computed from base tables excluding NULLs (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM player_ball_control_avg v LEFT JOIN Player p ON v.player_api_id = p.player_api_id LEFT JOIN Player_Attributes pa ON p.player_api_id = pa.player_api_id GROUP BY v.player_api_id, v.player_name HAVING ABS(v.avg_ball_control - (SELECT AVG(pa2.ball_control*1.0) FROM Player_Attributes pa2 WHERE pa2.player_api_id = v.player_api_id AND pa2.ball_control IS NOT NULL)) > 1e-9",
        "result": "inconclusive",
        "violations": null,
        "error": "timeout"
      },
      {
        "purpose": "Every view row corresponds to an existing player (no foreign keys to missing Player) and keys are NOT NULL",
        "sql": "SELECT COUNT(*) FROM player_ball_control_avg v LEFT JOIN Player p ON v.player_api_id = p.player_api_id WHERE v.player_api_id IS NULL OR v.player_name IS NULL OR p.player_api_id IS NULL",
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
SELECT p.player_api_id, p.player_name, AVG(pa.ball_control*1.0) AS avg_ball_control FROM Player p JOIN Player_Attributes pa ON p.player_api_id = pa.player_api_id WHERE pa.ball_control IS NOT NULL GROUP BY p.player_api_id, p.player_name
```

---

## Skill `player_height`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_4ea5927959d87f7a |
| output columns | `player_id`, `player_api_id`, `player_name`, `player_fifa_api_id`, `height`, `weight` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player height values for all players with a non-null height, useful as a base relation for height-based queries (tallest, shortest, height distributions, joins to player metadata).

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
    "grain_basis": "primary_key",
    "lineage": [
      "Player"
    ],
    "table_fingerprints": {
      "player": "032b398bb82740dc"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1079",
    "question": "Which player is the tallest?",
    "rewrite": "Task: Find the player(s) with the maximum height value (i.e., the tallest player(s)).\nRequired outputs: player identifier(s) or name(s) as given in the table; height value for each returned player\nFilters: height is equal to the maximum height across all players (height = MAX(height)); exclude rows where height is NULL",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:17:53+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:17:55+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "player_api_id",
      "player_name",
      "player_fifa_api_id",
      "height",
      "weight"
    ],
    "row_count": 11060,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View respects its grain: no duplicate player_id rows in player_height",
        "sql": "SELECT COUNT(*) FROM (SELECT player_id FROM player_height GROUP BY player_id HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows in view originate from Player with non-NULL height (no row with NULL height)",
        "sql": "SELECT COUNT(*) FROM player_height WHERE height IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in view corresponds to an existing Player row (no orphaned player_id)",
        "sql": "SELECT COUNT(*) FROM player_height ph LEFT JOIN Player p ON ph.player_id = p.id WHERE p.id IS NULL",
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
SELECT id AS player_id, player_api_id, player_name, player_fifa_api_id, height, weight FROM Player WHERE height IS NOT NULL
```

---

## Skill `matches_per_league_per_season`

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

For each league and season, the total number of matches played (counts of Match rows grouped by league_id and season).

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
      "2008/2009"
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
    "rewrite": "Task: Find the league identifier that had the maximum number of matches in the 2008/2009 season.\nRequired outputs: league_id (the identifier of the league with the most matches in season '2008/2009'); matches_count (the number of matches that league had in season '2008/2009')\nFilters: season = '2008/2009'\nSort/limit: order by matches_count desc limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:21:46+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:21:49+00:00",
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
        "purpose": "View has one row per (league_id, season) — detect duplicate rows in the view for the same key",
        "sql": "SELECT COUNT(*) FROM (SELECT league_id, season, COUNT(*) AS cnt FROM matches_per_league_per_season GROUP BY league_id, season) WHERE cnt > 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "matches_count equals the count of Match rows grouped by league_id and season",
        "sql": "SELECT COUNT(*) FROM matches_per_league_per_season v LEFT JOIN (SELECT league_id, season, COUNT(*) AS expected_cnt FROM \"Match\" GROUP BY league_id, season) m ON v.league_id IS m.league_id AND v.season IS m.season WHERE (m.expected_cnt IS NULL AND v.matches_count IS NOT NULL) OR (m.expected_cnt IS NOT NULL AND v.matches_count != m.expected_cnt)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Key columns league_id and season are not NULL in the view",
        "sql": "SELECT COUNT(*) FROM matches_per_league_per_season WHERE league_id IS NULL OR season IS NULL",
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

## Skill `team_away_matches_by_country`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `match_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_dc89b075eaf29242 |
| output columns | `match_id`, `match_date`, `season`, `match_api_id`, `team_api_id`, `team_long_name`, `away_team_goal`, `opponent_team_api_id`, `country_id`, `country_name`, `league_id` |
| source tables | `Match`, `Team`, `Country` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-match records for when a given team played as the away team, including away goals and match country to support cohort- or country-based aggregations

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
      "Parma",
      "Italy"
    ],
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "Match",
      "Team",
      "Country"
    ],
    "table_fingerprints": {
      "match": "a56b9117c06fb4c3",
      "team": "a19728cad815ec8a",
      "country": "a556b33684a1aaf5"
    },
    "data_fingerprints": {
      "match": "25979:25979",
      "team": "299:51606",
      "country": "11:24558"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1101",
    "question": "What is the average number of goals made by Parma as the away team while playing in Italy?",
    "rewrite": "Task: Compute the average number of goals scored by Parma when Parma is the away team and the match is played in Italy.\nRequired outputs: average_away_goals: the AVG(away_team_goal) for matches meeting the filters\nFilters: team_long_name = 'Parma' applied to the away team (i.e., Parma is the away team); country = 'Italy' for the match location",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:23:49+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:23:55+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "match_id",
      "match_date",
      "season",
      "match_api_id",
      "team_api_id",
      "team_long_name",
      "away_team_goal",
      "opponent_team_api_id",
      "country_id",
      "country_name",
      "league_id"
    ],
    "row_count": 25979,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Team.team_api_id=Match.away_team_api_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      },
      {
        "join": "Country.id=Match.country_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "View grain: match_id should be unique (no duplicate match_id rows).",
        "sql": "SELECT COUNT(*) FROM (SELECT match_id, COUNT(*) AS cnt FROM team_away_matches_by_country GROUP BY match_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Join completeness: every row in the view should correspond to an existing Match row (no phantom match_ids).",
        "sql": "SELECT COUNT(*) FROM team_away_matches_by_country v LEFT JOIN Match m ON m.id = v.match_id WHERE m.id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Measure reconciliation: away_team_goal in the view should match Match.away_team_goal for the same match_id.",
        "sql": "SELECT COUNT(*) FROM team_away_matches_by_country v JOIN Match m ON m.id = v.match_id WHERE (v.away_team_goal IS NOT m.away_team_goal) OR (v.away_team_goal IS NULL AND m.away_team_goal IS NOT NULL) OR (v.away_team_goal IS NOT NULL AND m.away_team_goal IS NULL)",
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
SELECT m.id AS match_id, m.date AS match_date, m.season AS season, m.match_api_id, m.away_team_api_id AS team_api_id, t.team_long_name AS team_long_name, m.away_team_goal AS away_team_goal, m.home_team_api_id AS opponent_team_api_id, c.id AS country_id, c.name AS country_name, m.league_id AS league_id FROM Match m JOIN Team t ON t.team_api_id = m.away_team_api_id JOIN Country c ON c.id = m.country_id
```

---

## Skill `player_attributes_with_player_info_by_date`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `id` (keyed) |
| status / version | active / v1 |
| skill id | sk_06632ff24832351d |
| output columns | `id`, `player_api_id`, `player_fifa_api_id`, `date`, `overall_rating`, `player_name`, `birthday` |
| source tables | `Player_Attributes`, `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Denormalized view of player attributes joined with player personal info for a given date (one row per player attribute record with player name and birthday), useful to query ratings or attributes by date.

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
      "77",
      "2016-06-23"
    ],
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "Player_Attributes",
      "Player"
    ],
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203",
      "player": "032b398bb82740dc"
    },
    "data_fingerprints": {
      "player_attributes": "183978:183978",
      "player": "11060:11075"
    },
    "db_id": "european_football_2",
    "question_id": "bird_dev_1102",
    "question": "For the players who had a 77 points overall rating on 2016/6/23, who was the oldest? Give the name of the player.",
    "rewrite": "Task: Find the player(s) who had overall_rating = 77 on 2016-06-23 and among those return the oldest player (earliest birthday).\nRequired outputs: name\nFilters: overall_rating = 77; date = '2016-06-23' or the record's date field equals 2016-06-23\nSort/limit: order by birthday ASC limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:24:11+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:24:18+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "id",
      "player_api_id",
      "player_fifa_api_id",
      "date",
      "overall_rating",
      "player_name",
      "birthday"
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
        "purpose": "View should have exactly one row per Player_Attributes.id (no duplicate ids produced by the join)",
        "sql": "SELECT COUNT(*) FROM (SELECT id, COUNT(*) AS cnt FROM player_attributes_with_player_info_by_date GROUP BY id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row's id must match an existing Player_Attributes row (join didn't create rows for non-existent attributes)",
        "sql": "SELECT COUNT(*) FROM player_attributes_with_player_info_by_date v WHERE NOT EXISTS (SELECT 1 FROM Player_Attributes pa WHERE pa.id = v.id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Denormalized measures (overall_rating) must equal the value from the base Player_Attributes table for the same id",
        "sql": "SELECT COUNT(*) FROM player_attributes_with_player_info_by_date v JOIN Player_Attributes pa ON pa.id = v.id WHERE (v.overall_rating IS NOT pa.overall_rating) OR (v.overall_rating IS NULL AND pa.overall_rating IS NOT NULL) OR (v.overall_rating IS NOT NULL AND pa.overall_rating IS NULL)",
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
SELECT pa.id, pa.player_api_id, pa.player_fifa_api_id, pa.date, pa.overall_rating, p.player_name, p.birthday FROM Player_Attributes pa LEFT JOIN Player p ON pa.player_api_id = p.player_api_id
```

---

## Skill `player_attributes_for_named_player_on_date`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `id` (keyed) |
| status / version | active / v1 |
| skill id | sk_c9220832fb239c53 |
| output columns | `id`, `player_api_id`, `player_fifa_api_id`, `player_name`, `player_attributes_id`, `date`, `potential` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Rows that pair a Player row with a Player_Attributes row for the same player (matched by player_api_id OR player_fifa_api_id) for a specific player name and attribute date; one output row per matched (Player.id, Player_Attributes.id) pair.

### Semantic filters

```json
{
  "player_name": "Francesco Parravicini",
  "date": "2010-08-30 00:00:00"
}
```

### Learned skill parameters

```json
{
  "description": "Rows that pair a Player row with a Player_Attributes row for the same player (matched by player_api_id OR player_fifa_api_id) for a specific player name and attribute date; one output row per matched (Player.id, Player_Attributes.id) pair.",
  "when_to_use": "Find the player_attributes record(s) and basic player identifiers for the player named 'Francesco Parravicini' on 2010-08-30. | Retrieve the potential value (and attribute id and date) for that player on that exact date. | Join-ready relation when you need both Player.id and the corresponding Player_Attributes.id for that player/date combination.",
  "when_not_to_use": "Do not use to get attributes for other players or other dates — the view is intrinsically filtered to player_name = 'Francesco Parravicini' and pa.date = '2010-08-30 00:00:00'. | Do not use when you require a single canonical attributes row per player if multiple Player_Attributes rows match (the JOIN uses OR on player_api_id or player_fifa_api_id and will return multiple pairs if duplicates exist). | Do not use to infer longitudinal trends or any time window beyond the single explicit date — it contains only one specific date. | Do not use for analyses expecting matches only via both ids; this view matches when either player_api_id OR player_fifa_api_id equals, which can produce spurious matches if ids are inconsistent or duplicated. | Do not use as an aggregation (e.g., max potential) — outputs are raw rows with no aggregation and may include multiple rows per player if multiple attribute records exist for the date."
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
      "text": "Task: Find the potential value for the player Francesco Parravicini on the date 2010-08-30 00:00:00.\nRequired outputs: player_name; date; potential\nFilters: player_name = 'Francesco Parravicini'; date = '2010-08-30 00:00:00'",
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
    "question_id": "bird_dev_1104",
    "question": "What was the potiential for Francesco Parravicini on 2010/8/30?",
    "rewrite": "Task: Find the potential value for the player Francesco Parravicini on the date 2010-08-30 00:00:00.\nRequired outputs: player_name; date; potential\nFilters: player_name = 'Francesco Parravicini'; date = '2010-08-30 00:00:00'",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:24:48+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:24:52+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "id",
      "player_api_id",
      "player_fifa_api_id",
      "player_name",
      "player_attributes_id",
      "date",
      "potential"
    ],
    "row_count": 1,
    "grain_check": "pass",
    "filter_checks": {
      "player_name": "pass",
      "date": "pass"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows by primary grain 'id' in the view (each id should appear at most once)",
        "sql": "SELECT COUNT(*) FROM (SELECT id, COUNT(*) AS cnt FROM chunk_view_0 GROUP BY id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows must satisfy intrinsic filters: player_name = 'Francesco Parravicini' and date = '2010-08-30 00:00:00'",
        "sql": "SELECT COUNT(*) FROM chunk_view_0 WHERE NOT (player_name = 'Francesco Parravicini' AND date = '2010-08-30 00:00:00')",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "potential in the view must match potential from Player_Attributes for the linked player_attributes_id",
        "sql": "SELECT COUNT(*) FROM chunk_view_0 v LEFT JOIN Player_Attributes pa ON pa.id = v.player_attributes_id WHERE pa.id IS NULL OR v.potential IS NULL OR v.potential != pa.potential",
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
  p.player_fifa_api_id,
  p.player_name,
  pa.id AS player_attributes_id,
  pa.date,
  pa.potential
FROM "Player" p
JOIN "Player_Attributes" pa
  ON pa.player_api_id = p.player_api_id
     OR pa.player_fifa_api_id = p.player_fifa_api_id
WHERE p.player_name = 'Francesco Parravicini'
  AND pa.date = '2010-08-30 00:00:00'
```

---

## Skill `player_attributes_by_player_and_date`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `id` (keyed) |
| status / version | active / v1 |
| skill id | sk_879981ca705e50be |
| output columns | `player_id`, `player_api_id`, `player_name`, `player_fifa_api_id`, `player_attributes_id`, `date`, `overall_rating`, `id`, `player_fifa_api_id:1`, `player_api_id:1`, `date:1`, `overall_rating:1`, `potential`, `preferred_foot`, `attacking_work_rate`, `defensive_work_rate`, `crossing`, `finishing`, `heading_accuracy`, `short_passing`, `volleys`, `dribbling`, `curve`, `free_kick_accuracy`, `long_passing`, `ball_control`, `acceleration`, `sprint_speed`, `agility`, `reactions`, `balance`, `shot_power`, `jumping`, `stamina`, `strength`, `long_shots`, `aggression`, `interceptions`, `positioning`, `vision`, `penalties`, `marking`, `standing_tackle`, `sliding_tackle`, `gk_diving`, `gk_handling`, `gk_kicking`, `gk_positioning`, `gk_reflexes` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player player_attributes records (join of Player and Player_Attributes) with keys and attribute values usable to compute aggregates or cohorts by player and date ranges.

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
      "'Marko Arnautovic'",
      "'2007-02-22 00:00:00'",
      "'2016-04-21 00:00:00'"
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
    "question_id": "bird_dev_1114",
    "question": "What was the average overall rating for Marko Arnautovic from 2007/2/22 to 2016/4/21?",
    "rewrite": "Task: Compute the average of the overall rating (avg(overall_rating)) for the player named 'Marko Arnautovic' over all records with dates from 2007-02-22 00:00:00 through 2016-04-21 00:00:00 inclusive.\nRequired outputs: average_overall_rating: a single numeric value equal to avg(overall_rating) for the selected records\nFilters: player_name = 'Marko Arnautovic'; date >= '2007-02-22 00:00:00'; date <= '2016-04-21 00:00:00'",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:28:58+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:29:01+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "player_api_id",
      "player_name",
      "player_fifa_api_id",
      "player_attributes_id",
      "date",
      "overall_rating",
      "id",
      "player_fifa_api_id:1",
      "player_api_id:1",
      "date:1",
      "overall_rating:1",
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
        "join": "Player_Attributes.player_api_id=Player.player_api_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the view grain (id is primary key of the view): count of duplicate ids in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT id, COUNT(*) AS cnt FROM player_attributes_by_player_and_date GROUP BY id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row must have matching Player and Player_Attributes join keys (player_api_id and player_attributes_id correspond to existing base rows and the join did not create mismatches): count of view",
        "sql": "SELECT COUNT(*) FROM player_attributes_by_player_and_date v LEFT JOIN Player p ON p.player_api_id = v.player_api_id LEFT JOIN Player_Attributes pa ON pa.id = v.player_attributes_id WHERE p.player_api_id IS NULL OR pa.id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All key columns from base tables used as keys in the view are NOT NULL (player_id and player_attributes_id must be present): count of view rows with NULL keys",
        "sql": "SELECT COUNT(*) FROM player_attributes_by_player_and_date WHERE player_id IS NULL OR player_attributes_id IS NULL",
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
SELECT p.id AS player_id, p.player_api_id, p.player_name, p.player_fifa_api_id, pa.id AS player_attributes_id, pa.date, pa.overall_rating, pa.* FROM Player p JOIN Player_Attributes pa ON pa.player_api_id = p.player_api_id
```

---

## Skill `player_basic_info_with_birthday`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_api_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_7c5e3c524c49df57 |
| output columns | `player_api_id`, `player_name`, `player_fifa_api_id`, `birthday` |
| source tables | `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Basic player identifiers and birthday for use in age calculations and joins

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
    "question_id": "bird_dev_1118",
    "question": "List down the name of players who are 35 years old and above.",
    "rewrite": "Task: Return the names of all players whose age is 35 years or older as of the current local timestamp.\nRequired outputs: name\nFilters: CURRENT local datetime minus player birthday >= 35 years; equivalently datetime(CURRENT_TIMESTAMP,'localtime') - datetime(birthday) > 34 (i.e., age >= 35)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:29:52+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:29:54+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
      "player_name",
      "player_fifa_api_id",
      "birthday"
    ],
    "row_count": 11060,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No NULL keys: ensure player_api_id (the declared grain key) is never NULL in the view",
        "sql": "SELECT COUNT(*) FROM player_basic_info_with_birthday WHERE player_api_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No duplicate rows at the declared grain: ensure player_api_id is unique in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT player_api_id FROM player_basic_info_with_birthday GROUP BY player_api_id HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View respects source filter: every row in the view must have a non-NULL birthday as enforced by the view definition",
        "sql": "SELECT COUNT(*) FROM player_basic_info_with_birthday WHERE birthday IS NULL",
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
SELECT player_api_id, player_name, player_fifa_api_id, birthday FROM Player WHERE birthday IS NOT NULL
```

---

## Skill `player_birthdays_and_attributes`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `player_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_e4c8eac0f0d5e8d6 |
| output columns | `player_id`, `player_api_id`, `player_fifa_api_id`, `player_name`, `birthday`, `player_attributes_id`, `attributes_date`, `overall_rating`, `potential`, `preferred_foot`, `attacking_work_rate`, `defensive_work_rate`, `crossing`, `finishing`, `heading_accuracy`, `short_passing`, `volleys`, `dribbling`, `curve`, `free_kick_accuracy`, `long_passing`, `ball_control`, `acceleration`, `sprint_speed`, `agility`, `reactions`, `balance`, `shot_power`, `jumping`, `stamina`, `strength`, `long_shots`, `aggression`, `interceptions`, `positioning`, `vision`, `penalties`, `marking`, `standing_tackle`, `sliding_tackle`, `gk_diving`, `gk_handling`, `gk_kicking`, `gk_positioning`, `gk_reflexes` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player record including player identifiers, birthday, and latest attributes joinable to match or goal records to compute age-based filters or per-player metrics

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
      "age threshold (31)",
      "age comparison operator",
      "current timestamp usage was left generic"
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
    "question_id": "bird_dev_1121",
    "question": "Calculate the total home team goal scored by players whose age are 30 years old and below.",
    "rewrite": "Task: Compute the total number of home team goals scored by players whose age is 30 years old or younger, where age is determined by subtracting the player's birthday from the current local timestamp and selecting players with resulting age less than 31.\nRequired outputs: total_home_goals: a single numeric value representing the sum of home team goals scored by all players whose age is 30 years old or below\nFilters: Include only records for players whose age, computed as SUBTRACT(datetime(CURRENT_TIMESTAMP,'localtime'), datetime(birthday)), is < 31 (i.e., age <= 30).; Consider only goals counted as 'home team goals' (as defined in the schema).",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:31:07+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:31:11+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "player_api_id",
      "player_fifa_api_id",
      "player_name",
      "birthday",
      "player_attributes_id",
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
        "purpose": "View grain uniqueness: no two rows share the same player_attributes_id (duplicates would break the declared grain).",
        "sql": "SELECT COUNT(*) FROM (SELECT player_attributes_id, COUNT(*) AS cnt FROM player_birthdays_and_attributes GROUP BY player_attributes_id HAVING player_attributes_id IS NOT NULL AND cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys not NULL: player_attributes_id must not be NULL because the view's declared grain is keyed by player_attributes_id.",
        "sql": "SELECT COUNT(*) FROM player_birthdays_and_attributes WHERE player_attributes_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Join correctness: every row in the view with a non-NULL player_attributes_id must match an existing base Player_Attributes row (no phantom attributes introduced by the view).",
        "sql": "SELECT COUNT(*) FROM player_birthdays_and_attributes v LEFT JOIN Player_Attributes pa ON v.player_attributes_id = pa.id WHERE v.player_attributes_id IS NOT NULL AND pa.id IS NULL",
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
SELECT p.id AS player_id, p.player_api_id, p.player_fifa_api_id, p.player_name, p.birthday, pa.id AS player_attributes_id, pa.date AS attributes_date, pa.overall_rating, pa.potential, pa.preferred_foot, pa.attacking_work_rate, pa.defensive_work_rate, pa.crossing, pa.finishing, pa.heading_accuracy, pa.short_passing, pa.volleys, pa.dribbling, pa.curve, pa.free_kick_accuracy, pa.long_passing, pa.ball_control, pa.acceleration, pa.sprint_speed, pa.agility, pa.reactions, pa.balance, pa.shot_power, pa.jumping, pa.stamina, pa.strength, pa.long_shots, pa.aggression, pa.interceptions, pa.positioning, pa.vision, pa.penalties, pa.marking, pa.standing_tackle, pa.sliding_tackle, pa.gk_diving, pa.gk_handling, pa.gk_kicking, pa.gk_positioning, pa.gk_reflexes FROM Player p LEFT JOIN Player_Attributes pa ON pa.player_api_id = p.player_api_id WHERE p.birthday IS NOT NULL
```

---

## Skill `player_max_overall_rating`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_api_id`, `player_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_ce609fa1b34b5874 |
| output columns | `player_api_id`, `player_name`, `max_overall` |
| source tables | `Player_Attributes`, `Player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-player maximum overall_rating across Player_Attributes, joined to player identifier for reuse in analyses of player strength.

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
      "Player_Attributes",
      "Player"
    ],
    "table_fingerprints": {
      "player_attributes": "8909d00fa680d203",
      "player": "032b398bb82740dc"
    },
    "data_fingerprints": {},
    "db_id": "european_football_2",
    "question_id": "bird_dev_1122",
    "question": "State 10 names of the strongest players.",
    "rewrite": "Task: Return the 10 player names with the highest overall_rating (i.e., the 10 strongest players by MAX(overall_rating)).\nRequired outputs: player_name (the name of the player); overall_rating (the player's overall rating used to determine strength)\nFilters: Include only rows corresponding to individual players; Use overall_rating values as provided; no ties are broken unless by ordering rule below\nSort/limit: order by overall_rating desc, limit 10",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:31:25+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:31:29+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
      "player_name",
      "max_overall"
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
        "purpose": "No duplicate rows at the declared grain (player_api_id, player_name).",
        "sql": "SELECT COUNT(*) FROM (SELECT player_api_id, player_name, COUNT(*) AS ct FROM player_max_overall_rating GROUP BY player_api_id, player_name HAVING ct > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every max_overall equals the MAX(overall_rating) computed from Player_Attributes for that player_api_id (detects aggregation/join mistakes).",
        "sql": "SELECT COUNT(*) FROM player_max_overall_rating v LEFT JOIN (SELECT pa.player_api_id, MAX(pa.overall_rating) AS expected_max FROM Player_Attributes pa GROUP BY pa.player_api_id) t ON v.player_api_id = t.player_api_id WHERE (t.expected_max IS NULL AND v.max_overall IS NOT NULL) OR (t.expected_max IS NOT NULL AND v.max_overall IS NULL) OR (t.expected_max IS NOT NULL AND v.max_overall != t.expected_max)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view refers to an existing Player (player_api_id present in Player) and the player_name matches the Player table (detects bad joins or NULL keys).",
        "sql": "SELECT COUNT(*) FROM player_max_overall_rating v LEFT JOIN Player p ON v.player_api_id = p.player_api_id WHERE p.player_api_id IS NULL OR (v.player_name IS NULL) OR (p.player_name IS NOT NULL AND v.player_name != p.player_name)",
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
SELECT p.player_api_id, p.player_name, MAX(pa.overall_rating) AS max_overall FROM Player_Attributes pa JOIN Player p ON p.player_api_id = pa.player_api_id GROUP BY p.player_api_id, p.player_name
```

---

## Skill `player_right_foot_attributes_by_player_attributes_id`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `player_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_1b95dd902265ae0d |
| output columns | `player_id`, `player_name`, `potential`, `preferred_foot`, `player_attributes_id` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Rows of player attributes for players whose preferred_foot is 'right', one row per Player_Attributes.id (player_attributes_id) joined to the Player record.

### Semantic filters

```json
{
  "preferred_foot": "right"
}
```

### Learned skill parameters

```json
{
  "description": "Rows of player attributes for players whose preferred_foot is 'right', one row per Player_Attributes.id (player_attributes_id) joined to the Player record.",
  "when_to_use": "To list players (player_api_id and player_name) together with a specific Player_Attributes row (player_attributes_id) and that row's potential when you only want players whose preferred_foot = 'right' | As a lookup from a Player_Attributes.id to the associated player_api_id, player_name and potential for right-footed entries | When joining or filtering by a specific Player_Attributes.id and you need the linked Player.player_api_id and player_name for right-footed attribute rows",
  "when_not_to_use": "When you need left-footed or unknown preferred_foot values — the view filters to preferred_foot = 'right' and will omit them | When you need a single row per player regardless of multiple attribute snapshots — the grain is Player_Attributes.id (player_attributes_id), so a player with multiple attribute rows will appear multiple times | When you need the most recent (or a time-windowed) attributes — the view does not filter or aggregate by Player_Attributes.date, so it can return historical snapshots | When you expect aggregation over players (e.g., max potential per player) — no aggregation is performed; columns are raw and at the attribute-row grain | When you expect joins via Player.id or player_fifa_api_id — the join path is specifically Player.player_api_id = Player_Attributes.player_api_id; other join keys are not available from this view and would require additional joins or different relations"
}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "av_chunk",
    "subgoal": {
      "want_name": "chunk_view_1",
      "category": "SEL",
      "required_outputs": [],
      "required_grain": [],
      "required_filters": {},
      "text": "Task: Select the top three football players' IDs who have the minimum possible 'potential' value and whose 'preferred_foot' is 'right'.\nRequired outputs: player_id\nFilters: potential = MIN(potential) across the table; preferred_foot = 'right'\nSort/limit: order by player_id (ascending) and limit 3",
      "source_tables": [
        "Country",
        "League",
        "Team",
        "Team_Attributes"
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
    "question_id": "bird_dev_1135",
    "question": "Please provide top three football players' IDs who are among the lowest potential players and prefer to use the right foot when attacking.",
    "rewrite": "Task: Select the top three football players' IDs who have the minimum possible 'potential' value and whose 'preferred_foot' is 'right'.\nRequired outputs: player_id\nFilters: potential = MIN(potential) across the table; preferred_foot = 'right'\nSort/limit: order by player_id (ascending) and limit 3",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:34:20+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:34:22+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_id",
      "player_name",
      "potential",
      "preferred_foot",
      "player_attributes_id"
    ],
    "row_count": 138409,
    "grain_check": "pass",
    "filter_checks": {
      "preferred_foot": "pass"
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
        "purpose": "View grain uniqueness: each player_attributes_id should appear at most once in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT player_attributes_id, COUNT(*) AS cnt FROM chunk_view_1 GROUP BY player_attributes_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Intrinsic filter upheld: no row in the view has preferred_foot different from 'right'",
        "sql": "SELECT COUNT(*) FROM chunk_view_1 WHERE NOT (preferred_foot = 'right' OR preferred_foot IS NULL) ",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Join completeness: every row in the view must correspond to an existing Player_Attributes row (player_attributes_id present in base table)",
        "sql": "SELECT COUNT(*) FROM chunk_view_1 cv WHERE NOT EXISTS (SELECT 1 FROM Player_Attributes pa WHERE pa.id = cv.player_attributes_id)",
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
  "Player"."player_api_id" AS "player_id",
  "Player"."player_name",
  "Player_Attributes"."potential",
  "Player_Attributes"."preferred_foot",
  "Player_Attributes"."id" AS "player_attributes_id"
FROM "Player"
JOIN "Player_Attributes" ON "Player"."player_api_id" = "Player_Attributes"."player_api_id"
WHERE "Player_Attributes"."preferred_foot" = 'right'
```

---

## Skill `player_with_max_weight`

Category: `RANK`

| field | value |
|---|---|
| grain (one row per) | `player_attributes_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_2fce3b31e16f0cf5 |
| output columns | `player_api_id`, `player_name`, `weight`, `player_attributes_id`, `date`, `finishing`, `curve` |
| source tables | `Player`, `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Rows for the player(s) having the maximum weight across all players, including player identifiers and attributes for joining

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
    "question_id": "bird_dev_1144",
    "question": "Please state the finishing rate and curve score of the player who has the heaviest weight.",
    "rewrite": "Task: Find the finishing rate and curve score for the player whose weight is the maximum (heaviest) among all players.\nRequired outputs: finishing rate; curve score\nFilters: row(s) where weight = MAX(weight) across the entire table",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:37:10+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:37:12+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "player_api_id",
      "player_name",
      "weight",
      "player_attributes_id",
      "date",
      "finishing",
      "curve"
    ],
    "row_count": 38,
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
        "purpose": "No duplicate player_attributes_id values (view grain keyed by player_attributes_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT player_attributes_id, COUNT(*) AS c FROM player_with_max_weight GROUP BY player_attributes_id HAVING c > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's weight equals the maximum weight in Player table",
        "sql": "SELECT COUNT(*) FROM player_with_max_weight v WHERE v.weight IS NULL OR v.weight <> (SELECT MAX(weight) FROM Player)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows reference an existing Player_Attributes.id and joined player_api_id matches Player_Attributes.player_api_id",
        "sql": "SELECT COUNT(*) FROM player_with_max_weight v LEFT JOIN Player_Attributes pa ON v.player_attributes_id = pa.id WHERE pa.id IS NULL OR v.player_api_id IS NULL OR v.player_api_id <> pa.player_api_id",
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
SELECT p.player_api_id, p.player_name, p.weight, pa.id AS player_attributes_id, pa.date, pa.finishing, pa.curve FROM Player p JOIN Player_Attributes pa ON p.player_api_id = pa.player_api_id WHERE p.weight = (SELECT MAX(weight) FROM Player)
```

---

## Skill `match_away_team_with_goals`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `match_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_15fff10d3d56e2a5 |
| output columns | `match_id`, `away_team_api_id`, `away_team_goal`, `team_api_id`, `team_long_name` |
| source tables | `Match`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-match rows linking matches to away team identifiers and away-team goal counts together with team long name for joining or filtering by away-team performance.

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
    "question_id": "bird_dev_1146",
    "question": "Please provide the full name of the away team that scored the most goals.",
    "rewrite": "Task: Find the team_long_name (full name) of the away team(s) whose away_team_goal value is the maximum across all matches.\nRequired outputs: team_long_name\nFilters: Consider rows where away_team_goal equals the maximum value of away_team_goal over all records (i.e., away_team_goal = MAX(away_team_goal)). Map away_team_api_id to team_long_name to return the full name of that away team.",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T01:37:47+00:00",
    "schema_fingerprint": "ea2cc5e8e2760e61"
  },
  "validation": {
    "validated_at": "2026-10-01T01:37:51+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "match_id",
      "away_team_api_id",
      "away_team_goal",
      "team_api_id",
      "team_long_name"
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
        "purpose": "Each match_id in the view should be unique (no duplicate rows for the view grain).",
        "sql": "SELECT COUNT(*) FROM match_away_team_with_goals t1 WHERE (SELECT COUNT(*) FROM match_away_team_with_goals t2 WHERE t2.match_id = t1.match_id) > 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view should reference an existing Match.id (the join didn't introduce rows for non-existent matches).",
        "sql": "SELECT COUNT(*) FROM match_away_team_with_goals v WHERE NOT EXISTS (SELECT 1 FROM \"Match\" m WHERE m.id = v.match_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "away_team_goal in the view must match the underlying Match.away_team_goal (measure reconciliation).",
        "sql": "SELECT COUNT(*) FROM match_away_team_with_goals v JOIN \"Match\" m ON m.id = v.match_id WHERE (v.away_team_goal IS NOT m.away_team_goal) OR (v.away_team_goal IS NULL AND m.away_team_goal IS NOT NULL) OR (v.away_team_goal IS NOT NULL AND m.away_team_goal IS NULL)",
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
SELECT Match.id AS match_id, Match.away_team_api_id, Match.away_team_goal, Team.team_api_id, Team.team_long_name FROM "Match" JOIN "Team" ON Match.away_team_api_id = Team.team_api_id
```

---
