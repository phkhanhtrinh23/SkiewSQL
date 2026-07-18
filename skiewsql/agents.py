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
    "future questions over this database, and select the relevant tables/columns. Strict JSON only."
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
- NEVER bake a question-specific literal into the view name or body (no 'prague', no '2025',
  no 'eligible'). Those are `question_ops`, applied later.
- NEVER make the view a final scalar like a COUNT/SUM-of-everything. A "how many X in region R"
  question needs a reusable ROW-LEVEL cohort view (e.g. `accounts_with_district_and_loan_status`
  exposing account_id, district, status); the COUNT and the `region=R` filter happen in the final
  query. Good: `accounts_with_loan_status`. Bad: `accounts_in_prague_eligible_for_loans`.
- Expose stable id/key columns + the dimensions a filter/grouping would use; keep measures raw.

Return JSON:
{{
  "views": [
    {{"name": "snake_case_name", "category": "ONE OF {cats}",
      "description": "general NL description (for retrieval)",
      "required_outputs": ["exact_output_column_names"],
      "grain": ["key_columns_one_row_per"],
      "view_filters": {{"column": "value"}},
      "question_ops": ["year=2025", "order by total desc limit 1"],
      "source_tables": ["tables_used_from_this_chunk"]}}
  ],
  "schema_selection": {{"tables": ["relevant_tables"], "columns": ["table.column", "..."]}}
}}"""


def propose_views(llm: LLM, chunk_schema: str, rewrite_text: str, max_views: int = 3,
                  tag: str = "propose") -> Tuple[List[ViewRequest], List[Dict], Dict]:
    user = PROPOSE_USER.format(schema=chunk_schema, rewrite=rewrite_text, cat_help=CAT_HELP,
                               cats="/".join(CATEGORIES), max_views=max_views)
    txt = llm.ask(PROPOSE_SYS, user, tag=tag, max_tokens=1100)
    data = extract_json(txt) or {}
    reqs, raw = [], []
    for v in (data.get("views", []) or [])[:max_views]:
        cat = str(v.get("category", "")).upper().strip()
        name = str(v.get("name", "")).strip()
        if cat not in CATEGORIES or not name:
            continue
        reqs.append(ViewRequest(
            want_name=name, category=cat,
            required_outputs=[str(x) for x in v.get("required_outputs", [])],
            required_grain=[str(x) for x in v.get("grain", [])],
            required_filters={str(k): str(val) for k, val in (v.get("view_filters", {}) or {}).items()},
            text=str(v.get("description", name))))
        raw.append(v)
    sel = data.get("schema_selection", {}) or {}
    selection = {"tables": [str(x) for x in sel.get("tables", [])],
                 "columns": [str(x) for x in sel.get("columns", [])]}
    return reqs, raw, selection


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
                  tag: str = "generate") -> Optional[ViewSpec]:
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
        view_filters=req.required_filters, existing=ex, value_hints=vh, shared=_SHARED_RULES, error=err)
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
    return ViewSpec(
        name=req.want_name, category=req.category, body_sql=body,
        source_tables=[str(x) for x in (meta.get("source_tables") or [])],
        output_columns=outs, grain=[str(x) for x in (meta.get("grain") or req.required_grain)],
        semantic_filters={str(k): str(v) for k, v in (meta.get("semantic_filters")
                          or req.required_filters or {}).items()},
        depends_on=deps, description=req.text)


# --------------------------------------------------------------------------- #
# Stage 3 — planner, SQL generator, execution repair, semantic revisor
# --------------------------------------------------------------------------- #
PLAN_SYS = ("You are the Planner. Produce a short, concrete plan for the final SQL: which views/"
            "tables to use, the join keys, projections, filters, grouping, ordering and limit. "
            "Plain text, <=8 lines, no SQL.")
PLAN_USER = """Filtered schema (SQLite):
{schema}

Rewritten question:
{rewrite}

Available CTE views you may use:
{views}

Plan the final query:"""


def planner(llm: LLM, schema: str, rewrite_text: str, chosen: List[ViewSpec],
            tag: str = "plan") -> str:
    vs = "\n".join(f"- {v.name} (cols: {', '.join(v.output_columns)}) — {v.description}"
                   for v in chosen) or "(none — use base tables)"
    return llm.ask(PLAN_SYS, PLAN_USER.format(schema=schema, rewrite=rewrite_text, views=vs),
                   tag=tag, max_tokens=400)


COMPOSE_SYS = (
    "You are the SQL Generator. The listed views are ALREADY DEFINED as CTEs (do not redefine "
    "them). Following the plan, write ONLY the final SELECT that answers the question using those "
    "views and, if needed, base tables. Output one ```sql block.")
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
