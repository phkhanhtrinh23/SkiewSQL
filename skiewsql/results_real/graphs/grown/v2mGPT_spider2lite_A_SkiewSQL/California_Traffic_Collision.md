# Skill graph — `California_Traffic_Collision` (1 skills)

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

_Task: Compute the fatality rate for motorcycle collisions separated by helmet usage by grouping collisions into two groups (collisions where parties were wearing helmets and collisions where parties w_

```sql
SELECT
  p.case_id,
  p.party_number,
  p.party_type,
  p.party_safety_equipment_1,
  p.party_safety_equipment_2,
  p.party_number_killed,
  p.party_number_injured,
  p.party_sex,
  p.party_age,
  p.vehicle_year,
  p.vehicle_make,
  p.statewide_vehicle_type,
  p.chp_vehicle_type_towing,
  p.chp_vehicle_type_towed,
  c.motorcycle_collision,
  c.killed_victims,
  c.injured_victims,
  c.collision_date,
  c.collision_time
FROM parties p
JOIN collisions c
  ON p.case_id = c.case_id
WHERE p.party_type IS NOT NULL
  AND c.motorcycle_collision IS NOT NULL
```

---
