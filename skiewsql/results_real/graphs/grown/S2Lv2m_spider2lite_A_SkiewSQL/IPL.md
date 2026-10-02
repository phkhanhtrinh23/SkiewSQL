# Skill graph — `IPL` (6 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `ball_by_ball`, `player`, `team`, `batsman_scored`, `extra_runs`, `wicket_taken`, `player_match`, `match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: Find the top 3 bowlers who, considering only overs that were the maximum-run over(s) within their respective match, conceded the largest single-over run totals across all matches. For each bowle_

```sql
SELECT
  bb.match_id,
  bb.over_id,
  bb.ball_id,
  bb.innings_no,
  bb.bowler,
  b.player_name AS bowler_name,
  tb.name AS bowling_team,
  bs.runs_scored,
  ex.extra_type,
  ex.extra_runs,
  wt.player_out,
  wt.kind_out,
  pm.team_id AS bowler_team_in_match,
  m.team_1,
  m.team_2,
  m.match_date
FROM ball_by_ball bb
LEFT JOIN player b
  ON bb.bowler = b.player_id
LEFT JOIN team tb
  ON bb.team_bowling = tb.team_id
LEFT JOIN batsman_scored bs
  ON bb.match_id = bs.match_id
  AND bb.over_id = bs.over_id
  AND bb.ball_id = bs.ball_id
  AND bb.innings_no = bs.innings_no
LEFT JOIN extra_runs ex
  ON bb.match_id = ex.match_id
  AND bb.over_id = ex.over_id
  AND bb.ball_id = ex.ball_id
  AND bb.innings_no = ex.innings_no
LEFT JOIN wicket_taken wt
  ON bb.match_id = wt.match_id
  AND bb.over_id = wt.over_id
  AND bb.ball_id = wt.ball_id
  AND bb.innings_no = wt.innings_no
LEFT JOIN player_match pm
  ON bb.match_id = pm.match_id
  AND bb.bowler = pm.player_id
LEFT JOIN match m
  ON bb.match_id = m.match_id
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `ball_by_ball`, `wicket_taken`, `batsman_scored`, `extra_runs`, `match`, `player`, `player_match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: Find the bowler who has the lowest bowling average per wicket taken. Required outputs: bowler (the name or identifier of the bowler). Bowling average per wicket taken (numeric value used to comp_

```sql
SELECT
  b.bowler,
  b.match_id,
  b.over_id,
  b.ball_id,
  bt.player_name AS bowler_name,
  wt.player_out,
  wt.kind_out,
  wt.innings_no AS wicket_innings_no,
  bs.runs_scored,
  eb.extra_runs,
  eb.extra_type,
  m.match_date,
  m.match_winner,
  pm.team_id AS bowler_team_id,
  p.player_id,
  p.player_name AS player_name_lookup
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
LEFT JOIN match m
  ON m.match_id = b.match_id
LEFT JOIN player bt
  ON bt.player_id = b.bowler
LEFT JOIN player p
  ON p.player_id = wt.player_out
LEFT JOIN player_match pm
  ON pm.match_id = b.match_id
  AND pm.player_id = b.bowler
```

---

**Skill `chunk_view_0_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `ball_by_ball`, `batsman_scored`, `match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute the average of the total runs scored by all strikers who have at least one match in which they scored more than 50 runs. Required outputs: average_total_runs: a single numeric value repr_

```sql
SELECT
  b.striker AS player_id,
  m.match_id,
  bs.runs_scored,
  -- include ball-level identifiers to allow joining/aggregation later
  b.over_id,
  b.ball_id,
  b.innings_no
FROM ball_by_ball AS b
JOIN batsman_scored AS bs
  ON b.match_id = bs.match_id
  AND b.over_id = bs.over_id
  AND b.ball_id = bs.ball_id
  AND b.innings_no = bs.innings_no
JOIN "match" AS m
  ON b.match_id = m.match_id
```

---

**Skill `chunk_view_0_3`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `batsman_scored`, `player`, `player_match`, `match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Find all players' names who scored at least 100 runs in a single match and in that same match their team lost. Required outputs: player_name Filters: Include only match records where the player'_

```sql
SELECT
  batsman_scored.match_id,
  batsman_scored.innings_no,
  batsman_scored.runs_scored,
  player.player_id,
  player.player_name,
  player_match.team_id,
  match.match_winner,
  match.team_1,
  match.team_2
FROM batsman_scored
JOIN player ON batsman_scored.match_id = player.player_id -- placeholder join to include player columns (actual join to be completed in later chunk)
LEFT JOIN player_match ON batsman_scored.match_id = player_match.match_id -- keep player_match keys to determine player's team in match
LEFT JOIN match ON batsman_scored.match_id = match.match_id
```

---

**Skill `chunk_view_0_4`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `player`, `player_match`, `match`, `batsman_scored` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | For each IPL season, identify the top three batsmen with the highest total runs scored and the top three bowlers with the most wickets taken, excluding ‘run out’, ‘hit wicket’, and ‘retired hurt’ dismissals. In the event of ties in runs or wickets, break the tie using the smaller player ID. Then out |
| counter_examples | 2 |

_Task: Find the top 5 players (by highest average runs per match) in season 5 and return each player's name and their batting average. Required outputs: player name. Average runs per match (used for ra_

```sql
SELECT
  player.player_id,
  player.player_name,
  match.match_id,
  match.season_id,
  batsman_scored.runs_scored,
  batsman_scored.innings_no,
  batsman_scored.over_id,
  batsman_scored.ball_id
FROM player
JOIN player_match ON player.player_id = player_match.player_id
JOIN match ON player_match.match_id = match.match_id
JOIN batsman_scored ON match.match_id = batsman_scored.match_id
  AND player.player_id = batsman_scored.match_id /* keep batsman_scored join keys present in this chunk */
```

---

**Skill `chunk_view_0_5`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `ball_by_ball`, `batsman_scored` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each match, identify the player pair(s) that together produced the single highest partnership runs value in that match, and for each such pair output the two player IDs ordered per the speci_

```sql
SELECT
  b.match_id,
  b.innings_no,
  b.over_id,
  b.ball_id,
  b.striker AS player_id,
  b.non_striker AS partner_id,
  bs.runs_scored AS striker_runs,
  -- include bowler and teams in case useful later
  b.bowler,
  b.team_batting,
  b.team_bowling
FROM ball_by_ball b
LEFT JOIN batsman_scored bs
  ON b.match_id = bs.match_id
  AND b.over_id = bs.over_id
  AND b.ball_id = bs.ball_id
  AND b.innings_no = bs.innings_no
```

---
