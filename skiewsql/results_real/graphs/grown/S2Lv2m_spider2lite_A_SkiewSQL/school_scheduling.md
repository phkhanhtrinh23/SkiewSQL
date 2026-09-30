# Skill graph — `school_scheduling` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Student_Schedules`, `Students`, `Classes`, `Subjects` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Produce, for every student who has completed English courses (completion defined as ClassStatus = 2), that student's last name together with a quintile label determined by ranking students by th_

```sql
SELECT
  Students.StudentID,
  Students.StudLastName,
  Student_Schedules.ClassID,
  Student_Schedules.Grade,
  Classes.SubjectID,
  Subjects.SubjectName,
  Student_Schedules.ClassStatus
FROM Student_Schedules
JOIN Students ON Student_Schedules.StudentID = Students.StudentID
JOIN Classes ON Student_Schedules.ClassID = Classes.ClassID
JOIN Subjects ON Classes.SubjectID = Subjects.SubjectID
WHERE Student_Schedules.ClassStatus = 2
  AND Subjects.SubjectName = 'English'
```

---
