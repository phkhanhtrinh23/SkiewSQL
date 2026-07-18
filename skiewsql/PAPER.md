# SkiewSQL: Taming Massive-Schema Text-to-SQL with Executable Agentic CTE Views — Decompose to Construct, Reuse to Save

> Working title / method name **SkiewSQL** (*Skill-driven, Execution-validated Views for SQL*) is a
> placeholder you can rename. This document is a full technical write-up intended as the backbone of
> a paper: every component, every data structure, and every design decision is described step by
> step, with a single running example carried from the first stage to the last, and with all
> mathematical notation defined before it is used.

---

## Abstract

Answering a natural-language question over a **real enterprise database** is hard for a reason that
has little to do with the question and everything to do with the **schema**: warehouses expose
hundreds to thousands of tables with deeply nested and date-sharded columns. Such a schema **does
not fit** in a language model's context window; and even when it is squeezed in, the model's
attention **degrades on the middle of a long context** — the *lost-in-the-middle* effect — so it can
neither reliably ground the relevant tables nor construct correct SQL. Meanwhile the *target* queries
are genuinely **complex** — multi-step Common Table Expressions (CTEs), window functions, careful
cohort definitions — which one-shot generation over a giant, half-attended schema botches, and which
are nearly impossible to debug when they fail as a single monolithic query.

Our central proposal is a way to **handle the long context of many tables and, from it, construct
complex SQL by decomposition.** SkiewSQL never shows the model the whole schema and never asks it to
emit one long query. Instead it **decomposes** each question into small, **executable, explainable,
debuggable** CTE sub-commands — *intermediate agentic table views* — each generated and **validated by
execution** over a manageable slice of the schema, and then **aggregates** those CTEs into the final
answer. Decomposition simultaneously defeats the context limit (the whole schema is never needed at
once) and lost-in-the-middle (each sub-command reasons over a small, focused context), and it turns
opaque analytic SQL into a chain of individually testable relational steps.

A CTE, once built, is itself a **small, self-contained table** — so it can be **reused**. This
observation yields a *dividend* on top of the decomposition contribution: we package each CTE as a
**skill agentic view** (the CTE plus the context an agent needs to know *when and how* to use it) and
keep a growing **skill set**. When later questions share overlapping structure — as they do when a
warehouse serves a stream of related analytics — SkiewSQL **retrieves and reuses** a skill instead of
regenerating a near-identical CTE, saving substantial token, rate-limit, and API cost (which matters
most under expensive commercial APIs). To keep reuse *safe*, retrieval is **typed capability matching**
(not mere similarity) backed by a navigable-small-world index, and reuse is protected by a
**four-layer defense** against the one failure a skill set can introduce — reusing a view that looks
right but is subtly wrong. SkiewSQL is **dialect-agnostic** (native SQLite and BigQuery, with *free*
dry-run validation in the cloud) and **budget-aware**. We formalize the method, walk a real analytic
question through the entire pipeline, analyze complexity and cost, and show that decomposition makes
massive-schema analytic SQL tractable while the skill set makes a *batch* of related queries markedly
cheaper — with a clean characterization of exactly when reuse pays: **reuse is proportional to
question-stream homogeneity.**

---

## 1. Introduction

### 1.1 The real obstacle is the schema, not the question

Modern data lives in **massive schemas**. A single analytics warehouse routinely exposes thousands
of columns across hundreds of tables, with nested record types and tables **sharded by date**
(`events_20210103, events_20210104, …`). This *long context of many tables* is the true obstacle to
Text-to-SQL, and it manifests as two compounding failures.

**Failure 1 — the schema does not fit.** A full textual rendering of such a database exceeds even a
long-context model's window. One simply cannot place the whole schema in the prompt.

**Failure 2 — even when it fits, the model does not *use* it.** Suppose the schema is squeezed in.
Language models attend **unevenly** to long inputs: they use information at the *beginning* and *end*
of the context far better than information in the **middle** — the *lost-in-the-middle* phenomenon
documented by Liu et al. [1] (§1.5). A relevant table buried mid-schema is effectively invisible, so
the model mis-grounds columns and hallucinates joins. Enlarging the context window does **not** fix
this; the degradation persists in explicitly long-context models [1].

These two failures matter precisely because the **target queries are complex**. The questions asked
of warehouses are not `SELECT … WHERE …` lookups; they are **analytic** — *"the 5-day moving average
of predicted sales,"* *"the RFM (recency–frequency–monetary) segment of each customer,"* *"the latest
recorded score per entity per year."* Correct SQL for these is long, multi-CTE, and window-heavy.
Asking a model to emit such a query **in one shot, over a giant half-attended schema** is doubly
doomed: it cannot see all the tables it needs, and it must produce a large monolithic query with no
opportunity to check any intermediate step. When it fails — a wrong join, a mis-scoped filter — the
error is buried inside an opaque block of SQL that is nearly impossible to localize or debug.

### 1.2 Our proposal: decompose the query into executable agentic CTE views

Our central idea is a way to **handle the long context of many tables and, from it, construct complex
SQL by decomposition** — never showing the model the whole schema at once, and never asking it to
write one long query.

> Decompose each question into a sequence of small, **executable, explainable, debuggable** CTE
> sub-commands — *intermediate agentic table views* — where each view is generated and **validated by
> execution** over a *manageable slice* of the schema; then **aggregate** the views into the final
> query.

Each CTE is a *tiny relational program with a single responsibility* (a join, a rollup, a
latest-per-key dedup). Because it is generated over a small, focused slice of the schema, the model
attends to it fully — sidestepping **both** Failure 1 (the whole schema is never needed) and Failure
2 (no relevant table is stranded in the middle of a long context). Because it is **executed and
checked** the moment it is written, an error is caught and localized at the *sub-command* level rather
than surfacing as a mysterious wrong answer at the end. And because the final query is a
*composition* of validated views, the reasoning is transparent and auditable. This is the primary
contribution: **decomposition-by-executable-views is what makes massive-schema, complex analytic
Text-to-SQL tractable and debuggable.**

### 1.3 A dividend: CTEs are small tables, so they are reusable

Once we have decomposed queries into validated CTE views, a second observation follows naturally: a
CTE **is itself a small, self-contained table**, and *the same intermediate relations recur* across
the many questions a warehouse serves ("latest version of a repeatedly-updated record," "orders
joined to customers with status," "revenue per region per month"). It is wasteful to regenerate — and
re-validate — a near-identical CTE for every question, especially under **expensive commercial APIs**
with token costs and rate limits.

So we take a further step: package each CTE as a **skill agentic view** — the CTE *plus the context an
agent needs to know when and how to use it* — and keep a growing **skill set**. When a later question
overlaps (in part or whole) with a stored skill, we **retrieve and reuse** it instead of regenerating.
This is a **cost dividend on top of the decomposition contribution**, and it is exactly the setting
that arises in practice: a **batch** of related analytics over one warehouse, where many questions
share overlapping ideas.

*On the natural objection ("a skill is reusable only within its own database — isn't that a waste?").*
No: this is the intended and realistic regime. Enterprise Text-to-SQL is **continual** — a warehouse
serves a long stream of related questions — so within-database reuse is precisely where the savings
live. Reuse is a *bonus* layered on the decomposition method; it never changes the answer a question
would otherwise get (§8.1), and it is *inert* (a no-op) when questions are unrelated (§12.4). Nothing
is wasted: unused skills simply cost nothing.

### 1.4 Why the dividend is hard to collect — and our contributions

A skill set is only safe if reuse is **precise**. Allowing reuse introduces one dangerous failure —
the **bad hit**: reusing a stored view that *looks* relevant but is subtly wrong for the current
question (an *all-rows* revenue view reused for a *completed-orders-only* question). A bad hit yields
confidently wrong SQL. Making reuse simultaneously **high-recall** (find the skill when it exists) and
**high-precision** (never reuse the wrong one), at massive scale, is the technical crux of the second
half of the paper.

**Contributions.**

1. **Decomposition into executable agentic CTE views** (§3–§6): a method that tames long-context,
   many-table schemas and constructs complex analytic SQL by decomposing each question into small,
   **execution-validated, explainable, debuggable** CTE sub-commands and composing them — the primary
   contribution.
2. **Recall-safe schema handling** (§6.2): the schema is processed **exhaustively by chunk** so that
   *no table is ever silently dropped* — the opposite of lossy retrieval-based schema linking — which
   is what defeats both context overflow (Failure 1) and lost-in-the-middle (Failure 2) without
   sacrificing recall.
3. **Execution-grounded, debuggable generation** (§5, §6.6): every CTE is **run** against the real
   database before it is trusted, so hallucinated columns/joins are caught and *localized* at the
   sub-command level rather than emerging as an opaque wrong answer.
4. **The reuse dividend — a skill set of agentic views** (§4–§5): CTEs are packaged as
   *skill agentic views* (with when/how-to-use context), **cold-started from the schema alone** so
   reuse is available from the first question, then retrieved and reused to save token/rate-limit/API
   cost on batches of related queries.
5. **Typed capability retrieval at scale** (§7): reuse is decided by a **compatibility contract** — a
   behavioral-subtyping check over a view's interface (category, outputs, grain, intrinsic filters) —
   composed with **dense+sparse hybrid** similarity and a **navigable-small-world (HNSW) filtered
   index**; retrieval as *constraint satisfaction over interfaces*, not mere similarity search.
6. **A four-layer defense against the bad hit** (§8): (L1) the symbolic contract, (L2) execution
   validation, (L3) an **adversarial verifier** (independent skeptics that must fail to refute a reuse
   for it to proceed), and (L4) a **provenance memory** in which each skill *learns its own boundary*
   from observed correct/incorrect reuses. A retrieval *miss* degrades gracefully to generation —
   never a wrong answer (§8.1), which we prove.
7. **Token-efficiency by design** (§7.4): a **selective-injection** rule bounds every generation
   prompt to $O(k)$ views independent of library size, turning the skill set from a token *cost* into
   a token *saving* on related-query batches.
8. **Dialect-agnostic, budget-aware execution** (§10): the same method runs on SQLite and **natively
   on BigQuery**, where **free dry-run validation** validates every candidate view at **zero scan
   cost**, keeping full cloud runs inside the monthly free tier.
9. **An empirical law** (§12): the reuse dividend is governed by **savings ∝ question-stream
   homogeneity** — large where a warehouse serves many related questions, near-zero for one-off
   questions — a clean, honest characterization of *when* the skill set pays.

### 1.5 Relation to prior work

**Long context and lost-in-the-middle.** That language models under-use the middle of long inputs is
established by Liu et al., *Lost in the Middle: How Language Models Use Long Contexts* (TACL 2024)
[1], who show accuracy is highest when relevant evidence sits at the start or end of the context and
degrades sharply in the middle — *even for long-context models*. This is the empirical foundation of
our Failure 2 and the reason we decompose rather than dump a giant schema into one prompt.
Retrieval-augmented approaches shorten the context by fetching a subset, but retrieval *may omit
necessary evidence* [2] — the recall failure our exhaustive, chunk-wise schema handling (§6.2) is
designed to avoid. **Large-schema Text-to-SQL.** Benchmarks such as Spider 2.0 [3] make the problem
concrete: schemas with thousands of columns and analytic questions whose gold answers are multi-CTE.
Our method targets exactly this regime. **Skill/library learning.** The idea of accumulating reusable
sub-programs appears in agent and program-synthesis settings; our skill set specializes it to
*execution-validated SQL views with typed reuse contracts*, and — distinctively — **cold-starts the
library from the schema before any question is seen** (§5).

> *References (to finalize with your bibliography):* **[1]** N. F. Liu, K. Lin, J. Hewitt, A.
> Paranjape, M. Bevilacqua, F. Petroni, P. Liang. "Lost in the Middle: How Language Models Use Long
> Contexts." *TACL*, 12:157–173, 2024 (arXiv:2307.03172). **[2]** the general RAG-omits-context
> observation. **[3]** the Spider 2.0 large-schema Text-to-SQL benchmark. **[4]** Text2SQL-Flow:
> a SQL-aware data-augmentation framework producing multi-variation Text-to-SQL streams over
> Spider/BIRD/EHRSQL (arXiv:2511.10192); the **SQLFlow** corpus used in §12.6.

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

**The reuse contract (skillification).** Beyond the terse description $d$, each view is *skillified*
into a structured, machine-usable contract that is injected at decision time: (i) a per-column
**output schema** — each $O$ column's meaning and the base column/metric it derives from; (ii)
**grounded columns** and **metric definitions** — the base `table.column`s the body touches and how
each derived measure is computed; and (iii) **composition** guidance — *cardinality-safe* join rules
stating which joins preserve the view's grain and which would fan-out and duplicate its measures. The
output-schema and metric fields are handed to the reuse **selector** (§8) to ground the match; the
composition rules are handed to the **planner** (§6.5) as **join-safety** constraints, so a reused
view is not silently multiplied by a one-to-many join (the classic wrong-yet-runnable failure). We
deliberately **exclude** suppression-style fields — a "when-not-to-use" blocklist and sibling
"use-$X$-instead" comparisons: an ablation showed they *suppress* legitimate reuse (the pipeline
already falls back to fresh generation whenever no view fits, §6.4) while raising both cost and
negative-reuse count. The contract is thus purely *enabling*; rejection is left to the four-layer
guard of §8.2.

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
EX (§2). We keep this revisor deliberately **conservative** — it corrects clear errors but does not
second-guess a correct query.

> **A note on what this stage can and cannot do.** Unlike the reuse guards of §8 (which only touch
> questions where reuse fired), the revisor runs on *every* question, so it is the natural place to
> attack the dominant residual error — a freshly-generated query that executes but computes the wrong
> answer downstream (wrong extreme, mis-derived age). We tested strengthening it into a **self-
> consistent self-check** — a more prescriptive revisor plus result-set majority voting over $m$
> independent re-derivations (`--self_consistency` $=m$). It **did not help**: on BIRD-MiniDev it
> *lowered* accuracy $\approx 6$ points, because the prescriptive revisor rewrote already-correct
> queries and, under voting, two such rewrites outvoted the correct original (self-consistency
> reinforcing *systematic* model errors rather than averaging out random ones). We therefore default
> to the single conservative pass ($m=1$) and report this as a negative result (§12.3). Improving
> single-query correctness on hard analytic questions remains open (§13).

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

**Snowflake (native cloud).** Generation targets Snowflake SQL (double-quoted lowercase identifiers;
`VARIANT` path access and `LATERAL FLATTEN` for semi-structured columns). View validation uses
`cursor.describe()`, which **compiles** the CTE against the live schema and returns its output columns
**without executing it** — scanning zero data — the Snowflake analogue of BigQuery's dry-run, so L2
validation is again *free*; only the final composed query consumes warehouse time (statement-timeout
and result-row guarded). The seed library (§5) is likewise built with describe-only validation, so
cold-starting a cloud database costs no warehouse compute.

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

### 12.3 The negative-reuse guards work — and how to *measure* negative reuse honestly

Unit-checked, the adversarial verifier (L3) **rejects** an all-rows view proposed for a
completed-only sub-goal and **accepts** it for a matching one — the canonical bad hit. In a
stream where the symbolic guard is disabled to isolate L3, verify (majority of 3) **rejected 5**
accepted reuses and **cut negative reuse** (reuses that led to wrong answers) from $5$ to $2$, at a
token cost and a small reuse loss. The guards' *value scales with how often bad reuse actually
occurs*.

**The metric itself must be defined with care, or it over-counts by an order of magnitude.** The naive
definition — *a reuse fired and the answer was wrong* — blames a reused view for a failure it did not
cause. Half of a grown library (on BIRD-MiniDev, $220/442$ views, $50\%$) are **trivial single-table
projections** (`SELECT cols FROM t`, no filter/join/aggregation); reusing one is semantically identical
to reading the base table and *cannot* change a result. Yet they match almost every question and so sit
in the `FROM` clause of many wrong answers as innocent bystanders. Counting them, BIRD-MiniDev config
**A** shows $35$ "negative reuses"; counting only **causally-capable** reuse (a JOIN/aggregation/window
view, which alone can distort a result) the real figure is **$4$** — a $9\times$ inflation. We therefore
report negative reuse over non-trivial reuse only, and cross-check with **reuse-conditional accuracy**
(a metric no inert hit can move): on BIRD-MiniDev, questions where reuse fired are answered *more*
accurately than those where it did not ($47.8\%$ vs $38.1\%$), confirming reuse is not harmful. The
residual real negatives ($0$–$8$ across configs) are concentrated exactly where §8 predicts — JOIN
views (row fan-out) and aggregation views (grain lock-in).

**Three negative results (what did *not* work), reported for completeness.** (i) *Blocking* trivial-
projection reuse outright drives the mislabelled count to $\approx 0$ but is a net loss: with the inert
views withheld, the system must **regenerate** them, so generations rise $+16$–$35\%$ and tokens
$+9$–$13\%$ with **no** accuracy gain (BIRD accuracy in fact *drops*, the base projections aiding column-
vocabulary consistency). The lesson is to fix the *metric*, not the reuse. (ii) Adding **grain self-
consistency** to the sub-goal proposer (three sampled decompositions, majority-merged grain) to reject
wrong-grain reuse *increased* real negative reuse ($4\to 8$ on BIRD) at $+24$–$48\%$ tokens: the extra
samples inflated the number of sub-goals faster than they tightened grain, and the compatibility guard
skips the grain test when a declared grain is empty, so more (not less) reuse slipped through. (iii)
Strengthening the final revisor (§6.7) into a **self-consistent self-check** — a prescriptive
"re-derive and check MIN/MAX, age, grain" revisor plus result-set majority voting over three
re-derivations — *lowered* BIRD-MiniDev accuracy by $\approx 6$ points ($39.4\%\to 33.3\%$ on config B)
at roughly $2\times$ tokens: the prescriptive pass rewrote already-correct queries and voting let two
matching wrong rewrites outvote the correct original, i.e. self-consistency **reinforced systematic
errors** instead of averaging out random ones. All three interventions were reverted (defaults restored:
trivial reuse kept, single decomposition sample, single conservative revisor); the durable outcome is
the honest metric above, and raising single-query accuracy on hard analytic questions remains open (§13).

### 12.4 The empirical law: reuse ∝ homogeneity

Across easy/homogeneous streams, medium/heterogeneous streams, and hard analytic benchmarks, reuse
tracks how *related* a database's questions are: high (tens of percent) where intermediate relations
recur, and near-zero where each question is bespoke — in the extreme, on a hard benchmark of mostly
one-off cloud-warehouse questions, reuse collapses to $\sim0$ and the memory is a near-no-op. This is
not a weakness to hide but a **characterization**: the method earns its keep exactly in the realistic
continual regime (a database serving a long stream of related questions), and is safely inert
otherwise (it never *hurts* accuracy — the miss is graceful, §8.1). §12.6 makes this law quantitative
across two augmented benchmarks, and shows a second-order effect: the *harder and less homogeneous*
the stream, the more the reuse must come from the **cold-start seed** rather than from slow online
accumulation.

### 12.5 It runs natively on the cloud, essentially for free

The full method (retrieve → generate BigQuery CTEs → free dry-run validation → compose → execute →
score) runs end-to-end on BigQuery within the monthly free tier — a 12-question database cost
**$\$0.0076$** total, with view validation contributing **zero** (dry-run). Feasibility at
warehouse scale is thus established with negligible spend.

### 12.6 Two augmented benchmarks: where the seed pays, and by how much

To probe the dividend on *realistic related-query streams* we evaluate on **SQLFlow** (the
Text2SQL-Flow corpus [4]), which expands each seed question of Spider/BIRD into six controlled
**semantic variation types** (business-logic changes, value transformations, structure modifications,
complexity/performance rewrites, advanced-SQL features). This is precisely the regime our method
targets: a database served by *many related but non-identical* questions. We run identical A/B/S
agents on the first 20 questions of three databases each from **SQLFlow-Spider** (a homogeneous,
mid-size regime) and **SQLFlow-BIRD** (a harder, more diverse regime whose `works_cycles` schema is a
large, multi-chunk AdventureWorks derivative), 60 questions per configuration:

| benchmark | cfg | EX | reuse | seed-reuse | view gens | gens vs **B** | tokens vs **B** | neg-reuse |
|---|---|---|---|---|---|---|---|---|
| SQLFlow-**Spider** | B | 86.7% | 0% | — | 176 | — | — | 0 |
| | A | 86.7% | **34.3%** | 0% | 117 | **−33.5%** | **−13.2%** | 4 |
| | **S** | **88.3%** | 28.2% | 7.3% | 126 | **−28.4%** | **−8.0%** | 3 |
| SQLFlow-**BIRD** | B | 56.7% | 0% | — | 175 | — | — | 0 |
| | A | 55.0% | 6.7% | 0% | 164 | −6.3% | ≈0% | 1 |
| | **S** | **56.7%** | **15.9%** | 6.8% | 145 | **−17.1%** | ≈0% | 8 |

Four things stand out, all consistent with the theory of §8–§12.4.

**(1) Accuracy is at parity.** On both benchmarks the memory configurations match the no-memory
baseline **B** within run-to-run noise (§13); **S** *equals* B on both (88.3 vs 86.7; 56.7 vs 56.7).
Reuse never *costs* accuracy — the graceful-miss guarantee (§8.1) holds empirically.

**(2) On the homogeneous stream, the memory is strictly cheaper — in tokens, not just generations.**
SQLFlow-Spider is the first setting where reuse is high enough (28–34%) that selective injection
(§7.4) turns the generation win into a *token* win: **A** and **S** cut total tokens by **13%** and
**8%** below baseline while cutting view generations by **~30%**, at equal accuracy. This is the
"same answers, cheaper" claim realized end-to-end on a real benchmark.

**(3) The colder and harder the stream, the more the seed matters.** The two benchmarks invert the
A-vs-S relationship, and instructively so. On easy/homogeneous SQLFlow-Spider, online memory
bootstraps fast enough that the empty-start **A** *overtakes* the seed on reuse (34.3% vs 28.2%): once
the library is warm, the seed's head start is marginal. On harder/diverse SQLFlow-BIRD the opposite
holds — online memory accumulates too slowly (each variation is genuinely different), so **A** reaches
only 6.7% reuse while **S** reaches **15.9%**, and cuts generations **17%** vs B where A cuts only 6%.
The effect is sharpest per-database: on `retail_world`, **S reuses 20 views (11 of them seeded) versus
A's 9** — the cold-start seed *more than doubles* reuse on the identical DB, supplying from question
\#0 the recurring relations that A never has time to rediscover. **The cold-start seed is worth most
exactly where continual online memory is weakest.**

**(4) More reuse concentrates the need for the guards.** Negative-reuse events rise with reuse volume
and stream difficulty — 8 for SQLFlow-BIRD **S** versus 0–4 elsewhere — because a harder schema offers
more superficially-similar-but-wrong views. This is not noise to hide but the *deployment signal* for
the L1–L4 defenses (§8.2): the adversarial verifier and counter-example memory earn their token cost
precisely on the hard, high-reuse databases where bad hits actually occur. On SQLFlow-BIRD, token
savings also *wash out* (≈0%) because the massive `works_cycles` schema dominates per-question cost
regardless of how many views are reused — so on truly massive schemas the dividend shows up as fewer
LLM generations and API/rate-limit pressure rather than raw tokens, which §12.4's law already predicts.

### 12.7 Does schema complexity break accuracy-neutrality? A cautionary null result

We stress-tested the accuracy-neutrality claim on **complex, domain-specific** schemas, expecting it to
break. It does **not** — and the way it fails to break is itself a useful, cautionary lesson about
single-run evaluation. We evaluate on **ScienceBenchmark** (Kosten et al.) — CORDIS (EU research),
OncoMX (cancer genomics), SDSS (astrophysics), on PostgreSQL — and **BEAVER** (enterprise data-warehouse,
MySQL), with gold SQL executed on the same engine as the prediction (fair EX). We compare **B** (no
memory), **A** (online, unconstrained = *aggressive* reuse), **A-atomic** (reuse restricted to atomic
SEL/NORM views — regenerate every join/aggregation fresh), **S** (vetted cold-start seed + online
growth), and **S-atomic**. Each ScienceBench run is 40 dev questions/DB whose gold executes.

**A single run tells a dramatic — and false — story.** On our first pass, aggressive reuse appeared to
*cost* accuracy sharply on the science schemas: CORDIS 70.0→57.5, OncoMX 57.5→52.5, SDSS 36.7→26.7, with
non-trivial negative reuse rising with difficulty (4, 4, 11), while the atomic policy and the vetted seed
appeared to *recover* it — even suggesting a clean "complementary mechanisms" pattern (atomic best on
SDSS, seed best on OncoMX). It was a compelling complexity-aware-Pareto narrative. **It did not
replicate.**

**Under repeated runs (n = 3 per cell, independent LLM samples), the effect dissolves into run-to-run
noise.** Because the underlying LLM is non-deterministic, EX on a 40-question set swings enormously: the
**no-memory baseline B alone varies 7–10 points** across identical re-runs. Mean ± range:

| DB | B | A (aggressive) | A-atomic | S |
|---|---|---|---|---|
| CORDIS | 66.7 [62.5–70.0] | 65.8 [57.5–**75.0**] | 68.8 [67.5–70.0] | 68.8 [67.5–70.0] |
| OncoMX | 59.2 [57.5–62.5] | 53.8 [52.5–55.0] | 60.0 [52.5–**67.5**] | 57.5 [55.0–60.0] |
| SDSS | 31.7 [26.7–36.7] | 30.0 [26.7–33.3] | 31.7 [26.7–36.7] | 26.7 [26.7] |

The apparent CORDIS "−12.5" collapses to **−0.9** (A 65.8 vs B 66.7, with A ranging up to 75.0); the
SDSS "−10" collapses to **−1.7**; and the "complementarity" is an **artifact** — A-atomic in fact
*recovers* OncoMX on re-runs (mean 60.0, up to 67.5), it does not fail there. Every configuration's mean
sits inside every other's range. **At n = 40 there is no statistically meaningful accuracy difference
between B, A, A-atomic, and S on these schemas.**

**What actually survives, honestly stated:**
1. **Reuse is ~accuracy-neutral even on complex schemas at this sample size.** The single-run 5–12-point
   "penalty" was noise; we could not measure a real effect above the ±7–10-point run-to-run variance.
2. **A weak, consistent *direction* remains** — unconstrained aggressive reuse sits slightly *below* B on
   all three complex schemas (mean gaps −0.9 / −5.4 / −1.7), while A-atomic and S sit *at or above* B on
   all three. This is suggestive of the join/grain negative-reuse mechanism of §8 (a reused join can
   execute yet answer a subtly different question) but is **not** a statistically established effect here;
   confirming it would need a much larger question set or a many-seed study.
3. **The robust, replicable benefit is the *generation saving*, not accuracy.** Across all runs A-atomic
   and S answer at B-level accuracy while generating materially fewer views (≈30–40% on CORDIS), and the
   atomic policy is harmless on the simple schemas (SQLFlow 86.7→85.3, within noise). So the safe default
   is **A-atomic or S — same accuracy, fewer generations** — with unconstrained aggressive reuse the only
   config that ever *trends* negative. The intermediate **balanced** policy (join reuse kept, plus a
   base-table-containment lineage check on each reuse) likewise lands ≈ B within noise (e.g. CORDIS
   A-balanced 67.5 vs B 66.7); none of the reuse policies moves accuracy at this sample size — they differ
   only in generation cost. The atomic restriction is also harmless in the *heterogeneous* regime
   (spider2lite S-atomic ≈ B), where reuse barely fires at all.
4. **BEAVER** sits near the floor for every configuration (~3–5% EX) — too hard at this model scale to
   inform the accuracy question at all.

**The methodological takeaway is as important as the empirical one:** single-run EX deltas on ~40-question
splits are unreliable under LLM non-determinism, and a dramatic-looking single-run result (here, a clean
5–12-point complexity-aware Pareto frontier) can be entirely manufactured by noise. We report the
retraction rather than the headline. A genuine test of whether schema complexity erodes reuse safety
requires larger per-DB samples and multi-seed averaging; that is future work (§13).

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

The obstacle to Text-to-SQL over real warehouses is the **schema**: it does not fit in context, and
where it does, the model *loses the middle* of it. We address this by **decomposing** each question
into small, **execution-validated, explainable, debuggable** CTE sub-commands — *intermediate agentic
table views* — each constructed over a focused slice of the schema and then **composed** into the
answer. Decomposition-by-executable-views is what makes massive-schema, complex analytic Text-to-SQL
tractable: no giant schema is ever shown at once, no monolithic query is ever written blind, and every
intermediate step is checked and localizable. On top of this, because a CTE is a small self-contained
table, we collect a **dividend**: package each view as a *skill* with when/how-to-use context, keep a
**skill set** (cold-started from the schema before any question), and **reuse** rather than regenerate
overlapping CTEs — cutting token, rate-limit, and API cost on the batches of related queries that real
warehouses actually receive. To make reuse safe we contribute typed capability retrieval (backed by an
HNSW filtered index) and a four-layer defense against the bad hit, and we prove that a retrieval miss
is *graceful* — never worse than plain generation. Finally, we give an honest law for the dividend —
**savings ∝ question homogeneity** — so practitioners know exactly when the skill set pays. We believe
"decompose into executable agentic views, then reuse them as skills" is a productive new lens on
database-grounded language interfaces, and that its recall-safe decomposition, capability retrieval,
and negative-reuse defenses each open their own line of follow-on work.

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
