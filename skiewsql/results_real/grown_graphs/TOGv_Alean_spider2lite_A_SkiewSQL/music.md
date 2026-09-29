# Skill graph — `music` (2 skills)

**Skill `track_durations`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `track` |
| output columns | `track_id`, `duration_minutes` |
| source tables | `Track` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `classified_tracks` |
| validated_on | — |
| counter_examples | 0 |

_one row per track with duration converted to minutes_

```sql
SELECT "TrackId" AS track_id, "Milliseconds" / 60000.0 AS duration_minutes
FROM "Track"
```

---

**Skill `classified_tracks`** — category `SEM`

| field | value |
|---|---|
| grain (one row per) | `track` |
| output columns | `track_id`, `duration_minutes`, `category` |
| source tables | `track_durations` |
| depends_on (builds on) | `track_durations` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_one row per track with category assigned based on global minimum, average, and maximum duration thresholds_

```sql
SELECT td.track_id, td.duration_minutes, CASE WHEN td.duration_minutes <= (SELECT MIN(duration_minutes) FROM track_durations) THEN 'Short' WHEN td.duration_minutes <= (SELECT AVG(duration_minutes) FROM track_durations) THEN 'Medium' WHEN td.duration_minutes <= (SELECT MAX(duration_minutes) FROM track_durations) THEN 'Long' ELSE 'Very Long' END AS category FROM track_durations td
```

---
