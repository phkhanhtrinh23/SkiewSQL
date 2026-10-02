# Skill graph — `city_legislation` (37 skills)

**Skill `cn_july_records`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `record_id` |
| output columns | `date`, `city_name_raw` |
| source tables | `cities` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `one_record_per_date`, `normalized_city_names` |
| validated_on | — |
| counter_examples | 0 |

_Select all records whose country_code_2 indicates China and whose date is within July 2021. Keep any columns needed to identify the city and the date for downstream processing._

```sql
SELECT
  city_id AS record_id,
  insert_date AS date,
  city_name AS city_name_raw,
  country_code_2,
  city_name,
  latitude,
  longitude
FROM cities
WHERE country_code_2 = 'cn'
  AND insert_date >= '2021-07-17'
  AND insert_date <= '2021-07-17'
```

---

**Skill `one_record_per_date`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `date` |
| output columns | `date`, `city_name_raw` |
| source tables | `cn_july_records` |
| depends_on (builds on) | `cn_july_records` |
| depended-on by (builds on this) | `normalized_city_names` |
| validated_on | — |
| counter_examples | 0 |

_For each calendar date in July 2021 that has at least one Chinese record, pick exactly one arbitrary record (deduplicate multiple records per date). Preserve the date and the associated city name from the chosen record._

```sql
SELECT
  date,
  city_name_raw
FROM (
  SELECT
    date,
    city_name_raw,
    ROW_NUMBER() OVER (PARTITION BY date ORDER BY date) AS rn
  FROM cn_july_records
) t
WHERE rn = 1
```

---

**Skill `normalized_city_names`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `date` |
| output columns | `date`, `city_name` |
| source tables | `legislation_date_dim`, `cn_july_records`, `one_record_per_date` |
| depends_on (builds on) | `cn_july_records`, `one_record_per_date` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Normalize the chosen city name so that only the first letter is capitalized and the rest are lowercase, producing the final city_name value for each date._

```sql
SELECT
  ld.date AS date,
  CASE
    WHEN length(tr.city_name_raw) = 0 OR tr.city_name_raw IS NULL THEN tr.city_name_raw
    ELSE upper(substr(tr.city_name_raw,1,1)) || lower(substr(tr.city_name_raw,2))
  END AS city_name
FROM legislation_date_dim ld
LEFT JOIN (
  SELECT date, city_name_raw FROM cn_july_records
  UNION
  SELECT date, city_name_raw FROM one_record_per_date
) tr
ON tr.date = ld.date
```

---

**Skill `june_city_inserts_by_country_day`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `city_record_id` |
| output columns | `country_code`, `insert_date` |
| source tables | `cities` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select city insertion events restricted to calendar days in June 2022 and normalize each event to the country code and the insertion_date (date without time). One row per raw city record that falls in the date range._

```sql
SELECT
  city_id AS city_record_id,
  country_code_2 AS country_code,
  date(insert_date) AS insert_date
FROM cities
WHERE date(insert_date) >= date('2022-06-01')
  AND date(insert_date) <= date('2022-06-30')
```

---

**Skill `country_day_presence`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `country_code_2`, `insert_date` |
| output columns | `country_code`, `date`, `city_id_example` |
| source tables | `cities` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `country_daily_sequence` |
| validated_on | — |
| counter_examples | 0 |

_Collapse city events to a presence flag per country per day: one row per country and calendar day in June 2022 that has at least one city insertion._

```sql
SELECT
  country_code_2 AS country_code,
  insert_date AS date,
  MIN(city_id) AS city_id_example
FROM
  cities
WHERE
  insert_date BETWEEN '2022-06-01' AND '2022-06-30'
GROUP BY
  country_code_2,
  insert_date
```

---

**Skill `country_daily_sequence`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `country_code`, `date` |
| output columns | `country_code`, `date`, `rn`, `prev_date` |
| source tables | `country_day_presence` |
| depends_on (builds on) | `country_day_presence` |
| depended-on by (builds on this) | `country_streaks` |
| validated_on | — |
| counter_examples | 0 |

_For each country, order its present dates in increasing date order and compute row-number and previous-date (lag) to help identify consecutive-day runs. One row per country-date (presence day)._

```sql
SELECT
  country_code AS country_code,
  date AS date,
  ROW_NUMBER() OVER (PARTITION BY country_code ORDER BY date) AS rn,
  LAG(date) OVER (PARTITION BY country_code ORDER BY date) AS prev_date
FROM country_day_presence
```

---

**Skill `country_streaks`** — category `REC`

| field | value |
|---|---|
| grain (one row per) | `country_code`, `streak_start_date`, `streak_end_date` |
| output columns | `country_code`, `streak_start_date`, `streak_end_date`, `streak_length` |
| source tables | `country_daily_sequence` |
| depends_on (builds on) | `country_daily_sequence` |
| depended-on by (builds on this) | `country_capital_proportions` |
| validated_on | — |
| counter_examples | 0 |

_Using the ordered country-date sequence, assign a streak-group identifier for consecutive calendar-day runs and compute each streak's length (number of days). One row per distinct streak for a country._

```sql
SELECT
  cds.country_code AS country_code,
  cds.streak_start_date AS streak_start_date,
  cds.streak_end_date AS streak_end_date,
  CAST((julianday(cds.streak_end_date) - julianday(cds.streak_start_date)) + 1 AS INTEGER) AS streak_length
FROM (
  SELECT
    country_code,
    MIN(date) AS streak_start_date,
    MAX(date) AS streak_end_date
  FROM (
    SELECT
      country_code,
      date,
      date(
        julianday(date, '-' || (rn - grp) || ' days')
      ) AS grp_anchor,
      (rn - CAST(strftime('%s', date) / 86400 AS INTEGER)) AS grp -- kept for readability though not used directly in outer
    FROM (
      SELECT
        country_code,
        date,
        rn,
        (rn - ROW_NUMBER() OVER (PARTITION BY country_code ORDER BY date)) AS grp
      FROM country_daily_sequence
    )
  )
  GROUP BY country_code, grp_anchor
) AS cds
```

---

**Skill `january_rows_per_country_day`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `row_id` |
| output columns | `country`, `city`, `insertion_datetime`, `insertion_date` |
| source tables | `cities` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `country_capital_proportions` |
| validated_on | — |
| counter_examples | 0 |

_All rows restricted to insertion_date within 2022-01-01..2022-01-31 inclusive, projecting country, city, insertion_date and the date part (calendar day)._

```sql
SELECT
  cities.city_id AS row_id,
  cities.country_code_2 AS country,
  cities.city_name AS city,
  cities.insert_date AS insertion_datetime,
  substr(cities.insert_date, 1, 10) AS insertion_date
FROM cities
WHERE cities.insert_date >= '2022-01-01'
  AND cities.insert_date <= '2022-01-31'
```

---

**Skill `country_day_flags`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `country_name`, `insertion_date` |
| output columns | `country`, `insertion_date`, `rows_on_date` |
| source tables | `cities_countries` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each country and calendar date in January 2022, indicate whether there is at least one row on that date and keep a count of rows for that country/date._

```sql
SELECT
  cc.country_name AS country,
  date(dates.calendar_date) AS insertion_date,
  COUNT(cities_countries.country_id) AS rows_on_date
FROM
  (
    SELECT '2022-01-12' AS calendar_date
    UNION ALL SELECT '2022-01-13'
    UNION ALL SELECT '2022-01-14'
    UNION ALL SELECT '2022-01-15'
    UNION ALL SELECT '2022-01-16'
    UNION ALL SELECT '2022-01-17'
    UNION ALL SELECT '2022-01-18'
    UNION ALL SELECT '2022-01-19'
    UNION ALL SELECT '2022-01-20'
    UNION ALL SELECT '2022-01-21'
    UNION ALL SELECT '2022-01-22'
    UNION ALL SELECT '2022-01-23'
    UNION ALL SELECT '2022-01-24'
    UNION ALL SELECT '2022-01-25'
    UNION ALL SELECT '2022-01-26'
    UNION ALL SELECT '2022-01-27'
    UNION ALL SELECT '2022-01-28'
    UNION ALL SELECT '2022-01-29'
    UNION ALL SELECT '2022-01-30'
    UNION ALL SELECT '2022-01-31'
  ) AS dates
CROSS JOIN cities_countries cc
LEFT JOIN cities_countries ON cities_countries.country_id = cc.country_id
  AND date(cities_countries.created_on) = date(dates.calendar_date)
GROUP BY
  cc.country_name,
  date(dates.calendar_date)
```

---

**Skill `country_capital_proportions`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `country`, `run_id` |
| output columns | `country`, `run_id`, `run_start_date`, `run_end_date`, `run_length_days`, `rows_in_run_total`, `rows_in_run_from_capital`, `distinct_january_2022_insertion_day_count`, `country_capital_city` |
| source tables | `country_streaks`, `cities_countries`, `january_rows_per_country_day`, `cities` |
| depends_on (builds on) | `january_rows_per_country_day`, `country_streaks` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each run (country + run_id), join back to the original january rows to count how many rows within the run have city equal to that country's capital value. Also include the country's distinct_january_2022_insertion_day_count (number of distinct january dates with any rows) so the final step can filter to the country with count = 9._

```sql
SELECT
  cc.country_name AS country,
  -- run identifier: use streak_start_date || '_' || streak_end_date to be deterministic within country
  (cs.streak_start_date || '_' || cs.streak_end_date) AS run_id,
  cs.streak_start_date AS run_start_date,
  cs.streak_end_date AS run_end_date,
  -- run length in days inclusive
  (julianday(cs.streak_end_date) - julianday(cs.streak_start_date) + 1) AS run_length_days,
  -- total rows in run: count of january_rows_per_country_day rows whose insertion_date between start and end for that country
  (
    SELECT COUNT(*)
    FROM january_rows_per_country_day jr
    WHERE jr.country = cc.country_name
      AND jr.insertion_date >= cs.streak_start_date
      AND jr.insertion_date <= cs.streak_end_date
  ) AS rows_in_run_total,
  -- rows in run coming from the country's capital: count jr rows in the run where jr.city equals the capital city_name from cities for that country_code_2
  (
    SELECT COUNT(*)
    FROM january_rows_per_country_day jr
    JOIN cities c ON lower(c.city_name) = lower(jr.city)
    WHERE jr.country = cc.country_name
      AND jr.insertion_date >= cs.streak_start_date
      AND jr.insertion_date <= cs.streak_end_date
      AND c.country_code_2 = cc.country_code_2
      AND c.capital = 1
  ) AS rows_in_run_from_capital,
  -- distinct january 2022 insertion day count: number of distinct insertion_date values in january rows for that country (lift year filtering out of view; keep generic distinct day count)
  (
    SELECT COUNT(DISTINCT jr.insertion_date)
    FROM january_rows_per_country_day jr
    WHERE jr.country = cc.country_name
  ) AS distinct_january_2022_insertion_day_count,
  -- country capital city name (if multiple capitals, this will return one arbitrarily via MIN)
  (
    SELECT MIN(c.city_name)
    FROM cities c
    WHERE c.country_code_2 = cc.country_code_2
      AND c.capital = 1
  ) AS country_capital_city
FROM
  country_streaks cs
JOIN
  cities_countries cc ON cc.country_name = cs.country_code
```

---

**Skill `city_inserts_raw`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `city_id` |
| output columns | `city_id`, `inserted_at`, `year`, `month_number`, `month_name` |
| source tables | `cities` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select raw city insertion events (rows) with the city id and the insertion timestamp/year/month extracted. One row per city insertion event._

```sql
SELECT
  city_id,
  insert_date AS inserted_at,
  CAST(strftime('%Y', insert_date) AS INTEGER) AS year,
  CAST(strftime('%m', insert_date) AS INTEGER) AS month_number,
  CASE CAST(strftime('%m', insert_date) AS INTEGER)
    WHEN 1 THEN 'January' WHEN 2 THEN 'February' WHEN 3 THEN 'March' WHEN 4 THEN 'April'
    WHEN 5 THEN 'May' WHEN 6 THEN 'June' WHEN 7 THEN 'July' WHEN 8 THEN 'August'
    WHEN 9 THEN 'September' WHEN 10 THEN 'October' WHEN 11 THEN 'November' WHEN 12 THEN 'December'
    ELSE NULL
  END AS month_name
FROM cities
```

---

**Skill `monthly_city_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `year`, `month_number`, `month_num_str`, `month_name` |
| output columns | `year`, `month_number`, `month_name`, `monthly_total` |
| source tables | `cities` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `monthly_running_totals`, `filter_and_yoy_metrics` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate raw city insertions to get the count of new cities per year and month (one row per year+month)._

```sql
SELECT
  CAST(strftime('%Y', insert_date) AS INTEGER) AS year,
  CAST(strftime('%m', insert_date) AS INTEGER) AS month_number,
  strftime('%m', insert_date) AS month_num_str,
  CASE strftime('%m', insert_date)
    WHEN '01' THEN 'January' WHEN '02' THEN 'February' WHEN '03' THEN 'March'
    WHEN '04' THEN 'April' WHEN '05' THEN 'May' WHEN '06' THEN 'June'
    WHEN '07' THEN 'July' WHEN '08' THEN 'August' WHEN '09' THEN 'September'
    WHEN '10' THEN 'October' WHEN '11' THEN 'November' WHEN '12' THEN 'December'
    ELSE NULL END AS month_name,
  COUNT(city_id) AS monthly_total
FROM cities
WHERE insert_date IS NOT NULL
GROUP BY year, month_number, month_num_str, month_name
```

---

**Skill `monthly_running_totals`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `year`, `month_number`, `month_name` |
| output columns | `year`, `month_number`, `month_name`, `monthly_total`, `running_total` |
| source tables | `monthly_city_counts` |
| depends_on (builds on) | `monthly_city_counts` |
| depended-on by (builds on this) | `filter_and_yoy_metrics` |
| validated_on | — |
| counter_examples | 0 |

_For each month_name (e.g., April) compute a running cumulative sum of monthly_total across years ordered by year (so running_total for year Y sums that month from earliest available year through Y)._

```sql
SELECT
  mcc.year AS year,
  mcc.month_number AS month_number,
  mcc.month_name AS month_name,
  mcc.monthly_total AS monthly_total,
  (
    SELECT SUM(m2.monthly_total)
    FROM monthly_city_counts m2
    WHERE m2.month_number = mcc.month_number
      AND m2.year <= mcc.year
  ) AS running_total
FROM monthly_city_counts mcc
```

---

**Skill `filter_and_yoy_metrics`** — category `RESHAPE`

| field | value |
|---|---|
| grain (one row per) | `year`, `month_name` |
| output columns | `year`, `month_name`, `monthly_total`, `running_total`, `monthly_yoy_pct`, `running_yoy_pct` |
| source tables | `monthly_city_counts`, `monthly_running_totals` |
| depends_on (builds on) | `monthly_city_counts`, `monthly_running_totals` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Filter to months April/May/June and years 2022/2023, join each row to the previous year's monthly_total and running_total for the same month to compute monthly_yoy_pct and running_yoy_pct (use NULL when previous-year value is zero or missing). Also enforce final sort order (year asc, month in calendar order)._

```sql
SELECT
  mct.year AS year,
  mct.month_name AS month_name,
  mct.monthly_total AS monthly_total,
  mrt.running_total AS running_total,
  CASE
    WHEN prev.monthly_total IS NULL OR prev.monthly_total = 0 THEN NULL
    ELSE (mct.monthly_total - prev.monthly_total) * 1.0 / prev.monthly_total
  END AS monthly_yoy_pct,
  CASE
    WHEN prev_rt.running_total IS NULL OR prev_rt.running_total = 0 THEN NULL
    ELSE (mrt.running_total - prev_rt.running_total) * 1.0 / prev_rt.running_total
  END AS running_yoy_pct
FROM
  monthly_city_counts mct
JOIN
  monthly_running_totals mrt
  ON mct.year = mrt.year
  AND mct.month_number = mrt.month_number
LEFT JOIN
  monthly_city_counts prev
  ON prev.year = mct.year - 1
  AND prev.month_number = mct.month_number
LEFT JOIN
  monthly_running_totals prev_rt
  ON prev_rt.year = mrt.year - 1
  AND prev_rt.month_number = mrt.month_number
WHERE
  mct.month_name IN ('April','May','June')
  AND mct.year IN (2022, 2023)
```

---

**Skill `remote_data_analyst_postings`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `posting_id` |
| output columns | `posting_id`, `annual_average_salary` |
| source tables | `job_postings_fact` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `skill_frequencies_within_cohort`, `postings_with_top_three_skills` |
| validated_on | — |
| counter_examples | 0 |

_Select all job postings that are remote, have job title equal to 'Data Analyst' (exact match), and have a non-null annual average salary. Keep one row per posting with its salary and identifier to join skills._

```sql
SELECT
  job_id AS posting_id,
  salary_year_avg AS annual_average_salary
FROM job_postings_fact
WHERE job_work_from_home = 1
  AND job_title_short = 'Data Analyst'
  AND salary_year_avg IS NOT NULL
```

---

**Skill `posting_skills`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `posting_id`, `skill` |
| output columns | `posting_id`, `skill` |
| source tables | `skills_job_dim`, `skills_dim` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `skill_frequencies_within_cohort`, `postings_with_top_three_skills` |
| validated_on | — |
| counter_examples | 0 |

_List all skill occurrences for postings (mapping each posting to each skill it lists). One row per posting-skill pair so frequency of skills can be counted._

```sql
SELECT
  sj.job_id AS posting_id,
  s.skills AS skill
FROM skills_job_dim AS sj
JOIN skills_dim AS s
  ON sj.skill_id = s.skill_id
```

---

**Skill `skill_frequencies_within_cohort`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `skills` |
| output columns | `skill`, `skill_count` |
| source tables | `skills_dim`, `skills_job_dim`, `posting_skills`, `remote_data_analyst_postings` |
| depends_on (builds on) | `posting_skills`, `remote_data_analyst_postings` |
| depended-on by (builds on this) | `postings_with_top_three_skills` |
| validated_on | — |
| counter_examples | 0 |

_Count occurrences of each skill restricted to the cohort of postings from remote_data_analyst_postings to produce skill frequencies (one row per skill)._

```sql
SELECT
  s.skills AS skill,
  COUNT(*) AS skill_count
FROM skills_dim s
JOIN skills_job_dim sj ON sj.skill_id = s.skill_id
JOIN posting_skills ps ON ps.posting_id = sj.job_id
JOIN remote_data_analyst_postings rdp ON rdp.posting_id = ps.posting_id
GROUP BY s.skills
```

---

**Skill `postings_with_top_three_skills`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `posting_id`, `annual_average_salary` |
| output columns | `posting_id`, `annual_average_salary` |
| source tables | `remote_data_analyst_postings`, `posting_skills`, `skill_frequencies_within_cohort` |
| depends_on (builds on) | `remote_data_analyst_postings`, `posting_skills`, `skill_frequencies_within_cohort` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Join the remote Data Analyst postings to their skills and filter to only those postings whose skill is among the top three most frequent skills (final top-k selection applied here). Keep one row per posting to be averaged with its salary._

```sql
SELECT
  rda.posting_id AS posting_id,
  rda.annual_average_salary AS annual_average_salary
FROM remote_data_analyst_postings rda
JOIN posting_skills ps ON ps.posting_id = rda.posting_id
JOIN skill_frequencies_within_cohort sfc ON sfc.skill = ps.skill
WHERE sfc.skill IN (
  SELECT skill FROM skill_frequencies_within_cohort
  ORDER BY skill_count DESC
  LIMIT 3
)
GROUP BY rda.posting_id, rda.annual_average_salary
```

---

**Skill `cohort_members`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `id_bioguide` |
| output columns | `legislator_id`, `first_term_start_date` |
| source tables | `legislators`, `legislators_terms` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `cohort_target_dates` |
| validated_on | — |
| counter_examples | 0 |

_Select the cohort of legislators whose first_term_start_date falls in the inclusive range 1917-01-01 to 1999-12-31. Keep one row per legislator with their identifier and canonical first_term_start_date._

```sql
SELECT
  l.id_bioguide AS legislator_id,
  MIN(t.term_start) AS first_term_start_date
FROM
  legislators l
JOIN
  legislators_terms t
  ON l.id_bioguide = t.id_bioguide
GROUP BY
  l.id_bioguide
HAVING
  MIN(t.term_start) >= '1917-01-01'
  AND MIN(t.term_start) <= '1999-12-31'
```

---

**Skill `service_intervals`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `legislator_id`, `service_start_date`, `service_end_date` |
| output columns | `legislator_id`, `service_start_date`, `service_end_date` |
| source tables | `legislators_terms` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `retention_flags` |
| validated_on | — |
| counter_examples | 0 |

_All service intervals for legislators: one row per served interval with legislator identifier, interval start_date and end_date (end_date may be NULL to indicate ongoing service). This provides raw membership-by-date for retention checks._

```sql
SELECT
  id_bioguide AS legislator_id,
  term_start AS service_start_date,
  CASE
    WHEN trim(term_end) = '' THEN NULL
    ELSE term_end
  END AS service_end_date
FROM legislators_terms
```

---

**Skill `cohort_target_dates`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `legislator_id`, `period_year` |
| output columns | `legislator_id`, `period_year`, `target_date` |
| source tables | `cohort_members` |
| depends_on (builds on) | `cohort_members` |
| depended-on by (builds on this) | `retention_flags` |
| validated_on | — |
| counter_examples | 0 |

_For each cohort member, generate 20 target dates corresponding to December 31 that occurs n years after their first_term_start_date for n = 1..20. One row per legislator per period_year with computed target_date and period_year integer._

```sql
SELECT
  cm.legislator_id AS legislator_id,
  n.period_year AS period_year,
  date(substr(cm.first_term_start_date,1,4) + n.period_year || '-12-31') AS target_date
FROM
  cohort_members cm,
  (SELECT 1 AS period_year UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5
   UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10
   UNION ALL SELECT 11 UNION ALL SELECT 12 UNION ALL SELECT 13 UNION ALL SELECT 14 UNION ALL SELECT 15
   UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18 UNION ALL SELECT 19 UNION ALL SELECT 20
  ) n
WHERE
  cm.first_term_start_date IS NOT NULL
```

---

**Skill `retention_flags`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `legislator_id`, `period_year` |
| output columns | `legislator_id`, `period_year`, `target_date`, `retained_flag` |
| source tables | `cohort_target_dates`, `service_intervals` |
| depends_on (builds on) | `cohort_target_dates`, `service_intervals` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Determine for each cohort member and period_year whether the legislator was in office on that period's target_date by checking if any service interval covers the target_date. Output one row per legislator per period_year with a retained_flag (1 retained, 0 not)._

```sql
SELECT
  c.legislator_id AS legislator_id,
  c.period_year AS period_year,
  c.target_date AS target_date,
  CASE WHEN EXISTS (
    SELECT 1
    FROM service_intervals s
    WHERE s.legislator_id = c.legislator_id
      AND DATE(s.service_start_date) <= DATE(c.target_date)
      AND DATE(s.service_end_date) >= DATE(c.target_date)
  ) THEN 1 ELSE 0 END AS retained_flag
FROM cohort_target_dates c
```

---

**Skill `legislator_first_terms`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `id_bioguide`, `gender`, `state` |
| output columns | `legislator_id`, `sex`, `state`, `first_term_start_date` |
| source tables | `legislators`, `legislators_terms` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `la_male_legislator_years_since_first` |
| validated_on | — |
| counter_examples | 0 |

_All legislators with their personal attributes and the start date of their first-ever term (earliest term start). This is a cohort restricted to legislators (no date filtering yet)._

```sql
SELECT
  l.id_bioguide AS legislator_id,
  l.gender AS sex,
  lt.state AS state,
  MIN(lt.term_start) AS first_term_start_date
FROM legislators l
LEFT JOIN legislators_terms lt
  ON l.id_bioguide = lt.id_bioguide
GROUP BY
  l.id_bioguide,
  l.gender,
  lt.state
```

---

**Skill `legislator_service_snapshot`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `legislator_id`, `term_start_date` |
| output columns | `legislator_id`, `term_start_date`, `term_end_date` |
| source tables | `legislators_terms` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All service intervals (terms) for legislators, with explicit start and end dates for each term. One row per term occurrence to allow testing whether a legislator was serving on a particular date._

```sql
SELECT
  id_bioguide AS legislator_id,
  term_start AS term_start_date,
  term_end AS term_end_date
FROM legislators_terms
```

---

**Skill `la_male_legislator_years_since_first`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `legislator_id`, `year` |
| output columns | `legislator_id`, `year`, `years_since_first_term` |
| source tables | `legislators`, `legislator_first_terms`, `legislators_terms` |
| depends_on (builds on) | `legislator_first_terms` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Filter to male legislators from Louisiana who were serving on Dec 31 of a year, compute years_since_first_term as the integer whole years between that Dec 31 date and the legislator's first_term_start_date (floor of year difference), and produce one row per legislator per year that meets the elapsed-years filter (do not collapse legislators yet)._

```sql
SELECT
  l.id_bioguide AS legislator_id,
  CAST(strftime('%Y', date(lt.term_end, 'start of year', '+12 months', '-1 day')) AS INTEGER) AS year,
  CAST(
    (julianday(date(lt.term_end, 'start of year', '+12 months', '-1 day')) - julianday(lft.first_term_start_date)) / 365.2425
    AS INTEGER
  ) AS years_since_first_term
FROM legislators l
JOIN legislator_first_terms lft
  ON l.id_bioguide = lft.legislator_id
JOIN legislators_terms lt
  ON l.id_bioguide = lt.id_bioguide
WHERE
  lft.sex = 'M'
  AND lft.state = 'LA'
  AND date(lt.term_end, 'start of year', '+12 months', '-1 day') = date(strftime('%Y', lt.term_end) || '-12-31')
  AND date(lt.term_end, 'start of year', '+12 months', '-1 day') <= date(lt.term_end)
```

---

**Skill `legislator_terms_sel`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `legislator_id`, `term_id` |
| output columns | `legislator_id`, `term_start`, `term_end`, `term_state` |
| source tables | `legislators`, `legislators_terms` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select all term records for legislators, keeping legislator identifier, term start and end dates, and the state represented in that term. Restrict to legislators identified as female._

```sql
SELECT
  l.id_bioguide AS legislator_id,
  t.term_id,
  t.term_start AS term_start,
  t.term_end AS term_end,
  t.state AS term_state
FROM legislators l
JOIN legislators_terms t
  ON l.id_bioguide = t.id_bioguide
WHERE l.gender = 'F'
```

---

**Skill `terms_including_dec31_norm`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `legislator_id`, `term_id` |
| output columns | `legislator_id`, `term_id`, `term_start`, `term_end`, `term_state`, `include_dec31` |
| source tables | `legislators_terms` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `female_legislators_with_dec31_per_state_agg` |
| validated_on | — |
| counter_examples | 0 |

_For each term row, normalize dates and determine whether the term interval includes December 31 of any year (i.e., there exists some YYYY where term_start <= YYYY-12-31 <= term_end). Keep a boolean flag include_dec31._

```sql
SELECT
  lt.id_bioguide AS legislator_id,
  lt.term_id AS term_id,
  lt.term_start AS term_start,
  lt.term_end AS term_end,
  lt.state AS term_state,
  (
    -- include_dec31 true if there exists some year Y where Y-12-31 is between term_start and term_end
    -- compute the year of term_start and term_end and also test boundary years by checking any Y between them
    -- SQLite: compare using string YYYY-12-31 constructed from substr(term_start,1,4) etc.
    (
      -- check if term_start's year dec31 falls within
      (substr(lt.term_start,1,4) || '-12-31') <= COALESCE(lt.term_end, '9999-12-31')
      AND (substr(lt.term_start,1,4) || '-12-31') >= lt.term_start
    )
    OR
    (
      -- check if term_end's year dec31 falls within
      (substr(COALESCE(lt.term_end, substr(lt.term_start,1,4)),1,4) || '-12-31') <= COALESCE(lt.term_end, '9999-12-31')
      AND (substr(COALESCE(lt.term_end, lt.term_start),1,4) || '-12-31') >= lt.term_start
    )
    OR
    (
      -- check if there is at least one whole year between start and end (i.e., start year +1 <= end year -1)
      CAST(substr(COALESCE(lt.term_end, lt.term_start),1,4) AS INTEGER) - CAST(substr(lt.term_start,1,4) AS INTEGER) >= 1
    )
  ) AS include_dec31
FROM legislators_terms lt
```

---

**Skill `legislator_first_state_rank`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `legislator_id` |
| output columns | `legislator_id`, `first_state`, `first_term_start` |
| source tables | `legislators`, `legislators_terms` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `female_legislators_with_dec31_per_state_agg` |
| validated_on | — |
| counter_examples | 0 |

_For each legislator, identify their earliest term (by term_start) and take the state of that earliest term as the legislator's first-represented state. Exclude legislators whose first state is null._

```sql
SELECT
  l.id_bioguide AS legislator_id,
  lt.state AS first_state,
  lt.term_start AS first_term_start
FROM legislators l
JOIN (
  SELECT id_bioguide,
         state,
         term_start
  FROM legislators_terms t
  WHERE state IS NOT NULL
  AND term_start IS NOT NULL
  AND (id_bioguide, term_start) IN (
    SELECT id_bioguide, MIN(term_start) AS term_start
    FROM legislators_terms
    WHERE term_start IS NOT NULL
    GROUP BY id_bioguide
  )
) lt
ON l.id_bioguide = lt.id_bioguide
```

---

**Skill `female_legislators_with_dec31_per_state_agg`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `first_state` |
| output columns | `first_state`, `legislator_count` |
| source tables | `legislators`, `legislator_first_state_rank`, `terms_including_dec31_norm` |
| depends_on (builds on) | `legislator_first_state_rank`, `terms_including_dec31_norm` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each legislator (one row per legislator), determine if they have at least one term with include_dec31=true, join with their first_state, then aggregate counts of distinct legislators per first_state._

```sql
SELECT
  lfs.first_state AS first_state,
  COUNT(DISTINCT l.id_bioguide) AS legislator_count
FROM legislators l
JOIN legislator_first_state_rank lfs
  ON l.id_bioguide = lfs.legislator_id
JOIN terms_including_dec31_norm t
  ON l.id_bioguide = t.legislator_id
WHERE t.include_dec31 = 1
GROUP BY lfs.first_state
```

---

**Skill `legislator_first_term_cohorts`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `legislator_id` |
| output columns | `legislator_id`, `state_abbreviation`, `gender`, `first_term_start_year` |
| source tables | `legislators`, `legislators_terms` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `cohort_retention_flags` |
| validated_on | — |
| counter_examples | 0 |

_One row per legislator cohort member with their legislator id, gender, state, and the year of their first term start. This selects/defines cohorts by (state, first_term_start_year, gender)._

```sql
SELECT
  l.id_bioguide AS legislator_id,
  t.state AS state_abbreviation,
  l.gender AS gender,
  CAST(substr(t.term_start, 1, 4) AS INTEGER) AS first_term_start_year
FROM legislators l
JOIN (
  SELECT
    id_bioguide,
    MIN(term_start) AS term_start,
    state
  FROM legislators_terms
  GROUP BY id_bioguide, state
) t
  ON l.id_bioguide = t.id_bioguide
```

---

**Skill `service_endpoints_on_dec31`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `legislator_id`, `year` |
| output columns | `legislator_id`, `year` |
| source tables | `legislators_terms` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `cohort_retention_flags` |
| validated_on | — |
| counter_examples | 0 |

_All records indicating that a given legislator was serving on December 31 of a specific calendar year. Each row is a (legislator_id, year) pair meaning that legislator was in office on that Dec 31._

```sql
SELECT
  id_bioguide AS legislator_id,
  CAST(strftime('%Y', term_end) AS INTEGER) AS year
FROM legislators_terms
WHERE
  -- term_end is on or after December 31 of the year and term_start is on or before that date
  -- For a given row, include all years for which Dec 31 falls within [term_start, term_end].
  -- Because a single row can't expand to multiple years in a simple SELECT, include any term
  -- that covers at least one Dec 31 date by ensuring term_end >= term_start (valid) and
  -- leaving per-year expansion to downstream queries using the term_start/term_end bounds.
  term_start IS NOT NULL
  AND term_end IS NOT NULL
  AND date(term_end) >= date(term_start)
```

---

**Skill `cohort_retention_flags`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `state_abbreviation`, `first_term_start_year`, `gender`, `legislator_id`, `offset` |
| output columns | `state_abbreviation`, `first_term_start_year`, `gender`, `legislator_id`, `offset`, `retained_flag` |
| source tables | `legislator_first_term_cohorts`, `service_endpoints_on_dec31` |
| depends_on (builds on) | `legislator_first_term_cohorts`, `service_endpoints_on_dec31` |
| depended-on by (builds on this) | `state_gender_offset_retention_counts` |
| validated_on | — |
| counter_examples | 0 |

_For each cohort member, join their cohort row to the service endpoints and produce retention indicator rows for each specified offset (0,2,4,6,8,10): include rows where year = first_term_start_year + offset and indicate offset and retained_flag (1 if served on that Dec 31). One row per cohort member per offset._

```sql
SELECT
  lftc.state_abbreviation AS state_abbreviation,
  lftc.first_term_start_year AS first_term_start_year,
  lftc.gender AS gender,
  lftc.legislator_id AS legislator_id,
  offsets.offset AS offset,
  CASE WHEN sip.year IS NOT NULL THEN 1 ELSE 0 END AS retained_flag
FROM
  legislator_first_term_cohorts lftc
JOIN
  (SELECT 0 AS offset UNION ALL SELECT 2 UNION ALL SELECT 4 UNION ALL SELECT 6 UNION ALL SELECT 8 UNION ALL SELECT 10) AS offsets
  ON 1=1
LEFT JOIN
  service_endpoints_on_dec31 sip
  ON sip.legislator_id = lftc.legislator_id
  AND sip.year = (lftc.first_term_start_year + offsets.offset)
```

---

**Skill `state_gender_offset_retention_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `state_abbreviation`, `first_term_start_year`, `gender`, `offset` |
| output columns | `state_abbreviation`, `first_term_start_year`, `gender`, `offset`, `retained_count` |
| source tables | `cohort_retention_flags` |
| depends_on (builds on) | `cohort_retention_flags` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregate retained_flag to count number of retained legislators per (state, gender, first_term_start_year, offset). This yields retention counts for each cohort (state+year+gender) at each offset._

```sql
SELECT
  crt.state_abbreviation AS state_abbreviation,
  crt.first_term_start_year AS first_term_start_year,
  crt.gender AS gender,
  crt.offset AS offset,
  SUM(CASE WHEN crt.retained_flag IS NOT NULL AND crt.retained_flag != 0 THEN 1 ELSE 0 END) AS retained_count
FROM cohort_retention_flags crt
GROUP BY
  crt.state_abbreviation,
  crt.first_term_start_year,
  crt.gender,
  crt.offset
```

---

**Skill `state_alien_population_rows`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `alien_id` |
| output columns | `state_id`, `alien_id`, `friendly_flag`, `hostile_flag`, `age` |
| source tables | `alien_data` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `state_level_metrics`, `states_ranked_by_population` |
| validated_on | — |
| counter_examples | 0 |

_One row per state-alien record producing counts and attributes needed per alien (or per raw alien row). This selects the raw rows representing aliens (or state-level alien records) so they can be aggregated later. Do not apply top-k or final filters here._

```sql
SELECT
  a.state        AS state_id,
  a.id           AS alien_id,
  CASE WHEN a.aggressive = 0 THEN 1 ELSE 0 END AS friendly_flag,
  CASE WHEN a.aggressive = 1 THEN 1 ELSE 0 END AS hostile_flag,
  a.age          AS age
FROM alien_data a
```

---

**Skill `state_level_metrics`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `state_id` |
| output columns | `state_id`, `total_population`, `friendly_count`, `hostile_count`, `pct_friendly`, `pct_hostile`, `avg_age` |
| source tables | `state_alien_population_rows` |
| depends_on (builds on) | `state_alien_population_rows` |
| depended-on by (builds on this) | `top10_states_filtered_by_conditions` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate per state to compute total alien population, count/percentage of friendly aliens, count/percentage of hostile aliens, and average alien age. Percentages should be expressed as fraction or percent derived from counts and total population but do not apply numeric thresholds here._

```sql
SELECT
  sr.state_id AS state_id,
  COUNT(*) AS total_population,
  SUM(CASE WHEN sr.friendly_flag = 1 THEN 1 ELSE 0 END) AS friendly_count,
  SUM(CASE WHEN sr.hostile_flag = 1 THEN 1 ELSE 0 END) AS hostile_count,
  CASE WHEN COUNT(*) = 0 THEN NULL
       ELSE CAST(SUM(CASE WHEN sr.friendly_flag = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) END AS pct_friendly,
  CASE WHEN COUNT(*) = 0 THEN NULL
       ELSE CAST(SUM(CASE WHEN sr.hostile_flag = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) END AS pct_hostile,
  AVG(sr.age) AS avg_age
FROM state_alien_population_rows sr
GROUP BY sr.state_id
```

---

**Skill `states_ranked_by_population`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `state_id` |
| output columns | `state_id`, `total_population`, `rank_by_population` |
| source tables | `state_alien_population_rows` |
| depends_on (builds on) | `state_alien_population_rows` |
| depended-on by (builds on this) | `top10_states_filtered_by_conditions` |
| validated_on | — |
| counter_examples | 0 |

_Rank states by total alien population in descending order so the top states can be selected. Produce a row-number or rank per state. Do not apply the top-10 limit here (that will be applied in the final step)._

```sql
SELECT
  s.state_id AS state_id,
  s.total_population AS total_population,
  RANK() OVER (ORDER BY s.total_population DESC) AS rank_by_population
FROM (
  SELECT
    state_id,
    COUNT(alien_id) AS total_population
  FROM state_alien_population_rows
  GROUP BY state_id
) AS s
```

---

**Skill `top10_states_filtered_by_conditions`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `state_id` |
| output columns | `state_id`, `total_population`, `pct_friendly`, `pct_hostile`, `avg_age` |
| source tables | `states_ranked_by_population`, `state_level_metrics` |
| depends_on (builds on) | `states_ranked_by_population`, `state_level_metrics` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_From the ranked states, keep only the top 10 by population (apply LIMIT 10 ordering by rank) and then filter those states to those where pct_friendly > pct_hostile (strict) AND avg_age > 200 (strict). This relation is one row per state that meets both conditions within the top-10 cohort._

```sql
SELECT
  s.state_id,
  s.total_population,
  m.pct_friendly,
  m.pct_hostile,
  m.avg_age
FROM states_ranked_by_population s
JOIN state_level_metrics m
  ON s.state_id = m.state_id
WHERE s.rank_by_population <= 10
  AND m.pct_friendly > m.pct_hostile
  AND m.avg_age > 200
```

---
