# Skill graph — `Airlines` (7 skills)

**Skill `routes_with_abakan`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `route_id` |
| output columns | `route_id`, `from_city`, `to_city`, `from_city_id`, `to_city_id` |
| source tables | `flights`, `airports_data` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `city_coordinates`, `route_cities_join`, `raw_routes_with_cities_and_distance` |
| validated_on | — |
| counter_examples | 0 |

_Select routes where either the departure city or arrival city is Abakan, keeping route identifiers and the from/to city keys or ids._

```sql
SELECT
  flights.flight_id AS route_id,
  CASE
    WHEN (airports_data_from.city->>'en') = 'Abakan' THEN airports_data_from.city->>'en'
    WHEN (airports_data_to.city->>'en') = 'Abakan' THEN airports_data_from.city->>'en'
    ELSE airports_data_from.city->>'en'
  END AS from_city,
  CASE
    WHEN (airports_data_to.city->>'en') = 'Abakan' THEN airports_data_to.city->>'en'
    WHEN (airports_data_from.city->>'en') = 'Abakan' THEN airports_data_to.city->>'en'
    ELSE airports_data_to.city->>'en'
  END AS to_city,
  airports_data_from.airport_code AS from_city_id,
  airports_data_to.airport_code AS to_city_id
FROM flights
JOIN airports_data AS airports_data_from ON flights.departure_airport = airports_data_from.airport_code
JOIN airports_data AS airports_data_to ON flights.arrival_airport = airports_data_to.airport_code
WHERE (airports_data_from.city->>'en') = 'Abakan' OR (airports_data_to.city->>'en') = 'Abakan'
```

---

**Skill `city_coordinates`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `city_id` |
| output columns | `city_id`, `city_name`, `latitude`, `longitude` |
| source tables | `airports_data` |
| depends_on (builds on) | `routes_with_abakan` |
| depended-on by (builds on this) | `route_cities_join` |
| validated_on | — |
| counter_examples | 0 |

_Retrieve city coordinate records (decimal latitude and longitude) for cities referenced by routes; one row per city._

```sql
SELECT
  r.from_city_id AS city_id,
  json_extract(a.city, '$.en') AS city_name,
  CAST(NULLIF(substr(trim('(' || replace(a.coordinates, ')', '') ), instr(replace(a.coordinates, ')', ''), ',')+1), 0) AS REAL) AS latitude,
  CAST(NULLIF(substr(trim('(' || replace(a.coordinates, ')', '') ), 1, instr(replace(a.coordinates, ')', ''), ',')-1), 0) AS REAL) AS longitude
FROM routes_with_abakan r
JOIN airports_data a
  ON a.airport_code = r.from_city
UNION
SELECT
  r.to_city_id AS city_id,
  json_extract(a.city, '$.en') AS city_name,
  CAST(NULLIF(substr(trim('(' || replace(a.coordinates, ')', '') ), instr(replace(a.coordinates, ')', ''), ',')+1), 0) AS REAL) AS latitude,
  CAST(NULLIF(substr(trim('(' || replace(a.coordinates, ')', '') ), 1, instr(replace(a.coordinates, ')', ''), ',')-1), 0) AS REAL) AS longitude
FROM routes_with_abakan r
JOIN airports_data a
  ON a.airport_code = r.to_city
```

---

**Skill `route_cities_join`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `route_id` |
| output columns | `route_id`, `from_city`, `to_city`, `from_lat`, `from_lon`, `to_lat`, `to_lon` |
| source tables | `routes_with_abakan`, `city_coordinates` |
| depends_on (builds on) | `routes_with_abakan`, `city_coordinates` |
| depended-on by (builds on this) | `route_distances_haversine` |
| validated_on | — |
| counter_examples | 0 |

_Join the filtered routes to the coordinate records for both departure and arrival cities to produce one row per route with both cities' lat/long values; exclude rows where either coordinate is NULL/missing._

```sql
SELECT
  r.route_id,
  r.from_city,
  r.to_city,
  fc.latitude AS from_lat,
  fc.longitude AS from_lon,
  tc.latitude AS to_lat,
  tc.longitude AS to_lon
FROM routes_with_abakan r
JOIN city_coordinates fc ON r.from_city_id = fc.city_id
JOIN city_coordinates tc ON r.to_city_id = tc.city_id
WHERE fc.latitude IS NOT NULL
  AND fc.longitude IS NOT NULL
  AND tc.latitude IS NOT NULL
  AND tc.longitude IS NOT NULL
```

---

**Skill `route_distances_haversine`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `route_id` |
| output columns | `route_id`, `distance_km` |
| source tables | `route_cities_join` |
| depends_on (builds on) | `route_cities_join` |
| depended-on by (builds on this) | `raw_routes_with_cities_and_distance` |
| validated_on | — |
| counter_examples | 0 |

_Compute the great-circle distance in kilometers between the from and to coordinates using the Haversine formula for each route row (one row per route)._

```sql
SELECT
  rcj.route_id AS route_id,
  -- Haversine formula
  (
    6371.0 * 2 * 
    ASIN(
      SQRT(
        POWER(SIN(RADIANS((rcj.to_lat - rcj.from_lat) / 2.0)), 2)
        + COS(RADIANS(rcj.from_lat)) * COS(RADIANS(rcj.to_lat))
          * POWER(SIN(RADIANS((rcj.to_lon - rcj.from_lon) / 2.0)), 2)
      )
    )
  ) AS distance_km
FROM route_cities_join rcj
```

---

**Skill `raw_routes_with_cities_and_distance`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `route_id` |
| output columns | `route_id`, `origin_city_id`, `destination_city_id`, `distance` |
| source tables | `routes_with_abakan`, `route_distances_haversine` |
| depends_on (builds on) | `routes_with_abakan`, `route_distances_haversine` |
| depended-on by (builds on this) | `cleaned_valid_routes` |
| validated_on | — |
| counter_examples | 0 |

_All route records joined to their origin and destination city identifiers and the route distance value as provided (distance may be NULL). One row per raw route between two cities._

```sql
SELECT
  r.route_id,
  r.from_city_id        AS origin_city_id,
  r.to_city_id          AS destination_city_id,
  d.distance_km         AS distance
FROM routes_with_abakan AS r
LEFT JOIN route_distances_haversine AS d USING (route_id)
```

---

**Skill `cleaned_valid_routes`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `route_id` |
| output columns | `route_id`, `city_a_id`, `city_b_id`, `distance` |
| source tables | `raw_routes_with_cities_and_distance` |
| depends_on (builds on) | `raw_routes_with_cities_and_distance` |
| depended-on by (builds on this) | `avg_distance_per_city_pair` |
| validated_on | — |
| counter_examples | 0 |

_Normalize and filter routes: canonicalize city pair ordering so each unordered city pair is represented consistently (e.g., city_a = min(origin,destination), city_b = max(...)); exclude rows with NULL or invalid distances or missing city identifiers._

```sql
SELECT
  -- route_id from available route sources; prefer raw_routes_with_cities_and_distance if present
  raw.route_id AS route_id,
  -- canonicalize city ids: smaller id as city_a_id, larger as city_b_id
  CASE
    WHEN raw.origin_city_id IS NOT NULL AND raw.destination_city_id IS NOT NULL AND raw.origin_city_id <= raw.destination_city_id
      THEN raw.origin_city_id
    ELSE raw.destination_city_id
  END AS city_a_id,
  CASE
    WHEN raw.origin_city_id IS NOT NULL AND raw.destination_city_id IS NOT NULL AND raw.origin_city_id <= raw.destination_city_id
      THEN raw.destination_city_id
    ELSE raw.origin_city_id
  END AS city_b_id,
  -- use distance from the raw routes if numeric and positive; otherwise NULL (will be filtered out by WHERE)
  raw.distance AS distance
FROM
  raw_routes_with_cities_and_distance AS raw
WHERE
  -- exclude missing city identifiers
  raw.origin_city_id IS NOT NULL
  AND raw.destination_city_id IS NOT NULL
  -- exclude invalid distances: must be numeric and positive
  AND raw.distance IS NOT NULL
  AND raw.distance > 0
```

---

**Skill `avg_distance_per_city_pair`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `city_a_id`, `city_b_id` |
| output columns | `city_a_id`, `city_b_id`, `avg_distance` |
| source tables | `cleaned_valid_routes` |
| depends_on (builds on) | `cleaned_valid_routes` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each unique unordered city pair (city_a_id, city_b_id), compute the average of distance across all cleaned routes between them. One row per unique city pair._

```sql
SELECT
  CASE
    WHEN r.city_a_id <= r.city_b_id THEN r.city_a_id
    ELSE r.city_b_id
  END AS city_a_id,
  CASE
    WHEN r.city_a_id <= r.city_b_id THEN r.city_b_id
    ELSE r.city_a_id
  END AS city_b_id,
  AVG(r.distance) AS avg_distance
FROM cleaned_valid_routes r
GROUP BY
  CASE
    WHEN r.city_a_id <= r.city_b_id THEN r.city_a_id
    ELSE r.city_b_id
  END,
  CASE
    WHEN r.city_a_id <= r.city_b_id THEN r.city_b_id
    ELSE r.city_a_id
  END
```

---
