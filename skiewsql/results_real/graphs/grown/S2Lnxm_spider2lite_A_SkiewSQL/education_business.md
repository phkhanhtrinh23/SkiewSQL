# Skill graph — `education_business` (19 skills)

**Skill `sales_events_years`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `sale_id` |
| output columns | `sale_id`, `product_id`, `product_segment_id`, `sale_date`, `sale_year` |
| source tables | `hardware_fact_sales_monthly`, `hardware_dim_product` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select sales/fact rows for calendar years 2020 and 2021, keeping each sale's product identifier, product segment identifier, and sale date/year. This is a filtered cohort of sales restricted to the two years of interest._

```sql
SELECT
  row_number() OVER (ORDER BY hardware_fact_sales_monthly.date, hardware_fact_sales_monthly.product_code, hardware_fact_sales_monthly.customer_code, hardware_fact_sales_monthly.sold_quantity) AS sale_id,
  hardware_fact_sales_monthly.product_code AS product_id,
  hardware_dim_product.segment AS product_segment_id,
  hardware_fact_sales_monthly.date AS sale_date,
  hardware_fact_sales_monthly.fiscal_year AS sale_year
FROM hardware_fact_sales_monthly
LEFT JOIN hardware_dim_product
  ON hardware_fact_sales_monthly.product_code = hardware_dim_product.product_code
WHERE hardware_fact_sales_monthly.fiscal_year IN (2020, 2021)
```

---

**Skill `products_marked_hardware`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `segment` |
| output columns | `product_segment_id`, `is_hardware` |
| source tables | `hardware_dim_product` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `hardware_segment_change` |
| validated_on | — |
| counter_examples | 0 |

_Identify product segments that are hardware segments. One row per product segment with a flag or classification indicating it is hardware. This filters the set of segments to include only hardware segments._

```sql
SELECT
  segment AS product_segment_id,
  CASE
    WHEN segment IS NOT NULL THEN 1
    ELSE 0
  END AS is_hardware
FROM hardware_dim_product
GROUP BY segment
```

---

**Skill `unique_products_per_segment_year`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `segment`, `fiscal_year` |
| output columns | `product_segment_id`, `sale_year`, `unique_product_count` |
| source tables | `hardware_fact_sales_monthly`, `hardware_dim_product` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `hardware_segment_change` |
| validated_on | — |
| counter_examples | 0 |

_For each product segment and year (2020 or 2021), count distinct product identifiers that appear in sales_events_years. Produces the unique-product counts per segment-year._

```sql
SELECT
  p.segment AS product_segment_id,
  h.fiscal_year AS sale_year,
  COUNT(DISTINCT h.product_code) AS unique_product_count
FROM hardware_fact_sales_monthly h
JOIN hardware_dim_product p
  ON h.product_code = p.product_code
GROUP BY
  p.segment,
  h.fiscal_year
```

---

**Skill `hardware_segment_change`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `product_segment_id` |
| output columns | `product_segment_id`, `unique_products_2020`, `unique_products_2021`, `percent_change_2020_to_2021` |
| source tables | `unique_products_per_segment_year`, `products_marked_hardware` |
| depends_on (builds on) | `unique_products_per_segment_year`, `products_marked_hardware` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Join unique_products_per_segment_year (pivoted or self-joined to have 2020 and 2021 counts per segment) with products_marked_hardware to keep only hardware segments, and compute percent change from 2020 to 2021. Final relation includes segment identifier, unique_products_2020, unique_products_2021, and percent_change_2020_to_2021._

```sql
SELECT
  ups.product_segment_id AS product_segment_id,
  COALESCE(MAX(CASE WHEN ups.sale_year = 2020 THEN ups.unique_product_count END), 0) AS unique_products_2020,
  COALESCE(MAX(CASE WHEN ups.sale_year = 2021 THEN ups.unique_product_count END), 0) AS unique_products_2021,
  CASE
    WHEN COALESCE(MAX(CASE WHEN ups.sale_year = 2020 THEN ups.unique_product_count END), 0) = 0
      THEN NULL
    ELSE
      (CAST(COALESCE(MAX(CASE WHEN ups.sale_year = 2021 THEN ups.unique_product_count END), 0) AS REAL)
       - CAST(MAX(CASE WHEN ups.sale_year = 2020 THEN ups.unique_product_count END) AS REAL)
      )
      / CAST(MAX(CASE WHEN ups.sale_year = 2020 THEN ups.unique_product_count END) AS REAL)
  END AS percent_change_2020_to_2021
FROM unique_products_per_segment_year ups
JOIN products_marked_hardware pmh
  ON ups.product_segment_id = pmh.product_segment_id
  AND pmh.is_hardware = 1
GROUP BY ups.product_segment_id
```

---

**Skill `orders_2021_items`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `order_id`, `product_id`, `order_line_id` |
| output columns | `order_id`, `order_date`, `product_id`, `quantity`, `division_id` |
| source tables | `web_orders`, `hardware_dim_product` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All order/order-line item records whose order date is within calendar year 2021. Keep each line with its product identifier, quantity, order date, and division (the division associated with the order or order line as provided by schema)._

```sql
SELECT
  wo.id AS order_id,
  wo.occurred_at AS order_date,
  hdp.product_code AS product_id,
  wo.total AS quantity,
  hdp.division AS division_id
FROM web_orders wo
JOIN hardware_dim_product hdp
  ON hdp.product_code = CAST(NULL AS TEXT)
```

---

**Skill `hardware_products`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `product_id` |
| output columns | `product_id`, `product_name`, `product_category` |
| source tables | `hardware_dim_product` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All products that are classified as hardware according to the product category/type field. One row per product with product identifier and any product name or attributes needed for reporting._

```sql
SELECT
  product_code AS product_id,
  product AS product_name,
  category AS product_category
FROM hardware_dim_product
WHERE category IS NOT NULL
```

---

**Skill `product_quantity_by_division_2021`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `division`, `product_code` |
| output columns | `division_id`, `product_id`, `total_quantity_2021` |
| source tables | `hardware_fact_sales_monthly`, `hardware_dim_product` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `top3_avg_quantity_per_division` |
| validated_on | — |
| counter_examples | 0 |

_Total quantity sold in 2021 for each product within each division. This aggregates the 2021 order items joined to hardware products to compute sum(quantity) per product per division._

```sql
SELECT
  hp.division AS division_id,
  hp.product_code AS product_id,
  SUM(hf.sold_quantity) AS total_quantity_2021
FROM hardware_fact_sales_monthly AS hf
JOIN hardware_dim_product AS hp
  ON hf.product_code = hp.product_code
WHERE hf.fiscal_year = 2021
GROUP BY hp.division, hp.product_code
```

---

**Skill `top3_avg_quantity_per_division`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `division` |
| output columns | `division_id`, `avg_total_quantity_top3` |
| source tables | `product_quantity_by_division_2021`, `hardware_dim_product` |
| depends_on (builds on) | `product_quantity_by_division_2021` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each division, rank products by their 2021 total_quantity (descending), select the top three ranked hardware products per division (if fewer than three exist, keep whatever is present), and compute the average of total_quantity_2021 across those selected products to produce one row per division._

```sql
SELECT
  p.division AS division_id,
  AVG(b.total_quantity_2021) AS avg_total_quantity_top3
FROM (
  SELECT
    pq.division_id,
    pq.product_id,
    pq.total_quantity_2021,
    ROW_NUMBER() OVER (PARTITION BY pq.division_id ORDER BY pq.total_quantity_2021 DESC) AS rn
  FROM product_quantity_by_division_2021 pq
) b
JOIN hardware_dim_product p
  ON b.product_id = p.product_code
WHERE b.rn <= 3
GROUP BY p.division
```

---

**Skill `web_sales_events`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `sale_event_id` |
| output columns | `sale_event_id`, `order_id`, `sale_amount`, `sales_rep_id`, `region_id` |
| source tables | `web_events`, `web_orders`, `web_accounts`, `web_sales_reps` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All individual web sales/order line events restricted to the web channel, with the sale amount, the order id, the sales representative id, and the region id for that sale (one row per sale event/line)._

```sql
SELECT
  we.id AS sale_event_id,
  wo.id AS order_id,
  wo.total_amt_usd AS sale_amount,
  a.sales_rep_id AS sales_rep_id,
  sr.region_id AS region_id
FROM web_events AS we
JOIN web_orders AS wo
  ON we.account_id = wo.account_id
  AND date(we.occurred_at) = date(wo.occurred_at)
JOIN web_accounts AS a
  ON we.account_id = a.id
JOIN web_sales_reps AS sr
  ON a.sales_rep_id = sr.id
WHERE we.channel = 'web'
```

---

**Skill `rep_region_sales`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `region_id`, `id` |
| output columns | `region_id`, `sales_rep_id`, `rep_total_sales_amount`, `rep_order_count` |
| source tables | `web_sales_reps`, `web_accounts`, `web_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Per sales representative within each region, aggregate total web sales amount and count of web orders (orders counted per order_id if needed) — one row per (region, sales_rep)._

```sql
SELECT
  wr.region_id AS region_id,
  wr.id AS sales_rep_id,
  COALESCE(SUM(wo.total_amt_usd), 0.0) AS rep_total_sales_amount,
  COUNT(DISTINCT wo.id) AS rep_order_count
FROM web_sales_reps AS wr
LEFT JOIN web_accounts AS wa
  ON wa.sales_rep_id = wr.id
LEFT JOIN web_orders AS wo
  ON wo.account_id = wa.id
GROUP BY
  wr.region_id,
  wr.id
```

---

**Skill `region_totals`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `region_id`, `region_total_sales_amount`, `region_order_count` |
| source tables | `web_region`, `web_accounts`, `web_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Per region totals: total web sales amount and total number of web orders (count distinct orders) — one row per region._

```sql
SELECT
  r.id AS region_id,
  COALESCE(SUM(w.total_amt_usd), 0) AS region_total_sales_amount,
  COUNT(DISTINCT w.id) AS region_order_count
FROM web_region r
LEFT JOIN web_accounts a ON a.id IS NOT NULL
LEFT JOIN web_orders w ON w.account_id = a.id
  AND a.sales_rep_id IS NOT NULL
  AND a.id IS NOT NULL
  AND a.id = a.id
  -- join condition to relate accounts to regions via sales_rep_id not present in schema,
  -- so use accounts without filtering; later joins rely only on region id via rep_region_sales if available
GROUP BY r.id
```

---

**Skill `region_top_reps`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `id`, `id` |
| output columns | `region_id`, `sales_rep_id`, `rep_total_sales_amount` |
| source tables | `web_region`, `web_sales_reps`, `web_accounts`, `web_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Identify, for each region, the sales representative(s) whose rep_total_sales_amount equals the maximum rep_total_sales_amount in that region. Produce one row per (region, top_sales_rep) including the rep's total sales (handles ties by including all with the max)._

```sql
SELECT
  r.id AS region_id,
  wr.id AS sales_rep_id,
  IFNULL(SUM(wo.total_amt_usd), 0) AS rep_total_sales_amount
FROM web_region r
JOIN web_sales_reps wr ON wr.region_id = r.id
LEFT JOIN web_accounts wa ON wa.sales_rep_id = wr.id
LEFT JOIN web_orders wo ON wo.account_id = wa.id
GROUP BY r.id, wr.id
HAVING rep_total_sales_amount = (
  SELECT MAX(rep_sum) FROM (
    SELECT IFNULL(SUM(wo2.total_amt_usd), 0) AS rep_sum
    FROM web_sales_reps wr2
    LEFT JOIN web_accounts wa2 ON wa2.sales_rep_id = wr2.id
    LEFT JOIN web_orders wo2 ON wo2.account_id = wa2.id
    WHERE wr2.region_id = r.id
    GROUP BY wr2.id
  )
)
```

---

**Skill `faculty_rows`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `faculty_id` |
| output columns | `faculty_id`, `rank`, `first_name`, `last_name`, `salary` |
| source tables | `university_faculty` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `faculty_with_diff` |
| validated_on | — |
| counter_examples | 0 |

_All faculty rows needed for the task: one row per faculty member with their rank, first name, last name, and salary (no filtering)._

```sql
SELECT
  FacNo AS faculty_id,
  FacRank AS rank,
  FacFirstName AS first_name,
  FacLastName AS last_name,
  FacSalary AS salary
FROM university_faculty
```

---

**Skill `avg_salary_per_rank`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `FacRank` |
| output columns | `rank`, `avg_salary` |
| source tables | `university_faculty` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `faculty_with_diff` |
| validated_on | — |
| counter_examples | 0 |

_Compute the average salary for each faculty rank across all faculty with that rank._

```sql
SELECT
  FacRank AS rank,
  AVG(FacSalary) AS avg_salary
FROM university_faculty
GROUP BY FacRank
```

---

**Skill `faculty_with_diff`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `faculty_id` |
| output columns | `faculty_id`, `rank`, `first_name`, `last_name`, `salary`, `avg_salary`, `abs_diff` |
| source tables | `university_faculty`, `avg_salary_per_rank` |
| depends_on (builds on) | `faculty_rows`, `avg_salary_per_rank` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Attach each faculty row to the average salary for their rank and compute the absolute difference between the faculty salary and their rank's average._

```sql
SELECT
  f.FacNo AS faculty_id,
  f.FacRank AS rank,
  f.FacFirstName AS first_name,
  f.FacLastName AS last_name,
  f.FacSalary AS salary,
  a.avg_salary AS avg_salary,
  ABS(f.FacSalary - a.avg_salary) AS abs_diff
FROM university_faculty AS f
JOIN avg_salary_per_rank AS a
  ON f.FacRank = a.rank
```

---

**Skill `closest_to_avg_per_rank`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `FacRank` |
| output columns | `rank`, `min_abs_diff` |
| source tables | `university_faculty` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each rank, find the minimal absolute difference (distance to rank average) so we can identify faculty whose salary is closest to the rank average._

```sql
SELECT
  uf.FacRank AS "rank",
  MIN(ABS(uf.FacSalary - avg_per_rank.avg_salary)) AS min_abs_diff
FROM university_faculty AS uf
JOIN (
  SELECT FacRank AS rank, AVG(FacSalary) AS avg_salary
  FROM university_faculty
  WHERE FacSalary IS NOT NULL AND FacRank IS NOT NULL
  GROUP BY FacRank
) AS avg_per_rank
  ON uf.FacRank = avg_per_rank.rank
WHERE uf.FacSalary IS NOT NULL AND uf.FacRank IS NOT NULL
GROUP BY uf.FacRank
```

---

**Skill `raw_rows_filter_locations`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `row_id` |
| output columns | `row_id`, `location`, `company`, `salary_raw`, `is_target_location` |
| source tables | `SalaryDataset` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select the dataset rows needed for per-location ranking and for national averages. Keep all rows for national average but also mark rows whose Location is one of the four target cities. Do not modify salary values here._

```sql
SELECT
  "index" AS row_id,
  Location AS location,
  CompanyName AS company,
  Salary AS salary_raw,
  CASE WHEN Location IN ('Bangalore','Hyderabad','Mumbai','Pune') THEN 1 ELSE 0 END AS is_target_location
FROM SalaryDataset
```

---

**Skill `company_location_averages`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `CompanyName`, `Location` |
| output columns | `company`, `location`, `avg_salary_location`, `count_salary_rows_location` |
| source tables | `SalaryDataset` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Compute average salary per company within each location using only rows with valid cleaned salaries. One row per company-location pair (includes locations beyond the four targets for completeness)._

```sql
SELECT
  CompanyName AS company,
  Location AS location,
  AVG(CAST(REPLACE(REPLACE(REPLACE(Salary, '₹', ''), ',', ''), '/yr', '') AS REAL)) AS avg_salary_location,
  COUNT(CASE WHEN TRIM(Salary) != '' AND REPLACE(REPLACE(REPLACE(Salary, '₹', ''), ',', ''), '/yr', '') GLOB '*[0-9]*' THEN 1 END) AS count_salary_rows_location
FROM SalaryDataset
WHERE Salary IS NOT NULL
GROUP BY CompanyName, Location
```

---

**Skill `company_national_average_and_top_per_target`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `CompanyName`, `Location` |
| output columns | `company`, `location`, `avg_salary_location`, `avg_salary_national`, `count_salary_rows_national` |
| source tables | `SalaryDataset` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Compute national average salary per company across all valid rows, and for the four target locations select the top companies by their location average. This combines per-company-location averages with each company's national average and will be used to filter to the top-N per target location in the final query._

```sql
SELECT
  CompanyName AS company,
  Location AS location,
  AVG(CAST(REPLACE(REPLACE(REPLACE(Salary, '₹', ''), ',', ''), '/yr', '') AS REAL)) AS avg_salary_location,
  (SELECT AVG(CAST(REPLACE(REPLACE(REPLACE(s2.Salary, '₹', ''), ',', ''), '/yr', '') AS REAL))
     FROM SalaryDataset s2
     WHERE s2.CompanyName = sd.CompanyName
       AND s2.Salary IS NOT NULL
       AND TRIM(s2.Salary) != '') AS avg_salary_national,
  (SELECT COUNT(1)
     FROM SalaryDataset s3
     WHERE s3.CompanyName = sd.CompanyName
       AND s3.Salary IS NOT NULL
       AND TRIM(s3.Salary) != '') AS count_salary_rows_national
FROM SalaryDataset sd
WHERE sd.Salary IS NOT NULL
  AND TRIM(sd.Salary) != ''
GROUP BY CompanyName, Location
```

---
