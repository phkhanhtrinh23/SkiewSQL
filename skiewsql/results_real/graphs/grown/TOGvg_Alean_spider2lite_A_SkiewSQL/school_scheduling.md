# Skill graph — `school_scheduling` (1 skills)

**Skill `student_quintile_labels`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `student` |
| output columns | `student_last_name`, `quintile_label` |
| source tables | `Students`, `Student_Schedules` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Compute the rank of each student based on their grade, calculate the rank-to-total ratio, and apply a business rule to map the ratio to the appropriate performance quintile category._

```sql
SELECT
    s."StudLastName" AS student_last_name,
    CASE
        WHEN r.rank_val * 1.0 / r.total_val <= 0.2 THEN 'Q1'
        WHEN r.rank_val * 1.0 / r.total_val <= 0.4 THEN 'Q2'
        WHEN r.rank_val * 1.0 / r.total_val <= 0.6 THEN 'Q3'
        WHEN r.rank_val * 1.0 / r.total_val <= 0.8 THEN 'Q4'
        ELSE 'Q5'
    END AS quintile_label
FROM Students s
JOIN Student_Schedules ss ON s."StudentID" = ss."StudentID"
JOIN (
    SELECT
        "StudentID",
        RANK() OVER (ORDER BY "Grade" DESC) AS rank_val,
        COUNT(*) OVER () AS total_val
    FROM Student_Schedules
) r ON ss."StudentID" = r."StudentID"
```

---
