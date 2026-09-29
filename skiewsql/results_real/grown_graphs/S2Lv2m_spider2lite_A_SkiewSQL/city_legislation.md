# Skill graph — `city_legislation` (7 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `cities` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: Find, among database records for Chinese cities (country_code_2 = 'cn') during July 2021, the shortest and the longest streaks of consecutive dates for which there is at least one record per dat_

```sql
SELECT
  cities.city_id,
  cities.city_name,
  cities.insert_date AS date,
  cities.country_code_2
FROM cities
WHERE cities.country_code_2 = 'cn'
  AND cities.insert_date BETWEEN '2021-07-01' AND '2021-07-31'
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `cities`, `cities_countries` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Find the country that has data inserted on exactly nine distinct days in January 2022; for that country, determine the longest consecutive-day interval in January 2022 during which there is at l_

```sql
SELECT
  cities_countries.country_name,
  cities.city_name AS city_name,
  cities.insert_date,
  cities.capital,
  cities.country_code_2,
  cities_countries.country_code_2 AS country_code_2_country,
  cities_countries.country_code_3,
  cities.population,
  cities.city_id,
  cities.country_code_2 || '-' || cities.insert_date AS country_date_key
FROM cities
LEFT JOIN cities_countries
  ON cities.country_code_2 = cities_countries.country_code_2
WHERE cities.insert_date BETWEEN '2022-01-01' AND '2022-01-31'
```

---

**Skill `chunk_view_0_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `cities` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each year 2022 and 2023, and for each month April, May, and June, compute the number of new cities inserted in that specific month of that year, the cumulative running total for that month a_

```sql
SELECT
  CAST(strftime('%Y', insert_date) AS INTEGER) AS year,
  CASE CAST(strftime('%m', insert_date) AS INTEGER)
    WHEN 4 THEN 'April'
    WHEN 5 THEN 'May'
    WHEN 6 THEN 'June'
  END AS month,
  COUNT(*) AS monthly_total
FROM cities
WHERE insert_date IS NOT NULL
  AND CAST(strftime('%m', insert_date) AS INTEGER) IN (4,5,6)
  AND CAST(strftime('%Y', insert_date) AS INTEGER) IN (2021,2022,2023)
GROUP BY CAST(strftime('%Y', insert_date) AS INTEGER), CAST(strftime('%m', insert_date) AS INTEGER)
```

---

**Skill `chunk_view_0_3`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `job_postings_fact`, `skills_job_dim`, `skills_dim` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute the overall average annual salary across job postings that have the job title exactly 'Data Analyst', have a non-null annual average salary, and are remote, where the salary average is c_

```sql
SELECT
  j.job_id,
  j.company_id,
  j.job_title_short,
  j.job_title,
  j.job_location,
  j.job_via,
  j.job_schedule_type,
  j.job_work_from_home,
  j.search_location,
  j.job_posted_date,
  j.job_no_degree_mention,
  j.job_health_insurance,
  j.job_country,
  j.salary_rate,
  j.salary_year_avg,
  s.skill_id,
  s.skills,
  s.type
FROM job_postings_fact AS j
LEFT JOIN skills_job_dim AS sj
  ON j.job_id = sj.job_id
LEFT JOIN skills_dim AS s
  ON sj.skill_id = s.skill_id
WHERE
  j.job_title_short = 'Data Analyst'
  AND j.salary_year_avg IS NOT NULL
  AND j.job_work_from_home = 1
```

---

**Skill `chunk_view_0_4`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `legislators_terms` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute, for legislators whose first term began between 1917-01-01 and 1999-12-31 inclusive, the annual retention rate for each of the first 20 years after their initial term start, where retent_

```sql
SELECT
  lt.id_bioguide,
  lt.term_start AS first_term_start,
  lt.term_id,
  lt.term_start,
  lt.term_end,
  lt.term_number,
  lt.term_type,
  lt.state,
  lt.district,
  lt.party
FROM legislators_terms lt
-- Keep all columns needed to identify each legislator's terms and their first term start.
```

---

**Skill `chunk_view_0_5`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `legislators`, `legislators_terms` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: Count distinct male legislators from Louisiana who were actively serving on December 31 of a given year, grouping counts by the exact integer number of years elapsed since each legislator's firs_

```sql
SELECT
  l.id_bioguide,
  l.gender,
  lt.term_start,
  lt.term_end,
  lt.state
FROM legislators l
JOIN legislators_terms lt
  ON l.id_bioguide = lt.id_bioguide
WHERE l.gender IS NOT NULL
  AND lt.state IS NOT NULL
  AND lt.term_start IS NOT NULL
  AND lt.term_end IS NOT NULL
  AND lt.state = 'LA'
  AND (l.gender = 'M' OR l.gender = 'Male' OR l.gender = 'male')
```

---

**Skill `chunk_view_0_6`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `alien_data` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Count how many of the top 10 states by alien population have (1) percentage of friendly aliens greater than percentage of hostile aliens, and (2) average alien age greater than 200.
Required out_

```sql
SELECT
  a.current_location AS state,
  a.state AS state_abbrev,
  COUNT(*) AS alien_count,
  AVG(a.age) AS avg_age,
  SUM(CASE WHEN a.aggressive = 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS pct_friendly,
  SUM(CASE WHEN a.aggressive = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS pct_hostile
FROM alien_data a
GROUP BY a.current_location, a.state
ORDER BY alien_count DESC
LIMIT 10
```

---
