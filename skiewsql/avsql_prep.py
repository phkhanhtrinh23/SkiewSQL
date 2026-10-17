"""AV-SQL database preprocessing used by the SkiewSQL pipeline (paper §4.1).

This module is the maintained home of the useful preprocessing code that once
lived in the separate ``av_sql`` prototype package:

* schema compression (§4.1.1): table-name patterns, re-clustering by identical
  column sets, groups of at least ten same-typed patterned columns, and a compact
  prompt that lists every clustered name while detailing one representative;
* schema splitting (§4.1.2): tables sorted by estimated size and greedily packed
  under the prompt token limit;
* value preprocessing (§4.1.3): selected database values indexed with 128-permutation
  MinHash over character 3-grams and an LSH threshold of 0.5, followed online by
  edit and MiniLM similarity checks.

Backend-agnostic: the SQLite and MySQL builders produce the same AV-SQL schema dict (`{table: {"columns_name", "columns_type", "columns_description", "example_values", "primary_key", "foreign_keys", "sample_rows", ...}}`), and everything downstream works on that dict.

Deviations, all for reproducibility or because the source has no equivalent: example values are the first 20 distinct values (AV-SQL uses ORDER BY RANDOM()), and the 3 shown per column are chosen by a seeded shuffle (AV-SQL uses the global random module). Column descriptions come from a Spider/BIRD tables.json when one is given, as in AV-SQL; otherwise they are empty."""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import pickle
import random
import re
from collections import defaultdict
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from datasketch import MinHash, MinHashLSH

# --------------------------------------------------------------------------- #
# §4.1.1 Schema compression: table patterns
# --------------------------------------------------------------------------- #


def detect_table_pattern(name: str) -> str:
    """AV-SQL table-name pattern: digit runs -> {NUM}, the first two `_` parts (or up to the first {NUM}) are a stable prefix, alphabetic suffix parts -> {VAR}."""
    pattern = re.sub(r"\d+", "{NUM}", name)
    parts = pattern.split("_")
    num_stable_parts = max(2, parts.index("{NUM}") if "{NUM}" in parts else 0)
    if len(parts) >= 3:
        prefix = "_".join(parts[:num_stable_parts])
        suffix_tokens = []
        for part in parts[num_stable_parts:]:
            if part == "{NUM}":
                suffix_tokens.append(part)
            elif re.match(r"^[a-z]+$", part, re.IGNORECASE):
                suffix_tokens.append("{VAR}")
            else:
                suffix_tokens.append(part)
        pattern = "_".join([prefix] + suffix_tokens)
    elif len(parts) == 2:
        if parts[1] != "{NUM}" and re.match(r"^[a-z]+$", parts[1], re.IGNORECASE):
            pattern = f"{parts[0]}_{{VAR}}"
    return pattern


def cluster_tables_by_columns(pattern_groups: Dict[str, List[str]],
                              columns: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Split each name-pattern group by identical (sorted) column-name sets. A table with a unique column set becomes its own group keyed by its name. Groups of 2+ are keyed `{pattern}_cluster_{i}`."""
    final_groups: Dict[str, List[str]] = {}
    for pattern, tables in pattern_groups.items():
        if len(tables) == 1:
            final_groups[tables[0]] = [tables[0]]
            continue
        column_clusters: Dict[Tuple[str, ...], List[str]] = defaultdict(list)
        for table in tables:
            column_clusters[tuple(sorted(columns.get(table, [])))].append(table)
        cluster_id = 0
        for clustered in column_clusters.values():
            if len(clustered) == 1:
                final_groups[clustered[0]] = [clustered[0]]
            else:
                final_groups[f"{pattern}_cluster_{cluster_id}"] = clustered
                cluster_id += 1
    return final_groups


def group_tables(schema_dict: Dict[str, dict]) -> Dict[str, List[str]]:
    pattern_groups: Dict[str, List[str]] = defaultdict(list)
    for t in schema_dict:
        pattern_groups[detect_table_pattern(t)].append(t)
    return cluster_tables_by_columns(dict(pattern_groups),
                                     {t: info["columns_name"] for t, info in schema_dict.items()})


# --------------------------------------------------------------------------- #
# §4.1.1 Schema compression: column patterns
# --------------------------------------------------------------------------- #
MIN_COLUMN_GROUP = 10        # "Just keep groups with at least 10 columns to reduce noise"


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein distance (nltk.edit_distance with default arguments)."""
    a, b = a or "", b or ""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def group_columns(info: dict) -> Dict[str, List[str]]:
    """{pattern: [columns]} for one table: digit runs -> {NUM}, groups of >= 10 columns, kept only when every column has the same type and the descriptions are close (average edit distance to the first < 0.7 x average column-name length)."""
    names, types = info["columns_name"], info["columns_type"]
    descs = info.get("columns_description") or [""] * len(names)
    groups: Dict[str, List[str]] = defaultdict(list)
    for n in names:
        groups[re.sub(r"\d+", "{NUM}", n)].append(n)
    out: Dict[str, List[str]] = {}
    for pattern, cols in groups.items():
        if len(cols) < MIN_COLUMN_GROUP:
            continue
        idx = [names.index(c) for c in cols]
        type_set = {types[i] for i in idx if i < len(types) and types[i]}
        desc_list = [descs[i] if i < len(descs) else None for i in idx]
        dists = [_edit_distance(desc_list[0], d) for d in desc_list[1:] if d is not None]
        avg = sum(dists) / len(dists) if dists else 0.0
        thr = 0.7 * sum(len(c) for c in cols) / len(cols)
        if len(type_set) == 1 and avg < thr:
            out[pattern] = cols
    return out


# --------------------------------------------------------------------------- #
# Compact schema text (av_sql DatabaseSchemaManager.compact_schema_prompt)
# --------------------------------------------------------------------------- #


def _is_number(s) -> bool:
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def _is_json_str(s: str) -> bool:
    try:
        json.loads(s)
        return True
    except (TypeError, ValueError):
        return False


def _clip(val) -> str:
    s = str(val)
    if _is_json_str(s) and not _is_number(s):
        return s[:1000] + " ..." if len(s) > 1002 else s
    if "{" in s and "}" in s:
        return s[:600] + " ..." if len(s) > 602 else s
    return s[:50] + " ..." if len(s) > 52 else s


def example_value_text(table: str, idx: int, exp_values: list, columns_name: list) -> str:
    """', Example Values:[ v1 ; v2 ; v3 ]' — up to 3 values, ~50 characters."""
    if not exp_values or idx >= len(exp_values) or len(exp_values) != len(columns_name):
        return ""
    vals = list(exp_values[idx])
    if not vals:
        return ""
    seed = int(hashlib.md5(f"{table}.{columns_name[idx]}".encode()).hexdigest()[:8], 16)
    random.Random(seed).shuffle(vals)
    text = ""
    for val in vals[:3]:
        if len(text) < 50:
            if text:
                text += " ; "
            text += _clip(val)
        else:
            text += " ;  ..."
            break
    return f", Example Values:[ {text} ]"


def sample_rows_text(sample_rows: list, max_size: int = 3000) -> str:
    if not sample_rows:
        return ""
    names = [str(c) for c in sample_rows[0]]
    row_str = "Row Names: " + " ;\t".join(names)
    text = "Sample rows of this table. The `;` character separates values in each row:\n"
    text += f" {row_str}\n" + " ;\t".join(["-----"] * len(names)) + "\n"
    for row in sample_rows[:3]:
        text += " " + " ;\t".join(_clip(v) for v in row.values()) + "\n"
        if len(text) > 2 * len(row_str) + max_size:
            return text[:2 * len(row_str) + max_size * 5] + " ...\n"
    return text


def compact_schema_text(schema_dict: Dict[str, dict], group_of_tables: Dict[str, List[str]],
                        group_of_columns: Dict[str, Dict[str, List[str]]],
                        use_sample_rows: bool = True, use_col_desc: bool = True) -> str:
    """AV-SQL's compact prompt. A group is rendered only when its representative (first member) is in `schema_dict`, so siblings never appear on their own."""
    text = ""
    for pattern, members in group_of_tables.items():
        rep = members[0]
        if rep not in schema_dict:
            continue
        info = schema_dict[rep]
        db_id = info.get("db_id", "")
        full = info.get("table_to_tablefullname") or rep
        if len(members) == 1:
            text += f"DATABASE_NAME : {db_id} . Table: {full}\n"
        else:
            pat = pattern.split("_cluster")[0]
            text += f"DATABASE_NAME : {db_id} .List of tables have same pattern {pat} : {', '.join(members)}\n"
            text += f"with representative Table for pattern {pat} : {full}\n"
        col_groups = group_of_columns.get(rep, {})
        col_to_pattern = {c: p for p, cols in col_groups.items() for c in cols}
        done = set()
        exp_values = info.get("example_values", [])
        for idx, col in enumerate(info["columns_name"]):
            pat = col_to_pattern.get(col, col)
            if pat in done:
                continue
            done.add(pat)
            ctype = info["columns_type"][idx]
            descs = info.get("columns_description") or []
            desc = (descs[idx] if idx < len(descs) else "") or ""
            desc += example_value_text(rep, idx, exp_values, info["columns_name"])
            if pat in col_groups:
                text += f"  Columns with pattern '{pat}': {', '.join(col_groups[pat])}\n"
                text += f"   with representative Column for pattern '{pat}' : {col} (Type: {ctype}"
            else:
                text += f"  Column: {col} (Type: {ctype}"
            if desc and use_col_desc:
                text += f", Description: {desc}"
            text += ")\n"
        if info.get("primary_key"):
            text += f"  Primary Key: {', '.join(info['primary_key'])}\n"
        if info.get("foreign_keys"):
            fks = "; ".join(f"{a[0]}.{a[1]} -> {b[0]}.{b[1]}" for a, b in info["foreign_keys"])
            text += f"  Foreign Key: {fks}\n"
        if use_sample_rows:
            text += sample_rows_text(info.get("sample_rows", []))
        text += "\n"
    return text


# --------------------------------------------------------------------------- #
# §4.1.2 Schema splitting (split_by_prompting_size_limit)
# --------------------------------------------------------------------------- #


def estimate_token_count(info: dict, est_tokens: Callable[[str], int], use_col_desc: bool = True) -> int:
    text = str(info["columns_name"]) * 3 + " " + str(info["columns_type"])
    if use_col_desc:
        text += str(info.get("columns_description") or [])
    return est_tokens(text)


def split_by_prompting_size_limit(schema_dict: Dict[str, dict], token_limit: int,
                                  est_tokens: Callable[[str], int],
                                  use_col_desc: bool = True) -> List[Dict[str, dict]]:
    sizes = {t: estimate_token_count(info, est_tokens, use_col_desc) for t, info in schema_dict.items()}
    parts, cur, cur_tok = [], {}, 0
    for t, n in sorted(sizes.items(), key=lambda kv: kv[1]):
        if cur_tok + n > token_limit:
            if cur:
                parts.append(cur)
            cur, cur_tok = {t: schema_dict[t]}, n
        else:
            cur[t] = schema_dict[t]
            cur_tok += n
    if cur:
        parts.append(cur)
    return parts


class PreparedSchema:
    """One database after AV-SQL preprocessing: groups, the representative-only schema, and its chunks."""

    def __init__(self, schema_dict: Dict[str, dict], token_limit: int, est_tokens: Callable[[str], int],
                 use_sample_rows: bool = True, use_col_desc: bool = True):
        self.schema_dict = schema_dict
        self.use_sample_rows, self.use_col_desc = use_sample_rows, use_col_desc
        self.group_of_tables = group_tables(schema_dict)
        self.group_of_columns = {t: group_columns(info) for t, info in schema_dict.items()}
        self.representative = {m: members[0] for members in self.group_of_tables.values() for m in members}
        reps = [members[0] for members in self.group_of_tables.values()]
        self.compact = {r: schema_dict[r] for r in reps}
        self.parts = split_by_prompting_size_limit(self.compact, token_limit, est_tokens, use_col_desc)

    def render(self, tables: Iterable[str]) -> str:
        """Compact text for these tables. A sibling is shown through its representative, so the group's full name list comes with it."""
        low = {t.lower(): t for t in self.representative}
        picked = {}
        for t in tables:
            a = low.get(str(t).lower().strip('`"'))
            if a:
                picked[self.representative[a]] = self.schema_dict[self.representative[a]]
        return compact_schema_text(picked, self.group_of_tables, self.group_of_columns,
                                   self.use_sample_rows, self.use_col_desc)

    def chunks(self) -> List[Tuple[str, List[str]]]:
        """[(chunk_text, [representative tables])], one per schema part."""
        return [(compact_schema_text(p, self.group_of_tables, self.group_of_columns,
                                     self.use_sample_rows, self.use_col_desc), list(p)) for p in self.parts]


# --------------------------------------------------------------------------- #
# Schema dict builders
# --------------------------------------------------------------------------- #
EXAMPLE_VALUES = 20
SAMPLE_ROWS = 5


def tables_json_descriptions(tables_path: Optional[str], db_id: str) -> Dict[str, List[str]]:
    """{table: [column description per column]} from a Spider/BIRD tables.json (its `column_names`, which AV-SQL uses as the description). Empty when unavailable."""
    if not tables_path or not os.path.exists(tables_path):
        return {}
    with open(tables_path) as f:
        items = json.load(f)
    for item in items:
        if item.get("db_id") != db_id:
            continue
        out: Dict[str, List[str]] = defaultdict(list)
        tnames = item["table_names_original"]
        for tid, col in item["column_names"]:
            if tid >= 0:
                out[tnames[tid]].append(str(col))
        return dict(out)
    return {}


def sqlite_schema_dict(con, db_id: str, descriptions: Optional[Dict[str, List[str]]] = None) -> Dict[str, dict]:
    from skiewsql.datasets import list_tables, _columns, _foreign_keys
    descriptions = descriptions or {}
    sd: Dict[str, dict] = {}
    for t in list_tables(con):
        cols = _columns(con, t)
        names = [c[1] for c in cols]
        examples = []
        for n in names:
            try:
                rows = con.execute(f'SELECT DISTINCT "{n}" FROM "{t}" LIMIT {EXAMPLE_VALUES}').fetchall()
            except Exception:  # noqa: BLE001
                rows = []
            examples.append([r[0] for r in rows])
        try:
            cur = con.execute(f'SELECT * FROM "{t}" LIMIT {SAMPLE_ROWS}')
            hdr = [d[0] for d in cur.description]
            sample = [dict(zip(hdr, r)) for r in cur.fetchall()]
        except Exception:  # noqa: BLE001
            sample = []
        desc = descriptions.get(t) or []
        if len(desc) != len(names):
            desc = [""] * len(names)
        sd[t] = {
            "db_type": "sqlite", "db_id": db_id, "columns_name": names,
            "columns_type": [c[2] or "" for c in cols], "columns_description": desc,
            "example_values": examples,
            "primary_key": [c[1] for c in sorted((c for c in cols if c[5]), key=lambda c: c[5])],
            "foreign_keys": [[[t, fk[3]], [fk[2], fk[4]]] for fk in _foreign_keys(con, t)],
            "table_to_tablefullname": t, "sample_rows": sample,
        }
    # AV-SQL lists a foreign key on both of its tables
    for t, info in sd.items():
        for fk in list(info["foreign_keys"]):
            ref = fk[1][0]
            if ref in sd and ref != t and fk not in sd[ref]["foreign_keys"]:
                sd[ref]["foreign_keys"].append(fk)
    return sd


def mysql_schema_dict(run: Callable[[str, tuple], list], db: str) -> Dict[str, dict]:
    """`run(sql, params) -> rows` executes on the MySQL connection with `db` selected."""
    rows = run("SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, COLUMN_KEY FROM information_schema.COLUMNS "
               "WHERE TABLE_SCHEMA=%s ORDER BY TABLE_NAME, ORDINAL_POSITION", (db,))
    fk_rows = run("SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME "
                  "FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA=%s "
                  "AND REFERENCED_TABLE_NAME IS NOT NULL", (db,))
    sd: Dict[str, dict] = {}
    for t, col, ctype, key in rows:
        info = sd.setdefault(t, {"db_type": "mysql", "db_id": db, "columns_name": [], "columns_type": [],
                                 "columns_description": [], "example_values": [], "primary_key": [],
                                 "foreign_keys": [], "table_to_tablefullname": t, "sample_rows": []})
        info["columns_name"].append(col)
        info["columns_type"].append(ctype)
        info["columns_description"].append("")
        if key == "PRI":
            info["primary_key"].append(col)
    for t, col, rt, rc in fk_rows:
        fk = [[t, col], [rt, rc]]
        for side in (t, rt):
            if side in sd and fk not in sd[side]["foreign_keys"]:
                sd[side]["foreign_keys"].append(fk)
    for t, info in sd.items():
        for col in info["columns_name"]:
            try:
                vals = run(f"SELECT DISTINCT `{col}` FROM `{t}` LIMIT {EXAMPLE_VALUES}", ())
            except Exception:  # noqa: BLE001
                vals = []
            info["example_values"].append([r[0] for r in vals])
        try:
            sample = run(f"SELECT * FROM `{t}` LIMIT {SAMPLE_ROWS}", ())
            info["sample_rows"] = [dict(zip(info["columns_name"], r)) for r in sample]
        except Exception:  # noqa: BLE001
            pass
    return sd


# --------------------------------------------------------------------------- #
# §4.1.3 Value preprocessing
# --------------------------------------------------------------------------- #
_SKIP_NAME_KEYWORDS = ["_id", " id", "url", "email", "time", "phone", "date", "number", "code", "zip",
                       "charternum", "text", "id", "_no", "_ref", "_key", "_point_", "tract_"]
_TEXT_TYPES = ("char", "text", "string", "enum")
LSH_MAX_VALUES = int(os.environ.get("AVSQL_LSH_MAX_VALUES", "5000000"))


def indexable_column(name: str, ctype: str, primary_key: List[str]) -> bool:
    """AV-SQL's filter: no primary keys, string-typed columns only, and no ID/date/code-like names."""
    if name in primary_key:
        return False
    if not any(k in (ctype or "").lower() for k in _TEXT_TYPES):
        return False
    if any(k in name.lower() for k in _SKIP_NAME_KEYWORDS) or name.endswith("Id"):
        return False
    return True


def unique_values(schema_dict: Dict[str, dict], fetch: Callable[[str, str], list]) -> Dict[str, Dict[str, List[str]]]:
    """{table: {column: [distinct values as str]}}. `fetch(table, column)` returns the column's distinct non-null values."""
    out: Dict[str, Dict[str, List[str]]] = defaultdict(dict)
    for t, info in schema_dict.items():
        for idx, col in enumerate(info["columns_name"]):
            if not indexable_column(col, info["columns_type"][idx], info.get("primary_key", [])):
                continue
            try:
                vals = fetch(t, col)
            except Exception:  # noqa: BLE001
                continue
            if vals:
                out[t][col] = [str(v) for v in vals]
    return dict(out)


def create_minhash(s: str, signature_size: int = 128, n_gram: int = 3) -> MinHash:
    """MinHash over the character n-grams of `s` (nltk.ngrams: a string shorter than n has none)."""
    m = MinHash(num_perm=signature_size)
    for i in range(len(s) - n_gram + 1):
        m.update(s[i:i + n_gram].encode("utf8"))
    return m


_MINILM = None


def _minilm():
    """all-MiniLM-L6-v2 through sentence-transformers, as in AV-SQL. None when the package is missing."""
    global _MINILM
    if _MINILM is None:
        try:
            from sentence_transformers import SentenceTransformer
            _MINILM = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        except Exception as e:  # noqa: BLE001
            print(f"  (all-MiniLM-L6-v2 unavailable: {e}. Value retrieval falls back to the run's embedder)")
            _MINILM = False
    return _MINILM or None


def extract_value_literals(sql: str, dialect: str = "sqlite") -> List[str]:
    """Non-numeric literals of a CTE (the values AV-SQL looks up)."""
    import sqlglot
    from sqlglot import expressions as exp
    out: List[str] = []
    try:
        tree = sqlglot.parse_one(sql or "", read=dialect)
    except Exception:  # noqa: BLE001
        return re.findall(r"'([^']+)'", sql or "")
    for lit in tree.find_all(exp.Literal):
        v = lit.name
        if v and not _is_number(v) and v not in out:
            out.append(v)
    return out


class AVSQLValueIndex:
    """Offline MinHash-LSH over the indexed values of one database, and AV-SQL's online retrieval."""

    def __init__(self, values: Dict[str, Dict[str, List[str]]], threshold: float = 0.5,
                 signature_size: int = 128, n_gram: int = 3):
        self.signature_size, self.n_gram = signature_size, n_gram
        self.lsh = MinHashLSH(threshold=threshold, num_perm=signature_size)
        self.minhashes: Dict[str, Tuple[MinHash, str, str, str]] = {}
        total = sum(len(v) for cols in values.values() for v in cols.values())
        if total > LSH_MAX_VALUES:
            print(f"  (value index skipped: {total} unique values > {LSH_MAX_VALUES})")
            return
        for t, cols in values.items():
            for c, vals in cols.items():
                for i, v in enumerate(vals):
                    m = create_minhash(v, signature_size, n_gram)
                    key = f"{t}_{c}_{i}"
                    self.minhashes[key] = (m, t, c, v)
                    self.lsh.insert(key, m)

    def query(self, q: str, top_k: int = 5) -> List[dict]:
        """LSH candidates by Jaccard, best first: top_k plus any further exact (1.0) matches."""
        qm = create_minhash(q, self.signature_size, self.n_gram)
        scored = sorted(((k, self.minhashes[k][0].jaccard(qm)) for k in self.lsh.query(qm)),
                        key=lambda x: x[1], reverse=True)
        out = []
        for k, s in scored:
            if len(out) < top_k or s == 1.0:
                _m, t, c, v = self.minhashes[k]
                out.append({"query": q, "lsh_score": s, "table_name": t, "column_name": c, "value": v})
        return out

    def relevant_values(self, sql: str, embedder=None, top_k: int = 5, tau_edit: float = 0.5,
                        tau_semantic: float = 0.5, dialect: str = "sqlite") -> List[str]:
        """One 'Relevant stored values ...' block per literal that has matches (empty list = nothing to show)."""
        texts = []
        model = _minilm()
        for lit in extract_value_literals(sql, dialect):
            cands = [c for c in self.query(lit, top_k)
                     if difflib.SequenceMatcher(None, c["value"], lit).ratio() >= tau_edit]
            if not cands:
                continue
            if model is not None:
                import numpy as np
                strs = list({lit, *(c["value"] for c in cands)})
                embs = dict(zip(strs, model.encode(strs)))

                def sim(a, b):
                    va, vb = embs[a], embs[b]
                    return float(np.dot(va, vb) / ((np.linalg.norm(va) * np.linalg.norm(vb)) or 1.0))
            elif embedder is not None:
                sim = embedder.sim
            else:
                sim = None
            if sim is not None:
                # A one-character database-value typo is already a strong edit
                # match and must not be lost when an embedding checkpoint gives
                # an unexpectedly low cosine for two near-identical strings.
                cands = [c for c in cands
                         if difflib.SequenceMatcher(None, c["value"], lit).ratio() >= 0.9
                         or sim(c["value"], lit) >= tau_semantic]
            if cands:
                texts.append(f"Relevant stored values for '{lit}' in database:\n" + "".join(
                    f"\"{c['value']}\" from table '{c['table_name']}', column '{c['column_name']}'\n"
                    for c in cands))
        return texts

    def ground(self, sql: str, tau_edit: float = 0.6, embedder=None, tau_semantic: float = 0.55,
               dialect: str = "sqlite") -> List[str]:
        """valuelink.ValueIndex.ground over this index, for SkiewSQL's own sub-goal generator: a hint only for a literal that is not a stored value but has a close one."""
        hints = []
        for lit in extract_value_literals(sql, dialect):
            cands = self.query(lit)
            if not cands or any(c["value"].lower() == lit.lower() for c in cands):
                continue
            scored = sorted(((difflib.SequenceMatcher(None, lit.lower(), c["value"].lower()).ratio(), c)
                             for c in cands), key=lambda x: x[0], reverse=True)
            best = [c for s, c in scored if s >= tau_edit]
            if not best and embedder is not None:
                best = [c for _s, c in scored if embedder.sim(lit, c["value"]) >= tau_semantic]
            if best:
                c = best[0]
                hints.append(f"literal '{lit}' is not a DB value. Closest real value is "
                             f"'{c['value']}' in {c['table_name']}.{c['column_name']} — use '{c['value']}'.")
        return hints


def load_or_build_index(cache_key: Optional[str], build: Callable[[], Dict[str, Dict[str, List[str]]]],
                        cache_dir: Optional[str] = None) -> AVSQLValueIndex:
    """Build the index once and pickle it (AV-SQL builds it offline and stores lsh_index.pkl). `cache_key` must change when the data changes. None disables the disk cache."""
    if cache_key is None:
        return AVSQLValueIndex(build())
    cache_dir = cache_dir or os.environ.get("AVSQL_LSH_CACHE_DIR",
                                            os.path.expanduser("~/.cache/skiewsql/avsql_lsh"))
    path = os.path.join(cache_dir, hashlib.sha1(cache_key.encode()).hexdigest() + ".pkl")
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception:  # noqa: BLE001 — a corrupt cache is rebuilt
            pass
    idx = AVSQLValueIndex(build())
    try:
        os.makedirs(cache_dir, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(idx, f)
    except Exception:  # noqa: BLE001
        pass
    return idx


__all__ = ["detect_table_pattern", "cluster_tables_by_columns", "group_tables", "group_columns",
           "compact_schema_text", "split_by_prompting_size_limit", "PreparedSchema",
           "tables_json_descriptions", "sqlite_schema_dict", "mysql_schema_dict", "indexable_column",
           "unique_values", "AVSQLValueIndex", "load_or_build_index", "extract_value_literals"]
