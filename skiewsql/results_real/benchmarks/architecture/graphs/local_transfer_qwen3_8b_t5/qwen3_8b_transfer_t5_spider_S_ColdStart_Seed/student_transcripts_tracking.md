# Skill graph — `student_transcripts_tracking` (30 skills)

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

Per-department counts of degree program records (one row per department with department id, name, and degree count) to support analyses of degree distribution across departments.

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
    "rewrite": "Task: Find the department (name and id) that offers the largest number of degrees, returning the department's name and id for the department(s) with the maximum count of degrees offered.\nRequired outputs: department name; department id\nFilters: Count degrees per department across all degree records; include only department(s) whose degree count equals the maximum degree count observed (i.e., return ties if multiple departments share the highest number). No other row-level filters.; Treat every degree record as contributing one to its department's degree total (no additional exclusions).\nSort/limit: no particular ordering required; return all department rows that tie for the maximum count (no numeric limit)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:27:14+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:27:16+00:00",
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
        "purpose": "View has one row per department (no duplicate department_id, department_name pairs)",
        "sql": "SELECT COUNT(*) FROM (SELECT department_id, department_name, COUNT(*) as cnt FROM department_degree_counts GROUP BY department_id, department_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "degree_count equals count of Degree_Programs linked to the department (reconciliation with base table)",
        "sql": "SELECT COUNT(*) FROM department_degree_counts v LEFT JOIN Departments d ON v.department_id = d.department_id LEFT JOIN (SELECT department_id, COUNT(*) AS actual_count FROM Degree_Programs GROUP BY department_id) dp ON d.department_id = dp.department_id WHERE COALESCE(v.degree_count,0) != COALESCE(dp.actual_count,0)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No NULLs in the key columns department_id or department_name",
        "sql": "SELECT COUNT(*) FROM department_degree_counts WHERE department_id IS NULL OR department_name IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 38,
    "selected": 5,
    "included": 3,
    "referenced": 3,
    "executed": 3,
    "inconclusive": 3,
    "positive": 3,
    "positive_subgoals": [
      "Task: Find the department that has the largest number of degrees and return that department's name and id.\nRequired outputs: department name; department id\nFilters: Consider departments that have one or more associated degree records.; If multiple departments tie for the largest number of degrees, return all tied departments.\nSort/limit: order by descending degree count; no fixed numeric limit (return all ties for top count)",
      "Task: Compute the number of departments that offer any degree (i.e., count distinct departments that offer at least one degree).\nRequired outputs: count of departments that offer any degree\nFilters: Include only departments that have at least one associated degree record (i.e., departments with one or more degrees). Do not count departments with zero degrees.",
      "Task: Compute the number of distinct departments that offer degrees.\nRequired outputs: count_of_distinct_departments: an integer representing how many different departments offer at least one degree\nFilters: Consider only rows where a department is recorded as 'offering a degree' (i.e., associated with at least one degree record).; Treat departments with the same name as identical (count unique department identifiers or names).; Exclude null or missing department identifiers/names from the count."
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

Per-course counts of linked sections (number of sections per course), including course id and name for joining

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
      "Sections.section_id",
      "Sections.course_id"
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
    "rewrite": "Task: Return the course names and course ids for every course that has at most 2 sections.\nRequired outputs: course name; course id\nFilters: Include only rows for courses whose number of sections is less than or equal to 2; Count sections per course using whatever table/column represents sections linked to a course (i.e., group by course id)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:29:53+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:29:56+00:00",
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
        "join": "Sections.course_id=Courses.course_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows per grain (course_id, course_name) in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT course_id, course_name, COUNT(*) AS dup_count FROM course_section_counts GROUP BY course_id, course_name HAVING dup_count > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "section_count matches count of Sections linked to each course (recomputed from base tables)",
        "sql": "SELECT COUNT(*) FROM course_section_counts v LEFT JOIN Courses c ON v.course_id = c.course_id LEFT JOIN (SELECT course_id, COUNT(section_id) AS real_count FROM Sections GROUP BY course_id) s ON v.course_id = s.course_id WHERE COALESCE(s.real_count, 0) != v.section_count",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys (course_id and course_name) are not NULL in the view",
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
      "Task: Return the name and id of every course that has fewer than 2 sections.\nRequired outputs: course name; course id\nFilters: count of sections associated with the course < 2"
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
SELECT c.course_id, c.course_name, COUNT(s.section_id) AS section_count FROM Courses c LEFT JOIN Sections s ON s.course_id = c.course_id GROUP BY c.course_id, c.course_name
```

---

## Skill `semester_registration_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `semester_id`, `semester_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_a6786e78d7ea2161 |
| output columns | `semester_id`, `semester_name`, `registration_count` |
| source tables | `Semesters`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-semester counts of student registrations (one row per semester with semester_id, semester_name, and registration_count) for use in further aggregation or ranking.

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
      "semesters": "29c2494a0d4e0c8e",
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_529",
    "question": "What is the semester which most student registered in? Show both the name and the id.",
    "rewrite": "Task: Find the semester (both its name and its id) that has the largest number of student registrations.\nRequired outputs: semester id; semester name\nFilters: Count registrations per semester across all students; include only semester(s) with the maximum registration count (if tie, return all tied semesters).\nSort/limit: order by registration count descending, limit to the top count (no numeric limit if ties should be returned)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:30:54+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:30:56+00:00",
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
        "purpose": "View has exactly one row per semester (no duplicate rows with same semester_id and semester_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT semester_id, semester_name, COUNT(*) AS cnt FROM semester_registration_counts GROUP BY semester_id, semester_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "registration_count matches the count of Student_Enrolment rows per semester from base tables",
        "sql": "SELECT COUNT(*) FROM semester_registration_counts v LEFT JOIN (SELECT semester_id, COUNT(student_enrolment_id) AS expected_count FROM Student_Enrolment GROUP BY semester_id) b ON v.semester_id = b.semester_id WHERE COALESCE(v.registration_count, -9223372036854775808) != COALESCE(b.expected_count, -9223372036854775808)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No NULL keys: semester_id and semester_name must not be NULL",
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
SELECT s.semester_id, s.semester_name, COUNT(se.student_enrolment_id) AS registration_count FROM Semesters s JOIN Student_Enrolment se ON se.semester_id = s.semester_id GROUP BY s.semester_id, s.semester_name
```

---

## Skill `semester_student_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `semester_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_1da047a0a02c1ed1 |
| output columns | `semester_id`, `student_count` |
| source tables | `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-semester counts of students enrolled (one row per semester with semester id and student count) useful for ranking or join with semester metadata.

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
      "student_count": [
        "Student_Enrolment.student_id"
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
    "question_id": "spider_dev_530",
    "question": "For each semester, what is the name and id of the one with the most students registered?",
    "rewrite": "Task: For each semester, identify the single record (semester) participant entry that has the largest number of students registered and return that semester's name and id.\nRequired outputs: semester name; semester id\nFilters: Consider only rows grouped by semester (i.e., compute the count of students registered per semester).; For each semester, select the row corresponding to the maximum number of students registered for that semester.; If there are ties for the maximum number of students within a semester, include exactly one arbitrary tied semester entry (deterministic tie-breaking can be applied if available, otherwise pick one).\nSort/limit: Return one output row per semester; no global ordering required.",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:31:19+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:31:21+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "semester_id",
      "student_count"
    ],
    "row_count": 9,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows per grain: each semester_id appears at most once in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT semester_id, COUNT(*) AS cnt FROM semester_student_counts GROUP BY semester_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count equals count of distinct student_id rows in base table per semester (detects incorrect aggregation or missing GROUP BY on source)",
        "sql": "SELECT COUNT(*) FROM semester_student_counts v LEFT JOIN (SELECT semester_id, COUNT(se.student_id) AS expected_count FROM Student_Enrolment se GROUP BY se.semester_id) b ON v.semester_id = b.semester_id WHERE (b.expected_count IS NULL AND v.student_count IS NOT NULL) OR (b.expected_count IS NOT NULL AND v.student_count != b.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's semester_id in the view must exist in the base table (no phantom semesters produced)",
        "sql": "SELECT COUNT(*) FROM semester_student_counts v WHERE NOT EXISTS (SELECT 1 FROM Student_Enrolment se WHERE se.semester_id = v.semester_id)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 27
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT se.semester_id, COUNT(se.student_id) AS student_count FROM Student_Enrolment se GROUP BY se.semester_id
```

---

## Skill `student_semester_degree_program_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `student_id`, `semester_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_e8127617c4fa5a6b |
| output columns | `student_id`, `semester_id`, `degree_program_count` |
| source tables | `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each student and semester, count of distinct degree programs the student is enrolled in (one row per student_id and semester_id with the program count).

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
      "degree_program_count": [
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
    "rewrite": "Task: Find all students who are enrolled in exactly two degree programs during the same single semester; return each matching student's first name, middle name, last name, and id.\nRequired outputs: first name; middle name; last name; id\nFilters: student must have two distinct degree program enrollments that occur in the same semester (same semester identifier); count of distinct degree programs for that student in that semester = 2; exclude students with fewer or more than 2 degree programs in that semester",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:32:01+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:32:05+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "semester_id",
      "degree_program_count"
    ],
    "row_count": 14,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (student_id, semester_id) in the view",
        "sql": "SELECT COUNT(*) FROM student_semester_degree_program_counts v JOIN (SELECT student_id, semester_id, COUNT(*) AS cnt FROM student_semester_degree_program_counts GROUP BY student_id, semester_id HAVING cnt > 1) d ON v.student_id = d.student_id AND v.semester_id = d.semester_id",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "degree_program_count equals the distinct count of degree_program_id in base table for that student and semester",
        "sql": "SELECT COUNT(*) FROM student_semester_degree_program_counts v LEFT JOIN (SELECT student_id, semester_id, COUNT(DISTINCT degree_program_id) AS expected_cnt FROM Student_Enrolment GROUP BY student_id, semester_id) b ON v.student_id = b.student_id AND v.semester_id = b.semester_id WHERE (b.expected_cnt IS NULL AND v.degree_program_count IS NOT NULL) OR (b.expected_cnt IS NOT NULL AND v.degree_program_count <> b.expected_cnt)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys student_id and semester_id are not NULL in the view",
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
      "Task: Find all students who enrolled in exactly 2 degree programs within the same semester, and return each such student's first name, middle name, last name, and student id.\nRequired outputs: first name; middle name; last name; id (student id)\nFilters: Count of distinct degree program enrollments for the student within a single semester must be exactly 2; Enrollments considered must share the same semester identifier (e.g., same term/session and year) for each counted pair; Include only students for whom such a semester exists"
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
SELECT student_id, semester_id, COUNT(DISTINCT degree_program_id) AS degree_program_count
FROM Student_Enrolment
GROUP BY student_id, semester_id
```

---

## Skill `students_enrolled_in_degree_program`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `student_id`, `first_name`, `middle_name`, `last_name`, `degree_program_id`, `degree_summary_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_495b40055d80d2b5 |
| output columns | `student_id`, `first_name`, `middle_name`, `last_name`, `degree_program_id`, `degree_summary_name` |
| source tables | `Student_Enrolment`, `Degree_Programs`, `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

All students who have an enrollment linking them to a degree program, with student name parts and the associated degree program identifier and degree summary name for reuse/filtering by degree level.

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
      "'Bachelor'"
    ],
    "contract_version": 3,
    "grain_basis": "distinct",
    "lineage": [
      "Student_Enrolment",
      "Degree_Programs",
      "Students"
    ],
    "source_columns": [
      "Students.student_id",
      "Students.first_name",
      "Students.middle_name",
      "Students.last_name",
      "Student_Enrolment.degree_program_id",
      "Degree_Programs.degree_summary_name",
      "Degree_Programs.degree_program_id",
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
      "degree_program_id": [
        "Student_Enrolment.degree_program_id"
      ],
      "degree_summary_name": [
        "Degree_Programs.degree_summary_name"
      ]
    },
    "operators": [
      "join",
      "project",
      "distinct"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "student_enrolment": "445257138d420d03",
      "degree_programs": "85466a54c4a97bc7",
      "students": "ad3aee5be9cacc55"
    },
    "data_fingerprints": {
      "student_enrolment": "15:15",
      "degree_programs": "15:15",
      "students": "15:15"
    },
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_535",
    "question": "Who is enrolled in a Bachelor degree program? List the first name, middle name, last name.",
    "rewrite": "Task: Find all persons who are enrolled in a Bachelor degree program and return their name parts.\nRequired outputs: first name; middle name; last name\nFilters: Enrollment records must indicate the person is currently enrolled in a program whose degree level is 'Bachelor' (or equivalent string 'Bachelors'/'B.Sc' if present) — include only rows where the program/degree level equals 'Bachelor'.; Include each person only if there exists an enrollment linking that person to such a Bachelor program.; Return all matching persons (no additional filtering by date, active flag, or program type unless those are required by the schema to define 'enrolled').",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:32:55+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:32:58+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "student_id",
      "first_name",
      "middle_name",
      "last_name",
      "degree_program_id",
      "degree_summary_name"
    ],
    "row_count": 13,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Student_Enrolment.degree_program_id=Degree_Programs.degree_program_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      },
      {
        "join": "Student_Enrolment.student_id=Students.student_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (student_id, first_name, middle_name, last_name, degree_program_id, degree_summary_name).",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id, first_name, middle_name, last_name, degree_program_id, degree_summary_name, COUNT(*) as cnt FROM students_enrolled_in_degree_program GROUP BY student_id, first_name, middle_name, last_name, degree_program_id, degree_summary_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view corresponds to an existing Student_Enrolment row (join didn't fabricate rows).",
        "sql": "SELECT COUNT(*) FROM students_enrolled_in_degree_program v LEFT JOIN Student_Enrolment se ON v.student_id = se.student_id AND v.degree_program_id = se.degree_program_id WHERE se.student_enrolment_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No nulls in key columns of the view (student_id and degree_program_id must be present).",
        "sql": "SELECT COUNT(*) FROM students_enrolled_in_degree_program WHERE student_id IS NULL OR degree_program_id IS NULL",
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
SELECT DISTINCT s.student_id, s.first_name, s.middle_name, s.last_name, se.degree_program_id, dp.degree_summary_name
FROM Student_Enrolment se
JOIN Degree_Programs dp ON se.degree_program_id = dp.degree_program_id
JOIN Students s ON se.student_id = s.student_id
```

---

## Skill `student_count_per_degree_program_kind`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `program_kind` (keyed) |
| status / version | active / v1 |
| skill id | sk_3bd750c50ddad753 |
| output columns | `program_kind`, `student_count` |
| source tables | `Student_Enrolment`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per program kind (degree_summary_name) count of distinct students enrolled in any degree program

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
      "ORDER BY student_count DESC",
      "LIMIT 1"
    ],
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Student_Enrolment",
      "Degree_Programs"
    ],
    "source_columns": [
      "Degree_Programs.degree_summary_name",
      "Student_Enrolment.degree_program_id",
      "Degree_Programs.degree_program_id",
      "Student_Enrolment.student_id"
    ],
    "output_lineage": {
      "program_kind": [
        "Degree_Programs.degree_summary_name"
      ],
      "student_count": [
        "Student_Enrolment.student_id"
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
      "student_enrolment": "445257138d420d03",
      "degree_programs": "85466a54c4a97bc7"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_537",
    "question": "Find the kind of program which most number of students are enrolled in?",
    "rewrite": "Task: Identify which program kind has the largest number of enrolled students and return that program kind along with the student count.\nRequired outputs: program kind (the kind/type/category of program); student count (number of students enrolled in that program kind)\nFilters: consider all students and their enrollments across all program kinds; count each student enrollment toward the program kind they are enrolled in; include only program kinds that have at least one enrolled student\nSort/limit: order results by student count descending and return the top 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:33:33+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:33:37+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "program_kind",
      "student_count"
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
        "purpose": "No NULLs in key column program_kind",
        "sql": "SELECT COUNT(*) FROM student_count_per_degree_program_kind WHERE program_kind IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count matches COUNT(DISTINCT student_id) computed from base tables per program_kind",
        "sql": "SELECT COUNT(*) FROM student_count_per_degree_program_kind v LEFT JOIN (SELECT dp.degree_summary_name AS program_kind, COUNT(DISTINCT se.student_id) AS expected_count FROM Student_Enrolment se JOIN Degree_Programs dp ON se.degree_program_id = dp.degree_program_id WHERE se.degree_program_id IS NOT NULL GROUP BY dp.degree_summary_name) b USING (program_kind) WHERE (v.student_count IS NULL AND b.expected_count IS NOT NULL) OR (v.student_count IS NOT NULL AND b.expected_count IS NULL) OR (v.student_count <> b.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in view corresponds to at least one enrolment joined to a degree program (no spurious program_kind)",
        "sql": "SELECT COUNT(*) FROM student_count_per_degree_program_kind v LEFT JOIN (SELECT DISTINCT dp.degree_summary_name AS program_kind FROM Student_Enrolment se JOIN Degree_Programs dp ON se.degree_program_id = dp.degree_program_id WHERE se.degree_program_id IS NOT NULL) b USING (program_kind) WHERE b.program_kind IS NULL",
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
SELECT dp.degree_summary_name AS program_kind, COUNT(DISTINCT se.student_id) AS student_count FROM Student_Enrolment se JOIN Degree_Programs dp ON se.degree_program_id = dp.degree_program_id WHERE se.degree_program_id IS NOT NULL GROUP BY dp.degree_summary_name
```

---

## Skill `degree_program_student_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `degree_program_id`, `degree_summary_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_4f17d1e4b6293341 |
| output columns | `degree_program_id`, `degree_summary_name`, `student_count` |
| source tables | `Degree_Programs`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per degree program (including its degree_summary_name), the distinct count of enrolled students aggregated across all student_enrolment records.

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
    "rewrite": "Task: Find the degree summary name that has the largest number of enrolled students.\nRequired outputs: degree summary name (the name/label identifying a degree summary); student count for that degree summary (number of students enrolled)\nFilters: consider all degree summaries present in the data; count students enrolled per degree summary across all records\nSort/limit: order by student count descending, limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:33:50+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:33:52+00:00",
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
        "join": "Student_Enrolment.degree_program_id=Degree_Programs.degree_program_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "View has one row per (degree_program_id, degree_summary_name) — detect duplicate rows in the view's grain",
        "sql": "SELECT COUNT(*) FROM (SELECT degree_program_id, degree_summary_name FROM degree_program_student_counts GROUP BY degree_program_id, degree_summary_name HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count equals COUNT(DISTINCT student_id) computed from base table for each degree_program — detect mismatched aggregates",
        "sql": "SELECT COUNT(*) FROM degree_program_student_counts v LEFT JOIN Degree_Programs dp ON v.degree_program_id = dp.degree_program_id WHERE (SELECT COUNT(DISTINCT se.student_id) FROM Student_Enrolment se WHERE se.degree_program_id = v.degree_program_id) IS NOT v.student_count",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every view row references an existing degree_program (no dangling foreign keys)",
        "sql": "SELECT COUNT(*) FROM degree_program_student_counts v LEFT JOIN Degree_Programs dp ON v.degree_program_id = dp.degree_program_id WHERE dp.degree_program_id IS NULL",
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
SELECT dp.degree_program_id, dp.degree_summary_name, COUNT(DISTINCT se.student_id) AS student_count FROM Degree_Programs dp JOIN Student_Enrolment se ON se.degree_program_id = dp.degree_program_id GROUP BY dp.degree_program_id, dp.degree_summary_name
```

---

## Skill `program_student_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `degree_program_id`, `degree_summary_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_d71d97cbc63d3e8d |
| output columns | `degree_program_id`, `degree_summary_name`, `student_count` |
| source tables | `Degree_Programs`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-degree-program counts of enrolled students (one row per program with program id, program summary, and student enrollment count).

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
      "degree_summary_name": [
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
    "question_id": "spider_dev_539",
    "question": "Find the program which most number of students are enrolled in. List both the id and the summary.",
    "rewrite": "Task: Return the program (its id and summary) that has the largest number of students enrolled.\nRequired outputs: program id; program summary\nFilters: Consider all programs and count how many students are enrolled in each program using whatever enrollment relation exists between students and programs.; Select the program(s) with the maximum student count (if there is a tie, include all tied programs).\nSort/limit: order by student count desc; limit to the maximum count (no fixed numeric limit)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:34:06+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:34:09+00:00",
    "contract_version": 3,
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
        "purpose": "No duplicate rows at the declared grain (each degree_program_id + degree_summary_name appears at most once).",
        "sql": "SELECT COUNT(*) FROM (SELECT degree_program_id, degree_summary_name, COUNT(*) AS c FROM program_student_counts GROUP BY degree_program_id, degree_summary_name HAVING c > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count matches COUNT of Student_Enrolment rows for that program (reconciles measure with base table), accounting for LEFT JOIN semantics (0 when no enrolments).",
        "sql": "SELECT COUNT(*) FROM program_student_counts p LEFT JOIN Degree_Programs dp ON p.degree_program_id = dp.degree_program_id WHERE (SELECT COUNT(*) FROM Student_Enrolment se WHERE se.degree_program_id = p.degree_program_id) != COALESCE(p.student_count, 0)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL: degree_program_id and degree_summary_name must be non-NULL for every row.",
        "sql": "SELECT COUNT(*) FROM program_student_counts WHERE degree_program_id IS NULL OR degree_summary_name IS NULL",
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
SELECT dp.degree_program_id, dp.degree_summary_name, COUNT(se.student_enrolment_id) AS student_count FROM Degree_Programs dp LEFT JOIN Student_Enrolment se ON se.degree_program_id = dp.degree_program_id GROUP BY dp.degree_program_id, dp.degree_summary_name
```

---

## Skill `degree_programs_with_enrolment_counts`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `degree_program_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_765235c914892c35 |
| output columns | `degree_program_id`, `degree_summary_name`, `degree_summary_description`, `department_id`, `other_details`, `students_enrolled` |
| source tables | `Degree_Programs`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-degree program counts of enrolled students by joining degree programs to student enrollment and aggregating enrollment count per degree program.

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
      "Degree_Programs",
      "Student_Enrolment"
    ],
    "source_columns": [
      "Degree_Programs.degree_program_id",
      "Degree_Programs.degree_summary_name",
      "Degree_Programs.degree_summary_description",
      "Degree_Programs.department_id",
      "Degree_Programs.other_details",
      "se.students_enrolled",
      "se.degree_program_id",
      "Student_Enrolment.degree_program_id"
    ],
    "output_lineage": {
      "degree_program_id": [
        "Degree_Programs.degree_program_id"
      ],
      "degree_summary_name": [
        "Degree_Programs.degree_summary_name"
      ],
      "degree_summary_description": [
        "Degree_Programs.degree_summary_description"
      ],
      "department_id": [
        "Degree_Programs.department_id"
      ],
      "other_details": [
        "Degree_Programs.other_details"
      ],
      "students_enrolled": [
        "se.students_enrolled"
      ]
    },
    "operators": [
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "degree_programs": "85466a54c4a97bc7",
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {
      "degree_programs": "15:15",
      "student_enrolment": "15:15"
    },
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_540",
    "question": "What is the program id and the summary of the degree that has the most students enrolled?",
    "rewrite": "Task: Find the degree record that has the largest number of students enrolled and return that degree's program id and its summary.\nRequired outputs: program id of the degree with the highest students enrolled; summary text of that same degree\nFilters: consider only rows representing degrees; among those, choose the row(s) whose students enrolled value is maximal (i.e., equal to the greatest numeric students enrolled in the degrees table)\nSort/limit: order by students enrolled descending limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:34:31+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:34:34+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "degree_program_id",
      "degree_summary_name",
      "degree_summary_description",
      "department_id",
      "other_details",
      "students_enrolled"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Degree_Programs.degree_program_id=se.degree_program_id",
        "left_unique": true,
        "right_unique": null,
        "relationship": "unknown"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate degree_program_id in the view (view should be keyed by degree_program_id).",
        "sql": "SELECT COUNT(*) FROM (SELECT degree_program_id, COUNT(*) AS cnt FROM degree_programs_with_enrolment_counts GROUP BY degree_program_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "students_enrolled matches the count of Student_Enrolment rows per degree_program_id (including zero when none).",
        "sql": "SELECT COUNT(*) FROM (SELECT dp.degree_program_id, dp.students_enrolled, COALESCE(se.cnt,0) AS expected FROM degree_programs_with_enrolment_counts dp LEFT JOIN (SELECT degree_program_id, COUNT(*) AS cnt FROM Student_Enrolment GROUP BY degree_program_id) se ON dp.degree_program_id = se.degree_program_id WHERE dp.students_enrolled != COALESCE(se.cnt,0))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every degree_program_id in the view exists in the base Degree_Programs table (join did not introduce phantom keys).",
        "sql": "SELECT COUNT(*) FROM degree_programs_with_enrolment_counts v LEFT JOIN Degree_Programs dp USING (degree_program_id) WHERE dp.degree_program_id IS NULL",
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
SELECT dp.degree_program_id, dp.degree_summary_name, dp.degree_summary_description, dp.department_id, dp.other_details, COALESCE(se.students_enrolled, 0) AS students_enrolled
FROM Degree_Programs dp
LEFT JOIN (
  SELECT degree_program_id, COUNT(*) AS students_enrolled
  FROM Student_Enrolment
  GROUP BY degree_program_id
) se ON dp.degree_program_id = se.degree_program_id
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

Per-student counts of enrollment records (number of enrollments per student), including student identifier for joining to student details.

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
    "rewrite": "Task: Find the student or students who have the highest count of enrollments across any program (i.e., the maximum number of times a student appears as enrolled), and return identifying name fields and counts for those student(s).\nRequired outputs: id; first name; middle name; last name; the number of enrollments; student id\nFilters: Consider all enrollment records in the database; group enrollments by student and count the number of enrollments per student; select only the student(s) whose enrollment count equals the maximum count observed across all students.\nSort/limit: order results by student id ascending (or leave unspecified) and return all students tied for the maximum (no numeric limit)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:34:53+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:34:56+00:00",
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
        "purpose": "View has one row per student_id (no duplicate student_id keys)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id, COUNT(*) AS cnt FROM student_enrollment_counts GROUP BY student_id HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "enrollment_count matches COUNT(*) of Student_Enrolment per student_id",
        "sql": "SELECT COUNT(*) FROM (SELECT v.student_id FROM student_enrollment_counts v LEFT JOIN (SELECT student_id, COUNT(*) AS expected_count FROM Student_Enrolment GROUP BY student_id) b ON v.student_id = b.student_id WHERE (b.expected_count IS NULL AND v.enrollment_count != 0) OR (b.expected_count IS NOT NULL AND v.enrollment_count != b.expected_count))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every student_id in the view is NOT NULL and exists in base Student_Enrolment (no NULL keys, no phantom keys)",
        "sql": "SELECT COUNT(*) FROM student_enrollment_counts v WHERE v.student_id IS NULL OR NOT EXISTS (SELECT 1 FROM Student_Enrolment s WHERE s.student_id = v.student_id)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 20
  }
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

## Skill `student_enrollment_counts_13`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `student_id`, `first_name`, `middle_name`, `last_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_f3f36815e0f3a9de |
| output columns | `student_id`, `first_name`, `middle_name`, `last_name`, `enrollment_count` |
| source tables | `Students`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-student counts of enrollment records (number of enrollments) alongside student identifying fields for reuse in joins and ranking queries.

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
      "Students",
      "Student_Enrolment"
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
      "students": "ad3aee5be9cacc55",
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_542",
    "question": "What is the first, middle, and last name, along with the id and number of enrollments, for the student who enrolled the most in any program?",
    "rewrite": "Task: Find the student who has the highest number of enrollments in any program and return that student's first name, middle name, last name, id, and the student's number of enrollments.\nRequired outputs: first name; middle name; last name; id; number of enrollments\nFilters: Consider each student's total number of enrollments across programs (count of enrollment records linked to the student).; Select the student whose total number of enrollments is maximal (if multiple students tie for the maximum, return all such students).\nSort/limit: Order not required; limit to rows where the student's number of enrollments equals the maximum (no numeric limit unless tie handling causes multiple rows).",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:35:14+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:35:17+00:00",
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
        "join": "Student_Enrolment.student_id=Students.student_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (student_id, first_name, middle_name, last_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id, first_name, middle_name, last_name, COUNT(*) AS cnt FROM student_enrollment_counts_13 GROUP BY student_id, first_name, middle_name, last_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each enrollment_count equals the number of Student_Enrolment rows for that student (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM student_enrollment_counts_13 v LEFT JOIN (SELECT student_id, COUNT(*) AS expected_count FROM Student_Enrolment GROUP BY student_id) b ON v.student_id = b.student_id WHERE (b.expected_count IS NULL AND v.enrollment_count != 0) OR (b.expected_count IS NOT NULL AND v.enrollment_count != b.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys used in the grain are not NULL",
        "sql": "SELECT COUNT(*) FROM student_enrollment_counts_13 WHERE student_id IS NULL OR first_name IS NULL OR last_name IS NULL",
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
SELECT s.student_id, s.first_name, s.middle_name, s.last_name, COUNT(se.student_enrolment_id) AS enrollment_count FROM Students s JOIN Student_Enrolment se ON se.student_id = s.student_id GROUP BY s.student_id, s.first_name, s.middle_name, s.last_name
```

---

## Skill `semesters_with_no_enrolments`

Category: `SET`

| field | value |
|---|---|
| grain (one row per) | `semester_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_220ec9671e66b749 |
| output columns | `semester_id`, `semester_name` |
| source tables | `Semesters`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

All semesters that have no student enrolment records (semesters with zero linked enrollments).

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
      "Semesters",
      "Student_Enrolment"
    ],
    "source_columns": [
      "Semesters.semester_id",
      "Semesters.semester_name",
      "Student_Enrolment.semester_id",
      "Student_Enrolment.student_enrolment_id"
    ],
    "output_lineage": {
      "semester_id": [
        "Semesters.semester_id"
      ],
      "semester_name": [
        "Semesters.semester_name"
      ]
    },
    "operators": [
      "filter",
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
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
    "rewrite": "Task: Return the names of semesters that have no students enrolled in them.\nRequired outputs: semester name\nFilters: Include only semesters for which there exists zero enrollment records linking any student to that semester (i.e., no student is enrolled in that semester).; Do not include semesters that have one or more students enrolled.",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:35:34+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:35:36+00:00",
    "contract_version": 3,
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
        "join": "Student_Enrolment.semester_id=Semesters.semester_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate semester_id in the view (grain is semester_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT semester_id, COUNT(*) AS cnt FROM semesters_with_no_enrolments GROUP BY semester_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view must correspond to a Semesters row that truly has zero linked Student_Enrolment rows",
        "sql": "SELECT COUNT(*) FROM semesters_with_no_enrolments v WHERE EXISTS (SELECT 1 FROM Student_Enrolment se WHERE se.semester_id = v.semester_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All semester_id values in the view are non-NULL and exist in Semesters",
        "sql": "SELECT COUNT(*) FROM semesters_with_no_enrolments v WHERE v.semester_id IS NULL OR NOT EXISTS (SELECT 1 FROM Semesters s WHERE s.semester_id = v.semester_id)",
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
LEFT JOIN Student_Enrolment se ON se.semester_id = s.semester_id
WHERE se.student_enrolment_id IS NULL
```

---

## Skill `semesters_with_enrolment_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `semester_id`, `semester_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_cf302fb5bc409cf5 |
| output columns | `semester_id`, `semester_name`, `enrolment_count` |
| source tables | `Semesters`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-semester counts of student enrolment records (zero indicates no students enrolled), preserving keys to join back to semesters.

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
    "rewrite": "Task: Return the name(s) of the semester(s) that have no students enrolled.\nRequired outputs: semester name (a string)\nFilters: Include only semesters for which there are zero enrollments linking any student to that semester (i.e., no student enrollment records for that semester).; Consider all semesters present in the semesters table regardless of year or term.",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:35:52+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:35:56+00:00",
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
        "join": "Student_Enrolment.semester_id=Semesters.semester_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (semester_id, semester_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT semester_id, semester_name, COUNT(*) AS cnt FROM semesters_with_enrolment_counts GROUP BY semester_id, semester_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each row preserves a valid semester key that exists in Semesters (no orphan semesters) and semester_name matches Semesters table",
        "sql": "SELECT COUNT(*) FROM semesters_with_enrolment_counts v LEFT JOIN Semesters s ON v.semester_id = s.semester_id WHERE s.semester_id IS NULL OR (v.semester_name IS NOT NULL AND v.semester_name != s.semester_name)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "enrolment_count equals count of Student_Enrolment rows for that semester (reconciles aggregate with base table, allowing zero)",
        "sql": "SELECT COUNT(*) FROM semesters_with_enrolment_counts v LEFT JOIN (SELECT semester_id, COUNT(student_enrolment_id) AS expected_count FROM Student_Enrolment GROUP BY semester_id) se ON v.semester_id = se.semester_id WHERE COALESCE(se.expected_count, 0) != v.enrolment_count",
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
SELECT s.semester_id, s.semester_name, COUNT(se.student_enrolment_id) AS enrolment_count
FROM Semesters s
LEFT JOIN Student_Enrolment se ON se.semester_id = s.semester_id
GROUP BY s.semester_id, s.semester_name
```

---

## Skill `courses_with_enrollments`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `course_id`, `course_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_cc4a9a4ef3c6890d |
| output columns | `course_id`, `course_name` |
| source tables | `Courses`, `Student_Enrolment_Courses`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

A list of courses that have at least one associated student enrollment record (one row per course with its id and name).

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
      "Student_Enrolment_Courses",
      "Student_Enrolment"
    ],
    "source_columns": [
      "Courses.course_id",
      "Courses.course_name",
      "Student_Enrolment_Courses.course_id",
      "Student_Enrolment.student_enrolment_id",
      "Student_Enrolment_Courses.student_enrolment_id",
      "Student_Enrolment_Courses.student_course_id"
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
      "student_enrolment_courses": "daf1efe3c261d034",
      "student_enrolment": "445257138d420d03"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_546",
    "question": "What are the names of all courses that have some students enrolled?",
    "rewrite": "Task: Return the names of every course that currently has at least one student enrolled.\nRequired outputs: course_name\nFilters: Include only courses for which there exists at least one enrollment record linking a student to that course (i.e., courses with one or more enrolled students). Exclude courses with zero enrollments.",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:36:23+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:36:25+00:00",
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
        "purpose": "No duplicate rows at the declared grain (course_id, course_name)",
        "sql": "SELECT COUNT(*) FROM (SELECT course_id, course_name, COUNT(*) AS cnt FROM courses_with_enrollments GROUP BY course_id, course_name HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view corresponds to an existing Courses row (course_id not missing from Courses)",
        "sql": "SELECT COUNT(*) FROM courses_with_enrollments v LEFT JOIN Courses c ON v.course_id = c.course_id WHERE c.course_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View only includes courses that actually have at least one linked Student_Enrolment (via Student_Enrolment_Courses -> Student_Enrolment)",
        "sql": "SELECT COUNT(*) FROM courses_with_enrollments v LEFT JOIN Student_Enrolment_Courses sec ON v.course_id = sec.course_id LEFT JOIN Student_Enrolment se ON sec.student_enrolment_id = se.student_enrolment_id WHERE se.student_enrolment_id IS NULL",
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
JOIN Student_Enrolment se ON se.student_enrolment_id = sec.student_enrolment_id
GROUP BY c.course_id, c.course_name
HAVING COUNT(sec.student_course_id) > 0
```

---

## Skill `course_enrollment_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `course_id`, `course_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_89efd945e5e385ee |
| output columns | `course_id`, `course_name`, `enrollment_count` |
| source tables | `Student_Enrolment_Courses`, `Courses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-course enrollment counts derived by counting rows in the student-course enrollment association, producing one row per course with its id, name, and enrollment_count — useful as a general metric for ranking or joining to course metadata.

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
      "Courses"
    ],
    "source_columns": [
      "Courses.course_id",
      "Courses.course_name",
      "Student_Enrolment_Courses.student_course_id",
      "Student_Enrolment_Courses.course_id"
    ],
    "output_lineage": {
      "course_id": [
        "Courses.course_id"
      ],
      "course_name": [
        "Courses.course_name"
      ],
      "enrollment_count": [
        "Student_Enrolment_Courses.student_course_id"
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
      "courses": "53e9befe1413d87f"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_547",
    "question": "What's the name of the course with most number of enrollments?",
    "rewrite": "Task: Find the course name that has the largest number of enrollments (i.e., the course with the highest enrollment count).\nRequired outputs: course name (the name/title of the course); enrollment count for that course\nFilters: consider all courses and their enrollments across the entire dataset (no additional filtering)\nSort/limit: order by enrollment count descending, limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:36:39+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:36:42+00:00",
    "contract_version": 3,
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
        "join": "Student_Enrolment_Courses.course_id=Courses.course_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (course_id, course_name)",
        "sql": "SELECT COUNT(*) FROM course_enrollment_counts v JOIN (SELECT course_id, course_name, COUNT(*) AS cnt FROM course_enrollment_counts GROUP BY course_id, course_name HAVING COUNT(*) > 1) dup USING (course_id, course_name)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "enrollment_count matches count of Student_Enrolment_Courses rows per course",
        "sql": "SELECT COUNT(*) FROM course_enrollment_counts v LEFT JOIN (SELECT course_id, COUNT(*) AS expected_count FROM Student_Enrolment_Courses GROUP BY course_id) bc ON v.course_id = bc.course_id WHERE (bc.expected_count IS NULL AND v.enrollment_count != 0) OR (bc.expected_count IS NOT NULL AND v.enrollment_count != bc.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys course_id and course_name are not NULL",
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
SELECT c.course_id, c.course_name, COUNT(sec.student_course_id) AS enrollment_count FROM Student_Enrolment_Courses AS sec JOIN Courses AS c ON sec.course_id = c.course_id GROUP BY c.course_id, c.course_name
```

---

## Skill `transcript_course_results_count`

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

Per-transcript count of associated course result / student_course entries to identify transcripts by how many course results they include

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
    "rewrite": "Task: Return rows giving the date and id of each transcript that has at least 2 associated course results.\nRequired outputs: transcript.date (the date of the transcript); transcript.id (the identifier of the transcript)\nFilters: Only include transcripts for which the count of related course results is >= 2 (i.e., there are two or more course result records associated with that transcript)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:38:13+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:38:15+00:00",
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
        "purpose": "No duplicate rows at the declared grain (transcript_id, transcript_date). Checks that the view does not contain multiple rows with same transcript_id and transcript_date.",
        "sql": "SELECT COUNT(*) FROM (SELECT transcript_id, transcript_date, COUNT(*) AS cnt FROM transcript_course_results_count GROUP BY transcript_id, transcript_date HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's course_result_count equals the count of Transcript_Contents rows for that transcript (measure reconciles with base tables).",
        "sql": "SELECT COUNT(*) FROM transcript_course_results_count v LEFT JOIN Transcripts t ON v.transcript_id = t.transcript_id WHERE (SELECT COUNT(*) FROM Transcript_Contents tc WHERE tc.transcript_id = v.transcript_id) IS NOT v.course_result_count",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL: transcript_id and transcript_date must be present for every row in the view.",
        "sql": "SELECT COUNT(*) FROM transcript_course_results_count WHERE transcript_id IS NULL OR transcript_date IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 18
  }
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

## Skill `transcript_course_counts_min2_per_transcript_date`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `id`, `date` (keyed) |
| status / version | active / v1 |
| skill id | sk_d34c0ce75a52378e |
| output columns | `id`, `date`, `number_of_courses` |
| source tables | `Transcripts`, `Transcript_Contents` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Each row represents a transcript (id) on a specific transcript_date with the count of student_course rows linked to that transcript, but only includes transcripts that have at least two linked courses.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{
  "description": "Each row represents a transcript (id) on a specific transcript_date with the count of student_course rows linked to that transcript, but only includes transcripts that have at least two linked courses.",
  "when_to_use": "To get, per transcript and transcript_date, how many student_course entries are associated with that transcript. | As a pre-aggregated source when you need transcripts that are linked to two or more course enrollments. | When joining to other data at the transcript-level keyed by transcript_id and transcript_date.",
  "when_not_to_use": "When you need transcripts that have zero or one course (they are excluded by the HAVING COUNT(...) >= 2 filter). | When you need counts of distinct courses or different course-level granularity — the view counts rows in Transcript_Contents (student_course_id) and does not deduplicate duplicate student_course_id values or count distinct course identifiers. | When you need a different time window or derived date grain — the view uses transcript_date as provided (exact datetime) and groups at that exact date value, so it may split what should be a single period-level record (e.g., grouping by date_trunc(day/month) is not applied). | When you need other transcript attributes not present (only transcript_id, transcript_date, number_of_courses are available). | When a different join path or additional filters are required — the view always joins Transcripts -> Transcript_Contents and applies no extra filters besides the HAVING; it does not reflect other relationships (e.g., to students or courses) that might change the intended cohort or counts."
}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "av_chunk",
    "subgoal": {
      "want_name": "chunk_view_1",
      "category": "SEL",
      "required_outputs": [],
      "required_grain": [],
      "required_filters": {},
      "text": "Task: Return the transcript records that have at least 2 courses listed, and for each such transcript provide its date and id.\nRequired outputs: date; id\nFilters: transcript must have number_of_courses >= 2 (i.e., at least 2 courses listed)",
      "source_tables": [
        "Student_Enrolment",
        "Student_Enrolment_Courses",
        "Transcript_Contents",
        "Transcripts"
      ],
      "depends_on": [],
      "join_keys": [],
      "relationship": "",
      "may_read_base_tables": true,
      "holistic": true,
      "inherited_filters": {}
    },
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
      "id": [
        "Transcripts.transcript_id"
      ],
      "date": [
        "Transcripts.transcript_date"
      ],
      "number_of_courses": [
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
    "question_id": "spider_dev_552",
    "question": "What is the date and id of the transcript with at least 2 courses listed?",
    "rewrite": "Task: Return the transcript records that have at least 2 courses listed, and for each such transcript provide its date and id.\nRequired outputs: date; id\nFilters: transcript must have number_of_courses >= 2 (i.e., at least 2 courses listed)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:38:26+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:38:30+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "id",
      "date",
      "number_of_courses"
    ],
    "row_count": 4,
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
        "purpose": "No duplicate rows at the view grain (id, date) — ensure view does not contain multiple rows with same id and date",
        "sql": "SELECT COUNT(*) FROM (SELECT id, date, COUNT(*) AS cnt FROM chunk_view_1 GROUP BY id, date HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every output row satisfies the intrinsic filter: number_of_courses >= 2",
        "sql": "SELECT COUNT(*) FROM chunk_view_1 WHERE number_of_courses < 2 OR number_of_courses IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Recomputed measure number_of_courses matches the view's number_of_courses (aggregated from base tables)",
        "sql": "SELECT COUNT(*) FROM (SELECT v.id, v.date, v.number_of_courses, coalesced.cnt AS recomputed_cnt FROM chunk_view_1 v LEFT JOIN (SELECT t.transcript_id AS id, t.transcript_date AS date, COUNT(tc.student_course_id) AS cnt FROM Transcripts t JOIN Transcript_Contents tc ON t.transcript_id = tc.transcript_id GROUP BY t.transcript_id, t.transcript_date HAVING COUNT(tc.student_course_id) >= 2) coalesced ON v.id = coalesced.id AND v.date = coalesced.date WHERE v.number_of_courses != coalesced.cnt OR coalesced.cnt IS NULL)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 25
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
  t.transcript_id AS id,
  t.transcript_date AS date,
  COUNT(tc.student_course_id) AS number_of_courses
FROM Transcripts t
JOIN Transcript_Contents tc
  ON t.transcript_id = tc.transcript_id
GROUP BY
  t.transcript_id,
  t.transcript_date
HAVING COUNT(tc.student_course_id) >= 2
```

---

## Skill `transcript_course_counts_per_transcript_date`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `transcript_id`, `transcript_date` (keyed) |
| status / version | active / v1 |
| skill id | sk_f11d0ab8695788eb |
| output columns | `transcript_id`, `transcript_date`, `number_of_courses` |
| source tables | `Transcripts`, `Transcript_Contents` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-transcript per-date counts of transcript-linked student_course rows (one row per transcript id and transcript_date with the number of associated courses).

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
      "number_of_courses": [
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
    "question_id": "spider_dev_552",
    "question": "What is the date and id of the transcript with at least 2 courses listed?",
    "rewrite": "Task: Return the transcript records that have at least 2 courses listed, and for each such transcript provide its date and id.\nRequired outputs: date; id\nFilters: transcript must have number_of_courses >= 2 (i.e., at least 2 courses listed)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:38:34+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:38:37+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "transcript_id",
      "transcript_date",
      "number_of_courses"
    ],
    "row_count": 10,
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
        "sql": "SELECT COUNT(*) FROM (SELECT transcript_id, transcript_date, COUNT(*) AS cnt FROM transcript_course_counts_per_transcript_date GROUP BY transcript_id, transcript_date HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "number_of_courses matches count of Transcript_Contents.student_course_id linked to each transcript",
        "sql": "SELECT COUNT(*) FROM transcript_course_counts_per_transcript_date v LEFT JOIN Transcripts t ON v.transcript_id = t.transcript_id LEFT JOIN (SELECT transcript_id, COUNT(student_course_id) AS expected_count FROM Transcript_Contents GROUP BY transcript_id) tc ON v.transcript_id = tc.transcript_id WHERE (tc.expected_count IS NULL AND v.number_of_courses != 0) OR (tc.expected_count IS NOT NULL AND v.number_of_courses != tc.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL (transcript_id or transcript_date should not be NULL)",
        "sql": "SELECT COUNT(*) FROM transcript_course_counts_per_transcript_date WHERE transcript_id IS NULL OR transcript_date IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 34
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT t.transcript_id AS transcript_id, t.transcript_date AS transcript_date, COUNT(tc.student_course_id) AS number_of_courses FROM Transcripts AS t JOIN Transcript_Contents AS tc ON t.transcript_id = tc.transcript_id GROUP BY t.transcript_id, t.transcript_date
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

All students whose permanent address differs from their current address, including keys and first name for reuse in joins or filters

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
    "question_id": "spider_dev_560",
    "question": "What is the first name of the student whose permanent address is different from his or her current one?",
    "rewrite": "Task: Find the first name of the student whose permanent address differs from their current address.\nRequired outputs: first name (string) of the student\nFilters: rows where the student's permanent address is not equal to the student's current address (permanent_address <> current_address)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:40:28+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:40:31+00:00",
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
        "purpose": "No duplicate student rows: ensure view has at most one row per student_id (grain uniqueness).",
        "sql": "SELECT COUNT(*) FROM (SELECT student_id, COUNT(*) AS cnt FROM students_with_different_permanent_and_current_address GROUP BY student_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's permanent and current address IDs are non-NULL and different (matches intrinsic WHERE clause).",
        "sql": "SELECT COUNT(*) FROM students_with_different_permanent_and_current_address WHERE permanent_address_id IS NULL OR current_address_id IS NULL OR permanent_address_id = current_address_id",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View rows correspond exactly to Students with differing addresses (no missing or extra rows): every view row must exist in Students and satisfy the condition, and every Students row that satisfies the",
        "sql": "SELECT ( (SELECT COUNT(*) FROM students_with_different_permanent_and_current_address EXCEPT SELECT student_id, first_name, permanent_address_id, current_address_id FROM Students WHERE permanent_address_id IS NOT NULL AND current_address_id IS NOT NULL AND permanent_address_id <> current_address_id) UNION ALL (SELECT COUNT(*) FROM (SELECT student_id, first_name, permanent_address_id, current_address_id FROM Students WHERE permanent_address_id IS NOT NULL AND current_address_id IS NOT NULL AND permanent_address_id <> current_address_id EXCEPT SELECT student_id, first_name, permanent_address_id, current_address_id FROM students_with_different_permanent_and_current_address)) ) AS mismatch_count LIMIT 1",
        "result": "inconclusive",
        "violations": null,
        "error": "OperationalError: near \"UNION\": syntax error"
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 22
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT student_id, first_name, permanent_address_id, current_address_id FROM Students WHERE permanent_address_id IS NOT NULL AND current_address_id IS NOT NULL AND permanent_address_id <> current_address_id
```

---

## Skill `students_per_current_address`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `address_id`, `line_1`, `line_2`, `line_3`, `city`, `zip_postcode`, `state_province_county`, `country` (keyed) |
| status / version | active / v1 |
| skill id | sk_f5ade95f529be3be |
| output columns | `address_id`, `line_1`, `line_2`, `line_3`, `city`, `zip_postcode`, `state_province_county`, `country`, `student_count` |
| source tables | `Addresses`, `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Counts how many currently-associated students live at each address (one row per address_id with student count and address fields).

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
    "rewrite": "Task: Find the address (address id and all address lines) that currently has the largest number of students living there.\nRequired outputs: address id; all lines for that address (e.g., line1, line2, line3 or however address lines are represented); the number of students at that address (to determine the maximum)\nFilters: Only consider students who are currently associated with an address (i.e., existing/current student-to-address records); exclude null/missing address assignments.; Count students per address using current student records; include all students regardless of other attributes (no additional demographic filters).\nSort/limit: Order addresses by descending student count and return the top 1 address (if multiple addresses tie for the maximum count, return all such addresses).",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:40:44+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:40:47+00:00",
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
        "purpose": "Each row in the view should be unique at the declared grain (no duplicate address key rows).",
        "sql": "SELECT COUNT(*) FROM (SELECT address_id, line_1, line_2, line_3, city, zip_postcode, state_province_county, country, COUNT(*) as cnt FROM students_per_current_address GROUP BY address_id, line_1, line_2, line_3, city, zip_postcode, state_province_county, country HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count must equal the number of Students whose current_address_id = that address_id (measure reconciliation).",
        "sql": "SELECT COUNT(*) FROM students_per_current_address v LEFT JOIN (SELECT current_address_id AS address_id, COUNT(student_id) AS expected_count FROM Students WHERE current_address_id IS NOT NULL GROUP BY current_address_id) s ON v.address_id = s.address_id WHERE COALESCE(s.expected_count,0) != COALESCE(v.student_count,0)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "address_id (the key) must not be NULL in any row of the view.",
        "sql": "SELECT COUNT(*) FROM students_per_current_address WHERE address_id IS NULL",
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
    "negative": 1,
    "negative_subgoals": [
      "Task: Return the distinct addresses that have one or more students living at them.\nRequired outputs: address (the address value for a location where at least one student lives)\nFilters: Include only addresses that are referenced by at least one student record (i.e., addresses with student_count >= 1).; Do not include addresses that have no students living there."
    ],
    "last_used": "spider_dev_578"
  }
}
```

### Validated on (0)

—

### Counter-examples (1)

- What are the different addresses that have students living there?

### Executable SQL body

```sql
SELECT A.address_id, A.line_1, A.line_2, A.line_3, A.city, A.zip_postcode, A.state_province_county, A.country, COUNT(S.student_id) AS student_count FROM Addresses A JOIN Students S ON S.current_address_id = A.address_id WHERE S.current_address_id IS NOT NULL GROUP BY A.address_id, A.line_1, A.line_2, A.line_3, A.city, A.zip_postcode, A.state_province_county, A.country
```

---

## Skill `address_student_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `address_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_af5c6f4ebc0192e1 |
| output columns | `address_id`, `line_1`, `line_2`, `student_count` |
| source tables | `Addresses`, `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-address counts of distinct students associated via current or permanent address

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
      "Addresses",
      "Students"
    ],
    "source_columns": [
      "Addresses.address_id",
      "Addresses.line_1",
      "Addresses.line_2",
      "agg.student_count",
      "agg.addr_id",
      "addr_id",
      "student_id",
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
      "student_count": [
        "agg.student_count"
      ]
    },
    "operators": [
      "filter",
      "join",
      "project"
    ],
    "upstream_skills": [],
    "parameter_bindings": {},
    "table_fingerprints": {
      "addresses": "be6ad43bf746a2b6",
      "students": "ad3aee5be9cacc55"
    },
    "data_fingerprints": {
      "addresses": "15:15",
      "students": "15:15"
    },
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_562",
    "question": "What is the id, line 1, and line 2 of the address with the most students?",
    "rewrite": "Task: Find the address that has the greatest number of students and return that address's id, line 1, and line 2.\nRequired outputs: id; line 1; line 2\nFilters: address must be the one associated with the maximum count of students (i.e., group students by their address and select the address with the highest student count)\nSort/limit: order by student count desc limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:41:06+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:41:09+00:00",
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
        "join": "agg.addr_id=Addresses.address_id",
        "left_unique": null,
        "right_unique": true,
        "relationship": "unknown"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate address_id rows in the view (grain uniqueness)",
        "sql": "SELECT COUNT(*) FROM (SELECT address_id, COUNT(*) AS cnt FROM address_student_counts GROUP BY address_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "student_count matches recomputed distinct student count from Students for that address (including current and permanent)",
        "sql": "SELECT COUNT(*) FROM address_student_counts v LEFT JOIN (SELECT addr_id AS address_id, COUNT(DISTINCT student_id) AS expected_count FROM (SELECT student_id, current_address_id AS addr_id FROM Students WHERE current_address_id IS NOT NULL UNION ALL SELECT student_id, permanent_address_id AS addr_id FROM Students WHERE permanent_address_id IS NOT NULL) s GROUP BY addr_id) r ON v.address_id = r.address_id WHERE (r.expected_count IS NULL AND v.student_count IS NOT NULL) OR (r.expected_count IS NOT NULL AND v.student_count IS NULL) OR (r.expected_count IS NOT NULL AND v.student_count != r.expected_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every address_id in the view exists in Addresses and is not NULL (no missing or NULL keys)",
        "sql": "SELECT COUNT(*) FROM address_student_counts v LEFT JOIN Addresses a ON v.address_id = a.address_id WHERE v.address_id IS NULL OR a.address_id IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 29
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT a.address_id AS address_id, a.line_1 AS line_1, a.line_2 AS line_2, agg.student_count AS student_count FROM Addresses a JOIN ( SELECT addr_id, COUNT(DISTINCT student_id) AS student_count FROM ( SELECT student_id, current_address_id AS addr_id FROM Students WHERE current_address_id IS NOT NULL UNION ALL SELECT student_id, permanent_address_id AS addr_id FROM Students WHERE permanent_address_id IS NOT NULL ) s GROUP BY addr_id ) agg ON agg.addr_id = a.address_id
```

---

## Skill `transcripts_with_release_dates`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `transcript_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_1637247f3bff5d45 |
| output columns | `transcript_id`, `release_date`, `details` |
| source tables | `Transcripts` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

A relation of transcripts that have non-null release dates with keys and detail fields for joining or filtering in other queries

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
      "Transcripts.transcript_date",
      "Transcripts.other_details"
    ],
    "output_lineage": {
      "transcript_id": [
        "Transcripts.transcript_id"
      ],
      "release_date": [
        "Transcripts.transcript_date"
      ],
      "details": [
        "Transcripts.other_details"
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
    "question_id": "spider_dev_565",
    "question": "When is the first transcript released? List the date and details.",
    "rewrite": "Task: Find the earliest (first) transcript release and return its release date and the associated details for that transcript.\nRequired outputs: release_date: the date the transcript was released (date/time or date); details: text or structured fields describing the transcript details (e.g., title, description, speaker(s), or other detail fields as they exist)\nFilters: Only consider rows that represent transcripts (i.e., items identified as transcripts); Include only transcripts that have a non-null release date; If multiple transcripts share the same earliest release date, include all of them\nSort/limit: order by release_date ascending; limit none (return all rows that tie for the earliest date)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:42:08+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:42:11+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "transcript_id",
      "release_date",
      "details"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate transcript_id in the view (grain uniqueness)",
        "sql": "SELECT COUNT(*) FROM (SELECT transcript_id, COUNT(*) AS cnt FROM transcripts_with_release_dates GROUP BY transcript_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows in the view have non-NULL release_date (intrinsic filter respected)",
        "sql": "SELECT COUNT(*) FROM transcripts_with_release_dates WHERE release_date IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each view row matches the base table: release_date and details equal the corresponding Transcripts values for that transcript_id (reconciliation with base table)",
        "sql": "SELECT COUNT(*) FROM transcripts_with_release_dates v LEFT JOIN Transcripts t ON v.transcript_id = t.transcript_id WHERE t.transcript_id IS NULL OR v.release_date != t.transcript_date OR (v.details IS NOT t.other_details AND (v.details IS NULL OR t.other_details IS NULL OR v.details <> t.other_details))",
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
SELECT transcript_id, transcript_date AS release_date, other_details AS details FROM Transcripts WHERE transcript_date IS NOT NULL
```

---

## Skill `transcript_release_earliest_records`

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

All transcript records whose transcript_date equals the minimum non-null transcript_date across the Transcripts table (earliest transcript release cohort).

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
      "Transcripts"
    ],
    "source_columns": [
      "Transcripts.transcript_date"
    ],
    "output_lineage": {
      "transcript_id": [],
      "transcript_date": [
        "Transcripts.transcript_date"
      ],
      "other_details": []
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
    "data_fingerprints": {
      "transcripts": "15:15"
    },
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_566",
    "question": "What is the earliest date of a transcript release, and what details can you tell me?",
    "rewrite": "Task: Find the earliest transcript release date and return that date plus all available details about the transcript release record(s) that have that earliest date.\nRequired outputs: transcript_release_date: the earliest date value present in the transcript release records; all_details: all other columns/fields from the transcript release record(s) that share that earliest transcript_release_date (for example: transcript_id or identifier, title, description, release_source, release_format, created_at/updated_at, and any other stored attributes)\nFilters: Include only rows where transcript_release_date IS NOT NULL; Select rows whose transcript_release_date equals the minimum transcript_release_date across all transcript release records (i.e., transcript_release_date = (SELECT MIN(transcript_release_date) FROM transcript_release_records))\nSort/limit: return all rows that match the earliest date (no additional ordering required), limit: none",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:42:22+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:42:24+00:00",
    "contract_version": 3,
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
        "purpose": "No row in the view has a transcript_date that is NULL (view filters require non-null transcript_date).",
        "sql": "SELECT COUNT(*) FROM transcript_release_earliest_records v WHERE v.transcript_date IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view has transcript_date equal to the minimum non-null transcript_date present in the base Transcripts table.",
        "sql": "SELECT COUNT(*) FROM transcript_release_earliest_records v WHERE v.transcript_date <> (SELECT MIN(transcript_date) FROM Transcripts WHERE transcript_date IS NOT NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "The view contains exactly one row per transcript_id (no duplicate transcript_id keys).",
        "sql": "SELECT COUNT(*) FROM (SELECT transcript_id, COUNT(*) AS cnt FROM transcript_release_earliest_records GROUP BY transcript_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 12
  }
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

All transcripts with their identifiers and release dates (only transcripts that have a non-null release date).

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
    "question_id": "spider_dev_570",
    "question": "When was the last transcript released?",
    "rewrite": "Task: Find the release date of the most recently released transcript.\nRequired outputs: transcript identifier or title (if available); release date of the transcript\nFilters: records must be transcripts; release date is not null\nSort/limit: order by release date descending, limit 1",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:43:20+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:43:22+00:00",
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
        "purpose": "No duplicate transcript_id in the view (ensures grain is transcript_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT transcript_id, COUNT(*) AS c FROM transcript_release_dates GROUP BY transcript_id HAVING c > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view corresponds to a base Transcripts row with the same transcript_id and matching transcript_date (ensures view didn't alter values)",
        "sql": "SELECT COUNT(*) FROM transcript_release_dates v LEFT JOIN Transcripts t ON v.transcript_id = t.transcript_id WHERE t.transcript_id IS NULL OR (t.transcript_date IS NOT v.transcript_date AND NOT (t.transcript_date IS NULL AND v.transcript_date IS NULL))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View only includes transcripts with non-NULL transcript_date (intrinsic filter)",
        "sql": "SELECT COUNT(*) FROM transcript_release_dates WHERE transcript_date IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 6
  }
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
| skill id | sk_db5446e1fcd68aa0 |
| output columns | `student_course_id`, `transcript_count` |
| source tables | `Student_Enrolment_Courses`, `Transcript_Contents` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each student course enrollment, the count of distinct transcripts in which that enrollment appears (zero if none).

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
      "transcript_count": [
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
    "rewrite": "Task: For each course enrollment id, compute the maximum number of distinct transcripts in which that course enrollment appears, and return the course enrollment id together with that maximum count.\nRequired outputs: course enrollment id; maximum number of transcripts that the course enrollment appears in (an integer)\nFilters: Consider each course enrollment id present in the data; Count distinct transcripts for each course enrollment id; Do not filter out any course enrollments unless they do not appear in any transcript (then their count is zero if such rows are represented)\nSort/limit: Order results by course enrollment id ascending (no limit)",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:43:48+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:43:51+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "student_course_id",
      "transcript_count"
    ],
    "row_count": 15,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "Transcript_Contents.student_course_id=Student_Enrolment_Courses.student_course_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows per grain: each student_course_id appears at most once in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT student_course_id, COUNT(*) AS cnt FROM student_course_transcript_counts GROUP BY student_course_id HAVING cnt <> 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "transcript_count matches count distinct transcripts in base tables for each student_course_id (including zero when no transcript rows)",
        "sql": "SELECT COUNT(*) FROM (SELECT v.student_course_id FROM student_course_transcript_counts v LEFT JOIN (SELECT sec.student_course_id AS scid, COUNT(DISTINCT tc.transcript_id) AS expected_count FROM Student_Enrolment_Courses sec LEFT JOIN Transcript_Contents tc ON tc.student_course_id = sec.student_course_id GROUP BY sec.student_course_id) b ON v.student_course_id = b.scid WHERE COALESCE(b.expected_count,0) <> v.transcript_count)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view references an existing Student_Enrolment_Courses.student_course_id (no phantom keys)",
        "sql": "SELECT COUNT(*) FROM student_course_transcript_counts v LEFT JOIN Student_Enrolment_Courses sec ON v.student_course_id = sec.student_course_id WHERE sec.student_course_id IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 35,
    "selected": 2,
    "included": 2,
    "referenced": 2,
    "executed": 2,
    "inconclusive": 2,
    "positive": 2,
    "positive_subgoals": [
      "Task: Find the course (by its enrollment id) that appears the greatest number of times across different transcripts, and report that maximum count together with the course's enrollment id.\nRequired outputs: enrollment id of the course (the identifier used to link a course enrollment to transcripts); the maximum number of distinct transcripts in which that course appears (an integer count)\nFilters: Consider all course entries across all transcripts in the database; Count each transcript only once per course (i.e., count distinct transcripts that contain the course); If a course appears multiple times within the same transcript, it should be counted only once for that transcript; Return the course (enrollment id) whose distinct-transcript count is maximal\nSort/limit: order by the distinct-transcript count in descending order and limit to 1 result",
      "Task: How many times at most can a course enrollment result show in different transcripts? Also show the course enrollment id."
    ],
    "last_used": "spider_dev_571"
  }
}
```

### Validated on (2)

- What is the maximum number of times that a course shows up in different transcripts and what is that course's enrollment id?
- How many times at most can a course enrollment result show in different transcripts? Also show the course enrollment id.

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT sec.student_course_id, COUNT(DISTINCT tc.transcript_id) AS transcript_count FROM Student_Enrolment_Courses sec LEFT JOIN Transcript_Contents tc ON tc.student_course_id = sec.student_course_id GROUP BY sec.student_course_id
```

---

## Skill `transcript_result_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `transcript_id`, `transcript_date` (keyed) |
| status / version | active / v1 |
| skill id | sk_8429dd0f5bf5a1ad |
| output columns | `transcript_id`, `transcript_date`, `result_count` |
| source tables | `Transcripts`, `Transcript_Contents` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-transcript counts of associated transcript content rows (number of results) with transcript id and date, including transcripts with zero results.

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
      "result_count": [
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
    "question_id": "spider_dev_573",
    "question": "Show the date of the transcript which shows the least number of results, also list the id.",
    "rewrite": "Task: Find the transcript date that has the smallest total number of results, and return that date along with the corresponding transcript id.\nRequired outputs: transcript date; transcript id\nFilters: Consider all transcripts (no additional filtering unless the schema implies status or deletion flags — include every transcript row).; Count the number of results associated with each transcript (group by transcript).; Select the transcript(s) whose associated results count is minimal across all transcripts.\nSort/limit: If multiple transcripts tie for the minimal results count, return all tied rows; otherwise return the single row with the minimal count. No additional ordering required.",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:44:31+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:44:33+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "transcript_id",
      "transcript_date",
      "result_count"
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
        "purpose": "No duplicate rows per declared grain (transcript_id, transcript_date)",
        "sql": "SELECT COUNT(*) FROM (SELECT transcript_id, transcript_date, COUNT(*) AS cnt FROM transcript_result_counts GROUP BY transcript_id, transcript_date HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's result_count equals COUNT of matching Transcript_Contents.student_course_id (recomputed from base tables)",
        "sql": "SELECT COUNT(*) FROM transcript_result_counts v LEFT JOIN Transcripts t ON t.transcript_id = v.transcript_id WHERE t.transcript_id IS NULL OR v.result_count != (SELECT COUNT(tc.student_course_id) FROM Transcript_Contents tc WHERE tc.transcript_id = v.transcript_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All key columns are NOT NULL (transcript_id, transcript_date) and each transcript in Transcripts appears once in the view (ensures inclusion of zero-result transcripts)",
        "sql": "SELECT COUNT(*) FROM Transcripts t LEFT JOIN transcript_result_counts v ON v.transcript_id = t.transcript_id AND ( (v.transcript_date = t.transcript_date) OR (v.transcript_date IS NULL AND t.transcript_date IS NULL) ) WHERE v.transcript_id IS NULL OR v.transcript_date IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "retrieved": 12
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT t.transcript_id, t.transcript_date, COUNT(tc.student_course_id) AS result_count FROM Transcripts t LEFT JOIN Transcript_Contents tc ON tc.transcript_id = t.transcript_id GROUP BY t.transcript_id, t.transcript_date
```

---

## Skill `semester_enrolment_degree_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `semester_id`, `degree_level` (keyed) |
| status / version | active / v1 |
| skill id | sk_796049368035bed1 |
| output columns | `semester_id`, `degree_level`, `enrolment_count` |
| source tables | `Student_Enrolment`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per semester counts of enrolled students broken down by degree level/type (e.g., Bachelor, Master) to identify semesters with enrollments across degree types.

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
    "contract_version": 3,
    "grain_basis": "group_by",
    "lineage": [
      "Student_Enrolment",
      "Degree_Programs"
    ],
    "source_columns": [
      "Student_Enrolment.semester_id",
      "Degree_Programs.degree_summary_name",
      "Student_Enrolment.degree_program_id",
      "Degree_Programs.degree_program_id",
      "Student_Enrolment.student_enrolment_id"
    ],
    "output_lineage": {
      "semester_id": [
        "Student_Enrolment.semester_id"
      ],
      "degree_level": [
        "Degree_Programs.degree_summary_name"
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
      "student_enrolment": "445257138d420d03",
      "degree_programs": "85466a54c4a97bc7"
    },
    "data_fingerprints": {},
    "db_id": "student_transcripts_tracking",
    "question_id": "spider_dev_575",
    "question": "Find the semester when both Master students and Bachelor students got enrolled in.",
    "rewrite": "Task: Return the semester(s) in which both Master students and Bachelor students were enrolled.\nRequired outputs: semester (the semester identifier/value)\nFilters: Include only semesters where there exists at least one enrolled student whose degree level/type is 'Master' AND at least one enrolled student whose degree level/type is 'Bachelor' in the same semester.",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T14:45:19+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-01T14:45:23+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "semester_id",
      "degree_level",
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
        "purpose": "No duplicate rows at the declared grain (semester_id, degree_level)",
        "sql": "SELECT COUNT(*) FROM (SELECT semester_id, degree_level, COUNT(*) AS cnt FROM semester_enrolment_degree_counts GROUP BY semester_id, degree_level HAVING cnt > 1) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "enrolment_count matches COUNT(DISTINCT student_enrolment_id) computed from base tables for each (semester_id, degree_level)",
        "sql": "SELECT COUNT(*) FROM (SELECT v.semester_id, v.degree_level FROM semester_enrolment_degree_counts v LEFT JOIN (SELECT se.semester_id, dp.degree_summary_name AS degree_level, COUNT(DISTINCT se.student_enrolment_id) AS expected_count FROM Student_Enrolment se JOIN Degree_Programs dp ON se.degree_program_id = dp.degree_program_id GROUP BY se.semester_id, dp.degree_summary_name) b ON v.semester_id = b.semester_id AND v.degree_level = b.degree_level WHERE (b.expected_count IS NULL AND (v.enrolment_count IS NOT NULL AND v.enrolment_count <> 0)) OR (b.expected_count IS NOT NULL AND v.enrolment_count <> b.expected_count)) AS mismatches",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL: semester_id and degree_level should never be NULL in the view",
        "sql": "SELECT COUNT(*) FROM semester_enrolment_degree_counts WHERE semester_id IS NULL OR degree_level IS NULL",
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
SELECT se.semester_id, dp.degree_summary_name AS degree_level, COUNT(DISTINCT se.student_enrolment_id) AS enrolment_count
FROM Student_Enrolment se
JOIN Degree_Programs dp ON se.degree_program_id = dp.degree_program_id
GROUP BY se.semester_id, dp.degree_summary_name
```

---

## Skill `department_degree_counts_29`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `department_id`, `department_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_1ebbab06074ebffe |
| output columns | `department_id`, `department_name`, `num_degrees` |
| source tables | `Departments`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Counts the number of degree programs associated with each department

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
      "specific department names/ids"
    ],
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
      "num_degrees": [
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
    "rewrite": "Task: What is the name and id of the department with the most number of degrees ?",
    "route": "nx1",
    "model": "qwen3:8b",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-02T14:51:40+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-02T14:51:40+00:00",
    "contract_version": 3,
    "failures": [],
    "executed": true,
    "columns": [
      "department_id",
      "department_name",
      "num_degrees"
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
    "passed": true
  },
  "evidence": {
    "retrieved": 22
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT d.department_id, d.department_name, COUNT(dp.degree_program_id) AS num_degrees FROM Departments d JOIN Degree_Programs dp ON d.department_id = dp.department_id GROUP BY d.department_id, d.department_name
```

---

## Skill `students_with_distinct_addresses`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `student_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_60df4f051b30ea25 |
| output columns | `student_id`, `first_name`, `current_address_id`, `permanent_address_id` |
| source tables | `Students` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

A list of students who have different current and permanent address IDs

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{
  "description": "A list of students who have different current and permanent address IDs",
  "when_to_use": "Identify students with mismatched address records | Validate address consistency across systems",
  "when_not_to_use": "When needing students with matching addresses (this view excludes them) | When requiring historical address data (view contains only current addresses) | When needing demographic data beyond basic student identifiers | When requiring joins with address details table (no join path provided)"
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
      "text": "Task: Find the first name of each student where the permanent address differs from the current address\nRequired outputs: first_name\nFilters: permanent_address != current_address",
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
    "contract_version": 3,
    "grain_basis": "primary_key",
    "lineage": [
      "Students"
    ],
    "source_columns": [
      "Students.student_id",
      "Students.first_name",
      "Students.current_address_id",
      "Students.permanent_address_id"
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
    "question_id": "spider_dev_560",
    "question": "What is the first name of the student whose permanent address is different from his or her current one?",
    "rewrite": "Task: Find the first name of each student where the permanent address differs from the current address\nRequired outputs: first_name\nFilters: permanent_address != current_address",
    "route": "nx1",
    "model": "qwen3:8b",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-02T15:47:34+00:00",
    "schema_fingerprint": "a1e20623a4665861"
  },
  "validation": {
    "validated_at": "2026-10-02T15:47:34+00:00",
    "contract_version": 3,
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
    "passed": true
  },
  "evidence": {
    "retrieved": 12
  }
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT Students.student_id, Students.first_name, Students.current_address_id, Students.permanent_address_id 
FROM Students 
WHERE Students.permanent_address_id != Students.current_address_id
```

---
