# Skill graph — `education_business` (4 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `hardware_dim_product`, `hardware_fact_sales_monthly` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: For each hardware product segment, compute the number of unique products that had sales facts in calendar year 2020, and return those segment names with their 2020 unique product counts, includi_

```sql
SELECT
  hd.segment,
  hf_2020.product_code AS product_code_2020,
  hf_2021.product_code AS product_code_2021,
  hf_2020.fiscal_year AS fiscal_year_2020,
  hf_2021.fiscal_year AS fiscal_year_2021,
  hd.product_code AS product_code_dim
FROM hardware_dim_product hd
LEFT JOIN hardware_fact_sales_monthly hf_2020
  ON hd.product_code = hf_2020.product_code
  AND hf_2020.fiscal_year = 2020
LEFT JOIN hardware_fact_sales_monthly hf_2021
  ON hd.product_code = hf_2021.product_code
  AND hf_2021.fiscal_year = 2021
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `web_region`, `web_sales_reps`, `web_accounts`, `web_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each region, compute a web sales report that includes the number of orders in that region, the total sales amount for the region, and, for each sales representative in that region who achiev_

```sql
SELECT
  wr.id AS region_id,
  wr.name AS region_name,
  wa.id AS account_id,
  wa.sales_rep_id,
  ws.id AS web_order_id,
  ws.occurred_at AS web_order_occurred_at,
  ws.total_amt_usd AS web_order_amount,
  srep.name AS sales_rep_name
FROM web_region wr
LEFT JOIN web_sales_reps srep
  ON srep.region_id = wr.id
LEFT JOIN web_accounts wa
  ON wa.sales_rep_id = srep.id
LEFT JOIN web_orders ws
  ON ws.account_id = wa.id
WHERE ws.id IS NOT NULL
```

---

**Skill `chunk_view_0_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `university_faculty` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each faculty rank, find the university faculty member(s) whose salary is closest to the average salary for that same rank, and return each matching member's rank, first name, last name, and _

```sql
SELECT
  FacNo,
  FacFirstName,
  FacLastName,
  FacRank,
  FacSalary
FROM
  university_faculty
```

---

**Skill `chunk_view_0_3`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `SalaryDataset` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute, for each of the four specified locations (Mumbai, Pune, New Delhi, Hyderabad), the top 5 companies by their average salary in that location after cleaning salary values to remove non-nu_

```sql
SELECT
  SalaryDataset.CompanyName,
  SalaryDataset.Location,
  SalaryDataset.Salary
FROM SalaryDataset
```

---
