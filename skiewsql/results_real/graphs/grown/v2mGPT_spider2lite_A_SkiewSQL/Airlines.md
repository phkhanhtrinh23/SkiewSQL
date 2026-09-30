# Skill graph — `Airlines` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `flights`, `airports_data` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute the maximum great-circle distance (in kilometers) among all flight routes where Abakan is either the departure city or the arrival city, using the Haversine formula on the coordinates of_

```sql
SELECT
  f.flight_id,
  f.departure_airport,
  f.arrival_airport,
  a_dep.airport_name AS departure_airport_name,
  a_dep.city AS departure_city,
  a_dep.coordinates AS departure_coordinates,
  a_arr.airport_name AS arrival_airport_name,
  a_arr.city AS arrival_city,
  a_arr.coordinates AS arrival_coordinates
FROM flights f
LEFT JOIN airports_data a_dep
  ON f.departure_airport = a_dep.airport_code
LEFT JOIN airports_data a_arr
  ON f.arrival_airport = a_arr.airport_code
WHERE
  -- keep routes where either endpoint has city 'Abakan' (city stored as jsonb)
  ( (a_dep.city ->> 'en') = 'Abakan' )
  OR
  ( (a_arr.city ->> 'en') = 'Abakan' )
  -- Note: do not filter out NULL coordinates here; downstream step will exclude invalid coords
```

---
