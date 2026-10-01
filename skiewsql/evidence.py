"""evidence.py — credit assignment, episodes, and the evidence ledger.

A question's outcome is question-level evidence. It becomes skill-level evidence only for skills the executed final SQL actually used. The levels are kept apart:

    retrieved  -> shortlisted by retrieval for some request
    selected   -> chosen to serve a request
    included   -> defined in the final WITH clause
    referenced -> in the dependency closure of what the outer query reads
    executed   -> referenced, the final SQL executed, and the CTE body is exactly the stored body (a repair that rewrote the CTE breaks the link)
    causal     -> ablation: regenerating that subgoal changes the outcome (causal_win / causal_loss / neutral)

Only `executed` skills receive positive or negative outcomes. The final SQL itself is stored as an EPISODE (question, rewrite, subgoals, retrieved / generated skills, final SQL, result signature, correctness, errors and repairs), linked to the skills it used and created. It is not stored as a skill."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sqlglot import expressions as exp

from skiewsql import contracts
from skiewsql.core import ViewGraph, ViewSpec

LEVELS = ("retrieved", "selected", "included", "referenced", "executed")


# --------------------------------------------------------------------------- #
# Which CTEs did the final query really use?
# --------------------------------------------------------------------------- #
def cte_references(sql: str, dialect: str = "sqlite") -> Dict:
    """Parse the final SQL: CTE bodies, CTEs read by the outer query, and their CTE-to-CTE dependency closure. Names are lowercase. `parsed` is False when sqlglot cannot parse the query (then nothing is credited)."""
    tree = contracts.parse(sql or "", dialect)
    if tree is None:
        return {"parsed": False, "ctes": {}, "outer": set(), "closure": set()}
    w = contracts.with_of(tree)
    bodies = {c.alias.lower(): c.this for c in (w.expressions if w is not None else [])}
    outer = tree.copy()
    contracts.set_with(outer, None)
    refs = {t.name.lower() for t in outer.find_all(exp.Table)} & set(bodies)
    closure, stack = set(), list(refs)
    while stack:
        n = stack.pop()
        if n in closure:
            continue
        closure.add(n)
        for t in bodies[n].find_all(exp.Table):
            m = t.name.lower()
            if m in bodies and m not in closure:
                stack.append(m)
    return {"parsed": True, "ctes": {n: b.sql(dialect=dialect) for n, b in bodies.items()},
            "outer": refs, "closure": closure}


def assign_credit(graph: ViewGraph, final_sql: Optional[str], executed: bool,
                  selected: List[str], retrieved: List[str] = (), dialect: str = "sqlite") -> Dict[str, Dict]:
    """Credit levels per view name for one question. Covers every view that was retrieved, selected, or appears in the final WITH clause and exists in the graph."""
    refs = cte_references(final_sql or "", dialect)
    names = list(dict.fromkeys(list(retrieved) + list(selected) +
                               [v for v in graph.views if v.lower() in refs["ctes"]]))
    sel = {n.lower() for n in selected}
    ret = {n.lower() for n in retrieved}
    out = {}
    for n in names:
        spec = graph.views.get(n)
        if spec is None:
            continue
        low = n.lower()
        included = low in refs["ctes"]
        referenced = low in refs["closure"]
        as_stored = bool(referenced and contracts.normalize_sql(refs["ctes"][low], dialect)
                         == contracts.normalize_sql(spec.body_sql, dialect))
        out[n] = {"retrieved": low in ret, "selected": low in sel, "included": included,
                  "referenced": referenced, "executed": bool(executed and as_stored),
                  "modified_by_repair": bool(referenced and not as_stored)}
    return out


def replace_cte_body(final_sql: str, name: str, old_body: str, new_body: str,
                     dialect: str = "sqlite") -> Optional[str]:
    """Swap the body of CTE `name` in the final query (used by ablation). Tries a verbatim replacement first so the rest of the query is byte-identical. Falls back to an AST edit."""
    old = (old_body or "").strip()
    if old and final_sql.count(old) == 1:
        return final_sql.replace(old, new_body.strip(), 1)
    tree = contracts.parse(final_sql, dialect)
    new = contracts.parse(new_body, dialect)
    w = contracts.with_of(tree) if tree is not None else None
    if w is None or new is None:
        return None
    for c in w.expressions:
        if c.alias.lower() == name.lower():
            c.set("this", new)
            return tree.sql(dialect=dialect)
    return None


def skill_outcome(question_label: Optional[bool], ablation: Optional[str], trivial: bool = False) -> str:
    """Skill-level outcome for an EXECUTED skill. Ablation, when conclusive, decides. Otherwise the outcome is association with the question label. A trivial projection is never blamed (reading it equals reading its base table)."""
    if ablation == "causal_win":
        return "positive"
    if ablation == "causal_loss":
        return "negative"
    if question_label is None:
        return "none"
    if ablation == "neutral":
        return "positive" if question_label else "none"
    if question_label:
        return "positive"
    return "none" if trivial else "negative"


def update_skill(spec: ViewSpec, levels: Dict[str, bool], outcome: str, subgoal: str, question: str,
                 ablation: Optional[str] = None, qid: str = "", cap: int = 10):
    """Fold one question's credit into the skill's evidence summary and its validated_on / counter_examples lists (those two lists only change on a skill-level outcome)."""
    ev = spec.evidence if spec.evidence is not None else {}
    for lvl in LEVELS:
        if levels.get(lvl):
            ev[lvl] = int(ev.get(lvl, 0)) + 1
    if ablation in ("causal_win", "causal_loss", "neutral", "divergent", "inconclusive"):
        ev[ablation] = int(ev.get(ablation, 0)) + 1
    if outcome in ("positive", "negative"):
        ev[outcome] = int(ev.get(outcome, 0)) + 1
        key = "positive_subgoals" if outcome == "positive" else "negative_subgoals"
        lst = list(ev.get(key, []))
        if subgoal and subgoal not in lst:
            ev[key] = (lst + [subgoal])[-cap:]
        if outcome == "positive" and question not in spec.validated_on:
            spec.validated_on = (spec.validated_on + [question])[-cap:]
        elif outcome == "negative" and question not in spec.counter_examples:
            spec.counter_examples = (spec.counter_examples + [question])[-cap:]
    if levels.get("executed"):
        ev["last_used"] = qid
    spec.evidence = ev


# --------------------------------------------------------------------------- #
# Episodes and the ledger (append-only JSONL next to the grown graph)
# --------------------------------------------------------------------------- #
def result_signature(rows) -> Optional[str]:
    try:
        canon = sorted(tuple(str(round(x, 6) if isinstance(x, float) else x) for x in r) for r in rows)
        return hashlib.sha1(json.dumps(canon).encode()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


class JsonlStore:
    """Buffered append-only JSONL records. `flush(path)` appends and clears the buffer."""

    def __init__(self):
        self.records: List[Dict] = []

    def add(self, rec: Dict):
        self.records.append(rec)

    def flush(self, path: str):
        if not self.records:
            return
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            for r in self.records:
                fh.write(json.dumps(r, default=str) + "\n")
        self.records = []

    @staticmethod
    def load(path: str) -> List[Dict]:
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]


class EvidenceLedger(JsonlStore):
    """One record per (question, skill) with every credit level, the ablation result, the question-level label, and the skill-level outcome. Also retrieval events (shortlists and rejections) per request."""


class EpisodeStore(JsonlStore):
    """One record per answered question: the final SQL lives here, not in the skill registry."""


@dataclass
class Episode:
    episode_id: str
    qid: str
    db_id: str
    question: str
    rewrite: str = ""
    route: str = ""
    subgoals: List[Dict] = field(default_factory=list)
    retrieved: Dict[str, List[str]] = field(default_factory=dict)
    reused: Dict[str, Dict] = field(default_factory=dict)          # request -> {base, mode, view}
    generated: List[str] = field(default_factory=list)
    final_sql: Optional[str] = None
    executed: bool = False
    result_signature: Optional[str] = None
    row_count: Optional[int] = None
    correct: Optional[bool] = None
    label_source: str = "gold"
    label: Optional[bool] = None
    errors: List[str] = field(default_factory=list)
    repairs: List[Dict] = field(default_factory=list)
    credit: Dict[str, Dict] = field(default_factory=dict)
    ablation: Dict[str, str] = field(default_factory=dict)
    admitted: Dict[str, str] = field(default_factory=dict)          # view -> outcome/detail
    created_at: str = field(default_factory=contracts.now_iso)


__all__ = ["cte_references", "assign_credit", "replace_cte_body", "skill_outcome", "update_skill",
           "EvidenceLedger", "EpisodeStore", "Episode", "result_signature", "LEVELS"]
