# Skill graph — `EntertainmentAgency` (2 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Musical_Styles`, `Musical_Preferences` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: For each musical style, count how many times that style appears as a 1st preference, as a 2nd preference, and as a 3rd preference, and return one row per musical style with these counts. Require_

```sql
SELECT
  ms.StyleID,
  ms.StyleName,
  mp.PreferenceSeq,
  mp.CustomerID
FROM "Musical_Styles" ms
LEFT JOIN "Musical_Preferences" mp
  ON ms.StyleID = mp.StyleID
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Entertainers`, `Entertainer_Styles`, `Customers`, `Musical_Preferences` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Find all pairs of an entertainer and a customer such that each has up to three style strengths or preferences, and the customer's first and second style preferences match the entertainer's first_

```sql
SELECT
    e.EntertainerID,
    e.EntStageName,
    c.CustomerID,
    c.CustLastName,
    es1.StyleID AS EntStyle1,
    es1.StyleStrength AS EntStrength1,
    es2.StyleID AS EntStyle2,
    es2.StyleStrength AS EntStrength2,
    es3.StyleID AS EntStyle3,
    es3.StyleStrength AS EntStrength3,
    mp1.StyleID AS CustPref1,
    mp1.PreferenceSeq AS CustPrefSeq1,
    mp2.StyleID AS CustPref2,
    mp2.PreferenceSeq AS CustPrefSeq2,
    mp3.StyleID AS CustPref3,
    mp3.PreferenceSeq AS CustPrefSeq3
FROM Entertainers e
-- entertainer styles (up to 3 possible strengths). Keep keys to allow later joins/filters.
LEFT JOIN Entertainer_Styles es1
  ON e.EntertainerID = es1.EntertainerID AND es1.StyleStrength IS NOT NULL
LEFT JOIN Entertainer_Styles es2
  ON e.EntertainerID = es2.EntertainerID AND es2.StyleStrength IS NOT NULL AND es2.StyleID <> es1.StyleID
LEFT JOIN Entertainer_Styles es3
  ON e.EntertainerID = es3.EntertainerID AND es3.StyleStrength IS NOT NULL AND es3.StyleID NOT IN (es1.StyleID, es2.StyleID)
-- customers and their musical preferences (up to 3). Keep keys for later filtering.
LEFT JOIN Customers c
  ON 1=1
LEFT JOIN Musical_Preferences mp1
  ON c.CustomerID = mp1.CustomerID AND mp1.PreferenceSeq = 1
LEFT JOIN Musical_Preferences mp2
  ON c.CustomerID = mp2.CustomerID AND mp2.PreferenceSeq = 2
LEFT JOIN Musical_Preferences mp3
  ON c.CustomerID = mp3.CustomerID AND mp3.PreferenceSeq = 3
```

---
