# Skill graph — `bank_sales_trading` (6 skills)

## Skill `customer_monthly_balances`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month` (keyed) |
| status / version | active / v1 |
| skill id | sk_b46fdc57f4e08cd1 |
| output columns | `customer_id`, `month`, `balance` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customer_monthly_changes` |

### Description

Extracts monthly balances for each customer.

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
      "want_name": "customer_monthly_balances",
      "category": "SEL",
      "required_outputs": [
        "customer_id",
        "month",
        "balance"
      ],
      "required_grain": [
        "customer_id",
        "month"
      ],
      "required_filters": {},
      "text": "Extracts monthly balances for each customer.",
      "source_tables": [],
      "depends_on": [],
      "join_keys": [],
      "relationship": "independent",
      "may_read_base_tables": true,
      "holistic": false
    },
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "customer_transactions"
    ],
    "table_fingerprints": {
      "customer_transactions": "f8010579183da4ad"
    },
    "db_id": "bank_sales_trading",
    "question_id": "local074",
    "question": "Please generate a summary of the closing balances at the end of each month for each customer transactions, show the monthly changes and monthly cumulative bank account balances. Ensure that even if a customer has no account activity in a given month, the balance for that month is still included in the output.",
    "rewrite": "Task: Generate a monthly summary of customer bank account balances, including monthly changes and cumulative balances, for all customers, even those with no transactions in a given month.\nRequired outputs: Monthly bank account balance for each customer; Monthly change in bank account balance (difference between the current and previous month's balance); Cumulative bank account balance (running total of balances over time) for each customer\nFilters: All customers must be included in the output.; For each customer, include data for every month in the dataset.; If a customer has no transactions in a specific month, the monthly balance for that month should still be included, defaulting to a balance of 0 for that month.",
    "route": "dependency_nxm_graph",
    "model": "local-gemma3-4b",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T10:57:25+00:00",
    "schema_fingerprint": "27492810c24891b6"
  },
  "validation": {
    "validated_at": "2026-09-30T10:57:25+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "customer_id",
      "month",
      "balance"
    ],
    "row_count": 1720,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
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
  c.customer_id,
  strftime('%Y-%m', c.txn_date) AS month,
  SUM(c.txn_amount) AS balance
FROM customer_transactions AS c
GROUP BY c.customer_id, strftime('%Y-%m', c.txn_date)
```

---

## Skill `customer_monthly_changes`

Category: `WIN`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month` (keyed) |
| status / version | active / v1 |
| skill id | sk_05150fd367ef8342 |
| output columns | `customer_id`, `month`, `balance_change` |
| source tables | — |
| depends_on (builds on) | `customer_monthly_balances` |
| depended-on by (builds on this) | `customer_cumulative_balances` |

### Description

Calculates the monthly change in balance for each customer using a running total window.

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
      "want_name": "customer_monthly_changes",
      "category": "WIN",
      "required_outputs": [
        "customer_id",
        "month",
        "balance_change"
      ],
      "required_grain": [
        "customer_id",
        "month"
      ],
      "required_filters": {},
      "text": "Calculates the monthly change in balance for each customer using a running total window.",
      "source_tables": [],
      "depends_on": [
        "customer_monthly_balances"
      ],
      "join_keys": [],
      "relationship": "aggregate_input",
      "may_read_base_tables": false,
      "holistic": false
    },
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "customer_transactions"
    ],
    "table_fingerprints": {
      "customer_transactions": "f8010579183da4ad"
    },
    "db_id": "bank_sales_trading",
    "question_id": "local074",
    "question": "Please generate a summary of the closing balances at the end of each month for each customer transactions, show the monthly changes and monthly cumulative bank account balances. Ensure that even if a customer has no account activity in a given month, the balance for that month is still included in the output.",
    "rewrite": "Task: Generate a monthly summary of customer bank account balances, including monthly changes and cumulative balances, for all customers, even those with no transactions in a given month.\nRequired outputs: Monthly bank account balance for each customer; Monthly change in bank account balance (difference between the current and previous month's balance); Cumulative bank account balance (running total of balances over time) for each customer\nFilters: All customers must be included in the output.; For each customer, include data for every month in the dataset.; If a customer has no transactions in a specific month, the monthly balance for that month should still be included, defaulting to a balance of 0 for that month.",
    "route": "dependency_nxm_graph",
    "model": "local-gemma3-4b",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T10:57:26+00:00",
    "schema_fingerprint": "27492810c24891b6"
  },
  "validation": {
    "validated_at": "2026-09-30T10:57:27+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "customer_id",
      "month",
      "balance_change"
    ],
    "row_count": 1720,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "customer_monthly_balances.customer_id=customer_monthly_balances.customer_id",
        "left_unique": null,
        "right_unique": null,
        "relationship": "unknown"
      },
      {
        "join": "customer_monthly_balances.month=customer_monthly_balances.month",
        "left_unique": null,
        "right_unique": null,
        "relationship": "unknown"
      }
    ],
    "tests": [
      {
        "purpose": "Check for duplicate rows based on customer_id and month",
        "sql": "SELECT COUNT(*) FROM customer_monthly_changes WHERE customer_id IN (SELECT customer_id FROM customer_monthly_changes GROUP BY customer_id, month HAVING COUNT(*) > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Check if every row satisfies the intrinsic filter (no filter)",
        "sql": "SELECT COUNT(*) FROM customer_monthly_changes WHERE balance_change IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Check if the sum of balance_change reconciles with the sum of (balance - balance) from the base table",
        "sql": "SELECT COUNT(*) FROM customer_monthly_changes WHERE balance_change != (SELECT SUM(balance - balance) FROM customer_monthly_balances)",
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
  ct1.customer_id,
  ct1.month,
  SUM(ct1.balance - ct2.balance) AS balance_change
FROM customer_monthly_balances ct1
LEFT JOIN customer_monthly_balances ct2
  ON ct1.customer_id = ct2.customer_id
  AND ct1.month = ct2.month
GROUP BY ct1.customer_id, ct1.month
```

---

## Skill `customer_cumulative_balances`

Category: `WIN`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month` (keyed) |
| status / version | active / v1 |
| skill id | sk_2db97ed3782f8beb |
| output columns | `customer_id`, `month`, `cumulative_balance` |
| source tables | — |
| depends_on (builds on) | `customer_monthly_changes` |
| depended-on by (builds on this) | — |

### Description

Calculates the cumulative balance for each customer using a running total window.

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
      "want_name": "customer_cumulative_balances",
      "category": "WIN",
      "required_outputs": [
        "customer_id",
        "month",
        "cumulative_balance"
      ],
      "required_grain": [
        "customer_id",
        "month"
      ],
      "required_filters": {},
      "text": "Calculates the cumulative balance for each customer using a running total window.",
      "source_tables": [],
      "depends_on": [
        "customer_monthly_changes"
      ],
      "join_keys": [],
      "relationship": "aggregate_input",
      "may_read_base_tables": false,
      "holistic": false
    },
    "contract_version": 2,
    "grain_basis": "verified_unique",
    "lineage": [
      "customer_transactions"
    ],
    "table_fingerprints": {
      "customer_transactions": "f8010579183da4ad"
    },
    "db_id": "bank_sales_trading",
    "question_id": "local074",
    "question": "Please generate a summary of the closing balances at the end of each month for each customer transactions, show the monthly changes and monthly cumulative bank account balances. Ensure that even if a customer has no account activity in a given month, the balance for that month is still included in the output.",
    "rewrite": "Task: Generate a monthly summary of customer bank account balances, including monthly changes and cumulative balances, for all customers, even those with no transactions in a given month.\nRequired outputs: Monthly bank account balance for each customer; Monthly change in bank account balance (difference between the current and previous month's balance); Cumulative bank account balance (running total of balances over time) for each customer\nFilters: All customers must be included in the output.; For each customer, include data for every month in the dataset.; If a customer has no transactions in a specific month, the monthly balance for that month should still be included, defaulting to a balance of 0 for that month.",
    "route": "dependency_nxm_graph",
    "model": "local-gemma3-4b",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T10:57:27+00:00",
    "schema_fingerprint": "27492810c24891b6"
  },
  "validation": {
    "validated_at": "2026-09-30T10:57:27+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "customer_id",
      "month",
      "cumulative_balance"
    ],
    "row_count": 1720,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
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
  ct.customer_id,
  ct.month,
  SUM(ct.balance_change) OVER (PARTITION BY ct.customer_id ORDER BY ct.month) AS cumulative_balance
FROM customer_monthly_changes ct
```

---

## Skill `customer_balances_2020`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `customer_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_1ab8b92922020dcc |
| output columns | `customer_id`, `balance` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Select customer balances for the year 2020.

### Semantic filters

```json
{
  "column": "txn_date",
  "value": "2020"
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
      "want_name": "customer_balances_2020",
      "category": "SEL",
      "required_outputs": [
        "customer_id",
        "balance"
      ],
      "required_grain": [
        "customer_id"
      ],
      "required_filters": {
        "year": "2020"
      },
      "text": "Select customer balances for the year 2020.",
      "source_tables": [],
      "depends_on": [],
      "join_keys": [],
      "relationship": "independent",
      "may_read_base_tables": true,
      "holistic": false
    },
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "customer_transactions"
    ],
    "table_fingerprints": {
      "customer_transactions": "f8010579183da4ad"
    },
    "db_id": "bank_sales_trading",
    "question_id": "local064",
    "question": "For each customer and each month of 2020, first calculate the month-end balance by adding all deposit amounts and subtracting all withdrawal amounts that occurred during that specific month. Then determine which month in 2020 has the highest count of customers with a positive month-end balance and which month has the lowest count. For each of these two months, compute the average month-end balance across all customers and provide the difference between these two averages",
    "rewrite": "Task: Calculate the month-end balance for each customer in 2020, identify the months with the highest and lowest counts of customers with positive balances, and then compute the average month-end balance for those two months, finally determining the difference between these two averages.\nRequired outputs: The average month-end balance for the month with the highest count of customers with a positive month-end balance.; The average month-end balance for the month with the lowest count of customers with a positive month-end balance.; The difference between the two average month-end balances.\nFilters: The analysis must be restricted to the year 2020.; The calculation of month-end balance must consider all deposits and withdrawals for each customer within a specific month.; A positive month-end balance is defined as the balance after deposits minus withdrawals for a given month.",
    "route": "dependency_nxm_graph",
    "model": "local-gemma3-4b",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T10:57:41+00:00",
    "schema_fingerprint": "27492810c24891b6"
  },
  "validation": {
    "validated_at": "2026-09-30T10:57:41+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "customer_id",
      "balance"
    ],
    "row_count": 500,
    "grain_check": "pass",
    "filter_checks": {
      "column": "n/a",
      "value": "n/a"
    },
    "join_cardinality": [],
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
  ct.customer_id,
  SUM(ct.txn_amount) AS balance
FROM customer_transactions AS ct
WHERE strftime('%Y', ct.txn_date) = '2020'
GROUP BY ct.customer_id
```

---

## Skill `monthly_net_balances`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month` (keyed) |
| status / version | active / v1 |
| skill id | sk_fffd6da0d474fd54 |
| output columns | `customer_id`, `month`, `net_balance` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `monthly_growth_rates` |

### Description

Calculate the monthly net balance for each customer.

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
      "want_name": "monthly_net_balances",
      "category": "AGG",
      "required_outputs": [
        "customer_id",
        "month",
        "net_balance"
      ],
      "required_grain": [
        "customer_id",
        "month"
      ],
      "required_filters": {},
      "text": "Calculate the monthly net balance for each customer.",
      "source_tables": [],
      "depends_on": [],
      "join_keys": [],
      "relationship": "aggregate_input",
      "may_read_base_tables": true,
      "holistic": false
    },
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "customer_transactions"
    ],
    "table_fingerprints": {
      "customer_transactions": "f8010579183da4ad"
    },
    "db_id": "bank_sales_trading",
    "question_id": "local297",
    "question": "For each customer, group all deposits and withdrawals by the first day of each month to obtain a monthly net amount, then calculate each month’s closing balance by cumulatively summing these monthly nets. Next, determine the most recent month’s growth rate by comparing its closing balance to the prior month’s balance, treating deposits as positive and withdrawals as negative, and if the previous month’s balance is zero, the growth rate should be the current month’s balance multiplied by 100. Finally, compute the percentage of customers whose most recent month shows a growth rate of more than 5%.",
    "rewrite": "Task: Calculate the percentage of customers with a monthly growth rate exceeding 5%, based on cumulative monthly net balances and comparing each month's closing balance to the previous month's balance.\nRequired outputs: The percentage of customers whose most recent month's closing balance shows a growth rate greater than 5%.; The closing balance for each customer for each month.\nFilters: For each customer, group deposits and withdrawals by the first day of each month to obtain a monthly net amount.; Calculate each month’s closing balance by cumulatively summing these monthly nets.; Determine the most recent month’s growth rate by comparing its closing balance to the prior month’s balance, treating deposits as positive and withdrawals as negative.; If the previous month’s balance is zero, the growth rate should be the current month’s balance multiplied by 100.; The calculation of growth rate must be performed for each customer, considering only the most recent month.",
    "route": "dependency_nxm_graph",
    "model": "local-gemma3-4b",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T10:57:55+00:00",
    "schema_fingerprint": "27492810c24891b6"
  },
  "validation": {
    "validated_at": "2026-09-30T10:57:55+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "customer_id",
      "month",
      "net_balance"
    ],
    "row_count": 1720,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "c.customer_id=customer_transactions.customer_id",
        "left_unique": null,
        "right_unique": false,
        "relationship": "unknown"
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
  c.customer_id,
  STRFTIME('%Y-%m', t.txn_date) AS month,
  SUM(t.txn_amount) AS net_balance
FROM customer_transactions t
JOIN (SELECT customer_id, txn_date FROM customer_transactions) AS c
ON c.customer_id = t.customer_id
GROUP BY c.customer_id, STRFTIME('%Y-%m', t.txn_date)
```

---

## Skill `monthly_growth_rates`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | — (scalar) |
| status / version | active / v1 |
| skill id | sk_09e0232327825e7c |
| output columns | `customer_id`, `month`, `growth_rate` |
| source tables | `customer_transactions` |
| depends_on (builds on) | `monthly_net_balances` |
| depended-on by (builds on this) | — |

### Description

Calculate the monthly growth rate for each customer.

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
      "want_name": "monthly_growth_rates",
      "category": "AGG",
      "required_outputs": [
        "customer_id",
        "month",
        "growth_rate"
      ],
      "required_grain": [
        "customer_id",
        "month"
      ],
      "required_filters": {},
      "text": "Calculate the monthly growth rate for each customer.",
      "source_tables": [],
      "depends_on": [
        "monthly_net_balances"
      ],
      "join_keys": [],
      "relationship": "aggregate_input",
      "may_read_base_tables": true,
      "holistic": false
    },
    "contract_version": 2,
    "grain_basis": "scalar_aggregate",
    "lineage": [
      "customer_transactions"
    ],
    "table_fingerprints": {
      "customer_transactions": "f8010579183da4ad"
    },
    "db_id": "bank_sales_trading",
    "question_id": "local297",
    "question": "For each customer, group all deposits and withdrawals by the first day of each month to obtain a monthly net amount, then calculate each month’s closing balance by cumulatively summing these monthly nets. Next, determine the most recent month’s growth rate by comparing its closing balance to the prior month’s balance, treating deposits as positive and withdrawals as negative, and if the previous month’s balance is zero, the growth rate should be the current month’s balance multiplied by 100. Finally, compute the percentage of customers whose most recent month shows a growth rate of more than 5%.",
    "rewrite": "Task: Calculate the percentage of customers with a monthly growth rate exceeding 5%, based on cumulative monthly net balances and comparing each month's closing balance to the previous month's balance.\nRequired outputs: The percentage of customers whose most recent month's closing balance shows a growth rate greater than 5%.; The closing balance for each customer for each month.\nFilters: For each customer, group deposits and withdrawals by the first day of each month to obtain a monthly net amount.; Calculate each month’s closing balance by cumulatively summing these monthly nets.; Determine the most recent month’s growth rate by comparing its closing balance to the prior month’s balance, treating deposits as positive and withdrawals as negative.; If the previous month’s balance is zero, the growth rate should be the current month’s balance multiplied by 100.; The calculation of growth rate must be performed for each customer, considering only the most recent month.",
    "route": "dependency_nxm_graph",
    "model": "local-gemma3-4b",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T10:57:57+00:00",
    "schema_fingerprint": "27492810c24891b6"
  },
  "validation": {
    "validated_at": "2026-09-30T10:57:57+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "customer_id",
      "month",
      "growth_rate"
    ],
    "row_count": 1,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
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
    ct.customer_id,
    strftime('%Y-%m', ct.txn_date) AS month,
    SUM(ct.txn_amount) * 1.0 / SUM(ct.txn_amount) OVER (PARTITION BY strftime('%Y-%m', ct.txn_date)) AS growth_rate
FROM customer_transactions ct
ORDER BY ct.customer_id, strftime('%Y-%m', ct.txn_date)
```

---
