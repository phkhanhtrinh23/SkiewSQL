# Skill graph — `education_business` (2 skills)

**Skill `unique_products_per_segment_year`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `segment`, `fiscal_year` |
| output columns | `segment`, `year`, `unique_product_count` |
| source tables | `hardware_fact_sales_monthly`, `hardware_dim_product` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `segment_growth_metrics` |
| validated_on | — |
| counter_examples | 0 |

_distinct product counts grouped by segment and year_

```sql
SELECT h.segment, f.fiscal_year AS year, COUNT(DISTINCT f.product_code) AS unique_product_count FROM hardware_fact_sales_monthly f JOIN hardware_dim_product h ON f.product_code = h.product_code GROUP BY h.segment, f.fiscal_year
```

---

**Skill `segment_growth_metrics`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `segment` |
| output columns | `segment`, `unique_product_count_2020`, `percentage_increase_2020_to_2021` |
| source tables | `unique_products_per_segment_year` |
| depends_on (builds on) | `unique_products_per_segment_year` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_join 2020 and 2021 counts per segment to compute percentage increase_

```sql
SELECT p20.segment, p20.unique_product_count AS unique_product_count_2020, CASE WHEN p20.unique_product_count = 0 THEN NULL ELSE ((p21.unique_product_count - p20.unique_product_count) * 100.0 / p20.unique_product_count) END AS percentage_increase_2020_to_2021 FROM unique_products_per_segment_year p20 LEFT JOIN unique_products_per_segment_year p21 ON p20.segment = p21.segment AND p20.year = 2020 AND p21.year = 2021 WHERE p20.year = 2020
```

---
