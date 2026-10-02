# Skill graph — `education_business` (4 skills)

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

Task: Calculate the average quantity sold for the top three best-selling hardware products within each division for the calendar year 2021, considering only sales data from that year. Required outputs

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

- Which university faculty members' salaries are closest to the average salary for their respective ranks? Please provide the ranks, first names, last names, and salaries.university

### Executable SQL body

```sql
SELECT
  hfsm.product_code,
  hfsm.sold_quantity,
  hfsm.fiscal_year
FROM hardware_fact_sales_monthly AS hfsm
WHERE hfsm.fiscal_year = 2021
ORDER BY hfsm.sold_quantity DESC
LIMIT 3
```

---

## Skill `top_sales_reps_per_region`

Category: `RANK`

| field | value |
|---|---|
| grain (one row per) | `region_id`, `name` |
| output columns | `region`, `sales_rep`, `total_sales_amount` |
| source tables | `web_sales_reps`, `web_accounts`, `web_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Ranks sales representatives by total sales within each region, including ties.

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
  r.region_id AS region,
  r.name AS sales_rep,
  SUM(wo.total_amt_usd) AS total_sales_amount
FROM web_sales_reps AS r
JOIN web_accounts AS a
  ON r.region_id = a.id
JOIN web_orders AS wo
  ON a.id = wo.account_id
GROUP BY
  r.region_id,
  r.name
```

---

## Skill `company_salaries_by_city`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `CompanyName`, `Location` |
| output columns | `company_name`, `city`, `average_salary` |
| source tables | `SalaryDataset` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Calculate average salaries for each company in each city.

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
    sd.CompanyName AS company_name,
    sd.Location AS city,
    AVG(sd.SalariesReported) AS average_salary
FROM
    SalaryDataset sd
GROUP BY
    sd.CompanyName,
    sd.Location
```

---

## Skill `top_companies_by_salary`

Category: `RANK`

| field | value |
|---|---|
| grain (one row per) | `CompanyName`, `Location` |
| output columns | `company_name`, `city`, `average_salary`, `average_salary_national` |
| source tables | `SalaryDataset` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Rank companies by average salary in each city, then filter to top 5.

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
    sd.CompanyName AS company_name,
    sd.Location AS city,
    AVG(sd.SalariesReported) AS average_salary,
    AVG(sd.SalariesReported) AS average_salary_national
FROM
    SalaryDataset sd
GROUP BY
    sd.CompanyName,
    sd.Location
ORDER BY
    average_salary DESC
LIMIT 5
```

---
