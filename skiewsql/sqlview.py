"""sqlview.py — the persistent view-memory layer for the *real* pipeline. Reuses the graph primitives from core.py (ViewSpec, ViewGraph, compose_sql) but adds:
  * embedding-based retrieval (OpenAI embeddings via llm.Embedder) with the compatibility contract (the negative-reuse guard).
  * execution-grounded validation against a real SQLite connection (case-insensitive output-column check, dependency closure).
  * JSON persistence of one graph per db_id (so the library survives across runs).

A node `v = <skill s, db D, CTE, contract, inputs, outputs, validation>` is exactly the ViewSpec dataclass. DEPENDS_ON (view->view) and READS_TABLE (view->table) edges are derived from the ViewSpec fields in the ViewGraph."""
from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

import networkx as nx

from skiewsql.core import ViewSpec, ViewGraph, ViewRequest, compose_sql
from skiewsql.llm import Embedder


# --------------------------------------------------------------------------- #
# Compatibility contract (negative-reuse guard) — robust to case / naming
# --------------------------------------------------------------------------- #
def _lower_set(xs) -> set:
    return {str(x).strip().lower() for x in xs}


def _norm_name(x: str) -> str:
    """Column-name key: lowercase, alphanumerics only (so `CountryCode`, `country_code`, `country code` all match). Absorbs the proposer's run-to-run alias-format variance and the raw-vs-canonical gap between online agents and the cold-start seed generator."""
    s = str(x).strip().lower()
    # drop an inline comment (grain keys sometimes carry `Code /* one row per country */`)
    s = s.split("/*", 1)[0].split("--", 1)[0]
    return "".join(ch for ch in s if ch.isalnum())


def _norm_set(xs) -> set:
    return {_norm_name(x) for x in xs if _norm_name(x)}


# --------------------------------------------------------------------------- #
# Contract derivation from the SQL body (so the L1 guard has ACCURATE Φ/G, instead of trusting the model's self-report). Upstream, no runtime LLM.
# --------------------------------------------------------------------------- #
import sqlglot                                             # noqa: E402
from sqlglot import expressions as _sx                     # noqa: E402


def _col_name(e) -> str:
    """Readable column key for a GROUP BY / predicate operand."""
    if isinstance(e, _sx.Column):
        return e.name
    try:
        return e.sql()
    except Exception:  # noqa: BLE001
        return str(e)


def _split_and(cond):
    """Flatten a top-level AND tree into conjuncts (ignore OR — too complex to be safe)."""
    if isinstance(cond, _sx.And):
        return _split_and(cond.left) + _split_and(cond.right)
    return [cond]


def _simple_pred(cond):
    """Return (col, value) for a *cohort-defining* filter, else None. Two kinds are recorded:
    - equality to a literal (status='completed', type='X', …): value is the bare literal.
    - a one-sided (semi-interval) NUMERIC inequality (col < c, col >= c, …): value is the operator-prefixed literal, e.g. ">=2020". These are matched by ray-containment in `compatible` (MiniCon's semi-interval reuse), so a view filtered to a looser ray can be reused for a query needing a tighter same-direction ray. `IS [NOT] NULL` stays excluded as hygiene. Non-numeric inequalities (date-as-string, etc.) are skipped too — they can't be safely ordered here, so we leave them out (a safe miss)."""
    if isinstance(cond, _sx.EQ) and isinstance(cond.left, _sx.Column):
        r = cond.right
        if isinstance(r, _sx.Literal):
            return _col_name(cond.left), r.name
        if isinstance(r, _sx.Boolean):
            return _col_name(cond.left), str(r.this).lower()
    for cls, op in ((_sx.GTE, ">="), (_sx.LTE, "<="), (_sx.GT, ">"), (_sx.LT, "<")):
        if isinstance(cond, cls) and isinstance(cond.left, _sx.Column):
            r = cond.right
            if isinstance(r, _sx.Literal) and not r.is_string:       # numeric literal only
                return _col_name(cond.left), f"{op}{r.name}"
    return None


# --- semi-interval (one-sided range) matching --------------------------------- #
_ORD_OPS = ("<=", ">=", "<", ">")


def _is_range(v) -> bool:
    return isinstance(v, str) and v.strip().startswith(_ORD_OPS)


def _parse_ineq(v: str):
    v = v.strip()
    for op in ("<=", ">=", "<", ">"):        # longest first
        if v.startswith(op):
            try:
                return op, float(v[len(op):].strip())
            except Exception:  # noqa: BLE001
                return None
    return None


def _ray_contains(view_v: str, query_v: str) -> bool:
    """True iff the VIEW's ray ⊇ the QUERY's ray (same direction): the view then holds every row the query needs, and the query's tighter bound is re-applied downstream — MiniCon-sound reuse."""
    pv, pq = _parse_ineq(view_v), _parse_ineq(query_v)
    if not pv or not pq:
        return False
    ov, tv = pv
    oq, tq = pq
    lower, upper = {">", ">="}, {"<", "<="}
    if ov in lower and oq in lower:
        return tv <= tq                       # [tv,∞) ⊇ [tq,∞)
    if ov in upper and oq in upper:
        return tv >= tq                       # (-∞,tv] ⊇ (-∞,tq]
    return False                              # opposite directions can't nest


def derive_contract(body_sql: str, dialect: str = "sqlite"):
    """Parse the view body and read the OUTERMOST WHERE → intrinsic filters Φ, and GROUP BY → grain G. Returns (filters_dict, grain_list). Either may be empty. Best-effort — never raises."""
    try:
        tree = sqlglot.parse_one(body_sql, read=dialect)
    except Exception:  # noqa: BLE001
        return {}, []
    sel = tree if isinstance(tree, _sx.Select) else (tree.find(_sx.Select) if tree else None)
    if sel is None:
        return {}, []
    # grain from GROUP BY, resolved to OUTPUT ALIASES so it matches the vocabulary sub-goals request
    grain = []
    grp = sel.args.get("group")
    if grp is not None:
        proj = {}                                          # underlying-expr sql -> output alias/name
        for e in sel.expressions:
            if isinstance(e, _sx.Alias):
                proj[e.this.sql()] = e.alias
            elif isinstance(e, _sx.Column):
                proj[e.sql()] = e.name
        for e in grp.expressions:
            if isinstance(e, _sx.Column):
                grain.append(e.name)
            else:
                grain.append(proj.get(e.sql(), e.sql()))   # alias if this expr is a SELECT column
        grain = [g for g in grain if g]
    filters = {}
    where = sel.args.get("where")
    if where is not None:
        for cond in _split_and(where.this):
            kv = _simple_pred(cond)
            if kv:
                filters[kv[0]] = kv[1]
    return filters, grain


def enforce_contract(spec, dialect: str = "sqlite") -> None:
    """Correct a ViewSpec's Φ/G in place from its SQL. GROUP BY is authoritative for grain. SQL-read intrinsic filters are UNIONed into Φ (catching filters the model forgot to declare). Over-declaring biases toward safe *misses*, never toward silent bad hits."""
    f, g = derive_contract(spec.body_sql or "", dialect)
    if g:                                                  # explicit GROUP BY -> authoritative grain
        spec.grain = g
    if f:
        merged = dict(spec.semantic_filters or {})
        for k, v in f.items():
            merged.setdefault(k, v)                        # SQL fills in what the model missed
        spec.semantic_filters = {str(k): str(v) for k, v in merged.items()}


# Whether to refuse a single-table projection as a reuse hit. DEFAULT OFF: the ablation (task #13) showed blocking these inert views drove the (mislabelled) negative-reuse count to ~0 but RAISED generations +16–35% and tokens +9–13% with no accuracy gain (BIRD even dropped) — because reusing a base projection genuinely saves a generate call and keeps column vocabulary consistent. So we KEEP trivial reuse and instead fix the metric (count only non-trivial reuse as negative). The knob stays available for reproducing the ablation: set SKIEW_BLOCK_TRIVIAL=1 to re-enable the block.
_SKIP_TRIVIAL_REUSE = os.environ.get("SKIEW_BLOCK_TRIVIAL") == "1"
_AGG_FN = re.compile(r"\b(count|sum|avg|min|max|row_number|rank|dense_rank|ntile|lag|lead)\s*\(")


def is_trivial_projection(spec: ViewSpec) -> bool:
    """True if the view is `SELECT <cols> FROM <one table>` with no filter/join/aggregation/window — reusing it is causally inert. Best-effort textual check. Never raises."""
    b = re.sub(r"\s+", " ", (getattr(spec, "body_sql", "") or "").lower()).strip()
    if not b or getattr(spec, "semantic_filters", None):
        return False
    if " join " in b or " where " in b or " group by " in b or " union " in b or " having " in b:
        return False
    if _AGG_FN.search(b):
        return False
    return b.count(" from ") == 1


def _reuse_blocked(spec: ViewSpec) -> bool:
    return _SKIP_TRIVIAL_REUSE and is_trivial_projection(spec)


# Complexity-aware reuse policy (task: adaptive reuse). On complex domain-specific schemas, reusing a join/aggregation view is the dominant source of negative reuse (wrong join path / wrong grain that still executes). `SKIEW_REUSE_POLICY`: aggressive (default): reuse any guard-compatible view (current behaviour). atomic: reuse ONLY atomic views (a SEL/NORM selection with no join or aggregation) — regenerate every join/aggregation fresh. Preserves most cost saving while removing the risky reuse. balanced: like aggressive but additionally require base-table containment (view's tables ⊆ the sub-goal's tables) — cheap lineage check against "right columns, wrong base tables". atomic implies the base-table check too.
_REUSE_POLICY = os.environ.get("SKIEW_REUSE_POLICY", "aggressive").lower()
_ATOMIC_CATS = {"SEL", "NORM"}


def set_reuse_policy(policy: str) -> None:
    """Set the active reuse policy at runtime (aggressive/atomic/balanced). Lets the caller switch per-DB — e.g. the `auto` mode picks atomic on high-ambiguity schemas (schema_complexity)."""
    global _REUSE_POLICY
    _REUSE_POLICY = str(policy).lower()


def get_reuse_policy() -> str:
    return _REUSE_POLICY


# Output-matching mode for the reuse guard. "subset" (default) = strict: every qualified `table.column` the sub-goal needs must be exposed by the view (the Fix-#1 discipline). "overlap" = relaxed: admit a view whose qualified outputs cover >= _OUTPUT_OVERLAP of the sub-goal's, and let the generator read any missing column from its base table (the no-substitution rule still governs that). Grain stays exact-or-finer in BOTH modes — that is the safety-critical check, never relaxed.
_OUTPUT_MATCH = os.environ.get("SKIEW_OUTPUT_MATCH", "subset").lower()
_OUTPUT_OVERLAP = float(os.environ.get("SKIEW_OUTPUT_OVERLAP", "0.5"))


def set_output_match(mode: str = "subset", overlap: float = 0.5) -> None:
    """Toggle the reuse output-match: 'subset' (strict qualified) or 'overlap' (grain + partial qualified-output overlap >= `overlap`). Grain/filter checks are unaffected."""
    global _OUTPUT_MATCH, _OUTPUT_OVERLAP
    _OUTPUT_MATCH = str(mode).lower()
    _OUTPUT_OVERLAP = float(overlap)


def is_atomic_view(spec: ViewSpec) -> bool:
    """Atomic = a plain selection/normalization (SEL/NORM) with no join and no aggregation/window in the body. Filters (WHERE) are allowed — a cohort/selection view is still atomic and safe to reuse. Join- and aggregation-bearing views are the ones that carry wrong-join / wrong-grain risk."""
    if spec.category not in _ATOMIC_CATS:
        return False
    b = re.sub(r"\s+", " ", (getattr(spec, "body_sql", "") or "").lower()).strip()
    if " join " in b or " group by " in b or " union " in b:
        return False
    if _AGG_FN.search(b):
        return False
    return True


def _policy_ok(spec: ViewSpec, req: ViewRequest) -> Tuple[bool, str]:
    """Apply the complexity-aware reuse policy. Returns (allowed, reason)."""
    if _REUSE_POLICY == "atomic" and not is_atomic_view(spec):
        return False, f"policy=atomic rejects non-atomic {spec.category} view"
    if _REUSE_POLICY in ("atomic", "balanced"):
        vt = {str(t).lower() for t in (getattr(spec, "source_tables", None) or [])}
        rt = {str(t).lower() for t in (getattr(req, "source_tables", None) or [])}
        if vt and rt and not vt.issubset(rt):
            return False, f"base tables not ⊆ sub-goal tables ({vt - rt} extra)"
    return True, "ok"


def compatible(spec: ViewSpec, req: ViewRequest, use_guard: bool = True) -> Tuple[bool, str]:
    if _REUSE_POLICY != "aggressive":
        ok, why = _policy_ok(spec, req)
        if not ok:
            return False, why
    if spec.category != req.category:
        return False, "category mismatch"
    req_out, spec_out = _norm_set(req.required_outputs), _norm_set(spec.output_columns)
    if _OUTPUT_MATCH == "overlap":
        if req_out:
            ov = len(req_out & spec_out) / len(req_out)
            if ov < _OUTPUT_OVERLAP:
                return False, f"output overlap {ov:.2f} < {_OUTPUT_OVERLAP}"
    elif not req_out.issubset(spec_out):
        return False, "required outputs not exposed"
    # grain must be exact-or-finer: every required key must be available to group on
    if req.required_grain and not _norm_set(req.required_grain).issubset(_norm_set(spec.grain)):
        return False, "grain too coarse"
    if use_guard:
        sf = {k.lower(): str(v).strip() for k, v in dict(spec.semantic_filters).items()}
        rf = {k.lower(): str(v).strip() for k, v in dict(req.required_filters).items()}
        # Equality dims must match EXACTLY (unchanged behaviour): a view baking a cohort filter the request doesn't declare, or vice-versa, is a bad hit.
        sf_eq = {c: v.lower() for c, v in sf.items() if not _is_range(v)}
        rf_eq = {c: v.lower() for c, v in rf.items() if not _is_range(v)}
        if sf_eq != rf_eq:
            return False, f"semantic-filter mismatch {sf_eq} != {rf_eq}"
        # Range (semi-interval) dims: the view and request must constrain the SAME columns, and on each the view's ray must CONTAIN the request's (view looser-or-equal, same direction) so the view holds every needed row and the tighter bound is re-applied downstream. Any range on one side but not the other, or a view ray that fails to contain the request's, is a safe miss.
        sf_rg = {c: v for c, v in sf.items() if _is_range(v)}
        rf_rg = {c: v for c, v in rf.items() if _is_range(v)}
        if set(sf_rg) != set(rf_rg):
            return False, f"range-filter columns mismatch {set(sf_rg)} != {set(rf_rg)}"
        for c in sf_rg:
            if not _ray_contains(sf_rg[c], rf_rg[c]):
                return False, f"range not contained on {c}: view {sf_rg[c]} vs req {rf_rg[c]}"
    return True, "ok"


def retrieve(graph: ViewGraph, req: ViewRequest, embedder: Embedder,
             tau: float = 0.55, use_guard: bool = True) -> Tuple[Optional[ViewSpec], Dict]:
    """Return (reused_spec_or_None, diagnostics) using embedding similarity + guard."""
    best, best_sim, best_reason = None, -1.0, "no candidate in graph"
    for cand in graph.candidates(req.category):
        if _reuse_blocked(cand):
            continue
        ok, reason = compatible(cand, req, use_guard=use_guard)
        if not ok:
            if best is None:
                best_reason = reason
            continue
        sim = embedder.sim(req.text, cand.description or cand.name)
        if sim > best_sim:
            best, best_sim = cand, sim
            if sim >= tau:
                best_reason = "compatible"
    if best is not None and best_sim >= tau:
        return best, {"hit": True, "sim": round(best_sim, 3), "view": best.name}
    return None, {"hit": False, "sim": round(max(best_sim, 0.0), 3), "reason": best_reason}


# --------------------------------------------------------------------------- #
# Deterministic ("zero-token") reuse selection — Zero-Mem style: embedding retrieval + structural guard + calibration that DISCARDS CONFLICTING EVIDENCE, with NO LLM verification call. Toggle with env SKIEW_DETERMINISTIC_REUSE=1 (read by the runners).
# --------------------------------------------------------------------------- #
_DET_REUSE = os.environ.get("SKIEW_DETERMINISTIC_REUSE", "0").lower() in ("1", "true", "yes")


def deterministic_reuse_on() -> bool:
    return _DET_REUSE


def skill_card_md(spec, depends_on_this=None) -> str:
    """Render every persisted ViewSpec field as a human-readable Markdown skill card. ``depends_on_this`` is derived from the graph (it is not a ViewSpec field) and lists the views that build on this skill.  The JSON remains canonical for reload. This representation is the complete human-readable audit artifact, including full outcome evidence and learned parameters."""
    g = spec.get if isinstance(spec, dict) else (lambda k, d=None: getattr(spec, k, d))
    def _fmt(xs):
        xs = list(xs or [])
        return ", ".join(f"`{x}`" for x in xs) if xs else "—"
    deps = g("depends_on") or []
    val = list(g("validated_on") or [])
    bad = list(g("counter_examples") or [])
    filters = g("semantic_filters") or {}
    params = g("params") or {}
    lines = [
        f"## Skill `{g('name')}`",
        "",
        f"Category: `{g('category')}`",
        "",
        "| field | value |",
        "|---|---|",
        f"| grain (one row per) | {_fmt(g('grain'))} ({g('grain_kind', 'unknown')}) |",
        f"| status / version | {g('status', 'active')} / v{g('version', 1)} |",
        f"| skill id | {g('skill_id', '') or '—'} |",
        f"| output columns | {_fmt(g('output_columns'))} |",
        f"| source tables | {_fmt(g('source_tables'))} |",
        f"| depends_on (builds on) | {_fmt(deps) if deps else '— (reads base tables directly)'} |",
    ]
    if depends_on_this is not None:
        lines.append(f"| depended-on by (builds on this) | {_fmt(depends_on_this)} |")
    lines += [
        "",
        "### Description",
        "",
        g("description") or "—",
        "",
        "### Semantic filters",
        "",
        "```json",
        json.dumps(filters, indent=2, ensure_ascii=False),
        "```",
        "",
        "### Learned skill parameters",
        "",
        "```json",
        json.dumps(params, indent=2, ensure_ascii=False),
        "```",
        "",
        "### Provenance, validation, evidence",
        "",
        "```json",
        json.dumps({"provenance": g("provenance") or {}, "validation": g("validation") or {},
                    "evidence": g("evidence") or {}}, indent=2, ensure_ascii=False, default=str),
        "```",
        "",
        f"### Validated on ({len(val)})",
        "",
        *(f"- {q}" for q in val),
        *(["—"] if not val else []),
        "",
        f"### Counter-examples ({len(bad)})",
        "",
        *(f"- {q}" for q in bad),
        *(["—"] if not bad else []),
        "",
        "### Executable SQL body",
        "",
        "```sql",
        (g("body_sql") or "").strip(),
        "```",
    ]
    return "\n".join(lines)


def select_reuse(graph: ViewGraph, req: ViewRequest, embedder: Embedder,
                 tau: float = 0.55, margin: float = 0.05, use_guard: bool = True):
    """Pick a view to reuse for `req` WITHOUT any LLM call (Zero-Mem 'zero-token memory op').
    1. structural guard: keep only category/grain/output/filter-compatible candidates
    2. embedding retrieval: rank survivors by similarity. Require the top >= tau (retrieval conf.)
    3. calibration (discard conflicting evidence): if a near-tie survivor (within `margin`) is structurally DIFFERENT (different grain or outputs), we cannot disambiguate deterministically -> return None and generate fresh (the safe choice). Returns (spec_or_None, diagnostics)."""
    survivors = []
    for c in graph.candidates(req.category):
        if _reuse_blocked(c):
            continue
        if not compatible(c, req, use_guard=use_guard)[0]:
            continue
        survivors.append((embedder.sim(req.text, c.description or c.name), c))
    if not survivors:
        return None, {"hit": False, "reason": "no compatible candidate"}
    survivors.sort(key=lambda x: -x[0])
    top_sim, top = survivors[0]
    if top_sim < tau:
        return None, {"hit": False, "sim": round(top_sim, 3), "reason": f"sim<{tau}"}
    for sim2, c2 in survivors[1:]:
        if top_sim - sim2 < margin and (_norm_set(c2.grain) != _norm_set(top.grain)
                                        or _norm_set(c2.output_columns) != _norm_set(top.output_columns)):
            return None, {"hit": False, "sim": round(top_sim, 3), "reason": "conflicting near-tie"}
        break
    return top, {"hit": True, "sim": round(top_sim, 3), "view": top.name, "mode": "deterministic"}


_TOK = re.compile(r"[a-z0-9]+")


def _tokens(*parts) -> set:
    out = set()
    for p in parts:
        if p is None:
            continue
        if isinstance(p, (list, tuple, set)):
            for x in p:
                out |= set(_TOK.findall(str(x).lower()))
        elif isinstance(p, dict):
            for k, v in p.items():
                out |= set(_TOK.findall(f"{k} {v}".lower()))
        else:
            out |= set(_TOK.findall(str(p).lower()))
    return out


def _lex_score(req: ViewRequest, spec: ViewSpec) -> float:
    """Cheap, embedding-free lexical overlap between the sub-goal and a candidate view. Weighted Jaccard over intent+outputs+grain vs the view's description+outputs+tables+name."""
    q = _tokens(req.text, req.required_outputs, req.required_grain)
    d = _tokens(spec.description, spec.output_columns, spec.source_tables, spec.name, spec.grain)
    if not q or not d:
        return 0.0
    inter = len(q & d)
    return inter / (len(q | d) or 1)


def retrieve_candidates(graph: ViewGraph, req: ViewRequest, embedder: Optional[Embedder] = None,
                        k: int = 6, use_guard: bool = True) -> List[ViewSpec]:
    """Two-stage, embedding-FREE-by-default shortlist for the LLM reuse selector — the LLM never sees the whole graph (it can't rate 1K CTEs), only <=k candidates:

      Stage 1 (exact, scales to thousands): the mechanical compatibility guard drops every view whose category / required-outputs / grain / intrinsic-filters cannot match. No cost. Stage 2 (cheap ranker, only if still >k): rank the survivors by lexical token overlap and keep the top k. Embedding is NOT used unless an `embedder` is explicitly passed (then it just breaks ties / blends), so the default path touches no embeddings.

    With <=k guard-compatible candidates every one is passed through and no ranking runs at all."""
    compat = [c for c in graph.candidates(req.category)
              if not _reuse_blocked(c) and compatible(c, req, use_guard=use_guard)[0]]
    if len(compat) <= k:
        return compat
    if embedder is None:
        scored = [(_lex_score(req, c), c) for c in compat]
    else:                                     # optional: blend lexical + embedding for the trim
        scored = [(0.5 * _lex_score(req, c) + 0.5 * embedder.sim(req.text, c.description or c.name), c)
                  for c in compat]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _s, c in scored[:k]]


# --------------------------------------------------------------------------- #
# Execution-grounded validation
# --------------------------------------------------------------------------- #
def validate_view(con: sqlite3.Connection, graph: ViewGraph, spec: ViewSpec,
                  timeout_rows: int = 5) -> Tuple[bool, str]:
    """Execute the view with its in-graph dependency closure. Confirm declared outputs."""
    try:
        dep_specs = graph.topo_closure(spec.depends_on) if spec.depends_on else []
        chosen = {s.name: s for s in dep_specs}
        chosen[spec.name] = spec
        ordered = _order_specs(list(chosen.values()))
        with_clause = ",\n".join(s.cte_clause() for s in ordered)
        prefix = "WITH RECURSIVE" if any(s.category == "REC" for s in ordered) else "WITH"
        sql = f"{prefix} {with_clause}\nSELECT * FROM {spec.name} LIMIT {timeout_rows}"
        cur = con.execute(sql)
        cols = _lower_set(d[0] for d in cur.description)
        cur.fetchall()
        missing = [c for c in spec.output_columns if c.lower() not in cols]
        if missing:
            return False, f"declared outputs missing from result: {missing} (got {sorted(cols)})"
        return True, "ok"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def _order_specs(specs: List[ViewSpec]) -> List[ViewSpec]:
    by_name = {s.name: s for s in specs}
    sub = nx.DiGraph()
    for s in specs:
        sub.add_node(s.name)
        for d in s.depends_on:
            if d in by_name:
                sub.add_edge(d, s.name)
    return [by_name[n] for n in nx.topological_sort(sub)]


# --------------------------------------------------------------------------- #
# Persistence (one graph per db_id)
# --------------------------------------------------------------------------- #
def save_graph(graph: ViewGraph, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {"db_id": graph.db_id, "views": [asdict(v) for v in graph.views.values()],
            # skill-to-skill relation edges are not derivable from the view fields, so they persist separately
            "relations": [list(r) for r in graph.relations()]}   # episodes live in {db}.episodes.jsonl
    json.dump(data, open(path, "w"), indent=2)              # canonical (needed for reload)
    # Also save the skills as a human-readable MARKDOWN skill-card file alongside the JSON — the graph's skills "saved in markdown format". (JSON stays as the machine-reloadable source.)
    try:
        rev: Dict[str, List[str]] = {}
        for v in graph.views.values():
            for d in (v.depends_on or []):
                rev.setdefault(d, []).append(v.name)
        cards = [f"# Skill graph — `{graph.db_id}` ({len(graph.views)} skills)\n"]
        for v in graph.views.values():
            cards.append(skill_card_md(v, depends_on_this=rev.get(v.name, [])))
            cards.append("\n---\n")
        open(os.path.splitext(path)[0] + ".md", "w", encoding="utf-8").write("\n".join(cards))
    except Exception:  # noqa: BLE001 — markdown export must never break a run
        pass


def load_graph(path: str) -> ViewGraph:
    data = json.load(open(path))
    g = ViewGraph(db_id=data["db_id"])
    # add in dependency order so edges resolve
    specs = {v["name"]: ViewSpec(**v) for v in data["views"]}
    added = set()

    def _add(name):
        if name in added or name not in specs:
            return
        for d in specs[name].depends_on:
            _add(d)
        g.add_view(specs[name])
        added.add(name)

    for n in list(specs):
        _add(n)
    for src, dst, etype in data.get("relations", []):
        g.add_relation(src, dst, etype)                   # relation types no longer kept are ignored
    return g


__all__ = ["compatible", "retrieve", "validate_view", "compose_sql",
           "save_graph", "load_graph", "ViewSpec", "ViewGraph", "ViewRequest"]
