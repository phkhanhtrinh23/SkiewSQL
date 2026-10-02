# Skill graph — `Airlines` (1 skills)

**Skill `routes`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `route_id` |
| output columns | `route_id`, `departure_city`, `destination_city`, `distance_km` |
| source tables | `flights`, `airports_data` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_base cohort of all routes containing departure city, destination city, and distance in kilometers_

```sql
SELECT f.flight_id AS route_id, a1.city->>'en' AS departure_city, a2.city->>'en' AS destination_city, 0.0 AS distance_km
FROM flights f
JOIN airports_data a1 ON f.departure_airport = a1.airport_code
JOIN airports_data a2 ON f.arrival_airport = a2.airport_code
```

---
