"""Zero-shot agents for SkiewSQL's retrieve-or-generate pipeline.

- Stage 1, `rewrite_question`: rewrite the question into a structured task, outputs, filters, and sort or limit specification.
- Stage 2, `propose_views`: plan reusable view subgoals for each schema chunk and return JSON schema selection J. The union of J becomes the filtered schema.
- Stage 2, `generate_view`: create one skill-driven CTE per subgoal with value-linking hints, execution validation, and source-table consistency.
- Stage 3, `planner`: create plan P over the chosen views, tables, joins, projections, groups, and ordering.
- Stage 3, `compose_final`: generate SQL from the selected views, filtered schema, plan P, and rewritten question.
- Repair and revision: repair execution errors and perform a final semantic verification pass.

The same agents are shared by the persistent-registry and no-memory runs."""
from __future__ import annotations
from skiewsql.prompt_loader import load_prompt

import hashlib
import json
import re
from typing import Callable, Dict, List, Optional, Tuple

from skiewsql.core import ViewSpec, ViewRequest
from skiewsql.llm import LLM, extract_json, extract_code

CATEGORIES = "SEL NORM AGG JOIN RANK WIN RESHAPE REC SET SEM".split()

CAT_HELP = load_prompt("agents/cat_help.txt")

_SHARED_RULES = load_prompt("agents/_shared_rules.txt")


# --------------------------------------------------------------------------- #
# Stage 1 — Question Rewriting (structured tuple, propagated downstream)
# --------------------------------------------------------------------------- #
REWRITE_SYS = load_prompt("agents/rewrite_sys.txt")
REWRITE_USER = load_prompt("agents/rewrite_user.txt")


REWRITE_USER_NOSCHEMA = load_prompt("agents/rewrite_user_noschema.txt")


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
PROPOSE_SYS = load_prompt("agents/propose_sys.txt")
PROPOSE_USER = load_prompt("agents/propose_user.txt")


# Appended to PROPOSE_USER when qualify_outputs=True (BEAVER path). Forces the proposer to commit to WHICH source column it means, so L1's subset test can reject a look-alike from the wrong table.
QUALIFY_OUTPUTS_RULE = load_prompt("agents/qualify_outputs_rule.txt")


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
DECOMPOSE_SYS = load_prompt("agents/decompose_sys.txt")
DECOMPOSE_USER = load_prompt("agents/decompose_user.txt")


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


ALIGN_SYS = load_prompt("agents/align_sys.txt")
ALIGN_USER = load_prompt("agents/align_user.txt")


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


NX1_RETRIEVAL_CONTRACT_SYS = load_prompt("agents/nx1_retrieval_contract_sys.txt")

NX1_RETRIEVAL_CONTRACT_USER = load_prompt("agents/nx1_retrieval_contract_user.txt")

_CATEGORY_OPERATOR = {
    "JOIN": "join", "AGG": "aggregate", "RANK": "window", "WIN": "window",
    "SET": "set", "REC": "recursive", "RESHAPE": "aggregate",
}
_CONTRACT_OPERATORS = {
    "filter", "project", "distinct", "join", "aggregate", "window", "set", "recursive",
}


def nx1_retrieval_contracts(llm: LLM, chunks_with_tables, rewrite_text: str,
                            tag_prefix: str = "") -> Tuple[Dict[str, ViewRequest], int, int]:
    """Return strict contracts keyed by the original N×1 chunk-request names. These contracts are only for registry lookup. Missing, uncertain, or malformed contracts are omitted so the caller bypasses retrieval and runs the original AV-SQL chunk generator unchanged. Returns the contracts, number of LLM calls, and number of fallbacks."""
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


DIFFICULTY_SYS = load_prompt("agents/difficulty_sys.txt")
DIFFICULTY_USER = load_prompt("agents/difficulty_user.txt")

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
    * moderate -> AV-SQL N×1: the full rewrite is sent to every schema chunk, with registry retrieve-or-generate applied by the caller to each request.
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


# AV-SQL-faithful per-chunk view generator (used in N×1 / v2m mode). This is an EXPLORATORY CTE over ONE schema chunk that extracts the columns/rows relevant to the question — a building block, NOT the final answer. The key rules that distinguish it from SkiewSQL's sub-goal generator (which forces required outputs and, on a single chunk, degenerates to NULL-padding + WHERE 1=0): no placeholders, use only columns present in this chunk, keep keys for later joins, and drop the chunk if irrelevant.
AV_VIEW_SYS = load_prompt("agents/av_view_sys.txt")
AV_VIEW_USER = load_prompt("agents/av_view_user.txt")


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
AV_SEL_SYS = load_prompt("agents/av_sel_sys.txt")
AV_SEL_USER = load_prompt("agents/av_sel_user.txt")


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
    """Generate at most one candidate skill view for a schema chunk.

    The SQL body may itself be a `WITH` program containing several dependent
    CTEs. In the paper that complete program is one validation and admission
    unit, so it becomes one ViewSpec rather than several independently reusable
    records. `taken(name)` is used only to avoid a registry-name collision.
    """
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

    steps = split_cte_chain(block, sql_dialect)
    complete_program = True
    try:
        sqlglot.parse_one(block, read=sql_dialect)
    except Exception:  # a declaration-only WITH block needs its final SELECT
        complete_program = False
    if steps and not complete_program:
        # The AV-SQL prompt permits a list of CTE declarations without a final
        # query. Complete the candidate by exposing its last internal CTE while
        # keeping the entire program inside one ViewSpec.
        block = block + f"\nSELECT * FROM {steps[-1][0]}"

    def unique(n):
        out = n
        i = 2
        while taken(out):
            out, i = f"{n}_{i}", i + 1
        return out

    # Keep the candidate exactly as generated. A nested WITH is legal as the
    # body of the outer named skill and lets validation execute every internal
    # CTE as one all-or-nothing program.
    spec = ViewSpec(
        name=unique(name), category="SEL", body_sql=block,
        source_tables=sorted(selection or {}), output_columns=[], grain=[],
        dialect=sql_dialect, description=rewrite_text[:200],
    )
    return [spec], selection, raw, block

# --------------------------------------------------------------------------- #
# Stage 2b — view generation (value-link aware) + execution/consistency repair
# --------------------------------------------------------------------------- #
GEN_SYS = load_prompt("agents/gen_sys.txt")
GEN_USER = load_prompt("agents/gen_user.txt")
EXISTING_VIEWS = load_prompt("agents/existing_views.txt")
DEPENDENCY_CONTRACT = load_prompt("agents/dependency_contract.txt")
VALUE_HINTS = load_prompt("agents/value_hints.txt")
PRIOR_ERROR = load_prompt("agents/prior_error.txt")


def generate_view(llm: LLM, schema: str, req: ViewRequest, existing_views: List[ViewSpec],
                  value_hints: Optional[List[str]] = None, prior_error: Optional[str] = None,
                  tag: str = "generate", reforce="") -> Optional[ViewSpec]:
    ex = ""
    if existing_views:
        lines = [f"- {v.name} ({v.category}): outputs {v.output_columns}" for v in existing_views]
        ex = EXISTING_VIEWS.format(views="\n".join(lines)).rstrip()
        if req.depends_on and not req.may_read_base_tables:
            ex += "\n" + DEPENDENCY_CONTRACT.rstrip()
    vh = VALUE_HINTS.format(hints="\n".join(value_hints)).rstrip() if value_hints else ""
    err = "\n" + PRIOR_ERROR.format(error=prior_error).rstrip() if prior_error else ""
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
PLAN_SYS = load_prompt("agents/plan_sys.txt")
PLAN_USER = load_prompt("agents/plan_user.txt")


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


COMPOSE_SYS = load_prompt("agents/compose_sys.txt")
COMPOSE_USER = load_prompt("agents/compose_user.txt")


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


DIRECT_SYS = load_prompt("agents/direct_sys.txt")
DIRECT_USER = load_prompt("agents/direct_user.txt")


def direct_sql(llm: LLM, schema: str, rewrite_text: str, question: str, evidence: str = "",
               tag: str = "direct") -> Optional[str]:
    ev = f"External knowledge: {evidence}" if evidence.strip() else ""
    txt = llm.ask(DIRECT_SYS, DIRECT_USER.format(schema=schema, rewrite=rewrite_text,
                  question=question, evidence=ev), tag=tag, max_tokens=700)
    sql = extract_code(txt, langs=("sql",))
    return sql.strip().rstrip(";") if sql else None


REVISE_SYS = load_prompt("agents/revise_sys.txt")
REVISE_USER = load_prompt("agents/revise_user.txt")


def revise_sql(llm: LLM, schema: str, question: str, evidence: str, sql: str, error: str,
               value_hints: Optional[List[str]] = None, tag: str = "revise") -> Optional[str]:
    ev = f"External knowledge: {evidence}" if evidence.strip() else ""
    vh = ("Value-linking hints:\n" + "\n".join(value_hints)) if value_hints else ""
    txt = llm.ask(REVISE_SYS, REVISE_USER.format(schema=schema, question=question, evidence=ev,
                  sql=sql, error=error, value_hints=vh), tag=tag, max_tokens=900)
    out = extract_code(txt, langs=("sql",))
    return out.strip().rstrip(";") if out else None


# NOTE: kept deliberately MILD. A more prescriptive "re-derive and check MIN/MAX, age, grain, ..." revisor was tested (task: self-consistency self-check) and HURT: it rewrote already-correct queries, and under result-set voting (--self_consistency>1) two such rewrites outvoted the correct original, dropping BIRD accuracy ~6pt. The lesson: a final revisor should correct only clear errors, not second-guess correct SQL. See PAPER §12.3 (third negative result).
SEM_SYS = load_prompt("agents/sem_sys.txt")
SEM_USER = load_prompt("agents/sem_user.txt")


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
VERIFY_SYS = load_prompt("agents/verify_sys.txt")
VERIFY_USER = load_prompt("agents/verify_user.txt")


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
CHOOSE_SYS = load_prompt("agents/choose_sys.txt")
CHOOSE_USER = load_prompt("agents/choose_user.txt")


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
DESCRIBE_SYS = load_prompt("agents/describe_sys.txt")
DESCRIBE_USER = load_prompt("agents/describe_user.txt")


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


TESTGEN_SYS = load_prompt("agents/testgen_sys.txt")
TESTGEN_USER = load_prompt("agents/testgen_user.txt")


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


EXTRACT_SYS = load_prompt("agents/extract_sys.txt")
EXTRACT_USER = load_prompt("agents/extract_user.txt")


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
