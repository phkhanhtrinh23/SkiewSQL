# Skill graph — `education_business` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `hardware_dim_product`, `hardware_fact_sales_monthly` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each hardware product segment, compute the number of unique products sold in 2020 and the percentage change in that unique product count from 2020 to 2021; then return only the rows for year_

```sql
SELECT
  hd.segment,
  hm_2020.fiscal_year AS year,
  hm_2020.unique_products_2020,
  hm_2021.unique_products_2021,
  -- percentage change from 2020 to 2021 as (2021-2020)/2020
  CASE
    WHEN hm_2020.unique_products_2020 = 0 THEN NULL
    ELSE (CAST(hm_2021.unique_products_2021 AS REAL) - CAST(hm_2020.unique_products_2020 AS REAL)) / CAST(hm_2020.unique_products_2020 AS REAL)
  END AS pct_change_2020_to_2021
FROM hardware_dim_product AS hd
-- aggregate distinct product counts for 2020 by segment using hardware_fact_sales_monthly
LEFT JOIN (
  SELECT
    product_code,
    customer_code,
    sold_quantity,
    fiscal_year,
    product_code AS prod_code_2020
  FROM hardware_fact_sales_monthly
  WHERE fiscal_year = 2020
) AS sales_2020 ON sales_2020.product_code = hd.product_code
LEFT JOIN (
  SELECT
    product_code,
    fiscal_year,
    product_code AS prod_code_2021
  FROM hardware_fact_sales_monthly
  WHERE fiscal_year = 2021
) AS sales_2021 ON sales_2021.product_code = hd.product_code
-- compute per-segment distinct product counts for 2020 and 2021
LEFT JOIN (
  SELECT
    hd_inner.segment,
    COUNT(DISTINCT hm.product_code) AS unique_products_2020,
    2020 AS fiscal_year
  FROM hardware_dim_product hd_inner
  JOIN hardware_fact_sales_monthly hm ON hm.product_code = hd_inner.product_code
  WHERE hm.fiscal_year = 2020
  GROUP BY hd_inner.segment
) AS hm_2020 ON hm_2020.segment = hd.segment
LEFT JOIN (
  SELECT
    hd_inner.segment,
    COUNT(DISTINCT hm.product_code) AS unique_products_2021
  FROM hardware_dim_product hd_inner
  JOIN hardware_fact_sales_monthly hm ON hm.product_code = hd_inner.product_code
  WHERE hm.fiscal_year = 2021
  GROUP BY hd_inner.segment
) AS hm_2021 ON hm_2021.segment = hd.segment
WHERE hd.segment IS NOT NULL
```

---
