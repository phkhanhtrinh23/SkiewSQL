# Skill graph — `chinook` (2 skills)

**Skill `artist_sales`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `Name` |
| output columns | `artist`, `total_sales` |
| source tables | `artists`, `albums`, `tracks`, `invoice_items` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_total sales amount aggregated per artist_

```sql
SELECT a.Name AS artist, SUM(ii.UnitPrice * ii.Quantity) AS total_sales FROM artists a JOIN albums ab ON a.ArtistId = ab.ArtistId JOIN tracks t ON ab.AlbumId = t.AlbumId JOIN invoice_items ii ON t.TrackId = ii.TrackId GROUP BY a.Name
```

---

**Skill `filtered_purchases`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `customer`, `purchase` |
| output columns | `customer_first_name`, `amount_spent` |
| source tables | `customers`, `invoices`, `invoice_items` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_joins customer first names and purchase amounts with the top-selling artist, filtered by a specified amount threshold_

```sql
SELECT c.FirstName AS customer_first_name, ii.UnitPrice * ii.Quantity AS amount_spent
FROM customers c
JOIN invoices i ON c.CustomerId = i.CustomerId
JOIN invoice_items ii ON i.InvoiceId = ii.InvoiceId
```

---
