"""retriever.py — advanced view retrieval for SkiewSQL, honestly fitted to the scale (tens–hundreds of views per database, LLM composer judges last, ranking only bites when many candidates survive). Two contributions over the plain dense retriever in `sqlview.retrieve`:

  1. HYBRID retrieval — after the typed compatibility contract narrows candidates, fuse a DENSE bi-encoder score (OpenAI embeddings, semantic intent) with a SPARSE BM25 score (lexical overlap on column/table/operator tokens) via Reciprocal Rank Fusion. Embeddings blur exact identifiers. BM25 catches them. The fusion gets both. To ISOLATE the ranking effect from the accept decision, hybrid accepts on the SAME max-dense ≥ tau gate as the dense retriever, and only differs in WHICH compatible view it returns (RRF-best vs dense-best).

  2. NSWIndex — a pure-numpy Navigable Small-World proximity graph (kNN graph + greedy best-first search): the "graph" data structure that genuinely powers vector retrieval. At this scale it reproduces exact search (see recall_at1), so it is for the technique/story and for scaling, not for speed here.

BM25 and NSW are implemented from scratch (no rank_bm25 / hnswlib dependency)."""
from __future__ import annotations

import math
import re
from typing import Dict, List, Optional, Tuple

import numpy as np

from skiewsql import sqlview
from skiewsql.core import ViewSpec, ViewGraph, ViewRequest


# --------------------------------------------------------------------------- #
# Tokenization (splits snake_case AND camelCase so column identifiers match)
# --------------------------------------------------------------------------- #
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def tokenize(text: str) -> List[str]:
    text = _CAMEL.sub(" ", str(text))
    return [t for t in re.split(r"[^A-Za-z0-9]+", text.lower()) if t]


def _view_sig(v: ViewSpec) -> List[str]:
    parts = [v.name, v.description or "", " ".join(v.output_columns),
             " ".join(v.source_tables), " ".join(v.grain), v.category]
    return tokenize(" ".join(parts))


def _query_tokens(req: ViewRequest) -> List[str]:
    parts = [req.want_name, req.text, " ".join(req.required_outputs), " ".join(req.required_grain)]
    return tokenize(" ".join(parts))


# --------------------------------------------------------------------------- #
# BM25 (Okapi), built on the fly over a small candidate corpus
# --------------------------------------------------------------------------- #
class BM25:
    def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = corpus
        self.N = len(corpus)
        self.avgdl = (sum(len(d) for d in corpus) / self.N) if self.N else 0.0
        df: Dict[str, int] = {}
        for d in corpus:
            for t in set(d):
                df[t] = df.get(t, 0) + 1
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()}
        self.tf = [{} for _ in corpus]
        for i, d in enumerate(corpus):
            for t in d:
                self.tf[i][t] = self.tf[i].get(t, 0) + 1

    def score(self, query: List[str], i: int) -> float:
        if not self.avgdl:
            return 0.0
        dl = len(self.docs[i])
        s = 0.0
        for t in query:
            f = self.tf[i].get(t, 0)
            if not f:
                continue
            s += self.idf.get(t, 0.0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return s


# --------------------------------------------------------------------------- #
# Hybrid retrieval (contract filter -> RRF(dense, BM25))
# --------------------------------------------------------------------------- #
def retrieve(graph: ViewGraph, req: ViewRequest, embedder, tau: float = 0.55,
             use_guard: bool = True, rrf_k: int = 60) -> Tuple[Optional[ViewSpec], Dict]:
    """Hybrid retrieval with the same accept gate as sqlview.retrieve (max dense sim >= tau), so only the CHOICE among compatible candidates changes (dense-best vs RRF-best)."""
    comp = [c for c in graph.candidates(req.category)
            if sqlview.compatible(c, req, use_guard=use_guard)[0]]
    if not comp:
        return None, {"hit": False, "sim": 0.0, "reason": "no compatible candidate"}

    dense = [embedder.sim(req.text, c.description or c.name) for c in comp]
    max_dense = max(dense)
    if max_dense < tau:                                # accept gate identical to dense retriever
        return None, {"hit": False, "sim": round(max_dense, 3), "reason": "below tau"}

    # single compatible candidate -> nothing to re-rank. Identical to dense
    if len(comp) == 1:
        return comp[0], {"hit": True, "sim": round(dense[0], 3), "view": comp[0].name, "rank": "single"}

    bm = BM25([_view_sig(c) for c in comp])
    q = _query_tokens(req)
    sparse = [bm.score(q, i) for i in range(len(comp))]

    d_order = sorted(range(len(comp)), key=lambda i: dense[i], reverse=True)
    s_order = sorted(range(len(comp)), key=lambda i: sparse[i], reverse=True)
    rrf = [0.0] * len(comp)
    for r, i in enumerate(d_order):
        rrf[i] += 1.0 / (rrf_k + r)
    for r, i in enumerate(s_order):
        rrf[i] += 1.0 / (rrf_k + r)
    best = max(range(len(comp)), key=lambda i: rrf[i])
    changed = best != d_order[0]                       # did fusion overturn the dense pick?
    return comp[best], {"hit": True, "sim": round(dense[best], 3), "view": comp[best].name,
                        "rrf": round(rrf[best], 4), "overturned_dense": changed}


# --------------------------------------------------------------------------- #
# NSW proximity-graph index (the "graph" that actually powers vector search)
# --------------------------------------------------------------------------- #
class NSWIndex:
    """Navigable Small-World kNN graph over unit-normalized vectors with greedy best-first search. Pure numpy. No hnswlib. At small N this matches exact cosine (see recall_at1)."""

    def __init__(self, M: int = 8):
        self.M = M
        self.vecs: List[np.ndarray] = []
        self.ids: List[str] = []
        self.adj: List[List[int]] = []

    @staticmethod
    def _unit(v: np.ndarray) -> np.ndarray:
        n = float(np.linalg.norm(v)) or 1.0
        return (v / n).astype(np.float32)

    def add(self, id_: str, vec: np.ndarray):
        v = self._unit(vec)
        idx = len(self.vecs)
        # connect to current M nearest (greedy, over existing nodes)
        nbrs = []
        if self.vecs:
            sims = [float(np.dot(v, self.vecs[j])) for j in range(len(self.vecs))]
            nbrs = sorted(range(len(self.vecs)), key=lambda j: sims[j], reverse=True)[:self.M]
        self.vecs.append(v)
        self.ids.append(id_)
        self.adj.append(list(nbrs))
        for j in nbrs:                                 # undirected: back-links (bounded degree)
            self.adj[j].append(idx)
            if len(self.adj[j]) > 2 * self.M:
                sims = [float(np.dot(self.vecs[j], self.vecs[k])) for k in self.adj[j]]
                self.adj[j] = [k for _, k in sorted(zip(sims, self.adj[j]), reverse=True)[:2 * self.M]]

    def search(self, query: np.ndarray, k: int = 5, ef: int = 32) -> List[Tuple[str, float]]:
        if not self.vecs:
            return []
        q = self._unit(query)
        start = 0
        visited, frontier = set(), [start]
        best = []
        while frontier:
            nxt = []
            for node in frontier:
                if node in visited:
                    continue
                visited.add(node)
                best.append((float(np.dot(q, self.vecs[node])), node))
                nxt.extend(self.adj[node])
            best.sort(reverse=True)
            best = best[:ef]
            frontier = [n for n in dict.fromkeys(nxt) if n not in visited][:ef]
        return [(self.ids[n], s) for s, n in best[:k]]

    def recall_at1(self, queries: List[np.ndarray]) -> float:
        """Fraction of queries whose NSW top-1 equals the brute-force exact top-1."""
        if not (self.vecs and queries):
            return 1.0
        mat = np.vstack(self.vecs)
        hits = 0
        for q in queries:
            qn = self._unit(q)
            exact = int(np.argmax(mat @ qn))
            got = self.search(q, k=1)
            if got and got[0][0] == self.ids[exact]:
                hits += 1
        return hits / len(queries)


def get_retriever(name: str):
    """'dense' -> sqlview.retrieve, 'hybrid' -> this module's retrieve."""
    return retrieve if name == "hybrid" else sqlview.retrieve
