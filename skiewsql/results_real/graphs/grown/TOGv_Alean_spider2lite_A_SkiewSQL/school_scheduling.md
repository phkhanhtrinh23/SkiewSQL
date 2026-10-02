# Skill graph — `school_scheduling` (2 skills)

**Skill `completed_english_students`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `student_id` |
| output columns | `student_id`, `last_name`, `grade` |
| source tables | `Students`, `Student_Schedules`, `Classes`, `Subjects`, `Categories` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `student_quintile_mapping` |
| validated_on | — |
| counter_examples | 0 |

_cohort of students who completed English courses, joining student demographics with enrollment and grade records_

```sql
SELECT
    s.StudentID as student_id,
    s.StudLastName as last_name,
    ss.Grade as grade
FROM Students s
JOIN Student_Schedules ss ON s.StudentID = ss.StudentID
JOIN Classes c ON ss.ClassID = c.ClassID
JOIN Subjects sub ON c.SubjectID = sub.SubjectID
JOIN Categories cat ON sub.CategoryID = cat.CategoryID
```

---

**Skill `student_quintile_mapping`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `student_id` |
| output columns | `last_name`, `quintile_category` |
| source tables | — |
| depends_on (builds on) | `completed_english_students` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_computes grade-based rank ratio for each student and maps it to the corresponding quintile category label_

```sql
SELECT 
    ce.last_name,
    CASE 
        WHEN PERCENT_RANK() OVER (ORDER BY ce.grade) <= 0.2 THEN '1st Quintile'
        WHEN PERCENT_RANK() OVER (ORDER BY ce.grade) <= 0.4 THEN '2nd Quintile'
        WHEN PERCENT_RANK() OVER (ORDER BY ce.grade) <= 0.6 THEN '3rd Quintile'
        WHEN PERCENT_RANK() OVER (ORDER BY ce.grade) <= 0.8 THEN '4th Quintile'
        ELSE '5th Quintile'
    END AS quintile_category
FROM completed_english_students ce
```

---
