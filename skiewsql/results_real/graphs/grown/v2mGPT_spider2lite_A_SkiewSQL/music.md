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

_Task: For each track, compute its duration in minutes, classify the track as Short, Medium, or Long using the provided External knowledge definition (where Short = duration between minimum and midpoin_

```sql
SELECT
    t."TrackId",
    t."Name" AS "TrackName",
    t."Milliseconds",
    (t."Milliseconds" / 60000.0) AS "DurationMinutes",
    t."UnitPrice",
    il."InvoiceLineId",
    il."InvoiceId",
    il."Quantity",
    (il."UnitPrice" * il."Quantity") AS "LineRevenue"
FROM "Track" t
JOIN "InvoiceLine" il ON il."TrackId" = t."TrackId"
WHERE t."Milliseconds" IS NOT NULL
  AND il."UnitPrice" IS NOT NULL
  AND il."Quantity" IS NOT NULL
```

---
