# Skill graph — `european_football_2` (2 skills)

## Skill `chunk_view_1`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Team`, `Team_Attributes` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Task: Identify the player with the maximum overall rating and return their API ID. Required outputs: The API ID of the player with the highest overall rating.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (2)

- Which league had the most goals in the 2016 season?
- List the top 5 leagues in ascending order of the number of goals made in all seasons combined.

### Counter-examples (10)

- What are the speed in which attacks are put together of the top 4 teams with the highest build Up Play Speed?
- Which League had the most matches end as draw in the 2016 season?
- At present, calculate for the player's age who have a sprint speed of no less than 97 between 2013 to 2015.
- Give the name of the league with the highest matches of all time and how many matches were played in the said league.
- What is the average height of players born between 1990 and 1995?
- List the players' api id who had the highest above average overall ratings in 2010.
- Give the team_fifa_api_id of teams with more than 50 but less than 60 build-up play speed.
- List the long name of teams with above-average build-up play passing in 2012.
- Calculate the percentage of players who prefer left foot, who were born between 1987 and 1992.
- Find the average number of long-shot done by Ahmed Samir Farag.

### Executable SQL body

```sql
SELECT
  T2."team_api_id"
FROM Team AS T2
JOIN Team_Attributes AS TA1
  ON T2."team_api_id" = TA1."team_api_id"
WHERE
  TA1."team_fifa_api_id" = 434
```

---

## Skill `chunk_view_2`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Match` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Task: Identify the player with the maximum overall rating and return their API ID. Required outputs: The API ID of the player with the highest overall rating.

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
  "home_player_X1"
FROM "Match"
ORDER BY
  "B365H" DESC
LIMIT 1
```

---
