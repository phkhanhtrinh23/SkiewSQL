# Skill graph — `chinook` (2 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `invoice_items`, `invoices`, `customers`, `tracks`, `albums`, `artists` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: Find the first names of customers and the amounts they spent on albums by the overall best-selling artist, but only include customers whose total spending on that artist's albums was less than $_

```sql
SELECT
    customers.CustomerId,
    customers.FirstName,
    invoices.InvoiceId,
    invoice_items.InvoiceLineId,
    invoice_items.TrackId,
    tracks.AlbumId,
    albums.ArtistId,
    invoice_items.UnitPrice,
    invoice_items.Quantity,
    invoice_items.UnitPrice * invoice_items.Quantity AS LineTotal
FROM invoice_items
JOIN invoices ON invoice_items.InvoiceId = invoices.InvoiceId
JOIN customers ON invoices.CustomerId = customers.CustomerId
JOIN tracks ON invoice_items.TrackId = tracks.TrackId
JOIN albums ON tracks.AlbumId = albums.AlbumId
JOIN artists ON albums.ArtistId = artists.ArtistId
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `invoices` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute the median of the total sales values, considering only rows for countries where the number of customers is greater than 4.
Required outputs: median_total_sales — a single numeric value r_

```sql
SELECT
  invoices.InvoiceId,
  invoices.CustomerId,
  invoices.InvoiceDate,
  invoices.BillingCountry,
  invoices.Total
FROM invoices
WHERE invoices.Total IS NOT NULL
```

---
