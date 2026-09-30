# Skill graph — `stacking` (2 skills)

**Skill `problem_step_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `L1_model`, `step` |
| output columns | `problem`, `step`, `occurrence_count` |
| source tables | `model` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `qualifying_problems` |
| validated_on | — |
| counter_examples | 0 |

_aggregates the number of occurrences for each problem within each step, forming a cohort of problem-step pairs with their counts._

```sql
SELECT L1_model AS problem, step, COUNT(*) AS occurrence_count
FROM model
GROUP BY L1_model, step
```

---

**Skill `qualifying_problems`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `problem` |
| output columns | `problem` |
| source tables | `problem_step_counts`, `model_score` |
| depends_on (builds on) | `problem_step_counts` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_joins problem occurrence counts with step-version score validity flags, applies the occurrence threshold filter, and extracts the qualifying problem identifiers._

```sql
SELECT p.problem FROM problem_step_counts p JOIN model_score m ON p.problem = m.name AND p.step = m.step GROUP BY p.problem
```

---
