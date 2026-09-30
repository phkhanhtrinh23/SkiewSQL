# Skill graph — `California_Traffic_Collision` (2 skills)

**Skill `collision_party_helmet_status`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `collision_id`, `party_id` |
| output columns | `collision_id`, `party_id`, `helmet_status` |
| source tables | `collisions`, `parties` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `helmet_fatalities_percentage` |
| validated_on | — |
| counter_examples | 0 |

_joins collision records with party safety equipment fields to classify each party involved in a motorcycle collision by helmet usage status_

```sql
SELECT
    c.case_id AS collision_id,
    p.id AS party_id,
    CASE
        WHEN p.party_safety_equipment_1 LIKE '%driver, motorcycle helmet used%' OR p.party_safety_equipment_2 LIKE '%driver, motorcycle helmet used%' THEN 'wearing helmet'
        WHEN p.party_safety_equipment_1 LIKE '%driver, motorcycle helmet not used%' OR p.party_safety_equipment_2 LIKE '%driver, motorcycle helmet not used%' THEN 'not wearing helmet'
        ELSE 'unknown'
    END AS helmet_status
FROM collisions c
JOIN parties p ON c.case_id = p.case_id
```

---

**Skill `helmet_fatalities_percentage`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `helmet_status` |
| output columns | `helmet_status`, `collision_count`, `motorcyclist_fatalities_count`, `fatality_percentage` |
| source tables | `collision_party_helmet_status`, `collisions` |
| depends_on (builds on) | `collision_party_helmet_status` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_groups the classified collision-party records by helmet status to count total collisions and motorcyclist fatalities, then computes the fatality percentage for each status_

```sql
SELECT
    cp.helmet_status,
    COUNT(c.case_id) AS collision_count,
    SUM(c.motorcyclist_killed_count) AS motorcyclist_fatalities_count,
    CAST(SUM(c.motorcyclist_killed_count) AS REAL) * 100.0 / COUNT(c.case_id) AS fatality_percentage
FROM collision_party_helmet_status cp
JOIN collisions c ON cp.collision_id = c.case_id
GROUP BY cp.helmet_status
```

---
