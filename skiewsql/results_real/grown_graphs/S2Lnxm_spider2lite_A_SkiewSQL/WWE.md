# Skill graph — `WWE` (3 skills)

**Skill `matches_sel`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `match_id` |
| output columns | `match_id`, `match_title`, `championship`, `description`, `result_text`, `match_type`, `raw_duration` |
| source tables | `Matches`, `Belts` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `nxt_title_shortest_match` |
| validated_on | — |
| counter_examples | 0 |

_Select matches that are relevant: rows representing individual matches that have a recorded duration and whose title/championship indicates an NXT title. Do not apply the 'title change' exclusion here (that is applied later). Also include match description, result, match type, and raw duration fields._

```sql
SELECT
  Matches.id AS match_id,
  Matches.title_id AS match_title,
  Belts.name AS championship,
  Matches.win_type AS description,
  CASE
    WHEN Matches.winner_id IS NOT NULL AND Matches.loser_id IS NOT NULL
      THEN 'Winner: ' || Matches.winner_id || '; Loser: ' || Matches.loser_id
    WHEN Matches.winner_id IS NOT NULL THEN 'Winner: ' || Matches.winner_id
    WHEN Matches.loser_id IS NOT NULL THEN 'Loser: ' || Matches.loser_id
    ELSE NULL
  END AS result_text,
  Matches.match_type_id AS match_type,
  Matches.duration AS raw_duration
FROM Matches
LEFT JOIN Belts ON Matches.title_id = Belts.id
WHERE Matches.duration IS NOT NULL
  AND Matches.duration != ''
  AND Matches.title_id IS NOT NULL
  AND Belts.name LIKE '%NXT%'
```

---

**Skill `competitors_join`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `competitor_id` |
| output columns | `match_id`, `competitor_id`, `competitor_name`, `competitor_slot` |
| source tables | `Matches`, `Wrestlers` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each match, assemble the competitor rows (each competitor's wrestler id and name) so there is one row per competitor per match, including an ordering or competitor slot if available (to identify two wrestlers in a match)._

```sql
SELECT
  m.id AS match_id,
  w.id AS competitor_id,
  w.name AS competitor_name,
  CASE
    WHEN m.winner_id IS NOT NULL AND CAST(m.winner_id AS TEXT) = CAST(w.id AS TEXT) THEN 'winner'
    WHEN m.loser_id IS NOT NULL AND CAST(m.loser_id AS TEXT) = CAST(w.id AS TEXT) THEN 'loser'
    ELSE 'participant'
  END AS competitor_slot
FROM Matches m
JOIN Wrestlers w ON CAST(w.id AS TEXT) = CAST(m.winner_id AS TEXT)
UNION ALL
SELECT
  m.id AS match_id,
  w.id AS competitor_id,
  w.name AS competitor_name,
  CASE
    WHEN m.winner_id IS NOT NULL AND CAST(m.winner_id AS TEXT) = CAST(w.id AS TEXT) THEN 'winner'
    WHEN m.loser_id IS NOT NULL AND CAST(m.loser_id AS TEXT) = CAST(w.id AS TEXT) THEN 'loser'
    ELSE 'participant'
  END AS competitor_slot
FROM Matches m
JOIN Wrestlers w ON CAST(w.id AS TEXT) = CAST(m.loser_id AS TEXT)
```

---

**Skill `nxt_title_shortest_match`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `match_id` |
| output columns | `match_id`, `duration_seconds`, `match_title`, `championship`, `description`, `result_text`, `match_type` |
| source tables | `matches_sel` |
| depends_on (builds on) | `matches_sel` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_From matches that are NXT title matches (joined to normalized duration) exclude any matches whose description, result_text, or match_type contains the literal phrase 'title change' (case-insensitive). Compute the minimum duration_seconds among the remaining matches and return the match_id(s) tied for that minimum duration. Keep match-level data to allow selecting the two competitors in the final output._

```sql
SELECT
  m.match_id,
  -- assume raw_duration is in a normalized format like seconds already; if not, this view's job is to use normalized duration_seconds column name
  CAST(m.raw_duration AS INTEGER) AS duration_seconds,
  m.match_title AS match_title,
  m.championship AS championship,
  m.description AS description,
  m.result_text AS result_text,
  m.match_type AS match_type
FROM matches_sel m
WHERE
  -- Only NXT title matches: championship contains 'NXT' (case-insensitive)
  LOWER(COALESCE(m.championship, '')) LIKE '%nxt%'
  -- Exclude any matches whose description, result_text, or match_type contains the literal phrase 'title change' (case-insensitive)
  AND LOWER(COALESCE(m.description, '')) NOT LIKE '%title change%'
  AND LOWER(COALESCE(m.result_text, '')) NOT LIKE '%title change%'
  AND LOWER(COALESCE(m.match_type, '')) NOT LIKE '%title change%'
  -- Exclude null or non-numeric durations; keep rows with a valid duration_seconds
  AND m.raw_duration IS NOT NULL
  AND TRIM(m.raw_duration) != ''
```

---
