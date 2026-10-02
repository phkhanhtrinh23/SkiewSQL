# Skill graph — `bank_sales_trading` (19 skills)

**Skill `monthly_balances`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `DATE(ctt.txn_date)` |
| output columns | `customer_id`, `month`, `balance` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customer_monthly_balances`, `monthly_net_balances` |
| validated_on | — |
| counter_examples | 0 |

_Calculate the monthly balance for each customer._

```sql
SELECT
  ctt.customer_id AS customer_id,
  DATE(ctt.txn_date) BETWEEN DATE('2020-01-01') AND DATE('2020-12-31') AS month,
  SUM(ctt.txn_amount) AS balance
FROM customer_transactions AS ctt
GROUP BY ctt.customer_id, DATE(ctt.txn_date)
```

---

**Skill `customer_monthly_balances`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month` |
| output columns | `customer_id`, `month`, `balance`, `cumulative_balance` |
| source tables | `customer_transactions` |
| depends_on (builds on) | `monthly_balances` |
| depended-on by (builds on this) | `monthly_net_balances` |
| validated_on | — |
| counter_examples | 0 |

_Calculate the monthly balance for each customer, including cumulative balance._

```sql
SELECT
    ctt.customer_id,
    strftime('%Y-%m', ctt.txn_date) AS month,
    SUM(ctt.txn_amount) AS balance,
    SUM(ctt.txn_amount) OVER (PARTITION BY ctt.customer_id) AS cumulative_balance
FROM customer_transactions ctt
GROUP BY ctt.customer_id, strftime('%Y-%m', ctt.txn_date)
```

---

**Skill `customer_balances`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `cumulative_balance` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `monthly_net_balances` |
| validated_on | — |
| counter_examples | 0 |

_Calculate the cumulative balance for each customer._

```sql
SELECT
  ct.customer_id,
  SUM(ct.txn_amount) AS cumulative_balance
FROM customer_transactions AS ct
GROUP BY ct.customer_id
```

---

**Skill `monthly_net_balances`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month` |
| output columns | `customer_id`, `month`, `net_balance` |
| source tables | `customer_transactions` |
| depends_on (builds on) | `monthly_balances`, `customer_monthly_balances`, `customer_balances` |
| depended-on by (builds on this) | `customer_monthly_balances_4` |
| validated_on | — |
| counter_examples | 0 |

_Calculate the monthly net balance for each customer._

```sql
SELECT
    ct1.customer_id,
    STRFTIME('%Y-%m', ct1.txn_date) AS month,
    SUM(ct1.txn_amount) AS net_balance
FROM customer_transactions AS ct1
GROUP BY ct1.customer_id,
STRFTIME('%Y-%m', ct1.txn_date)
```

---

**Skill `customer_monthly_balances_4`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month` |
| output columns | `customer_id`, `month`, `closing_balance` |
| source tables | `customer_transactions`, `monthly_net_balances` |
| depends_on (builds on) | `monthly_net_balances` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculate the cumulative closing balance for each month for each customer._

```sql
SELECT
    cdt.customer_id,
    strftime('%Y-%m', mnb.month) AS month,
    SUM(cdt.txn_amount) AS closing_balance
FROM customer_transactions cdt
JOIN monthly_net_balances mnb ON cdt.customer_id = mnb.customer_id
GROUP BY cdt.customer_id, strftime('%Y-%m', mnb.month)
```

---

**Skill `daily_balances`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `txn_date` |
| output columns | `customer_id`, `date`, `daily_balance` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `monthly_balances_6` |
| validated_on | — |
| counter_examples | 0 |

_Calculate daily balance for each customer._

```sql
SELECT
  ct.customer_id,
  ct.txn_date AS date,
  SUM(ct.txn_amount) AS daily_balance
FROM customer_transactions AS ct
WHERE ct.txn_date = '0' -- Intrinsic filter: daily_balance = 0
GROUP BY ct.customer_id, ct.txn_date
```

---

**Skill `monthly_balances_6`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month` |
| output columns | `customer_id`, `month`, `max_monthly_balance` |
| source tables | `daily_balances` |
| depends_on (builds on) | `daily_balances` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregate daily balances to monthly balances._

```sql
SELECT
  d.customer_id,
  STRFTIME('%Y-%m', d.date) AS month,
  SUM(d.daily_balance) AS max_monthly_balance
FROM daily_balances d
GROUP BY d.customer_id, STRFTIME('%Y-%m', d.date)
```

---

**Skill `product_views`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `product_id` |
| output columns | `view_count` |
| source tables | `shopping_cart_page_hierarchy` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Selects product view counts based on page ID._

```sql
SELECT
  'product_views' AS view_name,
  COUNT(shopping_cart_page_hierarchy.product_id) AS view_count
FROM shopping_cart_page_hierarchy
WHERE
  page_id NOT IN (
    1,
    2,
    12,
    13
  )
```

---

**Skill `product_cart_additions`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `product_id` |
| output columns | `cart_addition_count`, `product_id` |
| source tables | `shopping_cart_page_hierarchy` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Selects product cart addition counts based on page ID._

```sql
SELECT
  'cart_addition_count' AS cart_addition_count,
  page_id AS product_id
FROM shopping_cart_page_hierarchy
WHERE page_id NOT IN (1, 2, 12, 13)
```

---

**Skill `product_abandoned_carts`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `product_id` |
| output columns | `abandoned_cart_count`, `product_id` |
| source tables | `shopping_cart_page_hierarchy` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Selects product abandoned cart counts based on page ID._

```sql
SELECT
  'abandoned_cart_count' AS abandoned_cart_count,
  page_id AS product_id
FROM shopping_cart_page_hierarchy
WHERE
  page_id NOT IN (
    1,
    2,
    12,
    13
  )
```

---

**Skill `monthly_interest_data`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `date`, `interest_name`, `index_composition` |
| output columns | `date`, `interest_name`, `index_composition` |
| source tables | `interest_metrics`, `interest_map` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Extracts monthly interest data with relevant columns._

```sql
SELECT
    DATE(t1.month_year) AS date,
    t2.interest_name AS interest_name,
    t3.index_value AS index_composition
FROM
    interest_metrics t3
JOIN
    interest_map t2 ON t3.interest_id = t2.id
JOIN
    (SELECT month_year FROM interest_metrics GROUP BY month_year) t1 ON 1=1
WHERE
    t1.month_year BETWEEN '2018-09-01' AND '2019-08-31'
```

---

**Skill `rolling_average_composites`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `interest_name` |
| output columns | `date`, `interest_name`, `rolling_average_max_composition` |
| source tables | `interest_map`, `interest_metrics` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculates the three-month rolling average of the maximum index composition._

```sql
SELECT
    DATE('2020-08-31') AS date,
    i."interest_name" AS interest_name,
    AVG(im."index_value") AS rolling_average_max_composition
FROM
    "interest_map" i
JOIN
    "interest_metrics" im ON i."id" = im."interest_id"
WHERE
    im."_month" >= 7.0
GROUP BY
    i."interest_name"
ORDER BY
    i."interest_name"
```

---

**Skill `interest_composition`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `interest_name` |
| output columns | `interest_name`, `composition_value` |
| source tables | `interest_map`, `interest_metrics` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculates the total composition value for each interest across all months._

```sql
SELECT
  i."interest_name",
  SUM(im."composition") AS "composition_value"
FROM "interest_map" AS i
JOIN "interest_metrics" AS im
  ON i."id" = im."interest_id"
GROUP BY
  i."interest_name"
```

---

**Skill `btc_purchases_yearly`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `year`, `region` |
| output columns | `year`, `region`, `total_btc_amount`, `total_btc_quantity` |
| source tables | `bitcoin_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `btc_avg_price_yearly` |
| validated_on | — |
| counter_examples | 0 |

_Calculate total Bitcoin purchase amount and quantity for each year and region._

```sql
SELECT
    strftime('%Y', txn_date) AS year,
    substr(member_id, 1, 1) AS region,
    SUM(quantity) AS total_btc_amount,
    SUM(quantity) AS total_btc_quantity
FROM
    bitcoin_transactions
WHERE
    txn_date >= '2023-01-01'
GROUP BY
    year,
    substr(member_id, 1, 1)
```

---

**Skill `btc_avg_price_yearly`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `year`, `region` |
| output columns | `year`, `region`, `avg_btc_price` |
| source tables | `btc_purchases_yearly` |
| depends_on (builds on) | `btc_purchases_yearly` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculate the average purchase price per Bitcoin for each region for each year._

```sql
SELECT
    btc_purchases_yearly.year AS year,
    btc_purchases_yearly.region AS region,
    AVG(btc_purchases_yearly.total_btc_amount) AS avg_btc_price
FROM
    btc_purchases_yearly
GROUP BY
    btc_purchases_yearly.year,
    btc_purchases_yearly.region
```

---

**Skill `calculate_average_loss_rate`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `item_code` |
| output columns | `average_loss_rate` |
| source tables | `veg_loss_rate_df` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `item_loss_rates` |
| validated_on | — |
| counter_examples | 0 |

_Calculate the average loss rate across all items._

```sql
SELECT 'average_loss_rate' AS average_loss_rate
FROM veg_loss_rate_df
```

---

**Skill `item_loss_rates`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `item_code` |
| output columns | `item_id`, `loss_rate` |
| source tables | `veg_loss_rate_df` |
| depends_on (builds on) | `calculate_average_loss_rate` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculate the loss rate for each item._

```sql
SELECT
  v1."item_code" AS "item_id",
  AVG(v1."loss_rate_%" * 1.0) AS "loss_rate"
FROM "veg_loss_rate_df" AS v1
GROUP BY "item_code"
```

---

**Skill `weekly_sales_2018_2020`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `date`, `sales_amount` |
| output columns | `date`, `sales_amount` |
| source tables | `cleaned_weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Selects weekly sales data for the years 2018, 2019, and 2020._

```sql
SELECT
    DATE(cleaned_weekly_sales.week_date_formatted) AS date,
    cleaned_weekly_sales.sales AS sales_amount
FROM cleaned_weekly_sales
WHERE cleaned_weekly_sales.calendar_year IN (2018, 2019, 2020)
```

---

**Skill `calculate_percentage_change`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `year`, `percentage_change` |
| output columns | `year`, `percentage_change` |
| source tables | `weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculates the percentage change in sales between the four weeks preceding and the four weeks following June 15._

```sql
SELECT
    '2020' AS year,
    (
        SUM(CASE WHEN week_date BETWEEN '2020-07-01' AND '2020-07-17' THEN sales ELSE 0 END) -
        SUM(CASE WHEN week_date BETWEEN '2020-06-16' AND '2020-06-22' THEN sales ELSE 0 END)
    ) * 100.0 / SUM(CASE WHEN week_date BETWEEN '2020-07-01' AND '2020-07-17' THEN sales ELSE 0 END)
    AS percentage_change
FROM weekly_sales
WHERE week_date BETWEEN '2020-06-16' AND '2020-07-17'
```

---
