"""valuelink.py — execution-grounded value linking (AV-SQL §4.2 / Algorithm 1, step 1). Offline per-DB index of distinct cell values -> MinHash-LSH for fuzzy candidate retrieval. At generation time, literals are extracted from a candidate CTE/SQL with sqlglot and matched to real DB values by edit similarity (tau_edit) and, optionally, embedding similarity (tau_semantic). Mismatched literals produce a correction hint fed back into regeneration — the mechanism that fixes filter-value errors (AV-SQL's largest error class)."""
from __future__ import annotations

import difflib
import os
from typing import Dict, List, Optional, Tuple

import sqlglot
from sqlglot import expressions as exp
from datasketch import MinHash, MinHashLSH

from skiewsql.datasets import list_tables, _columns

# Parallel embedding recall (opt-in): MinHash-LSH matches only near-SPELLINGS (char trigrams), so it misses encoding/abbreviation mismatches like 'Active'->'A' or 'New York'->'NY' (zero shared trigrams). When SKIEW_VALUELINK_EMBED=1, ground() ALSO retrieves embedding-similar distinct values (a separate recall path, unioned with LSH), so a value LSH dropped can still be caught. Bounded by _VL_EMBED_MAX distinct values per DB to cap embedding cost.
_VL_EMBED = os.environ.get("SKIEW_VALUELINK_EMBED", "0") == "1"
_VL_EMBED_MAX = int(os.environ.get("SKIEW_VALUELINK_EMBED_MAX", "600"))


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

    def _build(self, con, cap: int, max_scan_rows: int = 50000):
        for t in list_tables(con):
            for c in _columns(con, t):
                name, ctype = c[1], (c[2] or "").upper()
                if any(k in ctype for k in ("INT", "REAL", "FLOA", "DOUB", "NUM", "DEC", "BOOL")):
                    continue  # value-linking targets textual filters
                try:
                    # Bound the scan: DISTINCT over a huge table forces a full-table dedup (the LSH-build bottleneck on big DBs). Sample the first `max_scan_rows` rows, then dedupe — bounded cost regardless of table size, still captures common values.
                    rows = con.execute(
                        f'SELECT DISTINCT "{name}" FROM '
                        f'(SELECT "{name}" FROM "{t}" WHERE "{name}" IS NOT NULL LIMIT {max_scan_rows}) '
                        f'LIMIT {cap}'
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

    def _embed_recall(self, literal: str, embedder, top_k: int = 5,
                      tau: float = 0.55) -> List[Tuple[float, str, str, str]]:
        """Embedding recall over the DB's distinct values — a SEPARATE path from LSH that can catch encoding/abbreviation matches LSH misses (returns [(embed_sim, value, table, column)]). Bounded to _VL_EMBED_MAX distinct values. Embeddings are cached in the Embedder, so the cost is paid once per DB across all literals."""
        pool = list(self.entries.values())[:_VL_EMBED_MAX]
        scored = []
        for (t, c, v) in pool:
            try:
                s = embedder.sim(literal, v)
            except Exception:  # noqa: BLE001
                continue
            if s >= tau:
                scored.append((s, v, t, c))
        scored.sort(reverse=True, key=lambda x: x[0])
        return scored[:top_k]

    def ground(self, sql: str, tau_edit: float = 0.6, embedder=None,
               tau_semantic: float = 0.55) -> List[str]:
        """Produce correction hints for literals whose exact value is not in the DB but a close real value exists. Empty list => all literals already grounded."""
        hints = []
        for lit in extract_literals(sql):
            matches = self.link(lit)
            if embedder is not None and _VL_EMBED:
                # parallel embedding recall: union in embed-similar values LSH missed (dedup by value)
                seen = {(t, c, v) for _es, v, t, c in matches}
                for s, v, t, c in self._embed_recall(lit, embedder, top_k=5, tau=tau_semantic):
                    if (t, c, v) not in seen:
                        es = difflib.SequenceMatcher(None, lit.lower(), v.lower()).ratio()
                        matches.append((es, v, t, c))  # give it an edit_sim so ranking stays uniform
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
                hints.append(f"literal '{lit}' is not a DB value. Closest real value is "
                             f"'{v}' in {t}.{c} — use '{v}'.")
        return hints


def profile_categoricals(con, max_card: int = 12, max_cols: int = 40, sample: int = 20000) -> str:
    """Value profile of LOW-CARDINALITY string columns: 'table.column ∈ {v1, v2, ...}'. Appended to the schema shown to the LLM so it writes the DB's ACTUAL encoding (e.g. 'T'/'F', 'A'/'I') directly — the robust fix for pure encodings that neither MinHash trigrams nor embeddings reliably catch. Only columns with <= max_card distinct values are listed (true categoricals). sqlite-quoted (matches this module's usage. Spider2-lite). Returns '' if nothing qualifies."""
    out: List[str] = []
    for t in list_tables(con):
        if len(out) >= max_cols:
            break
        for c in _columns(con, t):
            name, ctype = c[1], (c[2] or "").upper()
            if any(k in ctype for k in ("INT", "REAL", "FLOA", "DOUB", "NUM", "DEC", "BOOL")):
                continue
            try:
                rows = con.execute(
                    f'SELECT DISTINCT "{name}" FROM '
                    f'(SELECT "{name}" FROM "{t}" WHERE "{name}" IS NOT NULL LIMIT {sample}) '
                    f'LIMIT {max_card + 1}'
                ).fetchall()
            except Exception:  # noqa: BLE001
                continue
            vals = [v.strip() for (v,) in rows
                    if isinstance(v, str) and v.strip() and len(v.strip()) <= 40]
            if vals and len(vals) <= max_card:  # <= max_card distinct => a real categorical
                out.append(f"{t}.{name} ∈ {{{', '.join(repr(x) for x in vals)}}}")
                if len(out) >= max_cols:
                    break
    return "\n".join(out)


def schema_value_profile(sample_table_fn, tables, max_card: int = 12, max_cols: int = 40) -> str:
    """Dialect-agnostic value profile for the schema prompt: 'table.col ∈ {v1, v2, ...}' for low-cardinality STRING columns. Lets the model write the DB's actual encoding (T/F, 'Pending', '2023FA') instead of guessing — helps ALL benchmarks, not just the value-linking (Spider2) path.

    sample_table_fn(table) -> (colnames: list[str], rows: list[sequence]) samples one table. The caller owns dialect quoting + cost guards and may return ([], []) to skip (e.g. a BigQuery scan over the GB guard). Cardinality is judged over the sample, so this targets true categoricals, not IDs."""
    out: List[str] = []
    for t in tables:
        if len(out) >= max_cols:
            break
        try:
            cols, rows = sample_table_fn(t)
        except Exception:  # noqa: BLE001
            continue
        if not cols or not rows:
            continue
        for ci, name in enumerate(cols):
            vals, is_str_col = set(), True
            for r in rows:
                v = r[ci] if ci < len(r) else None
                if v is None:
                    continue
                if not isinstance(v, str):     # numeric/other -> not a value-linking target
                    is_str_col = False
                    break
                v = v.strip()
                if not v or len(v) > 40:
                    continue
                vals.add(v)
                if len(vals) > max_card:        # too many distinct -> not categorical, drop it
                    is_str_col = False
                    break
            if is_str_col and 0 < len(vals) <= max_card:
                out.append(f"{t}.{name} ∈ {{{', '.join(repr(x) for x in sorted(vals))}}}")
                if len(out) >= max_cols:
                    break
    return "\n".join(out)


_VPROFILE_CACHE: Dict[str, str] = {}


def value_profile_appendix(cache_key: str, build_fn, max_chars: int = 3000) -> str:
    """Schema appendix listing categorical column values, gated by SKIEW_VALUE_PROFILE=1. build_fn() -> (sample_table_fn, tables) is invoked only on a cache miss (so the DB sampling runs once per cache_key). Returns '' when disabled or nothing qualifies."""
    if os.environ.get("SKIEW_VALUE_PROFILE") != "1":
        return ""
    if cache_key not in _VPROFILE_CACHE:
        try:
            sample_fn, tables = build_fn()
            vp = schema_value_profile(sample_fn, tables)
        except Exception:  # noqa: BLE001
            vp = ""
        _VPROFILE_CACHE[cache_key] = vp[:max_chars]
    vp = _VPROFILE_CACHE[cache_key]
    if not vp:
        return ""
    return "\n\n-- Categorical column values (use these EXACT literals in WHERE/IN filters):\n" + vp


_INDEX_CACHE: Dict[str, ValueIndex] = {}


def get_index(con, db_path: str) -> ValueIndex:
    if db_path not in _INDEX_CACHE:
        _INDEX_CACHE[db_path] = ValueIndex(con)
    return _INDEX_CACHE[db_path]


_AV_INDEX_CACHE: Dict[str, object] = {}


def get_avsql_index(con, db_path: str, db_id: str = ""):
    """AV-SQL's value index (avsql_prep.AVSQLValueIndex) for a SQLite database: every distinct value of the indexable columns, pickled on disk keyed by the file's size and mtime."""
    from skiewsql import avsql_prep
    if db_path not in _AV_INDEX_CACHE:
        key = None
        if db_path and os.path.exists(db_path):
            st = os.stat(db_path)
            key = f"sqlite:{os.path.abspath(db_path)}:{st.st_size}:{st.st_mtime_ns}"

        def build():
            sd = {}
            for t in list_tables(con):
                cols = _columns(con, t)
                sd[t] = {"columns_name": [c[1] for c in cols], "columns_type": [c[2] or "" for c in cols],
                         "primary_key": [c[1] for c in cols if c[5]]}
            return avsql_prep.unique_values(sd, lambda t, c: [
                r[0] for r in con.execute(f'SELECT DISTINCT "{c}" FROM "{t}" WHERE "{c}" IS NOT NULL')])
        _AV_INDEX_CACHE[db_path] = avsql_prep.load_or_build_index(key, build)
    return _AV_INDEX_CACHE[db_path]
