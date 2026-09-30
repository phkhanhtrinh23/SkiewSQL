# Skill graph — `EntertainmentAgency` (2 skills)

**Skill `preference_records`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `preference_record` |
| output columns | `musical_style`, `preference_rank` |
| source tables | `Musical_Preferences`, `Musical_Styles` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `style_rank_pivot` |
| validated_on | — |
| counter_examples | 0 |

_all preference entries containing the musical style and its assigned preference rank_

```sql
SELECT ms.StyleName AS musical_style, mp.PreferenceSeq AS preference_rank
FROM Musical_Preferences mp
JOIN Musical_Styles ms ON mp.StyleID = ms.StyleID
```

---

**Skill `style_rank_pivot`** — category `RESHAPE`

| field | value |
|---|---|
| grain (one row per) | `musical_style` |
| output columns | `musical_style`, `count_rank_1`, `count_rank_2`, `count_rank_3` |
| source tables | `preference_records` |
| depends_on (builds on) | `preference_records` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_conditional aggregation that groups by musical style and pivots preference ranks into separate count columns_

```sql
SELECT 
    musical_style,
    COUNT(CASE WHEN preference_rank = 1 THEN 1 END) AS count_rank_1,
    COUNT(CASE WHEN preference_rank = 2 THEN 1 END) AS count_rank_2,
    COUNT(CASE WHEN preference_rank = 3 THEN 1 END) AS count_rank_3
FROM preference_records
GROUP BY musical_style
```

---
