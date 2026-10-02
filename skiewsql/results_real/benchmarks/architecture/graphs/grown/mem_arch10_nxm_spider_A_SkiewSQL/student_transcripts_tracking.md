# Skill graph — `student_transcripts_tracking` (6 skills)

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
WHERE 1=1
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
SELECT
  T1.course_description AS description
FROM Courses AS T1
WHERE
  T1.course_name = 'math course'
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
| source tables | `Departments`, `Degree_Programs`, `Student_Enrolment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Maps department IDs to their degree counts._

```sql
SELECT
  d.department_id,
  COUNT(se.degree_program_id) AS degree_count
FROM Departments AS d
JOIN Degree_Programs AS dp
  ON d.department_id = dp.department_id
JOIN Student_Enrolment AS se
  ON se.degree_program_id = dp.degree_program_id
GROUP BY
  d.department_id
```

---
