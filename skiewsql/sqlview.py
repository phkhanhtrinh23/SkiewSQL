"""
sqlview.py — the persistent view-memory layer for the *real* pipeline.

Reuses the graph primitives from core.py (ViewSpec, ViewGraph, compose_sql) but adds:
  * embedding-based retrieval (OpenAI embeddings via llm.Embedder) with the
    compatibility contract (the negative-reuse guard);
  * execution-grounded validation against a real SQLite connection (case-insensitive
    output-column check, dependency closure);
  * JSON persistence of one graph per db_id (so the library survives across runs).

A node `v = <skill s, db D, CTE, contract, inputs, outputs, validation>` is exactly the
ViewSpec dataclass; edges INSTANTIATES (skill->view) and DEPENDS_ON (view->view) live in
the ViewGraph.
"""
from __future__ import annotations

import json
import os
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


def compatible(spec: ViewSpec, req: ViewRequest, use_guard: bool = True) -> Tuple[bool, str]:
    if spec.category != req.category:
        return False, "category mismatch"
    if not _lower_set(req.required_outputs).issubset(_lower_set(spec.output_columns)):
        return False, "required outputs not exposed"
    # grain must be exact-or-finer: every required key must be available to group on
    if req.required_grain and not _lower_set(req.required_grain).issubset(_lower_set(spec.grain)):
        return False, "grain too coarse"
    if use_guard:
        sf = {k.lower(): str(v).lower() for k, v in dict(spec.semantic_filters).items()}
        rf = {k.lower(): str(v).lower() for k, v in dict(req.required_filters).items()}
        if sf != rf:
            return False, f"semantic-filter mismatch {sf} != {rf}"
    return True, "ok"


def retrieve(graph: ViewGraph, req: ViewRequest, embedder: Embedder,
             tau: float = 0.55, use_guard: bool = True) -> Tuple[Optional[ViewSpec], Dict]:
    """Return (reused_spec_or_None, diagnostics) using embedding similarity + guard."""
    best, best_sim, best_reason = None, -1.0, "no candidate in graph"
    for cand in graph.candidates(req.category):
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
# Execution-grounded validation
# --------------------------------------------------------------------------- #
def validate_view(con: sqlite3.Connection, graph: ViewGraph, spec: ViewSpec,
                  timeout_rows: int = 5) -> Tuple[bool, str]:
    """Execute the view with its in-graph dependency closure; confirm declared outputs."""
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
    data = {"db_id": graph.db_id, "views": [asdict(v) for v in graph.views.values()]}
    json.dump(data, open(path, "w"), indent=2)


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
    return g


__all__ = ["compatible", "retrieve", "validate_view", "compose_sql",
           "save_graph", "load_graph", "ViewSpec", "ViewGraph", "ViewRequest"]
