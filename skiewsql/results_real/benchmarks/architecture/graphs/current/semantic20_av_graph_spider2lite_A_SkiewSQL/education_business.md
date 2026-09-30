# Skill graph — `education_business` (5 skills)

## Skill `chunk_view_1`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | — |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Task: Generate a list of hardware product segments and their unique product counts for 2020, sorted by the segment with the largest percentage increase in unique fact sales products compared to 2021.

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

### Counter-examples (2)

- For the calendar year 2021, what is the overall average quantity sold of the top three best-selling hardware products (by total quantity sold) in each division?
- Provide a detailed web sales report for each region, including the number of orders, total sales amount, and the name and sales amount of all sales representatives who achieved the highest total sales amount in that region (include all representatives in case of a tie).

### Executable SQL body

```sql
SELECT
    "web_accounts".name AS product_segment,
    COUNT("web_accounts".id) AS unique_product_count,
    0 AS unique_product_count_2021
FROM
    "web_accounts"
WHERE
    STRFTIME('%Y', "web_accounts".website) = '2020'
GROUP BY
    "web_accounts".name
ORDER BY
    (
        SELECT
            CAST(COUNT(id) - COUNT(id) AS REAL) / COUNT(id)
        FROM
            "web_accounts" AS sub
        WHERE
            STRFTIME('%Y', "sub".website) = '2021'
    )
```

---

## Skill `chunk_view_2`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `hardware_fact_sales_monthly` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Task: Generate a list of hardware product segments and their unique product counts for 2020, sorted by the segment with the largest percentage increase in unique fact sales products compared to 2021.

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
    "product_code",
    COUNT(DISTINCT "product_code") AS "unique_product_count_2020"
FROM
    "hardware_fact_sales_monthly"
WHERE
    "fiscal_year" = 2020
GROUP BY
    "product_code"
```

---

## Skill `chunk_view_0`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `university_enrollment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Task: Identify university faculty members whose salaries are closest to the average salary for their specified rank, returning the rank, first name, last name, and salary for each matching faculty mem

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
  "university_enrollment".StdNo,
  "university_enrollment".EnrGrade
FROM university_enrollment
```

---

## Skill `chunk_view_1_3`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `university_faculty` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Task: Identify university faculty members whose salaries are closest to the average salary for their specified rank, returning the rank, first name, last name, and salary for each matching faculty mem

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
    "FacRank",
    "FacFirstName",
    "FacLastName",
    "FacSalary"
FROM
    "university_faculty"
WHERE
    "FacSalary" = (
        SELECT
            AVG("FacSalary")
        FROM
            "university_faculty"
        WHERE
            "FacRank" = "FacRank"
    )
```

---

## Skill `chunk_view_2_4`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `university_course`, `hardware_fact_gross_price` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Task: Identify university faculty members whose salaries are closest to the average salary for their specified rank, returning the rank, first name, last name, and salary for each matching faculty mem

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
  "university_course".CourseNo,
  "university_course".CrsDesc,
  "university_course".CrsUnits,
  "hardware_fact_gross_price".gross_price
FROM university_course
JOIN hardware_fact_gross_price
  ON university_course.CourseNo = hardware_fact_gross_price.product_code
```

---
