"""schema_complexity.py — a schema-level "join/grain ambiguity" score, from the schema + FK graph. The property that makes view REUSE risky (PAPER §12.7) is not schema *size* but **look-alike-but- different** structure: many join paths between the same entities and heavy name overlap, so a reused intermediate relation can execute yet answer a subtly different question. We quantify it with:

  STRUCTURAL signals
    1. join_ambiguity  — fraction of connected (<=2-hop) table pairs joinable by MORE THAN ONE route, over a FK graph AUGMENTED with LATENT edges inferred from column names+types (`x_id`->`x.id`, shared key-like columns) — because many dumps under-declare or omit FK constraints (e.g. BEAVER `dw` has zero).
    2. col_collision   — fraction of column names appearing in >=2 tables ("right columns, wrong table").
    3. bridge_frac     — fraction of tables that are junction/bridge tables (>=2 FK-ish cols, mostly keys).
    4. fk_density      — join edges per table (declared + latent), normalized. SEMANTIC signal (optional, needs an embedder)
    5. semantic_ambiguity — fraction of table-name pairs whose name embeddings are highly similar (look-alike entities: patient/sample/gene, project/programme) — the axis the structural proxies cannot see.

HONESTY: the signals are principled proxies. The score->policy THRESHOLD is an unvalidated heuristic (§12.7 found no replicable accuracy effect of reuse even on "complex" science schemas). Treat the score as a diagnostic / prior, with runtime negative-reuse signals the reliable decision."""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Optional

from skiewsql import datasets

# structural-only weights (renormalized if the semantic signal is absent)
_W = {"join_ambiguity": 0.30, "col_collision": 0.18, "bridge_frac": 0.10, "fk_density": 0.12,
      "semantic_ambiguity": 0.30}
DEFAULT_THRESHOLD = 0.5
_MAX_TABLES_PAIRS = 150
_SEM_SIM_THRESH = 0.72          # cosine above this = "confusably similar" table names
# key-like column suffixes that indicate a join key (not a generic hygiene column)
_KEYCOL = re.compile(r"(_id|id|_key|key|_code|code|_ref|_no|_num|_fk|_sk)$")
_GENERIC = {"id", "name", "date", "type", "value", "description", "status", "code",
            "created_at", "updated_at", "time", "year", "count", "number"}


def _typefam(t: str) -> str:
    t = (t or "").lower()
    if any(k in t for k in ("int", "serial", "number", "numeric", "decimal", "real", "double", "float")):
        return "num"
    if any(k in t for k in ("char", "text", "clob", "string", "varchar", "enum")):
        return "text"
    if any(k in t for k in ("date", "time", "year")):
        return "date"
    return "other"


def _infer_latent_edges(tables, cols_by_table, coltypes) -> List:
    """Infer joinable table pairs from naming/type conventions, to augment declared FKs."""
    edges = []
    norm = {t.lower().rstrip("s"): t for t in tables}          # crude singularized table lookup
    norm.update({t.lower(): t for t in tables})
    # (a) `<X>_id` / `<X>id` / `<X>_key` -> reference to table X
    for t in tables:
        for c in cols_by_table[t]:
            m = re.match(r"(.+?)_?(id|key|code|ref|fk|sk)$", c.lower())
            if not m:
                continue
            ent = m.group(1).strip("_")
            for cand in (ent, ent.rstrip("s"), ent + "s"):
                if cand in norm and norm[cand] != t:
                    edges.append((t, norm[cand]))
    # (b) same key-like column name (with compatible type) in >=2 tables -> mutually joinable
    keycol_tables = defaultdict(list)
    for t in tables:
        for c in cols_by_table[t]:
            cl = c.lower()
            if cl in _GENERIC or not _KEYCOL.search(cl):
                continue
            keycol_tables[cl].append((t, coltypes.get((t, cl), "other")))
    for cl, tts in keycol_tables.items():
        for i in range(len(tts)):
            for j in range(i + 1, len(tts)):
                (ta, tya), (tb, tyb) = tts[i], tts[j]
                if ta != tb and tya == tyb:                    # same type family
                    edges.append((ta, tb))
    return edges


def _join_ambiguity(tables, edges) -> float:
    adj = defaultdict(set)
    pair_direct = defaultdict(int)
    for a, b in edges:
        if a == b:
            continue
        adj[a].add(b); adj[b].add(a)
        pair_direct[frozenset((a, b))] += 1
    tabs = tables[:_MAX_TABLES_PAIRS]
    conn = amb = 0
    for i, a in enumerate(tabs):
        for b in tabs[i + 1:]:
            routes = pair_direct.get(frozenset((a, b)), 0) + len(adj[a] & adj[b])
            if routes >= 1:
                conn += 1
                if routes > 1:
                    amb += 1
    return amb / conn if conn else 0.0


def _semantic_ambiguity(tables, embedder) -> float:
    """Fraction of table-name pairs whose name embeddings exceed the similarity threshold."""
    import numpy as np
    if embedder is None or len(tables) < 2:
        return None
    # humanize names (snake/camel -> words) so the embedding sees the entity, not the identifier
    def human(t):
        return re.sub(r"[_]+", " ", re.sub(r"([a-z])([A-Z])", r"\1 \2", t)).strip().lower()
    tabs = tables[:_MAX_TABLES_PAIRS]
    vecs = [embedder.encode(human(t)) for t in tabs]
    vecs = [v / (np.linalg.norm(v) or 1.0) for v in vecs]
    pairs = high = 0
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            pairs += 1
            if float(np.dot(vecs[i], vecs[j])) >= _SEM_SIM_THRESH:
                high += 1
    return high / pairs if pairs else 0.0


def _score_from_facts(tables, cols_by_table, fk_edges, fkcols, coltypes, embedder=None) -> Dict:
    n = max(len(tables), 1)
    latent = _infer_latent_edges(tables, cols_by_table, coltypes)
    all_edges = list(fk_edges) + latent

    col_tables = defaultdict(set)
    for t, cols in cols_by_table.items():
        for c in cols:
            col_tables[c.lower()].add(t)
    col_collision = sum(1 for _c, ts in col_tables.items() if len(ts) >= 2) / max(len(col_tables), 1)

    # bridge: >=2 FK-ish cols (declared FK cols OR key-like cols) and those are >=half the table
    def keyish(t):
        ks = set(fkcols.get(t, set()))
        ks |= {c.lower() for c in cols_by_table[t] if _KEYCOL.search(c.lower()) and c.lower() not in _GENERIC}
        return ks
    bridge = sum(1 for t in tables if len(keyish(t)) >= 2 and cols_by_table[t]
                 and len(keyish(t)) / len(cols_by_table[t]) >= 0.5)
    bridge_frac = bridge / n

    fk_density = min((len(all_edges) / n) / 2.0, 1.0)
    join_ambiguity = _join_ambiguity(tables, all_edges)
    sem = _semantic_ambiguity(tables, embedder)

    signals = {"join_ambiguity": round(join_ambiguity, 3), "col_collision": round(col_collision, 3),
               "bridge_frac": round(bridge_frac, 3), "fk_density": round(fk_density, 3)}
    if sem is not None:
        signals["semantic_ambiguity"] = round(sem, 3)
        weights = _W
    else:
        weights = {k: v for k, v in _W.items() if k != "semantic_ambiguity"}
        s = sum(weights.values()); weights = {k: v / s for k, v in weights.items()}
    combined = round(sum(weights[k] * signals[k] for k in signals), 3)
    return {"n_tables": len(tables), "n_fk_declared": len(fk_edges), "n_fk_latent": len(latent),
            "signals": signals, "score": combined,
            "suggested_policy": "atomic" if combined >= DEFAULT_THRESHOLD else "aggressive"}


# --------------------------------------------------------------------------- #
# Engine-specific fact extraction (tables, cols_by_table, fk_edges, fkcols, coltypes)
# --------------------------------------------------------------------------- #
def _schema_facts(con):
    tables = datasets.list_tables(con)
    cols, fk_edges, fkcols, types = {}, [], {}, {}
    for t in tables:
        try:
            info = con.execute(f'PRAGMA table_info("{t}")').fetchall()
        except Exception:  # noqa: BLE001
            info = []
        cols[t] = [str(r[1]) for r in info]
        for r in info:
            types[(t, str(r[1]).lower())] = _typefam(str(r[2]))
        fkcols[t] = set()
        try:
            for fk in con.execute(f'PRAGMA foreign_key_list("{t}")').fetchall():
                fkcols[t].add(str(fk[3]).lower())
                if str(fk[2]) in tables:
                    fk_edges.append((t, str(fk[2])))
        except Exception:  # noqa: BLE001
            pass
    return tables, cols, fk_edges, fkcols, types


def _schema_facts_pg(conn, schema: str):
    with conn.cursor() as c:
        c.execute("SELECT table_name, column_name, data_type FROM information_schema.columns "
                  "WHERE table_schema=%s", (schema,))
        cols, types = {}, {}
        for t, col, dt in c.fetchall():
            cols.setdefault(t, []).append(col)
            types[(t, str(col).lower())] = _typefam(dt)
        c.execute(
            "SELECT tc.table_name, kcu.column_name, ccu.table_name FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name "
            "  AND tc.table_schema=kcu.table_schema "
            "JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name=tc.constraint_name "
            "  AND ccu.table_schema=tc.table_schema "
            "WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_schema=%s", (schema,))
        fk_edges, fkcols = [], {t: set() for t in cols}
        for t, col, ftable in c.fetchall():
            fkcols.setdefault(t, set()).add(str(col).lower())
            if ftable in cols:
                fk_edges.append((t, ftable))
    return list(cols), cols, fk_edges, fkcols, types


def _schema_facts_mysql(conn, db: str):
    with conn.cursor() as c:
        c.execute("SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS "
                  "WHERE TABLE_SCHEMA=%s", (db,))
        cols, types = {}, {}
        for t, col, dt in c.fetchall():
            cols.setdefault(t, []).append(col)
            types[(t, str(col).lower())] = _typefam(dt)
        c.execute("SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME FROM information_schema.KEY_COLUMN_USAGE "
                  "WHERE TABLE_SCHEMA=%s AND REFERENCED_TABLE_NAME IS NOT NULL", (db,))
        fk_edges, fkcols = [], {t: set() for t in cols}
        for t, col, ftable in c.fetchall():
            fkcols.setdefault(t, set()).add(str(col).lower())
            if ftable in cols:
                fk_edges.append((t, ftable))
    return list(cols), cols, fk_edges, fkcols, types


def score(con, embedder=None) -> Dict:
    return _score_from_facts(*_schema_facts(con), embedder=embedder)


def score_pg(conn, schema: str, embedder=None) -> Dict:
    return _score_from_facts(*_schema_facts_pg(conn, schema), embedder=embedder)


def score_mysql(conn, db: str, embedder=None) -> Dict:
    return _score_from_facts(*_schema_facts_mysql(conn, db), embedder=embedder)


def suggest_policy(con, threshold: float = DEFAULT_THRESHOLD) -> str:
    return "atomic" if score(con)["score"] >= threshold else "aggressive"


def main():
    import argparse
    import os
    ap = argparse.ArgumentParser(description="Score schema join/grain ambiguity for a SQLite DB.")
    ap.add_argument("db_path")
    ap.add_argument("--semantic", action="store_true", help="add the embedding-based semantic signal")
    args = ap.parse_args()
    emb = None
    if args.semantic:
        from skiewsql.llm import Embedder
        emb = Embedder()
    con = datasets.connect(args.db_path)
    r = score(con, embedder=emb)
    print(f"{os.path.basename(args.db_path)}: score={r['score']} -> {r['suggested_policy']}")
    print(f"  tables={r['n_tables']} fk(declared={r['n_fk_declared']},latent={r['n_fk_latent']}) "
          f"signals={r['signals']}")
    con.close()


if __name__ == "__main__":
    main()
