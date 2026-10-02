"""SkiewSQL skill-graph reuse for AV-SQL's CTE step.

A persistent, per-DB graph of previously-accepted CTEs ("skills"). At the CTE step, retrieve embedding-similar CTEs proven on the SAME database and offer them to the CTE agent for reuse. After a fresh CTE is generated, deposit it. This grafts SkiewSQL's memory/reuse onto AV-SQL's pipeline WITHOUT changing any other step.

Enabled only when the config has a `skill_graph:` block, so base AV-SQL is unaffected. Designed for n_processes=1 (sequential graph growth, no write races)."""
import os, json, threading
from typing import List, Dict

_MODEL = None
_MODEL_LOCK = threading.Lock()
_GRAPHS: Dict[str, "SkillGraph"] = {}


def _embedder():
    global _MODEL
    if _MODEL is None:
        with _MODEL_LOCK:
            if _MODEL is None:
                from sentence_transformers import SentenceTransformer
                _MODEL = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    return _MODEL


def _cos(a, b):
    import numpy as np
    a = np.asarray(a, dtype="float32"); b = np.asarray(b, dtype="float32")
    na = (a @ a) ** 0.5; nb = (b @ b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return float(a @ b / (na * nb))


class SkillGraph:
    def __init__(self, path: str, threshold: float = 0.5, top_k: int = 2):
        self.path = path
        self.threshold = threshold
        self.top_k = top_k
        # {db_id: [ {question, tables:[...], cte_sql, emb:[...]}, ... ]}
        self.store: Dict[str, List[dict]] = {}
        if path and os.path.exists(path):
            try:
                self.store = json.load(open(path))
            except Exception:
                self.store = {}
        self._lock = threading.Lock()

    def _save(self):
        if not self.path:
            return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        json.dump(self.store, open(tmp, "w"))
        os.replace(tmp, self.path)

    def retrieve(self, db_id: str, question: str, chunk_tables: List[str]) -> List[dict]:
        entries = self.store.get(db_id, [])
        if not entries:
            return []
        qemb = _embedder().encode([question])[0].tolist()
        ct = set(t.lower() for t in (chunk_tables or []))
        scored = []
        for e in entries:
            sim = _cos(qemb, e["emb"])
            if sim < self.threshold:
                continue
            # prefer CTEs whose tables are available in this chunk (overlap), but keep any strong match
            overlap = len(ct & set(t.lower() for t in e.get("tables", []))) if ct else 0
            scored.append((overlap > 0, sim, e))
        # rank: table-relevant first, then similarity
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [e for _, _, e in scored[: self.top_k]]

    def render_hints(self, db_id: str, question: str, chunk_tables: List[str]) -> str:
        hits = self.retrieve(db_id, question, chunk_tables)
        if not hits:
            return ""
        s = ("\n###\nPROVEN REUSABLE CTEs from earlier questions on THIS database. "
             "If one computes a sub-result useful here, REUSE it verbatim (or lightly adapt "
             "table/column names to this schema). Do not force an irrelevant one.\n")
        for i, e in enumerate(hits):
            s += f"```cte\n{e['cte_sql'].strip()}\n```\n"
        return s

    def deposit(self, db_id: str, question: str, tables: List[str], cte_sql: str):
        cte_sql = (cte_sql or "").strip()
        if not cte_sql or len(cte_sql) < 15:
            return
        with self._lock:
            lst = self.store.setdefault(db_id, [])
            # dedup on exact SQL
            if any(e["cte_sql"].strip() == cte_sql for e in lst):
                return
            emb = _embedder().encode([question])[0].tolist()
            lst.append({"question": question[:400], "tables": list(tables or []),
                        "cte_sql": cte_sql, "emb": emb})
            self._save()

    def size(self):
        return sum(len(v) for v in self.store.values())


def get_graph(config) -> "SkillGraph":
    """Singleton per graph path. Returns None if config has no skill_graph block."""
    sg = config.get("skill_graph") if isinstance(config, dict) else None
    if not sg:
        return None
    path = sg.get("path", "")
    if path not in _GRAPHS:
        _GRAPHS[path] = SkillGraph(path,
                                   threshold=float(sg.get("threshold", 0.5)),
                                   top_k=int(sg.get("top_k", 2)))
    return _GRAPHS[path]
