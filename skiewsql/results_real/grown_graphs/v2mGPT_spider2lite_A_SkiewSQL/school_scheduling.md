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

_Task: Produce a list of last names for every student who has completed English courses (completion defined as ClassStatus = 2) along with a quintile label determined by each student's rank among all s_

```sql
SELECT
  s.StudentID,
  s.StudLastName,
  ss.ClassID,
  ss.ClassStatus,
  ss.Grade,
  c.SubjectID,
  subj.SubjectName,
  subj.CategoryID
FROM
  Student_Schedules AS ss
JOIN
  Students AS s ON ss.StudentID = s.StudentID
JOIN
  Classes AS c ON ss.ClassID = c.ClassID
JOIN
  Subjects AS subj ON c.SubjectID = subj.SubjectID
WHERE
  ss.ClassStatus = 2
  AND subj.SubjectName LIKE '%English%'
```

---
