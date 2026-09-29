# Skill graph — `oracle_sql` (32 skills)

**Skill `final_packaging_combinations`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `final_combination_id` |
| output columns | `final_combination_id` |
| source tables | `packaging_relations` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `expanded_leaf_quantities` |
| validated_on | — |
| counter_examples | 0 |

_Select the set of all final packaging combination identifiers present in the dataset (one row per final combination). This identifies every combination that must be expanded; does not filter any out._

```sql
SELECT DISTINCT packaging_id AS final_combination_id
FROM packaging_relations
```

---

**Skill `packaging_edges`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `container_id`, `contained_item_id` |
| output columns | `container_id`, `contained_item_id`, `quantity_per_container` |
| source tables | `packaging_relations` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `expanded_leaf_quantities` |
| validated_on | — |
| counter_examples | 0 |

_Select all direct packaging relationships (edges) between a container/package and the thing it contains, including the contained item id and the multiplicative quantity (how many of the contained item are in one unit of the container). This is the raw adjacency list used for recursive expansion._

```sql
SELECT
  packaging_id AS container_id,
  contains_id AS contained_item_id,
  qty AS quantity_per_container
FROM packaging_relations
```

---

**Skill `expanded_leaf_quantities`** — category `REC`

| field | value |
|---|---|
| grain (one row per) | `final_combination_id`, `leaf_item_id`, `path_id` |
| output columns | `final_combination_id`, `leaf_item_id`, `effective_quantity` |
| source tables | `packaging`, `packaging_relations`, `packaging_edges`, `final_packaging_combinations` |
| depends_on (builds on) | `final_packaging_combinations`, `packaging_edges` |
| depended-on by (builds on this) | `per_combination_leaf_totals` |
| validated_on | — |
| counter_examples | 0 |

_Recursively traverse packaging_edges starting from each final_combination_id to expand all nested packaging until only leaf-level items (items that do not contain other items) remain. Emit one row per leaf item occurrence with the effective quantity contributed to the originating final combination (product of quantities along the path)._

```sql
SELECT
  f.final_combination_id,
  e.leaf_item_id,
  e.effective_quantity
FROM (
  WITH RECURSIVE
  -- start from each final combination as a root, seed paths with direct edges
  expansion(root_final_combination_id, path_id, current_item_id, effective_quantity, is_leaf) AS (
    SELECT
      f.final_combination_id AS root_final_combination_id,
      printf('%d', f.final_combination_id) || '-' || printf('%d', pe.contained_item_id) AS path_id,
      pe.contained_item_id AS current_item_id,
      pe.quantity_per_container AS effective_quantity,
      -- determine leafness by existence of outgoing edges from this contained_item_id
      NOT EXISTS(SELECT 1 FROM packaging_edges pe2 WHERE pe2.container_id = pe.contained_item_id) AS is_leaf
    FROM final_packaging_combinations f
    JOIN packaging_edges pe ON pe.container_id = f.final_combination_id
    UNION ALL
    -- recurse: expand current_item_id if it is a container (has contained items)
    SELECT
      exp.root_final_combination_id,
      exp.path_id || '-' || printf('%d', pe.contained_item_id) AS path_id,
      pe.contained_item_id AS current_item_id,
      exp.effective_quantity * pe.quantity_per_container AS effective_quantity,
      NOT EXISTS(SELECT 1 FROM packaging_edges pe2 WHERE pe2.container_id = pe.contained_item_id) AS is_leaf
    FROM expansion exp
    JOIN packaging_edges pe ON pe.container_id = exp.current_item_id
  )
  -- select only leaf nodes, emit one row per leaf occurrence with effective quantity
  SELECT
    root_final_combination_id AS final_combination_id,
    current_item_id AS leaf_item_id,
    effective_quantity AS effective_quantity
  FROM expansion
  WHERE is_leaf
) e
JOIN final_packaging_combinations f ON f.final_combination_id = e.final_combination_id
```

---

**Skill `per_combination_leaf_totals`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `final_combination_id` |
| output columns | `final_combination_id`, `total_leaf_quantity` |
| source tables | `expanded_leaf_quantities` |
| depends_on (builds on) | `expanded_leaf_quantities` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each final_combination_id, sum the effective_quantity of all expanded leaf items to produce the total quantity of leaf-level items for that final combination. Include combinations that sum to zero._

```sql
SELECT
  elq.final_combination_id AS final_combination_id,
  COALESCE(SUM(elq.effective_quantity), 0) AS total_leaf_quantity
FROM
  expanded_leaf_quantities elq
GROUP BY
  elq.final_combination_id
```

---

**Skill `packaging_items_direct`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `container_id`, `item_id`, `record_id` |
| output columns | `container_id`, `item_id`, `quantity` |
| source tables | `packaging_relations` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `top_container_item_accumulations` |
| validated_on | — |
| counter_examples | 0 |

_All direct item-quantity records inside packaging containers (each row represents an occurrence of an item stored in a specific container with its recorded quantity)._

```sql
SELECT
  packaging_relations.packaging_id AS container_id,
  packaging_relations.contains_id AS item_id,
  packaging_relations.qty AS quantity,
  packaging_relations.packaging_id || '-' || packaging_relations.contains_id AS record_id
FROM packaging_relations
```

---

**Skill `top_level_containers`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `top_container_id` |
| output columns | `top_container_id` |
| source tables | `packaging`, `packaging_relations` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `top_container_item_accumulations` |
| validated_on | — |
| counter_examples | 0 |

_All packaging containers that are top-level (they have no parent container)._

```sql
SELECT p.id AS top_container_id
FROM packaging p
LEFT JOIN packaging_relations pr ON pr.contains_id = p.id
WHERE pr.packaging_id IS NULL
```

---

**Skill `container_descendant_paths`** — category `REC`

| field | value |
|---|---|
| grain (one row per) | `ancestor_container_id`, `descendant_container_id` |
| output columns | `ancestor_container_id`, `descendant_container_id` |
| source tables | `packaging`, `packaging_relations` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `top_container_item_accumulations` |
| validated_on | — |
| counter_examples | 0 |

_Recursive expansion of container hierarchical relationships producing one row per (ancestor_container, descendant_container) pair including the ancestor itself (i.e., all descendants at any depth for each container)._

```sql
SELECT
  p.id AS ancestor_container_id,
  p_desc.id AS descendant_container_id
FROM packaging AS p
JOIN packaging AS p_desc
  ON p_desc.id = p.id
UNION
SELECT
  anc.id AS ancestor_container_id,
  child.id AS descendant_container_id
FROM packaging AS anc
JOIN packaging_relations AS rel1
  ON rel1.packaging_id = anc.id
JOIN packaging AS child
  ON child.id = rel1.contains_id
UNION
SELECT
  anc.id AS ancestor_container_id,
  desc2.id AS descendant_container_id
FROM packaging AS anc
JOIN packaging_relations AS rel1
  ON rel1.packaging_id = anc.id
JOIN packaging AS mid
  ON mid.id = rel1.contains_id
JOIN packaging_relations AS rel2
  ON rel2.packaging_id = mid.id
JOIN packaging AS desc2
  ON desc2.id = rel2.contains_id
UNION
SELECT
  anc.id AS ancestor_container_id,
  desc3.id AS descendant_container_id
FROM packaging AS anc
JOIN packaging_relations AS rel1
  ON rel1.packaging_id = anc.id
JOIN packaging AS mid1
  ON mid1.id = rel1.contains_id
JOIN packaging_relations AS rel2
  ON rel2.packaging_id = mid1.id
JOIN packaging AS mid2
  ON mid2.id = rel2.contains_id
JOIN packaging_relations AS rel3
  ON rel3.packaging_id = mid2.id
JOIN packaging AS desc3
  ON desc3.id = rel3.contains_id
```

---

**Skill `top_container_item_accumulations`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `top_container_id`, `item_id` |
| output columns | `top_container_id`, `item_id`, `accumulated_quantity` |
| source tables | `packaging_items_direct`, `top_level_containers`, `container_descendant_paths` |
| depends_on (builds on) | `top_level_containers`, `container_descendant_paths`, `packaging_items_direct` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each top-level container and each item, sum the quantities of that item across the top-level container and all its descendant containers (uses descendant paths joined to direct item quantities)._

```sql
SELECT
  t.top_container_id AS top_container_id,
  pid.item_id AS item_id,
  SUM(COALESCE(pid.quantity,0)) AS accumulated_quantity
FROM top_level_containers t
JOIN container_descendant_paths p
  ON p.ancestor_container_id = t.top_container_id
LEFT JOIN packaging_items_direct pid
  ON pid.container_id = p.descendant_container_id
GROUP BY
  t.top_container_id,
  pid.item_id
```

---

**Skill `order_lines_sel`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `order_line_identifier` |
| output columns | `order_id`, `order_line_identifier`, `product_id`, `order_line_sequence`, `order_line_quantity` |
| source tables | `orderlines` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `pick_plan_allocations_win` |
| validated_on | — |
| counter_examples | 0 |

_Select the order lines for the target order (the rows of the order with their sequence/identifier, product id, and requested quantity). This preserves the per-line sequence so multiple lines for the same product remain distinct._

```sql
SELECT
  order_id AS order_id,
  id AS order_line_identifier,
  product_id AS product_id,
  id AS order_line_sequence,
  qty AS order_line_quantity
FROM orderlines
```

---

**Skill `warehouse_inventory_sel`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `location_id`, `product_id` |
| output columns | `product_id`, `location_id`, `aisle`, `position`, `location_available_quantity_before_pick`, `location_purchase_date`, `warehouse_id`, `inventory_id`, `purchase_id` |
| source tables | `inventory`, `locations`, `purchases` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All inventory locations in the specified warehouse with their product, location id (aisle and position), available quantity, and purchase date. One row per physical inventory location for a product in warehouse 1._

```sql
SELECT
  i.product_id AS product_id,
  i.location_id AS location_id,
  l.aisle AS aisle,
  l.position AS position,
  i.qty AS location_available_quantity_before_pick,
  p.purchased AS location_purchase_date,
  l.warehouse AS warehouse_id,
  i.id AS inventory_id,
  p.id AS purchase_id
FROM inventory i
JOIN locations l ON l.id = i.location_id
LEFT JOIN purchases p ON p.id = i.purchase_id
WHERE l.warehouse = 1
```

---

**Skill `product_location_priority_rank`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `product_id`, `location_id` |
| output columns | `product_id`, `location_id`, `location_rank_by_priority`, `location_purchase_date`, `location_available_quantity_before_pick`, `aisle`, `position` |
| source tables | `inventory`, `purchases`, `locations` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `pick_plan_allocations_win` |
| validated_on | — |
| counter_examples | 0 |

_For each product, rank its inventory locations by selection priority: primary sort by earlier purchase_date (ascending), secondary by smaller available quantity (ascending). Keep the rank and the ordered available quantity per location to drive pick sequencing._

```sql
SELECT
  i.product_id AS product_id,
  i.location_id AS location_id,
  -- rank per product: primary by earliest purchase.purchased, secondary by smaller available qty
  (SELECT COUNT(1)
   FROM inventory i2
   LEFT JOIN purchases p2 ON i2.purchase_id = p2.id
   WHERE i2.product_id = i.product_id
     AND (
       COALESCE(p2.purchased, '') < COALESCE((SELECT purchased FROM purchases p3 WHERE p3.id = i.purchase_id), '')
       OR (
         COALESCE(p2.purchased, '') = COALESCE((SELECT purchased FROM purchases p3 WHERE p3.id = i.purchase_id), '')
         AND COALESCE(i2.qty, 0) <= COALESCE(i.qty, 0)
         AND (i2.id <> i.id OR (i2.id = i.id))
       )
     )
  ) AS location_rank_by_priority,
  (SELECT p.purchased FROM purchases p WHERE p.id = i.purchase_id) AS location_purchase_date,
  i.qty AS location_available_quantity_before_pick,
  l.aisle AS aisle,
  l.position AS position
FROM inventory i
LEFT JOIN locations l ON i.location_id = l.id
```

---

**Skill `pick_plan_allocations_win`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `order_line_identifier`, `location_id` |
| output columns | `order_id`, `order_line_identifier`, `product_id`, `aisle`, `position`, `location_id`, `pick_quantity_from_location`, `location_available_quantity_before_pick`, `location_purchase_date`, `cumulative_ordered_quantity_for_product_up_to_and_including_this_order_line`, `cumulative_picked_quantity_for_product_up_to_and_including_this_order_line_after_applying_this_location's_pick`, `location_rank_by_priority` |
| source tables | `order_lines_sel`, `product_location_priority_rank` |
| depends_on (builds on) | `order_lines_sel`, `product_location_priority_rank` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Generate pick allocations by walking inventory locations in priority order and assigning available quantities to satisfy order lines in sequence for each product. This produces one row per (order_line_identifier, location) allocation with running totals: cumulative ordered quantity for the product up to and including the order line, and cumulative picked quantity for the product up to and including this allocation. Respect that picks cannot exceed location available quantity or total remaining ordered quantity for the product; when a product has multiple order lines, allocations consume earlier lines first following their sequence._

```sql
SELECT
  ol.order_id,
  ol.order_line_identifier,
  ol.product_id,
  vip.aisle,
  vip.position,
  vip.location_id,
  -- pick quantity allocated from this location to this order line (computed)
  CASE
    WHEN remaining_for_line <= 0 OR vip.location_available_quantity_before_pick <= 0 THEN 0
    ELSE
      CASE
        WHEN vip.location_available_quantity_before_pick >= remaining_for_line THEN remaining_for_line
        ELSE vip.location_available_quantity_before_pick
      END
  END AS pick_quantity_from_location,
  vip.location_available_quantity_before_pick,
  vip.location_purchase_date,
  -- cumulative ordered qty for product up to and including this order line (by order_line_sequence)
  ol_cum.cumulative_ordered_quantity_for_product_up_to_and_including_this_order_line,
  -- cumulative picked qty for product up to and including this order line after applying this location's pick
  -- computed as previous cumulative picked for product up to previous order lines and prior locations plus this allocation
  (IFNULL(prev_picked.cumulative_picked_before_this_allocation,0)
    + CASE
        WHEN remaining_for_line <= 0 OR vip.location_available_quantity_before_pick <= 0 THEN 0
        ELSE
          CASE
            WHEN vip.location_available_quantity_before_pick >= remaining_for_line THEN remaining_for_line
            ELSE vip.location_available_quantity_before_pick
          END
      END
  ) AS "cumulative_picked_quantity_for_product_up_to_and_including_this_order_line_after_applying_this_location's_pick",
  vip.location_rank_by_priority
FROM
  order_lines_sel ol
  -- join inventory/priority info for product locations
  JOIN product_location_priority_rank vip
    ON vip.product_id = ol.product_id
  -- cumulative ordered quantity per product up to this order line (includes this line)
  JOIN (
    SELECT
      o1.product_id,
      o1.order_line_identifier,
      SUM(o2.order_line_quantity) AS cumulative_ordered_quantity_for_product_up_to_and_including_this_order_line
    FROM order_lines_sel o1
    JOIN order_lines_sel o2
      ON o2.product_id = o1.product_id
     AND (o2.order_line_sequence <= o1.order_line_sequence)
    GROUP BY o1.product_id, o1.order_line_identifier
  ) ol_cum
    ON ol_cum.product_id = ol.product_id
   AND ol_cum.order_line_identifier = ol.order_line_identifier
  -- compute remaining quantity for this order line at the time of considering this location
  JOIN (
    -- for each product + order_line + location rank, compute remaining quantity before allocating from this location
    SELECT
      base.product_id,
      base.order_line_identifier,
      base.order_line_sequence,
      base.order_line_quantity,
      pri.location_id,
      pri.location_rank_by_priority,
      -- compute sum of available qty at all prior locations for this product (higher priority = lower rank number)
      pri.location_available_quantity_before_pick,
      pri.location_purchase_date,
      -- remaining for this line equals line qty minus sum of allocations from prior locations to this line
      -- allocations from prior locations are limited by location availability and remaining after earlier lines;
      -- we approximate remaining by subtracting what earlier locations could have provided to earlier order lines of same product.
      -- To keep view deterministic and self-contained we compute remaining_for_line as:
      -- max(0, line_qty - sum(LEAST(location_available, remaining_after_prior_lines) over prior locations))
      -- implement by cumulative available up to prior ranks and prior order_line_sequence.
      CASE
        WHEN base.order_line_quantity - IFNULL(prior_cum.prior_available_consumable,0) <= 0 THEN 0
        ELSE base.order_line_quantity - IFNULL(prior_cum.prior_available_consumable,0)
      END AS remaining_for_line
    FROM
      order_lines_sel base
      JOIN product_location_priority_rank pri
        ON pri.product_id = base.product_id
      LEFT JOIN (
        -- prior available consumable quantity from locations with rank less than current for same product
        SELECT
          p1.product_id,
          p1.location_rank_by_priority AS curr_rank,
          p1.location_id,
          SUM(p2.location_available_quantity_before_pick) AS prior_available_consumable
        FROM product_location_priority_rank p1
        JOIN product_location_priority_rank p2
          ON p2.product_id = p1.product_id
         AND p2.location_rank_by_priority < p1.location_rank_by_priority
        GROUP BY p1.product_id, p1.location_rank_by_priority, p1.location_id
      ) prior_cum
        ON prior_cum.product_id = pri.product_id
       AND prior_cum.curr_rank = pri.location_rank_by_priority
  ) AS alloc_meta
    ON alloc_meta.product_id = ol.product_id
   AND alloc_meta.order_line_identifier = ol.order_line_identifier
   AND alloc_meta.location_id = vip.location_id
  -- previous picked cumulative for product before this allocation: sum of min(location_available, remaining) over all combinations of earlier order lines and earlier locations
  LEFT JOIN (
    -- approximate cumulative picked before this allocation by summing capacity of all locations with rank < current plus allocations to earlier order lines at same rank
    SELECT
      p.product_id,
      o.order_line_identifier,
      SUM(
        CASE
          WHEN p.location_rank_by_priority < vip2.location_rank_by_priority THEN p.location_available_quantity_before_pick
          ELSE 0
        END
      ) AS cumulative_picked_before_this_allocation
    FROM product_location_priority_rank p
    JOIN order_lines_sel o
      ON o.product_id = p.product_id
    LEFT JOIN product_location_priority_rank vip2
      ON vip2.product_id = p.product_id
    GROUP BY p.product_id, o.order_line_identifier
  ) prev_picked
    ON prev_picked.product_id = ol.product_id
   AND prev_picked.order_line_identifier = ol.order_line_identifier
  -- expose remaining_for_line from alloc_meta
  JOIN (SELECT 1) x
WHERE
  1=1
```

---

**Skill `orders_with_positive_required_qty`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `order_line_id` |
| output columns | `order_id`, `order_line_id`, `product_id`, `required_qty` |
| source tables | `orderlines` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `order_inventory_allocations` |
| validated_on | — |
| counter_examples | 0 |

_Select order lines (order items) for which the required/ordered quantity is present and greater than zero. Keep product and order identifiers and the ordered quantity needed to be picked._

```sql
SELECT
  order_id AS order_id,
  id AS order_line_id,
  product_id AS product_id,
  qty AS required_qty
FROM orderlines
WHERE qty IS NOT NULL
  AND qty > 0
```

---

**Skill `available_inventory_units`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `inventory_id` |
| output columns | `inventory_id`, `product_id`, `available_qty`, `purchase_date` |
| source tables | `inventory`, `purchases` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `fifo_inventory_ordering` |
| validated_on | — |
| counter_examples | 0 |

_Select inventory records that have available quantity greater than zero and include their purchase_date and available quantity so they can be used in FIFO allocations._

```sql
SELECT
  inventory.id AS inventory_id,
  inventory.product_id AS product_id,
  inventory.qty AS available_qty,
  purchases.purchased AS purchase_date
FROM inventory
JOIN purchases ON purchases.id = inventory.purchase_id
WHERE inventory.qty > 0
```

---

**Skill `fifo_inventory_ordering`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `product_id`, `inventory_id` |
| output columns | `product_id`, `inventory_id`, `available_qty`, `purchase_date`, `fifo_rank` |
| source tables | `available_inventory_units` |
| depends_on (builds on) | `available_inventory_units` |
| depended-on by (builds on this) | `order_inventory_allocations` |
| validated_on | — |
| counter_examples | 0 |

_Order inventory records per product into the FIFO allocation sequence: earliest purchase_date first; for identical purchase_date prefer the inventory record with the smaller available_qty first. Produce a deterministic per-product sequence position to drive allocations._

```sql
SELECT
  ai.product_id AS product_id,
  ai.inventory_id AS inventory_id,
  ai.available_qty AS available_qty,
  ai.purchase_date AS purchase_date,
  -- dense rank per product: earliest purchase_date first; ties broken by smaller available_qty first;
  -- use ROW_NUMBER to produce a deterministic sequence position per product (FIFO rank)
  ROW_NUMBER() OVER (
    PARTITION BY ai.product_id
    ORDER BY ai.purchase_date ASC, ai.available_qty ASC, ai.inventory_id ASC
  ) AS fifo_rank
FROM available_inventory_units ai
```

---

**Skill `order_inventory_allocations`** — category `REC`

| field | value |
|---|---|
| grain (one row per) | `order_line_id`, `inventory_id` |
| output columns | `order_line_id`, `product_id`, `inventory_id`, `allocated_picked_qty` |
| source tables | `orders`, `orderlines`, `fifo_inventory_ordering`, `orders_with_positive_required_qty`, `fifo_inventory_ordering` |
| depends_on (builds on) | `orders_with_positive_required_qty`, `fifo_inventory_ordering` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each order line (from orders_with_positive_required_qty) allocate required quantity against the product's FIFO-ordered inventory units (from fifo_inventory_ordering). Produce allocation rows that show the picked_qty equal to the overlap between the remaining required quantity and the inventory available_qty at the time of allocation. Do not collapse allocations; each row is one allocation from one inventory unit to one order line._

```sql
SELECT
  owpq.order_line_id AS order_line_id,
  owpq.product_id AS product_id,
  fio.inventory_id AS inventory_id,
  CASE
    WHEN owpq.required_qty <= 0 THEN 0
    WHEN fio.available_qty <= 0 THEN 0
    ELSE
      -- allocate the remaining required qty to each fifo inventory unit in rank order.
      -- We compute allocation as the minimum of the inventory unit's available_qty and
      -- the remaining required qty after summing allocations from prior fifo ranks.
      -- Achieve this by computing cumulative available_qty of fifo units up to current rank,
      -- then subtracting cumulative available_qty of prior ranks to get this unit's contribution,
      -- and capping by required_qty remaining.
      (
        -- amount available from all units up to and including this one
        CASE
          WHEN fio_cum.cum_available_up_to_rank IS NULL THEN 0
          ELSE
            -- min(total available up to this unit, required_qty)
            CASE WHEN fio_cum.cum_available_up_to_rank < owpq.required_qty THEN fio_cum.cum_available_up_to_rank ELSE owpq.required_qty END
        END
        -
        -- amount available from units strictly before this one
        CASE
          WHEN fio_prev.cum_available_before_rank IS NULL THEN 0
          ELSE fio_prev.cum_available_before_rank
        END
      )
  END AS allocated_picked_qty
FROM
  orders_with_positive_required_qty AS owpq
JOIN
  fifo_inventory_ordering AS fio
  ON fio.product_id = owpq.product_id
LEFT JOIN
  (
    -- cumulative available qty up to and including this fifo rank for the product
    SELECT
      product_id,
      inventory_id,
      fifo_rank,
      SUM(available_qty) OVER (PARTITION BY product_id ORDER BY fifo_rank ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_available_up_to_rank
    FROM fifo_inventory_ordering
  ) AS fio_cum
  ON fio_cum.product_id = fio.product_id AND fio_cum.inventory_id = fio.inventory_id AND fio_cum.fifo_rank = fio.fifo_rank
LEFT JOIN
  (
    -- cumulative available qty strictly before this fifo rank for the product
    SELECT
      product_id,
      inventory_id,
      fifo_rank,
      COALESCE(
        SUM(available_qty) OVER (PARTITION BY product_id ORDER BY fifo_rank ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
        0
      ) AS cum_available_before_rank
    FROM fifo_inventory_ordering
  ) AS fio_prev
  ON fio_prev.product_id = fio.product_id AND fio_prev.inventory_id = fio.inventory_id AND fio_prev.fifo_rank = fio.fifo_rank
WHERE
  owpq.required_qty > 0
  AND fio.available_qty > 0
  AND fio.product_id = owpq.product_id
```

---

**Skill `order_picks_cohort`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `pick_id` |
| output columns | `pick_id`, `order_id`, `product_id`, `pick_timestamp`, `picked_quantity`, `inventory_lot_id` |
| source tables | `picking_log`, `picking_line` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select all pick (or inventory-allocation) events that were applied to the specific order (cohort of pick records tied to an order). This filters raw pick/allocation history down to only records that contributed units to the target order (order id will be applied later in final step)._

```sql
SELECT
  picking_log.picklist_id || '-' || picking_log.log_time AS pick_id,
  picking_line.order_id AS order_id,
  picking_line.product_id AS product_id,
  picking_log.log_time AS pick_timestamp,
  -- pick quantity: correlate picking_line.qty as the amount applied by that pick event when pickline matches
  CASE
    WHEN picking_log.pickline_no = picking_line.line_no AND picking_log.picklist_id = picking_line.picklist_id
    THEN picking_line.qty
    ELSE NULL
  END AS picked_quantity,
  -- inventory lot id: there is no direct inventory link in picking_log; leave as NULL unless later joined
  NULL AS inventory_lot_id
FROM picking_log
JOIN picking_line
  ON picking_log.picklist_id = picking_line.picklist_id
  AND picking_log.pickline_no = picking_line.line_no
```

---

**Skill `product_inventory_lots`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `inventory_lot_id` |
| output columns | `inventory_lot_id`, `product_id`, `lot_received_timestamp`, `lot_available_quantity` |
| source tables | `inventory`, `purchases` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `fifo_allocations_per_lot` |
| validated_on | — |
| counter_examples | 0 |

_One-row-per inventory lot / inbound inventory record for products that can be consumed by picks. Includes lot arrival/receipt time (or other age indicator) and available quantity to support FIFO ordering of consumption._

```sql
SELECT
  inventory.id AS inventory_lot_id,
  inventory.product_id AS product_id,
  purchases.purchased AS lot_received_timestamp,
  inventory.qty AS lot_available_quantity
FROM inventory
LEFT JOIN purchases ON purchases.id = inventory.purchase_id
```

---

**Skill `fifo_allocations_per_lot`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `inventory_lot_id` |
| output columns | `product_id`, `inventory_lot_id`, `lot_received_timestamp`, `lot_available_quantity`, `lot_running_available_before`, `lot_running_available_after`, `lot_fifo_rank` |
| source tables | `product_inventory_lots` |
| depends_on (builds on) | `product_inventory_lots` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each product, order the inventory lots by their arrival/receipt time (oldest first) and compute running available quantity so we can determine how much from each lot would be consumed under FIFO when fulfilling demand. Produces per-lot running-available and ordinal position used by FIFO allocation logic._

```sql
SELECT
  pil.inventory_lot_id AS product_id,
  pil.inventory_lot_id,
  pil.lot_received_timestamp,
  pil.lot_available_quantity,
  -- running available before this lot = sum of available_qty of all older lots for same product
  COALESCE((
    SELECT SUM(pil2.lot_available_quantity)
    FROM product_inventory_lots pil2
    WHERE pil2.product_id = pil.product_id
      AND (
        pil2.lot_received_timestamp < pil.lot_received_timestamp
        OR (pil2.lot_received_timestamp = pil.lot_received_timestamp AND pil2.inventory_lot_id < pil.inventory_lot_id)
      )
  ), 0) AS lot_running_available_before,
  -- running available after = before + this lot's available
  COALESCE((
    SELECT SUM(pil2.lot_available_quantity)
    FROM product_inventory_lots pil2
    WHERE pil2.product_id = pil.product_id
      AND (
        pil2.lot_received_timestamp < pil.lot_received_timestamp
        OR (pil2.lot_received_timestamp = pil.lot_received_timestamp AND pil2.inventory_lot_id <= pil.inventory_lot_id)
      )
  ), 0) AS lot_running_available_after,
  -- fifo rank: 1 = oldest; tie-breaker by inventory_lot_id
  (
    SELECT COUNT(1)
    FROM product_inventory_lots pil3
    WHERE pil3.product_id = pil.product_id
      AND (
        pil3.lot_received_timestamp < pil.lot_received_timestamp
        OR (pil3.lot_received_timestamp = pil.lot_received_timestamp AND pil3.inventory_lot_id <= pil.inventory_lot_id)
      )
  ) AS lot_fifo_rank
FROM product_inventory_lots pil
```

---

**Skill `order_product_fifo_picks`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `pick_id`, `inventory_lot_id` |
| output columns | `order_id`, `product_id`, `inventory_lot_id`, `pick_id`, `quantity_allocated_to_order_from_lot` |
| source tables | `picking_line`, `inventory` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Determine, for each product used to fulfill the order, which pick/allocation quantities are drawn from which FIFO inventory lots and the exact quantity taken from each lot for that order. This joins the order picks with the FIFO-ordered lots and applies FIFO consumption rules so only allocations used for the order remain._

```sql
SELECT
  pl.order_id AS order_id,
  pl.product_id AS product_id,
  inv.id AS inventory_lot_id,
  pl.picklist_id || '-' || pl.line_no AS pick_id,
  (
    -- quantity allocated to this pick from this inventory lot following FIFO consumption:
    -- it's the minimum of:
    --  1) remaining available qty in the lot at time of consumption
    --  2) pick line quantity (pl.qty) minus quantity already allocated from earlier FIFO lots for same pick
    -- We compute using windowed cumulative sums ordered by inventory.id (proxy for FIFO by purchase order)
    -- and then derive the overlap (allocated portion) between cumulative ranges.
    CASE
      WHEN lot_running_available_before <= 0 THEN 0
      ELSE
        (
          -- overlap between [lot_running_available_before+1, lot_running_available_after] and
          -- [pick_consumed_start, pick_consumed_end]
          (
            (CASE WHEN lot_running_available_after < pick_consumed_start THEN 0
                  WHEN lot_running_available_before+1 > pick_consumed_end THEN 0
                  ELSE
                    (MIN(lot_running_available_after, pick_consumed_end)
                     - MAX(lot_running_available_before+1, pick_consumed_start) + 1)
             END)
          )
        )
    END
  ) * 1.0 AS quantity_allocated_to_order_from_lot
FROM
  picking_line pl
JOIN
  inventory inv ON inv.product_id = pl.product_id
-- compute FIFO ordering per product by inventory.id ascending (as proxy for lot receipt)
-- derive running available before/after for each lot per product
JOIN (
  SELECT
    product_id,
    id AS inventory_lot_id,
    qty AS lot_available_quantity,
    COALESCE(
      SUM(qty) OVER (PARTITION BY product_id ORDER BY id ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
      0
    ) AS lot_running_available_before,
    SUM(qty) OVER (PARTITION BY product_id ORDER BY id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS lot_running_available_after
  FROM inventory
) fifo ON fifo.product_id = inv.product_id AND fifo.inventory_lot_id = inv.id
-- compute for each pick (identified by picklist_id+line_no) the cumulative consumption window in FIFO coordinate space:
-- pick_consumed_start..pick_consumed_end are 1-based positions into the product's total FIFO sequence
JOIN (
  SELECT
    pl2.picklist_id || '-' || pl2.line_no AS pick_id,
    pl2.order_id,
    pl2.product_id,
    pl2.qty AS pick_qty,
    -- pick_consumed_end: cumulative sum of picks for this product up to and including this pick
    COALESCE(
      SUM(pl2.qty) OVER (PARTITION BY pl2.product_id ORDER BY pl2.picklist_id, pl2.line_no ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),
      0
    ) AS pick_consumed_end,
    -- pick_consumed_start is end minus this pick qty plus 1 (1-based)
    (COALESCE(
      SUM(pl2.qty) OVER (PARTITION BY pl2.product_id ORDER BY pl2.picklist_id, pl2.line_no ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),
      0
    ) - pl2.qty + 1) AS pick_consumed_start
  FROM picking_line pl2
) pc ON pc.order_id = pl.order_id AND pc.product_id = pl.product_id AND pc.pick_id = pl.picklist_id || '-' || pl.line_no
```

---

**Skill `monthly_sales_raw`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `product_id`, `year_month` |
| output columns | `product_id`, `year_month`, `sales_amount` |
| source tables | `monthly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `monthly_sales_ratios` |
| validated_on | — |
| counter_examples | 0 |

_Select monthly sales amounts per product for the period starting January 2016 and onward; one row per product-month with the calendar month (year-month) and the sales value used as the numerator._

```sql
SELECT
  m.product_id AS product_id,
  substr(m.mth, 1, 7) AS year_month,
  m.qty AS sales_amount
FROM monthly_sales m
WHERE m.mth >= '2016-01-01'
```

---

**Skill `monthly_sales_cma`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `product_id`, `year_month` |
| output columns | `product_id`, `year_month`, `cma_12m` |
| source tables | `monthly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `monthly_sales_ratios` |
| validated_on | — |
| counter_examples | 0 |

_Compute the 12-month centered moving average (CMA) for each product-month using the overlapping-window method described; produce one row per product-month with the CMA value. (This requires months before/after as needed by the centered 12-month window.)_

```sql
SELECT
  m.product_id AS product_id,
  m.mth AS year_month,
  -- centered 12-month moving average: average qty over window of 12 months centered on current month.
  -- For 12-month centered window, using overlapping-window method: include 11 months prior through current month (12-month window centered approximated by averaging two 12-month overlapping windows).
  -- Implemented here as the average of two 12-month trailing windows shifted by 0 and 1 month to produce a centered 12-month CMA.
  (
    (
      SELECT AVG(ms0.qty)
      FROM monthly_sales ms0
      WHERE ms0.product_id = m.product_id
        AND ms0.mth BETWEEN (
          SELECT date(m.mth, '-11 months')
        ) AND m.mth
    )
    +
    (
      SELECT AVG(ms1.qty)
      FROM monthly_sales ms1
      WHERE ms1.product_id = m.product_id
        AND ms1.mth BETWEEN (
          SELECT date(m.mth, '-12 months')
        ) AND date(m.mth, '-1 month')
    )
  ) / 2.0 AS cma_12m
FROM monthly_sales m
```

---

**Skill `monthly_sales_ratios`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `product_id`, `year_month` |
| output columns | `product_id`, `year_month`, `sales_amount`, `cma_12m`, `sales_to_cma_ratio` |
| source tables | `monthly_sales_raw`, `monthly_sales_cma` |
| depends_on (builds on) | `monthly_sales_raw`, `monthly_sales_cma` |
| depended-on by (builds on this) | `products_all_months_above_threshold_2017` |
| validated_on | — |
| counter_examples | 0 |

_Join monthly sales and CMA rows, compute the Sales-to-CMA Ratio = sales_amount / cma_12m, and exclude rows where cma_12m is zero or NULL/undefined. One row per product-month with the ratio._

```sql
SELECT
  msr.product_id AS product_id,
  msr.year_month AS year_month,
  msr.sales_amount AS sales_amount,
  msc.cma_12m AS cma_12m,
  (CAST(msr.sales_amount AS REAL) / msc.cma_12m) AS sales_to_cma_ratio
FROM
  monthly_sales_raw msr
  JOIN monthly_sales_cma msc
    ON msr.product_id = msc.product_id
    AND msr.year_month = msc.year_month
WHERE
  msc.cma_12m IS NOT NULL
  AND msc.cma_12m <> 0
```

---

**Skill `products_all_months_above_threshold_2017`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `product_id` |
| output columns | `product_id`, `month_2017_01_ratio`, `month_2017_02_ratio`, `month_2017_03_ratio`, `month_2017_04_ratio`, `month_2017_05_ratio`, `month_2017_06_ratio`, `month_2017_07_ratio`, `month_2017_08_ratio`, `month_2017_09_ratio`, `month_2017_10_ratio`, `month_2017_11_ratio`, `month_2017_12_ratio`, `all_12_months_above_2_indicator` |
| source tables | `monthly_sales_ratios` |
| depends_on (builds on) | `monthly_sales_ratios` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each product, consider only the 12 month-rows for calendar year 2017 (Jan–Dec 2017) from the monthly_sales_ratios relation; verify that all 12 months are present and that every month's sales_to_cma_ratio is strictly greater than 2.0. Produce one row per qualifying product including either the 12 monthly ratio values (or an indicator that all 12 exceed 2.0)._

```sql
SELECT
  msr.product_id AS product_id,
  MAX(CASE WHEN substr(msr.year_month,1,7) = '2017-01' THEN msr.sales_to_cma_ratio END) AS month_2017_01_ratio,
  MAX(CASE WHEN substr(msr.year_month,1,7) = '2017-02' THEN msr.sales_to_cma_ratio END) AS month_2017_02_ratio,
  MAX(CASE WHEN substr(msr.year_month,1,7) = '2017-03' THEN msr.sales_to_cma_ratio END) AS month_2017_03_ratio,
  MAX(CASE WHEN substr(msr.year_month,1,7) = '2017-04' THEN msr.sales_to_cma_ratio END) AS month_2017_04_ratio,
  MAX(CASE WHEN substr(msr.year_month,1,7) = '2017-05' THEN msr.sales_to_cma_ratio END) AS month_2017_05_ratio,
  MAX(CASE WHEN substr(msr.year_month,1,7) = '2017-06' THEN msr.sales_to_cma_ratio END) AS month_2017_06_ratio,
  MAX(CASE WHEN substr(msr.year_month,1,7) = '2017-07' THEN msr.sales_to_cma_ratio END) AS month_2017_07_ratio,
  MAX(CASE WHEN substr(msr.year_month,1,7) = '2017-08' THEN msr.sales_to_cma_ratio END) AS month_2017_08_ratio,
  MAX(CASE WHEN substr(msr.year_month,1,7) = '2017-09' THEN msr.sales_to_cma_ratio END) AS month_2017_09_ratio,
  MAX(CASE WHEN substr(msr.year_month,1,7) = '2017-10' THEN msr.sales_to_cma_ratio END) AS month_2017_10_ratio,
  MAX(CASE WHEN substr(msr.year_month,1,7) = '2017-11' THEN msr.sales_to_cma_ratio END) AS month_2017_11_ratio,
  MAX(CASE WHEN substr(msr.year_month,1,7) = '2017-12' THEN msr.sales_to_cma_ratio END) AS month_2017_12_ratio,
  CASE
    WHEN COUNT(DISTINCT substr(msr.year_month,1,7)) = 12
     AND MIN(CASE WHEN substr(msr.year_month,1,7) BETWEEN '2017-01' AND '2017-12' THEN msr.sales_to_cma_ratio END) > 2.0
    THEN 1 ELSE 0 END AS all_12_months_above_2_indicator
FROM monthly_sales_ratios msr
WHERE substr(msr.year_month,1,7) BETWEEN '2017-01' AND '2017-12'
GROUP BY msr.product_id
HAVING COUNT(DISTINCT substr(msr.year_month,1,7)) = 12
   AND MIN(CASE WHEN substr(msr.year_month,1,7) BETWEEN '2017-01' AND '2017-12' THEN msr.sales_to_cma_ratio END) > 2.0
```

---

**Skill `monthly_sales_history`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `product_id`, `month_start_date` |
| output columns | `product_id`, `month_start_date`, `month_index_from_start`, `sales` |
| source tables | `monthly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `weighted_regression_monthly_forecasts` |
| validated_on | — |
| counter_examples | 0 |

_Select the monthly sales history restricted to the input period used by the forecasting model: the first 36 months beginning 2016-01. Each row is one product-month observation with its sales value and date metadata._

```sql
SELECT
  product_id,
  mth AS month_start_date,
  ( (strftime('%Y', mth) - 2016) * 12
    + (strftime('%m', mth) - 1)
    + 1
  ) AS month_index_from_start,
  qty AS sales
FROM monthly_sales
WHERE mth >= '2016-01-01' AND mth <= '2018-12-01'
```

---

**Skill `seasonality_factors_by_time_step`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `model_time_step` |
| output columns | `model_time_step`, `seasonality_factor` |
| source tables | — |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `weighted_regression_monthly_forecasts` |
| validated_on | — |
| counter_examples | 0 |

_Provide seasonality multipliers or factors keyed by the forecasting model's internal time step index. This relation enumerates time_step indices and their seasonal factor; downstream logic will only apply factors for time steps 7 through 30 and ignore others._

```sql
SELECT
  ts.model_time_step AS model_time_step,
  ts.seasonality_factor AS seasonality_factor
FROM (
  SELECT 1 AS model_time_step, 1.00 AS seasonality_factor UNION ALL
  SELECT 2, 1.00 UNION ALL
  SELECT 3, 1.00 UNION ALL
  SELECT 4, 1.00 UNION ALL
  SELECT 5, 1.00 UNION ALL
  SELECT 6, 1.00 UNION ALL
  SELECT 7, 1.00 UNION ALL
  SELECT 8, 1.00 UNION ALL
  SELECT 9, 1.00 UNION ALL
  SELECT 10, 1.00 UNION ALL
  SELECT 11, 1.00 UNION ALL
  SELECT 12, 1.00 UNION ALL
  SELECT 13, 1.00 UNION ALL
  SELECT 14, 1.00 UNION ALL
  SELECT 15, 1.00 UNION ALL
  SELECT 16, 1.00 UNION ALL
  SELECT 17, 1.00 UNION ALL
  SELECT 18, 1.00 UNION ALL
  SELECT 19, 1.00 UNION ALL
  SELECT 20, 1.00 UNION ALL
  SELECT 21, 1.00 UNION ALL
  SELECT 22, 1.00 UNION ALL
  SELECT 23, 1.00 UNION ALL
  SELECT 24, 1.00 UNION ALL
  SELECT 25, 1.00 UNION ALL
  SELECT 26, 1.00 UNION ALL
  SELECT 27, 1.00 UNION ALL
  SELECT 28, 1.00 UNION ALL
  SELECT 29, 1.00 UNION ALL
  SELECT 30, 1.00 UNION ALL
  SELECT 31, 1.00 UNION ALL
  SELECT 32, 1.00 UNION ALL
  SELECT 33, 1.00 UNION ALL
  SELECT 34, 1.00 UNION ALL
  SELECT 35, 1.00 UNION ALL
  SELECT 36, 1.00
) AS ts
```

---

**Skill `weighted_regression_monthly_forecasts`** — category `SEM`

| field | value |
|---|---|
| grain (one row per) | `product_id`, `forecast_month_start_date` |
| output columns | `product_id`, `forecast_month_start_date`, `model_time_step`, `forecasted_monthly_sales` |
| source tables | `monthly_sales_history`, `seasonality_factors_by_time_step` |
| depends_on (builds on) | `monthly_sales_history`, `seasonality_factors_by_time_step` |
| depended-on by (builds on this) | `annual_forecast_and_average_for_selected_products` |
| validated_on | — |
| counter_examples | 0 |

_Use a weighted regression forecasting method that consumes the monthly_sales_history and seasonality_factors_by_time_step to produce forecasted monthly sales for each product and month in 2018. Apply seasonality multipliers only when the model_time_step for an observation is between 7 and 30 (inclusive). Output one forecast row per product-month for 2018._

```sql
SELECT
  h.product_id AS product_id,
  h.month_start_date AS forecast_month_start_date,
  sf.model_time_step AS model_time_step,
  -- weighted regression forecast: use past sales scaled by seasonality when model_time_step between 7 and 30 inclusive
  -- weight = 1 / (model_time_step) to emphasize recent observations; apply seasonality multiplier conditionally
  ( (h.sales * (CASE WHEN sf.model_time_step BETWEEN 7 AND 30 THEN sf.seasonality_factor ELSE 1.0 END))
    / NULLIF(sf.model_time_step,0)
  ) AS forecasted_monthly_sales
FROM monthly_sales_history h
JOIN seasonality_factors_by_time_step sf
  ON sf.model_time_step = h.month_index_from_start
WHERE
  -- intrinsic filter: produce forecasts for months that would be in a 2018 horizon (conceptual filter kept as intrinsic)
  -- We cannot hard-code a specific year here per construction rules; keep only the intrinsic horizon intent by ensuring
  -- we output rows where a month_start_date is not NULL (the final query will restrict to 2018 months).
  h.month_start_date IS NOT NULL
```

---

**Skill `annual_forecast_and_average_for_selected_products`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `product_id` |
| output columns | `product_id`, `forecast_year`, `forecasted_annual_sales`, `average_forecasted_annual_sales_for_products_4160_and_7790` |
| source tables | `weighted_regression_monthly_forecasts` |
| depends_on (builds on) | `weighted_regression_monthly_forecasts` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregate the 12 forecasted monthly sales for 2018 into an annual forecasted sales value per product, then restrict to the two target products (4160 and 7790) and compute the arithmetic mean of those two products' annual forecasts. Output one row per target product plus the final average as an additional column._

```sql
SELECT
  msf.product_id AS product_id,
  '2018' AS forecast_year,
  SUM(msf.forecasted_monthly_sales) AS forecasted_annual_sales,
  NULL AS average_forecasted_annual_sales_for_products_4160_and_7790
FROM weighted_regression_monthly_forecasts msf
WHERE msf.forecast_month_start_date LIKE '2018-%'
  AND msf.product_id IN (4160, 7790)
GROUP BY msf.product_id
```

---

**Skill `initial_december_end_inventory`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `product_id`, `dec_2018_ending_inventory` |
| source tables | `products`, `inventory`, `purchases` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `monthly_inventory_recursive_2019` |
| validated_on | — |
| counter_examples | 0 |

_Select each product's ending inventory as of December 2018 (the starting inventory for the recursion)._

```sql
SELECT
  p.id AS product_id,
  COALESCE(SUM(i.qty), 0.0) AS dec_2018_ending_inventory
FROM products p
LEFT JOIN inventory i
  ON i.product_id = p.id
  AND i.purchase_id IN (
    SELECT id FROM purchases WHERE purchased <= '2018-12-29'
  )
GROUP BY p.id
```

---

**Skill `monthly_receipts_and_shipments_2019`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `product_id`, `year_month` |
| output columns | `product_id`, `year_month`, `receipts`, `shipments` |
| source tables | `products`, `purchases`, `orderlines`, `orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `monthly_inventory_recursive_2019` |
| validated_on | — |
| counter_examples | 0 |

_Monthly receipts and shipments for each product for every month in 2019 (one row per product-month)._

```sql
SELECT
  p.id AS product_id,
  strftime('%Y-%m', m.mth) AS year_month,
  COALESCE(r.receipts, 0) AS receipts,
  COALESCE(s.shipments, 0) AS shipments
FROM products p
-- build 2019 months (intrinsic filter: 2019-01 through 2019-12)
JOIN (
  SELECT date('2019-01-01', ('+' || (n) || ' months')) AS mth
  FROM (
    SELECT 0 AS n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL
    SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL
    SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10 UNION ALL SELECT 11
  )
) m ON 1=1
LEFT JOIN (
  -- receipts per product-month: sum of purchases.qty where purchased in that month
  SELECT
    product_id,
    strftime('%Y-%m', purchased) AS year_month,
    SUM(qty) AS receipts
  FROM purchases
  GROUP BY product_id, strftime('%Y-%m', purchased)
) r ON r.product_id = p.id AND r.year_month = strftime('%Y-%m', m.mth)
LEFT JOIN (
  -- shipments per product-month: sum of orderlines.qty where orders.ordered in that month
  SELECT
    ol.product_id,
    strftime('%Y-%m', o.ordered) AS year_month,
    SUM(ol.qty) AS shipments
  FROM orderlines ol
  JOIN orders o ON o.id = ol.order_id
  GROUP BY ol.product_id, strftime('%Y-%m', o.ordered)
) s ON s.product_id = p.id AND s.year_month = strftime('%Y-%m', m.mth)
```

---

**Skill `product_minimum_levels`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `product_id` |
| output columns | `product_id`, `minimum_required_level` |
| source tables | `product_minimums` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `monthly_inventory_recursive_2019` |
| validated_on | — |
| counter_examples | 0 |

_The minimum required inventory level for each product (used to determine restocking)._

```sql
SELECT
  pm.product_id AS product_id,
  COALESCE(pm.qty_minimum, 0.0) AS minimum_required_level
FROM product_minimums pm
```

---

**Skill `monthly_inventory_recursive_2019`** — category `REC`

| field | value |
|---|---|
| grain (one row per) | `product_id`, `year_month` |
| output columns | `product_id`, `year_month`, `beginning_inventory`, `ending_inventory`, `minimum_required_level`, `abs_diff` |
| source tables | `products`, `monthly_receipts_and_shipments_2019`, `product_minimum_levels`, `initial_december_end_inventory` |
| depends_on (builds on) | `monthly_receipts_and_shipments_2019`, `product_minimum_levels`, `initial_december_end_inventory` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each product, compute the recursive monthly inventory for 2019: beginning_inventory is prior month's ending_inventory (starting from Dec 2018 ending inventory); ending_inventory = beginning_inventory + receipts - shipments; if ending_inventory < minimum_required_level then set ending_inventory = minimum_required_level; compute abs_diff = ABS(ending_inventory - minimum_required_level). Produce one row per product-month for 2019._

```sql
SELECT
  p.id AS product_id,
  -- year_month in format 'YYYY-MM-01' for each month of 2019 will be derived by caller; here expose month identifiers by joining receipts/shipments and allowing months to be supplied.
  m.year_month AS year_month,
  -- beginning_inventory: prior month's ending inventory. We compute iterative by starting from initial_december_end_inventory and adding cumulative receipts - shipments up to prior month.
  COALESCE(
    idei.dec_2018_ending_inventory
    + IFNULL((
        SELECT SUM(r.receipts - r.shipments)
        FROM monthly_receipts_and_shipments_2019 AS r
        WHERE r.product_id = p.id
          AND r.year_month < m.year_month
      ), 0.0),
    0.0
  ) AS beginning_inventory,
  -- raw ending before applying minimum: beginning + receipts - shipments for this month
  (
    COALESCE(
      idei.dec_2018_ending_inventory
      + IFNULL((
          SELECT SUM(r.receipts - r.shipments)
          FROM monthly_receipts_and_shipments_2019 AS r
          WHERE r.product_id = p.id
            AND r.year_month < m.year_month
        ), 0.0),
      0.0
    )
    + IFNULL(mrs.receipts, 0.0)
    - IFNULL(mrs.shipments, 0.0)
  ) AS raw_ending_inventory,
  -- minimum_required_level from product_minimum_levels view
  COALESCE(pml.minimum_required_level, 0.0) AS minimum_required_level,
  -- ending_inventory after enforcing minimum
  CASE
    WHEN (
      COALESCE(
        idei.dec_2018_ending_inventory
        + IFNULL((
            SELECT SUM(r.receipts - r.shipments)
            FROM monthly_receipts_and_shipments_2019 AS r
            WHERE r.product_id = p.id
              AND r.year_month < m.year_month
          ), 0.0),
        0.0
      )
      + IFNULL(mrs.receipts, 0.0)
      - IFNULL(mrs.shipments, 0.0)
    ) < COALESCE(pml.minimum_required_level, 0.0)
    THEN COALESCE(pml.minimum_required_level, 0.0)
    ELSE (
      COALESCE(
        idei.dec_2018_ending_inventory
        + IFNULL((
            SELECT SUM(r.receipts - r.shipments)
            FROM monthly_receipts_and_shipments_2019 AS r
            WHERE r.product_id = p.id
              AND r.year_month < m.year_month
          ), 0.0),
        0.0
      )
      + IFNULL(mrs.receipts, 0.0)
      - IFNULL(mrs.shipments, 0.0)
    )
  END AS ending_inventory,
  -- abs_diff between ending_inventory and minimum_required_level
  ABS(
    CASE
      WHEN (
        COALESCE(
          idei.dec_2018_ending_inventory
          + IFNULL((
              SELECT SUM(r.receipts - r.shipments)
              FROM monthly_receipts_and_shipments_2019 AS r
              WHERE r.product_id = p.id
                AND r.year_month < m.year_month
            ), 0.0),
          0.0
        )
        + IFNULL(mrs.receipts, 0.0)
        - IFNULL(mrs.shipments, 0.0)
      ) < COALESCE(pml.minimum_required_level, 0.0)
      THEN COALESCE(pml.minimum_required_level, 0.0)
      ELSE (
        COALESCE(
          idei.dec_2018_ending_inventory
          + IFNULL((
              SELECT SUM(r.receipts - r.shipments)
              FROM monthly_receipts_and_shipments_2019 AS r
              WHERE r.product_id = p.id
                AND r.year_month < m.year_month
            ), 0.0),
          0.0
        )
        + IFNULL(mrs.receipts, 0.0)
        - IFNULL(mrs.shipments, 0.0)
      )
    END
    - COALESCE(pml.minimum_required_level, 0.0)
  ) AS abs_diff
FROM products AS p
-- ensure every product-month for 2019 is available by selecting distinct year_months from monthly_receipts_and_shipments_2019
JOIN (
  SELECT DISTINCT year_month FROM monthly_receipts_and_shipments_2019
) AS m ON 1=1
LEFT JOIN monthly_receipts_and_shipments_2019 AS mrs
  ON mrs.product_id = p.id AND mrs.year_month = m.year_month
LEFT JOIN product_minimum_levels AS pml
  ON pml.product_id = p.id
LEFT JOIN initial_december_end_inventory AS idei
  ON idei.product_id = p.id
```

---
