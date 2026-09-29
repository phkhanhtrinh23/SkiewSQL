# Skill graph — `music` (4 skills)

**Skill `tracks_with_duration_minutes_and_revenue`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `track_id` |
| output columns | `track_id`, `duration_minutes`, `revenue` |
| source tables | `Track`, `InvoiceLine` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `global_duration_stats`, `tracks_with_length_category` |
| validated_on | — |
| counter_examples | 0 |

_Project each track with its duration converted to minutes and its revenue preserved; keep one row per track for downstream classification and aggregation._

```sql
SELECT
  Track.TrackId AS track_id,
  (Track.Milliseconds / 60000.0) AS duration_minutes,
  COALESCE((
    SELECT SUM(InvoiceLine.UnitPrice * InvoiceLine.Quantity)
    FROM InvoiceLine
    WHERE InvoiceLine.TrackId = Track.TrackId
  ), 0.0) AS revenue
FROM Track
```

---

**Skill `global_duration_stats`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `global` |
| output columns | `min_duration_global`, `avg_duration_global`, `max_duration_global`, `midpoint1`, `midpoint2` |
| source tables | `Track`, `tracks_with_duration_minutes_and_revenue` |
| depends_on (builds on) | `tracks_with_duration_minutes_and_revenue` |
| depended-on by (builds on this) | `tracks_with_length_category` |
| validated_on | — |
| counter_examples | 0 |

_Compute global summary statistics across all tracks: minimum, average, and maximum of duration_minutes, plus the two midpoints used to partition lengths._

```sql
SELECT
  MIN(t.duration_minutes) AS min_duration_global,
  AVG(t.duration_minutes) AS avg_duration_global,
  MAX(t.duration_minutes) AS max_duration_global,
  -- midpoint1: midpoint between min and avg
  (MIN(t.duration_minutes) + AVG(t.duration_minutes)) / 2.0 AS midpoint1,
  -- midpoint2: midpoint between avg and max
  (AVG(t.duration_minutes) + MAX(t.duration_minutes)) / 2.0 AS midpoint2
FROM tracks_with_duration_minutes_and_revenue t
```

---

**Skill `tracks_with_length_category`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `track_id` |
| output columns | `track_id`, `duration_minutes`, `revenue`, `category` |
| source tables | `Track`, `InvoiceLine` |
| depends_on (builds on) | `tracks_with_duration_minutes_and_revenue`, `global_duration_stats` |
| depended-on by (builds on this) | `category_level_aggregates` |
| validated_on | — |
| counter_examples | 0 |

_For each track (one row per track), attach the global duration stats and apply the Music Length Types rules to assign a category value 'Short', 'Medium', or 'Long' based on duration_minutes and the computed midpoints._

```sql
SELECT
  t.track_id AS track_id,
  t.duration_minutes AS duration_minutes,
  t.revenue AS revenue,
  CASE
    WHEN t.duration_minutes <= g.midpoint1 THEN 'Short'
    WHEN t.duration_minutes > g.midpoint1 AND t.duration_minutes < g.midpoint2 THEN 'Medium'
    ELSE 'Long'
  END AS category
FROM tracks_with_duration_minutes_and_revenue t
CROSS JOIN global_duration_stats g
```

---

**Skill `category_level_aggregates`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `category` |
| output columns | `category`, `min_duration_minutes`, `max_duration_minutes`, `total_revenue` |
| source tables | `tracks_with_length_category` |
| depends_on (builds on) | `tracks_with_length_category` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each category (Short, Medium, Long) compute the minimum and maximum duration_minutes among tracks in that category and the total revenue (sum of revenue) for the category; one row per category._

```sql
SELECT
  t.category AS category,
  MIN(t.duration_minutes) AS min_duration_minutes,
  MAX(t.duration_minutes) AS max_duration_minutes,
  SUM(t.revenue) AS total_revenue
FROM tracks_with_length_category t
GROUP BY t.category
```

---
