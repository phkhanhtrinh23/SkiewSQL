# Skill graph — `log` (2 skills)

**Skill `target_page_visits`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `session_id`, `page_path`, `visit_timestamp` |
| output columns | `session_id`, `page_path`, `visit_timestamp` |
| source tables | `activity_log` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `valid_sequence_sessions` |
| validated_on | — |
| counter_examples | 0 |

_Filter visit records to only include the two target registration pages, retaining session identifier, page path, and visit timestamp._

```sql
SELECT session AS session_id, path AS page_path, stamp AS visit_timestamp FROM activity_log WHERE path IN ('/regist/input', '/regist/confirm')
```

---

**Skill `valid_sequence_sessions`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `session_id` |
| output columns | `session_id` |
| source tables | `target_page_visits` |
| depends_on (builds on) | `target_page_visits` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregate visits per session to determine the earliest occurrence of each target page, then retain only sessions where the input page visit strictly precedes the confirm page visit._

```sql
SELECT i.session_id
FROM (
    SELECT session_id, MIN(visit_timestamp) AS min_ts
    FROM target_page_visits
    WHERE page_path = '/search_input/'
    GROUP BY session_id
) i
JOIN (
    SELECT session_id, MIN(visit_timestamp) AS min_ts
    FROM target_page_visits
    WHERE page_path = '/search_list/'
    GROUP BY session_id
) c ON i.session_id = c.session_id
WHERE i.min_ts < c.min_ts
```

---
