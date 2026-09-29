# Skill graph — `Baseball` (8 skills)

**Skill `players_with_valid_dates`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `debut_date`, `final_game_date` |
| source tables | `player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `player_date_diff_components`, `player_rounded_time_components` |
| validated_on | — |
| counter_examples | 0 |

_Select one row per player that has non-null, valid debut and final game dates (exclude players with missing or invalid dates). Keep the raw date values for later processing._

```sql
SELECT
  player.player_id AS player_id,
  player.debut AS debut_date,
  player.final_game AS final_game_date
FROM player
WHERE player.debut IS NOT NULL
  AND player.debut != ''
  AND player.final_game IS NOT NULL
  AND player.final_game != ''
```

---

**Skill `player_date_diff_components`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `years_diff_whole`, `months_diff_whole`, `days_diff_whole` |
| source tables | `players_with_valid_dates` |
| depends_on (builds on) | `players_with_valid_dates` |
| depended-on by (builds on this) | `player_rounded_time_components` |
| validated_on | — |
| counter_examples | 0 |

_For each player, compute the absolute difference between final_game_date and debut_date expressed as whole years, whole months, and whole days (three integer components). Also cast/normalize these components to numeric types suitable for rounding._

```sql
SELECT
  p.player_id,
  CAST(ABS(
    (strftime('%Y', p.final_game_date) - strftime('%Y', p.debut_date))
    - (strftime('%m-%d', p.final_game_date) < strftime('%m-%d', p.debut_date))
  ) AS NUMERIC) AS years_diff_whole,
  CAST(ABS(
    ((strftime('%Y', p.final_game_date) - strftime('%Y', p.debut_date)) * 12)
    + (strftime('%m', p.final_game_date) - strftime('%m', p.debut_date))
    - (
        (strftime('%m-%d', p.final_game_date) < strftime('%m-%d', p.debut_date))
        * 12
      )
  ) % 12 AS NUMERIC) AS months_diff_whole,
  CAST(ABS(
    julianday(p.final_game_date) - julianday(p.debut_date)
    - (
      (strftime('%Y', p.final_game_date) - strftime('%Y', p.debut_date))
      - (strftime('%m-%d', p.final_game_date) < strftime('%m-%d', p.debut_date))
    ) * 365
    - (
      ((strftime('%Y', p.final_game_date) - strftime('%Y', p.debut_date))
       - (strftime('%m-%d', p.final_game_date) < strftime('%m-%d', p.debut_date))
      ) / 4
    )
  ) AS NUMERIC) AS days_diff_whole
FROM players_with_valid_dates p
```

---

**Skill `player_rounded_time_components`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `rounded_years`, `rounded_months`, `rounded_days` |
| source tables | `player_date_diff_components`, `players_with_valid_dates` |
| depends_on (builds on) | `player_date_diff_components`, `players_with_valid_dates` |
| depended-on by (builds on this) | `player_career_span_years` |
| validated_on | — |
| counter_examples | 0 |

_For each player, round the years_diff_whole, months_diff_whole, and days_diff_whole to two decimal places (separately) producing rounded_years, rounded_months, rounded_days._

```sql
SELECT
  p.player_id,
  ROUND(d.years_diff_whole, 2) AS rounded_years,
  ROUND(d.months_diff_whole, 2) AS rounded_months,
  ROUND(d.days_diff_whole, 2) AS rounded_days
FROM player_date_diff_components d
JOIN players_with_valid_dates p ON p.player_id = d.player_id
```

---

**Skill `player_career_span_years`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `career_span_years` |
| source tables | `player_rounded_time_components` |
| depends_on (builds on) | `player_rounded_time_components` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each player, convert rounded_months to years (rounded_months / 12) and rounded_days to years (rounded_days / 365), sum rounded_years + (rounded_months/12) + (rounded_days/365) to produce the per-player career span in years. This relation is one row per player with the computed span._

```sql
SELECT
  player_id,
  (COALESCE(rounded_years,0)
   + COALESCE(rounded_months,0) / 12.0
   + COALESCE(rounded_days,0) / 365.0) AS career_span_years
FROM player_rounded_time_components
```

---

**Skill `player_stat_rows`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `given_name`, `games_played`, `runs`, `hits`, `home_runs` |
| source tables | `player`, `batting` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `games_played_values`, `runs_hits_hr_values`, `category_max_holders` |
| validated_on | — |
| counter_examples | 0 |

_Select the raw per-player statistic rows from the player-season (or player) statistics source, projecting the player identifier, given name, and the four numeric statistic columns (games played, runs, hits, home runs) without applying any filters._

```sql
SELECT
  player.player_id AS player_id,
  player.name_given AS given_name,
  batting.g AS games_played,
  batting.r AS runs,
  batting.h AS hits,
  batting.hr AS home_runs
FROM player
LEFT JOIN batting USING (player_id)
```

---

**Skill `games_played_values`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `given_name`, `games_played` |
| source tables | `player`, `player_stat_rows` |
| depends_on (builds on) | `player_stat_rows` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each player row, keep the games_played value as a per-player measure (this relation is one row per player carrying the games_played number). It prepares the per-player measure for computing the global maximum._

```sql
SELECT
  p.player_id,
  p.name_given AS given_name,
  ps.games_played
FROM player p
LEFT JOIN player_stat_rows ps
  ON ps.player_id = p.player_id
```

---

**Skill `runs_hits_hr_values`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `given_name`, `runs`, `hits`, `home_runs` |
| source tables | `player_stat_rows` |
| depends_on (builds on) | `player_stat_rows` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each player row, keep the runs, hits, and home_runs values as per-player measures (one row per player carrying these three numbers) to prepare for computing global maxima for each category._

```sql
SELECT
  psr.player_id AS player_id,
  psr.given_name AS given_name,
  COALESCE(psr.runs, 0) AS runs,
  COALESCE(psr.hits, 0) AS hits,
  COALESCE(psr.home_runs, 0) AS home_runs
FROM player_stat_rows psr
```

---

**Skill `category_max_holders`** — category `RESHAPE`

| field | value |
|---|---|
| grain (one row per) | `category`, `player_id` |
| output columns | `category`, `player_id`, `given_name`, `value` |
| source tables | `player_stat_rows` |
| depends_on (builds on) | `player_stat_rows` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Unpivot the per-player measures into rows of (category, player_id, given_name, value), then for each category identify rows where value equals the global maximum value for that category across all players. This yields one row per (category, player) for players tied at the maximum, containing category, given_name, and the maximum value._

```sql
SELECT
  category,
  player_id,
  given_name AS given_name,
  value
FROM (
  SELECT player_id, given_name, 'games_played' AS category, games_played AS value FROM player_stat_rows
  UNION ALL
  SELECT player_id, given_name, 'runs' AS category, runs AS value FROM player_stat_rows
  UNION ALL
  SELECT player_id, given_name, 'hits' AS category, hits AS value FROM player_stat_rows
  UNION ALL
  SELECT player_id, given_name, 'home_runs' AS category, home_runs AS value FROM player_stat_rows
) unpivoted
JOIN (
  SELECT category AS category, MAX(value) AS max_value
  FROM (
    SELECT 'games_played' AS category, games_played AS value FROM player_stat_rows
    UNION ALL
    SELECT 'runs' AS category, runs AS value FROM player_stat_rows
    UNION ALL
    SELECT 'hits' AS category, hits AS value FROM player_stat_rows
    UNION ALL
    SELECT 'home_runs' AS category, home_runs AS value FROM player_stat_rows
  )
  GROUP BY category
) maxima USING (category)
WHERE (unpivoted.value IS NOT NULL) AND (unpivoted.value = maxima.max_value)
```

---
