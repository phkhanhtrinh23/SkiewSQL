# Skill graph — `student_transcripts_tracking` (30 skills)

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

Per-department count of degree programs (includes departments with zero degrees)

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Departments",
      "Degree_Programs"
    ],
    "source_columns": [
      "Departments.department_id",
      "Departments.department_name",
      "Degree_Programs.degree_program_id",
      "Degree_Programs.department_id"
    ],
    "output_lineage": {
      "department_id": [
        "Departments.department_id"
      ],
      "department_name": [
        "Departments.department_name"
      ],
      "degree_count": [
        "Degree_Programs.degree_program_id"
      ]
    },
    "operators": [
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "departments": "188d438ee9ba34ad",
      "degree_programs": "85466a54c4a97bc7"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_515",
    "question": "Which department offers the most number of degrees? List department name and id.",
    "rewrite": "Task: Find the department (its name and its id) that offers the largest number of degrees.\nRequired outputs: department name; department id\nFilters: Consider all departments present in the database; count degrees associated with each department; if a department has zero degrees it is counted as zero.\nSort/limit: order by degree count descending and return only the top row (limit 1); if there are ties, return all departments that share the maximum count",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:00:51+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:00:53+00:00",
    "contract_version": 3,
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
        "purpose": "Every row's degree_count matches the count of Degree_Programs for that department (including zeroes)",
        "sql": "SELECT COUNT(*) FROM department_degree_counts ddc LEFT JOIN (SELECT department_id AS did, COUNT(*) AS expected_count FROM Degree_Programs GROUP BY department_id) dp ON ddc.department_id = dp.did WHERE COALESCE(dp.expected_count, 0) != ddc.degree_count",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL (department_id and department_name must be present)",
        "sql": "SELECT COUNT(*) FROM department_degree_counts WHERE department_id IS NULL OR department_name IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 4,
    "selected": 2,
    "included": 1,
    "referenced": 1,
    "executed": 1,
    "inconclusive": 1,
    "positive": 1,
    "positive_subgoals": [
      "Task: Count the number of distinct departments that offer any degree (i.e., departments that have at least one degree associated with them).\nRequired outputs: an integer count named e.g. department_count representing the number of departments that offer any degree\nFilters: include only departments that are associated with one or more degrees (exclude departments with zero degrees)"
    ],
    "last_used": "spider_dev_517"
  }
}
```

### Validated on (1)

- How many departments offer any degree?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT d.department_id, d.department_name, COUNT(dp.degree_program_id) AS degree_count FROM Departments d LEFT JOIN Degree_Programs dp ON d.department_id = dp.department_id GROUP BY d.department_id, d.department_name
```

---

## Skill `department_degree_counts_3`

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

Per-department counts of linked degree programs (department id and name with the number of degrees associated)

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Departments",
      "Degree_Programs"
    ],
    "source_columns": [
      "Departments.department_id",
      "Departments.department_name",
      "Degree_Programs.degree_program_id",
      "Degree_Programs.department_id"
    ],
    "output_lineage": {
      "department_id": [
        "Departments.department_id"
      ],
      "department_name": [
        "Departments.department_name"
      ],
      "degree_count": [
        "Degree_Programs.degree_program_id"
      ]
    },
    "operators": [
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "departments": "188d438ee9ba34ad",
      "degree_programs": "85466a54c4a97bc7"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_516",
    "question": "What is the name and id of the department with the most number of degrees ?",
    "rewrite": "Task: Find the department (its name and id) that has the largest number of degrees associated with it.\nRequired outputs: department name; department id\nFilters: Consider all departments and count the number of degrees linked to each department; no other filters (use all rows).; If multiple departments tie for the maximum number of degrees, return all such departments.\nSort/limit: order by degree count descending, limit to the maximum count (i.e., return department(s) whose degree count equals the highest count)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:01:05+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:01:07+00:00",
    "contract_version": 3,
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
        "purpose": "No duplicate rows per grain (department_id, department_name) in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT department_id, department_name, COUNT(*) AS cnt FROM department_degree_counts_3 GROUP BY department_id, department_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "degree_count matches count of Degree_Programs rows linked to each department (recompute aggregation from base tables)",
        "sql": "SELECT COUNT(*) FROM department_degree_counts_3 v LEFT JOIN (SELECT department_id, COUNT(degree_program_id) AS expected_count FROM Degree_Programs GROUP BY department_id) dp ON COALESCE(v.department_id, -999999) = COALESCE(dp.department_id, -999999) WHERE COALESCE(v.degree_count, 0) != COALESCE(dp.expected_count, 0)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "department_id and department_name are not NULL (keys must be present)",
        "sql": "SELECT COUNT(*) FROM department_degree_counts_3 WHERE department_id IS NULL OR department_name IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 4
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT d.department_id, d.department_name, COUNT(dp.degree_program_id) AS degree_count FROM Departments d LEFT JOIN Degree_Programs dp ON dp.department_id = d.department_id GROUP BY d.department_id, d.department_name
```

---

## Skill `departments_offering_degrees`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `department_id`, `department_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_53d4d30cc3093346 |
| output columns | `department_id`, `department_name` |
| source tables | `Departments`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Distinct departments (by name and id) that are linked to at least one degree program

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Departments",
      "Degree_Programs"
    ],
    "source_columns": [
      "Departments.department_id",
      "Departments.department_name",
      "Degree_Programs.department_id"
    ],
    "output_lineage": {
      "department_id": [
        "Departments.department_id"
      ],
      "department_name": [
        "Departments.department_name"
      ]
    },
    "operators": [
      "filter",
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "departments": "188d438ee9ba34ad",
      "degree_programs": "85466a54c4a97bc7"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_518",
    "question": "How many different departments offer degrees?",
    "rewrite": "Task: Count the number of distinct departments that offer degrees\nRequired outputs: a single integer value representing the count of distinct departments that offer one or more degrees\nFilters: consider only records where a department is listed as offering a degree (i.e., exclude null/empty department identifiers or names); treat departments with the same name as the same department (i.e., count distinct department names)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:01:44+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:01:46+00:00",
    "contract_version": 3,
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
        "join": "Degree_Programs.department_id=Departments.department_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate department rows at the declared grain (department_id, department_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT department_id, department_name, COUNT(*) AS cnt FROM departments_offering_degrees GROUP BY department_id, department_name HAVING cnt > 1) t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view has a non-NULL, non-empty department_name and non-NULL department_id (intrinsic filters respected)",
        "sql": "SELECT COUNT(*) FROM departments_offering_degrees WHERE department_id IS NULL OR department_name IS NULL OR TRIM(department_name) = ''",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every department in the view actually has at least one matching Degree_Programs row (the join did not introduce spurious departments)",
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
SELECT d.department_id, d.department_name
FROM Departments d
JOIN Degree_Programs dp ON dp.department_id = d.department_id
WHERE d.department_id IS NOT NULL
  AND d.department_name IS NOT NULL
  AND TRIM(d.department_name) <> ''
GROUP BY d.department_id, d.department_name
```

---

## Skill `course_section_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `course_id`, `course_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_0eb5d7fb1deded3c |
| output columns | `course_id`, `course_name`, `section_count` |
| source tables | `Courses`, `Sections` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-course total count of associated sections (includes courses with zero sections).

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Courses",
      "Sections"
    ],
    "source_columns": [
      "Courses.course_id",
      "Courses.course_name",
      "Sections.course_id",
      "Sections.section_id"
    ],
    "output_lineage": {
      "course_id": [
        "Courses.course_id"
      ],
      "course_name": [
        "Courses.course_name"
      ],
      "section_count": [
        "Sections.section_id"
      ]
    },
    "operators": [
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "courses": "53e9befe1413d87f",
      "sections": "33c74073d124c41c"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_525",
    "question": "What are the names and id of courses having at most 2 sections?",
    "rewrite": "Task: Return the course names and ids for every course that has at most 2 sections.\nRequired outputs: course id; course name\nFilters: Include only courses whose total number of associated sections is less than or equal to 2; Count sections per course across the sections relation (treat courses with zero sections as having 0 sections and include them); Do not include any other columns",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:03:33+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:03:36+00:00",
    "contract_version": 3,
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
        "sql": "SELECT COUNT(*) FROM (SELECT course_id, course_name, COUNT(*) AS cnt FROM course_section_counts GROUP BY course_id, course_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every course in Courses appears exactly once in the view (includes courses with zero sections)",
        "sql": "SELECT COUNT(*) FROM Courses c LEFT JOIN course_section_counts v ON c.course_id = v.course_id AND c.course_name = v.course_name WHERE v.course_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "section_count reconciles with base tables (count of Sections per course, treating NULL as 0)",
        "sql": "SELECT COUNT(*) FROM course_section_counts v LEFT JOIN Courses c ON v.course_id = c.course_id LEFT JOIN Sections s ON c.course_id = s.course_id GROUP BY v.course_id, v.course_name HAVING v.section_count != (SELECT COUNT(s2.section_id) FROM Sections s2 WHERE s2.course_id = v.course_id) LIMIT 1",
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
      "Task: Return the name and id for every course that has fewer than 2 sections (i.e., courses with 0 or 1 associated section).\nRequired outputs: course name; course id\nFilters: Include only courses whose count of associated sections is < 2 (that is, courses with 0 or 1 section).; Do not include courses with 2 or more sections."
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
SELECT c.course_id, c.course_name, COALESCE(COUNT(s.section_id), 0) AS section_count
FROM "Courses" c
LEFT JOIN "Sections" s ON c.course_id = s.course_id
GROUP BY c.course_id, c.course_name
```

---

## Skill `semester_registration_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `semester_id`, `semester_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_3947b887299d78c4 |
| output columns | `semester_id`, `semester_name`, `registration_count` |
| source tables | `Student_Enrolment`, `Semesters` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Counts of student registrations per semester by joining Student_Enrolment to Semesters, producing one row per semester with the semester id, semester name, and the number of enrolment records associated with that semester.

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Student_Enrolment",
      "Semesters"
    ],
    "source_columns": [
      "Semesters.semester_id",
      "Semesters.semester_name",
      "Student_Enrolment.student_enrolment_id",
      "Student_Enrolment.semester_id"
    ],
    "output_lineage": {
      "semester_id": [
        "Semesters.semester_id"
      ],
      "semester_name": [
        "Semesters.semester_name"
      ],
      "registration_count": [
        "Student_Enrolment.student_enrolment_id"
      ]
    },
    "operators": [
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "student_enrolment": "445257138d420d03",
      "semesters": "29c2494a0d4e0c8e"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_529",
    "question": "What is the semester which most student registered in? Show both the name and the id.",
    "rewrite": "Task: Find the semester (its name and its id) that has the largest number of student registrations.\nRequired outputs: semester name; semester id; (optionally) the count of students registered in that semester if helpful for tie-breaking or verification\nFilters: Consider all registration records in the database; count each student registration toward the semester in which it occurred.; If multiple semesters are tied for the largest number of student registrations, return all tied semesters (each with its name and id).\nSort/limit: order results by the student-registration count in descending order; no hard row limit (return all semesters that share the maximum count)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:04:41+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:04:43+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "semester_id",
      "semester_name",
      "registration_count"
    ],
    "row_count": 9,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Student_Enrolment.semester_id=Semesters.semester_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (semester_id, semester_name). Ensures view groups correctly and returns one row per semester key.",
        "sql": "SELECT COUNT(*) FROM (SELECT semester_id, semester_name, COUNT(*) AS cnt FROM semester_registration_counts GROUP BY semester_id, semester_name HAVING cnt > 1) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "registration_count equals the count of Student_Enrolment rows that join to that semester (measure reconciliation). Detects aggregation or join mistakes.",
        "sql": "SELECT COUNT(*) FROM semester_registration_counts v LEFT JOIN Semesters s ON v.semester_id = s.semester_id WHERE (SELECT COUNT(*) FROM Student_Enrolment se WHERE se.semester_id = v.semester_id) != v.registration_count",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL: semester_id and semester_name must be present for every row in the view (ensures key completeness).",
        "sql": "SELECT COUNT(*) FROM semester_registration_counts WHERE semester_id IS NULL OR semester_name IS NULL",
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
  s.semester_id,
  s.semester_name,
  COUNT(se.student_enrolment_id) AS registration_count
FROM Student_Enrolment se
JOIN Semesters s ON se.semester_id = s.semester_id
GROUP BY s.semester_id, s.semester_name
```

---

## Skill `per_semester_student_registration_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `semester_id`, `student_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_5b4c6f483777534f |
| output columns | `semester_id`, `student_id`, `registration_count` |
| source tables | `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per semester, per student counts of registrations/enrollments (one row per semester + student with their registration count) useful for identifying top registrants or cohorts.

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Student_Enrolment"
    ],
    "source_columns": [
      "Student_Enrolment.semester_id",
      "Student_Enrolment.student_id"
    ],
    "output_lineage": {
      "semester_id": [
        "Student_Enrolment.semester_id"
      ],
      "student_id": [
        "Student_Enrolment.student_id"
      ],
      "registration_count": []
    },
    "operators": [
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_530",
    "question": "For each semester, what is the name and id of the one with the most students registered?",
    "rewrite": "Task: For each semester, find the single student (name and id) who has the highest number of registered students for that semester.\nRequired outputs: semester; student id; student name; number of students registered (registration count) -- used to determine the maximum\nFilters: Group results by semester; For each semester include only the row(s) where the student's registration count equals the maximum registration count for that semester; If multiple students tie for the maximum count in a semester, include only one of them (tie-breaking unspecified) unless the schema/query allows returning all ties\nSort/limit: Order rows by semester ascending; limit is one row per semester (i.e., the single student with the maximum registrations for that semester)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:05:09+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:05:12+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "semester_id",
      "student_id",
      "registration_count"
    ],
    "row_count": 14,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (semester_id, student_id)",
        "sql": "SELECT COUNT(*) FROM per_semester_student_registration_counts v JOIN (SELECT semester_id, student_id, COUNT(*) AS cnt FROM per_semester_student_registration_counts GROUP BY semester_id, student_id HAVING cnt > 1) d ON v.semester_id = d.semester_id AND v.student_id = d.student_id",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "registration_count equals the count of Student_Enrolment rows for that semester_id and student_id",
        "sql": "SELECT COUNT(*) FROM per_semester_student_registration_counts v LEFT JOIN (SELECT semester_id, student_id, COUNT(*) AS expected_count FROM Student_Enrolment GROUP BY semester_id, student_id) e ON v.semester_id = e.semester_id AND v.student_id = e.student_id WHERE (e.expected_count IS NULL AND v.registration_count IS NOT NULL) OR (e.expected_count IS NOT NULL AND v.registration_count <> e.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL (semester_id and student_id must be present)",
        "sql": "SELECT COUNT(*) FROM per_semester_student_registration_counts v WHERE v.semester_id IS NULL OR v.student_id IS NULL",
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
SELECT se.semester_id, se.student_id, COUNT(*) AS registration_count FROM Student_Enrolment se GROUP BY se.semester_id, se.student_id
```

---

## Skill `student_semester_degree_program_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `student_id`, `semester_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_d8233b65a224977e |
| output columns | `student_id`, `semester_id`, `distinct_degree_programs` |
| source tables | `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-student per-semester counts of distinct degree programs the student is enrolled in (one row per student per semester)

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Student_Enrolment"
    ],
    "source_columns": [
      "Student_Enrolment.student_id",
      "Student_Enrolment.semester_id",
      "Student_Enrolment.degree_program_id"
    ],
    "output_lineage": {
      "student_id": [
        "Student_Enrolment.student_id"
      ],
      "semester_id": [
        "Student_Enrolment.semester_id"
      ],
      "distinct_degree_programs": [
        "Student_Enrolment.degree_program_id"
      ]
    },
    "operators": [
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_533",
    "question": "Who are enrolled in 2 degree programs in one semester? List the first name, middle name and last name and the id.",
    "rewrite": "Task: Find all students who are enrolled in exactly two degree programs within a single semester and return their identifying name parts and id.\nRequired outputs: first name; middle name; last name; id\nFilters: student must be enrolled in two degree programs during the same semester (i.e., there exist two distinct enrollments for the same student that have the same semester identifier but different degree program identifiers); include only students for whom first name, middle name, last name and id are present in the database rows returned",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:05:55+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:05:58+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "semester_id",
      "distinct_degree_programs"
    ],
    "row_count": 14,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View has one row per student_id + semester_id (no duplicate keys)",
        "sql": "SELECT COUNT(*) FROM student_semester_degree_program_counts v WHERE (SELECT COUNT(*) FROM student_semester_degree_program_counts v2 WHERE v2.student_id = v.student_id AND v2.semester_id = v.semester_id) > 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "distinct_degree_programs equals the true distinct count computed from base table",
        "sql": "SELECT COUNT(*) FROM student_semester_degree_program_counts v LEFT JOIN (SELECT student_id, semester_id, COUNT(DISTINCT degree_program_id) AS true_cnt FROM Student_Enrolment GROUP BY student_id, semester_id) b ON v.student_id = b.student_id AND v.semester_id = b.semester_id WHERE (b.true_cnt IS NULL AND v.distinct_degree_programs IS NOT NULL) OR (b.true_cnt IS NOT NULL AND v.distinct_degree_programs != b.true_cnt)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys student_id and semester_id are NOT NULL in the view",
        "sql": "SELECT COUNT(*) FROM student_semester_degree_program_counts WHERE student_id IS NULL OR semester_id IS NULL",
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
      "Task: Find all students who enrolled in exactly 2 degree programs within a single semester, and return each such student's first name, middle name, last name, and student id.\nRequired outputs: first name; middle name; last name; id\nFilters: Consider enrollment records grouped by student and by semester.; Include only students for whom, for at least one semester, the count of distinct degree programs enrolled in that semester = 2.; If a student enrolled in 2 programs in multiple semesters, include the student only once (no duplicate rows per semester).; Ignore enrollments where the semester is NULL or undefined."
    ],
    "last_used": "spider_dev_534"
  }
}
```

### Validated on (0)

—

### Counter-examples (1)

- What are the first, middle, and last names, along with the ids, of all students who enrolled in 2 degree programs in one semester?

### Executable SQL body

```sql
SELECT student_id, semester_id, COUNT(DISTINCT degree_program_id) AS distinct_degree_programs FROM Student_Enrolment GROUP BY student_id, semester_id
```

---

## Skill `enrolments_by_program_kind`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `program_kind` (keyed) |
| status / version | active / v1 |
| skill id | sk_773e6c9a8dd9a7a5 |
| output columns | `program_kind`, `total_enrolments` |
| source tables | `Student_Enrolment`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-program-kind total student enrolment counts by joining student enrolment records to degree programs and grouping by the program kind label.

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Student_Enrolment",
      "Degree_Programs"
    ],
    "source_columns": [
      "Degree_Programs.degree_summary_name",
      "Student_Enrolment.student_enrolment_id",
      "Student_Enrolment.degree_program_id",
      "Degree_Programs.degree_program_id"
    ],
    "output_lineage": {
      "program_kind": [
        "Degree_Programs.degree_summary_name"
      ],
      "total_enrolments": [
        "Student_Enrolment.student_enrolment_id"
      ]
    },
    "operators": [
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "student_enrolment": "445257138d420d03",
      "degree_programs": "85466a54c4a97bc7"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_537",
    "question": "Find the kind of program which most number of students are enrolled in?",
    "rewrite": "Task: Return the program kind (type of program) that has the largest total number of student enrollments across all records.\nRequired outputs: program kind (the label/name of the kind of program); total number of students enrolled in that program kind (an aggregate count or sum as an integer)\nFilters: include all enrollment records; group enrollments by program kind and sum the number of students per kind; consider every program kind present in the data\nSort/limit: order results by total number of students enrolled in descending order and return the top 1 row",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:07:29+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:07:32+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "program_kind",
      "total_enrolments"
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
        "purpose": "No duplicate rows at the declared grain (program_kind). Fails if view contains two or more rows with same program_kind.",
        "sql": "SELECT COUNT(*) FROM (SELECT program_kind, COUNT(*) AS cnt FROM enrolments_by_program_kind GROUP BY program_kind HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "total_enrolments equals count of Student_Enrolment rows that join to Degree_Programs for that program_kind (detects wrong aggregation or join duplication).",
        "sql": "SELECT COUNT(*) FROM (SELECT v.program_kind FROM enrolments_by_program_kind v LEFT JOIN (SELECT dp.degree_summary_name AS program_kind, COUNT(se.student_enrolment_id) AS expected_count FROM Student_Enrolment se JOIN Degree_Programs dp ON se.degree_program_id = dp.degree_program_id GROUP BY dp.degree_summary_name) x ON v.program_kind = x.program_kind WHERE x.expected_count IS NULL OR v.total_enrolments <> x.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "program_kind is never NULL in the view (key non-nullability).",
        "sql": "SELECT COUNT(*) FROM enrolments_by_program_kind WHERE program_kind IS NULL",
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
SELECT dp.degree_summary_name AS program_kind, COUNT(se.student_enrolment_id) AS total_enrolments FROM Student_Enrolment se JOIN Degree_Programs dp ON se.degree_program_id = dp.degree_program_id GROUP BY dp.degree_summary_name
```

---

## Skill `degree_program_enrollment_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `degree_program_id`, `degree_summary_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_91ce16d8ce9f18e8 |
| output columns | `degree_program_id`, `degree_summary_name`, `student_count` |
| source tables | `Degree_Programs`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per degree_program (with its degree_summary_name) count of distinct students enrolled, excluding programs with zero enrolled students; useful for reporting program-level enrollment and ranking.

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Degree_Programs",
      "Student_Enrolment"
    ],
    "source_columns": [
      "Degree_Programs.degree_program_id",
      "Degree_Programs.degree_summary_name",
      "Student_Enrolment.degree_program_id",
      "Student_Enrolment.student_id"
    ],
    "output_lineage": {
      "degree_program_id": [
        "Degree_Programs.degree_program_id"
      ],
      "degree_summary_name": [
        "Degree_Programs.degree_summary_name"
      ],
      "student_count": [
        "Student_Enrolment.student_id"
      ]
    },
    "operators": [
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "degree_programs": "85466a54c4a97bc7",
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_538",
    "question": "What is the degree summary name that has the most number of students enrolled?",
    "rewrite": "Task: Find the degree summary name that corresponds to the largest number of students enrolled.\nRequired outputs: degree summary name (the name/title of the degree summary); number of students enrolled in that degree summary\nFilters: include only degree summaries that have at least one enrolled student (i.e., count>0); treat enrollment counts as the number of distinct students assigned to each degree summary\nSort/limit: order by number of students enrolled descending, limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:07:49+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:07:51+00:00",
    "contract_version": 3,
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
        "join": "Degree_Programs.degree_program_id=Student_Enrolment.degree_program_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (each degree_program_id + degree_summary_name appears at most once)",
        "sql": "SELECT COUNT(*) FROM (SELECT degree_program_id, degree_summary_name, COUNT(*) AS cnt FROM degree_program_enrollment_counts GROUP BY degree_program_id, degree_summary_name HAVING cnt > 1) AS dup",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count matches count distinct student_id in base tables for each row",
        "sql": "SELECT COUNT(*) FROM degree_program_enrollment_counts v LEFT JOIN Degree_Programs dp USING(degree_program_id) LEFT JOIN (SELECT degree_program_id, COUNT(DISTINCT student_id) AS expected_count FROM Student_Enrolment GROUP BY degree_program_id) s USING(degree_program_id) WHERE (s.expected_count IS NULL AND v.student_count IS NOT NULL) OR (s.expected_count IS NOT NULL AND v.student_count != s.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No rows with NULL key columns (degree_program_id or degree_summary_name)",
        "sql": "SELECT COUNT(*) FROM degree_program_enrollment_counts WHERE degree_program_id IS NULL OR degree_summary_name IS NULL",
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
SELECT dp.degree_program_id, dp.degree_summary_name, COUNT(DISTINCT se.student_id) AS student_count FROM Degree_Programs dp JOIN Student_Enrolment se ON dp.degree_program_id = se.degree_program_id GROUP BY dp.degree_program_id, dp.degree_summary_name HAVING COUNT(DISTINCT se.student_id) > 0
```

---

## Skill `degree_program_student_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `degree_program_id`, `summary` (keyed) |
| status / version | active / v1 |
| skill id | sk_83b94b61e4f3d334 |
| output columns | `degree_program_id`, `summary`, `student_count` |
| source tables | `Degree_Programs`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-degree-program counts of student enrolments (one row per degree_program_id with its summary and the number of enrolled students).

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Degree_Programs",
      "Student_Enrolment"
    ],
    "source_columns": [
      "Degree_Programs.degree_program_id",
      "Degree_Programs.degree_summary_name",
      "Student_Enrolment.student_enrolment_id",
      "Student_Enrolment.degree_program_id"
    ],
    "output_lineage": {
      "degree_program_id": [
        "Degree_Programs.degree_program_id"
      ],
      "summary": [
        "Degree_Programs.degree_summary_name"
      ],
      "student_count": [
        "Student_Enrolment.student_enrolment_id"
      ]
    },
    "operators": [
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "degree_programs": "85466a54c4a97bc7",
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_540",
    "question": "What is the program id and the summary of the degree that has the most students enrolled?",
    "rewrite": "Task: Find the degree (program) that has the largest number of students enrolled and return its program id and the degree summary.\nRequired outputs: program id (the identifier of the degree/program); summary (the degree's summary description)\nFilters: Consider all degrees/programs in the database.; Count students enrolled per degree/program using the available enrollment/relationship between students and degrees; include degrees with zero students if schema requires but they will not be the maximum.; If multiple degrees tie for the maximum number of enrolled students, return all tied degrees (each with program id and summary).\nSort/limit: order by student count descending; limit to the maximum count (i.e., return all rows that have the highest enrollment).",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:08:33+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:08:36+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "degree_program_id",
      "summary",
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
        "purpose": "View has one row per degree_program_id + summary (no duplicate keys)",
        "sql": "SELECT COUNT(*) FROM (SELECT degree_program_id, summary, COUNT(*) AS cnt FROM degree_program_student_counts GROUP BY degree_program_id, summary HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count equals count of Student_Enrolment rows per degree_program_id (reconciles with base table)",
        "sql": "SELECT COUNT(*) FROM degree_program_student_counts v LEFT JOIN (SELECT degree_program_id, COUNT(*) AS expected_count FROM Student_Enrolment GROUP BY degree_program_id) b ON v.degree_program_id = b.degree_program_id WHERE (b.expected_count IS NULL AND v.student_count != 0) OR (b.expected_count IS NOT NULL AND v.student_count != b.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL (degree_program_id and summary must be present)",
        "sql": "SELECT COUNT(*) FROM degree_program_student_counts WHERE degree_program_id IS NULL OR summary IS NULL",
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
  dp.degree_program_id,
  dp.degree_summary_name AS summary,
  COUNT(se.student_enrolment_id) AS student_count
FROM Degree_Programs dp
LEFT JOIN Student_Enrolment se ON se.degree_program_id = dp.degree_program_id
GROUP BY dp.degree_program_id, dp.degree_summary_name
```

---

## Skill `student_enrollment_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `student_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_dd09c7ad7d1fb9c3 |
| output columns | `student_id`, `enrollment_count` |
| source tables | `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-student total enrollment counts aggregated from the student enrollment table, producing one row per student with their id and total number of enrollments.

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Student_Enrolment"
    ],
    "source_columns": [
      "Student_Enrolment.student_id"
    ],
    "output_lineage": {
      "student_id": [
        "Student_Enrolment.student_id"
      ],
      "enrollment_count": []
    },
    "operators": [
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_541",
    "question": "Which student has enrolled for the most times in any program? List the id, first name, middle name, last name, the number of enrollments and student id.",
    "rewrite": "Task: Find the student (or students, if tied) who has enrolled the greatest number of times in any program and return their identifying information along with that enrollment count.\nRequired outputs: id (the student's primary id); first name; middle name; last name; the number of enrollments (count of distinct enrollments for that student in programs); student id (duplicate of id if the schema uses the same field; include if a separate student identifier exists)\nFilters: Consider all enrollment records for all students across all programs; Count all enrollments for each student (no date or program-type restrictions) to compute each student's total number of enrollments; Only return row(s) for the student(s) whose enrollment count equals the maximum enrollment count among all students\nSort/limit: Order not required; return all students tied for the maximum enrollment count (no limit)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:08:55+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:08:57+00:00",
    "contract_version": 3,
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
        "purpose": "No duplicate student_id rows (view should have exactly one row per student_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id FROM student_enrollment_counts GROUP BY student_id HAVING COUNT(*) > 1) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "enrollment_count matches count of rows in Student_Enrolment per student_id",
        "sql": "SELECT COUNT(*) FROM student_enrollment_counts sec LEFT JOIN (SELECT student_id, COUNT(*) AS cnt FROM Student_Enrolment GROUP BY student_id) src ON sec.student_id = src.student_id WHERE COALESCE(sec.enrollment_count, -999999) != COALESCE(src.cnt, -999999)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_id in the view is not NULL",
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
SELECT se.student_id, COUNT(*) AS enrollment_count FROM Student_Enrolment se GROUP BY se.student_id
```

---

## Skill `student_enrollment_counts_13`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `student_id`, `first_name`, `middle_name`, `last_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_d899fc954ae0b5a3 |
| output columns | `student_id`, `first_name`, `middle_name`, `last_name`, `enrollment_count` |
| source tables | `Student_Enrolment`, `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-student total enrollment counts (one row per student who has at least one enrollment), including student identity columns for joining.

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Student_Enrolment",
      "Students"
    ],
    "source_columns": [
      "Students.student_id",
      "Students.first_name",
      "Students.middle_name",
      "Students.last_name",
      "Student_Enrolment.student_enrolment_id",
      "Student_Enrolment.student_id"
    ],
    "output_lineage": {
      "student_id": [
        "Students.student_id"
      ],
      "first_name": [
        "Students.first_name"
      ],
      "middle_name": [
        "Students.middle_name"
      ],
      "last_name": [
        "Students.last_name"
      ],
      "enrollment_count": [
        "Student_Enrolment.student_enrolment_id"
      ]
    },
    "operators": [
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "student_enrolment": "445257138d420d03",
      "students": "ad3aee5be9cacc55"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_542",
    "question": "What is the first, middle, and last name, along with the id and number of enrollments, for the student who enrolled the most in any program?",
    "rewrite": "Task: Find the student who has the single highest number of enrollments in any program and return that student's first name, middle name, last name, id, and number of enrollments.\nRequired outputs: first name; middle name; last name; id; number of enrollments\nFilters: Consider each student’s total number of enrollments across programs; select the student with the maximum enrollment count (if multiple students tie for the maximum, return all such students).; Only include rows for students present in the enrollment counts (exclude students with zero enrollments).\nSort/limit: order by number of enrollments descending; limit to the maximum value (or return all rows tied for the top value)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:09:17+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:09:23+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "first_name",
      "middle_name",
      "last_name",
      "enrollment_count"
    ],
    "row_count": 8,
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
        "purpose": "View has one row per student who has at least one enrollment (no students with zero enrollments, and students with enrollments are present). Finds Students referenced by Student_Enrolment but missing ",
        "sql": "SELECT ( (SELECT COUNT(DISTINCT se.student_id) FROM Student_Enrolment se) - (SELECT COUNT(DISTINCT s.student_id) FROM student_enrollment_counts_13 v JOIN Students s ON v.student_id = s.student_id) ) + ( (SELECT COUNT(*) FROM student_enrollment_counts_13 v WHERE v.enrollment_count < 1) ) AS violation_count",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Enrollment count matches base table counts: any row whose enrollment_count differs from the actual count of Student_Enrolment rows for that student.",
        "sql": "SELECT COUNT(*) FROM student_enrollment_counts_13 v LEFT JOIN (SELECT student_id, COUNT(student_enrolment_id) AS real_count FROM Student_Enrolment GROUP BY student_id) t ON v.student_id = t.student_id WHERE IFNULL(t.real_count,0) != IFNULL(v.enrollment_count,0)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View respects its declared grain keys: no duplicate rows for the same student identity (student_id, first_name, middle_name, last_name).",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id, first_name, middle_name, last_name, COUNT(*) AS cnt FROM student_enrollment_counts_13 GROUP BY student_id, first_name, middle_name, last_name HAVING cnt > 1)",
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
SELECT s.student_id, s.first_name, s.middle_name, s.last_name, COUNT(se.student_enrolment_id) AS enrollment_count FROM Student_Enrolment se JOIN Students s ON s.student_id = se.student_id GROUP BY s.student_id, s.first_name, s.middle_name, s.last_name
```

---

## Skill `semester_enrolment_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `semester_id`, `semester_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_02ca032c107e69cf |
| output columns | `semester_id`, `semester_name`, `enrolment_count` |
| source tables | `Semesters`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-semester counts of student enrolment records to identify enrollment levels or empty semesters

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Semesters",
      "Student_Enrolment"
    ],
    "source_columns": [
      "Semesters.semester_id",
      "Semesters.semester_name",
      "Student_Enrolment.student_enrolment_id",
      "Student_Enrolment.semester_id"
    ],
    "output_lineage": {
      "semester_id": [
        "Semesters.semester_id"
      ],
      "semester_name": [
        "Semesters.semester_name"
      ],
      "enrolment_count": [
        "Student_Enrolment.student_enrolment_id"
      ]
    },
    "operators": [
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "semesters": "29c2494a0d4e0c8e",
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_544",
    "question": "What is the name of the semester with no students enrolled?",
    "rewrite": "Task: Find the name of the semester that has no students enrolled in it.\nRequired outputs: semester name\nFilters: Only consider semesters for which the number of students enrolled equals zero (i.e., semesters with no enrollment records or where enrollment count is zero).; If multiple semesters have no students, return all such semester names.",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:09:51+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:09:53+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "semester_id",
      "semester_name",
      "enrolment_count"
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
        "sql": "SELECT COUNT(*) FROM (SELECT semester_id, semester_name, COUNT(*) AS cnt FROM semester_enrolment_counts GROUP BY semester_id, semester_name HAVING cnt > 1) t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "enrolment_count matches count of Student_Enrolment rows per semester (recomputed from base tables)",
        "sql": "SELECT COUNT(*) FROM semester_enrolment_counts v LEFT JOIN (SELECT s.semester_id, COUNT(se.student_enrolment_id) AS expected_count FROM Semesters s LEFT JOIN Student_Enrolment se ON s.semester_id = se.semester_id GROUP BY s.semester_id) b ON v.semester_id = b.semester_id WHERE COALESCE(v.enrolment_count,0) != COALESCE(b.expected_count,0)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL (semester_id and semester_name must be present)",
        "sql": "SELECT COUNT(*) FROM semester_enrolment_counts WHERE semester_id IS NULL OR semester_name IS NULL",
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
SELECT s.semester_id, s.semester_name, COUNT(se.student_enrolment_id) AS enrolment_count FROM Semesters s LEFT JOIN Student_Enrolment se ON s.semester_id = se.semester_id GROUP BY s.semester_id, s.semester_name
```

---

## Skill `courses_with_enrollments`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `course_id`, `course_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_ddcd6fee5e64e1f4 |
| output columns | `course_id`, `course_name` |
| source tables | `Courses`, `Student_Enrolment_Courses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

All courses that have at least one enrollment (represents the cohort of courses linked to one or more student enrollments).

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Courses",
      "Student_Enrolment_Courses"
    ],
    "source_columns": [
      "Courses.course_id",
      "Courses.course_name",
      "Student_Enrolment_Courses.course_id"
    ],
    "output_lineage": {
      "course_id": [
        "Courses.course_id"
      ],
      "course_name": [
        "Courses.course_name"
      ]
    },
    "operators": [
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "courses": "53e9befe1413d87f",
      "student_enrolment_courses": "daf1efe3c261d034"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_546",
    "question": "What are the names of all courses that have some students enrolled?",
    "rewrite": "Task: Return the names of every course that has at least one student enrolled in it.\nRequired outputs: course name (one value per row)\nFilters: only include courses for which there exists at least one enrollment linking a student to that course (i.e., courses with enrollment count > 0)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:10:19+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:10:21+00:00",
    "contract_version": 3,
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
      }
    ],
    "tests": [
      {
        "purpose": "View rows must be distinct at the declared grain (no duplicate course_id/course_name pairs)",
        "sql": "SELECT COUNT(*) FROM (SELECT course_id, course_name, COUNT(*) AS cnt FROM courses_with_enrollments GROUP BY course_id, course_name HAVING cnt > 1) sub",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view must correspond to at least one enrollment in the base table (no course in the view without a matching Student_Enrolment_Courses row)",
        "sql": "SELECT COUNT(*) FROM courses_with_enrollments v WHERE NOT EXISTS (SELECT 1 FROM Student_Enrolment_Courses sec WHERE sec.course_id = v.course_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys in the view must not be NULL (course_id must be non-NULL)",
        "sql": "SELECT COUNT(*) FROM courses_with_enrollments WHERE course_id IS NULL",
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
SELECT c.course_id, c.course_name
FROM Courses c
JOIN Student_Enrolment_Courses sec ON sec.course_id = c.course_id
GROUP BY c.course_id, c.course_name
```

---

## Skill `course_enrollment_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `course_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_8b569c07c8dcf319 |
| output columns | `course_id`, `enrollment_count` |
| source tables | `Student_Enrolment_Courses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-course enrollment counts computed by counting student-course enrollment records, providing course_id and enrollment count for joins and further analysis.

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Student_Enrolment_Courses"
    ],
    "source_columns": [
      "Student_Enrolment_Courses.course_id"
    ],
    "output_lineage": {
      "course_id": [
        "Student_Enrolment_Courses.course_id"
      ],
      "enrollment_count": []
    },
    "operators": [
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "student_enrolment_courses": "daf1efe3c261d034"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_547",
    "question": "What's the name of the course with most number of enrollments?",
    "rewrite": "Task: Find the name of the course that has the largest number of enrollments (i.e., the course whose enrollment count is maximum across all courses).\nRequired outputs: course name\nFilters: consider all courses and count enrollments per course; treat enrollments as records linking students to courses; if multiple courses tie for the maximum enrollment, return all such course names\nSort/limit: order by enrollment count descending, limit to the maximum count (i.e., return the top course(s) with the highest enrollment)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:10:33+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:10:36+00:00",
    "contract_version": 3,
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
        "purpose": "No duplicate course_id rows in the view (grain enforced)",
        "sql": "SELECT COUNT(*) FROM (SELECT course_id, COUNT(*) AS cnt FROM course_enrollment_counts GROUP BY course_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "enrollment_count matches COUNT(*) from base table per course_id",
        "sql": "SELECT COUNT(*) FROM (SELECT v.course_id FROM course_enrollment_counts v LEFT JOIN (SELECT course_id, COUNT(*) AS expected_count FROM Student_Enrolment_Courses GROUP BY course_id) b ON v.course_id = b.course_id WHERE (b.expected_count IS NULL AND (v.enrollment_count IS NOT NULL AND v.enrollment_count != 0)) OR (b.expected_count IS NOT NULL AND v.enrollment_count != b.expected_count))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "course_id in the view is never NULL",
        "sql": "SELECT COUNT(*) FROM course_enrollment_counts WHERE course_id IS NULL",
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
SELECT sec.course_id, COUNT(*) AS enrollment_count FROM Student_Enrolment_Courses sec GROUP BY sec.course_id
```

---

## Skill `course_enrollment_counts_17`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `course_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_4987eb8b48b6b991 |
| output columns | `course_id`, `enrollment_count` |
| source tables | `Student_Enrolment_Courses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-course enrollment counts computed from student enrollment records (one row per course with course_id and enrollment_count), useful for ranking or filtering courses by popularity.

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
      "ORDER BY",
      "LIMIT",
      "specific course names or ids"
    ],
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Student_Enrolment_Courses"
    ],
    "source_columns": [
      "Student_Enrolment_Courses.course_id",
      "Student_Enrolment_Courses.student_course_id"
    ],
    "output_lineage": {
      "course_id": [
        "Student_Enrolment_Courses.course_id"
      ],
      "enrollment_count": [
        "Student_Enrolment_Courses.student_course_id"
      ]
    },
    "operators": [
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "student_enrolment_courses": "daf1efe3c261d034"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_548",
    "question": "What is the name of the course with the most students enrolled?",
    "rewrite": "Task: Find the name of the course that has the highest number of students enrolled (i.e., the course with the maximum enrollment count).\nRequired outputs: course name\nFilters: Consider all courses; count the number of students enrolled in each course and select the course(s) whose enrolment count equals the maximum across all courses.\nSort/limit: order by enrollment count descending, limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:10:56+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:10:58+00:00",
    "contract_version": 3,
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
        "purpose": "No duplicate course_id in the view (view grain is one row per course_id).",
        "sql": "SELECT COUNT(*) FROM course_enrollment_counts_17 v JOIN (SELECT course_id FROM course_enrollment_counts_17 GROUP BY course_id HAVING COUNT(*) > 1) d USING (course_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "enrollment_count matches COUNT(student_course_id) from base table for each course_id.",
        "sql": "SELECT COUNT(*) FROM course_enrollment_counts_17 v LEFT JOIN (SELECT course_id, COUNT(student_course_id) AS expected_count FROM Student_Enrolment_Courses GROUP BY course_id) b USING (course_id) WHERE (b.expected_count IS NULL AND v.enrollment_count IS NOT NULL) OR (b.expected_count IS NOT NULL AND v.enrollment_count != b.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "course_id (the key) is never NULL in the view.",
        "sql": "SELECT COUNT(*) FROM course_enrollment_counts_17 WHERE course_id IS NULL",
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
SELECT course_id, COUNT(student_course_id) AS enrollment_count FROM Student_Enrolment_Courses GROUP BY course_id
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

Per-transcript counts of associated course-result (Transcript_Contents) rows, with transcript id and date for joining or filtering by count

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Transcripts",
      "Transcript_Contents"
    ],
    "source_columns": [
      "Transcripts.transcript_id",
      "Transcripts.transcript_date",
      "Transcript_Contents.student_course_id",
      "Transcript_Contents.transcript_id"
    ],
    "output_lineage": {
      "transcript_id": [
        "Transcripts.transcript_id"
      ],
      "transcript_date": [
        "Transcripts.transcript_date"
      ],
      "course_result_count": [
        "Transcript_Contents.student_course_id"
      ]
    },
    "operators": [
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "transcripts": "e9e22770a8b921c8",
      "transcript_contents": "ecac21baa04d7c6d"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_551",
    "question": "Show the date and id of the transcript with at least 2 course results.",
    "rewrite": "Task: Return rows for transcripts that have two or more associated course results, showing each transcript's date and id.\nRequired outputs: date (the transcript's date); id (the transcript's id)\nFilters: Only include transcripts that have at least 2 course results associated with that transcript (i.e., count of related course-result rows >= 2)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:12:17+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:12:19+00:00",
    "contract_version": 3,
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
        "purpose": "No NULLs in key columns (transcript_id, transcript_date) in the view",
        "sql": "SELECT COUNT(*) FROM transcript_course_result_counts WHERE transcript_id IS NULL OR transcript_date IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View's course_result_count equals the count of Transcript_Contents rows per transcript_id (detect mismatched aggregation or join issues)",
        "sql": "SELECT COUNT(*) FROM transcript_course_result_counts v LEFT JOIN (SELECT tc.transcript_id AS transcript_id, COUNT(*) AS expected_count FROM Transcript_Contents tc GROUP BY tc.transcript_id) x ON v.transcript_id = x.transcript_id WHERE (x.expected_count IS NULL AND v.course_result_count != 0) OR (x.expected_count IS NOT NULL AND v.course_result_count != x.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view corresponds to an existing Transcripts row (detect joins that produced rows for missing transcripts)",
        "sql": "SELECT COUNT(*) FROM transcript_course_result_counts v LEFT JOIN Transcripts t ON v.transcript_id = t.transcript_id WHERE t.transcript_id IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 2,
    "selected": 1,
    "included": 1,
    "referenced": 1,
    "executed": 1,
    "inconclusive": 1,
    "positive": 1,
    "positive_subgoals": [
      "Task: Return the date and id for each transcript that lists two or more courses.\nRequired outputs: date (the transcript's date); id (the transcript's identifier)\nFilters: only include transcripts that have at least 2 associated course entries (count of courses per transcript >= 2)"
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
SELECT t.transcript_id AS transcript_id, t.transcript_date AS transcript_date, COUNT(tc.student_course_id) AS course_result_count FROM Transcripts t JOIN Transcript_Contents tc ON tc.transcript_id = t.transcript_id GROUP BY t.transcript_id, t.transcript_date
```

---

## Skill `students_with_earliest_registration`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `student_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_b658501cee63e635 |
| output columns | `student_id`, `first_name`, `middle_name`, `last_name`, `date_first_registered` |
| source tables | `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

All student records whose registration timestamp equals the minimum registration timestamp across all students (i.e., the earliest-registered student(s)).

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
    "contract_version": 3,
    "grain_basis": "primary_key",
    "lineage": [
      "Students"
    ],
    "source_columns": [
      "Students.student_id",
      "Students.first_name",
      "Students.middle_name",
      "Students.last_name",
      "Students.date_first_registered"
    ],
    "output_lineage": {
      "student_id": [
        "Students.student_id"
      ],
      "first_name": [
        "Students.first_name"
      ],
      "middle_name": [
        "Students.middle_name"
      ],
      "last_name": [
        "Students.last_name"
      ],
      "date_first_registered": [
        "Students.date_first_registered"
      ]
    },
    "operators": [
      "filter",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "students": "ad3aee5be9cacc55"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_555",
    "question": "Who is the first student to register? List the first name, middle name and last name.",
    "rewrite": "Task: Return the student who registered first (earliest registration time), showing that student's first name, middle name, and last name.\nRequired outputs: first name; middle name; last name\nFilters: Choose a single student record with the earliest registration timestamp (i.e., the minimum registration time across all students).; If multiple students share the identical earliest registration timestamp, return all such students.\nSort/limit: order by registration time ascending; limit 1 (or no limit if ties must be returned)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:13:35+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:13:38+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "first_name",
      "middle_name",
      "last_name",
      "date_first_registered"
    ],
    "row_count": 1,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate student_id in the view (grain uniqueness). Counts student_ids that appear more than once in the view.",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id, COUNT(*) AS cnt FROM students_with_earliest_registration GROUP BY student_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view has date_first_registered equal to the minimum date_first_registered across all Students (intrinsic filter correctness). Counts rows in the view whose date_first_registered is no",
        "sql": "SELECT COUNT(*) FROM students_with_earliest_registration WHERE date_first_registered IS NULL OR date_first_registered <> (SELECT MIN(date_first_registered) FROM Students)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "The view includes exactly the Students rows that attain the global minimum registration date (no missing or extra rows). Counts mismatches between the view and the base Students filtered to the global",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id FROM students_with_earliest_registration UNION ALL SELECT student_id FROM Students WHERE date_first_registered = (SELECT MIN(date_first_registered) FROM Students) EXCEPT SELECT student_id FROM students_with_earliest_registration)",
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
      "Task: Return the first, middle, and last name of the student who registered first (i.e., the single student with the earliest registration time).\nRequired outputs: first name; middle name; last name\nFilters: row must be the student record whose registration timestamp is the minimum across all students (earliest registration). If multiple students share the exact same earliest timestamp, return the one with the smallest primary key or unique student identifier (as a deterministic tie-breaker).\nSort/limit: order by registration timestamp ASC, then by student primary key ASC; limit 1"
    ],
    "last_used": "spider_dev_556"
  }
}
```

### Validated on (1)

- What is the first, middle, and last name of the first student to register?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT student_id, first_name, middle_name, last_name, date_first_registered FROM Students WHERE date_first_registered = (SELECT MIN(date_first_registered) FROM Students)
```

---

## Skill `students_with_graduation_date`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `student_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_c5a2af7f49c09007 |
| output columns | `student_id`, `first_name`, `middle_name`, `last_name`, `graduation_date` |
| source tables | `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

A relation of students who have a recorded school graduation date, including their identifiers and name fields, useful for cohorting or finding earliest/latest graduates.

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
    "contract_version": 3,
    "grain_basis": "primary_key",
    "lineage": [
      "Students"
    ],
    "source_columns": [
      "Students.student_id",
      "Students.first_name",
      "Students.middle_name",
      "Students.last_name",
      "Students.date_left"
    ],
    "output_lineage": {
      "student_id": [
        "Students.student_id"
      ],
      "first_name": [
        "Students.first_name"
      ],
      "middle_name": [
        "Students.middle_name"
      ],
      "last_name": [
        "Students.last_name"
      ],
      "graduation_date": [
        "Students.date_left"
      ]
    },
    "operators": [
      "filter",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "students": "ad3aee5be9cacc55"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_557",
    "question": "Who is the earliest graduate of the school? List the first name, middle name and last name.",
    "rewrite": "Task: Find the single person who is the earliest graduate of the school and return that person's first name, middle name, and last name.\nRequired outputs: first name (string); middle name (string, may be NULL or empty if not present); last name (string)\nFilters: consider only records representing graduates of the school; if graduation dates exist, use the earliest graduation date (smallest/oldest date) to identify the graduate; if multiple graduates share the exact same earliest graduation date, return all such graduates\nSort/limit: order by graduation date ascending; no limit if ties for earliest must be returned (otherwise limit 1)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:14:14+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:14:16+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "first_name",
      "middle_name",
      "last_name",
      "graduation_date"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate student_id in the view (view grain is student_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id, COUNT(*) AS cnt FROM students_with_graduation_date GROUP BY student_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view corresponds to a Students row with non-NULL date_left and matching name fields (joins didn't introduce rows without source or with mismatched data)",
        "sql": "SELECT COUNT(*) FROM students_with_graduation_date v LEFT JOIN Students s ON v.student_id = s.student_id WHERE s.student_id IS NULL OR s.date_left IS NULL OR v.first_name IS NOT s.first_name OR (v.middle_name IS NOT s.middle_name) OR v.last_name IS NOT s.last_name OR v.graduation_date IS NOT s.date_left",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All student_id values in the view are NOT NULL",
        "sql": "SELECT COUNT(*) FROM students_with_graduation_date WHERE student_id IS NULL",
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
SELECT student_id, first_name, middle_name, last_name, date_left AS graduation_date FROM Students WHERE date_left IS NOT NULL
```

---

## Skill `student_first_transcript_date`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `student_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_383909e3699bd651 |
| output columns | `student_id`, `first_transcript_date` |
| source tables | `Transcripts`, `Transcript_Contents`, `Student_Enrolment_Courses`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per student, the earliest non-null transcript date (first transcript date) useful for identifying first graduation/record date by student

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Transcripts",
      "Transcript_Contents",
      "Student_Enrolment_Courses",
      "Student_Enrolment"
    ],
    "source_columns": [
      "Student_Enrolment.student_id",
      "Transcripts.transcript_date",
      "Transcript_Contents.transcript_id",
      "Transcripts.transcript_id",
      "Student_Enrolment_Courses.student_course_id",
      "Transcript_Contents.student_course_id",
      "Student_Enrolment.student_enrolment_id",
      "Student_Enrolment_Courses.student_enrolment_id"
    ],
    "output_lineage": {
      "student_id": [
        "Student_Enrolment.student_id"
      ],
      "first_transcript_date": [
        "Transcripts.transcript_date"
      ]
    },
    "operators": [
      "filter",
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "transcripts": "e9e22770a8b921c8",
      "transcript_contents": "ecac21baa04d7c6d",
      "student_enrolment_courses": "daf1efe3c261d034",
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_558",
    "question": "What is the first, middle, and last name of the earliest school graduate?",
    "rewrite": "Task: Find the earliest school graduate and return that person's first name, middle name, and last name.\nRequired outputs: first name; middle name; last name\nFilters: graduate records only (rows representing school graduates); select the row(s) with the earliest graduation date/time (the minimum graduation date)\nSort/limit: order by graduation date ascending, limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:14:31+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:14:34+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "first_transcript_date"
    ],
    "row_count": 4,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Transcript_Contents.transcript_id=Transcripts.transcript_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      },
      {
        "join": "Student_Enrolment_Courses.student_course_id=Transcript_Contents.student_course_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      },
      {
        "join": "Student_Enrolment.student_enrolment_id=Student_Enrolment_Courses.student_enrolment_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "View has one row per student_id (no duplicate student_id keys)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id, COUNT(*) AS cnt FROM student_first_transcript_date GROUP BY student_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "first_transcript_date equals the MIN(transcript_date) computed from base tables for that student (reconciliation with source)",
        "sql": "SELECT COUNT(*) FROM student_first_transcript_date v LEFT JOIN (SELECT se.student_id AS sid, MIN(t.transcript_date) AS expected_date FROM Transcripts t JOIN Transcript_Contents tc ON tc.transcript_id = t.transcript_id JOIN Student_Enrolment_Courses sec ON sec.student_course_id = tc.student_course_id JOIN Student_Enrolment se ON se.student_enrolment_id = sec.student_enrolment_id WHERE t.transcript_date IS NOT NULL GROUP BY se.student_id) s ON v.student_id = s.sid WHERE NOT ( (v.first_transcript_date IS NULL AND s.expected_date IS NULL) OR (v.first_transcript_date = s.expected_date) )",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's student_id is not NULL and corresponds to at least one enrolment in Student_Enrolment (key presence)",
        "sql": "SELECT COUNT(*) FROM student_first_transcript_date v LEFT JOIN Student_Enrolment se ON v.student_id = se.student_id WHERE v.student_id IS NULL OR se.student_enrolment_id IS NULL",
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
SELECT se.student_id, MIN(t.transcript_date) AS first_transcript_date FROM Transcripts t JOIN Transcript_Contents tc ON tc.transcript_id = t.transcript_id JOIN Student_Enrolment_Courses sec ON sec.student_course_id = tc.student_course_id JOIN Student_Enrolment se ON se.student_enrolment_id = sec.student_enrolment_id WHERE t.transcript_date IS NOT NULL GROUP BY se.student_id
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

All students with their permanent and current address identifiers when those two addresses differ (cohort of students whose permanent_address_id != current_address_id).

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
    "contract_version": 3,
    "grain_basis": "primary_key",
    "lineage": [
      "Students"
    ],
    "source_columns": [
      "Students.student_id",
      "Students.first_name",
      "Students.permanent_address_id",
      "Students.current_address_id"
    ],
    "output_lineage": {
      "student_id": [
        "Students.student_id"
      ],
      "first_name": [
        "Students.first_name"
      ],
      "permanent_address_id": [
        "Students.permanent_address_id"
      ],
      "current_address_id": [
        "Students.current_address_id"
      ]
    },
    "operators": [
      "filter",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "students": "ad3aee5be9cacc55"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_559",
    "question": "Whose permanent address is different from his or her current address? List his or her first name.",
    "rewrite": "Task: Find all people whose permanent address does not equal their current address and return each person's first name.\nRequired outputs: first name of each person (value from the person's FirstName/first_name column as provided in the schema)\nFilters: Only include rows where the permanent address is different from the current address: permanent address != current address (string inequality comparison); Do not filter by any other attribute (include all persons who meet the address inequality)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:14:55+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:14:58+00:00",
    "contract_version": 3,
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
        "purpose": "No duplicate student_id in the view (view grain is student_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id FROM students_with_different_permanent_and_current_address GROUP BY student_id HAVING COUNT(*) > 1) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view corresponds to a Students row and permanent_address_id and current_address_id are different and not NULL (intrinsic filter and existence)",
        "sql": "SELECT COUNT(*) FROM students_with_different_permanent_and_current_address v LEFT JOIN Students s USING(student_id) WHERE s.student_id IS NULL OR v.permanent_address_id IS NULL OR v.current_address_id IS NULL OR s.permanent_address_id IS NULL OR s.current_address_id IS NULL OR s.permanent_address_id = s.current_address_id OR v.permanent_address_id != s.permanent_address_id OR v.current_address_id != s.current_address_id",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View does not introduce students whose permanent_address_id equals current_address_id (ensures filter permanent_address_id != current_address_id applied)",
        "sql": "SELECT COUNT(*) FROM students_with_different_permanent_and_current_address v JOIN Students s USING(student_id) WHERE s.permanent_address_id = s.current_address_id",
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
SELECT student_id, first_name, permanent_address_id, current_address_id FROM Students WHERE permanent_address_id IS NOT NULL AND current_address_id IS NOT NULL AND permanent_address_id != current_address_id
```

---

## Skill `student_address_denormalized`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `student_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_2c10878a7ba97ce1 |
| output columns | `student_id`, `first_name`, `current_address_id`, `permanent_address_id`, `curr_address_id`, `curr_line_1`, `curr_line_2`, `curr_line_3`, `curr_city`, `curr_zip_postcode`, `curr_state_province_county`, `curr_country`, `perm_address_id`, `perm_line_1`, `perm_line_2`, `perm_line_3`, `perm_city`, `perm_zip_postcode`, `perm_state_province_county`, `perm_country` |
| source tables | `Students`, `Addresses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Denormalized relation joining students to their current and permanent address records, keeping address fields for comparison or filtering of address differences.

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
    "contract_version": 3,
    "grain_basis": "verified_unique",
    "lineage": [
      "Students",
      "Addresses"
    ],
    "source_columns": [
      "Students.student_id",
      "Students.first_name",
      "Students.current_address_id",
      "Students.permanent_address_id",
      "Addresses.address_id",
      "Addresses.line_1",
      "Addresses.line_2",
      "Addresses.line_3",
      "Addresses.city",
      "Addresses.zip_postcode",
      "Addresses.state_province_county",
      "Addresses.country"
    ],
    "output_lineage": {
      "student_id": [
        "Students.student_id"
      ],
      "first_name": [
        "Students.first_name"
      ],
      "current_address_id": [
        "Students.current_address_id"
      ],
      "permanent_address_id": [
        "Students.permanent_address_id"
      ],
      "curr_address_id": [
        "Addresses.address_id"
      ],
      "curr_line_1": [
        "Addresses.line_1"
      ],
      "curr_line_2": [
        "Addresses.line_2"
      ],
      "curr_line_3": [
        "Addresses.line_3"
      ],
      "curr_city": [
        "Addresses.city"
      ],
      "curr_zip_postcode": [
        "Addresses.zip_postcode"
      ],
      "curr_state_province_county": [
        "Addresses.state_province_county"
      ],
      "curr_country": [
        "Addresses.country"
      ],
      "perm_address_id": [
        "Addresses.address_id"
      ],
      "perm_line_1": [
        "Addresses.line_1"
      ],
      "perm_line_2": [
        "Addresses.line_2"
      ],
      "perm_line_3": [
        "Addresses.line_3"
      ],
      "perm_city": [
        "Addresses.city"
      ],
      "perm_zip_postcode": [
        "Addresses.zip_postcode"
      ],
      "perm_state_province_county": [
        "Addresses.state_province_county"
      ],
      "perm_country": [
        "Addresses.country"
      ]
    },
    "operators": [
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "students": "ad3aee5be9cacc55",
      "addresses": "be6ad43bf746a2b6"
    },
    "data_fingerprints": {
      "students": "15:15",
      "addresses": "15:15"
    },
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_560",
    "question": "What is the first name of the student whose permanent address is different from his or her current one?",
    "rewrite": "Task: Find the first name of the student whose permanent address is different from his or her current address.\nRequired outputs: first name of the student\nFilters: rows where permanent address != current address (i.e., permanent address and current address are not equal strings)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:15:38+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:15:41+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "first_name",
      "current_address_id",
      "permanent_address_id",
      "curr_address_id",
      "curr_line_1",
      "curr_line_2",
      "curr_line_3",
      "curr_city",
      "curr_zip_postcode",
      "curr_state_province_county",
      "curr_country",
      "perm_address_id",
      "perm_line_1",
      "perm_line_2",
      "perm_line_3",
      "perm_city",
      "perm_zip_postcode",
      "perm_state_province_county",
      "perm_country"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Students.current_address_id=Addresses.address_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      },
      {
        "join": "Students.permanent_address_id=Addresses.address_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "View grain enforcement: student_id should be unique (no duplicate student_id rows)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id, COUNT(*) AS cnt FROM student_address_denormalized GROUP BY student_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Join completeness: every Students row should appear in the view (no students dropped by the joins)",
        "sql": "SELECT COUNT(*) FROM Students s LEFT JOIN student_address_denormalized v ON s.student_id = v.student_id WHERE v.student_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Field provenance consistency: current_address_id and permanent_address_id in the view must match the Students table values",
        "sql": "SELECT COUNT(*) FROM student_address_denormalized v JOIN Students s ON v.student_id = s.student_id WHERE (v.current_address_id IS NOT s.current_address_id) OR (v.permanent_address_id IS NOT s.permanent_address_id)",
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
SELECT s.student_id, s.first_name, s.current_address_id, s.permanent_address_id, curr.address_id AS curr_address_id, curr.line_1 AS curr_line_1, curr.line_2 AS curr_line_2, curr.line_3 AS curr_line_3, curr.city AS curr_city, curr.zip_postcode AS curr_zip_postcode, curr.state_province_county AS curr_state_province_county, curr.country AS curr_country, perm.address_id AS perm_address_id, perm.line_1 AS perm_line_1, perm.line_2 AS perm_line_2, perm.line_3 AS perm_line_3, perm.city AS perm_city, perm.zip_postcode AS perm_zip_postcode, perm.state_province_county AS perm_state_province_county, perm.country AS perm_country FROM Students s LEFT JOIN Addresses curr ON s.current_address_id = curr.address_id LEFT JOIN Addresses perm ON s.permanent_address_id = perm.address_id
```

---

## Skill `address_current_student_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `address_id`, `line_1`, `line_2`, `line_3`, `city`, `zip_postcode`, `state_province_county`, `country`, `other_address_details` (keyed) |
| status / version | active / v1 |
| skill id | sk_7ae3827cbe3aeb7e |
| output columns | `address_id`, `line_1`, `line_2`, `line_3`, `city`, `zip_postcode`, `state_province_county`, `country`, `other_address_details`, `student_count` |
| source tables | `Addresses`, `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-address counts of students based on the students' current/active address association (one row per address with keys and student count).

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Addresses",
      "Students"
    ],
    "source_columns": [
      "Addresses.address_id",
      "Addresses.line_1",
      "Addresses.line_2",
      "Addresses.line_3",
      "Addresses.city",
      "Addresses.zip_postcode",
      "Addresses.state_province_county",
      "Addresses.country",
      "Addresses.other_address_details",
      "Students.student_id",
      "Students.current_address_id"
    ],
    "output_lineage": {
      "address_id": [
        "Addresses.address_id"
      ],
      "line_1": [
        "Addresses.line_1"
      ],
      "line_2": [
        "Addresses.line_2"
      ],
      "line_3": [
        "Addresses.line_3"
      ],
      "city": [
        "Addresses.city"
      ],
      "zip_postcode": [
        "Addresses.zip_postcode"
      ],
      "state_province_county": [
        "Addresses.state_province_county"
      ],
      "country": [
        "Addresses.country"
      ],
      "other_address_details": [
        "Addresses.other_address_details"
      ],
      "student_count": [
        "Students.student_id"
      ]
    },
    "operators": [
      "filter",
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "addresses": "be6ad43bf746a2b6",
      "students": "ad3aee5be9cacc55"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_561",
    "question": "Which address holds the most number of students currently? List the address id and all lines.",
    "rewrite": "Task: Find the address (address id and all address lines) that currently has the largest number of students living at it.\nRequired outputs: address id; all address lines (every column that represents address lines for an address record)\nFilters: Only consider students who are currently associated with an address (i.e., active/current student-address relationships in the database).; Count students per address using current/active student-address associations; exclude historical/previous associations if there is an explicit flag or date range distinguishing current vs past.; If multiple addresses tie for the maximum student count, return all of those address records.\nSort/limit: no particular ordering required; limit to rows that have the maximum student count (i.e., all tied maxima)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:16:04+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:16:07+00:00",
    "contract_version": 3,
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
    "row_count": 9,
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
        "purpose": "View has one row per address key (no duplicate address key combinations)",
        "sql": "SELECT COUNT(*) FROM address_current_student_counts v GROUP BY address_id, line_1, line_2, line_3, city, zip_postcode, state_province_county, country, other_address_details HAVING COUNT(*)>1 LIMIT 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count equals count of Students with that current_address_id (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM address_current_student_counts v LEFT JOIN (SELECT current_address_id AS address_id, COUNT(*) AS cnt FROM Students WHERE current_address_id IS NOT NULL GROUP BY current_address_id) s ON v.address_id = s.address_id WHERE COALESCE(s.cnt,0) != COALESCE(v.student_count,0)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's address_id refers to an existing Addresses row (join didn't create phantom addresses)",
        "sql": "SELECT COUNT(*) FROM address_current_student_counts v LEFT JOIN Addresses a ON v.address_id = a.address_id WHERE a.address_id IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 2,
    "selected": 2,
    "included": 2,
    "referenced": 2,
    "executed": 2,
    "inconclusive": 2,
    "positive": 1,
    "positive_subgoals": [
      "Task: Count the number of distinct addresses where students currently live\nRequired outputs: count of distinct student addresses as an integer\nFilters: include only rows for current students (i.e., students who are considered current in the dataset); treat addresses as distinct by exact match of the address field value provided for each student"
    ],
    "last_used": "spider_dev_578",
    "negative": 1,
    "negative_subgoals": [
      "Task: List each distinct address that has one or more students living there.\nRequired outputs: address (the address value for locations where students live)\nFilters: Include only addresses that are associated with at least one student; Exclude addresses with no students living there"
    ]
  }
}
```

### Validated on (1)

- How many different addresses do the students currently live?

### Counter-examples (1)

- What are the different addresses that have students living there?

### Executable SQL body

```sql
SELECT A.address_id, A.line_1, A.line_2, A.line_3, A.city, A.zip_postcode, A.state_province_county, A.country, A.other_address_details, COUNT(S.student_id) AS student_count FROM Addresses A JOIN Students S ON S.current_address_id = A.address_id WHERE S.current_address_id IS NOT NULL GROUP BY A.address_id, A.line_1, A.line_2, A.line_3, A.city, A.zip_postcode, A.state_province_county, A.country, A.other_address_details
```

---

## Skill `address_student_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `address_id`, `line_1`, `line_2` (keyed) |
| status / version | active / v1 |
| skill id | sk_89a5b439ef6182b4 |
| output columns | `address_id`, `line_1`, `line_2`, `student_count` |
| source tables | `Addresses`, `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-address counts of distinct students linked via current or permanent address (one row per address with student count and address fields)

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Addresses",
      "Students"
    ],
    "source_columns": [
      "Addresses.address_id",
      "Addresses.line_1",
      "Addresses.line_2",
      "dedup.address_id",
      "Students.student_id",
      "Students.current_address_id",
      "Students.permanent_address_id"
    ],
    "output_lineage": {
      "address_id": [
        "Addresses.address_id"
      ],
      "line_1": [
        "Addresses.line_1"
      ],
      "line_2": [
        "Addresses.line_2"
      ],
      "student_count": []
    },
    "operators": [
      "filter",
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "addresses": "be6ad43bf746a2b6",
      "students": "ad3aee5be9cacc55"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_562",
    "question": "What is the id, line 1, and line 2 of the address with the most students?",
    "rewrite": "Task: Find the address (its id, line 1, and line 2) that is associated with the largest number of students.\nRequired outputs: id; line 1; line 2\nFilters: consider only rows where an address is linked to one or more students; count students per address and choose the address with the maximum student count; if multiple addresses tie for the maximum count, include all such addresses",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:16:26+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:16:29+00:00",
    "contract_version": 3,
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
    "join_cardinality": [
      {
        "join": "Addresses.address_id=dedup.address_id",
        "left_unique": true,
        "right_unique": null,
        "relationship": "unknown"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (address_id, line_1, line_2)",
        "sql": "SELECT COUNT(*) FROM (SELECT address_id, line_1, line_2, COUNT(*) AS ct FROM address_student_counts GROUP BY address_id, line_1, line_2 HAVING ct > 1) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count equals the number of distinct students (via current or permanent) linked to that address",
        "sql": "SELECT COUNT(*) FROM address_student_counts AS v LEFT JOIN ( SELECT A.address_id, COUNT(DISTINCT s.student_id) AS correct_count FROM Addresses A JOIN ( SELECT DISTINCT student_id, current_address_id AS address_id FROM Students WHERE current_address_id IS NOT NULL UNION ALL SELECT DISTINCT student_id, permanent_address_id AS address_id FROM Students WHERE permanent_address_id IS NOT NULL ) AS d ON A.address_id = d.address_id GROUP BY A.address_id ) AS calc ON v.address_id = calc.address_id WHERE (v.student_count IS NOT calc.correct_count) OR (v.student_count IS NULL AND calc.correct_count IS NOT NULL) OR (v.student_count IS NOT NULL AND calc.correct_count IS NULL)",
        "result": "inconclusive",
        "violations": null,
        "error": "OperationalError: no such column: s.student_id"
      },
      {
        "purpose": "Every view row refers to an existing Addresses.address_id (no missing FK join) and address_id is not NULL",
        "sql": "SELECT COUNT(*) FROM address_student_counts v WHERE v.address_id IS NULL OR NOT EXISTS (SELECT 1 FROM Addresses A WHERE A.address_id = v.address_id)",
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
SELECT A.address_id, A.line_1, A.line_2, COUNT(*) AS student_count FROM ( SELECT DISTINCT student_id, current_address_id AS address_id FROM Students WHERE current_address_id IS NOT NULL UNION ALL SELECT DISTINCT student_id, permanent_address_id AS address_id FROM Students WHERE permanent_address_id IS NOT NULL ) AS dedup JOIN Addresses A ON A.address_id = dedup.address_id GROUP BY A.address_id, A.line_1, A.line_2
```

---

## Skill `transcripts_with_printed_date`

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

All transcript rows that have a non-null printed/printed date/time for use in joins or aggregate calculations

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
    "contract_version": 3,
    "grain_basis": "primary_key",
    "lineage": [
      "Transcripts"
    ],
    "source_columns": [
      "Transcripts.transcript_id",
      "Transcripts.transcript_date"
    ],
    "output_lineage": {
      "transcript_id": [
        "Transcripts.transcript_id"
      ],
      "transcript_date": [
        "Transcripts.transcript_date"
      ]
    },
    "operators": [
      "filter",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "transcripts": "e9e22770a8b921c8"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_563",
    "question": "On average, when were the transcripts printed?",
    "rewrite": "Task: Compute the average date on which the transcripts were printed.\nRequired outputs: average printed date of transcripts (a single value representing the mean of the transcript printed dates)\nFilters: Include only rows that represent transcripts (as provided by the transcripts table or equivalent).; Exclude rows with NULL or missing printed date values.; Treat printed dates as date/time values; if stored with time, include full precision when computing the average.",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:16:40+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:16:42+00:00",
    "contract_version": 3,
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
        "purpose": "View contains only rows that actually have a non-NULL transcript_date (intrinsic filter respected)",
        "sql": "SELECT COUNT(*) FROM transcripts_with_printed_date v WHERE v.transcript_date IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View grain uniqueness: no duplicate transcript_id rows",
        "sql": "SELECT COUNT(*) FROM (SELECT transcript_id, COUNT(*) AS cnt FROM transcripts_with_printed_date GROUP BY transcript_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View includes exactly the Transcripts rows with non-NULL transcript_date (no missing or extra rows compared to base table)",
        "sql": "SELECT COUNT(*) FROM (SELECT transcript_id FROM transcripts_with_printed_date EXCEPT SELECT transcript_id FROM Transcripts WHERE transcript_date IS NOT NULL UNION ALL SELECT transcript_id FROM Transcripts WHERE transcript_date IS NOT NULL EXCEPT SELECT transcript_id FROM transcripts_with_printed_date)",
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
| skill id | sk_a2d6e750ef3975fb |
| output columns | `student_course_id`, `distinct_transcript_count` |
| source tables | `Student_Enrolment_Courses`, `Transcript_Contents` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per student course enrollment, the count of distinct transcripts that reference that enrollment (one row per student_course_id and its distinct transcript count).

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Student_Enrolment_Courses",
      "Transcript_Contents"
    ],
    "source_columns": [
      "Student_Enrolment_Courses.student_course_id",
      "Transcript_Contents.student_course_id",
      "Transcript_Contents.transcript_id"
    ],
    "output_lineage": {
      "student_course_id": [
        "Student_Enrolment_Courses.student_course_id"
      ],
      "distinct_transcript_count": [
        "Transcript_Contents.transcript_id"
      ]
    },
    "operators": [
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "student_enrolment_courses": "daf1efe3c261d034",
      "transcript_contents": "ecac21baa04d7c6d"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_571",
    "question": "How many times at most can a course enrollment result show in different transcripts? Also show the course enrollment id.",
    "rewrite": "Task: Compute, for each course enrollment id, the maximum number of distinct transcripts in which that course enrollment appears; return the course enrollment id together with that maximum count.\nRequired outputs: course enrollment id; maximum number of different transcripts that the given course enrollment appears in (an integer)\nFilters: Consider all course enrollments present in the database (no additional filtering unless specified elsewhere); Count distinct transcript identifiers for each course enrollment when determining how many different transcripts it appears in\nSort/limit: order results by the maximum count descending; if tie-breaker needed, order by course enrollment id ascending; no row limit",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:19:05+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:19:07+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "student_course_id",
      "distinct_transcript_count"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Student_Enrolment_Courses.student_course_id=Transcript_Contents.student_course_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "View has one row per student_course_id in Student_Enrolment_Courses (no missing enrollments)",
        "sql": "SELECT COUNT(*) FROM Student_Enrolment_Courses sec WHERE NOT EXISTS (SELECT 1 FROM student_course_transcript_counts v WHERE v.student_course_id = sec.student_course_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_course_id is unique in the view (no duplicate keys)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_course_id, COUNT(*) AS cnt FROM student_course_transcript_counts GROUP BY student_course_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "distinct_transcript_count matches count of distinct Transcript_Contents.transcript_id per student_course_id",
        "sql": "SELECT COUNT(*) FROM student_course_transcript_counts v LEFT JOIN (SELECT student_course_id, COUNT(DISTINCT transcript_id) AS expected_count FROM Transcript_Contents GROUP BY student_course_id) t ON v.student_course_id = t.student_course_id WHERE COALESCE(v.distinct_transcript_count, 0) != COALESCE(t.expected_count, 0)",
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
      "Task: Find the course that appears in the largest number of distinct transcripts and report that maximum count along with that course's enrollment id.\nRequired outputs: enrollment id (identifier of the course enrollment); count of distinct transcripts in which that course enrollment appears (an integer)\nFilters: consider distinct transcripts (do not double-count the same transcript); include only course enrollments that appear in at least one transcript\nSort/limit: order by count descending limit 1"
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
SELECT sec.student_course_id AS student_course_id, COUNT(DISTINCT tc.transcript_id) AS distinct_transcript_count FROM Student_Enrolment_Courses AS sec LEFT JOIN Transcript_Contents AS tc ON sec.student_course_id = tc.student_course_id GROUP BY sec.student_course_id
```

---

## Skill `transcript_results_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `transcript_id`, `transcript_date` (keyed) |
| status / version | active / v1 |
| skill id | sk_3bdc4aed26de242d |
| output columns | `transcript_id`, `transcript_date`, `results` |
| source tables | `Transcripts`, `Transcript_Contents` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-transcript count of Transcript_Contents rows (number of results) with transcript id and date for joining or filtering

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Transcripts",
      "Transcript_Contents"
    ],
    "source_columns": [
      "Transcripts.transcript_id",
      "Transcripts.transcript_date",
      "Transcript_Contents.student_course_id",
      "Transcript_Contents.transcript_id"
    ],
    "output_lineage": {
      "transcript_id": [
        "Transcripts.transcript_id"
      ],
      "transcript_date": [
        "Transcripts.transcript_date"
      ],
      "results": [
        "Transcript_Contents.student_course_id"
      ]
    },
    "operators": [
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "transcripts": "e9e22770a8b921c8",
      "transcript_contents": "ecac21baa04d7c6d"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_574",
    "question": "What is the date and id of the transcript with the least number of results?",
    "rewrite": "Task: Find the transcript record that has the smallest value in its 'results' field and report that transcript's 'date' and 'id'.\nRequired outputs: date; id\nFilters: select rows where results is equal to the minimum results value across all transcripts (i.e., the transcript(s) with the least number of results)\nSort/limit: if multiple transcripts tie for the minimum results, return all tied rows; otherwise return the single row with the minimum results; no additional ordering",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:19:57+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:19:59+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "transcript_id",
      "transcript_date",
      "results"
    ],
    "row_count": 15,
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
        "purpose": "No duplicate rows at the declared grain (transcript_id, transcript_date)",
        "sql": "SELECT COUNT(*) FROM (SELECT transcript_id, transcript_date, COUNT(*) AS c FROM transcript_results_counts GROUP BY transcript_id, transcript_date HAVING c > 1) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "results matches count of Transcript_Contents rows (including zero) per transcript",
        "sql": "SELECT COUNT(*) FROM (SELECT t.transcript_id, t.transcript_date, trc.results, COALESCE(tc.cnt,0) AS expected FROM Transcripts t LEFT JOIN transcript_results_counts trc ON trc.transcript_id = t.transcript_id AND trc.transcript_date = t.transcript_date LEFT JOIN (SELECT transcript_id, COUNT(student_course_id) AS cnt FROM Transcript_Contents GROUP BY transcript_id) tc ON tc.transcript_id = t.transcript_id WHERE trc.results IS NULL OR trc.results != COALESCE(tc.cnt,0)) AS mismatches",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in view has non-NULL keys transcript_id and transcript_date",
        "sql": "SELECT COUNT(*) FROM transcript_results_counts WHERE transcript_id IS NULL OR transcript_date IS NULL",
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
SELECT t.transcript_id AS transcript_id, t.transcript_date AS transcript_date, COUNT(tc.student_course_id) AS results FROM Transcripts t LEFT JOIN Transcript_Contents tc ON tc.transcript_id = t.transcript_id GROUP BY t.transcript_id, t.transcript_date
```

---

## Skill `semester_enrollment_by_degree_summary`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `semester_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_8178418ad4b425e0 |
| output columns | `semester_id`, `distinct_degree_summary_count` |
| source tables | `Student_Enrolment`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-semester counts of distinct degree summary categories (e.g., Bachelor, Master) based on student enrolment linked to degree programs, useful for identifying semesters containing specific combinations of study levels.

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
      "'Bachelor'",
      "= 2"
    ],
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Student_Enrolment",
      "Degree_Programs"
    ],
    "source_columns": [
      "Student_Enrolment.semester_id",
      "Degree_Programs.degree_program_id",
      "Student_Enrolment.degree_program_id",
      "Degree_Programs.degree_summary_name"
    ],
    "output_lineage": {
      "semester_id": [
        "Student_Enrolment.semester_id"
      ],
      "distinct_degree_summary_count": [
        "Degree_Programs.degree_summary_name"
      ]
    },
    "operators": [
      "join",
      "project",
      "aggregate"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "student_enrolment": "445257138d420d03",
      "degree_programs": "85466a54c4a97bc7"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_576",
    "question": "What is the id of the semester that had both Masters and Bachelors students enrolled?",
    "rewrite": "Task: Find the semester id for the semester(s) that had at least one Masters student and at least one Bachelors student enrolled in that same semester.\nRequired outputs: semester id\nFilters: semester must have enrollment records (or links) indicating student study level = 'Masters' and also student study level = 'Bachelors' for the same semester id",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:20:45+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:20:48+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "semester_id",
      "distinct_degree_summary_count"
    ],
    "row_count": 9,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Degree_Programs.degree_program_id=Student_Enrolment.degree_program_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "No NULLs in the view key semester_id (every row must have a non-NULL key)",
        "sql": "SELECT COUNT(*) FROM semester_enrollment_by_degree_summary WHERE semester_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "distinct_degree_summary_count equals the distinct count of Degree_Programs.degree_summary_name for that semester (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM semester_enrollment_by_degree_summary v LEFT JOIN (SELECT se.semester_id AS semester_id, COUNT(DISTINCT dp.degree_summary_name) AS expected_count FROM Student_Enrolment se JOIN Degree_Programs dp ON dp.degree_program_id = se.degree_program_id GROUP BY se.semester_id) calc ON v.semester_id = calc.semester_id WHERE (v.distinct_degree_summary_count IS NULL AND calc.expected_count IS NOT NULL) OR (v.distinct_degree_summary_count IS NOT NULL AND calc.expected_count IS NULL) OR (v.distinct_degree_summary_count != calc.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No duplicate rows in the view at the declared grain (each semester_id appears at most once)",
        "sql": "SELECT COUNT(*) FROM (SELECT semester_id, COUNT(*) AS cnt FROM semester_enrollment_by_degree_summary GROUP BY semester_id HAVING cnt > 1)",
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
SELECT se.semester_id, COUNT(DISTINCT dp.degree_summary_name) AS distinct_degree_summary_count FROM Student_Enrolment se JOIN Degree_Programs dp ON dp.degree_program_id = se.degree_program_id GROUP BY se.semester_id
```

---

## Skill `student_permanent_address_and_contact`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `student_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_5f0e703be7463071 |
| output columns | `student_id`, `first_name`, `permanent_address_id`, `cell_mobile_number`, `perm_address_id`, `perm_country` |
| source tables | `Students`, `Addresses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-student relation that includes student IDs, first names, permanent address ID and country, and cell phone number to enable filtering or joining by residence country or phone.

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
    "contract_version": 3,
    "grain_basis": "verified_unique",
    "lineage": [
      "Students",
      "Addresses"
    ],
    "source_columns": [
      "Students.student_id",
      "Students.first_name",
      "Students.permanent_address_id",
      "Students.cell_mobile_number",
      "Addresses.address_id",
      "Addresses.country"
    ],
    "output_lineage": {
      "student_id": [
        "Students.student_id"
      ],
      "first_name": [
        "Students.first_name"
      ],
      "permanent_address_id": [
        "Students.permanent_address_id"
      ],
      "cell_mobile_number": [
        "Students.cell_mobile_number"
      ],
      "perm_address_id": [
        "Addresses.address_id"
      ],
      "perm_country": [
        "Addresses.country"
      ]
    },
    "operators": [
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "students": "ad3aee5be9cacc55",
      "addresses": "be6ad43bf746a2b6"
    },
    "data_fingerprints": {
      "students": "15:15",
      "addresses": "15:15"
    },
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_583",
    "question": "Find the first name of the students who permanently live in the country Haiti or have the cell phone number 09700166582 .",
    "rewrite": "Task: Return the first names of students who either permanently live in the country 'Haiti' or whose cell phone number is '09700166582'.\nRequired outputs: first name\nFilters: permanent residence country = 'Haiti' OR cell phone number = '09700166582'",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:22:37+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:22:39+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "first_name",
      "permanent_address_id",
      "cell_mobile_number",
      "perm_address_id",
      "perm_country"
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
        "purpose": "View grain: student_id should be unique (no duplicate student_id rows)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id, COUNT(*) AS cnt FROM student_permanent_address_and_contact GROUP BY student_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Join did not invent non-existent address matches: when perm_address_id is not NULL it must exist in Addresses.address_id",
        "sql": "SELECT COUNT(*) FROM student_permanent_address_and_contact v WHERE v.perm_address_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM Addresses a WHERE a.address_id = v.perm_address_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Key not NULL: student_id must not be NULL",
        "sql": "SELECT COUNT(*) FROM student_permanent_address_and_contact WHERE student_id IS NULL",
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
SELECT Students.student_id, Students.first_name, Students.permanent_address_id, Students.cell_mobile_number, Addresses.address_id AS perm_address_id, Addresses.country AS perm_country FROM Students LEFT JOIN Addresses ON Students.permanent_address_id = Addresses.address_id
```

---

## Skill `students_with_addresses_and_contact`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `student_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_0b4686457e820218 |
| output columns | `student_id`, `first_name`, `cell_mobile_number`, `permanent_address_id`, `current_address_id`, `perm_address_id`, `perm_country`, `curr_address_id`, `curr_country` |
| source tables | `Students`, `Addresses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-student contact and linked permanent/current address information for use in residence- or contact-based filters or joins.

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
      "permanently",
      "09700166582"
    ],
    "contract_version": 3,
    "grain_basis": "verified_unique",
    "lineage": [
      "Students",
      "Addresses"
    ],
    "source_columns": [
      "Students.student_id",
      "Students.first_name",
      "Students.cell_mobile_number",
      "Students.permanent_address_id",
      "Students.current_address_id",
      "Addresses.address_id",
      "Addresses.country"
    ],
    "output_lineage": {
      "student_id": [
        "Students.student_id"
      ],
      "first_name": [
        "Students.first_name"
      ],
      "cell_mobile_number": [
        "Students.cell_mobile_number"
      ],
      "permanent_address_id": [
        "Students.permanent_address_id"
      ],
      "current_address_id": [
        "Students.current_address_id"
      ],
      "perm_address_id": [
        "Addresses.address_id"
      ],
      "perm_country": [
        "Addresses.country"
      ],
      "curr_address_id": [
        "Addresses.address_id"
      ],
      "curr_country": [
        "Addresses.country"
      ]
    },
    "operators": [
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
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
    "rewrite": "Task: Return the first names of students who either live in Haiti permanently or have the cell phone number 09700166582.\nRequired outputs: first name\nFilters: student's residence country equals 'Haiti' AND residence status equals 'permanently' OR student's cell phone number equals '09700166582'",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:22:58+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:23:00+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "first_name",
      "cell_mobile_number",
      "permanent_address_id",
      "current_address_id",
      "perm_address_id",
      "perm_country",
      "curr_address_id",
      "curr_country"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Addresses.address_id=Students.permanent_address_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      },
      {
        "join": "Addresses.address_id=Students.current_address_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "View grain: student_id should be unique (no duplicate student rows)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id, COUNT(*) AS cnt FROM students_with_addresses_and_contact GROUP BY student_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every student_id in the view must exist in base Students table (no spuriously introduced student_ids)",
        "sql": "SELECT COUNT(*) FROM students_with_addresses_and_contact v WHERE NOT EXISTS (SELECT 1 FROM Students s WHERE s.student_id = v.student_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "If perm_address_id or curr_address_id in view is non-NULL it must match an Addresses.address_id (joined address not missing)",
        "sql": "SELECT COUNT(*) FROM students_with_addresses_and_contact v WHERE (v.perm_address_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM Addresses a WHERE a.address_id = v.perm_address_id)) OR (v.curr_address_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM Addresses a WHERE a.address_id = v.curr_address_id))",
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
SELECT s.student_id, s.first_name, s.cell_mobile_number, s.permanent_address_id, s.current_address_id, pa.address_id AS perm_address_id, pa.country AS perm_country, ca.address_id AS curr_address_id, ca.country AS curr_country FROM "Students" s LEFT JOIN "Addresses" pa ON pa.address_id = s.permanent_address_id LEFT JOIN "Addresses" ca ON ca.address_id = s.current_address_id
```

---
