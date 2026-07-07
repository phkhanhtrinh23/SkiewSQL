"""
core.py — SkiewSQL engine.

Components (paper §3-§5 of the SkiewSQL design):
  * ViewSpec        : a skill-driven, executable, schema-grounded CTE view node.
  * ViewGraph       : heterogeneous, self-growing graph of skills + instantiated views
                      (networkx DiGraph; INSTANTIATES + DEPENDS_ON edges).
  * validate_view   : execution-grounded validation against the real DB.
  * retrieve        : category + signature (compatibility contract) + semantic (TF-IDF)
                      retrieval. The compatibility contract is the *negative-reuse guard*.
  * compose_sql     : topologically order chosen views into one WITH ... SELECT statement.

The "generate-on-miss" step instantiates a canonical ViewSpec from a view library
(the deterministic stand-in for the AV-SQL CTEAgent/LLM) and validates it by execution.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ----------------------------------------------------------------------------- #
# View node
# ----------------------------------------------------------------------------- #
@dataclass
class ViewSpec:
    name: str
    category: str                       # SEL/SEM/AGG/JOIN/RANK/WIN/RESHAPE/SET/REC/NORM
    body_sql: str                       # the SELECT ... that defines the CTE body
    source_tables: List[str]
    output_columns: List[str]
    grain: List[str]                    # key columns; [] => single-row / scalar
    semantic_filters: Dict[str, str] = field(default_factory=dict)  # e.g. {"status": "completed"}
    depends_on: List[str] = field(default_factory=list)             # other view names
    params: Dict[str, str] = field(default_factory=dict)
    description: str = ""                # "when to use" text -> retrieval embedding source
    # Layer-4 provenance: sub-goals this view was execution-correct for, and sub-goals it must NOT
    # serve (learned from observed negative reuse). Both are NL strings used for embedding checks.
    validated_on: List[str] = field(default_factory=list)
    counter_examples: List[str] = field(default_factory=list)

    def cte_clause(self) -> str:
        return f"{self.name} AS (\n{self.body_sql.strip()}\n)"


@dataclass
class ViewRequest:
    """A decomposed sub-goal: the intermediate relation a question step needs."""
    want_name: str                      # canonical key the planner is asking for
    category: str
    required_outputs: List[str]
    required_grain: List[str]
    required_filters: Dict[str, str]
    text: str                           # NL description for semantic match


# ----------------------------------------------------------------------------- #
# Graph
# ----------------------------------------------------------------------------- #
class ViewGraph:
    def __init__(self, db_id: str):
        self.db_id = db_id
        self.g = nx.DiGraph()
        self.views: Dict[str, ViewSpec] = {}

    # --- skills are global capability nodes -----------------------------------
    def _ensure_skill(self, category: str):
        sk = f"skill::{category}"
        if sk not in self.g:
            self.g.add_node(sk, kind="skill", category=category)
        return sk

    def add_view(self, spec: ViewSpec):
        vid = f"view::{spec.name}"
        self.views[spec.name] = spec
        self.g.add_node(vid, kind="view", category=spec.category, db_id=self.db_id)
        sk = self._ensure_skill(spec.category)
        self.g.add_edge(sk, vid, etype="INSTANTIATES")
        for dep in spec.depends_on:
            self.g.add_edge(vid, f"view::{dep}", etype="DEPENDS_ON")

    def remove_view(self, name: str):
        """Remove a view node (used to roll back a view that failed validation)."""
        self.views.pop(name, None)
        vid = f"view::{name}"
        if vid in self.g:
            self.g.remove_node(vid)

    def has(self, name: str) -> bool:
        return name in self.views

    def candidates(self, category: str) -> List[ViewSpec]:
        return [v for v in self.views.values() if v.category == category]

    def topo_closure(self, names: List[str]) -> List[ViewSpec]:
        """Return specs for `names` plus all transitive deps, in dependency order."""
        wanted = set()
        stack = list(names)
        while stack:
            n = stack.pop()
            if n in wanted:
                continue
            wanted.add(n)
            stack.extend(self.views[n].depends_on)
        sub = self.g.subgraph([f"view::{n}" for n in wanted])
        order = [n.split("::", 1)[1] for n in nx.topological_sort(sub.reverse())]
        # reverse() so deps come before dependents
        return [self.views[n] for n in order]

    # --- metrics helpers ------------------------------------------------------
    def n_views(self) -> int:
        return len(self.views)

    def n_edges(self, etype: str) -> int:
        return sum(1 for *_e, d in self.g.edges(data=True) if d.get("etype") == etype)


# ----------------------------------------------------------------------------- #
# Validation (execution-grounded)
# ----------------------------------------------------------------------------- #
def validate_view(con: sqlite3.Connection, graph: ViewGraph, spec: ViewSpec) -> Tuple[bool, str]:
    """Execute the view (with its dependency closure) and confirm declared outputs."""
    try:
        specs = graph.topo_closure(spec.depends_on + []) if spec.depends_on else []
        # include deps already in graph; the new spec is appended last
        chosen = {s.name: s for s in specs}
        chosen[spec.name] = spec
        ordered = _order_specs(graph, list(chosen.values()))
        with_clause = ",\n".join(s.cte_clause() for s in ordered)
        prefix = "WITH RECURSIVE" if any(s.category == "REC" for s in ordered) else "WITH"
        sql = f"{prefix} {with_clause}\nSELECT * FROM {spec.name} LIMIT 5"
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        cur.fetchall()
        missing = [c for c in spec.output_columns if c not in cols]
        if missing:
            return False, f"declared outputs missing from result: {missing} (got {cols})"
        return True, "ok"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def _order_specs(graph: ViewGraph, specs: List[ViewSpec]) -> List[ViewSpec]:
    by_name = {s.name: s for s in specs}
    sub = nx.DiGraph()
    for s in specs:
        sub.add_node(s.name)
        for d in s.depends_on:
            if d in by_name:
                sub.add_edge(d, s.name)  # dep -> dependent
    return [by_name[n] for n in nx.topological_sort(sub)]


# ----------------------------------------------------------------------------- #
# Retrieval (category + compatibility contract + semantic similarity)
# ----------------------------------------------------------------------------- #
def _semantic_sim(req_text: str, cand_text: str) -> float:
    if not req_text.strip() or not cand_text.strip():
        return 0.0
    vec = TfidfVectorizer().fit([req_text, cand_text])
    m = vec.transform([req_text, cand_text])
    return float(cosine_similarity(m[0], m[1])[0][0])


def compatible(spec: ViewSpec, req: ViewRequest, use_guard: bool = True) -> Tuple[bool, str]:
    """The negative-reuse guard. Returns (is_compatible, reason)."""
    if spec.category != req.category:
        return False, "category mismatch"
    if not set(req.required_outputs).issubset(set(spec.output_columns)):
        return False, "required outputs not exposed"
    # grain: node must be exact or finer (superset of keys) so we can roll up
    if not set(req.required_grain).issubset(set(spec.grain)):
        return False, "grain too coarse"
    if use_guard:
        # filters must match exactly: a different/absent semantic filter changes meaning
        if dict(spec.semantic_filters) != dict(req.required_filters):
            return False, f"semantic-filter mismatch {spec.semantic_filters} != {req.required_filters}"
    return True, "ok"


def retrieve(graph: ViewGraph, req: ViewRequest, tau: float = 0.25,
             use_guard: bool = True) -> Tuple[Optional[ViewSpec], Dict]:
    """Return (reused_spec_or_None, diagnostics)."""
    best, best_sim, best_reason = None, -1.0, "no candidate"
    for cand in graph.candidates(req.category):
        ok, reason = compatible(cand, req, use_guard=use_guard)
        if not ok:
            if best is None:
                best_reason = reason
            continue
        sim = _semantic_sim(req.text, cand.description or cand.name)
        if sim > best_sim:
            best, best_sim, best_reason = cand, sim, "compatible"
    if best is not None and best_sim >= tau:
        return best, {"hit": True, "sim": round(best_sim, 3), "view": best.name}
    return None, {"hit": False, "sim": round(max(best_sim, 0.0), 3), "reason": best_reason}


# ----------------------------------------------------------------------------- #
# Composition
# ----------------------------------------------------------------------------- #
def compose_sql(graph: ViewGraph, view_names: List[str], final_select: str) -> str:
    specs = graph.topo_closure(view_names)
    with_clause = ",\n".join(s.cte_clause() for s in specs)
    prefix = "WITH RECURSIVE" if any(s.category == "REC" for s in specs) else "WITH"
    return f"{prefix} {with_clause}\n{final_select.strip()}"
