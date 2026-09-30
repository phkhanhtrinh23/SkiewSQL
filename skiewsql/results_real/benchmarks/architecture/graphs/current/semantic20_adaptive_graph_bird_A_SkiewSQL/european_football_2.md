# Skill graph — `european_football_2` (2 skills)

## Skill `chunk_view_0`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Player_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Task: Calculate the number of players with an overall rating between 60 and 65 who primarily engage in attack moves rather than defensive work. Required outputs: the count of players Filters: overall_

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (3)

- Which league had the most goals in the 2016 season?
- Give the name of the league with the highest matches of all time and how many matches were played in the said league.
- What is the average height of players born between 1990 and 1995?

### Counter-examples (10)

- In Scotland Premier League, which away team won the most during the 2010 season?
- What are the speed in which attacks are put together of the top 4 teams with the highest build Up Play Speed?
- Which League had the most matches end as draw in the 2016 season?
- At present, calculate for the player's age who have a sprint speed of no less than 97 between 2013 to 2015.
- List the players' api id who had the highest above average overall ratings in 2010.
- Give the team_fifa_api_id of teams with more than 50 but less than 60 build-up play speed.
- List the long name of teams with above-average build-up play passing in 2012.
- Calculate the percentage of players who prefer left foot, who were born between 1987 and 1992.
- List the top 5 leagues in ascending order of the number of goals made in all seasons combined.
- Find the average number of long-shot done by Ahmed Samir Farag.

### Executable SQL body

```sql
SELECT
  COUNT(id)
FROM Player_Attributes
WHERE
  overall_rating BETWEEN 60 AND 65
  AND attacking_work_rate = 'low'
```

---

## Skill `chunk_view_1`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Team_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Task: Calculate the number of players with an overall rating between 60 and 65 who primarily engage in attack moves rather than defensive work. Required outputs: the count of players Filters: overall_

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (0)

—

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  COUNT(
    T.team_api_id
  )
FROM "Team_Attributes" AS T
WHERE
  T.buildUpPlaySpeed >= 60
  AND T.buildUpPlaySpeed < 65
  AND T.buildUpPlaySpeedClass = 'Balanced'
```

---
