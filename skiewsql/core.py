"""core.py — SkiewSQL engine. Components (paper §3-§5 of the SkiewSQL design):
  * ViewSpec        : a skill-driven, executable, schema-grounded CTE view node.
  * ViewGraph       : heterogeneous, self-growing graph of skills + instantiated views (networkx DiGraph. INSTANTIATES + DEPENDS_ON edges), plus the skill-registry structure: table nodes (READS_TABLE), structural indexes, skill relations (EQUIVALENT_TO / SUBSUMES / SPECIALIZES / SUPERSEDES / CONFLICTS_WITH) and episode/subgoal nodes. See registry.py.
  * validate_view   : execution-grounded validation against the real DB.
  * retrieve        : category + signature (compatibility contract) + semantic (TF-IDF) retrieval. The compatibility contract is the *negative-reuse guard*.
  * compose_sql     : topologically order chosen views into one WITH ... SELECT statement.

The "generate-on-miss" step instantiates a canonical ViewSpec from a view library (the deterministic stand-in for the AV-SQL CTEAgent/LLM) and validates it by execution."""
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
    grain: List[str]                    # key columns. [] => single-row / scalar
    semantic_filters: Dict[str, str] = field(default_factory=dict)  # e.g. {"status": "completed"}
    depends_on: List[str] = field(default_factory=list)             # other view names
    params: Dict[str, str] = field(default_factory=dict)
    description: str = ""                # "when to use" text -> retrieval embedding source
    # Layer-4 provenance: sub-goals this view was execution-correct for, and sub-goals it must NOT serve (learned from observed negative reuse). Both are NL strings used for embedding checks.
    validated_on: List[str] = field(default_factory=list)
    counter_examples: List[str] = field(default_factory=list)
    # Skill-registry contract v2 (contracts.py / registry.py). Every default keeps pre-registry JSON graphs loadable. An empty `grain` alone is ambiguous, so `grain_kind` says whether it means one row (scalar), a verified key (keyed), or unknown. Unknown is never reused.
    skill_id: str = ""                  # stable identity: hash of dialect + normalized SQL + dependency hashes
    sql_hash: str = ""
    grain_kind: str = "unknown"         # scalar | keyed | unknown
    dialect: str = "sqlite"
    status: str = "active"              # active | exploratory (this question only) | retired | stale
    version: int = 1
    aggregation: Dict[str, str] = field(default_factory=dict)   # output column -> sum/count/avg/.../key/none
    join_keys: List[str] = field(default_factory=list)          # "table.col=table.col" from JOIN ... ON
    provenance: Dict = field(default_factory=dict)              # origin, creating question, subgoal, fingerprints, model, prompt version
    validation: Dict = field(default_factory=dict)              # contract assertions, cardinality stats, generated tests
    evidence: Dict = field(default_factory=dict)                # counters per credit level + positive/negative subgoals

    def cte_clause(self) -> str:
        return f"{self.name} AS (\n{self.body_sql.strip()}\n)"


def norm_key(x) -> str:
    """Column/table key: lowercase alphanumerics only, inline comments dropped (same rule as sqlview._norm_name)."""
    s = str(x).strip().lower().split("/*", 1)[0].split("--", 1)[0]
    return "".join(ch for ch in s if ch.isalnum())


@dataclass
class ViewRequest:
    """A decomposed sub-goal: the intermediate relation a question step needs."""
    want_name: str                      # canonical key the planner is asking for
    category: str
    required_outputs: List[str]
    required_grain: List[str]
    required_filters: Dict[str, str]
    text: str                           # NL description for semantic match
    source_tables: List[str] = field(default_factory=list)   # base tables the sub-goal draws on
                                        # (for base-table compatibility under the atomic reuse policy)
    # Logical DAG contract emitted by the decomposer.  These names refer to earlier ViewRequests. The runner resolves them to the actual generated/reused ViewSpec names.
    depends_on: List[str] = field(default_factory=list)
    join_keys: List[str] = field(default_factory=list)
    relationship: str = ""              # e.g. many_to_one / one_to_one / aggregate_input
    may_read_base_tables: bool = True
    # AV-SQL N×1 requests are generated with the exploratory-view agent rather than the one-responsibility dependency-subgoal agent. Adaptive moderate questions create one request per schema chunk.
    holistic: bool = False
    # Filters this subgoal receives through its dependencies (e.g. it aggregates a `status = done` cohort built by an earlier subgoal). Used only to match stored skills, whose contracts carry the same inherited filters. Never shown to the generator (it would re-apply them).
    inherited_filters: Dict[str, str] = field(default_factory=dict)


# ----------------------------------------------------------------------------- #
# Graph
# ----------------------------------------------------------------------------- #
# Skill-to-skill relation edges kept beside DEPENDS_ON (registry.py maintains them). EQUIVALENT_TO and CONFLICTS_WITH are symmetric and stored in both directions.
RELATION_ETYPES = ("EQUIVALENT_TO", "SUBSUMES", "SPECIALIZES", "SUPERSEDES", "CONFLICTS_WITH")


class ViewGraph:
    def __init__(self, db_id: str):
        self.db_id = db_id
        # MultiDiGraph keyed by edge type: one pair of nodes can carry several relations (e.g. DEPENDS_ON and SPECIALIZES, or USED_SKILL and VALIDATED) without one overwriting the other.
        self.g = nx.MultiDiGraph()
        self.views: Dict[str, ViewSpec] = {}
        # Structural indexes (normalized key -> view names) so retrieval can look up by table, output, grain, or SQL hash without scanning every view.
        self.idx_table: Dict[str, set] = {}
        self.idx_output: Dict[str, set] = {}
        self.idx_grain: Dict[str, set] = {}
        self.idx_hash: Dict[str, set] = {}
        self.idx_category: Dict[str, set] = {}

    def _edge(self, u: str, v: str, etype: str):
        """Add a typed edge. The key is the edge type, so re-adding the same relation is idempotent."""
        self.g.add_edge(u, v, key=etype, etype=etype)

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
        self._edge(sk, vid, "INSTANTIATES")
        for dep in spec.depends_on:
            self._edge(vid, f"view::{dep}", "DEPENDS_ON")
        self._link_tables(spec)
        self._index(spec)

    def remove_view(self, name: str):
        """Remove a view node (used to roll back a view that failed validation)."""
        spec = self.views.pop(name, None)
        if spec is not None:
            self._unindex(spec)
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
        # Deterministic order: dependencies first, otherwise view insertion order. (Sorting a subgraph of self.g depended on PYTHONHASHSEED, because networkx iterates small subgraphs through a set. Relation edges such as EQUIVALENT_TO would also form cycles.)
        rank = {n: i for i, n in enumerate(self.views)}
        dep = nx.DiGraph()
        for n in sorted(wanted, key=rank.get):
            dep.add_node(n)
            for d in self.views[n].depends_on:
                if d in wanted:
                    dep.add_edge(d, n)
        return [self.views[n] for n in nx.lexicographical_topological_sort(dep, key=rank.get)]

    # --- registry structure: tables, indexes, relations, episodes ---------------
    def _link_tables(self, spec: ViewSpec):
        vid = f"view::{spec.name}"
        for t in spec.source_tables or []:
            tid = f"table::{str(t).lower()}"
            if tid not in self.g:
                self.g.add_node(tid, kind="table", name=str(t))
            self._edge(vid, tid, "READS_TABLE")

    def _index_keys(self, spec: ViewSpec):
        return (
            (self.idx_table, {norm_key(t) for t in (list(spec.source_tables or []) +
                                                    list((spec.provenance or {}).get("lineage") or []))}),
            (self.idx_output, {norm_key(c) for c in (spec.output_columns or [])}),
            (self.idx_grain, {norm_key(c) for c in (spec.grain or [])}),
            (self.idx_hash, {spec.sql_hash} if spec.sql_hash else set()),
            (self.idx_category, {spec.category}),
        )

    def _index(self, spec: ViewSpec):
        for idx, keys in self._index_keys(spec):
            for k in keys:
                if k:
                    idx.setdefault(k, set()).add(spec.name)

    def _unindex(self, spec: ViewSpec):
        for idx, keys in self._index_keys(spec):
            for k in keys:
                idx.get(k, set()).discard(spec.name)

    def reindex(self, name: str, old: Optional[ViewSpec] = None):
        """Refresh indexes, READS_TABLE and DEPENDS_ON edges after a view's fields changed in place. `old` is a snapshot of the fields before the change (its index keys are removed first)."""
        spec = self.views[name]
        if old is not None:
            self._unindex(old)
        vid = f"view::{name}"
        for _u, t, k in [(u, v, k) for u, v, k, d in self.g.out_edges(vid, keys=True, data=True)
                         if d.get("etype") in ("READS_TABLE", "DEPENDS_ON")]:
            self.g.remove_edge(vid, t, key=k)
        for dep in spec.depends_on:
            self._edge(vid, f"view::{dep}", "DEPENDS_ON")
        self._link_tables(spec)
        self._index(spec)

    def rename_view(self, old: str, new: str):
        """Rename a view, rewriting the depends_on lists (not the SQL) of views that reference it."""
        spec = self.views[old]
        relations = [(u, v, d.get("etype")) for u, v, d in
                     list(self.g.in_edges(f"view::{old}", data=True)) + list(self.g.out_edges(f"view::{old}", data=True))
                     if d.get("etype") in RELATION_ETYPES]
        self.remove_view(old)
        spec.name = new
        for w in self.views.values():
            if old in (w.depends_on or []):
                w.depends_on = [new if d == old else d for d in w.depends_on]
                self._edge(f"view::{w.name}", f"view::{new}", "DEPENDS_ON")
        self.add_view(spec)
        for u, v, et in relations:
            u = f"view::{new}" if u == f"view::{old}" else u
            v = f"view::{new}" if v == f"view::{old}" else v
            if u in self.g and v in self.g:
                self._edge(u, v, et)

    def lookup(self, index: str, keys) -> set:
        """Views whose `index` (table/output/grain/hash/category) contains ANY of `keys` (normalized)."""
        idx = getattr(self, f"idx_{index}")
        out = set()
        for k in keys:
            out |= idx.get(k if index in ("hash", "category") else norm_key(k), set())
        return out

    def add_relation(self, src: str, dst: str, etype: str):
        if etype not in RELATION_ETYPES or src == dst:
            return
        u, v = f"view::{src}", f"view::{dst}"
        if u in self.g and v in self.g:
            self._edge(u, v, etype)
            if etype in ("EQUIVALENT_TO", "CONFLICTS_WITH"):
                self._edge(v, u, etype)

    def related(self, name: str, etype: str) -> List[str]:
        vid = f"view::{name}"
        if vid not in self.g:
            return []
        return [v.split("::", 1)[1] for _u, v, d in self.g.out_edges(vid, data=True)
                if d.get("etype") == etype and v.startswith("view::")]

    def relations(self) -> List[Tuple[str, str, str]]:
        return [(u.split("::", 1)[1], v.split("::", 1)[1], d["etype"])
                for u, v, d in self.g.edges(data=True)
                if d.get("etype") in RELATION_ETYPES]

    def episodes(self) -> List[Dict]:
        """Episode nodes with their links, in the add_episode argument format (used for persistence)."""
        out = []
        for n, d in self.g.nodes(data=True):
            if d.get("kind") != "episode":
                continue
            links: Dict[str, List[str]] = {}
            subgoals: Dict[str, List[str]] = {}
            for _u, v, ed in self.g.out_edges(n, data=True):
                if v.startswith("view::"):
                    links.setdefault(ed["etype"], []).append(v.split("::", 1)[1])
                elif ed.get("etype") == "REQUESTED":
                    sg = self.g.nodes[v].get("name", v.rsplit("::", 1)[-1])
                    subgoals[sg] = [u.split("::", 1)[1] for u, _v, e2 in self.g.in_edges(v, data=True)
                                    if e2.get("etype") == "GENERATED_FROM"]
            out.append({"id": n.split("::", 1)[1], "links": links, "subgoals": subgoals})
        return out

    def add_episode(self, episode_id: str, links: Dict[str, List[str]], subgoals: Dict[str, List[str]] = None):
        """Episode (one answered question) node. `links` maps an edge type (USED_SKILL, GENERATED_SKILL, VALIDATED) to view names. `subgoals` maps each requested subgoal name to the views generated from it (Question -REQUESTED-> Subgoal, Skill -GENERATED_FROM-> Subgoal)."""
        eid = f"episode::{episode_id}"
        self.g.add_node(eid, kind="episode")
        for etype, names in (links or {}).items():
            for n in names:
                if f"view::{n}" in self.g:
                    self._edge(eid, f"view::{n}", etype)
        for sg, made in (subgoals or {}).items():
            sid = f"subgoal::{episode_id}::{sg}"
            self.g.add_node(sid, kind="subgoal", name=sg)
            self._edge(eid, sid, "REQUESTED")
            for n in made:
                if f"view::{n}" in self.g:
                    self._edge(f"view::{n}", sid, "GENERATED_FROM")

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
        # include deps already in graph. The new spec is appended last
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
