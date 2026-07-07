"""
valuelink.py — execution-grounded value linking (AV-SQL §4.2 / Algorithm 1, step 1).

Offline per-DB index of distinct cell values -> MinHash-LSH for fuzzy candidate retrieval.
At generation time, literals are extracted from a candidate CTE/SQL with sqlglot and matched
to real DB values by edit similarity (tau_edit) and, optionally, embedding similarity
(tau_semantic). Mismatched literals produce a correction hint fed back into regeneration —
the mechanism that fixes filter-value errors (AV-SQL's largest error class).
"""
from __future__ import annotations

import difflib
from typing import Dict, List, Optional, Tuple

import sqlglot
from sqlglot import expressions as exp
from datasketch import MinHash, MinHashLSH

from skiewsql.datasets import list_tables, _columns


def extract_literals(sql: str) -> List[str]:
    """String literals appearing in a query (the values a WHERE clause compares against)."""
    if not sql:                      # hard questions can yield no SQL at all -> nothing to link
        return []
    out, seen = [], set()
    try:
        tree = sqlglot.parse_one(sql, read="sqlite")
        for lit in tree.find_all(exp.Literal):
            if lit.is_string:
                v = lit.this
                if v and v not in seen and len(v) <= 60:
                    seen.add(v)
                    out.append(v)
    except Exception:  # noqa: BLE001
        import re
        for m in re.findall(r"'([^']{1,60})'", sql):
            if m not in seen:
                seen.add(m)
                out.append(m)
    return out


class ValueIndex:
    """MinHash-LSH over distinct short string cell values of one database."""

    def __init__(self, con, max_vals_per_col: int = 400, num_perm: int = 64,
                 threshold: float = 0.5, n_gram: int = 3):
        self.num_perm = num_perm
        self.n_gram = n_gram
        self.lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
        self.entries: Dict[str, Tuple[str, str, str]] = {}
        self._build(con, max_vals_per_col)

    def _mh(self, s: str) -> MinHash:
        m = MinHash(num_perm=self.num_perm)
        s2 = s.lower()
        grams = {s2[i:i + self.n_gram] for i in range(max(1, len(s2) - self.n_gram + 1))} or {s2}
        for g in grams:
            m.update(g.encode("utf-8"))
        return m

    def _build(self, con, cap: int):
        for t in list_tables(con):
            for c in _columns(con, t):
                name, ctype = c[1], (c[2] or "").upper()
                if any(k in ctype for k in ("INT", "REAL", "FLOA", "DOUB", "NUM", "DEC", "BOOL")):
                    continue  # value-linking targets textual filters
                try:
                    rows = con.execute(
                        f'SELECT DISTINCT "{name}" FROM "{t}" WHERE "{name}" IS NOT NULL LIMIT {cap}'
                    ).fetchall()
                except Exception:  # noqa: BLE001
                    continue
                for (v,) in rows:
                    if not isinstance(v, str):
                        continue
                    v = v.strip()
                    if not v or len(v) > 60:
                        continue
                    key = f"{t}.{name}::{v}"
                    if key in self.entries:
                        continue
                    self.entries[key] = (t, name, v)
                    try:
                        self.lsh.insert(key, self._mh(v))
                    except ValueError:
                        pass

    def link(self, literal: str, top_k: int = 3) -> List[Tuple[float, str, str, str]]:
        """Return [(edit_sim, value, table, column)] sorted best-first for a literal."""
        try:
            cand = self.lsh.query(self._mh(literal))
        except Exception:  # noqa: BLE001
            cand = []
        scored = []
        lit = literal.lower()
        for key in cand:
            t, c, v = self.entries[key]
            es = difflib.SequenceMatcher(None, lit, v.lower()).ratio()
            scored.append((es, v, t, c))
        scored.sort(reverse=True, key=lambda x: x[0])
        return scored[:top_k]

    def ground(self, sql: str, tau_edit: float = 0.6, embedder=None,
               tau_semantic: float = 0.55) -> List[str]:
        """Produce correction hints for literals whose exact value is not in the DB but a
        close real value exists. Empty list => all literals already grounded."""
        hints = []
        for lit in extract_literals(sql):
            matches = self.link(lit)
            if not matches:
                continue
            if any(v.lower() == lit.lower() for _, v, _, _ in matches):
                continue  # already an exact DB value
            best = [(es, v, t, c) for es, v, t, c in matches if es >= tau_edit]
            if not best and embedder is not None:
                # semantic fallback (tau_semantic) on the LSH candidates
                rescored = []
                for _es, v, t, c in matches:
                    try:
                        s = embedder.sim(lit, v)
                    except Exception:  # noqa: BLE001
                        s = 0.0
                    if s >= tau_semantic:
                        rescored.append((s, v, t, c))
                rescored.sort(reverse=True, key=lambda x: x[0])
                best = rescored[:1]
            if best:
                _s, v, t, c = best[0]
                hints.append(f"literal '{lit}' is not a DB value; closest real value is "
                             f"'{v}' in {t}.{c} — use '{v}'.")
        return hints


_INDEX_CACHE: Dict[str, ValueIndex] = {}


def get_index(con, db_path: str) -> ValueIndex:
    if db_path not in _INDEX_CACHE:
        _INDEX_CACHE[db_path] = ValueIndex(con)
    return _INDEX_CACHE[db_path]
