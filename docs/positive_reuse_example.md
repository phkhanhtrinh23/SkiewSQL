# Positive view-reuse in config A — self-grown skills reused into *correct* answers

Verified positive-reuse case studies, traced end-to-end: **when/which earlier question built the skill, its full saved node (as a markdown skill card), the later question that reused it, and its graph neighbours.** A row counts only if the reused node **appears and is consumed** in the *correct* final SQL (not merely tallied).

**Favorability note.** The strongest case is when **both** the constructing question *and* the reusing question are correct (a good skill, born clean, reused clean). A weaker-but-still-positive case is when the skill was born in a *wrong* question and later reused correctly. Honest finding across our runs:

- **BigQuery has one FAVORABLE case** (correct-construct → correct-reuse): `objects_core` — Example 1.
- **Spider 2.0-lite has NO correct→correct case** — every genuine Spider2 reuse was born in a *wrong* question and reused correctly (Example 2). We report this rather than dress it up.

Skills below are rendered with `sqlview.skill_card_md()` (markdown, not JSON).

---

## Example 1 — FAVORABLE (correct → correct) · BigQuery · `the_met` · skill `objects_core`

**Constructed at `bq126` — CORRECT.**
> *"What are the titles, artist names, mediums, and original image URLs of objects with 'Photograph' in their names from the 'Photographs' department, created not by an unknown artist, with an object end date of 1839 or earlier?"* → `correct = True` (the skill was generated here and the answer was right).

**Reused at `bq414` — CORRECT.**
> *"Retrieve the object id, title, and the formatted metadata date (as 'YYYY-MM-DD') for objects in the 'The Libraries' department where the cropConfidence is greater than 0.5, and the object's title contains the word 'book'."* → `correct = True`, `reused = 1`, `seed = 0`.

So a clean base skill built by one correct question was reused by a later correct question — the favorable pattern.

### The saved skill (markdown)

**Skill `objects_core`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `object_id` |
| output columns | `object_id`, `title`, `object_name`, `department`, `artist_display_name`, `medium`, `object_end_date` |
| source tables | `` `bigquery-public-data.the_met.objects` `` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `images_by_object`, `objects_photographs_department`, `objects_with_images_join`, `object_label_associations`, `objects_normalized_text`, `objects_with_vision` |
| validated_on | *bq414* — "Retrieve the object id, title, and the formatted metadata date … 'book'." |
| counter_examples | 0 |

_One-row-per-object core records with canonical null-handling for textual fields. Exposes primary object attributes for downstream filtering and joins._

```sql
SELECT
  object_id,
  COALESCE(title, '')               AS title,      -- canonical null-handling
  COALESCE(object_name, '')         AS object_name,
  COALESCE(department, '')          AS department,
  COALESCE(artist_display_name, '') AS artist_display_name,
  COALESCE(medium, '')              AS medium,
  object_end_date
FROM `bigquery-public-data.the_met.objects`
```

### Consumed in the correct `bq414` query (the reused node is a referenced CTE)
```sql
WITH objects_core AS (            -- <-- REUSED node, verbatim
  SELECT object_id, COALESCE(title,'') AS title, ..., object_end_date
  FROM `bigquery-public-data.the_met.objects`
),
objects_with_vision AS (          -- newly generated at bq414, BUILT ON objects_core
  SELECT o.object_id, o.title, o.metadata_date,
         (SELECT MAX(ch.confidence) FROM UNNEST(v.cropHintsAnnotation.cropHints) ch) AS max_crop_hint_confidence, ...
  FROM objects_core o LEFT JOIN `bigquery-public-data.the_met.vision_api_data` v ON ...
)
SELECT object_id, title, metadata_date
FROM objects_with_vision
WHERE department = 'The Libraries' AND max_crop_hint_confidence > 0.5 AND LOWER(title) LIKE '%book%'
```

### Graph neighbours after the run
`objects_core` is a **heavily-shared foundation node**: `INSTANTIATES` under `skill::SEL`, no outgoing deps (reads base tables), and **six** later views build on it — including `objects_with_vision` (which `bq414` used). That is exactly the compounding-reuse the view-memory targets.

---

## Example 2 — positive but LESS favorable (wrong construct → correct reuse) · Spider2-lite · `IPL` · skill `ball_events_batsman_level`

**Constructed at `local021` — WRONG.**
> *"Could you calculate the average of the total runs scored by all strikers who have scored more than 50 runs in any single match?"* → `correct = False`. The *view itself* passed the execution dry-run and was kept. `local021`'s final composition failed elsewhere.

**Reused at `local022` — CORRECT.**
> *"Retrieve the names of players who scored no less than 100 runs in a match while playing for the team that lost that match."* → `correct = True`, `reused = 1`, `seed = 0`. (Only entry in the skill's `validated_on`.)

### The saved skill (markdown)

**Skill `ball_events_batsman_level`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `over_id`, `ball_id`, `innings_no`, `striker` |
| output columns | `match_id`, `over_id`, `ball_id`, `innings_no`, `striker`, `runs_scored` |
| source tables | `ball_by_ball`, `batsman_scored` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `player_match_runs`, `baller_delivery_events` |
| validated_on | *local022* — "Retrieve the names of players who scored no less than 100 runs …" |
| counter_examples | 0 |

_Denormalized ball-level events joined to the batsman runs so each row is a specific ball delivery associated with the striker and the batsman runs scored on that delivery. Keeps raw batsman runs separate from extras/wickets._

```sql
SELECT
  b.match_id, b.over_id, b.ball_id, b.innings_no, b.striker,
  bs.runs_scored
FROM ball_by_ball AS b
LEFT JOIN batsman_scored AS bs
  ON b.match_id=bs.match_id AND b.over_id=bs.over_id AND b.ball_id=bs.ball_id AND b.innings_no=bs.innings_no
```

### Consumed in the correct `local022` query
```sql
WITH ball_events_batsman_level AS ( ... ),               -- <-- REUSED node
player_match_participation AS ( SELECT match_id, player_id, team_id, role FROM player_match ),
player_match_runs AS (
  SELECT b.match_id, b.striker AS player_id, pm.team_id, SUM(b.runs_scored) AS total_runs
  FROM ball_events_batsman_level b                       -- <-- consumed here
  LEFT JOIN player_match_participation pm ON b.match_id=pm.match_id AND b.striker=pm.player_id
  GROUP BY b.match_id, b.striker, pm.team_id
)
SELECT DISTINCT p.player_name FROM player_match_runs pmr JOIN player_match_participation pmp ON ...
```

### Graph neighbours
`INSTANTIATES` under `skill::JOIN`. No outgoing deps. **Two** views build on it — `player_match_runs` (the CTE `local022` used) and `baller_delivery_events`.

---

## Additional Spider2 example (also wrong→correct) · `Pagila` · `film_categories`

**Skill `film_categories`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `film_id`, `category_id` |
| output columns | `film_id`, `category_id`, `category_name`, `last_update` |
| source tables | `film_category`, `category` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by | — |
| validated_on | *local039* — "…film category with the highest total rental hours in cities …" |

```sql
SELECT fc.film_id, fc.category_id, c.name AS category_name, fc.last_update
FROM film_category fc JOIN category c ON c.category_id = fc.category_id
```

Constructed at `local038` (**WRONG**) → reused correctly at `local039`: *"Please help me find the film category with the highest total rental hours in cities where the city's name either starts with 'A' or contains a hyphen."* (`correct = True`, `reused = 1`).

---

## Summary

| # | Benchmark | Skill | Construct → Reuse | Favorable? |
|---|---|---|---|---|
| 1 | BigQuery `the_met` | `objects_core` | `bq126` ✅ → `bq414` ✅ | **Yes (correct→correct)** |
| 2 | Spider2 `IPL` | `ball_events_batsman_level` | `local021` ❌ → `local022` ✅ | No (wrong construct) |
| 3 | Spider2 `Pagila` | `film_categories` | `local038` ❌ → `local039` ✅ | No (wrong construct) |

**Honest bottom line:** across all config-A runs, exactly **one** favorable correct→correct reuse exists (BigQuery `objects_core`). Every Spider2 genuine reuse had a *wrong* constructing question. The memory does compound (foundation nodes get built upon), but clean correct→correct reuse is still rare.
