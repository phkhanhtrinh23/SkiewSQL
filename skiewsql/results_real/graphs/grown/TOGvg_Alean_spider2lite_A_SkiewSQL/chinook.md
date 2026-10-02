# Skill graph — `chinook` (2 skills)

**Skill `artist_total_sales`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `ArtistId` |
| output columns | `artist_id`, `total_amount` |
| source tables | `invoice_items`, `tracks`, `albums` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_total amount spent per artist across all album purchases_

```sql
SELECT
    a.ArtistId AS artist_id,
    SUM(ii.UnitPrice * ii.Quantity) AS total_amount
FROM invoice_items ii
JOIN tracks t ON ii.TrackId = t.TrackId
JOIN albums a ON t.AlbumId = a.AlbumId
GROUP BY a.ArtistId
```

---

**Skill `filtered_customer_purchases`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `purchase_id` |
| output columns | `customer_id`, `purchase_id`, `customer_first_name`, `purchase_amount` |
| source tables | `customers`, `invoices` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_joins customer first names, purchase amounts, and artist sales aggregates, applying filters for the top artist and purchase amount threshold_

```sql
SELECT c.CustomerId AS customer_id, i.InvoiceId AS purchase_id, c.FirstName AS customer_first_name, i.Total AS purchase_amount
FROM customers c
JOIN invoices i ON c.CustomerId = i.CustomerId
```

---
