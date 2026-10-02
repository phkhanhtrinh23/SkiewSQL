# Skill graph — `chinook` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `invoice_items`, `invoices`, `customers`, `tracks`, `albums`, `artists` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Find the first names of customers and the amounts they spent on albums by the best-selling artist, but only include customers whose total spending on that artist's albums is less than $1. Requir_

```sql
SELECT
  c.CustomerId,
  c.FirstName,
  ii.InvoiceId,
  ii.InvoiceLineId,
  ii.TrackId,
  ii.UnitPrice,
  ii.Quantity,
  (ii.UnitPrice * ii.Quantity) AS LineAmount,
  t.AlbumId,
  a.ArtistId,
  ar.Name AS ArtistName
FROM invoice_items ii
JOIN invoices i ON ii.InvoiceId = i.InvoiceId
JOIN customers c ON i.CustomerId = c.CustomerId
JOIN tracks t ON ii.TrackId = t.TrackId
JOIN albums a ON t.AlbumId = a.AlbumId
JOIN artists ar ON a.ArtistId = ar.ArtistId
```

---
