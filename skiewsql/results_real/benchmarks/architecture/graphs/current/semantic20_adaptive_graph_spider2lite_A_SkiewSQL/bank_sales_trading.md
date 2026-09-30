# Skill graph — `bank_sales_trading` (12 skills)

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
    SUM(sales) OVER (PARTITION BY "month_number" ORDER BY "month_number" ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS "Initial Balance"
FROM cleaned_weekly_sales
WHERE "month_number" = 1
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
| depended-on by (builds on this) | `monthly_rolling_averages` |

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

## Skill `monthly_rolling_averages`

Category: `WIN`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month` |
| output columns | `month`, `customer_id`, `rolling_average_balance` |
| source tables | `customer_transactions` |
| depends_on (builds on) | `daily_transactions` |
| depended-on by (builds on this) | — |

### Description

Calculates the 30-day rolling average balance for each customer, excluding the first month.

### Semantic filters

```json
{
  "customer_id": "",
  "month": ""
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
    DATE('month') AS month,
    customer_id,
    AVG(txn_amount) AS rolling_average_balance
FROM customer_transactions
WHERE txn_date BETWEEN DATE('month', '-30 days') AND DATE('month')
GROUP BY customer_id, DATE('month')
```

---

## Skill `chunk_view_0`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `bitcoin_transactions`, `shopping_cart_users`, `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Task: Calculate the view count, cart addition count, abandoned cart count, and purchase count for each product, excluding products with page IDs 1, 2, 12, and 13. Required outputs: The number of times

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

- Identify the top 10 and bottom 10 interest categories based on their highest composition values across all months. For each category, display the time(MM-YYYY), interest name, and the composition value

### Executable SQL body

```sql
SELECT
    'bitcoin_transactions'.ticker,
    COUNT(shopping_cart_users.cookie_id) AS "cart_addition_count",
    COUNT(shopping_cart_users.cookie_id) AS "abandoned_cart_count",
    COUNT(customer_transactions.customer_id) AS "purchase_count"
FROM
    bitcoin_transactions
JOIN
    shopping_cart_users
    ON bitcoin_transactions.member_id = shopping_cart_users.cookie_id
JOIN
    customer_transactions
    ON shopping_cart_users.user_id = customer_transactions.customer_id
WHERE
    bitcoin_transactions.txn_id NOT IN (1, 2, 12, 13)
GROUP BY
    bitcoin_transactions.ticker
```

---

## Skill `chunk_view_1`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | — |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Task: Calculate the view count, cart addition count, abandoned cart count, and purchase count for each product, excluding products with page IDs 1, 2, 12, and 13. Required outputs: The number of times

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
    sp.page_id,
    COUNT(se.page_id) AS view_count,
    COUNT(DISTINCT se.visit_id) AS cart_addition_count,
    COUNT(DISTINCT se.visit_id) AS abandoned_cart_count,
    COUNT(DISTINCT se.visit_id) AS purchase_count
FROM shopping_cart_page_hierarchy sp
JOIN shopping_cart_events se ON sp.page_id = se.page_id
WHERE sp.page_id NOT IN (1, 2, 12, 13)
GROUP BY sp.page_id
```

---

## Skill `monthly_interest_data`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `date`, `interest_name`, `index_composition` |
| output columns | `date`, `interest_name`, `index_composition` |
| source tables | `interest_metrics`, `interest_map` |
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
    DATE(t1.month_year) AS date,
    t2.interest_name AS interest_name,
    t3.index_value AS index_composition
FROM
    interest_metrics AS t3
INNER JOIN
    interest_map AS t2
    ON t2.id = t3.interest_id
INNER JOIN
    (SELECT month_year FROM interest_metrics GROUP BY month_year) AS t1
    ON t1.month_year = t3.month_year
```

---

## Skill `rolling_average_composites`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `interest_name` |
| output columns | `date`, `interest_name`, `rolling_average_max_composition` |
| source tables | `interest_map`, `interest_metrics` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Calculates the three-month rolling average of the maximum index composition.

### Semantic filters

```json
{
  "_month": ">=7.0"
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

## Skill `btc_purchases_yearly`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `year`, `region` |
| output columns | `year`, `region`, `total_btc_amount`, `total_btc_quantity` |
| source tables | `bitcoin_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `btc_avg_price_yearly` |

### Description

Calculate total Bitcoin purchase amount and quantity for each year and region.

### Semantic filters

```json
{
  "year": ">= 2023"
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
    substr(member_id, 1, 1) AS region,
    sum(quantity) AS total_btc_amount,
    sum(quantity) AS total_btc_quantity
FROM
    bitcoin_transactions
WHERE
    txn_date >= '2023-01-01'
GROUP BY
    year,
    substr(member_id, 1, 1)
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
    AVG(btc_purchases_yearly.total_btc_amount / btc_purchases_yearly.total_btc_quantity) AS avg_btc_price
FROM
    btc_purchases_yearly
GROUP BY
    btc_purchases_yearly.year,
    btc_purchases_yearly.region
```

---

## Skill `weekly_sales_2018_2020`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `week_date_formatted` |
| output columns | `date`, `sales_amount` |
| source tables | `cleaned_weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Selects weekly sales data for the years 2018, 2019, and 2020.

### Semantic filters

```json
{
  "column": "calendar_year",
  "value": "[2018, 2019, 2020]"
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
    cwd.week_date_formatted AS date,
    SUM(cwd.sales) AS sales_amount
FROM cleaned_weekly_sales AS cwd
WHERE cwd.calendar_year IN (2018, 2019, 2020)
GROUP BY cwd.week_date_formatted
```

---

## Skill `calculate_percentage_change`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `year` |
| output columns | `year`, `percentage_change` |
| source tables | `cleaned_weekly_sales`, `cleaned_weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Calculates the percentage change in sales between the four weeks preceding and the four weeks following June 15.

### Semantic filters

```json
{
  "column": "calendar_year"
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
    t1."calendar_year" AS year,
    (t1."sales" - t2."sales") * 100.0 / t2."sales" AS percentage_change
FROM
    "cleaned_weekly_sales" t1
INNER JOIN
    "cleaned_weekly_sales" t2
ON
    t1."week_date" = t2."week_date" AND t1."calendar_year" = t2."calendar_year"
WHERE
    t1."week_date" BETWEEN (SELECT "week_date" FROM "cleaned_weekly_sales" WHERE "calendar_year" = 2020 AND "week_date" BETWEEN ('2020-06-01') AND ('2020-06-30')) AND (SELECT "week_date" FROM "cleaned_weekly_sales" WHERE "calendar_year" = 2020 AND "week_date" BETWEEN ('2020-07-01') AND ('2020-07-31'))
```

---
