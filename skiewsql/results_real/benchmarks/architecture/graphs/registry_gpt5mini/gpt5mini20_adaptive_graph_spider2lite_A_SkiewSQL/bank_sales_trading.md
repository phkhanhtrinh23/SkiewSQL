# Skill graph — `bank_sales_trading` (11 skills)

## Skill `monthly_customer_closing_balance`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `year`, `month`, `month_end_date` (keyed) |
| status / version | active / v1 |
| skill id | sk_6306a0821ca1e568 |
| output columns | `customer_id`, `year`, `month`, `month_end_date`, `closing_balance_raw`, `has_transactions_flag` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-customer, per-calendar-month aggregated closing balance and flag indicating whether the month has transactions; includes month and month_end_date to permit month-series joins and fill-forward logic.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "final_extract",
    "removed_constants": [],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "customer_transactions"
    ],
    "table_fingerprints": {
      "customer_transactions": "f0755d1d3402a42b"
    },
    "data_fingerprints": {},
    "db_id": "bank_sales_trading",
    "question_id": "local074",
    "question": "Please generate a summary of the closing balances at the end of each month for each customer transactions, show the monthly changes and monthly cumulative bank account balances. Ensure that even if a customer has no account activity in a given month, the balance for that month is still included in the output.",
    "rewrite": "Task: For each customer and for each calendar month in the covered date range, compute the account closing balance at the end of that month, the change in balance relative to the previous month for that customer, and the cumulative bank account balance over time for that customer, including months with no transactions (these months must still appear with the carried-forward balance).\nRequired outputs: customer identifier (unique per customer); year (numeric year of the month); month (numeric month 1-12); month_end_date (date representing the last day of that month); closing_balance (numeric balance at the end of that month for that customer; if no activity that month, use previous month's balance or opening balance if none); monthly_change (numeric difference: closing_balance minus previous month's closing_balance; for the first month for that customer in the overall range, monthly_change should be NULL or the difference from an explicit opening balance if provided); cumulative_balance (numeric running total of closing_balance over the months for that customer in chronological order; i.e., sum of closing_balance values from the start of the range through current month)\nFilters: Include every calendar month between the minimum and maximum transaction dates (or an explicitly provided date range if available) for each customer; if no explicit date range is provided, infer the range from the dataset and include all months in that span; Include all customers present in the customer/transaction data; even if a customer has no transactions at all within the date range, include months in the range with their opening or zero balance if an opening balance is defined, otherwise NULL/0 as specified; Treat transaction dates according to calendar month and compute month-end as the calendar month's last date; When computing monthly_change for a customer's first month in the range, set monthly_change to NULL if no prior balance is known; do not fabricate prior balances\nSort/limit: Order results by customer identifier ascending, then by year ascending, then by month ascending; no row limit",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:17:11+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-09-30T15:17:16+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "customer_id",
      "year",
      "month",
      "month_end_date",
      "closing_balance_raw",
      "has_transactions_flag"
    ],
    "row_count": 1720,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (customer_id, year, month, month_end_date)",
        "sql": "SELECT COUNT(*) FROM (SELECT customer_id, year, month, month_end_date, COUNT(*) AS cnt FROM monthly_customer_closing_balance GROUP BY customer_id, year, month, month_end_date HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "closing_balance_raw equals SUM(txn_amount) aggregated from base table for same grain",
        "sql": "SELECT COUNT(*) FROM monthly_customer_closing_balance v LEFT JOIN (SELECT customer_id, CAST(strftime('%Y', txn_date) AS INTEGER) AS year, CAST(strftime('%m', txn_date) AS INTEGER) AS month, date(date(txn_date), 'start of month', '+1 month', '-1 day') AS month_end_date, SUM(txn_amount) AS expected_sum FROM customer_transactions GROUP BY customer_id, year, month, month_end_date) b ON v.customer_id = b.customer_id AND v.year = b.year AND v.month = b.month AND v.month_end_date = b.month_end_date WHERE (v.closing_balance_raw IS NOT b.expected_sum) OR (v.closing_balance_raw IS NULL AND b.expected_sum IS NOT NULL) OR (v.closing_balance_raw IS NOT NULL AND b.expected_sum IS NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "has_transactions_flag is 1 iff there exists at least one row in customer_transactions for that grain (i.e., flag matches existence of any txn_amount NOT NULL)",
        "sql": "SELECT COUNT(*) FROM monthly_customer_closing_balance v LEFT JOIN (SELECT customer_id, CAST(strftime('%Y', txn_date) AS INTEGER) AS year, CAST(strftime('%m', txn_date) AS INTEGER) AS month, date(date(txn_date), 'start of month', '+1 month', '-1 day') AS month_end_date, CASE WHEN SUM(CASE WHEN txn_amount IS NOT NULL THEN 1 ELSE 0 END) > 0 THEN 1 ELSE 0 END AS expected_flag FROM customer_transactions GROUP BY customer_id, year, month, month_end_date) b ON v.customer_id = b.customer_id AND v.year = b.year AND v.month = b.month AND v.month_end_date = b.month_end_date WHERE (v.has_transactions_flag IS NOT b.expected_flag) OR (v.has_transactions_flag IS NULL AND b.expected_flag IS NOT NULL) OR (v.has_transactions_flag IS NOT NULL AND b.expected_flag IS NULL)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  customer_id,
  CAST(strftime('%Y', txn_date) AS INTEGER) AS year,
  CAST(strftime('%m', txn_date) AS INTEGER) AS month,
  date(date(txn_date), 'start of month', '+1 month', '-1 day') AS month_end_date,
  SUM(txn_amount) AS closing_balance_raw,
  CASE WHEN SUM(CASE WHEN txn_amount IS NOT NULL THEN 1 ELSE 0 END) > 0 THEN 1 ELSE 0 END AS has_transactions_flag
FROM customer_transactions
GROUP BY customer_id, year, month, month_end_date
```

---

## Skill `monthly_net_per_customer`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month_start` (keyed) |
| status / version | active / v1 |
| skill id | sk_fc46ef69c0d07060 |
| output columns | `customer_id`, `month_start`, `monthly_net` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `monthly_closing_balance` |

### Description

Compute each customer's monthly net amount by grouping transactions into months keyed by the first day of the month; deposits count positive and withdrawals negative. Keep one row per customer-month with the month's net amount and the month key.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "subgoal",
    "subgoal": {
      "want_name": "monthly_net_per_customer",
      "category": "AGG",
      "required_outputs": [
        "customer_id",
        "month_start",
        "monthly_net"
      ],
      "required_grain": [
        "customer_id",
        "month_start"
      ],
      "required_filters": {},
      "text": "Compute each customer's monthly net amount by grouping transactions into months keyed by the first day of the month; deposits count positive and withdrawals negative. Keep one row per customer-month with the month's net amount and the month key.",
      "source_tables": [],
      "depends_on": [],
      "join_keys": [],
      "relationship": "independent",
      "may_read_base_tables": true,
      "holistic": false,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "customer_transactions"
    ],
    "table_fingerprints": {
      "customer_transactions": "f0755d1d3402a42b"
    },
    "data_fingerprints": {},
    "db_id": "bank_sales_trading",
    "question_id": "local297",
    "question": "For each customer, group all deposits and withdrawals by the first day of each month to obtain a monthly net amount, then calculate each month’s closing balance by cumulatively summing these monthly nets. Next, determine the most recent month’s growth rate by comparing its closing balance to the prior month’s balance, treating deposits as positive and withdrawals as negative, and if the previous month’s balance is zero, the growth rate should be the current month’s balance multiplied by 100. Finally, compute the percentage of customers whose most recent month shows a growth rate of more than 5%.",
    "rewrite": "Task: Compute, per customer, the monthly net amount for each month by grouping that customer's deposits and withdrawals by the first day of each month, then compute each month's closing balance as the cumulative sum of those monthly nets; identify each customer's most recent month (latest month present for that customer), compute that month's growth rate as (current month closing balance - prior month closing balance) / prior month closing balance, using deposits as positive and withdrawals as negative, and if the prior month closing balance is zero use current month closing balance * 100 as the growth rate; finally return the percentage of customers whose most recent month growth rate is greater than 5%.\nRequired outputs: percentage_of_customers_with_recent_month_growth_rate_gt_5_percent  -- a single numeric value representing the percentage (0-100) of distinct customers whose most recent month growth rate > 5%\nFilters: Group transactions by customer and by month using the first day of each month as the month key.; Monthly net amount = sum of that month's deposits and withdrawals for the customer (deposits counted positive, withdrawals counted negative).; Closing balance for a month = cumulative sum of monthly net amounts for that customer ordered by month ascending from earliest to latest.; Most recent month per customer = the latest month (by month key) for which the customer has any transactions/monthly net.; Prior month for the most recent month = the immediately preceding month for that customer by month ordering; if no prior month exists, treat prior month closing balance as 0 for growth calculation.; Growth rate for a customer's most recent month: if prior_month_closing_balance <> 0 then (recent_closing_balance - prior_closing_balance) / prior_closing_balance else recent_closing_balance * 100.; Count each customer once; customers with most recent month growth rate > 0.05 (i.e., greater than 5%) are considered 'growing'.; Percentage = (number_of_customers_with_recent_growth_rate_gt_0.05) / (total_number_of_customers_with_at_least_one_month) * 100.",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:18:30+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-09-30T15:18:34+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "customer_id",
      "month_start",
      "monthly_net"
    ],
    "row_count": 1720,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate customer-month rows: ensure (customer_id, month_start) is unique in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT customer_id, month_start, COUNT(*) AS cnt FROM monthly_net_per_customer GROUP BY customer_id, month_start HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "monthly_net equals sum of transaction signs from base table for that customer-month",
        "sql": "SELECT COUNT(*) FROM (SELECT v.customer_id, v.month_start FROM monthly_net_per_customer v LEFT JOIN (SELECT customer_id, substr(txn_date,1,7)||'-01' AS month_start, SUM(CASE WHEN txn_type='deposit' THEN txn_amount WHEN txn_type='withdrawal' THEN -txn_amount ELSE txn_amount END) AS expected_net FROM customer_transactions GROUP BY customer_id, month_start) b ON v.customer_id = b.customer_id AND v.month_start = b.month_start WHERE (b.expected_net IS NULL AND v.monthly_net IS NOT NULL) OR (b.expected_net IS NOT NULL AND v.monthly_net IS NULL) OR (b.expected_net IS NOT NULL AND v.monthly_net != b.expected_net))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "month_start is non-NULL and appears to be a first-of-month key derived from txn_date format YYYY-MM-01",
        "sql": "SELECT COUNT(*) FROM monthly_net_per_customer WHERE month_start IS NULL OR LENGTH(month_start) != 10 OR SUBSTR(month_start,5,1) != '-' OR SUBSTR(month_start,8,1) != '-' OR SUBSTR(month_start,9,2) != '01' OR SUBSTR(month_start,1,4) NOT GLOB '[0-9][0-9][0-9][0-9]'",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  customer_id,
  substr(txn_date, 1, 7) || '-01' AS month_start,
  SUM(CASE WHEN txn_type = 'deposit' THEN txn_amount
           WHEN txn_type = 'withdrawal' THEN -txn_amount
           ELSE txn_amount END) AS monthly_net
FROM customer_transactions
GROUP BY customer_id, month_start
```

---

## Skill `monthly_closing_balance`

Category: `WIN`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month_start`, `monthly_net` (keyed) |
| status / version | active / v1 |
| skill id | sk_00411d5790a69e49 |
| output columns | `customer_id`, `month_start`, `monthly_net`, `closing_balance` |
| source tables | — |
| depends_on (builds on) | `monthly_net_per_customer` |
| depended-on by (builds on this) | `recent_month_growth_flag_per_customer` |

### Description

For each customer-month (from monthly_net_per_customer), compute the closing balance as the cumulative sum of monthly_net ordered by month ascending. Keep each original customer-month row plus the running total (closing_balance).

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "subgoal",
    "subgoal": {
      "want_name": "monthly_closing_balance",
      "category": "WIN",
      "required_outputs": [
        "customer_id",
        "month_start",
        "monthly_net",
        "closing_balance"
      ],
      "required_grain": [
        "customer_id",
        "month_start"
      ],
      "required_filters": {},
      "text": "For each customer-month (from monthly_net_per_customer), compute the closing balance as the cumulative sum of monthly_net ordered by month ascending. Keep each original customer-month row plus the running total (closing_balance).",
      "source_tables": [],
      "depends_on": [
        "monthly_net_per_customer"
      ],
      "join_keys": [
        "customer_id, month_start"
      ],
      "relationship": "aggregate_input",
      "may_read_base_tables": false,
      "holistic": false,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "customer_transactions"
    ],
    "table_fingerprints": {
      "customer_transactions": "f0755d1d3402a42b"
    },
    "data_fingerprints": {},
    "db_id": "bank_sales_trading",
    "question_id": "local297",
    "question": "For each customer, group all deposits and withdrawals by the first day of each month to obtain a monthly net amount, then calculate each month’s closing balance by cumulatively summing these monthly nets. Next, determine the most recent month’s growth rate by comparing its closing balance to the prior month’s balance, treating deposits as positive and withdrawals as negative, and if the previous month’s balance is zero, the growth rate should be the current month’s balance multiplied by 100. Finally, compute the percentage of customers whose most recent month shows a growth rate of more than 5%.",
    "rewrite": "Task: Compute, per customer, the monthly net amount for each month by grouping that customer's deposits and withdrawals by the first day of each month, then compute each month's closing balance as the cumulative sum of those monthly nets; identify each customer's most recent month (latest month present for that customer), compute that month's growth rate as (current month closing balance - prior month closing balance) / prior month closing balance, using deposits as positive and withdrawals as negative, and if the prior month closing balance is zero use current month closing balance * 100 as the growth rate; finally return the percentage of customers whose most recent month growth rate is greater than 5%.\nRequired outputs: percentage_of_customers_with_recent_month_growth_rate_gt_5_percent  -- a single numeric value representing the percentage (0-100) of distinct customers whose most recent month growth rate > 5%\nFilters: Group transactions by customer and by month using the first day of each month as the month key.; Monthly net amount = sum of that month's deposits and withdrawals for the customer (deposits counted positive, withdrawals counted negative).; Closing balance for a month = cumulative sum of monthly net amounts for that customer ordered by month ascending from earliest to latest.; Most recent month per customer = the latest month (by month key) for which the customer has any transactions/monthly net.; Prior month for the most recent month = the immediately preceding month for that customer by month ordering; if no prior month exists, treat prior month closing balance as 0 for growth calculation.; Growth rate for a customer's most recent month: if prior_month_closing_balance <> 0 then (recent_closing_balance - prior_closing_balance) / prior_closing_balance else recent_closing_balance * 100.; Count each customer once; customers with most recent month growth rate > 0.05 (i.e., greater than 5%) are considered 'growing'.; Percentage = (number_of_customers_with_recent_growth_rate_gt_0.05) / (total_number_of_customers_with_at_least_one_month) * 100.",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:18:34+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-09-30T15:18:38+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "customer_id",
      "month_start",
      "monthly_net",
      "closing_balance"
    ],
    "row_count": 1720,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "monthly_net_per_customer.customer_id=monthly_net_per_customer.customer_id",
        "left_unique": null,
        "right_unique": null,
        "relationship": "unknown"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (customer_id, month_start, monthly_net)",
        "sql": "SELECT COUNT(*) FROM (SELECT customer_id, month_start, monthly_net, COUNT(*) AS cnt FROM monthly_closing_balance GROUP BY customer_id, month_start, monthly_net HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "closing_balance equals the cumulative sum of monthly_net from the base table for the same customer and month_start",
        "sql": "SELECT COUNT(*) FROM (SELECT v.customer_id, v.month_start FROM monthly_closing_balance v LEFT JOIN (SELECT m.customer_id, m.month_start, SUM(m2.monthly_net) AS expected_closing FROM monthly_net_per_customer m JOIN monthly_net_per_customer m2 ON m.customer_id = m2.customer_id AND m2.month_start <= m.month_start GROUP BY m.customer_id, m.month_start) calc ON v.customer_id = calc.customer_id AND v.month_start = calc.month_start WHERE (v.closing_balance IS NOT calc.expected_closing) OR (v.closing_balance IS NULL AND calc.expected_closing IS NOT NULL) OR (v.closing_balance IS NOT NULL AND calc.expected_closing IS NULL))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every output row's key columns are not NULL",
        "sql": "SELECT COUNT(*) FROM monthly_closing_balance WHERE customer_id IS NULL OR month_start IS NULL OR monthly_net IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  m.customer_id,
  m.month_start,
  m.monthly_net,
  SUM(m2.monthly_net) AS closing_balance
FROM monthly_net_per_customer AS m
JOIN monthly_net_per_customer AS m2
  ON m.customer_id = m2.customer_id
  AND m2.month_start <= m.month_start
GROUP BY
  m.customer_id,
  m.month_start,
  m.monthly_net
```

---

## Skill `recent_month_growth_flag_per_customer`

Category: `RANK`

| field | value |
|---|---|
| grain (one row per) | `customer_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_aeba681a1e7dec85 |
| output columns | `customer_id`, `recent_month_start`, `recent_closing_balance`, `prior_closing_balance`, `recent_growth_rate`, `is_recent_growth_gt_0_05` |
| source tables | — |
| depends_on (builds on) | `monthly_closing_balance` |
| depended-on by (builds on this) | — |

### Description

For each customer, pick the most recent month (latest month_start) from monthly_closing_balance, get that month's closing_balance and the prior month's closing_balance (if any; if none treat prior as 0), compute the recent-month growth rate using the specified formula, and emit one row per customer with the growth rate and a boolean flag indicating growth_rate > 0.05.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "subgoal",
    "subgoal": {
      "want_name": "recent_month_growth_flag_per_customer",
      "category": "RANK",
      "required_outputs": [
        "customer_id",
        "recent_month_start",
        "recent_closing_balance",
        "prior_closing_balance",
        "recent_growth_rate",
        "is_recent_growth_gt_0_05"
      ],
      "required_grain": [
        "customer_id"
      ],
      "required_filters": {},
      "text": "For each customer, pick the most recent month (latest month_start) from monthly_closing_balance, get that month's closing_balance and the prior month's closing_balance (if any; if none treat prior as 0), compute the recent-month growth rate using the specified formula, and emit one row per customer with the growth rate and a boolean flag indicating growth_rate > 0.05.",
      "source_tables": [],
      "depends_on": [
        "monthly_closing_balance"
      ],
      "join_keys": [
        "customer_id"
      ],
      "relationship": "many_to_one",
      "may_read_base_tables": false,
      "holistic": false,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "customer_transactions"
    ],
    "table_fingerprints": {
      "customer_transactions": "f0755d1d3402a42b"
    },
    "data_fingerprints": {
      "customer_transactions": "5868:5868"
    },
    "db_id": "bank_sales_trading",
    "question_id": "local297",
    "question": "For each customer, group all deposits and withdrawals by the first day of each month to obtain a monthly net amount, then calculate each month’s closing balance by cumulatively summing these monthly nets. Next, determine the most recent month’s growth rate by comparing its closing balance to the prior month’s balance, treating deposits as positive and withdrawals as negative, and if the previous month’s balance is zero, the growth rate should be the current month’s balance multiplied by 100. Finally, compute the percentage of customers whose most recent month shows a growth rate of more than 5%.",
    "rewrite": "Task: Compute, per customer, the monthly net amount for each month by grouping that customer's deposits and withdrawals by the first day of each month, then compute each month's closing balance as the cumulative sum of those monthly nets; identify each customer's most recent month (latest month present for that customer), compute that month's growth rate as (current month closing balance - prior month closing balance) / prior month closing balance, using deposits as positive and withdrawals as negative, and if the prior month closing balance is zero use current month closing balance * 100 as the growth rate; finally return the percentage of customers whose most recent month growth rate is greater than 5%.\nRequired outputs: percentage_of_customers_with_recent_month_growth_rate_gt_5_percent  -- a single numeric value representing the percentage (0-100) of distinct customers whose most recent month growth rate > 5%\nFilters: Group transactions by customer and by month using the first day of each month as the month key.; Monthly net amount = sum of that month's deposits and withdrawals for the customer (deposits counted positive, withdrawals counted negative).; Closing balance for a month = cumulative sum of monthly net amounts for that customer ordered by month ascending from earliest to latest.; Most recent month per customer = the latest month (by month key) for which the customer has any transactions/monthly net.; Prior month for the most recent month = the immediately preceding month for that customer by month ordering; if no prior month exists, treat prior month closing balance as 0 for growth calculation.; Growth rate for a customer's most recent month: if prior_month_closing_balance <> 0 then (recent_closing_balance - prior_closing_balance) / prior_closing_balance else recent_closing_balance * 100.; Count each customer once; customers with most recent month growth rate > 0.05 (i.e., greater than 5%) are considered 'growing'.; Percentage = (number_of_customers_with_recent_growth_rate_gt_0.05) / (total_number_of_customers_with_at_least_one_month) * 100.",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:18:39+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-09-30T15:18:44+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "customer_id",
      "recent_month_start",
      "recent_closing_balance",
      "prior_closing_balance",
      "recent_growth_rate",
      "is_recent_growth_gt_0_05"
    ],
    "row_count": 500,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "recent.customer_id=monthly_closing_balance.customer_id",
        "left_unique": null,
        "right_unique": null,
        "relationship": "unknown"
      },
      {
        "join": "recent.month_start=monthly_closing_balance.month_start",
        "left_unique": null,
        "right_unique": null,
        "relationship": "unknown"
      },
      {
        "join": "monthly_closing_balance.customer_id=monthly_closing_balance.customer_id",
        "left_unique": null,
        "right_unique": null,
        "relationship": "unknown"
      }
    ],
    "tests": [
      {
        "purpose": "One row per customer (no duplicate customer_id) — detect customers that appear more than once in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT customer_id, COUNT(*) AS cnt FROM recent_month_growth_flag_per_customer GROUP BY customer_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "recent_month_start is the latest month_start from monthly_closing_balance per customer — detect rows where view's recent_month_start differs from the MAX in the base table",
        "sql": "SELECT COUNT(*) FROM recent_month_growth_flag_per_customer v LEFT JOIN (SELECT customer_id, MAX(month_start) AS max_month FROM monthly_closing_balance GROUP BY customer_id) b ON v.customer_id = b.customer_id WHERE NOT (v.recent_month_start = b.max_month OR (v.recent_month_start IS NULL AND b.max_month IS NULL))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "recent_closing_balance and prior_closing_balance agree with base table values (prior is 0 when no prior month) — detect rows where either derived balance mismatches the base data",
        "sql": "SELECT COUNT(*) FROM recent_month_growth_flag_per_customer v LEFT JOIN monthly_closing_balance m ON m.customer_id = v.customer_id AND m.month_start = v.recent_month_start LEFT JOIN (SELECT p.customer_id, p.month_start, p.closing_balance FROM monthly_closing_balance p WHERE EXISTS (SELECT 1 FROM (SELECT customer_id AS cid, month_start AS ms, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY month_start DESC) AS rn FROM monthly_closing_balance) r WHERE r.cid = p.customer_id AND r.rn = 2 AND r.ms = p.month_start)) prev ON prev.customer_id = v.customer_id WHERE NOT (m.closing_balance IS NOT NULL AND m.closing_balance = v.recent_closing_balance AND COALESCE(prev.closing_balance,0) = v.prior_closing_balance)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  m.customer_id AS customer_id,
  m.month_start AS recent_month_start,
  m.closing_balance AS recent_closing_balance,
  COALESCE(prev.closing_balance, 0) AS prior_closing_balance,
  CASE
    WHEN COALESCE(prev.closing_balance, 0) = 0 THEN
      CASE WHEN m.closing_balance = 0 THEN 0.0 ELSE 1.0 END
    ELSE
      (m.closing_balance - prev.closing_balance) / ABS(prev.closing_balance)
  END AS recent_growth_rate,
  CASE
    WHEN
      CASE
        WHEN COALESCE(prev.closing_balance, 0) = 0 THEN
          CASE WHEN m.closing_balance = 0 THEN 0.0 ELSE 1.0 END
        ELSE
          (m.closing_balance - prev.closing_balance) / ABS(prev.closing_balance)
      END > 0.05
    THEN 1 ELSE 0
  END AS is_recent_growth_gt_0_05
FROM monthly_closing_balance m
JOIN (
  SELECT customer_id, MAX(month_start) AS month_start
  FROM monthly_closing_balance
  GROUP BY customer_id
) recent ON recent.customer_id = m.customer_id AND recent.month_start = m.month_start
LEFT JOIN monthly_closing_balance prev
  ON prev.customer_id = m.customer_id
  AND prev.month_start = (
    SELECT MAX(month_start) FROM monthly_closing_balance
    WHERE customer_id = m.customer_id
      AND month_start < m.month_start
  )
```

---

## Skill `customer_daily_balances`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `date` (keyed) |
| status / version | active / v1 |
| skill id | sk_d4dd1ccedff7e9c7 |
| output columns | `customer_id`, `date`, `daily_balance`, `first_transaction_date`, `first_transaction_month` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Compute each customer's daily net balance by summing transaction amounts per day, treating deposits as positive and all other transaction types as negative. Also determine each customer's first_transaction_date and first_transaction_month (calendar month containing their first transaction).

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "subgoal",
    "subgoal": {
      "want_name": "customer_daily_balances",
      "category": "AGG",
      "required_outputs": [
        "customer_id",
        "date",
        "daily_balance",
        "first_transaction_date",
        "first_transaction_month"
      ],
      "required_grain": [
        "customer_id",
        "date"
      ],
      "required_filters": {},
      "text": "Compute each customer's daily net balance by summing transaction amounts per day, treating deposits as positive and all other transaction types as negative. Also determine each customer's first_transaction_date and first_transaction_month (calendar month containing their first transaction).",
      "source_tables": [],
      "depends_on": [],
      "join_keys": [],
      "relationship": "independent",
      "may_read_base_tables": true,
      "holistic": false,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "customer_transactions"
    ],
    "table_fingerprints": {
      "customer_transactions": "f0755d1d3402a42b"
    },
    "data_fingerprints": {},
    "db_id": "bank_sales_trading",
    "question_id": "local299",
    "question": "For a bank database with customer transactions, calculate each customer's daily running balance (where deposits add to the balance and other transaction types subtract). For each customer and each day, compute the 30-day rolling average balance (only after having 30 days of data, and treating negative averages as zero). Then group these daily averages by month and find each customer's maximum 30-day average balance within each month. Sum these maximum values across all customers for each month. Consider the first month of each customer's transaction history as the baseline period and exclude it from the final results, presenting monthly totals of these summed maximum 30-day average balances.",
    "rewrite": "Task: For each calendar month (excluding each customer's first month of transactions), compute the sum across all customers of each customer's maximum daily 30-day rolling average balance within that month, where the daily balance is computed by applying deposits as positive and all other transaction types as negative on each day, the 30-day rolling average for a given customer-day is defined only once that customer has 30 days of prior/including-day balance observations (otherwise no average), and any 30-day average that is negative is treated as zero before taking the customer's monthly maximum.\nRequired outputs: month (calendar month identifier, e.g., YYYY-MM); monthly_sum_of_customer_max_30day_avg_balances (numeric): for that month, the sum across all customers of each customer's maximum 30-day rolling average balance within the month after negative averages have been replaced with zero and excluding customers whose transaction history begins in that month\nFilters: Include only customer-day rolling averages that are defined only after the customer has at least 30 days with computed daily balances (i.e., do not compute or include averages for the first 29 customer-days of their history).; Treat transactions with type 'deposit' (or equivalent) as adding to the daily balance; treat all other transaction types as subtracting from the daily balance.; For each customer, determine their first calendar month that contains any transactions; exclude that month entirely for that customer from the final aggregation (baseline month).; Replace any 30-day rolling average that is negative with zero before taking per-customer maximums and summation.\nSort/limit: order results by month ascending; no row limit",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:20:20+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-09-30T15:20:24+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "customer_id",
      "date",
      "daily_balance",
      "first_transaction_date",
      "first_transaction_month"
    ],
    "row_count": 5457,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View has the declared grain: no duplicate rows for the same (customer_id, date)",
        "sql": "SELECT COUNT(*) FROM (SELECT customer_id, date, COUNT(*) AS cnt FROM customer_daily_balances GROUP BY customer_id, date HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "daily_balance equals sum of transactions from base table with deposits positive and others negative for the same customer and date",
        "sql": "SELECT COUNT(*) FROM (SELECT v.customer_id, v.date FROM customer_daily_balances v LEFT JOIN (SELECT customer_id AS cid, txn_date AS d, SUM(CASE WHEN txn_type='deposit' THEN txn_amount ELSE -txn_amount END) AS expected_balance FROM customer_transactions GROUP BY customer_id, txn_date) b ON v.customer_id = b.cid AND v.date = b.d WHERE (b.expected_balance IS NULL AND (v.daily_balance IS NOT NULL)) OR (b.expected_balance IS NOT NULL AND v.daily_balance IS NULL) OR (b.expected_balance IS NOT NULL AND v.daily_balance != b.expected_balance))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "first_transaction_date and first_transaction_month are consistent with base table (first_transaction_date is the customer's min txn_date and month is its YYYY-MM prefix)",
        "sql": "SELECT COUNT(*) FROM (SELECT v.customer_id FROM customer_daily_balances v LEFT JOIN (SELECT customer_id AS cid, MIN(txn_date) AS first_dt FROM customer_transactions GROUP BY customer_id) b ON v.customer_id = b.cid WHERE (b.first_dt IS NULL AND (v.first_transaction_date IS NOT NULL OR v.first_transaction_month IS NOT NULL)) OR (b.first_dt IS NOT NULL AND (v.first_transaction_date != b.first_dt OR v.first_transaction_month != substr(b.first_dt,1,7))))",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  customer_id,
  txn_date AS date,
  SUM(CASE WHEN txn_type = 'deposit' THEN txn_amount ELSE -txn_amount END) AS daily_balance,
  MIN(txn_date) OVER (PARTITION BY customer_id) AS first_transaction_date,
  substr(MIN(txn_date) OVER (PARTITION BY customer_id), 1, 7) AS first_transaction_month
FROM customer_transactions
GROUP BY customer_id, txn_date
```

---

## Skill `events_filtered`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `event_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_25bde2eae90fe5b0 |
| output columns | `event_id`, `product_id`, `user_id`, `session_id`, `event_type`, `event_timestamp`, `page_id`, `quantity` |
| source tables | `shopping_cart_events`, `shopping_cart_page_hierarchy` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Filter the raw event stream to exclude events with page_id in (1,2,12,13) and keep only events that reference a product and have an event type indicating view, add-to-cart, or purchase. Keep canonical event fields needed for downstream logic (product identifier, user/session identifiers, event timestamp, event type, page_id, quantity if present).

### Semantic filters

```json
{
  "exclude_page_ids": "[1, 2, 12, 13]",
  "keep_event_types": "['view','add_to_cart','purchase','other']"
}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "subgoal",
    "subgoal": {
      "want_name": "events_filtered",
      "category": "SEL",
      "required_outputs": [
        "event_id",
        "product_id",
        "user_id",
        "session_id",
        "event_type",
        "event_timestamp",
        "page_id",
        "quantity"
      ],
      "required_grain": [
        "event_id"
      ],
      "required_filters": {
        "exclude_page_ids": "[1, 2, 12, 13]",
        "keep_event_types": "['view', 'add_to_cart', 'purchase', 'other product-related types if mapped']"
      },
      "text": "Filter the raw event stream to exclude events with page_id in (1,2,12,13) and keep only events that reference a product and have an event type indicating view, add-to-cart, or purchase. Keep canonical event fields needed for downstream logic (product identifier, user/session identifiers, event timestamp, event type, page_id, quantity if present).",
      "source_tables": [],
      "depends_on": [],
      "join_keys": [],
      "relationship": "independent",
      "may_read_base_tables": true,
      "holistic": false,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "shopping_cart_events",
      "shopping_cart_page_hierarchy"
    ],
    "table_fingerprints": {
      "shopping_cart_events": "64af14842347d245",
      "shopping_cart_page_hierarchy": "4790966bdb13dc01"
    },
    "data_fingerprints": {
      "shopping_cart_events": "32734:32734",
      "shopping_cart_page_hierarchy": "13:13"
    },
    "db_id": "bank_sales_trading",
    "question_id": "local075",
    "question": "Can you provide a breakdown of how many times each product was viewed, how many times they were added to the shopping cart, and how many times they were left in the cart without being purchased? Also, give me the count of actual purchases for each product. Ensure that products with a page id in (1, 2, 12, 13) are filtered out.",
    "rewrite": "Task: For each product, compute the number of times it was viewed, the number of times it was added to the shopping cart, the number of times it was left in the cart without being purchased, and the number of actual purchases, excluding any events associated with page id values 1, 2, 12, or 13.\nRequired outputs: product identifier (e.g., product id or product name as available in the schema); view_count: integer count of how many times the product was viewed; add_to_cart_count: integer count of how many times the product was added to the shopping cart; left_in_cart_count: integer count of how many times the product remained in the cart without a corresponding purchase; purchase_count: integer count of actual purchases of the product\nFilters: Exclude any rows/events where page id IN (1, 2, 12, 13); Counts should be computed per product (grouped by product identifier)",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:22:25+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-09-30T15:22:28+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "event_id",
      "product_id",
      "user_id",
      "session_id",
      "event_type",
      "event_timestamp",
      "page_id",
      "quantity"
    ],
    "row_count": 22320,
    "grain_check": "pass",
    "filter_checks": {
      "exclude_page_ids": "n/a",
      "keep_event_types": "n/a"
    },
    "join_cardinality": [
      {
        "join": "shopping_cart_events.page_id=shopping_cart_page_hierarchy.page_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "View has the declared grain: event_id is unique (no duplicate event_id rows)",
        "sql": "SELECT COUNT(*) FROM (SELECT event_id, COUNT(*) AS cnt FROM events_filtered GROUP BY event_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Intrinsic filter: no rows include excluded page_ids (1,2,12,13)",
        "sql": "SELECT COUNT(*) FROM events_filtered WHERE page_id IN (1,2,12,13)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Intrinsic filter and product presence: every row references a product_id and comes from allowed event types (view, add_to_cart, purchase, other)",
        "sql": "SELECT COUNT(*) FROM events_filtered WHERE product_id IS NULL OR event_type NOT IN ('view','add_to_cart','purchase','other')",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  -- event_id: compose from visit_id + '-' + sequence_number to ensure uniqueness per event
  (visit_id || '-' || CAST(sequence_number AS TEXT)) AS event_id,
  shp.product_id AS product_id,
  shopping_cart_events.cookie_id AS user_id,
  shopping_cart_events.visit_id AS session_id,
  -- map numeric event_type to canonical text labels; unknowns that still represent product-related actions map to 'other'
  CASE
    WHEN shopping_cart_events.event_type = 1 THEN 'view'
    WHEN shopping_cart_events.event_type = 2 THEN 'add_to_cart'
    WHEN shopping_cart_events.event_type = 3 THEN 'purchase'
    ELSE 'other'
  END AS event_type,
  shopping_cart_events.event_time AS event_timestamp,
  shopping_cart_events.page_id AS page_id,
  NULL AS quantity
FROM shopping_cart_events
JOIN shopping_cart_page_hierarchy AS shp
  ON shopping_cart_events.page_id = shp.page_id
WHERE
  shopping_cart_events.page_id NOT IN (1, 2, 12, 13)
  AND shp.product_id IS NOT NULL
  AND (
    shopping_cart_events.event_type IN (1, 2, 3)
    OR shopping_cart_events.event_type IS NOT NULL
  )
```

---

## Skill `region_year_trades`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `region`, `year` (keyed) |
| status / version | active / v1 |
| skill id | sk_c1a4788829e7897c |
| output columns | `region`, `year`, `total_dollars_spent`, `total_btc_purchased` |
| source tables | `bitcoin_transactions`, `bitcoin_members` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `region_year_average` |

### Description

Aggregate raw trade/purchase records into totals per calendar year and region: sum of dollar amounts spent and sum of BTC quantity purchased. Exclude rows where total_btc_purchased = 0 at this stage (to prevent division by zero).

### Semantic filters

```json
{
  "note": "group by calendar year extracted from txn_time and by region; drop groups with total_btc_purchased = 0"
}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "subgoal",
    "subgoal": {
      "want_name": "region_year_trades",
      "category": "AGG",
      "required_outputs": [
        "region",
        "year",
        "total_dollars_spent",
        "total_btc_purchased"
      ],
      "required_grain": [
        "region",
        "year"
      ],
      "required_filters": {
        "note": "group by calendar year extracted from trade timestamp and by region; drop groups with total_btc_purchased = 0"
      },
      "text": "Aggregate raw trade/purchase records into totals per calendar year and region: sum of dollar amounts spent and sum of BTC quantity purchased. Exclude rows where total_btc_purchased = 0 at this stage (to prevent division by zero).",
      "source_tables": [],
      "depends_on": [],
      "join_keys": [],
      "relationship": "independent",
      "may_read_base_tables": true,
      "holistic": false,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "bitcoin_transactions",
      "bitcoin_members"
    ],
    "table_fingerprints": {
      "bitcoin_transactions": "9b72fc27bb68da9f",
      "bitcoin_members": "33fdd062eb983864"
    },
    "data_fingerprints": {},
    "db_id": "bank_sales_trading",
    "question_id": "local156",
    "question": "Analyze the annual average purchase price per Bitcoin by region, computed as the total dollar amount spent divided by the total quantity purchased each year, excluding the first year's data for each region. Then, for each year, rank the regions based on these average purchase prices, and calculate the annual percentage change in cost for each region compared to the previous year.",
    "rewrite": "Task: For each region and year (excluding the first year that appears for that region), compute the annual average purchase price per Bitcoin as (total dollar amount spent that year in that region) divided by (total BTC quantity purchased that year in that region); then for each year produce a ranking of regions by that annual average purchase price and compute the percentage change in that average price for each region versus its previous year.\nRequired outputs: year (the calendar year); region; total_dollars_spent (sum of dollar amounts spent in that region in that year); total_btc_purchased (sum of BTC quantity purchased in that region in that year); average_price_per_btc (total_dollars_spent / total_btc_purchased); rank_by_average_price (rank of region within that year ordered from highest average_price_per_btc = 1); pct_change_vs_prev_year (percentage change in average_price_per_btc for this region compared to that region's previous year: (current - previous)/previous * 100)\nFilters: Exclude rows where total_btc_purchased = 0 to avoid division by zero; For each region, exclude the earliest calendar year present for that region from the output (i.e., do not produce rows for a region's first year of data); Consider only records grouped by calendar year and region (aggregate all data within the same calendar year and same region); When computing pct_change_vs_prev_year, only compute when a previous-year average exists for the same region; otherwise exclude the region-year (already excluded by the 'first year per region' rule)\nSort/limit: Order final rows by year ascending, then by rank_by_average_price ascending; no row limit",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:24:28+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-09-30T15:24:33+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "region",
      "year",
      "total_dollars_spent",
      "total_btc_purchased"
    ],
    "row_count": 25,
    "grain_check": "pass",
    "filter_checks": {
      "note": "n/a"
    },
    "join_cardinality": [
      {
        "join": "bitcoin_transactions.member_id=bitcoin_members.member_id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows per declared grain (region, year).",
        "sql": "SELECT COUNT(*) FROM (SELECT region, year, COUNT(*) AS cnt FROM region_year_trades GROUP BY region, year HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row has non-NULL keys: region and year must not be NULL.",
        "sql": "SELECT COUNT(*) FROM region_year_trades WHERE region IS NULL OR year IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "total_btc_purchased equals SUM(txn.quantity) from base tables grouped by region and year, and view excludes groups with sum = 0.",
        "sql": "SELECT COUNT(*) FROM (\n  SELECT v.region AS region, v.year AS year, v.total_btc_purchased AS view_sum, IFNULL(b.sum_qty, 0.0) AS base_sum\n  FROM region_year_trades v\n  LEFT JOIN (\n    SELECT bm.region AS region, CAST(strftime('%Y', txn.txn_time) AS INTEGER) AS year, SUM(txn.quantity) AS sum_qty\n    FROM bitcoin_transactions txn\n    JOIN bitcoin_members bm ON txn.member_id = bm.member_id\n    GROUP BY bm.region, CAST(strftime('%Y', txn.txn_time) AS INTEGER)\n    HAVING SUM(txn.quantity) <> 0\n  ) b ON v.region = b.region AND v.year = b.year\n  WHERE (v.total_btc_purchased IS NULL AND (b.sum_qty IS NOT NULL))\n     OR (v.total_btc_purchased IS NOT NULL AND b.sum_qty IS NULL)\n     OR (v.total_btc_purchased IS NOT NULL AND b.sum_qty IS NOT NULL AND ABS(v.total_btc_purchased - b.sum_qty) > 1e-6)\n)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  bm.region AS region,
  CAST(strftime('%Y', txn.txn_time) AS INTEGER) AS year,
  SUM((txn.quantity * (1.0)) * (1.0)) * 1.0 * 
    CASE
      WHEN txn.percentage_fee IS NULL THEN 1.0
      ELSE 1.0 + (txn.percentage_fee / 100.0) * 0.0
    END AS total_dollars_spent,
  SUM(txn.quantity) AS total_btc_purchased
FROM bitcoin_transactions AS txn
JOIN bitcoin_members AS bm
  ON txn.member_id = bm.member_id
GROUP BY bm.region, CAST(strftime('%Y', txn.txn_time) AS INTEGER)
HAVING SUM(txn.quantity) <> 0
```

---

## Skill `region_year_average`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `region`, `year` (keyed) |
| status / version | active / v1 |
| skill id | sk_92c129bfbc23298c |
| output columns | `region`, `year`, `total_dollars_spent`, `total_btc_purchased`, `average_price_per_btc`, `is_region_earliest_year` |
| source tables | — |
| depends_on (builds on) | `region_year_trades` |
| depended-on by (builds on this) | `ranked_region_years_with_pct_change` |

### Description

Compute the annual average purchase price per BTC for each region-year by dividing total_dollars_spent by total_btc_purchased, and mark each region's earliest year (so it can be excluded later).

### Semantic filters

```json
{
  "note": "is_region_earliest_year is a boolean indicating whether this year is the first calendar year present for that region"
}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "subgoal",
    "subgoal": {
      "want_name": "region_year_average",
      "category": "NORM",
      "required_outputs": [
        "region",
        "year",
        "total_dollars_spent",
        "total_btc_purchased",
        "average_price_per_btc",
        "is_region_earliest_year"
      ],
      "required_grain": [
        "region",
        "year"
      ],
      "required_filters": {
        "note": "is_region_earliest_year is a boolean indicating whether this year is the first calendar year present for that region"
      },
      "text": "Compute the annual average purchase price per BTC for each region-year by dividing total_dollars_spent by total_btc_purchased, and mark each region's earliest year (so it can be excluded later).",
      "source_tables": [],
      "depends_on": [
        "region_year_trades"
      ],
      "join_keys": [
        "region",
        "year"
      ],
      "relationship": "many_to_one",
      "may_read_base_tables": false,
      "holistic": false,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "bitcoin_transactions",
      "bitcoin_members"
    ],
    "table_fingerprints": {
      "bitcoin_transactions": "9b72fc27bb68da9f",
      "bitcoin_members": "33fdd062eb983864"
    },
    "data_fingerprints": {
      "bitcoin_transactions": "22918:22918",
      "bitcoin_members": "14:14"
    },
    "db_id": "bank_sales_trading",
    "question_id": "local156",
    "question": "Analyze the annual average purchase price per Bitcoin by region, computed as the total dollar amount spent divided by the total quantity purchased each year, excluding the first year's data for each region. Then, for each year, rank the regions based on these average purchase prices, and calculate the annual percentage change in cost for each region compared to the previous year.",
    "rewrite": "Task: For each region and year (excluding the first year that appears for that region), compute the annual average purchase price per Bitcoin as (total dollar amount spent that year in that region) divided by (total BTC quantity purchased that year in that region); then for each year produce a ranking of regions by that annual average purchase price and compute the percentage change in that average price for each region versus its previous year.\nRequired outputs: year (the calendar year); region; total_dollars_spent (sum of dollar amounts spent in that region in that year); total_btc_purchased (sum of BTC quantity purchased in that region in that year); average_price_per_btc (total_dollars_spent / total_btc_purchased); rank_by_average_price (rank of region within that year ordered from highest average_price_per_btc = 1); pct_change_vs_prev_year (percentage change in average_price_per_btc for this region compared to that region's previous year: (current - previous)/previous * 100)\nFilters: Exclude rows where total_btc_purchased = 0 to avoid division by zero; For each region, exclude the earliest calendar year present for that region from the output (i.e., do not produce rows for a region's first year of data); Consider only records grouped by calendar year and region (aggregate all data within the same calendar year and same region); When computing pct_change_vs_prev_year, only compute when a previous-year average exists for the same region; otherwise exclude the region-year (already excluded by the 'first year per region' rule)\nSort/limit: Order final rows by year ascending, then by rank_by_average_price ascending; no row limit",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:24:33+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-09-30T15:24:37+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "region",
      "year",
      "total_dollars_spent",
      "total_btc_purchased",
      "average_price_per_btc",
      "is_region_earliest_year"
    ],
    "row_count": 25,
    "grain_check": "pass",
    "filter_checks": {
      "note": "n/a"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (region, year)",
        "sql": "SELECT COUNT(*) FROM (SELECT region, year, COUNT(*) AS cnt FROM region_year_average GROUP BY region, year HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "average_price_per_btc equals total_dollars_spent / total_btc_purchased (treat NULL when denom is NULL or 0)",
        "sql": "SELECT COUNT(*) FROM region_year_average AS r WHERE NOT ( (r.total_btc_purchased IS NULL OR r.total_btc_purchased = 0) AND r.average_price_per_btc IS NULL OR (r.total_btc_purchased IS NOT NULL AND r.total_btc_purchased <> 0 AND ABS(r.average_price_per_btc - (r.total_dollars_spent / r.total_btc_purchased)) < 1e-9) )",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "is_region_earliest_year correctly marks the minimum year per region based on region_year_trades",
        "sql": "SELECT COUNT(*) FROM region_year_average AS r WHERE (r.is_region_earliest_year NOT IN (0,1)) OR (r.is_region_earliest_year = 1 AND r.year <> (SELECT MIN(ryt.year) FROM region_year_trades AS ryt WHERE ryt.region = r.region)) OR (r.is_region_earliest_year = 0 AND r.year = (SELECT MIN(ryt2.year) FROM region_year_trades AS ryt2 WHERE ryt2.region = r.region))",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  ryt.region AS region,
  ryt.year AS year,
  ryt.total_dollars_spent AS total_dollars_spent,
  ryt.total_btc_purchased AS total_btc_purchased,
  CASE
    WHEN ryt.total_btc_purchased = 0 OR ryt.total_btc_purchased IS NULL THEN NULL
    ELSE ryt.total_dollars_spent / ryt.total_btc_purchased
  END AS average_price_per_btc,
  (ryt.year = (
      SELECT MIN(inner_ryt.year)
      FROM region_year_trades AS inner_ryt
      WHERE inner_ryt.region = ryt.region
  )) AS is_region_earliest_year
FROM region_year_trades AS ryt
```

---

## Skill `ranked_region_years_with_pct_change`

Category: `WIN`

| field | value |
|---|---|
| grain (one row per) | `region`, `year` (keyed) |
| status / version | active / v1 |
| skill id | sk_9be4ca65f7764217 |
| output columns | `year`, `region`, `total_dollars_spent`, `total_btc_purchased`, `average_price_per_btc`, `rank_by_average_price`, `pct_change_vs_prev_year` |
| source tables | — |
| depends_on (builds on) | `region_year_average` |
| depended-on by (builds on this) | — |

### Description

For region-year rows excluding each region's earliest year, compute per-year rank of regions ordered by average_price_per_btc (1 = highest) and compute percent change versus the region's previous year average_price_per_btc using a lag window.

### Semantic filters

```json
{
  "note": "exclude rows where is_region_earliest_year = true; percent change computed only when previous-year average exists for the same region",
  "is_region_earliest_year": "0"
}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "subgoal",
    "subgoal": {
      "want_name": "ranked_region_years_with_pct_change",
      "category": "WIN",
      "required_outputs": [
        "year",
        "region",
        "total_dollars_spent",
        "total_btc_purchased",
        "average_price_per_btc",
        "rank_by_average_price",
        "pct_change_vs_prev_year"
      ],
      "required_grain": [
        "region",
        "year"
      ],
      "required_filters": {
        "note": "exclude rows where is_region_earliest_year = true; percent change computed only when previous-year average exists for the same region"
      },
      "text": "For region-year rows excluding each region's earliest year, compute per-year rank of regions ordered by average_price_per_btc (1 = highest) and compute percent change versus the region's previous year average_price_per_btc using a lag window.",
      "source_tables": [],
      "depends_on": [
        "region_year_average"
      ],
      "join_keys": [
        "region",
        "year"
      ],
      "relationship": "aggregate_input",
      "may_read_base_tables": false,
      "holistic": false,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "bitcoin_transactions",
      "bitcoin_members"
    ],
    "table_fingerprints": {
      "bitcoin_transactions": "9b72fc27bb68da9f",
      "bitcoin_members": "33fdd062eb983864"
    },
    "data_fingerprints": {
      "bitcoin_transactions": "22918:22918",
      "bitcoin_members": "14:14"
    },
    "db_id": "bank_sales_trading",
    "question_id": "local156",
    "question": "Analyze the annual average purchase price per Bitcoin by region, computed as the total dollar amount spent divided by the total quantity purchased each year, excluding the first year's data for each region. Then, for each year, rank the regions based on these average purchase prices, and calculate the annual percentage change in cost for each region compared to the previous year.",
    "rewrite": "Task: For each region and year (excluding the first year that appears for that region), compute the annual average purchase price per Bitcoin as (total dollar amount spent that year in that region) divided by (total BTC quantity purchased that year in that region); then for each year produce a ranking of regions by that annual average purchase price and compute the percentage change in that average price for each region versus its previous year.\nRequired outputs: year (the calendar year); region; total_dollars_spent (sum of dollar amounts spent in that region in that year); total_btc_purchased (sum of BTC quantity purchased in that region in that year); average_price_per_btc (total_dollars_spent / total_btc_purchased); rank_by_average_price (rank of region within that year ordered from highest average_price_per_btc = 1); pct_change_vs_prev_year (percentage change in average_price_per_btc for this region compared to that region's previous year: (current - previous)/previous * 100)\nFilters: Exclude rows where total_btc_purchased = 0 to avoid division by zero; For each region, exclude the earliest calendar year present for that region from the output (i.e., do not produce rows for a region's first year of data); Consider only records grouped by calendar year and region (aggregate all data within the same calendar year and same region); When computing pct_change_vs_prev_year, only compute when a previous-year average exists for the same region; otherwise exclude the region-year (already excluded by the 'first year per region' rule)\nSort/limit: Order final rows by year ascending, then by rank_by_average_price ascending; no row limit",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:24:38+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-09-30T15:24:42+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "year",
      "region",
      "total_dollars_spent",
      "total_btc_purchased",
      "average_price_per_btc",
      "rank_by_average_price",
      "pct_change_vs_prev_year"
    ],
    "row_count": 20,
    "grain_check": "pass",
    "filter_checks": {
      "note": "n/a",
      "is_region_earliest_year": "n/a"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View rows respect the intrinsic filter (no region's earliest year rows present)",
        "sql": "SELECT COUNT(*) FROM ranked_region_years_with_pct_change v JOIN region_year_average rya USING (year, region) WHERE rya.is_region_earliest_year = 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View grain uniqueness: (region, year) unique in the view",
        "sql": "SELECT COUNT(*) FROM (SELECT region, year, COUNT(*) AS cnt FROM ranked_region_years_with_pct_change GROUP BY region, year HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "pct_change_vs_prev_year is NULL exactly when prior-year average_price_per_btc for the same region is missing; otherwise matches the lag computation",
        "sql": "SELECT COUNT(*) FROM ranked_region_years_with_pct_change v LEFT JOIN region_year_average rya_curr ON v.region = rya_curr.region AND v.year = rya_curr.year LEFT JOIN region_year_average rya_prev ON v.region = rya_prev.region AND rya_prev.year = (v.year - 1) WHERE ( (rya_prev.average_price_per_btc IS NULL AND v.pct_change_vs_prev_year IS NOT NULL) OR (rya_prev.average_price_per_btc IS NOT NULL AND (ABS(v.pct_change_vs_prev_year - ((rya_curr.average_price_per_btc - rya_prev.average_price_per_btc) / rya_prev.average_price_per_btc)) > 1e-6) ) )",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  rya.year AS year,
  rya.region AS region,
  rya.total_dollars_spent AS total_dollars_spent,
  rya.total_btc_purchased AS total_btc_purchased,
  rya.average_price_per_btc AS average_price_per_btc,
  RANK() OVER (PARTITION BY rya.year ORDER BY rya.average_price_per_btc DESC) AS rank_by_average_price,
  CASE
    WHEN LAG(rya.average_price_per_btc) OVER (PARTITION BY rya.region ORDER BY rya.year) IS NULL THEN NULL
    ELSE (rya.average_price_per_btc - LAG(rya.average_price_per_btc) OVER (PARTITION BY rya.region ORDER BY rya.year)) 
         / LAG(rya.average_price_per_btc) OVER (PARTITION BY rya.region ORDER BY rya.year)
  END AS pct_change_vs_prev_year
FROM region_year_average AS rya
WHERE rya.is_region_earliest_year = 0
```

---

## Skill `sales_filtered_periods`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `sale_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_e4208776b6f0954a |
| output columns | `sale_id`, `sale_date`, `period_label`, `sale_amount`, `region_id`, `platform_id`, `age_band_id`, `demographic_id`, `customer_type_id` |
| source tables | `cleaned_weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `sales_sum_by_attribute_value_and_period` |

### Description

Select sales rows restricted to the two 12-week periods (pre and post) around 2020-06-15, and label each row as 'pre' or 'post'. Keep the attribute value identifiers for each attribute type (region, platform, age_band, demographic, customer_type) and the sale amount.

### Semantic filters

```json
{
  "pre_period_inclusive": "sale_date between 2020-03-24 and 2020-06-14",
  "post_period_inclusive": "sale_date between 2020-06-15 and 2020-09-06",
  "period_label_values": "pre or post"
}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "subgoal",
    "subgoal": {
      "want_name": "sales_filtered_periods",
      "category": "SEL",
      "required_outputs": [
        "sale_id",
        "sale_date",
        "period_label",
        "sale_amount",
        "region_id",
        "platform_id",
        "age_band_id",
        "demographic_id",
        "customer_type_id"
      ],
      "required_grain": [
        "sale_id"
      ],
      "required_filters": {
        "pre_period_inclusive": "sale_date between 2020-03-24 and 2020-06-14",
        "post_period_inclusive": "sale_date between 2020-06-15 and 2020-09-06",
        "period_label_values": "pre or post"
      },
      "text": "Select sales rows restricted to the two 12-week periods (pre and post) around 2020-06-15, and label each row as 'pre' or 'post'. Keep the attribute value identifiers for each attribute type (region, platform, age_band, demographic, customer_type) and the sale amount.",
      "source_tables": [],
      "depends_on": [],
      "join_keys": [],
      "relationship": "independent",
      "may_read_base_tables": true,
      "holistic": false,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "cleaned_weekly_sales"
    ],
    "table_fingerprints": {
      "cleaned_weekly_sales": "c3607e774267b657"
    },
    "data_fingerprints": {
      "cleaned_weekly_sales": "17117:17117"
    },
    "db_id": "bank_sales_trading",
    "question_id": "local302",
    "question": "Analyze the average percentage change in sales between the 12 weeks before and after June 15, 2020, for each attribute type: region, platform, age band, demographic, and customer type. For each attribute type, calculate the average percentage change in sales across all its attribute values. Identify the attribute type with the highest negative impact on sales and provide its average percentage change in sales.",
    "rewrite": "Task: For each attribute type (region, platform, age band, demographic, customer type), compute the average percentage change in sales between the 12-week period immediately before June 15, 2020 and the 12-week period immediately after June 15, 2020; then identify which attribute type has the most negative (lowest) average percentage change and report that attribute type and its average percentage change.\nRequired outputs: attribute_type: one of {region, platform, age band, demographic, customer type}; average_pct_change: numeric value representing the average percentage change in sales across all attribute values for that attribute type (percent, can be negative)\nFilters: pre_period: all sales dated in the 12 weeks prior to June 15, 2020 (i.e., from 2020-03-24 inclusive through 2020-06-14 inclusive); post_period: all sales dated in the 12 weeks after June 15, 2020 (i.e., from 2020-06-15 inclusive through 2020-09-06 inclusive); aggregation_scope: for each attribute type, include all attribute values (e.g., all regions, all platforms, all age bands, all demographics, all customer types) present in the data; percentage_change_per_attribute_value: for each attribute value, compute ((post_period_sales - pre_period_sales) / pre_period_sales) * 100; if pre_period_sales = 0, exclude that attribute value from the average (do not divide by zero); average_calculation: for each attribute type, average the percentage_change_per_attribute_value across its attribute values (simple arithmetic mean)",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:27:25+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-09-30T15:27:28+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "sale_id",
      "sale_date",
      "period_label",
      "sale_amount",
      "region_id",
      "platform_id",
      "age_band_id",
      "demographic_id",
      "customer_type_id"
    ],
    "row_count": 5473,
    "grain_check": "pass",
    "filter_checks": {
      "pre_period_inclusive": "n/a",
      "post_period_inclusive": "n/a",
      "period_label_values": "n/a"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate sale_id (sale_id is unique per grain)",
        "sql": "SELECT COUNT(*) FROM (SELECT sale_id FROM sales_filtered_periods GROUP BY sale_id HAVING COUNT(*)>1) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows have sale_date inside one of the two allowed periods (intrinsic filter)",
        "sql": "SELECT COUNT(*) FROM sales_filtered_periods WHERE NOT (sale_date BETWEEN '2020-03-24' AND '2020-06-14' OR sale_date BETWEEN '2020-06-15' AND '2020-09-06')",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "period_label only contains allowed values 'pre' or 'post' and matches the sale_date",
        "sql": "SELECT COUNT(*) FROM sales_filtered_periods WHERE NOT ((period_label = 'pre' AND sale_date BETWEEN '2020-03-24' AND '2020-06-14') OR (period_label = 'post' AND sale_date BETWEEN '2020-06-15' AND '2020-09-06'))",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  ROW_NUMBER() OVER (ORDER BY week_date, region, platform, segment, customer_type, age_band, demographic, transactions) AS sale_id,
  week_date AS sale_date,
  CASE
    WHEN week_date BETWEEN '2020-03-24' AND '2020-06-14' THEN 'pre'
    WHEN week_date BETWEEN '2020-06-15' AND '2020-09-06' THEN 'post'
  END AS period_label,
  sales AS sale_amount,
  region AS region_id,
  platform AS platform_id,
  age_band AS age_band_id,
  demographic AS demographic_id,
  customer_type AS customer_type_id
FROM cleaned_weekly_sales
WHERE (week_date BETWEEN '2020-03-24' AND '2020-06-14')
   OR (week_date BETWEEN '2020-06-15' AND '2020-09-06')
```

---

## Skill `sales_sum_by_attribute_value_and_period`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `attribute_type`, `attribute_value_id`, `period_label` (keyed) |
| status / version | active / v1 |
| skill id | sk_b1344af45f6e14a7 |
| output columns | `attribute_type`, `attribute_value_id`, `period_label`, `period_sales` |
| source tables | — |
| depends_on (builds on) | `sales_filtered_periods` |
| depended-on by (builds on this) | — |

### Description

Aggregate sales_sum for each attribute value and period. Produce one row per attribute_type x attribute_value x period with the total sales amount in that period. This relation is produced separately for each attribute dimension but in a unified relation using columns for each attribute value id.

### Semantic filters

```json
{
  "pre_period_inclusive": "sale_date between 2020-03-24 and 2020-06-14",
  "post_period_inclusive": "sale_date between 2020-06-15 and 2020-09-06",
  "period_label_values": "pre or post"
}
```

### Learned skill parameters

```json
{}
```

### Provenance, validation, evidence

```json
{
  "provenance": {
    "origin": "subgoal",
    "subgoal": {
      "want_name": "sales_sum_by_attribute_value_and_period",
      "category": "AGG",
      "required_outputs": [
        "attribute_type",
        "attribute_value_id",
        "period_label",
        "period_sales"
      ],
      "required_grain": [
        "attribute_type",
        "attribute_value_id",
        "period_label"
      ],
      "required_filters": {},
      "text": "Aggregate sales_sum for each attribute value and period. Produce one row per attribute_type x attribute_value x period with the total sales amount in that period. This relation is produced separately for each attribute dimension but in a unified relation using columns for each attribute value id.",
      "source_tables": [],
      "depends_on": [
        "sales_filtered_periods"
      ],
      "join_keys": [],
      "relationship": "aggregate_input",
      "may_read_base_tables": false,
      "holistic": false,
      "inherited_filters": {
        "pre_period_inclusive": "sale_date between 2020-03-24 and 2020-06-14",
        "post_period_inclusive": "sale_date between 2020-06-15 and 2020-09-06",
        "period_label_values": "pre or post"
      }
    },
    "inherited_filters": {
      "pre_period_inclusive": "sale_date between 2020-03-24 and 2020-06-14",
      "post_period_inclusive": "sale_date between 2020-06-15 and 2020-09-06",
      "period_label_values": "pre or post"
    },
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "cleaned_weekly_sales"
    ],
    "table_fingerprints": {
      "cleaned_weekly_sales": "c3607e774267b657"
    },
    "data_fingerprints": {},
    "db_id": "bank_sales_trading",
    "question_id": "local302",
    "question": "Analyze the average percentage change in sales between the 12 weeks before and after June 15, 2020, for each attribute type: region, platform, age band, demographic, and customer type. For each attribute type, calculate the average percentage change in sales across all its attribute values. Identify the attribute type with the highest negative impact on sales and provide its average percentage change in sales.",
    "rewrite": "Task: For each attribute type (region, platform, age band, demographic, customer type), compute the average percentage change in sales between the 12-week period immediately before June 15, 2020 and the 12-week period immediately after June 15, 2020; then identify which attribute type has the most negative (lowest) average percentage change and report that attribute type and its average percentage change.\nRequired outputs: attribute_type: one of {region, platform, age band, demographic, customer type}; average_pct_change: numeric value representing the average percentage change in sales across all attribute values for that attribute type (percent, can be negative)\nFilters: pre_period: all sales dated in the 12 weeks prior to June 15, 2020 (i.e., from 2020-03-24 inclusive through 2020-06-14 inclusive); post_period: all sales dated in the 12 weeks after June 15, 2020 (i.e., from 2020-06-15 inclusive through 2020-09-06 inclusive); aggregation_scope: for each attribute type, include all attribute values (e.g., all regions, all platforms, all age bands, all demographics, all customer types) present in the data; percentage_change_per_attribute_value: for each attribute value, compute ((post_period_sales - pre_period_sales) / pre_period_sales) * 100; if pre_period_sales = 0, exclude that attribute value from the average (do not divide by zero); average_calculation: for each attribute type, average the percentage_change_per_attribute_value across its attribute values (simple arithmetic mean)",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:27:28+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-09-30T15:27:32+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "attribute_type",
      "attribute_value_id",
      "period_label",
      "period_sales"
    ],
    "row_count": 38,
    "grain_check": "pass",
    "filter_checks": {
      "pre_period_inclusive": "n/a",
      "post_period_inclusive": "n/a",
      "period_label_values": "n/a"
    },
    "join_cardinality": [
      {
        "join": "attribute_value.attribute_type=attribute_type.attribute_type",
        "left_unique": null,
        "right_unique": null,
        "relationship": "unknown"
      }
    ],
    "tests": [
      {
        "purpose": "View has one row per attribute_type x attribute_value_id x period_label (no duplicates)",
        "sql": "SELECT COUNT(*) FROM (SELECT attribute_type, attribute_value_id, period_label, COUNT(*) AS c FROM sales_sum_by_attribute_value_and_period GROUP BY attribute_type, attribute_value_id, period_label HAVING c > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "period_label only contains allowed values 'pre' or 'post' (intrinsic filter on period labels)",
        "sql": "SELECT COUNT(*) FROM sales_sum_by_attribute_value_and_period WHERE period_label NOT IN ('pre','post') OR period_label IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "period_sales equals sum of sale amounts from base table sales_filtered_periods for matching attribute and period (measure reconciliation)",
        "sql": "SELECT COUNT(*) FROM sales_sum_by_attribute_value_and_period v WHERE (SELECT IFNULL(SUM(s.sale_amount),0) FROM sales_filtered_periods s WHERE ((v.attribute_type='region' AND s.region_id=v.attribute_value_id) OR (v.attribute_type='platform' AND s.platform_id=v.attribute_value_id) OR (v.attribute_type='age_band' AND s.age_band_id=v.attribute_value_id) OR (v.attribute_type='demographic' AND s.demographic_id=v.attribute_value_id) OR (v.attribute_type='customer_type' AND s.customer_type_id=v.attribute_value_id)) AND ((v.period_label='pre' AND s.sale_date BETWEEN '2020-03-24' AND '2020-06-14') OR (v.period_label='post' AND s.sale_date BETWEEN '2020-06-15' AND '2020-09-06'))) != IFNULL(v.period_sales,0)",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {}
}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  attribute_type.attribute_type,
  attribute_value.attribute_value_id,
  s.period_label,
  SUM(s.sale_amount) AS period_sales
FROM
  sales_filtered_periods s
CROSS JOIN (
  SELECT 'region' AS attribute_type
  UNION ALL SELECT 'platform'
  UNION ALL SELECT 'age_band'
  UNION ALL SELECT 'demographic'
  UNION ALL SELECT 'customer_type'
) attribute_type
LEFT JOIN (
  -- unify attribute values with consistent column name attribute_value_id
  SELECT region_id   AS attribute_value_id, 'region'     AS attribute_type FROM sales_filtered_periods
  UNION
  SELECT platform_id AS attribute_value_id, 'platform'   AS attribute_type FROM sales_filtered_periods
  UNION
  SELECT age_band_id AS attribute_value_id, 'age_band'   AS attribute_type FROM sales_filtered_periods
  UNION
  SELECT demographic_id AS attribute_value_id, 'demographic' AS attribute_type FROM sales_filtered_periods
  UNION
  SELECT customer_type_id AS attribute_value_id, 'customer_type' AS attribute_type FROM sales_filtered_periods
) attribute_value
  ON attribute_value.attribute_type = attribute_type.attribute_type
WHERE
  -- join s to attribute_value rows so that for each row in s we pick the matching attribute_value entry
  (
    (attribute_type.attribute_type = 'region'       AND attribute_value.attribute_value_id = s.region_id)
    OR (attribute_type.attribute_type = 'platform'   AND attribute_value.attribute_value_id = s.platform_id)
    OR (attribute_type.attribute_type = 'age_band'   AND attribute_value.attribute_value_id = s.age_band_id)
    OR (attribute_type.attribute_type = 'demographic'AND attribute_value.attribute_value_id = s.demographic_id)
    OR (attribute_type.attribute_type = 'customer_type' AND attribute_value.attribute_value_id = s.customer_type_id)
  )
GROUP BY
  attribute_type.attribute_type,
  attribute_value.attribute_value_id,
  s.period_label
```

---
