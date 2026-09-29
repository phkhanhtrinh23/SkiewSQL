# Skill graph — `stacking` (9 skills)

**Skill `problems_rows_filtered_steps`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `row_id` |
| output columns | `problem`, `step`, `version`, `model`, `test_score`, `other_columns_optional` |
| source tables | `problem`, `model`, `model_score` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `problems_rows_flagged_stack_higher` |
| validated_on | — |
| counter_examples | 0 |

_All rows from the problems table restricted to step values 1, 2, or 3 (no other filtering)._

```sql
SELECT
  problem.name AS problem,
  model.step AS step,
  model.version AS version,
  model.L1_model AS model,
  ms.test_score AS test_score,
  NULL AS other_columns_optional,
  -- carry source primary keys for joinability
  problem.name AS source_problem_name,
  model.rowid AS model_rowid
FROM problem
LEFT JOIN model ON model.name = problem.name
LEFT JOIN model_score ms ON ms.name = problem.name AND ms.version = model.version AND ms.step = model.step
WHERE model.step IN (1,2,3)
```

---

**Skill `stack_max_nonstack_by_step_version`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `step`, `version` |
| output columns | `step`, `version`, `stack_test_score`, `max_nonstack_test_score` |
| source tables | `model_score` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `problems_rows_flagged_stack_higher` |
| validated_on | — |
| counter_examples | 0 |

_For each step and version, compute the test score of the 'Stack' model (if present) and the maximum test score among non-'Stack' models for that same step and version._

```sql
SELECT
  mr.step AS step,
  mr.version AS version,
  MAX(CASE WHEN mr.model = 'Stack' THEN mr.test_score END) AS stack_test_score,
  MAX(CASE WHEN mr.model != 'Stack' THEN mr.test_score END) AS max_nonstack_test_score
FROM model_score mr
GROUP BY mr.step, mr.version
```

---

**Skill `problems_rows_flagged_stack_higher`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `row_id` |
| output columns | `problem`, `step`, `version`, `model`, `test_score`, `stack_higher_flag` |
| source tables | `problems_rows_filtered_steps`, `stack_max_nonstack_by_step_version` |
| depends_on (builds on) | `problems_rows_filtered_steps`, `stack_max_nonstack_by_step_version` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Annotate each problems-row (from steps 1-3) with a boolean flag indicating whether for that row's step and version the 'Stack' test score is strictly greater than the max non-'Stack' test score._

```sql
SELECT
  prf.problem AS problem,
  prf.step AS step,
  prf.version AS version,
  prf.model AS model,
  prf.test_score AS test_score,
  (s.max_nonstack_test_score IS NULL AND s.stack_test_score IS NOT NULL)
    OR (s.stack_test_score IS NOT NULL AND s.stack_test_score > s.max_nonstack_test_score) AS stack_higher_flag
FROM
  problems_rows_filtered_steps prf
LEFT JOIN
  stack_max_nonstack_by_step_version s
ON
  prf.step = s.step
  AND prf.version = s.version
```

---

**Skill `model_step_rows`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `model_name`, `model_version`, `step`, `model_type` |
| output columns | `model_name`, `model_version`, `step`, `model_type`, `L1_model`, `test_score` |
| source tables | `model`, `model_score` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All raw rows for model evaluations at the step level, keeping model identity, version, step, model_type, L1_model and test_score. This is the base cohort of every evaluated model-step instance._

```sql
SELECT
  m.name AS model_name,
  m.version AS model_version,
  m.step AS step,
  ms.model AS model_type,
  m.L1_model AS L1_model,
  ms.test_score AS test_score,
  m.name AS __pk_model_name,
  m.version AS __pk_model_version,
  m.step AS __pk_model_step,
  ms.name AS __pk_score_name,
  ms.version AS __pk_score_version,
  ms.step AS __pk_score_step,
  ms.model AS __pk_score_model
FROM model m
JOIN model_score ms
  ON m.name = ms.name
  AND m.version = ms.version
  AND m.step = ms.step
```

---

**Skill `step_stack_vs_nonstack`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `name`, `version`, `step` |
| output columns | `model_name`, `model_version`, `step`, `stack_test_score`, `max_non_stack_test_score` |
| source tables | `model_score` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each model (name+version) and step, compute the Stack test_score and the max test_score among non-Stack models so we can determine per-step comparisons._

```sql
SELECT
  m.name   AS model_name,
  m.version AS model_version,
  m.step AS step,
  -- stack_test_score: test_score for rows where model = 'Stack'
  MAX(CASE WHEN m.model = 'Stack' THEN m.test_score END) AS stack_test_score,
  -- max_non_stack_test_score: max test_score among rows where model != 'Stack'
  MAX(CASE WHEN m.model != 'Stack' THEN m.test_score END) AS max_non_stack_test_score
FROM model_score AS m
GROUP BY
  m.name,
  m.version,
  m.step
```

---

**Skill `model_modal_l1_per_status`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `name`, `version`, `status` |
| output columns | `model_name`, `model_version`, `status`, `modal_L1_model` |
| source tables | `model` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each model (name+version) and for each status ('strong' and 'soft') it qualifies for, determine the single modal L1_model (the most-frequent L1_model among that model's rows). One row per model per status with the chosen L1_model._

```sql
SELECT
  m.name AS model_name,
  m.version AS model_version,
  s.status AS status,
  (
    SELECT L1_model
    FROM model AS m2
    WHERE m2.name = m.name
      AND m2.version = m.version
      AND (
        (s.status = 'strong' AND m2.step >= 2)
        OR
        (s.status = 'soft' AND m2.step < 2)
      )
    GROUP BY L1_model
    ORDER BY COUNT(*) DESC, L1_model ASC
    LIMIT 1
  ) AS modal_L1_model
FROM
  model AS m,
  (SELECT 'strong' AS status UNION ALL SELECT 'soft') AS s
GROUP BY
  m.name,
  m.version,
  s.status
```

---

**Skill `normalized_l1_model`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `row_id` |
| output columns | `row_id`, `L1_model_norm` |
| source tables | `model` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `l1_model_counts` |
| validated_on | — |
| counter_examples | 0 |

_Canonicalize / normalize the L1_model values (trim, NULL handling, consistent casing) so identical logical models are counted together; preserve one row per original row._

```sql
SELECT
  rowid AS row_id,
  CASE
    WHEN L1_model IS NULL THEN NULL
    ELSE lower(trim(L1_model))
  END AS L1_model_norm
FROM model
```

---

**Skill `l1_model_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `L1_model_norm` |
| output columns | `L1_model_norm`, `count` |
| source tables | `normalized_l1_model` |
| depends_on (builds on) | `normalized_l1_model` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregate the normalized rows to produce a count of rows per L1_model_norm across all steps and versions (each input row contributes one count)._

```sql
SELECT
  nlm.L1_model_norm AS L1_model_norm,
  COUNT(nlm.row_id) AS count
FROM
  normalized_l1_model nlm
GROUP BY
  nlm.L1_model_norm
```

---

**Skill `top_l1_model`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `L1_model` |
| output columns | `L1_model_norm`, `count`, `rank` |
| source tables | `model` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Rank or order the aggregated L1_model counts descending and select the top 1 L1_model_norm with its count._

```sql
SELECT
  m.L1_model AS L1_model_norm,
  COUNT(*) AS count,
  RANK() OVER (ORDER BY COUNT(*) DESC) AS rank
FROM model AS m
GROUP BY m.L1_model
```

---
