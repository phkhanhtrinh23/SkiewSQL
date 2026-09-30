# Skill graph — `EntertainmentAgency` (2 skills)

**Skill `filtered_preferences`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `preference` |
| output columns | `CustomerID`, `StyleID`, `style`, `rank` |
| source tables | `Musical_Preferences`, `Musical_Styles` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `style_preference_counts` |
| validated_on | — |
| counter_examples | 0 |

_preference records filtered to the target preference ranks_

```sql
SELECT mp.CustomerID, mp.StyleID, ms.StyleName AS style, mp.PreferenceSeq AS rank
FROM Musical_Preferences mp
JOIN Musical_Styles ms ON mp.StyleID = ms.StyleID
```

---

**Skill `style_preference_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `style` |
| output columns | `style`, `count_rank_1`, `count_rank_2`, `count_rank_3` |
| source tables | `filtered_preferences` |
| depends_on (builds on) | `filtered_preferences` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_aggregated counts of preferences grouped by style, combining the counts for each target rank into a single row per style_

```sql
SELECT style, COUNT(CASE WHEN rank = 1 THEN 1 END) AS count_rank_1, COUNT(CASE WHEN rank = 2 THEN 1 END) AS count_rank_2, COUNT(CASE WHEN rank = 3 THEN 1 END) AS count_rank_3 FROM filtered_preferences GROUP BY style
```

---
