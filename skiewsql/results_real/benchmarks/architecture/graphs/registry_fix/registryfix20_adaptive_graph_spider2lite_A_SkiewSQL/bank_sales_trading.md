# Skill graph — `bank_sales_trading` (2 skills)

## Skill `customer_monthly_balances`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month` (keyed) |
| status / version | active / v1 |
| skill id | sk_e2d21b3b77168272 |
| output columns | `customer_id`, `month`, `balance` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

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
    "question_id": "local074",
    "question": "Please generate a summary of the closing balances at the end of each month for each customer transactions, show the monthly changes and monthly cumulative bank account balances. Ensure that even if a customer has no account activity in a given month, the balance for that month is still included in the output.",
    "rewrite": "Task: Generate a monthly summary of customer bank account balances, including monthly changes and cumulative balances, for all customers, even those with no transactions in a given month.\nRequired outputs: Monthly bank account balance for each customer; Monthly change in bank account balance (difference between the current and previous month's balance); Cumulative bank account balance (running total of balances over time) for each customer\nFilters: All customers must be included in the output.; For each customer, include data for every month in the dataset.; If a customer has no transactions in a specific month, the monthly balance for that month should still be included, defaulting to a balance of 0 for that month.",
    "route": "dependency_nxm_graph",
    "model": "local-gemma3-4b",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T14:40:29+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-09-30T14:40:29+00:00",
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
  "evidence": {
    "included": 1
  }
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
    STRFTIME('%Y-%m', ct1.txn_date) AS month,
    SUM(ct1.txn_amount) AS balance
FROM customer_transactions AS ct1
GROUP BY ct1.customer_id,
STRFTIME('%Y-%m', ct1.txn_date)
```

---

## Skill `aggregate_results`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | — (scalar) |
| status / version | active / v1 |
| skill id | sk_a991de129d060ac2 |
| output columns | `attribute_type`, `max_negative_change` |
| source tables | `bitcoin_prices` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Calculate the maximum negative average percentage change across all attribute types.

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
      "want_name": "aggregate_results",
      "category": "NORM",
      "required_outputs": [
        "attribute_type",
        "max_negative_change"
      ],
      "required_grain": [
        "attribute_type",
        "max_negative_change"
      ],
      "required_filters": {},
      "text": "Calculate the maximum negative average percentage change across all attribute types.",
      "source_tables": [],
      "depends_on": [],
      "join_keys": [],
      "relationship": "aggregate_input",
      "may_read_base_tables": true,
      "holistic": false,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "scalar_aggregate",
    "lineage": [
      "bitcoin_prices"
    ],
    "table_fingerprints": {
      "bitcoin_prices": "2a38b4c2d0a75721"
    },
    "data_fingerprints": {},
    "db_id": "bank_sales_trading",
    "question_id": "local302",
    "question": "Analyze the average percentage change in sales between the 12 weeks before and after June 15, 2020, for each attribute type: region, platform, age band, demographic, and customer type. For each attribute type, calculate the average percentage change in sales across all its attribute values. Identify the attribute type with the highest negative impact on sales and provide its average percentage change in sales.",
    "rewrite": "Task: Calculate the average percentage change in sales for each attribute type (region, platform, age band, demographic, and customer type) over a 12-week window before and after June 15, 2020, and identify the attribute type with the greatest negative average percentage change.\nRequired outputs: The average percentage change in sales for each attribute type.; The attribute type with the highest negative average percentage change in sales.\nFilters: Consider a time window of 12 weeks before and 12 weeks after June 15, 2020.; Calculate the percentage change in sales for each attribute type across all its distinct attribute values within the specified time window.; Specifically, for each attribute type (region, platform, age band, demographic, and customer type), determine the average percentage change in sales across all values within that attribute type.",
    "route": "dependency_nxm_graph",
    "model": "local-gemma3-4b",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T14:44:50+00:00",
    "schema_fingerprint": "9004702d36a964ec"
  },
  "validation": {
    "validated_at": "2026-09-30T14:44:50+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "attribute_type",
      "max_negative_change"
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
    'bitcoin_prices' AS attribute_type,
    MAX(CASE WHEN change LIKE '-%' THEN CAST(SUBSTR(change, 1, LENGTH(change) - 1) AS REAL) ELSE NULL END) AS max_negative_change
FROM bitcoin_prices
```

---
