# SkiewSQL — Graph Data Structure & View Retrieval

Reference for the memory that makes SkiewSQL work: the **self-growing view graph** and the **retrieval** that decides, per sub-goal, whether an existing view can be reused instead of generating a new CTE. Sections 1–9 describe the original retrieval in `core.py` and `sqlview.py` (retrieval flavor 2 = dense embeddings). The other benchmark runners and `realrun.py --skill_registry 0` still use it. The deterministic mechanism study (`core.retrieve`) is flavor 1 = TF-IDF.

**`realrun.py` now defaults to the skill registry (§10):** a versioned skill catalog with complete contracts, a five-stage retrieval that can abstain, graph search before N×M alignment, promotion-only persistence, AST-based credit assignment, ablation, episodes, and an evidence ledger.

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

Both gates must pass: the **contract** guarantees the view is *usable* (correctness), the **threshold** guarantees it is *about the right thing* (relevance). Retrieval runs once per sub-goal. A question has up to `max_views` sub-goals.

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
`cte_clause()` renders `name AS (\n body_sql \n)`. A `ViewSpec` is simultaneously a **node**, an **interface/type signature** (`category`, `output_columns`, `grain`, `semantic_filters`), and an **executable artifact** (`body_sql`).

### 2.2 `ViewRequest` — the query (a decomposed sub-goal)  ·  `core.py`
```
want_name        : str
category         : str
required_outputs : list[str]     # columns this step needs
required_grain   : list[str]     # keys it must be groupable by
required_filters : dict[str,str] # intrinsic filters it needs
text             : str           # NL description → embedding query
```
Produced by `agents.propose_views`: an LLM decomposes the rewritten question into these structured + NL sub-goals (one retrieval query each).

### 2.3 `ViewGraph` — the per-database memory  ·  `core.py`
Backed by **two** structures:
- `views: dict[str, ViewSpec]` — primary hash-map lookup (name → spec).
- `g: networkx.DiGraph` — a **heterogeneous, typed** graph:
  - node kinds: `skill::<CATEGORY>` (capability nodes) and `view::<name>` (instances).
  - edge types: **`INSTANTIATES`** (skill → view) and **`DEPENDS_ON`** (view → view). *(Historical: the current graph has no category nodes or `INSTANTIATES`. See §10.2.)*

```
skill::AGG ──INSTANTIATES──▶ view::country_population_metrics
skill::WIN ──INSTANTIATES──▶ view::country_score_trends ──DEPENDS_ON──▶ view::latest_scores
```

Key operations:
- `candidates(category)` → linear scan of `views` filtered by category (the retrieval bucket).
- `add_view` / `remove_view` → keep `views` and `g` in sync (remove used to roll back a view that fails validation).
- `topo_closure(names)` → transitive `DEPENDS_ON` closure in dependency order (see §6).
- `n_views`, `n_edges(etype)` → metrics.

Persistence: `sqlview.save_graph` / `load_graph` serialize every `ViewSpec` to JSON (`asdict`) and rebuild the graph **in dependency order** so edges resolve. One frozen graph file per `db_id`.

### 2.4 Embedding cache  ·  `llm.Embedder`
`dict[str, np.ndarray(1536)]` memoizing `text → vector` (`text-embedding-3-small`), so each distinct string is embedded once. There is **no ANN index** (no FAISS/HNSW). The candidate set is tiny so brute-force cosine is optimal. (`chromadb` is in `requirements.txt` but unused by skiewsql view retrieval.)

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

Returns `(spec_or_None, diagnostics)`. The diagnostics (`hit`, `sim`, `reason`) are logged per sub-goal and are how retrieval misses are debugged (e.g. `reason="required outputs not exposed"`).

### Stage 1 — Category bucketing (symbolic partition)
Only views of the request's **skill category** are candidates — an exact match on the 10-way taxonomy. An `AGG` request never sees a `JOIN` view.

### Stage 2 — Compatibility contract (`compatible`, the *negative-reuse guard*)
A **hard boolean gate**: the view's interface must *satisfy* the request. It is effectively a **behavioral-subtyping / capability check** with four clauses (all name-normalized, §4):

| clause | rule | why |
|---|---|---|
| category | `spec.category == req.category` | same operator class |
| **outputs superset** | `required_outputs ⊆ output_columns` | the view must expose ≥ the needed columns so the final SELECT can project them |
| **grain finer-or-equal** | `required_grain ⊆ grain` | view must be at same/finer granularity → can still `GROUP BY` up to required grain. A coarser view already aggregated a key away |
| **filters equal** (guard) | `semantic_filters == required_filters` | intrinsic filters must match exactly — blocks reusing an *all-rows* view for a *filtered-cohort* question |

The filter clause is the **negative-reuse guard**. Config **C** disables it (`use_guard=False`) to measure the resulting bad reuse.

### Stage 3 — Dense semantic ranking
Among contract-passing candidates, rank by **cosine similarity of OpenAI embeddings** between the request's NL `text` and each view's `description`:
```
sim(a,b) = (E(a)·E(b)) / (‖E(a)‖ ‖E(b)‖),   E = text-embedding-3-small  (1536-dim, cached)
```
This is a **description-to-description** dense match (not SQL-to-SQL). Selection is **argmax** (first max wins on ties). Brute-force linear scan. No index.

### Stage 4 — Acceptance threshold τ
Accept the argmax only if `best_sim ≥ τ` (`sqlview` default `0.55`, CLI default `0.60`). Otherwise **miss** → generate a new CTE. A semantically perfect but contract-failing view is rejected in Stage 2. A contract-passing but off-topic view is rejected here.

---

## 4. Name normalization  ·  `_norm_name`

Before the Stage-2 set operations, every column/grain name is canonicalized:
```
_norm_name(x) = lowercase(x), strip inline /* … */ and -- comments, keep [a-z0-9] only
```
So `CountryCode`, `country_code`, `country code` all unify. This absorbs the LLM's run-to-run alias-format jitter and the raw-vs-canonical gap between the online proposer and the cold-start seed generator. (It does **not** unify true synonyms like `name` ↔ `country_name` — those remain genuine misses.)

---

## 5. Two retrieval flavors (sparse vs dense)

Same category + contract pre-filter. Different similarity function:

| | mechanism study `core.retrieve` | real pipeline `sqlview.retrieve` |
|---|---|---|
| similarity | **TF-IDF cosine** (sklearn `TfidfVectorizer`) — sparse/lexical | **embedding cosine** — dense/semantic |
| τ | 0.25 | 0.55 / 0.60 |
| dependencies | none (deterministic, no network) | embedding API (cached) |

---

## 6. Graph algorithms around retrieval (composition & validation)

Once sub-goals resolve (reused or generated), chosen views become one query via **topological sort** over the `DEPENDS_ON` DAG:

- `topo_closure(names)`: DFS/stack walk to gather the transitive dependency closure, then a lexicographic topological sort over the `depends_on` lists (dependencies first, ties broken by view insertion order). The order is deterministic. The earlier subgraph sort depended on `PYTHONHASHSEED`, because networkx iterates small subgraphs through a set.
- `compose_sql`: emit `WITH [RECURSIVE] a AS (…), b AS (…), … SELECT …` in dependency order (`RECURSIVE` auto-added if any chosen view has category `REC`).
- `validate_view` (build/generate time): execute the candidate **with its dependency closure** against real SQLite (`… SELECT * FROM v LIMIT 5`) and confirm declared `output_columns` exist — an execution-grounded runtime check that the advertised interface is real. Failure → `remove_view` (roll back).

---

## 7. Complexity

Let `C` = candidates in the request's category, `G` = total views, `d` = 1536:
- **retrieve:** `O(C)` contract checks (small-set ops) + `O(C·d)` cached dot products + argmax. No index, no sort.
- **compose / validate:** `O(V+E)` topo sort over the chosen sub-DAG.
- **selective generation context** (`_relevant_views`, `--gen_topk`): `O(G·d)` sims + partial sort.

The design assumes a **small per-database graph** (tens–low-hundreds of views). Brute-force beats an ANN index at that scale.

---

## 8. Not to be confused with *value linking* (which does use LSH)

A separate subsystem, `valuelink.py`, matches **literals in generated SQL to real DB cell values** — this is where classic ANN lives:
- **MinHash-LSH** (`datasketch`, `num_perm=64`, character **3-gram** shingles, LSH threshold 0.5) as a blocking index over distinct cell values.
- **edit similarity** (`difflib.SequenceMatcher`) to re-rank.
- optional **embedding** fallback for semantic matches.

View retrieval (this document) uses category + contract + dense cosine and **no** LSH. Value linking uses LSH + edit distance. Different problems, different machinery.

---

## 9. Limitations of the current retrieval

- **Category is a hard gate** — a useful cross-category view is never surfaced.
- **Single best only** — one view per sub-goal. No multi-view opportunistic composition at retrieval.
- **Strict AND contract** — one unmatched required output kills the match (normalization helps. true synonyms still miss).
- **Global fixed τ** — not learned, not per-category. Trades reuse vs. false matches.
- **Description-quality dependent** — match quality hinges on the LLM writing good "when to use" descriptions for both the view and the sub-goal.
- **No ANN index** — fine for tens–hundreds of views per DB. Would need FAISS/HNSW to scale to cross-database or very large libraries.

See `COLDSTART_RESULTS.md` for how retrieval behaves empirically (reuse rates, seed vs online) and `README.md` for the SkiewSQL overview.

---

## 10. Skill registry (`contracts.py`, `registry.py`, `evidence.py`; default in `realrun.py`)

The dependency graph composes skills. It does not decide which stored relation is safe to reuse. The registry adds what that decision needs: a complete contract per skill, retrieval that can abstain, and evidence that only counts what the final SQL actually used.

### 10.1 What a skill stores (contract v2)

`ViewSpec` gains registry fields. Every default keeps older JSON graphs loadable.

| field | meaning |
|---|---|
| `skill_id`, `sql_hash` | Stable identity: hash of dialect + normalized SQL + dependency hashes. Used for dedup. |
| `grain_kind` | `scalar`, `keyed`, or `unknown`. An empty `grain` no longer means both "one row" and "unknown". |
| `dialect`, `status`, `version` | `status` is `active`, `exploratory` (this question only), `retired`, or `stale`. `version` increases when the SQL or the skill card is revised. |
| `aggregation` | Per output column: `sum`, `count`, `count_distinct`, `avg`, `min`, `max`, `window`, `key`, or `none`. |
| `join_keys` | Equi-join conditions parsed from `JOIN ... ON`. |
| `provenance` | Origin (`subgoal`, `av_chunk`, `final_extract`, `ported`, `legacy`), creating question id, question and rewrite, subgoal contract, route, model, prompt version (`agents.PROMPT_VERSION`), creation time, lineage, per-table schema fingerprints (columns, types, NOT NULL, primary keys, unique indexes, foreign keys), data fingerprints (row count and max rowid) when the grain was only observed on the data, inherited filters, contract version, and grain basis. |
| `validation` | Execution result, row count, grain check, filter checks, join cardinality, generated tests, and pass/fail. |
| `evidence` | Counters per credit level, positive and negative outcomes, ablation results, and the subgoals where the skill helped or hurt. |

Contracts are **derived, not trusted** (`contracts.derive`). Outputs are the columns the view returns when executed. The grain comes from `GROUP BY`, from a scalar aggregate, from `DISTINCT`, from a projected primary key, or from a candidate key verified unique on the data. An empty view proves no key, so its grain stays `unknown`. Filters come from the outermost `WHERE`: equality, numeric and ISO-date ranges, and `BETWEEN` (time windows). The contract is **effective**: a view also carries the filters of every dependency it reads, so a view built on an `active_users` cohort is never reused for all users. A grain observed on the data (`verified_unique`, `distinct`) is tied to a data fingerprint and must be revalidated when the rows change. Structural grains (`group_by`, `primary_key`, `scalar_aggregate`) are not.

A skill is **complete** only with known outputs, a known grain whose keys are exposed, passed validation, and contract v2. **Incomplete skills are never reused.**

### 10.2 Graph structure

`ViewGraph.g` is a `MultiDiGraph` keyed by edge type, so one pair of views can carry several relations (for example `DEPENDS_ON` and `SUBSUMES`). It keeps two kinds of edges and nothing else:

| Kind | Edge | Meaning | Source of truth |
|---|---|---|---|
| Operational | `DEPENDS_ON` | view → view it reads | **`ViewSpec.depends_on`**: the edge is derived, written only by `ViewGraph` (`add_view`, `set_depends_on`, `reindex`). `check_consistency()` reports any drift. |
| Operational | `READS_TABLE` | view → base table (`table::` node) | `ViewSpec.source_tables`, derived the same way |
| Semantic | `SUBSUMES` | broader skill → narrower skill (same tables and grain, stricter filters) | the graph (persisted as `relations`) |
| Semantic | `CONFLICTS_WITH` | same contract, different results (stored both ways) | the graph |
| Semantic | `SUPERSEDES` | newer skill → retired skill with the same contract | the graph |

`ViewSpec.depends_on` is authoritative because SQL composition (`topo_closure`, `compose_sql`) and persistence use it, and the other benchmark runners rely on it. To change a stored view's dependencies, call `ViewGraph.set_depends_on`. Structural indexes (`idx_category`, `idx_table` over lineage, `idx_output`, `idx_grain`, `idx_hash`) generate retrieval candidates: category ∩ every required output ∩ every required grain key, or lineage tables for holistic requests. There is no scan over the category bucket. `save_graph` persists the views and the semantic relations. Episodes and the evidence ledger are stored only as JSONL next to the grown graph: `{db}.episodes.jsonl` and `{db}.ledger.jsonl`. Earlier versions also stored `INSTANTIATES` (category → view), `SPECIALIZES` (the inverse of `SUBSUMES`), `EQUIVALENT_TO`, and episode/subgoal nodes. No decision read them, so they were removed. Old graph files that contain them still load, and the removed types are ignored.

**Equivalence is canonicalization, not an edge.** A new view that duplicates an existing skill (same SQL hash), or is equivalent to it (same contract and same result), is merged into the existing skill: dependents are rewritten to read it, and the alias is recorded in `provenance.aliases`. Only one representative of an equivalence class is ever stored.

### 10.3 Five-stage retrieval (`registry.retrieve`)

```
request
  │ 0 names      map the request's logical output/grain names onto the stored vocabulary of its category
  │              (shared word tokens ≥ 0.5, or embedding ≥ 0.6 for outputs / ≥ 0.8 for grain keys)
  │   indexes    candidates = category ∩ required outputs ∩ required grain keys (holistic: lineage tables)
  │ 1 scope      active + complete contract, same DB and dialect, unchanged table fingerprints (and data
  │              fingerprints for observed grains),
  │              eligible dependencies, lineage ⊆ request tables, not already used in this question
  │ 2 contract   category, outputs ⊆, grain equal or finer, effective filters and time windows compatible
  │              (the request's own filters plus those inherited from its dependency subgoals),
  │              aggregation semantics, no many-to-many join under a measure
  │ 3 ranking    description similarity + column/table overlap + metric overlap + prior good subgoals
  │              − known misuses (veto at 0.6). Accept only sim ≥ τ
  │ 4 reuse mode exact | specialization (filter downstream) | rollup (SUM/COUNT/MIN/MAX re-aggregation
  │              or DISTINCT) | composition (1:1 join of two skills at the requested grain, checked lossless)
  │ 5 verify     LLM selector may answer NONE. A vote counts only at confidence ≥ 0.6, JOIN/AGG/WIN/SET/REC
  │              candidates get ≥ 3 votes, and reuse needs a strict majority (deterministic mode abstains on
  │              conflicting near-ties)
  ▼
exact skill, a validated thin derived CTE over it, or MISS → generate
```

**Name mapping (Stage 0)** exists because the schema-free decomposer names outputs logically (`net_balance`, `num_students`) while stored skills expose real aliases (`balance`, `student_count`). Without it, almost every lookup returned no index candidate. The mapping only proposes candidates: Stage 2 still checks the contract on the mapped names, a match that relied on a mapping always goes to the LLM verifier with the renames listed, and deterministic mode abstains on it. Grain keys use a stricter threshold because a wrong grain (for example `month` → `year`) silently corrupts results.

Holistic AV-SQL (moderate) requests have no category, outputs or grain. Scope, filters, ranking and the verifier constrain them, and a stored view can serve at most one chunk per question.

### 10.4 Pipeline changes in `realrun.py`

- **Hard route:** decompose into M contracts and search the registry for each (`prefetch`). Each hit is then **grounded**: the subgoal is aligned only against the chunks that contain the skill's lineage tables, and the hit is kept only if alignment selects all of them. An ungrounded hit is released and searched again after full alignment, restricted to the aligned tables. Alignment costs about N×(M−H) + H calls instead of N×M. Every search after alignment is restricted to the request's aligned tables.
- **Generation:** a generated view whose declared grain or filters are violated on the data gets that feedback and is regenerated. Every new view is `exploratory` until admission.
- **Why each view is here (per question):** every chosen view carries a reason in a per-question memory. A reused view gets the verifier's reason, the reuse mode and any renamed columns. A generated view gets its subgoal and why no stored skill fit. The planner and composer see these reasons next to each view. They are never written onto the skill.
- **AV-SQL view validation (paper §4.3):** in the registry pipeline, each N×1 chunk view is generated together with a JSON schema selection `{table: [columns] | "drop_all"}` (`agents.av_view_selected`). Each attempt runs three checks: value retrieval on the CTE's literals (τ_edit = τ_semantic = 0.5), execution on the database, and rule-based CTE/JSON consistency (`contracts.selection_consistency`): an empty selection means no CTE, a CTE needs a non-empty selection, and every table and column the CTE uses must be selected. All problems and the matched database values are fed back to the next attempt. The loop stops when the view executes and is consistent, or after `--view_attempts` (T_max) attempts, and only valid views are kept. There is no extra review step before aggregation.
- **Admission after the question** (`registry.admit`): a new view persists only if the executed final SQL used it unmodified and it passes full derivation, validation and generated tests (`--gen_tests`), and completeness. A hash duplicate or an equivalent (same contract and same result) is merged into the existing skill. AV chunk views also get a question-independent name, description, and known limitations, plus a category inferred from their SQL.
- **Final SQL** is stored as an episode. `--promote_final` may extract one reusable relation from it. The extraction is rejected if any literal in it appears in the question, its evidence, or its rewrite (case-insensitive: casing cannot separate `'france'` from an intrinsic `'completed'`, so the policy is conservative). It is also rejected if it is a trivial projection or reads a non-skill view.
- **Credit** (`evidence.assign_credit`): the final SQL is parsed, and only CTEs in the dependency closure of the outer query, with bodies identical to the stored skill, count as executed. Dead CTEs and CTEs rewritten by a repair get no credit.
- **Ablation** (`--ablation`): each executed reused skill's CTE body is replaced by a freshly generated view for the same subgoal, with the rest of the SQL unchanged. The result is `causal_win`, `causal_loss`, or `neutral` (label-free: `neutral` or `divergent`). Ablation decides the skill outcome when it is conclusive.
- **Retirement:** a net-negative skill (≥2 harmful and more harmful than good) is retired. A newer skill with the same contract `SUPERSEDES` it, and its dependents become ineligible.
- **Schema versioning:** loaded graphs (seed or earlier runs) go through `registry.refresh`. Legacy or changed skills are re-derived and become `stale` if they no longer pass. Legacy AV `chunk_view_*` views are stale outright.
- **Portability** (`--port_from DIR`): skills from other databases' graphs are copied when every table they read has an identical interface (same fingerprint), transpiled across dialects, then re-validated and admitted.

`--skill_registry 0` restores the legacy pipeline. In registry mode, `--verify N` sets the Stage-5 selector votes (at least 1), and `--retriever` is unused. The new summary metrics are `alignment_calls_total`, `prefetch_hits`, `reuse_executed_count`, `negative_reuse_referenced_count`, `causal_{positive,negative}_reuse_count`, `skills_admitted`, `skills_retired`, `reuse_modes`, and `tokens_learning` (tokens spent after answering, already included in the totals).

### 10.5 Known limits

- A grain verified on the data can be coincidental: it holds for the current rows, not for all future ones. It is invalidated when row counts change, but an in-place `UPDATE` does not change the data fingerprint. Structural bases (`group_by`, `primary_key`) are stronger. `provenance.grain_basis` records which one applied.
- Generated tests that fail to execute count as inconclusive, not as failures.
- Ablation needs the regenerated view to keep the reused view's interface. When it does not, the result is `inconclusive` and credit falls back to association.
- τ and the ranking weights are fixed, not calibrated.
