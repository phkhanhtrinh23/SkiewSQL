# Skill graph — `education_business` (5 skills)

## Skill `product_to_hardware_segment`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `product_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_5a24efab99ff7b6e |
| output columns | `product_id`, `segment_id`, `segment_name` |
| source tables | `hardware_dim_product` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `sales_2021_hardware_lines` |

### Description

Mapping that assigns each product to its hardware product segment (identifier or name). One row per product with its segment identifier/name. This relation is used to attribute sales facts to segments.

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
      "want_name": "product_to_hardware_segment",
      "category": "JOIN",
      "required_outputs": [
        "product_id",
        "segment_id",
        "segment_name"
      ],
      "required_grain": [
        "product_id"
      ],
      "required_filters": {},
      "text": "Mapping that assigns each product to its hardware product segment (identifier or name). One row per product with its segment identifier/name. This relation is used to attribute sales facts to segments.",
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
      "hardware_dim_product"
    ],
    "table_fingerprints": {
      "hardware_dim_product": "0e31cb51dc850d12"
    },
    "data_fingerprints": {
      "hardware_dim_product": "397:397"
    },
    "db_id": "education_business",
    "question_id": "local058",
    "question": "Can you provide a list of hardware product segments along with their unique product counts for 2020 in the output, ordered by the highest percentage increase in unique fact sales products from 2020 to 2021?",
    "rewrite": "Task: For each hardware product segment, compute the number of unique products that have sales facts in 2020, and return those segments and their 2020 unique-product counts ordered by the highest percentage increase in unique products from 2020 to 2021.\nRequired outputs: hardware product segment identifier or name; unique_product_count_2020 (integer): the count of distinct products in that segment that appear in sales facts dated in calendar year 2020; unique_product_count_2021 (integer): the count of distinct products in that segment that appear in sales facts dated in calendar year 2021; percent_change_2020_to_2021 (numeric): percent change computed as ((unique_product_count_2021 - unique_product_count_2020) / NULLIF(unique_product_count_2020,0)) * 100; if unique_product_count_2020 is 0, define percent_change as NULL or a special indicator\nFilters: include only sales facts whose sale date falls within calendar year 2020 for the 2020 counts and within calendar year 2021 for the 2021 counts; consider a product as belonging to a hardware product segment according to the product-to-segment relationship in the schema; count distinct products per segment (unique products) based on product identifier; exclude segments that have no sales facts in both 2020 and 2021 only if desired; otherwise include segments with zero counts as appropriate\nSort/limit: order rows by percent_change_2020_to_2021 in descending order (highest percentage increase first); no row limit",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:28:21+00:00",
    "schema_fingerprint": "055b79cf780a8f69"
  },
  "validation": {
    "validated_at": "2026-09-30T15:28:23+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "product_id",
      "segment_id",
      "segment_name"
    ],
    "row_count": 397,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View has one row per product_id (no duplicate product_id)",
        "sql": "SELECT COUNT(*) FROM product_to_hardware_segment v JOIN (SELECT product_code FROM hardware_dim_product) b ON 1=1 WHERE (SELECT COUNT(*) FROM product_to_hardware_segment v2 WHERE v2.product_id = v.product_id) > 1",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in view corresponds to an existing product in base table (no dangling product_id)",
        "sql": "SELECT COUNT(*) FROM product_to_hardware_segment v LEFT JOIN hardware_dim_product p ON v.product_id = p.product_code WHERE p.product_code IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "segment_id and segment_name are not NULL for any product (keys/attributes present)",
        "sql": "SELECT COUNT(*) FROM product_to_hardware_segment v WHERE v.segment_id IS NULL OR v.segment_name IS NULL",
        "result": "pass",
        "violations": 0
      }
    ],
    "passed": true
  },
  "evidence": {
    "included": 1,
    "referenced": 1,
    "executed": 1,
    "last_used": "local059"
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
  product_code AS product_id,
  segment AS segment_id,
  segment AS segment_name
FROM hardware_dim_product
```

---

## Skill `unique_products_per_segment_per_year`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `segment_name`, `sale_year` (keyed) |
| status / version | active / v1 |
| skill id | sk_f4c703678c87f2e7 |
| output columns | `segment_id`, `segment_name`, `sale_year`, `unique_product_count` |
| source tables | `hardware_fact_sales_monthly`, `hardware_dim_product` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

For each hardware product segment and calendar year, counts the distinct products that have sales facts in that year (one row per segment-year with segment id/name and unique product count).

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
      "hardware_fact_sales_monthly",
      "hardware_dim_product"
    ],
    "table_fingerprints": {
      "hardware_fact_sales_monthly": "f08928d9e9c465aa",
      "hardware_dim_product": "0e31cb51dc850d12"
    },
    "data_fingerprints": {},
    "db_id": "education_business",
    "question_id": "local058",
    "question": "Can you provide a list of hardware product segments along with their unique product counts for 2020 in the output, ordered by the highest percentage increase in unique fact sales products from 2020 to 2021?",
    "rewrite": "Task: For each hardware product segment, compute the number of unique products that have sales facts in 2020, and return those segments and their 2020 unique-product counts ordered by the highest percentage increase in unique products from 2020 to 2021.\nRequired outputs: hardware product segment identifier or name; unique_product_count_2020 (integer): the count of distinct products in that segment that appear in sales facts dated in calendar year 2020; unique_product_count_2021 (integer): the count of distinct products in that segment that appear in sales facts dated in calendar year 2021; percent_change_2020_to_2021 (numeric): percent change computed as ((unique_product_count_2021 - unique_product_count_2020) / NULLIF(unique_product_count_2020,0)) * 100; if unique_product_count_2020 is 0, define percent_change as NULL or a special indicator\nFilters: include only sales facts whose sale date falls within calendar year 2020 for the 2020 counts and within calendar year 2021 for the 2021 counts; consider a product as belonging to a hardware product segment according to the product-to-segment relationship in the schema; count distinct products per segment (unique products) based on product identifier; exclude segments that have no sales facts in both 2020 and 2021 only if desired; otherwise include segments with zero counts as appropriate\nSort/limit: order rows by percent_change_2020_to_2021 in descending order (highest percentage increase first); no row limit",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:28:26+00:00",
    "schema_fingerprint": "055b79cf780a8f69"
  },
  "validation": {
    "validated_at": "2026-09-30T15:28:31+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "segment_id",
      "segment_name",
      "sale_year",
      "unique_product_count"
    ],
    "row_count": 18,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [
      {
        "join": "hardware_fact_sales_monthly.product_code=hardware_dim_product.product_code",
        "left_unique": false,
        "right_unique": true,
        "relationship": "many_to_one"
      }
    ],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (segment_name, sale_year)",
        "sql": "SELECT COUNT(*) FROM (SELECT segment_name, sale_year, COUNT(*) AS cnt FROM unique_products_per_segment_per_year GROUP BY segment_name, sale_year HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "unique_product_count matches COUNT(DISTINCT s.product_code) recomputed from base tables per segment and year",
        "sql": "SELECT COUNT(*) FROM (SELECT v.segment_name, v.sale_year FROM unique_products_per_segment_per_year v LEFT JOIN (SELECT p.segment AS segment_name, CAST(strftime('%Y', s.date) AS INTEGER) AS sale_year, COUNT(DISTINCT s.product_code) AS expected_count FROM hardware_fact_sales_monthly s JOIN hardware_dim_product p ON s.product_code = p.product_code GROUP BY p.segment, CAST(strftime('%Y', s.date) AS INTEGER)) b ON v.segment_name = b.segment_name AND v.sale_year = b.sale_year WHERE (v.unique_product_count IS NOT b.expected_count) OR (b.expected_count IS NULL) OR (v.unique_product_count IS NULL))",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row in the view corresponds to at least one underlying sale (no segment-year with zero facts)",
        "sql": "SELECT COUNT(*) FROM unique_products_per_segment_per_year v WHERE NOT EXISTS (SELECT 1 FROM hardware_fact_sales_monthly s JOIN hardware_dim_product p ON s.product_code = p.product_code WHERE p.segment = v.segment_name AND CAST(strftime('%Y', s.date) AS INTEGER) = v.sale_year)",
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
SELECT p.segment AS segment_id,
       p.segment AS segment_name,
       CAST(strftime('%Y', s.date) AS INTEGER) AS sale_year,
       COUNT(DISTINCT s.product_code) AS unique_product_count
FROM hardware_fact_sales_monthly s
JOIN hardware_dim_product p
  ON s.product_code = p.product_code
GROUP BY p.segment, CAST(strftime('%Y', s.date) AS INTEGER)
```

---

## Skill `sales_2021_hardware_lines`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `sale_id`, `product_id`, `division_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_1b7d94f38983ff71 |
| output columns | `sale_id`, `sale_date`, `product_id`, `division_id`, `quantity` |
| source tables | `hardware_fact_sales_monthly` |
| depends_on (builds on) | `product_to_hardware_segment` |
| depended-on by (builds on this) | — |

### Description

All sales line items from the calendar year 2021 that refer to products classified as hardware, with the product, division (the division that sold the product or the division of the selling location/customer as appropriate), sale date, and quantity sold for the line.

### Semantic filters

```json
{
  "date_range": "sale_date between 2021-01-01 and 2021-12-31 inclusive",
  "product_type": "product classified as hardware",
  "date": ">=2021-01-01;<=2021-12-31"
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
      "want_name": "sales_2021_hardware_lines",
      "category": "SEL",
      "required_outputs": [
        "sale_id",
        "sale_date",
        "product_id",
        "division_id",
        "quantity"
      ],
      "required_grain": [
        "sale_id",
        "product_id",
        "division_id"
      ],
      "required_filters": {
        "date_range": "sale_date between 2021-01-01 and 2021-12-31 inclusive",
        "product_type": "product classified as hardware"
      },
      "text": "All sales line items from the calendar year 2021 that refer to products classified as hardware, with the product, division (the division that sold the product or the division of the selling location/customer as appropriate), sale date, and quantity sold for the line.",
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
      "hardware_fact_sales_monthly",
      "hardware_dim_product"
    ],
    "table_fingerprints": {
      "hardware_fact_sales_monthly": "f08928d9e9c465aa",
      "hardware_dim_product": "0e31cb51dc850d12"
    },
    "data_fingerprints": {
      "hardware_fact_sales_monthly": "971631:971631",
      "hardware_dim_product": "397:397"
    },
    "db_id": "education_business",
    "question_id": "local059",
    "question": "For the calendar year 2021, what is the overall average quantity sold of the top three best-selling hardware products (by total quantity sold) in each division?",
    "rewrite": "Task: For calendar year 2021, compute for each division the overall average quantity sold of that division's top three best-selling hardware products, where top three are determined by total quantity sold during 2021 and 'hardware products' means items classified as hardware.\nRequired outputs: division (division identifier or name); average_quantity_sold_top_3_hardware_products_2021 (numeric) -- the overall average quantity sold across the top three hardware products for that division during 2021\nFilters: only include sales occurring in the calendar year 2021 (date between 2021-01-01 and 2021-12-31 inclusive); only consider products classified as hardware; determine top three products per division by total quantity sold in 2021 within that division; if a division has fewer than three hardware products sold in 2021, compute the average over the available hardware products (do not invent rows)\nSort/limit: order results by division ascending; no row limit",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:29:09+00:00",
    "schema_fingerprint": "055b79cf780a8f69"
  },
  "validation": {
    "validated_at": "2026-09-30T15:29:14+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "sale_id",
      "sale_date",
      "product_id",
      "division_id",
      "quantity"
    ],
    "row_count": 403453,
    "grain_check": "pass",
    "filter_checks": {
      "date_range": "n/a",
      "product_type": "n/a",
      "date": "n/a"
    },
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate rows at the declared grain (sale_id, product_id, division_id). Count rows in the view that have the same (sale_id, product_id, division_id) appearing more than once.",
        "sql": "SELECT COUNT(*) FROM (SELECT sale_id, product_id, division_id, COUNT(*) AS c FROM sales_2021_hardware_lines GROUP BY sale_id, product_id, division_id HAVING c > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All rows fall inside the intrinsic date range (sale_date between 2021-01-01 and 2021-12-31 inclusive). Count rows in the view whose sale_date is outside that inclusive range or NULL.",
        "sql": "SELECT COUNT(*) FROM sales_2021_hardware_lines WHERE sale_date IS NULL OR date(sale_date) < date('2021-01-01') OR date(sale_date) > date('2021-12-31')",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every product_id in the view is classified as hardware according to product_to_hardware_segment (i.e., product exists in that mapping). Count rows whose product_id is not present in product_to_hardwar",
        "sql": "SELECT COUNT(*) FROM sales_2021_hardware_lines v WHERE NOT EXISTS (SELECT 1 FROM product_to_hardware_segment m WHERE m.product_id = v.product_id)",
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
  rowid AS sale_id,
  date AS sale_date,
  product_code AS product_id,
  customer_code AS division_id,
  sold_quantity AS quantity
FROM hardware_fact_sales_monthly
WHERE date BETWEEN '2021-01-01' AND '2021-12-31'
  AND product_code IN (
    SELECT product_id FROM product_to_hardware_segment
  )
```

---

## Skill `faculty_rows`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `faculty_id` (keyed) |
| status / version | active / v1 |
| skill id | sk_1dcef32671a73bca |
| output columns | `faculty_id`, `rank`, `first_name`, `last_name`, `salary` |
| source tables | `university_faculty` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `avg_salary_per_rank` |

### Description

All faculty rows with the columns needed: rank, faculty identifier, first name, last name, and salary (no aggregation). One row per faculty member.

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
      "want_name": "faculty_rows",
      "category": "SEL",
      "required_outputs": [
        "faculty_id",
        "rank",
        "first_name",
        "last_name",
        "salary"
      ],
      "required_grain": [
        "faculty_id"
      ],
      "required_filters": {},
      "text": "All faculty rows with the columns needed: rank, faculty identifier, first name, last name, and salary (no aggregation). One row per faculty member.",
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
      "university_faculty"
    ],
    "table_fingerprints": {
      "university_faculty": "ee0364b1e82bae8f"
    },
    "data_fingerprints": {
      "university_faculty": "8:8"
    },
    "db_id": "education_business",
    "question_id": "local163",
    "question": "Which university faculty members' salaries are closest to the average salary for their respective ranks? Please provide the ranks, first names, last names, and salaries.university",
    "rewrite": "Task: For each faculty rank, find the faculty member(s) whose salary is closest to the average salary for that rank; return their rank, first name, last name, and salary.\nRequired outputs: rank; first name; last name; salary\nFilters: compute average salary per rank across all faculty of that rank; for each faculty row, compute absolute difference between that faculty's salary and their rank's average; include only those faculty rows whose difference equals the minimum difference for that rank (i.e., closest to the rank average)\nSort/limit: order results by rank (ascending) and then by last name (ascending); no limit",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:30:26+00:00",
    "schema_fingerprint": "055b79cf780a8f69"
  },
  "validation": {
    "validated_at": "2026-09-30T15:30:29+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "faculty_id",
      "rank",
      "first_name",
      "last_name",
      "salary"
    ],
    "row_count": 8,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "No duplicate faculty_id (one row per faculty member / correct grain)",
        "sql": "SELECT COUNT(*) FROM (SELECT faculty_id, COUNT(*) AS cnt FROM faculty_rows GROUP BY faculty_id HAVING cnt > 1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "All output columns are not NULL for each row (required columns present)",
        "sql": "SELECT COUNT(*) FROM faculty_rows WHERE faculty_id IS NULL OR rank IS NULL OR first_name IS NULL OR last_name IS NULL OR salary IS NULL",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Each row matches the source table (values reconcile with university_faculty)",
        "sql": "SELECT COUNT(*) FROM faculty_rows fr LEFT JOIN university_faculty uf ON fr.faculty_id = uf.FacNo WHERE uf.FacNo IS NULL OR fr.rank != uf.FacRank OR fr.first_name != uf.FacFirstName OR fr.last_name != uf.FacLastName OR fr.salary != uf.FacSalary",
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
  FacNo AS faculty_id,
  FacRank AS rank,
  FacFirstName AS first_name,
  FacLastName AS last_name,
  FacSalary AS salary
FROM university_faculty
```

---

## Skill `avg_salary_per_rank`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `rank` (keyed) |
| status / version | active / v1 |
| skill id | sk_73245e5ca41c60b1 |
| output columns | `rank`, `avg_salary` |
| source tables | — |
| depends_on (builds on) | `faculty_rows` |
| depended-on by (builds on this) | — |

### Description

Compute the average salary for each faculty rank. One row per rank with the average salary.

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
      "want_name": "avg_salary_per_rank",
      "category": "AGG",
      "required_outputs": [
        "rank",
        "avg_salary"
      ],
      "required_grain": [
        "rank"
      ],
      "required_filters": {},
      "text": "Compute the average salary for each faculty rank. One row per rank with the average salary.",
      "source_tables": [],
      "depends_on": [
        "faculty_rows"
      ],
      "join_keys": [],
      "relationship": "aggregate_input",
      "may_read_base_tables": false,
      "holistic": false,
      "inherited_filters": {}
    },
    "contract_version": 2,
    "grain_basis": "group_by",
    "lineage": [
      "university_faculty"
    ],
    "table_fingerprints": {
      "university_faculty": "ee0364b1e82bae8f"
    },
    "data_fingerprints": {},
    "db_id": "education_business",
    "question_id": "local163",
    "question": "Which university faculty members' salaries are closest to the average salary for their respective ranks? Please provide the ranks, first names, last names, and salaries.university",
    "rewrite": "Task: For each faculty rank, find the faculty member(s) whose salary is closest to the average salary for that rank; return their rank, first name, last name, and salary.\nRequired outputs: rank; first name; last name; salary\nFilters: compute average salary per rank across all faculty of that rank; for each faculty row, compute absolute difference between that faculty's salary and their rank's average; include only those faculty rows whose difference equals the minimum difference for that rank (i.e., closest to the rank average)\nSort/limit: order results by rank (ascending) and then by last name (ascending); no limit",
    "route": "dependency_nxm_graph",
    "model": "gpt-5-mini",
    "prompt_version": "180ca50c3a",
    "created_at": "2026-09-30T15:30:29+00:00",
    "schema_fingerprint": "055b79cf780a8f69"
  },
  "validation": {
    "validated_at": "2026-09-30T15:30:32+00:00",
    "contract_version": 2,
    "failures": [],
    "executed": true,
    "columns": [
      "rank",
      "avg_salary"
    ],
    "row_count": 3,
    "grain_check": "pass",
    "filter_checks": {},
    "join_cardinality": [],
    "tests": [
      {
        "purpose": "View has one row per distinct rank (no duplicate rank rows)",
        "sql": "SELECT COUNT(*) FROM (SELECT \"rank\" FROM avg_salary_per_rank GROUP BY \"rank\" HAVING COUNT(*)>1)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "Every row's avg_salary equals AVG(salary) computed from base table for that rank",
        "sql": "SELECT COUNT(*) FROM avg_salary_per_rank v WHERE ABS(v.avg_salary - (SELECT AVG(fr.salary) FROM faculty_rows fr WHERE fr.rank = v.rank)) > 1e-9 OR (v.avg_salary IS NULL AND (SELECT AVG(fr.salary) FROM faculty_rows fr WHERE fr.rank = v.rank) IS NOT NULL) OR (v.avg_salary IS NOT NULL AND (SELECT AVG(fr.salary) FROM faculty_rows fr WHERE fr.rank = v.rank) IS NULL)",
        "result": "pass",
        "violations": 0
      },
      {
        "purpose": "No NULLs in the key column rank",
        "sql": "SELECT COUNT(*) FROM avg_salary_per_rank WHERE \"rank\" IS NULL",
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
  fr.rank AS "rank",
  AVG(fr.salary) AS "avg_salary"
FROM faculty_rows AS fr
GROUP BY fr.rank
```

---
