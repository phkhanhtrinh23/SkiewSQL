# Skill graph — `log` (4 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `form_log` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: Count the number of distinct sessions that first visited the /regist/input page and then later visited the /regist/confirm page, with the visits occurring in that order for each session. Require_

```sql
SELECT
  session,
  stamp,
  path
FROM form_log
WHERE path IN ('/regist/input', '/regist/confirm')
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `activity_log` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each web page value present in the activity log table, compute the total number of distinct user sessions in which that page appears as the session's landing page (the earliest timestamp wit_

```sql
SELECT
  al.session,
  al.stamp,
  al.path AS page
FROM
  activity_log al
WHERE
  al.path IS NOT NULL
```

---

**Skill `chunk_view_0_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `mst_users` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Count the number of users grouped by age category, where age categories are: '20s' for ages 20–29, '30s' for ages 30–39, '40s' for ages 40–49, '50s' for ages 50–59, and 'others' for all other ag_

```sql
SELECT
  user_id,
  birth_date
FROM
  mst_users
```

---

**Skill `chunk_view_0_3`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `activity_log` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each user session in the activity log table, count events that occur before the first event whose path is '/detail' or '/complete' (the first '/detail' or '/complete' event per session), cou_

```sql
SELECT
  al.session,
  al.stamp,
  al.path,
  al.search_type
FROM activity_log al
JOIN (
  -- find earliest '/detail' or '/complete' stamp per session
  SELECT
    session,
    MIN(stamp) AS first_detail_complete_stamp
  FROM activity_log
  WHERE path IN ('/detail','/complete')
  GROUP BY session
) first_pc
  ON al.session = first_pc.session
WHERE
  -- only events strictly before the first detail/complete event
  al.stamp < first_pc.first_detail_complete_stamp
  -- only events with non-empty search_type
  AND al.search_type IS NOT NULL
  AND al.search_type <> ''
```

---
