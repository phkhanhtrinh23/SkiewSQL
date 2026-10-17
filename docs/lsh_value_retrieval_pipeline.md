# LSH Value Retrieval — Full Pipeline, What Goes In / What Comes Out, and Impact

This documents AV-SQL's MinHash-LSH **value retrieval** end-to-end on the Spider2-lite / BEAVER runs (model `gpt-5-mini`): exactly where it sits in the pipeline, what literal goes *into* the LSH, what stored value comes *out*, a worked case where the correction is objectively necessary, the full list of real corrections observed, and the measured impact.

TL.DR — LSH **does** surface correct DB values the model would otherwise get wrong (e.g. `United States` → `United States of America`, where an equality filter on the model's literal returns **0 rows**). But on `gpt-5-mini` its *aggregate* effect is small, because the strong model routes around value-spelling with `LIKE` patterns and many DBs expose a clean normalized column. Measured net impact: **0 points on BEAVER** (2.8% → 2.8%) and **+1.5 pts on Spider2-lite** (36.3% vs 34.8% in a controlled LSH-on/off ablation) — but that +1.5 hides a near coin-flip: **toggling LSH changes 24 of 135 answers (13 helped, 11 hurt)**. LSH's corrections are real and individually meaningful, yet in aggregate they help and harm in near-equal measure. See §5.

---

## 1. Where LSH sits in the pipeline

```
question ──► REPHRASE ──► CTE AGENT (per schema chunk) ──► PLANNER ──► SQL AGENT ──► REVISE (≤5 exec-fix)
                              │
                              │  the CTE agent writes a candidate CTE containing literals,
                              │  e.g.  WHERE country_name = 'United States'
                              ▼
                        ┌───────────────────────────────────────────────┐
                        │  LSH VALUE RETRIEVAL (skiewsql/avsql_prep.py)   │
                        │  in:  each literal the CTE used                 │
                        │  out: closest REAL stored DB values             │
                        │  → injected back into the CTE fix-prompt        │
                        └───────────────────────────────────────────────┘
```

LSH fires **inside the CTE agent's fix loop** (`cte_agent.process_relevant_values`). It does not change the schema or the plan — it only feeds the model the real spellings of the values it tried to filter on, so the next fix attempt can correct them.

---

## 2. The LSH mechanism — what goes IN, what comes OUT

**Offline (build):** for each DB, every distinct **string** column value is hashed into a MinHash (3-gram shingles, 128 permutations) and inserted into a `MinHashLSH`. The index is a local pickle (`lsh_output/<db>/lsh_index/*.pkl`). Numeric columns and id/date/code-like columns are skipped. (BEAVER's index is a 558 MB full-scan over 97 tables / 1530 columns.)

**Online (per literal), `get_relevant_values(query_str)`:**

| stage | operation | example |
|---|---|---|
| **IN** | the literal the model put in the CTE | `query_str = 'United States'` |
| 1. LSH | MinHash the literal (3-gram, 128-perm), query the index → candidate keys | candidates: values sharing char-trigrams |
| 2. edit filter | keep candidates with edit-similarity ≥ `edit_similarity_threshold` (0.5) | drops far strings |
| 3. embedding filter | keep candidates with cosine(MiniLM) ≥ `embedding_similarity_threshold` (0.5) | drops semantically unrelated |
| **OUT** | top-k stored values, formatted and injected | `Relevant stored values for 'United States': "United States of America" from table 'countries', column 'country_name'` |

The injected block is appended to the CTE fix-prompt with the instruction *"Use these relevant values to revise the format and spelling of values in the CTE."* Numeric literals are never looked up.

---

## 3. Worked case where LSH is objectively necessary — `local060` (complex_oracle)

**Question (excerpt):** *"**In the United States**, for Q4 2019 and Q4 2020, first select only those cities where total sales … rose by at least 20% …"*

**What the model naturally writes** from the phrase "in the United States":
```sql
... WHERE country_name = 'United States' ...
```

**LSH input → output (from the run log):**
```
[ValueManager] query_str : 'United States'
Relevant stored values for 'United States' in database:
  "United States of America" from table 'countries', column 'country_name'
  "United States of Ame"     from table 'currency',  column 'country'   (truncated to 20 chars in that table)
```

**Objective proof the correction matters** (run directly on the DB):
```
countries.country_name = 'United States'             -> 0 rows
countries.country_name = 'United States of America'  -> 1 row
actual distinct values LIKE '%United%': ['United Kingdom', 'United States of America']
```
So a plain equality filter on the model's literal returns **nothing** → the whole query is empty → wrong. LSH supplies the only value that works.

**What actually happened here (honest):** the model hedged and wrote `country_name LIKE 'United States%'`, which *also* matches `United States of America`, so `local060` executed with data either way. This is precisely why LSH's aggregate lift is small on `gpt-5-mini`: **the model often defends against value-spelling with `LIKE`**, so the LSH correction, while real and correct, was not strictly required on this instance. On a model (or a prompt) that writes exact-equality filters, the same correction is the difference between 0 rows and the right answer.

---

## 4. Every real correction LSH produced (Spider2-lite skill-graph run)

Across the run the value manager issued **477** lookups. **150** returned ≥1 stored value. **100** returned a value textually different from the query. Filtering out numeric/date/short-string noise, the genuine *semantic* corrections were:

| IN (model's literal) | OUT (real stored value) | note |
|---|---|---|
| `United States` | `United States of America` | equality on the literal = 0 rows (§3) |
| `United States of Ame` | `United States of America` | recovers a value truncated to 20 chars in `currency` |
| `Data Analyst` | `CRM Data Analyst`, `Data Analyst I`, `Data Analyst II` | surfaces job-title variants |
| `%Data Analyst%` | `Data Analyst`, `CRM Data Analyst`, `IT Data Analyst` | exact values behind a LIKE |
| `/detail` | `/detail/`, `detail` | URL-path normalization |
| `/complete` | `/contact/complete` | URL-path completion |
| `Bronx` | `Bronxdale` | borderline / likely noise |

And the noise LSH also returns (why edit+embedding thresholds matter, and why it is not free): short strings (`G` → `PG`), and date mismatches (`2021-07-01` → `1921-07-07`). These are filtered or ignored by the model but show LSH is a fuzzy, not exact, retriever.

---

## 5. Measured impact

**BEAVER — the one place AV-SQL was run with *and* without LSH:**

| AV-SQL on BEAVER (108 scored) | value layer | accuracy |
|---|---|---|
| no LSH | — | **2.8%** (3/108) |
| + full-scan LSH + skill-graph | 558 MB index | **2.8%** (3/108) |
| + full-scan LSH + CHESS | 558 MB index | **2.8%** (3/108) |

→ **0-point change.** On BEAVER the bottleneck is composing 11+ schema chunks, not value spelling, so even a full-scan index over 1530 columns changes nothing.

**Spider2-lite — the controlled LSH-on vs LSH-off ablation (now complete, all 135):**

| AV-SQL on Spider2-lite (135) | accuracy |
|---|---|
| **LSH ON** | **49/135 = 36.3%** |
| **LSH OFF** (`gpt5mini_nolsh.yaml`) | **47/135 = 34.8%** |
| **net effect of LSH** | **+2 questions (+1.5 pts)** |

But the net hides the real story — **LSH is close to a coin-flip, not a clean win:**

- **LSH flipped 13 questions wrong → right** (`on✓ off✗`): `local026,024,229,335` (IPL/f1), `local031,037` (Brazilian_E_Commerce), `local074,300,301` (bank_sales_trading), `local132` (EntertainmentAgency), `local199` (sqlite-sakila), `local209` (delivery_center), `local262` (stacking).
- **LSH flipped 11 questions right → wrong** (`off✓ on✗`): `local028` (Brazilian_E_Commerce), `local041` (modern_data), `local055` (chinook), `local067` (complex_oracle), `local070` (city_legislation), `local085` (northwind), `local131` (EntertainmentAgency), `local157` (bank_sales_trading), `local197` (sqlite-sakila), `local210` (delivery_center), `local310` (f1).

So **24 of 135 answers (18%) change** when LSH is toggled, but they nearly cancel (13 − 11 = +2). Confirmed *difference-making* cases exist — e.g. `local031` (Brazilian_E_Commerce), where LSH surfaced the order-status value `'delivered'` and the query became correct — but for **every** such win there is almost a matching loss, where an LSH candidate (often a noisy near-match like `G`→`PG` or a truncated `United States of Ame`) **mislead** the model into a worse filter.

**Verdict:** LSH's value corrections are real and individually meaningful, but on `gpt-5-mini` over these benchmarks the retriever helps and harms in near-equal measure, so the aggregate effect is a wash — **+1.5 pts on Spider2-lite, 0 pts on BEAVER.** It is not a reliable accuracy lever here.

---

## 6. Conclusion

- **What goes into LSH:** the literal values the CTE agent writes (e.g. `'United States'`), one lookup per non-numeric literal.
- **What comes out:** the closest real stored DB values (e.g. `'United States of America'`), injected as a spelling/format hint.
- **When it matters:** whenever the natural-language value differs from the stored value *and* the query filters by equality — then the model's literal returns 0 rows and LSH is the fix (objectively shown in §3).
- **Why it is nearly inert here:** `gpt-5-mini` sees each column's example values in the schema prompt, hedges filters with `LIKE`, and many DBs expose a clean normalized column — so the correct value is usually reached without LSH. Net measured effect on BEAVER = 0. The Spider2-lite flip count is being measured.

LSH is a genuinely useful, correctly-functioning component (it retrieves the right values), but on a strong model over these benchmarks it is **rarely the deciding factor** — the same verdict reached for the skill-graph.

---

## Reproduction
- Maintained LSH code: `skiewsql/avsql_prep.py` (`AVSQLValueIndex.query`, `relevant_values`, and `ground`). Active runners pass its grounding hints to the agents in `skiewsql/agents.py`.
- Indexes: `~/skiew_together/avsql_s2local/lsh_output/<db>/lsh_index/*.pkl`, `~/skiew_together/avsql_beaver/lsh_output/dw/lsh_index/*.pkl`.
- LSH-on run: `~/skiew_together/avsql_s2local/logs/`. LSH-off run: `~/skiew_together/avsql_s2local/logs_nolsh/` (in progress).
- Correction log: search `Relevant stored values for` in `~/skiew_together/avsql_s2local/run_reuse.log`.
