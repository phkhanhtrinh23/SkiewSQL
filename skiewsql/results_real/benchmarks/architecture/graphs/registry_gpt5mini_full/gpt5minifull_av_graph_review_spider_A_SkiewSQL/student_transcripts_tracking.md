# Skill graph — `student_transcripts_tracking` (28 skills)

## Skill `department_degree_counts`

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

Per-department counts of associated degree programs (one row per department with department id, name, and degree count).

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
    "rewrite": "Task: Find the department (name and id) that offers the largest number of degrees.\nRequired outputs: department name; department id\nFilters: Count degrees per department across all records; include only the department(s) whose degree count is maximal (i.e., equal to the highest degree count among all departments). Exclude departments with zero associated degrees only if there exists at least one department with >0 degrees; if all departments have zero degrees, return all departments (their name and id).\nSort/limit: If multiple departments tie for the maximum count, return all tied departments in any order; no explicit limit.",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T05:55:41+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T05:55:45+00:00",
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
        "purpose": "View has exactly one row per department (no missing departments): every department_id in Departments must appear in the view",
        "sql": "SELECT COUNT(*) FROM Departments d WHERE NOT EXISTS (SELECT 1 FROM department_degree_counts v WHERE v.department_id = d.department_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View has no duplicate keys (department_id, department_name) - duplicates would violate the declared grain",
        "sql": "SELECT COUNT(*) FROM (SELECT department_id, department_name, COUNT(*) AS cnt FROM department_degree_counts GROUP BY department_id, department_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "degree_count equals the count of Degree_Programs per department (reconciles with base table)",
        "sql": "SELECT COUNT(*) FROM department_degree_counts v LEFT JOIN (SELECT department_id, COUNT(degree_program_id) AS expected_count FROM Degree_Programs GROUP BY department_id) dp ON dp.department_id = v.department_id WHERE (dp.expected_count IS NULL AND v.degree_count != 0) OR (dp.expected_count IS NOT NULL AND v.degree_count != dp.expected_count)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 3,
    "selected": 3,
    "included": 3,
    "referenced": 3,
    "executed": 3,
    "inconclusive": 3,
    "positive": 3,
    "positive_subgoals": [
      "Task: Find the department that has the largest number of degrees and return that department's name and id.\nRequired outputs: department name; department id\nFilters: consider all departments and count how many degrees are associated with each department; if multiple departments tie for the maximum number of degrees, return all such departments\nSort/limit: order not required; no row limit (return all departments that match the maximum count)",
      "Task: Compute the number of distinct departments that offer any degree (i.e., count departments for which there exists at least one degree they offer).\nRequired outputs: a single numeric value representing the count of departments that offer at least one degree\nFilters: include only departments that are associated with one or more degree records (existence of at least one degree for the department); exclude departments with no associated degree records",
      "Task: Count the number of distinct departments that offer degrees\nRequired outputs: a single integer giving the count of distinct department identifiers or names that offer degrees\nFilters: consider only rows where a department is associated with at least one degree offering (i.e., exclude departments with no degrees)"
    ],
    "last_used": "spider_dev_518"
  }
}
```

### Validated on (3)

- What is the name and id of the department with the most number of degrees ?
- How many departments offer any degree?
- How many different departments offer degrees?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT d.department_id, d.department_name, COUNT(dp.degree_program_id) AS degree_count FROM Departments d LEFT JOIN Degree_Programs dp ON dp.department_id = d.department_id GROUP BY d.department_id, d.department_name
```

---

## Skill `degree_names_distinct_count`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `degree_summary_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_c2c575c023168c57 |
| output columns | `degree_summary_name` |
| source tables | `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

A relation that returns each distinct degree name from the Degree_Programs table, suitable as a building block for counts or joins against degree names.

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
      "Degree_Programs"
    ],
    "table_fingerprints": {
      "degree_programs": "85466a54c4a97bc7"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_519",
    "question": "How many different degree names are offered?",
    "rewrite": "Task: Return the number of distinct degree names offered.\nRequired outputs: a single numeric value representing the count of unique degree names\nFilters: no additional filters; consider all rows in the degree name field/table",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T05:56:45+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T05:56:47+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "degree_summary_name"
    ],
    "row_count": 3,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No NULLs in the key column degree_summary_name",
        "sql": "SELECT COUNT(*) FROM Degree_Programs AS dp WHERE dp.degree_summary_name IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View contains exactly the distinct degree_summary_name values from Degree_Programs (no missing distinct values)",
        "sql": "SELECT COUNT(*) FROM (SELECT DISTINCT degree_summary_name FROM Degree_Programs EXCEPT SELECT degree_summary_name FROM degree_names_distinct_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View does not contain any values that are not present in Degree_Programs (no extraneous rows)",
        "sql": "SELECT COUNT(*) FROM (SELECT degree_summary_name FROM degree_names_distinct_count EXCEPT SELECT DISTINCT degree_summary_name FROM Degree_Programs)",
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
      "Task: Compute the number of distinct degrees offered.\nRequired outputs: count_of_distinct_degrees"
    ],
    "last_used": "spider_dev_520"
  }
}
```

### Validated on (1)

- How many different degrees are offered?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT degree_summary_name FROM "Degree_Programs" GROUP BY degree_summary_name
```

---

## Skill `degree_programs_with_department`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `degree_program_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_e2ea7294f7aba2ce |
| output columns | `degree_program_id`, `department_id`, `degree_summary_name`, `degree_summary_description`, `other_details`, `department_id:1`, `department_name` |
| source tables | `Degree_Programs`, `Departments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

All degree programs joined with their department metadata to allow filtering or aggregation by department attributes.

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
      "engineering"
    ],
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "Degree_Programs",
      "Departments"
    ],
    "table_fingerprints": {
      "degree_programs": "85466a54c4a97bc7",
      "departments": "188d438ee9ba34ad"
    },
    "data_fingerprints": {
      "degree_programs": "15:15",
      "departments": "15:15"
    },
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_521",
    "question": "How many degrees does the engineering department offer?",
    "rewrite": "Task: Count how many degrees are offered by the engineering department.\nRequired outputs: a single numeric value representing the count of degrees offered by the engineering department\nFilters: department must be 'engineering' (case-insensitive match)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T05:57:15+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T05:57:18+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "degree_program_id",
      "department_id",
      "degree_summary_name",
      "degree_summary_description",
      "other_details",
      "department_id:1",
      "department_name"
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
        "purpose": "View grain: each degree_program_id appears exactly once (no duplicate rows for the view's grain).",
        "sql": "SELECT COUNT(*) FROM (SELECT degree_program_id FROM degree_programs_with_department GROUP BY degree_program_id HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows in the view must reference an existing department (the join should not introduce rows with missing department_id or department_name).",
        "sql": "SELECT COUNT(*) FROM degree_programs_with_department v WHERE v.department_id IS NULL OR v.department_name IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Join correctness: for each degree_program row, the department_name in the view must match the Departments table's department_name (measure reconciles with base table).",
        "sql": "SELECT COUNT(*) FROM degree_programs_with_department v JOIN Departments d ON v.department_id = d.department_id WHERE (v.department_name IS NOT d.department_name) OR (v.department_name IS NULL AND d.department_name IS NOT NULL) OR (v.department_name IS NOT NULL AND d.department_name IS NULL)",
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
SELECT dp.*,
       d.department_id,
       d.department_name
FROM "Degree_Programs" dp
JOIN "Departments" d ON dp.department_id = d.department_id
```

---

## Skill `course_section_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `course_id`, `course_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_6fa3a022c44755e8 |
| output columns | `course_id`, `course_name`, `section_count` |
| source tables | `Courses`, `Sections` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-course counts of sections (one row per course with course id, name, and number of sections) useful for filtering or joining by how many sections a course has.

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
    "rewrite": "Task: Find all courses that have at most 2 sections, and return each course's name and id.\nRequired outputs: course name; course id\nFilters: count of sections for a course_id <= 2",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T05:58:04+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T05:58:06+00:00",
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
        "join": "Sections.course_id=Courses.course_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows per declared grain (course_id, course_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT course_id, course_name, COUNT(*) as cnt FROM course_section_counts GROUP BY course_id, course_name HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each section_count equals number of Sections rows with that course_id (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM course_section_counts v LEFT JOIN Courses c ON v.course_id = c.course_id WHERE (SELECT COUNT(*) FROM Sections s WHERE s.course_id = v.course_id) != v.section_count",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All keys in the view are NOT NULL (course_id and course_name)",
        "sql": "SELECT COUNT(*) FROM course_section_counts WHERE course_id IS NULL OR course_name IS NULL",
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
    "negative": 1,
    "negative_subgoals": [
      "Task: Return the name and id for every course that has fewer than 2 associated sections.\nRequired outputs: course id; course name\nFilters: only include courses where the count of sections associated with that course is less than 2 (i.e., 0 or 1 sections); treat association between a course and its sections using the schema's relationship for sections linked to courses"
    ],
    "last_used": "spider_dev_526"
  }
}
```

### Validated on (0)

—

### Counter-examples (1)

- What are the names and ids of every course with less than 2 sections?

### Executable SQL body

```sql
SELECT c.course_id, c.course_name, COUNT(s.section_id) AS section_count
FROM Courses c
LEFT JOIN Sections s ON s.course_id = c.course_id
GROUP BY c.course_id, c.course_name
```

---

## Skill `semester_registration_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `semester_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_a126ae01ad558071 |
| output columns | `semester_id`, `registration_count` |
| source tables | `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Counts of student registrations per semester (one row per semester with semester id and registration count) useful for comparing or ranking semester enrollment levels.

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
    "question_id": "spider_dev_529",
    "question": "What is the semester which most student registered in? Show both the name and the id.",
    "rewrite": "Task: Find the semester (both its name and its id) that has the largest number of student registrations.\nRequired outputs: semester id; semester name\nFilters: Count registrations per semester across all student registration records; consider all semesters present in the registration data (no additional filtering).; If multiple semesters tie for the maximum number of student registrations, return all such semesters.",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T05:59:13+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T05:59:15+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "semester_id",
      "registration_count"
    ],
    "row_count": 9,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate semester_id rows (view should have one row per semester_id key)",
        "sql": "SELECT COUNT(*) FROM (SELECT semester_id, COUNT(*) AS c FROM semester_registration_counts GROUP BY semester_id HAVING c > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "registration_count matches count of rows in base table per semester_id",
        "sql": "SELECT COUNT(*) FROM semester_registration_counts v LEFT JOIN (SELECT semester_id, COUNT(*) AS expected_count FROM Student_Enrolment GROUP BY semester_id) b ON v.semester_id = b.semester_id WHERE (b.expected_count IS NULL AND v.registration_count IS NOT NULL) OR (b.expected_count IS NOT NULL AND v.registration_count != b.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "semester_id in view is not NULL (key must be present)",
        "sql": "SELECT COUNT(*) FROM semester_registration_counts WHERE semester_id IS NULL",
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
SELECT semester_id, COUNT(*) AS registration_count
FROM Student_Enrolment
GROUP BY semester_id
```

---

## Skill `student_enrollment_degree_counts_by_semester`

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

Per-student, per-semester counts of distinct degree program enrollments (only includes enrollment records), useful to find students enrolled in multiple programs in the same semester.

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
    "rewrite": "Task: Find all students who are enrolled in exactly two degree programs during the same semester; return each student's first name, middle name, last name, and student id.\nRequired outputs: first name; middle name; last name; id\nFilters: Only include students who have two distinct degree program enrollments that occur in the same semester (same semester identifier and year if semester is split into those fields).; Count only enrollments that are active/enrolled for that semester (exclude withdrawn/cancelled enrollments if status field exists).; If a student has more than two enrollments in that semester, do not include them (require exactly two distinct degree program enrollments in that semester).",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:00:10+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:00:13+00:00",
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
        "purpose": "No NULLs in key columns (student_id, semester_id) in the view",
        "sql": "SELECT COUNT(*) FROM student_enrollment_degree_counts_by_semester WHERE student_id IS NULL OR semester_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "distinct_degree_program_count equals COUNT(DISTINCT degree_program_id) recomputed from base Student_Enrolment for that student+semester (detect mismatches)",
        "sql": "SELECT COUNT(*) FROM student_enrollment_degree_counts_by_semester v LEFT JOIN (SELECT student_id, semester_id, COUNT(DISTINCT degree_program_id) AS recomputed_cnt FROM Student_Enrolment GROUP BY student_id, semester_id) b ON v.student_id = b.student_id AND v.semester_id = b.semester_id WHERE COALESCE(v.distinct_degree_program_count, -9999999) <> COALESCE(b.recomputed_cnt, -9999999)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View does not include rows for student+semester combinations that have no enrollment records (every view row should correspond to at least one Student_Enrolment row)",
        "sql": "SELECT COUNT(*) FROM student_enrollment_degree_counts_by_semester v LEFT JOIN Student_Enrolment se ON v.student_id = se.student_id AND v.semester_id = se.semester_id WHERE se.student_enrolment_id IS NULL",
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
SELECT se.student_id AS student_id,
       se.semester_id AS semester_id,
       COUNT(DISTINCT se.degree_program_id) AS distinct_degree_program_count
FROM Student_Enrolment se
GROUP BY se.student_id, se.semester_id
```

---

## Skill `student_semester_program_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `student_id`, `semester_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_ccf22f115d4a9408 |
| output columns | `student_id`, `semester_id`, `program_count` |
| source tables | `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per student and semester counts of distinct degree program enrollments (one row per student-semester with the count of distinct degree_program_id).

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
    "question_id": "spider_dev_534",
    "question": "What are the first, middle, and last names, along with the ids, of all students who enrolled in 2 degree programs in one semester?",
    "rewrite": "Task: Find all students who enrolled in exactly two degree programs within a single semester, and return each matching student's first name, middle name, last name, and id.\nRequired outputs: first name; middle name; last name; id\nFilters: Include only students for whom, for at least one semester, the count of degree program enrollments in that semester equals 2 (i.e., exactly two program enrollments that share the same semester for that student).; Do not include students who never had exactly two program enrollments in any single semester (exclude students with only one program in every semester or with three or more programs in the same semester).",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:00:36+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:00:39+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "semester_id",
      "program_count"
    ],
    "row_count": 14,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (student_id, semester_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id, semester_id, COUNT(*) AS cnt FROM student_semester_program_counts GROUP BY student_id, semester_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "program_count matches the distinct count of degree_program_id in the base table per student and semester",
        "sql": "SELECT COUNT(*) FROM student_semester_program_counts v LEFT JOIN (SELECT student_id, semester_id, COUNT(DISTINCT degree_program_id) AS expected_count FROM Student_Enrolment GROUP BY student_id, semester_id) b ON v.student_id = b.student_id AND v.semester_id = b.semester_id WHERE (b.expected_count IS NULL AND v.program_count IS NOT NULL) OR (b.expected_count IS NOT NULL AND v.program_count IS NULL) OR (b.expected_count IS NOT NULL AND v.program_count != b.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys student_id and semester_id are never NULL in the view",
        "sql": "SELECT COUNT(*) FROM student_semester_program_counts WHERE student_id IS NULL OR semester_id IS NULL",
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
SELECT se.student_id AS student_id,
       se.semester_id AS semester_id,
       COUNT(DISTINCT se.degree_program_id) AS program_count
FROM Student_Enrolment se
GROUP BY se.student_id, se.semester_id
```

---

## Skill `degree_program_enrollment_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `program_kind` (keyed) |
| status / version | active / v1 |
| skill id | sk_9dde1c65976bdbd0 |
| output columns | `program_kind`, `total_enrolled_students` |
| source tables | `Degree_Programs`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-degree-program aggregated counts of enrolled students, joining Degree_Programs to Student_Enrolment to produce total enrolled students per program kind

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
    "rewrite": "Task: Find the program kind (type of program) that has the largest total number of enrolled students, returning that program kind and the corresponding total student count.\nRequired outputs: program_kind (the kind/category of program); total_enrolled_students (the total number of students enrolled in that program kind)\nFilters: Include all program kinds present in the data; count all students enrolled in each program kind. Exclude program kinds with zero enrolled students if none are enrolled. If multiple program kinds tie for the maximum total enrolled students, return all tied program kinds and their equal totals.\nSort/limit: order by total_enrolled_students desc limit to the maximum value (return all rows that equal the maximum total)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:01:21+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:01:24+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "program_kind",
      "total_enrolled_students"
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
        "purpose": "No NULLs in the view key program_kind (ensures grouping key is present)",
        "sql": "SELECT COUNT(*) FROM degree_program_enrollment_counts WHERE program_kind IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No duplicate rows per grain (program_kind) — view should have at most one row per program_kind",
        "sql": "SELECT COUNT(*) FROM (SELECT program_kind, COUNT(*) AS cnt FROM degree_program_enrollment_counts GROUP BY program_kind HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "total_enrolled_students equals count of Student_Enrolment.student_id joined to Degree_Programs per program_kind (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM (SELECT dp.degree_summary_name AS program_kind, COUNT(se.student_id) AS expected_count FROM Degree_Programs dp JOIN Student_Enrolment se ON se.degree_program_id = dp.degree_program_id GROUP BY dp.degree_summary_name EXCEPT SELECT program_kind, total_enrolled_students FROM degree_program_enrollment_counts)",
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
SELECT dp.degree_summary_name AS program_kind, COUNT(se.student_id) AS total_enrolled_students FROM "Degree_Programs" dp JOIN "Student_Enrolment" se ON se.degree_program_id = dp.degree_program_id GROUP BY dp.degree_summary_name
```

---

## Skill `degree_program_enrollment_counts_10`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `degree_program_id`, `degree_summary_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_813b395f9047c36f |
| output columns | `degree_program_id`, `degree_summary_name`, `num_students_enrolled` |
| source tables | `Degree_Programs`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-degree-program counts of enrolled students by joining degree programs to student enrollments, including degree program identifiers and names for joins and grouping.

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
    "question_id": "spider_dev_538",
    "question": "What is the degree summary name that has the most number of students enrolled?",
    "rewrite": "Task: Find the degree summary name that has the largest number of students enrolled.\nRequired outputs: degree summary name; number of students enrolled in that degree summary\nFilters: Consider all degree summaries present in the data; Count students enrolled per degree summary by aggregating enrollments linked to each degree summary; Include degree summaries with zero enrollments only if no degree summary has positive enrollments\nSort/limit: order by number of students enrolled descending, limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:01:41+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:01:43+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "degree_program_id",
      "degree_summary_name",
      "num_students_enrolled"
    ],
    "row_count": 15,
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
        "purpose": "View rows should be unique at the declared grain (no duplicate (degree_program_id, degree_summary_name) pairs)",
        "sql": "SELECT COUNT(*) FROM (SELECT degree_program_id, degree_summary_name, COUNT(*) AS cnt FROM degree_program_enrollment_counts_10 GROUP BY degree_program_id, degree_summary_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row's key degree_program_id must not be NULL (keys cannot be NULL)",
        "sql": "SELECT COUNT(*) FROM degree_program_enrollment_counts_10 WHERE degree_program_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "num_students_enrolled must equal the count of Student_Enrolment rows that reference that degree_program_id (reconcile measure with base table)",
        "sql": "SELECT COUNT(*) FROM degree_program_enrollment_counts_10 v LEFT JOIN (SELECT degree_program_id AS dpid, COUNT(student_id) AS expected_count FROM Student_Enrolment GROUP BY degree_program_id) b ON v.degree_program_id = b.dpid WHERE COALESCE(b.expected_count, 0) != COALESCE(v.num_students_enrolled, 0)",
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
SELECT dp.degree_program_id AS degree_program_id,
       dp.degree_summary_name AS degree_summary_name,
       COUNT(se.student_id) AS num_students_enrolled
FROM Degree_Programs dp
LEFT JOIN Student_Enrolment se ON se.degree_program_id = dp.degree_program_id
GROUP BY dp.degree_program_id, dp.degree_summary_name
```

---

## Skill `degree_program_student_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `degree_program_id`, `degree_summary_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_1f678c24f1f2fc88 |
| output columns | `degree_program_id`, `degree_summary_name`, `student_count` |
| source tables | `Degree_Programs`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-degree_program counts of current/valid student enrollments (one row per degree_program with student count and keys for joining).

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
    "question_id": "spider_dev_539",
    "question": "Find the program which most number of students are enrolled in. List both the id and the summary.",
    "rewrite": "Task: Find the program (i.e., the program record) that has the largest number of students enrolled and return that program's id and summary.\nRequired outputs: program id; program summary\nFilters: Count students enrolled per program and select the program(s) with the maximum student count; Include only enrollments that are current/valid (no additional temporal filters provided in the question)\nSort/limit: order by student count descending, limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:01:56+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:01:59+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "degree_program_id",
      "degree_summary_name",
      "student_count"
    ],
    "row_count": 15,
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
        "purpose": "No duplicate rows at the declared grain (degree_program_id, degree_summary_name).",
        "sql": "SELECT COUNT(*) FROM (SELECT degree_program_id, degree_summary_name, COUNT(*) AS cnt FROM degree_program_student_counts GROUP BY degree_program_id, degree_summary_name HAVING cnt > 1) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count matches count of Student_Enrolment rows per degree_program (including zero) — detects aggregation or join mistakes.",
        "sql": "SELECT COUNT(*) FROM degree_program_student_counts dpsc LEFT JOIN (SELECT degree_program_id, COUNT(student_id) AS expected_count FROM Student_Enrolment GROUP BY degree_program_id) se ON dpsc.degree_program_id = se.degree_program_id WHERE (COALESCE(se.expected_count, 0) != COALESCE(dpsc.student_count, 0))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys degree_program_id and degree_summary_name are never NULL.",
        "sql": "SELECT COUNT(*) FROM degree_program_student_counts WHERE degree_program_id IS NULL OR degree_summary_name IS NULL",
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
SELECT dp.degree_program_id AS degree_program_id,
       dp.degree_summary_name AS degree_summary_name,
       COUNT(se.student_id) AS student_count
FROM "Degree_Programs" dp
LEFT JOIN "Student_Enrolment" se ON se.degree_program_id = dp.degree_program_id
GROUP BY dp.degree_program_id, dp.degree_summary_name
```

---

## Skill `degree_program_enrolment_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `degree_program_id`, `degree_summary_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_7f8f6ba49c1f95ba |
| output columns | `degree_program_id`, `degree_summary_name`, `student_count` |
| source tables | `Degree_Programs`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-degree program counts of distinct currently enrolled students (one row per degree program with its id, summary, and student count).

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
    "question_id": "spider_dev_540",
    "question": "What is the program id and the summary of the degree that has the most students enrolled?",
    "rewrite": "Task: Find the program id and the degree summary for the single degree (program) that currently has the largest number of students enrolled.\nRequired outputs: program id (the identifier of the degree/program); summary of the degree (the summary/description text associated with that degree)\nFilters: Consider only degrees/programs for which there is a numeric count of currently enrolled students; determine the degree with the maximum such enrollment count; If multiple degrees tie for the maximum enrollment, return the program id and summary for all degrees that share that maximum\nSort/limit: order by enrollment count descending and limit to the maximum (i.e., return only rows whose enrollment equals the highest enrollment); no additional ordering required",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:02:27+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:02:30+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "degree_program_id",
      "degree_summary_name",
      "student_count"
    ],
    "row_count": 9,
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
        "purpose": "View has one row per degree_program_id + degree_summary_name (no duplicate keys)",
        "sql": "SELECT COUNT(*) FROM (SELECT degree_program_id, degree_summary_name, COUNT(*) AS cnt FROM degree_program_enrolment_counts GROUP BY degree_program_id, degree_summary_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count equals COUNT(DISTINCT student_id) from Student_Enrolment for that degree_program (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM degree_program_enrolment_counts v LEFT JOIN (SELECT degree_program_id, COUNT(DISTINCT student_id) AS expected_count FROM Student_Enrolment GROUP BY degree_program_id) s ON v.degree_program_id = s.degree_program_id WHERE COALESCE(v.student_count, -999999999) <> COALESCE(s.expected_count, -999999999)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row corresponds to an existing Degree_Programs row (join did not create phantom rows)",
        "sql": "SELECT COUNT(*) FROM degree_program_enrolment_counts v LEFT JOIN Degree_Programs dp ON v.degree_program_id = dp.degree_program_id AND (v.degree_summary_name = dp.degree_summary_name) WHERE dp.degree_program_id IS NULL",
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
SELECT dp.degree_program_id, dp.degree_summary_name, COUNT(DISTINCT se.student_id) AS student_count FROM "Degree_Programs" dp JOIN "Student_Enrolment" se ON se.degree_program_id = dp.degree_program_id GROUP BY dp.degree_program_id, dp.degree_summary_name
```

---

## Skill `student_enrollment_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `student_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_2df779bb80ec06de |
| output columns | `student_id`, `enrollment_count` |
| source tables | `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-student total enrollment counts across all enrollment records (one row per student with their id and enrollment count).

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
    "rewrite": "Task: Find the student (or students, if tied) who has the greatest number of enrollments in any program, returning that student's identifying information and the count of their enrollments.\nRequired outputs: id (the student's id); first name; middle name; last name; the number of enrollments (an integer count of how many times that student enrolled in any program); student id (the same student identifier as 'id' if the schema uses that term, include if schema has a separate student id field)\nFilters: Consider all enrollment records across all programs and all time; no date or program-type filtering unless the schema imposes constraints; Aggregate enrollments by student and count all enrollments associated with each student; Return only the student(s) whose enrollment count equals the maximum enrollment count among all students\nSort/limit: Order results by the number of enrollments in descending order; if multiple students tie for the maximum, include all tied students (no row limit)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:02:40+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:02:43+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "enrollment_count"
    ],
    "row_count": 8,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate student_id rows (grain uniqueness: one row per student_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id FROM student_enrollment_counts GROUP BY student_id HAVING COUNT(*) > 1) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "enrollment_count matches COUNT(*) from base table Student_Enrolment per student_id",
        "sql": "SELECT COUNT(*) FROM student_enrollment_counts sec LEFT JOIN (SELECT student_id, COUNT(*) AS expected_count FROM Student_Enrolment GROUP BY student_id) be ON sec.student_id = be.student_id WHERE (be.expected_count IS NULL AND sec.enrollment_count IS NOT NULL) OR (be.expected_count IS NOT NULL AND sec.enrollment_count != be.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_id in view is never NULL (key not NULL)",
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
SELECT student_id, COUNT(*) AS enrollment_count FROM Student_Enrolment GROUP BY student_id
```

---

## Skill `courses_with_any_enrollment`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `course_id`, `course_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_6c5f31951b3df1da |
| output columns | `course_id`, `course_name` |
| source tables | `Courses`, `Student_Enrolment_Courses`, `Student_Enrolment`, `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Distinct courses that have at least one linked student enrollment (i.e., courses referenced by any student enrollment record).

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
      "Student_Enrolment_Courses",
      "Student_Enrolment",
      "Students"
    ],
    "table_fingerprints": {
      "courses": "53e9befe1413d87f",
      "student_enrolment_courses": "daf1efe3c261d034",
      "student_enrolment": "445257138d420d03",
      "students": "ad3aee5be9cacc55"
    },
    "data_fingerprints": {
      "courses": "15:15",
      "student_enrolment_courses": "15:83814225",
      "student_enrolment": "15:15",
      "students": "15:15"
    },
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_545",
    "question": "What are all the course names of the courses which ever have students enrolled in?",
    "rewrite": "Task: Return the distinct names of all courses that have had at least one student enrolled at any time.\nRequired outputs: course_name: the name/title of each course (text)\nFilters: Include only courses for which there exists at least one enrollment/registration record linking a student to that course (i.e., courses with one or more students enrolled). Exclude courses with zero enrollments. No additional value filters (include all enrollment dates and statuses).\nSort/limit: No specific ordering required; no row limit",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:03:48+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:03:51+00:00",
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
        "join": "Student_Enrolment_Courses.course_id=Courses.course_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      },
      {
        "join": "Student_Enrolment.student_enrolment_id=Student_Enrolment_Courses.student_enrolment_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      },
      {
        "join": "Students.student_id=Student_Enrolment.student_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "View grain uniqueness: no duplicate (course_id, course_name) rows in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT course_id, course_name, COUNT(*) AS cnt FROM courses_with_any_enrollment GROUP BY course_id, course_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view refers to an existing Courses row (course_id must exist in Courses)",
        "sql": "SELECT COUNT(*) FROM courses_with_any_enrollment v LEFT JOIN Courses c ON v.course_id = c.course_id WHERE c.course_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View only includes courses that actually have at least one linked student enrollment via the join path (Courses -> Student_Enrolment_Courses -> Student_Enrolment -> Students)",
        "sql": "SELECT COUNT(*) FROM courses_with_any_enrollment v WHERE NOT EXISTS (SELECT 1 FROM Student_Enrolment_Courses sec JOIN Student_Enrolment se ON sec.student_enrolment_id = se.student_enrolment_id JOIN Students s ON se.student_id = s.student_id WHERE sec.course_id = v.course_id)",
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
JOIN Student_Enrolment_Courses sec ON sec.course_id = c.course_id
JOIN Student_Enrolment se ON se.student_enrolment_id = sec.student_enrolment_id
JOIN Students s ON s.student_id = se.student_id
```

---

## Skill `course_enrollment_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `course_id`, `course_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_60665dadf33cb2c5 |
| output columns | `course_id`, `course_name`, `enrollment_count` |
| source tables | `Courses`, `Student_Enrolment_Courses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-course enrollment counts by joining courses to student enrollment records, excluding courses with zero enrollments

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
    "rewrite": "Task: Find the course name that has the highest number of enrollments (i.e., the course with the maximum enrollment count).\nRequired outputs: course name (the name/title of the course); enrollment count (the number of enrollments for that course)\nFilters: consider all courses and their enrollment records; group enrollments by course and count them; include only courses that have at least one enrollment (exclude courses with zero enrollments)\nSort/limit: order by enrollment count descending, limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:04:33+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:04:36+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "course_id",
      "course_name",
      "enrollment_count"
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
        "purpose": "No duplicate rows per declared grain (course_id, course_name)",
        "sql": "SELECT COUNT(*) FROM (\n  SELECT course_id, course_name, COUNT(*) AS cnt FROM course_enrollment_counts GROUP BY course_id, course_name HAVING cnt > 1\n) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "enrollment_count matches COUNT of Student_Enrolment_Courses per course",
        "sql": "SELECT COUNT(*) FROM course_enrollment_counts cec\nLEFT JOIN Courses c ON cec.course_id = c.course_id\nWHERE (\n  (SELECT COUNT(*) FROM Student_Enrolment_Courses sec WHERE sec.course_id = cec.course_id) != cec.enrollment_count\n)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All view rows correspond to existing Courses and enrollment_count > 0 (no NULL keys and no zero/negative counts)",
        "sql": "SELECT COUNT(*) FROM course_enrollment_counts cec\nLEFT JOIN Courses c ON cec.course_id = c.course_id\nWHERE c.course_id IS NULL OR cec.course_id IS NULL OR cec.course_name IS NULL OR cec.enrollment_count <= 0",
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
SELECT c.course_id, c.course_name, COUNT(sec.student_course_id) AS enrollment_count FROM Courses c JOIN Student_Enrolment_Courses sec ON c.course_id = sec.course_id GROUP BY c.course_id, c.course_name HAVING COUNT(sec.student_course_id) > 0
```

---

## Skill `course_enrollment_counts_20`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `course_id`, `course_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_b3d9c8844f4b1e36 |
| output columns | `course_id`, `course_name`, `student_count` |
| source tables | `Courses`, `Student_Enrolment_Courses`, `Student_Enrolment`, `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-course counts of distinct students enrolled, joining courses to enrollments and students to compute enrollment counts for each course

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
      "Student_Enrolment_Courses",
      "Student_Enrolment",
      "Students"
    ],
    "table_fingerprints": {
      "courses": "53e9befe1413d87f",
      "student_enrolment_courses": "daf1efe3c261d034",
      "student_enrolment": "445257138d420d03",
      "students": "ad3aee5be9cacc55"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_548",
    "question": "What is the name of the course with the most students enrolled?",
    "rewrite": "Task: Find the name of the course that has the highest number of students enrolled\nRequired outputs: course name\nFilters: consider all courses present in the database; count students enrolled per course using the enrollment/registration relationship between students and courses\nSort/limit: order by student count descending, limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:05:16+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:05:19+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "course_id",
      "course_name",
      "student_count"
    ],
    "row_count": 10,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Student_Enrolment_Courses.course_id=Courses.course_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      },
      {
        "join": "Student_Enrolment.student_enrolment_id=Student_Enrolment_Courses.student_enrolment_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      },
      {
        "join": "Students.student_id=Student_Enrolment.student_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (course_id, course_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT course_id, course_name, COUNT(*) AS cnt FROM course_enrollment_counts_20 GROUP BY course_id, course_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count reconciles with distinct students computed from base tables for each course",
        "sql": "SELECT COUNT(*) FROM course_enrollment_counts_20 v LEFT JOIN (SELECT c.course_id, COUNT(DISTINCT s.student_id) AS expected_count FROM Courses c JOIN Student_Enrolment_Courses sec ON sec.course_id = c.course_id JOIN Student_Enrolment se ON se.student_enrolment_id = sec.student_enrolment_id JOIN Students s ON s.student_id = se.student_id GROUP BY c.course_id) b ON v.course_id = b.course_id WHERE (b.expected_count IS NULL AND v.student_count IS NOT NULL) OR (b.expected_count IS NOT NULL AND v.student_count <> b.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys course_id and course_name are not NULL in the view",
        "sql": "SELECT COUNT(*) FROM course_enrollment_counts_20 WHERE course_id IS NULL OR course_name IS NULL",
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
SELECT c.course_id, c.course_name, COUNT(DISTINCT s.student_id) AS student_count
FROM Courses c
JOIN Student_Enrolment_Courses sec ON sec.course_id = c.course_id
JOIN Student_Enrolment se ON se.student_enrolment_id = sec.student_enrolment_id
JOIN Students s ON s.student_id = se.student_id
GROUP BY c.course_id, c.course_name
```

---

## Skill `transcript_course_result_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `transcript_id`, `transcript_date` (keyed) |
| status / version | active / v1 |
| skill id | sk_5172af8fd3bd26fb |
| output columns | `transcript_id`, `transcript_date`, `course_result_count` |
| source tables | `Transcripts`, `Transcript_Contents` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-transcript counts of associated course result rows (one row per transcript with its id and date and the count of linked course results).

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
    "rewrite": "Task: Return rows for transcripts that have at least 2 associated course results, showing each transcript's date and id.\nRequired outputs: date (the transcript's date); id (the transcript's id)\nFilters: count of course results linked to the transcript >= 2",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:07:01+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:07:03+00:00",
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
        "purpose": "view has one row per transcript_id, transcript_date key (no duplicate keys)",
        "sql": "SELECT COUNT(*) FROM (SELECT transcript_id, transcript_date, COUNT(*) AS cnt FROM transcript_course_result_counts GROUP BY transcript_id, transcript_date HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "course_result_count matches count of linked Transcript_Contents rows",
        "sql": "SELECT COUNT(*) FROM transcript_course_result_counts v LEFT JOIN Transcripts t ON t.transcript_id = v.transcript_id LEFT JOIN Transcript_Contents tc ON tc.transcript_id = t.transcript_id GROUP BY v.transcript_id, v.transcript_date HAVING v.course_result_count != COUNT(tc.student_course_id) LIMIT 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "every view row refers to an existing transcript and the key columns are NOT NULL",
        "sql": "SELECT COUNT(*) FROM transcript_course_result_counts v LEFT JOIN Transcripts t ON t.transcript_id = v.transcript_id WHERE v.transcript_id IS NULL OR v.transcript_date IS NULL OR t.transcript_id IS NULL",
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
      "Task: Return the date and id of each transcript that lists at least 2 courses.\nRequired outputs: transcript.date; transcript.id\nFilters: transcript must be associated with two or more course entries (i.e., transcripts having count(courses) >= 2)"
    ],
    "last_used": "spider_dev_552"
  }
}
```

### Validated on (1)

- What is the date and id of the transcript with at least 2 courses listed?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT t.transcript_id AS transcript_id,
       t.transcript_date AS transcript_date,
       COUNT(tc.student_course_id) AS course_result_count
FROM Transcripts t
JOIN Transcript_Contents tc ON tc.transcript_id = t.transcript_id
GROUP BY t.transcript_id, t.transcript_date
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

Rows for students whose permanent address ID is present and different from their current address ID (keeps student identifier and address IDs for joins/filters).

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
    "rewrite": "Task: Find all persons whose permanent address is different from their current address and return each person's first name.\nRequired outputs: first name\nFilters: Select rows where the person's permanent address value is not equal to the person's current address value (i.e., permanent address <> current address).; Include all persons for whom both permanent and current address values are present (not NULL) unless schema allows comparison with NULL as unequal per DB semantics.",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:09:15+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:09:18+00:00",
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
        "purpose": "View rows must have permanent_address_id NOT NULL and current_address_id NOT NULL and they must be different",
        "sql": "SELECT COUNT(*) FROM students_with_different_permanent_and_current_address v WHERE v.permanent_address_id IS NULL OR v.current_address_id IS NULL OR v.permanent_address_id = v.current_address_id",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Grain/key uniqueness: student_id must be unique in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id FROM students_with_different_permanent_and_current_address GROUP BY student_id HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row must exist in base Students table with matching columns (detect incorrect joins or computed values)",
        "sql": "SELECT COUNT(*) FROM students_with_different_permanent_and_current_address v LEFT JOIN Students s ON s.student_id = v.student_id WHERE s.student_id IS NULL OR s.first_name != v.first_name OR s.permanent_address_id != v.permanent_address_id OR s.current_address_id != v.current_address_id",
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
      "Task: Find the first name of the student whose permanent address is different from his or her current address.\nRequired outputs: first name\nFilters: rows where permanent address != current address"
    ],
    "last_used": "spider_dev_560"
  }
}
```

### Validated on (1)

- What is the first name of the student whose permanent address is different from his or her current one?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT student_id, first_name, permanent_address_id, current_address_id FROM Students WHERE permanent_address_id IS NOT NULL AND current_address_id IS NOT NULL AND permanent_address_id <> current_address_id
```

---

## Skill `current_student_counts_by_address`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `address_id`, `line_1`, `line_2`, `line_3`, `city`, `zip_postcode`, `state_province_county`, `country`, `other_address_details` (keyed) |
| status / version | active / v1 |
| skill id | sk_f6dd055228b6fcc0 |
| output columns | `address_id`, `line_1`, `line_2`, `line_3`, `city`, `zip_postcode`, `state_province_county`, `country`, `other_address_details`, `student_count` |
| source tables | `Addresses`, `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-address counts of students whose enrollment is currently active, together with the address line fields for joining or reporting.

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
    "question_id": "spider_dev_561",
    "question": "Which address holds the most number of students currently? List the address id and all lines.",
    "rewrite": "Task: Find the address that currently has the largest number of students living at it, and return that address's id and all address line fields.\nRequired outputs: address id; all address lines (every column in the address record that represents lines of the address)\nFilters: Consider only students who are currently enrolled (i.e., count each student who is active/current as of now).; Count a student at the address where the student's current address is recorded (use the student's current address association).; Only include addresses that have at least one current student.\nSort/limit: order results by descending student count and return the top 1 address (if multiple addresses tie for the maximum, return all addresses that share that maximum count)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:09:44+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:09:48+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "address_id",
      "line_1",
      "line_2",
      "line_3",
      "city",
      "zip_postcode",
      "state_province_county",
      "country",
      "other_address_details",
      "student_count"
    ],
    "row_count": 0,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Students.current_address_id=Addresses.address_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "View rows should be unique at the declared grain (no duplicate address key combos)",
        "sql": "SELECT COUNT(*) FROM current_student_counts_by_address v JOIN (SELECT address_id, line_1, line_2, line_3, city, zip_postcode, state_province_county, country, other_address_details, COUNT(*) AS ct FROM current_student_counts_by_address GROUP BY address_id, line_1, line_2, line_3, city, zip_postcode, state_province_county, country, other_address_details HAVING ct > 1) dup ON v.address_id = dup.address_id AND v.line_1 = dup.line_1 AND v.line_2 = dup.line_2 AND v.line_3 = dup.line_3 AND v.city = dup.city AND v.zip_postcode = dup.zip_postcode AND v.state_province_county = dup.state_province_county AND v.country = dup.country AND v.other_address_details = dup.other_address_details",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count should equal the number of active students (date_left IS NULL) in base tables for that address",
        "sql": "SELECT COUNT(*) FROM current_student_counts_by_address v LEFT JOIN (SELECT s.current_address_id AS address_id, COUNT(s.student_id) AS expected_count FROM Students s WHERE s.date_left IS NULL GROUP BY s.current_address_id) b ON v.address_id = b.address_id WHERE COALESCE(b.expected_count,0) != COALESCE(v.student_count,0)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's address_id in the view must reference an existing Addresses row (no dangling FK after join)",
        "sql": "SELECT COUNT(*) FROM current_student_counts_by_address v LEFT JOIN Addresses a ON v.address_id = a.address_id WHERE a.address_id IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 2
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT a.address_id,
       a.line_1,
       a.line_2,
       a.line_3,
       a.city,
       a.zip_postcode,
       a.state_province_county,
       a.country,
       a.other_address_details,
       COUNT(s.student_id) AS student_count
FROM Addresses a
JOIN Students s ON s.current_address_id = a.address_id
WHERE s.date_left IS NULL
GROUP BY a.address_id, a.line_1, a.line_2, a.line_3, a.city, a.zip_postcode, a.state_province_county, a.country, a.other_address_details
```

---

## Skill `students_per_address`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `address_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_919376681de32753 |
| output columns | `address_id`, `student_count` |
| source tables | `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Counts how many student-address associations exist per address id, treating current and permanent addresses as separate associations (useful to find address cohorts or top addresses by student count).

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
      "Students"
    ],
    "table_fingerprints": {
      "students": "ad3aee5be9cacc55"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_562",
    "question": "What is the id, line 1, and line 2 of the address with the most students?",
    "rewrite": "Task: Find the address (its id, line 1, and line 2) that has the largest number of students associated with it.\nRequired outputs: id; line 1; line 2\nFilters: Consider each distinct address and count how many students are associated with that address; choose the address with the maximum student count; if there are ties, return all addresses that share the maximum count.",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:09:56+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:09:58+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "address_id",
      "student_count"
    ],
    "row_count": 14,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate address_id rows in the view (grain uniqueness): view should have at most one row per address_id",
        "sql": "SELECT COUNT(*) FROM (SELECT address_id, COUNT(*) AS c FROM students_per_address GROUP BY address_id HAVING c > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count matches count of student-address associations in base table (recomputed via UNION ALL)",
        "sql": "SELECT COUNT(*) FROM students_per_address v LEFT JOIN (SELECT address_id, COUNT(*) AS expected_count FROM (SELECT current_address_id AS address_id FROM Students WHERE current_address_id IS NOT NULL UNION ALL SELECT permanent_address_id AS address_id FROM Students WHERE permanent_address_id IS NOT NULL) t GROUP BY address_id) b ON v.address_id = b.address_id WHERE b.expected_count IS NULL OR v.student_count != b.expected_count",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "address_id is never NULL in the view",
        "sql": "SELECT COUNT(*) FROM students_per_address WHERE address_id IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 2
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT address_id, COUNT(*) AS student_count
FROM (
  SELECT current_address_id AS address_id FROM Students WHERE current_address_id IS NOT NULL
  UNION ALL
  SELECT permanent_address_id AS address_id FROM Students WHERE permanent_address_id IS NOT NULL
) t
GROUP BY address_id
```

---

## Skill `transcript_release_dates_agg`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | — (scalar) |
| status / version | active / v1 |
| skill id | sk_5d6f71b1c210e7c9 |
| output columns | `last_transcript_release_date` |
| source tables | `Transcripts` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-dataset aggregate of transcript release dates providing the maximum (most recent) non-null transcript release date across all transcript records.

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
    "question_id": "spider_dev_569",
    "question": "What is the last transcript release date?",
    "rewrite": "Task: Find the most recent (latest) transcript release date from the transcripts data.\nRequired outputs: last_transcript_release_date (the single latest date on which a transcript was released)\nFilters: no additional filters unless transcript records include a release date field; consider only rows where a transcript release date is present (non-null)\nSort/limit: order by release date descending, limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:12:42+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:12:45+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "last_transcript_release_date"
    ],
    "row_count": 1,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View returns exactly one row (scalar grain)",
        "sql": "SELECT CASE WHEN (SELECT COUNT(*) FROM transcript_release_dates_agg)=1 THEN 0 ELSE 1 END",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "last_transcript_release_date equals the MAX(transcript_date) computed from base table (reconciliation of measure)",
        "sql": "SELECT CASE WHEN (SELECT last_transcript_release_date FROM transcript_release_dates_agg) IS (SELECT MAX(transcript_date) FROM Transcripts WHERE transcript_date IS NOT NULL) THEN 0 ELSE 1 END",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "If there are no non-NULL transcript_date values, the view's last_transcript_release_date must be NULL",
        "sql": "SELECT CASE WHEN (SELECT COUNT(*) FROM Transcripts WHERE transcript_date IS NOT NULL)=0 AND (SELECT last_transcript_release_date FROM transcript_release_dates_agg) IS NOT NULL THEN 1 WHEN (SELECT COUNT(*) FROM Transcripts WHERE transcript_date IS NOT NULL)>0 AND (SELECT last_transcript_release_date FROM transcript_release_dates_agg) IS NULL THEN 1 ELSE 0 END",
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
      "Task: Find the release date of the most recently released transcript.\nRequired outputs: transcript release date (the date when a transcript was released)\nFilters: rows must represent transcripts where a release date is present (non-null)\nSort/limit: order by release date descending limit 1"
    ],
    "last_used": "spider_dev_570"
  }
}
```

### Validated on (1)

- When was the last transcript released?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT MAX(transcript_date) AS last_transcript_release_date FROM Transcripts WHERE transcript_date IS NOT NULL
```

---

## Skill `transcript_max_release_date`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | — (scalar) |
| status / version | active / v1 |
| skill id | sk_68b09b468ef9cffb |
| output columns | `max_transcript_release_date` |
| source tables | `Transcripts` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-dataset aggregate providing the most recent non-null transcript release date across all Transcripts.

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
    "question_id": "spider_dev_570",
    "question": "When was the last transcript released?",
    "rewrite": "Task: Find the release date of the most recently released transcript.\nRequired outputs: transcript release date (the date when a transcript was released)\nFilters: rows must represent transcripts where a release date is present (non-null)\nSort/limit: order by release date descending limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:12:58+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:13:01+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "max_transcript_release_date"
    ],
    "row_count": 1,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View returns at most one row (scalar grain)",
        "sql": "SELECT CASE WHEN (SELECT COUNT(*) FROM transcript_max_release_date) <= 1 THEN 0 ELSE (SELECT COUNT(*) FROM transcript_max_release_date) END",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows in view have max_transcript_release_date equal to MAX(transcript_date) from base table (measure reconciles)",
        "sql": "SELECT CASE WHEN (SELECT COUNT(*) FROM transcript_max_release_date WHERE (max_transcript_release_date IS NOT (SELECT MAX(transcript_date) FROM Transcripts WHERE transcript_date IS NOT NULL))) = 0 THEN 0 ELSE (SELECT COUNT(*) FROM transcript_max_release_date WHERE (max_transcript_release_date IS NOT (SELECT MAX(transcript_date) FROM Transcripts WHERE transcript_date IS NOT NULL))) END",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View does not produce a non-NULL max_transcript_release_date when there are no non-NULL transcript_date values in base table (should be zero rows or NULL)",
        "sql": "SELECT CASE WHEN (SELECT COUNT(*) FROM Transcripts WHERE transcript_date IS NOT NULL)=0 THEN (SELECT CASE WHEN (SELECT COUNT(*) FROM transcript_max_release_date WHERE max_transcript_release_date IS NULL)= (SELECT COUNT(*) FROM transcript_max_release_date) THEN 0 ELSE (SELECT COUNT(*) FROM transcript_max_release_date WHERE NOT (max_transcript_release_date IS NULL)) END) ELSE 0 END",
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
SELECT MAX(transcript_date) AS max_transcript_release_date FROM Transcripts WHERE transcript_date IS NOT NULL
```

---

## Skill `transcript_course_appearance_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `enrollment_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_6ac34e95b8d41907 |
| output columns | `enrollment_id`, `transcript_appearance_count` |
| source tables | `Transcript_Contents` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-course counts of distinct transcripts in which each enrollment (student_course_id) appears, excluding null enrollment ids.

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
    "question_id": "spider_dev_572",
    "question": "What is the maximum number of times that a course shows up in different transcripts and what is that course's enrollment id?",
    "rewrite": "Task: Find the course (identified by its enrollment id) that appears the maximum number of times across different transcripts and report that maximum count along with the enrollment id of that course.\nRequired outputs: max_count: the maximum number of transcript appearances for any single course (integer); enrollment_id: the enrollment id of the course that has that maximum count (value as appears in data)\nFilters: Consider each occurrence of a course within a transcript as one appearance; count distinct transcript occurrences per course.; Exclude null or missing enrollment id values from consideration.\nSort/limit: order by max_count desc limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:13:21+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:13:24+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "enrollment_id",
      "transcript_appearance_count"
    ],
    "row_count": 9,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No NULL enrollment_id in view (intrinsic filter enforced)",
        "sql": "SELECT COUNT(*) FROM transcript_course_appearance_counts WHERE enrollment_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each row's transcript_appearance_count equals COUNT(DISTINCT transcript_id) from base table for that enrollment_id",
        "sql": "SELECT COUNT(*) FROM transcript_course_appearance_counts v JOIN (SELECT tc.student_course_id AS enrollment_id, COUNT(DISTINCT tc.transcript_id) AS expected_count FROM Transcript_Contents tc WHERE tc.student_course_id IS NOT NULL GROUP BY tc.student_course_id) b ON v.enrollment_id = b.enrollment_id WHERE v.transcript_appearance_count != b.expected_count",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View contains exactly one row per enrollment_id present in base table (no missing or duplicate rows)",
        "sql": "SELECT (SELECT COUNT(*) FROM (SELECT DISTINCT student_course_id AS enrollment_id FROM Transcript_Contents WHERE student_course_id IS NOT NULL)) - (SELECT COUNT(*) FROM (SELECT DISTINCT enrollment_id FROM transcript_course_appearance_counts)) AS diff",
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
SELECT tc.student_course_id AS enrollment_id, COUNT(DISTINCT tc.transcript_id) AS transcript_appearance_count FROM Transcript_Contents tc WHERE tc.student_course_id IS NOT NULL GROUP BY tc.student_course_id
```

---

## Skill `transcript_with_result_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `transcript_id`, `transcript_date` (keyed) |
| status / version | active / v1 |
| skill id | sk_af8be18cc05cb29b |
| output columns | `transcript_id`, `transcript_date`, `num_results` |
| source tables | `Transcripts`, `Transcript_Contents` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-transcript row with the transcript date, id, and the count of associated transcript content rows (number of results) for reuse in queries that need per-transcript result counts or to find minima/maxima.

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
    "question_id": "spider_dev_573",
    "question": "Show the date of the transcript which shows the least number of results, also list the id.",
    "rewrite": "Task: Find the transcript date (date of the transcript) and the corresponding id for the transcript record that has the smallest value in its 'number of results' field.\nRequired outputs: transcript date (the date of the transcript); id (the id of that transcript record)\nFilters: Consider only transcript records present in the data.; Select the record(s) with the minimum value of the 'number of results' field (i.e., the least number of results). If multiple transcripts tie for the minimum number of results, include any one of them or all tied records depending on downstream query semantics.\nSort/limit: order by 'number of results' ascending, limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:13:35+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:13:38+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "transcript_id",
      "transcript_date",
      "num_results"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Transcripts.transcript_id=Transcript_Contents.transcript_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (transcript_id, transcript_date)",
        "sql": "SELECT COUNT(*) FROM (SELECT transcript_id, transcript_date, COUNT(*) AS cnt FROM transcript_with_result_counts GROUP BY transcript_id, transcript_date HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "num_results matches count of Transcript_Contents per transcript (including transcripts with zero contents)",
        "sql": "SELECT COUNT(*) FROM transcript_with_result_counts v LEFT JOIN Transcripts t ON v.transcript_id = t.transcript_id AND v.transcript_date = t.transcript_date WHERE (SELECT COUNT(*) FROM Transcript_Contents tc WHERE tc.transcript_id = v.transcript_id) != v.num_results",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL: transcript_id and transcript_date must be present for every row",
        "sql": "SELECT COUNT(*) FROM transcript_with_result_counts WHERE transcript_id IS NULL OR transcript_date IS NULL",
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
    "negative": 1,
    "negative_subgoals": [
      "Task: Find the transcript that has the smallest value in its 'results' field and return that transcript's date and id.\nRequired outputs: date; id\nFilters: consider only rows where 'results' is not NULL; if multiple transcripts tie for the smallest 'results' value, return all tied transcripts' date and id\nSort/limit: order by results ASC; no fixed limit (return all ties for the minimum)"
    ],
    "last_used": "spider_dev_574"
  }
}
```

### Validated on (0)

—

### Counter-examples (1)

- What is the date and id of the transcript with the least number of results?

### Executable SQL body

```sql
SELECT t.transcript_id, t.transcript_date, COUNT(tc.student_course_id) AS num_results
FROM Transcripts t
LEFT JOIN Transcript_Contents tc ON t.transcript_id = tc.transcript_id
GROUP BY t.transcript_id, t.transcript_date
```

---

## Skill `semester_enrolment_by_degree_level`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `semester_id`, `semester_name`, `degree_level` (keyed) |
| status / version | active / v1 |
| skill id | sk_d8a14beec5be9533 |
| output columns | `semester_id`, `semester_name`, `degree_level` |
| source tables | `Semesters`, `Student_Enrolment`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each semester and degree program level, indicates that there is at least one student enrolment (cohort of semester × degree level)

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
      "Master",
      "Bachelor"
    ],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "Semesters",
      "Student_Enrolment",
      "Degree_Programs"
    ],
    "table_fingerprints": {
      "semesters": "29c2494a0d4e0c8e",
      "student_enrolment": "445257138d420d03",
      "degree_programs": "85466a54c4a97bc7"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_575",
    "question": "Find the semester when both Master students and Bachelor students got enrolled in.",
    "rewrite": "Task: Return the semester(s) in which both Master students and Bachelor students were enrolled.\nRequired outputs: semester (the semester identifier/value)\nFilters: include only semesters for which there exists at least one enrolled student whose degree/program level is Master and at least one enrolled student whose degree/program level is Bachelor",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:14:04+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:14:07+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "semester_id",
      "semester_name",
      "degree_level"
    ],
    "row_count": 10,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Student_Enrolment.semester_id=Semesters.semester_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      },
      {
        "join": "Student_Enrolment.degree_program_id=Degree_Programs.degree_program_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (semester_id, semester_name, degree_level)",
        "sql": "SELECT COUNT(*) FROM (SELECT semester_id, semester_name, degree_level, COUNT(*) AS cnt FROM semester_enrolment_by_degree_level GROUP BY semester_id, semester_name, degree_level HAVING cnt > 1) t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row corresponds to at least one underlying enrolment (no phantom cohort rows): ensure there exists a Student_Enrolment and Degree_Programs match for each view row",
        "sql": "SELECT COUNT(*) FROM semester_enrolment_by_degree_level v WHERE NOT EXISTS (SELECT 1 FROM Student_Enrolment se JOIN Degree_Programs dp ON se.degree_program_id = dp.degree_program_id JOIN Semesters s ON se.semester_id = s.semester_id WHERE s.semester_id = v.semester_id AND s.semester_name = v.semester_name AND dp.degree_summary_name = v.degree_level)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL: none of the key columns should be NULL",
        "sql": "SELECT COUNT(*) FROM semester_enrolment_by_degree_level WHERE semester_id IS NULL OR semester_name IS NULL OR degree_level IS NULL",
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
SELECT s.semester_id, s.semester_name, dp.degree_summary_name AS degree_level
FROM Semesters s
JOIN Student_Enrolment se ON se.semester_id = s.semester_id
JOIN Degree_Programs dp ON se.degree_program_id = dp.degree_program_id
GROUP BY s.semester_id, s.semester_name, dp.degree_summary_name
```

---

## Skill `semester_enrolment_by_degree_summary`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `semester_id`, `degree_summary_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_69eef9d3942da568 |
| output columns | `semester_id`, `degree_summary_name` |
| source tables | `Student_Enrolment`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each semester and degree summary name, indicates that at least one student enrolment exists (one row per semester and degree_summary_name). Useful to know which degree types had enrolments in which semesters.

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
      "Masters",
      "Bachelors"
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
    "rewrite": "Task: Return the id of the semester that had both Masters and Bachelors students enrolled.\nRequired outputs: semester id\nFilters: semester must have at least one enrolled student with degree = 'Masters' AND at least one enrolled student with degree = 'Bachelors'",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:14:17+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:14:20+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "semester_id",
      "degree_summary_name"
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
        "purpose": "No duplicate rows at the declared grain (semester_id, degree_summary_name). Ensures the view groups correctly and returns unique pairs.",
        "sql": "SELECT COUNT(*) FROM (SELECT semester_id, degree_summary_name, COUNT(*) AS cnt FROM semester_enrolment_by_degree_summary GROUP BY semester_id, degree_summary_name) t WHERE t.cnt > 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view corresponds to at least one Student_Enrolment joined to a Degree_Programs row (no phantom rows).",
        "sql": "SELECT COUNT(*) FROM semester_enrolment_by_degree_summary v LEFT JOIN Student_Enrolment se ON v.semester_id = se.semester_id LEFT JOIN Degree_Programs dp ON v.degree_summary_name = dp.degree_summary_name WHERE se.student_enrolment_id IS NULL OR dp.degree_program_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys in the view are NOT NULL: semester_id and degree_summary_name must be present for every row.",
        "sql": "SELECT COUNT(*) FROM semester_enrolment_by_degree_summary WHERE semester_id IS NULL OR degree_summary_name IS NULL",
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
SELECT se.semester_id, dp.degree_summary_name
FROM Student_Enrolment se
JOIN Degree_Programs dp ON se.degree_program_id = dp.degree_program_id
GROUP BY se.semester_id, dp.degree_summary_name
```

---

## Skill `students_current_residence`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `student_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_770d800a30bf1a2d |
| output columns | `student_id`, `current_address_id` |
| source tables | `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-student current residence identifiers indicating where each student currently lives, for use in counts or joins to address data.

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
    "question_id": "spider_dev_577",
    "question": "How many different addresses do the students currently live?",
    "rewrite": "Task: Count the number of distinct addresses at which students currently live.\nRequired outputs: a single numeric value representing the count of different addresses where students currently live\nFilters: only consider students who 'currently live' (i.e., the current residence status) — exclude any past or future residences",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:14:34+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:14:36+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "current_address_id"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View has one row per student_id (no duplicate student_id in the view)",
        "sql": "SELECT COUNT(*) FROM students_current_residence v JOIN (SELECT student_id, COUNT(*) AS c FROM students_current_residence GROUP BY student_id HAVING c > 1) dup USING (student_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view references a non-NULL current_address_id (intrinsic filter preserved)",
        "sql": "SELECT COUNT(*) FROM students_current_residence WHERE current_address_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View rows match base table: every row in view exists in Students with same student_id and current_address_id",
        "sql": "SELECT COUNT(*) FROM students_current_residence v LEFT JOIN Students s ON v.student_id = s.student_id AND (v.current_address_id IS s.current_address_id OR (v.current_address_id IS NULL AND s.current_address_id IS NULL)) WHERE s.student_id IS NULL",
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
SELECT student_id, current_address_id
FROM Students
WHERE current_address_id IS NOT NULL
```

---

## Skill `addresses_with_students`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `address_id`, `address` (keyed) |
| status / version | active / v1 |
| skill id | sk_31aa496cf2c13dfb |
| output columns | `address_id`, `address` |
| source tables | `Addresses`, `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Distinct addresses that are referenced by one or more students as a current or permanent residence (address_id and denormalized address string).

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
    "rewrite": "Task: List the distinct addresses that have at least one student living at them.\nRequired outputs: address (the address string or identifier for a residence where students live)\nFilters: include only addresses that are associated with one or more students (i.e., there exists a student record indicating that address as their residence)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:14:53+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:14:55+00:00",
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
        "purpose": "No duplicate rows at the declared grain (address_id, address) — ensure view rows are unique",
        "sql": "SELECT COUNT(*) FROM (SELECT address_id, address, COUNT(*) as cnt FROM addresses_with_students GROUP BY address_id, address HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row corresponds to an Addresses.address_id that is referenced by at least one student as current or permanent address",
        "sql": "SELECT COUNT(*) FROM addresses_with_students v WHERE NOT EXISTS (SELECT 1 FROM Students s WHERE s.current_address_id IS NOT NULL AND s.current_address_id = v.address_id OR s.permanent_address_id IS NOT NULL AND s.permanent_address_id = v.address_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "address_id in the view is never NULL (key not null)",
        "sql": "SELECT COUNT(*) FROM addresses_with_students WHERE address_id IS NULL",
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
SELECT DISTINCT A.address_id, COALESCE(A.line_1, '') || CASE WHEN A.line_2 IS NOT NULL AND A.line_2 <> '' THEN ', ' || A.line_2 ELSE '' END || CASE WHEN A.line_3 IS NOT NULL AND A.line_3 <> '' THEN ', ' || A.line_3 ELSE '' END || CASE WHEN A.city IS NOT NULL AND A.city <> '' THEN ', ' || A.city ELSE '' END || CASE WHEN A.state_province_county IS NOT NULL AND A.state_province_county <> '' THEN ', ' || A.state_province_county ELSE '' END || CASE WHEN A.zip_postcode IS NOT NULL AND A.zip_postcode <> '' THEN ' ' || A.zip_postcode ELSE '' END || CASE WHEN A.country IS NOT NULL AND A.country <> '' THEN ', ' || A.country ELSE '' END AS address FROM Addresses A WHERE A.address_id IN (SELECT current_address_id FROM Students WHERE current_address_id IS NOT NULL UNION SELECT permanent_address_id FROM Students WHERE permanent_address_id IS NOT NULL)
```

---

## Skill `students_with_address_country`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `student_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_5a4cc63f49c89449 |
| output columns | `student_id`, `first_name`, `cell_mobile_number`, `address_id`, `country` |
| source tables | `Students`, `Addresses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

A denormalized relation listing students paired with the country of their associated address, allowing filtering of students by address country or joining on address attributes.

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
      "Haiti",
      "09700166582"
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
    "question_id": "spider_dev_584",
    "question": "What are the first names of the students who live in Haiti permanently or have the cell phone number 09700166582 ?",
    "rewrite": "Task: Select the first names of all students who either have their permanent residence listed as 'Haiti' or have the cell phone number '09700166582'.\nRequired outputs: first_name — the student's first name (one value per matching student)\nFilters: Include rows where the student's permanent residence equals the literal string 'Haiti'.; Include rows where the student's cell phone number equals the literal string '09700166582'.; Return each matching student (if a student meets both conditions, include them only once).",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T06:16:20+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T06:16:22+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "first_name",
      "cell_mobile_number",
      "address_id",
      "country"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Students.permanent_address_id=Addresses.address_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "Ensure view has exactly one row per student_id (no duplicate student_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id FROM students_with_address_country GROUP BY student_id HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Ensure every row's address_id exists in Addresses and matches country returned (join didn't introduce addresses that don't exist or mismatched country)",
        "sql": "SELECT COUNT(*) FROM students_with_address_country v LEFT JOIN Addresses a ON v.address_id = a.address_id WHERE a.address_id IS NULL OR (a.country IS NOT NULL AND a.country != v.country)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Ensure student_id is not NULL and corresponds to an existing Students row (key non-null and join didn't duplicate/misassign)",
        "sql": "SELECT COUNT(*) FROM students_with_address_country v LEFT JOIN Students s ON v.student_id = s.student_id WHERE v.student_id IS NULL OR s.student_id IS NULL",
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
SELECT s.student_id, s.first_name, s.cell_mobile_number, a.address_id, a.country
FROM Students s
JOIN Addresses a ON s.permanent_address_id = a.address_id
```

---
