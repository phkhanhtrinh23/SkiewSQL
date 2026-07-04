# SkiewSQL — Graph Data Structure & View Retrieval

Reference for the memory that makes SkiewSQL work: the **self-growing view graph** and the
**retrieval** that decides, per sub-goal, whether an existing view can be reused instead of
generating a new CTE. Everything here describes the real pipeline in `core.py`, `sqlview.py`,
`realrun.py` (retrieval flavor 2 = dense embeddings); the deterministic mechanism study
(`core.retrieve`) is flavor 1 = TF-IDF.

---

## 1. Overview

Retrieval is a **hybrid symbolic + neural** lookup:

```
sub-goal (ViewRequest)
      │
      ▼
[1] category bucket        ── same skill category only  (exact categorical match)
      │
      ▼
[2] compatibility contract ── HARD gate: outputs ⊇, grain ⊑, filters =   (negative-reuse guard)
      │  (survivors)
      ▼
[3] dense similarity rank  ── cosine(embed(req.text), embed(view.description)), argmax
      │
      ▼
[4] threshold τ            ── accept best iff sim ≥ τ, else MISS → generate
```

Both gates must pass: the **contract** guarantees the view is *usable* (correctness), the
**threshold** guarantees it is *about the right thing* (relevance). Retrieval runs once per
sub-goal; a question has up to `max_views` sub-goals.

---

## 2. Data structures

### 2.1 `ViewSpec` — a graph node (a reusable CTE + its interface)  ·  `core.py`
```
name            : str                      # unique key within a database's graph
category        : str                      # SEL|NORM|AGG|JOIN|RANK|WIN|RESHAPE|SET|REC|SEM
body_sql        : str                      # the SELECT defining the CTE body (no WITH wrapper)
source_tables   : list[str]
output_columns  : list[str]                # INTERFACE: columns the view exposes
grain           : list[str]                # key columns → granularity ([] = scalar/single row)
semantic_filters: dict[str,str]            # intrinsic filters, e.g. {"status":"active"}
depends_on      : list[str]                # names of other views it builds on (→ DEPENDS_ON edges)
description     : str                       # NL "when to use" → the retrieval embedding text
```
`cte_clause()` renders `name AS (\n body_sql \n)`. A `ViewSpec` is simultaneously a **node**, an
**interface/type signature** (`category`, `output_columns`, `grain`, `semantic_filters`), and an
**executable artifact** (`body_sql`).

### 2.2 `ViewRequest` — the query (a decomposed sub-goal)  ·  `core.py`
```
want_name        : str
category         : str
required_outputs : list[str]     # columns this step needs
required_grain   : list[str]     # keys it must be groupable by
required_filters : dict[str,str] # intrinsic filters it needs
text             : str           # NL description → embedding query
```
Produced by `agents.propose_views`: an LLM decomposes the rewritten question into these
structured + NL sub-goals (one retrieval query each).

### 2.3 `ViewGraph` — the per-database memory  ·  `core.py`
Backed by **two** structures:
- `views: dict[str, ViewSpec]` — primary hash-map lookup (name → spec).
- `g: networkx.DiGraph` — a **heterogeneous, typed** graph:
  - node kinds: `skill::<CATEGORY>` (capability nodes) and `view::<name>` (instances);
  - edge types: **`INSTANTIATES`** (skill → view) and **`DEPENDS_ON`** (view → view).

```
skill::AGG ──INSTANTIATES──▶ view::country_population_metrics
skill::WIN ──INSTANTIATES──▶ view::country_score_trends ──DEPENDS_ON──▶ view::latest_scores
```

Key operations:
- `candidates(category)` → linear scan of `views` filtered by category (the retrieval bucket).
- `add_view` / `remove_view` → keep `views` and `g` in sync (remove used to roll back a view that
  fails validation).
- `topo_closure(names)` → transitive `DEPENDS_ON` closure in dependency order (see §6).
- `n_views`, `n_edges(etype)` → metrics.

Persistence: `sqlview.save_graph` / `load_graph` serialize every `ViewSpec` to JSON (`asdict`) and
rebuild the graph **in dependency order** so edges resolve. One frozen graph file per `db_id`.

### 2.4 Embedding cache  ·  `llm.Embedder`
`dict[str, np.ndarray(1536)]` memoizing `text → vector` (`text-embedding-3-small`), so each
distinct string is embedded once. There is **no ANN index** (no FAISS/HNSW); the candidate set is
tiny so brute-force cosine is optimal. (`chromadb` is in `requirements.txt` but unused by skiewsql
view retrieval.)

---

## 3. Retrieval algorithm  ·  `sqlview.retrieve`

```python
best, best_sim = None, -1.0
for cand in graph.candidates(req.category):              # [1] category bucket
    ok, _reason = compatible(cand, req, use_guard)       # [2] interface contract (hard gate)
    if not ok:
        continue
    sim = embedder.sim(req.text, cand.description or cand.name)  # [3] dense similarity
    if sim > best_sim:
        best, best_sim = cand, sim                       #     argmax over compatible candidates
if best is not None and best_sim >= tau:                 # [4] acceptance threshold
    return best, {"hit": True,  "sim": best_sim, "view": best.name}
return None, {"hit": False, "sim": max(best_sim, 0.0), "reason": ...}   # MISS → generate
```

Returns `(spec_or_None, diagnostics)`. The diagnostics (`hit`, `sim`, `reason`) are logged per
sub-goal and are how retrieval misses are debugged (e.g. `reason="required outputs not exposed"`).

### Stage 1 — Category bucketing (symbolic partition)
Only views of the request's **skill category** are candidates — an exact match on the 10-way
taxonomy. An `AGG` request never sees a `JOIN` view.

### Stage 2 — Compatibility contract (`compatible`, the *negative-reuse guard*)
A **hard boolean gate**: the view's interface must *satisfy* the request. It is effectively a
**behavioral-subtyping / capability check** with four clauses (all name-normalized, §4):

| clause | rule | why |
|---|---|---|
| category | `spec.category == req.category` | same operator class |
| **outputs superset** | `required_outputs ⊆ output_columns` | the view must expose ≥ the needed columns so the final SELECT can project them |
| **grain finer-or-equal** | `required_grain ⊆ grain` | view must be at same/finer granularity → can still `GROUP BY` up to required grain; a coarser view already aggregated a key away |
| **filters equal** (guard) | `semantic_filters == required_filters` | intrinsic filters must match exactly — blocks reusing an *all-rows* view for a *filtered-cohort* question |

The filter clause is the **negative-reuse guard**. Config **C** disables it (`use_guard=False`) to
measure the resulting bad reuse.

### Stage 3 — Dense semantic ranking
Among contract-passing candidates, rank by **cosine similarity of OpenAI embeddings** between the
request's NL `text` and each view's `description`:
```
sim(a,b) = (E(a)·E(b)) / (‖E(a)‖ ‖E(b)‖),   E = text-embedding-3-small  (1536-dim, cached)
```
This is a **description-to-description** dense match (not SQL-to-SQL). Selection is **argmax**
(first max wins on ties). Brute-force linear scan; no index.

### Stage 4 — Acceptance threshold τ
Accept the argmax only if `best_sim ≥ τ` (`sqlview` default `0.55`, CLI default `0.60`); otherwise
**miss** → generate a new CTE. A semantically perfect but contract-failing view is rejected in
Stage 2; a contract-passing but off-topic view is rejected here.

---

## 4. Name normalization  ·  `_norm_name`

Before the Stage-2 set operations, every column/grain name is canonicalized:
```
_norm_name(x) = lowercase(x), strip inline /* … */ and -- comments, keep [a-z0-9] only
```
So `CountryCode`, `country_code`, `country code` all unify. This absorbs the LLM's run-to-run
alias-format jitter and the raw-vs-canonical gap between the online proposer and the cold-start
seed generator. (It does **not** unify true synonyms like `name` ↔ `country_name` — those remain
genuine misses.)

---

## 5. Two retrieval flavors (sparse vs dense)

Same category + contract pre-filter; different similarity function:

| | mechanism study `core.retrieve` | real pipeline `sqlview.retrieve` |
|---|---|---|
| similarity | **TF-IDF cosine** (sklearn `TfidfVectorizer`) — sparse/lexical | **embedding cosine** — dense/semantic |
| τ | 0.25 | 0.55 / 0.60 |
| dependencies | none (deterministic, no network) | embedding API (cached) |

---

## 6. Graph algorithms around retrieval (composition & validation)

Once sub-goals resolve (reused or generated), chosen views become one query via **topological
sort** over the `DEPENDS_ON` DAG:

- `topo_closure(names)`: DFS/stack walk to gather the transitive dependency closure, then
  `networkx.topological_sort` on the **reversed** subgraph so dependencies precede dependents.
- `compose_sql`: emit `WITH [RECURSIVE] a AS (…), b AS (…), … SELECT …` in dependency order
  (`RECURSIVE` auto-added if any chosen view has category `REC`).
- `validate_view` (build/generate time): execute the candidate **with its dependency closure**
  against real SQLite (`… SELECT * FROM v LIMIT 5`) and confirm declared `output_columns` exist —
  an execution-grounded runtime check that the advertised interface is real. Failure → `remove_view`
  (roll back).

---

## 7. Complexity

Let `C` = candidates in the request's category, `G` = total views, `d` = 1536:
- **retrieve:** `O(C)` contract checks (small-set ops) + `O(C·d)` cached dot products + argmax. No
  index, no sort.
- **compose / validate:** `O(V+E)` topo sort over the chosen sub-DAG.
- **selective generation context** (`_relevant_views`, `--gen_topk`): `O(G·d)` sims + partial sort.

The design assumes a **small per-database graph** (tens–low-hundreds of views); brute-force beats
an ANN index at that scale.

---

## 8. Not to be confused with *value linking* (which does use LSH)

A separate subsystem, `valuelink.py`, matches **literals in generated SQL to real DB cell values**
— this is where classic ANN lives:
- **MinHash-LSH** (`datasketch`, `num_perm=64`, character **3-gram** shingles, LSH threshold 0.5)
  as a blocking index over distinct cell values;
- **edit similarity** (`difflib.SequenceMatcher`) to re-rank;
- optional **embedding** fallback for semantic matches.

View retrieval (this document) uses category + contract + dense cosine and **no** LSH; value
linking uses LSH + edit distance. Different problems, different machinery.

---

## 9. Limitations of the current retrieval

- **Category is a hard gate** — a useful cross-category view is never surfaced.
- **Single best only** — one view per sub-goal; no multi-view opportunistic composition at retrieval.
- **Strict AND contract** — one unmatched required output kills the match (normalization helps;
  true synonyms still miss).
- **Global fixed τ** — not learned, not per-category; trades reuse vs. false matches.
- **Description-quality dependent** — match quality hinges on the LLM writing good "when to use"
  descriptions for both the view and the sub-goal.
- **No ANN index** — fine for tens–hundreds of views per DB; would need FAISS/HNSW to scale to
  cross-database or very large libraries.

See `COLDSTART_RESULTS.md` for how retrieval behaves empirically (reuse rates, seed vs online) and
`README.md` for the SkiewSQL overview.
