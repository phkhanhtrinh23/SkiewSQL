# Skill graph — `student_transcripts_tracking` (1 skills)

## Skill `department_program_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `department_name`, `department_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_d3ef4f074ea9c986 |
| output columns | `department_name`, `department_id` |
| source tables | `Departments`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

The view computes the count of degree programs associated with each department, based on the number of degree programs linked to each department in the Degree_Programs table.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{
  "description": "The view computes the count of degree programs associated with each department, based on the number of degree programs linked to each department in the Degree_Programs table.",
  "when_to_use": "Identifying the most popular departments based on the number of degree programs offered. | Understanding departmental specialization based on degree program enrollment.",
  "when_not_to_use": "Grain: Incorrect if analyzing departmental performance based on student enrollment, not just degree program count. Reuse would be wrong because the view only considers the number of degree programs, not the number of students enrolled in those programs. | Cohort/Filter:  The view doesn't allow for cohort or filter analysis.  Reuse would be wrong if you need to analyze departments based on specific student cohorts or demographic filters. | Aggregation: The aggregation is limited to counting degree programs per department. Reuse would be wrong if you need more complex aggregations (e.g., average degree program cost, distribution of degree types). | Join Path: The join path is fixed to `Departments.department_id = Degree_Programs.department_id`.  Reuse would be wrong if you need to analyze departments based on a different relationship between departments and degree programs. | Time Window: The view does not incorporate any time windowing. Reuse would be wrong if you need to analyze departmental performance over a specific time period."
}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "av_chunk",
    "subgoal": {
      "want_name": "chunk_view_0",
      "category": "SEL",
      "required_outputs": [],
      "required_grain": [],
      "required_filters": {},
      "text": "Task: Identify the department name and ID that has the highest number of degrees.\nRequired outputs: Department Name; Department ID\nFilters: The result should be the department with the maximum number of degrees.",
      "source_tables": [
        "Addresses",
        "Courses",
        "Degree_Programs",
        "Departments",
        "Sections",
        "Semesters",
        "Students"
      ],
      "depends_on": [],
      "join_keys": [],
      "relationship": "",
      "may_read_base_tables": true,
      "holistic": true,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Departments",
      "Degree_Programs"
    ],
    "table_fingerprints": {
      "departments": "188d438ee9ba34ad",
      "degree_programs": "85466a54c4a97bc7"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_516",
    "question": "What is the name and id of the department with the most number of degrees ?",
    "rewrite": "Task: Identify the department name and ID that has the highest number of degrees.\nRequired outputs: Department Name; Department ID\nFilters: The result should be the department with the maximum number of degrees.",
    "route": "av_nx1_graph",
    "model": "local-gemma3-4b",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T14:37:23+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T14:37:23+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "department_name",
      "department_id"
    ],
    "row_count": 1,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Departments.department_id=Degree_Programs.department_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  D."department_name",
  D."department_id"
FROM Departments AS D
JOIN Degree_Programs AS DP
  ON D."department_id" = DP."department_id"
GROUP BY
  D."department_name",
  D."department_id"
ORDER BY
  COUNT(DP."degree_program_id") DESC
LIMIT 1
```

---
