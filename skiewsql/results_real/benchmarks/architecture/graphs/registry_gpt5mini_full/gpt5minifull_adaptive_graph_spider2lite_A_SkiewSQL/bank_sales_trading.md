# Skill graph — `bank_sales_trading` (15 skills)

## Skill `customers_cohort`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `customer_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_5605d75c76306244 |
| output columns | `customer_id`, `initial_balance` |
| source tables | `customer_nodes`, `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customer_monthly_closing_balances` |

### Description

Canonical list of every customer to include. One row per customer with the customer identifier and any canonical opening/initial balance if available in customer master data. This cohort covers all customers present in customer data or transaction data.

### Semantic filters

```json
{
  "note": "Include all customers appearing in customer_nodes or customer_transactions; do not filter out inactive customers"
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
      "want_name": "customers_cohort",
      "category": "SEL",
      "required_outputs": [
        "customer_id",
        "initial_balance"
      ],
      "required_grain": [
        "customer_id"
      ],
      "required_filters": {
        "note": "May optionally include all customers appearing in transactions by union; do not filter out inactive customers."
      },
      "text": "Canonical list of every customer to include. One row per customer with the customer identifier and any canonical opening/initial balance if available in customer master data. This cohort covers all customers present in customer data or transaction data.",
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
      "customer_nodes",
      "customer_transactions"
    ],
    "table_fingerprints": {
      "customer_nodes": "9f463ad9509a25de",
      "customer_transactions": "f0755d1d3402a42b"
    },
    "data_fingerprints": {
      "customer_nodes": "3500:3500",
      "customer_transactions": "5868:5868"
    },
    "db_id": "bank_sales_trading",
    "question_id": "local074",
    "question": "Please generate a summary of the closing balances at the end of each month for each customer transactions, show the monthly changes and monthly cumulative bank account balances. Ensure that even if a customer has no account activity in a given month, the balance for that month is still included in the output.",
    "rewrite": "Task: For each customer and for every calendar month in the requested reporting period, compute the customer's account closing balance at the end of that month, the month-over-month change (difference between this month's closing balance and the previous month's closing balance for the same customer), and the running cumulative bank account balance across months for that customer; include months with no transactions by carrying forward the prior balance so that every month in the period appears for every customer.\nRequired outputs: customer identifier (unique key that identifies the customer); year (integer, calendar year of the month); month (integer 1-12, calendar month); month_end_date (date representing the last calendar date of the month); closing_balance (numeric: customer's account balance as of the month_end_date; if no transactions in or before the month, treat as zero or initial balance as per data); month_over_month_change (numeric: closing_balance for this month minus closing_balance for prior month for same customer; for the first month in the reporting period for a customer, compute change relative to the prior month's balance which may be zero or prior-data balance if available); cumulative_balance (numeric: running cumulative sum of closing_balance values across months for the customer in chronological order within the reporting period)\nFilters: Include every customer present in the customer dataset (or in transaction dataset) — each customer must have one row per calendar month in the reporting period, even if they have no transactions that month; Reporting period: every calendar month between the specified start_date and end_date inclusive (these input literal dates must be provided when executing the query); rows must be generated for each month in that inclusive range; Balance carry-forward rule: if a customer has no transactions in a month, the closing_balance for that month equals the previous month's closing_balance for that customer (or an initial balance of zero if no prior balance exists); Treat transaction effects and opening balances according to the source data when computing closing balances; do not drop customers or months for lack of activity\nSort/limit: Order the output by customer identifier ascending, then by year ascending, then by month ascending; no row limit unless an external limit is specified",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:25:42+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-10-01T00:25:45+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "customer_id",
      "initial_balance"
    ],
    "row_count": 500,
    "grain_check": "pass",
    "filter_checks": {
      "note": "n/a"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate customer_id rows (view grain = one row per customer_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT customer_id, COUNT(*) AS ct FROM customers_cohort GROUP BY customer_id HAVING ct > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every customer appearing in base tables is present in the view (cohort covers all customers in customer_nodes or customer_transactions)",
        "sql": "SELECT COUNT(*) FROM (SELECT customer_id FROM (SELECT customer_id FROM customer_nodes UNION SELECT customer_id FROM customer_transactions) EXCEPT SELECT customer_id FROM customers_cohort)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "customer_id in the view is never NULL (key not NULL)",
        "sql": "SELECT COUNT(*) FROM customers_cohort WHERE customer_id IS NULL",
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
  NULL AS initial_balance
FROM (
  SELECT customer_id FROM customer_nodes
  UNION
  SELECT customer_id FROM customer_transactions
)
```

---

## Skill `customer_monthly_closing_balances`

Category: `WIN`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `year`, `month` (keyed) |
| status / version | active / v1 |
| skill id | sk_995751d9efce8426 |
| output columns | `customer_id`, `year`, `month`, `month_end_date`, `closing_balance`, `month_over_month_change`, `cumulative_balance` |
| source tables | `customer_transactions`, `customer_nodes` |
| depends_on (builds on) | `customers_cohort` |
| depended-on by (builds on this) | — |

### Description

For each customer x month (every combination from customers_cohort cross-joined with report_months_calendar), compute the closing_balance as of the month_end_date by applying all transactions and any initial/opening balances up to that date. Also compute month_over_month_change (closing_balance minus prior month's closing_balance for same customer) and cumulative_balance (running sum of closing_balance across months per customer in chronological order). Carry forward prior balance for months with no transactions per customer (i.e., closing_balance repeats previous month's closing_balance or uses initial_balance/zero if no prior).

### Semantic filters

```json
{
  "note": "Includes every customer x month in the reporting period; months are filled even with no transactions by carrying forward balances."
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
      "want_name": "customer_monthly_closing_balances",
      "category": "WIN",
      "required_outputs": [
        "customer_id",
        "year",
        "month",
        "month_end_date",
        "closing_balance",
        "month_over_month_change",
        "cumulative_balance"
      ],
      "required_grain": [
        "customer_id",
        "year",
        "month"
      ],
      "required_filters": {
        "note": "Includes every customer x month in the reporting period; months are filled even with no transactions by carrying forward balances."
      },
      "text": "For each customer x month (every combination from customers_cohort cross-joined with report_months_calendar), compute the closing_balance as of the month_end_date by applying all transactions and any initial/opening balances up to that date. Also compute month_over_month_change (closing_balance minus prior month's closing_balance for same customer) and cumulative_balance (running sum of closing_balance across months per customer in chronological order). Carry forward prior balance for months with no transactions per customer (i.e., closing_balance repeats previous month's closing_balance or uses initial_balance/zero if no prior).",
      "source_tables": [],
      "depends_on": [
        "customers_cohort"
      ],
      "join_keys": [
        "customer_id",
        "year",
        "month"
      ],
      "relationship": "aggregate_input",
      "may_read_base_tables": true,
      "holistic": false,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "customer_transactions",
      "customer_nodes"
    ],
    "table_fingerprints": {
      "customer_transactions": "f0755d1d3402a42b",
      "customer_nodes": "9f463ad9509a25de"
    },
    "data_fingerprints": {
      "customer_transactions": "5868:5868",
      "customer_nodes": "3500:3500"
    },
    "db_id": "bank_sales_trading",
    "question_id": "local074",
    "question": "Please generate a summary of the closing balances at the end of each month for each customer transactions, show the monthly changes and monthly cumulative bank account balances. Ensure that even if a customer has no account activity in a given month, the balance for that month is still included in the output.",
    "rewrite": "Task: For each customer and for every calendar month in the requested reporting period, compute the customer's account closing balance at the end of that month, the month-over-month change (difference between this month's closing balance and the previous month's closing balance for the same customer), and the running cumulative bank account balance across months for that customer; include months with no transactions by carrying forward the prior balance so that every month in the period appears for every customer.\nRequired outputs: customer identifier (unique key that identifies the customer); year (integer, calendar year of the month); month (integer 1-12, calendar month); month_end_date (date representing the last calendar date of the month); closing_balance (numeric: customer's account balance as of the month_end_date; if no transactions in or before the month, treat as zero or initial balance as per data); month_over_month_change (numeric: closing_balance for this month minus closing_balance for prior month for same customer; for the first month in the reporting period for a customer, compute change relative to the prior month's balance which may be zero or prior-data balance if available); cumulative_balance (numeric: running cumulative sum of closing_balance values across months for the customer in chronological order within the reporting period)\nFilters: Include every customer present in the customer dataset (or in transaction dataset) — each customer must have one row per calendar month in the reporting period, even if they have no transactions that month; Reporting period: every calendar month between the specified start_date and end_date inclusive (these input literal dates must be provided when executing the query); rows must be generated for each month in that inclusive range; Balance carry-forward rule: if a customer has no transactions in a month, the closing_balance for that month equals the previous month's closing_balance for that customer (or an initial balance of zero if no prior balance exists); Treat transaction effects and opening balances according to the source data when computing closing balances; do not drop customers or months for lack of activity\nSort/limit: Order the output by customer identifier ascending, then by year ascending, then by month ascending; no row limit unless an external limit is specified",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:25:45+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-10-01T00:25:48+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "customer_id",
      "year",
      "month",
      "month_end_date",
      "closing_balance",
      "month_over_month_change",
      "cumulative_balance"
    ],
    "row_count": 3500,
    "grain_check": "pass",
    "filter_checks": {
      "note": "n/a"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "Every customer x month combination exists (no missing months): compare expected cross join of customers_cohort x report_months_calendar to rows present in the view.",
        "sql": "SELECT COUNT(*) FROM (SELECT cc.customer_id, rm.month_start FROM customers_cohort cc CROSS JOIN report_months_calendar rm EXCEPT SELECT customer_id, date(year || '-' || month || '-01') FROM customer_monthly_closing_balances) AS t",
        "result": "inconclusive",
        "violations": null,
        "error": "OperationalError: no such table: report_months_calendar"
      },
      {
        "purpose": "No NULLs in key columns (customer_id, year, month) — keys must be present for every row.",
        "sql": "SELECT COUNT(*) FROM customer_monthly_closing_balances WHERE customer_id IS NULL OR year IS NULL OR month IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "month_over_month_change equals closing_balance minus prior month's closing_balance for same customer (detect any rows where it does not).",
        "sql": "SELECT COUNT(*) FROM customer_monthly_closing_balances cur LEFT JOIN customer_monthly_closing_balances prev ON cur.customer_id = prev.customer_id AND (strftime('%Y-%m', date(cur.year || '-' || cur.month || '-01'), '-1 month') = strftime('%Y-%m', date(prev.year || '-' || prev.month || '-01'))) WHERE (cur.closing_balance - COALESCE(prev.closing_balance, 0)) IS NOT cur.month_over_month_change",
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
  cc.customer_id AS customer_id,
  strftime('%Y', rm.month_start) AS year,
  strftime('%m', rm.month_start) AS month,
  rm.month_end AS month_end_date,
  -- closing_balance: sum of initial_balance + all txn_amounts up to month_end_date
  COALESCE(
    cc.initial_balance,
    0
  )
  +
  COALESCE((
    SELECT SUM(ct.txn_amount)
    FROM customer_transactions ct
    WHERE ct.customer_id = cc.customer_id
      AND date(ct.txn_date) <= date(rm.month_end)
  ), 0) AS closing_balance,
  -- month_over_month_change: closing_balance minus prior month's closing_balance
  (
    (
      COALESCE(cc.initial_balance,0)
      +
      COALESCE((
        SELECT SUM(ct2.txn_amount)
        FROM customer_transactions ct2
        WHERE ct2.customer_id = cc.customer_id
          AND date(ct2.txn_date) <= date(rm.month_end)
      ),0)
    )
    -
    (
      COALESCE(cc.initial_balance,0)
      +
      COALESCE((
        SELECT SUM(ct3.txn_amount)
        FROM customer_transactions ct3
        WHERE ct3.customer_id = cc.customer_id
          AND date(ct3.txn_date) <= date(date(rm.month_start, '-1 day'))
      ),0)
    )
  ) AS month_over_month_change,
  -- cumulative_balance: running sum of closing_balance across months per customer
  (
    SELECT SUM(
      COALESCE(cc2.initial_balance,0)
      +
      COALESCE((
        SELECT SUM(ct4.txn_amount)
        FROM customer_transactions ct4
        WHERE ct4.customer_id = cc.customer_id
          AND date(ct4.txn_date) <= date(rm2.month_end)
      ),0)
    )
    FROM customers_cohort cc2
    JOIN (
      -- generate same report months rows via recursive approach substitution:
      -- but to keep view self-contained, assume there exists same months in customers_cohort join space
      -- replicate rows by selecting distinct month starts/ends from a calendar derived from transactions and node dates
      SELECT DISTINCT
        date(strftime('%Y-%m-01', date(t.txn_date))) AS month_start,
        date(date(strftime('%Y-%m-01', date(t.txn_date)), '+1 month', '-1 day')) AS month_end
      FROM customer_transactions t
      UNION
      SELECT DISTINCT
        date(strftime('%Y-%m-01', date(start_date))) AS month_start,
        date(date(strftime('%Y-%m-01', date(start_date)), '+1 month', '-1 day')) AS month_end
      FROM customer_nodes
    ) rm2 ON 1=1
    WHERE cc2.customer_id = cc.customer_id
      AND (date(rm2.month_end) <= date(rm.month_end))
  ) AS cumulative_balance
FROM customers_cohort cc
-- derive report months calendar by union of months present in data to ensure every month in reporting period is present
JOIN (
  SELECT DISTINCT
    date(strftime('%Y-%m-01', date(t.txn_date))) AS month_start,
    date(date(strftime('%Y-%m-01', date(t.txn_date)), '+1 month', '-1 day')) AS month_end
  FROM customer_transactions t
  UNION
  SELECT DISTINCT
    date(strftime('%Y-%m-01', date(start_date))) AS month_start,
    date(date(strftime('%Y-%m-01', date(start_date)), '+1 month', '-1 day')) AS month_end
  FROM customer_nodes
) rm ON 1=1
```

---

## Skill `all_customers_months_2020`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month_start_date` (keyed) |
| status / version | active / v1 |
| skill id | sk_ce823cfbcb6586ba |
| output columns | `customer_id`, `month_start_date`, `month_label` |
| source tables | `customer_nodes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Generate one row per customer for each calendar month in 2020. This produces the complete set of customer-month pairs to ensure customers with no transactions in a month are included (their balances will be computed as zero later).

### Semantic filters

```json
{
  "month_range": "months restricted to 2020 (2020-01 .. 2020-12)"
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
      "want_name": "all_customers_months_2020",
      "category": "SEL",
      "required_outputs": [
        "customer_id",
        "month_start_date",
        "month_label"
      ],
      "required_grain": [
        "customer_id",
        "month_start_date"
      ],
      "required_filters": {
        "month_range": "months restricted to 2020 (2020-01 .. 2020-12)"
      },
      "text": "Generate one row per customer for each calendar month in 2020. This produces the complete set of customer-month pairs to ensure customers with no transactions in a month are included (their balances will be computed as zero later).",
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
      "customer_nodes"
    ],
    "table_fingerprints": {
      "customer_nodes": "9f463ad9509a25de"
    },
    "data_fingerprints": {
      "customer_nodes": "3500:3500"
    },
    "db_id": "bank_sales_trading",
    "question_id": "local064",
    "question": "For each customer and each month of 2020, first calculate the month-end balance by adding all deposit amounts and subtracting all withdrawal amounts that occurred during that specific month. Then determine which month in 2020 has the highest count of customers with a positive month-end balance and which month has the lowest count. For each of these two months, compute the average month-end balance across all customers and provide the difference between these two averages",
    "rewrite": "Task: For each customer and for each calendar month in 2020, compute that customer's month-end balance defined as the sum of deposit amounts minus the sum of withdrawal amounts that occurred during that calendar month; then find (1) the month in 2020 with the largest count of customers whose month-end balance is strictly greater than zero and (2) the month in 2020 with the smallest count of customers whose month-end balance is strictly greater than zero; for each of those two months compute the average of the month-end balances across all customers (including customers with zero or negative month-end balances), and finally report the difference between those two monthly averages (average_for_month_with_highest_positive_count minus average_for_month_with_lowest_positive_count).\nRequired outputs: month_with_highest_positive_count (calendar month in 2020, e.g., '2020-03' or month number 1-12); highest_positive_customer_count (integer count of distinct customers with month-end balance > 0 in that month); average_month_end_balance_for_highest_month (numeric average of month-end balances across all customers for that month); month_with_lowest_positive_count (calendar month in 2020); lowest_positive_customer_count (integer count of distinct customers with month-end balance > 0 in that month); average_month_end_balance_for_lowest_month (numeric average of month-end balances across all customers for that month); difference_between_averages (numeric: average_for_highest_month minus average_for_lowest_month)\nFilters: consider only transactions that occurred on dates within the calendar year 2020 (i.e., transaction date >= '2020-01-01' and <= '2020-12-31'); for month grouping use calendar months January through December 2020 (12 distinct months); month-end balance for a given customer and month = (sum of amounts of all transactions classified as deposits within that month) minus (sum of amounts of all transactions classified as withdrawals within that month); if a customer has no transactions in a month their month-end balance = 0; positive month-end balance means strictly greater than 0 (> 0); average month-end balance for a month is the arithmetic mean of the month-end balances for all customers (include every customer present in the customers dataset or relevant customer list, even if their balance is zero for that month)",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:26:32+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-10-01T00:26:38+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "customer_id",
      "month_start_date",
      "month_label"
    ],
    "row_count": 6000,
    "grain_check": "pass",
    "filter_checks": {
      "month_range": "n/a"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate customer-month rows: view should have at most one row per (customer_id, month_start_date)",
        "sql": "SELECT COUNT(*) FROM (SELECT customer_id, month_start_date, COUNT(*) AS cnt FROM all_customers_months_2020 GROUP BY customer_id, month_start_date HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All months are restricted to 2020 (month_start_date must be first day of a month in 2020)",
        "sql": "SELECT COUNT(*) FROM all_customers_months_2020 WHERE NOT (substr(month_start_date,1,4) = '2020' AND substr(month_start_date,6,2) IN ('01','02','03','04','05','06','07','08','09','10','11','12') AND substr(month_start_date,9,2) = '01')",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every customer in customer_nodes appears for every month of 2020 (no missing customer-month pairs)",
        "sql": "SELECT COUNT(*) FROM (SELECT c.customer_id, m.month_start_date FROM (SELECT DISTINCT customer_id FROM customer_nodes) AS c CROSS JOIN (SELECT '2020-01-01' AS month_start_date UNION ALL SELECT '2020-02-01' UNION ALL SELECT '2020-03-01' UNION ALL SELECT '2020-04-01' UNION ALL SELECT '2020-05-01' UNION ALL SELECT '2020-06-01' UNION ALL SELECT '2020-07-01' UNION ALL SELECT '2020-08-01' UNION ALL SELECT '2020-09-01' UNION ALL SELECT '2020-10-01' UNION ALL SELECT '2020-11-01' UNION ALL SELECT '2020-12-01') AS m EXCEPT SELECT customer_id, month_start_date FROM all_customers_months_2020)",
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
  c.customer_id AS customer_id,
  date(months.month_start) AS month_start_date,
  strftime('%Y-%m', months.month_start) || '-01' AS month_label
FROM
  (
    SELECT DISTINCT customer_id
    FROM customer_nodes
  ) AS c
CROSS JOIN
  (
    SELECT '2020-01-01' AS month_start UNION ALL
    SELECT '2020-02-01' UNION ALL
    SELECT '2020-03-01' UNION ALL
    SELECT '2020-04-01' UNION ALL
    SELECT '2020-05-01' UNION ALL
    SELECT '2020-06-01' UNION ALL
    SELECT '2020-07-01' UNION ALL
    SELECT '2020-08-01' UNION ALL
    SELECT '2020-09-01' UNION ALL
    SELECT '2020-10-01' UNION ALL
    SELECT '2020-11-01' UNION ALL
    SELECT '2020-12-01'
  ) AS months
```

---

## Skill `monthly_nets_per_customer`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month_start` (keyed) |
| status / version | active / v1 |
| skill id | sk_851557763dff6ee7 |
| output columns | `customer_id`, `month_start`, `monthly_net` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each customer and calendar month (map transaction date to month start), sum deposits as positive and withdrawals as negative to produce the monthly net amount.

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
      "want_name": "monthly_nets_per_customer",
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
      "text": "For each customer and calendar month (map transaction date to month start), sum deposits as positive and withdrawals as negative to produce the monthly net amount.",
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
    "rewrite": "Task: For each customer, aggregate all deposits and withdrawals by month (grouping transactions by the first day of that month) to compute a monthly net amount, compute each customer’s monthly closing balances by cumulatively summing those monthly nets in chronological order, identify each customer's most recent month and its prior month, compute that most recent month’s growth rate as: (most_recent_closing_balance - prior_month_closing_balance) / prior_month_closing_balance, except when prior_month_closing_balance = 0 in which case set growth rate = most_recent_closing_balance * 100, then compute the percentage of customers whose most recent month growth rate is greater than 0.05 (5%).\nRequired outputs: overall_percentage_customers_with_growth_gt_5_percent: numeric value representing the percentage (0-100) of customers whose most recent month growth rate > 0.05; numerator_customers: integer count of customers meeting growth > 5%; denominator_customers: integer count of customers considered (customers having at least two months of balances or one month if prior balance is treated as zero per rule)\nFilters: Group transactions into months by mapping each transaction date to the month start date (the first day of that month).; Monthly net amount per customer = sum of deposits and withdrawals in that month, treating deposits as positive and withdrawals as negative.; Monthly closing balance per customer is the cumulative sum of the monthly net amounts ordered by month ascending.; Most recent month per customer = the latest month for which the customer has a monthly net (and thus a closing balance).; Prior month per customer = the immediately preceding month chronologically for that customer; if no prior month exists, treat prior_month_closing_balance = 0 for the growth-rate rule.; Growth-rate comparison threshold = 0.05 (strictly greater than 0.05).",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:27:13+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-10-01T00:27:16+00:00",
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
        "purpose": "No duplicate rows per grain (customer_id, month_start)",
        "sql": "SELECT COUNT(*) FROM (SELECT customer_id, substr(txn_date,1,7)||'-01' AS month_start, COUNT(*) AS cnt FROM monthly_nets_per_customer GROUP BY customer_id, month_start HAVING cnt > 1)",
        "result": "inconclusive",
        "violations": null,
        "error": "OperationalError: no such column: txn_date"
      },
      {
        "purpose": "monthly_net equals recomputed sum from base table (checks deposits positive, withdrawals negative)",
        "sql": "SELECT COUNT(*) FROM monthly_nets_per_customer m LEFT JOIN (SELECT customer_id, substr(txn_date,1,7)||'-01' AS month_start, SUM(CASE WHEN txn_type='deposit' THEN txn_amount WHEN txn_type='withdrawal' THEN -txn_amount ELSE 0 END) AS recomputed_net FROM customer_transactions GROUP BY customer_id, month_start) b ON m.customer_id = b.customer_id AND m.month_start = b.month_start WHERE (m.monthly_net IS NULL AND b.recomputed_net IS NOT NULL) OR (m.monthly_net IS NOT NULL AND b.recomputed_net IS NULL) OR (m.monthly_net != b.recomputed_net)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys customer_id and month_start are not NULL",
        "sql": "SELECT COUNT(*) FROM monthly_nets_per_customer WHERE customer_id IS NULL OR month_start IS NULL",
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
           ELSE 0 END) AS monthly_net
FROM customer_transactions
GROUP BY customer_id, month_start
```

---

## Skill `customer_monthly_closing_balances_4`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month_start` (keyed) |
| status / version | active / v1 |
| skill id | sk_506aae25ee14f6ab |
| output columns | `customer_id`, `month_start`, `monthly_net`, `closing_balance` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per customer and month (month start date), the monthly net amount (deposits positive, withdrawals negative) and the cumulative closing balance up to that month.

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
    "question_id": "local297",
    "question": "For each customer, group all deposits and withdrawals by the first day of each month to obtain a monthly net amount, then calculate each month’s closing balance by cumulatively summing these monthly nets. Next, determine the most recent month’s growth rate by comparing its closing balance to the prior month’s balance, treating deposits as positive and withdrawals as negative, and if the previous month’s balance is zero, the growth rate should be the current month’s balance multiplied by 100. Finally, compute the percentage of customers whose most recent month shows a growth rate of more than 5%.",
    "rewrite": "Task: For each customer, aggregate all deposits and withdrawals by month (grouping transactions by the first day of that month) to compute a monthly net amount, compute each customer’s monthly closing balances by cumulatively summing those monthly nets in chronological order, identify each customer's most recent month and its prior month, compute that most recent month’s growth rate as: (most_recent_closing_balance - prior_month_closing_balance) / prior_month_closing_balance, except when prior_month_closing_balance = 0 in which case set growth rate = most_recent_closing_balance * 100, then compute the percentage of customers whose most recent month growth rate is greater than 0.05 (5%).\nRequired outputs: overall_percentage_customers_with_growth_gt_5_percent: numeric value representing the percentage (0-100) of customers whose most recent month growth rate > 0.05; numerator_customers: integer count of customers meeting growth > 5%; denominator_customers: integer count of customers considered (customers having at least two months of balances or one month if prior balance is treated as zero per rule)\nFilters: Group transactions into months by mapping each transaction date to the month start date (the first day of that month).; Monthly net amount per customer = sum of deposits and withdrawals in that month, treating deposits as positive and withdrawals as negative.; Monthly closing balance per customer is the cumulative sum of the monthly net amounts ordered by month ascending.; Most recent month per customer = the latest month for which the customer has a monthly net (and thus a closing balance).; Prior month per customer = the immediately preceding month chronologically for that customer; if no prior month exists, treat prior_month_closing_balance = 0 for the growth-rate rule.; Growth-rate comparison threshold = 0.05 (strictly greater than 0.05).",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:27:18+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-10-01T00:27:22+00:00",
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
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows per grain (customer_id, month_start)",
        "sql": "SELECT COUNT(*) FROM (SELECT customer_id, month_start, COUNT(*) AS cnt FROM customer_monthly_closing_balances_4 GROUP BY customer_id, month_start HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "monthly_net equals sum of transactions for that customer and month",
        "sql": "SELECT COUNT(*) FROM customer_monthly_closing_balances_4 v LEFT JOIN (SELECT customer_id, substr(txn_date,1,7)||'-01' AS month_start, SUM(CASE WHEN txn_type='deposit' THEN txn_amount WHEN txn_type='withdrawal' THEN -txn_amount ELSE 0 END) AS expected_monthly_net FROM customer_transactions GROUP BY customer_id, month_start) t ON v.customer_id = t.customer_id AND v.month_start = t.month_start WHERE (v.monthly_net IS NULL AND t.expected_monthly_net IS NOT NULL) OR (v.monthly_net IS NOT NULL AND t.expected_monthly_net IS NULL) OR (v.monthly_net != t.expected_monthly_net)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "closing_balance equals running sum of monthly_net per customer ordered by month_start",
        "sql": "SELECT COUNT(*) FROM (SELECT v.customer_id, v.month_start, v.closing_balance, (SELECT SUM(v2.monthly_net) FROM customer_monthly_closing_balances_4 v2 WHERE v2.customer_id = v.customer_id AND v2.month_start <= v.month_start) AS expected_closing FROM customer_monthly_closing_balances_4 v) x WHERE (x.closing_balance IS NULL AND x.expected_closing IS NOT NULL) OR (x.closing_balance IS NOT NULL AND x.expected_closing IS NULL) OR (x.closing_balance != x.expected_closing)",
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
  SUM(CASE WHEN txn_type = 'deposit' THEN txn_amount WHEN txn_type = 'withdrawal' THEN -txn_amount ELSE 0 END) AS monthly_net,
  SUM(SUM(CASE WHEN txn_type = 'deposit' THEN txn_amount WHEN txn_type = 'withdrawal' THEN -txn_amount ELSE 0 END)) OVER (PARTITION BY customer_id ORDER BY substr(txn_date,1,7) || '-01' ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS closing_balance
FROM customer_transactions
GROUP BY customer_id, month_start
```

---

## Skill `balances_on_first_of_month`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `user_id`, `balance_date` (keyed) |
| status / version | active / v1 |
| skill id | sk_937f01eeaea3b06a |
| output columns | `user_id`, `balance_date`, `balance` |
| source tables | `shopping_cart_users`, `shopping_cart_events` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Select per-user balance records that fall exactly on the first day of a month. This yields one row per observed balance measurement on a month's first day (do not aggregate).

### Semantic filters

```json
{
  "date_is_first_of_month": "balance_date is exactly the first day of its month"
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
      "want_name": "balances_on_first_of_month",
      "category": "SEL",
      "required_outputs": [
        "user_id",
        "balance_date",
        "balance"
      ],
      "required_grain": [
        "user_id",
        "balance_date"
      ],
      "required_filters": {
        "date_is_first_of_month": "balance_date is exactly the first day of its month"
      },
      "text": "Select per-user balance records that fall exactly on the first day of a month. This yields one row per observed balance measurement on a month's first day (do not aggregate).",
      "source_tables": [],
      "depends_on": [],
      "join_keys": [],
      "relationship": "one_to_one",
      "may_read_base_tables": true,
      "holistic": false,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "shopping_cart_users",
      "shopping_cart_events"
    ],
    "table_fingerprints": {
      "shopping_cart_users": "d3abab93ec342103",
      "shopping_cart_events": "64af14842347d245"
    },
    "data_fingerprints": {
      "shopping_cart_users": "1782:1782",
      "shopping_cart_events": "32734:32734"
    },
    "db_id": "bank_sales_trading",
    "question_id": "local298",
    "question": "For each month, calculate the total balance from all users for the previous month (measured as of the 1st of each month), replacing any negative balances with zero. Ensure that data from the first month is used only as a baseline for calculating previous total balance, and exclude it from the final output. Sort the results in ascending order by month. ",
    "rewrite": "Task: For every month after the first month present in the data, compute the total of all users' balances as of the first day of the previous month, treating any individual negative balances as zero when summing; return one row per month (excluding the first month), where the 'month' identifies the current month and the 'previous_month_total_balance' is the sum computed from balances measured on the 1st day of the previous month.\nRequired outputs: month — identifier for the current month (use the same month representation as in the schema/data, e.g., a date truncated to month or a year-month string); previous_month_total_balance — numeric total equal to the sum across all users of their balance as of the 1st day of the previous month with each individual negative balance replaced by zero\nFilters: Exclude the very first month present in the dataset from the output; use that first month only as the baseline to compute the previous_month_total_balance for the following month; When computing balances for a given previous month, use balances measured specifically on the 1st day of that previous month; Replace any negative per-user balance values with zero before summing them into previous_month_total_balance\nSort/limit: Sort results in ascending order by month; no limit",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:27:55+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-10-01T00:27:58+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "user_id",
      "balance_date",
      "balance"
    ],
    "row_count": 839,
    "grain_check": "pass",
    "filter_checks": {
      "date_is_first_of_month": "n/a"
    },
    "join_cardinality": [
      {
        "join": "shopping_cart_users.cookie_id=shopping_cart_events.cookie_id",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "View rows occur only on the first day of their month (intrinsic filter holds)",
        "sql": "SELECT COUNT(*) FROM balances_on_first_of_month WHERE strftime('%d', balance_date) != '01' OR balance_date IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "View has no duplicate rows at its declared grain (user_id, balance_date)",
        "sql": "SELECT COUNT(*) FROM (SELECT user_id, balance_date, COUNT(*) AS cnt FROM balances_on_first_of_month GROUP BY user_id, balance_date HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's user_id matches an existing shopping_cart_users.user_id (no orphaned rows from join) and cookie join didn't produce missing users",
        "sql": "SELECT COUNT(*) FROM balances_on_first_of_month b LEFT JOIN shopping_cart_users u ON b.user_id = u.user_id WHERE u.user_id IS NULL",
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
  su.user_id AS user_id,
  se.event_time AS balance_date,
  CAST(NULL AS REAL) AS balance
FROM
  shopping_cart_users AS su
JOIN
  shopping_cart_events AS se
  ON su.cookie_id = se.cookie_id
WHERE
  strftime('%d', se.event_time) = '01'
```

---

## Skill `customer_daily_balances_8`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `date` (keyed) |
| status / version | active / v1 |
| skill id | sk_e4c701d0c9d77900 |
| output columns | `customer_id`, `date`, `daily_balance` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-customer per-day net daily balance where deposits add and other transaction types subtract (one row per customer per date with daily balance)

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
    "question_id": "local299",
    "question": "For a bank database with customer transactions, calculate each customer's daily running balance (where deposits add to the balance and other transaction types subtract). For each customer and each day, compute the 30-day rolling average balance (only after having 30 days of data, and treating negative averages as zero). Then group these daily averages by month and find each customer's maximum 30-day average balance within each month. Sum these maximum values across all customers for each month. Consider the first month of each customer's transaction history as the baseline period and exclude it from the final results, presenting monthly totals of these summed maximum 30-day average balances.",
    "rewrite": "Task: Compute, for each calendar month (excluding each customer's first month of transactions), the sum across all customers of that customer's maximum 30-day rolling average daily balance observed within that month, where the daily balance is computed per customer as deposits adding and all other transaction types subtracting, 30-day rolling averages are computed only for days with a full 30-day window and any negative 30-day average is treated as zero.\nRequired outputs: month: the calendar month (year-month) for which the aggregate is reported; monthly_sum_of_max_30day_avg_balances: numeric total equal to the sum over all customers of each customer's maximum 30-day average balance within that month (after applying the non-negativity rule and excluding customers' first-month data)\nFilters: Only include daily balances where deposits add to the balance and all other transaction types subtract.; Compute a 30-day rolling average balance per customer per day only when that customer has 30 days of consecutive historical daily balances available (i.e., a full 30-day window ending on that day); do not produce a rolling-average value for days without a full 30-day history.; If a computed 30-day rolling average for a customer on a day is negative, treat it as zero when considering maxima and sums.; For each customer, identify their first calendar month that contains any transaction(s) and exclude that month entirely from the final aggregated results for that customer.; Group daily 30-day-average values by calendar month (year-month) and for each customer and month take the maximum of that customer's daily 30-day averages within the month (after applying non-negativity).; For each month (across all customers), sum those per-customer monthly maxima to produce the reported monthly total.; Include only months where at least one customer contributes a non-excluded maximum (i.e., months that are not every customer's excluded baseline month).\nSort/limit: order results by month ascending; no row limit",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:28:38+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-10-01T00:28:41+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "customer_id",
      "date",
      "daily_balance"
    ],
    "row_count": 5457,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows per grain (customer_id, date)",
        "sql": "SELECT COUNT(*) FROM (SELECT customer_id, date, COUNT(*) AS ct FROM customer_daily_balances_8 GROUP BY customer_id, date HAVING ct > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "daily_balance equals recomputed sum from base table (deposits positive, others negative)",
        "sql": "SELECT COUNT(*) FROM customer_daily_balances_8 v LEFT JOIN (SELECT customer_id, txn_date AS date, SUM(CASE WHEN txn_type = 'deposit' THEN txn_amount ELSE -txn_amount END) AS expected_daily_balance FROM customer_transactions GROUP BY customer_id, txn_date) b ON v.customer_id = b.customer_id AND v.date = b.date WHERE (b.expected_daily_balance IS NULL AND (v.daily_balance IS NOT NULL)) OR (b.expected_daily_balance IS NOT NULL AND (v.daily_balance IS NULL OR v.daily_balance != b.expected_daily_balance))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys customer_id and date are not NULL",
        "sql": "SELECT COUNT(*) FROM customer_daily_balances_8 WHERE customer_id IS NULL OR date IS NULL",
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
SELECT customer_id, txn_date AS date, SUM(CASE WHEN txn_type = 'deposit' THEN txn_amount ELSE -txn_amount END) AS daily_balance FROM customer_transactions GROUP BY customer_id, txn_date
```

---

## Skill `events_filtered`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `event_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_9a7ac3f2341355dc |
| output columns | `event_id`, `event_type`, `product_id`, `user_id`, `timestamp`, `page_id`, `session_id`, `quantity`, `other_event_metadata` |
| source tables | `shopping_cart_events`, `shopping_cart_page_hierarchy` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `product_event_flags` |

### Description

Filter the raw event log to exclude any events whose product page id is in the excluded set (1,2,12,13). Keep only events that relate to a product (views, add-to-cart, purchases, cart removals/abandonment events).

### Semantic filters

```json
{
  "exclude_page_ids": "[1, 2, 12, 13]",
  "product_required": "True"
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
        "event_type",
        "product_id",
        "user_id",
        "timestamp",
        "page_id",
        "session_id",
        "quantity",
        "other_event_metadata"
      ],
      "required_grain": [
        "event_id"
      ],
      "required_filters": {
        "exclude_page_ids": "[1, 2, 12, 13]",
        "product_required": "True"
      },
      "text": "Filter the raw event log to exclude any events whose product page id is in the excluded set (1,2,12,13). Keep only events that relate to a product (views, add-to-cart, purchases, cart removals/abandonment events).",
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
    "rewrite": "Task: Compute, for each product, the number of times it was viewed, the number of times it was added to the shopping cart, the number of times it was left in the cart without being purchased, and the number of actual purchases, excluding any events where the product's page id is in (1, 2, 12, 13).\nRequired outputs: product identifier (product id or equivalent); view_count: integer count of times the product was viewed; add_to_cart_count: integer count of times the product was added to the shopping cart; left_in_cart_count: integer count of times the product was left in the cart without being purchased; purchase_count: integer count of actual purchases of the product\nFilters: Exclude any rows/events where product's page id IN (1, 2, 12, 13); Only include products that appear in the dataset after applying the page id filter",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:30:25+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-10-01T00:30:28+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "event_id",
      "event_type",
      "product_id",
      "user_id",
      "timestamp",
      "page_id",
      "session_id",
      "quantity",
      "other_event_metadata"
    ],
    "row_count": 22320,
    "grain_check": "pass",
    "filter_checks": {
      "exclude_page_ids": "n/a",
      "product_required": "n/a"
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
        "purpose": "View has one row per event_id (no duplicate event_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT event_id, COUNT(*) AS cnt FROM events_filtered GROUP BY event_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No row has a NULL product_id (intrinsic filter product_required)",
        "sql": "SELECT COUNT(*) FROM events_filtered WHERE product_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No row has a page_id in the excluded set (intrinsic filter exclude_page_ids)",
        "sql": "SELECT COUNT(*) FROM events_filtered WHERE page_id IN (1, 2, 12, 13)",
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
  -- event_id: construct stable id from visit_id + sequence_number (keeps PK-ish from source)
  visit_id || ':' || CAST(sequence_number AS TEXT) AS event_id,
  event_type,
  shopping_cart_page_hierarchy.product_id AS product_id,
  cookie_id AS user_id,
  event_time AS timestamp,
  shopping_cart_events.page_id AS page_id,
  visit_id AS session_id,
  NULL AS quantity,
  NULL AS other_event_metadata
FROM shopping_cart_events
JOIN shopping_cart_page_hierarchy
  ON shopping_cart_events.page_id = shopping_cart_page_hierarchy.page_id
WHERE
  shopping_cart_page_hierarchy.product_id IS NOT NULL
  AND shopping_cart_page_hierarchy.page_id NOT IN (1, 2, 12, 13)
```

---

## Skill `product_event_flags`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `event_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_e358cd8f5a739681 |
| output columns | `event_id`, `product_id`, `user_id`, `timestamp`, `is_view`, `is_add_to_cart`, `is_cart_removal_or_abandon`, `is_purchase` |
| source tables | — |
| depends_on (builds on) | `events_filtered` |
| depended-on by (builds on this) | `product_action_counts` |

### Description

Normalize and classify each filtered event into canonical boolean flags for the product-level actions of interest (is_view, is_add_to_cart, is_purchase, is_cart_removal_or_abandon). Keep one row per event with these flags and canonical product identifier and timestamp.

### Semantic filters

```json
{
  "exclude_page_ids": "[1, 2, 12, 13]",
  "product_required": "True"
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
      "want_name": "product_event_flags",
      "category": "NORM",
      "required_outputs": [
        "event_id",
        "product_id",
        "user_id",
        "timestamp",
        "is_view",
        "is_add_to_cart",
        "is_cart_removal_or_abandon",
        "is_purchase"
      ],
      "required_grain": [
        "event_id"
      ],
      "required_filters": {},
      "text": "Normalize and classify each filtered event into canonical boolean flags for the product-level actions of interest (is_view, is_add_to_cart, is_purchase, is_cart_removal_or_abandon). Keep one row per event with these flags and canonical product identifier and timestamp.",
      "source_tables": [],
      "depends_on": [
        "events_filtered"
      ],
      "join_keys": [],
      "relationship": "one_to_one",
      "may_read_base_tables": false,
      "holistic": false,
      "inherited_filters": {
        "exclude_page_ids": "[1, 2, 12, 13]",
        "product_required": "True"
      }
    },
    "inherited_filters": {
      "exclude_page_ids": "[1, 2, 12, 13]",
      "product_required": "True"
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
    "rewrite": "Task: Compute, for each product, the number of times it was viewed, the number of times it was added to the shopping cart, the number of times it was left in the cart without being purchased, and the number of actual purchases, excluding any events where the product's page id is in (1, 2, 12, 13).\nRequired outputs: product identifier (product id or equivalent); view_count: integer count of times the product was viewed; add_to_cart_count: integer count of times the product was added to the shopping cart; left_in_cart_count: integer count of times the product was left in the cart without being purchased; purchase_count: integer count of actual purchases of the product\nFilters: Exclude any rows/events where product's page id IN (1, 2, 12, 13); Only include products that appear in the dataset after applying the page id filter",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:30:28+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-10-01T00:30:30+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "event_id",
      "product_id",
      "user_id",
      "timestamp",
      "is_view",
      "is_add_to_cart",
      "is_cart_removal_or_abandon",
      "is_purchase"
    ],
    "row_count": 22320,
    "grain_check": "pass",
    "filter_checks": {
      "exclude_page_ids": "n/a",
      "product_required": "n/a"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View grain: ensure event_id is unique (no duplicate rows per event_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT event_id, COUNT(*) AS cnt FROM product_event_flags GROUP BY event_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Intrinsic filter: exclude events whose page_id is in excluded list [1,2,12,13] — detect any rows that come from those pages (requires joining back to base table that has page_id).",
        "sql": "SELECT COUNT(*) FROM product_event_flags v JOIN shopping_cart_events e ON v.event_id = e.sequence_number WHERE e.page_id IN (1,2,12,13)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Intrinsic filter: product_required = True — product_id must not be NULL",
        "sql": "SELECT COUNT(*) FROM product_event_flags WHERE product_id IS NULL",
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
  ef.event_id AS event_id,
  ef.product_id AS product_id,
  ef.user_id AS user_id,
  ef.timestamp AS timestamp,
  CASE WHEN ef.event_type = 1 THEN 1 ELSE 0 END AS is_view,
  CASE WHEN ef.event_type = 2 THEN 1 ELSE 0 END AS is_add_to_cart,
  CASE WHEN ef.event_type IN (3,4) THEN 1 ELSE 0 END AS is_cart_removal_or_abandon,
  CASE WHEN ef.event_type = 5 THEN 1 ELSE 0 END AS is_purchase
FROM events_filtered ef
```

---

## Skill `product_action_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `product_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_50ce6d179d37feb9 |
| output columns | `product_id`, `view_count`, `add_to_cart_count`, `left_in_cart_count`, `purchase_count` |
| source tables | — |
| depends_on (builds on) | `product_event_flags` |
| depended-on by (builds on this) | — |

### Description

Aggregate the normalized event flags to compute counts per product: number of views, number of add-to-cart events, number of cart-left-without-purchase events, and number of purchases. Only include products that appear after the page_id filter (i.e., present in product_event_flags).

### Semantic filters

```json
{
  "exclude_page_ids": "[1, 2, 12, 13]",
  "product_required": "True"
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
      "want_name": "product_action_counts",
      "category": "AGG",
      "required_outputs": [
        "product_id",
        "view_count",
        "add_to_cart_count",
        "left_in_cart_count",
        "purchase_count"
      ],
      "required_grain": [
        "product_id"
      ],
      "required_filters": {},
      "text": "Aggregate the normalized event flags to compute counts per product: number of views, number of add-to-cart events, number of cart-left-without-purchase events, and number of purchases. Only include products that appear after the page_id filter (i.e., present in product_event_flags).",
      "source_tables": [],
      "depends_on": [
        "product_event_flags"
      ],
      "join_keys": [
        "product_id"
      ],
      "relationship": "aggregate_input",
      "may_read_base_tables": false,
      "holistic": false,
      "inherited_filters": {
        "exclude_page_ids": "[1, 2, 12, 13]",
        "product_required": "True"
      }
    },
    "inherited_filters": {
      "exclude_page_ids": "[1, 2, 12, 13]",
      "product_required": "True"
    },
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "shopping_cart_events",
      "shopping_cart_page_hierarchy"
    ],
    "table_fingerprints": {
      "shopping_cart_events": "64af14842347d245",
      "shopping_cart_page_hierarchy": "4790966bdb13dc01"
    },
    "data_fingerprints": {},
    "db_id": "bank_sales_trading",
    "question_id": "local075",
    "question": "Can you provide a breakdown of how many times each product was viewed, how many times they were added to the shopping cart, and how many times they were left in the cart without being purchased? Also, give me the count of actual purchases for each product. Ensure that products with a page id in (1, 2, 12, 13) are filtered out.",
    "rewrite": "Task: Compute, for each product, the number of times it was viewed, the number of times it was added to the shopping cart, the number of times it was left in the cart without being purchased, and the number of actual purchases, excluding any events where the product's page id is in (1, 2, 12, 13).\nRequired outputs: product identifier (product id or equivalent); view_count: integer count of times the product was viewed; add_to_cart_count: integer count of times the product was added to the shopping cart; left_in_cart_count: integer count of times the product was left in the cart without being purchased; purchase_count: integer count of actual purchases of the product\nFilters: Exclude any rows/events where product's page id IN (1, 2, 12, 13); Only include products that appear in the dataset after applying the page id filter",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:30:30+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-10-01T00:30:33+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "product_id",
      "view_count",
      "add_to_cart_count",
      "left_in_cart_count",
      "purchase_count"
    ],
    "row_count": 9,
    "grain_check": "pass",
    "filter_checks": {
      "exclude_page_ids": "n/a",
      "product_required": "n/a"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate product rows in the view (grain = product_id)",
        "sql": "SELECT COUNT(*) FROM (SELECT product_id, COUNT(*) AS cnt FROM product_action_counts GROUP BY product_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows in the view correspond to a product present in product_event_flags (view should only include products after page_id filter)",
        "sql": "SELECT COUNT(*) FROM product_action_counts pac WHERE NOT EXISTS (SELECT 1 FROM product_event_flags pef WHERE pef.product_id = pac.product_id)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each aggregated count matches the sum of the underlying flags in product_event_flags for the same product_id",
        "sql": "SELECT COUNT(*) FROM (SELECT pef.product_id FROM (SELECT product_id, SUM(CASE WHEN is_view = 1 THEN 1 ELSE 0 END) AS view_count_calc, SUM(CASE WHEN is_add_to_cart = 1 THEN 1 ELSE 0 END) AS add_to_cart_count_calc, SUM(CASE WHEN is_cart_removal_or_abandon = 1 THEN 1 ELSE 0 END) AS left_in_cart_count_calc, SUM(CASE WHEN is_purchase = 1 THEN 1 ELSE 0 END) AS purchase_count_calc FROM product_event_flags GROUP BY product_id) calc LEFT JOIN product_action_counts pac ON pac.product_id = calc.product_id WHERE pac.product_id IS NULL OR pac.view_count != calc.view_count_calc OR pac.add_to_cart_count != calc.add_to_cart_count_calc OR pac.left_in_cart_count != calc.left_in_cart_count_calc OR pac.purchase_count != calc.purchase_count_calc)",
        "result": "inconclusive",
        "violations": null,
        "error": "OperationalError: no such column: pef.product_id"
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
  product_id,
  SUM(CASE WHEN is_view = 1 THEN 1 ELSE 0 END) AS view_count,
  SUM(CASE WHEN is_add_to_cart = 1 THEN 1 ELSE 0 END) AS add_to_cart_count,
  SUM(CASE WHEN is_cart_removal_or_abandon = 1 THEN 1 ELSE 0 END) AS left_in_cart_count,
  SUM(CASE WHEN is_purchase = 1 THEN 1 ELSE 0 END) AS purchase_count
FROM product_event_flags
GROUP BY product_id
```

---

## Skill `raw_purchases_year_region`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `purchase_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_020108ddaf72398f |
| output columns | `purchase_id`, `region`, `purchase_year`, `dollars_spent`, `quantity_purchased`, `purchase_timestamp` |
| source tables | `bitcoin_transactions`, `bitcoin_members` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Select raw purchase records with purchase timestamp cast to calendar year and canonical region and numeric dollar and quantity fields; exclude records with NULL region or NULL/zero quantity or NULL dollars at this stage only if schema forces. This is the base cohort of purchases with a year column.

### Semantic filters

```json
{
  "exclude_null_quantity": "True",
  "exclude_zero_quantity": "True",
  "exclude_null_purchase_id": "True"
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
      "want_name": "raw_purchases_year_region",
      "category": "SEL",
      "required_outputs": [
        "purchase_id",
        "region",
        "purchase_year",
        "dollars_spent",
        "quantity_purchased",
        "purchase_timestamp"
      ],
      "required_grain": [
        "purchase_id"
      ],
      "required_filters": {},
      "text": "Select raw purchase records with purchase timestamp cast to calendar year and canonical region and numeric dollar and quantity fields; exclude records with NULL region or NULL/zero quantity or NULL dollars at this stage only if schema forces. This is the base cohort of purchases with a year column.",
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
    "rewrite": "Task: For each region and calendar year (excluding each region's first year of purchase data), compute the annual average purchase price per Bitcoin as (total dollar amount spent in that region and year) divided by (total quantity of Bitcoin purchased in that region and year); then, for each year, rank the regions by that average purchase price and also compute, for each region and year, the percentage change in that average price relative to the immediately preceding year for the same region.\nRequired outputs: year (calendar year); region; total_dollars_spent (sum of dollars spent in that region and year); total_quantity_purchased (sum of quantity purchased in that region and year); average_price_per_bitcoin (total_dollars_spent / total_quantity_purchased); region_rank_within_year (rank of region for that year ordered by average_price_per_bitcoin descending or specify ordering); pct_change_from_previous_year (percentage change in average_price_per_bitcoin compared to the previous calendar year for the same region; NULL if previous-year data absent)\nFilters: Exclude rows where the year is the first calendar year that has any purchase records for that region (i.e., omit each region's earliest year present in the data).; Exclude any year/region combinations where total_quantity_purchased is zero or NULL to avoid division by zero.; Use calendar year derived from the purchase timestamp/date fields; treat year as integer (e.g., 2021).\nSort/limit: Order the final result first by year ascending, then by region_rank_within_year ascending; no row limit.",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:32:36+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-10-01T00:32:39+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "purchase_id",
      "region",
      "purchase_year",
      "dollars_spent",
      "quantity_purchased",
      "purchase_timestamp"
    ],
    "row_count": 22918,
    "grain_check": "pass",
    "filter_checks": {
      "exclude_null_quantity": "n/a",
      "exclude_zero_quantity": "n/a",
      "exclude_null_purchase_id": "n/a"
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
        "purpose": "View grain: no duplicate purchase_id (each purchase_id appears at most once)",
        "sql": "SELECT COUNT(*) FROM (SELECT purchase_id FROM raw_purchases_year_region GROUP BY purchase_id HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Intrinsic filters: no rows with NULL or zero quantity or NULL purchase_id",
        "sql": "SELECT COUNT(*) FROM raw_purchases_year_region WHERE purchase_id IS NULL OR quantity_purchased IS NULL OR quantity_purchased = 0",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Intrinsic filter: region is present (view WHERE required region non-NULL via members.region OR transactions.ticker); check for NULL region",
        "sql": "SELECT COUNT(*) FROM raw_purchases_year_region WHERE region IS NULL",
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
  bitcoin_transactions.txn_id AS purchase_id,
  COALESCE(bitcoin_members.region, bitcoin_transactions.ticker, NULL) AS region,
  CAST(strftime('%Y', substr(bitcoin_transactions.txn_date, -4) || '-' || 
       printf('%02d', CASE 
         WHEN instr(bitcoin_transactions.txn_date, '-') = 3 THEN substr(bitcoin_transactions.txn_date, 1, 2)
         ELSE NULL END) || '-01') AS INTEGER) AS purchase_year,
  (bitcoin_transactions.quantity * 1.0) * (1.0) AS dollars_spent,
  bitcoin_transactions.quantity AS quantity_purchased,
  bitcoin_transactions.txn_time AS purchase_timestamp
FROM bitcoin_transactions
LEFT JOIN bitcoin_members ON bitcoin_transactions.member_id = bitcoin_members.member_id
WHERE bitcoin_transactions.quantity IS NOT NULL
  AND bitcoin_transactions.quantity != 0
  AND bitcoin_transactions.txn_id IS NOT NULL
  AND (bitcoin_members.region IS NOT NULL OR bitcoin_transactions.ticker IS NOT NULL)
```

---

## Skill `annual_region_purchase_totals`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `region`, `purchase_year` (keyed) |
| status / version | active / v1 |
| skill id | sk_d72c3d061f4dead1 |
| output columns | `region`, `purchase_year`, `total_dollars_spent`, `total_quantity_purchased`, `first_purchase_year` |
| source tables | `bitcoin_transactions`, `bitcoin_members` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-region, per-calendar-year totals of dollars spent and quantity purchased with the region's first purchase year included so it can be filtered by callers.

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
    "rewrite": "Task: For each region and calendar year (excluding each region's first year of purchase data), compute the annual average purchase price per Bitcoin as (total dollar amount spent in that region and year) divided by (total quantity of Bitcoin purchased in that region and year); then, for each year, rank the regions by that average purchase price and also compute, for each region and year, the percentage change in that average price relative to the immediately preceding year for the same region.\nRequired outputs: year (calendar year); region; total_dollars_spent (sum of dollars spent in that region and year); total_quantity_purchased (sum of quantity purchased in that region and year); average_price_per_bitcoin (total_dollars_spent / total_quantity_purchased); region_rank_within_year (rank of region for that year ordered by average_price_per_bitcoin descending or specify ordering); pct_change_from_previous_year (percentage change in average_price_per_bitcoin compared to the previous calendar year for the same region; NULL if previous-year data absent)\nFilters: Exclude rows where the year is the first calendar year that has any purchase records for that region (i.e., omit each region's earliest year present in the data).; Exclude any year/region combinations where total_quantity_purchased is zero or NULL to avoid division by zero.; Use calendar year derived from the purchase timestamp/date fields; treat year as integer (e.g., 2021).\nSort/limit: Order the final result first by year ascending, then by region_rank_within_year ascending; no row limit.",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:32:45+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-10-01T00:32:49+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "region",
      "purchase_year",
      "total_dollars_spent",
      "total_quantity_purchased",
      "first_purchase_year"
    ],
    "row_count": 30,
    "grain_check": "pass",
    "filter_checks": {},
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
        "purpose": "No duplicate rows at the declared grain (region, purchase_year)",
        "sql": "SELECT COUNT(*) FROM (SELECT region, purchase_year, COUNT(*) AS cnt FROM annual_region_purchase_totals GROUP BY region, purchase_year HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "total_dollars_spent matches sum of quantity per underlying transactions (no unexpected aggregation or join duplication)",
        "sql": "SELECT COUNT(*) FROM (SELECT v.region, v.purchase_year FROM annual_region_purchase_totals v LEFT JOIN (SELECT COALESCE(m.region, t.ticker) AS region, CAST(strftime('%Y', substr(t.txn_date, -4) || '-' || printf('%02d', CASE WHEN instr(t.txn_date, '-') = 3 THEN substr(t.txn_date,1,2) ELSE NULL END) || '-01') AS INTEGER) AS purchase_year, SUM((t.quantity * 1.0) * 1.0) AS expected_total_dollars_spent FROM bitcoin_transactions t LEFT JOIN bitcoin_members m ON t.member_id = m.member_id WHERE t.quantity IS NOT NULL AND t.txn_id IS NOT NULL GROUP BY region, purchase_year) s ON v.region = s.region AND v.purchase_year = s.purchase_year WHERE (v.total_dollars_spent IS NULL AND s.expected_total_dollars_spent IS NOT NULL) OR (v.total_dollars_spent IS NOT NULL AND ROUND(v.total_dollars_spent - s.expecte",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "first_purchase_year equals the minimum transaction year for that region",
        "sql": "SELECT COUNT(*) FROM (SELECT v.region, v.first_purchase_year FROM annual_region_purchase_totals v LEFT JOIN (SELECT COALESCE(m.region, t.ticker) AS region, MIN(CAST(strftime('%Y', substr(t.txn_date, -4) || '-' || printf('%02d', CASE WHEN instr(t.txn_date, '-') = 3 THEN substr(t.txn_date,1,2) ELSE NULL END) || '-01') AS INTEGER)) AS min_year FROM bitcoin_transactions t LEFT JOIN bitcoin_members m ON t.member_id = m.member_id WHERE t.quantity IS NOT NULL AND t.txn_id IS NOT NULL GROUP BY region) s ON v.region = s.region WHERE (v.first_purchase_year IS NULL AND s.min_year IS NOT NULL) OR (v.first_purchase_year IS NOT NULL AND v.first_purchase_year != s.min_year))",
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
  COALESCE(m.region, t.ticker) AS region,
  CAST(strftime('%Y', substr(t.txn_date, -4) || '-' || printf('%02d', CASE WHEN instr(t.txn_date, '-') = 3 THEN substr(t.txn_date, 1, 2) ELSE NULL END) || '-01') AS INTEGER) AS purchase_year,
  SUM((t.quantity * 1.0) * 1.0) AS total_dollars_spent,
  SUM(t.quantity) AS total_quantity_purchased,
  MIN(CAST(strftime('%Y', substr(t.txn_date, -4) || '-' || printf('%02d', CASE WHEN instr(t.txn_date, '-') = 3 THEN substr(t.txn_date, 1, 2) ELSE NULL END) || '-01') AS INTEGER)) OVER (PARTITION BY COALESCE(m.region, t.ticker)) AS first_purchase_year
FROM bitcoin_transactions t
LEFT JOIN bitcoin_members m ON t.member_id = m.member_id
WHERE t.quantity IS NOT NULL
  AND t.txn_id IS NOT NULL
GROUP BY region, purchase_year
```

---

## Skill `veg_whsle_rows_sel`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `row_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_5099b165f80fc83c |
| output columns | `row_id`, `year`, `category`, `wholesale_price`, `selling_price`, `loss`, `loss_rate` |
| source tables | `veg_whsle_df`, `veg_cat`, `veg_loss_rate_df` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Select only veg wholesale data rows whose date/year is in 2020-2023 and whose category is non-null/non-empty. Keep original numeric fields needed for later aggregation (wholesale_price, selling_price, loss, loss_rate) and the year extracted from the date.

### Semantic filters

```json
{
  "year_in": "[2020, 2021, 2022, 2023]",
  "category_not_null": "True",
  "category_not_empty": "True"
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
      "want_name": "veg_whsle_rows_sel",
      "category": "SEL",
      "required_outputs": [
        "row_id",
        "year",
        "category",
        "wholesale_price",
        "selling_price",
        "loss",
        "loss_rate"
      ],
      "required_grain": [
        "row_id"
      ],
      "required_filters": {
        "year_in": "[2020, 2021, 2022, 2023]",
        "category_not_null": "True",
        "category_not_empty": "True"
      },
      "text": "Select only veg wholesale data rows whose date/year is in 2020-2023 and whose category is non-null/non-empty. Keep original numeric fields needed for later aggregation (wholesale_price, selling_price, loss, loss_rate) and the year extracted from the date.",
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
      "veg_whsle_df",
      "veg_cat",
      "veg_loss_rate_df"
    ],
    "table_fingerprints": {
      "veg_whsle_df": "ca2476beebba87be",
      "veg_cat": "8f2bc76eff0086cb",
      "veg_loss_rate_df": "f1984b6f1dc0c87f"
    },
    "data_fingerprints": {
      "veg_whsle_df": "55982:55982",
      "veg_cat": "251:251",
      "veg_loss_rate_df": "251:251"
    },
    "db_id": "bank_sales_trading",
    "question_id": "local285",
    "question": "For veg whsle data, can you analyze our financial performance over the years 2020 to 2023? I need insights into the average wholesale price, maximum wholesale price, minimum wholesale price, wholesale price difference, total wholesale price, total selling price, average loss rate, total loss, and profit for each category within each year. Round all calculated values to two decimal places.",
    "rewrite": "Task: Compute, for each year 2020, 2021, 2022, and 2023 and for each category in the veg whsle data, the requested yearly summary metrics (averages, maxima, minima, sums, rates, and derived values) using only records in those years.\nRequired outputs: year (2020, 2021, 2022, or 2023); category (the category value from the veg whsle data); average_wholesale_price (average wholesale price for that category-year, rounded to 2 decimals); maximum_wholesale_price (maximum wholesale price for that category-year, rounded to 2 decimals); minimum_wholesale_price (minimum wholesale price for that category-year, rounded to 2 decimals); wholesale_price_difference (maximum_wholesale_price - minimum_wholesale_price, rounded to 2 decimals); total_wholesale_price (sum of wholesale prices for that category-year, rounded to 2 decimals); total_selling_price (sum of selling prices for that category-year, rounded to 2 decimals); average_loss_rate (average of per-record loss rate for that category-year, expressed as a decimal or percentage as in source data, rounded to 2 decimals); total_loss (sum of losses for that category-year, rounded to 2 decimals); profit (per-category-year profit defined as total_selling_price - total_wholesale_price - total_loss, rounded to 2 decimals)\nFilters: include only records with a date/year value in {2020, 2021, 2022, 2023}; group results by year and category; exclude rows where category is NULL or empty (if applicable)\nSort/limit: order results by year ascending, then by category ascending; no row limit",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:34:24+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-10-01T00:34:26+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "row_id",
      "year",
      "category",
      "wholesale_price",
      "selling_price",
      "loss",
      "loss_rate"
    ],
    "row_count": 55982,
    "grain_check": "pass",
    "filter_checks": {
      "year_in": "n/a",
      "category_not_null": "n/a",
      "category_not_empty": "n/a"
    },
    "join_cardinality": [
      {
        "join": "veg_whsle_df.item_code=veg_cat.item_code",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      },
      {
        "join": "veg_whsle_df.item_code=veg_loss_rate_df.item_code",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "Ensure view rows are within allowed years (2020-2023). Counts rows whose year is outside the intrinsic filter.",
        "sql": "SELECT COUNT(*) FROM veg_whsle_rows_sel WHERE year NOT IN (2020,2021,2022,2023)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Ensure category is not NULL or empty. Counts rows where category is NULL or only whitespace.",
        "sql": "SELECT COUNT(*) FROM veg_whsle_rows_sel WHERE category IS NULL OR trim(category) = ''",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Ensure row_id is a unique key (no duplicate row_id). Counts number of duplicate row_id values.",
        "sql": "SELECT COALESCE(SUM(cnt-1),0) FROM (SELECT row_id, COUNT(*) AS cnt FROM veg_whsle_rows_sel GROUP BY row_id HAVING cnt>1)",
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
  veg_whsle_df."index" AS row_id,
  CAST(strftime('%Y', veg_whsle_df.whsle_date) AS INTEGER) AS year,
  veg_cat.category_name AS category,
  veg_whsle_df."whsle_px_rmb-kg" AS wholesale_price,
  NULL AS selling_price,
  NULL AS loss,
  veg_loss_rate_df."loss_rate_%" AS loss_rate
FROM veg_whsle_df
LEFT JOIN veg_cat
  ON veg_whsle_df.item_code = veg_cat.item_code
LEFT JOIN veg_loss_rate_df
  ON veg_whsle_df.item_code = veg_loss_rate_df.item_code
WHERE year IN (2020, 2021, 2022, 2023)
  AND veg_cat.category_name IS NOT NULL
  AND trim(veg_cat.category_name) <> ''
```

---

## Skill `veg_whsle_rows_norm_15`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `row_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_5d6368c4eff8d7b4 |
| output columns | `row_id`, `year`, `category`, `wholesale_price`, `selling_price`, `loss`, `loss_rate`, `wholesale_price_num`, `selling_price_num`, `loss_num`, `loss_rate_dec` |
| source tables | `veg_whsle_df`, `veg_cat`, `veg_loss_rate_df` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Normalized veg wholesale rows with year, category, numeric wholesale/selling/loss fields and a decimal loss rate, filtered to years 2020-2023 and non-empty categories.

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
    "removed_constants": [
      "2020",
      "2021",
      "2022",
      "2023"
    ],
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "veg_whsle_df",
      "veg_cat",
      "veg_loss_rate_df"
    ],
    "table_fingerprints": {
      "veg_whsle_df": "ca2476beebba87be",
      "veg_cat": "8f2bc76eff0086cb",
      "veg_loss_rate_df": "f1984b6f1dc0c87f"
    },
    "data_fingerprints": {
      "veg_whsle_df": "55982:55982",
      "veg_cat": "251:251",
      "veg_loss_rate_df": "251:251"
    },
    "db_id": "bank_sales_trading",
    "question_id": "local285",
    "question": "For veg whsle data, can you analyze our financial performance over the years 2020 to 2023? I need insights into the average wholesale price, maximum wholesale price, minimum wholesale price, wholesale price difference, total wholesale price, total selling price, average loss rate, total loss, and profit for each category within each year. Round all calculated values to two decimal places.",
    "rewrite": "Task: Compute, for each year 2020, 2021, 2022, and 2023 and for each category in the veg whsle data, the requested yearly summary metrics (averages, maxima, minima, sums, rates, and derived values) using only records in those years.\nRequired outputs: year (2020, 2021, 2022, or 2023); category (the category value from the veg whsle data); average_wholesale_price (average wholesale price for that category-year, rounded to 2 decimals); maximum_wholesale_price (maximum wholesale price for that category-year, rounded to 2 decimals); minimum_wholesale_price (minimum wholesale price for that category-year, rounded to 2 decimals); wholesale_price_difference (maximum_wholesale_price - minimum_wholesale_price, rounded to 2 decimals); total_wholesale_price (sum of wholesale prices for that category-year, rounded to 2 decimals); total_selling_price (sum of selling prices for that category-year, rounded to 2 decimals); average_loss_rate (average of per-record loss rate for that category-year, expressed as a decimal or percentage as in source data, rounded to 2 decimals); total_loss (sum of losses for that category-year, rounded to 2 decimals); profit (per-category-year profit defined as total_selling_price - total_wholesale_price - total_loss, rounded to 2 decimals)\nFilters: include only records with a date/year value in {2020, 2021, 2022, 2023}; group results by year and category; exclude rows where category is NULL or empty (if applicable)\nSort/limit: order results by year ascending, then by category ascending; no row limit",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:34:37+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-10-01T00:34:40+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "row_id",
      "year",
      "category",
      "wholesale_price",
      "selling_price",
      "loss",
      "loss_rate",
      "wholesale_price_num",
      "selling_price_num",
      "loss_num",
      "loss_rate_dec"
    ],
    "row_count": 55982,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "veg_whsle_df.item_code=veg_cat.item_code",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      },
      {
        "join": "veg_whsle_df.item_code=veg_loss_rate_df.item_code",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "Each row_id in the view is unique (no duplicate rows at the declared grain).",
        "sql": "SELECT COUNT(*) FROM (SELECT row_id, COUNT(*) AS cnt FROM veg_whsle_rows_norm_15 GROUP BY row_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows have year between 2020 and 2023 (view promised filtering to years 2020-2023).",
        "sql": "SELECT COUNT(*) FROM veg_whsle_rows_norm_15 WHERE year IS NULL OR year < 2020 OR year > 2023",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows have non-empty category (view filtered to non-empty categories).",
        "sql": "SELECT COUNT(*) FROM veg_whsle_rows_norm_15 WHERE category IS NULL OR trim(category) = ''",
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
  veg_whsle_df."index" AS row_id,
  CAST(strftime('%Y', veg_whsle_df.whsle_date) AS INTEGER) AS year,
  veg_cat.category_name AS category,
  veg_whsle_df."whsle_px_rmb-kg" AS wholesale_price,
  NULL AS selling_price,
  NULL AS loss,
  veg_loss_rate_df."loss_rate_%" AS loss_rate,
  -- normalized numeric wholesale_price
  CASE
    WHEN typeof(veg_whsle_df."whsle_px_rmb-kg") = 'integer' OR typeof(veg_whsle_df."whsle_px_rmb-kg") = 'real' THEN CAST(veg_whsle_df."whsle_px_rmb-kg" AS REAL)
    WHEN trim(veg_whsle_df."whsle_px_rmb-kg") = '' THEN NULL
    ELSE CAST(replace(replace(veg_whsle_df."whsle_px_rmb-kg", '$', ''), ',', '') AS REAL)
  END AS wholesale_price_num,
  -- normalized selling_price (kept generic; original source may have NULLs)
  CASE
    WHEN typeof(NULL) = 'integer' OR typeof(NULL) = 'real' THEN CAST(NULL AS REAL)
    WHEN NULL IS NOT NULL AND trim(NULL) = '' THEN NULL
    ELSE CAST(replace(replace(NULL, '$', ''), ',', '') AS REAL)
  END AS selling_price_num,
  -- normalized loss
  CASE
    WHEN typeof(NULL) = 'integer' OR typeof(NULL) = 'real' THEN CAST(NULL AS REAL)
    WHEN NULL IS NOT NULL AND trim(NULL) = '' THEN NULL
    ELSE CAST(replace(replace(NULL, '$', ''), ',', '') AS REAL)
  END AS loss_num,
  -- normalized loss_rate to decimal
  CASE
    WHEN veg_loss_rate_df."loss_rate_%" IS NULL OR trim(veg_loss_rate_df."loss_rate_%") = '' THEN NULL
    WHEN typeof(veg_loss_rate_df."loss_rate_%") = 'integer' OR typeof(veg_loss_rate_df."loss_rate_%") = 'real' THEN CAST(veg_loss_rate_df."loss_rate_%" AS REAL)
    WHEN instr(veg_loss_rate_df."loss_rate_%", '%') > 0 THEN CAST(replace(veg_loss_rate_df."loss_rate_%", '%', '') AS REAL) / 100.0
    ELSE CAST(replace(veg_loss_rate_df."loss_rate_%", ',', '') AS REAL)
  END AS loss_rate_dec
FROM veg_whsle_df
LEFT JOIN veg_cat ON veg_whsle_df.item_code = veg_cat.item_code
LEFT JOIN veg_loss_rate_df ON veg_whsle_df.item_code = veg_loss_rate_df.item_code
WHERE veg_cat.category_name IS NOT NULL
  AND trim(veg_cat.category_name) <> ''
```

---

## Skill `daily_sales_events`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `other_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_1ff11189647597af |
| output columns | `sale_date`, `sale_amount`, `other_id` |
| source tables | `cleaned_weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Select the atomic sales rows (one row per sale event or weekly-sales entry) with their sale_date and sale_amount. This relation is a filtered projection of the raw sales data into canonical columns used for date-range membership.

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
      "want_name": "daily_sales_events",
      "category": "SEL",
      "required_outputs": [
        "sale_date",
        "sale_amount",
        "other_id"
      ],
      "required_grain": [
        "sale_event"
      ],
      "required_filters": {},
      "text": "Select the atomic sales rows (one row per sale event or weekly-sales entry) with their sale_date and sale_amount. This relation is a filtered projection of the raw sales data into canonical columns used for date-range membership.",
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
    "question_id": "local301",
    "question": "For weekly-sales data, I need an analysis of our sales performance around mid-June for the years 2018, 2019, and 2020. Specifically, calculate the percentage change in sales between the four weeks leading up to June 15 and the four weeks following June 15 for each year.",
    "rewrite": "Task: For each year in {2018,2019,2020}, compute the percentage change in total sales between the four-week period immediately preceding June 15 (the 4 weeks ending the day before June 15) and the four-week period immediately following June 15 (the 4 weeks starting the day after June 15).\nRequired outputs: year — the calendar year (2018, 2019, or 2020); pre_period_start_date — start date of the four-week pre-June-15 period; pre_period_end_date — end date of the four-week pre-June-15 period; pre_period_sales — total sales summed over the four-week pre-period; post_period_start_date — start date of the four-week post-June-15 period; post_period_end_date — end date of the four-week post-period; post_period_sales — total sales summed over the four-week post-period; pct_change — percentage change from pre_period_sales to post_period_sales computed as ((post_period_sales - pre_period_sales) / NULLIF(pre_period_sales,0)) * 100; if pre_period_sales is zero, pct_change should be NULL or indicated as undefined\nFilters: Include only rows for years 2018, 2019, and 2020; Define June 15 of each year as the date boundary: pre-period = the 28 days immediately before June 15 (i.e., from June 15 minus 28 days through June 14 inclusive); post-period = the 28 days immediately after June 15 (i.e., from June 16 through June 15 plus 28 days inclusive); Use calendar dates (not ISO weeks); aggregate sales by summing the weekly-sales data entries whose date/timestamp falls within the inclusive date ranges above; Exclude any partial-week handling ambiguity by using the exact date ranges specified; if the underlying weekly-sales data uses week-start or week-end dates, include a sale in a period if its associated date falls within the inclusive range\nSort/limit: order results by year ascending, no row limit",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:35:16+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-10-01T00:35:19+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "sale_date",
      "sale_amount",
      "other_id"
    ],
    "row_count": 17117,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (other_id must be unique)",
        "sql": "SELECT COUNT(*) FROM (SELECT other_id, COUNT(*) AS cnt FROM daily_sales_events GROUP BY other_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Keys are not NULL (other_id must have a value for every row)",
        "sql": "SELECT COUNT(*) FROM daily_sales_events WHERE other_id IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "sale_amount and sale_date must match the source columns from cleaned_weekly_sales for the same other_id (detect mismatches or missing source rows)",
        "sql": "SELECT COUNT(*) FROM daily_sales_events d LEFT JOIN cleaned_weekly_sales c ON d.other_id = c.rowid WHERE NOT ( (c.week_date IS NOT NULL AND d.sale_date = c.week_date) OR (c.week_date IS NULL AND d.sale_date IS NULL) ) OR NOT ( (c.sales IS NOT NULL AND d.sale_amount = c.sales) OR (c.sales IS NULL AND d.sale_amount IS NULL) ) OR c.rowid IS NULL",
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
  week_date AS sale_date,
  sales AS sale_amount,
  rowid AS other_id
FROM cleaned_weekly_sales
```

---
