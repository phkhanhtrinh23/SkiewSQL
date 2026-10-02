# Skill graph — `education_business` (2 skills)

**Skill `unique_products_per_segment_year`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `segment`, `fiscal_year` |
| output columns | `hardware_segment`, `year`, `unique_product_count` |
| source tables | `hardware_dim_product`, `hardware_fact_sales_monthly` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `segment_yearly_metrics` |
| validated_on | — |
| counter_examples | 0 |

_distinct product counts grouped by hardware segment and year_

```sql
SELECT p.segment AS hardware_segment, s.fiscal_year AS year, COUNT(DISTINCT p.product_code) AS unique_product_count
FROM hardware_dim_product p
JOIN hardware_fact_sales_monthly s ON p.product_code = s.product_code
GROUP BY p.segment, s.fiscal_year
```

---

**Skill `segment_yearly_metrics`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `hardware_segment` |
| output columns | `hardware_segment`, `unique_product_count_2020`, `percentage_increase_2020_to_2021` |
| source tables | `unique_products_per_segment_year` |
| depends_on (builds on) | `unique_products_per_segment_year` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_joins 2020 and 2021 counts per segment to compute percentage increase, filters for segments with both years, and orders by increase descending_

```sql
SELECT 
    y2020.hardware_segment,
    y2020.unique_product_count AS unique_product_count_2020,
    CASE 
        WHEN y2021.unique_product_count IS NOT NULL 
        THEN ROUND((y2021.unique_product_count - y2020.unique_product_count) * 100.0 / y2020.unique_product_count, 2)
        ELSE NULL 
    END AS percentage_increase_2020_to_2021
FROM unique_products_per_segment_year y2020
JOIN unique_products_per_segment_year y2021 
    ON y2020.hardware_segment = y2021.hardware_segment
WHERE y2020.year = 2020 AND y2021.year = 2021
```

---
