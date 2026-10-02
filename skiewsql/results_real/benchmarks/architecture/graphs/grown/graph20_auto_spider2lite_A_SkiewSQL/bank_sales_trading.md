# Skill graph — `bank_sales_trading` (6 skills)

**Skill `focused_whole_view`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `customer_transactions`, `weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 9 |

_Task: Calculate the month-end balance for each customer in 2020, identify the months with the highest and lowest customer counts having a positive balance, and then compute the average month-end balan_

```sql
SELECT
  c_t."txn_date",
  c_t."txn_amount",
  c_t."txn_type",
  w_s."sales",
  w_s."transactions"
FROM customer_transactions AS c_t
JOIN weekly_sales AS w_s
  ON c_t."txn_date" = w_s."week_date"
WHERE
  STRFTIME('%Y', c_t."txn_date") = '2020'
```

---

**Skill `monthly_balances_calculated`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `Month` |
| output columns | `Month`, `Total Balance` |
| source tables | `weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `final_monthly_balances` |
| validated_on | — |
| counter_examples | 0 |

_Calculate the total balance for each month based on the previous month's balance, replacing negative balances with zero._

```sql
SELECT
    'Month' AS Month,
    SUM(CASE WHEN strftime('%Y-%m', week_date) = strftime('%Y-%m', 'Month - 1') THEN 0 ELSE sales END) AS "Total Balance"
FROM weekly_sales
WHERE strftime('%Y-%m', week_date) <> strftime('%Y-%m', 'Month - 1')
```

---

**Skill `final_monthly_balances`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `Month` |
| output columns | `Month`, `Total Balance` |
| source tables | `cleaned_weekly_sales` |
| depends_on (builds on) | `monthly_balances_calculated` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Clean and format the calculated balances for the final output._

```sql
SELECT
    CAST(strftime('%Y-%m', week_date_formatted) AS TEXT) AS "Month",
    SUM("Total Balance") AS "Total Balance"
FROM
    cleaned_weekly_sales
GROUP BY
    "Month"
```

---

**Skill `btc_purchases_yearly`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `year`, `member_id` |
| output columns | `year`, `region`, `total_btc_amount`, `total_btc_quantity` |
| source tables | `bitcoin_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `btc_avg_price_yearly` |
| validated_on | — |
| counter_examples | 0 |

_Calculate total Bitcoin purchase amount and quantity for each year and region._

```sql
SELECT
    STRFTIME('%Y', txn_date) AS year,
    member_id AS region,
    SUM(quantity) AS total_btc_quantity,
    SUM(quantity) AS total_btc_amount
FROM
    bitcoin_transactions
WHERE
    txn_date >= '2023-01-01'
GROUP BY
    year,
    member_id
```

---

**Skill `btc_avg_price_yearly`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `year`, `region` |
| output columns | `year`, `region`, `avg_btc_price` |
| source tables | `btc_purchases_yearly` |
| depends_on (builds on) | `btc_purchases_yearly` |
| depended-on by (builds on this) | `btc_price_change_yearly` |
| validated_on | — |
| counter_examples | 0 |

_Calculate the average purchase price per Bitcoin for each region for each year._

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

**Skill `btc_price_change_yearly`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `year`, `region` |
| output columns | `year`, `region`, `price_change_percent` |
| source tables | `btc_avg_price_yearly`, `customer_regions` |
| depends_on (builds on) | `btc_avg_price_yearly` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculate the percentage change in average Bitcoin price compared to the previous year for each region._

```sql
SELECT
    strftime('%Y', btc_avg_price_yearly.year) AS year,
    customer_regions.region_name AS region,
    CAST((btc_avg_price_yearly.avg_btc_price - btc_avg_price_yearly.avg_btc_price) / btc_avg_price_yearly.avg_btc_price AS REAL) * 100 AS price_change_percent
FROM btc_avg_price_yearly
JOIN customer_regions ON btc_avg_price_yearly.region = customer_regions.region_id
```

---
