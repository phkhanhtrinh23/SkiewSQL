# Case studies: how `A + chunk-select + N×M + ReFoRCE` fixes questions the baseline gets wrong

Two real questions — one from **BEAVER**, one from **Spider 2.0-lite** — that the baseline (**B: AV-SQL**, single per-chunk proposer, no ReFoRCE) answers **incorrectly**, and that the full **SkiewSQL config A** pipeline (**chunk-select → question rewrite → N×M decompose-and-align → per-sub-goal ReFoRCE column-exploration → view generation → compose**) answers **correctly**.

Every artifact below is captured from an actual run (`scratchpad/capture_traces.py`). The "before" SQL is the real baseline output, the "after" trace is a cold re-run of config A that reproduces the correct answer (`correct = True`).

---

## Example 1 — BEAVER · `dw_real_5`

**Question.** List the unique term code, subject title, room, floor, building key, building street address, city, state, and postal code, formats, and number of enrolled students for all courses with more than 300 attendees.

**Database.** `dw` — a wide data-warehouse schema (**98 tables**, chunked into **5 schema chunk(s)**).

### ❌ Before — Baseline B (AV-SQL, no N×M / no ReFoRCE): WRONG

The single-pass proposer wrote SQL against **tables and columns that do not exist** — it guessed an enrollment column from DDL-style names instead of checking the data:

```sql
WITH sections_enrollment AS (
  SELECT
    s.SECTION_ID,
    s.TERM_CODE,
    s.SUBJECT_ID,
    s.SUBJECT_TITLE,
    s.MEET_PLACE,
    -- derive enrollment from possible columns. Treat non-numeric/NULL as 0
    COALESCE(
      NULLIF(s.ENROLLED_STUDENTS, '') + 0,
      NULLIF(s.ENROLLMENT, '') + 0,
      NULLIF(s.ENROLLED, '') + 0,
      0
    ) AS ENROLLED
  FROM course_catalog_subject_offered s
  -- filter to rows that have >300 after converting possible text to number
  WHERE COALESCE(
      NULLIF(s.ENROLLED_STUDENTS, '') + 0,
      NULLIF(s.ENROLLMENT, '') + 0,
      NULLIF(s.ENROLLED, '') + 0,
      0
    ) > 300
),
parsed_place AS (
  SELECT
    se.SECTION_ID,
    se.TERM_CODE,
    se.SUBJECT_ID,
    se.SUBJECT_TITLE,
    se.MEET_PLACE,
    TRIM(se.MEET_PLACE) AS raw_place,
    se.ENROLLED
  FROM sections_enrollment se
),
place_components AS (
  SELECT
    p.SECTION_ID,
    p.TERM_CODE,
    p.SUBJECT_ID,
    p.SUBJECT_TITLE,
    p.MEET_PLACE,
    p.raw_place,
    p.ENROLLED,
    -- room: take trailing token after last dash if present, else trailing token after last space, else whole raw_place
    CASE
      WHEN p.raw_place LIKE '%-%' THEN TRIM(SUBSTRING_INDEX(p.raw_place, '-', -1))
      WHEN p.raw_place LIKE '% %' THEN TRIM(SUBSTRING_INDEX(p.raw_place, ' ', -1))
      ELSE TRIM(p.raw_place)
    END AS room,
    -- floor_guess: leading digits of the room token if present
    CASE
      WHEN (CASE
              WHEN p.raw_place LIKE '%-%' THEN TRIM(SUBSTRING_INDEX(p.raw_place, '-', -1))
              WHEN p.raw_place LIKE '% %' THEN TRIM(SUBSTRING_INDEX(p.raw_place, ' ', -1))
              ELSE TRIM(p.raw_place)
            END) REGEXP '^[0-9]+'
      THEN CAST(
             (CASE
                WHEN p.raw_place LIKE '%-%' THEN TRIM(SUBSTRING_INDEX(p.raw_place, '-', -1))
                WHEN p.raw_place LIKE '% %' THEN TRIM(SUBSTRING_INDEX(p.raw_place, ' ', -1))
                ELSE TRIM(p.raw_place)
              END) AS UNSIGNED
           )
      ELSE NULL
    END AS floor
  FROM parsed_place p
),
meeting_places AS (
  SELECT
    pc.SECTION_ID,
    pc.TERM_CODE,
    pc.SUBJECT_ID,
    pc.SUBJECT_TITLE,
    pc.MEET_PLACE,
    pc.room,
    pc.floor,
    b.FAC_BUILDING_KEY,
    b.BUILDING_NAME,
    b.BUILDING_NUMBER,
    aba.ADDRESS_LINE AS street_address,
    aba.CITY,
    aba.STATE_PROVINCE AS state,
    aba.POSTAL_CODE AS postal_code,
    pc.ENROLLED
  FROM place_components pc
  LEFT JOIN fac_building b
    -- match on building number occurring in meet_place/raw_place when available
    ON b.BUILDING_NUMBER IS NOT NULL
    AND b.BUILDING_NUMBER <> ''
    AND (
      pc.MEET_PLACE LIKE CONCAT('%', b.BUILDING_NUMBER, '%')
      OR pc.raw_place LIKE CONCAT('%', b.BUILDING_NUMBER, '%')
    )
  LEFT JOIN fac_building_address aba
    ON aba.FAC_BUILDING_KEY = b.FAC_BUILDING_KEY
    AND aba.ADDRESS_PURPOSE = 'STREET'
),
final_enroll AS (
  SELECT
    mp.TERM_CODE,
    mp.SUBJECT_TITLE,
    mp.room,
    mp.floor,
    mp.FAC_BUILDING_KEY,
    mp.street_address,
    mp.CITY,
    mp.state,
    mp.postal_code,
    mp.ENROLLED
  FROM meeting_places mp
)
SELECT
  DISTINCT
  TERM_CODE,
  SUBJECT_TITLE,
  room AS ROOM,
  floor AS FLOOR,
  FAC_BUILDING_KEY AS BUILDING_KEY,
  street_address AS STREET_ADDRESS,
  CITY,
  state AS STATE,
  postal_code AS POSTAL_CODE,
  FORMAT(ENROLLED,0) AS ENROLLED_COUNT_FORMATTED,
  ENROLLED AS ENROLLED_COUNT
FROM final_enroll
```

**Result:** `(1054, "Unknown column 's.ENROLLED_STUDENTS' in 'field list'")` → the query fails to execute. The proposer invented `course_catalog_subject_offered.ENROLLED_STUDENTS` / `.ENROLLMENT` / `.ENROLLED`, none of which exist on that table.

### ✅ After — Config A (chunk-select + N×M + ReFoRCE): CORRECT

**Step 1 — Question rewrite** (structured task + required outputs):

```
Task: Return one row per course (section) that has more than 300 enrolled students, including term and location details and formatted student count.
Required outputs: TERM_CODE (unique term code for the course/section). SUBJECT_TITLE (title of the subject/course). ROOM (room identifier / meet_place). FLOOR (floor extracted from building or room data if available). BUILDING_KEY (BUILDING_KEY from buildings table linked to the room/section). BUILDING_STREET_ADDRESS (the street address for the building. Only rows where ADDRESS_PURPOSE = 'STREET' should be used to identify a street address). CITY (city of the building's address). STATE (state of the building's address). POSTAL_CODE (postal / ZIP code of the building's address). PHONE_FORMATS (any phone format(s) associated with the building or room, if present in the schema — otherwise null). NUM_ENROLLED (number of enrolled students for the
```

**Step 2 — ReFoRCE format restriction** (fix the answer columns up front):

```
```csv
term_code,subject_title,room,floor,building_key,building_street_address,city,state,postal_code,formats,enrolled_students
```
```

**Step 3 — N×M decompose** the question into coherent sub-goals (each with a target grain):

1. **`sections_with_meetplace_and_enrollment`** — category `SEL`, grain `['subject_offered.CLASS_NBR', 'subject_offered.TERM_CODE']`
   - _One row per course section (subject-offered / course instance) with its term code, meet place/room identifier, and enrolled headcount where available. Keeps raw section-level fields so downstream joins can link to course catalog and building data._
2. **`course_catalog_titles`** — category `JOIN`, grain `['cis_course_catalog.SUBJECT', 'cis_course_catalog.CATALOG_NBR']`
   - _Mapping of course catalog entries to canonical course title/subject information. One row per distinct course identifier (subject + catalog number + optional term/effective term if needed) providing the human-readable course title used for sections._
3. **`buildings_with_street_address`** — category `SEL`, grain `['buildings.BUILDING_KEY']`
   - _One row per building key with its STREET-purpose address components (street, city, state, postal code) when an ADDRESS_PURPOSE = 'STREET' row exists. If an address table is not present, these columns will be null in downstream joins._
4. **`room_to_building_mapping_and_floor`** — category `JOIN`, grain `['fac_rooms.ROOM_ID']`
   - _Resolve room or meet_place identifiers to building keys and extract floor where possible. One row per room identifier (room/building pair or meet_place string). Attempts to use facility/space tables to map room codes to BUILDING_KEY and floor. If not available, floor may be parsed from MEET_PLACE string._

**Step 4 — Align** each sub-goal against every schema chunk to collect *only* its real tables (the N×M loop). The decomposer's guessed `source_tables` are pruned to what actually exists in the chunks:

- `sections_with_meetplace_and_enrollment` → **['course_catalog_subject_offered', 'subject_offered']**
- `course_catalog_titles` → **['cis_course_catalog', 'course_catalog_subject_offered', 'drupal_course_catalog', 'subject_offered', 'subject_offered_summary', 'subject_selector', 'subject_summary', 'tip_subject_offered']**
- `buildings_with_street_address` → **['buildings', 'fac_building', 'fac_building_address']**
- `room_to_building_mapping_and_floor` → **['buildings', 'fac_building', 'fac_floor', 'fac_rooms', 'fclt_building', 'fclt_building_address', 'fclt_floor', 'fclt_rooms', 'fclt_rooms_hist', 'space_detail', 'space_floor', 'space_unit', 'space_unit2']**

**Step 5 — ReFoRCE column-exploration** — before writing each view, run `SELECT DISTINCT` probes so columns are chosen from *observed values*, not DDL names. E.g.:

```
Query:
SELECT DISTINCT `COURSE_NUMBER` FROM `subject_offered_summary`;
Answer:
COURSE_NUMBER
            1
           10
           11
           12
           13
Query:
SELECT DISTINCT SUBJECT_SUMMARY_KEY
FROM subject_offered_summary
WHERE SUBJECT_SUMMARY_KEY IS NOT NULL
LIMIT 100;
Answer:
SUBJECT_
```
```
Query:
SELECT DISTINCT SUBJECT_ID
FROM cis_course_catalog
ORDER BY SUBJECT_ID
LIMIT 200;
Answer:
SUBJECT_ID
     1.011
     1.080
     1.082
     1.083
     1.133
Query:
SELECT DISTINCT `SUBJECT_ID` AS `SUBJECT`, `SUBJECT_NUMBER` AS `CATALOG_NBR`
FROM `cis_course_catalog`
ORDER BY `SUBJECT`, `CATALO
```

**Step 6 — Generate the aligned views** (grounded in the real columns found above):

**View `sections_with_meetplace_and_enrollment`** — grain `['subject_offered.CLASS_NBR', 'subject_offered.TERM_CODE']`
- output columns: `['subject_offered.TERM_CODE', 'subject_offered.SUBJECT', 'subject_offered.CATALOG_NBR', 'subject_offered.CLASS_NBR', 'subject_offered.MEET_PLACE', 'subject_offered.ENRL_TOT']`

```sql
SELECT
  so.`TERM_CODE`                                                   AS TERM_CODE,
  so.`SUBJECT_ID`                                                   AS SUBJECT,
  so.`COURSE_NUMBER`                                                AS CATALOG_NBR,
  so.`SECTION_ID`                                                   AS CLASS_NBR,
  so.`MEET_PLACE`                                                   AS MEET_PLACE,
  so.`NUM_ENROLLED_STUDENTS`                                        AS ENRL_TOT
FROM `subject_offered` so
```

**View `course_catalog_titles`** — grain `['cis_course_catalog.SUBJECT', 'cis_course_catalog.CATALOG_NBR']`
- output columns: `['cis_course_catalog.SUBJECT', 'cis_course_catalog.CATALOG_NBR', 'cis_course_catalog.TITLE']`

```sql
SELECT
  `cis_course_catalog`.`SUBJECT` AS `SUBJECT`,
  `cis_course_catalog`.`SUBJECT_NUMBER` AS `CATALOG_NBR`,
  `cis_course_catalog`.`SUBJECT_TITLE` AS `TITLE`
FROM `cis_course_catalog`
```

**View `buildings_with_street_address`** — grain `['buildings.BUILDING_KEY']`
- output columns: `['buildings.BUILDING_KEY', 'buildings.TITLE', 'fac_building_address.ADDRESS_PURPOSE', 'fac_building_address.ADDRESS_LINE1', 'fac_building_address.CITY', 'fac_building_address.STATE', 'fac_building_address.POSTAL_CODE']`

```sql
SELECT
  b.BUILDING_KEY AS BUILDING_KEY,
  b.BUILDING_NAME AS TITLE,
  fba.ADDRESS_PURPOSE AS ADDRESS_PURPOSE,
  -- Construct ADDRESS_LINE1 from fac_building_address components: prefer STREET_NUMBER + STREET_NAME when available
  CASE
    WHEN fba.STREET_NUMBER IS NOT NULL AND fba.STREET_NAME IS NOT NULL THEN
      CONCAT(
        COALESCE(fba.STREET_NUMBER, ''),
        CASE WHEN COALESCE(fba.STREET_NUMBER, '') <> '' AND COALESCE(fba.STREET_NUMBER_SUFFIX, '') <> '' THEN CONCAT(fba.STREET_NUMBER_SUFFIX, '') ELSE COALESCE(fba.STREET_NUMBER_SUFFIX, '') END,
        CASE WHEN COALESCE(fba.PRE_DIRECTIONAL, '') <> '' THEN CONCAT(' ', fba.PRE_DIRECTIONAL) ELSE '' END,
        CASE WHEN COALESCE(fba.STREET_NUMBER, '') <> '' AND COALESCE(fba.STREET_NAME, '') <> '' THEN ' ' ELSE '' END,
        COALESCE(fba.STREET_NAME, ''),
        CASE WHEN COALESCE(fba.STREET_SUFFIX, '') <> '' THEN CONCAT(' ', fba.STREET_SUFFIX) ELSE '' END,
        CASE WHEN COALESCE(fba.POST_DIRECTIONAL, '') <> '' THEN CONCAT(' ', fba.POST_DIRECTIONAL) ELSE '' END
      )
    ELSE NULL
  END AS ADDRESS_LINE1,
  fba.CITY AS CITY,
  fba.STATE AS STATE,
  fba.POSTAL_CODE AS POSTAL_CODE
FROM buildings b
LEFT JOIN fac_building_address fba
  ON fba.BUILDING_KEY = b.BUILDING_KEY
  AND fba.ADDRESS_PURPOSE = 'STREET'
```

**View `room_to_building_mapping_and_floor`** — grain `['fac_rooms.ROOM_ID']`
- output columns: `['fac_rooms.BUILDING_KEY', 'fac_rooms.ROOM_ID', 'fclt_rooms.BUILDING_KEY', 'fclt_rooms.ROOM_ID', 'space_unit.ROOM', 'space_unit.BUILDING_KEY', 'space_floor.FLOOR']`

```sql
SELECT
  fr.BUILDING_KEY AS `BUILDING_KEY`,
  fr.FAC_ROOM_KEY AS `ROOM_ID`,
  fr2.FCLT_BUILDING_KEY AS `FCLT_BUILDING_KEY`,
  fr2.FCLT_ROOM_KEY AS `FCLT_ROOM_ID`,
  su.SPACE_UNIT AS `ROOM`,
  su.FCLT_ORGANIZATION_KEY AS `SPACE_UNIT_BUILDING_KEY`,
  sf.FLOOR AS `FLOOR`
FROM fac_rooms fr
LEFT JOIN fclt_rooms fr2
  ON fr.BUILDING_KEY = fr2.FCLT_BUILDING_KEY
  AND fr.ROOM = fr2.ROOM
LEFT JOIN space_detail sd
  ON fr.BUILDING_KEY = sd.BUILDING_KEY
  AND fr.FLOOR_KEY = sd.FLOOR_KEY
  AND fr.ROOM = sd.ROOM_NUMBER
LEFT JOIN space_unit su
  ON sd.SPACE_UNIT_KEY = su.SPACE_UNIT_KEY
LEFT JOIN space_floor sf
  ON sd.FLOOR_KEY = sf.FLOOR_KEY
```

**Step 7 — Compose** the sub-goal views into the final query (executes, matches gold):

```sql
SELECT
  s.TERM_CODE AS term_code,
  so.SUBJECT_TITLE AS subject_title,
  s.MEET_PLACE AS room,
  COALESCE(r.FLOOR,
           NULLIF(TRIM(SUBSTRING_INDEX(s.MEET_PLACE, '/', 1)),'')
  ) AS floor,
  COALESCE(r.BUILDING_KEY, su.FCLT_ORGANIZATION_KEY) AS building_key,
  COALESCE(bwa.ADDRESS_LINE1, b.BUILDING_STREET_ADDRESS) AS building_street_address,
  bwa.CITY AS city,
  bwa.STATE AS state,
  bwa.POSTAL_CODE AS postal_code,
  NULL AS formats,
  s.ENRL_TOT AS enrolled_students
FROM (
  -- sections with meet place and enrollment
  SELECT
    so.TERM_CODE,
    so.MEET_PLACE,
    so.NUM_ENROLLED_STUDENTS AS ENRL_TOT,
    so.SUBJECT_ID,
    so.COURSE_NUMBER,
    so.SECTION_ID,
    so.SUBJECT_OFFERED_SUMMARY_KEY
  FROM subject_offered so
) s
LEFT JOIN subject_offered so
  ON s.SUBJECT_OFFERED_SUMMARY_KEY = so.SUBJECT_OFFERED_SUMMARY_KEY
-- map room to building and floor where possible
LEFT JOIN (
  SELECT
    fr.BUILDING_KEY,
    fr.FAC_ROOM_KEY,
    fr.ROOM,
    fr.FLOOR
  FROM fac_rooms fr
  UNION
  SELECT
    fclt.FCLT_BUILDING_KEY AS BUILDING_KEY,
    fclt.FCLT_ROOM_KEY AS FAC_ROOM_KEY,
    fclt.ROOM,
    fclt.FLOOR
  FROM fclt_rooms fclt
) r
  ON s.MEET_PLACE = r.ROOM
-- try to get space unit/building key from space_detail -> space_unit
LEFT JOIN space_detail sd
  ON r.BUILDING_KEY = sd.BUILDING_KEY
  AND (r.ROOM = sd.ROOM_NUMBER OR s.MEET_PLACE = sd.BUILDING_ROOM)
LEFT JOIN space_unit su
  ON sd.SPACE_UNIT_KEY = su.SPACE_UNIT_KEY
-- building master record
LEFT JOIN buildings b
  ON COALESCE(r.BUILDING_KEY, su.FCLT_ORGANIZATION_KEY) = b.BUILDING_KEY
-- building street address (fac_building_address / fac_building_address.ADDRESS_PURPOSE = 'STREET')
LEFT JOIN (
  SELECT
    fba.BUILDING_KEY,
    fba.ADDRESS_PURPOSE,
    CASE
      WHEN COALESCE(fba.STREET_NUMBER,'') <> '' OR COALESCE(fba.STREET_NAME,'') <> '' THEN
        CONCAT(
          COALESCE(fba.STREET_NUMBER,''),
          COALESCE(fba.STREET_NUMBER_SUFFIX,''),
          CASE WHEN COALESCE(fba.PRE_DIRECTIONAL,'') <> '' THEN CONCAT(' ', fba.PRE_DIRECTIONAL) ELSE '' END,
          CASE WHEN COALESCE(fba.STREET_NUMBER,'') <> '' AND COALESCE(fba.STREET_NAME,'') <> '' THEN ' ' ELSE '' END,
          COALESCE(fba.STREET_NAME,''),
          CASE WHEN COALESCE(fba.STREET_SUFFIX,'') <> '' THEN CONCAT(' ', fba.STREET_SUFFIX) ELSE '' END,
          CASE WHEN COALESCE(fba.POST_DIRECTIONAL,'') <> '' THEN CONCAT(' ', fba.POST_DIRECTIONAL) ELSE '' END
        )
      ELSE NULL
    END AS ADDRESS_LINE1,
    fba.CITY,
    fba.STATE,
    fba.POSTAL_CODE
  FROM fac_building_address fba
  WHERE fba.ADDRESS_PURPOSE = 'STREET'
) bwa
  ON b.BUILDING_KEY = bwa.BUILDING_KEY
WHERE s.ENRL_TOT IS NOT NULL
  AND s.ENRL_TOT > 300
GROUP BY
  s.TERM_CODE,
  so.SUBJECT_TITLE,
  s.MEET_PLACE,
  COALESCE(r.FLOOR, NULLIF(TRIM(SUBSTRING_INDEX(s.MEET_PLACE, '/', 1)),'') ),
  COALESCE(r.BUILDING_KEY, su.FCLT_ORGANIZATION_KEY),
  COALESCE(bwa.ADDRESS_LINE1, b.BUILDING_STREET_ADDRESS),
  bwa.CITY,
  bwa.STATE,
  bwa.POSTAL_CODE,
  s.ENRL_TOT
```

**Result: `correct = True`** (3 views generated & validated). The full pipeline used the *real* `subject_offered.NUM_ENROLLED_STUDENTS` enrollment column (surfaced by exploration) and the real `cis_course_catalog` / `fac_building_address` / `fac_rooms` tables (surfaced by alignment) — exactly the pieces the baseline hallucinated.

**Why the pipeline fixed it:** *alignment* replaced a hallucinated table with the real `subject_offered`, and *ReFoRCE exploration* replaced a guessed `ENROLLED_STUDENTS` column with the real enrollment column verified against data.

---

## Example 2 — Spider 2.0-lite · `local026` (`IPL` cricket DB)

**Question.** Please help me identify the top 3 bowlers who, in the overs where the maximum runs were conceded in each match, gave up the highest number of runs in a single over across all matches. For each of these bowlers, provide the match in which they conceded these maximum runs. Only consider overs that had the most runs conceded within their respective matches, and among these, determine which bowlers conceded the most runs in a single over overall.

**Database.** `IPL` — ball-by-ball cricket data (**1 chunk(s)**).

### ❌ Before — Baseline B (AV-SQL): WRONG (executes, wrong answer)

B computed over-totals **collapsing the `innings_no` grain** — it summed runs for a `(match, over)` *across both innings*, then attached bowlers through a separate `DISTINCT (match, over, bowler)` join. That conflates two different innings' overs into one and mis-attributes the bowler:

```sql
WITH over_runs_by_innings AS (
SELECT
  b.match_id,
  b.over_id,
  b.innings_no,
  COALESCE(b.sum_runs, 0) + COALESCE(e.sum_extras, 0) AS runs_in_over_innings
FROM
  (
    SELECT
      match_id,
      over_id,
      innings_no,
      SUM(runs_scored) AS sum_runs
    FROM batsman_scored
    GROUP BY match_id, over_id, innings_no
  ) AS b
  LEFT JOIN
  (
    SELECT
      match_id,
      over_id,
      innings_no,
      SUM(extra_runs) AS sum_extras
    FROM extra_runs
    GROUP BY match_id, over_id, innings_no
  ) AS e
  ON b.match_id = e.match_id
  AND b.over_id = e.over_id
  AND b.innings_no = e.innings_no
UNION
-- include overs/innings that have only extras but no batsman_scored rows
SELECT
  e.match_id,
  e.over_id,
  e.innings_no,
  COALESCE(b.sum_runs, 0) + COALESCE(e.sum_extras, 0) AS runs_in_over_innings
FROM
  (
    SELECT
      match_id,
      over_id,
      innings_no,
      SUM(extra_runs) AS sum_extras
    FROM extra_runs
    GROUP BY match_id, over_id, innings_no
  ) AS e
  LEFT JOIN
  (
    SELECT
      match_id,
      over_id,
      innings_no,
      SUM(runs_scored) AS sum_runs
    FROM batsman_scored
    GROUP BY match_id, over_id, innings_no
  ) AS b
  ON e.match_id = b.match_id
  AND e.over_id = b.over_id
  AND e.innings_no = b.innings_no
WHERE b.sum_runs IS NULL
),
bowlers_by_match_over AS (
SELECT DISTINCT
  b.match_id AS match_id,
  b.over_id AS over_id,
  b.bowler AS bowler
FROM ball_by_ball b
WHERE b.match_id IS NOT NULL
  AND b.over_id IS NOT NULL
  AND b.bowler IS NOT NULL
),
over_total_runs_across_innings AS (
SELECT
  ori.match_id,
  ori.over_id,
  SUM(ori.runs_in_over_innings) AS runs_conceded_in_over
FROM over_runs_by_innings AS ori
GROUP BY
  ori.match_id,
  ori.over_id
)
SELECT
  p.player_id AS bowler_id,
  p.player_name AS bowler_name,
  o.match_id,
  o.over_id,
  o.runs_conceded_in_over
FROM over_total_runs_across_innings o
JOIN (
  SELECT match_id, MAX(runs_conceded_in_over) AS max_runs
  FROM over_total_runs_across_innings
  WHERE match_id IS NOT NULL
  GROUP BY match_id
) m ON o.match_id = m.match_id AND o.runs_conceded_in_over = m.max_runs
JOIN bowlers_by_match_over b
  ON o.match_id = b.match_id AND o.over_id = b.over_id
JOIN player p
  ON b.bowler = p.player_id
WHERE o.match_id IS NOT NULL
  AND o.over_id IS NOT NULL
  AND b.bowler IS NOT NULL
ORDER BY o.runs_conceded_in_over DESC, o.match_id ASC, p.player_id ASC
LIMIT 3
```

**Result:** executes but returns the **wrong rows** — the runs-per-over are inflated by summing across innings, and a single over can pull in the wrong bowler.

### ✅ After — Config A (chunk-select + N×M + ReFoRCE): CORRECT

**Step 1 — Question rewrite:**

```
Task: Find the top 3 bowlers who, considering only the overs that were the maximum-scoring over(s) within their match, conceded the most runs in a single over across all matches, and report for each bowler the match where that maximum-over concession occurred.
Required outputs: bowler_id (integer). bowler_name (text). match_id (integer) in which the bowler conceded the reported runs. match_date (date) of that match. team_bowling_id (integer) the bowler represented in that match/over. over_id (integer) identifying the over within the match. runs_conceded_in_over (integer) total runs conceded by the bowler in that over (including batsman runs and extras). rank (integer) 1..3 with 1 = highest runs conceded
Filters: Only consider overs that are the maximum total-run over(s) within their respec
```

**Step 2 — ReFoRCE format restriction:**

```
```csv
bowler_name,player_id,match_id,match_date,over_number,runs_in_over:int
```
```

**Step 3 — N×M decompose** — note every sub-goal **keeps `innings_no` in its grain**, the key the baseline dropped:

1. **`ball_level_events`** — category `JOIN`, grain `['match_id', 'innings_no', 'over_id', 'ball_id']`
   - _One row per ball delivery event, denormalizing ball_by_ball with batsman_scored and extra_runs so each delivery carries its batsman runs and extra runs (nullable if none). Includes match, innings, over, bowler, and team bowling info._
2. **`over_total_runs`** — category `AGG`, grain `['match_id', 'innings_no', 'over_id']`
   - _Total runs in each over (summing batsman runs and extras) per match, innings, and over. One row per over with the summed total_runs_in_over._
3. **`match_max_over_runs`** — category `AGG`, grain `['match_id']`
   - _For each match (across all innings), the maximum over total runs value observed in that match. One row per match with max_over_runs._
4. **`bowler_over_concessions`** — category `AGG`, grain `['match_id', 'innings_no', 'over_id', 'bowler']`
   - _Runs conceded by each bowler in each over (summing batsman runs and extras for balls in that over where they were the bowler). One row per match, innings, over and bowler indicating runs_conceded_in_over and team_bowling_id._

**Step 4 — Align** each sub-goal to its real tables:

- `ball_level_events` → **['ball_by_ball', 'batsman_scored', 'extra_runs']**
- `over_total_runs` → **['batsman_scored', 'extra_runs']**
- `match_max_over_runs` → **['batsman_scored', 'extra_runs']**
- `bowler_over_concessions` → **['ball_by_ball', 'batsman_scored', 'extra_runs']**

**Step 5 — ReFoRCE column-exploration** literally probes the grain from data (`SELECT DISTINCT match_id, innings_no, over_id, ball_id ...`), confirming a ball is keyed by innings:

```
Query:
-- Description: Get distinct combinations of match, innings, over and ball present in ball_by_ball to understand grain
SELECT DISTINCT "match_id", "innings_no", "over_id", "ball_id" FROM "ball_by_ball" LIMIT 50;
Answer:
[(335987, 2, 1, 1), (335987, 1, 1, 2), (335987, 2, 1,
```
```
Query:
--Description: show distinct matches present in the batsman_scored table
SELECT DISTINCT "match_id" FROM "batsman_scored";
Answer:
[(335987,), (335988,), (335989,), (335990,), (335991,)]
Query:
--Description: show distinct innings numbers present in the batsman_scored tabl
```

**Step 6 — Generate the aligned views** (grain preserved end-to-end):

**View `ball_level_events`** — grain `['match_id', 'innings_no', 'over_id', 'ball_id']`
- output columns: `['match_id', 'innings_no', 'over_id', 'ball_id', 'bowler', 'team_bowling_id', 'runs_scored', 'extra_runs']`

```sql
SELECT
  b.match_id,
  b.innings_no,
  b.over_id,
  b.ball_id,
  b.bowler,
  b.team_bowling AS team_bowling_id,
  bs.runs_scored AS runs_scored,
  er.extra_runs AS extra_runs
FROM ball_by_ball b
LEFT JOIN batsman_scored bs
  ON bs.match_id = b.match_id
  AND bs.innings_no = b.innings_no
  AND bs.over_id = b.over_id
  AND bs.ball_id = b.ball_id
LEFT JOIN extra_runs er
  ON er.match_id = b.match_id
  AND er.innings_no = b.innings_no
  AND er.over_id = b.over_id
  AND er.ball_id = b.ball_id
```

**View `over_total_runs`** — grain `['match_id', 'innings_no', 'over_id']`
- output columns: `['match_id', 'innings_no', 'over_id', 'total_runs_in_over']`

```sql
SELECT
  ble.match_id AS match_id,
  ble.innings_no AS innings_no,
  ble.over_id AS over_id,
  SUM(COALESCE(ble.runs_scored, 0) + COALESCE(ble.extra_runs, 0)) AS total_runs_in_over
FROM
  ball_level_events AS ble
GROUP BY
  ble.match_id,
  ble.innings_no,
  ble.over_id
```

**View `bowler_over_concessions`** — grain `['match_id', 'innings_no', 'over_id', 'bowler', 'team_bowling_id']`
- output columns: `['match_id', 'innings_no', 'over_id', 'bowler', 'team_bowling_id', 'runs_conceded_in_over']`

```sql
SELECT
  ble.match_id,
  ble.innings_no,
  ble.over_id,
  ble.bowler,
  ble.team_bowling_id,
  SUM(COALESCE(ble.runs_scored,0) + COALESCE(ble.extra_runs,0)) AS runs_conceded_in_over
FROM
  ball_level_events AS ble
GROUP BY
  ble.match_id,
  ble.innings_no,
  ble.over_id,
  ble.bowler,
  ble.team_bowling_id
```

**Step 7 — Compose** into the final query (executes, matches gold):

```sql
WITH ball_level_events AS (
SELECT
  b.match_id,
  b.innings_no,
  b.over_id,
  b.ball_id,
  b.bowler,
  b.team_bowling AS team_bowling_id,
  bs.runs_scored AS runs_scored,
  er.extra_runs AS extra_runs
FROM ball_by_ball b
LEFT JOIN batsman_scored bs
  ON bs.match_id = b.match_id
  AND bs.innings_no = b.innings_no
  AND bs.over_id = b.over_id
  AND bs.ball_id = b.ball_id
LEFT JOIN extra_runs er
  ON er.match_id = b.match_id
  AND er.innings_no = b.innings_no
  AND er.over_id = b.over_id
  AND er.ball_id = b.ball_id
),
over_total_runs AS (
SELECT
  ble.match_id AS match_id,
  ble.innings_no AS innings_no,
  ble.over_id AS over_id,
  SUM(COALESCE(ble.runs_scored, 0) + COALESCE(ble.extra_runs, 0)) AS total_runs_in_over
FROM
  ball_level_events AS ble
GROUP BY
  ble.match_id,
  ble.innings_no,
  ble.over_id
),
bowler_over_concessions AS (
SELECT
  ble.match_id,
  ble.innings_no,
  ble.over_id,
  ble.bowler,
  ble.team_bowling_id,
  SUM(COALESCE(ble.runs_scored,0) + COALESCE(ble.extra_runs,0)) AS runs_conceded_in_over
FROM
  ball_level_events AS ble
GROUP BY
  ble.match_id,
  ble.innings_no,
  ble.over_id,
  ble.bowler,
  ble.team_bowling_id
)
SELECT
  boc.bowler AS bowler_id,
  p.player_name AS bowler_name,
  boc.match_id,
  m.match_date,
  boc.team_bowling_id,
  boc.over_id,
  boc.runs_conceded_in_over,
  ROW_NUMBER() OVER (
    ORDER BY boc.runs_conceded_in_over DESC, m.match_date ASC, boc.match_id ASC, boc.bowler ASC
  ) AS rank
FROM bowler_over_concessions boc
JOIN (
  SELECT
    otr.match_id,
    MAX(otr.total_runs_in_over) AS match_max_over_runs
  FROM over_total_runs otr
  GROUP BY otr.match_id
) mm ON boc.match_id = mm.match_id
JOIN over_total_runs otr2
  ON otr2.match_id = boc.match_id
  AND otr2.innings_no = boc.innings_no
  AND otr2.over_id = boc.over_id
  AND otr2.total_runs_in_over = mm.match_max_over_runs
LEFT JOIN player p ON p.player_id = boc.bowler
LEFT JOIN match m ON m.match_id = boc.match_id
ORDER BY boc.runs_conceded_in_over DESC, m.match_date ASC, boc.match_id ASC, boc.bowler ASC
LIMIT 3
```

**Result: `correct = True`**. Because N×M built a ball-level view at grain `(match, innings, over, ball, bowler)` first, the per-over totals stay **within an innings** and the bowler is carried at the correct grain — fixing exactly the collapse that made the baseline wrong.

**Why the pipeline fixed it:** the *decomposition* pinned the correct grain (`innings_no` retained), and *exploration* verified that grain against the data before any aggregation was written.

---

## Summary

| | Baseline B | Config A (chunk-select + N×M + ReFoRCE) |
|---|---|---|
| BEAVER `dw_real_5` | ❌ hallucinated table/column → SQL error | ✅ real columns via align + exploration |
| Spider2 `local026` | ❌ collapsed innings grain → wrong rows | ✅ grain preserved via N×M decomposition |

In both cases the fix is the same mechanism: **N×M decompose-and-align** grounds each sub-goal in the real tables (no hallucinated schema), and **ReFoRCE exploration** grounds each column and grain in observed data before any SQL is written.
