# Skill graph — `California_Traffic_Collision` (2 skills)

**Skill `motorcycle_party_collisions`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `collision`, `party` |
| output columns | `collision_id`, `party_id`, `helmet_status` |
| source tables | `collisions`, `parties` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `collision_stats_by_helmet` |
| validated_on | — |
| counter_examples | 0 |

_join collision and party tables, restrict to motorcycle collisions and driver/passenger roles, and derive a binary helmet status from safety equipment fields_

```sql
SELECT c.case_id AS collision_id, p.id AS party_id, CASE WHEN p.party_safety_equipment_1 = 'driver, motorcycle helmet used' OR p.party_safety_equipment_2 = 'driver, motorcycle helmet used' THEN 1 ELSE 0 END AS helmet_status FROM collisions c JOIN parties p ON c.case_id = p.case_id WHERE c.motorcycle_collision = 1 AND p.party_type IN ('driver', 'passenger')
```

---

**Skill `collision_stats_by_helmet`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `helmet_status` |
| output columns | `helmet_status`, `collision_count`, `fatality_count` |
| source tables | `motorcycle_party_collisions`, `collisions` |
| depends_on (builds on) | `motorcycle_party_collisions` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_aggregate collision and fatality counts grouped by the derived helmet status_

```sql
SELECT 
    mpc.helmet_status,
    COUNT(mpc.collision_id) AS collision_count,
    SUM(c.killed_victims) AS fatality_count
FROM (
    SELECT DISTINCT collision_id, helmet_status
    FROM motorcycle_party_collisions
) mpc
JOIN collisions c ON mpc.collision_id = c.case_id
GROUP BY mpc.helmet_status
```

---
