# Skill graph — `music` (2 skills)

**Skill `classified_tracks`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `track` |
| output columns | `track`, `duration_minutes`, `category` |
| source tables | `Track` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `category_aggregates` |
| validated_on | — |
| counter_examples | 0 |

_joins track records with global duration thresholds, converts duration to minutes, and applies the classification rule to assign a category._

```sql
SELECT 
    TrackId AS track,
    Milliseconds / 60000.0 AS duration_minutes,
    CASE 
        WHEN Milliseconds / 60000.0 < 3 THEN 'Short'
        WHEN Milliseconds / 60000.0 <= 5 THEN 'Medium'
        ELSE 'Long'
    END AS category
FROM Track
```

---

**Skill `category_aggregates`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `category` |
| output columns | `category`, `min_duration_minutes`, `max_duration_minutes`, `total_revenue` |
| source tables | `classified_tracks`, `InvoiceLine` |
| depends_on (builds on) | `classified_tracks` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_groups the classified tracks by category to compute minimum duration, maximum duration, and total revenue._

```sql
SELECT 
    ct.category,
    MIN(ct.duration_minutes) AS min_duration_minutes,
    MAX(ct.duration_minutes) AS max_duration_minutes,
    SUM(il.UnitPrice * il.Quantity) AS total_revenue
FROM classified_tracks ct
JOIN InvoiceLine il ON ct.track = il.TrackId
GROUP BY ct.category
```

---
