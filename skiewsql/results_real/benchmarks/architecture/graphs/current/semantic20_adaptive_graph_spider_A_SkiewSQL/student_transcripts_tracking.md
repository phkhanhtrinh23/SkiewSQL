# Skill graph — `student_transcripts_tracking` (1 skills)

## Skill `chunk_view_0`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Departments`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Task: Identify the department with the highest number of degree offerings, returning the department's name and unique identifier. Required outputs: Department Name. Department ID Filters: The output m

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (1)

- What is the name and id of the department with the most number of degrees ?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  "Departments"."department_name",
  "Departments"."department_id"
FROM Departments
WHERE
  "Departments"."department_id" IN (
    SELECT
      department_id
    FROM Degree_Programs
    GROUP BY
      department_id
    ORDER BY
      COUNT(*) DESC
    LIMIT 1
  )
```

---
