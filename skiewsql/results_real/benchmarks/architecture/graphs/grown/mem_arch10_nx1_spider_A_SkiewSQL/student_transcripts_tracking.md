# Skill graph — `student_transcripts_tracking` (2 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Addresses` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | What is the first and second line for all addresses?. How many courses in total are listed?. How many courses are there?. How is the math course described?. What are the descriptions for all the math courses?. What is the zip code of the address in the city Port Chelsea?. What is the zip code for Po |
| counter_examples | 0 |

_Task: Retrieve all addresses, including the line 1 and line 2 address components. Required outputs: The complete address, consisting of line 1, line 2, and any other relevant address information._

```sql
SELECT
  "Addresses"."line_1",
  "Addresses"."line_2"
FROM "Addresses"
```

---

**Skill `chunk_view_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Transcripts` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Retrieve all addresses, including the line 1 and line 2 address components. Required outputs: The complete address, consisting of line 1, line 2, and any other relevant address information._

```sql
SELECT
    T."other_details"
FROM
    Transcripts AS T
```

---
