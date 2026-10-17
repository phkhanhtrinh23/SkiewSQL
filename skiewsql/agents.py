"""Implement the zero-shot SQLite agents from AV-SQL with SkiewSQL's retrieve-or-generate view graph.

- Stage 1, `rewrite_question`: rewrite the question into a structured task, outputs, filters, and sort or limit specification.
- Stage 2, `propose_views`: plan reusable view subgoals for each schema chunk and return JSON schema selection J. The union of J becomes the filtered schema.
- Stage 2, `generate_view`: create one skill-driven CTE per subgoal with value-linking hints, execution validation, and source-table consistency.
- Stage 3, `planner`: create plan P over the chosen views, tables, joins, projections, groups, and ordering.
- Stage 3, `compose_final`: generate SQL from the selected views, filtered schema, plan P, and rewritten question.
- Repair and revision: repair execution errors and perform a final semantic verification pass.

The ONLY difference between SkiewSQL and the AV-SQL baseline is whether the view graph persists across questions — these agents are shared verbatim."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Callable, Dict, List, Optional, Tuple

from skiewsql.core import ViewSpec, ViewRequest
from skiewsql.llm import LLM, extract_json, extract_code

CATEGORIES = "SEL NORM AGG JOIN RANK WIN RESHAPE REC SET SEM".split()

CAT_HELP = (
    "SEL=row subset/cohort (WHERE filter). NORM=projection+cleaning (casts/NULL/canonicalize). "
    "AGG=grouped measures per key (GROUP BY rollup). JOIN=denormalized wide relation across tables. "
    "RANK=window rank (ROW_NUMBER/RANK: latest-per-key, top-k, dedup). WIN=ordered analytic window "
    "(running total, moving avg, LAG/LEAD). RESHAPE=pivot/unpivot (conditional aggregation). "
    "REC=recursive CTE (hierarchy/graph paths). SET=union/intersect/except cohort algebra. "
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


REWRITE_USER_NOSCHEMA = """Question: {question}
{evidence}

Restate the question as a precise task. Do NOT invent table/column names — describe the answer's
columns and constraints in the question's own terms (schema is attached later).

Return JSON:
{{"task": "one-sentence precise restatement of what to compute",
  "required_outputs": ["the columns/values the answer must contain"],
  "filters": ["explicit row constraints, with resolved literal values"],
  "sort_limit": "ordering and limit if any, else ''"}}"""


def rewrite_question(llm: LLM, schema: str, question: str, evidence: str = "",
                     tag: str = "rewrite") -> Tuple[Dict, str]:
    ev = f"External knowledge: {evidence}" if evidence.strip() else ""
    # Schema-free rewrite (the default now): restating a question as sub-goals is a purely logical step. Real tables are attached later by N×M alignment. Fall back to the schema-aware prompt only if a caller still passes a schema.
    if schema and schema.strip():
        user = REWRITE_USER.format(schema=schema, question=question, evidence=ev)
    else:
        user = REWRITE_USER_NOSCHEMA.format(question=question, evidence=ev)
    txt = llm.ask(REWRITE_SYS, user, tag=tag, max_tokens=400)
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
not `top_customer_2025`). Intrinsic concept-defining filters go in `view_filters`. Question-
specific selections (specific value, top-k, ordering) go in `question_ops` for the final query.
Also return the relevant tables/columns from this chunk (the schema selection).

Generalization rules (critical for reuse):
- NEVER bake a question-specific literal into the view name or body (no city name, no specific year,
  no 'eligible'). Those are `question_ops`, applied later.
- NEVER make the view a final scalar like a COUNT/SUM-of-everything. A "how many X in region R"
  question needs a reusable ROW-LEVEL cohort view (e.g. `accounts_with_district_and_loan_status`
  exposing account_id, district, status). The COUNT and the `region=R` filter happen in the final
  query. Good: `accounts_with_loan_status`. Bad: `accounts_in_<city>_eligible_for_loans`.
- Expose stable id/key columns + the dimensions a filter/grouping would use. Keep measures raw.

GRAIN rule (critical — decide it before you write anything else):
- `grain` is the exact schema key column(s) the view is ONE ROW PER. It MUST be real column names
  copied from the schema chunk above — never invent, never a description.
- Read the question for a grouping cue and set the grain to match what the answer needs:
    * "per / each / by / for every / average ... for each <X>" or any breakdown  -> grain is <X>'s
      key column(s). An aggregating (AGG) view MUST group at exactly this level, no coarser.
    * a single total/count/max over a cohort with no "per <X>"  -> keep a ROW-LEVEL view whose grain
      is the entity's key (do the final aggregate in `question_ops`), rather than pre-aggregating.
  Generic examples (not tied to any question): "goals per team" -> grain ["team_id"]. "Average price
  per category per month" -> grain ["category_id","month"]. "How many orders in 2020" -> row-level
  orders cohort, grain ["order_id"].
- If unsure, declare the FINER grain (more key columns). Over-declaring is safe: it only makes reuse
  miss and regenerate. Under-declaring silently reuses a wrongly-aggregated view.

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


# Appended to PROPOSE_USER when qualify_outputs=True (BEAVER path). Forces the proposer to commit to WHICH source column it means, so L1's subset test can reject a look-alike from the wrong table.
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
    """Majority-merge grain across samples: keep every key BASE declared, and ADD any key that a majority (>=2) of the matched sibling views also declared. Monotonic (never drops base keys) and biased to the FINER grain — the safe direction: it can only make reuse miss, never silently admit a wrongly-aggregated view. This is where an under-declared 'per team' key gets recovered."""
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
    # NOTE: samples default reverted to 1. The 3-sample grain self-consistency (task #14) was tested on BIRD+SQLFlow and REJECTED: it inflated sub-goals faster than it tightened grain, so reuse (and real negative reuse) rose (BIRD negFIXED 4->8, acc 41.7->40.0) at +24-48% tokens, with no gain on SQLFlow. Pass samples>1 only to reproduce that ablation. The grain prompt slot + cue-parse (suggestions 1-2) remain in the prompt — free and principled, though unproven in isolation.
    user = PROPOSE_USER.format(schema=chunk_schema, rewrite=rewrite_text, cat_help=CAT_HELP,
                               cats="/".join(CATEGORIES), max_views=max_views)
    if qualify_outputs:
        user += "\n\n" + QUALIFY_OUTPUTS_RULE
    # Self-consistency: sample the decomposition `samples` times. Grain errors are unstable across samples, so a per-view majority vote recovers the grain key a single pass under-declares.
    decomps: List[Dict] = []
    for _ in range(max(1, samples)):
        data = extract_json(llm.ask(PROPOSE_SYS, user, tag=tag, max_tokens=1300)) or {}
        if data.get("views"):
            decomps.append(data)
    if not decomps:
        return [], [], {"tables": [], "columns": []}
    # base = the decomposition proposing the most valid views (richest structure). Others vote on grain
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
    # schema selection: take the BASE sample only (do NOT union across samples — a broadened table set lets the generator write a much larger join and, on big local DBs, run away with no statement timeout). Self-consistency is applied to GRAIN, which is the actual fix. Selection stays as-was.
    sel = base.get("schema_selection", {}) or {}
    selection = {"tables": [str(x) for x in sel.get("tables", [])],
                 "columns": [str(x) for x in sel.get("columns", [])]}
    return reqs, raw, selection


# --------------------------------------------------------------------------- # Stage 2 (N×M variant) — global decomposition into M sub-goals, then align each sub-goal against every one of the N chunks (max-recall table gathering).
#
# vs propose_views: propose_views invents views chunk-by-chunk (each chunk blind to the others) and the caller truncates to max_views. Here we (1) decompose the question ONCE with a whole-DB table index in view -> M coherent, de-duplicated sub-goals, then (2) scan each sub-goal against each chunk to collect EVERY table relevant to it (the N×M loop). A sub-goal whose tables are split across chunks still gathers all of them, and there is no arbitrary cap on M. --------------------------------------------------------------------------- #
DECOMPOSE_SYS = (
    "You decompose a Text-to-SQL question into an ORDERED list of reusable intermediate relations "
    "(sub-goals) — the step-by-step plan to answer it. This is a PURELY LOGICAL decomposition of the "
    "QUESTION: you do NOT see the database schema and you do not need it. Real table/column names are "
    "attached LATER by an alignment step that scans each schema chunk. Build from the FINEST grain "
    "upward (events -> per-group aggregates -> filters/ranking). The LAST sub-goal only combines / "
    "filters the earlier ones. Declaring each sub-goal's row GRAIN precisely (the entity it is one row "
    "per) is critical, especially keys that must NOT be collapsed. Strict JSON only.")
DECOMPOSE_USER = """Decompose the question into at most {max_subgoals} ordered, reusable sub-goals.
Follow the STYLE of these examples (schema-free — describe relations to build, not tables):

EXAMPLE A
Question: Top 3 bowlers who, in the over with the most runs conceded in each match, gave up the highest
runs in a single over across all matches. Report the match for each.
Sub-goals:
  1. ball_events (JOIN) — one row per delivery with its runs (batsman runs + extras) and the bowler.
     grain: [match, innings, over, ball]
  2. over_runs (AGG) — total runs per over. grain: [match, innings, over]   (keep innings: an over is per-innings)
  3. match_max_over (AGG) — the maximum over-total within each match. grain: [match]
  4. top_bowler_overs (AGG) — overs whose total equals the match maximum, ordered by runs. grain: [match, innings, over, bowler]

EXAMPLE B
Question: Term code, subject title, room, floor, building key, street address, city, state, postal code,
formats and enrolled count for courses with more than 300 attendees.
Sub-goals:
  1. sections (SEL) — course sections with term, meet-place, enrollment count and format flags. grain: [section]
  2. course_titles (JOIN) — the title of each subject. grain: [subject, catalog_number]
  3. building_address (SEL) — street address, city, state, postal for each building. grain: [building]
  4. room_to_building (JOIN) — map a room / meet-place to its building and floor. grain: [room]

EXAMPLE C
Question: For each customer, total amount spent in 2023, only customers who spent over $1000.
Sub-goals:
  1. orders_2023 (SEL) — orders restricted to year 2023. grain: [order]
  2. spend_per_customer (AGG) — sum of amount per customer. grain: [customer]

EXAMPLE D
Question: Products that have never been ordered.
Sub-goals:
  1. ordered_products (SEL) — distinct product ids that appear in any order line. grain: [product]
  2. all_products (SEL) — every product. grain: [product]

Now decompose THIS question (rewritten):
{rewrite}

Categories: {cats}
{cat_help}

Rules:
- Each sub-goal = ONE responsibility (one category). Canonical snake_case name. GENERAL — no
  question-specific literals / top-k / ordering (those go in the final combine step, not a sub-goal).
- GRAIN = the key(s) the sub-goal is ONE ROW PER (logical names are fine). Prefer the FINER grain if
  unsure. Keep innings/entity keys that must not be collapsed.
- Never make a sub-goal a final scalar (a COUNT/SUM-of-everything). Keep row-level cohorts.
- Order sub-goals so any that another depends on comes first.
- Declare dependencies explicitly. A dependent sub-goal must consume the earlier relation instead of
  independently re-reading the same one-to-many base table. Set may_read_base_tables=false when its
  inputs are fully supplied by dependencies. State join keys and relationship so composition does not
  multiply rows or aggregate measures twice.

Return JSON:
{{"subgoals": [
  {{"name": "snake_case_name", "category": "ONE OF {cats}",
    "description": "general NL description of the relation this builds",
    "required_outputs": ["logical_output_column_names"],
    "grain": ["key_columns_one_row_per"],
    "view_filters": {{}},
    "depends_on": ["earlier_subgoal_names_or_empty"],
    "join_keys": ["keys_used_to_join_dependencies_or_empty"],
    "relationship": "one_to_one|many_to_one|aggregate_input|independent",
    "may_read_base_tables": true}}
]}}"""


def decompose_subgoals(llm: LLM, table_index: str, rewrite_text: str, max_subgoals: int = 6,
                       tag: str = "decompose", qualify_outputs: bool = False) -> List[ViewRequest]:
    """Schema-free decomposition: ONE call, question-only -> M ordered sub-goals. `table_index` is accepted for backward-compat but intentionally UNUSED — the decomposition is purely logical. The N×M alignment step attaches real tables per chunk afterward."""
    user = DECOMPOSE_USER.format(rewrite=rewrite_text, cat_help=CAT_HELP,
                                 cats="/".join(CATEGORIES), max_subgoals=max_subgoals)
    data = extract_json(llm.ask(DECOMPOSE_SYS, user, tag=tag, max_tokens=1500)) or {}
    reqs: List[ViewRequest] = []
    earlier_names = set()
    for v in (data.get("subgoals") or [])[:max_subgoals]:
        cat = str(v.get("category", "")).upper().strip()
        name = str(v.get("name", "")).strip()
        if cat not in CATEGORIES or not name:
            continue
        raw_base_access = v.get("may_read_base_tables", True)
        may_read_base = (raw_base_access if isinstance(raw_base_access, bool)
                         else str(raw_base_access).strip().lower() not in {"false", "0", "no"})
        reqs.append(ViewRequest(
            want_name=name, category=cat,
            required_outputs=[str(x) for x in (v.get("required_outputs") or [])],
            required_grain=[str(x) for x in (v.get("grain") or [])],
            required_filters={str(k): str(val) for k, val in (v.get("view_filters") or {}).items()},
            text=str(v.get("description", name)),
            source_tables=[str(x) for x in (v.get("source_tables") or [])],
            # Only earlier names are legal: this guarantees an acyclic logical plan even if the model emits a forward reference or self-cycle.
            depends_on=[str(x) for x in (v.get("depends_on") or []) if str(x) in earlier_names],
            join_keys=[str(x) for x in (v.get("join_keys") or [])],
            relationship=str(v.get("relationship", "") or ""),
            may_read_base_tables=may_read_base))
        earlier_names.add(name)
    # Effective filters through the dependency DAG (earlier subgoals are already complete).
    by_name = {}
    for r in reqs:
        inh = {}
        for d in r.depends_on:
            dep = by_name.get(d)
            if dep is not None:
                for k, v in {**dep.inherited_filters, **dep.required_filters}.items():
                    inh.setdefault(k, v)
        r.inherited_filters = {k: v for k, v in inh.items() if k not in r.required_filters}
        by_name[r.want_name] = r
    return reqs


ALIGN_SYS = (
    "You decide whether ONE schema chunk is relevant to ONE sub-goal, and if so which of THIS chunk's "
    "tables the sub-goal would draw on. Name only tables that appear verbatim in this chunk. If the "
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
    # last dot-segment = table name (BigQuery names are `project.dataset.table`. Bare names unaffected)
    return [str(x).split(".")[-1].strip("`\" ") for x in (data.get("tables") or [])]


def align_subgoals(llm: LLM, reqs: List[ViewRequest], chunks: List[str],
                   tag_prefix: str = "") -> Tuple[Dict[str, set], int]:
    """Align each sub-goal against every chunk (the N×M loop). Returns (per_subgoal_tables, n_align_calls)."""
    per: Dict[str, set] = {}
    n_calls = 0
    for req in reqs:
        tabs = {str(t).split(".")[-1].strip("`\" ") for t in (req.source_tables or [])}
        for ch in chunks:                                     # N chunks × this sub-goal = the N×M loop
            tabs |= set(align_subgoal_chunk(llm, req, ch, tag=(tag_prefix + "align")))
            n_calls += 1
        per[req.want_name] = {t for t in tabs if t}
    return per, n_calls


def chunk_has_table(chunk: str, table: str) -> bool:
    """True when the chunk defines `table`: a CREATE TABLE block, or AV-SQL's compact form (`Table: t` or a clustered table listed after `List of tables have same pattern ... :`)."""
    t = re.escape(table)
    if re.search(rf'CREATE\s+TABLE\s+[`"\[]?(?:[\w.]+\.)?{t}[`"\]]?\s*\(', chunk, re.IGNORECASE):
        return True
    if re.search(rf'(?m)\.\s*Table:\s*(?:[\w.]+\.)?{t}\s*$', chunk, re.IGNORECASE):
        return True
    return any(table.lower() in [n.strip().lower() for n in m.group(1).split(",")]
               for m in re.finditer(r'(?m)List of tables have same pattern .*? : (.*)$', chunk))


def decompose_and_align(llm: LLM, chunks: List[str], rewrite_text: str, table_index: str,
                        max_subgoals: int = 6, qualify_outputs: bool = False,
                        tag_prefix: str = "",
                        prefetch: Optional[Callable[[List[ViewRequest]], Dict[str, list]]] = None,
                        on_ungrounded: Optional[Callable[[str], None]] = None,
                        ) -> Tuple[List[ViewRequest], Dict[str, set], int]:
    """The N×M driver. M sub-goals decomposed globally, each aligned against all N chunks. Returns (reqs, per_subgoal_tables{name:set[str]}, n_align_calls).

    ``prefetch(reqs) -> {name: skill lineage tables}`` searches the skill registry BEFORE alignment. A hit is then GROUNDED: the sub-goal is aligned only against the chunks that hold the skill's lineage tables, and it is kept only if alignment selects every one of those tables. Otherwise ``on_ungrounded(name)`` is called and the sub-goal is aligned in full like a miss. Grounded hits cost one call per lineage chunk, so alignment is about N×(M−H) + H instead of N×M."""
    reqs = decompose_subgoals(llm, table_index, rewrite_text, max_subgoals=max_subgoals,
                              tag=(tag_prefix + "decompose"), qualify_outputs=qualify_outputs)
    hits = dict(prefetch(reqs) or {}) if prefetch is not None else {}
    by_name = {r.want_name: r for r in reqs}
    grounded: Dict[str, set] = {}
    n_ground = 0
    for name, lineage in hits.items():
        lin = {str(t).split(".")[-1].lower() for t in (lineage or [])}
        touched = [ch for ch in chunks if any(chunk_has_table(ch, t) for t in lin)]
        got: set = set()
        for ch in touched:
            got |= {t.lower() for t in align_subgoal_chunk(llm, by_name[name], ch, tag=(tag_prefix + "align"))}
            n_ground += 1
        if lin and touched and lin <= got:
            grounded[name] = got
        elif on_ungrounded is not None:
            on_ungrounded(name)
    per, n_calls = align_subgoals(llm, [r for r in reqs if r.want_name not in grounded], chunks, tag_prefix)
    per.update(grounded)
    return reqs, per, n_calls + n_ground


def nx1_requests(chunks_with_tables, rewrite_text: str) -> Tuple[List[ViewRequest], Dict[str, set]]:
    """AV-SQL-style N×1 (SkiewSQL v2m): exactly ONE whole-question view per schema CHUNK — no sub-goal decomposition. Each of the N chunks yields one ViewRequest whose text is the FULL rewritten question, aligned to that chunk's own tables (so the view is generated against the chunk's schema). Mirrors AV-SQL: k chunks -> k views (whole question each) -> compose. `chunks_with_tables`: list of (chunk_text, iterable_of_table_names). Returns (reqs, per_tables{name:set[str]})."""
    reqs: List[ViewRequest] = []
    per: Dict[str, set] = {}
    for j, (_ctext, tabs) in enumerate(chunks_with_tables):
        name = f"chunk_view_{j}"
        tabset = {str(t).split(".")[-1].strip('`" ') for t in (tabs or []) if str(t).strip()}
        reqs.append(ViewRequest(want_name=name, category="SEL", required_outputs=[],
                                required_grain=[], required_filters={}, text=rewrite_text,
                                source_tables=sorted(tabset), holistic=True))
        per[name] = tabset
    return reqs, per


NX1_RETRIEVAL_CONTRACT_SYS = (
    "You define a strict reusable-relation contract used only to search a stored skill registry. You see "
    "one schema chunk and the complete rewritten question. Describe one general relation when the chunk "
    "supports a clear reusable contract. Otherwise mark it uncertain. This decision never removes the "
    "chunk from fresh chunk-view generation. Output strict JSON only."
)

NX1_RETRIEVAL_CONTRACT_USER = """Schema chunk (SQLite):
{schema}

Rewritten question:
{rewrite}

Define one reusable intermediate relation that this chunk can provide. Do not describe the final answer. For example, a request for the department with the most degrees should ask for degree counts per department, not for only the winning department. Remove question-specific top-k, ordering, limits, and literal values unless a literal is intrinsic to the reusable concept.

Contract rules:
- Use one dominant category from {cats}.
- `required_outputs` lists every key, dimension, and measure the relation must expose.
- Qualify a base output as `table.column`. Keep a derived measure as its intended alias.
- `grain` is the exact key or keys that identify one output row. Use real qualified schema columns.
- `operators` lists every required relational operation from filter, project, distinct, join, aggregate, window, set, and recursive.
- `source_tables` contains only exact table names from this chunk.
- `view_filters` contains only intrinsic reusable filters. It is normally empty.
- A row-level relation must expose an entity key and declare that key as its grain.
- An aggregate relation must expose its group keys and measures and declare its group keys as its grain.

Return:
{{"relevant": true,
  "name": "canonical_snake_case_name",
  "category": "ONE OF {cats}",
  "description": "what one row means and when this relation is useful",
  "required_outputs": ["table.key", "derived_measure"],
  "grain": ["table.key"],
  "view_filters": {{}},
  "operators": ["join", "aggregate"],
  "source_tables": ["exact_table_name"]}}

If no safe and complete retrieval contract can be stated, return:
{{"relevant": false}}
"""

_CATEGORY_OPERATOR = {
    "JOIN": "join", "AGG": "aggregate", "RANK": "window", "WIN": "window",
    "SET": "set", "REC": "recursive", "RESHAPE": "aggregate",
}
_CONTRACT_OPERATORS = {
    "filter", "project", "distinct", "join", "aggregate", "window", "set", "recursive",
}


def nx1_retrieval_contracts(llm: LLM, chunks_with_tables, rewrite_text: str,
                            tag_prefix: str = "") -> Tuple[Dict[str, ViewRequest], int, int]:
    """Return strict contracts keyed by the original N×1 chunk-request names. These contracts are only for graph lookup. Missing, uncertain, or malformed contracts are omitted so the caller bypasses retrieval and runs the original AV-SQL chunk generator unchanged. Returns the contracts, number of LLM calls, and number of fallbacks."""
    contracts_by_name: Dict[str, ViewRequest] = {}
    calls = 0
    fallbacks = 0
    for j, (chunk_text, tabs) in enumerate(chunks_with_tables):
        name = f"chunk_view_{j}"
        table_names = [str(t).split(".")[-1].strip('`" ') for t in (tabs or []) if str(t).strip()]
        available = {t.lower(): t for t in table_names}
        user = NX1_RETRIEVAL_CONTRACT_USER.format(
            schema=chunk_text, rewrite=rewrite_text, cats="/".join(CATEGORIES))
        data = extract_json(llm.ask(
            NX1_RETRIEVAL_CONTRACT_SYS, user,
            tag=tag_prefix + "nx1_retrieval_contract", max_tokens=800)) or {}
        calls += 1
        if data.get("relevant") is False:
            fallbacks += 1
            continue
        category = str(data.get("category", "")).upper().strip()
        outputs = [str(x).strip() for x in (data.get("required_outputs") or []) if str(x).strip()]
        grain = [str(x).strip() for x in (data.get("grain") or []) if str(x).strip()]
        selected = []
        for raw in data.get("source_tables") or []:
            key = str(raw).split(".")[-1].strip('`" ').lower()
            if key in available and available[key] not in selected:
                selected.append(available[key])
        operators = []
        for raw in data.get("operators") or []:
            op = str(raw).lower().strip()
            if op in _CONTRACT_OPERATORS and op not in operators:
                operators.append(op)
        expected = _CATEGORY_OPERATOR.get(category)
        if expected and expected not in operators:
            operators.append(expected)
        contract_ok = category in CATEGORIES and bool(outputs) and bool(grain) and bool(selected)
        if contract_ok:
            relation_name = re.sub(
                r"[^a-z0-9_]", "", str(data.get("name", "")).strip().lower().replace(" ", "_"))
            description = str(data.get("description", "")).strip() or relation_name or name
            contracts_by_name[name] = ViewRequest(
                want_name=name,
                category=category,
                required_outputs=outputs,
                required_grain=grain,
                required_filters={
                    str(k): str(v) for k, v in (data.get("view_filters") or {}).items()
                },
                text=description,
                source_tables=selected,
                required_operators=operators,
            )
        else:
            fallbacks += 1
    return contracts_by_name, calls, fallbacks


DIFFICULTY_SYS = (
    "You route a rewritten Text-to-SQL question to one of three execution architectures. Judge "
    "SEMANTIC difficulty, not wording length and not join count alone. EASY means a direct query "
    "over at most two clearly identifiable tables, one output grain, and no dependent intermediate "
    "relations. A simple filter, lookup, COUNT, SUM, MIN, or MAX may still be easy. MODERATE means "
    "the complete question can be handled as one coherent plan (including ordinary joins, grouping, "
    "sorting, and top-k) without separately materializing relations at different grains. HARD means "
    "the answer needs dependent intermediate relations or multiple grains/cohorts: numerator versus "
    "denominator, nested aggregation, comparison with a group/global aggregate, window computation, "
    "set difference/intersection, recursion, correlated logic, or another multi-stage calculation. "
    "Be conservative: uncertain cases are MODERATE. Output strict JSON only."
)
DIFFICULTY_USER = """Available table names:
{tables}

Rewritten question:
{rewrite}

Return:
{{"difficulty": "easy|moderate|hard",
  "relevant_tables": ["exact_available_table_name"],
  "independent_grains": 1,
  "needs_dependent_relations": false,
  "operations": ["filter|join|aggregate|ratio|nested_aggregation|window|set_operation|recursive|correlated_subquery"],
  "confidence": 0.0,
  "reason": "short explanation"}}
"""

_HARD_OPERATIONS = {
    "ratio", "multiple_cohorts", "nested_aggregation", "window", "set_operation", "recursive",
    "correlated_subquery", "group_vs_global", "dependent_aggregation",
}


def classify_question_difficulty(llm: LLM, rewrite_text: str, available_tables,
                                 tag: str = "difficulty") -> Dict:
    """Return a conservative, schema-name-grounded routing decision. Easy is deliberately strict because a false easy decision bypasses the view pipeline.  Hard signals override the model's label. An incomplete/low-confidence response falls back to moderate, which runs the ordinary AV-SQL N×1 path."""
    tables = sorted({str(t).strip() for t in available_tables if str(t).strip()})
    raw = extract_json(llm.ask(
        DIFFICULTY_SYS,
        DIFFICULTY_USER.format(tables=", ".join(tables), rewrite=rewrite_text),
        tag=tag, max_tokens=500,
    )) or {}

    # Resolve case/qualification variants back to exact names supplied by the schema.
    lookup = {}
    for table in tables:
        lookup[table.lower()] = table
        lookup[table.split(".")[-1].strip('`" ').lower()] = table
    relevant = []
    for value in (raw.get("relevant_tables") or []):
        key = str(value).strip().strip('`"').lower()
        match = lookup.get(key) or lookup.get(key.split(".")[-1])
        if match and match not in relevant:
            relevant.append(match)

    label = str(raw.get("difficulty", "moderate")).strip().lower()
    operations = {str(x).strip().lower().replace(" ", "_")
                  for x in (raw.get("operations") or [])}
    try:
        grains = max(1, int(raw.get("independent_grains", 1)))
    except (TypeError, ValueError):
        grains = 1
    dependent_raw = raw.get("needs_dependent_relations", False)
    dependent = (dependent_raw if isinstance(dependent_raw, bool)
                 else str(dependent_raw).strip().lower() in {"true", "1", "yes"})
    try:
        confidence = float(raw.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    hard_signal = dependent or grains > 1 or bool(operations & _HARD_OPERATIONS)
    if label == "hard" or hard_signal:
        difficulty = "hard"
    elif label == "easy" and confidence >= 0.75 and 1 <= len(relevant) <= 2:
        difficulty = "easy"
    else:
        difficulty = "moderate"
    return {
        "difficulty": difficulty,
        "relevant_tables": relevant,
        "independent_grains": grains,
        "needs_dependent_relations": dependent,
        "operations": sorted(operations),
        "confidence": confidence,
        "reason": str(raw.get("reason", "")),
    }


def adaptive_requests(
        llm: LLM,
        chunks_with_tables,
        rewrite_text: str,
        table_index: str,
        render_selected: Callable[[set], str],
        estimate_tokens: Callable[[str], int],
        focused_budget: int,
        max_subgoals: int = 6,
        qualify_outputs: bool = False,
        tag_prefix: str = "",
        prefetch: Optional[Callable[[List[ViewRequest]], Dict[str, list]]] = None,
        on_ungrounded: Optional[Callable[[str], None]] = None,
) -> Tuple[List[ViewRequest], Dict[str, set], str, set, int]:
    """Route easy/moderate/hard questions to direct SQL, AV-SQL N×1, or dependency N×M. Returns ``(requests, per_request_tables, route, selected_tables, align_calls)``.

    * easy -> no view requests. The caller generates final SQL directly over selected tables.
    * moderate -> AV-SQL N×1: the full rewrite is sent to every schema chunk, with graph retrieve-or-generate applied by the caller to each request.
    * hard -> dependency-aware N×M subgoals. With ``prefetch`` the registry is searched per subgoal before alignment. Hits are grounded against their lineage chunks and only misses (or ungrounded hits) are aligned in full.

    ``render_selected``, ``estimate_tokens``, and ``focused_budget`` remain in the signature so old experiment commands keep working. Schema size no longer decides semantic question difficulty."""
    _ = (render_selected, estimate_tokens, focused_budget)
    chunks_with_tables = list(chunks_with_tables)
    all_tables = {str(t) for _text, tabs in chunks_with_tables for t in (tabs or []) if str(t).strip()}
    decision = classify_question_difficulty(
        llm, rewrite_text, all_tables, tag=(tag_prefix + "difficulty"))
    difficulty = decision["difficulty"]

    if difficulty == "easy":
        selected = set(decision["relevant_tables"])
        return [], {}, "direct_sql", selected, 0

    if difficulty == "moderate":
        reqs, per = nx1_requests(chunks_with_tables, rewrite_text)
        return reqs, per, "av_nx1", all_tables, 0

    chunk_texts = [text for text, _tabs in chunks_with_tables]
    subgoals, aligned, n_calls = decompose_and_align(
        llm, chunk_texts, rewrite_text, table_index, max_subgoals=max_subgoals,
        qualify_outputs=qualify_outputs, tag_prefix=tag_prefix, prefetch=prefetch,
        on_ungrounded=on_ungrounded)
    selected = set().union(*aligned.values()) if aligned else set()
    return subgoals, aligned, "dependency_nxm", selected, n_calls


# AV-SQL-faithful per-chunk view generator (used in N×1 / v2m mode). Ported from AV-SQL's CTE prompt (prompt_templates/schema_linking_cte_macsql.txt): an EXPLORATORY CTE over ONE schema chunk that extracts the columns/rows relevant to the question — a building block, NOT the final answer. The key rules that distinguish it from SkiewSQL's sub-goal generator (which forces required outputs and, on a single chunk, degenerates to NULL-padding + WHERE 1=0): no placeholders, use only columns present in this chunk, keep keys for later joins, and drop the chunk if irrelevant.
AV_VIEW_SYS = (
    "You are an experienced database expert. You are given ONE PART (a chunk) of a larger database "
    "schema and a question. Write a CTE body (a single SELECT) that pulls from THIS chunk the columns "
    "and rows that could help answer the question — an intermediate building-block view, NOT the final "
    "answer. Follow these rules strictly:\n"
    "1. Use ONLY tables and columns that appear in the provided chunk. Copy their names EXACTLY.\n"
    "2. NEVER invent a column, and NEVER pad with NULL/placeholders for columns that are not in this "
    "chunk. Do not write `WHERE 1=0`.\n"
    "3. The schema shown is INCOMPLETE — do NOT try to fully answer the question from this chunk. "
    "extracting the relevant pieces is enough (later chunks/base tables complete the answer).\n"
    "4. Keep primary-key / id / foreign-key columns so the view can be joined later.\n"
    "5. BIAS TOWARD INCLUSION: if any table in this chunk plausibly relates to ANY part of the "
    "question (an entity, filter, join key, or output it mentions), write a CTE selecting the relevant "
    "columns from it. When unsure whether a column is needed, include it — better too much than too "
    "little. Only reply with exactly IRRELEVANT (and no SQL) if NO table in this chunk relates to any "
    "part of the question at all.\n"
    "Output one ```sql block (the SELECT defining the CTE body, no WITH wrapper, no trailing semicolon) then "
    'one ```json block: {"output_columns": ["table.col", ...], "source_tables": ["table", ...]}.')
AV_VIEW_USER = ("Database schema chunk:\n{schema}\n\nQuestion: {question}\n{evidence}\n"
                "Target SQL dialect: {dialect}\n```sql\nSELECT ...\n```\n"
                '```json\n{{"output_columns": [], "source_tables": []}}\n```')


def av_view(llm: LLM, chunk_schema: str, rewrite_text: str, name: str, evidence: str = "",
            dialect: str = "", tag: str = "av_view") -> Optional[ViewSpec]:
    """Generate ONE AV-SQL-style exploratory CTE view for a single schema chunk. Returns None when the chunk is judged irrelevant (or nothing parseable was produced)."""
    ev = f"External knowledge: {evidence}" if (evidence or "").strip() else ""
    txt = llm.ask(AV_VIEW_SYS, AV_VIEW_USER.format(schema=chunk_schema[:24000], question=rewrite_text,
                  evidence=ev, dialect=dialect or "the target SQL dialect"), tag=tag, max_tokens=1200)
    if not txt:
        return None
    if "IRRELEVANT" in txt and "```" not in txt:
        return None
    body = extract_code(txt, langs=("sql", "cte"))
    if not body:
        return None
    body = body.strip().rstrip(";")
    meta = extract_json(txt) or {}
    srcs = [str(x) for x in (meta.get("source_tables") or [])]
    # NOTE: AV-SQL's exploratory CTE has NO strict output contract — the model's declared columns often list fields from tables outside its own SELECT, which the view validator would (wrongly) reject. Leave output_columns empty so a view is valid iff its CTE executes. The composer reads the CTE bodies directly.
    return ViewSpec(name=name, category="SEL", body_sql=body, source_tables=srcs,
                    output_columns=[], grain=[], description=rewrite_text[:200])



# AV-SQL view generation with a JSON schema selection (paper §4.3, Algorithm 1). The agent returns a CTE body plus J = {table: [columns] | "drop_all"} for the tables of its chunk. The caller validates each attempt (value retrieval on the CTE's literals, execution, rule-based CTE/JSON consistency) and feeds every problem back through `feedback` for the next attempt, up to T_max attempts.
AV_SEL_SYS = (
    "You are an experienced database expert. You are given ONE PART (a chunk) of a larger database "
    "schema and a question. You have two tasks.\n"
    "1. Write a CTE query that pulls from THIS chunk the columns and rows that could help answer the "
    "question: intermediate building blocks, NOT the final answer. Write either one SELECT, or several "
    "named CTEs in one WITH block (WITH name1 AS (...), name2 AS (...)) when it helps to build the "
    "information in steps or to keep separate parts apart. A later CTE may read an earlier one. Give each "
    "CTE a short descriptive name. Do not add a final SELECT after the WITH block.\n"
    "2. Write a JSON schema selection: for EVERY table of this chunk, either the list of its columns "
    "needed to answer the question, or \"drop_all\" if the table is irrelevant.\n"
    "Rules:\n"
    "- Use ONLY tables and columns that appear in the chunk. Copy their names EXACTLY. Never invent a "
    "column, never pad with NULL or placeholders, never write `WHERE 1=0`.\n"
    "- The schema shown is incomplete: do not try to fully answer the question from this chunk.\n"
    "- Keep primary-key / id / foreign-key columns so the view can be joined later.\n"
    "- When unsure whether a column is needed, include it: better too much than too little.\n"
    "- The JSON must be consistent with the CTE: every table and column the CTE uses (in SELECT, JOIN, "
    "WHERE, GROUP BY, ORDER BY) must be selected in the JSON. If every table is \"drop_all\", write NO CTE.\n"
    "Output one ```sql block (a single SELECT, or a WITH block of named CTEs; no trailing semicolon) "
    "and one ```json block: {\"think\": \"...\", \"<table>\": [\"col\", ...] or \"drop_all\", ...}. "
    "If the whole chunk is irrelevant, output only the ```json block with every table \"drop_all\".")
AV_SEL_USER = ("Database schema chunk:\n{schema}\n\nQuestion: {question}\n{evidence}\n"
               "Target SQL dialect: {dialect}\n{feedback}"
               "```sql\nSELECT ...\n```\nor\n```sql\nWITH name1 AS (SELECT ...),\nname2 AS (SELECT ... FROM name1 ...)\n```\n"
               "```json\n{{\"think\": \"...\", \"table_name\": [\"col\"] or \"drop_all\"}}\n```")


def _fmt_av_feedback(fb: Optional[Dict]) -> str:
    if not fb:
        return ""
    parts = ["\nYOUR PREVIOUS ATTEMPT HAD PROBLEMS. Fix them in this attempt.",
             f"Previous CTE:\n```sql\n{fb.get('cte') or '(none)'}\n```",
             f"Previous JSON selection: {json.dumps(fb.get('selection') or {})}"]
    if fb.get("error"):
        parts.append(f"Execution error: {fb['error']}")
    for msg in fb.get("consistency") or []:
        parts.append(f"Inconsistency: {msg}")
    if fb.get("values"):
        parts.append("Database values matching the literals you used (use the exact DB value):\n" + "\n".join(fb["values"]))
    return "\n".join(parts) + "\n\n"


def split_cte_chain(body: str, dialect: str = "sqlite") -> Optional[List[Tuple[str, "exp.Expression"]]]:
    """Split a chunk agent's ```sql block into its named CTEs, in order: [(cte_name, select_expression)].
    A block without WITH returns None (one plain SELECT). A WITH block may end without a final SELECT, as
    AV-SQL allows. A final SELECT that does more than `SELECT * FROM <cte>` is kept as one more step named
    "result". Returns None when the block does not parse."""
    import sqlglot
    from sqlglot import exp
    text = body.strip().rstrip(";")
    if not re.match(r"(?is)^\s*with\b", text):
        return None
    tree = None
    for candidate, sentinel in ((text, False), (text + "\nSELECT NULL AS __end__", True)):
        try:
            tree = sqlglot.parse_one(candidate, read=dialect)
            break
        except Exception:  # noqa: BLE001
            continue
    with_ = (tree.args.get("with_") or tree.args.get("with")) if tree is not None else None
    if with_ is None:
        return None
    steps = [(c.alias, c.this.copy()) for c in with_.expressions]
    final = tree.copy()
    final.set("with_" if "with_" in final.arg_types else "with", None)
    names = {n.lower() for n, _q in steps}
    trivial = ("__end__" in final.sql() or
               (isinstance(final, exp.Select) and len(final.expressions) == 1
                and isinstance(final.expressions[0], exp.Star) and final.args.get("where") is None
                and not final.args.get("joins") and final.find(exp.Table) is not None
                and final.find(exp.Table).name.lower() in names))
    if not trivial:
        steps.append(("result", final))
    return steps


def av_views_selected(llm: LLM, chunk_schema: str, rewrite_text: str, name: str, evidence: str = "",
                      dialect: str = "", feedback: Optional[Dict] = None, tag: str = "av_view",
                      taken: Optional[Callable[[str], bool]] = None
                      ) -> Tuple[List[ViewSpec], Optional[Dict[str, List[str]]], Optional[Dict], str]:
    """One AV-SQL view-generator call. The agent may write one SELECT or a WITH block of several named CTEs,
    as in AV-SQL. Each named CTE becomes its own view: one SELECT keeps the name `name`, a chain of k CTEs
    becomes `name_1` .. `name_k`, with references between them rewritten and recorded in `depends_on`.
    `taken(name)` says whether a view name is already used. Returns (views in order, selection {table: [columns]}
    without dropped tables, raw JSON or None when no JSON block was produced, the raw ```sql block)."""
    from sqlglot import exp
    ev = f"External knowledge: {evidence}" if (evidence or "").strip() else ""
    txt = llm.ask(AV_SEL_SYS, AV_SEL_USER.format(schema=chunk_schema[:24000], question=rewrite_text,
                  evidence=ev, dialect=dialect or "SQLite", feedback=_fmt_av_feedback(feedback)),
                  tag=tag, max_tokens=2400)
    raw = extract_json(txt or "")
    selection = None
    if isinstance(raw, dict):
        selection = {}
        for k, v in raw.items():
            if k == "think" or (isinstance(v, str) and v.strip().lower() == "drop_all"):
                continue
            if isinstance(v, list):
                selection[str(k)] = [str(c) for c in v]
    block = extract_code(txt or "", langs=("sql", "cte"))
    if not block:
        return [], selection, raw, ""
    block = block.strip().rstrip(";")
    taken = taken or (lambda _n: False)
    sql_dialect = (dialect or "sqlite").lower()

    def unique(n):
        out = n
        i = 2
        while taken(out):
            out, i = f"{n}_{i}", i + 1
        return out

    steps = split_cte_chain(block, sql_dialect)
    if not steps:                                          # one plain SELECT (or an unparsable block)
        body = block
        if re.match(r"(?is)^\s*with\b", body):             # a WITH wrapper sqlglot could not split
            m = re.search(r"(?is)\bas\s*\((.*)\)\s*(select\b.*)?$", body)
            if m and not (m.group(2) or "").strip():
                body = m.group(1).strip()
        return ([ViewSpec(name=unique(name), category="SEL", body_sql=body,
                          source_tables=sorted(selection or {}), output_columns=[], grain=[],
                          description=rewrite_text[:200])], selection, raw, block)
    if len(steps) == 1:                                    # a WITH wrapper around a single CTE
        return ([ViewSpec(name=unique(name), category="SEL", body_sql=steps[0][1].sql(dialect=sql_dialect),
                          source_tables=sorted(selection or {}), output_columns=[], grain=[],
                          description=rewrite_text[:200])], selection, raw, block)
    rename, specs = {}, []
    for k, (cte, q) in enumerate(steps, 1):
        new = unique(f"{name}_{k}")
        deps, base = [], []
        for t in q.find_all(exp.Table):
            old = t.name
            if old.lower() in rename and not t.args.get("db"):
                target = rename[old.lower()]
                if not t.args.get("alias"):                # keep `old.col` references working
                    t.set("alias", exp.TableAlias(this=exp.to_identifier(old)))
                t.set("this", exp.to_identifier(target))
                if target not in deps:
                    deps.append(target)
            elif old and old not in base:
                base.append(old)
        rename[cte.lower()] = new
        specs.append(ViewSpec(name=new, category="SEL", body_sql=q.sql(dialect=sql_dialect),
                              depends_on=deps, source_tables=sorted(base), output_columns=[], grain=[],
                              description=f"{cte} (step {k} of {len(steps)} for this chunk): {rewrite_text[:160]}"))
    return specs, selection, raw, block

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
Intrinsic view filters (apply these. Do NOT apply question-specific filters): {view_filters}
Declared dependency views: {declared_dependencies}
Dependency join keys: {join_keys}
Dependency relationship: {relationship}
May read base tables in addition to dependencies: {may_read_base_tables}

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
        if req.depends_on and not req.may_read_base_tables:
            ex += ("\nDEPENDENCY CONTRACT: SELECT from the declared views above. Do not re-read "
                   "their underlying base tables independently.")
    vh = ("Value-linking hints (use the exact DB values):\n" + "\n".join(value_hints)) if value_hints else ""
    err = f"\nThe previous attempt failed with:\n{prior_error}\nFix it." if prior_error else ""
    user = GEN_USER.format(
        schema=schema, name=req.want_name, category=req.category, description=req.text,
        required_outputs=req.required_outputs, grain=req.required_grain,
        view_filters=req.required_filters, declared_dependencies=req.depends_on,
        join_keys=req.join_keys, relationship=req.relationship or "unspecified",
        may_read_base_tables=req.may_read_base_tables,
        existing=ex, reforce=reforce, value_hints=vh, shared=_SHARED_RULES, error=err)
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
    if req.depends_on and not req.may_read_base_tables:
        # The logical planner made these mandatory. Include the closure even if the model omitted metadata. Validation will then compile the dependency CTEs with the candidate.
        deps = list(dict.fromkeys(deps + [d for d in req.depends_on
                                         if any(d == v.name for v in existing_views)]))
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


def _view_line(v: ViewSpec, reason: str = "") -> str:
    params = getattr(v, "params", {}) or {}
    line = f"- {v.name} (cols: {', '.join(v.output_columns)}, grain: {v.grain}) — {params.get('description') or v.description}"
    if reason:                                            # why this view is here, for THIS question only
        line += f"\n    why it is here: {reason}"
    if params.get("metric"):                              # notation -> planner grounds the measures
        line += f"\n    metric: {params['metric']}"
    if params.get("composition"):                         # skill JOIN-SAFETY contract -> planner
        line += f"\n    JOIN-SAFETY: {params['composition']}"
    return line


def planner(llm: LLM, schema: str, rewrite_text: str, chosen: List[ViewSpec],
            tag: str = "plan", reasons: Optional[Dict[str, str]] = None) -> str:
    vs = "\n".join(_view_line(v, (reasons or {}).get(v.name, "")) for v in chosen) or "(none — use base tables)"
    return llm.ask(PLAN_SYS, PLAN_USER.format(schema=schema, rewrite=rewrite_text, views=vs),
                   tag=tag, max_tokens=500)


COMPOSE_SYS = (
    "You are the SQL Generator. The listed views are ALREADY DEFINED as CTEs (do not redefine "
    "them). Following the plan, write ONLY the final SELECT that answers the question using those "
    "views and, if needed, base tables.\n"
    "PROJECTION DISCIPLINE (critical — the answer is compared column-by-column against the expected "
    "result):\n"
    "  - SELECT **exactly** the columns the question asks for, in the order asked, and NOTHING else. "
    "A reused view exposes many columns (keys, intermediate measures, descriptive attributes). Those "
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
                  chosen: List[ViewSpec], plan: str, tag: str = "compose",
                  reasons: Optional[Dict[str, str]] = None) -> Optional[str]:
    if not chosen:
        return None
    vs = "\n".join(f"- {v.name} (cols: {', '.join(v.output_columns)}) — {v.description}"
                   + (f"\n    why it is here: {(reasons or {})[v.name]}" if (reasons or {}).get(v.name) else "")
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


# NOTE: kept deliberately MILD. A more prescriptive "re-derive and check MIN/MAX, age, grain, ..." revisor was tested (task: self-consistency self-check) and HURT: it rewrote already-correct queries, and under result-set voting (--self_consistency>1) two such rewrites outvoted the correct original, dropping BIRD accuracy ~6pt. The lesson: a final revisor should correct only clear errors, not second-guess correct SQL. See PAPER §12.3 (third negative result).
SEM_SYS = ("You are the Revisor performing a final semantic check. Given a query that already "
           "executes, verify it truly answers the intent (correct columns, filters, aggregation, "
           "ordering/limit). If correct, return it unchanged. Otherwise return a corrected query. "
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
# Layer 3 — adversarial reuse verifier (skeptical. Guards against negative reuse)
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
# LLM reuse SELECTOR — the LLM (not embedding cosine) makes the final call over a candidate LIST: pick exactly one view to reuse, or NONE (generate fresh). Reject-biased: NONE is the safe default. Only reuse on a guaranteed match.
# --------------------------------------------------------------------------- #
CHOOSE_SYS = (
    "You decide whether ANY of a list of already-built SQL views can be safely REUSED to satisfy a "
    "new sub-goal, or whether a fresh view must be generated. Reusing a subtly-wrong view silently "
    "produces WRONG results, so you are strongly biased toward generating fresh: choosing NONE is "
    "ALWAYS the safe default. Reuse a candidate ONLY if you can guarantee it matches the sub-goal on "
    "ALL of: (1) intent/semantics, (2) required output columns are all exposed, (3) grain is exactly "
    "the same or strictly finer, (4) intrinsic filters/cohort match exactly (an all-rows view is NOT "
    "reusable for a filtered cohort, and vice-versa), (5) aggregation level matches (raw rows vs "
    "grouped measures), (6) any time-window matches, and (7) table lineage, column lineage and "
    "relational operators support the requested relation. If even one candidate criterion is uncertain, "
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
aggregation, table and column lineage, operator structure and time-window. Otherwise choose NONE and a fresh view will be generated. When in
doubt, choose NONE.
Return JSON only: {{"choice": "<candidate name>" | "NONE", "reason": "...", "confidence": 0.0-1.0}}"""


def _fmt_candidates(cands, notes: Optional[Dict[str, str]] = None) -> str:
    lines = []
    for c in cands:
        note = (notes or {}).get(c.name, "")
        body = (getattr(c, "body_sql", "") or "")[:300]
        params = getattr(c, "params", {}) or {}
        provenance = getattr(c, "provenance", {}) or {}
        # ENABLING skill contract (from skillify) — output schema + notation ground the columns so the selector reuses this view and composes on top of it. (No when-not/comparison: those suppress reuse. The whole point is that CTEs are reusable building blocks.)
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
            f"    intrinsic filters baked in: {c.semantic_filters}\n"
            f"    base-table lineage: {provenance.get('lineage', c.source_tables)}\n"
            f"    source columns: {provenance.get('source_columns', [])}\n"
            f"    output lineage: {provenance.get('output_lineage', {})}\n"
            f"    relational operators: {provenance.get('operators', [])}\n"
            f"    upstream skills: {provenance.get('upstream_skills', c.depends_on)}\n"
            f"    parameter bindings: {provenance.get('parameter_bindings', {})}"
            f"{skill}\n"
            + (f"    how it would be reused: {note}\n" if note else "")
            + f"    body: {body}")
    return "\n".join(lines)


def choose_reuse(llm: LLM, req, candidates, tag: str = "choose",
                 notes: Optional[Dict[str, str]] = None) -> Tuple[Optional[str], str, float]:
    """LLM picks ONE candidate view to reuse, or NONE (fresh). Reject-biased. Returns (chosen_name_or_None, reason, confidence). A choice is honored only if it names an actual candidate. Anything else (NONE, hallucinated name, unparseable) => None (generate fresh). ``notes`` (name -> text) explains a non-exact reuse mode (downstream filter, rollup, composition) and prior outcomes."""
    if not candidates:
        return None, "no candidates", 0.0
    names = {c.name for c in candidates}
    txt = llm.ask(CHOOSE_SYS, CHOOSE_USER.format(
        text=req.text, req_outputs=req.required_outputs, req_grain=req.required_grain,
        req_filters=req.required_filters, category=req.category,
        candidates=_fmt_candidates(candidates, notes)), tag=tag, max_tokens=350)
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


# --------------------------------------------------------------------------- #
# Skill registry — promotion description, generated validation tests, and extraction of a reusable relation from a final query
# --------------------------------------------------------------------------- #
DESCRIBE_SYS = (
    "You document a validated SQL view so it can be REUSED by later, different questions. Describe the "
    "RELATION the view computes (what one row is, what the columns mean, which rows it keeps), not the "
    "question that happened to create it. Name only columns and tables present in the SQL. State its "
    "limitations: situations where reusing it would give a wrong answer (grain, cohort/filter, "
    "aggregation, join path, time window). Output strict JSON only.")
DESCRIBE_USER = """View `{name}` (category {category})
Grain: {grain_kind} {grain}
Outputs: {outputs}
Intrinsic filters: {filters}
Aggregation per output: {aggregation}
Joins: {joins}
SQL:
{body}

Relevant schema:
{schema}

Return JSON:
{{"name": "general_snake_case_name_for_the_relation",
  "description": "one sentence: the relation this view computes (question-independent)",
  "when_to_use": ["kind of sub-goal it answers", "..."],
  "when_not_to_use": ["limitation + why reuse would be wrong", "..."]}}"""


def describe_skill(llm: LLM, spec: ViewSpec, schema: str = "", tag: str = "promote_describe") -> Dict:
    """Question-independent description, reuse guidance, and known limitations for a promoted view."""
    txt = llm.ask(DESCRIBE_SYS, DESCRIBE_USER.format(
        name=spec.name, category=spec.category, grain_kind=spec.grain_kind, grain=spec.grain,
        outputs=spec.output_columns, filters=spec.semantic_filters, aggregation=spec.aggregation,
        joins=spec.join_keys, body=(spec.body_sql or "")[:1600], schema=(schema or "")[:4000]),
        tag=tag, max_tokens=600)
    d = extract_json(txt) or {}

    def _join(k):
        v = d.get(k) or []
        return " | ".join(str(x) for x in v) if isinstance(v, list) else str(v)
    name = re.sub(r"[^a-z0-9_]", "", str(d.get("name", "")).strip().lower().replace(" ", "_"))
    return {"name": name if re.match(r"^[a-z][a-z0-9_]{2,60}$", name or "") else "",
            "description": str(d.get("description", "")).strip(),
            "when_to_use": _join("when_to_use"), "when_not_to_use": _join("when_not_to_use")}


TESTGEN_SYS = (
    "You write TEST QUERIES that check whether a SQL view really satisfies its contract. Each test is a "
    "single SQLite SELECT returning exactly ONE number: the count of rows that VIOLATE one property "
    "(0 means the property holds). Tests may read the view by its name and the base tables. Good "
    "properties: the view has no duplicate rows per its grain, every row satisfies its intrinsic "
    "filters, each measure reconciles with the same measure recomputed from the base tables, keys are "
    "not NULL, a join did not drop or duplicate entities. Do not test question-specific values. Output "
    "strict JSON only.")
TESTGEN_USER = """View `{name}` (category {category}) — {description}
Sub-goal it serves: {subgoal}
Grain: {grain_kind} {grain}
Outputs: {outputs}
Intrinsic filters: {filters}
Aggregation per output: {aggregation}
SQL body:
{body}

Relevant schema:
{schema}

Return up to 3 tests:
{{"tests": [{{"purpose": "what property it checks", "sql": "SELECT COUNT(*) FROM ... WHERE <violation>"}}]}}"""


def generate_view_tests(llm: LLM, spec: ViewSpec, subgoal: str = "", schema: str = "",
                        tag: str = "gen_tests") -> List[Dict]:
    txt = llm.ask(TESTGEN_SYS, TESTGEN_USER.format(
        name=spec.name, category=spec.category, description=spec.description, subgoal=subgoal or "(n/a)",
        grain_kind=spec.grain_kind, grain=spec.grain, outputs=spec.output_columns,
        filters=spec.semantic_filters, aggregation=spec.aggregation, body=(spec.body_sql or "")[:1600],
        schema=(schema or "")[:4000]), tag=tag, max_tokens=700)
    d = extract_json(txt) or {}
    tests = d.get("tests") or []
    return [t for t in tests if isinstance(t, dict) and t.get("sql")][:3]


EXTRACT_SYS = (
    "You decide whether a FINAL Text-to-SQL query contains a REUSABLE intermediate relation worth "
    "storing as a skill for future, different questions. Most final queries do NOT: they are one-off "
    "answers. Extract a relation only if it is a general building block (a cohort, a per-entity "
    "measure, a denormalized join) that other questions over this database are likely to need. When "
    "extracting: REMOVE every question-specific constant (specific names, ids, years, thresholds, "
    "top-k), ORDER BY, LIMIT, and final presentation (renaming, rounding, percentage scaling). Keep the "
    "keys needed to join or filter it later. Never return the final answer itself. Output strict JSON only.")
EXTRACT_USER = """Rewritten question:
{rewrite}
Original question: {question}

Final query (it executed):
```sql
{sql}
```

Views it could build on (already stored skills, reference them by name):
{views}

Return JSON:
{{"reusable": false, "reason": "..."}}
or
{{"reusable": true, "name": "general_snake_case_name", "category": "ONE OF {cats}",
  "description": "one sentence: the relation, question-independent",
  "removed_constants": ["constants you lifted out"],
  "body_sql": "SELECT ... (single SELECT, no WITH, no ORDER BY/LIMIT)"}}"""


def extract_reusable(llm: LLM, final_sql: str, rewrite_text: str, question: str,
                     views: List[ViewSpec], tag: str = "extract_final") -> Optional[Dict]:
    """Ask whether the final query holds a reusable relation. Returns the extraction dict or None."""
    vs = "\n".join(f"- {v.name} ({v.category}): {v.description}" for v in views) or "(none)"
    txt = llm.ask(EXTRACT_SYS, EXTRACT_USER.format(
        rewrite=rewrite_text, question=question, sql=(final_sql or "")[:4000], views=vs,
        cats="/".join(CATEGORIES)), tag=tag, max_tokens=900)
    d = extract_json(txt) or {}
    if not d.get("reusable") or not d.get("body_sql"):
        return None
    name = re.sub(r"[^a-z0-9_]", "", str(d.get("name", "")).strip().lower().replace(" ", "_"))
    cat = str(d.get("category", "SEL")).upper().strip()
    return {"name": name if re.match(r"^[a-z][a-z0-9_]{2,60}$", name or "") else "final_relation",
            "category": cat if cat in CATEGORIES else "SEL",
            "description": str(d.get("description", "")).strip(),
            "removed_constants": [str(x) for x in (d.get("removed_constants") or [])],
            "body_sql": str(d["body_sql"]).strip().rstrip(";")}


# Version stamp recorded in every skill's provenance: changes whenever a view-producing prompt changes.
PROMPT_VERSION = hashlib.sha1("\n".join([
    GEN_SYS, GEN_USER, _SHARED_RULES, AV_VIEW_SYS, AV_VIEW_USER, DECOMPOSE_SYS, DECOMPOSE_USER,
    DESCRIBE_SYS, TESTGEN_SYS, EXTRACT_SYS]).encode()).hexdigest()[:10]
