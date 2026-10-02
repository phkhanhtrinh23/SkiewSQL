# Skill graph — `bank_sales_trading` (15 skills)

## Skill `customer_balances`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `cumulative_balance` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Calculate the cumulative balance for each customer.

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
  c.customer_id,
  SUM(c.txn_amount) AS cumulative_balance
FROM customer_transactions AS c
GROUP BY c.customer_id
```

---

## Skill `monthly_balances_initial`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `Month` |
| output columns | `Month`, `Initial Balance` |
| source tables | `cleaned_weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Calculate the initial balance for each month based on the first month's balance.

### Semantic filters

```json
{
  "column": "month_number",
  "value": "1",
  "month_number": "1"
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
    'January' AS Month,
    SUM(sales) OVER (PARTITION BY "month_number" ORDER BY "month_number" ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING) AS "Initial Balance"
FROM cleaned_weekly_sales
WHERE "month_number" = 1
```

---

## Skill `final_monthly_balances`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `Month` |
| output columns | `Month`, `Total Balance` |
| source tables | `cleaned_weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Clean and format the calculated balances for the final output.

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
    strftime('%Y-%m', t1.week_date_formatted) AS "Month",
    SUM(t1.sales) AS "Total Balance"
FROM cleaned_weekly_sales AS t1
GROUP BY "Month"
```

---

## Skill `daily_transactions`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `transaction_date` |
| output columns | `customer_id`, `transaction_date`, `transaction_amount` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Extracts daily transaction data for each customer.

### Semantic filters

```json
{
  "customer_id": "",
  "transaction_date": ""
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
    c.customer_id,
    c.txn_date AS transaction_date,
    c.txn_amount AS transaction_amount
FROM customer_transactions AS c
```

---

## Skill `product_views`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `product_id` |
| output columns | `view_count` |
| source tables | `shopping_cart_page_hierarchy` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Selects product view counts based on page ID.

### Semantic filters

```json
{
  "column": "page_id",
  "value": "[1, 2, 12, 13]"
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
  COUNT(shopping_cart_page_hierarchy.product_id) AS view_count
FROM shopping_cart_page_hierarchy
WHERE shopping_cart_page_hierarchy.page_id NOT IN (1, 2, 12, 13)
```

---

## Skill `product_abandoned_carts`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `product_id` |
| output columns | `abandoned_cart_count`, `product_id` |
| source tables | `shopping_cart_page_hierarchy` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Selects product abandoned cart counts based on page ID.

### Semantic filters

```json
{
  "page_id_not": "[1, 2, 12, 13]"
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
  'abandoned_cart_count' AS abandoned_cart_count,
  sp.product_id AS product_id
FROM shopping_cart_page_hierarchy AS sp
WHERE
  sp.page_id NOT IN (1, 2, 12, 13)
```

---

## Skill `monthly_interest_data`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `date`, `interest_name`, `index_composition` |
| output columns | `date`, `interest_name`, `index_composition` |
| source tables | `interest_map`, `interest_metrics` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Extracts monthly interest data with relevant columns.

### Semantic filters

```json
{
  "column": "value"
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
    DATE(T1.month_year) AS date,
    T2.interest_name AS interest_name,
    T3.index_value AS index_composition
FROM
    interest_metrics AS T1
INNER JOIN
    interest_map AS T2
    ON T1.interest_id = T2.id
INNER JOIN
    interest_metrics AS T3
    ON T1.interest_id = T3.interest_id
WHERE
    T1.month_year BETWEEN '2018-09-01' AND '2019-08-31'
```

---

## Skill `interest_composition`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `interest_name` |
| output columns | `interest_name`, `composition_value` |
| source tables | `interest_map`, `interest_metrics` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Calculates the total composition value for each interest across all months.

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
    im."interest_name",
    SUM(im."composition") AS "composition_value"
FROM
    interest_map AS im
JOIN
    interest_metrics AS im
ON
    im."interest_id" = im."interest_id"
GROUP BY
    im."interest_name"
```

---

## Skill `btc_purchases_yearly`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `year`, `member_id` |
| output columns | `year`, `region`, `total_btc_amount`, `total_btc_quantity` |
| source tables | `bitcoin_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `btc_avg_price_yearly` |

### Description

Calculate total Bitcoin purchase amount and quantity for each year and region.

### Semantic filters

```json
{
  "column": "txn_date",
  "value": ">= 2023"
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
    strftime('%Y', txn_date) AS year,
    member_id AS region,
    SUM(quantity) AS total_btc_quantity,
    SUM(quantity) AS total_btc_amount
FROM
    bitcoin_transactions
WHERE
    strftime('%Y', txn_date) >= '2023'
GROUP BY
    year,
    member_id
```

---

## Skill `btc_avg_price_yearly`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `year`, `region` |
| output columns | `year`, `region`, `avg_btc_price` |
| source tables | `btc_purchases_yearly` |
| depends_on (builds on) | `btc_purchases_yearly` |
| depended-on by (builds on this) | — |

### Description

Calculate the average purchase price per Bitcoin for each region for each year.

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

## Skill `calculate_average_loss_rate`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `item_code` |
| output columns | `average_loss_rate` |
| source tables | `veg_loss_rate_df` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Calculate the average loss rate across all items.

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
  'average_loss_rate' AS average_loss_rate
FROM veg_loss_rate_df
```

---

## Skill `category_wholesale_summary_2020_2023`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `category_name`, `year` |
| output columns | `category`, `year`, `average_wholesale_price`, `maximum_wholesale_price`, `minimum_wholesale_price`, `total_wholesale_price` |
| source tables | `veg_whsle_df`, `veg_cat` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Calculate summary statistics (average, max, min, total) for wholesale prices by category and year.

### Semantic filters

```json
{
  "column": "whsle_date",
  "value": "2020-01-01 2023-12-31"
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
    v1."category_name" AS category,
    STRFTIME('%Y', v2."whsle_date") AS year,
    AVG(v2."whsle_px_rmb-kg") AS average_wholesale_price,
    MAX(v2."whsle_px_rmb-kg") AS maximum_wholesale_price,
    MIN(v2."whsle_px_rmb-kg") AS minimum_wholesale_price,
    SUM(v2."whsle_px_rmb-kg") AS total_wholesale_price
FROM "veg_whsle_df" v2
JOIN "veg_cat" v1 ON v2."item_code" = v1."index"
WHERE STRFTIME('%Y', v2."whsle_date") BETWEEN '2020-01-01' AND '2023-12-31'
GROUP BY v1."category_name", STRFTIME('%Y', v2."whsle_date")
```

---

## Skill `sales_by_week`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `week_number` |
| output columns | `week_number`, `total_sales` |
| source tables | `cleaned_weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Aggregates sales amount by week for each year.

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
    T1.week_number,
    SUM(T1.sales) AS total_sales
FROM cleaned_weekly_sales AS T1
GROUP BY T1.week_number
```

---

## Skill `sales_by_time_window`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `sales_amount`, `time_window` |
| output columns | `sales_amount`, `time_window` |
| source tables | `cleaned_weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `sales_by_attribute` |

### Description

Calculate sales for each time window (12 weeks before and after June 15, 2020).

### Semantic filters

```json
{
  "column": "week_date",
  "value": "between DATE('2020-06-15', '-12 weeks') AND DATE('2020-06-15', '+12 weeks')"
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
    t1.sales_amount,
    t1.time_window
FROM (
    SELECT
        CASE
            WHEN week_date BETWEEN DATE('2020-06-15', '-12 weeks') AND DATE('2020-06-15') THEN '12 weeks before June 15, 2020'
            WHEN week_date BETWEEN DATE('2020-06-15') AND DATE('2020-06-15', '+1 week') THEN 'June 15, 2020 - 0 weeks'
            WHEN week_date BETWEEN DATE('2020-06-15', '+1 week') AND DATE('2020-06-15', '+12 weeks') THEN 'June 15, 2020 - 12 weeks'
            ELSE 'Other'
        END AS time_window,
        SUM(sales) AS sales_amount
    FROM cleaned_weekly_sales
    WHERE week_date BETWEEN DATE('2020-06-15', '-12 weeks') AND DATE('2020-06-15', '+12 weeks')
    GROUP BY time_window
) t1
```

---

## Skill `sales_by_attribute`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `attribute_type` |
| output columns | `attribute_type`, `average_percentage_change` |
| source tables | `cleaned_weekly_sales` |
| depends_on (builds on) | `sales_by_time_window` |
| depended-on by (builds on this) | — |

### Description

Aggregate sales by attribute type (region, platform, age band, demographic, and customer type).

### Semantic filters

```json
{
  "time_window": "sales_by_time_window"
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
    'region' AS attribute_type,
    AVG(sales) AS average_percentage_change
FROM
    cleaned_weekly_sales
GROUP BY
    attribute_type
```

---
