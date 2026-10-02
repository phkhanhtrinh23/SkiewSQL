# Skill graph — `log` (2 skills)

**Skill `target_page_visits`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `session_id`, `visit_id` |
| output columns | `session_id`, `page_step`, `visit_order`, `visit_id` |
| source tables | `form_log` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_extracts page visit events for the relevant registration steps, preserving session context and chronological or sequential order_

```sql
SELECT 
    session AS session_id,
    path AS page_step,
    rowid AS visit_id,
    ROW_NUMBER() OVER (PARTITION BY session ORDER BY stamp) AS visit_order
FROM form_log
```

---

**Skill `sessions_with_valid_precedence`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `session` |
| output columns | `session_id`, `has_valid_sequence` |
| source tables | `action_log` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_evaluates per-session visit order to flag sessions where the initial step chronologically precedes the final step_

```sql
SELECT session AS session_id, MIN(stamp) < MAX(stamp) AS has_valid_sequence FROM action_log GROUP BY session
```

---
