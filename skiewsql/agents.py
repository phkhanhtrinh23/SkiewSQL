"""
agents.py — the LLM agents, a faithful reimplementation of AV-SQL's stages with the
SkiewSQL twist that view generation is "retrieve-or-generate" against a persistent graph.

Faithful AV-SQL stages (all zero-shot, SQLite dialect):
  Stage 1  rewrite_question : Question Rewriting -> structured tuple <task, outputs, filters, sort/limit>
  Stage 2  propose_views    : per schema-chunk view planner -> reusable view sub-goals + JSON
                              schema selection J (tables/cols); union of J -> S_filtered.
           generate_view    : one skill-driven CTE per sub-goal, with value-linking hints +
                              execution validation + consistency (source tables subset of J).
  Stage 3  planner          : plan P (which views/tables, joins, projections, group/order).
           compose_final    : SQL generator over chosen views + S_filtered, given P + Q_rewrite.
           revise_sql       : execution-grounded repair (T_max loop, error feedback).
           semantic_revise  : final semantic verification pass (identity if correct, else edit).

The ONLY difference between SkiewSQL and the AV-SQL baseline is whether the view graph
persists across questions — these agents are shared verbatim.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from skiewsql.core import ViewSpec, ViewRequest
from skiewsql.llm import LLM, extract_json, extract_code

CATEGORIES = "SEL NORM AGG JOIN RANK WIN RESHAPE REC SET SEM".split()

CAT_HELP = (
    "SEL=row subset/cohort (WHERE filter); NORM=projection+cleaning (casts/NULL/canonicalize); "
    "AGG=grouped measures per key (GROUP BY rollup); JOIN=denormalized wide relation across tables; "
    "RANK=window rank (ROW_NUMBER/RANK: latest-per-key, top-k, dedup); WIN=ordered analytic window "
    "(running total, moving avg, LAG/LEAD); RESHAPE=pivot/unpivot (conditional aggregation); "
    "REC=recursive CTE (hierarchy/graph paths); SET=union/intersect/except cohort algebra; "
    "SEM=derived business rule from external knowledge."
)

_SHARED_RULES = """Construction rules for a reusable view (CTE body):
- Use ONLY tables/columns that appear verbatim in the schema. Copy names exactly.
- Carry the primary key / id of each source table into the output so the view stays joinable.
- One responsibility per view: do ONLY this category's operation.
- Lift question-specific literals (a specific year, country, name, k, LIMIT) OUT of the view —
  those belong in the final query, not the view. Keep only filters intrinsic to the concept.
- No final-answer projection, no ORDER BY / LIMIT, no comments. Valid SQLite only."""


# --------------------------------------------------------------------------- #
# Stage 1 — Question Rewriting (structured tuple, propagated downstream)
# --------------------------------------------------------------------------- #
REWRITE_SYS = (
    "You are the Question Rewriting stage of a Text-to-SQL system. Rewrite the question into "
    "an explicit, unambiguous specification, folding in any external knowledge and resolving "
    "underspecified references. Output strict JSON only."
)
REWRITE_USER = """Database schema (SQLite):
{schema}

Question: {question}
{evidence}

Return JSON:
{{"task": "one-sentence precise restatement of what to compute",
  "required_outputs": ["the columns/values the answer must contain"],
  "filters": ["explicit row constraints, with resolved literal values"],
  "sort_limit": "ordering and limit if any, else ''"}}"""


def rewrite_question(llm: LLM, schema: str, question: str, evidence: str = "",
                     tag: str = "rewrite") -> Tuple[Dict, str]:
    ev = f"External knowledge: {evidence}" if evidence.strip() else ""
    txt = llm.ask(REWRITE_SYS, REWRITE_USER.format(schema=schema, question=question, evidence=ev),
                  tag=tag, max_tokens=400)
    d = extract_json(txt) or {}
    parts = [f"Task: {d.get('task', question)}"]
    if d.get("required_outputs"):
        parts.append("Required outputs: " + "; ".join(map(str, d["required_outputs"])))
    if d.get("filters"):
        parts.append("Filters: " + "; ".join(map(str, d["filters"])))
    if d.get("sort_limit"):
        parts.append("Sort/limit: " + str(d["sort_limit"]))
    return d, "\n".join(parts)


# --------------------------------------------------------------------------- #
# Stage 2a — per-chunk view planner (+ JSON schema selection J)
# --------------------------------------------------------------------------- #
PROPOSE_SYS = (
    "You plan the reusable intermediate relations (agent views) for a Text-to-SQL view memory, "
    "looking at ONE chunk of the schema. Propose views that help answer THIS question AND likely "
    "future questions over this database, and select the relevant tables/columns. Declaring each "
    "view's row GRAIN precisely and grounded in real schema columns is critical: a later reuse guard "
    "compares a stored view's grain against the grain you declare here, so an under-declared grain "
    "silently admits a view aggregated at the wrong level. Strict JSON only."
)
PROPOSE_USER = """Schema chunk (SQLite):
{schema}

Rewritten question:
{rewrite}

View categories: {cat_help}

From THIS chunk, propose at most {max_views} reusable views (omit if this chunk is irrelevant:
return empty "views"). Make each view GENERAL: canonical name (e.g. `customer_yearly_spend`,
not `top_customer_2025`); intrinsic concept-defining filters go in `view_filters`; question-
specific selections (specific value, top-k, ordering) go in `question_ops` for the final query.
Also return the relevant tables/columns from this chunk (the schema selection).

Generalization rules (critical for reuse):
- NEVER bake a question-specific literal into the view name or body (no city name, no specific year,
  no 'eligible'). Those are `question_ops`, applied later.
- NEVER make the view a final scalar like a COUNT/SUM-of-everything. A "how many X in region R"
  question needs a reusable ROW-LEVEL cohort view (e.g. `accounts_with_district_and_loan_status`
  exposing account_id, district, status); the COUNT and the `region=R` filter happen in the final
  query. Good: `accounts_with_loan_status`. Bad: `accounts_in_<city>_eligible_for_loans`.
- Expose stable id/key columns + the dimensions a filter/grouping would use; keep measures raw.

GRAIN rule (critical — decide it before you write anything else):
- `grain` is the exact schema key column(s) the view is ONE ROW PER. It MUST be real column names
  copied from the schema chunk above — never invent, never a description.
- Read the question for a grouping cue and set the grain to match what the answer needs:
    * "per / each / by / for every / average ... for each <X>" or any breakdown  -> grain is <X>'s
      key column(s); an aggregating (AGG) view MUST group at exactly this level, no coarser.
    * a single total/count/max over a cohort with no "per <X>"  -> keep a ROW-LEVEL view whose grain
      is the entity's key (do the final aggregate in `question_ops`), rather than pre-aggregating.
  Generic examples (not tied to any question): "goals per team" -> grain ["team_id"]; "average price
  per category per month" -> grain ["category_id","month"]; "how many orders in 2020" -> row-level
  orders cohort, grain ["order_id"].
- If unsure, declare the FINER grain (more key columns). Over-declaring is safe: it only makes reuse
  miss and regenerate; under-declaring silently reuses a wrongly-aggregated view.

Return JSON:
{{
  "views": [
    {{"name": "snake_case_name", "category": "ONE OF {cats}",
      "description": "general NL description (for retrieval)",
      "answer_grain": "one row per ... (the grain the FINAL answer needs, in words)",
      "required_outputs": ["exact_output_column_names"],
      "grain": ["exact_schema_key_columns_one_row_per"],
      "view_filters": {{"column": "value"}},
      "question_ops": ["<literal filters>", "order by total desc limit 1"],
      "source_tables": ["tables_used_from_this_chunk"]}}
  ],
  "schema_selection": {{"tables": ["relevant_tables"], "columns": ["table.column", "..."]}}
}}"""


# Appended to PROPOSE_USER when qualify_outputs=True (BEAVER path). Forces the proposer to commit to
# WHICH source column it means, so L1's subset test can reject a look-alike from the wrong table.
QUALIFY_OUTPUTS_RULE = """OUTPUT-COLUMN QUALIFICATION (STRICT — overrides the generic `required_outputs` hint above):
- Every entry in `required_outputs` MUST be written as `table.column`, naming the EXACT base table
  AND column the answer needs — never a bare column, never a natural-language description.
- If the answer needs the department NAME, write `fac_organization.HR_DEPARTMENT_NAME`, not
  `department name` and not `fac_rooms.DEPT_CODE`. Committing to the source table lets the reuse
  guard reject a view exposing a same-named or look-alike column from the WRONG table.
- Use the real table names exactly as written in the schema chunk above."""


def _norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _view_outputs_sig(v: Dict) -> set:
    return {_norm_key(x) for x in (v.get("required_outputs") or []) if _norm_key(x)}


def _match_sibling(base: Dict, others: List[Dict]) -> Optional[Dict]:
    """Best-matching view from another sample: same category, max output-column overlap (>0)."""
    bcat = str(base.get("category", "")).upper()
    bsig = _view_outputs_sig(base)
    best, best_ov = None, 0
    for o in others:
        if str(o.get("category", "")).upper() != bcat:
            continue
        ov = len(bsig & _view_outputs_sig(o))
        if ov > best_ov:
            best, best_ov = o, ov
    return best


def _consensus_grain(base: Dict, samples: List[List[Dict]]) -> List[str]:
    """Majority-merge grain across samples: keep every key BASE declared, and ADD any key that a
    majority (>=2) of the matched sibling views also declared. Monotonic (never drops base keys) and
    biased to the FINER grain — the safe direction: it can only make reuse miss, never silently admit
    a wrongly-aggregated view. This is where an under-declared 'per team' key gets recovered."""
    grain = [str(x) for x in (base.get("grain") or [])]
    have = {_norm_key(g) for g in grain}
    freq: Dict[str, int] = {}
    display: Dict[str, str] = {}
    for other in samples:                                  # one matched sibling per other sample
        sib = _match_sibling(base, other)
        if not sib:
            continue
        for g in (sib.get("grain") or []):
            k = _norm_key(g)
            if not k:
                continue
            freq[k] = freq.get(k, 0) + 1
            display.setdefault(k, str(g))
    for k, c in freq.items():
        if c >= 2 and k not in have:                       # majority of siblings agreed, base missed it
            grain.append(display[k])
            have.add(k)
    return grain


def propose_views(llm: LLM, chunk_schema: str, rewrite_text: str, max_views: int = 3,
                  tag: str = "propose", samples: int = 1,
                  qualify_outputs: bool = False) -> Tuple[List[ViewRequest], List[Dict], Dict]:
    # NOTE: samples default reverted to 1. The 3-sample grain self-consistency (task #14) was tested on
    # BIRD+SQLFlow and REJECTED: it inflated sub-goals faster than it tightened grain, so reuse (and
    # real negative reuse) rose (BIRD negFIXED 4->8, acc 41.7->40.0) at +24-48% tokens, with no gain
    # on SQLFlow. Pass samples>1 only to reproduce that ablation. The grain prompt slot + cue-parse
    # (suggestions 1-2) remain in the prompt — free and principled, though unproven in isolation.
    user = PROPOSE_USER.format(schema=chunk_schema, rewrite=rewrite_text, cat_help=CAT_HELP,
                               cats="/".join(CATEGORIES), max_views=max_views)
    if qualify_outputs:
        user += "\n\n" + QUALIFY_OUTPUTS_RULE
    # Self-consistency: sample the decomposition `samples` times. Grain errors are unstable across
    # samples, so a per-view majority vote recovers the grain key a single pass under-declares.
    decomps: List[Dict] = []
    for _ in range(max(1, samples)):
        data = extract_json(llm.ask(PROPOSE_SYS, user, tag=tag, max_tokens=1300)) or {}
        if data.get("views"):
            decomps.append(data)
    if not decomps:
        return [], [], {"tables": [], "columns": []}
    # base = the decomposition proposing the most valid views (richest structure); others vote on grain
    base = max(decomps, key=lambda d: len(d.get("views") or []))
    other_view_lists = [d.get("views") or [] for d in decomps if d is not base]

    reqs, raw = [], []
    for v in (base.get("views", []) or [])[:max_views]:
        cat = str(v.get("category", "")).upper().strip()
        name = str(v.get("name", "")).strip()
        if cat not in CATEGORIES or not name:
            continue
        grain = _consensus_grain(v, other_view_lists)
        reqs.append(ViewRequest(
            want_name=name, category=cat,
            required_outputs=[str(x) for x in v.get("required_outputs", [])],
            required_grain=grain,
            required_filters={str(k): str(val) for k, val in (v.get("view_filters", {}) or {}).items()},
            text=str(v.get("description", name)),
            source_tables=[str(x) for x in (v.get("source_tables", []) or [])]))
        rv = dict(v); rv["grain"] = grain                  # reflect the merged grain in the raw record
        raw.append(rv)
    # schema selection: take the BASE sample only (do NOT union across samples — a broadened table set
    # lets the generator write a much larger join and, on big local DBs, run away with no statement
    # timeout). Self-consistency is applied to GRAIN, which is the actual fix; selection stays as-was.
    sel = base.get("schema_selection", {}) or {}
    selection = {"tables": [str(x) for x in sel.get("tables", [])],
                 "columns": [str(x) for x in sel.get("columns", [])]}
    return reqs, raw, selection


# --------------------------------------------------------------------------- #
# Stage 2 (N×M variant) — global decomposition into M sub-goals, then align each
# sub-goal against every one of the N chunks (max-recall table gathering).
#
# vs propose_views: propose_views invents views chunk-by-chunk (each chunk blind to the others) and the
# caller truncates to max_views. Here we (1) decompose the question ONCE with a whole-DB table index in
# view -> M coherent, de-duplicated sub-goals, then (2) scan each sub-goal against each chunk to collect
# EVERY table relevant to it (the N×M loop). A sub-goal whose tables are split across chunks still
# gathers all of them, and there is no arbitrary cap on M.
# --------------------------------------------------------------------------- #
DECOMPOSE_SYS = (
    "You decompose a Text-to-SQL question into the minimal set of reusable intermediate relations "
    "(sub-goals) needed to answer it. You see the FULL list of table names in the database (an index), "
    "so decompose with the whole schema in mind: no duplicate sub-goals, each a distinct reusable "
    "concept. Declaring each sub-goal's row GRAIN precisely (real key columns / the entity it is one "
    "row per) is critical: a later reuse guard compares a stored view's grain against it. Strict JSON "
    "only.")
DECOMPOSE_USER = """Database table index (every table in this DB):
{table_index}

Rewritten question:
{rewrite}

View categories: {cat_help}

Decompose into at most {max_subgoals} reusable sub-goals (fewer is better; only as many as the question
truly needs). Each sub-goal is ONE responsibility (one category). Make each GENERAL: canonical
snake_case name (e.g. `customer_yearly_spend`, not `top_customer_2025`); intrinsic concept-defining
filters only — question-specific literals / top-k / ordering are applied later in the final query, NOT
here. NEVER make a sub-goal a final scalar (a COUNT/SUM-of-everything); keep row-level cohorts. Order
sub-goals so any that another depends on comes first.

GRAIN rule: `grain` is the exact schema key column(s) the sub-goal is ONE ROW PER — real column names,
never a description. "per/each/by/for every <X>" -> grain is <X>'s key column(s). If unsure, declare the
FINER grain (more keys): over-declaring only makes reuse miss; under-declaring silently reuses a
wrongly-aggregated view.

Return JSON:
{{"subgoals": [
  {{"name": "snake_case_name", "category": "ONE OF {cats}",
    "description": "general NL description (for retrieval)",
    "required_outputs": ["exact_output_column_names"],
    "grain": ["exact_schema_key_columns_one_row_per"],
    "view_filters": {{"column": "value"}},
    "source_tables": ["tables_this_subgoal_likely_needs (names from the index)"]}}
]}}"""


def decompose_subgoals(llm: LLM, table_index: str, rewrite_text: str, max_subgoals: int = 6,
                       tag: str = "decompose", qualify_outputs: bool = False) -> List[ViewRequest]:
    """Global decomposition: one call, whole-DB table index in view -> M coherent sub-goals."""
    user = DECOMPOSE_USER.format(table_index=table_index, rewrite=rewrite_text, cat_help=CAT_HELP,
                                 cats="/".join(CATEGORIES), max_subgoals=max_subgoals)
    if qualify_outputs:
        user += "\n\n" + QUALIFY_OUTPUTS_RULE
    data = extract_json(llm.ask(DECOMPOSE_SYS, user, tag=tag, max_tokens=1500)) or {}
    reqs: List[ViewRequest] = []
    for v in (data.get("subgoals") or [])[:max_subgoals]:
        cat = str(v.get("category", "")).upper().strip()
        name = str(v.get("name", "")).strip()
        if cat not in CATEGORIES or not name:
            continue
        reqs.append(ViewRequest(
            want_name=name, category=cat,
            required_outputs=[str(x) for x in (v.get("required_outputs") or [])],
            required_grain=[str(x) for x in (v.get("grain") or [])],
            required_filters={str(k): str(val) for k, val in (v.get("view_filters") or {}).items()},
            text=str(v.get("description", name)),
            source_tables=[str(x) for x in (v.get("source_tables") or [])]))
    return reqs


ALIGN_SYS = (
    "You decide whether ONE schema chunk is relevant to ONE sub-goal, and if so which of THIS chunk's "
    "tables the sub-goal would draw on. Name only tables that appear verbatim in this chunk; if the "
    "chunk is irrelevant to the sub-goal, return an empty list. Strict JSON only.")
ALIGN_USER = """Schema chunk:
{schema}

Sub-goal:
- name: {name}   (category {category})
- meaning: {desc}
- required outputs: {outs}
- grain (one row per): {grain}

From THIS chunk ONLY, list the tables (verbatim names) this sub-goal needs. Empty list if none apply.
Return JSON: {{"tables": ["table", "..."]}}"""


def align_subgoal_chunk(llm: LLM, req: ViewRequest, chunk_schema: str, tag: str = "align") -> List[str]:
    """One (sub-goal × chunk) alignment probe: which of this chunk's tables the sub-goal needs."""
    user = ALIGN_USER.format(schema=chunk_schema, name=req.want_name, category=req.category,
                             desc=req.text, outs=req.required_outputs, grain=req.required_grain)
    data = extract_json(llm.ask(ALIGN_SYS, user, tag=tag, max_tokens=250)) or {}
    # last dot-segment = table name (BigQuery names are `project.dataset.table`; bare names unaffected)
    return [str(x).split(".")[-1].strip("`\" ") for x in (data.get("tables") or [])]


def decompose_and_align(llm: LLM, chunks: List[str], rewrite_text: str, table_index: str,
                        max_subgoals: int = 6, qualify_outputs: bool = False,
                        tag_prefix: str = "") -> Tuple[List[ViewRequest], Dict[str, set], int]:
    """The N×M driver. M sub-goals decomposed globally, each aligned against all N chunks.
    Returns (reqs, per_subgoal_tables{name:set[str]}, n_align_calls)."""
    reqs = decompose_subgoals(llm, table_index, rewrite_text, max_subgoals=max_subgoals,
                              tag=(tag_prefix + "decompose"), qualify_outputs=qualify_outputs)
    per: Dict[str, set] = {}
    n_calls = 0
    for req in reqs:
        tabs = {str(t).split(".")[-1].strip("`\" ") for t in (req.source_tables or [])}
        for ch in chunks:                                     # N chunks × this sub-goal = the N×M loop
            tabs |= set(align_subgoal_chunk(llm, req, ch, tag=(tag_prefix + "align")))
            n_calls += 1
        per[req.want_name] = {t for t in tabs if t}
    return reqs, per, n_calls


# --------------------------------------------------------------------------- #
# Stage 2b — view generation (value-link aware) + execution/consistency repair
# --------------------------------------------------------------------------- #
GEN_SYS = (
    "You build ONE reusable, executable SQL view (a CTE body) for a Text-to-SQL view memory. "
    "Output exactly one ```sql block (the SELECT defining the view body, no WITH wrapper) and "
    "one ```json block of metadata. Nothing else."
)
GEN_USER = """Database schema (SQLite):
{schema}

Build the view `{name}` (category {category}).
Meaning: {description}
Required output columns (alias EXACTLY to these names): {required_outputs}
Grain (one row per): {grain}
Intrinsic view filters (apply these; do NOT apply question-specific filters): {view_filters}

{existing}
{value_hints}
{shared}
{error}

Output the CTE body as a single SELECT (no `WITH`, no trailing `;`):
```sql
SELECT ...
```
Then metadata:
```json
{{"output_columns": ["..."], "source_tables": ["..."], "grain": ["..."],
  "semantic_filters": {{"column": "value"}}, "depends_on": ["existing_view_names_used_or_empty"]}}
```"""


def generate_view(llm: LLM, schema: str, req: ViewRequest, existing_views: List[ViewSpec],
                  value_hints: Optional[List[str]] = None, prior_error: Optional[str] = None,
                  tag: str = "generate", reforce="") -> Optional[ViewSpec]:
    ex = ""
    if existing_views:
        lines = [f"- {v.name} ({v.category}): outputs {v.output_columns}" for v in existing_views]
        ex = ("You MAY compose on these already-built views by selecting FROM them and listing "
              "them in depends_on (prefer this over re-reading base tables):\n" + "\n".join(lines))
    vh = ("Value-linking hints (use the exact DB values):\n" + "\n".join(value_hints)) if value_hints else ""
    err = f"\nThe previous attempt failed with:\n{prior_error}\nFix it." if prior_error else ""
    user = GEN_USER.format(
        schema=schema, name=req.want_name, category=req.category, description=req.text,
        required_outputs=req.required_outputs, grain=req.required_grain,
        view_filters=req.required_filters, existing=ex, reforce=reforce, value_hints=vh, shared=_SHARED_RULES, error=err)
    txt = llm.ask(GEN_SYS, user, tag=tag, max_tokens=1100)
    body = extract_code(txt, langs=("sql", "cte"))
    meta = extract_json(txt) or {}
    if not body:
        return None
    body = body.strip().rstrip(";")
    outs = [str(x) for x in (meta.get("output_columns") or req.required_outputs)]
    low = {o.lower() for o in outs}
    for r in req.required_outputs:
        if r.lower() not in low:
            outs.append(r)
    deps = [str(d) for d in (meta.get("depends_on") or []) if any(d == v.name for v in existing_views)]
    spec = ViewSpec(
        name=req.want_name, category=req.category, body_sql=body,
        source_tables=[str(x) for x in (meta.get("source_tables") or [])],
        output_columns=outs, grain=[str(x) for x in (meta.get("grain") or req.required_grain)],
        semantic_filters={str(k): str(v) for k, v in (meta.get("semantic_filters")
                          or req.required_filters or {}).items()},
        depends_on=deps, description=req.text)
    from skiewsql import sqlview                            # derive Φ/G from SQL (accurate guard)
    sqlview.enforce_contract(spec, "sqlite")
    return spec


# --------------------------------------------------------------------------- #
# Stage 3 — planner, SQL generator, execution repair, semantic revisor
# --------------------------------------------------------------------------- #
PLAN_SYS = ("You are the Planner. Produce a short, concrete plan for the final SQL: which views/"
            "tables to use, the join keys, projections, filters, grouping, ordering and limit. "
            "Each view may carry a JOIN-SAFETY contract (how to join it without duplicating its "
            "measures): OBEY it — use the stated safe join keys, and never join a view to a "
            "one-to-many relation without re-aggregating first, or its measures will be inflated. "
            "Plain text, <=8 lines, no SQL.")
PLAN_USER = """Filtered schema (SQLite):
{schema}

Rewritten question:
{rewrite}

Available CTE views you may use:
{views}

Plan the final query:"""


def _view_line(v: ViewSpec) -> str:
    params = getattr(v, "params", {}) or {}
    line = f"- {v.name} (cols: {', '.join(v.output_columns)}, grain: {v.grain}) — {params.get('description') or v.description}"
    if params.get("metric"):                              # notation -> planner grounds the measures
        line += f"\n    metric: {params['metric']}"
    if params.get("composition"):                         # skill JOIN-SAFETY contract -> planner
        line += f"\n    JOIN-SAFETY: {params['composition']}"
    return line


def planner(llm: LLM, schema: str, rewrite_text: str, chosen: List[ViewSpec],
            tag: str = "plan") -> str:
    vs = "\n".join(_view_line(v) for v in chosen) or "(none — use base tables)"
    return llm.ask(PLAN_SYS, PLAN_USER.format(schema=schema, rewrite=rewrite_text, views=vs),
                   tag=tag, max_tokens=500)


COMPOSE_SYS = (
    "You are the SQL Generator. The listed views are ALREADY DEFINED as CTEs (do not redefine "
    "them). Following the plan, write ONLY the final SELECT that answers the question using those "
    "views and, if needed, base tables.\n"
    "PROJECTION DISCIPLINE (critical — the answer is compared column-by-column against the expected "
    "result):\n"
    "  - SELECT **exactly** the columns the question asks for, in the order asked, and NOTHING else. "
    "A reused view exposes many columns (keys, intermediate measures, descriptive attributes); those "
    "are for computing the answer, NOT for returning. Do not pass an id/key through unless the "
    "question asks for it, and do not return an intermediate value (a total, an area, a denominator) "
    "just because you used it.\n"
    "  - If the question asks for one value ('what is the q1 time of X'), return ONE column.\n"
    "  - Use SELECT DISTINCT when the question asks for a set of distinct entities (e.g. 'the names "
    "of the races', 'which countries') and the joins could repeat rows.\n"
    "  - Do not rescale a ratio to a percentage unless the question says percent.\n"
    "Output one ```sql block.")
COMPOSE_USER = """Filtered schema (SQLite):
{schema}

Already-defined CTE views you can SELECT FROM (do NOT redefine):
{views}

Rewritten question:
{rewrite}
Original question: {question}
{evidence}

Plan:
{plan}

Write the final query as a single SELECT (it will be appended after the view definitions).
Apply question-specific filters / ordering / limit here. Use exact column names.
```sql
SELECT ...
```"""


def compose_final(llm: LLM, schema: str, rewrite_text: str, question: str, evidence: str,
                  chosen: List[ViewSpec], plan: str, tag: str = "compose") -> Optional[str]:
    if not chosen:
        return None
    vs = "\n".join(f"- {v.name} (cols: {', '.join(v.output_columns)}) — {v.description}"
                   for v in chosen)
    ev = f"External knowledge: {evidence}" if evidence.strip() else ""
    user = COMPOSE_USER.format(schema=schema, views=vs, rewrite=rewrite_text, question=question,
                               evidence=ev, plan=plan)
    txt = llm.ask(COMPOSE_SYS, user, tag=tag, max_tokens=900)
    sql = extract_code(txt, langs=("sql",))
    return sql.strip().rstrip(";") if sql else None


DIRECT_SYS = ("You are a Text-to-SQL generator for SQLite. Output one ```sql block with a single "
              "executable query. No explanation.")
DIRECT_USER = """Database schema (SQLite):
{schema}

Rewritten question:
{rewrite}
Original question: {question}
{evidence}

```sql
SELECT ...
```"""


def direct_sql(llm: LLM, schema: str, rewrite_text: str, question: str, evidence: str = "",
               tag: str = "direct") -> Optional[str]:
    ev = f"External knowledge: {evidence}" if evidence.strip() else ""
    txt = llm.ask(DIRECT_SYS, DIRECT_USER.format(schema=schema, rewrite=rewrite_text,
                  question=question, evidence=ev), tag=tag, max_tokens=700)
    sql = extract_code(txt, langs=("sql",))
    return sql.strip().rstrip(";") if sql else None


REVISE_SYS = ("You are the SQL revisor. Fix the SQLite query so it executes and answers the "
              "question. Output one corrected ```sql block only.")
REVISE_USER = """Database schema (SQLite):
{schema}

Question: {question}
{evidence}
{value_hints}
This query failed or may be wrong:
```sql
{sql}
```
Error / issue: {error}

Return the corrected single query:
```sql
SELECT ...
```"""


def revise_sql(llm: LLM, schema: str, question: str, evidence: str, sql: str, error: str,
               value_hints: Optional[List[str]] = None, tag: str = "revise") -> Optional[str]:
    ev = f"External knowledge: {evidence}" if evidence.strip() else ""
    vh = ("Value-linking hints:\n" + "\n".join(value_hints)) if value_hints else ""
    txt = llm.ask(REVISE_SYS, REVISE_USER.format(schema=schema, question=question, evidence=ev,
                  sql=sql, error=error, value_hints=vh), tag=tag, max_tokens=900)
    out = extract_code(txt, langs=("sql",))
    return out.strip().rstrip(";") if out else None


# NOTE: kept deliberately MILD. A more prescriptive "re-derive and check MIN/MAX, age, grain, ..."
# revisor was tested (task: self-consistency self-check) and HURT: it rewrote already-correct queries,
# and under result-set voting (--self_consistency>1) two such rewrites outvoted the correct original,
# dropping BIRD accuracy ~6pt. The lesson: a final revisor should correct only clear errors, not
# second-guess correct SQL. See PAPER §12.3 (third negative result).
SEM_SYS = ("You are the Revisor performing a final semantic check. Given a query that already "
           "executes, verify it truly answers the intent (correct columns, filters, aggregation, "
           "ordering/limit). If correct, return it unchanged; otherwise return a corrected query. "
           "Output one ```sql block only.")
SEM_USER = """Schema (SQLite):
{schema}

Rewritten question:
{rewrite}
Original question: {question}
{evidence}

Current query and a preview of its result:
```sql
{sql}
```
Result preview (first rows): {preview}

Return the verified/corrected single query:
```sql
SELECT ...
```"""


def semantic_revise(llm: LLM, schema: str, rewrite_text: str, question: str, evidence: str,
                    sql: str, preview: str, tag: str = "semantic") -> Optional[str]:
    ev = f"External knowledge: {evidence}" if evidence.strip() else ""
    txt = llm.ask(SEM_SYS, SEM_USER.format(schema=schema, rewrite=rewrite_text, question=question,
                  evidence=ev, sql=sql, preview=preview), tag=tag, max_tokens=900)
    out = extract_code(txt, langs=("sql",))
    return out.strip().rstrip(";") if out else None


# --------------------------------------------------------------------------- #
# Layer 3 — adversarial reuse verifier (skeptical; guards against negative reuse)
# --------------------------------------------------------------------------- #
VERIFY_SYS = (
    "You are a SKEPTICAL SQL view-reuse verifier. You are shown a STORED VIEW and a SUB-GOAL it is "
    "proposed to satisfy. Your job is to find any reason the view does NOT truly satisfy the "
    "sub-goal: a filter/cohort mismatch (e.g. all rows vs a filtered subset), a grain/granularity "
    "mismatch, an aggregation mismatch (raw rows vs aggregated), a time-window mismatch, or "
    "missing/renamed required outputs. Reusing a subtly-wrong view produces wrong SQL, so DEFAULT "
    "TO REJECT when uncertain. Output strict JSON only."
)
VERIFY_USER = """SUB-GOAL to satisfy:
- intent: {text}
- required outputs: {req_outputs}
- required grain (one row per): {req_grain}
- required intrinsic filters: {req_filters}

STORED VIEW `{name}` (category {category}):
- description / when-to-use: {desc}
- exposes outputs: {outputs}
- grain: {grain}
- intrinsic filters baked in: {filters}
- body: {body}
{counters}
Does the stored view TRULY satisfy the sub-goal with NO subtle mismatch (filter, grain,
aggregation, time-window, outputs)? Return JSON: {{"verdict": "REUSE" | "REJECT", "reason": "..."}}"""


def verify_reuse(llm: LLM, spec, req, counter_examples=None, tag: str = "verify") -> Tuple[bool, str]:
    """One skeptical verdict on whether `spec` may be reused for `req`. Returns (allow, reason)."""
    ce = ""
    if counter_examples:
        ce = ("\nThis view has previously been the WRONG choice for sub-goals like:\n- "
              + "\n- ".join(counter_examples[:4]) + "\nReject if the current sub-goal is similar.\n")
    body = (spec.body_sql or "")[:600]
    txt = llm.ask(VERIFY_SYS, VERIFY_USER.format(
        text=req.text, req_outputs=req.required_outputs, req_grain=req.required_grain,
        req_filters=req.required_filters, name=spec.name, category=spec.category,
        desc=spec.description, outputs=spec.output_columns, grain=spec.grain,
        filters=spec.semantic_filters, body=body, counters=ce), tag=tag, max_tokens=250)
    d = extract_json(txt) or {}
    verdict = str(d.get("verdict", "REJECT")).upper()
    return ("REUSE" in verdict and "REJECT" not in verdict), str(d.get("reason", ""))


# --------------------------------------------------------------------------- #
# LLM reuse SELECTOR — the LLM (not embedding cosine) makes the final call over
# a candidate LIST: pick exactly one view to reuse, or NONE (generate fresh).
# Reject-biased: NONE is the safe default; only reuse on a guaranteed match.
# --------------------------------------------------------------------------- #
CHOOSE_SYS = (
    "You decide whether ANY of a list of already-built SQL views can be safely REUSED to satisfy a "
    "new sub-goal, or whether a fresh view must be generated. Reusing a subtly-wrong view silently "
    "produces WRONG results, so you are strongly biased toward generating fresh: choosing NONE is "
    "ALWAYS the safe default. Reuse a candidate ONLY if you can guarantee it matches the sub-goal on "
    "ALL of: (1) intent/semantics, (2) required output columns are all exposed, (3) grain is exactly "
    "the same or strictly finer, (4) intrinsic filters/cohort match exactly (an all-rows view is NOT "
    "reusable for a filtered cohort, and vice-versa), (5) aggregation level matches (raw rows vs "
    "grouped measures), (6) any time-window matches. If even one candidate criterion is uncertain, "
    "or two candidates seem equally plausible, or nothing is clearly guaranteed — choose NONE. Do "
    "NOT reuse merely because a view is topically related or shares table names. Output strict JSON only."
)
CHOOSE_USER = """NEW SUB-GOAL to satisfy:
- intent: {text}
- required outputs (must ALL be exposed): {req_outputs}
- required grain (one row per): {req_grain}
- required intrinsic filters/cohort: {req_filters}
- category: {category}

CANDIDATE VIEWS already in the graph (you may reuse AT MOST ONE, exactly as-is):
{candidates}

Decide. Reuse a candidate only if it is a GUARANTEED match on intent, outputs, grain, filters,
aggregation and time-window; otherwise choose NONE and a fresh view will be generated. When in
doubt, choose NONE.
Return JSON only: {{"choice": "<candidate name>" | "NONE", "reason": "...", "confidence": 0.0-1.0}}"""


def _fmt_candidates(cands) -> str:
    lines = []
    for c in cands:
        body = (getattr(c, "body_sql", "") or "")[:300]
        params = getattr(c, "params", {}) or {}
        # ENABLING skill contract (from skillify) — output schema + notation ground the columns so
        # the selector reuses this view and composes on top of it. (No when-not/comparison: those
        # suppress reuse; the whole point is that CTEs are reusable building blocks.)
        skill = ""
        if params.get("output_schema"):
            skill += f"\n    output schema: {params['output_schema']}"
        if params.get("grounded_columns"):
            skill += f"\n    grounded columns: {params['grounded_columns']}"
        if params.get("metric"):
            skill += f"\n    metric: {params['metric']}"
        lines.append(
            f"- name: {c.name} (category {c.category})\n"
            f"    when-to-use: {params.get('when_to_use') or c.description}\n"
            f"    exposes outputs: {c.output_columns}\n"
            f"    grain: {c.grain}\n"
            f"    intrinsic filters baked in: {c.semantic_filters}"
            f"{skill}\n"
            f"    body: {body}")
    return "\n".join(lines)


def choose_reuse(llm: LLM, req, candidates, tag: str = "choose") -> Tuple[Optional[str], str, float]:
    """LLM picks ONE candidate view to reuse, or NONE (fresh). Reject-biased.
    Returns (chosen_name_or_None, reason, confidence). A choice is honored only if it names an
    actual candidate; anything else (NONE, hallucinated name, unparseable) => None (generate fresh)."""
    if not candidates:
        return None, "no candidates", 0.0
    names = {c.name for c in candidates}
    txt = llm.ask(CHOOSE_SYS, CHOOSE_USER.format(
        text=req.text, req_outputs=req.required_outputs, req_grain=req.required_grain,
        req_filters=req.required_filters, category=req.category,
        candidates=_fmt_candidates(candidates)), tag=tag, max_tokens=350)
    d = extract_json(txt) or {}
    choice = str(d.get("choice", "NONE")).strip()
    reason = str(d.get("reason", ""))
    try:
        conf = float(d.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    if choice in names and choice.upper() != "NONE":
        return choice, reason, conf
    return None, reason or "NONE", conf
