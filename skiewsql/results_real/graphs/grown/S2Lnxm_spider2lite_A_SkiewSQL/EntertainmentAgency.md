# Skill graph — `EntertainmentAgency` (12 skills)

**Skill `preference_rows`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `row_id` |
| output columns | `row_id`, `first_pref`, `second_pref`, `third_pref` |
| source tables | `Musical_Preferences` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `preference_values_normalized`, `unpivot_prefs` |
| validated_on | — |
| counter_examples | 0 |

_Select the rows that contain the three preference fields (first, second, third). Exclude rows where preference values are NULL or empty for any counting purposes will be handled later. Keep raw preference values as-is for exact-match counting._

```sql
SELECT
  CustomerID AS row_id,
  StyleID AS first_pref,
  NULL AS second_pref,
  NULL AS third_pref
FROM Musical_Preferences
```

---

**Skill `preference_values_normalized`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `row_id` |
| output columns | `row_id`, `first_pref_norm`, `second_pref_norm`, `third_pref_norm` |
| source tables | `preference_rows` |
| depends_on (builds on) | `preference_rows` |
| depended-on by (builds on this) | `unpivot_prefs` |
| validated_on | — |
| counter_examples | 0 |

_Normalize/canonicalize the three preference value columns (trim whitespace, treat empty strings as NULL) but do not perform synonym or partial matching. Preserve each preference value in its original position._

```sql
SELECT
  row_id,
  NULLIF(TRIM(first_pref), '') AS first_pref_norm,
  NULLIF(TRIM(second_pref), '') AS second_pref_norm,
  NULLIF(TRIM(third_pref), '') AS third_pref_norm
FROM preference_rows
```

---

**Skill `unpivot_prefs`** — category `RESHAPE`

| field | value |
|---|---|
| grain (one row per) | `row_id`, `pref_position` |
| output columns | `row_id`, `musical_style`, `pref_position` |
| source tables | `preference_rows`, `preference_values_normalized` |
| depends_on (builds on) | `preference_rows`, `preference_values_normalized` |
| depended-on by (builds on this) | `style_pref_counts` |
| validated_on | — |
| counter_examples | 0 |

_Unpivot the normalized preference columns into one row per original row_id and preference position, producing (musical_style, pref_position) only for non-NULL/non-empty normalized values. This yields one row per occurrence of a style in a specific preference slot._

```sql
SELECT
  pr.row_id,
  pv.first_pref_norm AS musical_style,
  1 AS pref_position
FROM preference_rows pr
JOIN preference_values_normalized pv USING (row_id)
WHERE pv.first_pref_norm IS NOT NULL AND pv.first_pref_norm <> ''

UNION ALL

SELECT
  pr.row_id,
  pv.second_pref_norm AS musical_style,
  2 AS pref_position
FROM preference_rows pr
JOIN preference_values_normalized pv USING (row_id)
WHERE pv.second_pref_norm IS NOT NULL AND pv.second_pref_norm <> ''

UNION ALL

SELECT
  pr.row_id,
  pv.third_pref_norm AS musical_style,
  3 AS pref_position
FROM preference_rows pr
JOIN preference_values_normalized pv USING (row_id)
WHERE pv.third_pref_norm IS NOT NULL AND pv.third_pref_norm <> ''
```

---

**Skill `style_pref_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `StyleName` |
| output columns | `musical_style`, `first_pref_count`, `second_pref_count`, `third_pref_count` |
| source tables | `Musical_Styles`, `unpivot_prefs` |
| depends_on (builds on) | `unpivot_prefs` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each distinct musical style, count occurrences where pref_position = 'first', 'second', and 'third'. Include every style that appears at least once in any position. Produce one row per musical style with three integer counts._

```sql
SELECT
  ms.StyleName AS musical_style,
  COALESCE(SUM(CASE WHEN up.pref_position = 'first' THEN 1 ELSE 0 END), 0) AS first_pref_count,
  COALESCE(SUM(CASE WHEN up.pref_position = 'second' THEN 1 ELSE 0 END), 0) AS second_pref_count,
  COALESCE(SUM(CASE WHEN up.pref_position = 'third' THEN 1 ELSE 0 END), 0) AS third_pref_count
FROM Musical_Styles ms
JOIN unpivot_prefs up
  ON up.musical_style = ms.StyleName
GROUP BY ms.StyleName
```

---

**Skill `pref_rows_filtered`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `musical_preference_row_id` |
| output columns | `musical_style`, `preference_seq` |
| source tables | `Musical_Preferences` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select Musical_Preferences rows that have a non-null MusicalStyle and a PreferenceSeq in {1,2,3}. Remove/ignore other rows._

```sql
SELECT
  Musical_Preferences.CustomerID AS row_id,
  Musical_Preferences.StyleID AS musical_style,
  Musical_Preferences.PreferenceSeq AS preference_seq
FROM Musical_Preferences
WHERE Musical_Preferences.StyleID IS NOT NULL
  AND Musical_Preferences.PreferenceSeq IN (1, 2, 3)
```

---

**Skill `style_pref_counts_5`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `StyleID`, `StyleName` |
| output columns | `musical_style`, `count_pref1`, `count_pref2`, `count_pref3` |
| source tables | `Musical_Styles`, `Musical_Preferences` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `style_weighted_scores` |
| validated_on | — |
| counter_examples | 0 |

_For each musical style, count how many PreferenceSeq=1, =2, and =3 rows it has (only counting filtered rows)._

```sql
SELECT
  ms.StyleName AS musical_style,
  COALESCE(SUM(CASE WHEN mp.PreferenceSeq = 1 THEN 1 ELSE 0 END), 0) AS count_pref1,
  COALESCE(SUM(CASE WHEN mp.PreferenceSeq = 2 THEN 1 ELSE 0 END), 0) AS count_pref2,
  COALESCE(SUM(CASE WHEN mp.PreferenceSeq = 3 THEN 1 ELSE 0 END), 0) AS count_pref3
FROM Musical_Styles ms
LEFT JOIN Musical_Preferences mp
  ON ms.StyleID = mp.StyleID
GROUP BY ms.StyleID, ms.StyleName
```

---

**Skill `style_weighted_scores`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `musical_style` |
| output columns | `musical_style`, `total_weighted_score` |
| source tables | `Musical_Styles`, `style_pref_counts_5` |
| depends_on (builds on) | `style_pref_counts_5` |
| depended-on by (builds on this) | `style_scores_with_average` |
| validated_on | — |
| counter_examples | 0 |

_Compute each style's TotalWeightedScore using counts: 3*count_pref1 + 2*count_pref2 + 1*count_pref3. Keep one row per style (only styles with at least one counted preference)._

```sql
SELECT
  ms.StyleName AS musical_style,
  (COALESCE(spc.count_pref1,0)*3 + COALESCE(spc.count_pref2,0)*2 + COALESCE(spc.count_pref3,0)*1) AS total_weighted_score
FROM Musical_Styles ms
JOIN style_pref_counts_5 spc
  ON ms.StyleName = spc.musical_style
WHERE (COALESCE(spc.count_pref1,0) + COALESCE(spc.count_pref2,0) + COALESCE(spc.count_pref3,0)) > 0
```

---

**Skill `style_scores_with_average`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `musical_style` |
| output columns | `musical_style`, `total_weighted_score`, `avg_weighted_score`, `abs_diff_from_average` |
| source tables | `style_weighted_scores` |
| depends_on (builds on) | `style_weighted_scores` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Attach the average of total_weighted_score across all styles (that have at least one ranking) to each style row, and compute the absolute difference between the style's score and that average._

```sql
SELECT
  s.musical_style,
  sws.total_weighted_score,
  avg_scores.avg_weighted_score,
  ABS(COALESCE(sws.total_weighted_score,0) - avg_scores.avg_weighted_score) AS abs_diff_from_average
FROM style_weighted_scores AS sws
JOIN (
  SELECT AVG(total_weighted_score) AS avg_weighted_score
  FROM style_weighted_scores
  WHERE total_weighted_score IS NOT NULL
) AS avg_scores
ON 1=1
JOIN (
  SELECT musical_style FROM style_weighted_scores
) AS s
ON s.musical_style = sws.musical_style
```

---

**Skill `entertainer_styles_raw`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `entertainer_id`, `style_position` |
| output columns | `entertainer_id`, `stage_name`, `style`, `style_position` |
| source tables | `Entertainers`, `Entertainer_Styles`, `Musical_Styles` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select all style-strength rows for entertainers (one row per entertainer-style entry). Do not collapse or pivot. Keep the ordering/position information if available (e.g., position or sequence number)._

```sql
SELECT
  E.EntertainerID AS entertainer_id,
  E.EntStageName AS stage_name,
  MS.StyleName AS style,
  ES.StyleStrength AS style_position
FROM Entertainers E
JOIN Entertainer_Styles ES ON E.EntertainerID = ES.EntertainerID
JOIN Musical_Styles MS ON ES.StyleID = MS.StyleID
```

---

**Skill `customer_preferences_raw`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `preference_position` |
| output columns | `customer_id`, `last_name`, `style`, `preference_position` |
| source tables | `Musical_Preferences`, `Customers`, `Musical_Styles` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select all style-preference rows for customers (one row per customer-preference entry). Do not collapse or pivot. Keep the ordering/position information if available (e.g., preference_position)._

```sql
SELECT
  c.CustomerID AS customer_id,
  c.CustLastName AS last_name,
  ms.StyleName AS style,
  mp.PreferenceSeq AS preference_position
FROM Musical_Preferences mp
JOIN Customers c ON mp.CustomerID = c.CustomerID
JOIN Musical_Styles ms ON mp.StyleID = ms.StyleID
```

---

**Skill `entertainer_styles_grouped`** — category `RESHAPE`

| field | value |
|---|---|
| grain (one row per) | `EntertainerID`, `EntStageName` |
| output columns | `entertainer_id`, `stage_name`, `style_1`, `style_2`, `style_3`, `style_count` |
| source tables | `Entertainers`, `Entertainer_Styles`, `Musical_Styles` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each entertainer, pivot or assemble their style strengths into ordinal positions (first, second, third), but only include entertainers who have at most three style entries and at least two (so first and second exist). Keep stage name with the entertainer._

```sql
SELECT
  e."EntertainerID" AS entertainer_id,
  e."EntStageName" AS stage_name,
  MAX(CASE WHEN es."StyleStrength" IS NOT NULL AND ranked.rn = 1 THEN ms."StyleID" END) AS style_1,
  MAX(CASE WHEN es."StyleStrength" IS NOT NULL AND ranked.rn = 2 THEN ms."StyleID" END) AS style_2,
  MAX(CASE WHEN es."StyleStrength" IS NOT NULL AND ranked.rn = 3 THEN ms."StyleID" END) AS style_3,
  COUNT(es."StyleID") AS style_count
FROM "Entertainers" e
JOIN "Entertainer_Styles" es ON e."EntertainerID" = es."EntertainerID"
LEFT JOIN "Musical_Styles" ms ON es."StyleID" = ms."StyleID"
-- rank style entries per entertainer by StyleStrength desc, then StyleID asc to break ties
JOIN (
  SELECT
    es2."EntertainerID",
    es2."StyleID",
    es2."StyleStrength",
    (SELECT COUNT(*) FROM "Entertainer_Styles" es3
     WHERE es3."EntertainerID" = es2."EntertainerID"
       AND (es3."StyleStrength" > es2."StyleStrength"
            OR (es3."StyleStrength" = es2."StyleStrength" AND es3."StyleID" <= es2."StyleID"))
    ) AS rn
  FROM "Entertainer_Styles" es2
) ranked
  ON ranked."EntertainerID" = es."EntertainerID" AND ranked."StyleID" = es."StyleID"
GROUP BY e."EntertainerID", e."EntStageName"
HAVING COUNT(es."StyleID") BETWEEN 2 AND 3
```

---

**Skill `customer_preferences_grouped`** — category `RESHAPE`

| field | value |
|---|---|
| grain (one row per) | `CustomerID`, `CustLastName` |
| output columns | `customer_id`, `last_name`, `pref_1`, `pref_2`, `pref_3`, `pref_count` |
| source tables | `Customers`, `Musical_Preferences`, `Musical_Styles` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each customer, pivot or assemble their style preferences into ordinal positions (first, second, third), but only include customers who have at most three preference entries and at least two. Keep last name with the customer._

```sql
SELECT
  C.CustomerID AS customer_id,
  C.CustLastName AS last_name,
  MAX(CASE WHEN MP.PreferenceSeq = 1 THEN MS.StyleName END) AS pref_1,
  MAX(CASE WHEN MP.PreferenceSeq = 2 THEN MS.StyleName END) AS pref_2,
  MAX(CASE WHEN MP.PreferenceSeq = 3 THEN MS.StyleName END) AS pref_3,
  COUNT(MP.StyleID) AS pref_count
FROM Customers C
JOIN Musical_Preferences MP ON C.CustomerID = MP.CustomerID
JOIN Musical_Styles MS ON MP.StyleID = MS.StyleID
GROUP BY C.CustomerID, C.CustLastName
HAVING pref_count BETWEEN 2 AND 3
```

---
