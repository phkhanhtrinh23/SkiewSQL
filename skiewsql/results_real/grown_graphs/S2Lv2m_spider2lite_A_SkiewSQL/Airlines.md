# Skill graph — `Airlines` (2 skills)

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

_Task: Compute the maximum flight route distance (in kilometers) among all routes where either the departure city or the arrival city is Abakan, using the Haversine formula as described.
Required outpu_

```sql
SELECT
  f.flight_id,
  f.flight_no,
  f.departure_airport,
  f.arrival_airport,
  a_dep.airport_name AS dep_airport_name,
  a_dep.city     AS dep_city,
  a_dep.coordinates AS dep_coordinates,
  a_arr.airport_name AS arr_airport_name,
  a_arr.city     AS arr_city,
  a_arr.coordinates AS arr_coordinates
FROM flights f
LEFT JOIN airports_data a_dep
  ON f.departure_airport = a_dep.airport_code
LEFT JOIN airports_data a_arr
  ON f.arrival_airport = a_arr.airport_code
WHERE
  -- include routes where either departure or arrival city JSON contains "Abakan" in its "en" field
  (
    (a_dep.city IS NOT NULL AND (a_dep.city->>'en') = 'Abakan')
    OR
    (a_arr.city IS NOT NULL AND (a_arr.city->>'en') = 'Abakan')
  )
  -- ensure coordinates exist for both endpoints so distance can be computed later
  AND a_dep.coordinates IS NOT NULL
  AND a_arr.coordinates IS NOT NULL
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `flights`, `airports_data` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute, for each unique unordered city pair (city A, city B), the average Haversine distance across all routes between those two cities and then bucket each pair into distance ranges 0, 1000, 2_

```sql
SELECT
    f.flight_id,
    f.departure_airport,
    f.arrival_airport,
    a_from.airport_code AS from_airport_code,
    a_from.city AS from_city,
    a_from.coordinates AS from_coordinates,
    a_arr.airport_code AS to_airport_code,
    a_arr.city AS to_city,
    a_arr.coordinates AS to_coordinates
FROM
    flights f
JOIN
    airports_data a_from
    ON f.departure_airport = a_from.airport_code
JOIN
    airports_data a_arr
    ON f.arrival_airport = a_arr.airport_code
WHERE
    f.departure_airport IS NOT NULL
    AND f.arrival_airport IS NOT NULL
    AND a_from.coordinates IS NOT NULL
    AND a_arr.coordinates IS NOT NULL
```

---
