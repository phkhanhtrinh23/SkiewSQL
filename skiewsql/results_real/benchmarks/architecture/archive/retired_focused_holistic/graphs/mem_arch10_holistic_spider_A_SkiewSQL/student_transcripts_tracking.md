# Skill graph — `student_transcripts_tracking` (2 skills)

**Skill `focused_whole_view`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Addresses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | What is the first and second line for all addresses?. How many courses in total are listed?. How many courses are there?. How is the math course described?. What are the descriptions for all the math courses?. What is the zip code of the address in the city Port Chelsea?. What is the zip code for Po |
| counter_examples | 0 |

_Task: Retrieve all addresses, including the line 1 and line 2 address components. Required outputs: A record containing the address line 1, address line 2, and the entire address._

```sql
SELECT
  "line_1",
  "line_2",
  "line_1",
  "line_2",
  "other_address_details"
FROM Addresses
```

---

**Skill `focused_whole_view_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Departments`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: Identify the department with the highest number of degree offerings, returning the department's name and unique identifier. Required outputs: Department Name. Department ID Filters: The result s_

```sql
SELECT
  D."department_name",
  D."department_id"
FROM Departments AS D
JOIN Degree_Programs AS DP
  ON D."department_id" = DP."department_id"
```

---
