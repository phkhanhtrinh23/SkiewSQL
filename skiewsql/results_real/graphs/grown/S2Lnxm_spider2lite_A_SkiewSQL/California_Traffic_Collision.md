# Skill graph — `California_Traffic_Collision` (12 skills)

**Skill `motorcycle_parties_sel`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `party_id` |
| output columns | `collision_id`, `party_id`, `party_safety_equipment`, `is_fatality` |
| source tables | `parties` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `collision_helmet_status_agg`, `collision_motorcyclist_fatalities_agg`, `helmet_group_level_metrics_join` |
| validated_on | — |
| counter_examples | 0 |

_Select parties that are motorcyclists (party body/type indicates motorcycle) and retain party identifiers, collision id, party_safety_equipment, and fatality indicator for that party/person. This filters to only parties that are motorcycles so collisions without any motorcycle parties can be excluded later._

```sql
SELECT
  case_id AS collision_id,
  id AS party_id,
  COALESCE(party_safety_equipment_1, party_safety_equipment_2) AS party_safety_equipment,
  CASE WHEN party_number_killed IS NOT NULL AND party_number_killed > 0 THEN 1 ELSE 0 END AS is_fatality
FROM parties
WHERE party_type = 'motorcycle' OR statewide_vehicle_type = 'motorcycle' OR chp_vehicle_type_towing = 'motorcycle' OR chp_vehicle_type_towed = 'motorcycle'
```

---

**Skill `collision_helmet_status_agg`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `collision_id` |
| output columns | `collision_id`, `any_helmet_used_flag`, `any_no_helmet_flag`, `all_unknown_flag` |
| source tables | `motorcycle_parties_sel` |
| depends_on (builds on) | `motorcycle_parties_sel` |
| depended-on by (builds on this) | `helmet_group_level_metrics_join` |
| validated_on | — |
| counter_examples | 0 |

_For each collision that has at least one motorcycle party, determine helmet-usage classification based on parties' party_safety_equipment values: whether any motorcycle party in the collision has helmet used, whether any explicitly has no helmet, and whether helmet status is unknown for all. Keep flags to allow final assignment to helmet_used or helmet_not_used and to exclude collisions with only unknown/undetermined helmet data when required._

```sql
SELECT
  mp.collision_id AS collision_id,
  MAX(CASE WHEN lower(coalesce(mp.party_safety_equipment, '')) LIKE '%helmet%' AND lower(mp.party_safety_equipment) NOT LIKE '%not used%' THEN 1 ELSE 0 END) AS any_helmet_used_flag,
  MAX(CASE WHEN lower(coalesce(mp.party_safety_equipment, '')) LIKE '%not used%' OR lower(mp.party_safety_equipment) LIKE '%no helmet%' THEN 1 ELSE 0 END) AS any_no_helmet_flag,
  MIN(CASE WHEN mp.party_safety_equipment IS NULL OR trim(mp.party_safety_equipment) = '' OR lower(mp.party_safety_equipment) = 'unknown' THEN 1 ELSE 0 END) = 1 AS all_unknown_flag
FROM
  motorcycle_parties_sel mp
GROUP BY
  mp.collision_id
```

---

**Skill `collision_motorcyclist_fatalities_agg`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `collision_id` |
| output columns | `collision_id`, `motorcyclist_fatalities` |
| source tables | `motorcycle_parties_sel` |
| depends_on (builds on) | `motorcycle_parties_sel` |
| depended-on by (builds on this) | `helmet_group_level_metrics_join` |
| validated_on | — |
| counter_examples | 0 |

_For each collision that has at least one motorcycle party, count the number of motorcyclist fatalities (sum of is_fatality among motorcycle parties). Produce one row per collision with that count._

```sql
SELECT
  m.collision_id AS collision_id,
  SUM(CASE WHEN m.is_fatality = 1 THEN 1 ELSE 0 END) AS motorcyclist_fatalities
FROM
  motorcycle_parties_sel m
GROUP BY
  m.collision_id
HAVING
  SUM(1) > 0
```

---

**Skill `helmet_group_level_metrics_join`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `collision_id` |
| output columns | `collision_id`, `helmet_usage_group`, `motorcyclist_fatalities` |
| source tables | `motorcycle_parties_sel`, `collision_helmet_status_agg`, `collision_motorcyclist_fatalities_agg` |
| depends_on (builds on) | `motorcycle_parties_sel`, `collision_helmet_status_agg`, `collision_motorcyclist_fatalities_agg` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Join collision helmet-status flags with per-collision motorcyclist fatality counts, assign each collision to exactly one helmet_usage_group ('helmet_used' if any_helmet_used_flag is true. Else 'helmet_not_used' if any_no_helmet_flag is true. Exclude collisions where neither helmet_used nor no_helmet can be determined and all_unknown_flag is true). Produce one row per collision with assigned group and fatality count for later aggregation into group-level metrics._

```sql
SELECT
  m.collision_id AS collision_id,
  CASE
    WHEN h.any_helmet_used_flag = 1 THEN 'helmet_used'
    WHEN h.any_helmet_used_flag = 0 AND h.any_no_helmet_flag = 1 THEN 'helmet_not_used'
    -- Exclude collisions where helmet status cannot be determined and all_unknown_flag = 1 by filtering them out
  END AS helmet_usage_group,
  f.motorcyclist_fatalities AS motorcyclist_fatalities
FROM motorcycle_parties_sel m
JOIN collision_helmet_status_agg h ON m.collision_id = h.collision_id
JOIN collision_motorcyclist_fatalities_agg f ON m.collision_id = f.collision_id
WHERE NOT (h.any_helmet_used_flag IS NULL AND h.any_no_helmet_flag IS NULL AND h.all_unknown_flag = 1)
```

---

**Skill `accidents_by_year_and_cause`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `year`, `cause` |
| output columns | `year`, `cause`, `accident_count` |
| source tables | `collisions`, `case_ids` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `yearly_cause_ranks` |
| validated_on | — |
| counter_examples | 0 |

_Count number of accidents grouped by year and cause. This produces one row per year-cause with the total accident count for that cause in that year._

```sql
SELECT
  CAST(case_ids.db_year AS INTEGER) AS year,
  COALESCE(collisions.primary_collision_factor, 'UNKNOWN') AS cause,
  COUNT(DISTINCT collisions.case_id) AS accident_count
FROM collisions
JOIN case_ids USING (case_id)
GROUP BY CAST(case_ids.db_year AS INTEGER), COALESCE(collisions.primary_collision_factor, 'UNKNOWN')
```

---

**Skill `yearly_cause_ranks`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `year`, `cause` |
| output columns | `year`, `cause`, `accident_count`, `cause_rank` |
| source tables | `accidents_by_year_and_cause` |
| depends_on (builds on) | `accidents_by_year_and_cause` |
| depended-on by (builds on this) | `top_two_causes_per_year` |
| validated_on | — |
| counter_examples | 0 |

_Rank causes within each year by accident_count in descending order and assign rank positions so we can identify the top two causes per year._

```sql
SELECT
  year AS year,
  cause AS cause,
  accident_count AS accident_count,
  ROW_NUMBER() OVER (PARTITION BY year ORDER BY accident_count DESC, cause) AS cause_rank
FROM
  accidents_by_year_and_cause
```

---

**Skill `top_two_causes_per_year`** — category `RESHAPE`

| field | value |
|---|---|
| grain (one row per) | `year`, `cause`, `accident_count`, `cause`, `accident_count` |
| output columns | `year`, `cause1`, `count1`, `cause2`, `count2` |
| source tables | `yearly_cause_ranks` |
| depends_on (builds on) | `yearly_cause_ranks` |
| depended-on by (builds on this) | `years_with_unique_top_two_sets` |
| validated_on | — |
| counter_examples | 0 |

_For each year, extract the top two causes (rank 1 and rank 2) along with their counts, producing one row per year that includes cause1, count1, cause2, count2. Only include years that have at least two distinct causes recorded._

```sql
SELECT
  ycr.year AS year,
  c1.cause AS cause1,
  c1.accident_count AS count1,
  c2.cause AS cause2,
  c2.accident_count AS count2
FROM yearly_cause_ranks AS ycr
JOIN yearly_cause_ranks AS c1
  ON ycr.year = c1.year AND c1.cause_rank = 1
JOIN yearly_cause_ranks AS c2
  ON ycr.year = c2.year AND c2.cause_rank = 2
GROUP BY ycr.year, c1.cause, c1.accident_count, c2.cause, c2.accident_count
```

---

**Skill `years_with_unique_top_two_sets`** — category `SET`

| field | value |
|---|---|
| grain (one row per) | `year` |
| output columns | `year`, `cause1`, `count1`, `cause2`, `count2` |
| source tables | `top_two_causes_per_year` |
| depends_on (builds on) | `top_two_causes_per_year` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Compare the set of top-two causes for each year to the sets for all other years and keep only years whose top-two set is not equal to the top-two set of any other year. This yields the final rows to return._

```sql
SELECT
  t.year AS year,
  t.cause1 AS cause1,
  t.count1 AS count1,
  t.cause2 AS cause2,
  t.count2 AS count2
FROM
  top_two_causes_per_year t
WHERE
  NOT EXISTS (
    SELECT 1
    FROM top_two_causes_per_year o
    WHERE
      o.year != t.year
      AND (
        (COALESCE(o.cause1, '') = COALESCE(t.cause1, '')
         AND COALESCE(o.cause2, '') = COALESCE(t.cause2, '')
         AND COALESCE(o.count1, -1) = COALESCE(t.count1, -2)
         AND COALESCE(o.count2, -1) = COALESCE(t.count2, -2)
        )
        OR
        -- also consider sets equal regardless of order: cause1/cause2 swapped but counts swapped accordingly
        (COALESCE(o.cause1, '') = COALESCE(t.cause2, '')
         AND COALESCE(o.cause2, '') = COALESCE(t.cause1, '')
         AND COALESCE(o.count1, -1) = COALESCE(t.count2, -2)
         AND COALESCE(o.count2, -1) = COALESCE(t.count1, -2)
        )
      )
  )
```

---

**Skill `incidents_filtered_years`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `incident_id_or_count` |
| output columns | `year`, `collision_factor_violation_category`, `incident_id_or_count` |
| source tables | `collisions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select incident records restricted to the years of interest (2011 and 2021) and keep fields needed for grouping: year, collision factor violation category, and an identifier or count unit for incidents._

```sql
SELECT
  CAST(strftime('%Y', collision_date) AS INTEGER) AS year,
  pcf_violation_category AS collision_factor_violation_category,
  case_id AS incident_id_or_count
FROM collisions
WHERE collision_date IS NOT NULL
  AND (CAST(strftime('%Y', collision_date) AS INTEGER) = 2011 OR CAST(strftime('%Y', collision_date) AS INTEGER) = 2021)
```

---

**Skill `annual_totals_by_category`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `db_year`, `pcf_violation_category` |
| output columns | `year`, `collision_factor_violation_category`, `incidents_count` |
| source tables | `collisions`, `case_ids` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `annual_totals_all_categories`, `category_shares_and_top2021` |
| validated_on | — |
| counter_examples | 0 |

_For each year and collision factor violation category, compute the total number of incidents (count of incident units)._

```sql
SELECT
  ci.db_year AS year,
  c.pcf_violation_category AS collision_factor_violation_category,
  COUNT(*) AS incidents_count
FROM collisions AS c
JOIN case_ids AS ci
  ON c.case_id = ci.case_id
GROUP BY
  ci.db_year,
  c.pcf_violation_category
```

---

**Skill `annual_totals_all_categories`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `year` |
| output columns | `year`, `total_incidents_all_categories` |
| source tables | `annual_totals_by_category` |
| depends_on (builds on) | `annual_totals_by_category` |
| depended-on by (builds on this) | `category_shares_and_top2021` |
| validated_on | — |
| counter_examples | 0 |

_For each year compute the total number of incidents across all collision factor violation categories (year-level denominator for share calculation)._

```sql
SELECT
  year AS year,
  SUM(incidents_count) AS total_incidents_all_categories
FROM annual_totals_by_category
GROUP BY year
```

---

**Skill `category_shares_and_top2021`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `year`, `collision_factor_violation_category` |
| output columns | `year`, `collision_factor_violation_category`, `incidents_count`, `total_incidents_all_categories`, `share_percentage`, `is_top_in_2021` |
| source tables | `annual_totals_by_category`, `annual_totals_all_categories` |
| depends_on (builds on) | `annual_totals_by_category`, `annual_totals_all_categories` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Join per-category counts with year totals to compute each category's share of annual incidents (as percentage) for 2011 and 2021, and identify the single category that has the maximum incident count in 2021. Do not collapse to a single scalar here — keep rows per (year, category) but mark the top-2021 category for filtering in the final step._

```sql
SELECT
  a.year AS year,
  a.collision_factor_violation_category AS collision_factor_violation_category,
  a.incidents_count AS incidents_count,
  t.total_incidents_all_categories AS total_incidents_all_categories,
  CASE
    WHEN t.total_incidents_all_categories = 0 THEN 0.0
    ELSE (CAST(a.incidents_count AS REAL) / CAST(t.total_incidents_all_categories AS REAL)) * 100.0
  END AS share_percentage,
  CASE
    WHEN a.year = 2021 AND a.incidents_count = (
      SELECT MAX(at.incidents_count)
      FROM annual_totals_by_category at
      WHERE at.year = 2021
    ) THEN 1
    ELSE 0
  END AS is_top_in_2021
FROM
  annual_totals_by_category a
JOIN
  annual_totals_all_categories t
  ON a.year = t.year
```

---
