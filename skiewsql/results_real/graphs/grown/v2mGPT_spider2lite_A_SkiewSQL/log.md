# Skill graph — `log` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `form_log` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Count the number of distinct sessions that visited the /regist/input page and then later visited the /regist/confirm page in that order (input visit before confirm visit). Required outputs: coun_

```sql
SELECT
  session,
  stamp,
  path
FROM form_log
WHERE path IN ('/regist/input', '/regist/confirm')
```

---
