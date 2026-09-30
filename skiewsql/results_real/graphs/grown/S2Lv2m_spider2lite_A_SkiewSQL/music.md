# Skill graph — `music` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Track`, `InvoiceLine` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each track, compute its duration in minutes, classify each track as Short, Medium, or Long according to the provided Music Length Types definition based on the distribution of durations (usi_

```sql
SELECT
  t.TrackId,
  t.Name AS TrackName,
  t.Milliseconds,
  (t.Milliseconds / 60000.0) AS duration_minutes,
  il.InvoiceLineId,
  il.InvoiceId,
  il.UnitPrice AS InvoiceLineUnitPrice,
  il.Quantity AS InvoiceLineQuantity,
  (il.UnitPrice * il.Quantity) AS invoice_line_revenue
FROM
  "Track" t
LEFT JOIN
  "InvoiceLine" il
ON
  t.TrackId = il.TrackId
WHERE
  t.Milliseconds IS NOT NULL
  AND t.Milliseconds > 0
  AND (il.UnitPrice IS NULL OR il.UnitPrice >= 0)
```

---
