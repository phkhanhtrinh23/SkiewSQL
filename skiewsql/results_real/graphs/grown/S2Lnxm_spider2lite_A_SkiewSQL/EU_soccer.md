# Skill graph — `EU_soccer` (19 skills)

**Skill `team_season_goals`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `team_id`, `season_id` |
| output columns | `team_id`, `season_id`, `season_goals` |
| source tables | `Match`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `team_max_season_goals` |
| validated_on | — |
| counter_examples | 0 |

_All observed season-level goals values for each team (one row per team-season) — include only rows where a numeric goals value exists._

```sql
SELECT
  Team.team_api_id AS team_id,
  Match.season AS season_id,
  CAST(
    COALESCE(
      Match.home_team_goal,
      Match.away_team_goal
    ) AS INTEGER
  ) AS season_goals
FROM Match
JOIN Team
  ON Team.team_api_id = Match.home_team_api_id
UNION ALL
SELECT
  Team.team_api_id AS team_id,
  Match.season AS season_id,
  CAST(
    COALESCE(
      Match.home_team_goal,
      Match.away_team_goal
    ) AS INTEGER
  ) AS season_goals
FROM Match
JOIN Team
  ON Team.team_api_id = Match.away_team_api_id
WHERE
  TRUE
```

---

**Skill `team_max_season_goals`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `team_id` |
| output columns | `team_id`, `max_season_goals` |
| source tables | `team_season_goals` |
| depends_on (builds on) | `team_season_goals` |
| depended-on by (builds on this) | `teams_ranked_by_max_goals` |
| validated_on | — |
| counter_examples | 0 |

_For each team, compute that team's highest season_goals value across all seasons (one row per team). Exclude teams with no season_goals rows._

```sql
SELECT
  team_id,
  MAX(season_goals) AS max_season_goals
FROM team_season_goals
GROUP BY team_id
```

---

**Skill `teams_ranked_by_max_goals`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `team_id` |
| output columns | `team_id`, `max_season_goals`, `row_number`, `total_teams` |
| source tables | `team_max_season_goals` |
| depends_on (builds on) | `team_max_season_goals` |
| depended-on by (builds on this) | `median_highest_season_goals_calc` |
| validated_on | — |
| counter_examples | 0 |

_Assign an ordering (rank) to teams by their max_season_goals so that the median position(s) can be identified. Also include a row_number and total_team_count for use in median selection._

```sql
SELECT
  team_id,
  max_season_goals AS max_season_goals,
  ROW_NUMBER() OVER (ORDER BY max_season_goals DESC, team_id ASC) AS row_number,
  COUNT(*) OVER () AS total_teams
FROM team_max_season_goals
```

---

**Skill `median_highest_season_goals_calc`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | `median_highest_season_goals` |
| source tables | — |
| depends_on (builds on) | `teams_ranked_by_max_goals` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select the median value of max_season_goals across teams: if odd number of teams take the middle max_season_goals. If even average the two middle max_season_goals. Produces one row with the median scalar._

```sql
SELECT
  CASE
    WHEN total_teams % 2 = 1 THEN
      (SELECT CAST(max_season_goals AS REAL) FROM teams_ranked_by_max_goals WHERE row_number = (total_teams+1)/2)
    ELSE
      (
        (SELECT CAST(max_season_goals AS REAL) FROM teams_ranked_by_max_goals WHERE row_number = total_teams/2)
        +
        (SELECT CAST(max_season_goals AS REAL) FROM teams_ranked_by_max_goals WHERE row_number = total_teams/2 + 1)
      ) / 2.0
  END AS median_highest_season_goals
FROM (
  SELECT
    MAX(row_number) AS total_teams
  FROM teams_ranked_by_max_goals
)
```

---

**Skill `match_results_rowlevel`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `match_id` |
| output columns | `match_id`, `league_id`, `home_team_id`, `away_team_id`, `home_goals`, `away_goals` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `team_match_win_flags`, `team_total_wins` |
| validated_on | — |
| counter_examples | 0 |

_One row per match indicating match id, home team, away team, home goals, away goals, and league (and season if available). This is the raw set of matches to evaluate win/loss outcomes across all seasons._

```sql
SELECT
  id AS match_id,
  league_id AS league_id,
  home_team_api_id AS home_team_id,
  away_team_api_id AS away_team_id,
  home_team_goal AS home_goals,
  away_team_goal AS away_goals
FROM Match
```

---

**Skill `team_match_win_flags`** — category `RESHAPE`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `team_id` |
| output columns | `match_id`, `league_id`, `team_id`, `is_win` |
| source tables | `match_results_rowlevel` |
| depends_on (builds on) | `match_results_rowlevel` |
| depended-on by (builds on this) | `team_total_wins` |
| validated_on | — |
| counter_examples | 0 |

_Turn each match into two team-level rows (one for the home team, one for the away team) with a win_flag indicating whether that team won the match determined by comparing goals (home_goals > away_goals for home team win, away_goals > home_goals for away team win). Include league association for each team row._

```sql
SELECT
  m.match_id AS match_id,
  m.league_id AS league_id,
  m.home_team_id AS team_id,
  CASE WHEN m.home_goals > m.away_goals THEN 1 ELSE 0 END AS is_win
FROM match_results_rowlevel m
UNION ALL
SELECT
  m.match_id AS match_id,
  m.league_id AS league_id,
  m.away_team_id AS team_id,
  CASE WHEN m.away_goals > m.home_goals THEN 1 ELSE 0 END AS is_win
FROM match_results_rowlevel m
```

---

**Skill `team_total_wins`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `team_api_id`, `league_id` |
| output columns | `league_id`, `team_id`, `total_wins` |
| source tables | `Team`, `match_results_rowlevel`, `team_match_win_flags` |
| depends_on (builds on) | `match_results_rowlevel`, `team_match_win_flags` |
| depended-on by (builds on this) | `league_min_win_team`, `wins_per_team` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate the team-level win flags across all matches to compute total wins per team (sum of is_win). Keep teams with zero wins by grouping all teams that appear in the league/team roster or in matches._

```sql
SELECT
  t_league.league_id AS league_id,
  t.team_api_id AS team_id,
  COALESCE(SUM(tmwf.is_win), 0) AS total_wins
FROM
  Team t
LEFT JOIN (
  -- derive league membership per team via matches where they appear as home or away
  SELECT league_id, home_team_id AS team_id, match_id
  FROM match_results_rowlevel
  UNION
  SELECT league_id, away_team_id AS team_id, match_id
  FROM match_results_rowlevel
) t_league ON t.team_api_id = t_league.team_id
LEFT JOIN team_match_win_flags tmwf
  ON tmwf.team_id = t.team_api_id
GROUP BY
  t.team_api_id,
  t_league.league_id
```

---

**Skill `league_min_win_team`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `league_id` |
| output columns | `league_id`, `team_id`, `total_wins` |
| source tables | `team_total_wins` |
| depends_on (builds on) | `team_total_wins` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Per league, rank teams by total_wins ascending and pick the single top-ranked team per league (ties may be broken arbitrarily) to produce one team with the fewest total wins for each league._

```sql
SELECT
  ttw.league_id AS league_id,
  ttw.team_id AS team_id,
  ttw.total_wins AS total_wins
FROM team_total_wins ttw
JOIN (
  SELECT league_id, MIN(total_wins) AS min_wins
  FROM team_total_wins
  GROUP BY league_id
) mv ON ttw.league_id = mv.league_id AND ttw.total_wins = mv.min_wins
```

---

**Skill `team_list`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `team_id` |
| output columns | `team_id`, `team_name` |
| source tables | `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `wins_per_team`, `teams_with_wins` |
| validated_on | — |
| counter_examples | 0 |

_All teams in the league (one row per team). This is the canonical set of teams to consider. Do not filter by season/division here._

```sql
SELECT
  Team.id AS team_id,
  Team.team_long_name AS team_name
FROM Team
```

---

**Skill `match_results`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `match_id` |
| output columns | `match_id`, `winner_team_id` |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All completed match results indicating which team won each match (one row per match-team outcome). Each row should identify the match and the winning team. If source data records winners as a flag or scores, normalize into a winner indicator in a later step._

```sql
SELECT
  m.id AS match_id,
  CASE
    WHEN m.home_team_goal IS NOT NULL
     AND m.away_team_goal IS NOT NULL
     AND m.home_team_goal > m.away_team_goal THEN m.home_team_api_id
    WHEN m.home_team_goal IS NOT NULL
     AND m.away_team_goal IS NOT NULL
     AND m.away_team_goal > m.home_team_goal THEN m.away_team_api_id
    ELSE NULL
  END AS winner_team_id
FROM Match AS m
```

---

**Skill `wins_per_team`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `team_id` |
| output columns | `team_id`, `wins` |
| source tables | `Team`, `team_list`, `team_total_wins` |
| depends_on (builds on) | `team_list`, `team_total_wins` |
| depended-on by (builds on this) | `teams_with_wins` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate count of wins for each team by counting match results where the team is the winner. Produces one row per team with their total wins (zero wins should be represented as zero when joined with full team list)._

```sql
SELECT
  t.team_id AS team_id,
  COALESCE(w.total_wins, 0) AS wins
FROM
  Team AS base_team
  -- join to team_list if available for canonical team ids/names; otherwise derive from Team table
  LEFT JOIN (
    SELECT team_id, team_name FROM team_list
  ) t ON t.team_id = base_team.team_api_id
  LEFT JOIN (
    SELECT team_id, total_wins FROM team_total_wins
  ) w ON w.team_id = base_team.team_api_id
```

---

**Skill `teams_with_wins`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `team_id` |
| output columns | `team_id`, `team_name`, `wins` |
| source tables | `team_list`, `wins_per_team` |
| depends_on (builds on) | `team_list`, `wins_per_team` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Left-join the full team list with the wins aggregation to produce one row per team including team identifier/name and their wins (use zero for teams with no matching wins). This relation is the basis for final ranking and top-k selection._

```sql
SELECT
  t.team_id AS team_id,
  t.team_name AS team_name,
  COALESCE(w.wins, 0) AS wins
FROM
  team_list t
LEFT JOIN
  wins_per_team w
ON
  t.team_id = w.team_id
```

---

**Skill `player_match_outcomes`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `player_id`, `match_id`, `team_id` |
| output columns | `player_id`, `match_id`, `team_id`, `is_win`, `is_loss` |
| source tables | `Player`, `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `player_win_loss_counts` |
| validated_on | — |
| counter_examples | 0 |

_Canonicalize/normalize each participation row to attach a boolean or indicator for whether the player's team won or lost that match (two separate flags: is_win, is_loss) without changing row grain._

```sql
SELECT
  p.player_api_id AS player_id,
  m.id AS match_id,
  -- determine which team the player belonged to in this match by checking home/away player columns
  CASE
    WHEN p.player_api_id IN (
      m.home_player_1, m.home_player_2, m.home_player_3, m.home_player_4, m.home_player_5,
      m.home_player_6, m.home_player_7, m.home_player_8, m.home_player_9, m.home_player_10, m.home_player_11
    ) THEN m.home_team_api_id
    WHEN p.player_api_id IN (
      m.away_player_1, m.away_player_2, m.away_player_3, m.away_player_4, m.away_player_5,
      m.away_player_6, m.away_player_7, m.away_player_8, m.away_player_9, m.away_player_10, m.away_player_11
    ) THEN m.away_team_api_id
    ELSE NULL
  END AS team_id,
  -- is_win: true if player's team scored more goals than opponent in that match
  CASE
    WHEN
      -- player is on home team and home_team_goal > away_team_goal
      p.player_api_id IN (
        m.home_player_1, m.home_player_2, m.home_player_3, m.home_player_4, m.home_player_5,
        m.home_player_6, m.home_player_7, m.home_player_8, m.home_player_9, m.home_player_10, m.home_player_11
      ) AND m.home_team_goal IS NOT NULL AND m.away_team_goal IS NOT NULL AND m.home_team_goal > m.away_team_goal
    THEN 1
    WHEN
      -- player is on away team and away_team_goal > home_team_goal
      p.player_api_id IN (
        m.away_player_1, m.away_player_2, m.away_player_3, m.away_player_4, m.away_player_5,
        m.away_player_6, m.away_player_7, m.away_player_8, m.away_player_9, m.away_player_10, m.away_player_11
      ) AND m.home_team_goal IS NOT NULL AND m.away_team_goal IS NOT NULL AND m.away_team_goal > m.home_team_goal
    THEN 1
    ELSE 0
  END AS is_win,
  -- is_loss: true if player's team scored fewer goals than opponent in that match
  CASE
    WHEN
      p.player_api_id IN (
        m.home_player_1, m.home_player_2, m.home_player_3, m.home_player_4, m.home_player_5,
        m.home_player_6, m.home_player_7, m.home_player_8, m.home_player_9, m.home_player_10, m.home_player_11
      ) AND m.home_team_goal IS NOT NULL AND m.away_team_goal IS NOT NULL AND m.home_team_goal < m.away_team_goal
    THEN 1
    WHEN
      p.player_api_id IN (
        m.away_player_1, m.away_player_2, m.away_player_3, m.away_player_4, m.away_player_5,
        m.away_player_6, m.away_player_7, m.away_player_8, m.away_player_9, m.away_player_10, m.away_player_11
      ) AND m.home_team_goal IS NOT NULL AND m.away_team_goal IS NOT NULL AND m.away_team_goal < m.home_team_goal
    THEN 1
    ELSE 0
  END AS is_loss
FROM
  Player p
JOIN
  Match m
  ON (
    p.player_api_id IN (
      m.home_player_1, m.home_player_2, m.home_player_3, m.home_player_4, m.home_player_5,
      m.home_player_6, m.home_player_7, m.home_player_8, m.home_player_9, m.home_player_10, m.home_player_11,
      m.away_player_1, m.away_player_2, m.away_player_3, m.away_player_4, m.away_player_5,
      m.away_player_6, m.away_player_7, m.away_player_8, m.away_player_9, m.away_player_10, m.away_player_11
    )
  )
WHERE
  -- exclude participations where we could not determine a team (shouldn't happen due to join condition),
  -- and ensure goals are present to classify win/loss (draws yield both flags = 0)
  (m.home_team_goal IS NOT NULL AND m.away_team_goal IS NOT NULL)
```

---

**Skill `player_win_loss_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `win_participation_count`, `loss_participation_count` |
| source tables | `player_match_outcomes` |
| depends_on (builds on) | `player_match_outcomes` |
| depended-on by (builds on this) | `top_players_by_outcome` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate normalized participation rows to count distinct matches each player participated in where their team won and where their team lost. One row per player with two counts._

```sql
SELECT
  pmo.player_id AS player_id,
  SUM(CASE WHEN pmo.is_win = 1 THEN 1 ELSE 0 END) AS win_participation_count,
  SUM(CASE WHEN pmo.is_loss = 1 THEN 1 ELSE 0 END) AS loss_participation_count
FROM player_match_outcomes pmo
GROUP BY pmo.player_id
```

---

**Skill `top_players_by_outcome`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `win_participation_count`, `loss_participation_count`, `win_rank`, `loss_rank` |
| source tables | `player_win_loss_counts` |
| depends_on (builds on) | `player_win_loss_counts` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_From per-player counts, produce ordered rankings separately for wins and losses so the top player(s) by win count and top player(s) by loss count can be selected. Preserve player-level counts and ranking positions._

```sql
SELECT
  p.player_id AS player_id,
  COALESCE(pc.win_participation_count, 0) AS win_participation_count,
  COALESCE(pc.loss_participation_count, 0) AS loss_participation_count,
  -- win_rank: dense rank of players ordered by win_participation_count DESC
  (SELECT 1 + COUNT(DISTINCT p2.win_participation_count)
     FROM player_win_loss_counts p2
     WHERE COALESCE(p2.win_participation_count,0) > COALESCE(pc.win_participation_count,0)
  ) AS win_rank,
  -- loss_rank: dense rank of players ordered by loss_participation_count DESC
  (SELECT 1 + COUNT(DISTINCT p3.loss_participation_count)
     FROM player_win_loss_counts p3
     WHERE COALESCE(p3.loss_participation_count,0) > COALESCE(pc.loss_participation_count,0)
  ) AS loss_rank
FROM
  (SELECT DISTINCT player_id FROM player_win_loss_counts) p
  LEFT JOIN player_win_loss_counts pc ON p.player_id = pc.player_id
```

---

**Skill `match_results_15`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `match_id` |
| output columns | `match_id`, `season`, `league`, `country`, `home_team_id`, `away_team_id`, `home_goals`, `away_goals`, `result_flag` |
| source tables | `Match`, `League`, `Country` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select match-level result records needed to determine per-team outcome, retaining season, league, country, home team, away team, and the match result indicator (win/tie/loss for each side or goals scored to derive result). Exclude matches with missing result data._

```sql
SELECT
  M.id AS match_id,
  M.season AS season,
  L.name AS league,
  C.name AS country,
  M.home_team_api_id AS home_team_id,
  M.away_team_api_id AS away_team_id,
  M.home_team_goal AS home_goals,
  M.away_team_goal AS away_goals,
  CASE
    WHEN M.home_team_goal IS NULL OR M.away_team_goal IS NULL THEN NULL
    WHEN M.home_team_goal > M.away_team_goal THEN 'home_win'
    WHEN M.home_team_goal < M.away_team_goal THEN 'away_win'
    ELSE 'draw'
  END AS result_flag
FROM "Match" M
JOIN "League" L ON M.league_id = L.id
JOIN "Country" C ON M.country_id = C.id
WHERE M.home_team_goal IS NOT NULL
  AND M.away_team_goal IS NOT NULL
```

---

**Skill `team_match_outcomes`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `team_id` |
| output columns | `match_id`, `season`, `league`, `country`, `team_id`, `is_home`, `outcome` |
| source tables | `Match`, `League`, `Country` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Transform match_results into one row per team per match indicating whether that team was home or away and the outcome for that team (win/tie/loss) within the same season, league, country. This duplicates each match into two rows (one per participating team) and computes a canonical outcome flag for the team in that match._

```sql
SELECT
  m.id AS match_id,
  m.season AS season,
  L.name AS league,
  C.name AS country,
  t.team_id AS team_id,
  CASE WHEN t.team_id = m.home_team_api_id THEN 1 ELSE 0 END AS is_home,
  CASE
    WHEN t.team_id = m.home_team_api_id AND COALESCE(m.home_team_goal,0) > COALESCE(m.away_team_goal,0) THEN 'win'
    WHEN t.team_id = m.away_team_api_id AND COALESCE(m.away_team_goal,0) > COALESCE(m.home_team_goal,0) THEN 'win'
    WHEN COALESCE(m.home_team_goal,0) = COALESCE(m.away_team_goal,0) THEN 'tie'
    ELSE 'loss'
  END AS outcome
FROM Match m
JOIN League L ON m.league_id = L.id
JOIN Country C ON m.country_id = C.id
-- expand each match into two rows: home team and away team
JOIN (
  SELECT home_team_api_id AS team_id, id AS match_id FROM Match
  UNION ALL
  SELECT away_team_api_id AS team_id, id AS match_id FROM Match
) t ON t.match_id = m.id
```

---

**Skill `team_season_record`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `season`, `name`, `name`, `team_api_id` |
| output columns | `season`, `league`, `country`, `team_id`, `wins`, `ties`, `losses` |
| source tables | `Match`, `League`, `Country`, `Team` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `season_league_champions` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate team_match_outcomes to compute counts of wins, ties, and losses per team within each season + league + country grouping. Keep one row per team per season/league/country with the aggregated counts._

```sql
SELECT
  m.season AS season,
  l.name AS league,
  c.name AS country,
  t.team_api_id AS team_id,
  SUM(
    CASE
      WHEN (m.home_team_api_id = t.team_api_id AND m.home_team_goal > m.away_team_goal)
        OR (m.away_team_api_id = t.team_api_id AND m.away_team_goal > m.home_team_goal)
      THEN 1 ELSE 0 END
  ) AS wins,
  SUM(
    CASE
      WHEN m.home_team_goal = m.away_team_goal
        AND (m.home_team_api_id = t.team_api_id OR m.away_team_api_id = t.team_api_id)
      THEN 1 ELSE 0 END
  ) AS ties,
  SUM(
    CASE
      WHEN (m.home_team_api_id = t.team_api_id AND m.home_team_goal < m.away_team_goal)
        OR (m.away_team_api_id = t.team_api_id AND m.away_team_goal < m.home_team_goal)
      THEN 1 ELSE 0 END
  ) AS losses
FROM "Match" m
JOIN "League" l ON m.league_id = l.id
JOIN "Country" c ON m.country_id = c.id
JOIN "Team" t ON (t.team_api_id = m.home_team_api_id OR t.team_api_id = m.away_team_api_id)
GROUP BY m.season, l.name, c.name, t.team_api_id
```

---

**Skill `season_league_champions`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `season`, `league`, `country`, `team_id` |
| output columns | `season`, `league`, `country`, `team_id`, `points` |
| source tables | `Match`, `Team`, `League`, `Country` |
| depends_on (builds on) | `team_season_record` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Compute points for each team as 3*wins + 1*ties + 0*losses and, per season + league + country, identify the team(s) whose points equal the maximum points in that group. Produce one row per champion team per season/league/country._

```sql
SELECT
  tsr.season AS season,
  tsr.league AS league,
  tsr.country AS country,
  tsr.team_id AS team_id,
  (COALESCE(tsr.wins,0) * 3 + COALESCE(tsr.ties,0) * 1 + COALESCE(tsr.losses,0) * 0) AS points
FROM team_season_record AS tsr
JOIN (
  SELECT season, league, country, MAX(COALESCE(wins,0)*3 + COALESCE(ties,0)*1 + COALESCE(losses,0)*0) AS max_points
  FROM team_season_record
  GROUP BY season, league, country
) AS grp
  ON tsr.season = grp.season
  AND tsr.league = grp.league
  AND tsr.country = grp.country
  AND (COALESCE(tsr.wins,0)*3 + COALESCE(tsr.ties,0)*1 + COALESCE(tsr.losses,0)*0) = grp.max_points
```

---
