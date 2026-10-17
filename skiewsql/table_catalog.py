"""table_catalog.py — description-based table shortlisting for schemas too large to show. Spider 2.0 cloud schemas run to 836k chars (BigQuery `bls`), of which the pipeline historically showed the first 16k — 1.9%. Naive chunking is not an option either: at ~15k chars per table a chunk-per-question sweep would cost dozens of proposer calls.

Table NAMES alone are too vague to shortlist on (`bls` tables are things like `cu_series`, `wm_data_1_AllData`), so we build a CATALOG once per database:

    1. BUILD (offline, cached to disk): for every table, one line describing what it holds, generated in batches from the table name + its column names. Cheap and reusable.
    2. SHORTLIST (per question): show the compact catalog (name + description, all tables fit easily) and ask which tables the question needs.
    3. RENDER: emit those tables IN FULL, degrading gracefully — if the selection still exceeds the budget, trim each table's COLUMN LIST (keys and a prefix are kept) rather than dropping whole tables, so a needed table is never invisible.

Dialect-agnostic: callers pass {table_name: ddl_block}."""
from __future__ import annotations
from skiewsql.prompt_loader import load_prompt

import json
import os
import re
import sys
from typing import Dict, List
from skiewsql.paths import TABLE_CATALOGS_DIR

CATALOG_DIR = str(TABLE_CATALOGS_DIR)
BATCH = 12                 # tables described per LLM call
COLS_FOR_DESC = 40         # column names shown to the describer (enough to characterise a table)


DESC_SYS = load_prompt("table_catalog/desc_sys.txt")
DESC_USER = load_prompt("table_catalog/desc_user.txt")

PICK_SYS = load_prompt("table_catalog/pick_sys.txt")
PICK_USER = load_prompt("table_catalog/pick_user.txt")


def _cols_of(ddl: str, limit: int = COLS_FOR_DESC) -> List[str]:
    """Column names from a CREATE TABLE block (backtick / double-quote / bare)."""
    body = ddl[ddl.find("(") + 1:]
    cols = []
    for line in body.split("\n"):
        m = re.match(r"\s*[`\"]?([A-Za-z_][\w\-]*)[`\"]?\s+\S", line)
        if m and m.group(1).lower() not in ("primary", "foreign", "key", "constraint", "unique"):
            cols.append(m.group(1))
        if len(cols) >= limit:
            break
    return cols


def build_catalog(llm, db: str, blocks: Dict[str, str], force: bool = False) -> Dict[str, str]:
    """{table: one-line description}, cached on disk — built once per database."""
    os.makedirs(CATALOG_DIR, exist_ok=True)
    path = os.path.join(CATALOG_DIR, f"{db}.json")
    if os.path.exists(path) and not force:
        try:
            return json.load(open(path))
        except Exception:  # noqa: BLE001
            pass
    from skiewsql.llm import extract_json
    cat: Dict[str, str] = {}
    names = list(blocks)
    for i in range(0, len(names), BATCH):
        chunk = names[i:i + BATCH]
        listing = "\n".join(f"- {t}: columns = {', '.join(_cols_of(blocks[t]))}" for t in chunk)
        try:
            d = extract_json(llm.ask(DESC_SYS, DESC_USER.format(tables=listing),
                                     tag="catalog_describe", max_tokens=1400)) or {}
            got = d.get("descriptions") or {}
            for t in chunk:
                cat[t] = str(got.get(t, "")) or f"table {t}"
        except Exception:  # noqa: BLE001
            for t in chunk:
                cat[t] = f"table {t}"
    json.dump(cat, open(path, "w"), indent=1)
    return cat


def shortlist(llm, question: str, catalog: Dict[str, str], k: int = 8, evidence: str = "") -> List[str]:
    """Pick the tables this question needs, from the compact catalog (names + descriptions)."""
    from skiewsql.llm import extract_json
    listing = "\n".join(f"- {t}: {d}" for t, d in catalog.items())
    ev = f"External knowledge: {evidence}" if (evidence or "").strip() else ""
    try:
        d = extract_json(llm.ask(PICK_SYS, PICK_USER.format(question=question, evidence=ev,
                                                            catalog=listing[:60000], k=k),
                                 tag="catalog_pick", max_tokens=600)) or {}
        low = {t.lower(): t for t in catalog}
        picked = [low[str(x).lower()] for x in (d.get("tables") or []) if str(x).lower() in low]
        return picked[:k] or list(catalog)[:k]
    except Exception:  # noqa: BLE001
        return list(catalog)[:k]


def _canon(name: str) -> str:
    """Collapse a table name to its shard-family base so the wildcard/stem/concrete forms of a date-sharded BigQuery table all resolve to one key. `events_*`, `events_<YYYYMMDD>`, `proj.ds.events_20210131` → `events`. Mirrors spider2bq._stem plus the wildcard rewrite."""
    s = str(name).strip().strip("`\"").split(".")[-1].lower()   # drop project.dataset qualifier
    s = re.sub(r"[_-]?\*+$", "", s)                             # wildcard suffix: events_* / events*
    s = re.sub(r"<yyyymmdd>$|<yyyymm>$|<n>$", "", s)            # _stem placeholders (lowercased)
    s = re.sub(r"(19|20)\d{6}$", "", s)                         # concrete YYYYMMDD shard
    s = re.sub(r"(19|20)\d{4}$", "", s)                         # concrete YYYYMM shard
    s = re.sub(r"\d+$", "", s)                                  # trailing numeric shard
    return s.rstrip("_-")


def _resolve_tables(blocks: Dict[str, str], tables: List[str]) -> List[str]:
    """Match requested names to block keys: exact first, then shard-family canonical. Names that the align/decompose model returns in wildcard form (events_*) still find the stem key (events_<...>)."""
    matched: List[str] = []
    seen = set()
    by_canon: Dict[str, List[str]] = {}
    for k in blocks:
        by_canon.setdefault(_canon(k), []).append(k)
    for t in tables:
        cands = [t] if t in blocks else by_canon.get(_canon(t), [])
        for k in cands:
            if k not in seen:
                matched.append(k); seen.add(k)
    return matched


def render_selected(blocks: Dict[str, str], tables: List[str], budget: int = 24000) -> str:
    """Render the chosen tables, trimming COLUMNS (never dropping a table) if over budget, so a needed table is never invisible — the failure mode a prefix slice creates."""
    chosen = _resolve_tables(blocks, tables)
    if not chosen:
        # No requested name matched any block, even by shard family. Fall back to the first 3 tables so we render *something*, but SURFACE it — a silent fallback reads as a real schema and produced the ga4/ga360 gen=0 failures in the N×M path.
        print(f"[render_selected] WARN no table matched {list(tables)[:6]} "
              f"against {len(blocks)} blocks. Falling back to first 3", file=sys.stderr)
        chosen = list(blocks)[:3]
    total = sum(len(blocks[t]) for t in chosen)
    if total <= budget:
        return "\n\n".join(blocks[t] for t in chosen)
    per = max(budget // max(len(chosen), 1), 900)
    out = []
    for t in chosen:
        b = blocks[t]
        if len(b) <= per:
            out.append(b); continue
        head, lines = b.split("\n")[0], b.split("\n")[1:]
        keep, n = [], 0
        for ln in lines:
            if n + len(ln) > per:
                break
            keep.append(ln); n += len(ln)
        out.append(head + "\n" + "\n".join(keep)
                   + f"\n  /* ... column list truncated ({len(lines)} columns total) ... */\n);")
    return "\n\n".join(out)
