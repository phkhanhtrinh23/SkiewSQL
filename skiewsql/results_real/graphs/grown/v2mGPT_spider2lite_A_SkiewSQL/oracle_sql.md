# Skill graph — `oracle_sql` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `packaging`, `packaging_relations` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute the average of the total quantity per final packaging combination, where for each final packaging combination you first expand any nested packaging relationships to list only the leaf-le_

```sql
SELECT
  p.id AS packaging_id,
  p.name AS packaging_name,
  pr.contains_id AS direct_contains_id,
  pr.qty AS direct_qty
FROM packaging p
LEFT JOIN packaging_relations pr
  ON p.id = pr.packaging_id
```

---
