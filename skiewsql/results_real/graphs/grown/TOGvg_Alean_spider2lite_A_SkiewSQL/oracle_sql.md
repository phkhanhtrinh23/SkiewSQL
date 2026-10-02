# Skill graph — `oracle_sql` (2 skills)

**Skill `leaf_items_per_package`** — category `REC`

| field | value |
|---|---|
| grain (one row per) | `final_package_key`, `leaf_item_id` |
| output columns | `final_package_key`, `leaf_item_id`, `quantity` |
| source tables | `packaging`, `packaging_relations` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `package_quantity_sums` |
| validated_on | — |
| counter_examples | 0 |

_recursively traverses the packaging hierarchy to isolate only the bottom-most (leaf) items, preserving the final packaging combination identifier and each leaf item's quantity._

```sql
WITH RECURSIVE pkg_hierarchy AS (
    SELECT p.id AS top_id, p.id AS curr_id
    FROM packaging p
    WHERE p.id NOT IN (SELECT packaging_id FROM packaging_relations)
    UNION ALL
    SELECT ph.top_id, pr.contains_id
    FROM pkg_hierarchy ph
    JOIN packaging_relations pr ON ph.curr_id = pr.packaging_id
),
leaf_items AS (
    SELECT ph.top_id, ph.curr_id AS leaf_item_id, pr.qty AS quantity
    FROM pkg_hierarchy ph
    JOIN packaging_relations pr ON ph.curr_id = pr.contains_id
    WHERE ph.curr_id NOT IN (SELECT packaging_id FROM packaging_relations)
)
SELECT top_id AS final_package_key, leaf_item_id, quantity
FROM leaf_items
```

---

**Skill `package_quantity_sums`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `final_package_key` |
| output columns | `final_package_key`, `total_leaf_quantity` |
| source tables | `leaf_items_per_package` |
| depends_on (builds on) | `leaf_items_per_package` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_aggregates the resolved leaf items by final packaging combination to compute the total summed quantity for each combination._

```sql
SELECT final_package_key, SUM(quantity) AS total_leaf_quantity
FROM leaf_items_per_package
GROUP BY final_package_key
```

---
