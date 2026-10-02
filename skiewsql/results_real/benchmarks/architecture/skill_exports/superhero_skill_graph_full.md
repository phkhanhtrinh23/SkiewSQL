# Skill graph — `superhero` (29 skills)

## Skill `superhero_core`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `one row per superhero.id` |
| output columns | `id`, `superhero_name`, `full_name`, `gender_id`, `eye_colour_id`, `hair_colour_id`, `skin_colour_id`, `race_id`, `publisher_id`, `alignment_id`, `height_cm`, `weight_kg` |
| source tables | `superhero` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `superhero_basic_demographics`, `superhero_core_attributes`, `superhero_basic_attributes`, `superhero_physical_cohort` |

### Description

One row per superhero with canonical identity and foreign-key ids for joins (clean projection of core superhero attributes).

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
  s.id AS id,
  s.superhero_name AS superhero_name,
  s.full_name AS full_name,
  s.gender_id AS gender_id,
  s.eye_colour_id AS eye_colour_id,
  s.hair_colour_id AS hair_colour_id,
  s.skin_colour_id AS skin_colour_id,
  s.race_id AS race_id,
  s.publisher_id AS publisher_id,
  s.alignment_id AS alignment_id,
  s.height_cm AS height_cm,
  s.weight_kg AS weight_kg
FROM superhero s
```

---

## Skill `hero_power_link`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `hero_id`, `power_id` |
| output columns | `hero_id`, `power_id` |
| source tables | `hero_power` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `superhero_power_membership` |

### Description

Row-level link between a superhero and each superpower they possess (one row per hero-power relationship).

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (1)

- Among the superheroes with the super power of "Super Strength", how many of them have a height of over 200cm?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  hero_id,
  power_id
FROM hero_power
```

---

## Skill `superpower_dim`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `power_name` |
| source tables | `superpower` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Canonical projection of superpower entities (one row per superpower id with its name).

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (2)

- Among the superheroes with the super power of "Super Strength", how many of them have a height of over 200cm?
- How many heroes have stealth power?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  id,
  power_name
FROM
  superpower
```

---

## Skill `superhero_base`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `superhero_name`, `full_name`, `height_cm`, `weight_kg`, `gender_id`, `publisher_id`, `alignment_id`, `race_id`, `eye_colour_id`, `hair_colour_id`, `skin_colour_id` |
| source tables | `superhero` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `superhero_core_attributes`, `superhero_basic_attributes` |

### Description

Canonical superhero rows with key identity and core attributes (one row per superhero). Cleans/normalizes raw columns and exposes the id and columns commonly used for filtering, grouping and joining.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (8)

- Among the superheroes with blue eyes, how many of them have the super power of "Agility"?
- Please list the superhero names of all the superheroes that have blue eyes and blond hair.
- List the superheroes from Marvel Comics who have the super power of 'Super Strength'.
- How many gold-eyed superheroes did Marvel Comics publish?
- What is Copycat's race?
- What are the names of the superheroes with the power of death touch?
- How many female superheroes have a strength value of 100?
- What is the total number of superheroes without full name?

### Counter-examples (2)

- Between DC and Marvel Comics, which publisher has published more superheroes? Find the difference in the number of superheroes they have published.
- Which superhero has the most durability published by Dark Horse Comics?

### Executable SQL body

```sql
SELECT
  s.id,
  s.superhero_name,
  s.full_name,
  s.height_cm,
  s.weight_kg,
  s.gender_id,
  s.publisher_id,
  s.alignment_id,
  s.race_id,
  s.eye_colour_id,
  s.hair_colour_id,
  s.skin_colour_id AS skin_colour_id
FROM superhero s
```

---

## Skill `hero_power_link_4`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `hero_id`, `power_id` |
| output columns | `hero_id`, `power_id`, `power_name` |
| source tables | `hero_power`, `superpower` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Row-level mapping of which superhero (hero_id) has which power (power_id) with power name included. One row per hero-power association to support filtering heroes by specific powers.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (4)

- List the superheroes from Marvel Comics who have the super power of 'Super Strength'.
- What are the names of the superheroes with the power of death touch?
- List down at least five superpowers of male superheroes.
- What are the superpowers of heroes with ID 1?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  hp.hero_id AS hero_id,
  hp.power_id AS power_id,
  sp.power_name AS power_name
FROM hero_power AS hp
JOIN superpower AS sp ON sp.id = hp.power_id
```

---

## Skill `colour_lookup`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `colour` |
| source tables | `colour` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Lookup of colour id to colour name for all colour roles (eye, hair, skin). Useful to filter superheroes by a human-readable colour.

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
  colour.id AS id,
  colour.colour AS colour
FROM colour
```

---

## Skill `colour_lookup_6`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `colour` |
| source tables | `colour` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Denormalized mapping of colour ids to colour text. Each row is one colour id and its name. Intended to join to superhero colour foreign keys for human-readable filters and results.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (1)

- How many gold-eyed superheroes did Marvel Comics publish?

### Counter-examples (1)

- Provide the hair colour of the human superhero who is 185 cm tall.

### Executable SQL body

```sql
SELECT
  id,
  colour
FROM colour
```

---

## Skill `superhero_with_colour_names`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `superhero_name`, `eye_colour`, `hair_colour`, `skin_colour` |
| source tables | `superhero`, `colour` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Denormalized hero-level view that attaches eye, hair, and skin colour names to each superhero row for easy textual filtering and presentation.

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
  s.id AS id,
  s.superhero_name AS superhero_name,
  ce.colour AS eye_colour,
  ch.colour AS hair_colour,
  cs.colour AS skin_colour
FROM superhero AS s
LEFT JOIN colour AS ce ON s.eye_colour_id = ce.id
LEFT JOIN colour AS ch ON s.hair_colour_id = ch.id
LEFT JOIN colour AS cs ON s.skin_colour_id = cs.id
```

---

## Skill `superhero_basic_demographics`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `superhero_name`, `full_name`, `gender_id`, `gender`, `publisher_id`, `publisher_name`, `alignment_id`, `alignment`, `race_id`, `race`, `eye_colour_id`, `eye_colour`, `hair_colour_id`, `hair_colour`, `skin_colour_id`, `skin_colour`, `height_cm`, `weight_kg` |
| source tables | `superhero_core`, `gender`, `publisher`, `alignment`, `race`, `colour` |
| depends_on (builds on) | `superhero_core` |
| depended-on by (builds on this) | `superhero_denorm_basic_dims` |

### Description

One row per superhero with primary identifying and demographic columns joined to their referenced lookup labels (gender, publisher, alignment, race, eye/hair/skin colours). Useful as a denormalized superhero master for filtering, display, and further aggregation.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (8)

- List the superheroes from Marvel Comics who have the super power of 'Super Strength'.
- Which publisher published the slowest superhero?
- What is Copycat's race?
- Give the publisher ID of Star Trek.
- What is the average weight of all female superheroes?
- Among the superheroes with height from 170 to 190, list the names of the superheroes with no eye color.
- Among the male superheroes, list the super hero names of superheroes with weight greater than the 79% average weight of all superheroes.
- How many heroes have stealth power?

### Counter-examples (6)

- Rank superheroes from Marvel Comics by their eye color popularity, starting with the most common color.
- What is the percentage of superheroes who act in their own self-interest or make decisions based on their own moral code? Indicate how many of the said superheroes were published by Marvel Comics.
- Between DC and Marvel Comics, which publisher has published more superheroes? Find the difference in the number of superheroes they have published.
- Provide the hair colour of the human superhero who is 185 cm tall.
- What is the hero's full name with the highest attribute in strength?
- List the eyes, hair and skin colour of all female superheroes published by Dark Horse Comics.

### Executable SQL body

```sql
SELECT
  s.id,
  s.superhero_name,
  s.full_name,
  s.gender_id,
  g.gender AS gender,
  s.publisher_id,
  p.publisher_name AS publisher_name,
  s.alignment_id,
  a.alignment AS alignment,
  s.race_id,
  r.race AS race,
  s.eye_colour_id,
  ec.colour AS eye_colour,
  s.hair_colour_id,
  hc.colour AS hair_colour,
  s.skin_colour_id,
  sc.colour AS skin_colour,
  s.height_cm,
  s.weight_kg
FROM superhero_core s
LEFT JOIN gender g ON s.gender_id = g.id
LEFT JOIN publisher p ON s.publisher_id = p.id
LEFT JOIN alignment a ON s.alignment_id = a.id
LEFT JOIN race r ON s.race_id = r.id
LEFT JOIN colour ec ON s.eye_colour_id = ec.id
LEFT JOIN colour hc ON s.hair_colour_id = hc.id
LEFT JOIN colour sc ON s.skin_colour_id = sc.id
```

---

## Skill `superhero_attributes_raw`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `hero_id`, `attribute_id` |
| output columns | `hero_id`, `attribute_id`, `attribute_value` |
| source tables | `hero_attribute` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Raw hero-attribute rows: one row per (hero_id, attribute_id) exposing the attribute value. Useful for computing per-hero aggregates or filtering heroes by attribute thresholds.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (2)

- Which publisher published the slowest superhero?
- What is the total number of superheroes without full name?

### Counter-examples (2)

- What is the percentage of superheroes who act in their own self-interest or make decisions based on their own moral code? Indicate how many of the said superheroes were published by Marvel Comics.
- What is the hero's full name with the highest attribute in strength?

### Executable SQL body

```sql
SELECT
  hero_id AS hero_id,
  attribute_id AS attribute_id,
  attribute_value AS attribute_value
FROM hero_attribute
```

---

## Skill `superhero_power_membership`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `hero_id`, `power_id` |
| output columns | `hero_id`, `power_id` |
| source tables | `hero_power` |
| depends_on (builds on) | `hero_power_link` |
| depended-on by (builds on this) | — |

### Description

One row per (hero_id, power_id) listing a hero's superpowers and allowing filtering or counting powers per hero.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (2)

- What are the superpowers of heroes with ID 1?
- How many heroes have stealth power?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT DISTINCT
  hero_id,
  power_id
FROM hero_power
```

---

## Skill `colour_lookup_11`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `colour` |
| source tables | `colour` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Colour reference table exposing colour id and normalized colour text for joins and labels.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (1)

- Among the superheroes with height from 170 to 190, list the names of the superheroes with no eye color.

### Counter-examples (1)

- List the eyes, hair and skin colour of all female superheroes published by Dark Horse Comics.

### Executable SQL body

```sql
SELECT
  id,
  colour
FROM colour
```

---

## Skill `attribute_lookup`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `attribute_name` |
| source tables | `attribute` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Canonical attribute id to attribute_name mapping for filtering or labeling attributes.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (1)

- How many female superheroes have a strength value of 100?

### Counter-examples (1)

- What is the hero's full name with the highest attribute in strength?

### Executable SQL body

```sql
SELECT
  id,
  attribute_name
FROM attribute
```

---

## Skill `publisher_lookup`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `publisher_name` |
| source tables | `publisher` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Publisher lookup table exposing publisher id and name. Useful for translating publisher ids in superhero rows to publisher names for filters and group-bys.

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
  id,
  publisher_name
FROM
  publisher
```

---

## Skill `attribute_lookup_14`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `attribute_name` |
| source tables | `attribute` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Attribute id to attribute_name mapping. One row per attribute.id. Useful to resolve attribute_name filters (e.g., 'Intelligence') to attribute_id for use with hero_attribute_rows.

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
  attribute.id AS id,
  attribute.attribute_name AS attribute_name
FROM attribute
```

---

## Skill `race_lookup`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `race` |
| source tables | `race` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Lookup table for race id to race name mapping (one row per race).

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
  id,
  race
FROM
  race
```

---

## Skill `hero_attribute_values`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `hero_id`, `attribute_id` |
| output columns | `hero_id`, `superhero_name`, `full_name`, `attribute_id`, `attribute_name`, `attribute_value` |
| source tables | `superhero`, `hero_attribute`, `attribute` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Denormalized row-level relation of each hero's attribute values, joining hero, attribute, and hero_attribute so each row is a single attribute measurement for a single superhero.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (1)

- How many female superheroes have a strength value of 100?

### Counter-examples (1)

- Which superhero has the most durability published by Dark Horse Comics?

### Executable SQL body

```sql
SELECT
  h.id AS hero_id,
  h.superhero_name AS superhero_name,
  h.full_name AS full_name,
  a.id AS attribute_id,
  a.attribute_name AS attribute_name,
  ha.attribute_value AS attribute_value
FROM superhero AS h
JOIN hero_attribute AS ha
  ON h.id = ha.hero_id
JOIN attribute AS a
  ON ha.attribute_id = a.id
```

---

## Skill `superpower_basic`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `power_name` |
| source tables | `superpower` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Canonical listing of superpowers with stable ids and normalized names.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (2)

- List down at least five superpowers of male superheroes.
- What are the superpowers of heroes with ID 1?

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  id,
  power_name
FROM superpower
```

---

## Skill `superhero_core_18`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `superhero_name`, `full_name`, `alignment_id`, `publisher_id`, `gender_id`, `height_cm`, `weight_kg`, `eye_colour_id`, `hair_colour_id`, `skin_colour_id`, `race_id` |
| source tables | `superhero` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `superhero_core_attributes`, `superhero_basic_attributes` |

### Description

One row per superhero with canonicalized FK ids and basic attributes needed for filtering and counting (publisher, alignment, name, physical measures). NULLs are preserved so caller can decide how to treat them.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (2)

- List down at least five superpowers of male superheroes.
- Among the male superheroes, list the super hero names of superheroes with weight greater than the 79% average weight of all superheroes.

### Counter-examples (0)

—

### Executable SQL body

```sql
SELECT
  s.id AS id,
  s.superhero_name AS superhero_name,
  s.full_name AS full_name,
  s.alignment_id AS alignment_id,
  s.publisher_id AS publisher_id,
  s.gender_id AS gender_id,
  s.height_cm AS height_cm,
  s.weight_kg AS weight_kg,
  s.eye_colour_id AS eye_colour_id,
  s.hair_colour_id AS hair_colour_id,
  s.skin_colour_id AS skin_colour_id,
  s.race_id AS race_id
FROM superhero AS s
```

---

## Skill `publisher_lookup_19`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `publisher_name` |
| source tables | `publisher` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Publisher dimension lookup exposing publisher id and canonical publisher_name for joins and filtering.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (2)

- Give the publisher ID of Star Trek.
- Which superhero has the same eyes, hair and skin colour? Indicate the publisher of the superhero.

### Counter-examples (1)

- Which superhero has the most durability published by Dark Horse Comics?

### Executable SQL body

```sql
SELECT
  id,
  publisher_name
FROM publisher
```

---

## Skill `superhero_denorm_basic_dims`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `superhero.id` |
| output columns | `id`, `superhero_name`, `full_name`, `gender`, `publisher_name`, `alignment`, `race`, `eye_colour`, `hair_colour`, `skin_colour`, `height_cm`, `weight_kg` |
| source tables | `superhero`, `gender`, `publisher`, `alignment`, `race`, `colour` |
| depends_on (builds on) | `superhero_basic_demographics` |
| depended-on by (builds on this) | — |

### Description

Denormalized superhero rows joining in common dimension text (gender, publisher, alignment, race, colours) to expose human-readable attributes for filtering/grouping in queries. One row per superhero. Do not aggregate measures.

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
  s.id AS id,
  s.superhero_name AS superhero_name,
  s.full_name AS full_name,
  s.gender AS gender,
  s.publisher_name AS publisher_name,
  s.alignment AS alignment,
  s.race AS race,
  s.eye_colour AS eye_colour,
  s.hair_colour AS hair_colour,
  s.skin_colour AS skin_colour,
  s.height_cm AS height_cm,
  s.weight_kg AS weight_kg
FROM superhero_basic_demographics s
```

---

## Skill `superhero_base_21`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `superhero_name`, `full_name`, `gender_id`, `weight_kg`, `height_cm`, `publisher_id`, `alignment_id`, `race_id`, `eye_colour_id`, `hair_colour_id`, `skin_colour_id` |
| source tables | `superhero` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `superhero_core_attributes`, `superhero_basic_attributes` |

### Description

Base row-level cohort of superheroes with relevant identifying and demographic columns (one row per superhero). Keeps raw measures like weight and keys to related dimension tables.

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
  s.id AS id,
  s.superhero_name AS superhero_name,
  s.full_name AS full_name,
  s.gender_id AS gender_id,
  s.weight_kg AS weight_kg,
  s.height_cm AS height_cm,
  s.publisher_id AS publisher_id,
  s.alignment_id AS alignment_id,
  s.race_id AS race_id,
  s.eye_colour_id AS eye_colour_id,
  s.hair_colour_id AS hair_colour_id,
  s.skin_colour_id AS skin_colour_id
FROM superhero s
```

---

## Skill `gender_lookup`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `gender` |
| source tables | `gender` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Normalized mapping of gender id to canonical gender text. One row per gender.id.

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
  g.id AS id,
  g.gender AS gender
FROM gender g
```

---

## Skill `superhero_core_attributes`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `superhero_name`, `full_name`, `height_cm`, `weight_kg`, `gender_id`, `eye_colour_id`, `hair_colour_id`, `skin_colour_id`, `race_id`, `publisher_id`, `alignment_id` |
| source tables | `superhero` |
| depends_on (builds on) | `superhero_core`, `superhero_base`, `superhero_core_18`, `superhero_base_21` |
| depended-on by (builds on this) | `superhero_basic_attributes` |

### Description

One row per superhero with key identifying columns and raw attribute-like fields normalized (no joins to lookups). Exposes height, weight, name columns and foreign-key ids for joins.

### Semantic filters

```json
{}
```

### Learned skill parameters

```json
{}
```

### Validated on (1)

- Which superhero has the same eyes, hair and skin colour? Indicate the publisher of the superhero.

### Counter-examples (1)

- Provide the hair colour of the human superhero who is 185 cm tall.

### Executable SQL body

```sql
SELECT
  s.id,
  s.superhero_name,
  s.full_name,
  s.height_cm,
  s.weight_kg,
  s.gender_id,
  s.eye_colour_id,
  s.hair_colour_id,
  s.skin_colour_id,
  s.race_id,
  s.publisher_id,
  s.alignment_id
FROM superhero s
```

---

## Skill `superhero_basic_attributes`

Category: `NORM`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `superhero_id`, `superhero_name`, `full_name`, `height_cm`, `weight_kg`, `publisher_id`, `alignment_id`, `gender_id`, `eye_colour_id`, `hair_colour_id`, `skin_colour_id`, `race_id` |
| source tables | `superhero` |
| depends_on (builds on) | `superhero_core`, `superhero_base`, `superhero_core_18`, `superhero_base_21`, `superhero_core_attributes` |
| depended-on by (builds on this) | — |

### Description

Canonical, cleaned projection of superhero core attributes and foreign keys (one row per superhero). Keeps raw numeric measures (height_cm, weight_kg) and references to related dimension ids for joins.

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
  s.id AS superhero_id,
  s.superhero_name AS superhero_name,
  s.full_name AS full_name,
  s.height_cm AS height_cm,
  s.weight_kg AS weight_kg,
  s.publisher_id AS publisher_id,
  s.alignment_id AS alignment_id,
  s.gender_id AS gender_id,
  s.eye_colour_id AS eye_colour_id,
  s.hair_colour_id AS hair_colour_id,
  s.skin_colour_id AS skin_colour_id,
  s.race_id AS race_id
FROM superhero s
```

---

## Skill `superhero_with_publisher`

Category: `JOIN`

| field | value |
|---|---|
| grain (one row per) | `superhero.id` |
| output columns | `superhero_id`, `superhero_name`, `height_cm`, `publisher_id`, `publisher_name` |
| source tables | `superhero`, `publisher` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Denormalized view joining superhero to publisher name (one row per superhero). Exposes publisher_name alongside superhero core columns for easy filtering and grouping by publisher.

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
  s.id AS superhero_id,
  s.superhero_name AS superhero_name,
  s.height_cm AS height_cm,
  p.id AS publisher_id,
  p.publisher_name AS publisher_name
FROM superhero s
LEFT JOIN publisher p
  ON s.publisher_id = p.id
```

---

## Skill `superhero_physical_cohort`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `superhero_id`, `height_cm`, `weight_kg` |
| source tables | `superhero_core` |
| depends_on (builds on) | `superhero_core` |
| depended-on by (builds on this) | — |

### Description

Cohort view selecting superheroes with available height (and optional weight) measures. One row per superhero, intended for building cohorts by physical attributes (height/weight ranges).

### Semantic filters

```json
{
  "height_cm": "IS NOT NULL"
}
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
  id AS superhero_id,
  height_cm,
  weight_kg
FROM
  superhero_core
WHERE
  height_cm IS NOT NULL
```

---

## Skill `superhero_with_attributes_and_powers_counts`

Category: `AGG`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `superhero_name`, `weight_kg`, `height_cm`, `num_powers`, `num_attributes` |
| source tables | `superhero`, `hero_power`, `hero_attribute` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Per-superhero aggregated measures: counts of linked powers and attributes plus raw measures. Useful for questions that rank or filter heroes by capability breadth while preserving one row per hero.

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
  s.id AS id,
  s.superhero_name AS superhero_name,
  s.weight_kg AS weight_kg,
  s.height_cm AS height_cm,
  COALESCE(p.num_powers, 0) AS num_powers,
  COALESCE(a.num_attributes, 0) AS num_attributes
FROM superhero s
LEFT JOIN (
  SELECT hero_id, COUNT(DISTINCT power_id) AS num_powers
  FROM hero_power
  GROUP BY hero_id
) p ON s.id = p.hero_id
LEFT JOIN (
  SELECT hero_id, COUNT(DISTINCT attribute_id) AS num_attributes
  FROM hero_attribute
  GROUP BY hero_id
) a ON s.id = a.hero_id
```

---

## Skill `superhero_colour_cohort`

Category: `SEL`

| field | value |
|---|---|
| grain (one row per) | `id` |
| output columns | `id`, `superhero_name`, `eye_colour_id`, `hair_colour_id`, `skin_colour_id`, `all_colours_equal` |
| source tables | `superhero` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |

### Description

Cohort of superheroes annotated with whether all three colour FK columns are equal. One row per superhero. Useful for queries that look for matching or differing eye/hair/skin colours.

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
  s.id AS id,
  s.superhero_name AS superhero_name,
  s.eye_colour_id AS eye_colour_id,
  s.hair_colour_id AS hair_colour_id,
  s.skin_colour_id AS skin_colour_id,
  CASE
    WHEN s.eye_colour_id IS NOT NULL
     AND s.hair_colour_id IS NOT NULL
     AND s.skin_colour_id IS NOT NULL
     AND s.eye_colour_id = s.hair_colour_id
     AND s.eye_colour_id = s.skin_colour_id
    THEN 1
    WHEN s.eye_colour_id IS NULL
     OR s.hair_colour_id IS NULL
     OR s.skin_colour_id IS NULL
    THEN 0
    WHEN s.eye_colour_id = s.hair_colour_id
     AND s.eye_colour_id = s.skin_colour_id
    THEN 1
    ELSE 0
  END AS all_colours_equal
FROM superhero s
```

---
