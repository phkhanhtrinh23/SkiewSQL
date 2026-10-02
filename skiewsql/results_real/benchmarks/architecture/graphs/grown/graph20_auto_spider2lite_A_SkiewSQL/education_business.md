# Skill graph — `education_business` (2 skills)

**Skill `focused_whole_view`** — category `SEL`

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
    "hardware_dim_product".segment,
    COUNT(DISTINCT "hardware_fact_sales_monthly"."product_code")
FROM "hardware_dim_product"
INNER JOIN "hardware_fact_sales_monthly"
    ON "hardware_dim_product"."product_code" = "hardware_fact_sales_monthly"."product_code"
WHERE
    "hardware_fact_sales_monthly"."fiscal_year" = 2020
GROUP BY
    "hardware_dim_product".segment
ORDER BY
    (
        SELECT
            CAST(COUNT(DISTINCT "hardware_fact_sales_monthly"."product_code") FILTER (WHERE "hardware_fact_sales_monthly"."fiscal_year" = 2020) AS REAL) /
            CAST(COUNT(DISTINCT "hardware_fact_sales_monthly"."product_code") FILTER (WHERE "hardware_fact_sales_monthly"."fiscal_year" = 2020) AS REAL)
    )
    ASC
```

---

**Skill `focused_whole_view_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `university_faculty` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: Identify university faculty members whose salaries are closest to the average salary for their specified rank, returning the rank, first name, last name, and salary for each matching faculty mem_

```sql
SELECT
  FacRank,
  FacFirstName,
  FacLastName,
  FacSalary
FROM university_faculty
WHERE FacRank IN (
  SELECT
    FacRank
  FROM university_faculty
)
```

---
