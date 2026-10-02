# Skill graph — `E_commerce` (12 skills)

**Skill `training_rows`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `date` |
| output columns | `date`, `sales` |
| source tables | `orders`, `order_items`, `customers` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `training_features` |
| validated_on | — |
| counter_examples | 0 |

_Select the daily toy-sales rows restricted to the regression training date range (inclusive). This is the raw cohort used to fit the linear model._

```sql
SELECT
  date(order_purchase_timestamp) AS date,
  COUNT(DISTINCT orders.order_id) AS sales,
  orders.order_id,
  customers.customer_id
FROM orders
JOIN order_items USING(order_id)
JOIN customers USING(customer_id)
WHERE orders.order_status = 'delivered'
GROUP BY date(order_purchase_timestamp)
```

---

**Skill `training_features`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `date` |
| output columns | `date`, `time_index`, `sales` |
| source tables | `training_rows` |
| depends_on (builds on) | `training_rows` |
| depended-on by (builds on this) | `predicted_daily_sales` |
| validated_on | — |
| counter_examples | 0 |

_Project and normalize the training rows into numeric features for regression: convert date into a numeric time variable (e.g., days since epoch) and ensure sales is numeric. One row per original date is retained._

```sql
SELECT
  date,
  CAST((JULIANDAY(date) - JULIANDAY('1970-01-01')) AS REAL) AS time_index,
  CAST(sales AS REAL) AS sales
FROM training_rows
```

---

**Skill `predicted_daily_sales`** — category `SEM`

| field | value |
|---|---|
| grain (one row per) | `date`, `time_index` |
| output columns | `date`, `time_index`, `predicted_sales` |
| source tables | `training_features` |
| depends_on (builds on) | `training_features` |
| depended-on by (builds on this) | `predicted_moving_averages` |
| validated_on | — |
| counter_examples | 0 |

_Fit a simple linear regression of sales ~ time_index using the training_features, then apply the fitted model to produce predicted sales for any requested calendar date. This relation contains predicted sales for every date needed (all prediction target dates plus any +/-2 day neighbors). Produce one row per predicted date with its predicted_sales._

```sql
SELECT
  f.date AS date,
  f.time_index AS time_index,
  (
    -- predicted_sales = intercept + slope * time_index
    ( ( (SUM(f.time_index * f.sales) - (SUM(f.time_index) * SUM(f.sales) / COUNT(*)) )
        /
        ( (SUM(f.time_index * f.time_index) - (SUM(f.time_index) * SUM(f.time_index) / COUNT(*)) ) )
      )
      * (f.time_index - (SUM(f.time_index) / COUNT(*)))
    )
    + (SUM(f.sales) / COUNT(*))
  ) AS predicted_sales
FROM training_features f
GROUP BY f.date, f.time_index
```

---

**Skill `predicted_moving_averages`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `date` |
| output columns | `date`, `predicted_sales_for_date`, `5_day_symmetric_moving_average_of_predicted_sales`, `sum_of_the_four_5_day_moving_averages` |
| source tables | `predicted_daily_sales` |
| depends_on (builds on) | `predicted_daily_sales` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each prediction target date, assemble the centered 5-day window (target date ±2 days) of predicted_sales from predicted_daily_sales and compute the 5-day symmetric moving average. Also compute the final scalar sum across the four 5-day averages (the sum is included as a column repeated on each row or as an additional aggregate row in downstream use). This relation returns one row per target date with its predicted_sales (for the date) and its 5-day_symmetric_moving_average_of_predicted_sales. The sum_of_the_four_5_day_moving_averages is produced alongside or as a separate aggregate value derived from these rows._

```sql
SELECT
  p.date AS date,
  p.predicted_sales AS predicted_sales_for_date,
  (
    SELECT AVG(p2.predicted_sales)
    FROM predicted_daily_sales p2
    WHERE DATE(p2.date) BETWEEN DATE(p.date, '-2 day') AND DATE(p.date, '+2 day')
  ) AS "5_day_symmetric_moving_average_of_predicted_sales",
  (
    SELECT SUM(avg5.avg_val) FROM (
      SELECT
        (
          SELECT AVG(p3.predicted_sales)
          FROM predicted_daily_sales p3
          WHERE DATE(p3.date) BETWEEN DATE(p4.date, '-2 day') AND DATE(p4.date, '+2 day')
        ) AS avg_val
      FROM predicted_daily_sales p4
      ORDER BY p4.date
      LIMIT 4
    ) avg5
  ) AS sum_of_the_four_5_day_moving_averages
FROM predicted_daily_sales p
```

---

**Skill `delivered_orders_sel`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `order_id`, `customer_id`, `order_purchase_timestamp` |
| output columns | `order_id`, `customer_id`, `order_timestamp`, `order_total` |
| source tables | `orders`, `order_payments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customer_order_events_agg` |
| validated_on | — |
| counter_examples | 0 |

_Select all orders whose status equals 'delivered' and retain order identifier, customer identifier, order timestamp, and order total amount (monetary). This relation is the filtered cohort of orders to base all RFM calculations on._

```sql
SELECT
  o.order_id AS order_id,
  o.customer_id AS customer_id,
  o.order_purchase_timestamp AS order_timestamp,
  COALESCE(SUM(op.payment_value), 0.0) AS order_total
FROM orders o
LEFT JOIN order_payments op
  ON o.order_id = op.order_id
WHERE o.order_status = 'delivered'
GROUP BY o.order_id, o.customer_id, o.order_purchase_timestamp
```

---

**Skill `customer_order_events_agg`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `last_purchase_timestamp`, `recency_days`, `frequency`, `monetary_total` |
| source tables | `delivered_orders_sel` |
| depends_on (builds on) | `delivered_orders_sel` |
| depended-on by (builds on this) | `customer_rfm_scores_rank`, `segment_level_metrics` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate delivered orders to one row per customer computing: last_purchase_timestamp (max order_timestamp), frequency (count of delivered orders), monetary_total (sum of order_total). Also compute recency_days as the difference in days between a single analysis reference date (provided at runtime) and last_purchase_timestamp. Exclude or mark customers with zero delivered orders per the analysis rule._

```sql
SELECT
  d.customer_id AS customer_id,
  MAX(d.order_timestamp) AS last_purchase_timestamp,
  CAST((JULIANDAY(MAX(d.order_timestamp)) - JULIANDAY('1970-01-01')) AS INTEGER) /* placeholder, recency computed vs runtime reference */ AS recency_days,
  COUNT(d.order_id) AS frequency,
  SUM(d.order_total) AS monetary_total
FROM delivered_orders_sel d
GROUP BY d.customer_id
```

---

**Skill `customer_rfm_scores_rank`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `R_score`, `F_score`, `M_score`, `RFM_segment` |
| source tables | `customer_order_events_agg` |
| depends_on (builds on) | `customer_order_events_agg` |
| depended-on by (builds on this) | `segment_level_metrics` |
| validated_on | — |
| counter_examples | 0 |

_Compute R, F, and M quintile scores (1..5) for each customer by ranking customers into 20%-bucket quintiles across recency_days (where the most recent customers -> R=1 and least recent -> R=5), frequency (highest frequency -> F=1, lowest -> F=5), and monetary_total (highest spend -> M=1, lowest -> M=5). Produce R_score, F_score, M_score and concatenate them into RFM_segment string. Keep one row per customer with scores._

```sql
SELECT
  coea.customer_id,
  -- Recency: lower recency_days => more recent. Rank into quintiles 1 (most recent) .. 5 (least recent)
  (CASE
    WHEN recency_rank <= total_customers * 0.2 THEN 1
    WHEN recency_rank <= total_customers * 0.4 THEN 2
    WHEN recency_rank <= total_customers * 0.6 THEN 3
    WHEN recency_rank <= total_customers * 0.8 THEN 4
    ELSE 5
  END) AS R_score,
  -- Frequency: higher frequency => better (1). Rank descending.
  (CASE
    WHEN freq_rank_desc <= total_customers * 0.2 THEN 1
    WHEN freq_rank_desc <= total_customers * 0.4 THEN 2
    WHEN freq_rank_desc <= total_customers * 0.6 THEN 3
    WHEN freq_rank_desc <= total_customers * 0.8 THEN 4
    ELSE 5
  END) AS F_score,
  -- Monetary: higher monetary_total => better (1). Rank descending.
  (CASE
    WHEN mon_rank_desc <= total_customers * 0.2 THEN 1
    WHEN mon_rank_desc <= total_customers * 0.4 THEN 2
    WHEN mon_rank_desc <= total_customers * 0.6 THEN 3
    WHEN mon_rank_desc <= total_customers * 0.8 THEN 4
    ELSE 5
  END) AS M_score,
  -- Concatenate R,F,M as string
  (CAST(
    (CASE
      WHEN recency_rank <= total_customers * 0.2 THEN 1
      WHEN recency_rank <= total_customers * 0.4 THEN 2
      WHEN recency_rank <= total_customers * 0.6 THEN 3
      WHEN recency_rank <= total_customers * 0.8 THEN 4
      ELSE 5
    END) AS TEXT)
   || CAST(
    (CASE
      WHEN freq_rank_desc <= total_customers * 0.2 THEN 1
      WHEN freq_rank_desc <= total_customers * 0.4 THEN 2
      WHEN freq_rank_desc <= total_customers * 0.6 THEN 3
      WHEN freq_rank_desc <= total_customers * 0.8 THEN 4
      ELSE 5
    END) AS TEXT)
   || CAST(
    (CASE
      WHEN mon_rank_desc <= total_customers * 0.2 THEN 1
      WHEN mon_rank_desc <= total_customers * 0.4 THEN 2
      WHEN mon_rank_desc <= total_customers * 0.6 THEN 3
      WHEN mon_rank_desc <= total_customers * 0.8 THEN 4
      ELSE 5
    END) AS TEXT)
  ) AS RFM_segment
FROM (
  SELECT
    customer_id,
    recency_days,
    frequency,
    monetary_total,
    -- rank customers by recency ascending (most recent -> rank 1)
    (SELECT COUNT(*) FROM customer_order_events_agg AS t2 WHERE t2.recency_days < t1.recency_days) + 1 AS recency_rank,
    -- rank by frequency descending (highest frequency -> rank 1)
    (SELECT COUNT(*) FROM customer_order_events_agg AS t3 WHERE t3.frequency > t1.frequency) + 1 AS freq_rank_desc,
    -- rank by monetary_total descending (highest spend -> rank 1)
    (SELECT COUNT(*) FROM customer_order_events_agg AS t4 WHERE t4.monetary_total > t1.monetary_total) + 1 AS mon_rank_desc,
    -- total number of customers to compute quintile thresholds
    (SELECT COUNT(*) FROM customer_order_events_agg) AS total_customers
  FROM customer_order_events_agg AS t1
) AS coea
```

---

**Skill `segment_level_metrics`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `RFM_segment`, `customer_id`, `last_purchase_timestamp`, `recency_days`, `frequency`, `monetary_total`, `R_score`, `F_score`, `M_score` |
| output columns | `RFM_segment`, `segment_avg_sales_per_order`, `segment_customer_count`, `customer_id`, `last_purchase_timestamp`, `recency_days`, `frequency`, `monetary_total`, `avg_sales_per_order`, `R_score`, `F_score`, `M_score` |
| source tables | `customer_rfm_scores_rank`, `customer_order_events_agg` |
| depends_on (builds on) | `customer_rfm_scores_rank`, `customer_order_events_agg` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Combine per-customer metrics and RFM segment assignments to compute per-segment aggregates: for each RFM_segment, compute segment_avg_sales_per_order (average of customers' avg_sales_per_order where avg_sales_per_order = monetary_total / frequency and division-by-zero handled per rules) and segment_customer_count. Also include customers' detailed output (customer_id, last_purchase_timestamp, recency_days, frequency, monetary_total, avg_sales_per_order, R_score, F_score, M_score, RFM_segment) for reporting and to enable textual comparison between segments._

```sql
SELECT
  r.RFM_segment AS RFM_segment,
  AVG(
    CASE
      WHEN co.frequency IS NULL OR co.frequency = 0 THEN 0.0
      ELSE co.monetary_total * 1.0 / co.frequency
    END
  ) AS segment_avg_sales_per_order,
  COUNT(r.customer_id) AS segment_customer_count,
  r.customer_id AS customer_id,
  co.last_purchase_timestamp AS last_purchase_timestamp,
  co.recency_days AS recency_days,
  co.frequency AS frequency,
  co.monetary_total AS monetary_total,
  CASE
    WHEN co.frequency IS NULL OR co.frequency = 0 THEN 0.0
    ELSE co.monetary_total * 1.0 / co.frequency
  END AS avg_sales_per_order,
  r.R_score AS R_score,
  r.F_score AS F_score,
  r.M_score AS M_score
FROM customer_rfm_scores_rank r
LEFT JOIN customer_order_events_agg co
  ON r.customer_id = co.customer_id
GROUP BY r.RFM_segment, r.customer_id, co.last_purchase_timestamp, co.recency_days, co.frequency, co.monetary_total, r.R_score, r.F_score, r.M_score
```

---

**Skill `customer_orders`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `order_id` |
| output columns | `customer_id`, `order_id`, `payment_amount`, `purchase_date` |
| source tables | `orders`, `order_payments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `per_customer_order_stats` |
| validated_on | — |
| counter_examples | 0 |

_All orders that belong to customers, with each order's payment amount and purchase date. This filters to orders that have an associated customer and a payment amount/date present (i.e., only orders to be considered for metrics)._

```sql
SELECT
  o.customer_id AS customer_id,
  o.order_id AS order_id,
  op.payment_value AS payment_amount,
  o.order_purchase_timestamp AS purchase_date
FROM orders o
JOIN order_payments op
  ON o.order_id = op.order_id
WHERE o.customer_id IS NOT NULL
  AND op.payment_value IS NOT NULL
  AND o.order_purchase_timestamp IS NOT NULL
```

---

**Skill `per_customer_order_stats`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `order_count`, `sum_payments`, `avg_payment_per_order`, `first_purchase_date`, `last_purchase_date` |
| source tables | `customer_orders`, `order_payments` |
| depends_on (builds on) | `customer_orders` |
| depended-on by (builds on this) | `per_customer_lifespan` |
| validated_on | — |
| counter_examples | 0 |

_Per-customer aggregates computed from customer_orders: count of orders, sum of payments, average payment per order (or compute avg from sum/count), earliest purchase_date and latest purchase_date._

```sql
SELECT
  co.customer_id AS customer_id,
  COUNT(DISTINCT co.order_id) AS order_count,
  COALESCE(SUM(op.payment_value), 0.0) AS sum_payments,
  CASE WHEN COUNT(DISTINCT co.order_id) = 0 THEN 0.0
       ELSE COALESCE(SUM(op.payment_value), 0.0) / COUNT(DISTINCT co.order_id)
  END AS avg_payment_per_order,
  MIN(co.purchase_date) AS first_purchase_date,
  MAX(co.purchase_date) AS last_purchase_date
FROM customer_orders co
LEFT JOIN order_payments op
  ON co.order_id = op.order_id
GROUP BY co.customer_id
```

---

**Skill `per_customer_lifespan`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `order_count`, `avg_payment_per_order`, `lifespan_weeks` |
| source tables | `per_customer_order_stats` |
| depends_on (builds on) | `per_customer_order_stats` |
| depended-on by (builds on this) | `top_customers_by_avg_payment` |
| validated_on | — |
| counter_examples | 0 |

_Compute customer lifespan in weeks from first and last purchase dates: lifespan_weeks = (last_purchase_date - first_purchase_date) in days divided by 7, but if that result < 1.0 then set to 1.0. Keep other per-customer metrics unchanged._

```sql
SELECT
  p.customer_id AS customer_id,
  p.order_count AS order_count,
  p.avg_payment_per_order AS avg_payment_per_order,
  CASE
    WHEN (julianday(p.last_purchase_date) - julianday(p.first_purchase_date)) / 7.0 < 1.0
    THEN 1.0
    ELSE (julianday(p.last_purchase_date) - julianday(p.first_purchase_date)) / 7.0
  END AS lifespan_weeks
FROM per_customer_order_stats p
```

---

**Skill `top_customers_by_avg_payment`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `order_count`, `avg_payment_per_order`, `lifespan_weeks` |
| source tables | `per_customer_lifespan` |
| depends_on (builds on) | `per_customer_lifespan` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Rank customers by avg_payment_per_order descending and select the top 3 customers. Output customer identifier, order_count (integer), avg_payment_per_order (numeric), and lifespan_weeks (numeric)._

```sql
SELECT
  p.customer_id AS customer_id,
  p.order_count AS order_count,
  p.avg_payment_per_order AS avg_payment_per_order,
  p.lifespan_weeks AS lifespan_weeks
FROM per_customer_lifespan p
WHERE p.order_count IS NOT NULL
```

---
