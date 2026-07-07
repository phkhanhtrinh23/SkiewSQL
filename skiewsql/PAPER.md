# SkiewSQL: A Self-Growing Memory of Reusable, Execution-Validated SQL Views for Text-to-SQL over Massive Schemas

> Working title / method name **SkiewSQL** (*Skill-driven, Execution-validated Views for SQL*) is a
> placeholder you can rename. This document is a full technical write-up intended as the backbone of
> a paper: every component, every data structure, and every design decision is described step by
> step, with a single running example carried from the first stage to the last, and with all
> mathematical notation defined before it is used.

---

## Abstract

Answering a natural-language question over a **real enterprise database** — hundreds to thousands of
tables, deeply nested and date-sharded columns, and analytic questions that require multi-step
Common Table Expressions (CTEs), window functions, and careful cohort definitions — breaks the
dominant "retrieve-the-relevant-schema-then-generate-one-query" recipe in three ways at once. (i)
The retrieval step **silently drops** tables the query needs (a recall failure that no amount of
downstream cleverness can repair). (ii) One-shot generation of long analytic SQL is brittle and
hard to debug. (iii) Every question re-derives the **same** intermediate relations from scratch,
wasting computation and producing inconsistent, un-auditable SQL.

We introduce **SkiewSQL**, a framework that treats the recurring intermediate relations of a
database as **reusable, executable, schema-grounded skills** and organizes them in a **self-growing
view graph**. For each question, SkiewSQL **retrieves and composes** the skills it already has and
**generates only what is missing**; each newly generated skill is **validated by execution** before
it is trusted and stored. Crucially, the library is **cold-started from the schema alone** — before
any question is seen — so reuse is available from the very first query. To make reuse *safe* at
scale, retrieval is not mere similarity search but **typed capability matching** backed by a
navigable-small-world index, and reuse is protected by a **four-layer defense** against the one
failure mode a memory introduces: reusing a view that looks right but is subtly wrong. SkiewSQL is
**dialect-agnostic** (it runs natively on SQLite and BigQuery, using free dry-run validation on the
cloud) and **budget-aware**. We formalize the method, walk a real analytic question through the
entire pipeline, analyze complexity and cost, and report experiments showing that the memory
delivers **the same answers more cheaply** and that its payoff is governed by a clean, previously
unarticulated law: **reuse is proportional to question-stream homogeneity.**

---

## 1. Introduction

### 1.1 The setting that breaks current Text-to-SQL

Modern data lives in **massive schemas**. A single analytics warehouse routinely exposes thousands
of columns across hundreds of tables, with nested record types and tables **sharded by date**
(`events_20210103, events_20210104, …`). The questions asked of such warehouses are not toy
`SELECT … WHERE …` lookups; they are **analytic**: *"the 5-day moving average of predicted sales,"*
*"the RFM (recency–frequency–monetary) segment of each customer,"* *"the latest recorded score per
entity per year."* Correct SQL for these questions is long, multi-CTE, and window-function heavy.

Two facts about this setting are decisive, and together they defeat the standard pipeline.

**Fact 1 — the schema does not fit, so it must be reduced; but reduction loses recall.** Because the
full schema exceeds the model's context window, the field's default is to **retrieve** a relevant
subset of tables/columns (e.g., by embedding similarity, keyword match, or an LLM selector) and
generate over that subset. Retrieval, however, **can and does omit necessary tables** — a bridge
table needed for a join, a lookup no keyword matched, a column whose name does not resemble the
question. A single omitted table makes the correct query **unexpressible**, and no downstream repair
can recover it. This is a **recall** failure, and it is silent.

**Fact 2 — the same relations recur, yet are re-derived every time.** Across the many questions a
warehouse serves, a small set of intermediate relations reappears constantly: *"latest version of a
repeatedly-updated record," "orders joined to customers and status," "revenue rolled up per region
per month."* The standard pipeline recomputes and re-verifies these **from scratch for every
question**, which is wasteful, inconsistent (two questions define "active customer" differently),
and un-auditable.

### 1.2 Our idea in one sentence

> Treat the recurring intermediate relations of a database as **reusable, execution-validated CTE
> skills**, keep them in a **self-growing graph memory**, **pre-build** that memory from the schema
> before any question arrives, and for each new question **retrieve-and-compose** the skills you
> have while **generating — and validating — only what is missing.**

This reframes Text-to-SQL from *"link the schema, then generate a query"* to *"maintain a validated
library of building blocks, then assemble."* It attacks both facts of §1.1 simultaneously: recall is
protected by processing the schema **exhaustively** (no lossy up-front retrieval of tables — §6.2)
and by **falling back to generation** whenever a needed skill is absent; and redundant re-derivation
is eliminated by **reuse**.

### 1.3 Why this is hard — and what makes it novel

A memory of views is only useful if reuse is **safe**. The moment you allow reuse, you introduce a
new, dangerous failure mode: **the bad hit** — reusing a stored view that *looks* relevant but is
semantically wrong for the current question (e.g., reusing an *all-rows* revenue view for a
*completed-orders-only* question). A bad hit produces confidently wrong SQL. Making reuse both
**high-recall** (find the view when it exists) and **high-precision** (never reuse the wrong one) at
massive scale is the central technical problem, and it is where our contributions concentrate.

### 1.4 Contributions

1. **A self-growing, execution-validated view memory** (§4): a heterogeneous **graph** whose nodes
   are *skills* (operator categories) and *views* (concrete, executable CTEs), with typed edges for
   *instantiation* and *dependency*. Every view is trusted only after it **runs** against the real
   database.
2. **Cold-start seeding** (§5): the library is constructed **from the schema alone, with provable
   leakage-safety** (no test question or gold query is ever observed), so reuse is available from the
   **first** question — there is no warm-up penalty. To our knowledge this "generate-a-reusable-view-
   library-before-you-see-a-question" formulation is new.
3. **Typed capability retrieval at scale** (§7): reuse is decided by a **compatibility contract** —
   a behavioral-subtyping check over a view's *interface* (category, exposed outputs, grain,
   intrinsic filters) — composed with **dense+sparse hybrid** similarity and a **navigable-small-world
   (HNSW) filtered index**. This is retrieval as *constraint satisfaction over interfaces*, not mere
   nearest-neighbor search.
4. **A four-layer defense against the bad hit** (§8): (L1) the symbolic contract, (L2) execution-
   grounded validation, (L3) an **adversarial verifier** — independent skeptical judges that must
   fail to refute a reuse for it to proceed — and (L4) a **provenance memory** in which each skill
   *learns its own boundary* from observed correct and incorrect reuses.
5. **Recall-safe schema handling and a graceful miss** (§6.2, §8.1): the schema is processed
   **exhaustively by chunk** so no table is silently dropped, and a retrieval *miss* degrades to
   *generation* — costing at worst a redundant re-derivation, **never a wrong answer**. We prove the
   system is *at least as correct as pure generation*.
6. **Token-efficiency by design** (§7.4): a **selective-injection** rule bounds the size of every
   generation prompt independent of how large the library grows, turning memory from a token *cost*
   into a token *saving* on homogeneous streams.
7. **Dialect-agnostic, budget-aware execution** (§10): the same method runs on SQLite and **natively
   on BigQuery**, where **free dry-run validation** lets us validate every candidate view at **zero
   scan cost**, keeping full runs inside the cloud free tier.
8. **An empirical law** (§12): the payoff of the memory is governed by **reuse ∝ question-stream
   homogeneity** — large where a database serves many related questions, near-zero for one-off
   heterogeneous questions — a clean characterization of *when* view memory helps that, we argue, is
   a contribution in its own right.

---

## 2. Problem Formulation

We define all notation here; later sections use only symbols introduced below.

**Database.** A database is a triple
$$ D=(\mathcal{T},\ \mathcal{C},\ \mathcal{R}), $$
where $\mathcal{T}=\{T_1,\dots,T_m\}$ is a set of $m$ **tables**; $\mathcal{C}=\{C_1,\dots,C_m\}$
gives, for each table $T_i$, its ordered set of **columns** $C_i=\{c_i^1,\dots,c_i^{n_i}\}$ (so $T_i$
has $n_i$ columns); and $\mathcal{R}$ is the set of **foreign-key relations** (directed links
$c_i^a \to c_j^b$ meaning column $c_i^a$ references column $c_j^b$). A *massive schema* is one where
$m$ (tables) and/or $\sum_i n_i$ (total columns) is large enough that a full textual rendering of $D$
exceeds the language model's context window.

**Schema.** $S$ denotes the **textual schema** of $D$: a rendering of every table's `CREATE TABLE`
(column names, types, keys) plus foreign keys and a few sample values. $S$ is what a language model
"sees"; it never sees the full data.

**Question and knowledge.** $Q$ is a natural-language **question**; $K$ is optional **external
knowledge** (documentation, business definitions) supplied with $Q$. Either may be empty.

**Query and its result.** A SQL query is written $Y$. Executing $Y$ against the concrete data of $D$
yields a **result table** written $\llbracket Y \rrbracket_D$. Text-to-SQL asks for a query $Y^\star$
whose result matches that of the (hidden) gold query $Y^{\mathrm{gold}}$:
$$ \llbracket Y^\star \rrbracket_D \ \equiv\ \llbracket Y^{\mathrm{gold}} \rrbracket_D, $$
where $\equiv$ is **result-set equivalence** (multiset equality up to column order, with a numeric
tolerance and, when the gold query is unordered, up to row order). The metric that counts a
prediction correct under $\equiv$ is **Execution Accuracy (EX)**.

**The learned function.** A Text-to-SQL system is a function
$$ Y=f(Q,\ S,\ K \mid \theta), $$
with parameters/prompt configuration $\theta$. This paper's contribution is a particular, memory-
augmented $f$.

---

## 3. Overview and a Running Example

### 3.1 The running example (used throughout)

We fix one concrete database $D^\ast$ and one concrete question $Q^\ast$ and carry them through
**every** stage below.

**Database $D^\ast$ — university rankings** ($m=5$ tables):

```
countries(country_id PK, country_name, region)
universities(university_id PK, university_name, country_id → countries,
             parent_university_id → universities, founded_year, status)   -- status ∈ {active,closed,merged}
criteria(criteria_id PK, criteria_name, maximum_score, weight)            -- criteria_name ∈ {Teaching,Research,Citations}
university_scores(score_id PK, university_id → universities, criteria_id → criteria,
                  score_year, score, recorded_at)                          -- MULTIPLE recorded versions per (uni,criterion,year);
                                                                           --   the row with latest recorded_at is the current one
university_rankings(ranking_id PK, university_id → universities, ranking_year, overall_rank, published_at)
```

**Question $Q^\ast$:** *"What percentage of **active** universities with a **Teaching** score above
**90** in **2011** are located in the **United States**?"*

The correct answer requires: (i) join universities → countries → criteria → scores; (ii) keep the
**latest recorded version** of each score (a repeatedly-updated record); (iii) restrict to
`status='active'`, `criteria_name='Teaching'`, `score_year=2011`, `score>90`; (iv) compute the
fraction whose `country_name` is the United States. Points (i) and (ii) are **reusable across many
questions**; points (iii)–(iv) are **question-specific**. That separation is the crux of the method.

### 3.2 Pipeline at a glance

```
                         ┌──────────────────  VIEW-MEMORY GRAPH  𝒢  ──────────────────┐
                         │  skill nodes (SEL/AGG/JOIN/RANK/…)  +  validated view nodes │
   COLD-START (once,     │  edges: INSTANTIATES (skill→view), DEPENDS_ON (view→view)   │
   from schema only) ───▶│  built by Prompts A→B→C→D, execution-validated, FROZEN      │
                         └───────────────────────────▲───────────────────────────────┘
                                                      │ retrieve / grow
 Q,S,K ─▶ (1) Rewrite ─▶ (2) Exhaustive chunk + per-chunk view proposal (recall-safe schema linking)
        ─▶ (3) for each sub-goal ρ:  retrieve(𝒢,ρ) ──hit──▶ [L1 contract][L3 verifier][L4 provenance] ─▶ reuse
                                          │                                                     │ reject
                                          └──miss────────────────────────────────────▶ generate + [L2 validate] ─▶ store
        ─▶ (4) compose (topological over DEPENDS_ON)  ─▶ (5) execute-repair (+ value linking)
        ─▶ (6) semantic revise  ─▶  Y*
```

Every arrow is defined below.

---

## 4. The Reusable-View Memory

### 4.1 A view is a typed, executable skill

The atomic unit of the memory is a **view** — a named CTE together with the *interface contract* that
makes it safely reusable. Formally a view is
$$ v=\big\langle\, n,\ \kappa,\ \beta,\ O,\ G,\ \Phi,\ \delta,\ d\,\big\rangle, $$
with the components:

| symbol | meaning |
|---|---|
| $n$ | unique **name** within the database's memory |
| $\kappa\in\mathcal{K}$ | **skill category** (the operator class the view performs) |
| $\beta$ | the **body**: the SQL `SELECT` that defines the CTE (no `WITH` wrapper) |
| $O$ | the **output columns** the view exposes (its *provided interface*) |
| $G$ | the **grain**: the key column(s) — "one row per $G$"; $G=\varnothing$ ⇒ a scalar/single-row view |
| $\Phi$ | the **intrinsic filters**: predicates baked into the view (e.g., $\Phi=\{\texttt{status}\!=\!\texttt{active}\}$) |
| $\delta$ | **dependencies**: names of other views this view builds on |
| $d$ | a natural-language **description** ("when to use"), the source text for retrieval embeddings |

The **skill categories** are a fixed ten-way taxonomy of relational operations:
$$ \mathcal{K}=\{\text{SEL, NORM, AGG, JOIN, RANK, WIN, RESHAPE, SET, REC, SEM}\}, $$
namely selection/cohort, normalization/cleaning, aggregation, join-enrichment, ranking/dedup,
ordered analytic window, pivot/unpivot reshaping, set algebra, recursive traversal, and semantic
(documented business rule). The category is the coarse "type" of a skill.

In the running example, three reusable views (among others) will appear:

- $v_{\text{join}}$ — a **JOIN** skill "`university_criterion_scores`": one row per recorded score,
  exposing $O=\{$`university_id, university_name, country_name, region, criteria_name, score,
  score_year, status`$\}$, grain $G=\{$`score_id`$\}$, filters $\Phi=\varnothing$.
- $v_{\text{latest}}$ — a **RANK** skill "`latest_university_scores`": the current version of each
  score, $O=\{$`university_id, criteria_id, score_year, score`$\}$, $G=\{$`university_id, criteria_id,
  score_year`$\}$, with intrinsic filter $\Phi=\{$`version`$=$`latest`$\}$.
- $v_{\text{wperf}}$ — a **SEM** skill "`university_weighted_performance`" that **depends on**
  $v_{\text{latest}}$ ($\delta=\{v_{\text{latest}}\}$), implementing the documented weighted-score
  formula.

### 4.2 The graph $\mathcal{G}$

The memory is a **heterogeneous directed graph**
$$ \mathcal{G}=(\ \mathcal{V}\cup\mathcal{SK},\ \ \mathcal{E}\ ), $$
with two kinds of nodes and two kinds of edges:

- **view nodes** $\mathcal{V}$ — one per stored view $v$;
- **skill nodes** $\mathcal{SK}$ — one per category $\kappa\in\mathcal{K}$ actually present;
- edges $\mathcal{E}=\mathcal{E}_{\text{inst}}\ \cup\ \mathcal{E}_{\text{dep}}$, where
  $\mathcal{E}_{\text{inst}}$ contains an **INSTANTIATES** edge $\kappa\!\to\!v$ for every view $v$ of
  category $\kappa$, and $\mathcal{E}_{\text{dep}}$ contains a **DEPENDS_ON** edge $v\!\to\!v'$ for
  every $v'\in\delta_v$.

A hash map $n\mapsto v$ backs $\mathcal{V}$ for $O(1)$ lookup by name. The graph is what lets us (i)
**retrieve within a category** in one step (follow INSTANTIATES from the skill node), (ii)
**materialize a view together with its transitive dependencies in the correct order** (topological
sort over $\mathcal{E}_{\text{dep}}$, §6.5), and (iii) later **reason structurally** about the library
(dependency-aware refactoring/eviction — §13). Example fragment:

```
skill::RANK ──INSTANTIATES──▶ view::latest_university_scores
skill::SEM  ──INSTANTIATES──▶ view::university_weighted_performance
view::university_weighted_performance ──DEPENDS_ON──▶ view::latest_university_scores
```

### 4.3 The query against the memory: a sub-goal

A question is decomposed (in §6.3) into **sub-goals**. A sub-goal is a *request for an intermediate
relation* — i.e., a view-shaped query against $\mathcal{G}$:
$$ \rho=\big\langle\ \kappa_\rho,\ O_\rho,\ G_\rho,\ \Phi_\rho,\ t_\rho\ \big\rangle, $$
where $\kappa_\rho$ is the required category, $O_\rho$ the required output columns, $G_\rho$ the
required grain, $\Phi_\rho$ the required intrinsic filters, and $t_\rho$ a natural-language
description used for semantic matching. Retrieval (§7) answers: *is there a stored $v$ that satisfies
$\rho$?*

---

## 5. Cold-Start Seeding: Building the Library Before Any Question

The distinctive move is to construct $\mathcal{G}$ **from the schema $S$ alone**, offline, *before*
any question is observed. This removes the warm-up period during which a purely online memory has
nothing to reuse.

### 5.1 Leakage-safety (a structural guarantee)

Seeding is a function of $(S, K_{\text{schema}})$ only — DDL, foreign keys, sample rows, and light
profile statistics (row counts, low-cardinality enum values). It **never** receives $Q$,
$Y^{\mathrm{gold}}$, expected answers, or the test-question distribution. Because the interface is
structurally restricted to schema inputs, no test-time information can leak into the seed — a
property we can state as an invariant rather than merely assert.

### 5.2 The four seeding stages (A→B→C→D)

**Prompt A — schema analysis.** From $S$ (+ profile), an analyst pass produces, for each table, its
*role* (entity/fact/dimension/bridge/hierarchy/archive), *grain*, keys, temporal/versioning columns,
stable-state columns, and *safe join paths* flagged with row-multiplication risk; and a list of
*supported categories* with evidence. This is structured JSON, not SQL.

**Prompt B — candidate generation.** Grounded in the **authoritative schema** (and the analysis),
generate reusable CTE bodies across $\mathcal{K}$, one responsibility each. Two rules are essential
for later reuse: (i) **lift question-specific literals out** (no `year=2011`, no `country='US'`,
no `LIMIT 10`) so a view is a *general* relation; only *intrinsic* filters (`status='active'`,
"latest version") belong in $\Phi$. (ii) **alias pass-through columns to their exact schema names**
so that a downstream sub-goal asking for `Name`/`Population`/`CountryCode` matches the view's $O$;
otherwise retrieval's output-subset check (§7.2) fails and the seed is never used.

**Prompt C — execution-grounded validation (this is L2).** Each candidate is *run* against the real
database with its dependency closure, `… SELECT * FROM v LIMIT k`, and accepted only if it executes
and its declared outputs $O$ actually appear in the result schema. Failures are repaired up to a
bound and otherwise discarded; near-duplicates (same category, outputs, grain) are pruned.

**Prompt D — registration.** Survivors are inserted into $\mathcal{G}$ with INSTANTIATES edges and
DEPENDS_ON edges extracted from $\delta$. The graph is then **frozen** as the cold-start library;
any views generated later, at question time, are tracked separately as **online growth**.

For $D^\ast$, seeding yields (among others) $v_{\text{join}}$, $v_{\text{latest}}$, and
$v_{\text{wperf}}$ from §4.1 — the canonical building blocks of university-ranking questions — each
already execution-validated.

---

## 6. The Per-Question Pipeline

We now process $Q^\ast$ end to end. The graph $\mathcal{G}$ persists across the questions of a
database (it is the memory); for a purely-online ablation it starts empty and grows.

### 6.1 Stage 1 — Question rewriting

An LLM rewrites $(Q,K)$ into an explicit specification $\tilde{Q}$: a one-sentence task, the required
output values, the **resolved** filters (with literal values), and any sort/limit. This folds in
external knowledge and resolves under-specified references, and it *separates* the intrinsic concept
from the question-specific operations.

*Example.* $\tilde{Q}^\ast$: **task** = "fraction of active universities with Teaching score > 90 in
2011 that are in the United States"; **outputs** = {a single percentage}; **filters** =
{`status=active`, `criteria_name=Teaching`, `score_year=2011`, `score>90`}; the "latest recorded
version" requirement is made explicit.

### 6.2 Stage 2a — Recall-safe schema handling (why we do *not* retrieve tables)

For a massive schema, $S$ cannot be shown whole. Rather than **retrieve** a subset of tables (which
can silently omit a needed one — Fact 1), we **partition and process exhaustively**. Let $B$ be a
token budget. First, **compress** near-duplicate tables: tables whose names share a stem after
stripping date/number suffixes (`events_<YYYYMMDD>`, `ga_sessions_<N>`) are clustered and one
representative is rendered with a note listing the collapsed siblings. Then **length-based
partition** the (compressed) schema into chunks
$$ \Pi(S)=\{S^1,\dots,S^k\},\qquad \forall j:\ \operatorname{len}(S^j)<B, $$
where each chunk $S^j$ holds **complete** table definitions. Every chunk is processed; no table is
dropped by a lossy scorer. This trades more model calls for **guaranteed schema recall** — the
opposite of retrieval-based schema linking, and the reason large heterogeneous schemas do not cause
silent misses here.

### 6.3 Stage 2b — Per-chunk view proposal (schema linking as sub-goal proposal)

For each chunk $S^j$ and the rewritten question $\tilde Q$, a proposer LLM emits (a) a set of
**reusable sub-goals** $\{\rho\}$ (each a view-request of §4.3, with a *general* name and its
$\kappa,O,G,\Phi,t$), and (b) a **schema selection** $J^j=(\text{tables},\text{columns})$ — the
relevant schema elements from this chunk. The union $\bigcup_j J^j$ forms the **filtered schema**
$S_{\text{filt}}$ used downstream. Because proposal runs on *every* chunk, the sub-goals collectively
cover all relevant tables (recall), while $S_{\text{filt}}$ keeps the downstream prompts small
(precision). This *is* our schema-linking step — but expressed as *validated view construction*
rather than lossy up-front pruning.

*Example.* Proposal yields three sub-goals for $Q^\ast$:
$\rho_1$ (JOIN: university+country+criteria+score attributes, grain per score),
$\rho_2$ (RANK: latest score per university/criterion/year, $\Phi_{\rho_2}=\{$latest$\}$), and
$\rho_3$ (SEL: active universities). Question-specific pieces (year=2011, Teaching, >90, US, the
percentage) are deliberately **not** in any $\rho$; they are applied in Stage 3.

### 6.4 Stage 2c — Retrieve-or-generate (the heart of the method)

For each sub-goal $\rho$: attempt **retrieval** from $\mathcal{G}$ (§7). If a compatible, verified
view is found → **reuse** it. Otherwise → **generate** a new view for $\rho$, **validate it by
execution** (L2), and **store** it in $\mathcal{G}$. Formally, letting $\mathrm{ret}(\mathcal{G},\rho)$
be the retrieval result (a view or $\bot$),
$$
v_\rho=\begin{cases}
\mathrm{ret}(\mathcal{G},\rho) & \text{if } \mathrm{ret}(\mathcal{G},\rho)\neq\bot \text{ and passes the guards (§8)}\\
\mathrm{gen\text{-}and\text{-}validate}(\rho, S_{\text{filt}}, \mathcal{G}) & \text{otherwise.}
\end{cases}
$$

*Example, cold start (empty $\mathcal{G}$):* all three sub-goals miss → each is generated and
execution-validated, populating $\mathcal{G}$ with $v_{\text{join}},v_{\text{latest}},v_{\text{active}}$.
*Example, with the seed:* $\rho_1$ retrieves $v_{\text{join}}$ and $\rho_2$ retrieves $v_{\text{latest}}$
**with no generation** — the seed pays off on the first question.

### 6.5 Stage 3 — Composition (topological over dependencies)

The chosen views $\{v_\rho\}$ are assembled into a single query. Because a view may depend on others
($\mathcal{E}_{\text{dep}}$), we take the **transitive dependency closure** and order it by a
**topological sort** of the DEPENDS_ON sub-graph so that each CTE is defined before it is used:
$$ \textsf{compose}(\{v_\rho\})=\ \texttt{WITH}\ \big[\texttt{RECURSIVE}\big]\ v_{(1)}\ \texttt{AS}\ (\beta_{(1)}),\ \dots,\ v_{(p)}\ \texttt{AS}\ (\beta_{(p)})\ \ \tau_{\text{final}}, $$
where $v_{(1)},\dots,v_{(p)}$ is a topological order of the closure (dependencies first),
`RECURSIVE` is emitted iff any chosen view has category `REC`, and $\tau_{\text{final}}$ is the
**final SELECT** produced by a generator conditioned on $S_{\text{filt}}$, $\tilde Q$, and the
chosen views. $\tau_{\text{final}}$ is where the **question-specific** operations live.

*Example.* $\tau_{\text{final}}$ joins $v_{\text{latest}}$ into $v_{\text{join}}$, applies
`criteria_name='Teaching' AND score_year=2011 AND score>90 AND status='active'`, and computes
`100.0 * SUM(country_name = 'United States') / COUNT(*)`. Note the reusable views carry the joins and
the latest-version logic; only the filters and the percentage are new.

### 6.6 Stage 4 — Execution-grounded repair (with value linking)

The composed query is executed. On error, an execution-feedback **repair** loop (bounded by
$T_{\max}$ attempts) revises it using the error message and **value-linking hints** (§9). This is the
mechanism that catches the single largest error class — filter values that do not exist verbatim in
the data.

*Example.* If the model wrote `country_name = 'United States'` but the database stores
`'United States of America'`, value linking returns the correct literal and the revisor substitutes
it; the query now executes.

### 6.7 Stage 5 — Semantic revision

A final skeptical pass checks that the executing query *actually* answers $\tilde Q$ (right columns,
filters, aggregation, ordering/limit), given a preview of its result; it returns the query unchanged
if correct, else a correction adopted only if it still executes. The output is $Y^\star$, scored by
EX (§2).

---

## 7. Retrieval at Scale: Typed Capability Matching + HNSW

Retrieval decides, per sub-goal $\rho$, whether a stored view can be reused. It is a **filter → rank
→ threshold** pipeline, not plain similarity search.

### 7.1 Stage R1 — Category bucketing

Only views of the request's category are candidates: follow the INSTANTIATES edges from skill node
$\kappa_\rho$, giving the bucket $\mathcal{B}_\rho=\{v\in\mathcal{V}:\kappa_v=\kappa_\rho\}$. An `AGG`
request never sees a `JOIN` view.

### 7.2 Stage R2 — The compatibility contract (the *type check*)

Among $\mathcal{B}_\rho$, keep only views whose **interface satisfies** $\rho$. Define a name
normalizer $\nu(\cdot)$ that lower-cases a column identifier and strips non-alphanumerics (so
`CountryCode`, `country_code`, `country code` unify) and drops inline comments. The **compatibility
predicate** is
$$
\mathrm{compat}(v,\rho)\ =\
\underbrace{[\kappa_v=\kappa_\rho]}_{\text{category}}\ \wedge\
\underbrace{\big[\nu(O_\rho)\subseteq\nu(O_v)\big]}_{\text{outputs exposed}}\ \wedge\
\underbrace{\big[\nu(G_\rho)\subseteq\nu(G_v)\big]}_{\text{grain fine-enough}}\ \wedge\
\underbrace{\big[\Phi_v=\Phi_\rho\big]}_{\text{filters match (guard)}}.
$$

Each clause has a precise justification:
- **outputs $O_\rho\subseteq O_v$** — the view must expose *at least* the columns the sub-goal needs,
  so the final SELECT can project them (a *covariant* provided-interface requirement).
- **grain $G_\rho\subseteq G_v$** — the view must be at the **same or finer** granularity, so one can
  still `GROUP BY` up to $G_\rho$; a coarser view has already aggregated a key away and is
  unrecoverable (a *contravariant* granularity requirement).
- **filters $\Phi_v=\Phi_\rho$** — intrinsic filters must match **exactly**. This clause is the
  **negative-reuse guard (L1)**: it blocks reusing an all-rows view ($\Phi_v=\varnothing$) for a
  filtered-cohort sub-goal ($\Phi_\rho=\{$latest$\}$).

This is **behavioral subtyping**: $v$ is reusable for $\rho$ iff $v$'s interface is a subtype of what
$\rho$ demands. It is what makes retrieval *precise* — not "topically similar" but *provably usable*.

### 7.3 Stage R3 — Hybrid semantic ranking and Stage R4 — threshold

Let $\mathcal{C}_\rho=\{v\in\mathcal{B}_\rho:\mathrm{compat}(v,\rho)\}$. Among these, rank by
similarity of the request text $t_\rho$ to each view description $d_v$. We use a **hybrid** score
fusing a **dense** bi-encoder and a **sparse** lexical signal. Let $E:\text{text}\to\mathbb{R}^{h}$
be an embedding model ($h=1536$) and
$$ \mathrm{sim}(a,b)=\frac{E(a)\cdot E(b)}{\lVert E(a)\rVert\,\lVert E(b)\rVert}\in[-1,1] $$
the cosine similarity. Let $\mathrm{bm25}(t_\rho,v)$ be an Okapi-BM25 score over a token signature of
$v$ (its name, columns, tables, operators) — this catches exact identifier overlap that embeddings
blur. Fuse by **Reciprocal Rank Fusion** with constant $\eta$ (=60): if $r_{\text{den}}(v)$ and
$r_{\text{spa}}(v)$ are $v$'s ranks under dense and sparse scores,
$$ \mathrm{rrf}(v)=\frac{1}{\eta+r_{\text{den}}(v)}+\frac{1}{\eta+r_{\text{spa}}(v)}. $$
Retrieval returns $\hat v=\arg\max_{v\in\mathcal{C}_\rho}\mathrm{rrf}(v)$ **iff** its dense similarity
clears an acceptance threshold $\tau$; otherwise it is a **miss**:
$$ \mathrm{ret}(\mathcal{G},\rho)=\begin{cases}\hat v & \text{if } \max_{v\in\mathcal{C}_\rho}\mathrm{sim}(t_\rho,d_v)\ge\tau\\ \bot & \text{otherwise.}\end{cases} $$
Both gates are required: the **contract** guarantees the view is *usable* (correctness), the
**threshold** guarantees it is *about the right thing* (relevance).

### 7.4 Selective injection: bounding the generation prompt

When a sub-goal **misses** and a view must be generated, the generator is told which existing views
it may build upon. Injecting the *whole* graph makes each generation prompt grow with the library —
a token cost that rises without bound. Instead we inject only the **top-$k$** existing views by
relevance to $\rho$:
$$ \mathrm{Inject}_k(\rho)=\operatorname*{top\text{-}k}_{v\in\mathcal{V}}\ \mathrm{sim}(t_\rho,d_v). $$
This bounds every generation prompt to $O(k)$ views **independent of $|\mathcal{V}|$**, which (§12)
is what turns memory from a token *penalty* into a token *saving*.

### 7.5 Retrieval at massive scale: HNSW filtered ANN

Sections R1–R4 as stated scan the category bucket. For a *modest* per-database library (tens–hundreds
of views) this exact scan is optimal — brute-force cosine over so few vectors is microseconds, and it
is *exact*, whereas any approximate index would only risk missing the true nearest for no speed gain.

But the design **anticipates the massive regime**: a cross-database or continually-grown library with
$10^5$–$10^7$ views, where an exact scan is infeasible. There, R3 becomes a **filtered
approximate-nearest-neighbor** search over view-description embeddings, and the right index is a
**Hierarchical Navigable Small World (HNSW)** graph. HNSW is itself a graph: each view-embedding is a
node connected to a few nearest neighbors, with a small number of long-range "shortcut" links so that
a *greedy best-first walk* — start anywhere, repeatedly step to the neighbor closest to the query —
reaches the true nearest neighbors in $O(\log|\mathcal{V}|)$ hops instead of scanning all
$|\mathcal{V}|$. Two points make HNSW the correct choice *here specifically*:

1. **It is dense-vector native.** View retrieval ranks by cosine over embeddings; HNSW is the
   state-of-the-art index for exactly that (unlike LSH, which is built for *set/string* similarity and
   is used in this system only for value linking, §9).
2. **The contract becomes a metadata filter.** R2 is a set of hard predicates over view attributes;
   modern practice fuses such predicates *into* the ANN traversal (filtered-HNSW) so that the greedy
   walk only ever considers contract-passing views. Retrieval thus reads as
   $$ \text{attribute filter (R1–R2)} \ \to\ \text{filtered-HNSW over embeddings (R3)} \ \to\ \text{threshold (R4)}. $$

So the *same* four-stage retrieval scales from a small exact scan to a billion-scale filtered ANN by
swapping the R3 index — the algorithm and its guarantees are unchanged. (At small scale we run the
exact scan; the graph story here is the honest, scale-appropriate one, and HNSW earns its place only
once the library is large.)

---

## 8. Guarding Correctness: The Miss and the Bad Hit

A memory introduces exactly two new failure modes relative to pure generation. We handle each with a
*guarantee*, not a hope.

### 8.1 The miss is safe (a correctness theorem)

A **miss** is a retrieval that fails to surface a relevant stored view. Its consequence here is **not**
a wrong answer: the sub-goal falls through to **generation** (§6.4), the same complete generator that
a memory-less system would use, backed by the recall-safe exhaustive schema handling of §6.2. Hence:

> **Proposition (graceful miss).** For any question, the answer produced with the view memory is
> *at least as correct* as the answer produced by pure generation, provided the reuse guards (§8.2)
> admit only interface-compatible, verifier-approved views. A retrieval miss can only cause a
> **redundant re-derivation** (an efficiency cost), never an incorrectness the generator would not
> also incur.

Intuitively, the memory is a **cache over a complete function**: a cache *miss* recomputes (correct,
slower); only a *bad hit* can be wrong. This reframes the recall problem of §1.1 into a benign
cache-miss and concentrates all correctness risk on the bad hit, which we now attack in four layers.

### 8.2 The bad hit — a four-layer defense

A **bad hit** reuses a view that passes retrieval but is subtly wrong for $\rho$ (wrong filter, grain,
aggregation, time window, or a renamed output). This is the *only* way the memory can *reduce*
correctness, so it receives the bulk of our machinery. The layers are cheap-first and independent, so
they compose as a funnel.

**L1 — Symbolic contract (§7.2).** The exact-filter clause $\Phi_v=\Phi_\rho$ already rejects the
canonical bad hit (all-rows vs filtered cohort) whenever the intrinsic filter is *declared*. Most bad
hits are *undeclared*-semantics cases the contract cannot see — hence L3/L4.

**L2 — Execution-grounded validation.** A reused view is composed into a query that is **executed**
(§6.6); if the reuse produced a broken query it fails and repair triggers. This catches *structural*
mismatches but not a reuse that is wrong-yet-runnable.

**L3 — Adversarial verifier.** After retrieval proposes a hit $\hat v$ for $\rho$, $N$ **independent,
skeptical** verifier judges each look for a reason $\hat v$ does **not** satisfy $\rho$ — a filter,
grain, aggregation, time-window, or output mismatch — and default to **REJECT** when uncertain. Let
$\mathrm{ver}_i(\hat v,\rho)\in\{0,1\}$ be the $i$-th judge's approval ($1$=allow). Reuse proceeds
only under a **majority-allow** rule:
$$ \textsf{accept}(\hat v,\rho)=\Big[\ \textstyle\sum_{i=1}^{N}\mathrm{ver}_i(\hat v,\rho)\ \ge\ \big\lceil N/2\big\rceil\ \Big]. $$
Because each judge is prompted to *refute* and defaults to reject, L3 catches semantic mismatches the
symbolic contract misses — e.g., a view that returns *all recorded versions* proposed for a sub-goal
that needs the *latest* version, when "latest" was not captured in $\Phi$.

**L4 — Provenance / counter-example memory (a skill learns its boundary).** Each view $v$ carries two
evolving sets:
$$ \mathrm{Valid}(v)\ =\ \{\text{sub-goals } \rho \text{ for which reusing } v \text{ yielded a correct answer}\}, $$
$$ \mathrm{Counter}(v)\ =\ \{\text{sub-goals for which reusing } v \text{ was wrong (an observed bad hit)}\}. $$
After each question, reused views are updated: a correct outcome appends $\tilde Q$ to
$\mathrm{Valid}(v)$; a bad hit appends it to $\mathrm{Counter}(v)$. Before any future reuse, a cheap
**pre-emptive reject** fires if the current sub-goal resembles a stored counter-example:
$$ \textsf{reject}_{\text{prov}}(v,\rho)=\Big[\ \max_{c\in\mathrm{Counter}(v)}\mathrm{sim}(t_\rho,c)\ \ge\ \theta\ \Big], $$
with threshold $\theta$. Over time each skill accumulates the empirical *preconditions* under which
it is safe — the library becomes self-correcting, and every observed bad hit becomes a hard negative
that also sharpens L1/L3.

The full reuse decision is therefore
$$ \text{reuse } \hat v \iff \mathrm{compat}(\hat v,\rho)\ \wedge\ \neg\,\textsf{reject}_{\text{prov}}(\hat v,\rho)\ \wedge\ \textsf{accept}(\hat v,\rho), $$
and the reused view is *still* execution-validated in composition (L2). The four layers are
independent lines of defense; a bad hit must defeat all of them.

*Example.* Suppose the library holds $v_{\text{allver}}$ = "all recorded score versions"
($\Phi=\varnothing$) and the sub-goal $\rho_2$ needs the *latest* version ($\Phi_{\rho_2}=\{$latest$\}$).
L1 rejects it (filters differ). Had $v_{\text{allver}}$ *failed* to declare its "all versions"
semantics, L3's skeptic would note "this view does not restrict to the latest recorded row" and
reject; and if this exact bad hit had occurred before, L4 would reject pre-emptively. The correct
$v_{\text{latest}}$ is retrieved instead.

---

## 9. Value Linking

Filter literals in generated SQL frequently do not match the data verbatim (`'US'` vs
`'United States of America'`). We ground them with a **MinHash-LSH** index over the database's
distinct short string cell values. Offline, each value is shingled into character 3-grams,
MinHash-signed, and inserted into a Locality-Sensitive-Hashing index (near-duplicate strings collide
into shared buckets). At generation/repair time, string literals are extracted from the candidate SQL
(via SQL-AST parsing), each is MinHash-queried to retrieve near-value candidates, and the best is
chosen by edit similarity (with an optional embedding fallback). A mismatched literal yields a
correction hint fed back into repair. **LSH is the right tool here** — the value set is large and the
similarity is *set/string* (Jaccard over shingles) — which is precisely the regime where LSH beats a
dense index, and complements the dense-vector HNSW used for *view* retrieval (§7.5).

---

## 10. Dialect-Agnostic, Budget-Aware Execution

The method is defined over an abstract "execute this SQL against $D$" primitive and therefore runs on
any executable backend. We instantiate two.

**SQLite.** Local databases execute directly; a per-query wall-clock bound (via a progress handler)
and a result-row cap keep runaway queries from hanging the run.

**BigQuery (native cloud).** For warehouse-scale databases, generation targets BigQuery Standard SQL
(backtick-qualified tables, `UNNEST` for nested fields, wildcard tables for date-shards). The key
cost lever: **view validation uses BigQuery *dry-runs*, which scan zero bytes and are therefore
free**, so every candidate view is validated (L2) at **no cost**; only the *final* composed query per
question is billed. A per-query byte cost-guard and a cumulative budget cap keep an entire run inside
BigQuery's monthly free tier. This makes execution-grounded validation — the backbone of the method —
*affordable at cloud scale*.

---

## 11. Complexity and Cost

Let $|\mathcal{V}|$ be the library size, $\mathcal{C}_\rho$ the contract-passing candidates for a
sub-goal, $h$ the embedding dimension, and $k$ the selective-injection width.

- **Retrieval (per sub-goal), small regime:** $O(|\mathcal{B}_\rho|)$ contract checks (small-set
  operations) + $O(|\mathcal{C}_\rho|\cdot h)$ cached dot products + an argmax. No sort, no index.
- **Retrieval, massive regime (§7.5):** attribute filter + $O(\log|\mathcal{V}|)$-hop filtered-HNSW
  walk; embeddings cached, dot products $O(h)$ per hop.
- **Generation context:** $O(k)$ injected views regardless of $|\mathcal{V}|$ (§7.4).
- **Composition/validation:** $O(V{+}E)$ topological sort over the chosen dependency sub-DAG.
- **Cloud cost:** dominated by *final* query bytes; view validation is *free* (dry-run). Value
  linking's LSH index is built once per database.

The upshot: per-question work is **bounded independent of library size** in both compute (selective
injection + ANN) and cloud dollars (free validation), which is what makes a continually-growing
memory tractable.

---

## 12. Experiments

We report the current, honest evidence. All runs use a strong reasoning LLM, real execution, and real
token/byte accounting; Execution Accuracy (EX, §2) is scored against gold. Configurations share
identical agents and differ **only** in memory, so their deltas isolate each mechanism:
**A** = online memory from an empty start; **B** = no memory (regenerate every view, discard);
**S** = cold-start seed then online growth.

### 12.1 The memory delivers the same answers more cheaply (homogeneous streams)

On a homogeneous multi-question stream (three databases, 20 questions each), **S** and **A** match the
no-memory baseline **B** on accuracy while **generating far fewer views**: e.g., total view
generations $128$ (**S**) vs $137$ (**A**) vs $179$ (**B**) — a $\sim28\%$ reduction — with **S**
reaching the **highest reuse** and answering $5\times$ more questions with **zero** new generation
than **A**. The seed contributes reuse from question #0, exactly its purpose.

### 12.2 Selective injection converts memory into a token *saving*

A controlled 40-question single-database stream shows the token dynamics precisely. The no-memory
baseline is **flat** ($\approx9.3$k tokens/question). With *whole-graph* injection, the seed config's
per-question cost **rises** as the library grows and ends $\sim18\%$ *above* baseline in total tokens
**despite** generating $43\%$ fewer views — memory shifts cost from *generation count* to *prompt
size*. With **selective injection** (§7.4) the per-question cost **falls** over the stream and total
tokens drop to $\sim8\%$ **below** baseline while keeping the generation win — the intended "same
answers, cheaper."

### 12.3 The negative-reuse guards work

Unit-checked, the adversarial verifier (L3) **rejects** an all-rows view proposed for a
completed-only sub-goal and **accepts** it for a matching one — the canonical bad hit. In a
stream where the symbolic guard is disabled to isolate L3, verify (majority of 3) **rejected 5**
accepted reuses and **cut negative reuse** (reuses that led to wrong answers) from $5$ to $2$, at a
token cost and a small reuse loss. The guards' *value scales with how often bad reuse actually
occurs*.

### 12.4 The empirical law: reuse ∝ homogeneity

Across easy/homogeneous streams, medium/heterogeneous streams, and hard analytic benchmarks, reuse
tracks how *related* a database's questions are: high (tens of percent) where intermediate relations
recur, and near-zero where each question is bespoke — in the extreme, on a hard benchmark of mostly
one-off cloud-warehouse questions, reuse collapses to $\sim0$ and the memory is a near-no-op. This is
not a weakness to hide but a **characterization**: the method earns its keep exactly in the realistic
continual regime (a database serving a long stream of related questions), and is safely inert
otherwise (it never *hurts* accuracy — the miss is graceful, §8.1).

### 12.5 It runs natively on the cloud, essentially for free

The full method (retrieve → generate BigQuery CTEs → free dry-run validation → compose → execute →
score) runs end-to-end on BigQuery within the monthly free tier — a 12-question database cost
**$\$0.0076$** total, with view validation contributing **zero** (dry-run). Feasibility at
warehouse scale is thus established with negligible spend.

---

## 13. Discussion, Limitations, and Future Work

- **When to deploy.** The method is for **continual** Text-to-SQL over a database serving many
  related questions (dashboards, BI assistants, repeated analytics). §12.4 makes the deployment
  criterion explicit and honest.
- **Library hygiene (redundancy).** A retrieval miss regenerates a possibly-near-duplicate view, so a
  long-lived library accumulates variants. This is an *efficiency* concern (not correctness) with a
  clear remedy we outline but leave to future work: **write-time dedup** (structural-AST hash +
  execution-equivalence), **periodic refactoring** (cluster → merge → *extract shared base views* via
  anti-unification, gated by execution-equivalence and a minimum-description-length objective), and
  **usage-based eviction** — precisely the operations for which the DEPENDS_ON graph (§4.2) becomes
  load-bearing.
- **A learned retriever.** Every observed correct/incorrect reuse (§8.2, L4) is a labeled
  $(\text{sub-goal},\text{view})$ example, with the contract supplying *hard negatives* for free —
  enabling an execution-grounded, contrastively fine-tuned retriever as a natural next step.
- **Determinism.** With a reasoning LLM that fixes decoding temperature, run-to-run variation is
  non-trivial; small accuracy deltas across configurations are within this noise, which is why we
  emphasize the *mechanistic* deltas (reuse counts, generation counts, tokens) that are robust to it.

---

## 14. Conclusion

We recast Text-to-SQL over massive schemas as the maintenance and assembly of a **self-growing,
execution-validated library of reusable SQL-view skills**, cold-started from the schema before any
question is seen. The design is *recall-safe by construction* (exhaustive schema handling; a graceful
miss that degrades to generation), *precise by a typed capability contract* backed by an HNSW filtered
index, *correct under reuse via a four-layer defense* against the bad hit, *token-bounded via selective
injection*, and *affordable at cloud scale via free dry-run validation*. Beyond the artifact, we
contribute a clean law — **reuse ∝ question homogeneity** — that says precisely when such a memory
pays off. We believe this "views-as-skills, validated-then-reused" paradigm is a productive new lens
on database-grounded language interfaces, and that its graph memory, capability retrieval, and
negative-reuse defenses each open their own line of follow-on work.

---

### Appendix A — Symbol reference

| symbol | meaning | defined |
|---|---|---|
| $D=(\mathcal{T},\mathcal{C},\mathcal{R})$ | database: tables, columns, foreign keys | §2 |
| $m,\ n_i$ | #tables; #columns of table $T_i$ | §2 |
| $S,\ \Pi(S)=\{S^j\},\ B$ | schema; its chunk partition; chunk token budget | §2, §6.2 |
| $S_{\text{filt}},\ J^j$ | filtered schema; per-chunk schema selection | §6.3 |
| $Q,\ K,\ \tilde Q$ | question; external knowledge; rewritten question | §2, §6.1 |
| $Y,\ \llbracket Y\rrbracket_D,\ \equiv$ | query; its result; result-set equivalence (EX) | §2 |
| $v=\langle n,\kappa,\beta,O,G,\Phi,\delta,d\rangle$ | a view (skill) and its interface | §4.1 |
| $\mathcal{K}$ | the 10 skill categories | §4.1 |
| $\mathcal{G}=(\mathcal{V}\cup\mathcal{SK},\mathcal{E})$ | view-memory graph: view/skill nodes, edges | §4.2 |
| $\mathcal{E}_{\text{inst}},\ \mathcal{E}_{\text{dep}}$ | INSTANTIATES, DEPENDS_ON edges | §4.2 |
| $\rho=\langle\kappa_\rho,O_\rho,G_\rho,\Phi_\rho,t_\rho\rangle$ | sub-goal (view request) | §4.3 |
| $\nu(\cdot),\ \mathrm{compat}(v,\rho)$ | name normalizer; compatibility contract (L1) | §7.2 |
| $E,\ h,\ \mathrm{sim},\ \tau$ | embedding; its dim (1536); cosine; accept threshold | §7.3 |
| $\mathrm{bm25},\ \mathrm{rrf},\ \eta$ | BM25; reciprocal-rank fusion; RRF constant (60) | §7.3 |
| $\mathrm{ret}(\mathcal{G},\rho),\ \bot$ | retrieval result; the miss symbol | §7.3 |
| $\mathrm{Inject}_k,\ k$ | selective-injection set; its width | §7.4 |
| $\mathrm{ver}_i,\ N,\ \textsf{accept}$ | verifier judges; their count; majority rule (L3) | §8.2 |
| $\mathrm{Valid}(v),\mathrm{Counter}(v),\theta$ | provenance sets; counter-example threshold (L4) | §8.2 |
| $T_{\max}$ | execution-repair attempt bound | §6.6 |
