# order_payments_aggregated
Aggregate metrics about payments grouped at the order level. Answers questions like "per order, how many payment rows, total/avg payment value, installments range, and most common payment type?"

## SQL view
```sql
SELECT
  order_id,
  COUNT(*) AS payment_rows_count,
  SUM(payment_value) AS payment_value_sum,
  AVG(payment_value) AS payment_value_avg,
  MIN(payment_installments) AS payment_installments_min,
  MAX(payment_installments) AS payment_installments_max,
  -- most common payment_type per order derived by ordering types by frequency and picking the first via GROUP_CONCAT trick
  (SELECT split.value
   FROM (
     SELECT
       payment_type || '|' || COUNT(*) AS kt,
       payment_type AS value
     FROM order_payments op2
     WHERE op2.order_id = op.order_id
     GROUP BY payment_type
     ORDER BY COUNT(*) DESC, payment_type ASC
   ) AS split
   LIMIT 1) AS payment_type_mode
FROM order_payments op
GROUP BY order_id
```

## When to use
- When you need per-order payment-level aggregates (one row per order): total payment value, average payment value, count of payment rows, min/max installments.
- To find orders whose payments used a particular payment_type_mode (most frequent payment_type for that order).
- When joining order-level payment summaries to orders, customers, or order-level item aggregates without duplicating payment metrics (see Composition).
- For dashboards showing payment counts/sums per order, or downstream aggregation to customer-level by further grouping on customer_id (with care).

## When not to use
- Do not reuse this when you need payment-row-level detail (payment_id, timestamp, raw payment_type per row) — this view is aggregated to order_id and loses row-level identity.
- Do not use if your desired grain is finer than order_id (for example, order_item_id or payment_id) — reusing it will produce the wrong grain and may hide multiplicity.
- Do not use to compute per-customer payment totals unless you explicitly join to orders (to get customer_id) and then re-aggregate by customer_id; directly grouping this view by customer_id without re-aggregation risks mis-counting if orders are joined multiple times.
- Do not use if you need time-windowed payment aggregates (e.g., payments within a date range using payment timestamp) unless order_payments has already been filtered by that date range — this view has no built-in temporal filter and will return totals over all rows for the order.
- Do not use when you need a strict tie-break on payment type different from alphabetical order: the modal payment_type tie-breaker here uses payment_type ASC (alphabetical) for ties. If you need deterministic tie-break by e.g. most recent payment row, this view gives a different result.

## Output schema
- order_id — the order identifier (grouping key).
- payment_rows_count — COUNT(*) of rows in order_payments for that order (derived from order_payments.*).
- payment_value_sum — SUM(payment_value) over order_payments rows for that order.
- payment_value_avg — AVG(payment_value) over order_payments rows for that order.
- payment_installments_min — MIN(payment_installments) over order_payments rows for that order.
- payment_installments_max — MAX(payment_installments) over order_payments rows for that order.
- payment_type_mode — the most frequent payment_type for that order (derived by counting payment_type occurrences per order; ties broken by payment_type ASC).

## Notation
- Grounded columns (as referenced in the view):
  - order_payments.order_id
  - order_payments.payment_value
  - order_payments.payment_installments
  - order_payments.payment_type
- Metrics:
  - payment_rows_count = COUNT(*) over order_payments rows grouped by order_id
  - payment_value_sum = SUM(order_payments.payment_value) grouped by order_id
  - payment_value_avg = AVG(order_payments.payment_value) grouped by order_id
  - payment_installments_min = MIN(order_payments.payment_installments) grouped by order_id
  - payment_installments_max = MAX(order_payments.payment_installments) grouped by order_id
  - payment_type_mode = argmax(payment_type frequency, tie-break payment_type ASC) per order_id
- Key and grain:
  - Grain: tuple ['order_id']
  - Primary key for this view: order_id (one row per order_id)

## Composition
- Safe joins (do not duplicate this view's measures):
  - Join this view to an orders-level view or table on order_id (one-to-one cardinality expected when the orders source has one row per order_id). Example: orders_clean_timestamps AS o JOIN order_payments_aggregated AS p ON o.order_id = p.order_id. This is cardinality-safe because order_payments_aggregated is one row per order_id and orders_clean_timestamps is expected to be one row per order_id.
  - Join to order-level aggregates (order_reviews_per_order, orders_with_items_payments_reviews, customer_order_counts after re-aggregation) on order_id — ensure the sibling is also at order_id grain or you re-aggregate after join.
- Joins that will duplicate measures (avoid unless you re-aggregate):
  - Do NOT join this view directly to order_items_with_product_and_seller (which is at order_item-level with potentially multiple rows per order_id) without re-aggregation. Joining without aggregation will replicate payment metrics across each item row, inflating counts and sums.
  - If you must combine with item-level data, either:
    - Aggregate item-level rows to order_id first, then join order_id-to-order_id (safe), or
    - Join and then group by order_id, computing SUM(payment_value_sum) is wrong — instead use MAX(payment_value_sum) or re-aggregate original payment rows. Correct pattern: join order_items_with_product_and_seller aggregated to order_id (e.g., items_count, items_price_sum) with order_payments_aggregated on order_id.
- Example safe query:
  - "List orders with order purchase timestamp, total item price, and total payment value":
    SELECT o.order_id, o.order_purchase_timestamp, it.items_price_sum, p.payment_value_sum
    FROM orders_clean_timestamps o
    LEFT JOIN (SELECT order_id, SUM(price) AS items_price_sum FROM order_items_with_product_and_seller GROUP BY order_id) it USING(order_id)
    LEFT JOIN order_payments_aggregated p USING(order_id);
  - This is safe because each joined subquery is aggregated to order_id before the join, preserving one-row-per-order_id cardinality.

## Comparison
- Use orders_with_items_payments_reviews instead when:
  - You need a wide denormalized order-level view that already includes items and reviews aggregates alongside payment aggregates. It has the same payment metrics (payment_rows_count, payment_value_sum) but also includes items_count, items_price_sum and reviews_count — use it for convenience when you need those combined columns without composing multiple joins.
- Use order_reviews_per_order instead when:
  - You only need reviews aggregates per order (reviews_count, review_score_avg). That view is narrower and focused on reviews; join it with order_payments_aggregated when you need both payments and reviews at order grain.
- Use order_items_with_product_and_seller instead when:
  - You require item-level detail (order_item_id, product attributes). That view is lower-grain (order_item-level); do not substitute order_payments_aggregated for item-level analysis.
- Use customer_order_counts or customer_ranking_by_recency_frequency when:
  - Your target grain is customer_id (customer-level aggregates). These sibling views are already at customer grain; if you start from order_payments_aggregated to produce customer totals, be sure to join to orders to get customer_id and then re-aggregate by customer_id (to avoid double-counting when orders are duplicated).

## Dialect notes
This view is written for SQLite and uses SQLite-specific string concatenation (payment_type || '|' || COUNT(*)) and a correlated scalar subquery returning one row with LIMIT 1. Differences across dialects:

- SQLite (current view):
  - String concat: payment_type || '|' || COUNT(*)
  - LIMIT within scalar subquery: ... LIMIT 1
  - AVG, SUM, COUNT, MIN, MAX are available as-is.

- PostgreSQL / Snowflake:
  - String concat: use payment_type || '|' || COUNT(*) (PostgreSQL supports ||). However, ordering a derived inline SELECT with non-aggregated COUNT(*) in the select-list requires COUNT(*) to be computed in the grouped subquery exactly as shown. LIMIT 1 is supported.
  - Correlated subquery with ORDER BY and LIMIT 1 is supported. No syntactic change needed for the approach used here.
  - If using ARRAY_AGG or DISTINCT ON for modal value:
    - PostgreSQL alternative (more explicit): SELECT (ARRAY_AGG(payment_type ORDER BY cnt DESC, payment_type ASC))[1] FROM (SELECT payment_type, COUNT(*) AS cnt FROM order_payments WHERE order_id = op.order_id GROUP BY payment_type) t

- BigQuery:
  - String concat: use CONCAT(payment_type, '|', CAST(COUNT(*) AS STRING)) if you mimic the same trick.
  - BigQuery does not allow LIMIT inside a scalar subquery without ORDER BY in the same way; a recommended pattern is:
    - Use ARRAY_AGG with ORDER BY and SAFE_OFFSET(0):
      (SELECT ARRAY_AGG(payment_type ORDER BY cnt DESC, payment_type ASC LIMIT 1)[OFFSET(0)]
       FROM (SELECT payment_type, COUNT(*) AS cnt FROM order_payments op2 WHERE op2.order_id = op.order_id GROUP BY payment_type))
    - Or use ANY_VALUE with STRUCT ordering: (SELECT payment_type FROM (SELECT payment_type, COUNT(*) AS cnt FROM order_payments WHERE order_id = op.order_id GROUP BY payment_type ORDER BY cnt DESC, payment_type ASC LIMIT 1))
  - COUNT(*) inside a concatenation must be cast to STRING if concatenating to text.

Summary: the modal-value technique using an ordered subquery with LIMIT 1 is portable, but the exact string concatenation and scalar-subquery idioms may need small adjustments: BigQuery prefers ARRAY_AGG/LIMIT or SELECT ... LIMIT 1 with explicit casting; PostgreSQL/Snowflake generally accept the SQLite-style correlated subquery and || concatenation.