# Skill graph — `student_transcripts_tracking` (33 skills)

## Skill `department_degree_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `department_id`, `department_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_f92e3b36084156b4 |
| output columns | `department_id`, `department_name`, `degree_program_count` |
| source tables | `Departments`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-department counts of degree programs (one row per department with department_id, department_name, and degree_program_count) for reuse in ranking or filtering departments by number of degrees.

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
    "rewrite": "Task: Find the department (its name and its id) that offers the largest number of degrees, i.e., the department with the maximum count of degrees associated with it.\nRequired outputs: department name; department id\nFilters: Consider only departments that are present in the database; count the number of degree records associated with each department and select the department(s) with the highest count. If multiple departments tie for the maximum count, include all of them.",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:48:11+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:48:14+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "department_id",
      "department_name",
      "degree_program_count"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Degree_Programs.department_id=Departments.department_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "View has exactly one row per department (no missing departments): counts departments present in Departments but absent from the view",
        "sql": "SELECT COUNT(*) FROM Departments d WHERE NOT EXISTS (SELECT 1 FROM department_degree_counts v WHERE v.department_id = d.department_id AND (v.department_name = d.department_name OR (v.department_name IS NULL AND d.department_name IS NULL)))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View has no duplicate rows for the declared grain (department_id, department_name) — i.e., duplicates in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT department_id, department_name, COUNT(*) AS cnt FROM department_degree_counts GROUP BY department_id, department_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "degree_program_count reconciles with base tables: counts where the stored degree_program_count does not equal the number of Degree_Programs linked to that department",
        "sql": "SELECT COUNT(*) FROM department_degree_counts v LEFT JOIN (SELECT department_id, COUNT(*) AS expected_count FROM Degree_Programs GROUP BY department_id) dp ON dp.department_id = v.department_id WHERE COALESCE(v.degree_program_count, -9223372036854775808) <> COALESCE(dp.expected_count, 0)",
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
SELECT d.department_id, d.department_name, COUNT(dp.degree_program_id) AS degree_program_count
FROM Departments d
LEFT JOIN Degree_Programs dp ON dp.department_id = d.department_id
GROUP BY d.department_id, d.department_name
```

---

## Skill `department_degree_counts_1`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `department_id`, `department_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_2c243f6d05e2e8e7 |
| output columns | `department_id`, `department_name`, `degree_count` |
| source tables | `Departments`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-department counts of associated degree programs (one row per department with department_id, department_name, and degree_count) useful for comparing or filtering departments by number of degrees

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
    "question_id": "spider_dev_516",
    "question": "What is the name and id of the department with the most number of degrees ?",
    "rewrite": "Task: Find the department that has the largest number of degrees and return that department's name and id.\nRequired outputs: department name; department id\nFilters: consider all departments and count how many degree records are associated with each department; if multiple departments tie for the maximum number of degrees, return all such departments\nSort/limit: order by count of degrees descending; no explicit limit (return all departments tied for the maximum)",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:48:21+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:48:24+00:00",
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
        "join": "Degree_Programs.department_id=Departments.department_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows per declared grain (department_id, department_name)",
        "sql": "SELECT COUNT(*) FROM (\n  SELECT department_id, department_name, COUNT(*) AS c FROM department_degree_counts_1\n  GROUP BY department_id, department_name\n  HAVING c > 1\n) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "degree_count matches count of Degree_Programs per department (including zero) — detects incorrect aggregation or join issues",
        "sql": "SELECT COUNT(*) FROM department_degree_counts_1 v\nLEFT JOIN Departments d ON d.department_id = v.department_id\nLEFT JOIN (\n  SELECT department_id, COUNT(degree_program_id) AS actual_count FROM Degree_Programs GROUP BY department_id\n) dp ON dp.department_id = v.department_id\nWHERE (\n  (COALESCE(dp.actual_count, 0) IS NULL AND v.degree_count IS NOT NULL) OR\n  (COALESCE(dp.actual_count, 0) IS NOT NULL AND v.degree_count IS NULL) OR\n  (COALESCE(dp.actual_count, 0) <> COALESCE(v.degree_count, 0))\n)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL for the grain columns (department_id, department_name)",
        "sql": "SELECT COUNT(*) FROM department_degree_counts_1 WHERE department_id IS NULL OR department_name IS NULL",
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
SELECT d.department_id, d.department_name, COUNT(dp.degree_program_id) AS degree_count
FROM Departments d
LEFT JOIN Degree_Programs dp ON dp.department_id = d.department_id
GROUP BY d.department_id, d.department_name
```

---

## Skill `departments_with_degrees`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `department_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_6b84e36874e992a4 |
| output columns | `department_id` |
| source tables | `Departments`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

All departments that are associated with one or more degree program records (one row per department), retaining keys needed to join to departments or degree programs.

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
    "grain_basis": "distinct",
    "lineage": [
      "Departments",
      "Degree_Programs"
    ],
    "table_fingerprints": {
      "departments": "188d438ee9ba34ad",
      "degree_programs": "85466a54c4a97bc7"
    },
    "data_fingerprints": {
      "departments": "15:15",
      "degree_programs": "15:15"
    },
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_517",
    "question": "How many departments offer any degree?",
    "rewrite": "Task: Count how many distinct departments offer any degree\nRequired outputs: a single numeric value representing the number of departments that offer at least one degree\nFilters: include only departments that are associated with one or more degree records (i.e., departments that offer any degree)",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:48:31+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:48:33+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "department_id"
    ],
    "row_count": 10,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Degree_Programs.department_id=Departments.department_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate department_id rows in the view (grain uniqueness)",
        "sql": "SELECT COUNT(*) FROM (SELECT department_id, COUNT(*) AS cnt FROM departments_with_degrees GROUP BY department_id HAVING cnt > 1) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view corresponds to an existing Departments row (no dangling department_id)",
        "sql": "SELECT COUNT(*) FROM departments_with_degrees v WHERE NOT EXISTS (SELECT 1 FROM Departments d WHERE d.department_id = v.department_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every department_id in the view has at least one matching Degree_Programs row (the join condition is preserved)",
        "sql": "SELECT COUNT(*) FROM departments_with_degrees v WHERE NOT EXISTS (SELECT 1 FROM Degree_Programs dp WHERE dp.department_id = v.department_id)",
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
SELECT DISTINCT d.department_id
FROM Departments d
JOIN Degree_Programs dp ON dp.department_id = d.department_id
```

---

## Skill `departments_offering_degrees`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `department_id`, `department_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_d6b641c048b12d2e |
| output columns | `department_id`, `department_name` |
| source tables | `Departments`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Relation listing departments that are associated with at least one degree program (one row per department), useful as a general cohort of departments that offer degrees.

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
    "grain_basis": "distinct",
    "lineage": [
      "Departments",
      "Degree_Programs"
    ],
    "table_fingerprints": {
      "departments": "188d438ee9ba34ad",
      "degree_programs": "85466a54c4a97bc7"
    },
    "data_fingerprints": {
      "departments": "15:15",
      "degree_programs": "15:15"
    },
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_518",
    "question": "How many different departments offer degrees?",
    "rewrite": "Task: Count the number of distinct departments that offer degrees.\nRequired outputs: count_of_departments: integer representing the number of unique departments that offer degrees\nFilters: Consider only rows where a department is associated with offering a degree (i.e., exclude null/empty department identifiers or entries that do not indicate an offered degree). Treat departments with distinct identifiers/names as different departments.",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:48:39+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:48:41+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "department_id",
      "department_name"
    ],
    "row_count": 10,
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
        "sql": "SELECT COUNT(*) FROM (SELECT department_id, department_name, COUNT(*) AS cnt FROM departments_offering_degrees GROUP BY department_id, department_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view has a non-NULL department_id (as enforced by view WHERE clause)",
        "sql": "SELECT COUNT(*) FROM departments_offering_degrees WHERE department_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view corresponds to at least one Degree_Programs row (join did not create phantom rows)",
        "sql": "SELECT COUNT(*) FROM departments_offering_degrees d WHERE NOT EXISTS (SELECT 1 FROM Degree_Programs dp WHERE dp.department_id = d.department_id)",
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
SELECT DISTINCT d.department_id, d.department_name
FROM Departments d
JOIN Degree_Programs dp ON d.department_id = dp.department_id
WHERE d.department_id IS NOT NULL
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

Per-course counts of associated sections (includes courses with zero sections), useful for filtering or reporting courses by number of sections.

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
    "question_id": "spider_dev_525",
    "question": "What are the names and id of courses having at most 2 sections?",
    "rewrite": "Task: Return the name(s) and id(s) of courses that have at most 2 sections.\nRequired outputs: course name; course id\nFilters: Include only courses where the count of associated sections is less than or equal to 2; Treat courses with zero sections as satisfying 'at most 2 sections'",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:49:24+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:49:27+00:00",
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
        "purpose": "No duplicate rows at the declared grain (course_id, course_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT course_id, course_name, COUNT(*) AS cnt FROM courses_with_section_counts GROUP BY course_id, course_name HAVING cnt > 1) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each row's section_count matches count of Sections in base tables for that course_id (reconciles the aggregate)",
        "sql": "SELECT COUNT(*) FROM (SELECT v.course_id FROM courses_with_section_counts v LEFT JOIN (SELECT course_id, COUNT(section_id) AS expected_count FROM Sections GROUP BY course_id) b ON v.course_id = b.course_id WHERE COALESCE(b.expected_count,0) != v.section_count) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL (course_id and course_name must be present)",
        "sql": "SELECT COUNT(*) FROM courses_with_section_counts WHERE course_id IS NULL OR course_name IS NULL",
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
SELECT c.course_id, c.course_name, COUNT(s.section_id) AS section_count
FROM Courses c
LEFT JOIN Sections s ON c.course_id = s.course_id
GROUP BY c.course_id, c.course_name
```

---

## Skill `semester_registration_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `semester_id`, `semester_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_4c3e653ce2d2cd40 |
| output columns | `semester_id`, `semester_name`, `registration_count` |
| source tables | `Semesters`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-semester counts of student registrations (one row per semester with its id, name, and total number of student_enrolment records).

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
      "Semesters",
      "Student_Enrolment"
    ],
    "table_fingerprints": {
      "semesters": "29c2494a0d4e0c8e",
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_529",
    "question": "What is the semester which most student registered in? Show both the name and the id.",
    "rewrite": "Task: Find the semester (both its name and its id) that has the largest number of student registrations.\nRequired outputs: semester id; semester name; count of student registrations (optional)\nFilters: consider all registration records for all students; count registrations per semester and select the semester with the maximum count\nSort/limit: order by registration count descending, limit 1",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:49:51+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:49:54+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "semester_id",
      "semester_name",
      "registration_count"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Semesters.semester_id=Student_Enrolment.semester_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (semester_id, semester_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT semester_id, semester_name, COUNT(*) AS cnt FROM semester_registration_counts GROUP BY semester_id, semester_name HAVING cnt > 1) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "registration_count reconciles with COUNT of Student_Enrolment rows per semester (mismatched counts)",
        "sql": "SELECT COUNT(*) FROM semester_registration_counts v LEFT JOIN Semesters s ON v.semester_id = s.semester_id AND v.semester_name = s.semester_name WHERE v.registration_count != (SELECT COUNT(*) FROM Student_Enrolment se WHERE se.semester_id = v.semester_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL (semester_id or semester_name should never be NULL)",
        "sql": "SELECT COUNT(*) FROM semester_registration_counts WHERE semester_id IS NULL OR semester_name IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "included": 1,
    "referenced": 1,
    "executed": 1,
    "negative": 1,
    "last_used": "spider_dev_530"
  }
}
```

### Validated on (0)

—

### Counter-examples (1)

- For each semester, what is the name and id of the one with the most students registered?

### Executable SQL body

```sql
SELECT s.semester_id,
       s.semester_name,
       COUNT(se.student_enrolment_id) AS registration_count
FROM Semesters s
LEFT JOIN Student_Enrolment se ON s.semester_id = se.semester_id
GROUP BY s.semester_id, s.semester_name
```

---

## Skill `semester_entry_registered_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `semester_id`, `semester_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_0695a75ede8d28b0 |
| output columns | `entry_id`, `semester_id`, `semester_name`, `registered_count` |
| source tables | `Semesters`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-semester, per-semester-entry counts of student enrollments (one row per semester entry with semester entry id, semester id, semester name, and number of student_enrolment records for that entry).

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
      "Semesters",
      "Student_Enrolment"
    ],
    "table_fingerprints": {
      "semesters": "29c2494a0d4e0c8e",
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_530",
    "question": "For each semester, what is the name and id of the one with the most students registered?",
    "rewrite": "Task: For each semester, find the single semester entry that has the largest number of students registered and return that semester's name and id.\nRequired outputs: semester name; semester id\nFilters: Consider each semester separately (group by semester). For each semester, include only the row(s) corresponding to the maximum number of students registered in that semester. If multiple entries within the same semester are tied for the maximum number of students registered, include the one with the highest id? (If tie-breaking is not required, include all tied entries.)",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:50:26+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:50:28+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "entry_id",
      "semester_id",
      "semester_name",
      "registered_count"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Semesters.semester_id=Student_Enrolment.semester_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "View has one row per semester (no duplicate semester_id, semester_name pairs)",
        "sql": "SELECT COUNT(*) FROM (SELECT semester_id, semester_name, COUNT(*) AS cnt FROM semester_entry_registered_counts GROUP BY semester_id, semester_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "registered_count matches count of Student_Enrolment rows per semester in the base tables",
        "sql": "SELECT COUNT(*) FROM semester_entry_registered_counts v LEFT JOIN (SELECT semester_id, COUNT(student_enrolment_id) AS expected_count FROM Student_Enrolment GROUP BY semester_id) b ON v.semester_id = b.semester_id WHERE COALESCE(b.expected_count,0) != v.registered_count",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Key columns semester_id and semester_name are not NULL in the view",
        "sql": "SELECT COUNT(*) FROM semester_entry_registered_counts WHERE semester_id IS NULL OR semester_name IS NULL",
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
SELECT
  Semesters.semester_id AS entry_id,
  Semesters.semester_id AS semester_id,
  Semesters.semester_name AS semester_name,
  COALESCE(COUNT(se.student_enrolment_id), 0) AS registered_count
FROM Semesters
LEFT JOIN Student_Enrolment se ON Semesters.semester_id = se.semester_id
GROUP BY Semesters.semester_id, Semesters.semester_name
```

---

## Skill `student_semester_degree_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `student_id`, `semester_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_4fc0f415a284e588 |
| output columns | `student_id`, `semester_id`, `distinct_degree_program_count` |
| source tables | `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per student per semester counts of distinct degree programs the student is enrolled in (one row per student and semester)

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
      "Student_Enrolment"
    ],
    "table_fingerprints": {
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_533",
    "question": "Who are enrolled in 2 degree programs in one semester? List the first name, middle name and last name and the id.",
    "rewrite": "Task: Find all students who are enrolled in exactly two degree programs within a single semester; return for each such student their first name, middle name, last name, and id.\nRequired outputs: first name; middle name; last name; id\nFilters: Group enrollments by student and by semester (a semester defined by whatever semester identifier exists in the schema).; Select students whose count of distinct degree programs enrolled in for the same semester equals 2.; Include only enrollments within a single semester for each returned row (the two-degree condition must hold within the same semester).; Exclude students who have fewer than 2 or more than 2 distinct degree programs in any given semester.",
    "route": "av_nx1_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:50:52+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:50:56+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "semester_id",
      "distinct_degree_program_count"
    ],
    "row_count": 14,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View grain uniqueness: no duplicate rows per (student_id, semester_id)",
        "sql": "SELECT COUNT(*) FROM (\n  SELECT student_id, semester_id, COUNT(*) AS cnt\n  FROM student_semester_degree_counts\n  GROUP BY student_id, semester_id\n  HAVING cnt <> 1\n) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Measures reconcile: distinct_degree_program_count equals count of distinct degree_program_id in base table",
        "sql": "SELECT COUNT(*) FROM (\n  SELECT v.student_id, v.semester_id\n  FROM student_semester_degree_counts v\n  LEFT JOIN (\n    SELECT se.student_id, se.semester_id, COUNT(DISTINCT se.degree_program_id) AS expected_count\n    FROM Student_Enrolment se\n    GROUP BY se.student_id, se.semester_id\n  ) b ON v.student_id = b.student_id AND v.semester_id = b.semester_id\n  WHERE (b.expected_count IS NULL AND v.distinct_degree_program_count IS NOT NULL)\n     OR (b.expected_count IS NOT NULL AND v.distinct_degree_program_count <> b.expected_count)\n) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All key columns are NOT NULL in the view (student_id and semester_id must be present)",
        "sql": "SELECT COUNT(*) FROM student_semester_degree_counts WHERE student_id IS NULL OR semester_id IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 1
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT se.student_id AS student_id, se.semester_id AS semester_id, COUNT(DISTINCT se.degree_program_id) AS distinct_degree_program_count
FROM Student_Enrolment se
GROUP BY se.student_id, se.semester_id
```

---

## Skill `students_enrolled_in_program`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `student_enrolment_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_80047ebe07f2ccfb |
| output columns | `student_id`, `first_name`, `middle_name`, `last_name`, `student_enrolment_id`, `degree_program_id`, `degree_summary_name` |
| source tables | `Students`, `Student_Enrolment`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

One row per student enrollment linking student to their degree program (keeps student identifiers and program identifiers to find students by program level)

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
    "removed_constants": [
      "'Bachelors'"
    ],
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "Students",
      "Student_Enrolment",
      "Degree_Programs"
    ],
    "table_fingerprints": {
      "students": "ad3aee5be9cacc55",
      "student_enrolment": "445257138d420d03",
      "degree_programs": "85466a54c4a97bc7"
    },
    "data_fingerprints": {
      "students": "15:15",
      "student_enrolment": "15:15",
      "degree_programs": "15:15"
    },
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_536",
    "question": "What are the first, middle, and last names for everybody enrolled in a Bachelors program?",
    "rewrite": "Task: Retrieve the first, middle, and last names of every person who is enrolled in a Bachelors program.\nRequired outputs: first name (string); middle name (string or null if none); last name (string)\nFilters: enrollment program level equals 'Bachelors' (only include rows for people currently enrolled in a Bachelors program)",
    "route": "av_nx1_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:51:41+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:51:45+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "first_name",
      "middle_name",
      "last_name",
      "student_enrolment_id",
      "degree_program_id",
      "degree_summary_name"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Student_Enrolment.student_id=Students.student_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      },
      {
        "join": "Degree_Programs.degree_program_id=Student_Enrolment.degree_program_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain student_enrolment_id (each student_enrolment_id should appear at most once)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_enrolment_id FROM students_enrolled_in_program GROUP BY student_enrolment_id HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view must reference an existing base Student_Enrolment row (no enrolment ids in the view that don't exist in Student_Enrolment)",
        "sql": "SELECT COUNT(*) FROM students_enrolled_in_program v LEFT JOIN Student_Enrolment se ON v.student_enrolment_id = se.student_enrolment_id WHERE se.student_enrolment_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "degree_program_id in the view must match the degree_program_id from Student_Enrolment for the same student_enrolment_id (measure reconciliation of the join key)",
        "sql": "SELECT COUNT(*) FROM students_enrolled_in_program v JOIN Student_Enrolment se ON v.student_enrolment_id = se.student_enrolment_id WHERE (v.degree_program_id IS NOT se.degree_program_id) AND NOT (v.degree_program_id IS NULL AND se.degree_program_id IS NULL)",
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
SELECT s.student_id, s.first_name, s.middle_name, s.last_name, se.student_enrolment_id, se.degree_program_id, dp.degree_summary_name FROM Students s JOIN Student_Enrolment se ON se.student_id = s.student_id JOIN Degree_Programs dp ON dp.degree_program_id = se.degree_program_id
```

---

## Skill `degree_program_enrolment_counts_by_kind`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `program_kind` (keyed) |
| status / version | active / v1 |
| skill id | sk_09c125cd04b44551 |
| output columns | `program_kind`, `total_students` |
| source tables | `Degree_Programs`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Total student enrolment counts aggregated per program kind (degree_summary_name) by joining Degree_Programs to Student_Enrolment

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
      "Degree_Programs",
      "Student_Enrolment"
    ],
    "table_fingerprints": {
      "degree_programs": "85466a54c4a97bc7",
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_537",
    "question": "Find the kind of program which most number of students are enrolled in?",
    "rewrite": "Task: Return the program kind that has the largest total number of student enrollments.\nRequired outputs: program kind (the categorical name of the kind of program); total number of students enrolled in that program kind\nFilters: consider all student enrollments present in the data (no additional filters unless specified elsewhere)\nSort/limit: order by total number of students enrolled descending, limit 1",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:51:51+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:51:54+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "program_kind",
      "total_students"
    ],
    "row_count": 2,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Student_Enrolment.degree_program_id=Degree_Programs.degree_program_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the view grain (program_kind) — there should be at most one row per program_kind",
        "sql": "SELECT COUNT(*) FROM (SELECT program_kind, COUNT(*) AS cnt FROM degree_program_enrolment_counts_by_kind GROUP BY program_kind HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every total_students equals the count of Student_Enrolment rows for that program_kind computed from the base tables (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM degree_program_enrolment_counts_by_kind v LEFT JOIN (SELECT dp.degree_summary_name AS program_kind, COUNT(se.student_enrolment_id) AS expected_total FROM Degree_Programs dp JOIN Student_Enrolment se ON se.degree_program_id = dp.degree_program_id GROUP BY dp.degree_summary_name) b ON v.program_kind = b.program_kind WHERE (b.expected_total IS NULL AND v.total_students IS NOT NULL) OR (b.expected_total IS NOT NULL AND v.total_students != b.expected_total)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys (program_kind) are not NULL in the view",
        "sql": "SELECT COUNT(*) FROM degree_program_enrolment_counts_by_kind WHERE program_kind IS NULL",
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
SELECT dp.degree_summary_name AS program_kind, COUNT(se.student_enrolment_id) AS total_students FROM Degree_Programs dp JOIN Student_Enrolment se ON se.degree_program_id = dp.degree_program_id GROUP BY dp.degree_summary_name
```

---

## Skill `degree_program_enrollment_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `degree_program_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_d5c0ec41dc151d30 |
| output columns | `degree_program_id`, `student_count` |
| source tables | `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-degree-program counts of currently enrolled students (for programs where degree_program_id is known), useful to rank or filter programs by enrollment.

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
      "Student_Enrolment"
    ],
    "table_fingerprints": {
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_540",
    "question": "What is the program id and the summary of the degree that has the most students enrolled?",
    "rewrite": "Task: Find the program id and the summary of the degree for the single degree program that currently has the largest number of students enrolled.\nRequired outputs: program id (the identifier of the degree program); summary of the degree (text describing the degree)\nFilters: Consider only degree programs for which a numeric count of currently enrolled students can be determined.; Select the degree program with the maximum number of enrolled students; if multiple programs tie for the maximum, return the program id and summary for each tied program.\nSort/limit: order by student count descending, limit to the top row(s) corresponding to the maximum count (i.e., return only the program(s) with the highest enrollment)",
    "route": "av_nx1_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:52:27+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:52:30+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "degree_program_id",
      "student_count"
    ],
    "row_count": 9,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate degree_program_id rows in the view (view should be keyed by degree_program_id).",
        "sql": "SELECT COUNT(*) FROM degree_program_enrollment_counts t1 WHERE (SELECT COUNT(*) FROM degree_program_enrollment_counts t2 WHERE t2.degree_program_id = t1.degree_program_id) > 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows in the view have non-NULL degree_program_id (intrinsic filter WHERE degree_program_id IS NOT NULL).",
        "sql": "SELECT COUNT(*) FROM degree_program_enrollment_counts WHERE degree_program_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count matches the count of Student_Enrolment rows per degree_program_id (reconciles measure with base table).",
        "sql": "SELECT COUNT(*) FROM degree_program_enrollment_counts v LEFT JOIN (SELECT degree_program_id, COUNT(*) AS expected_count FROM Student_Enrolment WHERE degree_program_id IS NOT NULL GROUP BY degree_program_id) b ON v.degree_program_id = b.degree_program_id WHERE b.expected_count IS NULL OR v.student_count <> b.expected_count",
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
SELECT degree_program_id, COUNT(*) AS student_count
FROM Student_Enrolment
WHERE degree_program_id IS NOT NULL
GROUP BY degree_program_id
```

---

## Skill `student_enrollment_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `student_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_0a711fc71305cce0 |
| output columns | `student_id`, `enrol_count` |
| source tables | `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-student total count of enrollment records across all programs (one row per student with their student_id and enrollment count).

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
      "Student_Enrolment"
    ],
    "table_fingerprints": {
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_541",
    "question": "Which student has enrolled for the most times in any program? List the id, first name, middle name, last name, the number of enrollments and student id.",
    "rewrite": "Task: Find the student (or students, in case of a tie) who has the highest number of enrollments across all programs, and return that student's identifying information along with the count of their enrollments.\nRequired outputs: id (the student's id as given in the question); first name; middle name; last name; the number of enrollments (an integer count of how many times that student has enrolled in any program); student id (a repeat of the student's id as requested in the question)\nFilters: Consider all enrollment records for all students and all programs (no date or program-type restriction).; Count each enrollment record per student; use that count to determine the maximum number of enrollments.; Return only student(s) whose enrollment count equals the maximum count found (include ties).\nSort/limit: order by the number of enrollments descending; if multiple students tie for the maximum, include them all (no row limit).",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:52:39+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:52:41+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "enrol_count"
    ],
    "row_count": 8,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate student_id rows (view grain violated)",
        "sql": "SELECT COUNT(*) FROM (\n  SELECT student_id FROM student_enrollment_counts\n  GROUP BY student_id\n  HAVING COUNT(*) > 1\n) as t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "enrol_count matches count of Student_Enrolment rows per student_id",
        "sql": "SELECT COUNT(*) FROM student_enrollment_counts sec\nWHERE sec.enrol_count != (\n  SELECT COUNT(*) FROM Student_Enrolment se\n  WHERE se.student_id = sec.student_id\n)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No NULL student_id in the view (key presence)",
        "sql": "SELECT COUNT(*) FROM student_enrollment_counts WHERE student_id IS NULL",
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
SELECT student_id, COUNT(*) AS enrol_count FROM Student_Enrolment GROUP BY student_id
```

---

## Skill `student_enrollment_counts_12`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `student_id`, `first_name`, `middle_name`, `last_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_119f5d170befd220 |
| output columns | `student_id`, `first_name`, `middle_name`, `last_name`, `num_enrollments` |
| source tables | `Students`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-student total count of enrollment records, including student identifiers and names for joining or reporting.

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
      "Students",
      "Student_Enrolment"
    ],
    "table_fingerprints": {
      "students": "ad3aee5be9cacc55",
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_542",
    "question": "What is the first, middle, and last name, along with the id and number of enrollments, for the student who enrolled the most in any program?",
    "rewrite": "Task: Find the student who has the largest number of enrollments in any program and return that student's first name, middle name, last name, id, and the number of enrollments.\nRequired outputs: first name; middle name; last name; id; number of enrollments\nFilters: Consider each student's total number of enrollments across programs; select the student with the maximum total enrollments (if there are ties, return all students who share the maximum).; Only include rows for actual students present in the data (no null or missing id).\nSort/limit: order by number of enrollments descending; limit to the top value (if ties, include all rows with that top value)",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:52:50+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:52:53+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "first_name",
      "middle_name",
      "last_name",
      "num_enrollments"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Students.student_id=Student_Enrolment.student_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (student_id, first_name, middle_name, last_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id, first_name, middle_name, last_name, COUNT(*) as c FROM student_enrollment_counts_12 GROUP BY student_id, first_name, middle_name, last_name HAVING c > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "num_enrollments equals the count of Student_Enrolment rows per student (recomputed from base tables)",
        "sql": "SELECT COUNT(*) FROM student_enrollment_counts_12 v LEFT JOIN (SELECT student_id, COUNT(student_enrolment_id) AS expected_cnt FROM Student_Enrolment GROUP BY student_id) b ON v.student_id = b.student_id WHERE COALESCE(b.expected_cnt,0) != v.num_enrollments",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys required by the grain are not NULL",
        "sql": "SELECT COUNT(*) FROM student_enrollment_counts_12 WHERE student_id IS NULL OR first_name IS NULL OR middle_name IS NULL OR last_name IS NULL",
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
SELECT s.student_id, s.first_name, s.middle_name, s.last_name, COUNT(se.student_enrolment_id) AS num_enrollments FROM Students s LEFT JOIN Student_Enrolment se ON s.student_id = se.student_id WHERE s.student_id IS NOT NULL GROUP BY s.student_id, s.first_name, s.middle_name, s.last_name
```

---

## Skill `semesters_with_no_enrollments`

Category: `SET`

| field | value |
|---|---|
| grain (one row per) | `semester_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_9f5db7f48eab6989 |
| output columns | `semester_id`, `semester_name` |
| source tables | `Semesters`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

All semesters that currently have no student enrollment records (semesters with zero linked enrollments).

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
    "grain_basis": "verified_unique",
    "lineage": [
      "Semesters",
      "Student_Enrolment"
    ],
    "table_fingerprints": {
      "semesters": "29c2494a0d4e0c8e",
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {
      "semesters": "15:15",
      "student_enrolment": "15:15"
    },
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_543",
    "question": "Which semesters do not have any student enrolled? List the semester name.",
    "rewrite": "Task: Find all semesters that have zero students enrolled and return their semester names.\nRequired outputs: semester name\nFilters: Include only semesters for which there exists no enrollment record linking any student to that semester (i.e., semesters with count(enrolled students)=0). Treat semester name exactly as stored in the semesters/terms table.; Do not include semesters that have at least one associated student enrollment record.",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:53:00+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:53:02+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "semester_id",
      "semester_name"
    ],
    "row_count": 6,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Semesters.semester_id=Student_Enrolment.semester_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate semester_id in the view (grain uniqueness)",
        "sql": "SELECT COUNT(*) FROM (SELECT semester_id FROM semesters_with_no_enrollments) v GROUP BY semester_id HAVING COUNT(*) > 1 LIMIT 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view refers to an existing Semesters row (no dangling FK) and semester_id is not NULL",
        "sql": "SELECT COUNT(*) FROM semesters_with_no_enrollments v LEFT JOIN Semesters s ON v.semester_id = s.semester_id WHERE v.semester_id IS NULL OR s.semester_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each semester in the view truly has zero linked Student_Enrolment rows",
        "sql": "SELECT COUNT(*) FROM semesters_with_no_enrollments v JOIN Student_Enrolment e ON v.semester_id = e.semester_id",
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
SELECT s.semester_id, s.semester_name
FROM Semesters s
LEFT JOIN Student_Enrolment e ON s.semester_id = e.semester_id
WHERE e.student_enrolment_id IS NULL
```

---

## Skill `semesters_with_enrollment_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `semester_id`, `semester_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_b7d5064b7b426407 |
| output columns | `semester_id`, `semester_name`, `enrollment_count` |
| source tables | `Semesters`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-semester counts of student enrollments (one row per semester with its id, name, and number of linked enrollments) useful for finding semesters with zero or low enrollment.

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
      "Semesters",
      "Student_Enrolment"
    ],
    "table_fingerprints": {
      "semesters": "29c2494a0d4e0c8e",
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_544",
    "question": "What is the name of the semester with no students enrolled?",
    "rewrite": "Task: Find the name of the semester that has no students enrolled.\nRequired outputs: semester name\nFilters: semester must have zero students enrolled (i.e., no enrollment records linking any student to that semester)",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:53:09+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:53:12+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "semester_id",
      "semester_name",
      "enrollment_count"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Semesters.semester_id=Student_Enrolment.semester_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (semester_id, semester_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT semester_id, semester_name, COUNT(*) AS cnt FROM semesters_with_enrollment_counts GROUP BY semester_id, semester_name HAVING cnt > 1) t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "enrollment_count matches COUNT of Student_Enrolment rows per semester (detects incorrect aggregation or join issues)",
        "sql": "SELECT COUNT(*) FROM semesters_with_enrollment_counts v LEFT JOIN (SELECT semester_id AS s_id, COUNT(student_enrolment_id) AS actual_count FROM Student_Enrolment GROUP BY semester_id) b ON v.semester_id = b.s_id WHERE (b.actual_count IS NULL AND v.enrollment_count != 0) OR (b.actual_count IS NOT NULL AND v.enrollment_count != b.actual_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL (semester_id and semester_name must be present for each row)",
        "sql": "SELECT COUNT(*) FROM semesters_with_enrollment_counts WHERE semester_id IS NULL OR semester_name IS NULL",
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
SELECT s.semester_id, s.semester_name, COUNT(e.student_enrolment_id) AS enrollment_count
FROM Semesters s
LEFT JOIN Student_Enrolment e ON s.semester_id = e.semester_id
GROUP BY s.semester_id, s.semester_name
```

---

## Skill `courses_with_any_enrollment`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `course_id`, `course_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_d622f10a1e272e1f |
| output columns | `course_id`, `course_name` |
| source tables | `Courses`, `Student_Enrolment_Courses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

All courses that have at least one student enrollment (a denormalized relation listing courses that are linked to enrollment records).

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
    "grain_basis": "distinct",
    "lineage": [
      "Courses",
      "Student_Enrolment_Courses"
    ],
    "table_fingerprints": {
      "courses": "53e9befe1413d87f",
      "student_enrolment_courses": "daf1efe3c261d034"
    },
    "data_fingerprints": {
      "courses": "15:15",
      "student_enrolment_courses": "15:83814225"
    },
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_545",
    "question": "What are all the course names of the courses which ever have students enrolled in?",
    "rewrite": "Task: Return the names of every course that has had at least one student enrolled at any time.\nRequired outputs: course name (the name/title of the course)\nFilters: Include only courses for which there exists at least one enrollment/registration record linking a student to that course (i.e., courses that have ever had one or more students enrolled).; Exclude courses with zero enrollments (no students ever enrolled).",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:53:21+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:53:24+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "course_id",
      "course_name"
    ],
    "row_count": 10,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Courses.course_id=Student_Enrolment_Courses.course_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "View contains only courses that actually have at least one enrollment (no false positives)",
        "sql": "SELECT COUNT(*) FROM courses_with_any_enrollment v LEFT JOIN Student_Enrolment_Courses sec ON v.course_id = sec.course_id WHERE sec.student_course_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No duplicate rows in the view at the declared grain (course_id, course_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT course_id, course_name, COUNT(*) AS cnt FROM courses_with_any_enrollment GROUP BY course_id, course_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view has non-NULL key course_id",
        "sql": "SELECT COUNT(*) FROM courses_with_any_enrollment WHERE course_id IS NULL",
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
SELECT DISTINCT c.course_id, c.course_name
FROM Courses c
JOIN Student_Enrolment_Courses sec ON c.course_id = sec.course_id
```

---

## Skill `course_enrollment_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `course_id`, `course_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_0ce80116272e5c0e |
| output columns | `course_id`, `course_name`, `enrollment_count` |
| source tables | `Courses`, `Student_Enrolment_Courses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-course enrollment counts (one row per course with its id, name, and number of enrollments across the enrollments table).

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
      "Student_Enrolment_Courses"
    ],
    "table_fingerprints": {
      "courses": "53e9befe1413d87f",
      "student_enrolment_courses": "daf1efe3c261d034"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_547",
    "question": "What's the name of the course with most number of enrollments?",
    "rewrite": "Task: Find the course name(s) of the course or courses that have the highest number of enrollments.\nRequired outputs: course name\nFilters: Consider all courses; count enrollments per course across the entire enrollments dataset; include course(s) whose enrollment count equals the maximum enrollment count among all courses.",
    "route": "av_nx1_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:53:45+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:53:48+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "course_id",
      "course_name",
      "enrollment_count"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Student_Enrolment_Courses.course_id=Courses.course_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (course_id, course_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT course_id, course_name, COUNT(*) AS cnt FROM course_enrollment_counts GROUP BY course_id, course_name HAVING cnt > 1) AS dup",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "enrollment_count equals count of Student_Enrolment_Courses rows per course (reconciles aggregate to base table)",
        "sql": "SELECT COUNT(*) FROM course_enrollment_counts v LEFT JOIN Courses c ON v.course_id = c.course_id LEFT JOIN (SELECT course_id, COUNT(student_course_id) AS real_count FROM Student_Enrolment_Courses GROUP BY course_id) s ON v.course_id = s.course_id WHERE COALESCE(s.real_count,0) != COALESCE(v.enrollment_count,0)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL (course_id and course_name must be present)",
        "sql": "SELECT COUNT(*) FROM course_enrollment_counts WHERE course_id IS NULL OR course_name IS NULL",
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
SELECT c.course_id, c.course_name, COUNT(s.student_course_id) AS enrollment_count FROM Courses c LEFT JOIN Student_Enrolment_Courses s ON s.course_id = c.course_id GROUP BY c.course_id, c.course_name
```

---

## Skill `course_enrollment_counts_19`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `course_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_05a3493dc9619dc7 |
| output columns | `course_id`, `enrollment_count` |
| source tables | `Student_Enrolment_Courses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-course counts of student enrollments (number of student_enrolment_courses rows per course), with course_id for joins to course metadata

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
      "Student_Enrolment_Courses"
    ],
    "table_fingerprints": {
      "student_enrolment_courses": "daf1efe3c261d034"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_548",
    "question": "What is the name of the course with the most students enrolled?",
    "rewrite": "Task: Find the course name for the course that has the highest number of students enrolled.\nRequired outputs: course name (the name/title of the course)\nFilters: consider all courses and their enrollments; count number of enrolled students per course; if multiple courses tie for the maximum enrollment, include the name(s) of all tied courses\nSort/limit: order by enrollment count descending and limit to the maximum count (i.e., return course(s) with the top enrollment)",
    "route": "av_nx1_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:54:05+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:54:09+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "course_id",
      "enrollment_count"
    ],
    "row_count": 10,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate course_id keys in the view (each course_id appears at most once)",
        "sql": "SELECT COUNT(*) FROM (SELECT course_id FROM course_enrollment_counts_19 GROUP BY course_id HAVING COUNT(*) > 1) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "enrollment_count matches COUNT(*) of Student_Enrolment_Courses per course_id",
        "sql": "SELECT COUNT(*) FROM (SELECT v.course_id FROM course_enrollment_counts_19 v LEFT JOIN (SELECT course_id, COUNT(*) AS cnt FROM Student_Enrolment_Courses GROUP BY course_id) b ON v.course_id = b.course_id WHERE (b.cnt IS NULL AND v.enrollment_count != 0) OR (b.cnt IS NOT NULL AND v.enrollment_count != b.cnt)) AS mismatches",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "course_id in the view is never NULL",
        "sql": "SELECT COUNT(*) FROM course_enrollment_counts_19 WHERE course_id IS NULL",
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
SELECT course_id, COUNT(*) AS enrollment_count FROM Student_Enrolment_Courses GROUP BY course_id
```

---

## Skill `student_degree_registrations`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `registration_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_552d4ffee4096b98 |
| output columns | `registration_id`, `student_id`, `degree_program_id`, `registration_status` |
| source tables | `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

List all registration records that link students to degree programs (one row per registration association). This relation is used to identify which students have any degree registration.

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
    "origin": "subgoal",
    "subgoal": {
      "want_name": "student_degree_registrations",
      "category": "SEL",
      "required_outputs": [
        "student_id",
        "degree_program_id",
        "registration_id",
        "registration_status"
      ],
      "required_grain": [
        "registration_id"
      ],
      "required_filters": {},
      "text": "List all registration records that link students to degree programs (one row per registration association). This relation is used to identify which students have any degree registration.",
      "source_tables": [],
      "depends_on": [],
      "join_keys": [],
      "relationship": "many_to_one",
      "may_read_base_tables": true,
      "holistic": false,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "primary_key",
    "lineage": [
      "Student_Enrolment"
    ],
    "table_fingerprints": {
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_549",
    "question": "Find the last name of the students who currently live in the state of North Carolina but have not registered in any degree program.",
    "rewrite": "Task: Return the last names of all students who currently live in the state of North Carolina and who are not registered in any degree program.\nRequired outputs: last name\nFilters: student currently lives in state = 'North Carolina'; student has no registration in any degree program (i.e., there is no associated registration/degree record linking that student to any degree program)",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:54:32+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:54:35+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "registration_id",
      "student_id",
      "degree_program_id",
      "registration_status"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "registration_id is the key and must be unique and not NULL (no duplicate or NULL registration_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT registration_id, COUNT(*) AS cnt FROM student_degree_registrations GROUP BY registration_id HAVING registration_id IS NULL OR cnt <> 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view must correspond to an existing Student_Enrolment row (no phantom registrations)",
        "sql": "SELECT COUNT(*) FROM student_degree_registrations v LEFT JOIN Student_Enrolment s ON v.registration_id = s.student_enrolment_id WHERE s.student_enrolment_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "degree_program_id and student_id in the view must match the base table values for that registration (measures reconcile)",
        "sql": "SELECT COUNT(*) FROM student_degree_registrations v JOIN Student_Enrolment s ON v.registration_id = s.student_enrolment_id WHERE (v.student_id IS NOT s.student_id) OR (v.degree_program_id IS NOT s.degree_program_id)",
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
    "neutral": 1,
    "last_used": "spider_dev_550"
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  student_enrolment_id AS registration_id,
  student_id,
  degree_program_id,
  NULL AS registration_status
FROM Student_Enrolment
```

---

## Skill `students_in_state`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `student_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_4f126a46920ab4d2 |
| output columns | `student_id`, `last_name`, `state` |
| source tables | `Students`, `Addresses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Students with their IDs, last names, and state from their current address (one row per student)

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
    "removed_constants": [
      "North Carolina"
    ],
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "Students",
      "Addresses"
    ],
    "table_fingerprints": {
      "students": "ad3aee5be9cacc55",
      "addresses": "be6ad43bf746a2b6"
    },
    "data_fingerprints": {
      "students": "15:15",
      "addresses": "15:15"
    },
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_550",
    "question": "What are the last name of the students who live in North Carolina but have not registered in any degree programs?",
    "rewrite": "Task: Find the last names of students who live in North Carolina and who have not registered in any degree programs.\nRequired outputs: last name\nFilters: student's state = 'North Carolina'; student is not registered in any degree program (no associated registration/degree program records)",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:55:02+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:55:05+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "last_name",
      "state"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Addresses.address_id=Students.current_address_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "View obeys its declared grain: student_id is unique (no duplicate student_id rows)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id, COUNT(*) AS cnt FROM students_in_state GROUP BY student_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_id is never NULL (key not NULL)",
        "sql": "SELECT COUNT(*) FROM students_in_state WHERE student_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "state value matches the state_province_county of the current address in base tables (measure reconciles with base tables)",
        "sql": "SELECT COUNT(*) FROM students_in_state vis WHERE NOT EXISTS (SELECT 1 FROM Students s LEFT JOIN Addresses a ON a.address_id = s.current_address_id WHERE s.student_id = vis.student_id AND ( (vis.state IS NULL AND a.state_province_county IS NULL) OR (vis.state = a.state_province_county) ) )",
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
SELECT s.student_id AS student_id, s.last_name AS last_name, a.state_province_county AS state FROM Students s LEFT JOIN Addresses a ON a.address_id = s.current_address_id
```

---

## Skill `transcript_course_result_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `transcript_id`, `transcript_date` (keyed) |
| status / version | active / v1 |
| skill id | sk_57d48c41a58e944b |
| output columns | `transcript_id`, `transcript_date`, `course_result_count` |
| source tables | `Transcripts`, `Transcript_Contents` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-transcript count of associated course/result records (one row per transcript with its id, date, and number of linked course-result entries).

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
      "Transcripts",
      "Transcript_Contents"
    ],
    "table_fingerprints": {
      "transcripts": "e9e22770a8b921c8",
      "transcript_contents": "ecac21baa04d7c6d"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_551",
    "question": "Show the date and id of the transcript with at least 2 course results.",
    "rewrite": "Task: Return rows for transcripts that have at least 2 associated course results, showing each transcript's date and id.\nRequired outputs: transcript date; transcript id\nFilters: only include transcripts that are linked to 2 or more course result records",
    "route": "av_nx1_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:55:18+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:55:21+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "transcript_id",
      "transcript_date",
      "course_result_count"
    ],
    "row_count": 10,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Transcript_Contents.transcript_id=Transcripts.transcript_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows per grain (transcript_id, transcript_date) in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT transcript_id, transcript_date, COUNT(*) AS cnt FROM transcript_course_result_counts GROUP BY transcript_id, transcript_date HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row's course_result_count equals the number of Transcript_Contents rows linked to that transcript_id",
        "sql": "SELECT COUNT(*) FROM (SELECT v.transcript_id, v.transcript_date FROM transcript_course_result_counts v LEFT JOIN (SELECT transcript_id, COUNT(student_course_id) AS expected_count FROM Transcript_Contents GROUP BY transcript_id) tc ON v.transcript_id = tc.transcript_id WHERE IFNULL(tc.expected_count,0) != IFNULL(v.course_result_count,0))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL (transcript_id or transcript_date should never be NULL in the view)",
        "sql": "SELECT COUNT(*) FROM transcript_course_result_counts WHERE transcript_id IS NULL OR transcript_date IS NULL",
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
SELECT t.transcript_id, t.transcript_date, COUNT(tc.student_course_id) AS course_result_count FROM Transcripts t JOIN Transcript_Contents tc ON tc.transcript_id = t.transcript_id GROUP BY t.transcript_id, t.transcript_date
```

---

## Skill `transcript_course_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `transcript_id`, `transcript_date` (keyed) |
| status / version | active / v1 |
| skill id | sk_d7f3bcbf30430992 |
| output columns | `transcript_id`, `transcript_date`, `course_count` |
| source tables | `Transcripts`, `Transcript_Contents` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-transcript count of associated course entries (one row per transcript with transcript id and date and the number of course entries).

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
      "Transcripts",
      "Transcript_Contents"
    ],
    "table_fingerprints": {
      "transcripts": "e9e22770a8b921c8",
      "transcript_contents": "ecac21baa04d7c6d"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_552",
    "question": "What is the date and id of the transcript with at least 2 courses listed?",
    "rewrite": "Task: Return the date and id values for each transcript that lists at least 2 courses.\nRequired outputs: date; id\nFilters: transcript must have a count of associated course entries >= 2",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:55:28+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:55:31+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "transcript_id",
      "transcript_date",
      "course_count"
    ],
    "row_count": 10,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Transcript_Contents.transcript_id=Transcripts.transcript_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "View has one row per transcript (no duplicate keys on transcript_id, transcript_date)",
        "sql": "SELECT COUNT(*) FROM (SELECT transcript_id, transcript_date, COUNT(*) AS dup_count FROM transcript_course_counts GROUP BY transcript_id, transcript_date HAVING dup_count > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "course_count equals the count of Transcript_Contents.student_course_id for that transcript (measure reconciles with base table)",
        "sql": "SELECT COUNT(*) FROM transcript_course_counts v LEFT JOIN Transcripts t ON v.transcript_id = t.transcript_id LEFT JOIN (SELECT transcript_id, COUNT(student_course_id) AS expected_count FROM Transcript_Contents GROUP BY transcript_id) tc ON v.transcript_id = tc.transcript_id WHERE COALESCE(v.course_count, -999999) != COALESCE(tc.expected_count, 0)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row refers to an existing transcript (no FK or missing parent rows)",
        "sql": "SELECT COUNT(*) FROM transcript_course_counts v LEFT JOIN Transcripts t ON v.transcript_id = t.transcript_id WHERE t.transcript_id IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 1
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT t.transcript_id, t.transcript_date, COUNT(tc.student_course_id) AS course_count FROM Transcripts t JOIN Transcript_Contents tc ON tc.transcript_id = t.transcript_id GROUP BY t.transcript_id, t.transcript_date
```

---

## Skill `students_with_mismatched_addresses`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `student_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_6576c0211aa48f83 |
| output columns | `student_id`, `first_name`, `current_address_id`, `permanent_address_id` |
| source tables | `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Pairs student ids with their current and permanent address ids for students whose permanent address differs from their current address

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
    "grain_basis": "primary_key",
    "lineage": [
      "Students"
    ],
    "table_fingerprints": {
      "students": "ad3aee5be9cacc55"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_559",
    "question": "Whose permanent address is different from his or her current address? List his or her first name.",
    "rewrite": "Task: Find all people whose permanent address is different from their current address and return each person's first name.\nRequired outputs: first name (the person's first name as stored in the schema)\nFilters: Include only rows where the permanent address value is not equal to the current address value for the same person; Compare addresses using exact inequality (permanent_address <> current_address)",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:56:43+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:56:46+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "first_name",
      "current_address_id",
      "permanent_address_id"
    ],
    "row_count": 14,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate student_id in the view (grain uniqueness)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id, COUNT(*) AS cnt FROM students_with_mismatched_addresses GROUP BY student_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view comes from Students and has permanent_address_id different from current_address_id (intrinsic filter)",
        "sql": "SELECT COUNT(*) FROM students_with_mismatched_addresses v LEFT JOIN Students s USING(student_id) WHERE s.student_id IS NULL OR (s.permanent_address_id = s.current_address_id) OR (v.permanent_address_id IS NULL AND v.current_address_id IS NULL) OR (v.permanent_address_id = v.current_address_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All student_id, first_name, current_address_id, permanent_address_id in the view match the values in Students (measures/columns reconcile with base table)",
        "sql": "SELECT COUNT(*) FROM students_with_mismatched_addresses v JOIN Students s USING(student_id) WHERE v.first_name IS NOT s.first_name OR (v.current_address_id IS NOT s.current_address_id) OR (v.permanent_address_id IS NOT s.permanent_address_id)",
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
SELECT student_id, first_name, current_address_id, permanent_address_id FROM Students WHERE permanent_address_id <> current_address_id
```

---

## Skill `students_with_different_permanent_and_current_address`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `student_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_d9e51a38321ce339 |
| output columns | `student_id`, `first_name`, `permanent_address_id`, `current_address_id` |
| source tables | `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Pairs of students whose permanent address differs from their current address (identifies students with distinct permanent_address_id and current_address_id), returning student identifiers and first name for reuse in other queries.

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
    "grain_basis": "primary_key",
    "lineage": [
      "Students"
    ],
    "table_fingerprints": {
      "students": "ad3aee5be9cacc55"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_560",
    "question": "What is the first name of the student whose permanent address is different from his or her current one?",
    "rewrite": "Task: Find the first name of the student whose permanent address is different from their current address.\nRequired outputs: first name of the student\nFilters: rows where the student's permanent address is not equal to the student's current address (permanent_address <> current_address)",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:56:53+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:56:57+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "first_name",
      "permanent_address_id",
      "current_address_id"
    ],
    "row_count": 14,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate student_id rows (view should be keyed by student_id).",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id, COUNT(*) AS cnt FROM students_with_different_permanent_and_current_address GROUP BY student_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows satisfy permanent_address_id IS NOT NULL AND current_address_id IS NOT NULL and they differ.",
        "sql": "SELECT COUNT(*) FROM students_with_different_permanent_and_current_address WHERE permanent_address_id IS NULL OR current_address_id IS NULL OR permanent_address_id = current_address_id",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view must correspond to an existing Students row with matching fields (no spurious rows or altered values).",
        "sql": "SELECT COUNT(*) FROM students_with_different_permanent_and_current_address v LEFT JOIN Students s ON v.student_id = s.student_id AND v.first_name = s.first_name AND v.permanent_address_id = s.permanent_address_id AND v.current_address_id = s.current_address_id WHERE s.student_id IS NULL",
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
SELECT student_id, first_name, permanent_address_id, current_address_id
FROM Students
WHERE permanent_address_id IS NOT NULL
  AND current_address_id IS NOT NULL
  AND permanent_address_id <> current_address_id
```

---

## Skill `active_students_current_address_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `address_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_5bd04699bd2b1f06 |
| output columns | `address_id`, `student_count` |
| source tables | `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-address counts of currently active students based on each student's current address reference

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
    "removed_constants": [
      "NULL filtering for date_left (kept as condition but no specific dates)",
      "exclude NULL current_address_id"
    ],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Students"
    ],
    "table_fingerprints": {
      "students": "ad3aee5be9cacc55"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_561",
    "question": "Which address holds the most number of students currently? List the address id and all lines.",
    "rewrite": "Task: Find the address (address id and all address lines) that currently has the largest number of students living there.\nRequired outputs: address id; all address lines for that address (as stored in the address record)\nFilters: Consider only students who are currently students (i.e., rows representing active/current students in the students table — exclude any students marked inactive or graduated if such a status column exists).; Count students grouped by the address id that represents where the student currently lives (use the students' current address reference column).; If multiple addresses tie for the highest student count, include all tied addresses.\nSort/limit: Order by student count descending; return the top count(s). If ties occur, include all tied rows (no numeric limit).",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:57:06+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:57:09+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "address_id",
      "student_count"
    ],
    "row_count": 0,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No NULL address_id in view (address_id is the key and should not be NULL)",
        "sql": "SELECT COUNT(*) FROM active_students_current_address_counts WHERE address_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count equals count of active students in base table for that address_id",
        "sql": "SELECT COUNT(*) FROM active_students_current_address_counts v WHERE v.student_count <> (SELECT COUNT(*) FROM Students s WHERE s.date_left IS NULL AND s.current_address_id = v.address_id AND s.current_address_id IS NOT NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View contains exactly the set of address_ids that have at least one active student (no extra or missing address groups)",
        "sql": "SELECT ( (SELECT COUNT(*) FROM (SELECT address_id FROM active_students_current_address_counts UNION ALL SELECT DISTINCT current_address_id FROM Students WHERE date_left IS NULL AND current_address_id IS NOT NULL EXCEPT SELECT address_id FROM active_students_current_address_counts)) + (SELECT COUNT(*) FROM (SELECT DISTINCT current_address_id FROM Students WHERE date_left IS NULL AND current_address_id IS NOT NULL EXCEPT SELECT address_id FROM active_students_current_address_counts)) ) WHERE 1=1",
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
SELECT s.current_address_id AS address_id, COUNT(*) AS student_count
FROM Students s
WHERE s.date_left IS NULL AND s.current_address_id IS NOT NULL
GROUP BY s.current_address_id
```

---

## Skill `address_student_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `address_id`, `line_1`, `line_2` (keyed) |
| status / version | active / v1 |
| skill id | sk_a591b7de30dc6408 |
| output columns | `address_id`, `line_1`, `line_2`, `student_count` |
| source tables | `Addresses`, `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-address counts of students associated via current or permanent address (one row per address with its student count).

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
      "Addresses",
      "Students"
    ],
    "table_fingerprints": {
      "addresses": "be6ad43bf746a2b6",
      "students": "ad3aee5be9cacc55"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_562",
    "question": "What is the id, line 1, and line 2 of the address with the most students?",
    "rewrite": "Task: Find the address that has the largest number of students associated with it and return that address's id, line 1, and line 2.\nRequired outputs: id (the identifier of the address); line 1 (the first address line); line 2 (the second address line)\nFilters: Consider only addresses that have one or more students associated; select the address(es) whose associated student count is maximal across all addresses; If multiple addresses tie for the maximum student count, include the address rows for all tied addresses\nSort/limit: no particular ordering required; limit to all addresses that achieve the maximum student count (i.e., no numeric LIMIT unless to break ties, which is not requested)",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:57:16+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:57:19+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "address_id",
      "line_1",
      "line_2",
      "student_count"
    ],
    "row_count": 14,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate address rows: each address_id+line_1+line_2 appears at most once in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT address_id, line_1, line_2, COUNT(*) AS cnt FROM address_student_counts GROUP BY address_id, line_1, line_2 HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count equals count of Students who reference the address either as current or permanent",
        "sql": "SELECT COUNT(*) FROM address_student_counts v LEFT JOIN Addresses a ON v.address_id = a.address_id WHERE v.student_count != (SELECT COUNT(*) FROM Students s WHERE s.current_address_id = a.address_id OR s.permanent_address_id = a.address_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL: address_id, line_1, line_2 must be non-NULL in every view row",
        "sql": "SELECT COUNT(*) FROM address_student_counts WHERE address_id IS NULL OR line_1 IS NULL OR line_2 IS NULL",
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
SELECT a.address_id AS address_id, a.line_1 AS line_1, a.line_2 AS line_2, COUNT(s.student_id) AS student_count
FROM Addresses a
JOIN Students s ON s.current_address_id = a.address_id OR s.permanent_address_id = a.address_id
GROUP BY a.address_id, a.line_1, a.line_2
```

---

## Skill `transcript_mean_timestamp`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | — (scalar) |
| status / version | active / v1 |
| skill id | sk_03af8e404b8b5db0 |
| output columns | `mean_transcript_timestamp` |
| source tables | `Transcripts` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-dataset aggregate relation giving the mean (average) transcript timestamp across all non-null transcript_date rows.

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
    "grain_basis": "scalar_aggregate",
    "lineage": [
      "Transcripts"
    ],
    "table_fingerprints": {
      "transcripts": "e9e22770a8b921c8"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_564",
    "question": "What is the average transcript date?",
    "rewrite": "Task: Compute the average (mean) of the transcript date values across all rows in the table (i.e., the average date/time value of the transcript date column).\nRequired outputs: average_transcript_date: a single value representing the mean of the transcript date column (expressed as a date/time or numeric timestamp)\nFilters: Include all rows (no row-level filters). Exclude NULL/missing transcript date values from the calculation.",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:57:33+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:57:36+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "mean_transcript_timestamp"
    ],
    "row_count": 1,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View should contain exactly one row (scalar grain) — detect if it has zero or multiple rows",
        "sql": "SELECT CASE WHEN (SELECT COUNT(*) FROM transcript_mean_timestamp)=1 THEN 0 ELSE 1 END",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows in view must have mean_transcript_timestamp numeric (no NULL) when there exists at least one non-NULL transcript_date in base table",
        "sql": "SELECT CASE WHEN (SELECT COUNT(*) FROM Transcripts WHERE transcript_date IS NOT NULL)=0 THEN 0 WHEN (SELECT mean_transcript_timestamp IS NULL FROM transcript_mean_timestamp) THEN 1 ELSE 0 END",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Measure must match recomputed average from base table (recomputed in seconds since epoch)",
        "sql": "SELECT CASE WHEN (SELECT COUNT(*) FROM transcript_mean_timestamp)=0 THEN 0 WHEN abs((SELECT mean_transcript_timestamp FROM transcript_mean_timestamp) - (SELECT avg(strftime('%s', transcript_date)) FROM Transcripts WHERE transcript_date IS NOT NULL)) < 1e-6 THEN 0 ELSE 1 END",
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
SELECT avg(strftime('%s', transcript_date)) AS mean_transcript_timestamp FROM Transcripts WHERE transcript_date IS NOT NULL
```

---

## Skill `transcripts_with_min_release_date`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `transcript_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_2abb1d0ee4ff49da |
| output columns | `transcript_id`, `transcript_date`, `other_details` |
| source tables | `Transcripts` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

All transcript records whose transcript_date equals the minimum non-null transcript_date in the Transcripts table (earliest transcript release cohort).

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
    "grain_basis": "verified_unique",
    "lineage": [
      "Transcripts"
    ],
    "table_fingerprints": {
      "transcripts": "e9e22770a8b921c8"
    },
    "data_fingerprints": {
      "transcripts": "15:15"
    },
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_566",
    "question": "What is the earliest date of a transcript release, and what details can you tell me?",
    "rewrite": "Task: Find the earliest transcript release date in the dataset and return that date along with all available details about the corresponding transcript release record(s).\nRequired outputs: earliest_transcript_release_date (date); all other columns/fields from the transcript release record(s) as available in the schema (e.g., id, title, transcript_text, release_date, source, created_at, updated_at, any speaker/meeting identifiers)\nFilters: Consider only rows that represent transcript releases (exclude non-transcript records).; Include only rows where release_date is not NULL.; No additional filter on date range — search the entire table to find the minimum release_date value.\nSort/limit: order by release_date ASC; limit to all rows that have release_date equal to the minimum value (no arbitrary numeric limit)",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:57:55+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:57:58+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "transcript_id",
      "transcript_date",
      "other_details"
    ],
    "row_count": 1,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View only contains transcripts whose transcript_date equals the minimum non-null transcript_date from the base table",
        "sql": "SELECT COUNT(*) FROM transcripts_with_min_release_date v WHERE v.transcript_date IS NULL OR v.transcript_date <> (SELECT MIN(transcript_date) FROM Transcripts WHERE transcript_date IS NOT NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View includes every transcript row from Transcripts that has the minimum non-null transcript_date (no omissions)",
        "sql": "SELECT COUNT(*) FROM Transcripts t WHERE t.transcript_date IS NOT NULL AND t.transcript_date = (SELECT MIN(transcript_date) FROM Transcripts WHERE transcript_date IS NOT NULL) AND NOT EXISTS (SELECT 1 FROM transcripts_with_min_release_date v WHERE v.transcript_id = t.transcript_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "transcript_id in the view are not NULL and respect the declared grain (no duplicate transcript_id rows)",
        "sql": "SELECT COUNT(*) FROM (SELECT transcript_id, COUNT(*) AS cnt FROM transcripts_with_min_release_date GROUP BY transcript_id HAVING transcript_id IS NULL OR cnt <> 1)",
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
SELECT t.*
FROM Transcripts t
WHERE t.transcript_date IS NOT NULL
  AND t.transcript_date = (SELECT MIN(transcript_date) FROM Transcripts WHERE transcript_date IS NOT NULL)
```

---

## Skill `transcript_release_dates`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `transcript_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_52060b09a1c8841c |
| output columns | `transcript_id`, `transcript_date` |
| source tables | `Transcripts` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

All transcripts with their identifiers and release dates (only rows representing transcripts with a non-null release date).

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
    "grain_basis": "primary_key",
    "lineage": [
      "Transcripts"
    ],
    "table_fingerprints": {
      "transcripts": "e9e22770a8b921c8"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_570",
    "question": "When was the last transcript released?",
    "rewrite": "Task: Find the release date of the most recently released transcript.\nRequired outputs: transcript identifier or title (if available); release date (the date the transcript was released)\nFilters: only consider rows that represent transcripts; only consider transcripts that have a non-null release date\nSort/limit: order by release date descending, limit 1",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:58:20+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:58:23+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "transcript_id",
      "transcript_date"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate transcript_id rows in the view (grain uniqueness)",
        "sql": "SELECT COUNT(*) FROM (SELECT transcript_id, COUNT(*) AS cnt FROM transcript_release_dates GROUP BY transcript_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view has a non-NULL transcript_date (intrinsic filter respected)",
        "sql": "SELECT COUNT(*) FROM transcript_release_dates WHERE transcript_date IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view corresponds to a real Transcripts row and the transcript_date matches the base table (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM transcript_release_dates v LEFT JOIN Transcripts t ON v.transcript_id = t.transcript_id WHERE t.transcript_id IS NULL OR (v.transcript_date IS NOT t.transcript_date AND NOT (v.transcript_date IS NULL AND t.transcript_date IS NULL))",
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
SELECT transcript_id, transcript_date FROM Transcripts WHERE transcript_date IS NOT NULL
```

---

## Skill `student_course_transcript_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `student_course_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_29c62086964342c4 |
| output columns | `student_course_id`, `distinct_transcript_count` |
| source tables | `Transcript_Contents` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each student course enrollment, the count of distinct transcripts in which that enrollment appears.

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
      "Transcript_Contents"
    ],
    "table_fingerprints": {
      "transcript_contents": "ecac21baa04d7c6d"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_571",
    "question": "How many times at most can a course enrollment result show in different transcripts? Also show the course enrollment id.",
    "rewrite": "Task: Find, for each course enrollment id, the maximum number of different transcripts in which that course enrollment appears; return only those course enrollment ids paired with that maximum count.\nRequired outputs: course enrollment id (the course enrollment identifier); max count of distinct transcripts that the course enrollment appears in (an integer)\nFilters: include every course enrollment id present in the data; for each course enrollment id count distinct transcript identifiers in which that course enrollment appears; no additional filtering (e.g., no date/user filters)\nSort/limit: order results by the max count in descending order; if counts tie, order by course enrollment id ascending; no row limit",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:58:30+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:58:33+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "student_course_id",
      "distinct_transcript_count"
    ],
    "row_count": 9,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View has one row per student_course_id (no duplicates of the key)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_course_id FROM student_course_transcript_counts GROUP BY student_course_id HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "distinct_transcript_count equals COUNT(DISTINCT transcript_id) recomputed from base table for each student_course_id",
        "sql": "SELECT COUNT(*) FROM student_course_transcript_counts v LEFT JOIN (SELECT student_course_id, COUNT(DISTINCT transcript_id) AS recomputed_count FROM Transcript_Contents GROUP BY student_course_id) b ON v.student_course_id = b.student_course_id WHERE (b.recomputed_count IS NULL AND v.distinct_transcript_count IS NOT NULL) OR (b.recomputed_count IS NOT NULL AND v.distinct_transcript_count != b.recomputed_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_course_id (the key) is not NULL in the view",
        "sql": "SELECT COUNT(*) FROM student_course_transcript_counts WHERE student_course_id IS NULL",
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
      "Task: Find the course that appears in the largest number of different transcripts and report that maximum count along with the course's enrollment id.\nRequired outputs: enrollment id of the course (enrollment id); the number of distinct transcripts that course appears in (maximum count)\nFilters: consider each transcript separately and count distinct transcripts per course; if multiple courses tie for the maximum count, include the enrollment id for each tied course"
    ],
    "last_used": "spider_dev_572"
  }
}
```

### Validated on (1)

- What is the maximum number of times that a course shows up in different transcripts and what is that course's enrollment id?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT student_course_id, COUNT(DISTINCT transcript_id) AS distinct_transcript_count FROM Transcript_Contents GROUP BY student_course_id
```

---

## Skill `semester_enrolments_by_degree`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `semester_id`, `degree_summary_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_3f50d47f33ec0f78 |
| output columns | `semester_id`, `degree_summary_name`, `enrolment_count` |
| source tables | `Student_Enrolment`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each semester and degree_summary_name, indicates that at least one student enrolment exists (one row per semester and degree_summary_name)

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
    "removed_constants": [
      "'Master'",
      "'Bachelor'"
    ],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Student_Enrolment",
      "Degree_Programs"
    ],
    "table_fingerprints": {
      "student_enrolment": "445257138d420d03",
      "degree_programs": "85466a54c4a97bc7"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_575",
    "question": "Find the semester when both Master students and Bachelor students got enrolled in.",
    "rewrite": "Task: Find the semester(s) in which both Master students and Bachelor students were enrolled.\nRequired outputs: semester — the semester identifier/value for which the condition holds\nFilters: Include only semesters where at least one student with degree = 'Master' was enrolled; AND at least one student with degree = 'Bachelor' was enrolled",
    "route": "av_nx1_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:59:21+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:59:25+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "semester_id",
      "degree_summary_name",
      "enrolment_count"
    ],
    "row_count": 10,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Student_Enrolment.degree_program_id=Degree_Programs.degree_program_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "View rows are unique per declared key (semester_id, degree_summary_name). Checks for duplicate rows in the view for the key pair.",
        "sql": "SELECT COUNT(*) FROM (SELECT semester_id, degree_summary_name, COUNT(*) AS cnt FROM semester_enrolments_by_degree GROUP BY semester_id, degree_summary_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row corresponds to at least one Student_Enrolment joined to the Degree_Programs (enrolment_count matches actual count recomputed from base tables).",
        "sql": "SELECT COUNT(*) FROM semester_enrolments_by_degree v LEFT JOIN (SELECT se.semester_id, dp.degree_summary_name, COUNT(*) AS expected_count FROM Student_Enrolment se JOIN Degree_Programs dp ON se.degree_program_id = dp.degree_program_id GROUP BY se.semester_id, dp.degree_summary_name) b ON v.semester_id = b.semester_id AND v.degree_summary_name = b.degree_summary_name WHERE b.expected_count IS NULL OR v.enrolment_count != b.expected_count",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys in the view are not NULL (semester_id and degree_summary_name must be present).",
        "sql": "SELECT COUNT(*) FROM semester_enrolments_by_degree WHERE semester_id IS NULL OR degree_summary_name IS NULL",
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
SELECT se.semester_id, dp.degree_summary_name, COUNT(*) AS enrolment_count
FROM Student_Enrolment se
JOIN Degree_Programs dp ON se.degree_program_id = dp.degree_program_id
GROUP BY se.semester_id, dp.degree_summary_name
```

---

## Skill `semester_enrollment_degree_levels`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `semester_id`, `degree_summary_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_6b42e73fa254d6f0 |
| output columns | `semester_id`, `degree_summary_name`, `enrollments_count`, `distinct_students_count` |
| source tables | `Student_Enrolment`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-semester counts of distinct student degree level values (degree_summary_name) present among enrollments, with keys to join to semesters and degree programs

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
    "removed_constants": [
      "'Masters'",
      "'Bachelors'",
      "= 2"
    ],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Student_Enrolment",
      "Degree_Programs"
    ],
    "table_fingerprints": {
      "student_enrolment": "445257138d420d03",
      "degree_programs": "85466a54c4a97bc7"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_576",
    "question": "What is the id of the semester that had both Masters and Bachelors students enrolled?",
    "rewrite": "Task: Find the id of the semester for which there exist enrollments of both Masters students and Bachelors students in that same semester.\nRequired outputs: semester id\nFilters: Consider only semesters that have at least one enrollment record for a student whose degree level is 'Masters' and at least one enrollment record for a student whose degree level is 'Bachelors'.; Degree level values to match are the literal strings 'Masters' and 'Bachelors'.; Both enrollments must reference the same semester id.",
    "route": "av_nx1_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T23:59:40+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-09-30T23:59:46+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "semester_id",
      "degree_summary_name",
      "enrollments_count",
      "distinct_students_count"
    ],
    "row_count": 10,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Student_Enrolment.degree_program_id=Degree_Programs.degree_program_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "View rows are unique at the declared grain (semester_id, degree_summary_name) — no duplicate rows for the key",
        "sql": "SELECT COUNT(*) FROM (SELECT semester_id, degree_summary_name, COUNT(*) AS cnt FROM semester_enrollment_degree_levels GROUP BY semester_id, degree_summary_name HAVING cnt > 1) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "enrollments_count matches COUNT(*) of Student_Enrolment rows that join to the same degree_summary_name and semester_id",
        "sql": "SELECT COUNT(*) FROM semester_enrollment_degree_levels v LEFT JOIN (SELECT se.semester_id, dp.degree_summary_name, COUNT(*) AS expected_enrollments FROM Student_Enrolment se JOIN Degree_Programs dp ON se.degree_program_id = dp.degree_program_id GROUP BY se.semester_id, dp.degree_summary_name) b ON v.semester_id = b.semester_id AND v.degree_summary_name = b.degree_summary_name WHERE (v.enrollments_count IS NULL AND b.expected_enrollments IS NOT NULL) OR (v.enrollments_count IS NOT NULL AND b.expected_enrollments IS NULL) OR (v.enrollments_count <> b.expected_enrollments)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "distinct_students_count equals the distinct count of student_id from Student_Enrolment for that semester_id and degree_summary_name",
        "sql": "SELECT COUNT(*) FROM semester_enrollment_degree_levels v LEFT JOIN (SELECT se.semester_id, dp.degree_summary_name, COUNT(DISTINCT se.student_id) AS expected_distinct FROM Student_Enrolment se JOIN Degree_Programs dp ON se.degree_program_id = dp.degree_program_id GROUP BY se.semester_id, dp.degree_summary_name) b ON v.semester_id = b.semester_id AND v.degree_summary_name = b.degree_summary_name WHERE (v.distinct_students_count IS NULL AND b.expected_distinct IS NOT NULL) OR (v.distinct_students_count IS NOT NULL AND b.expected_distinct IS NULL) OR (v.distinct_students_count <> b.expected_distinct)",
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
SELECT se.semester_id, dp.degree_summary_name, COUNT(*) AS enrollments_count, COUNT(DISTINCT se.student_id) AS distinct_students_count FROM Student_Enrolment se JOIN Degree_Programs dp ON se.degree_program_id = dp.degree_program_id GROUP BY se.semester_id, dp.degree_summary_name
```

---

## Skill `addresses_with_students`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `address_id`, `address` (keyed) |
| status / version | active / v1 |
| skill id | sk_ad91e47aaa1adc7d |
| output columns | `address_id`, `address` |
| source tables | `Addresses`, `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Distinct addresses that are associated with one or more students via current or permanent address references

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
    "grain_basis": "distinct",
    "lineage": [
      "Addresses",
      "Students"
    ],
    "table_fingerprints": {
      "addresses": "be6ad43bf746a2b6",
      "students": "ad3aee5be9cacc55"
    },
    "data_fingerprints": {
      "addresses": "15:15",
      "students": "15:15"
    },
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_578",
    "question": "What are the different addresses that have students living there?",
    "rewrite": "Task: List the distinct addresses that have students living at them.\nRequired outputs: address (the address value/location where at least one student resides)\nFilters: Include only addresses that are associated with one or more students (i.e., addresses that have at least one student living there).; Do not include addresses with no students.",
    "route": "direct_sql",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:00:02+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T00:00:06+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "address_id",
      "address"
    ],
    "row_count": 14,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows per declared grain (address_id, address)",
        "sql": "SELECT COUNT(*) FROM (SELECT address_id, address, COUNT(*) AS cnt FROM addresses_with_students GROUP BY address_id, address HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row corresponds to an Addresses row that is referenced by at least one student (no stray addresses)",
        "sql": "SELECT COUNT(*) FROM addresses_with_students aws LEFT JOIN Addresses a ON aws.address_id = a.address_id LEFT JOIN Students s ON s.current_address_id = aws.address_id OR s.permanent_address_id = aws.address_id WHERE a.address_id IS NULL OR s.student_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Recomputed address string from Addresses matches the view's address for each address_id",
        "sql": "SELECT COUNT(*) FROM addresses_with_students aws JOIN Addresses a ON aws.address_id = a.address_id WHERE aws.address != (COALESCE(a.line_1, '') || CASE WHEN a.line_2 IS NOT NULL AND a.line_2 <> '' THEN ', ' || a.line_2 ELSE '' END || CASE WHEN a.line_3 IS NOT NULL AND a.line_3 <> '' THEN ', ' || a.line_3 ELSE '' END || CASE WHEN a.city IS NOT NULL AND a.city <> '' THEN ', ' || a.city ELSE '' END || CASE WHEN a.state_province_county IS NOT NULL AND a.state_province_county <> '' THEN ', ' || a.state_province_county ELSE '' END || CASE WHEN a.zip_postcode IS NOT NULL AND a.zip_postcode <> '' THEN ' ' || a.zip_postcode ELSE '' END || CASE WHEN a.country IS NOT NULL AND a.country <> '' THEN ', ' || a.country ELSE '' END)",
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
SELECT DISTINCT a.address_id, COALESCE(a.line_1, '') || CASE WHEN a.line_2 IS NOT NULL AND a.line_2 <> '' THEN ', ' || a.line_2 ELSE '' END || CASE WHEN a.line_3 IS NOT NULL AND a.line_3 <> '' THEN ', ' || a.line_3 ELSE '' END || CASE WHEN a.city IS NOT NULL AND a.city <> '' THEN ', ' || a.city ELSE '' END || CASE WHEN a.state_province_county IS NOT NULL AND a.state_province_county <> '' THEN ', ' || a.state_province_county ELSE '' END || CASE WHEN a.zip_postcode IS NOT NULL AND a.zip_postcode <> '' THEN ' ' || a.zip_postcode ELSE '' END || CASE WHEN a.country IS NOT NULL AND a.country <> '' THEN ', ' || a.country ELSE '' END AS address FROM Addresses a JOIN Students s ON s.current_address_id = a.address_id OR s.permanent_address_id = a.address_id
```

---
