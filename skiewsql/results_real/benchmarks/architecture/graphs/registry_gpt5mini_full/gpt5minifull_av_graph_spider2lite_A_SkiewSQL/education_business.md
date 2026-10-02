# Skill graph — `education_business` (2 skills)

## Skill `product_segment_yearly_unique_product_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `segment`, `fiscal_year` (keyed) |
| status / version | active / v1 |
| skill id | sk_f6547dff828903a8 |
| output columns | `segment`, `fiscal_year`, `unique_product_count` |
| source tables | `hardware_dim_product`, `hardware_fact_sales_monthly` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per product segment and fiscal year, count of distinct products sold (unique product count) derived by joining product dimension to sales fact.

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
      "2021"
    ],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "hardware_dim_product",
      "hardware_fact_sales_monthly"
    ],
    "table_fingerprints": {
      "hardware_dim_product": "0e31cb51dc850d12",
      "hardware_fact_sales_monthly": "f08928d9e9c465aa"
    },
    "data_fingerprints": {},
    "db_id": "education_business",
    "question_id": "local058",
    "question": "Can you provide a list of hardware product segments along with their unique product counts for 2020 in the output, ordered by the highest percentage increase in unique fact sales products from 2020 to 2021?",
    "rewrite": "Task: Compute, for each hardware product segment, the number of unique products sold (unique product count) in 2020, and the percentage change in that unique product count from 2020 to 2021; return only segments that have data for 2020, and order the results by the percentage increase from 2020 to 2021 in descending order.\nRequired outputs: hardware product segment (segment identifier/name); unique product count for 2020 (integer); unique product count for 2021 (integer); percentage change from 2020 to 2021 ((2021_count - 2020_count) / 2020_count * 100; show sign and percent)\nFilters: include only rows for year = 2020 and year = 2021 when computing counts; consider unique products by whatever product identifier is available (count distinct products); exclude segments where the 2020 unique product count is zero or missing to avoid division by zero\nSort/limit: order by percentage change from 2020 to 2021 descending; no limit",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:55:57+00:00",
    "schema_fingerprint": "055b79cf780a8f69"
  },
  "validation": {
    "validated_at": "2026-10-01T00:56:02+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "segment",
      "fiscal_year",
      "unique_product_count"
    ],
    "row_count": 12,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "hardware_dim_product.product_code=hardware_fact_sales_monthly.product_code",
        "left_unique": true,
        "right_unique": false,
        "relationship": "one_to_many"
      }
    ],
    "tests": [
      {
        "purpose": "View has the declared grain: no duplicate rows for the (segment, fiscal_year) key",
        "sql": "SELECT COUNT(*) FROM product_segment_yearly_unique_product_counts t JOIN (SELECT segment, fiscal_year, COUNT(*) AS c FROM product_segment_yearly_unique_product_counts GROUP BY segment, fiscal_year HAVING c > 1) dup ON t.segment = dup.segment AND t.fiscal_year = dup.fiscal_year",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "unique_product_count equals the distinct count of products from the base tables for that (segment, fiscal_year)",
        "sql": "SELECT COUNT(*) FROM product_segment_yearly_unique_product_counts v LEFT JOIN (SELECT p.segment AS segment, s.fiscal_year AS fiscal_year, COUNT(DISTINCT p.product_code) AS expected_count FROM hardware_dim_product p JOIN hardware_fact_sales_monthly s ON p.product_code = s.product_code GROUP BY p.segment, s.fiscal_year) b ON v.segment = b.segment AND v.fiscal_year = b.fiscal_year WHERE (v.unique_product_count IS NOT b.expected_count) OR (v.unique_product_count IS NULL AND b.expected_count IS NOT NULL) OR (v.unique_product_count IS NOT NULL AND b.expected_count IS NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's key columns are non-NULL (segment, fiscal_year)",
        "sql": "SELECT COUNT(*) FROM product_segment_yearly_unique_product_counts WHERE segment IS NULL OR fiscal_year IS NULL",
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
SELECT p.segment AS segment, s.fiscal_year AS fiscal_year, COUNT(DISTINCT p.product_code) AS unique_product_count FROM hardware_dim_product p JOIN hardware_fact_sales_monthly s ON p.product_code = s.product_code GROUP BY p.segment, s.fiscal_year
```

---

## Skill `web_orders_by_region_and_rep_sales`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `region_id`, `region_name`, `rep_id`, `rep_name` (keyed) |
| status / version | active / v1 |
| skill id | sk_a2febfbc8fb69611 |
| output columns | `region_id`, `region_name`, `rep_id`, `rep_name`, `rep_order_count`, `rep_total_sales`, `region_total_sales`, `region_order_count` |
| source tables | `web_orders`, `web_accounts`, `web_sales_reps`, `web_region` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-region and per-sales-representative aggregates for web orders: order counts and sales sums for each region and for each rep (with region and rep identifiers to join/filter further).

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
      "'web'",
      "channel filters",
      "ORDER BY r.name ASC"
    ],
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "web_orders",
      "web_accounts",
      "web_sales_reps",
      "web_region"
    ],
    "table_fingerprints": {
      "web_orders": "deba3d8be0acf568",
      "web_accounts": "93c8a94899b7f400",
      "web_sales_reps": "47073fb3c645d822",
      "web_region": "fb894d2cd8733e26"
    },
    "data_fingerprints": {},
    "db_id": "education_business",
    "question_id": "local114",
    "question": "Provide a detailed web sales report for each region, including the number of orders, total sales amount, and the name and sales amount of all sales representatives who achieved the highest total sales amount in that region (include all representatives in case of a tie).",
    "rewrite": "Task: For each region, compute a web sales report that shows the region name, the number of orders in that region, the total sales amount in that region, and for every sales representative in that region who attained the highest total sales amount in that region, include that representative's name and that representative's total sales amount (if multiple reps tie for highest include each).\nRequired outputs: region (region name); order_count (number of orders in the region); region_total_sales (sum of sales amounts for all orders in the region); top_rep_name (name of a sales representative who has the highest total sales amount in that region); top_rep_sales (that representative's total sales amount in the region)\nFilters: Only include rows grouped by region that have at least one web order (i.e., regions with zero orders should be excluded); Consider only sales that are web orders (explicitly restrict to web channel / web sales); When multiple sales representatives tie for the highest total sales amount within a region, include one output row for each tied representative\nSort/limit: Order results by region name ascending; no row limit",
    "route": "nx1",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-10-01T00:56:50+00:00",
    "schema_fingerprint": "055b79cf780a8f69"
  },
  "validation": {
    "validated_at": "2026-10-01T00:56:53+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "region_id",
      "region_name",
      "rep_id",
      "rep_name",
      "rep_order_count",
      "rep_total_sales",
      "region_total_sales",
      "region_order_count"
    ],
    "row_count": 50,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "web_orders.account_id=web_accounts.id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      },
      {
        "join": "web_accounts.sales_rep_id=web_sales_reps.id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      },
      {
        "join": "web_sales_reps.region_id=web_region.id",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (region_id, region_name, rep_id, rep_name).",
        "sql": "SELECT COUNT(*) FROM (SELECT region_id, region_name, rep_id, rep_name, COUNT(*) AS cnt FROM web_orders_by_region_and_rep_sales GROUP BY region_id, region_name, rep_id, rep_name HAVING cnt > 1) AS t",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "rep_order_count matches count of orders for that rep (joined through accounts -> sales_reps).",
        "sql": "SELECT COUNT(*) FROM web_orders_by_region_and_rep_sales v LEFT JOIN web_sales_reps sr ON v.rep_id = sr.id LEFT JOIN web_accounts a ON sr.id = a.sales_rep_id LEFT JOIN web_orders o ON o.account_id = a.id WHERE (v.rep_order_count IS NULL AND EXISTS (SELECT 1 FROM web_orders o2 JOIN web_accounts a2 ON o2.account_id = a2.id WHERE a2.sales_rep_id = v.rep_id) ) OR (v.rep_order_count IS NOT NULL AND v.rep_order_count != (SELECT COUNT(o3.id) FROM web_orders o3 JOIN web_accounts a3 ON o3.account_id = a3.id WHERE a3.sales_rep_id = v.rep_id))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "region_total_sales equals sum of rep_total_sales over reps in the same region (window consistency).",
        "sql": "SELECT COUNT(*) FROM web_orders_by_region_and_rep_sales v WHERE v.region_total_sales IS NULL OR v.region_total_sales != (SELECT SUM(v2.rep_total_sales) FROM web_orders_by_region_and_rep_sales v2 WHERE v2.region_id = v.region_id)",
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
  sr.region_id,
  r.name AS region_name,
  sr.id AS rep_id,
  sr.name AS rep_name,
  COUNT(o.id) AS rep_order_count,
  SUM(o.total_amt_usd) AS rep_total_sales,
  SUM(SUM(o.total_amt_usd)) OVER (PARTITION BY sr.region_id) AS region_total_sales,
  SUM(COUNT(o.id)) OVER (PARTITION BY sr.region_id) AS region_order_count
FROM web_orders o
JOIN web_accounts a ON o.account_id = a.id
JOIN web_sales_reps sr ON a.sales_rep_id = sr.id
JOIN web_region r ON sr.region_id = r.id
GROUP BY sr.region_id, r.name, sr.id, sr.name
```

---
