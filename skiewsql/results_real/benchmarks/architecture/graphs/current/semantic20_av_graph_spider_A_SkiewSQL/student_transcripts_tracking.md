# Skill graph — `student_transcripts_tracking` (3 skills)

## Skill `chunk_view_0`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Addresses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Task: Retrieve all addresses, including the line 1 and line 2 address components. Required outputs: A record containing the address line 1, address line 2, and the entire address.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (7)

- What is the first and second line for all addresses?
- How many courses in total are listed?
- How many courses are there?
- How is the math course described?
- What are the descriptions for all the math courses?
- What is the zip code of the address in the city Port Chelsea?
- What are the names and descriptions of all the sections?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  a."line_1",
  a."line_2",
  a.*
FROM "Addresses" AS a
```

---

## Skill `chunk_view_1`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Task: Retrieve all addresses, including the line 1 and line 2 address components. Required outputs: A record containing the address line 1, address line 2, and the entire address.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  "Student_Enrolment".other_details AS "address"
FROM "Student_Enrolment"
```

---

## Skill `chunk_view_0_2`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Departments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Task: Identify the department name and ID that has the highest number of degrees. Required outputs: Department Name. Department ID Filters: The result should be the department with the maximum number

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (4)

- How many departments offer any degree?
- How many different degree names are offered?
- How many degrees does the engineering department have?
- What are the names and id of courses having at most 2 sections?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  "Departments"."department_name",
  "Departments"."department_id"
FROM Departments
```

---
