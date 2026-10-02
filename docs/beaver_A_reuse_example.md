# View-reuse in config A on BEAVER — the actual trigger, documented faithfully

**Setup:** config A (SkiewSQL, no seed), new schema-free rewrite + N×M decompose + ReFoRCE, **strict** output match (`SKIEW_OUTPUT_MATCH=subset`). Run tag `cmpA`, full `dw_real` (108 tasks).

## Did reuse trigger? — Yes, but exactly **once** in 108 tasks

```
=== BEAVER summary [A] === tasks 108 | correct 15 (13.9%) | reuse 1 (seed 0) | gen 41 | neg-reuse 0
```

The single reuse event, from the log:

```
dw_real_117    dw    ok=0 reuse=1(seed=0) gen=0 vrej=0 graph=36 result mismatch
```

So on BEAVER, config A's self-growing view-memory is **almost entirely inert**: it reused a stored view on **1 / 108** questions (and `seed=0`, since we no longer load seeds). The other 107 questions generated fresh views (`gen=41` total) with no reuse.

## The one reuse, decoded

**Question (`dw_real_117`).** *For subjects offered in the summer term, list the subject titles, the number of instructors, and the length of the longest instructor name.*

**What was reused.** The sub-goal "subject titles" retrieved and reused an existing view `subject_titles` (grown earlier in the run) instead of generating a new one. It is the only CTE in the composed query (`gen=0` ⇒ nothing new was generated, so the single CTE **is** the reused view):

```sql
WITH subject_titles AS (
  SELECT
    ss.SUBJECT_ID   AS SUBJECT_ID,
    ss.SUBJECT_TITLE AS SUBJECT_TITLE
  FROM subject_summary ss
)
SELECT
  st.SUBJECT_TITLE                               AS subject_title,
  COUNT(DISTINCT lci.INSTRUCTOR_NAME)            AS number_of_instructors,
  MAX(CHAR_LENGTH(lci.INSTRUCTOR_NAME))          AS length_of_longest_instructor_name
FROM subject_offered so
JOIN subject_titles st ON so.SUBJECT_ID = st.SUBJECT_ID
LEFT JOIN library_subject_offered      lso ON lso.SUBJECT_ID = so.SUBJECT_ID AND lso.TERM_CODE = so.TERM_CODE
LEFT JOIN library_reserve_matrl_detail lr  ON lr.LIBRARY_SUBJECT_OFFERED_KEY = lso.LIBRARY_SUBJECT_OFFERED_KEY AND lr.TERM_CODE = lso.TERM_CODE
LEFT JOIN library_course_instructor    lci ON lci.LIBRARY_COURSE_INSTRUCTOR_KEY = lr.LIBRARY_COURSE_INSTRUCTOR_KEY
WHERE so.TERM_CODE LIKE '%SU'
GROUP BY st.SUBJECT_TITLE
```

**Outcome.** `ok=0` (result mismatch) — **but `neg-reuse=0`**. That combination is the point:

- `subject_titles` is a **trivial projection** (`SELECT <cols> FROM <one table>`, no filter/join/agg). `is_trivial_projection` → true, so it is **causally inert**: reusing it neither helped nor hurt.
- The wrong answer comes from the **unrelated instructor-join chain** (`library_subject_offered → library_reserve_matrl_detail → library_course_instructor`), not from the reuse. That is exactly why the negative-reuse metric (which only counts *non-trivial* reuse that precedes a wrong answer) correctly reports **0** here.

## Honest takeaway

- **Reuse fired, but it was a trivial building-block reuse**, and it neither caused nor prevented the failure. There is **no example on BEAVER A of a *non-trivial* skill being reused** in this run.
- This matches the broader finding: without cold-start seeds, config A's view-memory is effectively a **per-question compose scaffold**, not a cross-question skill library — reuse ≈ 0 and its accuracy edge on BEAVER (13.9% vs 8–11% for the baselines) comes from **N×M decomposition + ReFoRCE**, not from reuse.
- The lever to make reuse *meaningful and safe* is a **partial-match augment operator** (reuse a ≥k%-relevant view and explicitly join the missing columns), not the current all-or-nothing guard — which under relaxed match produced net-negative reuse on BEAVER instead.
