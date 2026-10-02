# Skill graph — `education_business` (7 skills)

## Skill `sales_2020`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `product_code` |
| output columns | `product_id`, `sales_quantity`, `sales_price` |
| source tables | `hardware_fact_sales_monthly`, `web_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Select sales records for the year 2020.

### Semantic filters

```json
{
  "column": "fiscal_year",
  "value": "2020",
  "fiscal_year": "2020"
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
    hfsm.product_code AS product_id,
    hfsm.sold_quantity AS sales_quantity,
    SUM(wo.total_amt_usd) AS sales_price
FROM
    hardware_fact_sales_monthly AS hfsm
JOIN
    web_orders AS wo ON hfsm.customer_code = wo.account_id
WHERE
    hfsm.fiscal_year = 2020
GROUP BY
    hfsm.product_code
```

---

## Skill `sales_2021`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `product_id` |
| output columns | `product_id`, `sales_quantity`, `sales_price` |
| source tables | `hardware_fact_sales_monthly`, `web_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Select sales records for the year 2021.

### Semantic filters

```json
{
  "column": "fiscal_year",
  "value": "2021",
  "fiscal_year": "2021"
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
    hfsm.product_code AS product_id,
    hfsm.sold_quantity AS sales_quantity,
    wo.total_amt_usd * wo.standard_qty AS sales_price
FROM
    hardware_fact_sales_monthly AS hfsm
JOIN
    web_orders AS wo ON hfsm.customer_code = wo.account_id
WHERE
    hfsm.fiscal_year = 2021
```

---

## Skill `aggregate_top_products`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `division`, `product_code` |
| output columns | `division_name`, `product_id`, `average_quantity_sold` |
| source tables | `hardware_dim_product`, `hardware_fact_sales_monthly` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Calculate the average quantity sold for the top three hardware products within each division.

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
    hd.division AS division_name,
    hd.product_code AS product_id,
    AVG(hf.sold_quantity) AS average_quantity_sold
FROM
    hardware_dim_product hd
JOIN
    hardware_fact_sales_monthly hf ON hd.product_code = hf.product_code
GROUP BY
    hd.division,
    hd.product_code
ORDER BY
    hd.division,
    hd.product_code
```

---

## Skill `orders_by_region`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `region` |
| output columns | `region`, `order_count`, `total_sales_amount` |
| source tables | `web_orders`, `hardware_dim_customer` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Groups orders by region to calculate sales totals and order counts.

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
  T1.region,
  COUNT(T2.id) AS "order_count",
  SUM(T2.total_amt_usd) AS "total_sales_amount"
FROM web_orders AS T2
INNER JOIN hardware_dim_customer AS T1
  ON T2.account_id = T1.customer_code
GROUP BY
  T1.region
```

---

## Skill `top_sales_reps_per_region`

Category: `RANK`

| field | value |
|---|---|
| grain (one row per) | `name`, `name` |
| output columns | `region`, `sales_rep`, `total_sales_amount` |
| source tables | `web_region`, `web_sales_reps`, `web_orders` |
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
    wr.name AS region,
    srs.name AS sales_rep,
    SUM(wo.total_amt_usd) AS total_sales_amount
FROM
    web_region wr
JOIN
    web_sales_reps srs ON wr.id = srs.region_id
JOIN
    web_orders wo ON srs.id = wo.account_id
GROUP BY
    wr.name,
    srs.name
ORDER BY
    total_sales_amount DESC,
    srs.name
```

---

## Skill `faculty_salaries`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `faculty_id` |
| output columns | `faculty_id`, `salary` |
| source tables | `university_faculty` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `rank_salaries` |

### Description

Select faculty members and their salaries.

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
  T1.FacNo AS faculty_id,
  T1.FacSalary AS salary
FROM university_faculty AS T1
```

---

## Skill `rank_salaries`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `FacRank` |
| output columns | `rank`, `average_salary` |
| source tables | `university_faculty` |
| depends_on (builds on) | `faculty_salaries` |
| depended-on by (builds on this) | — |

### Description

Calculate the average salary for each rank.

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
    "FacRank" AS rank,
    AVG("FacSalary") AS average_salary
FROM university_faculty
GROUP BY "FacRank"
```

---
