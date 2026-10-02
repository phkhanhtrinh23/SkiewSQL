# Skill graph — `EntertainmentAgency` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Musical_Styles`, `Musical_Preferences` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each distinct musical style, produce a single row that reports the musical style and three counts: how many times that style appears as a 1st preference, as a 2nd preference, and as a 3rd pr_

```sql
SELECT
  ms.StyleID,
  ms.StyleName,
  -- count how many customers have this style as PreferenceSeq = 1
  SUM(CASE WHEN mp.PreferenceSeq = 1 THEN 1 ELSE 0 END) AS count_first_preference,
  -- count how many customers have this style as PreferenceSeq = 2
  SUM(CASE WHEN mp.PreferenceSeq = 2 THEN 1 ELSE 0 END) AS count_second_preference,
  -- count how many customers have this style as PreferenceSeq = 3 THEN 1 ELSE 0 END) AS count_third_preference
  SUM(CASE WHEN mp.PreferenceSeq = 3 THEN 1 ELSE 0 END) AS count_third_preference
FROM Musical_Styles ms
LEFT JOIN Musical_Preferences mp
  ON ms.StyleID = mp.StyleID
GROUP BY
  ms.StyleID,
  ms.StyleName
HAVING
  -- include only styles that appear in any preference position (1,2,3)
  SUM(CASE WHEN mp.PreferenceSeq IN (1,2,3) THEN 1 ELSE 0 END) > 0
```

---
