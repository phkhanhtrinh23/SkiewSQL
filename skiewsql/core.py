"""Core data structures for the SkiewSQL pipeline.

The paper stores one flat, indexed skill registry per database.  Dependencies
are fields of a :class:`ViewSpec`; they are not duplicated in a separate
topology. Executed rows are transient validation evidence and are
never stored here.

Components:
  * ViewSpec        : one executable, schema-grounded skill view.
  * SkillRegistry   : the per-database ViewSpec catalog and structural indexes.
  * validate_view   : execution-grounded validation against the real DB.
  * retrieve        : category + signature (compatibility contract) + semantic (TF-IDF) retrieval. The compatibility contract is the *negative-reuse guard*.
  * compose_sql     : topologically order chosen views into one WITH ... SELECT statement.

The "generate-on-miss" step instantiates a canonical ViewSpec from a view library (the deterministic stand-in for the AV-SQL CTEAgent/LLM) and validates it by execution."""
from __future__ import annotations

import sqlite3
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

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
    # Skill-registry contract v3. An empty `grain` alone is ambiguous, so
    # `grain_kind` records scalar, keyed, or unknown. Unknown is not reused.
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
    # Relational operators that a stored skill must contain. Category captures the dominant operation, while this list can also require supporting structure such as both join and aggregate.
    required_operators: List[str] = field(default_factory=list)


# ----------------------------------------------------------------------------- #
# Per-database registry
# ----------------------------------------------------------------------------- #
RELATION_ETYPES = ("SUBSUMES", "CONFLICTS_WITH", "SUPERSEDES")


class SkillRegistry:
    """Persistent ViewSpecs and lookup indexes for exactly one database.

    ``_relations`` retains optional admission hints such as conflicts and
    supersession as ordinary metadata. Dependency closure is computed directly
    from ``ViewSpec.depends_on``.
    """

    def __init__(self, db_id: str):
        self.db_id = db_id
        self.views: Dict[str, ViewSpec] = {}
        self._relations: set[Tuple[str, str, str]] = set()
        # Structural indexes (normalized key -> view names) so retrieval can look up by table, output, grain, or SQL hash without scanning every view.
        self.idx_table: Dict[str, set] = {}
        self.idx_output: Dict[str, set] = {}
        self.idx_grain: Dict[str, set] = {}
        self.idx_hash: Dict[str, set] = {}
        self.idx_category: Dict[str, set] = {}
        self.idx_skill_id: Dict[str, set] = {}
        self.idx_description: Dict[str, set] = {}

    @property
    def skills(self) -> Dict[str, ViewSpec]:
        """Canonical skill-id lookup; exploratory records fall back to name."""
        return {(spec.skill_id or spec.name): spec for spec in self.views.values()}

    def add_view(self, spec: ViewSpec):
        old = self.views.get(spec.name)
        if old is not None:
            self._unindex(old)
        self.views[spec.name] = spec
        self._index(spec)

    def remove_view(self, name: str):
        """Remove a view node (used to roll back a view that failed validation)."""
        spec = self.views.pop(name, None)
        if spec is not None:
            self._unindex(spec)
        self._relations = {r for r in self._relations if name not in r[:2]}

    def set_depends_on(self, name: str, deps: List[str]):
        """Update the dependency names stored in a ViewSpec."""
        self.views[name].depends_on = list(dict.fromkeys(deps))

    def check_consistency(self) -> List[str]:
        """Return dependency-contract errors (empty means consistent)."""
        out = []
        for name, spec in self.views.items():
            missing = [d for d in spec.depends_on or [] if d not in self.views]
            if missing:
                out.append(f"{name}: missing dependencies {sorted(missing)}")
            if name in (spec.depends_on or []):
                out.append(f"{name}: depends on itself")
        try:
            self.topo_closure(list(self.views))
        except ValueError as exc:
            out.append(str(exc))
        return out

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
        # Deterministic dependency-first order; no materialized graph.
        rank = {n: i for i, n in enumerate(self.views)}
        ordered, temporary, permanent = [], set(), set()

        def visit(n):
            if n in permanent:
                return
            if n in temporary:
                raise ValueError(f"cyclic ViewSpec dependency at {n}")
            temporary.add(n)
            for d in sorted(self.views[n].depends_on, key=rank.get):
                if d in wanted:
                    visit(d)
            temporary.remove(n)
            permanent.add(n)
            ordered.append(n)

        for n in sorted(wanted, key=rank.get):
            visit(n)
        return [self.views[n] for n in ordered]

    # --- structural indexes ----------------------------------------------------
    def _index_keys(self, spec: ViewSpec):
        description_tokens = set(re.findall(r"[a-z0-9]+", (spec.description or "").lower()))
        return (
            (self.idx_table, {norm_key(t) for t in (list(spec.source_tables or []) +
                                                    list((spec.provenance or {}).get("lineage") or []))}),
            (self.idx_output, {norm_key(c) for c in (spec.output_columns or [])}),
            (self.idx_grain, {norm_key(c) for c in (spec.grain or [])}),
            (self.idx_hash, {spec.sql_hash} if spec.sql_hash else set()),
            (self.idx_category, {spec.category}),
            (self.idx_skill_id, {spec.skill_id} if spec.skill_id else set()),
            (self.idx_description, description_tokens),
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
        """Refresh indexes after a ViewSpec changed in place."""
        if old is not None:
            self._unindex(old)
        self._index(self.views[name])

    def rename_view(self, old: str, new: str):
        """Rename a view, rewriting the depends_on lists (not the SQL) of views that reference it."""
        spec = self.views[old]
        relations = list(self._relations)
        self.remove_view(old)
        spec.name = new
        self.add_view(spec)
        for w in list(self.views.values()):
            if old in (w.depends_on or []):
                self.set_depends_on(w.name, [new if d == old else d for d in w.depends_on])
        self._relations = {(new if u == old else u, new if v == old else v, et)
                           for u, v, et in relations}

    def lookup(self, index: str, keys) -> set:
        """View names whose selected index contains any requested key."""
        idx = getattr(self, f"idx_{index}")
        out = set()
        for k in keys:
            out |= idx.get(k if index in ("hash", "category", "skill_id") else norm_key(k), set())
        return out

    def add_relation(self, src: str, dst: str, etype: str):
        if etype not in RELATION_ETYPES or src == dst:
            return
        if src in self.views and dst in self.views:
            self._relations.add((src, dst, etype))
            if etype == "CONFLICTS_WITH":
                self._relations.add((dst, src, etype))

    def related(self, name: str, etype: str) -> List[str]:
        return [dst for src, dst, kind in sorted(self._relations)
                if src == name and kind == etype]

    def relations(self) -> List[Tuple[str, str, str]]:
        return sorted(self._relations)

    # --- metrics helpers ------------------------------------------------------
    def n_views(self) -> int:
        return len(self.views)

    def n_edges(self, etype: str) -> int:
        if etype == "DEPENDS_ON":
            return sum(len(v.depends_on or []) for v in self.views.values())
        if etype == "READS_TABLE":
            return sum(len(v.source_tables or []) for v in self.views.values())
        return sum(1 for _u, _v, kind in self._relations if kind == etype)


# ----------------------------------------------------------------------------- #
# Validation (execution-grounded)
# ----------------------------------------------------------------------------- #
def validate_view(con: sqlite3.Connection, registry: SkillRegistry, spec: ViewSpec) -> Tuple[bool, str]:
    """Execute the view (with its dependency closure) and confirm declared outputs."""
    try:
        specs = registry.topo_closure(spec.depends_on + []) if spec.depends_on else []
        # include deps already in registry. The new spec is appended last
        chosen = {s.name: s for s in specs}
        chosen[spec.name] = spec
        ordered = _order_specs(registry, list(chosen.values()))
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


def _order_specs(registry: SkillRegistry, specs: List[ViewSpec]) -> List[ViewSpec]:
    by_name = {s.name: s for s in specs}
    return [s for s in registry.topo_closure(list(by_name)) if s.name in by_name]


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


def retrieve(registry: SkillRegistry, req: ViewRequest, tau: float = 0.25,
             use_guard: bool = True) -> Tuple[Optional[ViewSpec], Dict]:
    """Return (reused_spec_or_None, diagnostics)."""
    best, best_sim, best_reason = None, -1.0, "no candidate"
    for cand in registry.candidates(req.category):
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
def compose_sql(registry: SkillRegistry, view_names: List[str], final_select: str) -> str:
    specs = registry.topo_closure(view_names)
    with_clause = ",\n".join(s.cte_clause() for s in specs)
    prefix = "WITH RECURSIVE" if any(s.category == "REC" for s in specs) else "WITH"
    return f"{prefix} {with_clause}\n{final_select.strip()}"
