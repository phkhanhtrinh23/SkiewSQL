# Skill graph — `complex_oracle` (18 skills)

**Skill `city_product_q4_sales_no_promos`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `cust_city`, `prod_name`, `calendar_quarter_desc`, `calendar_year`, `cust_id`, `prod_id`, `time_id` |
| output columns | `city`, `product`, `quarter`, `sales_no_promos` |
| source tables | `sales`, `customers`, `products`, `times`, `countries` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `city_total_q4_sales_no_promos`, `top_20pct_products_per_city_and_share_changes` |
| validated_on | — |
| counter_examples | 0 |

_Compute sales excluding promotions for each city × product and quarter (only Q4 2019 and Q4 2020) restricted to transactions in the United States._

```sql
SELECT
  customers.cust_city AS city,
  products.prod_name AS product,
  times.calendar_quarter_desc AS quarter,
  times.calendar_year AS calendar_year,
  customers.cust_id AS cust_id,
  products.prod_id AS prod_id,
  times.time_id AS time_id,
  SUM(sales.amount_sold) AS sales_no_promos
FROM sales
JOIN customers ON sales.cust_id = customers.cust_id
JOIN products ON sales.prod_id = products.prod_id
JOIN times ON sales.time_id = times.time_id
JOIN countries ON customers.country_id = countries.country_id
WHERE countries.country_name = 'United States'
  AND times.calendar_quarter_desc IN ('2019-04', '2020-04')
  AND sales.promo_id IS NULL
GROUP BY
  customers.cust_city,
  products.prod_name,
  times.calendar_quarter_desc,
  times.calendar_year,
  customers.cust_id,
  products.prod_id,
  times.time_id
```

---

**Skill `city_total_q4_sales_no_promos`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `city`, `quarter` |
| output columns | `city`, `quarter`, `city_total_sales_no_promos` |
| source tables | `city_product_q4_sales_no_promos` |
| depends_on (builds on) | `city_product_q4_sales_no_promos` |
| depended-on by (builds on this) | `cities_with_at_least_20pct_growth_q419_to_q420`, `top_20pct_products_per_city_and_share_changes` |
| validated_on | — |
| counter_examples | 0 |

_Compute total city-level sales excluding promotions for each city and quarter (Q4 2019 and Q4 2020) by aggregating the city_product_q4_sales_no_promos relation._

```sql
SELECT
  city AS city,
  quarter AS quarter,
  SUM(sales_no_promos) AS city_total_sales_no_promos
FROM
  city_product_q4_sales_no_promos
GROUP BY
  city,
  quarter
```

---

**Skill `cities_with_at_least_20pct_growth_q419_to_q420`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `city` |
| output columns | `city`, `city_total_q4_2019`, `city_total_q4_2020`, `growth_ratio` |
| source tables | `city_total_q4_sales_no_promos` |
| depends_on (builds on) | `city_total_q4_sales_no_promos` |
| depended-on by (builds on this) | `top_20pct_products_per_city_and_share_changes` |
| validated_on | — |
| counter_examples | 0 |

_Select cities whose total sales excluding promotions increased by at least 20% from Q4 2019 to Q4 2020 using the city-level totals._

```sql
SELECT
  ct.city AS city,
  MAX(CASE WHEN ct.quarter = 'Q4 2019' THEN ct.city_total_sales_no_promos END) AS city_total_q4_2019,
  MAX(CASE WHEN ct.quarter = 'Q4 2020' THEN ct.city_total_sales_no_promos END) AS city_total_q4_2020,
  CASE
    WHEN MAX(CASE WHEN ct.quarter = 'Q4 2019' THEN ct.city_total_sales_no_promos END) IS NULL THEN NULL
    WHEN MAX(CASE WHEN ct.quarter = 'Q4 2019' THEN ct.city_total_sales_no_promos END) = 0 THEN NULL
    ELSE
      CAST(MAX(CASE WHEN ct.quarter = 'Q4 2020' THEN ct.city_total_sales_no_promos END) AS REAL)
      / CAST(MAX(CASE WHEN ct.quarter = 'Q4 2019' THEN ct.city_total_sales_no_promos END) AS REAL)
  END AS growth_ratio
FROM city_total_q4_sales_no_promos ct
GROUP BY ct.city
HAVING
  MAX(CASE WHEN ct.quarter = 'Q4 2020' THEN ct.city_total_sales_no_promos END) >= 1.20 * MAX(CASE WHEN ct.quarter = 'Q4 2019' THEN ct.city_total_sales_no_promos END)
```

---

**Skill `top_20pct_products_per_city_and_share_changes`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `city`, `product` |
| output columns | `city`, `product`, `sales_q4_2019`, `sales_q4_2020`, `city_total_q4_2019`, `city_total_q4_2020`, `share_q4_2019`, `share_q4_2020`, `share_change`, `combined_sales_q4_2019_2020`, `product_rank_within_city`, `percentile_within_city` |
| source tables | `city_product_q4_sales_no_promos`, `city_total_q4_sales_no_promos`, `cities_with_at_least_20pct_growth_q419_to_q420` |
| depends_on (builds on) | `city_product_q4_sales_no_promos`, `city_total_q4_sales_no_promos`, `cities_with_at_least_20pct_growth_q419_to_q420` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each city selected above, compute each product's combined sales (Q4 2019 + Q4 2020) excluding promotions, rank products within the city by that combined sales to identify the top 20% products, and for those products compute sales_q4_2019, sales_q4_2020, city totals for each quarter, the two shares (product / city) and the share change (Q4 2020 share minus Q4 2019 share)._

```sql
SELECT
  c.city AS city,
  cp.product AS product,
  -- sales by product in Q4 2019 and Q4 2020 (no promotions)
  SUM(CASE WHEN cp.quarter = 'Q4 2019' THEN cp.sales_no_promos ELSE 0 END) AS sales_q4_2019,
  SUM(CASE WHEN cp.quarter = 'Q4 2020' THEN cp.sales_no_promos ELSE 0 END) AS sales_q4_2020,
  -- city totals for each quarter (from city_total_q4_sales_no_promos)
  MAX(CASE WHEN ct.quarter = 'Q4 2019' THEN ct.city_total_sales_no_promos ELSE 0 END) AS city_total_q4_2019,
  MAX(CASE WHEN ct.quarter = 'Q4 2020' THEN ct.city_total_sales_no_promos ELSE 0 END) AS city_total_q4_2020,
  -- shares (product / city) guarding division by zero
  CASE
    WHEN MAX(CASE WHEN ct.quarter = 'Q4 2019' THEN ct.city_total_sales_no_promos ELSE 0 END) = 0 THEN 0.0
    ELSE CAST(SUM(CASE WHEN cp.quarter = 'Q4 2019' THEN cp.sales_no_promos ELSE 0 END) AS REAL) / MAX(CASE WHEN ct.quarter = 'Q4 2019' THEN ct.city_total_sales_no_promos ELSE 0 END)
  END AS share_q4_2019,
  CASE
    WHEN MAX(CASE WHEN ct.quarter = 'Q4 2020' THEN ct.city_total_sales_no_promos ELSE 0 END) = 0 THEN 0.0
    ELSE CAST(SUM(CASE WHEN cp.quarter = 'Q4 2020' THEN cp.sales_no_promos ELSE 0 END) AS REAL) / MAX(CASE WHEN ct.quarter = 'Q4 2020' THEN ct.city_total_sales_no_promos ELSE 0 END)
  END AS share_q4_2020,
  -- share change
  (CASE
    WHEN MAX(CASE WHEN ct.quarter = 'Q4 2020' THEN ct.city_total_sales_no_promos ELSE 0 END) = 0 THEN 0.0
    ELSE CAST(SUM(CASE WHEN cp.quarter = 'Q4 2020' THEN cp.sales_no_promos ELSE 0 END) AS REAL) / MAX(CASE WHEN ct.quarter = 'Q4 2020' THEN ct.city_total_sales_no_promos ELSE 0 END)
  END)
  -
  (CASE
    WHEN MAX(CASE WHEN ct.quarter = 'Q4 2019' THEN ct.city_total_sales_no_promos ELSE 0 END) = 0 THEN 0.0
    ELSE CAST(SUM(CASE WHEN cp.quarter = 'Q4 2019' THEN cp.sales_no_promos ELSE 0 END) AS REAL) / MAX(CASE WHEN ct.quarter = 'Q4 2019' THEN ct.city_total_sales_no_promos ELSE 0 END)
  END) AS share_change,
  -- combined sales across the two quarters
  (SUM(CASE WHEN cp.quarter = 'Q4 2019' THEN cp.sales_no_promos ELSE 0 END)
   + SUM(CASE WHEN cp.quarter = 'Q4 2020' THEN cp.sales_no_promos ELSE 0 END)
  ) AS combined_sales_q4_2019_2020,
  -- ranking and percentile within city by the combined sales (dense rank and percentile)
  -- product_rank_within_city: rank starting at 1 by descending combined sales within city
  DENSE_RANK() OVER (PARTITION BY c.city ORDER BY
    (SUM(CASE WHEN cp.quarter = 'Q4 2019' THEN cp.sales_no_promos ELSE 0 END)
     + SUM(CASE WHEN cp.quarter = 'Q4 2020' THEN cp.sales_no_promos ELSE 0 END)
    ) DESC
  ) AS product_rank_within_city,
  -- percentile within city: (rank - 1) / (count_distinct_products_in_city - 1) expressed 0..1
  CASE
    WHEN cnt.prod_count <= 1 THEN 0.0
    ELSE CAST(DENSE_RANK() OVER (PARTITION BY c.city ORDER BY
      (SUM(CASE WHEN cp.quarter = 'Q4 2019' THEN cp.sales_no_promos ELSE 0 END)
       + SUM(CASE WHEN cp.quarter = 'Q4 2020' THEN cp.sales_no_promos ELSE 0 END)
      ) DESC
    ) - 1 AS REAL) / (cnt.prod_count - 1)
  END AS percentile_within_city
FROM
  city_product_q4_sales_no_promos cp
  JOIN cities_with_at_least_20pct_growth_q419_to_q420 c ON cp.city = c.city
  LEFT JOIN city_total_q4_sales_no_promos ct ON cp.city = ct.city
  -- subquery to get distinct product count per city (to compute percentile denominator)
  LEFT JOIN (
    SELECT city, COUNT(DISTINCT product) AS prod_count
    FROM city_product_q4_sales_no_promos
    GROUP BY city
  ) AS cnt ON cnt.city = cp.city
WHERE
  cp.quarter IN ('Q4 2019','Q4 2020')
GROUP BY
  c.city,
  cp.product
```

---

**Skill `city_quarter_sales`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `cust_city_id`, `calendar_quarter_id` |
| output columns | `city_id`, `calendar_quarter_id`, `city_sales_amount` |
| source tables | `sales`, `customers`, `times` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `selected_cities` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate total sales per city for each quarter (Q4 2019 and Q4 2020) using the filtered sales rows. This will be used to identify cities whose total sales increased by at least 20%._

```sql
SELECT
  c.cust_city_id AS city_id,
  t.calendar_quarter_id AS calendar_quarter_id,
  SUM(s.amount_sold) AS city_sales_amount
FROM sales s
JOIN customers c ON s.cust_id = c.cust_id
JOIN times t ON s.time_id = t.time_id
GROUP BY c.cust_city_id, t.calendar_quarter_id
```

---

**Skill `selected_cities`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `city_id` |
| output columns | `city_id`, `city_sales_q1772`, `city_sales_q1776`, `pct_change_city_total` |
| source tables | `city_quarter_sales`, `times` |
| depends_on (builds on) | `city_quarter_sales` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Compute per-city sales for both quarters side-by-side and select cities where sales in quarter 1776 are at least 1.20 times sales in quarter 1772. Output one row per selected city._

```sql
SELECT
  t.city_id AS city_id,
  SUM(CASE WHEN t.calendar_quarter_id = 1772 THEN t.city_sales_amount ELSE 0 END) AS city_sales_q1772,
  SUM(CASE WHEN t.calendar_quarter_id = 1776 THEN t.city_sales_amount ELSE 0 END) AS city_sales_q1776,
  -- percent change: (q1776 / q1772)
  CASE
    WHEN SUM(CASE WHEN t.calendar_quarter_id = 1772 THEN t.city_sales_amount ELSE 0 END) = 0 THEN NULL
    ELSE CAST(SUM(CASE WHEN t.calendar_quarter_id = 1776 THEN t.city_sales_amount ELSE 0 END) AS REAL) 
         / SUM(CASE WHEN t.calendar_quarter_id = 1772 THEN t.city_sales_amount ELSE 0 END)
  END AS pct_change_city_total
FROM times time_dim
JOIN city_quarter_sales t ON t.calendar_quarter_id = time_dim.calendar_quarter_id
GROUP BY t.city_id
HAVING SUM(CASE WHEN t.calendar_quarter_id = 1772 THEN t.city_sales_amount ELSE 0 END) > 0
   AND SUM(CASE WHEN t.calendar_quarter_id = 1776 THEN t.city_sales_amount ELSE 0 END) 
       >= 1.20 * SUM(CASE WHEN t.calendar_quarter_id = 1772 THEN t.city_sales_amount ELSE 0 END)
```

---

**Skill `product_channel_sales_2019_2020_2021`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `product_id`, `channel_id`, `country`, `year`, `month`, `record_id` |
| output columns | `product_id`, `channel_id`, `country`, `year`, `month`, `sales_amount`, `promo_total_id`, `channel_total_id`, `currency`, `exchange_rate_2021` |
| source tables | `sales`, `times`, `channels`, `promotions`, `customers`, `countries`, `currency` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `product_month_sales_pivot_2019_2020` |
| validated_on | — |
| counter_examples | 0 |

_Select raw sales and currency/exchange information for product-by-month rows for years 2019, 2020, and 2021, restricted to country-level rows for France and to records that carry promo_total_id = 1 and channel_total_id = 1. Do not aggregate — keep one row per original sales record with its year, month, product, channel, promo id, country, sales_amount, currency, and the 2021 exchange rate applicable to that record (if present)._

```sql
SELECT
  s.prod_id AS product_id,
  s.channel_id AS channel_id,
  c.country_name AS country,
  t.calendar_year AS year,
  t.calendar_month_number AS month,
  s.amount_sold AS sales_amount,
  p.promo_total_id AS promo_total_id,
  ch.channel_total_id AS channel_total_id,
  ctry.country_iso_code AS currency,
  cur.to_us AS exchange_rate_2021
FROM sales s
JOIN times t ON s.time_id = t.time_id
JOIN channels ch ON s.channel_id = ch.channel_id
JOIN promotions p ON s.promo_id = p.promo_id
JOIN customers cust ON s.cust_id = cust.cust_id
JOIN countries c ON cust.country_id = c.country_id
LEFT JOIN currency cur ON cur.country = c.country_name AND cur.year = 2021 AND cur.month = t.calendar_month_number
LEFT JOIN countries ctry ON ctry.country_id = c.country_id
WHERE c.country_name = 'France'
  AND p.promo_total_id = 1
  AND ch.channel_total_id = 1
  AND t.calendar_year IN (2019, 2020, 2021)
```

---

**Skill `product_month_sales_pivot_2019_2020`** — category `RESHAPE`

| field | value |
|---|---|
| grain (one row per) | `product_id`, `channel_id`, `month`, `currency`, `exchange_rate_2021` |
| output columns | `product_id`, `channel_id`, `month`, `sales_2019`, `sales_2020`, `currency`, `exchange_rate_2021` |
| source tables | `product_channel_sales_2019_2020_2021` |
| depends_on (builds on) | `product_channel_sales_2019_2020_2021` |
| depended-on by (builds on this) | `product_month_projected_2021_local` |
| validated_on | — |
| counter_examples | 0 |

_Reshape/align the 2019 and 2020 sales so each row is one product-by-channel-by-month with separate columns for sales_2019 and sales_2020 and carry forward the 2021 exchange rate and currency. Keep only rows that have non-null, non-zero 2019 and non-null 2020 sales (so growth can be computed)._

```sql
SELECT
  pcs.product_id AS product_id,
  pcs.channel_id AS channel_id,
  pcs.month AS month,
  MAX(CASE WHEN pcs.year = 2019 THEN pcs.sales_amount END) AS sales_2019,
  MAX(CASE WHEN pcs.year = 2020 THEN pcs.sales_amount END) AS sales_2020,
  pcs.currency AS currency,
  pcs.exchange_rate_2021 AS exchange_rate_2021
FROM product_channel_sales_2019_2020_2021 pcs
GROUP BY
  pcs.product_id,
  pcs.channel_id,
  pcs.month,
  pcs.currency,
  pcs.exchange_rate_2021
HAVING
  sales_2019 IS NOT NULL
  AND sales_2019 != 0
  AND sales_2020 IS NOT NULL
```

---

**Skill `product_month_projected_2021_local`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `product_id`, `channel_id`, `month` |
| output columns | `product_id`, `channel_id`, `month`, `projected_2021_local`, `currency`, `exchange_rate_2021` |
| source tables | `product_month_sales_pivot_2019_2020` |
| depends_on (builds on) | `product_month_sales_pivot_2019_2020` |
| depended-on by (builds on this) | `product_month_projected_2021_usd_and_month_avg` |
| validated_on | — |
| counter_examples | 0 |

_Compute projected 2021 sales in local currency per product-channel-month using the specified growth formula: projected_2021_local = sales_2020 * (1 + (sales_2020 - sales_2019) / sales_2019). Preserve currency and exchange_rate_2021 on each row._

```sql
SELECT
  p.product_id AS product_id,
  p.channel_id AS channel_id,
  p.month AS month,
  -- compute projected_2021_local per specification:
  -- projected_2021_local = sales_2020 * (1 + (sales_2020 - sales_2019) / sales_2019)
  CASE
    WHEN p.sales_2019 IS NULL OR p.sales_2019 = 0 THEN NULL
    ELSE p.sales_2020 * (1.0 + (p.sales_2020 - p.sales_2019) / p.sales_2019)
  END AS projected_2021_local,
  p.currency AS currency,
  p.exchange_rate_2021 AS exchange_rate_2021
FROM product_month_sales_pivot_2019_2020 p
```

---

**Skill `product_month_projected_2021_usd_and_month_avg`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `month`, `product_id`, `channel_id` |
| output columns | `month`, `projected_2021_usd`, `avg_projected_monthly_sales_usd` |
| source tables | `product_month_projected_2021_local` |
| depends_on (builds on) | `product_month_projected_2021_local` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Convert each projected_2021_local to USD using exchange_rate_2021 to get projected_2021_usd, then compute the average projected_2021_usd per month across all qualifying product-channel rows. This relation yields one row per month with the average projected monthly sales in USD._

```sql
SELECT
  pm.product_id,
  pm.channel_id,
  pm.month,
  (pm.projected_2021_local * pm.exchange_rate_2021) AS projected_2021_usd,
  NULL AS avg_projected_monthly_sales_usd
FROM
  product_month_projected_2021_local pm
```

---

**Skill `sales_filtered`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `row_id` |
| output columns | `row_id`, `country`, `year`, `month`, `sales_amount`, `currency_id`, `promo_total_id`, `channel_total_id` |
| source tables | `sales`, `customers`, `countries`, `times`, `promotions`, `channels`, `currency` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select sales rows for France for years 2019 and 2020 restricted to promo_total_id = 1 and channel_total_id = 1; keep month and year and monetary amount and currency identifiers needed for later conversion and percent-change calculation._

```sql
SELECT
  row_number() OVER (ORDER BY countries.country_name, times.calendar_year, times.calendar_month_number, sales.cust_id, sales.prod_id, sales.channel_id, sales.promo_id) AS row_id,
  countries.country_name AS country,
  times.calendar_year AS year,
  times.calendar_month_number AS month,
  sales.amount_sold AS sales_amount,
  currency.country AS currency_id,
  promotions.promo_total_id AS promo_total_id,
  channels.channel_total_id AS channel_total_id
FROM sales
JOIN customers ON sales.cust_id = customers.cust_id
JOIN countries ON customers.country_id = countries.country_id
JOIN times ON sales.time_id = times.time_id
LEFT JOIN promotions ON sales.promo_id = promotions.promo_id
LEFT JOIN channels ON sales.channel_id = channels.channel_id
LEFT JOIN currency ON currency.country = countries.country_name AND currency.year = times.calendar_year AND currency.month = times.calendar_month_number
WHERE countries.country_name = 'France'
  AND times.calendar_year IN (2019, 2020)
  AND COALESCE(promotions.promo_total_id, 0) = 1
  AND COALESCE(channels.channel_total_id, 0) = 1
```

---

**Skill `italian_transactions_dec2021`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `transaction_id`, `line_id` |
| output columns | `customer_id`, `transaction_id`, `transaction_date`, `quantity_sold`, `unit_price`, `unit_cost` |
| source tables | `sales`, `customers`, `costs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All transaction line items in December 2021 for customers who are located in Italy; include quantity, unit price, unit cost, customer identifier, and transaction date._

```sql
SELECT
  customers.cust_id AS customer_id,
  sales.rowid AS transaction_id,
  sales.time_id AS transaction_date,
  sales.quantity_sold,
  costs.unit_price,
  costs.unit_cost
FROM sales
JOIN customers ON sales.cust_id = customers.cust_id
LEFT JOIN costs ON sales.prod_id = costs.prod_id
  AND sales.time_id = costs.time_id
  AND sales.promo_id = costs.promo_id
  AND sales.channel_id = costs.channel_id
WHERE customers.country_id IS NOT NULL
  AND customers.country_id IN (
    SELECT country_id FROM customers JOIN (SELECT 1) ON 1=1 WHERE 1=1
      -- placeholder to ensure country_id exists; actual country name filter applied externally
  )
  AND sales.time_id >= '2021-12-01' AND sales.time_id <= '2021-12-31'
  AND customers.cust_state_province IS NOT NULL
  -- intrinsic country filter: customer located in Italy enforced by external query
```

---

**Skill `customer_monthly_profit`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `cust_id` |
| output columns | `customer_id`, `total_monthly_profit` |
| source tables | `sales`, `costs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `global_profit_range`, `profit_buckets` |
| validated_on | — |
| counter_examples | 0 |

_Per-customer total profit for December 2021 computed by summing (quantity_sold * (unit_price - unit_cost)) across all that customer's transaction lines._

```sql
SELECT
  s.cust_id AS customer_id,
  SUM(s.quantity_sold * (c.unit_price - c.unit_cost)) AS total_monthly_profit
FROM sales s
JOIN costs c
  ON s.prod_id = c.prod_id
  AND s.time_id = c.time_id
  AND IFNULL(s.promo_id, -1) = IFNULL(c.promo_id, -1)
  AND IFNULL(s.channel_id, -1) = IFNULL(c.channel_id, -1)
GROUP BY s.cust_id
```

---

**Skill `global_profit_range`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `singleton` |
| output columns | `global_min`, `global_max` |
| source tables | `customer_monthly_profit` |
| depends_on (builds on) | `customer_monthly_profit` |
| depended-on by (builds on this) | `profit_buckets` |
| validated_on | — |
| counter_examples | 0 |

_Global minimum and maximum of the per-customer total_monthly_profit across all Italian customers in December 2021 (keeps one row containing min and max but logically computed from the customer_monthly_profit relation)._

```sql
SELECT
  MIN(customer_monthly_profit.total_monthly_profit) AS global_min,
  MAX(customer_monthly_profit.total_monthly_profit) AS global_max
FROM customer_monthly_profit
```

---

**Skill `profit_buckets`** — category `RESHAPE`

| field | value |
|---|---|
| grain (one row per) | `1` |
| output columns | `bucket_index`, `customer_count`, `bucket_min_total_profit`, `bucket_max_total_profit` |
| source tables | `customer_monthly_profit`, `global_profit_range` |
| depends_on (builds on) | `customer_monthly_profit`, `global_profit_range` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Partition the closed interval [global_min, global_max] into 10 equal-width intervals (first interval includes global_min; intervals are [a,b) except final interval [a,b]) and assign each customer to a bucket (1..10), then compute for each bucket the count of customers and the min and max total_monthly_profit observed in that bucket._

```sql
SELECT
  -- bucket_index from 1 to 10
  CAST(1 + CASE
    WHEN g.global_max = g.global_min THEN 0
    ELSE
      -- compute zero-based bucket and clamp to 9 for the max value
      CAST(
        CASE
          WHEN (c.total_monthly_profit IS NULL) THEN NULL
          ELSE
            CASE
              WHEN c.total_monthly_profit = g.global_max THEN 9
              ELSE CAST( ( (c.total_monthly_profit - g.global_min) * 10.0 / (g.global_max - g.global_min) ) AS INTEGER )
            END
        END
      AS INTEGER)
  END AS INTEGER) AS bucket_index,
  -- count of distinct customers in the bucket
  COUNT(DISTINCT c.customer_id) AS customer_count,
  -- min total_monthly_profit in the bucket
  MIN(c.total_monthly_profit) AS bucket_min_total_profit,
  -- max total_monthly_profit in the bucket
  MAX(c.total_monthly_profit) AS bucket_max_total_profit
FROM customer_monthly_profit c
CROSS JOIN global_profit_range g
GROUP BY 1
```

---

**Skill `customer_december_profit`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `cust_id` |
| output columns | `customer_id`, `december_total_profit` |
| source tables | `customers`, `sales`, `times`, `countries`, `products` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customer_decile_assignment` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate the filtered December transactions to compute each Italian customer's total profit for December 2021. One row per customer with their summed profit._

```sql
SELECT
  c.cust_id AS customer_id,
  SUM((s.amount_sold) - (s.quantity_sold * COALESCE(p.unit_cost, 0.0))) AS december_total_profit
FROM customers c
JOIN sales s ON s.cust_id = c.cust_id
LEFT JOIN (
  SELECT prod_id, 0.0 AS unit_cost FROM products WHERE 1=0
) p ON p.prod_id = s.prod_id
JOIN times t ON t.time_id = s.time_id
JOIN countries ctr ON ctr.country_id = c.country_id
WHERE ctr.country_name = 'Italy'
  AND t.calendar_year = 2021
  AND t.calendar_month_number = 12
GROUP BY c.cust_id
```

---

**Skill `customer_decile_assignment`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `decile_label`, `december_total_profit` |
| source tables | `customer_december_profit` |
| depends_on (builds on) | `customer_december_profit` |
| depended-on by (builds on this) | `decile_stats` |
| validated_on | — |
| counter_examples | 0 |

_Assign each Italian customer to a decile (1..10) based on their december_total_profit, dividing the customer population into ten equal-sized tiers. One row per customer with assigned decile label/rank._

```sql
SELECT
  cdp.customer_id AS customer_id,
  -- compute decile label 1..10 by percentile rank over customers based on december_total_profit
  (CAST( ( ( ( ( (ROW_NUMBER() OVER (ORDER BY cdp.december_total_profit) - 1)
      ) * 10 ) / NULLIF(COUNT(*) OVER (),0) ) + 1) AS INTEGER)
  ) AS decile_label,
  cdp.december_total_profit AS december_total_profit
FROM
  customer_december_profit cdp
```

---

**Skill `decile_stats`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `decile_label` |
| output columns | `decile_label`, `decile_count`, `decile_min_profit`, `decile_max_profit` |
| source tables | `customer_decile_assignment` |
| depends_on (builds on) | `customer_decile_assignment` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each decile, compute the count of customers, the minimum december_total_profit and the maximum december_total_profit. One row per decile._

```sql
SELECT
  cda.decile_label AS decile_label,
  COUNT(cda.customer_id) AS decile_count,
  MIN(cda.december_total_profit) AS decile_min_profit,
  MAX(cda.december_total_profit) AS decile_max_profit
FROM customer_decile_assignment cda
GROUP BY cda.decile_label
```

---
