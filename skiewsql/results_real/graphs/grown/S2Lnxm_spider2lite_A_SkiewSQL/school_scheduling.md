# Skill graph — `school_scheduling` (3 skills)

**Skill `english_enrollments_completed`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `enrollment_id` |
| output columns | `student_id`, `last_name`, `grade`, `course_id`, `enrollment_id` |
| source tables | `Student_Schedules`, `Students`, `Classes`, `Subjects` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `student_grade_records`, `grade_rank_proportion` |
| validated_on | — |
| counter_examples | 0 |

_Select all enrollment/course records that are for English courses and represent completed classes (ClassStatus = 2). Keep each student-course enrollment as a separate row (do not aggregate multiple enrollments per student)._

```sql
SELECT
  Student_Schedules.ClassID AS course_id,
  Student_Schedules.StudentID AS student_id,
  Students.StudLastName AS last_name,
  Student_Schedules.Grade AS grade,
  Student_Schedules.ClassID || '-' || Student_Schedules.StudentID AS enrollment_id
FROM Student_Schedules
JOIN Students ON Students.StudentID = Student_Schedules.StudentID
JOIN Classes ON Classes.ClassID = Student_Schedules.ClassID
JOIN Subjects ON Subjects.SubjectID = Classes.SubjectID
WHERE Subjects.CategoryID = 'SEL'
  AND Student_Schedules.ClassStatus = 2
```

---

**Skill `student_grade_records`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `enrollment_id` |
| output columns | `student_id`, `last_name`, `grade`, `enrollment_id` |
| source tables | `english_enrollments_completed` |
| depends_on (builds on) | `english_enrollments_completed` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Normalize projection of the completed English enrollment rows: canonicalize grade values (e.g., numeric conversion or NULL handling) and ensure each row has student identifier and last name alongside the grade. Do not collapse multiple enrollments per student here._

```sql
SELECT
  english_enrollments_completed.student_id AS student_id,
  english_enrollments_completed.last_name AS last_name,
  CASE
    WHEN english_enrollments_completed.grade = '' THEN NULL
    WHEN english_enrollments_completed.grade IS NULL THEN NULL
    WHEN typeof(english_enrollments_completed.grade) = 'text' THEN
      (CASE
         WHEN trim(english_enrollments_completed.grade) = '' THEN NULL
         WHEN (trim(english_enrollments_completed.grade) GLOB '*[^0-9.-]*') THEN NULL
         ELSE CAST(trim(english_enrollments_completed.grade) AS REAL)
       END)
    ELSE CAST(english_enrollments_completed.grade AS REAL)
  END AS grade,
  english_enrollments_completed.enrollment_id AS enrollment_id
FROM english_enrollments_completed
```

---

**Skill `grade_rank_proportion`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `enrollment_id` |
| output columns | `student_id`, `last_name`, `grade`, `count_ge`, `total_count`, `proportion_ge` |
| source tables | `english_enrollments_completed` |
| depends_on (builds on) | `english_enrollments_completed` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each student-course record, compute the count of completed-English records with grade greater than or equal to this record's grade and the total number of completed-English records. Produce the proportion = (count_ge / total). Keep one row per student-course record._

```sql
SELECT
  e.enrollment_id AS student_id,
  e.last_name AS last_name,
  e.grade AS grade,
  (SELECT COUNT(*) FROM english_enrollments_completed ee
     WHERE ee.grade >= e.grade) AS count_ge,
  (SELECT COUNT(*) FROM english_enrollments_completed) AS total_count,
  CAST((SELECT COUNT(*) FROM english_enrollments_completed ee
         WHERE ee.grade >= e.grade) AS REAL) / NULLIF((SELECT COUNT(*) FROM english_enrollments_completed),0) AS proportion_ge
FROM english_enrollments_completed e
```

---
