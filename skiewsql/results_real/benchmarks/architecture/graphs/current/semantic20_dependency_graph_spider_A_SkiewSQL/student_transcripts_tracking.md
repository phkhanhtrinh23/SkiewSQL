# Skill graph — `student_transcripts_tracking` (14 skills)

## Skill `second_lines`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `address_id` |
| output columns | `line2`, `address_id` |
| source tables | `Addresses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Selects the second line from the addresses table.

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
    a.line_2 AS line2,
    a.address_id
FROM Addresses a
```

---

## Skill `course_counts`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `course_id` |
| output columns | `course_id` |
| source tables | `Courses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Selects all courses from the database.

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
SELECT c.course_id
FROM Courses c
LIMIT 0
```

---

## Skill `find_math_course`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `course_id`, `course_name` |
| output columns | `description` |
| source tables | `Courses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Select the course description for the 'math course' entry.

### Semantic filters

```json
{
  "column": "course_name",
  "value": "math course",
  "course_name": "math course"
}
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
SELECT T1.course_description AS description
FROM Courses AS T1
WHERE T1.course_name = 'math course'
```

---

## Skill `department_degree_count`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `department_name` |
| output columns | `department_name`, `degree_count` |
| source tables | `Departments`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `degree_offerings_per_dept` |

### Description

Calculate the number of degree offerings per department.

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
    d.department_name,
    COUNT(dp.degree_program_id) AS degree_count
FROM
    Departments d
JOIN
    Degree_Programs dp ON d.department_id = dp.department_id
GROUP BY
    d.department_name
```

---

## Skill `degree_offerings_per_dept`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `department_name` |
| output columns | `department_name`, `degree_count` |
| source tables | `Departments`, `Degree_Programs` |
| depends_on (builds on) | `department_degree_count` |
| depended-on by (builds on this) | — |

### Description

Join departments with their degree offerings.

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
  d.department_name,
  COUNT(dp.degree_program_id) AS degree_count
FROM Departments AS d
JOIN Degree_Programs AS dp
  ON d.department_id = dp.department_id
GROUP BY
  d.department_name
```

---

## Skill `department_degrees`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `department_id` |
| output columns | `department_id`, `degree_count` |
| source tables | `Departments`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `max_department_degree` |

### Description

Calculates the number of degrees for each department.

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
    d.department_id,
    COUNT(dep.degree_program_id) AS degree_count
FROM
    Departments d
JOIN
    Degree_Programs dep ON d.department_id = dep.department_id
GROUP BY
    d.department_id
```

---

## Skill `department_details`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `department_id`, `department_name` |
| output columns | `department_id`, `department_name` |
| source tables | `Departments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Selects department ID and name.

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
SELECT department_id, department_name FROM Departments
```

---

## Skill `max_department_degree`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `max_degree_count` |
| output columns | `max_degree_count` |
| source tables | `department_degrees` |
| depends_on (builds on) | `department_degrees` |
| depended-on by (builds on this) | — |

### Description

Determines the maximum degree count across all departments.

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
SELECT MAX(degree_count) AS 'max_degree_count' FROM department_degrees
```

---

## Skill `degree_names`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `degree_name` |
| output columns | `degree_name` |
| source tables | `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `degree_program_names` |

### Description

Select all degree names from the degrees table.

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
SELECT "degree_summary_name" AS "degree_name" FROM "Degree_Programs"
```

---

## Skill `degree_program_names`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `degree_program_name` |
| output columns | `degree_program_name` |
| source tables | `Degree_Programs` |
| depends_on (builds on) | `degree_names` |
| depended-on by (builds on this) | — |

### Description

Selects all degree program names.

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
SELECT "degree_program_name" AS degree_program_name FROM Degree_Programs
```

---

## Skill `department_details_10`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `department_name` |
| output columns | `department_name`, `department_count` |
| source tables | `Departments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Selects department information based on the department name.

### Semantic filters

```json
{
  "column": "department_name",
  "value": "engineering",
  "department_name": "engineering"
}
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
SELECT "department_name", COUNT(*) AS "department_count" FROM Departments WHERE "department_name" = 'engineering' GROUP BY "department_name"
```

---

## Skill `get_section_details`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `section_id` |
| output columns | `section_name`, `section_description` |
| source tables | `Sections` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `sections_sel` |

### Description

Retrieve section details based on the section identifier.

### Semantic filters

```json
{
  "section_id": "1"
}
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
  "Sections".section_name,
  "Sections".section_description
FROM "Sections"
WHERE "Sections".section_id = 1
```

---

## Skill `sections_sel`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `section_name`, `section_description` |
| output columns | `section_name`, `section_description` |
| source tables | `Sections` |
| depends_on (builds on) | `get_section_details` |
| depended-on by (builds on this) | — |

### Description

Selects section names and descriptions from the database.

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
  s.section_name,
  s.section_description
FROM Sections AS s
```

---

## Skill `course_section_counts`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `course_id`, `course_name` |
| output columns | `course_id`, `course_name`, `section_count` |
| source tables | `Courses`, `Sections` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Selects courses and their section counts.

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

### Counter-examples (1)

- What are the names and ids of every course with less than 2 sections?

### Executable SQL body

```sql
SELECT
  c.course_id,
  c.course_name,
  COUNT(s.section_id) AS section_count
FROM Courses AS c
JOIN Sections AS s
  ON c.course_id = s.course_id
GROUP BY
  c.course_id,
  c.course_name
```

---
