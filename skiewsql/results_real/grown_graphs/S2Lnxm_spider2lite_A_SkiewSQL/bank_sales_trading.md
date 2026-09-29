# Skill graph — `bank_sales_trading` (54 skills)

**Skill `customers_cohort`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customer_monthly_closing_and_running`, `all_customers` |
| validated_on | — |
| counter_examples | 0 |

_All valid customers to include in the report (exclude any non-existent customers). This is the master list of customers that will be reported for every month in the period._

```sql
SELECT DISTINCT customer_id
FROM customer_transactions
WHERE customer_id IS NOT NULL
```

---

**Skill `month_range`** — category `SEM`

| field | value |
|---|---|
| grain (one row per) | `year_month` |
| output columns | `year_month`, `month_start_date`, `month_end_date` |
| source tables | `customer_transactions`, `bitcoin_transactions`, `cleaned_weekly_sales`, `veg_whsle_df`, `veg_txn_df`, `weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customer_monthly_closing_and_running`, `all_customers`, `monthly_summary_with_universe`, `prior_month_balances_per_user`, `monthly_customer_max_balance`, `monthly_max_interest` |
| validated_on | — |
| counter_examples | 0 |

_Continuous list of year-month periods that define the report range. If explicit start/end months are provided use them; otherwise derive start = min(transaction_date) and end = max(transaction_date) from the transactions dataset, then expand to every month in between (inclusive)._

```sql
SELECT
  strftime('%Y-%m', month_dt) AS year_month,
  date(month_dt, 'start of month') AS month_start_date,
  date(month_dt, 'start of month', '+1 month', '-1 day') AS month_end_date
FROM (
  SELECT date(min_dt, printf('-%02d-01', 1)) AS month_dt FROM (
    SELECT
      date(
        substr(min_txn, 1, 4) || '-' || substr(min_txn, 6, 2) || '-01'
      ) AS min_dt
    FROM (
      SELECT
        MIN(
          COALESCE(
            (SELECT MIN(txn_date) FROM customer_transactions),
            (SELECT MIN(txn_date) FROM bitcoin_transactions),
            (SELECT MIN(week_date) FROM cleaned_weekly_sales),
            (SELECT MIN(whsle_date) FROM veg_whsle_df),
            (SELECT MIN(txn_date) FROM veg_txn_df),
            (SELECT MIN(week_date) FROM weekly_sales)
          )
        ) AS min_txn
    )
  )
  UNION ALL
  SELECT date(month_dt, '+' || n || ' months') FROM (
    SELECT
      (SELECT date(min_dt) FROM (
         SELECT date(
           substr(min_txn, 1, 4) || '-' || substr(min_txn, 6, 2) || '-01'
         ) AS min_dt
         FROM (
           SELECT
             MIN(
               COALESCE(
                 (SELECT MIN(txn_date) FROM customer_transactions),
                 (SELECT MIN(txn_date) FROM bitcoin_transactions),
                 (SELECT MIN(week_date) FROM cleaned_weekly_sales),
                 (SELECT MIN(whsle_date) FROM veg_whsle_df),
                 (SELECT MIN(txn_date) FROM veg_txn_df),
                 (SELECT MIN(week_date) FROM weekly_sales)
               )
             ) AS min_txn
         )
      )) AS month_dt,
      n
    FROM (
      SELECT 0 AS n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5
      UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10 UNION ALL SELECT 11
      UNION ALL SELECT 12 UNION ALL SELECT 13 UNION ALL SELECT 14 UNION ALL SELECT 15 UNION ALL SELECT 16 UNION ALL SELECT 17
      UNION ALL SELECT 18 UNION ALL SELECT 19 UNION ALL SELECT 20 UNION ALL SELECT 21 UNION ALL SELECT 22 UNION ALL SELECT 23
      UNION ALL SELECT 24 UNION ALL SELECT 25 UNION ALL SELECT 26 UNION ALL SELECT 27 UNION ALL SELECT 28 UNION ALL SELECT 29
      UNION ALL SELECT 30 UNION ALL SELECT 31 UNION ALL SELECT 32 UNION ALL SELECT 33 UNION ALL SELECT 34 UNION ALL SELECT 35
      UNION ALL SELECT 36 UNION ALL SELECT 37 UNION ALL SELECT 38 UNION ALL SELECT 39 UNION ALL SELECT 40 UNION ALL SELECT 41
      UNION ALL SELECT 42 UNION ALL SELECT 43 UNION ALL SELECT 44 UNION ALL SELECT 45 UNION ALL SELECT 46 UNION ALL SELECT 47
      UNION ALL SELECT 48 UNION ALL SELECT 49 UNION ALL SELECT 50 UNION ALL SELECT 51 UNION ALL SELECT 52 UNION ALL SELECT 53
      UNION ALL SELECT 54 UNION ALL SELECT 55 UNION ALL SELECT 56 UNION ALL SELECT 57 UNION ALL SELECT 58 UNION ALL SELECT 59
      UNION ALL SELECT 60
    )
    WHERE date(month_dt, '+' || n || ' months') <= (
      SELECT date(
        substr(max_txn, 1, 4) || '-' || substr(max_txn, 6, 2) || '-01'
      , '+1 month', '-1 day')
      FROM (
        SELECT
          MAX(
            COALESCE(
              (SELECT MAX(txn_date) FROM customer_transactions),
              (SELECT MAX(txn_date) FROM bitcoin_transactions),
              (SELECT MAX(week_date) FROM cleaned_weekly_sales),
              (SELECT MAX(whsle_date) FROM veg_whsle_df),
              (SELECT MAX(txn_date) FROM veg_txn_df),
              (SELECT MAX(week_date) FROM weekly_sales)
            )
          ) AS max_txn
      )
    )
  )
)
GROUP BY year_month
```

---

**Skill `transactions_monthly_balances`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `year_month` |
| output columns | `customer_id`, `year_month`, `monthly_net_change`, `closing_balance_from_activity`, `last_transaction_date_in_month` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customer_monthly_closing_and_running`, `all_customers` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate transactions per customer and per month to compute activity and end-of-month closing balance implied by transactions in that month. This produces a closing balance for months with activity; months without transactions will be filled later by carrying forward prior balance._

```sql
SELECT
  ct.customer_id,
  substr(ct.txn_date,1,7) AS year_month,
  SUM(ct.txn_amount * CASE WHEN ct.txn_type = 'deposit' THEN 1 WHEN ct.txn_type = 'withdrawal' THEN -1 ELSE 0 END) AS monthly_net_change,
  SUM(ct.txn_amount * CASE WHEN ct.txn_type = 'deposit' THEN 1 WHEN ct.txn_type = 'withdrawal' THEN -1 ELSE 0 END) AS closing_balance_from_activity,
  MAX(ct.txn_date) AS last_transaction_date_in_month
FROM customer_transactions ct
GROUP BY ct.customer_id, substr(ct.txn_date,1,7)
```

---

**Skill `customer_monthly_closing_and_running`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `year_month` |
| output columns | `customer_id`, `year_month`, `closing_balance`, `monthly_change`, `cumulative_closing_balance` |
| source tables | `customers_cohort`, `month_range`, `transactions_monthly_balances` |
| depends_on (builds on) | `customers_cohort`, `month_range`, `transactions_monthly_balances` |
| depended-on by (builds on this) | `all_customers` |
| validated_on | — |
| counter_examples | 0 |

_Cartesian-join customers_cohort to month_range to ensure every customer×month row, left-join monthly activity balances, then fill forward prior closing balances for months with no activity, compute month-over-month change (difference vs previous month's closing balance) and compute cumulative running total of closing balances from the start of the report period per customer (running sum of closing_balance)._

```sql
SELECT
  c.customer_id AS customer_id,
  m.year_month AS year_month,
  -- closing_balance: carry closing_balance_from_activity if present, else forward-fill from prior months per customer
  COALESCE(t.closing_balance_from_activity, 
           -- get the most recent prior non-null closing_balance_from_activity for this customer
           (SELECT tp.closing_balance_from_activity
            FROM transactions_monthly_balances tp
            WHERE tp.customer_id = c.customer_id
              AND tp.year_month <= m.year_month
              AND tp.closing_balance_from_activity IS NOT NULL
            ORDER BY tp.year_month DESC
            LIMIT 1)
          ) AS closing_balance,
  -- monthly_change: difference between this month's closing_balance and previous month's closing_balance (may be NULL if no prior)
  COALESCE(
    COALESCE(t.closing_balance_from_activity,
             (SELECT tp.closing_balance_from_activity
              FROM transactions_monthly_balances tp
              WHERE tp.customer_id = c.customer_id
                AND tp.year_month <= m.year_month
                AND tp.closing_balance_from_activity IS NOT NULL
              ORDER BY tp.year_month DESC
              LIMIT 1)
            )
    -
    (SELECT COALESCE(prev.closing_balance_from_activity,
                     (SELECT pprev.closing_balance_from_activity
                      FROM transactions_monthly_balances pprev
                      WHERE pprev.customer_id = c.customer_id
                        AND pprev.year_month < m.year_month
                        AND pprev.closing_balance_from_activity IS NOT NULL
                      ORDER BY pprev.year_month DESC
                      LIMIT 1))
     FROM transactions_monthly_balances prev
     WHERE prev.customer_id = c.customer_id
       AND prev.year_month < m.year_month
     ORDER BY prev.year_month DESC
     LIMIT 1
    ),
    NULL
  ) AS monthly_change,
  -- cumulative_closing_balance: running sum of the closing_balance from the start of month_range up to current month for this customer
  (SELECT SUM(
            COALESCE(tp2.closing_balance_from_activity,
                     (SELECT tp_prior.closing_balance_from_activity
                      FROM transactions_monthly_balances tp_prior
                      WHERE tp_prior.customer_id = c.customer_id
                        AND tp_prior.year_month <= tp2.year_month
                        AND tp_prior.closing_balance_from_activity IS NOT NULL
                      ORDER BY tp_prior.year_month DESC
                      LIMIT 1)
                    )
          )
   FROM month_range mr2
   LEFT JOIN transactions_monthly_balances tp2
     ON tp2.customer_id = c.customer_id
     AND tp2.year_month = mr2.year_month
   WHERE mr2.year_month <= m.year_month
  ) AS cumulative_closing_balance
FROM customers_cohort c
CROSS JOIN month_range m
LEFT JOIN transactions_monthly_balances t
  ON t.customer_id = c.customer_id
  AND t.year_month = m.year_month
```

---

**Skill `all_customers`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id` |
| source tables | `customer_transactions`, `customer_nodes` |
| depends_on (builds on) | `customers_cohort`, `month_range`, `transactions_monthly_balances`, `customer_monthly_closing_and_running` |
| depended-on by (builds on this) | `monthly_summary_with_universe`, `prior_month_balances_per_user` |
| validated_on | — |
| counter_examples | 0 |

_All distinct customers in the dataset. This relation is the universe of customers to include when computing per-month averages and counts (customers with no transactions still appear here)._

```sql
SELECT DISTINCT customer_id
FROM (
  SELECT customer_id FROM customer_transactions
  UNION
  SELECT customer_id FROM customer_nodes
)
```

---

**Skill `transactions_2020`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `transaction_id` |
| output columns | `transaction_id`, `customer_id`, `transaction_date`, `month_id`, `deposit_amount`, `withdrawal_amount` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All transaction rows that occur within the inclusive date range 2020-01-01 through 2020-12-31, with normalized fields indicating deposit and withdrawal amounts and a month identifier (e.g., '2020-01'). Do not aggregate here; keep one row per transaction._

```sql
SELECT
  row_number() OVER (ORDER BY txn_date, customer_id, txn_type, txn_amount) AS transaction_id,
  customer_id,
  txn_date AS transaction_date,
  substr(txn_date,1,7) AS month_id,
  CASE WHEN lower(txn_type) = 'deposit' THEN txn_amount ELSE 0 END AS deposit_amount,
  CASE WHEN lower(txn_type) = 'withdrawal' THEN txn_amount ELSE 0 END AS withdrawal_amount
FROM customer_transactions
WHERE txn_date BETWEEN '2020-01-01' AND '2020-12-31'
```

---

**Skill `customer_month_balances`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `year_month` |
| output columns | `customer_id`, `month_id`, `month_end_balance` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `monthly_summary_with_universe` |
| validated_on | — |
| counter_examples | 0 |

_Per-customer, per-month balances for each calendar month in 2020: sum of deposits in that month minus sum of withdrawals in that month. Include months where a customer had no transactions by later joining to all months and all customers (this relation itself is only rows for customer-months that have transactions)._

```sql
SELECT
  ct.customer_id AS customer_id,
  mr.year_month AS month_id,
  COALESCE(SUM(
    CASE LOWER(ct.txn_type)
      WHEN 'deposit' THEN ct.txn_amount
      WHEN 'withdrawal' THEN -ct.txn_amount
      ELSE 0
    END
  ), 0) AS month_end_balance
FROM customer_transactions ct
JOIN (
  SELECT DISTINCT year_month
  FROM (
    SELECT substr(txn_date,1,7) AS year_month FROM customer_transactions
  )
) mr ON substr(ct.txn_date,1,7) = mr.year_month
GROUP BY ct.customer_id, mr.year_month
```

---

**Skill `monthly_summary_with_universe`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `year_month` |
| output columns | `month_id`, `positive_customer_count`, `average_month_end_balance` |
| source tables | `month_range`, `all_customers`, `customer_month_balances` |
| depends_on (builds on) | `month_range`, `all_customers`, `customer_month_balances` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For every customer and every month of 2020 (cartesian of all_customers x the 12 month_ids), attach the month_end_balance (use zero where no transaction-derived balance exists). Then for each month compute: the count of customers with month_end_balance > 0 and the average of month_end_balance across all customers._

```sql
SELECT
  m.year_month AS month_id,
  SUM(CASE WHEN COALESCE(b.month_end_balance,0) > 0 THEN 1 ELSE 0 END) AS positive_customer_count,
  AVG(COALESCE(b.month_end_balance,0)) AS average_month_end_balance
FROM month_range m
CROSS JOIN all_customers c
LEFT JOIN customer_month_balances b
  ON b.customer_id = c.customer_id
  AND b.month_id = m.year_month
GROUP BY m.year_month
```

---

**Skill `customer_monthly_transactions`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `transaction_id` |
| output columns | `customer_id`, `transaction_id`, `transaction_date`, `month_start`, `signed_amount` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `monthly_net_per_customer` |
| validated_on | — |
| counter_examples | 0 |

_All deposit and withdrawal transactions normalized to a month bucket: one row per transaction with customer id, transaction date, month_start (the first day of the transaction's month), and signed_amount (deposits positive, withdrawals negative). Only include transactions that can be assigned to a month._

```sql
SELECT
  rowid AS transaction_id,
  customer_id AS customer_id,
  txn_date AS transaction_date,
  substr(txn_date, 1, 7) || '-01' AS month_start,
  CASE
    WHEN lower(txn_type) = 'deposit' THEN txn_amount
    WHEN lower(txn_type) = 'withdrawal' THEN -txn_amount
    ELSE NULL
  END AS signed_amount
FROM customer_transactions
WHERE txn_date IS NOT NULL
  AND length(txn_date) >= 7
  AND (lower(txn_type) = 'deposit' OR lower(txn_type) = 'withdrawal')
  AND txn_amount IS NOT NULL
```

---

**Skill `monthly_net_per_customer`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month_start` |
| output columns | `customer_id`, `month_start`, `monthly_net` |
| source tables | `customer_transactions`, `customer_monthly_transactions` |
| depends_on (builds on) | `customer_monthly_transactions` |
| depended-on by (builds on this) | `customer_monthly_closing_balances` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate the normalized transactions to compute each customer's monthly net amount by summing signed_amounts for each month_start._

```sql
SELECT
  ct.customer_id,
  cmt.month_start AS month_start,
  SUM(cmt.signed_amount) AS monthly_net
FROM
  customer_transactions ct
JOIN
  customer_monthly_transactions cmt
  ON ct.customer_id = cmt.customer_id
GROUP BY
  ct.customer_id,
  cmt.month_start
```

---

**Skill `customer_monthly_closing_balances`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month_start` |
| output columns | `customer_id`, `month_start`, `monthly_net`, `closing_balance`, `month_rank` |
| source tables | `customer_transactions`, `monthly_net_per_customer` |
| depends_on (builds on) | `monthly_net_per_customer` |
| depended-on by (builds on this) | `most_recent_growth_per_customer` |
| validated_on | — |
| counter_examples | 0 |

_For each customer and month (ordered chronologically by month_start), compute the closing balance as the running cumulative sum of monthly_net up to and including that month. Keep months even if monthly_net is zero if they exist in the sequence._

```sql
SELECT
  m.customer_id,
  m.month_start,
  COALESCE(n.monthly_net, 0) AS monthly_net,
  SUM(COALESCE(n.monthly_net, 0)) OVER (PARTITION BY m.customer_id ORDER BY m.month_start ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS closing_balance,
  ROW_NUMBER() OVER (PARTITION BY m.customer_id ORDER BY m.month_start) AS month_rank
FROM
  monthly_net_per_customer AS n
RIGHT JOIN
  (
    SELECT customer_id, month_start
    FROM monthly_net_per_customer
    UNION
    SELECT customer_id, month_start
    FROM monthly_net_per_customer
  ) AS m
ON m.customer_id = n.customer_id AND m.month_start = n.month_start
```

---

**Skill `most_recent_growth_per_customer`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `most_recent_month_start`, `most_recent_closing_balance`, `prior_month_start`, `prior_closing_balance`, `has_prior_month`, `growth_rate` |
| source tables | `customer_monthly_closing_balances` |
| depends_on (builds on) | `customer_monthly_closing_balances` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each customer, identify the most recent month (latest month_start) and its prior month (immediately previous month_start for that customer). Produce most_recent_closing_balance, prior_closing_balance, and compute growth_rate per the rule: if prior_closing_balance = 0 then growth_rate = most_recent_closing_balance * 100 else growth_rate = (most_recent_closing_balance - prior_closing_balance) / prior_closing_balance. Also include a flag indicating whether the customer has a prior month. Do not collapse customers with only one month unless downstream filter applies._

```sql
SELECT
  cmc.customer_id,
  cmc.month_start AS most_recent_month_start,
  cmc.closing_balance AS most_recent_closing_balance,
  prev.month_start AS prior_month_start,
  prev.closing_balance AS prior_closing_balance,
  CASE WHEN prev.customer_id IS NOT NULL THEN 1 ELSE 0 END AS has_prior_month,
  CASE
    WHEN prev.customer_id IS NULL THEN NULL
    WHEN prev.closing_balance = 0 THEN cmc.closing_balance * 100.0
    ELSE (cmc.closing_balance - prev.closing_balance) / prev.closing_balance
  END AS growth_rate
FROM customer_monthly_closing_balances cmc
LEFT JOIN customer_monthly_closing_balances prev
  ON cmc.customer_id = prev.customer_id
  AND prev.month_rank = cmc.month_rank - 1
WHERE cmc.month_rank = (
  SELECT MAX(month_rank) FROM customer_monthly_closing_balances m2
  WHERE m2.customer_id = cmc.customer_id
)
```

---

**Skill `balance_snapshots_on_first_of_month`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `user_id`, `snapshot_month` |
| output columns | `user_id`, `snapshot_month`, `snapshot_date`, `balance` |
| source tables | `shopping_cart_users` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `normalized_balances` |
| validated_on | — |
| counter_examples | 0 |

_Select balance snapshot records that represent each user's balance as of the first day of each month (rows whose snapshot date is the 1st of some month). Do not apply month-exclusion logic here._

```sql
SELECT
  scu.user_id AS user_id,
  strftime('%Y-%m', date(scu.start_date)) AS snapshot_month,
  date(scu.start_date) AS snapshot_date,
  0.0 AS balance
FROM shopping_cart_users scu
WHERE strftime('%d', date(scu.start_date)) = '01'
```

---

**Skill `normalized_balances`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `user_id`, `month` |
| output columns | `user_id`, `month`, `balance` |
| source tables | `balance_snapshots_on_first_of_month` |
| depends_on (builds on) | `balance_snapshots_on_first_of_month` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Normalize/clean the snapshot balances and canonicalize the month identifier; produce a per-user-per-month balance value where balance is cast to a numeric and missing balances are handled. Do NOT apply the negative-to-zero rule here (that is an aggregation-time rule), only ensure types and canonical month representation._

```sql
SELECT
  b.user_id AS user_id,
  -- canonicalize month as YYYY-MM (attempt ISO YYYY-MM from snapshot_month or snapshot_date)
  COALESCE(
    -- if snapshot_month already like 'YYYY-MM' or 'YYYY-M' or 'YYYYMM', try to normalize using substrings
    CASE
      WHEN length(b.snapshot_month) = 7 AND substr(b.snapshot_month,5,1) = '-' THEN b.snapshot_month
      WHEN length(b.snapshot_month) = 6 AND substr(b.snapshot_month,5,1) = '-' THEN b.snapshot_month
      WHEN length(b.snapshot_month) = 6 AND b.snapshot_month GLOB '[0-9][0-9][0-9][0-9][0-9][0-9]' THEN substr(b.snapshot_month,1,4) || '-' || substr(b.snapshot_month,5,2)
      WHEN length(b.snapshot_month) = 5 AND b.snapshot_month GLOB '[0-9][0-9][0-9][0-9][0-9]' THEN substr(b.snapshot_month,1,4) || '-' || substr(b.snapshot_month,5,1)
      ELSE NULL
    END,
    -- fallback: try to parse ISO-like date from snapshot_date 'YYYY-MM-DD' or 'YYYY/MM/DD'
    CASE
      WHEN b.snapshot_date IS NOT NULL AND length(b.snapshot_date) >= 7 AND (substr(b.snapshot_date,5,1) = '-' OR substr(b.snapshot_date,5,1) = '/') THEN substr(b.snapshot_date,1,4) || '-' || substr(b.snapshot_date,6,2)
      ELSE NULL
    END
  ) AS month,
  -- canonical numeric balance: try casting balance text to real; if null or empty produce NULL
  CASE
    WHEN b.balance IS NULL THEN NULL
    WHEN trim(b.balance) = '' THEN NULL
    ELSE CAST(replace(replace(replace(b.balance, ',', ''), '$', ''), ' ', '') AS REAL)
  END AS balance
FROM balance_snapshots_on_first_of_month b
```

---

**Skill `prior_month_balances_per_user`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `month`, `user_id` |
| output columns | `month`, `user_id`, `prior_month_balance` |
| source tables | `month_range`, `all_customers`, `customer_transactions` |
| depends_on (builds on) | `month_range`, `all_customers` |
| depended-on by (builds on this) | `monthly_previous_month_total_balance` |
| validated_on | — |
| counter_examples | 0 |

_For each target month M (every month present in data except none), attach each user's balance as of the first day of the previous month (M-1). This produces one row per (target month, user) pairing with the user's balance measured on M-1 first day (if present)._

```sql
SELECT
  mr.year_month AS month,
  c.customer_id AS user_id,
  -- balance as of the first day of the previous month:
  -- find latest transaction date strictly before month_start (i.e., before first day of target month)
  COALESCE(
    (
      SELECT SUM(
        CASE txn.txn_type
          WHEN 'deposit' THEN txn.txn_amount
          WHEN 'withdrawal' THEN -txn.txn_amount
          ELSE txn.txn_amount
        END
      )
      FROM customer_transactions AS txn
      WHERE txn.customer_id = c.customer_id
        AND date(txn.txn_date) < date(mr.month_start_date)
    ),
    0
  ) AS prior_month_balance
FROM
  month_range AS mr
CROSS JOIN
  all_customers AS c
```

---

**Skill `monthly_previous_month_total_balance`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `month` |
| output columns | `month`, `previous_month_total_balance` |
| source tables | `prior_month_balances_per_user` |
| depends_on (builds on) | `prior_month_balances_per_user` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each target month, sum the per-user prior-month balances but treat any individual negative balance as zero before summing. Exclude the very first available month in the dataset from the final output (because it has no prior month to report)._

```sql
SELECT
  p.month AS month,
  SUM(
    CASE
      WHEN COALESCE(p.prior_month_balance, 0) < 0 THEN 0
      ELSE COALESCE(p.prior_month_balance, 0)
    END
  ) AS previous_month_total_balance
FROM prior_month_balances_per_user p
GROUP BY p.month
HAVING COUNT(*) > 0
```

---

**Skill `raw_transactions_by_day`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `transaction_date`, `transaction_id` |
| output columns | `customer_id`, `transaction_date`, `signed_amount` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select raw transaction events normalized to one row per customer per transaction with amount signed: deposits as positive, all other transaction types negated, plus transaction date. Filter to transactions with non-null customer and date._

```sql
SELECT
  customer_id,
  txn_date AS transaction_date,
  CASE
    WHEN txn_type = 'deposit' THEN txn_amount
    ELSE -txn_amount
  END AS signed_amount,
  rowid AS transaction_id
FROM customer_transactions
WHERE customer_id IS NOT NULL
  AND txn_date IS NOT NULL
```

---

**Skill `daily_balances`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `txn_date` |
| output columns | `customer_id`, `day_date`, `daily_balance` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customer_30day_rolling_avg`, `monthly_customer_max_balance` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate signed transactions to compute each customer's daily balance (sum of signed amounts per customer per calendar day)._

```sql
SELECT
  customer_id,
  txn_date AS day_date,
  SUM(
    CASE
      WHEN txn_type = 'deposit' THEN txn_amount
      WHEN txn_type = 'withdrawal' THEN -txn_amount
      ELSE txn_amount
    END
  ) AS daily_balance
FROM customer_transactions
GROUP BY customer_id, txn_date
```

---

**Skill `customer_30day_rolling_avg`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `day_date` |
| output columns | `customer_id`, `day_date`, `rolling_30day_avg_nonneg` |
| source tables | `daily_balances` |
| depends_on (builds on) | `daily_balances` |
| depended-on by (builds on this) | `monthly_customer_max_30day_and_exclude_first_month` |
| validated_on | — |
| counter_examples | 0 |

_For each customer and day, compute the 30-day rolling average of daily_balance looking at that day and the prior 29 days. Only produce rows for days where the customer has at least 30 days of daily_balance history (i.e., full 30-day window). Replace negative rolling averages with zero (i.e., floor at 0)._

```sql
SELECT
  db.customer_id AS customer_id,
  db.day_date AS day_date,
  -- compute 30-day rolling average including current day and prior 29 days
  (
    SELECT AVG(db2.daily_balance)
    FROM daily_balances db2
    WHERE db2.customer_id = db.customer_id
      AND date(substr(db2.day_date, 1, 10)) BETWEEN date(substr(db.day_date, 1, 10), '-29 days') AND date(substr(db.day_date, 1, 10))
  ) AS rolling_30day_avg_nonneg
FROM daily_balances db
WHERE
  -- ensure there are at least 30 days in the window for this customer ending on this day
  (
    SELECT COUNT(1)
    FROM daily_balances db3
    WHERE db3.customer_id = db.customer_id
      AND date(substr(db3.day_date, 1, 10)) BETWEEN date(substr(db.day_date, 1, 10), '-29 days') AND date(substr(db.day_date, 1, 10))
  ) >= 30
```

---

**Skill `monthly_customer_max_30day_and_exclude_first_month`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month_year` |
| output columns | `customer_id`, `month_year`, `customer_month_max_30day_avg` |
| source tables | `customer_30day_rolling_avg` |
| depends_on (builds on) | `customer_30day_rolling_avg` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each customer and calendar month, compute the customer's maximum rolling_30day_avg_nonneg within that month, but exclude the customer's very first calendar month that contains any transaction (i.e., drop that month per customer). Produce one row per customer per month with the per-customer monthly maximum._

```sql
SELECT
  r.customer_id,
  substr(r.day_date,1,7) AS month_year,
  MAX(r.rolling_30day_avg_nonneg) AS customer_month_max_30day_avg
FROM customer_30day_rolling_avg AS r
JOIN (
  SELECT customer_id, MIN(substr(day_date,1,7)) AS first_month
  FROM customer_30day_rolling_avg
  GROUP BY customer_id
) AS firsts
  ON r.customer_id = firsts.customer_id
WHERE substr(r.day_date,1,7) <> firsts.first_month
GROUP BY r.customer_id, substr(r.day_date,1,7)
```

---

**Skill `customer_date_range`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `min_date`, `max_date` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `monthly_customer_max_balance` |
| validated_on | — |
| counter_examples | 0 |

_For each customer compute their inclusive date range: earliest transaction date and latest transaction date._

```sql
SELECT
  customer_id,
  MIN(txn_date) AS min_date,
  MAX(txn_date) AS max_date
FROM customer_transactions
GROUP BY customer_id
```

---

**Skill `monthly_customer_max_balance`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `year_month`, `customer_id` |
| output columns | `month_id`, `customer_id`, `customer_month_max_balance` |
| source tables | `month_range`, `customer_date_range`, `daily_balances` |
| depends_on (builds on) | `month_range`, `customer_date_range`, `daily_balances` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each customer and calendar month, compute the customer's maximum daily_balance_nonnegative within that month (ignore days outside the customer's date range)._

```sql
SELECT
  -- month identifier in YYYY-MM or year_month as in month_range / other views
  mr.year_month AS month_id,
  cd.customer_id AS customer_id,
  MAX(db.daily_balance) AS customer_month_max_balance
FROM
  month_range mr
JOIN
  customer_date_range cd
  ON cd.min_date <= mr.month_end_date
  AND cd.max_date >= mr.month_start_date
JOIN
  daily_balances db
  ON db.customer_id = cd.customer_id
  AND db.day_date >= mr.month_start_date
  AND db.day_date <= mr.month_end_date
GROUP BY
  mr.year_month,
  cd.customer_id
```

---

**Skill `events_filtered`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `event_id` |
| output columns | `event_id`, `event_type`, `product_id`, `user_id`, `session_id`, `timestamp`, `order_id`, `page_id`, `quantity` |
| source tables | `shopping_cart_events`, `shopping_cart_page_hierarchy`, `shopping_cart_users` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Subset of raw event rows excluding any events whose page id is in the banned set (1,2,12,13). Keep all columns necessary to classify event type, product identifier, and any order/purchase identifiers._

```sql
SELECT
  -- event unique id: compose from visit_id + sequence_number to ensure uniqueness per event row
  visit_id || ':' || CAST(sequence_number AS TEXT) AS event_id,
  event_type AS event_type,
  shopping_cart_page_hierarchy.product_id AS product_id,
  shopping_cart_users.user_id AS user_id,
  visit_id AS session_id,
  event_time AS timestamp,
  NULL AS order_id,
  shopping_cart_events.page_id AS page_id,
  NULL AS quantity
FROM shopping_cart_events
LEFT JOIN shopping_cart_page_hierarchy
  ON shopping_cart_events.page_id = shopping_cart_page_hierarchy.page_id
LEFT JOIN shopping_cart_users
  ON shopping_cart_events.cookie_id = shopping_cart_users.cookie_id
WHERE shopping_cart_events.page_id NOT IN (1, 2, 12, 13)
```

---

**Skill `product_event_flags`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `event_id` |
| output columns | `event_id`, `product_id`, `is_view`, `is_add_to_cart`, `is_purchase`, `user_id`, `session_id`, `timestamp`, `order_id`, `quantity` |
| source tables | `shopping_cart_events`, `shopping_cart_event_identifier`, `shopping_cart_page_hierarchy`, `shopping_cart_users` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `product_events_per_instance` |
| validated_on | — |
| counter_examples | 0 |

_Normalize and canonicalize event types for product-related actions (view, add_to_cart, purchase) and attach a single product identifier per event. Ensure event_type values are standardized and quantities are numeric._

```sql
SELECT
  e.event_id,
  -- canonical product_id: prefer event-level product_id, else page hierarchy product_id
  COALESCE(e.product_id, ph.product_id) AS product_id,
  -- normalized event flags based on shopping_cart_event_identifier mapping
  CASE WHEN ei.event_name IN ('Page View','View','Product View') THEN 1 ELSE 0 END AS is_view,
  CASE WHEN ei.event_name IN ('Add to Cart','AddToCart','Add') THEN 1 ELSE 0 END AS is_add_to_cart,
  CASE WHEN ei.event_name IN ('Purchase','Order Completed','Buy') THEN 1 ELSE 0 END AS is_purchase,
  -- carry user/session identifiers
  u.user_id AS user_id,
  e.session_id AS session_id,
  -- canonical timestamp
  e.timestamp AS timestamp,
  -- order identifier if present
  e.order_id AS order_id,
  -- ensure quantity is numeric (coerce non-numeric to NULL)
  CASE
    WHEN trim(e.quantity) = '' THEN NULL
    WHEN CAST(e.quantity AS REAL) IS NOT NULL THEN CAST(e.quantity AS REAL)
    ELSE NULL
  END AS quantity
FROM (
  -- derive a unified events source combining base events and already-normalized events_filtered if present
  SELECT
    s.rowid AS event_id,
    s.event_type,
    s.event_time AS timestamp,
    s.page_id,
    s.cookie_id,
    NULL AS user_id,
    s.visit_id AS session_id,
    NULL AS order_id,
    NULL AS product_id,
    NULL AS quantity
  FROM shopping_cart_events s
) e
LEFT JOIN shopping_cart_event_identifier ei
  ON ei.event_type = e.event_type
LEFT JOIN shopping_cart_page_hierarchy ph
  ON ph.page_id = e.page_id
LEFT JOIN shopping_cart_users u
  ON u.cookie_id = e.cookie_id
```

---

**Skill `product_events_per_instance`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `event_id` |
| output columns | `event_id`, `product_id`, `is_view`, `is_add_to_cart`, `is_purchase`, `user_id`, `session_id`, `timestamp`, `order_id` |
| source tables | `product_event_flags` |
| depends_on (builds on) | `product_event_flags` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Build one row per product-event occurrence instance to be used for counting: preserve each event instance (after normalization) with its flags so counts can be aggregated without collapsing other keys._

```sql
SELECT
  pe.event_id AS event_id,
  pe.product_id AS product_id,
  CASE WHEN pe.is_view IS NOT NULL THEN pe.is_view ELSE 0 END AS is_view,
  CASE WHEN pe.is_add_to_cart IS NOT NULL THEN pe.is_add_to_cart ELSE 0 END AS is_add_to_cart,
  CASE WHEN pe.is_purchase IS NOT NULL THEN pe.is_purchase ELSE 0 END AS is_purchase,
  pe.user_id AS user_id,
  pe.session_id AS session_id,
  pe.timestamp AS timestamp,
  pe.order_id AS order_id
FROM product_event_flags pe
```

---

**Skill `product_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `page_id` |
| output columns | `product_id`, `view_count`, `add_to_cart_count`, `cart_abandon_count`, `purchase_count` |
| source tables | `shopping_cart_events`, `shopping_cart_page_hierarchy` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregate counts per product: sum of view flags, sum of add-to-cart flags, sum of purchase flags, and cart_abandon_count defined as number of add-to-cart instances for which no later purchase exists for the same cart/order/session/user-product combination (calculated using available order_id/session_id/user_id)._

```sql
SELECT
  p.page_id AS product_id,
  SUM(CASE WHEN e.event_type = 1 THEN 1 ELSE 0 END) AS view_count,
  SUM(CASE WHEN e.event_type = 2 THEN 1 ELSE 0 END) AS add_to_cart_count,
  SUM(CASE WHEN e.event_type = 3 THEN 1 ELSE 0 END) AS purchase_count,
  -- cart_abandon_count: count of add-to-cart events for which there is no later purchase for same visit_id and product (using visit_id as session/cart)
  SUM(
    CASE
      WHEN e.event_type = 2
       AND NOT EXISTS (
         SELECT 1 FROM shopping_cart_events p2
         WHERE p2.visit_id = e.visit_id
           AND p2.page_id = e.page_id
           AND p2.event_type = 3
           AND (
             -- purchase happened at a later sequence_number if sequence_number available, else later event_time
             (e.sequence_number IS NOT NULL AND p2.sequence_number IS NOT NULL AND p2.sequence_number > e.sequence_number)
             OR
             (e.sequence_number IS NULL OR p2.sequence_number IS NULL) AND (p2.event_time > e.event_time)
           )
       )
      THEN 1 ELSE 0
    END
  ) AS cart_abandon_count
FROM shopping_cart_events e
LEFT JOIN shopping_cart_page_hierarchy p
  ON e.page_id = p.page_id
GROUP BY p.page_id
```

---

**Skill `monthly_interest_records`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `record` |
| output columns | `record_date`, `month`, `interest_id`, `interest_name`, `composition`, `index` |
| source tables | `interest_metrics`, `interest_map` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select all raw records restricted to the calendar months of interest (2018-09 through 2019-08) and exclude records where index is null or zero. Preserve the record date, interest identifier/name, composition and index for later calculations._

```sql
SELECT
  date(month_year || '-01') AS record_date,
  CAST(_month AS INTEGER) AS month,
  interest_id,
  interest_map.id AS interest_map_id,
  interest_map.interest_name AS interest_name,
  composition,
  index_value AS "index"
FROM interest_metrics
LEFT JOIN interest_map
  ON CAST(interest_metrics.interest_id AS INTEGER) = interest_map.id
WHERE
  -- intrinsic date range: 2018-09-01 through 2019-08-31
  date(month_year || '-01') BETWEEN date('2018-09-01') AND date('2019-08-31')
  AND index_value IS NOT NULL
  AND index_value != 0
```

---

**Skill `interest_month_avg_ratio`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `month`, `interest_id`, `interest_name` |
| output columns | `month`, `interest_id`, `interest_name`, `avg_index_composition` |
| source tables | `interest_metrics`, `interest_map` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `monthly_max_interest` |
| validated_on | — |
| counter_examples | 0 |

_For each interest in each calendar month, compute the average of (composition / index) across all valid records in that month._

```sql
SELECT
  CAST(strftime('%m-%Y', date(month_year || '-01')) AS TEXT) AS month,
  im.id AS interest_id,
  im.interest_name AS interest_name,
  AVG(imt.composition / NULLIF(imt.index_value, 0)) AS avg_index_composition
FROM interest_metrics imt
JOIN interest_map im
  ON CAST(imt.interest_id AS INTEGER) = im.id
GROUP BY month, interest_id, interest_name
```

---

**Skill `monthly_max_interest`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `month` |
| output columns | `month`, `interest_id`, `interest_name`, `max_index_composition` |
| source tables | `interest_month_avg_ratio`, `interest_map`, `month_range` |
| depends_on (builds on) | `month_range`, `interest_month_avg_ratio` |
| depended-on by (builds on this) | `monthly_max_with_lags_and_3mo` |
| validated_on | — |
| counter_examples | 0 |

_For each month, identify the interest with the highest avg_index_composition. If a month has no interest rows, produce a single row for that month with nulls for interest and numeric fields (i.e., ensure one row per month in the full month range)._

```sql
SELECT
  mr.year_month AS month,
  im.id AS interest_id,
  im.interest_name AS interest_name,
  ima.avg_index_composition AS max_index_composition
FROM month_range mr
LEFT JOIN (
  -- for each month, find the interest(s) with the maximum avg_index_composition
  SELECT
    ama.month,
    ama.interest_id,
    ama.interest_name,
    ama.avg_index_composition
  FROM interest_month_avg_ratio ama
  JOIN (
    SELECT
      month,
      MAX(avg_index_composition) AS max_avg_index_composition
    FROM interest_month_avg_ratio
    GROUP BY month
  ) mm ON ama.month = mm.month AND ama.avg_index_composition = mm.max_avg_index_composition
) ima ON ima.month = mr.year_month
LEFT JOIN interest_map im ON im.id = ima.interest_id
```

---

**Skill `monthly_max_with_lags_and_3mo`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `month` |
| output columns | `month`, `interest_name`, `max_index_composition`, `rolling_average_3mo`, `prev1_interest_name`, `prev1_max_index_composition`, `prev2_interest_name`, `prev2_max_index_composition` |
| source tables | `monthly_max_interest` |
| depends_on (builds on) | `monthly_max_interest` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each month (one row per month in the 2018-09..2019-08 range), attach the prior 1- and 2-month monthly_max_interest interest names and values using lag(), and compute the 3-month rolling average of max_index_composition over the current and two preceding months. If fewer than 3 months of numeric max values exist for the window, rolling_average_3mo should be null._

```sql
SELECT
  mmi.month AS month,
  mmi.interest_name AS interest_name,
  mmi.max_index_composition AS max_index_composition,
  CASE
    WHEN cnt_window = 3 THEN (mv0 + mv1 + mv2) / 3.0
    ELSE NULL
  END AS rolling_average_3mo,
  LAG(mmi.interest_name, 1) OVER (ORDER BY mmi.month) AS prev1_interest_name,
  LAG(mmi.max_index_composition, 1) OVER (ORDER BY mmi.month) AS prev1_max_index_composition,
  LAG(mmi.interest_name, 2) OVER (ORDER BY mmi.month) AS prev2_interest_name,
  LAG(mmi.max_index_composition, 2) OVER (ORDER BY mmi.month) AS prev2_max_index_composition
FROM (
  SELECT
    month,
    interest_name,
    max_index_composition,
    -- values for current and two preceding months for rolling calc
    max_index_composition AS mv0,
    LAG(max_index_composition, 1) OVER (ORDER BY month) AS mv1,
    LAG(max_index_composition, 2) OVER (ORDER BY month) AS mv2,
    -- count how many of the three are non-null numeric
    (CASE WHEN max_index_composition IS NOT NULL THEN 1 ELSE 0 END)
    + (CASE WHEN LAG(max_index_composition, 1) OVER (ORDER BY month) IS NOT NULL THEN 1 ELSE 0 END)
    + (CASE WHEN LAG(max_index_composition, 2) OVER (ORDER BY month) IS NOT NULL THEN 1 ELSE 0 END)
    AS cnt_window
  FROM monthly_max_interest
  -- intrinsic time range for this category (one row per month in 2018-09..2019-08)
  WHERE month >= '2018-09' AND month <= '2019-08'
) mmi
```

---

**Skill `normalized_month`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `month`, `interest_id` |
| output columns | `month`, `month_key`, `month_label_mm_yyyy`, `interest_id`, `interest_name`, `composition_value` |
| source tables | `interest_metrics`, `interest_map` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `interest_max_by_month` |
| validated_on | — |
| counter_examples | 0 |

_Normalize and canonicalize the month field into a consistent month identifier and formatting helper (e.g., YYYY-MM and formatted MM-YYYY). Also clean/normalize interest identifiers/names and composition_value types (casts, NULL handling). Keeps one row per original measurement._

```sql
SELECT
  -- canonical ISO month key YYYY-MM as text
  printf('%04d-%02d', CAST(COALESCE(CAST("_year" AS INTEGER), 0) AS INTEGER), CAST(COALESCE(CAST("_month" AS INTEGER), 0) AS INTEGER)) AS month,
  -- numeric key useful for joins / ordering: YYYYMM integer (NULL when year or month missing)
  CASE
    WHEN "_year" IS NOT NULL AND "_month" IS NOT NULL
    THEN (CAST(COALESCE(CAST("_year" AS INTEGER), 0) AS INTEGER) * 100) + CAST(COALESCE(CAST("_month" AS INTEGER), 0) AS INTEGER)
    ELSE NULL
  END AS month_key,
  -- formatted month label MM-YYYY (two-digit month)
  printf('%02d-%04d', CAST(COALESCE(CAST("_month" AS INTEGER), 0) AS INTEGER), CAST(COALESCE(CAST("_year" AS INTEGER), 0) AS INTEGER)) AS month_label_mm_yyyy,
  -- canonical interest id as integer (preserve NULL)
  CASE WHEN interest_id IS NOT NULL THEN CAST(interest_id AS INTEGER) ELSE NULL END AS interest_id,
  -- normalized interest name: prefer interest_map.interest_name when available, else pass through any name-like column from interest_map joined by id;
  -- since base tables do not contain an interest_name besides interest_map, left join will supply it when id matches.
  interest_map.interest_name AS interest_name,
  -- normalized composition value as real (NULL-safe)
  CASE WHEN composition IS NOT NULL THEN CAST(composition AS REAL) ELSE NULL END AS composition_value,
  -- include original source keys to keep joinability
  interest_metrics._month AS source__month_raw,
  interest_metrics._year AS source__year_raw,
  interest_metrics.month_year AS source_month_year_raw,
  interest_metrics.ranking AS source_ranking,
  interest_metrics.percentile_ranking AS source_percentile_ranking,
  interest_map.id AS interest_map_id,
  interest_map.interest_summary AS interest_map_summary,
  interest_map.created_at AS interest_map_created_at,
  interest_map.last_modified AS interest_map_last_modified
FROM interest_metrics
LEFT JOIN interest_map
  ON CAST(interest_metrics.interest_id AS INTEGER) = interest_map.id
```

---

**Skill `interest_max_by_month`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `interest_id`, `month_key` |
| output columns | `interest_id`, `interest_name`, `max_composition_value`, `month_key`, `month_label_mm_yyyy` |
| source tables | `interest_map`, `normalized_month` |
| depends_on (builds on) | `normalized_month` |
| depended-on by (builds on this) | `ranked_interest_maxima` |
| validated_on | — |
| counter_examples | 0 |

_For each interest, compute its maximum composition_value across all months and capture which month(s) that maximum occurred in. Keep one row per interest-month occurrence where the composition equals the interest's maximum (ties preserved for now)._

```sql
SELECT
  im.id AS interest_id,
  im.interest_name AS interest_name,
  nm.max_composition_value AS max_composition_value,
  nm.month_key AS month_key,
  nm.month_label_mm_yyyy AS month_label_mm_yyyy
FROM interest_map im
JOIN (
  SELECT
    n.interest_id,
    n.month_key,
    n.month_label_mm_yyyy,
    n.composition_value,
    -- compute max composition per interest using a correlated aggregation to avoid window misuse
    (SELECT MAX(n2.composition_value)
     FROM normalized_month n2
     WHERE n2.interest_id = n.interest_id
    ) AS max_composition_value
  FROM normalized_month n
) nm
  ON nm.interest_id = im.id
WHERE nm.composition_value = nm.max_composition_value
```

---

**Skill `ranked_interest_maxima`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `interest_id` |
| output columns | `interest_id`, `interest_name`, `max_composition_value`, `month_key`, `month_label_mm_yyyy`, `rank_desc`, `rank_asc` |
| source tables | `interest_max_by_month` |
| depends_on (builds on) | `interest_max_by_month` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_From the per-interest maxima rows, pick a single deterministic month per interest when ties exist (e.g., earliest or latest month) and rank interests by their max_composition_value. Produce an ordered relation that can be used to select the top N and bottom N interests._

```sql
SELECT
  imb.interest_id AS interest_id,
  imb.interest_name AS interest_name,
  imb.max_composition_value AS max_composition_value,
  imb.month_key AS month_key,
  imb.month_label_mm_yyyy AS month_label_mm_yyyy,
  RANK() OVER (ORDER BY imb.max_composition_value DESC, imb.month_key ASC, imb.interest_id ASC) AS rank_desc,
  RANK() OVER (ORDER BY imb.max_composition_value ASC, imb.month_key ASC, imb.interest_id ASC) AS rank_asc
FROM interest_max_by_month imb
```

---

**Skill `raw_purchases_sel`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `event_id` |
| output columns | `event_id`, `event_date`, `year`, `region`, `dollars_spent`, `quantity_btc` |
| source tables | `bitcoin_transactions`, `bitcoin_members`, `bitcoin_prices` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `region_year_totals_agg` |
| validated_on | — |
| counter_examples | 0 |

_Select the raw purchase events to be analyzed, projecting event date, calendar year, region identifier/name, dollar amount spent for the event, and quantity of Bitcoin purchased; also filter out any events with NULL or non-positive quantity or dollar amount if desired downstream._

```sql
SELECT
  bitcoin_transactions.txn_id AS event_id,
  bitcoin_transactions.txn_time AS event_date,
  CAST(strftime('%Y', bitcoin_transactions.txn_time) AS INTEGER) AS year,
  bitcoin_members.region AS region,
  (bitcoin_transactions.quantity * bitcoin_prices.price) AS dollars_spent,
  bitcoin_transactions.quantity AS quantity_btc
FROM bitcoin_transactions
LEFT JOIN bitcoin_members
  ON bitcoin_transactions.member_id = bitcoin_members.member_id
LEFT JOIN bitcoin_prices
  ON bitcoin_transactions.ticker = bitcoin_prices.ticker
  AND bitcoin_prices.market_date = bitcoin_transactions.txn_date
WHERE bitcoin_transactions.txn_type = 'BUY'
  AND bitcoin_transactions.quantity IS NOT NULL
  AND bitcoin_transactions.quantity > 0
  AND bitcoin_prices.price IS NOT NULL
  AND (bitcoin_transactions.quantity * bitcoin_prices.price) > 0
```

---

**Skill `region_year_totals_agg`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `region`, `year` |
| output columns | `region`, `year`, `total_dollars_spent`, `total_quantity_purchased` |
| source tables | `raw_purchases_sel` |
| depends_on (builds on) | `raw_purchases_sel` |
| depended-on by (builds on this) | `region_year_rank_and_change_win` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate the raw purchase events to compute, per region and calendar year, the total dollars spent and total quantity purchased. Do not exclude any year here; keep one row per region-year with the summed metrics._

```sql
SELECT
  region,
  year AS year,
  SUM(dollars_spent) AS total_dollars_spent,
  SUM(quantity_btc) AS total_quantity_purchased
FROM raw_purchases_sel
GROUP BY region, year
```

---

**Skill `region_first_year_sel`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `region` |
| output columns | `region`, `first_year` |
| source tables | `cleaned_weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `region_year_rank_and_change_win` |
| validated_on | — |
| counter_examples | 0 |

_For each region, determine the earliest calendar year in which that region has any purchases (the first year to be excluded later). This is one row per region with its min(year)._

```sql
SELECT
  region,
  MIN(calendar_year) AS first_year
FROM cleaned_weekly_sales
WHERE region IS NOT NULL
GROUP BY region
```

---

**Skill `region_year_rank_and_change_win`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `region`, `year` |
| output columns | `year`, `region`, `total_dollars_spent`, `total_quantity_purchased`, `avg_purchase_price_per_bitcoin`, `region_year_rank`, `pct_change_vs_prev_year` |
| source tables | `region_year_totals_agg`, `region_first_year_sel` |
| depends_on (builds on) | `region_year_totals_agg`, `region_first_year_sel` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Using region-year totals, compute average purchase price per bitcoin (total_dollars_spent / total_quantity_purchased), exclude rows where total_quantity_purchased <= 0 and exclude rows where year = region's first_year, then for each year: rank regions by average purchase price descending (deterministic tie handling), and compute the percentage change of the average purchase price versus the previous year for the same region using a lag function (NULL if no previous year or previous avg = 0). Keep all region-year rows that survive the filters._

```sql
SELECT
  ryt.year AS year,
  ryt.region AS region,
  ryt.total_dollars_spent AS total_dollars_spent,
  ryt.total_quantity_purchased AS total_quantity_purchased,
  (ryt.total_dollars_spent / ryt.total_quantity_purchased) AS avg_purchase_price_per_bitcoin,
  -- deterministic rank: rank by avg desc, tie-break by region asc
  (SELECT COUNT(*) + 1
   FROM (
     SELECT region AS r2,
            (total_dollars_spent / total_quantity_purchased) AS avg2
     FROM region_year_totals_agg ryt2
     WHERE ryt2.year = ryt.year
       AND ryt2.total_quantity_purchased > 0
   ) sub
   WHERE (sub.avg2 > (ryt.total_dollars_spent / ryt.total_quantity_purchased))
      OR (sub.avg2 = (ryt.total_dollars_spent / ryt.total_quantity_purchased) AND sub.r2 < ryt.region)
  ) AS region_year_rank,
  -- percent change vs previous year for same region
  (CASE
     WHEN prev.avg_prev IS NULL THEN NULL
     WHEN prev.avg_prev = 0 THEN NULL
     ELSE ((ryt.total_dollars_spent / ryt.total_quantity_purchased) - prev.avg_prev) / prev.avg_prev
   END) AS pct_change_vs_prev_year
FROM region_year_totals_agg ryt
LEFT JOIN (
  SELECT
    ryt2.region AS region,
    ryt2.year AS year,
    (ryt2.total_dollars_spent / ryt2.total_quantity_purchased) AS avg_prev
  FROM region_year_totals_agg ryt2
) prev ON prev.region = ryt.region AND prev.year = (ryt.year - 1)
JOIN region_first_year_sel rfy ON rfy.region = ryt.region
WHERE ryt.total_quantity_purchased > 0
  AND ryt.year != rfy.first_year
```

---

**Skill `raw_rows_in_date_range`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `ticker`, `date` |
| output columns | `ticker`, `date`, `raw_volume_str` |
| source tables | `bitcoin_prices` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select rows from the bitcoin_prices source restricted to the target date window. Keep every original row for tickers and dates even if volume is '-' or null so later normalization and lookbacks can operate._

```sql
SELECT
  ticker,
  market_date AS date,
  volume AS raw_volume_str
FROM
  bitcoin_prices
WHERE
  market_date >= '21-08-2021'
  AND market_date <= '21-08-2020'
```

---

**Skill `normalized_volumes`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `ticker`, `date` |
| output columns | `ticker`, `date`, `volume` |
| source tables | `bitcoin_prices` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `prev_non_zero_volume_per_row` |
| validated_on | — |
| counter_examples | 0 |

_Normalize the raw volume string into a numeric volume: treat '-' as 0, parse numbers, multiply trailing 'K' by 1,000 and trailing 'M' by 1,000,000. Produce a numeric volume and preserve ticker/date rows exactly (one row per ticker-date)._

```sql
SELECT
  ticker AS ticker,
  market_date AS date,
  CASE
    WHEN volume IS NULL THEN 0
    WHEN TRIM(volume) = '-' THEN 0
    ELSE
      -- Remove surrounding whitespace
      (
        CASE
          -- Ends with K or k
          WHEN upper(substr(trim(volume), -1, 1)) = 'K' THEN
            -- take all but last char, remove commas, convert to number, multiply by 1000
            (CAST(replace(substr(trim(volume), 1, length(trim(volume)) - 1), ',', '') AS REAL) * 1000.0)
          -- Ends with M or m
          WHEN upper(substr(trim(volume), -1, 1)) = 'M' THEN
            (CAST(replace(substr(trim(volume), 1, length(trim(volume)) - 1), ',', '') AS REAL) * 1000000.0)
          -- Plain number (possibly with commas)
          ELSE
            CAST(replace(trim(volume), ',', '') AS REAL)
        END
      )
  END AS volume
FROM bitcoin_prices
```

---

**Skill `prev_non_zero_volume_per_row`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `ticker`, `date` |
| output columns | `ticker`, `date`, `volume`, `prev_non_zero_volume` |
| source tables | `normalized_volumes` |
| depends_on (builds on) | `normalized_volumes` |
| depended-on by (builds on this) | `daily_pct_change_final` |
| validated_on | — |
| counter_examples | 0 |

_For each ticker and date row, find the most recent prior date (date < current date) for the same ticker whose normalized volume > 0, and return that prior normalized volume as prev_non_zero_volume. If none exists, prev_non_zero_volume is null. Keep one row per original ticker-date._

```sql
SELECT
  n1.ticker AS ticker,
  n1.date AS date,
  n1.volume AS volume,
  (
    SELECT n2.volume
    FROM normalized_volumes n2
    WHERE n2.ticker = n1.ticker
      AND n2.date < n1.date
      AND n2.volume > 0
    ORDER BY n2.date DESC
    LIMIT 1
  ) AS prev_non_zero_volume
FROM normalized_volumes n1
```

---

**Skill `daily_pct_change_final`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `ticker`, `date` |
| output columns | `ticker`, `date`, `volume`, `prev_non_zero_volume`, `daily_pct_change` |
| source tables | `bitcoin_prices`, `prev_non_zero_volume_per_row` |
| depends_on (builds on) | `prev_non_zero_volume_per_row` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Compute daily percentage change per row using prev_non_zero_volume: ((volume - prev_non_zero_volume) / prev_non_zero_volume) * 100. If prev_non_zero_volume is null or zero, set daily_pct_change to null. Output rows for the requested date range ordered later by ticker and date._

```sql
SELECT
  p.ticker AS ticker,
  p.market_date AS date,
  v.volume AS volume,
  v.prev_non_zero_volume AS prev_non_zero_volume,
  CASE
    WHEN v.prev_non_zero_volume IS NULL THEN NULL
    WHEN v.prev_non_zero_volume = 0 THEN NULL
    ELSE ((v.volume - v.prev_non_zero_volume) / v.prev_non_zero_volume) * 100.0
  END AS daily_pct_change
FROM bitcoin_prices p
JOIN prev_non_zero_volume_per_row v
  ON p.ticker = v.ticker
  AND p.market_date = v.date
WHERE p.market_date >= '21-08-2021'
  AND p.market_date <= '21-08-2021'
```

---

**Skill `raw_items_sel`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `raw_item_id`, `source_row_id` |
| output columns | `raw_item_id`, `raw_loss_rate`, `source_row_id` |
| source tables | `veg_whsle_df`, `veg_loss_rate_df` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `item_loss_rate_norm` |
| validated_on | — |
| counter_examples | 0 |

_Select all rows representing items from the veg whsle dataset, excluding rows where the loss rate is NULL or non-numeric. This is the raw item-level cohort before any per-item aggregation or cleaning._

```sql
SELECT
  vwr."item_code" AS raw_item_id,
  vwr."loss_rate_%" AS raw_loss_rate,
  vwr."index" AS source_row_id
FROM veg_whsle_df vwh
JOIN veg_loss_rate_df vwr
  ON vwh."item_code" = vwr."item_code"
WHERE vwr."loss_rate_%" IS NOT NULL
  AND (json_type(json(vwr."loss_rate_%")) IS NULL OR (typeof(vwr."loss_rate_%") IN ('integer','real')))
```

---

**Skill `item_loss_rate_norm`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `raw_item_id`, `source_row_id` |
| output columns | `raw_item_id`, `clean_loss_rate` |
| source tables | `raw_items_sel` |
| depends_on (builds on) | `raw_items_sel` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Normalize and cast loss rate values to numeric, apply any canonicalization (e.g., convert percentages to decimals if needed), and mark or remove invalid values. Produce a cleaned numeric loss rate per source row._

```sql
SELECT
  raw_item_id,
  CASE
    WHEN raw_loss_rate IS NULL THEN NULL
    WHEN TRIM(raw_loss_rate) = '' THEN NULL
    -- numeric numeric already (e.g., 4.39 or 10.46)
    WHEN typeof(raw_loss_rate) = 'real' OR typeof(raw_loss_rate) = 'integer' THEN
      CASE
        WHEN raw_loss_rate > 1 THEN raw_loss_rate / 100.0
        WHEN raw_loss_rate < 0 THEN NULL
        ELSE raw_loss_rate
      END
    -- text that may contain percent sign or be numeric string
    WHEN typeof(raw_loss_rate) = 'text' THEN
      CASE
        WHEN instr(raw_loss_rate, '%') > 0 THEN
          -- remove percent sign and any spaces, then try to cast
          (CASE
            WHEN CAST(replace(replace(raw_loss_rate, '%', ''), ' ', '') AS REAL) IS NOT NULL
              THEN
                (CASE
                  WHEN CAST(replace(replace(raw_loss_rate, '%', ''), ' ', '') AS REAL) > 1
                    THEN CAST(replace(replace(raw_loss_rate, '%', ''), ' ', '') AS REAL) / 100.0
                  WHEN CAST(replace(replace(raw_loss_rate, '%', ''), ' ', '') AS REAL) < 0
                    THEN NULL
                  ELSE CAST(replace(replace(raw_loss_rate, '%', ''), ' ', '') AS REAL)
                END)
            ELSE NULL
          END)
        ELSE
          (CASE
            WHEN CAST(raw_loss_rate AS REAL) IS NOT NULL
              THEN
                (CASE
                  WHEN CAST(raw_loss_rate AS REAL) > 1 THEN CAST(raw_loss_rate AS REAL) / 100.0
                  WHEN CAST(raw_loss_rate AS REAL) < 0 THEN NULL
                  ELSE CAST(raw_loss_rate AS REAL)
                END)
            ELSE NULL
          END)
      END
    ELSE NULL
  END AS clean_loss_rate,
  source_row_id
FROM raw_items_sel
```

---

**Skill `per_item_loss_rate_agg`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `item_code` |
| output columns | `item_id`, `item_loss_rate` |
| source tables | `veg_loss_rate_df` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregate rows belonging to the same logical item to produce one loss rate per item. If multiple rows exist for an item, compute that item's representative loss rate (e.g., average of its clean_loss_rate or another specified aggregation)._

```sql
SELECT
  CAST(item_code AS TEXT) AS item_id,
  AVG("loss_rate_%") AS item_loss_rate
FROM veg_loss_rate_df
GROUP BY item_code
```

---

**Skill `normalized_fields`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `record_id` |
| output columns | `record_id`, `year`, `category`, `wholesale_price_num`, `selling_price_num`, `loss_rate_num` |
| source tables | `veg_cat`, `veg_whsle_df`, `veg_txn_df`, `veg_loss_rate_df` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Normalize and canonicalize relevant fields: derive year from date if needed, cast numeric fields (wholesale_price, selling_price, loss_rate) to numeric types, treat empty strings as NULLs, and ensure loss_rate is expressed as a numeric fraction or percentage consistently for aggregation._

```sql
SELECT
  -- record identifier: prefer existing primary-like ids from veg tables, else construct from available columns
  COALESCE(
    CAST(veg_cat."index" AS TEXT) || '_vegcat',
    CAST(veg_loss_rate_df."index" AS TEXT) || '_loss',
    CAST(veg_whsle_df."index" AS TEXT) || '_whsle',
    veg_txn_df."index" || '_txn'
  ) AS record_id,
  -- derive year where possible from available date-like fields; keep NULL if not parseable
  CASE
    WHEN instr(veg_whsle_df.whsle_date, '-') > 0 THEN
      substr(veg_whsle_df.whsle_date, 1, 4)
    WHEN instr(veg_txn_df.txn_date, '-') > 0 AND length(veg_txn_df.txn_date) >= 4 THEN
      substr(veg_txn_df.txn_date, 1, 4)
    ELSE NULL
  END AS year,
  -- canonical category: prefer veg_cat.category_name, fallback to NULL
  NULLIF(trim(veg_cat.category_name), '') AS category,
  -- wholesale price numeric: from veg_whsle_df."whsle_px_rmb-kg"
  CASE
    WHEN trim(COALESCE(veg_whsle_df."whsle_px_rmb-kg", '')) = '' THEN NULL
    ELSE CAST(veg_whsle_df."whsle_px_rmb-kg" AS REAL)
  END AS wholesale_price_num,
  -- selling price numeric: from veg_txn_df."unit_selling_px_rmb/kg"
  CASE
    WHEN trim(COALESCE(veg_txn_df."unit_selling_px_rmb/kg", '')) = '' THEN NULL
    ELSE CAST(veg_txn_df."unit_selling_px_rmb/kg" AS REAL)
  END AS selling_price_num,
  -- loss rate normalized to fraction (0-1). If stored as percent like 4.39 assume percent and divide by 100.
  CASE
    WHEN veg_loss_rate_df."loss_rate_%" IS NULL THEN NULL
    ELSE
      -- values appear as percent numbers like 4.39; convert to fraction
      CAST(veg_loss_rate_df."loss_rate_%" AS REAL) / 100.0
  END AS loss_rate_num
FROM veg_cat
LEFT JOIN veg_whsle_df ON veg_cat.item_code = veg_whsle_df.item_code
LEFT JOIN veg_txn_df ON veg_cat.item_code = veg_txn_df.item_code
LEFT JOIN veg_loss_rate_df ON veg_cat.item_code = veg_loss_rate_df.item_code
```

---

**Skill `per_record_loss_profit`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `record_id` |
| output columns | `record_id`, `year`, `category`, `wholesale_price_num`, `selling_price_num`, `loss_rate_num`, `loss_amount`, `profit_amount` |
| source tables | `veg_txn_df`, `veg_whsle_df`, `veg_loss_rate_df`, `veg_cat` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Compute per-row derived monetary loss and profit measures using normalized numeric fields so they can be summed later (e.g., loss_amount = wholesale_price_num * loss_rate_num, profit_amount = selling_price_num - wholesale_price_num or another domain definition). Keep one row per original record._

```sql
SELECT
  -- record identifier: prefer original txn index if present, else wholesale or loss_rate index; coalesce to ensure one id per source row
  COALESCE(vt."index", vw."index", vl."index") AS record_id,
  -- derive year from available date/time fields
  CASE
    WHEN vt.txn_date IS NOT NULL THEN substr(vt.txn_date, 1, 4)
    WHEN vw.whsle_date IS NOT NULL THEN substr(vw.whsle_date, 1, 4)
    ELSE NULL
  END AS year,
  -- category: join veg_cat on item_code when available; else NULL
  vc.category_name AS category,
  -- normalized wholesale price numeric: prefer veg_whsle_df.whsle_px_rmb-kg
  vw."whsle_px_rmb-kg" AS wholesale_price_num,
  -- normalized selling price numeric: prefer veg_txn_df.unit_selling_px_rmb/kg
  vt."unit_selling_px_rmb/kg" AS selling_price_num,
  -- normalized loss rate numeric: prefer veg_loss_rate_df.loss_rate_%
  vl."loss_rate_%" AS loss_rate_num,
  -- loss amount monetary: wholesale_price_num * loss_rate_num (interpreting loss_rate_num as percent)
  CASE
    WHEN vw."whsle_px_rmb-kg" IS NOT NULL AND vl."loss_rate_%" IS NOT NULL THEN (vw."whsle_px_rmb-kg" * (vl."loss_rate_%" / 100.0))
    ELSE NULL
  END AS loss_amount,
  -- profit amount monetary: selling_price_num - wholesale_price_num when both available
  CASE
    WHEN vt."unit_selling_px_rmb/kg" IS NOT NULL AND vw."whsle_px_rmb-kg" IS NOT NULL THEN (vt."unit_selling_px_rmb/kg" - vw."whsle_px_rmb-kg")
    ELSE NULL
  END AS profit_amount
FROM veg_txn_df vt
FULL OUTER JOIN veg_whsle_df vw ON vt.item_code = vw.item_code
LEFT JOIN veg_loss_rate_df vl ON COALESCE(vt.item_code, vw.item_code) = vl.item_code
LEFT JOIN veg_cat vc ON COALESCE(vt.item_code, vw.item_code, vl.item_code) = vc.item_code
```

---

**Skill `calendar_days`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `date` |
| output columns | `date` |
| source tables | `customer_transactions`, `bitcoin_transactions`, `cleaned_weekly_sales`, `weekly_sales`, `shopping_cart_users`, `veg_whsle_df`, `veg_txn_df` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All calendar dates (or sales-date rows) in the source dataset covering the years of interest, restricted to dates needed to build the four-week pre- and post-June-15 windows for target years. This relation yields one row per date with its calendar date value so windows can be computed by date range._

```sql
SELECT
  date(day) AS date
FROM (
  -- derive candidate date ranges from existing tables' date-like columns
  SELECT txn_date AS day FROM customer_transactions
  UNION
  SELECT txn_date AS day FROM bitcoin_transactions
  UNION
  SELECT week_date AS day FROM cleaned_weekly_sales
  UNION
  SELECT week_date AS day FROM weekly_sales
  UNION
  SELECT start_date AS day FROM shopping_cart_users
  UNION
  SELECT whsle_date AS day FROM veg_whsle_df
  UNION
  SELECT txn_date AS day FROM veg_txn_df
) src
WHERE day IS NOT NULL
GROUP BY date(day)
```

---

**Skill `sales_by_date`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `date` |
| output columns | `date`, `total_sales` |
| source tables | `cleaned_weekly_sales`, `weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregate total sales per calendar date. If source data is at a finer grain (transactions), sum amounts per date; if already by date/week, normalize to date-level sales that can be filtered by inclusive date ranges._

```sql
SELECT
  date(week_date) AS date,
  SUM(sales) AS total_sales
FROM (
  SELECT week_date, sales FROM cleaned_weekly_sales
  UNION ALL
  SELECT week_date, sales FROM weekly_sales
)
GROUP BY date
```

---

**Skill `year_period_boundaries`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `year` |
| output columns | `year`, `pre_period_start_date`, `pre_period_end_date`, `post_period_start_date`, `post_period_end_date` |
| source tables | `customer_nodes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `year_period_sales` |
| validated_on | — |
| counter_examples | 0 |

_For each target year (one row per year), compute the start and end dates for the pre-June-15 four-week period and the post-June-15 four-week period. Pre period: end_date = June 14 of the year, start_date = end_date - 27 days. Post period: start_date = June 15 of the year, end_date = start_date + 27 days. Produce the four boundary dates and the year key._

```sql
SELECT
  CAST(strftime('%Y', date(substr(start_of_year,1,10))) AS INTEGER) AS year,
  date(strftime('%Y', date(substr(start_of_year,1,10))) || '-06-14', '-27 days') AS pre_period_start_date,
  date(strftime('%Y', date(substr(start_of_year,1,10))) || '-06-14') AS pre_period_end_date,
  date(strftime('%Y', date(substr(start_of_year,1,10))) || '-06-15') AS post_period_start_date,
  date(strftime('%Y', date(substr(start_of_year,1,10))) || '-06-15', '+27 days') AS post_period_end_date
FROM (
  SELECT DISTINCT
    date(substr(start_date,1,10)) AS start_of_year
  FROM customer_nodes
)
```

---

**Skill `year_period_sales`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `year`, `pre_period_start_date`, `pre_period_end_date`, `post_period_start_date`, `post_period_end_date` |
| output columns | `year`, `pre_period_start_date`, `pre_period_end_date`, `pre_period_total_sales`, `post_period_start_date`, `post_period_end_date`, `post_period_total_sales`, `percent_change` |
| source tables | `year_period_boundaries`, `cleaned_weekly_sales` |
| depends_on (builds on) | `year_period_boundaries` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each year, join the period boundaries to daily sales and compute the aggregated sales sums for the pre and post four-week inclusive date ranges, and compute percent change (null if pre sum = 0). This relation returns one row per year containing the period start/end dates, aggregated sales for each period, and percent_change._

```sql
SELECT
  ypb.year AS year,
  ypb.pre_period_start_date AS pre_period_start_date,
  ypb.pre_period_end_date AS pre_period_end_date,
  COALESCE(SUM(CASE WHEN date(week_date) BETWEEN date(ypb.pre_period_start_date) AND date(ypb.pre_period_end_date) THEN cleaned_weekly_sales.sales END), 0) AS pre_period_total_sales,
  ypb.post_period_start_date AS post_period_start_date,
  ypb.post_period_end_date AS post_period_end_date,
  COALESCE(SUM(CASE WHEN date(week_date) BETWEEN date(ypb.post_period_start_date) AND date(ypb.post_period_end_date) THEN cleaned_weekly_sales.sales END), 0) AS post_period_total_sales,
  CASE
    WHEN SUM(CASE WHEN date(week_date) BETWEEN date(ypb.pre_period_start_date) AND date(ypb.pre_period_end_date) THEN cleaned_weekly_sales.sales END) = 0
      THEN NULL
    ELSE
      (CAST(SUM(CASE WHEN date(week_date) BETWEEN date(ypb.post_period_start_date) AND date(ypb.post_period_end_date) THEN cleaned_weekly_sales.sales END) AS REAL)
       - CAST(SUM(CASE WHEN date(week_date) BETWEEN date(ypb.pre_period_start_date) AND date(ypb.pre_period_end_date) THEN cleaned_weekly_sales.sales END) AS REAL)
      )
      / CAST(SUM(CASE WHEN date(week_date) BETWEEN date(ypb.pre_period_start_date) AND date(ypb.pre_period_end_date) THEN cleaned_weekly_sales.sales END) AS REAL)
  END AS percent_change
FROM year_period_boundaries ypb
LEFT JOIN cleaned_weekly_sales
  ON date(cleaned_weekly_sales.week_date) BETWEEN date(ypb.pre_period_start_date) AND date(ypb.post_period_end_date)
GROUP BY
  ypb.year,
  ypb.pre_period_start_date,
  ypb.pre_period_end_date,
  ypb.post_period_start_date,
  ypb.post_period_end_date
```

---

**Skill `sales_pre_post_cohort`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `sale_id` |
| output columns | `sale_id`, `sale_date`, `amount`, `period_label` |
| source tables | `cleaned_weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select sales records that fall within either the pre-period (the 84 days immediately before the reference date) or the post-period (the 84 days immediately after the reference date), and label each row with which period it belongs to. Do not aggregate here; keep all sales-level rows so later grouping can compute totals. Exclude rows outside both periods._

```sql
SELECT
  ROW_NUMBER() OVER (ORDER BY week_date) AS sale_id,
  week_date AS sale_date,
  sales AS amount,
  CASE
    WHEN date(week_date) BETWEEN date(reference_dates.ref_date, '-84 days') AND date(reference_dates.ref_date, '-1 day') THEN 'pre'
    WHEN date(week_date) BETWEEN date(reference_dates.ref_date, '+1 day') AND date(reference_dates.ref_date, '+84 days') THEN 'post'
    ELSE NULL
  END AS period_label
FROM cleaned_weekly_sales,
(
  SELECT
    -- placeholder reference date column; consumers of this view must join or replace this CTE
    NULL AS ref_date
) AS reference_dates
WHERE
  -- keep only rows that fall into either pre or post windows relative to the reference date
  (date(week_date) BETWEEN date(reference_dates.ref_date, '-84 days') AND date(reference_dates.ref_date, '-1 day'))
  OR
  (date(week_date) BETWEEN date(reference_dates.ref_date, '+1 day') AND date(reference_dates.ref_date, '+84 days'))
```

---

**Skill `sales_with_attributes`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `sale_id` |
| output columns | `sale_id`, `sale_date`, `amount`, `period_label`, `region`, `platform`, `age_band`, `demographic`, `customer_type` |
| source tables | `cleaned_weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `attribute_value_period_totals` |
| validated_on | — |
| counter_examples | 0 |

_Attach attribute values (region, platform, age_band, demographic, customer_type) to each selected sale so each sale row includes all five attribute dimensions needed for grouping. This is a denormalized sales row with attributes._

```sql
SELECT
  -- sale_id: construct a stable id per weekly row using week_date + region + platform + segment + customer_type + age_band + demographic
  week_date || '|' || region || '|' || platform || '|' || segment || '|' || customer_type || '|' || COALESCE(age_band,'') || '|' || COALESCE(demographic,'') AS sale_id,
  -- sale_date: use canonical week_date
  week_date AS sale_date,
  -- amount: use sales as the monetary amount for the denormalized sale row
  sales AS amount,
  -- period_label: year-month label composed from calendar_year and month_number
  calendar_year || '-' || printf('%02d', month_number) AS period_label,
  -- attributes: pass through region, platform, age_band, demographic, customer_type
  region,
  platform,
  age_band,
  demographic,
  customer_type
FROM cleaned_weekly_sales
```

---

**Skill `attribute_value_period_totals`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `attribute_type`, `attribute_value`, `period_label` |
| output columns | `attribute_type`, `attribute_value`, `period_label`, `total_sales`, `has_sales_flag` |
| source tables | `sales_with_attributes` |
| depends_on (builds on) | `sales_with_attributes` |
| depended-on by (builds on this) | `attribute_value_percentage_changes` |
| validated_on | — |
| counter_examples | 0 |

_For each attribute type and each attribute value, and for each period (pre or post), compute the total sales amount and the indicator of whether any sales exist. Keep one row per attribute_type x attribute_value x period._

```sql
SELECT
  attribute_type,
  attribute_value,
  period_label,
  SUM(amount) AS total_sales,
  CASE WHEN SUM(CASE WHEN amount IS NOT NULL AND amount != 0 THEN 1 ELSE 0 END) > 0 THEN 1 ELSE 0 END AS has_sales_flag
FROM (
  SELECT 'region' AS attribute_type, region AS attribute_value, period_label, amount
  FROM sales_with_attributes
  UNION ALL
  SELECT 'platform' AS attribute_type, platform AS attribute_value, period_label, amount
  FROM sales_with_attributes
  UNION ALL
  SELECT 'age_band' AS attribute_type, age_band AS attribute_value, period_label, amount
  FROM sales_with_attributes
  UNION ALL
  SELECT 'demographic' AS attribute_type, demographic AS attribute_value, period_label, amount
  FROM sales_with_attributes
  UNION ALL
  SELECT 'customer_type' AS attribute_type, customer_type AS attribute_value, period_label, amount
  FROM sales_with_attributes
) attrs
GROUP BY attribute_type, attribute_value, period_label
```

---

**Skill `attribute_value_percentage_changes`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `attribute_type`, `attribute_value` |
| output columns | `attribute_type`, `attribute_value`, `pre_sales`, `post_sales`, `percentage_change`, `average_percentage_change_per_attribute_type` |
| source tables | `attribute_value_period_totals` |
| depends_on (builds on) | `attribute_value_period_totals` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each attribute type and attribute value, pivot or join the pre and post totals to compute the percentage change = (post_sales - pre_sales) / NULLIF(pre_sales, 0). Exclude attribute values where pre_sales is zero or where there are no sales in both periods. This produces one row per attribute_type x attribute_value with its percentage change. Then compute the average of those percentage changes across all attribute values within each attribute_type (one row per attribute_type)._

```sql
SELECT
  avt.attribute_type AS attribute_type,
  avt.attribute_value AS attribute_value,
  SUM(CASE WHEN avt.period_label = 'pre' THEN avt.total_sales ELSE 0 END) AS pre_sales,
  SUM(CASE WHEN avt.period_label = 'post' THEN avt.total_sales ELSE 0 END) AS post_sales,
  (CAST(SUM(CASE WHEN avt.period_label = 'post' THEN avt.total_sales ELSE 0 END) AS REAL)
   - CAST(SUM(CASE WHEN avt.period_label = 'pre' THEN avt.total_sales ELSE 0 END) AS REAL))
   / NULLIF(CAST(SUM(CASE WHEN avt.period_label = 'pre' THEN avt.total_sales ELSE 0 END) AS REAL), 0) AS percentage_change,
  AVG((CAST(SUM(CASE WHEN avt.period_label = 'post' THEN avt.total_sales ELSE 0 END) AS REAL)
       - CAST(SUM(CASE WHEN avt.period_label = 'pre' THEN avt.total_sales ELSE 0 END) AS REAL))
       / NULLIF(CAST(SUM(CASE WHEN avt.period_label = 'pre' THEN avt.total_sales ELSE 0 END) AS REAL), 0)
      ) OVER (PARTITION BY avt.attribute_type) AS average_percentage_change_per_attribute_type
FROM attribute_value_period_totals AS avt
GROUP BY
  avt.attribute_type,
  avt.attribute_value
HAVING
  SUM(CASE WHEN avt.period_label = 'pre' THEN avt.total_sales ELSE 0 END) IS NOT NULL
  AND SUM(CASE WHEN avt.period_label = 'post' THEN avt.total_sales ELSE 0 END) IS NOT NULL
  AND SUM(CASE WHEN avt.period_label = 'pre' THEN avt.total_sales ELSE 0 END) != 0
  AND (SUM(CASE WHEN avt.period_label = 'pre' THEN avt.total_sales ELSE 0 END)
       + SUM(CASE WHEN avt.period_label = 'post' THEN avt.total_sales ELSE 0 END)) > 0
```

---
