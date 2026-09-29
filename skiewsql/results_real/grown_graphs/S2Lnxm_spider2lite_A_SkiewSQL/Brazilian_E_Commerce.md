# Skill graph — `Brazilian_E_Commerce` (30 skills)

**Skill `delivered_orders_cohort`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `order_id` |
| output columns | `order_id`, `delivery_date` |
| source tables | `olist_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `delivery_date_parts` |
| validated_on | — |
| counter_examples | 0 |

_Select orders whose delivery/delivered date is present and falls in the years 2016, 2017, or 2018. Keep the order identifier and the delivery date (full date/time) for downstream month/year extraction._

```sql
SELECT
  order_id,
  order_delivered_customer_date AS delivery_date
FROM
  olist_orders
WHERE
  order_delivered_customer_date IS NOT NULL
  AND (substr(order_delivered_customer_date,1,4) = '2016'
       OR substr(order_delivered_customer_date,1,4) = '2017'
       OR substr(order_delivered_customer_date,1,4) = '2018')
```

---

**Skill `delivery_date_parts`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `order_id` |
| output columns | `order_id`, `delivery_date`, `delivery_year`, `delivery_month_number` |
| source tables | `delivered_orders_cohort` |
| depends_on (builds on) | `delivered_orders_cohort` |
| depended-on by (builds on this) | `monthly_yearly_counts` |
| validated_on | — |
| counter_examples | 0 |

_Project calendar parts from each order's delivery_date: delivery_year and delivery_month_number (1-12). Cast/normalize month to integer and year to integer. Keep one row per order._

```sql
SELECT
  d.order_id AS order_id,
  d.delivery_date AS delivery_date,
  CAST(strftime('%Y', d.delivery_date) AS INTEGER) AS delivery_year,
  CAST(strftime('%m', d.delivery_date) AS INTEGER) AS delivery_month_number
FROM delivered_orders_cohort d
```

---

**Skill `monthly_yearly_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `delivery_year`, `delivery_month_number` |
| output columns | `delivery_month_number`, `delivery_year`, `delivered_order_count` |
| source tables | `delivery_date_parts` |
| depends_on (builds on) | `delivery_date_parts` |
| depended-on by (builds on this) | `months_pivoted_report` |
| validated_on | — |
| counter_examples | 0 |

_Count delivered orders grouped by delivery_month_number and delivery_year. Produce one row per month-year combination that exists in the cohort with the count of orders delivered in that month-year._

```sql
SELECT
  ddp.delivery_month_number AS delivery_month_number,
  ddp.delivery_year AS delivery_year,
  COUNT(ddp.order_id) AS delivered_order_count
FROM delivery_date_parts ddp
GROUP BY
  ddp.delivery_year,
  ddp.delivery_month_number
```

---

**Skill `months_pivoted_report`** — category `RESHAPE`

| field | value |
|---|---|
| grain (one row per) | `delivery_month_number` |
| output columns | `delivery_month_number`, `month_name_or_number`, `delivered_orders_2016`, `delivered_orders_2017`, `delivered_orders_2018` |
| source tables | `monthly_yearly_counts` |
| depends_on (builds on) | `monthly_yearly_counts` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Reshape/pivot the month-year counts into one row per calendar month (1..12) with separate columns for delivered_orders_2016, delivered_orders_2017, delivered_orders_2018. Ensure months with zero counts for a year appear with zero. Include month name or number and order rows January through December._

```sql
SELECT
  m.delivery_month_number AS delivery_month_number,
  m.delivery_month_number AS month_name_or_number,
  COALESCE(SUM(CASE WHEN m.delivery_year = 2016 THEN m.delivered_order_count END), 0) AS delivered_orders_2016,
  COALESCE(SUM(CASE WHEN m.delivery_year = 2017 THEN m.delivered_order_count END), 0) AS delivered_orders_2017,
  COALESCE(SUM(CASE WHEN m.delivery_year = 2018 THEN m.delivered_order_count END), 0) AS delivered_orders_2018
FROM
  monthly_yearly_counts AS m
GROUP BY
  m.delivery_month_number
```

---

**Skill `delivered_events_filtered_years`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `order_event` |
| output columns | `order_date`, `year`, `month`, `delivered_orders_volume` |
| source tables | `olist_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select all records representing delivered orders within the calendar years 2016, 2017, and 2018. Keep the date (or year and month) and the delivered_orders_volume value for each record; exclude any non-delivered statuses._

```sql
SELECT
  order_id,
  order_delivered_customer_date AS order_date,
  CAST(strftime('%Y', order_delivered_customer_date) AS INTEGER) AS year,
  CAST(strftime('%m', order_delivered_customer_date) AS INTEGER) AS month,
  1 AS delivered_orders_volume
FROM olist_orders
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL
  AND CAST(strftime('%Y', order_delivered_customer_date) AS INTEGER) IN (2016, 2017, 2018)
```

---

**Skill `monthly_delivered_volume`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `year`, `month` |
| output columns | `year`, `month`, `monthly_delivered_volume` |
| source tables | `olist_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `select_lowest_year_and_its_top_month` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate delivered orders volume to compute total delivered volume for each year-month combination (i.e., sum delivered_orders_volume per year and month)._

```sql
SELECT
  CAST(strftime('%Y', order_delivered_customer_date) AS INTEGER) AS year,
  CAST(strftime('%m', order_delivered_customer_date) AS INTEGER) AS month,
  COUNT(order_id) AS monthly_delivered_volume
FROM olist_orders
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL
GROUP BY year, month
```

---

**Skill `annual_delivered_volume`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `year` |
| output columns | `year`, `annual_delivered_volume` |
| source tables | `olist_orders`, `olist_order_items` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `select_lowest_year_and_its_top_month` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate delivered orders volume to compute total delivered volume per year by summing all delivered_orders_volume for each year (using the filtered records)._

```sql
SELECT
  CAST(strftime('%Y', o.order_delivered_customer_date) AS INTEGER) AS year,
  SUM(oi.price + oi.freight_value) AS annual_delivered_volume
FROM olist_orders o
JOIN olist_order_items oi USING(order_id)
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY CAST(strftime('%Y', o.order_delivered_customer_date) AS INTEGER)
```

---

**Skill `select_lowest_year_and_its_top_month`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `result_row` |
| output columns | `year_with_lowest_annual_delivered_orders_volume`, `lowest_annual_delivered_orders_volume`, `highest_monthly_delivered_orders_volume_in_that_year`, `month_of_that_highest_monthly_volume`, `result_row` |
| source tables | `annual_delivered_volume`, `monthly_delivered_volume` |
| depends_on (builds on) | `annual_delivered_volume`, `monthly_delivered_volume` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_From annual_delivered_volume, identify the year(s) with the minimum annual_delivered_volume; if multiple years tie, choose the earliest year. Then, for that selected year, find the month with the maximum monthly_delivered_volume and return the year, the chosen year's annual total, that month's monthly total, and the month._

```sql
SELECT
  a.year AS year_with_lowest_annual_delivered_orders_volume,
  a.annual_delivered_volume AS lowest_annual_delivered_orders_volume,
  m.monthly_delivered_volume AS highest_monthly_delivered_orders_volume_in_that_year,
  m.month AS month_of_that_highest_monthly_volume,
  1 AS result_row
FROM annual_delivered_volume a
JOIN monthly_delivered_volume m
  ON m.year = a.year
WHERE a.year = (
    SELECT year FROM annual_delivered_volume
    WHERE annual_delivered_volume = (
        SELECT MIN(annual_delivered_volume) FROM annual_delivered_volume
    )
    ORDER BY year ASC
    LIMIT 1
)
AND m.monthly_delivered_volume = (
    SELECT MAX(monthly_delivered_volume)
    FROM monthly_delivered_volume md
    WHERE md.year = a.year
)
```

---

**Skill `customer_orders_sel`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `order_id` |
| output columns | `order_id`, `customer_unique_id`, `order_status`, `city`, `state`, `payment_id` |
| source tables | `olist_orders`, `olist_customers`, `olist_order_payments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customer_delivered_counts_join`, `five_lowest_payment_cities_averages` |
| validated_on | — |
| counter_examples | 2 |

_Select orders and their core attributes (order id, customer_unique_id, order_status, city, state, and link to payments) restricted to rows representing orders (no aggregation). This is the per-order cohort that later allows counting delivered orders and joining payments._

```sql
SELECT
  o.order_id AS order_id,
  c.customer_unique_id AS customer_unique_id,
  o.order_status AS order_status,
  c.customer_city AS city,
  c.customer_state AS state,
  op.order_id || '-' || COALESCE(op.payment_sequential, 1) AS payment_id
FROM olist_orders o
JOIN olist_customers c
  ON o.customer_id = c.customer_id
LEFT JOIN olist_order_payments op
  ON o.order_id = op.order_id
```

---

**Skill `customer_payments_agg`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_unique_id` |
| output columns | `customer_unique_id`, `avg_payment_value`, `payment_count` |
| source tables | `olist_order_payments`, `olist_orders`, `olist_customers` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customer_delivered_counts_join` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate payment records per customer to compute average payment value. This relation groups payment records (either linked by payment->order or payment->customer depending on schema) to produce the per-customer average payment value and count of payment records._

```sql
SELECT
  c.customer_unique_id AS customer_unique_id,
  AVG(p.payment_value) AS avg_payment_value,
  COUNT(*) AS payment_count
FROM olist_order_payments p
JOIN olist_orders o ON o.order_id = p.order_id
JOIN olist_customers c ON c.customer_id = o.customer_id
GROUP BY c.customer_unique_id
```

---

**Skill `customer_delivered_counts_join`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_unique_id` |
| output columns | `customer_unique_id`, `delivered_orders_count`, `avg_payment_value`, `city`, `state` |
| source tables | `olist_customers`, `customer_orders_sel`, `customer_payments_agg` |
| depends_on (builds on) | `customer_orders_sel`, `customer_payments_agg` |
| depended-on by (builds on this) | `five_lowest_payment_cities_averages` |
| validated_on | — |
| counter_examples | 0 |

_Count delivered orders per customer by aggregating delivered_orders_filter, then join with customer_payments_agg and a representative city/state for the customer (chosen from their delivered orders or orders table). Produces one row per customer with delivered_orders_count, avg_payment_value, city, and state._

```sql
SELECT
  c.customer_unique_id AS customer_unique_id,
  COALESCE(d.delivered_orders_count, 0) AS delivered_orders_count,
  p.avg_payment_value AS avg_payment_value,
  COALESCE(c.customer_city, co.city) AS city,
  COALESCE(c.customer_state, co.state) AS state
FROM (
  SELECT
    customer_unique_id,
    customer_city,
    customer_state
  FROM olist_customers
) c
LEFT JOIN (
  SELECT
    o.customer_unique_id,
    COUNT(*) AS delivered_orders_count
  FROM customer_orders_sel o
  WHERE o.order_status = 'delivered'
  GROUP BY o.customer_unique_id
) d
  ON c.customer_unique_id = d.customer_unique_id
LEFT JOIN customer_payments_agg p
  ON c.customer_unique_id = p.customer_unique_id
LEFT JOIN (
  -- representative city/state from delivered orders if any exist (fallback source)
  SELECT
    customer_unique_id,
    MIN(city) AS city,
    MIN(state) AS state
  FROM customer_orders_sel
  WHERE order_status = 'delivered'
  GROUP BY customer_unique_id
) co
  ON c.customer_unique_id = co.customer_unique_id
```

---

**Skill `payments_per_order`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `payment_id` |
| output columns | `order_id`, `payment_amount` |
| source tables | `olist_order_payments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select payment records and associate each payment amount with its corresponding order identifier (one row per payment)._

```sql
SELECT
  order_id,
  payment_value AS payment_amount
FROM olist_order_payments
```

---

**Skill `city_level_measures`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_city` |
| output columns | `city`, `total_payments`, `delivered_order_count` |
| source tables | `olist_customers`, `olist_orders`, `olist_order_payments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `five_lowest_payment_cities_averages` |
| validated_on | — |
| counter_examples | 0 |

_For each city, aggregate payments and count delivered orders by joining delivered orders to payments; produce total_payments (sum of payment_amount for orders in that city) and delivered_order_count (distinct delivered orders count) per city. Do not apply ordering or top-k here._

```sql
SELECT
  c.customer_city AS city,
  SUM(op.payment_value) AS total_payments,
  COUNT(DISTINCT o.order_id) AS delivered_order_count
FROM olist_customers c
JOIN olist_orders o
  ON c.customer_id = o.customer_id
JOIN olist_order_payments op
  ON o.order_id = op.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_city
```

---

**Skill `five_lowest_payment_cities_averages`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `city` |
| output columns | `average_total_payments_across_selected_cities`, `average_total_delivered_order_count_across_selected_cities` |
| source tables | `olist_orders`, `city_level_measures`, `customer_orders_sel`, `customer_delivered_counts_join` |
| depends_on (builds on) | `city_level_measures`, `customer_orders_sel`, `customer_delivered_counts_join` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Order cities by total_payments ascending, take the first five cities (lowest total_payments), and compute two scalars: the average of total_payments across those five cities and the average of delivered_order_count across those five cities._

```sql
SELECT
  clm.city AS selected_city,
  AVG(clm.total_payments) OVER () AS average_total_payments_across_selected_cities,
  AVG(clm.delivered_order_count) OVER () AS average_total_delivered_order_count_across_selected_cities
FROM olist_orders o
JOIN customer_orders_sel cos ON o.order_id = cos.order_id
JOIN customer_delivered_counts_join cdc ON cos.customer_unique_id = cdc.customer_unique_id
JOIN city_level_measures clm ON clm.city = cdc.city
GROUP BY clm.city
HAVING 1=1
```

---

**Skill `delivered_order_items`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `order_item_id` |
| output columns | `order_id`, `order_status`, `order_item_id`, `seller_id`, `customer_unique_id`, `price`, `freight_value`, `review_score` |
| source tables | `olist_order_items`, `olist_orders`, `olist_customers`, `olist_order_reviews` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `seller_item_profit` |
| validated_on | — |
| counter_examples | 0 |

_All order items that belong to orders with status 'delivered'; keep item-level financials, seller, order, customer and rating fields needed downstream._

```sql
SELECT
  oi.order_id,
  o.order_status,
  oi.order_item_id,
  oi.seller_id,
  c.customer_unique_id,
  oi.price,
  oi.freight_value,
  r.review_score
FROM olist_order_items AS oi
JOIN olist_orders AS o
  ON oi.order_id = o.order_id
LEFT JOIN olist_customers AS c
  ON o.customer_id = c.customer_id
LEFT JOIN olist_order_reviews AS r
  ON oi.order_id = r.order_id
WHERE o.order_status = 'delivered'
```

---

**Skill `seller_item_profit`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `order_item_id` |
| output columns | `order_item_id`, `seller_id`, `order_id`, `customer_unique_id`, `profit`, `is_5_star` |
| source tables | `olist_order_items`, `olist_customers`, `olist_orders`, `olist_order_reviews`, `delivered_order_items` |
| depends_on (builds on) | `delivered_order_items` |
| depended-on by (builds on this) | `seller_metrics_agg` |
| validated_on | — |
| counter_examples | 0 |

_Compute per-item profit for each delivered order item as price minus freight_value and normalize/clean numeric fields and review_score._

```sql
SELECT
  doi.order_item_id AS order_item_id,
  doi.seller_id AS seller_id,
  doi.order_id AS order_id,
  doi.customer_unique_id AS customer_unique_id,
  (CAST(doi.price AS REAL) - CAST(doi.freight_value AS REAL)) AS profit,
  CASE WHEN CAST(COALESCE(doi.review_score, 0) AS INTEGER) = 5 THEN 1 ELSE 0 END AS is_5_star
FROM delivered_order_items AS doi
WHERE doi.order_status = 'delivered'
```

---

**Skill `seller_metrics_agg`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `seller_id` |
| output columns | `seller_id`, `distinct_customers`, `total_profit`, `distinct_orders`, `five_star_count` |
| source tables | `seller_item_profit` |
| depends_on (builds on) | `seller_item_profit` |
| depended-on by (builds on this) | `top_seller_per_category` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate delivered-item-level rows to seller-level metrics: distinct customer count, sum of profit, distinct order count, and count of 5-star ratings._

```sql
SELECT
  s.seller_id AS seller_id,
  COUNT(DISTINCT s.customer_unique_id) AS distinct_customers,
  SUM(s.profit) AS total_profit,
  COUNT(DISTINCT s.order_id) AS distinct_orders,
  SUM(CASE WHEN s.is_5_star = 1 THEN 1 ELSE 0 END) AS five_star_count
FROM seller_item_profit s
GROUP BY s.seller_id
```

---

**Skill `top_seller_per_category`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `category_row` |
| output columns | `description`, `seller_id`, `value` |
| source tables | `seller_metrics_agg`, `olist_sellers` |
| depends_on (builds on) | `seller_metrics_agg` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each of the four metric categories, pick the single seller with the maximum metric value and label the row with the corresponding description._

```sql
SELECT 'max_total_profit' AS description,
       s.seller_id AS seller_id,
       sm.total_profit AS value
FROM seller_metrics_agg sm
JOIN olist_sellers s USING (seller_id)
WHERE sm.total_profit = (
    SELECT MAX(total_profit) FROM seller_metrics_agg
)
UNION ALL
SELECT 'max_distinct_customers' AS description,
       s.seller_id AS seller_id,
       sm.distinct_customers AS value
FROM seller_metrics_agg sm
JOIN olist_sellers s USING (seller_id)
WHERE sm.distinct_customers = (
    SELECT MAX(distinct_customers) FROM seller_metrics_agg
)
UNION ALL
SELECT 'max_distinct_orders' AS description,
       s.seller_id AS seller_id,
       sm.distinct_orders AS value
FROM seller_metrics_agg sm
JOIN olist_sellers s USING (seller_id)
WHERE sm.distinct_orders = (
    SELECT MAX(distinct_orders) FROM seller_metrics_agg
)
UNION ALL
SELECT 'max_five_star_count' AS description,
       s.seller_id AS seller_id,
       sm.five_star_count AS value
FROM seller_metrics_agg sm
JOIN olist_sellers s USING (seller_id)
WHERE sm.five_star_count = (
    SELECT MAX(five_star_count) FROM seller_metrics_agg
)
```

---

**Skill `payments_with_product_category`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `payment_id` |
| output columns | `payment_id`, `payment_method`, `product_category` |
| source tables | `olist_order_payments`, `olist_order_items`, `olist_products` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All individual payment records joined to the product(s) or order items that determine the product's category so each payment is associated with a product category. Keep only payments that can be linked to an existing category._

```sql
SELECT
  olist_order_payments.order_id || '-' || CAST(olist_order_payments.payment_sequential AS TEXT) AS payment_id,
  olist_order_payments.payment_type AS payment_method,
  olist_products.product_category_name AS product_category
FROM olist_order_payments
JOIN olist_order_items
  ON olist_order_payments.order_id = olist_order_items.order_id
JOIN olist_products
  ON olist_order_items.product_id = olist_products.product_id
WHERE olist_products.product_category_name IS NOT NULL
```

---

**Skill `category_method_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `product_category_name`, `payment_type`, `product_id`, `order_id`, `payment_sequential` |
| output columns | `product_category`, `payment_method`, `payments_count`, `product_id`, `order_id`, `payment_sequential` |
| source tables | `olist_products`, `olist_order_items`, `olist_order_payments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `category_top_method` |
| validated_on | — |
| counter_examples | 0 |

_Count of payments grouped by product category and payment method (number of payments using that method for that category)._

```sql
SELECT
  p.product_category_name AS product_category,
  op.payment_type AS payment_method,
  COUNT(*) AS payments_count,
  p.product_id,
  op.order_id,
  op.payment_sequential
FROM olist_products p
JOIN olist_order_items oi ON oi.product_id = p.product_id
JOIN olist_order_payments op ON op.order_id = oi.order_id
GROUP BY
  p.product_category_name,
  op.payment_type,
  p.product_id,
  op.order_id,
  op.payment_sequential
```

---

**Skill `category_top_method`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `product_category` |
| output columns | `product_category`, `payment_method`, `payments_count` |
| source tables | `category_method_counts` |
| depends_on (builds on) | `category_method_counts` |
| depended-on by (builds on this) | `category_top_method_with_average` |
| validated_on | — |
| counter_examples | 0 |

_For each product category, choose the payment method with the highest payments_count. If ties exist, keep any one tied method per category._

```sql
SELECT
  cm.product_category                                       AS product_category,
  cm.payment_method                                         AS payment_method,
  cm.payments_count                                         AS payments_count
FROM (
  SELECT
    product_category,
    payment_method,
    payments_count,
    ROW_NUMBER() OVER (PARTITION BY product_category ORDER BY payments_count DESC) AS rn
  FROM category_method_counts
) cm
WHERE cm.rn = 1
```

---

**Skill `category_top_method_with_average`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `product_category` |
| output columns | `product_category`, `most_preferred_payment_method`, `payments_for_most_preferred_method`, `average_of_these_payments` |
| source tables | `category_top_method` |
| depends_on (builds on) | `category_top_method` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Combine the per-category chosen top payment-method rows and compute the average of their payments_count across all categories; also emit each category's chosen method and its payments_count alongside the overall average (average is a scalar repeated or returned separately as required)._

```sql
SELECT
  c.product_category AS product_category,
  c.payment_method AS most_preferred_payment_method,
  c.payments_count AS payments_for_most_preferred_method,
  (SELECT AVG(payments_count) FROM category_top_method) AS average_of_these_payments
FROM category_top_method c
```

---

**Skill `payments_with_product_category_22`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `payment_id`, `product_category_id` |
| output columns | `payment_id`, `payment_type_id`, `product_category_id` |
| source tables | `olist_order_payments`, `olist_order_items`, `olist_products` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Join payments to the product(s) on each payment (via order/order_lines or payment->order->order_lines) and map each payment to the product category(ies) involved so each row represents a single payment applied to a single product category. Keep one row per payment-category pairing so payments that cover multiple product categories appear multiple times._

```sql
SELECT
  p.order_id || '-' || p.payment_sequential AS payment_id,
  p.payment_type AS payment_type_id,
  prod.product_category_name AS product_category_id
FROM olist_order_payments AS p
JOIN olist_order_items AS oi
  ON oi.order_id = p.order_id
JOIN olist_products AS prod
  ON prod.product_id = oi.product_id
```

---

**Skill `payment_type_names`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `payment_type` |
| output columns | `payment_type_id`, `payment_type_name` |
| source tables | `olist_order_payments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `category_top_payment_type` |
| validated_on | — |
| counter_examples | 0 |

_Resolve canonical names or identifiers for payment types so each payment_type_id is associated with a readable payment_type_name._

```sql
SELECT
  payment_type AS payment_type_id,
  CASE
    WHEN payment_type = 'credit_card' THEN 'credit_card'
    WHEN payment_type = 'debit_card' THEN 'debit_card'
    WHEN payment_type = 'boleto' THEN 'boleto'
    WHEN payment_type = 'voucher' THEN 'voucher'
    WHEN payment_type IS NULL OR TRIM(payment_type) = '' THEN 'unknown'
    ELSE payment_type
  END AS payment_type_name
FROM olist_order_payments
GROUP BY payment_type
```

---

**Skill `category_payment_type_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `product_category_name`, `payment_type` |
| output columns | `product_category_id`, `payment_type_id`, `payments_count` |
| source tables | `olist_order_payments`, `olist_order_items`, `olist_products` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `category_top_payment_type` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate the joined payment-category rows to count how many payments of each payment type occur within each product category. One row per (product_category, payment_type) with the count of payments._

```sql
SELECT
  p.product_category_name AS product_category_id,
  op.payment_type AS payment_type_id,
  COUNT(*) AS payments_count
FROM olist_order_payments op
JOIN olist_order_items oi
  ON op.order_id = oi.order_id
JOIN olist_products p
  ON oi.product_id = p.product_id
GROUP BY
  p.product_category_name,
  op.payment_type
```

---

**Skill `category_top_payment_type`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `product_category_id`, `payment_type_id` |
| output columns | `product_category_id`, `payment_type_id`, `payment_type_name`, `payments_count` |
| source tables | `category_payment_type_counts`, `payment_type_names` |
| depends_on (builds on) | `category_payment_type_counts`, `payment_type_names` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each product category, pick the payment type(s) with the highest payments_count (ties allowed). Attach the payment type name and produce one or more rows per category for its top payment-type(s). Do not apply the final top-3 category filter here._

```sql
SELECT
  cpc.product_category_id,
  cpc.payment_type_id,
  ptn.payment_type_name,
  cpc.payments_count
FROM category_payment_type_counts AS cpc
LEFT JOIN payment_type_names AS ptn
  ON cpc.payment_type_id = ptn.payment_type_id
```

---

**Skill `geolocation_rows`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `geolocation_id` |
| output columns | `geolocation_id`, `geolocation_state`, `geolocation_city`, `geolocation_zip_code_prefix`, `geolocation_lat_deg`, `geolocation_lng_deg` |
| source tables | `olist_geolocation` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `geolocation_radians`, `ordered_geolocation_with_prev` |
| validated_on | — |
| counter_examples | 0 |

_Select all rows from the geolocation source with the raw columns needed for ordering and distance calculation (ids, state, city, zip prefix, latitude and longitude in degrees). No additional filtering._

```sql
SELECT
  rowid AS geolocation_id,
  geolocation_state,
  geolocation_city,
  geolocation_zip_code_prefix,
  geolocation_lat AS geolocation_lat_deg,
  geolocation_lng AS geolocation_lng_deg
FROM olist_geolocation
```

---

**Skill `geolocation_radians`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `geolocation_id` |
| output columns | `geolocation_id`, `geolocation_state`, `geolocation_city`, `geolocation_zip_code_prefix`, `lat_rad`, `lng_rad`, `geolocation_lat_deg`, `geolocation_lng_deg` |
| source tables | `geolocation_rows` |
| depends_on (builds on) | `geolocation_rows` |
| depended-on by (builds on this) | `ordered_geolocation_with_prev` |
| validated_on | — |
| counter_examples | 0 |

_Normalize/convert lat/lng degrees to radians and project the columns needed for ordering and distance math. Keep one row per geolocation id._

```sql
SELECT
  geolocation_id,
  geolocation_state,
  geolocation_city,
  geolocation_zip_code_prefix,
  RADIANS(geolocation_lat_deg) AS lat_rad,
  RADIANS(geolocation_lng_deg) AS lng_rad,
  geolocation_lat_deg,
  geolocation_lng_deg
FROM geolocation_rows
```

---

**Skill `ordered_geolocation_with_prev`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `geolocation_id` |
| output columns | `geolocation_id`, `prev_geolocation_id`, `geolocation_state`, `geolocation_city`, `prev_geolocation_state`, `prev_geolocation_city`, `geolocation_zip_code_prefix`, `geolocation_lat_deg`, `geolocation_lng_deg`, `prev_geolocation_zip_code_prefix`, `prev_geolocation_lat_deg`, `prev_geolocation_lng_deg`, `lat_rad`, `lng_rad`, `prev_lat_rad`, `prev_lng_rad` |
| source tables | `geolocation_rows`, `geolocation_radians` |
| depends_on (builds on) | `geolocation_rows`, `geolocation_radians` |
| depended-on by (builds on this) | `pairwise_distance_candidates` |
| validated_on | — |
| counter_examples | 0 |

_Order rows by state ASC, city ASC, zip prefix ASC, latitude ASC, longitude ASC and for each row produce the immediate predecessor's key and coordinate fields (using a lag/lead-style window). One row per current geolocation with its previous neighbor attached._

```sql
SELECT
  g.geolocation_id,
  LAG(g.geolocation_id) OVER (ORDER BY g.geolocation_state ASC, g.geolocation_city ASC, g.geolocation_zip_code_prefix ASC, g.geolocation_lat_deg ASC, g.geolocation_lng_deg ASC) AS prev_geolocation_id,
  g.geolocation_state,
  g.geolocation_city,
  LAG(g.geolocation_state) OVER (ORDER BY g.geolocation_state ASC, g.geolocation_city ASC, g.geolocation_zip_code_prefix ASC, g.geolocation_lat_deg ASC, g.geolocation_lng_deg ASC) AS prev_geolocation_state,
  LAG(g.geolocation_city) OVER (ORDER BY g.geolocation_state ASC, g.geolocation_city ASC, g.geolocation_zip_code_prefix ASC, g.geolocation_lat_deg ASC, g.geolocation_lng_deg ASC) AS prev_geolocation_city,
  g.geolocation_zip_code_prefix,
  g.geolocation_lat_deg,
  g.geolocation_lng_deg,
  LAG(g.geolocation_zip_code_prefix) OVER (ORDER BY g.geolocation_state ASC, g.geolocation_city ASC, g.geolocation_zip_code_prefix ASC, g.geolocation_lat_deg ASC, g.geolocation_lng_deg ASC) AS prev_geolocation_zip_code_prefix,
  LAG(g.geolocation_lat_deg) OVER (ORDER BY g.geolocation_state ASC, g.geolocation_city ASC, g.geolocation_zip_code_prefix ASC, g.geolocation_lat_deg ASC, g.geolocation_lng_deg ASC) AS prev_geolocation_lat_deg,
  LAG(g.geolocation_lng_deg) OVER (ORDER BY g.geolocation_state ASC, g.geolocation_city ASC, g.geolocation_zip_code_prefix ASC, g.geolocation_lat_deg ASC, g.geolocation_lng_deg ASC) AS prev_geolocation_lng_deg,
  r.lat_rad,
  r.lng_rad,
  LAG(r.lat_rad) OVER (ORDER BY g.geolocation_state ASC, g.geolocation_city ASC, g.geolocation_zip_code_prefix ASC, g.geolocation_lat_deg ASC, g.geolocation_lng_deg ASC) AS prev_lat_rad,
  LAG(r.lng_rad) OVER (ORDER BY g.geolocation_state ASC, g.geolocation_city ASC, g.geolocation_zip_code_prefix ASC, g.geolocation_lat_deg ASC, g.geolocation_lng_deg ASC) AS prev_lng_rad
FROM geolocation_rows g
JOIN geolocation_radians r
  ON g.geolocation_id = r.geolocation_id
```

---

**Skill `pairwise_distance_candidates`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `prev_geolocation_id`, `geolocation_id` |
| output columns | `prev_geolocation_id`, `geolocation_id`, `prev_geolocation_state`, `prev_geolocation_city`, `geolocation_state`, `geolocation_city`, `prev_geolocation_zip_code_prefix`, `prev_geolocation_lat_deg`, `prev_geolocation_lng_deg`, `geolocation_zip_code_prefix`, `geolocation_lat_deg`, `geolocation_lng_deg`, `distance_km` |
| source tables | `ordered_geolocation_with_prev` |
| depends_on (builds on) | `ordered_geolocation_with_prev` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each row that has an immediate predecessor, compute the great-circle distance (km) between the row and its predecessor using the Spherical Law of Cosines with Earth radius = 6371. Produce one row per adjacent-pair candidate containing both ids, their attributes, and the computed distance._

```sql
SELECT
  o.prev_geolocation_id,
  o.geolocation_id,
  o.prev_geolocation_state,
  o.prev_geolocation_city,
  o.geolocation_state,
  o.geolocation_city,
  o.prev_geolocation_zip_code_prefix,
  o.prev_geolocation_lat_deg,
  o.prev_geolocation_lng_deg,
  o.geolocation_zip_code_prefix,
  o.geolocation_lat_deg,
  o.geolocation_lng_deg,
  -- spherical law of cosines distance in km; guard for numeric stability using LEAST/GREATEST
  6371.0 * acos(
    -- ensure the argument to acos is within [-1,1]
    CASE
      WHEN ( (sin(o.prev_lat_rad) * sin(o.lat_rad)) + (cos(o.prev_lat_rad) * cos(o.lat_rad) * cos(o.lng_rad - o.prev_lng_rad)) ) > 1.0 THEN 1.0
      WHEN ( (sin(o.prev_lat_rad) * sin(o.lat_rad)) + (cos(o.prev_lat_rad) * cos(o.lat_rad) * cos(o.lng_rad - o.prev_lng_rad)) ) < -1.0 THEN -1.0
      ELSE (sin(o.prev_lat_rad) * sin(o.lat_rad)) + (cos(o.prev_lat_rad) * cos(o.lat_rad) * cos(o.lng_rad - o.prev_lng_rad))
    END
  ) AS distance_km
FROM ordered_geolocation_with_prev o
WHERE o.prev_geolocation_id IS NOT NULL
```

---
