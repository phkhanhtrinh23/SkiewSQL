# Skill graph — `student_transcripts_tracking` (2 skills)

## Skill `department_degree_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `department_id`, `department_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_d3a26fca266af033 |
| output columns | `department_id`, `department_name`, `degree_count` |
| source tables | `Departments`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-department counts of degree programs (one row per department with department id, name, and the number of degrees offered)

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [],
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
    "question_id": "spider_dev_515",
    "question": "Which department offers the most number of degrees? List department name and id.",
    "rewrite": "Task: Find the department (name and id) that offers the highest number of degrees.\nRequired outputs: department name; department id\nFilters: Consider all departments present in the database; Count degrees offered by each department across all degree records; If multiple departments tie for the highest count, include all tied departments\nSort/limit: order by degree count descending; limit to the maximum count (no fixed numeric limit)",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:09:13+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T15:09:16+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "department_id",
      "department_name",
      "degree_count"
    ],
    "row_count": 15,
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
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (department_id, department_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT department_id, department_name, COUNT(*) AS cnt FROM department_degree_counts GROUP BY department_id, department_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "degree_count matches count of Degree_Programs per department (recomputed from base tables)",
        "sql": "SELECT COUNT(*) FROM department_degree_counts ddc LEFT JOIN (SELECT department_id AS dep_id, COUNT(degree_program_id) AS expected_count FROM Degree_Programs GROUP BY department_id) dp ON ddc.department_id = dp.dep_id WHERE COALESCE(dp.expected_count,0) <> COALESCE(ddc.degree_count,0)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL: department_id and department_name must be present for every row",
        "sql": "SELECT COUNT(*) FROM department_degree_counts WHERE department_id IS NULL OR department_name IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 1,
    "selected": 1,
    "included": 1,
    "referenced": 1,
    "executed": 1,
    "inconclusive": 1,
    "positive": 1,
    "positive_subgoals": [
      "Task: Count the number of distinct departments that offer degrees\nRequired outputs: a single integer value representing the count of different departments that offer degrees\nFilters: Consider only rows where a department is indicated as offering a degree (i.e., include each department that offers at least one degree)"
    ],
    "last_used": "spider_dev_518"
  }
}
```

### Validated on (1)

- How many different departments offer degrees?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT d.department_id, d.department_name, COUNT(dp.degree_program_id) AS degree_count FROM Departments d LEFT JOIN Degree_Programs dp ON d.department_id = dp.department_id GROUP BY d.department_id, d.department_name
```

---

## Skill `courses_with_section_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `course_id`, `course_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_e3d86f2764fa5e86 |
| output columns | `course_id`, `course_name`, `section_count` |
| source tables | `Courses`, `Sections` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each course, the course id and name together with the count of associated sections (0 if none); useful as a cohort or per-course measure for other queries.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Courses",
      "Sections"
    ],
    "table_fingerprints": {
      "courses": "53e9befe1413d87f",
      "sections": "33c74073d124c41c"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_526",
    "question": "What are the names and ids of every course with less than 2 sections?",
    "rewrite": "Task: Return every course's name and id for courses that have fewer than 2 sections.\nRequired outputs: course name; course id\nFilters: include only courses whose count of associated sections is less than 2 (i.e., 0 or 1 section)",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:10:49+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T15:10:52+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "course_id",
      "course_name",
      "section_count"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Courses.course_id=Sections.course_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows per grain (course_id, course_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT course_id, course_name, COUNT(*) AS cnt FROM courses_with_section_counts GROUP BY course_id, course_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every course in base table appears exactly once in the view",
        "sql": "SELECT COUNT(*) FROM Courses c LEFT JOIN (SELECT course_id AS v_course_id FROM courses_with_section_counts) v ON c.course_id = v.v_course_id WHERE v.v_course_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "section_count matches COUNT of Sections per course (including zero) recomputed from base tables",
        "sql": "SELECT COUNT(*) FROM courses_with_section_counts v LEFT JOIN (SELECT course_id, COUNT(section_id) AS real_count FROM Sections GROUP BY course_id) s ON v.course_id = s.course_id WHERE COALESCE(s.real_count, 0) != v.section_count",
        "result": "pass",
        "violations": 0
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
SELECT c.course_id, c.course_name, COUNT(s.section_id) AS section_count FROM Courses c LEFT JOIN Sections s ON c.course_id = s.course_id GROUP BY c.course_id, c.course_name
```

---
