# Skill graph — `student_transcripts_tracking` (18 skills)

**Skill `address_components`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `address_id` |
| output columns | `address_id`, `line1`, `line2`, `full_address` |
| source tables | `Addresses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | What is the first and second line for all addresses? |
| counter_examples | 0 |

_Extracts address line components from the address record._

```sql
SELECT
    a."address_id",
    a."line_1" AS "line1",
    a."line_2" AS "line2",
    a."line_1" || ', ' || a."line_2" AS "full_address"
FROM Addresses a
```

---

**Skill `course_counts`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `course_id` |
| output columns | `course_id` |
| source tables | `Courses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | How many courses are there? |
| counter_examples | 0 |

_Selects all courses from the database._

```sql
SELECT c.course_id
FROM Courses c
```

---

**Skill `find_math_course`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `course_id`, `course_name` |
| output columns | `description` |
| source tables | `Courses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select the course description for the 'math course' entry._

```sql
SELECT T1.course_description AS description
FROM Courses AS T1
WHERE T1.course_name = 'math course'
```

---

**Skill `port_chelsea_addresses`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `address` |
| output columns | `address`, `line1`, `line2`, `line3`, `city`, `zip_postcode`, `state_province_county`, `country`, `other_address_details` |
| source tables | `Addresses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select addresses located in Port Chelsea._

```sql
SELECT
    a."address_id" AS address,
    a."line_1" AS line1,
    a."line_2" AS line2,
    a."line_3" AS line3,
    a."city" AS city,
    a."zip_postcode" AS zip_postcode,
    a."state_province_county" AS state_province_county,
    a."country" AS country,
    a."other_address_details" AS other_address_details
FROM
    Addresses a
WHERE
    a."city" = 'Port Chelsea'
```

---

**Skill `city_zip_lookup`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `city_name`, `zip_code` |
| output columns | `zip_code` |
| source tables | `Addresses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Selects the zip code associated with a given city name._

```sql
SELECT 'zip_code' AS zip_code, T1.zip_postcode AS zip_code FROM Addresses T1 WHERE T1.city = 'Port Chelsea'
```

---

**Skill `department_id_degree_count`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `department_id` |
| output columns | `department_id`, `degree_count` |
| source tables | `Departments`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `department_program_count` |
| validated_on | — |
| counter_examples | 0 |

_Maps department IDs to their degree counts._

```sql
SELECT
  d.department_id,
  COUNT(se.degree_program_id) AS degree_count
FROM Departments AS d
JOIN Student_Enrolment AS se
  ON d.department_id = se.degree_program_id
GROUP BY
  d.department_id
```

---

**Skill `department_degrees`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `department_id` |
| output columns | `department_id`, `degree_count` |
| source tables | `Departments`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `max_department_degree` |
| validated_on | — |
| counter_examples | 0 |

_Calculates the number of degrees for each department._

```sql
SELECT
    d."department_id",
    COUNT(se."degree_program_id") AS "degree_count"
FROM
    Departments d
JOIN
    Student_Enrolment se ON d."department_id" = se."degree_program_id"
GROUP BY
    d."department_id"
```

---

**Skill `max_department_degree`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `max_degree_count` |
| output columns | `max_degree_count` |
| source tables | `department_degrees` |
| depends_on (builds on) | `department_degrees` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Determines the maximum degree count across all departments._

```sql
SELECT MAX(degree_count) AS max_degree_count FROM department_degrees
```

---

**Skill `departments_with_programs`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `department_id` |
| output columns | `department_id` |
| source tables | `Departments`, `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `programs_with_degrees` |
| validated_on | — |
| counter_examples | 0 |

_Select departments that have at least one associated program._

```sql
SELECT t1."department_id"
FROM "Departments" AS t1
JOIN "Degree_Programs" AS t2
ON t1."department_id" = t2."department_id"
```

---

**Skill `programs_with_degrees`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `program_id` |
| output columns | `program_id` |
| source tables | `Degree_Programs` |
| depends_on (builds on) | `departments_with_programs` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select programs that are degree programs._

```sql
SELECT dp.degree_program_id AS program_id FROM Degree_Programs dp WHERE dp.degree_summary_name LIKE '%degree%'
```

---

**Skill `department_program_count`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `department_id` |
| output columns | `department_id`, `program_count` |
| source tables | `Departments`, `Degree_Programs` |
| depends_on (builds on) | `department_id_degree_count` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Count the number of programs associated with each department._

```sql
SELECT
    d.department_id,
    COUNT(dp.degree_program_id) AS program_count
FROM
    Departments d
JOIN
    Degree_Programs dp ON d.department_id = dp.department_id
GROUP BY
    d.department_id
```

---

**Skill `degree_names`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `degree_name` |
| output columns | `degree_program_id`, `degree_name` |
| source tables | `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select all degree names from the degrees table._

```sql
SELECT "degree_program_id" AS degree_program_id, "degree_summary_name" AS degree_name
FROM "Degree_Programs"
```

---

**Skill `degree_program_names`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `degree_program_name` |
| output columns | `degree_program_name` |
| source tables | `Degree_Programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Selects all degree program names._

```sql
SELECT "degree_program_id" AS "degree_program_name" FROM "Degree_Programs"
```

---

**Skill `engineering_programs`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `program_name` |
| output columns | `program_id`, `program_name` |
| source tables | `degree_programs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Selects degree programs offered by the engineering department._

```sql
SELECT "degree_programs"."degree_program_id" AS "program_id", "degree_programs"."degree_summary_name" AS "program_name"
FROM "degree_programs"
WHERE "degree_programs"."department_id" = (SELECT "department_id" FROM "Departments" WHERE "Departments"."department_name" = 'Engineering')
```

---

**Skill `department_details`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `department_name` |
| output columns | `department_name`, `degree_count` |
| source tables | `Departments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Selects department name and degree count for the engineering department._

```sql
SELECT d."department_name", sum(case when d."department_name" = 'engineering' then 1 else 0 end) as "degree_count"
FROM Departments d
WHERE d."department_name" = 'engineering'
GROUP BY d."department_name"
```

---

**Skill `get_section_details`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `section_id` |
| output columns | `section_name`, `section_description` |
| source tables | `Sections` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `sections_sel` |
| validated_on | — |
| counter_examples | 0 |

_Retrieve section details based on the section identifier._

```sql
SELECT
  s.section_name,
  s.section_description
FROM Sections AS s
WHERE s.section_id = 1
```

---

**Skill `sections_sel`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `section_name`, `section_description` |
| output columns | `section_name`, `section_description` |
| source tables | `Sections` |
| depends_on (builds on) | `get_section_details` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Selects section names and descriptions from the database._

```sql
SELECT
  s.section_name,
  s.section_description
FROM Sections AS s
```

---

**Skill `course_section_counts`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `course_id`, `course_name` |
| output columns | `course_id`, `course_name`, `section_count` |
| source tables | `Courses`, `Sections` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Selects courses and their section counts._

```sql
SELECT
    c.course_id,
    c.course_name,
    COUNT(s.section_id) AS section_count
FROM
    Courses c
LEFT JOIN
    Sections s ON c.course_id = s.course_id
GROUP BY
    c.course_id,
    c.course_name
```

---
