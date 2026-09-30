# Skill graph — `education_business` (9 skills)

**Skill `sales_comparison`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `product_code` |
| output columns | `product_id`, `unique_sales_2020`, `unique_sales_2021`, `percentage_change` |
| source tables | `hardware_fact_sales_monthly` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculate the unique product sales count for 2020 and 2021 and the percentage change._

```sql
SELECT
    hfs_m.product_code AS product_id,
    COUNT(DISTINCT hfs_m.customer_code) AS unique_sales_2020,
    COUNT(DISTINCT hfs_m.customer_code) AS unique_sales_2021,
    CASE
        WHEN COUNT(DISTINCT hfs_m.customer_code) - COUNT(DISTINCT hfs_m.customer_code) = 0
        THEN 0
        ELSE (CAST(COUNT(DISTINCT hfs_m.customer_code) - COUNT(DISTINCT hfs_m.customer_code) AS REAL) / COUNT(DISTINCT hfs_m.customer_code) * 100)
    END AS percentage_change
FROM
    hardware_fact_sales_monthly AS hfs_m
WHERE
    hfs_m.fiscal_year = 2020 OR hfs_m.fiscal_year = 2021
GROUP BY
    hfs_m.product_code
```

---

**Skill `sales_by_product_and_division_2021`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `product_code`, `division` |
| output columns | `product_id`, `division_name`, `total_quantity_sold` |
| source tables | `hardware_fact_sales_monthly`, `hardware_dim_product` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculate total sales quantity for each product within each division in 2021._

```sql
SELECT
  hp.product_code AS product_id,
  hd.division AS division_name,
  SUM(hfs.sold_quantity) AS total_quantity_sold
FROM hardware_fact_sales_monthly AS hfs
JOIN hardware_dim_product AS hp
  ON hfs.product_code = hp.product_code
JOIN hardware_dim_product AS hd
  ON hp.division = hd.division
WHERE
  STRFTIME('%Y', hfs.date) = '2021'
GROUP BY
  hp.product_code,
  hd.division
```

---

**Skill `aggregate_top_products`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `division`, `product_code` |
| output columns | `division_name`, `product_id`, `average_quantity_sold` |
| source tables | `hardware_dim_product`, `hardware_fact_sales_monthly` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculate the average quantity sold for the top three hardware products within each division._

```sql
SELECT
  hd.division AS "division_name",
  hd.product_code AS "product_id",
  AVG(hfs.sold_quantity) AS "average_quantity_sold"
FROM hardware_dim_product AS hd
JOIN hardware_fact_sales_monthly AS hfs
  ON hd.product_code = hfs.product_code
GROUP BY
  hd.division,
  hd.product_code
ORDER BY
  hd.division,
  hd.product_code
```

---

**Skill `orders_by_region`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `region` |
| output columns | `region`, `order_count`, `total_sales_amount` |
| source tables | `hardware_dim_customer`, `web_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Groups orders by region to calculate sales totals and order counts._

```sql
SELECT
  t1."region",
  COUNT(t2."id") AS "order_count",
  SUM(t2."total_amt_usd") AS "total_sales_amount"
FROM "hardware_dim_customer" AS t1
JOIN "web_orders" AS t2
  ON t1."customer_code" = t2."account_id"
GROUP BY
  t1."region"
```

---

**Skill `top_sales_reps_per_region`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `name`, `name` |
| output columns | `region`, `sales_rep`, `total_sales_amount` |
| source tables | `web_region`, `web_sales_reps`, `web_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Ranks sales representatives by total sales within each region, including ties._

```sql
SELECT
    r.name AS region,
    w.name AS sales_rep,
    SUM(wo.total_amt_usd) AS total_sales_amount
FROM web_region r
JOIN web_sales_reps w ON r.id = w.region_id
JOIN web_orders wo ON w.id = wo.account_id
GROUP BY r.name, w.name
ORDER BY r.name, SUM(wo.total_amt_usd)
```

---

**Skill `faculty_salaries`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `faculty_id` |
| output columns | `faculty_id`, `salary` |
| source tables | `university_faculty` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `rank_salaries` |
| validated_on | — |
| counter_examples | 0 |

_Select faculty members and their salaries._

```sql
SELECT
  t1.FacNo AS faculty_id,
  t1.FacSalary AS salary
FROM university_faculty AS t1
```

---

**Skill `rank_salaries`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `FacRank` |
| output columns | `rank`, `average_salary` |
| source tables | `university_faculty` |
| depends_on (builds on) | `faculty_salaries` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculate the average salary for each rank._

```sql
SELECT
    "FacRank" AS rank,
    AVG("FacSalary") AS average_salary
FROM university_faculty
GROUP BY "FacRank"
```

---

**Skill `company_salaries_by_city`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `CompanyName`, `Location` |
| output columns | `company_name`, `city`, `average_salary` |
| source tables | `SalaryDataset` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculate average salaries for each company in each city._

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

**Skill `top_companies_by_salary`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `CompanyName`, `Location` |
| output columns | `company_name`, `city`, `average_salary`, `average_salary_national` |
| source tables | `SalaryDataset` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Rank companies by average salary in each city, then filter to top 5._

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
