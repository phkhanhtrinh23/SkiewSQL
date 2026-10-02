# Skill graph — `oracle_sql` (2 skills)

**Skill `leaf_items_per_package`** — category `REC`

| field | value |
|---|---|
| grain (one row per) | `final_package_id`, `leaf_item_id` |
| output columns | `final_package_id`, `leaf_item_id`, `quantity` |
| source tables | `packaging`, `packaging_relations` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `package_quantity_sums` |
| validated_on | — |
| counter_examples | 0 |

_recursively traverses packaging hierarchies to isolate only the bottom-most items for each top-level combination_

```sql
WITH RECURSIVE pkg_hierarchy AS (
    SELECT p.id AS top_id, p.id AS current_id
    FROM packaging p
    WHERE NOT EXISTS (SELECT 1 FROM packaging_relations pr WHERE pr.contains_id = p.id)
    UNION ALL
    SELECT ph.top_id, pr.contains_id
    FROM pkg_hierarchy ph
    JOIN packaging_relations pr ON ph.current_id = pr.packaging_id
)
SELECT top_id AS final_package_id, current_id AS leaf_item_id, 1 AS quantity
FROM pkg_hierarchy
WHERE NOT EXISTS (SELECT 1 FROM packaging_relations pr WHERE pr.packaging_id = current_id)
```

---

**Skill `package_quantity_sums`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `final_package_id` |
| output columns | `final_package_id`, `total_quantity` |
| source tables | `leaf_items_per_package` |
| depends_on (builds on) | `leaf_items_per_package` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_aggregates the quantities of leaf items to compute the total quantity per final packaging combination_

```sql
SELECT final_package_id, SUM(quantity) AS total_quantity
FROM leaf_items_per_package
GROUP BY final_package_id
```

---
