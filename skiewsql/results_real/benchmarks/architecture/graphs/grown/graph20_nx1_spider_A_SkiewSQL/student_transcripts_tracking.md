# Skill graph — `student_transcripts_tracking` (3 skills)

**Skill `chunk_view_0`** — category `SEL`

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
  "Addresses".line_1,
  "Addresses".line_2,
  "Addresses"
FROM "Addresses"
```

---

**Skill `chunk_view_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Retrieve all addresses, including the line 1 and line 2 address components. Required outputs: A record containing the address line 1, address line 2, and the entire address._

```sql
SELECT
  "Student_Enrolment".other_details
FROM "Student_Enrolment"
WHERE "Student_Enrolment".other_details IS NOT NULL
```

---

**Skill `chunk_view_0_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Departments`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | How many different departments offer degrees?. How many different degree names are offered?. How many degrees does the engineering department offer?. What are the names and id of courses having at most 2 sections? |
| counter_examples | 4 |

_Task: Identify the department name and ID that has the highest number of degrees. Required outputs: Department Name. Department ID Filters: The result should be the department with the maximum number _

```sql
SELECT
  D."department_name",
  D."department_id"
FROM Departments AS D
JOIN Degree_Programs AS DP
  ON D."department_id" = DP."department_id"
GROUP BY
  D."department_name",
  D."department_id"
ORDER BY
  COUNT(DP."degree_program_id") DESC
LIMIT 1
```

---
