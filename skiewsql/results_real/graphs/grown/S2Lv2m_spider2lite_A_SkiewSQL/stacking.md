# Skill graph — `stacking` (2 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `problem`, `model_score`, `solution` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each problem, find problems where the count of all occurrences of that problem in the solution table across steps 1, 2, and 3 is less than the problem's total number of occurrences across th_

```sql
SELECT
  p.name AS problem,
  ms.name AS source_name,
  ms.version AS version,
  ms.step AS step,
  ms.model AS model,
  ms.test_score AS test_score,
  s.name AS solution_name
FROM
  problem p
JOIN
  model_score ms
  ON ms.name = p.name
LEFT JOIN
  solution s
  ON s.name = p.name AND s.version = ms.version
WHERE
  ms.step IN (1,2,3)
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `model`, `model_score` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: For each distinct L1_model, compute how many models (identified by their name and version) are most frequently associated with that L1_model among the models that have a 'strong' status and sepa_

```sql
SELECT
  m.name,
  m.version,
  m.step,
  m.L1_model,
  ms.model AS model_name,
  ms.train_score,
  ms.test_score
FROM model m
LEFT JOIN model_score ms
  ON ms.name = m.name
  AND ms.version = m.version
  AND ms.step = m.step
```

---
