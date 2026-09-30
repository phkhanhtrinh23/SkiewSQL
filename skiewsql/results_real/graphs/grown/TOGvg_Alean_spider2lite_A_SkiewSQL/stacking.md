# Skill graph — `stacking` (2 skills)

**Skill `problem_occurrence_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `name` |
| output columns | `problem`, `occurrence_count` |
| source tables | `solution` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `filtered_problems` |
| validated_on | — |
| counter_examples | 0 |

_total occurrences per problem across the specified steps_

```sql
SELECT name AS problem, COUNT(*) AS occurrence_count
FROM solution
GROUP BY name
```

---

**Skill `filtered_problems`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `problem` |
| output columns | `problem` |
| source tables | `problem_occurrence_counts`, `model_score` |
| depends_on (builds on) | `problem_occurrence_counts` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_joins problem occurrence counts with step/version score comparisons, applies occurrence threshold and score condition filters, outputs problem_

```sql
SELECT DISTINCT poc.problem
FROM problem_occurrence_counts poc
JOIN model_score ms ON poc.problem = ms.name
```

---
