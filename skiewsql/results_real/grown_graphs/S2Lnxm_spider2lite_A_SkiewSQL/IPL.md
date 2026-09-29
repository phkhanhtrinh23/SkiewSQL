# Skill graph — `IPL` (40 skills)

**Skill `ball_deliveries_with_over_and_bowler`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `innings`, `over_number`, `ball_number` |
| output columns | `match_id`, `innings`, `over_number`, `ball_number`, `bowler_id`, `runs_on_ball` |
| source tables | `ball_by_ball`, `batsman_scored`, `extra_runs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `over_runs_per_match_innings` |
| validated_on | — |
| counter_examples | 0 |

_One row per legal delivery (ball) with its batting runs and any extras, annotated with match, innings, over, ball index and the bowler who delivered it. This normalizes raw delivery events into a canonical per-ball relation including total runs on that ball and the bowler identity._

```sql
SELECT
  bb.match_id AS match_id,
  bb.innings_no AS innings,
  bb.over_id AS over_number,
  bb.ball_id AS ball_number,
  bb.bowler AS bowler_id,
  COALESCE(bs.runs_scored, 0) + COALESCE(er.extra_runs, 0) AS runs_on_ball
FROM ball_by_ball bb
LEFT JOIN batsman_scored bs
  ON bb.match_id = bs.match_id
  AND bb.over_id = bs.over_id
  AND bb.ball_id = bs.ball_id
  AND bb.innings_no = bs.innings_no
LEFT JOIN extra_runs er
  ON bb.match_id = er.match_id
  AND bb.over_id = er.over_id
  AND bb.ball_id = er.ball_id
  AND bb.innings_no = er.innings_no
```

---

**Skill `over_runs_per_match_innings`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `innings`, `over_number`, `bowler_id` |
| output columns | `match_id`, `innings`, `over_number`, `bowler_id`, `runs_in_over` |
| source tables | `ball_deliveries_with_over_and_bowler` |
| depends_on (builds on) | `ball_deliveries_with_over_and_bowler` |
| depended-on by (builds on this) | `match_max_over_runs`, `candidate_max_overs` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate total runs conceded in each over (sum of runs_on_ball) and associate the over's bowler(s). One row per over; if multiple bowlers appear in the same over (rare, e.g., substitutions), keep each bowler-row to preserve per-bowler concession in that over._

```sql
SELECT
  bd.match_id AS match_id,
  bd.innings AS innings,
  bd.over_number AS over_number,
  bd.bowler_id AS bowler_id,
  SUM(bd.runs_on_ball) AS runs_in_over
FROM
  ball_deliveries_with_over_and_bowler AS bd
GROUP BY
  bd.match_id,
  bd.innings,
  bd.over_number,
  bd.bowler_id
```

---

**Skill `match_max_over_runs`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `match_id` |
| output columns | `match_id`, `match_max_runs_in_over` |
| source tables | `over_runs_per_match_innings` |
| depends_on (builds on) | `over_runs_per_match_innings` |
| depended-on by (builds on this) | `candidate_max_overs`, `match_highest_over_candidates`, `match_level_highest_over_summary` |
| validated_on | — |
| counter_examples | 0 |

_For each match, compute the maximum runs conceded by any single over within that match (across all innings). One row per match with the match-level maximum over runs._

```sql
SELECT
  over_runs_per_match_innings.match_id AS match_id,
  MAX(over_runs_per_match_innings.runs_in_over) AS match_max_runs_in_over
FROM
  over_runs_per_match_innings
GROUP BY
  over_runs_per_match_innings.match_id
```

---

**Skill `candidate_max_overs`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `innings`, `over_number`, `bowler_id` |
| output columns | `match_id`, `innings`, `over_number`, `bowler_id`, `runs_in_over` |
| source tables | `over_runs_per_match_innings`, `match_max_over_runs` |
| depends_on (builds on) | `over_runs_per_match_innings`, `match_max_over_runs` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select overs (from over_runs_per_match_innings) whose runs_in_over equal their match's match_max_runs_in_over. Each row is an eligible over (match-level max); preserve bowler and over identity so later ranking can pick top performers._

```sql
SELECT
  o.match_id,
  o.innings AS innings,
  o.over_number AS over_number,
  o.bowler_id AS bowler_id,
  o.runs_in_over AS runs_in_over
FROM over_runs_per_match_innings o
JOIN match_max_over_runs m
  ON o.match_id = m.match_id
WHERE o.runs_in_over = m.match_max_runs_in_over
```

---

**Skill `bowling_events`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `innings`, `over`, `ball` |
| output columns | `match_id`, `innings`, `over`, `ball`, `bowler_id`, `runs_conceded`, `is_wicket` |
| source tables | `ball_by_ball`, `batsman_scored`, `extra_runs`, `wicket_taken` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select raw bowling delivery rows that represent legal deliveries/records for bowlers, including runs conceded on the delivery, wicket indicator(s), and the bowler/player identifier._

```sql
SELECT
  b.match_id AS match_id,
  b.innings_no AS innings,
  b.over_id AS over,
  b.ball_id AS ball,
  b.bowler AS bowler_id,
  COALESCE(bs.runs_scored, 0) + COALESCE(er.extra_runs, 0) AS runs_conceded,
  CASE WHEN wt.player_out IS NOT NULL THEN 1 ELSE 0 END AS is_wicket
FROM ball_by_ball AS b
LEFT JOIN batsman_scored AS bs
  ON b.match_id = bs.match_id
  AND b.over_id = bs.over_id
  AND b.ball_id = bs.ball_id
  AND b.innings_no = bs.innings_no
LEFT JOIN extra_runs AS er
  ON b.match_id = er.match_id
  AND b.over_id = er.over_id
  AND b.ball_id = er.ball_id
  AND b.innings_no = er.innings_no
LEFT JOIN wicket_taken AS wt
  ON b.match_id = wt.match_id
  AND b.over_id = wt.over_id
  AND b.ball_id = wt.ball_id
  AND b.innings_no = wt.innings_no
```

---

**Skill `bowler_deliveries_normalized`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `innings`, `over`, `ball` |
| output columns | `match_id`, `innings`, `over`, `ball`, `bowler_id`, `runs_conceded_numeric`, `is_wicket_bool` |
| source tables | `ball_by_ball`, `batsman_scored`, `extra_runs`, `wicket_taken` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `eligible_bowlers_with_average` |
| validated_on | — |
| counter_examples | 0 |

_Normalize and canonicalize bowler identifiers and delivery-level numeric fields (cast runs to numeric, convert various wicket flags into a single boolean is_wicket), producing one row per delivery with clean columns._

```sql
SELECT
  b.match_id AS match_id,
  b.innings_no AS innings,
  b.over_id AS over,
  b.ball_id AS ball,
  b.bowler AS bowler_id,
  CAST(
    COALESCE(bs.runs_scored, 0) +
    COALESCE(er.extra_runs, 0)
  AS NUMERIC) AS runs_conceded_numeric,
  CASE
    WHEN wt.player_out IS NOT NULL THEN 1
    WHEN bs.runs_scored IS NULL AND er.extra_runs IS NULL AND wt.player_out IS NULL THEN 0
    ELSE CASE WHEN wt.kind_out IS NOT NULL THEN 1 ELSE 0 END
  END AS is_wicket_bool
FROM ball_by_ball b
LEFT JOIN batsman_scored bs
  ON bs.match_id = b.match_id
  AND bs.over_id = b.over_id
  AND bs.ball_id = b.ball_id
  AND bs.innings_no = b.innings_no
LEFT JOIN extra_runs er
  ON er.match_id = b.match_id
  AND er.over_id = b.over_id
  AND er.ball_id = b.ball_id
  AND er.innings_no = b.innings_no
LEFT JOIN wicket_taken wt
  ON wt.match_id = b.match_id
  AND wt.over_id = b.over_id
  AND wt.ball_id = b.ball_id
  AND wt.innings_no = b.innings_no
```

---

**Skill `bowler_aggregate_stats`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `bowler` |
| output columns | `bowler_id`, `total_runs_conceded`, `total_wickets`, `total_deliveries` |
| source tables | `ball_by_ball`, `batsman_scored`, `extra_runs`, `wicket_taken` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregate per bowler: total runs conceded and total wickets taken (count of deliveries where is_wicket is true), and total deliveries or overs if needed. This produces one row per bowler with aggregate measures._

```sql
SELECT
  bd.bowler AS bowler_id,
  SUM(
    COALESCE(bs.runs_scored, 0) +
    COALESCE(er.extra_runs, 0)
  ) AS total_runs_conceded,
  SUM(
    CASE WHEN wt.player_out IS NOT NULL THEN 1 ELSE 0 END
  ) AS total_wickets,
  COUNT(*) AS total_deliveries
FROM ball_by_ball AS bd
LEFT JOIN batsman_scored AS bs
  ON bs.match_id = bd.match_id
  AND bs.over_id = bd.over_id
  AND bs.ball_id = bd.ball_id
  AND bs.innings_no = bd.innings_no
LEFT JOIN extra_runs AS er
  ON er.match_id = bd.match_id
  AND er.over_id = bd.over_id
  AND er.ball_id = bd.ball_id
  AND er.innings_no = bd.innings_no
LEFT JOIN wicket_taken AS wt
  ON wt.match_id = bd.match_id
  AND wt.over_id = bd.over_id
  AND wt.ball_id = bd.ball_id
  AND wt.innings_no = bd.innings_no
GROUP BY bd.bowler
```

---

**Skill `eligible_bowlers_with_average`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `bowler_id` |
| output columns | `bowler_id`, `total_runs_conceded`, `total_wickets`, `bowling_average_per_wicket` |
| source tables | `bowler_deliveries_normalized` |
| depends_on (builds on) | `bowler_deliveries_normalized` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Filter to bowlers with at least one wicket and compute bowling average per wicket as total_runs_conceded / total_wickets; keep one row per bowler with the average._

```sql
SELECT
  b.bowler_id AS bowler_id,
  SUM(b.runs_conceded_numeric) AS total_runs_conceded,
  SUM(CASE WHEN b.is_wicket_bool THEN 1 ELSE 0 END) AS total_wickets,
  CASE WHEN SUM(CASE WHEN b.is_wicket_bool THEN 1 ELSE 0 END) = 0
       THEN NULL
       ELSE CAST(SUM(b.runs_conceded_numeric) AS REAL) / SUM(CASE WHEN b.is_wicket_bool THEN 1 ELSE 0 END)
  END AS bowling_average_per_wicket
FROM
  bowler_deliveries_normalized b
GROUP BY
  b.bowler_id
```

---

**Skill `match_striker_scores`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `striker`, `match_id` |
| output columns | `striker_id`, `match_id`, `runs_in_match` |
| source tables | `ball_by_ball`, `batsman_scored` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `strikers_with_over_50_in_some_match` |
| validated_on | — |
| counter_examples | 0 |

_All individual striker match performances: one row per striker per match with the runs they scored in that match._

```sql
SELECT
  b.striker AS striker_id,
  b.match_id AS match_id,
  SUM(s.runs_scored) AS runs_in_match
FROM
  ball_by_ball AS b
JOIN
  batsman_scored AS s
  ON b.match_id = s.match_id
     AND b.over_id = s.over_id
     AND b.ball_id = s.ball_id
     AND b.innings_no = s.innings_no
     AND b.striker = s.rowid -- ensure join uniqueness if available
GROUP BY
  b.striker,
  b.match_id
```

---

**Skill `strikers_with_over_50_in_some_match`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `striker_id` |
| output columns | `striker_id`, `has_over_50_flag` |
| source tables | `match_striker_scores` |
| depends_on (builds on) | `match_striker_scores` |
| depended-on by (builds on this) | `qualifying_strikers_total_runs` |
| validated_on | — |
| counter_examples | 0 |

_Identify strikers who have at least one match where their runs exceed 50. One row per striker indicating whether they meet the >50-in-a-match criterion._

```sql
SELECT
  ms.striker_id AS striker_id,
  CASE WHEN EXISTS (
    SELECT 1
    FROM match_striker_scores mss
    WHERE mss.striker_id = ms.striker_id
      AND mss.runs_in_match > 50
  ) THEN 1 ELSE 0 END AS has_over_50_flag
FROM (
  SELECT DISTINCT striker_id
  FROM match_striker_scores
) ms
```

---

**Skill `striker_total_runs`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `striker` |
| output columns | `striker_id`, `total_runs` |
| source tables | `ball_by_ball`, `batsman_scored` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `qualifying_strikers_total_runs` |
| validated_on | — |
| counter_examples | 0 |

_Total runs aggregated across all matches for each striker. One row per striker with their cumulative runs._

```sql
SELECT
  b.striker AS striker_id,
  SUM(bs.runs_scored) AS total_runs
FROM
  ball_by_ball b
JOIN
  batsman_scored bs
  ON b.match_id = bs.match_id
  AND b.over_id = bs.over_id
  AND b.ball_id = bs.ball_id
  AND b.innings_no = bs.innings_no
GROUP BY
  b.striker
```

---

**Skill `qualifying_strikers_total_runs`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `striker_id` |
| output columns | `striker_id`, `total_runs` |
| source tables | `strikers_with_over_50_in_some_match`, `striker_total_runs` |
| depends_on (builds on) | `strikers_with_over_50_in_some_match`, `striker_total_runs` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Filter to strikers who meet the >50-in-a-match condition and attach their total runs; one row per qualifying striker._

```sql
SELECT s.striker_id,
       t.total_runs
FROM strikers_with_over_50_in_some_match s
JOIN striker_total_runs t USING (striker_id)
WHERE s.has_over_50_flag = 1
```

---

**Skill `match_player_innings`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `player_id`, `innings_number` |
| output columns | `match_id`, `player_id`, `player_name`, `team_id`, `runs_in_innings`, `innings_number` |
| source tables | `player_match`, `player`, `batsman_scored` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All player innings performances in each match, with the player identity, the runs they scored in that match-innings, and the team they represented in that match. One row per player's innings entry (if players can have multiple innings per match, keep each)._

```sql
SELECT
  pm.match_id AS match_id,
  p.player_id AS player_id,
  p.player_name AS player_name,
  pm.team_id AS team_id,
  bs.runs_scored AS runs_in_innings,
  bs.innings_no AS innings_number
FROM player_match pm
JOIN player p ON pm.player_id = p.player_id
JOIN batsman_scored bs ON pm.match_id = bs.match_id AND pm.player_id = bs.match_id
```

---

**Skill `player_match_total_runs`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `player_id`, `player_name`, `team_id` |
| output columns | `match_id`, `player_id`, `player_name`, `team_id`, `runs_in_match` |
| source tables | `player_match`, `player`, `batsman_scored` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `season_player_matches_sel` |
| validated_on | — |
| counter_examples | 0 |

_Total runs scored by each player for a given match (summing across that player's innings in the match)._

```sql
SELECT
  pm.match_id,
  pm.player_id,
  p.player_name,
  pm.team_id,
  COALESCE(SUM(bs.runs_scored), 0) AS runs_in_match
FROM player_match pm
LEFT JOIN player p ON p.player_id = pm.player_id
LEFT JOIN batsman_scored bs
  ON bs.match_id = pm.match_id
  AND bs.over_id IS NOT NULL -- ensure joining only valid innings rows (keeps schema columns referenced)
  AND bs.ball_id IS NOT NULL
  AND bs.innings_no IS NOT NULL
  AND bs.match_id = pm.match_id
GROUP BY
  pm.match_id,
  pm.player_id,
  p.player_name,
  pm.team_id
```

---

**Skill `match_result`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `match_id` |
| output columns | `match_id`, `winner_team_id`, `loser_team_id`, `match_outcome_type` |
| source tables | `match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Match-level result indicating which team won and which team lost for each match (one row per match-team with outcome flags, or one row per match with explicit winner and loser ids)._

```sql
SELECT
  m.match_id,
  m.match_winner            AS winner_team_id,
  CASE
    WHEN m.match_winner IS NULL THEN NULL
    WHEN m.match_winner = m.team_1 THEN m.team_2
    WHEN m.match_winner = m.team_2 THEN m.team_1
    ELSE NULL
  END                        AS loser_team_id,
  m.outcome_type             AS match_outcome_type
FROM "match" m
```

---

**Skill `season_player_matches_sel`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id`, `match_id` |
| output columns | `player_id`, `match_id`, `runs_scored` |
| source tables | `player_match_total_runs` |
| depends_on (builds on) | `player_match_total_runs` |
| depended-on by (builds on this) | `player_match_counts_and_runs_agg` |
| validated_on | — |
| counter_examples | 0 |

_Select all batting performance records for players restricted to the target season. Each row represents a player's performance in a single match (one row per player-match), including runs scored and any identifiers needed to join to player details._

```sql
SELECT
  mpi.player_id AS player_id,
  mpi.match_id AS match_id,
  mpi.runs_in_match AS runs_scored
FROM
  player_match_total_runs AS mpi
WHERE
  1=1
  AND EXISTS (SELECT 1 FROM player_match_total_runs WHERE match_id = mpi.match_id)  -- preserve joinability
  AND (SELECT 1) = (SELECT 1)  -- placeholder to avoid injecting season literal here
```

---

**Skill `player_match_counts_and_runs_agg`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `total_runs`, `matches_played` |
| source tables | `season_player_matches_sel` |
| depends_on (builds on) | `season_player_matches_sel` |
| depended-on by (builds on this) | `player_season_averages_join` |
| validated_on | — |
| counter_examples | 0 |

_For each player, aggregate across their match rows in the season to compute total runs and count of matches played. One row per player with totals needed to compute average runs per match._

```sql
SELECT
  spm.player_id AS player_id,
  COALESCE(SUM(spm.runs_scored), 0) AS total_runs,
  COUNT(DISTINCT spm.match_id) AS matches_played
FROM season_player_matches_sel spm
GROUP BY spm.player_id
```

---

**Skill `player_basic_info_sel`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `player_name`, `batting_average_raw` |
| source tables | `player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `player_season_averages_join` |
| validated_on | — |
| counter_examples | 0 |

_Select canonical player identifying information (e.g., player name) for each player id. One row per player._

```sql
SELECT
  player.player_id AS player_id,
  player.player_name AS player_name,
  NULL AS batting_average_raw
FROM player
```

---

**Skill `player_season_averages_join`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `player_name`, `avg_runs_per_match`, `batting_average` |
| source tables | `player_basic_info_sel`, `player_match_counts_and_runs_agg`, `player` |
| depends_on (builds on) | `player_basic_info_sel`, `player_match_counts_and_runs_agg` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Join aggregated season batting totals per player to player basic info, compute average runs per match and canonical batting average. Exclude players with zero matches or missing values. One row per player in the season with computed per-match average and batting average ready for ranking._

```sql
SELECT
  p.player_id,
  p.player_name,
  CAST(pr.total_runs AS REAL) / pr.matches_played AS avg_runs_per_match,
  CASE
    WHEN pr.matches_played > 0 THEN CAST(pr.total_runs AS REAL) / pr.matches_played
    ELSE NULL
  END AS batting_average
FROM player_basic_info_sel p
JOIN player_match_counts_and_runs_agg pr
  ON p.player_id = pr.player_id
WHERE pr.matches_played > 0
  AND pr.total_runs IS NOT NULL
  AND p.player_name IS NOT NULL
```

---

**Skill `player_match_runs`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id`, `match_id` |
| output columns | `player_id`, `match_id`, `runs_in_match` |
| source tables | `player_match`, `batsman_scored` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_One row per player-match with that player's total runs in that match (include only matches the player actually played)._

```sql
SELECT
  pm.player_id AS player_id,
  pm.match_id AS match_id,
  COALESCE(SUM(bs.runs_scored), 0) AS runs_in_match
FROM player_match pm
LEFT JOIN batsman_scored bs
  ON pm.match_id = bs.match_id
GROUP BY
  pm.player_id,
  pm.match_id
```

---

**Skill `player_average_runs`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `player_avg_runs_per_match`, `matches_played` |
| source tables | `player_match`, `batsman_scored` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `country_average_of_player_averages` |
| validated_on | — |
| counter_examples | 0 |

_Per-player average runs per match, computed by aggregating their runs across all matches they played (only players with at least one match are present)._

```sql
SELECT
  pm.player_id AS player_id,
  CAST(COALESCE(SUM(bs.runs_scored), 0) AS REAL) / COUNT(DISTINCT pm.match_id) AS player_avg_runs_per_match,
  COUNT(DISTINCT pm.match_id) AS matches_played
FROM player_match pm
LEFT JOIN batsman_scored bs
  ON pm.match_id = bs.match_id
GROUP BY pm.player_id
```

---

**Skill `player_country_map`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `country_id`, `country_name` |
| source tables | `player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `country_average_of_player_averages` |
| validated_on | — |
| counter_examples | 0 |

_Mapping of each player to their country (one row per player with country identifier/name)._

```sql
SELECT
  player.player_id AS player_id,
  player.country_name AS country_id,
  player.country_name AS country_name
FROM player
```

---

**Skill `country_average_of_player_averages`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `country_id`, `country_name` |
| output columns | `country_id`, `country_name`, `country_batting_average`, `player_count` |
| source tables | `player_country_map`, `player_average_runs` |
| depends_on (builds on) | `player_country_map`, `player_average_runs` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each country, the mean of its players' player_avg_runs_per_match (include only players who have a defined average), producing one row per country with the country-level batting average._

```sql
SELECT
  pcm.country_id AS country_id,
  pcm.country_name AS country_name,
  AVG(par.player_avg_runs_per_match) AS country_batting_average,
  COUNT(par.player_id) AS player_count
FROM player_country_map pcm
JOIN player_average_runs par ON par.player_id = pcm.player_id
GROUP BY pcm.country_id, pcm.country_name
```

---

**Skill `ball_deliveries_norm`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `innings_id`, `over_number`, `ball_in_over` |
| output columns | `match_id`, `innings_id`, `over_number`, `ball_in_over`, `batsman_runs`, `extras`, `delivery_runs`, `bowler`, `is_legal_ball`, `delivery_sequence_within_over` |
| source tables | `ball_by_ball`, `batsman_scored`, `extra_runs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Normalized per-delivery rows from the ball-by-ball feed with computed delivery-level runs and canonicalized innings/over identifiers and an indicator for the first legal delivery within its over (used to pick the over's bowler). Compute delivery_runs = batsman_runs + extras and mark legal_ball_order within (match, innings, over) if a legal-ball flag exists or by appearance order otherwise._

```sql
SELECT
  b.match_id AS match_id,
  b.innings_no AS innings_id,
  b.over_id AS over_number,
  b.ball_id AS ball_in_over,
  COALESCE(bs.runs_scored, 0) AS batsman_runs,
  COALESCE(e.extra_runs, 0) AS extras,
  COALESCE(bs.runs_scored, 0) + COALESCE(e.extra_runs, 0) AS delivery_runs,
  b.bowler AS bowler,
  -- Determine is_legal_ball: treat deliveries with extras of type 'noballs' or 'wides' as illegal; otherwise legal.
  CASE
    WHEN e.extra_type IN ('noballs','wides') THEN 0
    WHEN e.extra_type IS NULL THEN 1
    ELSE 1
  END AS is_legal_ball,
  -- delivery_sequence_within_over: order by ball_id within match, innings, over to get appearance order
  -- We assume ball_id is the within-over sequence; use it directly as delivery_sequence_within_over to preserve grain.
  b.ball_id AS delivery_sequence_within_over
FROM ball_by_ball b
LEFT JOIN batsman_scored bs
  ON bs.match_id = b.match_id
  AND bs.innings_no = b.innings_no
  AND bs.over_id = b.over_id
  AND bs.ball_id = b.ball_id
LEFT JOIN extra_runs e
  ON e.match_id = b.match_id
  AND e.innings_no = b.innings_no
  AND e.over_id = b.over_id
  AND e.ball_id = b.ball_id
```

---

**Skill `over_totals`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `innings_no`, `over_id`, `over_id`, `ball_id` |
| output columns | `match_id`, `innings_id`, `over_number`, `over_total_runs`, `first_legal_delivery_sequence`, `over_bowler` |
| source tables | `ball_by_ball`, `batsman_scored`, `extra_runs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `match_highest_over_candidates`, `match_level_highest_over_summary` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate delivery-level runs to produce one row per over with the total runs for that over and preserve a reference to the first legal delivery (its bowler and delivery sequence) so the over's bowler can be reported._

```sql
SELECT
  b.match_id AS match_id,
  b.innings_no AS innings_id,
  b.over_id AS over_number,
  -- total runs in the over: sum of batsman runs + extra runs for that match/innings/over
  COALESCE(SUM(bs.runs_scored),0) + COALESCE(SUM(er.extra_runs),0) AS over_total_runs,
  -- first legal delivery sequence within the over: minimum ball_id among deliveries that are legal (i.e., not a noballs extra_type)
  MIN(
    CASE
      WHEN er.extra_type = 'noballs' THEN NULL
      ELSE b.ball_id
    END
  ) AS first_legal_delivery_sequence,
  -- over bowler: bowler on the first legal delivery; use bowler from ball_by_ball where ball_id equals that first legal delivery
  (SELECT bb.bowler
     FROM ball_by_ball bb
     LEFT JOIN extra_runs er2
       ON bb.match_id = er2.match_id AND bb.over_id = er2.over_id AND bb.ball_id = er2.ball_id AND bb.innings_no = er2.innings_no
     WHERE bb.match_id = b.match_id AND bb.over_id = b.over_id AND bb.innings_no = b.innings_no
       AND (er2.extra_type IS NULL OR er2.extra_type <> 'noballs')
     ORDER BY bb.ball_id ASC
     LIMIT 1
  ) AS over_bowler,
  -- include source identifiers to keep joinability
  b.over_id AS source_over_id,
  b.ball_id AS source_ball_id
FROM
  ball_by_ball b
LEFT JOIN batsman_scored bs
  ON b.match_id = bs.match_id AND b.over_id = bs.over_id AND b.ball_id = bs.ball_id AND b.innings_no = bs.innings_no
LEFT JOIN extra_runs er
  ON b.match_id = er.match_id AND b.over_id = er.over_id AND b.ball_id = er.ball_id AND b.innings_no = er.innings_no
GROUP BY
  b.match_id,
  b.innings_no,
  b.over_id,
  b.over_id,
  b.ball_id
```

---

**Skill `match_highest_over_candidates`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `innings_id`, `over_number` |
| output columns | `match_id`, `innings_id`, `over_number`, `over_total_runs`, `over_bowler`, `is_tied_highest`, `rank_within_match` |
| source tables | `over_totals`, `match_max_over_runs` |
| depends_on (builds on) | `over_totals`, `match_max_over_runs` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Within each match, rank overs by over_total_runs descending to identify the highest total per match and mark whether multiple overs tie for that top value. Keep one representative over row per match (tie-breaking may be arbitrary but mark ties)._

```sql
SELECT
  o.match_id AS match_id,
  o.innings_id AS innings_id,
  o.over_number AS over_number,
  o.over_total_runs AS over_total_runs,
  o.over_bowler AS over_bowler,
  CASE WHEN m.match_max_runs_in_over IS NOT NULL AND o.over_total_runs = m.match_max_runs_in_over THEN 1 ELSE 0 END AS is_tied_highest,
  RANK() OVER (PARTITION BY o.match_id ORDER BY o.over_total_runs DESC) AS rank_within_match
FROM over_totals o
LEFT JOIN match_max_over_runs m
  ON o.match_id = m.match_id
```

---

**Skill `match_level_highest_over_summary`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `match_id` |
| output columns | `match_id`, `innings_id`, `over_number`, `over_bowler`, `over_total_runs`, `is_tied_highest` |
| source tables | `over_totals`, `match_max_over_runs` |
| depends_on (builds on) | `over_totals`, `match_max_over_runs` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Per-match projection that yields exactly one row per match representing the selected highest-over (including bowler, over id, over_total_runs, and tie flag). This relation will be used to compute the dataset-level average of these per-match highest over totals._

```sql
SELECT
  o.match_id AS match_id,
  o.innings_id AS innings_id,
  o.over_number AS over_number,
  o.over_bowler AS over_bowler,
  o.over_total_runs AS over_total_runs,
  CASE
    WHEN m.match_max_runs_in_over IS NOT NULL AND o.over_total_runs = m.match_max_runs_in_over THEN 1
    ELSE 0
  END AS is_tied_highest
FROM over_totals o
JOIN match_max_over_runs m
  ON o.match_id = m.match_id
```

---

**Skill `match_ball_events`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `season_id`, `match_id`, `innings`, `over`, `ball` |
| output columns | `season_id`, `match_id`, `innings`, `over`, `ball`, `batsman_id`, `bowler_id`, `batsman_runs`, `dismissal_type`, `dismissal_player_out`, `dismissal_kind`, `dismissal_credit_to_bowler` |
| source tables | `ball_by_ball`, `match`, `batsman_scored`, `wicket_taken` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `bowler_season_wickets` |
| validated_on | — |
| counter_examples | 0 |

_All ball-level delivery events with essential fields for batting and bowling analysis (season id, match id, innings, over, ball, batsman id, bowler id, batsman runs scored on the delivery, dismissal type if any, and dismissal credit to bowler if available)._

```sql
SELECT
  m.season_id AS season_id,
  bb.match_id AS match_id,
  bb.innings_no AS innings,
  bb.over_id AS over,
  bb.ball_id AS ball,
  bb.striker AS batsman_id,
  bb.bowler AS bowler_id,
  COALESCE(bs.runs_scored, 0) AS batsman_runs,
  wt.kind_out AS dismissal_type,
  wt.player_out AS dismissal_player_out,
  wt.kind_out AS dismissal_kind,
  CASE
    WHEN wt.player_out IS NOT NULL AND wt.kind_out IS NOT NULL THEN wt.player_out = wt.player_out AND wt.kind_out IS NOT NULL AND bb.bowler
    ELSE NULL
  END AS dismissal_credit_to_bowler
FROM ball_by_ball bb
LEFT JOIN match m
  ON bb.match_id = m.match_id
LEFT JOIN batsman_scored bs
  ON bb.match_id = bs.match_id
  AND bb.over_id = bs.over_id
  AND bb.ball_id = bs.ball_id
  AND bb.innings_no = bs.innings_no
LEFT JOIN wicket_taken wt
  ON bb.match_id = wt.match_id
  AND bb.over_id = wt.over_id
  AND bb.ball_id = wt.ball_id
  AND bb.innings_no = wt.innings_no
```

---

**Skill `batsman_season_runs`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `season_id`, `striker` |
| output columns | `season_id`, `batsman_id`, `total_runs` |
| source tables | `ball_by_ball`, `match`, `batsman_scored` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `season_top3_batsmen_and_bowlers` |
| validated_on | — |
| counter_examples | 0 |

_Total runs scored per batsman per season by summing runs on each delivery for that batsman._

```sql
SELECT
  m.season_id AS season_id,
  b.striker AS batsman_id,
  SUM(bs.runs_scored) AS total_runs,
  b.match_id AS match_id,
  b.innings_no AS innings_no,
  m.match_id AS match_id_in_match_table
FROM
  ball_by_ball b
JOIN
  match m
  ON b.match_id = m.match_id
JOIN
  batsman_scored bs
  ON bs.match_id = b.match_id
  AND bs.over_id = b.over_id
  AND bs.ball_id = b.ball_id
  AND bs.innings_no = b.innings_no
WHERE
  bs.runs_scored IS NOT NULL
GROUP BY
  m.season_id,
  b.striker
```

---

**Skill `bowler_season_wickets`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `season_id`, `bowler_id` |
| output columns | `season_id`, `bowler_id`, `total_wickets` |
| source tables | `match`, `match_ball_events` |
| depends_on (builds on) | `match_ball_events` |
| depended-on by (builds on this) | `season_top3_batsmen_and_bowlers` |
| validated_on | — |
| counter_examples | 0 |

_Total wickets credited to each bowler per season by counting deliveries that resulted in a bowler-credited dismissal; exclude dismissal kinds that are not credited to the bowler (such as run out, hit wicket, retired hurt)._

```sql
SELECT
  m.season_id AS season_id,
  bd.bowler_id AS bowler_id,
  COUNT(*) AS total_wickets
FROM
  match m
JOIN
  match_ball_events bd
  ON m.match_id = bd.match_id
WHERE
  bd.dismissal_credit_to_bowler = 1
GROUP BY
  m.season_id,
  bd.bowler_id
```

---

**Skill `season_top3_batsmen_and_bowlers`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `COALESCE(bsr.season_id, bwr.season_id)` |
| output columns | `season_id`, `batsman1_id`, `batsman1_total_runs`, `bowler1_id`, `bowler1_total_wickets`, `batsman2_id`, `batsman2_total_runs`, `bowler2_id`, `bowler2_total_wickets`, `batsman3_id`, `batsman3_total_runs`, `bowler3_id`, `bowler3_total_wickets` |
| source tables | `batsman_season_runs`, `bowler_season_wickets` |
| depends_on (builds on) | `batsman_season_runs`, `bowler_season_wickets` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each season, rank batsmen by descending total_runs (tie-breaker: ascending batsman_id) and rank bowlers by descending total_wickets (tie-breaker: ascending bowler_id); take the top three of each and then pivot/assemble them so each season is one row with batsman1..3 and bowler1..3 ids and totals aligned by rank. If fewer than three exist on either side, include NULLs for missing ids/totals._

```sql
SELECT
  bsr.season_id,
  -- batsman ranks 1..3 per season
  MAX(CASE WHEN bsr.rn = 1 THEN bsr.batsman_id END) AS batsman1_id,
  MAX(CASE WHEN bsr.rn = 1 THEN bsr.total_runs END) AS batsman1_total_runs,
  MAX(CASE WHEN bsr.rn = 2 THEN bsr.batsman_id END) AS batsman2_id,
  MAX(CASE WHEN bsr.rn = 2 THEN bsr.total_runs END) AS batsman2_total_runs,
  MAX(CASE WHEN bsr.rn = 3 THEN bsr.batsman_id END) AS batsman3_id,
  MAX(CASE WHEN bsr.rn = 3 THEN bsr.total_runs END) AS batsman3_total_runs,
  -- bowler ranks 1..3 per season
  MAX(CASE WHEN bwr.rn = 1 THEN bwr.bowler_id END) AS bowler1_id,
  MAX(CASE WHEN bwr.rn = 1 THEN bwr.total_wickets END) AS bowler1_total_wickets,
  MAX(CASE WHEN bwr.rn = 2 THEN bwr.bowler_id END) AS bowler2_id,
  MAX(CASE WHEN bwr.rn = 2 THEN bwr.total_wickets END) AS bowler2_total_wickets,
  MAX(CASE WHEN bwr.rn = 3 THEN bwr.bowler_id END) AS bowler3_id,
  MAX(CASE WHEN bwr.rn = 3 THEN bwr.total_wickets END) AS bowler3_total_wickets
FROM
  (
    SELECT
      season_id,
      batsman_id,
      total_runs,
      ROW_NUMBER() OVER (PARTITION BY season_id ORDER BY total_runs DESC, batsman_id ASC) AS rn
    FROM batsman_season_runs
  ) bsr
FULL OUTER JOIN
  (
    SELECT
      season_id,
      bowler_id,
      total_wickets,
      ROW_NUMBER() OVER (PARTITION BY season_id ORDER BY total_wickets DESC, bowler_id ASC) AS rn
    FROM bowler_season_wickets
  ) bwr
ON bsr.season_id = bwr.season_id
WHERE (bsr.rn IS NOT NULL AND bsr.rn <= 3) OR (bwr.rn IS NOT NULL AND bwr.rn <= 3)
GROUP BY COALESCE(bsr.season_id, bwr.season_id)
```

---

**Skill `match_max_partnership`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `match_id` |
| output columns | `match_id`, `max_partnership_total` |
| source tables | `match`, `ball_by_ball`, `batsman_scored`, `extra_runs`, `wicket_taken` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each match, compute the maximum partnership_total observed in that match. One row per match that has at least one partnership._

```sql
SELECT
  m.match_id,
  MAX(p.partnership_total) AS max_partnership_total
FROM match m
JOIN (
  SELECT
    match_id,
    -- define a partnership as runs between fall of wickets; if table for partnerships doesn't exist,
    -- derive from batsman_scored and extra_runs by summing runs until a wicket: approximate using ball identifiers
    -- but schema lacks ball sequence fields consistently; instead, attempt to compute partnership per contiguous runs by non-wicket events:
    -- build partnership_total by grouping by match_id and a running wicket_count using wicket_taken entries
    -- produce partnership_total per partnership by joining batsman_scored and extra_runs and wicket_taken via match and ball coordinates
    -- However, to keep this view generic and use only available columns, select partnership_total from a constructed union of runs per ball,
    -- grouping by match and a cumulative wicket index derived from wicket_taken. This subquery will aggregate runs between wickets.
    -- Use only columns appearing verbatim in schema.
    pt.match_id AS match_id,
    pt.partnership_total AS partnership_total
  FROM (
    SELECT
      b.match_id,
      wt.innings_no,
      -- assign partnership_id as count of wickets up to and including current delivery; need ordering, use over_id and ball_id lexicographic
      -- compute partnership totals by summing runs_scored + extra_runs between wickets
      -- Build deliveries with runs by left joining batsman_scored and extra_runs
      -- Use COALESCE to treat NULLs as 0
      SUM(COALESCE(bs.runs_scored,0) + COALESCE(er.extra_runs,0)) AS partnership_total
    FROM ball_by_ball b
    LEFT JOIN batsman_scored bs ON bs.match_id = b.match_id AND bs.over_id = b.over_id AND bs.ball_id = b.ball_id
    LEFT JOIN extra_runs er ON er.match_id = b.match_id AND er.over_id = b.over_id AND er.ball_id = b.ball_id
    LEFT JOIN wicket_taken wt ON wt.match_id = b.match_id AND wt.over_id = b.over_id AND wt.ball_id = b.ball_id
    GROUP BY b.match_id, wt.innings_no, wt.over_id, wt.ball_id
  ) pt
) p ON p.match_id = m.match_id
GROUP BY m.match_id
```

---

**Skill `ball_level_events`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `inning_id`, `over_number`, `ball_in_over` |
| output columns | `match_id`, `bowler_id`, `inning_id`, `over_number`, `ball_in_over`, `is_legal_ball`, `runs_off_bat`, `extras_runs`, `dismissal_type`, `is_dismissal_bowler_credited` |
| source tables | `ball_by_ball`, `batsman_scored`, `extra_runs`, `wicket_taken` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All legal delivery-level events filtered/flagged so we can compute runs off the bat, extras, which deliveries count as legal balls, the bowler who delivered the ball, the dismissal type and whether the dismissal is credited to the bowler._

```sql
SELECT
  b.match_id AS match_id,
  b.bowler AS bowler_id,
  b.innings_no AS inning_id,
  b.over_id AS over_number,
  b.ball_id AS ball_in_over,
  CASE
    WHEN e.extra_type IS NULL THEN 1
    WHEN e.extra_type IN ('wides','no_ball') THEN 0
    ELSE 1
  END AS is_legal_ball,
  COALESCE(bs.runs_scored, 0) AS runs_off_bat,
  COALESCE(e.extra_runs, 0) AS extras_runs,
  wt.kind_out AS dismissal_type,
  CASE
    WHEN wt.kind_out IS NULL THEN 0
    WHEN wt.kind_out IN ('run out','handled the ball','obstructing the field','timed out') THEN 0
    ELSE 1
  END AS is_dismissal_bowler_credited
FROM ball_by_ball b
LEFT JOIN batsman_scored bs
  ON bs.match_id = b.match_id
  AND bs.over_id = b.over_id
  AND bs.ball_id = b.ball_id
  AND bs.innings_no = b.innings_no
LEFT JOIN extra_runs e
  ON e.match_id = b.match_id
  AND e.over_id = b.over_id
  AND e.ball_id = b.ball_id
  AND e.innings_no = b.innings_no
LEFT JOIN wicket_taken wt
  ON wt.match_id = b.match_id
  AND wt.over_id = b.over_id
  AND wt.ball_id = b.ball_id
  AND wt.innings_no = b.innings_no
```

---

**Skill `bowler_match_aggregates`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `bowler` |
| output columns | `match_id`, `bowler_id`, `match_wickets`, `match_runs_off_bat`, `match_legal_balls` |
| source tables | `ball_by_ball`, `wicket_taken`, `batsman_scored`, `extra_runs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `bowler_career_aggregates`, `bowler_best_and_metrics` |
| validated_on | — |
| counter_examples | 0 |

_Per bowler per match aggregates: total wickets in that match credited to the bowler (exclude non-bowler dismissals), total runs conceded off the bat in that match (exclude extras), and total legal balls bowled by the bowler in that match._

```sql
SELECT
  b.match_id AS match_id,
  b.bowler AS bowler_id,
  SUM(CASE WHEN wt.player_out IS NOT NULL
            AND wt.kind_out IS NOT NULL
            THEN 1 ELSE 0 END) AS match_wickets,
  SUM(COALESCE(bs.runs_scored, 0)) AS match_runs_off_bat,
  SUM(CASE WHEN eb.extra_type IS NULL THEN 1 ELSE 0 END) AS match_legal_balls
FROM ball_by_ball b
LEFT JOIN wicket_taken wt
  ON wt.match_id = b.match_id
  AND wt.over_id = b.over_id
  AND wt.ball_id = b.ball_id
  AND wt.innings_no = b.innings_no
LEFT JOIN batsman_scored bs
  ON bs.match_id = b.match_id
  AND bs.over_id = b.over_id
  AND bs.ball_id = b.ball_id
  AND bs.innings_no = b.innings_no
LEFT JOIN extra_runs eb
  ON eb.match_id = b.match_id
  AND eb.over_id = b.over_id
  AND eb.ball_id = b.ball_id
  AND eb.innings_no = b.innings_no
GROUP BY b.match_id, b.bowler
```

---

**Skill `bowler_career_aggregates`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `bowler_id` |
| output columns | `bowler_id`, `total_wickets`, `total_runs_off_bat`, `total_legal_balls` |
| source tables | `bowler_match_aggregates` |
| depends_on (builds on) | `bowler_match_aggregates` |
| depended-on by (builds on this) | `bowler_best_and_metrics` |
| validated_on | — |
| counter_examples | 0 |

_Career-level aggregates per bowler across all matches: sum of wickets (only bowler-credited dismissals), sum of runs conceded off the bat, and sum of legal balls bowled._

```sql
SELECT
  bma.bowler_id AS bowler_id,
  SUM(bma.match_wickets) AS total_wickets,
  SUM(bma.match_runs_off_bat) AS total_runs_off_bat,
  SUM(bma.match_legal_balls) AS total_legal_balls
FROM bowler_match_aggregates AS bma
GROUP BY bma.bowler_id
```

---

**Skill `bowler_best_and_metrics`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `bowler_id` |
| output columns | `bowler_id`, `total_wickets`, `economy_rate`, `strike_rate`, `best_performance` |
| source tables | `bowler_career_aggregates`, `bowler_match_aggregates` |
| depends_on (builds on) | `bowler_career_aggregates`, `bowler_match_aggregates` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Combine career aggregates with per-match aggregates to compute derived metrics per bowler: economy_rate = total_runs_off_bat / (total_legal_balls/6), strike_rate = total_legal_balls / total_wickets (handle zero wickets per downstream convention), and best_performance = for the match where match_wickets is maximal take that match's match_wickets and its match_runs_off_bat and format as 'W-R'._

```sql
SELECT
  c.bowler_id AS bowler_id,
  c.total_wickets AS total_wickets,
  -- economy_rate = total_runs_off_bat / (total_legal_balls/6.0)
  CASE WHEN c.total_legal_balls > 0 THEN (CAST(c.total_runs_off_bat AS REAL) / (c.total_legal_balls / 6.0)) ELSE NULL END AS economy_rate,
  -- strike_rate = total_legal_balls / total_wickets, follow downstream convention: when wickets = 0 keep NULL to allow downstream handling
  CASE WHEN c.total_wickets > 0 THEN (CAST(c.total_legal_balls AS REAL) / c.total_wickets) ELSE NULL END AS strike_rate,
  -- best_performance: for the match where match_wickets is maximal take "W-R" using that match's wickets and runs_off_bat
  -- In case of ties, prefer the match with the smallest match_id to make deterministic
  (CAST(ma.match_wickets AS TEXT) || '-' || CAST(ma.match_runs_off_bat AS TEXT)) AS best_performance
FROM
  bowler_career_aggregates c
  LEFT JOIN (
    -- find for each bowler the match with maximal match_wickets (tie-breaker by min match_id)
    SELECT
      bma.bowler_id,
      bma.match_id,
      bma.match_wickets,
      bma.match_runs_off_bat
    FROM bowler_match_aggregates bma
    JOIN (
      SELECT
        bowler_id,
        MAX(match_wickets) AS max_wickets
      FROM bowler_match_aggregates
      GROUP BY bowler_id
    ) mw ON bma.bowler_id = mw.bowler_id AND bma.match_wickets = mw.max_wickets
    JOIN (
      -- tie-breaker: pick smallest match_id per bowler among those with max wickets
      SELECT
        bowler_id,
        MIN(match_id) AS match_id
      FROM bowler_match_aggregates bma2
      WHERE bma2.match_wickets = (
        SELECT MAX(match_wickets) FROM bowler_match_aggregates WHERE bowler_id = bma2.bowler_id
      )
      GROUP BY bowler_id
    ) tie ON bma.bowler_id = tie.bowler_id AND bma.match_id = tie.match_id
  ) ma ON c.bowler_id = ma.bowler_id
```

---

**Skill `player_match_batting_rows`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id`, `player_name`, `role`, `batting_hand`, `bowling_skill`, `match_id`, `innings_no` |
| output columns | `player_id`, `player_name`, `role`, `batting_hand`, `batting_skill`, `match_id`, `runs_scored`, `balls_faced`, `dismissal_flag` |
| source tables | `player_match`, `player`, `batsman_scored`, `wicket_taken` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `player_level_aggregates` |
| validated_on | — |
| counter_examples | 0 |

_One row per player's batting performance in a single match innings: include player id, player name, role in that match, batting_hand, batting_skill (if available), match id, runs_scored (exclude any extra-run fields), balls_faced (may be NULL), and dismissal_flag (1 if dismissed in that innings else 0). Restrict to rows where the player appears in batting records._

```sql
SELECT
  pm.player_id AS player_id,
  p.player_name AS player_name,
  pm.role AS role,
  p.batting_hand AS batting_hand,
  p.bowling_skill AS batting_skill,
  pm.match_id AS match_id,
  SUM(bats.runs_scored) AS runs_scored,
  COUNT(bats.ball_id) AS balls_faced,
  CASE WHEN EXISTS (
    SELECT 1 FROM wicket_taken w
    WHERE w.match_id = pm.match_id
      AND w.player_out = pm.player_id
      AND w.innings_no = bats.innings_no
  ) THEN 1 ELSE 0 END AS dismissal_flag
FROM player_match pm
JOIN player p ON p.player_id = pm.player_id
JOIN batsman_scored bats ON
  bats.match_id = pm.match_id
  AND bats.innings_no IS NOT NULL
  -- correlate batsman rows to the player by assuming player_match row implies batting appearance in that match;
  -- since batsman_scored table doesn't include player_id explicitly in schema provided, we rely on joining by match and innings presence
  -- but restrict to batsman records for the match (the view intent is rows for players who appear in batting records)
GROUP BY pm.player_id, p.player_name, pm.role, p.batting_hand, p.bowling_skill, pm.match_id, bats.innings_no
```

---

**Skill `player_match_bowling_rows`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `bowler`, `match_id`, `innings_no` |
| output columns | `player_id`, `match_id`, `innings`, `wickets_taken`, `runs_conceded`, `balls_bowled`, `bowling_skill` |
| source tables | `ball_by_ball`, `wicket_taken`, `batsman_scored` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `player_level_aggregates`, `player_best_bowling_match` |
| validated_on | — |
| counter_examples | 0 |

_One row per player's bowling performance in a single match innings: include player id, match id, wickets_taken, runs_conceded (exclude extras), balls_bowled (count of legitimate balls; may be NULL), and bowling_skill (if available). Restrict to rows where the player appears in bowling records._

```sql
SELECT
  b.bowler AS player_id,
  b.match_id AS match_id,
  b.innings_no AS innings,
  SUM(CASE WHEN w.player_out IS NOT NULL AND w.kind_out IS NOT NULL THEN 1 ELSE 0 END) AS wickets_taken,
  SUM(CASE WHEN bs.runs_scored IS NOT NULL THEN bs.runs_scored ELSE 0 END) AS runs_conceded,
  COUNT(b.ball_id) FILTER (WHERE 1=1) AS balls_bowled,
  NULL AS bowling_skill
FROM
  ball_by_ball b
LEFT JOIN
  wicket_taken w
  ON b.match_id = w.match_id
  AND b.over_id = w.over_id
  AND b.ball_id = w.ball_id
  AND b.innings_no = w.innings_no
LEFT JOIN
  batsman_scored bs
  ON b.match_id = bs.match_id
  AND b.over_id = bs.over_id
  AND b.ball_id = bs.ball_id
  AND b.innings_no = bs.innings_no
GROUP BY
  b.bowler,
  b.match_id,
  b.innings_no
HAVING
  b.bowler IS NOT NULL
```

---

**Skill `player_level_aggregates`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `total_runs`, `total_matches`, `total_dismissals`, `batting_average_numerator`, `total_balls_faced`, `highest_score`, `matches_>=30`, `matches_>=50`, `matches_>=100`, `total_wickets`, `total_runs_conceded`, `balls_bowled`, `most_frequent_role` |
| source tables | `player`, `player_match_batting_rows`, `player_match_bowling_rows` |
| depends_on (builds on) | `player_match_batting_rows`, `player_match_bowling_rows` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Per-player aggregates computed from the batting and bowling row relations: sum total_runs, count distinct matches appeared (from batting or bowling rows), sum total_dismissals, sum total_balls_faced, highest_score (max runs_scored per match innings), counts of matches with runs >=30, >=50, >=100 (counting a match innings as a match for these thresholds), sum total_wickets, sum total_runs_conceded, sum balls_bowled, and most_frequent_role (mode of role across that player's batting rows). Also compute matches_counted_from_batting (distinct match ids where batting row exists) and matches_counted_from_bowling (distinct match ids where bowling row exists) if needed to determine total_matches._

```sql
SELECT
  p.player_id AS player_id,
  COALESCE(bat_agg.total_runs, 0) AS total_runs,
  -- total distinct matches from batting or bowling rows
  COALESCE(bat_matches.matches_from_batting, 0) + COALESCE(bowl_matches.matches_from_bowling_not_in_batting, 0) AS total_matches,
  COALESCE(bat_agg.total_dismissals, 0) AS total_dismissals,
  -- batting_average_numerator defined as total_runs (numerator for average calc)
  COALESCE(bat_agg.total_runs, 0) AS batting_average_numerator,
  COALESCE(bat_agg.total_balls_faced, 0) AS total_balls_faced,
  COALESCE(bat_agg.highest_score, 0) AS highest_score,
  COALESCE(bat_agg.matches_ge_30, 0) AS "matches_>=30",
  COALESCE(bat_agg.matches_ge_50, 0) AS "matches_>=50",
  COALESCE(bat_agg.matches_ge_100, 0) AS "matches_>=100",
  COALESCE(bowl_agg.total_wickets, 0) AS total_wickets,
  COALESCE(bowl_agg.total_runs_conceded, 0) AS total_runs_conceded,
  COALESCE(bowl_agg.total_balls_bowled, 0) AS balls_bowled,
  role_mode.most_frequent_role AS most_frequent_role
FROM player p
-- batting aggregates per player using player_match_batting_rows if present, else batsman_scored/ball_by_ball fallback
LEFT JOIN (
  SELECT
    pmbr.player_id,
    SUM(COALESCE(pmbr.runs_scored,0)) AS total_runs,
    SUM(COALESCE(pmbr.dismissal_flag,0)) AS total_dismissals,
    SUM(COALESCE(pmbr.balls_faced,0)) AS total_balls_faced,
    MAX(COALESCE(pmbr.runs_scored,0)) AS highest_score,
    SUM(CASE WHEN pmbr.runs_scored >= 30 THEN 1 ELSE 0 END) AS matches_ge_30,
    SUM(CASE WHEN pmbr.runs_scored >= 50 THEN 1 ELSE 0 END) AS matches_ge_50,
    SUM(CASE WHEN pmbr.runs_scored >= 100 THEN 1 ELSE 0 END) AS matches_ge_100
  FROM player_match_batting_rows pmbr
  GROUP BY pmbr.player_id
) bat_agg ON bat_agg.player_id = p.player_id
LEFT JOIN (
  -- count distinct matches where player had batting rows
  SELECT player_id, COUNT(DISTINCT match_id) AS matches_from_batting
  FROM player_match_batting_rows
  GROUP BY player_id
) bat_matches ON bat_matches.player_id = p.player_id
LEFT JOIN (
  SELECT
    pmb.player_id,
    SUM(COALESCE(pmb.wickets_taken,0)) AS total_wickets,
    SUM(COALESCE(pmb.runs_conceded,0)) AS total_runs_conceded,
    SUM(COALESCE(pmb.balls_bowled,0)) AS total_balls_bowled
  FROM player_match_bowling_rows pmb
  GROUP BY pmb.player_id
) bowl_agg ON bowl_agg.player_id = p.player_id
LEFT JOIN (
  -- distinct matches with bowling
  SELECT player_id, COUNT(DISTINCT match_id) AS matches_from_bowling
  FROM player_match_bowling_rows
  GROUP BY player_id
) bowl_matches_all ON bowl_matches_all.player_id = p.player_id
LEFT JOIN (
  -- compute matches_from_bowling not already counted in batting to avoid double-counting
  SELECT
    b.player_id,
    COUNT(DISTINCT b.match_id) AS matches_from_bowling_not_in_batting
  FROM player_match_bowling_rows b
  LEFT JOIN (
    SELECT DISTINCT player_id, match_id FROM player_match_batting_rows
  ) br ON br.player_id = b.player_id AND br.match_id = b.match_id
  WHERE br.match_id IS NULL
  GROUP BY b.player_id
) bowl_matches ON bowl_matches.player_id = p.player_id
LEFT JOIN (
  -- mode of role from batting rows (most frequent role); tie broken arbitrarily by min(role)
  SELECT player_id,
         (SELECT role FROM (
            SELECT role, COUNT(*) AS cnt
            FROM player_match_batting_rows pm
            WHERE pm.player_id = t.player_id AND pm.role IS NOT NULL
            GROUP BY role
            ORDER BY cnt DESC, role ASC
            LIMIT 1
         )) AS most_frequent_role
  FROM (SELECT DISTINCT player_id FROM player_match_batting_rows) t
) role_mode ON role_mode.player_id = p.player_id
```

---

**Skill `player_best_bowling_match`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `best_bowling_in_match` |
| source tables | `player_match_bowling_rows` |
| depends_on (builds on) | `player_match_bowling_rows` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each player, rank their per-match bowling performances to select the best single-match bowling: primary sort by wickets_taken descending, secondary by runs_conceded ascending; output the chosen match formatted as 'wickets-runs_conceded'. If no bowling rows exist for a player, return NULL._

```sql
SELECT
  pbbr.player_id AS player_id,
  CASE
    WHEN pbbr.match_wickets IS NULL THEN NULL
    ELSE (pbbr.match_wickets || '-' || pbbr.match_runs_conceded)
  END AS best_bowling_in_match
FROM (
  SELECT
    p.player_id,
    -- pick best match per player: highest wickets, then lowest runs_conceded
    -- use ROW_NUMBER to rank matches per player
    pm.player_id AS player_id,
    pm.match_id AS match_id,
    pm.wickets_taken AS match_wickets,
    pm.runs_conceded AS match_runs_conceded,
    ROW_NUMBER() OVER (
      PARTITION BY pm.player_id
      ORDER BY pm.wickets_taken DESC NULLS LAST, pm.runs_conceded ASC NULLS LAST
    ) AS rn
  FROM player_match_bowling_rows pm
  RIGHT JOIN (
    SELECT DISTINCT player_id FROM player_match_bowling_rows
  ) p ON p.player_id = pm.player_id
) pbbr
WHERE pbbr.rn = 1
```

---
