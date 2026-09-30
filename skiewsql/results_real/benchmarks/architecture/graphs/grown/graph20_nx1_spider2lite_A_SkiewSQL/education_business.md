# Skill graph — `education_business` (4 skills)

**Skill `chunk_view_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | — |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 2 |

_Task: Generate a list of hardware product segments and their unique product counts for 2020, sorted by the segment with the largest percentage increase in unique fact sales products compared to 2021. _

```sql
SELECT
  "web_accounts"."name" AS "hardware_segment",
  COUNT("web_accounts"."id") AS "unique_product_count",
  0.0 AS "percentage_increase"
FROM web_accounts
LIMIT 5
```

---

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `StaffHours` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Identify university faculty members whose salaries are closest to the average salary for their specified rank, returning the rank, first name, last name, and salary for each matching faculty mem_

```sql
SELECT
  'Faculty' AS Rank,
  s.StaffMember AS First_Name,
  s.StaffMember AS Last_Name,
  s.EventTime AS Salary
FROM StaffHours AS s
```

---

**Skill `chunk_view_1_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `university_faculty` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Identify university faculty members whose salaries are closest to the average salary for their specified rank, returning the rank, first name, last name, and salary for each matching faculty mem_

```sql
SELECT
    "FacRank",
    "FacFirstName",
    "FacLastName",
    "FacSalary"
FROM university_faculty
WHERE
    "FacRank" IN (
        SELECT
            "FacRank"
        FROM university_faculty
        GROUP BY
            "FacRank"
    )
```

---

**Skill `chunk_view_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `university_course`, `hardware_fact_gross_price` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Identify university faculty members whose salaries are closest to the average salary for their specified rank, returning the rank, first name, last name, and salary for each matching faculty mem_

```sql
SELECT
  "university_course".CourseNo,
  "university_course".CrsDesc,
  "university_course".CrsUnits,
  "hardware_fact_gross_price".gross_price
FROM university_course
JOIN hardware_fact_gross_price ON university_course.CourseNo = hardware_fact_gross_price.product_code
```

---
