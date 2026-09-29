# Skill graph — `log` (18 skills)

**Skill `session_events_filtered`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `session_id`, `event_timestamp`, `event_row_id` |
| output columns | `session_id`, `event_timestamp`, `page_path`, `event_row_id` |
| source tables | `form_log` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `session_event_ordered`, `session_landing_and_exit_rows` |
| validated_on | — |
| counter_examples | 0 |

_All event rows restricted to only those events whose page path exactly equals '/regist/input' or '/regist/confirm', keeping their session identifier and event timestamp._

```sql
SELECT
  session AS session_id,
  stamp AS event_timestamp,
  path AS page_path,
  rowid AS event_row_id
FROM form_log
WHERE path IN ('/regist/input', '/regist/confirm')
```

---

**Skill `session_event_ordered`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `session_id`, `event_row_id` |
| output columns | `session_id`, `event_timestamp`, `page_path`, `event_rank_in_session` |
| source tables | `session_events_filtered` |
| depends_on (builds on) | `session_events_filtered` |
| depended-on by (builds on this) | `session_has_input_and_confirm_flags` |
| validated_on | — |
| counter_examples | 0 |

_For each filtered event within a session, compute an ordering (e.g., row_number) by event timestamp to establish chronological order of events in the session._

```sql
SELECT
  session_id,
  event_timestamp,
  page_path,
  ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY event_timestamp) AS event_rank_in_session
FROM session_events_filtered
```

---

**Skill `session_has_input_and_confirm_flags`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `session_id` |
| output columns | `session_id`, `exists_input`, `exists_confirm`, `first_input_ts`, `first_confirm_ts` |
| source tables | `session_event_ordered` |
| depends_on (builds on) | `session_event_ordered` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Per session, compute boolean flags and earliest/latest timestamps for '/regist/input' and '/regist/confirm' events from the ordered filtered events (e.g., min timestamp for input, min timestamp for confirm, exists_input, exists_confirm)._

```sql
SELECT
  se.session_id AS session_id,
  CASE WHEN MIN(CASE WHEN se.page_path = '/regist/input' THEN se.event_timestamp END) IS NOT NULL THEN 1 ELSE 0 END AS exists_input,
  CASE WHEN MIN(CASE WHEN se.page_path = '/regist/confirm' THEN se.event_timestamp END) IS NOT NULL THEN 1 ELSE 0 END AS exists_confirm,
  MIN(CASE WHEN se.page_path = '/regist/input' THEN se.event_timestamp END) AS first_input_ts,
  MIN(CASE WHEN se.page_path = '/regist/confirm' THEN se.event_timestamp END) AS first_confirm_ts
FROM session_event_ordered se
WHERE se.page_path IN ('/regist/input','/regist/confirm')
GROUP BY se.session_id
```

---

**Skill `sessions_input_before_confirm`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `session_id` |
| output columns | `session_id` |
| source tables | `form_log` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select sessions that have at least one input and at least one confirm and where the earliest input timestamp is strictly earlier than the earliest confirm timestamp; produce one row per qualifying session to be counted once._

```sql
SELECT
  fh.session AS session_id
FROM (
  SELECT
    session,
    MIN(stamp) AS first_input_ts
  FROM form_log
  WHERE path = '/input'
  GROUP BY session
) fh
JOIN (
  SELECT
    session,
    MIN(stamp) AS first_confirm_ts
  FROM form_log
  WHERE path = '/confirm'
  GROUP BY session
) fc
  ON fh.session = fc.session
WHERE fh.first_input_ts < fc.first_confirm_ts
```

---

**Skill `activity_rows_with_sessions`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `row` |
| output columns | `session_id`, `timestamp`, `page` |
| source tables | `activity_log` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Subset of activity log rows that have a defined session identifier (i.e., only rows that belong to a session)._

```sql
SELECT
  session AS session_id,
  stamp AS timestamp,
  path AS page
FROM activity_log
WHERE session IS NOT NULL
  AND session <> ''
```

---

**Skill `session_landing_and_exit_rows`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `session_id` |
| output columns | `session_id`, `landing_page`, `exit_page` |
| source tables | `session_events_filtered` |
| depends_on (builds on) | `session_events_filtered` |
| depended-on by (builds on this) | `session_page_pairs`, `page_session_counts` |
| validated_on | — |
| counter_examples | 0 |

_For each session, identify the row(s) with the minimum timestamp (landing) and the row(s) with the maximum timestamp (exit). Keep the page value for landing and exit; if multiple rows share the min or max timestamp, each such row is kept (later deduping per session+page will handle duplicates)._

```sql
SELECT
  se.session_id AS session_id,
  se.page_path AS landing_page,
  ex.page_path AS exit_page
FROM
  -- landing rows: rows that have the minimum event_timestamp per session
  session_events_filtered se
JOIN
  (
    SELECT session_id, MIN(event_timestamp) AS min_ts
    FROM session_events_filtered
    GROUP BY session_id
  ) min_ts_per_s
  ON se.session_id = min_ts_per_s.session_id
  AND se.event_timestamp = min_ts_per_s.min_ts
JOIN
  -- exit rows: choose one of the rows having the maximum event_timestamp per session
  (
    SELECT session_id, page_path, event_timestamp
    FROM session_events_filtered
  ) ex
  ON ex.session_id = se.session_id
  AND ex.event_timestamp = (
    SELECT MAX(event_timestamp) FROM session_events_filtered WHERE session_id = se.session_id
  )
```

---

**Skill `session_page_pairs`** — category `RESHAPE`

| field | value |
|---|---|
| grain (one row per) | `session_id`, `page` |
| output columns | `session_id`, `page` |
| source tables | `session_landing_and_exit_rows` |
| depends_on (builds on) | `session_landing_and_exit_rows` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Unpivot the per-session landing and exit pages into one row per session_id and page where the page equals either the session's landing or exit page. Ensure that if landing_page equals exit_page the session still produces only one row for that page (deduplicate session+page pairs)._

```sql
SELECT
  session_id,
  landing_page AS page
FROM session_landing_and_exit_rows
UNION
SELECT
  session_id,
  exit_page AS page
FROM session_landing_and_exit_rows
```

---

**Skill `page_session_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `page` |
| output columns | `page`, `session_count` |
| source tables | `session_landing_and_exit_rows` |
| depends_on (builds on) | `session_landing_and_exit_rows` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each page value that appears as a landing or exit page in at least one session, count distinct sessions (session_id) that map to that page._

```sql
SELECT
  p.page AS page,
  COUNT(DISTINCT p.session_id) AS session_count
FROM (
  SELECT session_id, landing_page AS page FROM session_landing_and_exit_rows WHERE landing_page IS NOT NULL
  UNION ALL
  SELECT session_id, exit_page AS page FROM session_landing_and_exit_rows WHERE exit_page IS NOT NULL
) p
GROUP BY p.page
```

---

**Skill `ordered_user_sequences`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `event_id` |
| output columns | `user_id`, `session_id`, `event_timestamp`, `page_1`, `page_2`, `page_3` |
| source tables | `action_log` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `detail_detail_third_candidates` |
| validated_on | — |
| counter_examples | 0 |

_For each user's (or session's) events, order events chronologically and compute the page values for the current event and the next two events using lead functions so each row represents a 3-consecutive-visit window anchored at the first visit._

```sql
SELECT
  al.user_id AS user_id,
  al.session AS session_id,
  al.stamp AS event_timestamp,
  al.category AS page_1,
  LEAD(al.category, 1) OVER (PARTITION BY al.session ORDER BY al.stamp, rowid) AS page_2,
  LEAD(al.category, 2) OVER (PARTITION BY al.session ORDER BY al.stamp, rowid) AS page_3,
  rowid AS event_id
FROM action_log al
```

---

**Skill `detail_detail_third_candidates`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `event_id` |
| output columns | `user_id`, `session_id`, `event_timestamp`, `third_page` |
| source tables | — |
| depends_on (builds on) | `ordered_user_sequences` |
| depended-on by (builds on this) | `third_page_counts` |
| validated_on | — |
| counter_examples | 0 |

_Filter the ordered 3-visit windows to keep only those where page_1 and page_2 are both '/detail' (literal excluded from subgoal name per rules) and none of page_1/page_2/page_3 are NULL — each row is a candidate triple where the third page is the target._

```sql
SELECT
  ordered_user_sequences.user_id AS user_id,
  ordered_user_sequences.session_id AS session_id,
  ordered_user_sequences.event_timestamp AS event_timestamp,
  ordered_user_sequences.page_3 AS third_page
FROM ordered_user_sequences
WHERE ordered_user_sequences.page_1 = '/detail'
  AND ordered_user_sequences.page_2 = '/detail'
  AND ordered_user_sequences.page_1 IS NOT NULL
  AND ordered_user_sequences.page_2 IS NOT NULL
  AND ordered_user_sequences.page_3 IS NOT NULL
```

---

**Skill `third_page_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `third_page` |
| output columns | `third_page`, `count` |
| source tables | `detail_detail_third_candidates` |
| depends_on (builds on) | `detail_detail_third_candidates` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregate the candidate triples by the third_page value to count how many times each third_page follows two consecutive '/detail' visits. This produces one row per third_page with its occurrence count._

```sql
SELECT
  third_page AS third_page,
  COUNT(*) AS count
FROM
  detail_detail_third_candidates
GROUP BY
  third_page
```

---

**Skill `users_raw`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `user_id` |
| output columns | `user_id`, `age` |
| source tables | `mst_users` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `users_age_normalized` |
| validated_on | — |
| counter_examples | 0 |

_Select all rows from the users table, keeping the user identifier and the raw age value. Do not filter out any users here; include NULL ages._

```sql
SELECT
  user_id,
  CASE
    WHEN trim(birth_date) = '' THEN NULL
    ELSE
      (strftime('%Y', 'now') - strftime('%Y', birth_date)) - 
      (strftime('%m-%d', 'now') < strftime('%m-%d', birth_date))
  END AS age
FROM mst_users
```

---

**Skill `users_age_normalized`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `user_id` |
| output columns | `user_id`, `age_clean` |
| source tables | `users_raw` |
| depends_on (builds on) | `users_raw` |
| depended-on by (builds on this) | `users_with_age_category` |
| validated_on | — |
| counter_examples | 0 |

_Normalize and canonicalize the age value: ensure age is an integer or NULL, and produce a cleaned age field suitable for categorization (e.g., cast strings to integer where possible, leave invalid/unparsable as NULL)._

```sql
SELECT
  user_id,
  CASE
    WHEN trim(age) = '' THEN NULL
    WHEN age IS NULL THEN NULL
    WHEN CAST(age AS INTEGER) IS NOT NULL AND age LIKE '%[^0-9]%' = 0 AND instr(age, '.') = 0 THEN CAST(age AS INTEGER)
    WHEN age GLOB '[0-9]*' THEN CAST(age AS INTEGER)
    ELSE
      (CASE
         WHEN age GLOB '*[0-9]*' THEN
           -- extract leading integer digits
           CAST(substr(age, 1,
             (CASE
                WHEN instr(age, ' ')>0 THEN instr(age,' ')-1
                WHEN instr(age,'-')>0 THEN instr(age,'-')-1
                WHEN instr(age,'/')>0 THEN instr(age,'/')-1
                ELSE
                  (SELECT
                     CASE
                       WHEN instr(age, '.')>0 THEN instr(age,'.')-1
                       WHEN instr(age, ',')>0 THEN instr(age,',')-1
                       ELSE length(age)
                     END
                   )
              END
             )
           ) AS INTEGER)
         ELSE NULL
       END)
  END AS age_clean
FROM users_raw
```

---

**Skill `users_with_age_category`** — category `RESHAPE`

| field | value |
|---|---|
| grain (one row per) | `user_id` |
| output columns | `user_id`, `age_category` |
| source tables | `mst_users`, `users_age_normalized` |
| depends_on (builds on) | `users_age_normalized` |
| depended-on by (builds on this) | `user_count_per_age_category` |
| validated_on | — |
| counter_examples | 0 |

_Assign each user to an age_category based on age_clean into buckets: '20s' (20-29), '30s' (30-39), '40s' (40-49), '50s' (50-59), and 'others' (age_clean NULL, <20, or >=60). One row per user with their assigned category._

```sql
SELECT
  u.user_id,
  CASE
    WHEN a.age_clean BETWEEN 20 AND 29 THEN '20s'
    WHEN a.age_clean BETWEEN 30 AND 39 THEN '30s'
    WHEN a.age_clean BETWEEN 40 AND 49 THEN '40s'
    WHEN a.age_clean BETWEEN 50 AND 59 THEN '50s'
    ELSE 'others'
  END AS age_category
FROM users_age_normalized a
JOIN mst_users u USING (user_id)
```

---

**Skill `user_count_per_age_category`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `age_category` |
| output columns | `age_category`, `user_count` |
| source tables | `mst_users`, `users_with_age_category` |
| depends_on (builds on) | `users_with_age_category` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Count users per age_category. Do not apply additional filters here; produce one row per age_category with the user_count._

```sql
SELECT
  coalesce(uac.age_category, 'unknown') AS age_category,
  COUNT(m.user_id) AS user_count
FROM mst_users m
LEFT JOIN users_with_age_category uac
  ON m.user_id = uac.user_id
GROUP BY coalesce(uac.age_category, 'unknown')
```

---

**Skill `session_events_raw`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `session`, `event_id` |
| output columns | `session`, `event_id`, `event_timestamp`, `path`, `search_type`, `event_order` |
| source tables | `activity_log` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Select raw activity log events filtered to sessions that contain at least one '/detail' or '/complete' event. Keep event timestamp/order, session id, path, and search_type for each event._

```sql
SELECT
  session AS session,
  rowid AS event_id,
  stamp AS event_timestamp,
  path AS path,
  search_type AS search_type,
  NULL AS event_order
FROM activity_log
WHERE session IN (
  SELECT DISTINCT session FROM activity_log WHERE path = '/detail' OR path = '/complete'
)
```

---

**Skill `session_first_detail_or_complete`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `session` |
| output columns | `session`, `first_dc_event_id`, `first_dc_event_timestamp`, `first_dc_event_order` |
| source tables | `activity_log`, `form_log` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each session, find the earliest event (by timestamp or log order) whose path is '/detail' or '/complete'._

```sql
SELECT
  session AS session,
  MIN(rowid) AS first_dc_event_id,
  MIN(stamp) AS first_dc_event_timestamp,
  MIN(rowid) AS first_dc_event_order
FROM (
  SELECT rowid, stamp, session, path FROM activity_log
  UNION ALL
  SELECT rowid, stamp, session, path FROM form_log
)
WHERE path IN ('/detail', '/complete')
GROUP BY session
```

---

**Skill `pre_click_counts_and_min_sessions`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `session`, `path`, `search_type` |
| output columns | `session`, `pre_click_pre_conversion_count`, `path`, `search_type` |
| source tables | `activity_log` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Compute the count of pre-click/pre-conversion events (with non-empty search_type) per session, then identify the minimum count and return all sessions that equal that minimum along with the determining events' path and search_type rows for those sessions._

```sql
SELECT
  al.session AS session,
  COUNT(*) FILTER (WHERE al.search_type IS NOT NULL AND al.search_type <> '') AS pre_click_pre_conversion_count,
  al.path AS path,
  al.search_type AS search_type
FROM activity_log al
WHERE al.search_type IS NOT NULL AND al.search_type <> ''
GROUP BY al.session, al.path, al.search_type
HAVING COUNT(*) = (
  SELECT MIN(sess_count) FROM (
    SELECT COUNT(*) AS sess_count
    FROM activity_log al2
    WHERE al2.search_type IS NOT NULL AND al2.search_type <> ''
    GROUP BY al2.session
  )
)
```

---
