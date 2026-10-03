"""registry.py — the skill registry around the ViewGraph: a versioned catalog (ViewSpec + contract v3), a dependency DAG, structural indexes, a vector index, semantic relation edges (SUBSUMES / CONFLICTS_WITH / SUPERSEDES), and the five-stage retrieval that decides whether a stored skill may serve a new request.

Retrieval stages (`retrieve`):
  1. Hard scope  : active status, complete contract (known outputs AND known grain AND passed validation), same database, same dialect, unchanged table fingerprints, eligible dependencies, request's source-table domain, not already used in this question.
  2. Contract    : category, required outputs, grain equal-or-finer, filters/time windows compatible, aggregation semantics, fan-out-safe joins.
  3. Ranking     : description similarity + column/table overlap + metric overlap + prior successful subgoals - known misuses. Accept only above tau.
  4. Reuse mode  : exact | specialization (filter downstream) | rollup (re-aggregate a finer grain) | composition (1:1 join of two skills at the requested grain). Non-exact modes become a thin derived CTE over the stored skill, validated before use.
  5. Verify      : an LLM selector may reject every candidate (NONE). Deterministic mode abstains on conflicting near-ties. Uncertain -> generate fresh.

Admission (`admit`) is the only way a view becomes a persistent, reusable skill: full contract derivation, validation (+ optional generated tests), completeness, SQL-hash dedup, result-equivalence merge (canonicalization), and SUBSUMES / CONFLICTS_WITH / SUPERSEDES edges."""
from __future__ import annotations

import copy
import dataclasses
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import sqlglot

from skiewsql import contracts
from skiewsql.contracts import GRAIN_KEYED, GRAIN_SCALAR, MEASURE_KINDS, Scope
from skiewsql.core import ViewGraph, ViewRequest, ViewSpec, norm_key

ROW_CATEGORIES = {"SEL", "NORM", "JOIN"}
NEG_REJECT = 0.6          # similarity to a known misuse that vetoes a candidate (the old Layer-4 threshold)
_LEGACY_AV = re.compile(r"^chunk_view_\d+(_\d+)?$")


# --------------------------------------------------------------------------- #
# Stage 1 — eligibility and scope
# --------------------------------------------------------------------------- #
def eligible(spec: ViewSpec, graph: ViewGraph, scope: Scope, _seen=None) -> Tuple[bool, str]:
    """May this stored skill be reused automatically at all (independent of the request)?"""
    _seen = set() if _seen is None else _seen
    if spec.status != "active":
        return False, f"status={spec.status}"
    why = contracts.completeness(spec)
    if why:
        return False, "incomplete contract: " + ", ".join(why)
    prov = spec.provenance or {}
    if prov.get("db_id") and prov["db_id"] != scope.db_id:
        return False, f"other database {prov['db_id']}"
    if (spec.dialect or "sqlite") != scope.dialect:
        return False, f"dialect {spec.dialect} != {scope.dialect}"
    fps = prov.get("table_fingerprints") or {}
    if not fps and prov.get("lineage"):
        return False, "no table fingerprints"
    for t, fp in fps.items():
        if scope.table_fp.get(t) != fp:
            return False, f"schema changed for table {t}"
    for t, dfp in (prov.get("data_fingerprints") or {}).items():
        if scope.data_fp and scope.data_fp.get(t) != dfp:
            return False, f"data changed for table {t} (observed grain must be revalidated)"
    _seen.add(spec.name)
    for d in spec.depends_on or []:
        dep = graph.views.get(d)
        if dep is None:
            return False, f"missing dependency {d}"
        if d in _seen:
            continue
        ok, why = eligible(dep, graph, scope, _seen)
        if not ok:
            return False, f"dependency {d}: {why}"
    return True, "ok"


def stage1(spec: ViewSpec, req: ViewRequest, graph: ViewGraph, scope: Scope, exclude=()) -> Tuple[bool, str]:
    from skiewsql import sqlview
    if spec.name in exclude:
        return False, "already used in this question"
    ok, why = eligible(spec, graph, scope)
    if not ok:
        return False, why
    if sqlview.get_reuse_policy() == "atomic" and not sqlview.is_atomic_view(spec):
        return False, "policy=atomic rejects a non-atomic view"
    if req.source_tables:
        dom = {str(t).split(".")[-1].lower() for t in req.source_tables}
        lin = {t.lower() for t in (spec.provenance or {}).get("lineage", spec.source_tables or [])}
        if lin and not lin <= dom:
            return False, f"reads tables outside the request domain: {sorted(lin - dom)}"
    return True, "ok"


# --------------------------------------------------------------------------- #
# Stage 2 — contract compatibility and reuse mode
# --------------------------------------------------------------------------- #
@dataclass
class Match:
    spec: ViewSpec
    mode: str = "exact"                                    # exact | specialization | rollup | specialized_rollup | composition
    extra_filters: Dict[str, str] = field(default_factory=dict)   # actual output column -> value, applied downstream
    rollup_to: List[str] = field(default_factory=list)            # actual grain columns to roll up to
    outputs: List[str] = field(default_factory=list)              # actual columns the request needs
    partner: Optional[ViewSpec] = None
    sim: float = 0.0
    score: float = 0.0
    verifier_reason: str = ""

    @property
    def key(self) -> str:
        return self.spec.name + (f"+{self.partner.name}" if self.partner is not None else "")


def _map(names, columns) -> Tuple[List[str], List[str]]:
    """Map requested names onto actual columns by normalized key -> (mapped, missing)."""
    by = {norm_key(c): c for c in columns}
    mapped, missing = [], []
    for n in names:
        m = by.get(norm_key(n)) or by.get(norm_key(str(n).split(".")[-1]))
        (mapped if m else missing).append(m or n)
    return mapped, missing


def measures(spec: ViewSpec) -> List[str]:
    return [c for c, k in (spec.aggregation or {}).items() if k in MEASURE_KINDS]


def is_row_level(spec: ViewSpec) -> bool:
    kinds = set((spec.aggregation or {}).values())
    return spec.grain_kind != GRAIN_SCALAR and not (kinds & (MEASURE_KINDS | {"window"}))


def stage2(spec: ViewSpec, req: ViewRequest, use_guard: bool = True) -> Tuple[Optional[Match], str]:
    """Holistic (AV-SQL N×1) requests carry no category, outputs or grain, so only filters and scope constrain them."""
    from skiewsql import sqlview
    if not req.holistic and spec.category != req.category:
        return None, "category mismatch"
    outs = list(spec.output_columns)
    req_out = [r for r in req.required_outputs if norm_key(r)]
    mapped_out, missing = _map(req_out, outs)
    if sqlview._OUTPUT_MATCH == "overlap" and req_out:
        if len(req_out) - len(missing) < sqlview._OUTPUT_OVERLAP * len(req_out):
            return None, "required outputs not exposed"
        mapped_out = [m for m, n in zip(mapped_out, req_out) if n not in missing]
    elif missing:
        return None, "required outputs not exposed"
    meas = measures(spec)
    if not req.holistic and req.category in ROW_CATEGORIES and meas:
        return None, "aggregation mismatch: stored view is aggregated"
    if not req.holistic and req.category == "AGG" and not meas:
        return None, "aggregation mismatch: stored view has no measures"
    if meas and any(j.get("relationship") == "many_to_many"
                    for j in (spec.validation or {}).get("join_cardinality", [])):
        return None, "unsafe join: many-to-many join before aggregation"
    # grain: equal or finer
    rg = [g for g in req.required_grain if norm_key(g)]
    rollup: List[str] = []
    if spec.grain_kind == GRAIN_SCALAR:
        if rg:
            return None, "grain too coarse (scalar view)"
    else:
        if not rg:
            if req.category in ("AGG", "RANK", "WIN") and not req.holistic:
                return None, "request grain unknown for an aggregate subgoal"
        else:
            rg_m, rg_missing = _map(rg, spec.grain)
            if rg_missing:
                return None, "grain too coarse"
            if {norm_key(g) for g in rg} != {norm_key(g) for g in spec.grain}:
                rollup = rg_m
    # filters and time windows
    extra: Dict[str, str] = {}
    if use_guard:
        sf = {norm_key(k): (k, str(v).strip()) for k, v in (spec.semantic_filters or {}).items()}
        req_filters = {**(getattr(req, "inherited_filters", None) or {}), **(req.required_filters or {})}
        rf = {norm_key(k): (k, str(v).strip()) for k, v in req_filters.items()}
        for key, (k, v) in sf.items():
            if key not in rf:
                return None, f"stored view is narrower: filter {k}={v} not requested"
            rv = rf[key][1]
            if contracts.is_range(v) or contracts.is_range(rv):
                if not (contracts.is_range(v) and contracts.is_range(rv)):
                    return None, f"filter kind mismatch on {k}"
                if not contracts.interval_contains(v, rv):
                    return None, f"range not contained on {k}: view {v} vs request {rv}"
                if contracts.parse_interval(v) != contracts.parse_interval(rv):
                    extra[rf[key][0]] = rv
            elif contracts.norm_value(v) != contracts.norm_value(rv):
                return None, f"filter value mismatch on {k}: {v} != {rv}"
        for key, (k, rv) in rf.items():
            if key not in sf:
                extra[k] = rv
    extra_cols: Dict[str, str] = {}
    if extra:
        mapped, miss = _map(list(extra), outs)
        if miss:
            return None, f"cannot specialize: {miss} not exposed by the stored view"
        grain_keys = {norm_key(g) for g in spec.grain}
        if not is_row_level(spec) and not all(norm_key(m) in grain_keys for m in mapped):
            return None, "cannot specialize an aggregated view on a non-key column"
        extra_cols = {m: extra[k] for m, k in zip(mapped, extra)}
    if rollup:
        if spec.category in ("RANK", "WIN", "RESHAPE", "REC", "SET"):
            return None, f"rollup of a {spec.category} view is not safe"
        if not is_row_level(spec):
            keyset = {norm_key(c) for c in rollup}
            needed = [c for c in mapped_out if norm_key(c) not in keyset] or \
                [c for c in meas if (spec.aggregation or {}).get(c) in contracts.DECOMPOSABLE]
            for c in needed:
                kind = (spec.aggregation or {}).get(c, "none")
                if kind not in contracts.DECOMPOSABLE:
                    return None, f"rollup unsafe: {c} is {kind}, not re-aggregable"
            mapped_out = list(dict.fromkeys(rollup + needed))
    mode = ("specialized_rollup" if extra_cols and rollup else "specialization" if extra_cols
            else "rollup" if rollup else "exact")
    return Match(spec=spec, mode=mode, extra_filters=extra_cols, rollup_to=rollup, outputs=mapped_out), "ok"


_CATEGORY_OPERATOR = {"JOIN": "join", "AGG": "aggregate", "RANK": "window", "WIN": "window",
                      "SET": "set", "REC": "recursive"}


def provenance_compatible(match: Match, req: ViewRequest) -> Tuple[bool, str]:
    """Check qualified output lineage and the relational operator shape after contract matching.

    Bare logical output names do not claim a source table, so they remain the verifier's job. A
    qualified request such as ``ratings.user_id`` must trace to that exact base column.
    """
    specs = [match.spec] + ([match.partner] if match.partner is not None else [])
    operators = {op for s in specs for op in ((s.provenance or {}).get("operators") or [])}
    expected = set(req.required_operators or [])
    category_operator = None if req.holistic else _CATEGORY_OPERATOR.get(req.category)
    if category_operator:
        expected.add(category_operator)
    missing_operators = sorted(expected - operators)
    if missing_operators:
        return False, f"operator mismatch: request requires {', '.join(missing_operators)}"
    for requested in req.required_outputs:
        parts = str(requested).strip('`"').split(".")
        if len(parts) < 2:
            continue
        want_table, want_col = norm_key(parts[-2]), norm_key(parts[-1])
        refs = []
        for spec in specs:
            by_output = {norm_key(k): v for k, v in ((spec.provenance or {}).get("output_lineage") or {}).items()}
            refs.extend(by_output.get(want_col) or [])
        if not refs:
            return False, f"no column lineage for qualified output {requested}"
        if not any(len(str(ref).split(".")) >= 2 and
                   norm_key(str(ref).split(".")[-2]) == want_table and
                   norm_key(str(ref).split(".")[-1]) == want_col for ref in refs):
            return False, f"column lineage mismatch for {requested}: {refs}"
    return True, "ok"


def composition_matches(specs: List[ViewSpec], req: ViewRequest, use_guard: bool = True,
                        limit: int = 8) -> List[Match]:
    """Two keyed skills at exactly the requested grain whose outputs jointly (not singly) cover the request. Joined 1:1 on the grain keys."""
    rg = {norm_key(g) for g in req.required_grain if norm_key(g)}
    req_out = {norm_key(r) for r in req.required_outputs if norm_key(r)}
    if not rg or not req_out:
        return []
    probe = dataclasses.replace(req, required_outputs=[])
    pool = []
    for s in specs:
        if s.grain_kind != GRAIN_KEYED or {norm_key(g) for g in s.grain} != rg:
            continue
        m, _ = stage2(s, probe, use_guard)
        if m is not None and m.mode == "exact":
            pool.append(s)
    out = []
    for i, a in enumerate(pool[:limit]):
        ao = {norm_key(c) for c in a.output_columns}
        for b in pool[i + 1:limit]:
            bo = {norm_key(c) for c in b.output_columns}
            if req_out <= ao or req_out <= bo or not req_out <= (ao | bo):
                continue
            out.append(Match(spec=a, mode="composition", partner=b))
    return out


# --------------------------------------------------------------------------- #
# Stage 3 — ranking (dense + lexical + metric + evidence), vector index
# --------------------------------------------------------------------------- #
_TOK = re.compile(r"[a-z0-9]+")


def _tokens(*parts) -> set:
    out = set()
    for p in parts:
        if isinstance(p, dict):
            p = " ".join(f"{k} {v}" for k, v in p.items())
        elif isinstance(p, (list, tuple, set)):
            p = " ".join(map(str, p))
        out |= set(_TOK.findall(str(p or "").lower()))
    return out


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def describe_text(spec: ViewSpec) -> str:
    return (spec.params or {}).get("description") or spec.description or spec.name


class VectorIndex:
    """Cosine top-k over skill descriptions. Uses the embedder's cached vectors when it exposes `encode`, and falls back to pairwise `sim` otherwise."""

    def __init__(self, embedder):
        self.embedder = embedder

    def topk(self, text: str, matches: List[Match], k: int) -> List[Match]:
        if len(matches) <= k:
            return matches
        if hasattr(self.embedder, "encode"):
            try:
                qv = np.asarray(self.embedder.encode(text), dtype=np.float32)
                mat = np.vstack([np.asarray(self.embedder.encode(describe_text(m.spec)), dtype=np.float32)
                                 for m in matches])
                sims = mat @ qv / ((np.linalg.norm(mat, axis=1) * (np.linalg.norm(qv) or 1.0)) + 1e-9)
                order = np.argsort(-sims)[:k]
                return [matches[i] for i in order]
            except Exception:  # noqa: BLE001
                pass
        scored = sorted(matches, key=lambda m: -self.embedder.sim(text, describe_text(m.spec)))
        return scored[:k]


def stage3(matches: List[Match], req: ViewRequest, embedder, graph: ViewGraph, tau: float,
           diag: Dict, prefilter: int = 32) -> List[Match]:
    matches = VectorIndex(embedder).topk(req.text, matches, prefilter)
    q_tok = _tokens(req.text, req.required_outputs, req.required_grain)
    kept = []
    for m in matches:
        s = m.spec
        m.sim = embedder.sim(req.text, describe_text(s))
        if m.partner is not None:
            m.sim = (m.sim + embedder.sim(req.text, describe_text(m.partner))) / 2
        lex = _jaccard(q_tok, _tokens(s.description, s.output_columns, s.source_tables, s.name, s.grain))
        metric = _jaccard(q_tok, _tokens(s.aggregation, (s.params or {}).get("metric", "")))
        prov = _jaccard(q_tok, _tokens((s.provenance or {}).get("source_columns", []),
                                       (s.provenance or {}).get("operators", []),
                                       (s.provenance or {}).get("output_lineage", {})))
        ev = s.evidence or {}
        pos_texts = list(ev.get("positive_subgoals", []))[-5:]
        neg_texts = list(ev.get("negative_subgoals", []))[-5:] + list(s.counter_examples or [])[-5:]
        pos = max((embedder.sim(req.text, t) for t in pos_texts), default=0.0)
        neg = max((embedder.sim(req.text, t) for t in neg_texts), default=0.0)
        if neg >= NEG_REJECT and neg > pos:
            diag.setdefault("stage3_rejected", {})[m.key] = f"similar to a known misuse ({neg:.2f})"
            continue
        if m.sim < tau:
            diag.setdefault("stage3_rejected", {})[m.key] = f"sim {m.sim:.3f} < tau {tau}"
            continue
        m.score = m.sim + 0.15 * lex + 0.1 * metric + 0.1 * prov + 0.1 * pos - 0.2 * neg
        kept.append(m)
    kept.sort(key=lambda m: -m.score)
    # Equivalent skills never coexist: admission merges a duplicate or result-equivalent view into the existing skill.
    return kept


# --------------------------------------------------------------------------- #
# Stage 4 — derived views for non-exact reuse modes
# --------------------------------------------------------------------------- #
def build_derived(m: Match, req: ViewRequest, name: str) -> ViewSpec:
    base, q = m.spec, contracts.q
    filters = dict(base.semantic_filters or {})
    if m.mode == "composition":
        a, b = base, m.partner
        a_keys, _ = _map(req.required_grain, a.grain)
        b_keys, _ = _map(req.required_grain, b.grain)
        a_cols = {norm_key(c) for c in a.output_columns}
        extra = [c for c in b.output_columns if norm_key(c) not in a_cols]
        on = " AND ".join(f"a.{q(x)} = b.{q(y)}" for x, y in zip(a_keys, b_keys))
        body = (f"SELECT a.*{''.join(', b.' + q(c) for c in extra)}\nFROM {a.name} AS a\n"
                f"JOIN {b.name} AS b ON {on}")
        outputs, grain, deps = list(a.output_columns) + extra, list(a_keys), [a.name, b.name]
        filters.update(b.semantic_filters or {})
    else:
        where = [contracts.filter_sql(c, v) for c, v in m.extra_filters.items()]
        where_sql = ("\nWHERE " + " AND ".join(w for w in where if w)) if any(where) else ""
        filters.update(m.extra_filters)
        if m.rollup_to and is_row_level(base):
            outputs = list(dict.fromkeys(m.rollup_to + m.outputs))
            body = f"SELECT DISTINCT {', '.join(q(c) for c in outputs)}\nFROM {base.name}{where_sql}"
        elif m.rollup_to:
            keyset = {norm_key(c) for c in m.rollup_to}
            meas = [c for c in m.outputs if norm_key(c) not in keyset]
            cols = [q(c) for c in m.rollup_to] + \
                   [f"{contracts.DECOMPOSABLE[base.aggregation[c]]}({q(c)}) AS {q(c)}" for c in meas]
            outputs = list(m.rollup_to) + meas
            body = (f"SELECT {', '.join(cols)}\nFROM {base.name}{where_sql}\n"
                    f"GROUP BY {', '.join(q(c) for c in m.rollup_to)}")
        else:
            outputs = list(base.output_columns)
            body = f"SELECT *\nFROM {base.name}{where_sql}"
        grain, deps = list(m.rollup_to or base.grain), [base.name]
    return ViewSpec(
        name=name, category=req.category, body_sql=body, source_tables=[], output_columns=outputs,
        grain=grain, semantic_filters={str(k): str(v) for k, v in filters.items()}, depends_on=deps,
        description=req.text, grain_kind=GRAIN_KEYED if grain else base.grain_kind,
        dialect=base.dialect, status="exploratory",
        aggregation={c: ("key" if norm_key(c) in {norm_key(g) for g in grain}
                         else base.aggregation.get(c, "none")) for c in outputs},
        provenance={"origin": "derived", "mode": m.mode, "base": base.name,
                    "partner": m.partner.name if m.partner is not None else ""})


def _unique_name(graph: ViewGraph, name: str) -> str:
    if not graph.has(name):
        return name
    i = len(graph.views)
    while graph.has(f"{name}_{i}"):
        i += 1
    return f"{name}_{i}"


def _materialize(graph: ViewGraph, con, m: Match, req: ViewRequest) -> Tuple[Optional[ViewSpec], str]:
    """Add the derived view for a non-exact match to the working graph and validate it. Composition must also be lossless (same row count as both inputs)."""
    spec = build_derived(m, req, _unique_name(graph, req.want_name))
    graph.add_view(spec)
    rec = contracts.validate(con, graph, spec, timeout=5.0)          # on the answer path: keep it short
    ok = rec.get("passed", False)
    why = "; ".join(rec.get("failures", [])) or "ok"
    if ok and m.mode == "composition":
        n = rec.get("row_count")
        na = (m.spec.validation or {}).get("row_count")
        nb = (m.partner.validation or {}).get("row_count")
        if n is None or n != na or n != nb:
            ok, why = False, f"composition is not 1:1 (rows {n} vs {na}/{nb})"
    spec.validation = rec
    if not ok:
        graph.remove_view(spec.name)
        return None, why
    return spec, "ok"


# --------------------------------------------------------------------------- #
# Stage 5 — verification and abstention
# --------------------------------------------------------------------------- #
def _note(m: Match) -> str:
    ev = m.spec.evidence or {}
    parts = []
    if m.mode in ("specialization", "specialized_rollup"):
        parts.append("reused after filtering to " + ", ".join(f"{c}={v}" for c, v in m.extra_filters.items()))
    if m.mode in ("rollup", "specialized_rollup"):
        parts.append(f"re-aggregated from grain {m.spec.grain} to {m.rollup_to}")
    if m.mode == "composition":
        parts.append(f"1:1 join of {m.spec.name} and {m.partner.name} on {m.spec.grain}")
    if ev.get("positive") or ev.get("negative"):
        parts.append(f"prior outcomes: {ev.get('positive', 0)} good, {ev.get('negative', 0)} harmful")
    return "; ".join(parts)


RISKY_CATEGORIES = {"JOIN", "AGG", "WIN", "SET", "REC"}   # wrong join path / grain / window silently corrupts results


def stage5(ranked: List[Match], req: ViewRequest, graph: ViewGraph, llm=None, n_votes: int = 1,
           deterministic: bool = False, margin: float = 0.05, min_confidence: float = 0.6,
           risky_votes: int = 3, name_map: Optional[Dict[str, str]] = None) -> Tuple[Optional[Match], str]:
    """Verification with abstention. A vote counts only when the verifier names a candidate with confidence >= min_confidence. Risky categories get at least `risky_votes` votes. Reuse needs a strict majority of all votes."""
    if not ranked:
        return None, "no candidate"
    if deterministic or llm is None:
        top = ranked[0]
        if len(ranked) > 1:
            nxt = ranked[1]
            different = (contracts.contract_signature(top.spec) != contracts.contract_signature(nxt.spec))
            conflict = nxt.spec.name in graph.related(top.spec.name, "CONFLICTS_WITH")
            if conflict or (top.score - nxt.score < margin and different):
                return None, "conflicting near-tie"
        return top, "deterministic"
    from skiewsql import agents
    display, notes, by_key = [], {}, {}
    for m in ranked:
        if m.mode == "composition":
            d = build_derived(m, req, m.key)
            d.params = {"description": f"{describe_text(m.spec)} + {describe_text(m.partner)}"}
        else:
            d = m.spec
        display.append(d)
        notes[d.name] = "; ".join(x for x in [
            ("the sub-goal's column names were mapped to stored names, check they mean the same: "
             + ", ".join(f"{a} -> {b}" for a, b in name_map.items())) if name_map else "",
            _note(m)] if x)
        by_key[d.name] = m
    risky = any(m.spec.category in RISKY_CATEGORIES or
                (m.partner is not None and m.partner.category in RISKY_CATEGORIES) for m in ranked)
    votes = max(1, n_votes, risky_votes if risky else 1)
    picks = [agents.choose_reuse(llm, req, display, notes=notes) for _ in range(votes)]
    named = [p[0] for p in picks if p[0]]
    if not named:
        return None, "verifier chose NONE"
    names = [p[0] for p in picks if p[0] and p[2] >= min_confidence]
    if not names:
        return None, "verifier confidence too low"
    top = max(set(names), key=names.count)
    if names.count(top) * 2 <= votes:
        return None, "no verifier majority"
    # keep the verifier's own explanation for the planner/composer (per-question memory, not stored on the skill)
    by_key[top].verifier_reason = next((p[1] for p in picks if p[0] == top and p[1]), "")
    return by_key[top], "verified"


# --------------------------------------------------------------------------- #
# The five-stage retrieval
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# Stage 0 — map the decomposer's logical names onto the stored column vocabulary
# --------------------------------------------------------------------------- #
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
OUTPUT_MAP_EMB, GRAIN_MAP_EMB, MAP_TOKENS = 0.6, 0.8, 0.5


def name_tokens(name) -> set:
    """Word tokens of a column name (snake/camel/space split, simple plural stripping)."""
    toks = re.findall(r"[a-z0-9]+", _CAMEL.sub(" ", str(name).split(".")[-1]).lower())
    return {t[:-1] if len(t) > 3 and t.endswith("s") else t for t in toks}


def map_names(names, vocab, embedder, min_emb: float, min_tok: float = MAP_TOKENS) -> Dict[str, str]:
    """Map each requested name that has no exact stored match to the closest stored column name, by shared word tokens (Jaccard >= min_tok) or embedding similarity (>= min_emb). Returns {requested: stored}. Unmatched names are left out. This only proposes candidates: Stage 2 still checks the contract, and Stage 5 must verify any match that relied on a mapping."""
    by = {norm_key(v): v for v in vocab}
    out: Dict[str, str] = {}
    for n in names:
        if not norm_key(n) or norm_key(n) in by or norm_key(str(n).split(".")[-1]) in by:
            continue
        nt, best, best_s = name_tokens(n), None, 0.0
        for v in by.values():
            tok = _jaccard(nt, name_tokens(v))
            s = tok if tok >= min_tok else 0.0
            if s < 1.0:
                try:
                    emb = embedder.sim(str(n).replace("_", " "), str(v).replace("_", " "))
                except Exception:  # noqa: BLE001
                    emb = 0.0
                if emb >= min_emb:
                    s = max(s, emb)
            if s > best_s:
                best, best_s = v, s
        if best is not None:
            out[str(n)] = best
    return out


def map_request(pool: ViewGraph, req: ViewRequest, embedder) -> Tuple[ViewRequest, Dict[str, str]]:
    """Rewrite the request's outputs and grain keys into the vocabulary of stored skills of its category (grain keys need a stricter match). Returns (mapped request, {requested: stored})."""
    if req.holistic:
        return req, {}
    names = pool.lookup("category", [req.category])
    outs_vocab = {c for n in names for c in pool.views[n].output_columns}
    grain_vocab = {c for n in names for c in pool.views[n].grain}
    omap = map_names(req.required_outputs, outs_vocab, embedder, OUTPUT_MAP_EMB)
    gmap = map_names(req.required_grain, grain_vocab, embedder, GRAIN_MAP_EMB)
    mapping = {**omap, **{k: v for k, v in gmap.items()}}
    if not mapping:
        return req, {}
    mreq = dataclasses.replace(
        req, required_outputs=list(dict.fromkeys(omap.get(o, o) for o in req.required_outputs)),
        required_grain=list(dict.fromkeys(gmap.get(g, g) for g in req.required_grain)))
    return mreq, mapping


def _all_of(pool: ViewGraph, index: str, names) -> Optional[set]:
    """Views that contain EVERY requested key in `index` (a qualified `table.col` also matches bare `col`). None when no keys constrain the lookup."""
    out = None
    for n in names:
        if not norm_key(n):
            continue
        hit = pool.lookup(index, [n, str(n).split(".")[-1]])
        out = hit if out is None else out & hit
    return out


def index_candidates(pool: ViewGraph, req: ViewRequest, composition: bool = False) -> List[ViewSpec]:
    """Structural-index candidate generation (no scan over the category bucket). Non-holistic: category ∩ every required output (subset mode) ∩ every required grain key. Composition relaxes outputs (they are split across two skills). Holistic: skills whose lineage touches the request's tables."""
    from skiewsql import sqlview
    if req.holistic:
        names = (pool.lookup("table", req.source_tables) if req.source_tables else set(pool.views))
    else:
        names = pool.lookup("category", [req.category])
        if sqlview._OUTPUT_MATCH != "overlap" and not composition:
            outs = _all_of(pool, "output", req.required_outputs)
            if outs is not None:
                names &= outs
        grain = _all_of(pool, "grain", req.required_grain)
        if grain is not None:
            names &= grain
    order = {n: i for i, n in enumerate(pool.views)}
    return [pool.views[n] for n in sorted(names, key=order.get) if n in pool.views]


def retrieve(pool: ViewGraph, graph: ViewGraph, req: ViewRequest, embedder, *, scope: Scope, con,
             tau: float = 0.6, use_guard: bool = True, llm=None, n_votes: int = 1,
             deterministic: bool = False, exclude=(), k: int = 4, min_confidence: float = 0.6,
             risky_votes: int = 3) -> Tuple[Optional[ViewSpec], Dict]:
    """Return (spec to use for `req` or None, diagnostics). `pool` is the question-start snapshot (candidates). `graph` is the working graph where derived views are added. For a non-exact mode the returned spec is the derived view. diag['base'] names the stored skill(s)."""
    diag: Dict = {"hit": False}
    # Stage 0: speak the stored vocabulary. Matches that rely on a renamed output/grain need LLM verification.
    req, name_map = map_request(pool, req, embedder)
    if name_map:
        diag["name_map"] = name_map

    def _stage1(cands):
        kept = []
        for c in cands:
            ok, why = stage1(c, req, pool, scope, exclude)
            if ok:
                kept.append(c)
            else:
                diag.setdefault("stage1_rejected", {})[c.name] = why
        return kept

    cands = index_candidates(pool, req)
    diag["index_candidates"] = len(cands)
    s1 = _stage1(cands)
    matches = []
    for c in s1:
        m, why = stage2(c, req, use_guard)
        if m is not None:
            ok, pwhy = provenance_compatible(m, req)
            if ok:
                matches.append(m)
            else:
                diag.setdefault("provenance_rejected", {})[c.name] = pwhy
        else:
            diag.setdefault("stage2_rejected", {})[c.name] = why
    if not matches and not req.holistic:
        for m in composition_matches(_stage1(index_candidates(pool, req, composition=True)), req, use_guard):
            ok, pwhy = provenance_compatible(m, req)
            if ok:
                matches.append(m)
            else:
                diag.setdefault("provenance_rejected", {})[m.key] = pwhy
    # Relation edges (equivalence, conflicts) live on the working graph, not on the snapshot.
    ranked = stage3(matches, req, embedder, graph, tau, diag)[:k]
    diag["shortlist"] = [m.key for m in ranked]
    diag["sim"] = round(ranked[0].sim, 3) if ranked else 0.0
    if name_map and ranked and (deterministic or llm is None):
        chosen, how = None, "name mapping needs LLM verification"
    else:
        chosen, how = stage5(ranked, req, graph, llm=llm, n_votes=n_votes, deterministic=deterministic,
                             min_confidence=min_confidence, risky_votes=risky_votes, name_map=name_map)
    diag["decision"] = how
    if chosen is None:
        diag["reason"] = how if ranked else ("no eligible candidate" if not s1 else "no compatible candidate")
        return None, diag
    base_names = [chosen.spec.name] + ([chosen.partner.name] if chosen.partner is not None else [])
    diag["provenance"] = {
        n: {k: (pool.views[n].provenance or {}).get(k, {} if k in ("output_lineage", "parameter_bindings") else [])
            for k in ("lineage", "source_columns", "output_lineage", "operators", "upstream_skills",
                      "parameter_bindings")}
        for n in base_names if n in pool.views
    }
    diag.update(mode=chosen.mode, base=base_names, sim=round(chosen.sim, 3),
                verifier_reason=chosen.verifier_reason or f"{how} (similarity {chosen.sim:.2f})",
                mode_note=_note(chosen))
    if chosen.mode == "exact":
        diag.update(hit=True, view=chosen.spec.name)
        return chosen.spec, diag
    spec, why = _materialize(graph, con, chosen, req)
    if spec is None:
        diag["reason"] = f"derived view failed validation: {why}"
        return None, diag
    diag.update(hit=True, view=spec.name)
    return spec, diag


# --------------------------------------------------------------------------- #
# Admission, dedup, relations, retirement
# --------------------------------------------------------------------------- #
def subsumes(a: ViewSpec, b: ViewSpec) -> bool:
    """a is strictly broader than b: same category, grain and lineage, b's outputs within a's, and a's filters a strict relaxation of b's (b = a + narrower filters)."""
    if a.category != b.category or a.grain_kind != b.grain_kind:
        return False
    if {norm_key(g) for g in a.grain} != {norm_key(g) for g in b.grain}:
        return False
    la = {t.lower() for t in (a.provenance or {}).get("lineage", a.source_tables)}
    lb = {t.lower() for t in (b.provenance or {}).get("lineage", b.source_tables)}
    if la != lb or not {norm_key(c) for c in b.output_columns} <= {norm_key(c) for c in a.output_columns}:
        return False
    fa = {norm_key(k): str(v) for k, v in (a.semantic_filters or {}).items()}
    fb = {norm_key(k): str(v) for k, v in (b.semantic_filters or {}).items()}
    strict = len(fb) > len(fa)
    for k, v in fa.items():
        if k not in fb:
            return False
        if contracts.is_range(v) and contracts.is_range(fb[k]):
            if not contracts.interval_contains(v, fb[k]):
                return False
            strict = strict or contracts.parse_interval(v) != contracts.parse_interval(fb[k])
        elif contracts.norm_value(v) != contracts.norm_value(fb[k]):
            return False
    return strict


def _active_peers(graph: ViewGraph, spec: ViewSpec) -> List[ViewSpec]:
    lin = (spec.provenance or {}).get("lineage") or spec.source_tables or []
    names = graph.lookup("table", lin) if lin else set(graph.views)
    return [graph.views[n] for n in sorted(names)
            if n != spec.name and n in graph.views and graph.views[n].status == "active"]


def admit(graph: ViewGraph, spec: ViewSpec, con, scope: Scope, *, tests_fn: Optional[Callable] = None,
          describe_fn: Optional[Callable] = None, origin: str = "", created: Optional[Dict] = None
          ) -> Tuple[str, str]:
    """Try to turn an in-graph view into a persistent skill. Returns (outcome, detail): admitted | duplicate (detail = existing skill) | equivalent (detail = existing skill) | rejected (detail = reason). The caller removes non-admitted views. Cheap checks (derivation, completeness, hash dedup, result equivalence) run before any LLM call (generated tests, description)."""
    contracts.derive(con, graph, spec, scope)
    if origin:
        spec.provenance["origin"] = origin
    if created:
        spec.provenance.update(created)
    why = contracts.completeness(spec)
    if why:
        return "rejected", "incomplete contract: " + ", ".join(why)
    dups = [n for n in graph.lookup("hash", [spec.sql_hash])
            if n != spec.name and graph.views[n].status == "active"]
    if dups:
        return "duplicate", dups[0]
    sig = contracts.contract_signature(spec)
    rsig = None
    conflicts, broader, narrower, superseded = [], [], [], []
    for p in _active_peers(graph, spec) + [v for v in graph.views.values() if v.status == "retired"]:
        if contracts.completeness(p) and p.status == "active":
            continue
        psig = contracts.contract_signature(p)
        if psig == sig:
            if p.status == "retired":
                superseded.append(p.name)
                continue
            if contracts.provenance_signature(p) != contracts.provenance_signature(spec):
                continue
            rsig = rsig or contracts.result_signature(con, graph, spec)
            prs = contracts.result_signature(con, graph, p)
            if rsig and prs and rsig == prs:
                return "equivalent", p.name
            if rsig and prs:
                conflicts.append(p.name)
        elif p.status == "active" and subsumes(p, spec):
            broader.append(p.name)
        elif p.status == "active" and subsumes(spec, p):
            narrower.append(p.name)
    if tests_fn is not None:
        try:
            tests = tests_fn(spec)
        except Exception:  # noqa: BLE001 — a test-generation failure must not block admission
            tests = None
        if tests:
            spec.validation = contracts.validate(con, graph, spec, tests=tests)
            if not spec.validation.get("passed"):
                return "rejected", "; ".join(spec.validation.get("failures", []))[:300]
    if describe_fn is not None:
        try:
            describe_fn(spec)
        except Exception:  # noqa: BLE001
            pass
    spec.status = "active"
    for n in conflicts:
        graph.add_relation(spec.name, n, "CONFLICTS_WITH")
    for n in broader:
        graph.add_relation(n, spec.name, "SUBSUMES")
    for n in narrower:
        graph.add_relation(spec.name, n, "SUBSUMES")
    for n in superseded:
        graph.add_relation(spec.name, n, "SUPERSEDES")
    return "admitted", spec.name


def merge_into(graph: ViewGraph, dup: str, canonical: str, alias_note: str = ""):
    """Drop view `dup` in favour of the existing skill `canonical`: in-graph views that read `dup` are rewritten to read `canonical` (their SQL and depends_on)."""
    for w in list(graph.views.values()):
        if w.name != dup and dup in (w.depends_on or []):
            old = dataclasses.replace(w)
            w.body_sql = contracts.rename_table_refs(w.body_sql, dup, canonical, w.dialect or "sqlite")
            graph.reindex(w.name, old)
            graph.set_depends_on(w.name, [canonical if d == dup else d for d in w.depends_on])
    can = graph.views.get(canonical)
    if can is not None and alias_note:
        aliases = can.provenance.setdefault("aliases", [])
        if alias_note not in aliases:
            aliases.append(alias_note)
    graph.remove_view(dup)


def retire_if_harmful(graph: ViewGraph, spec: ViewSpec, min_negative: int = 2) -> bool:
    """Retire a skill whose skill-level evidence is net-negative. A newer active skill with the same contract SUPERSEDES it. Its dependents become ineligible through the dependency check."""
    ev = spec.evidence or {}
    neg, pos = int(ev.get("negative", 0)), int(ev.get("positive", 0))
    if spec.status != "active" or neg < min_negative or neg <= pos:
        return False
    spec.status = "retired"
    spec.provenance["retired_at"] = contracts.now_iso()
    spec.provenance["retired_reason"] = f"net-negative evidence ({pos} good, {neg} harmful)"
    sig = contracts.contract_signature(spec)
    for p in graph.views.values():
        if p is not spec and p.status == "active" and contracts.contract_signature(p) == sig:
            graph.add_relation(p.name, spec.name, "SUPERSEDES")
    return True


# --------------------------------------------------------------------------- #
# Schema versioning (refresh) and cross-database portability
# --------------------------------------------------------------------------- #
def _topo(graph: ViewGraph) -> List[ViewSpec]:
    try:
        return graph.topo_closure(list(graph.views))
    except Exception:  # noqa: BLE001
        return list(graph.views.values())


def refresh(graph: ViewGraph, con, scope: Scope) -> Dict[str, int]:
    """Bring loaded skills (seed graphs, older runs) to contract v3 and the current schema. Skills whose contract is legacy, or whose lineage tables changed, are re-derived and re-validated. Those that no longer pass become 'stale' (kept, never reused). Legacy AV exploratory chunk views are marked stale outright: they were never promoted."""
    stats = {"current": 0, "upgraded": 0, "stale": 0}
    for spec in _topo(graph):
        if spec.status in ("retired", "stale"):
            continue
        prov = spec.provenance or {}
        if not prov.get("origin") and _LEGACY_AV.match(spec.name) and not spec.output_columns:
            spec.status = "stale"
            spec.provenance["stale_reason"] = "legacy AV exploratory view (never promoted)"
            stats["stale"] += 1
            continue
        fps = prov.get("table_fingerprints") or {}
        current = (int(prov.get("contract_version", 0) or 0) >= contracts.CONTRACT_VERSION and fps
                   and all(scope.table_fp.get(t) == fp for t, fp in fps.items())
                   and all(scope.data_fp.get(t) == d for t, d in (prov.get("data_fingerprints") or {}).items()))
        if current and not contracts.completeness(spec):
            stats["current"] += 1
            continue
        prev_hash = spec.sql_hash
        contracts.derive(con, graph, spec, scope)
        spec.provenance.setdefault("origin", "legacy")
        spec.provenance["refreshed_at"] = contracts.now_iso()
        if prev_hash and prev_hash != spec.sql_hash:
            spec.version = int(spec.version or 1) + 1
        if contracts.completeness(spec):
            spec.status = "stale"
            spec.provenance["stale_reason"] = "; ".join(contracts.completeness(spec))
            stats["stale"] += 1
        else:
            spec.status = "active"
            stats["upgraded"] += 1
    return stats


def port(src: ViewGraph, dst: ViewGraph, dst_con, dst_scope: Scope) -> Dict[str, str]:
    """Copy skills from another database's registry when every table they read exists in the destination with an identical interface (same table fingerprint). Transpiles across dialects, re-derives and re-validates on the destination, and admits through the usual dedup. Evidence is not carried over (it is database-specific). Returns {source skill: outcome}."""
    out: Dict[str, str] = {}
    renamed: Dict[str, str] = {}
    for spec in _topo(src):
        if spec.status != "active" or contracts.completeness(spec):
            continue
        prov = spec.provenance or {}
        fps = prov.get("table_fingerprints") or {}
        if not fps or any(dst_scope.table_fp.get(t) != fp for t, fp in fps.items()):
            out[spec.name] = "tables differ"
            continue
        if any(d not in renamed for d in spec.depends_on):
            out[spec.name] = "dependency not ported"
            continue
        new = copy.deepcopy(spec)
        new.name = _unique_name(dst, spec.name)
        new.depends_on = [renamed[d] for d in spec.depends_on]
        body = spec.body_sql
        for d in spec.depends_on:
            if renamed[d] != d:
                body = contracts.rename_table_refs(body, d, renamed[d], spec.dialect or "sqlite")
        if (spec.dialect or "sqlite") != dst_scope.dialect:
            try:
                body = sqlglot.transpile(body, read=spec.dialect, write=dst_scope.dialect)[0]
            except Exception:  # noqa: BLE001
                out[spec.name] = "transpile failed"
                continue
        new.body_sql, new.dialect, new.status = body, dst_scope.dialect, "exploratory"
        new.validated_on, new.counter_examples, new.evidence = [], [], {}
        new.provenance = {"origin": "ported", "ported_from": {"db_id": prov.get("db_id", src.db_id),
                                                              "skill_id": spec.skill_id, "name": spec.name},
                          "created_at": contracts.now_iso()}
        dst.add_view(new)
        outcome, detail = admit(dst, new, dst_con, dst_scope)
        if outcome == "admitted":
            renamed[spec.name] = new.name
        else:
            dst.remove_view(new.name)
            if outcome in ("duplicate", "equivalent"):
                renamed[spec.name] = detail
        out[spec.name] = outcome
    return out


def compact_diag(d: Dict, examples: int = 3) -> Dict:
    """Retrieval diagnostics small enough for result rows and the ledger: Stage-1 rejections become counts per reason (every stored view is checked, so the full map grows with the registry). Stage-2/3 rejections keep a few examples."""
    out = {k: v for k, v in d.items() if not k.endswith("_rejected")}
    s1 = d.get("stage1_rejected") or {}
    if s1:
        counts: Dict[str, int] = {}
        for why in s1.values():
            key = why.split(":", 1)[0]
            counts[key] = counts.get(key, 0) + 1
        out["stage1_rejected_counts"] = counts
    for k in ("stage2_rejected", "provenance_rejected", "stage3_rejected"):
        if d.get(k):
            items = list(d[k].items())
            out[k] = dict(items[:examples])
            if len(items) > examples:
                out[k + "_more"] = len(items) - examples
    return out


__all__ = ["eligible", "stage1", "stage2", "provenance_compatible", "stage3", "stage5", "retrieve", "admit", "merge_into", "compact_diag",
           "retire_if_harmful", "refresh", "port", "subsumes", "Match", "VectorIndex", "build_derived"]
