# Skill graph — `California_Traffic_Collision` (3 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `parties`, `collisions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute the fatality rate for motorcyclist-involved collisions separately for collisions in which parties were recorded as wearing helmets and collisions in which parties were recorded as not we_

```sql
SELECT
  p.id AS party_id,
  p.case_id AS case_id,
  p.party_number AS party_number,
  p.party_type AS party_type,
  p.party_safety_equipment_1 AS party_safety_equipment_1,
  p.party_safety_equipment_2 AS party_safety_equipment_2,
  p.party_age AS party_age,
  p.party_sex AS party_sex,
  p.party_number_killed AS party_number_killed,
  p.party_number_injured AS party_number_injured,
  c.collision_date AS collision_date,
  c.collision_time AS collision_time,
  c.killed_victims AS collision_killed_victims,
  c.injured_victims AS collision_injured_victims
FROM parties p
JOIN collisions c
  ON p.case_id = c.case_id
WHERE p.party_type IS NOT NULL
  AND c.case_id IS NOT NULL
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `collisions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Find the year (or years) in which the two most common causes of traffic accidents for that year are different from the two most common causes in every other year.
Required outputs: year
Filters:_

```sql
SELECT
  collisions.collision_date,
  collisions.primary_collision_factor,
  collisions.pcf_violation_category,
  collisions.pcf_violation,
  collisions.case_id
FROM collisions
WHERE collisions.collision_date IS NOT NULL
```

---

**Skill `chunk_view_0_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `collisions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute the decrease in percentage points between 2011 and 2021 of the share of annual road incidents for the single primary collision factor violation category that was the most common cause of_

```sql
SELECT
  collisions.pcf_violation_category,
  collisions.collision_date,
  collisions.case_id,
  collisions.collision_time,
  collisions.killed_victims,
  collisions.injured_victims,
  collisions.party_count,
  collisions.primary_collision_factor,
  collisions.pcf_violation,
  collisions.pcf_violation_code,
  collisions.collision_severity,
  collisions.latitude,
  collisions.longitude
FROM collisions
WHERE collisions.pcf_violation_category IS NOT NULL
  AND collisions.collision_date IS NOT NULL
```

---
