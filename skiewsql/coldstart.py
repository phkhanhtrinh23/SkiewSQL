"""Build a frozen cold-start registry of reusable CTE views before any test question is observed, then pass it to `realrun.py` as the initial memory.

- Prompt A analyzes roles, grains, keys, temporal fields, versioning, join paths, and supported categories.
- Prompt B generates reusable candidates across SEL, NORM, AGG, JOIN, RANK, WIN, RESHAPE, REC, SET, and SEM.
- Prompt C validates candidates against the real SQLite database, repairs failures, and prunes duplicates.
- Prompt D registers `ViewSpec` nodes and `DEPENDS_ON` edges in a `SkillRegistry`, then persists it with `sqlview.save_registry`.

DATA-LEAKAGE RULE (enforced structurally): this module never receives questions or gold SQL. It sees only schema DDL, foreign keys, sample rows, and light profile statistics (row counts + low-cardinality enum values). The produced registry is frozen. Any CTE generated later, during evaluation, is reported by realrun.py as *online growth*, not part of the cold-start registry.

The nodes it emits are ordinary `core.ViewSpec` objects, so the frozen registry is byte-compatible with sqlview.load_registry / retrieve / compose_sql used by the real pipeline."""
from __future__ import annotations
from skiewsql.prompt_loader import load_prompt

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from skiewsql import datasets, sqlview
from skiewsql.agents import CATEGORIES, CAT_HELP
from skiewsql.core import ViewSpec, SkillRegistry
from skiewsql.llm import LLM, extract_json, extract_code, USAGE
from skiewsql.paths import SEED_REGISTRIES_DIR

SEED_ROOT = str(SEED_REGISTRIES_DIR)
MAX_REPAIR = 3


# --------------------------------------------------------------------------- #
# Light, leakage-safe profiling (row counts + low-cardinality enum values)
# --------------------------------------------------------------------------- #
def profile_db(con: sqlite3.Connection, max_enum: int = 12, max_cols_scan: int = 60) -> str:
    """Return a compact profile: per-table row count + enum-like text columns and their values. Uses only the database itself (permitted statistics/sampled values)."""
    lines: List[str] = []
    scanned = 0
    for t in datasets.list_tables(con):
        try:
            n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        except Exception:  # noqa: BLE001
            n = "?"
        lines.append(f'{t}: {n} rows')
        cols = con.execute(f'PRAGMA table_info("{t}")').fetchall()
        for c in cols:
            if scanned >= max_cols_scan:
                break
            name, ctype = c[1], (c[2] or "").upper()
            if not any(k in ctype for k in ("CHAR", "TEXT", "CLOB", "")):
                continue
            scanned += 1
            try:
                d = con.execute(
                    f'SELECT COUNT(DISTINCT "{name}") FROM "{t}"').fetchone()[0]
            except Exception:  # noqa: BLE001
                continue
            if isinstance(d, int) and 1 < d <= max_enum:
                try:
                    vals = con.execute(
                        f'SELECT DISTINCT "{name}" FROM "{t}" '
                        f'WHERE "{name}" IS NOT NULL LIMIT {max_enum}').fetchall()
                    vv = ", ".join(str(v[0])[:24] for v in vals)
                    lines.append(f'  {t}.{name} enum({d}): {vv}')
                except Exception:  # noqa: BLE001
                    pass
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Prompt A — schema analysis
# --------------------------------------------------------------------------- #
ANALYSE_SYS = load_prompt("coldstart/analyse_sys.txt")
ANALYSE_USER = load_prompt("coldstart/analyse_user.txt")


def analyse_schema(llm: LLM, schema: str, profile: str, tag: str = "cs_analyse") -> Dict:
    # Big schemas overflow a small budget (finish=length -> unparseable -> empty analysis). retry larger until the tables list parses.
    d = {}
    for budget in (6000, 9000):
        txt = llm.ask(ANALYSE_SYS, ANALYSE_USER.format(schema=schema, profile=profile),
                      tag=tag, max_tokens=budget)
        d = extract_json(txt) or {}
        if d.get("tables"):
            break
    return d


# --------------------------------------------------------------------------- #
# Prompt B — candidate generation
# --------------------------------------------------------------------------- #
GEN_SYS = load_prompt("coldstart/gen_sys.txt")
GEN_USER = load_prompt("coldstart/gen_user.txt")


# Appended to GEN_USER when qualify_outputs=True: store pass-through output columns QUALIFIED so the frozen seed registry matches the (also-qualified) proposer requests under the strict reuse guard.
QUALIFY_SEED_OUTPUTS = load_prompt("coldstart/qualify_seed_outputs.txt")


def generate_candidates(llm: LLM, analysis: Dict, existing: List[ViewSpec], schema: str = "",
                        max_per_cat: int = 2, tag: str = "cs_generate",
                        qualify_outputs: bool = False) -> Tuple[List[Dict], List[Dict]]:
    ex = "\n".join(f"- {v.name} ({v.category}): outputs {v.output_columns}. Grain {v.grain}"
                   for v in existing) or "(empty)"
    user = GEN_USER.format(schema=schema, analysis=json.dumps(analysis)[:6000], existing=ex,
                           cat_help=CAT_HELP, cats="/".join(CATEGORIES), max_per_cat=max_per_cat)
    if qualify_outputs:
        user += "\n\n" + QUALIFY_SEED_OUTPUTS
    # Raw-name output lists are long. A tight budget truncates the candidates JSON (finish=length) -> unparseable -> zero candidates. Use a generous budget and retry once even larger. Optional: restrict the seed to a subset of categories (e.g. SKIEW_SEED_CATS=SEL,NORM to seed only the safe atomic primitives and let JOIN/AGG/... grow online during the run).
    allow = {c.strip().upper() for c in os.environ.get("SKIEW_SEED_CATS", "").split(",") if c.strip()}
    for budget in (6000, 9500):
        txt = llm.ask(GEN_SYS, user, tag=tag, max_tokens=budget)
        data = extract_json(txt) or {}
        cands = list(data.get("candidates", []) or [])
        if allow:
            cands = [c for c in cands if str(c.get("category", "")).upper() in allow]
        if cands:
            return cands, list(data.get("unsupported_categories", []) or [])
    return [], []


# --------------------------------------------------------------------------- #
# candidate dict -> ViewSpec
# --------------------------------------------------------------------------- #
def _clean_body(sql: str) -> str:
    """Accept either a bare SELECT or a full `WITH x AS (...) SELECT * FROM x`. Return the body SELECT the ViewSpec expects (no WITH wrapper, no trailing semicolon)."""
    if not sql:
        return ""
    body = sql.strip().rstrip(";").strip()
    low = body.lower()
    if low.startswith("with"):
        # extract the innermost defining SELECT: `name AS ( <body> )`
        i = body.find("(")
        depth, j = 0, -1
        for k in range(i, len(body)):
            if body[k] == "(":
                depth += 1
            elif body[k] == ")":
                depth -= 1
                if depth == 0:
                    j = k
                    break
        if i != -1 and j != -1:
            return body[i + 1:j].strip()
    return body


def _to_spec(c: Dict) -> Optional[ViewSpec]:
    name = str(c.get("name", "")).strip()
    cat = str(c.get("category", "")).upper().strip()
    body = _clean_body(str(c.get("sql", "")))
    if not name or cat not in CATEGORIES or not body:
        return None
    outs = [str(x) for x in (c.get("output_columns") or [])]
    desc_bits = [str(c.get("description", name))]
    fams = c.get("potential_question_families") or []
    if fams:
        desc_bits.append("Use for: " + "; ".join(str(f) for f in fams[:6]))
    return ViewSpec(
        name=name, category=cat, body_sql=body,
        source_tables=[str(x) for x in (c.get("input_tables") or [])],
        output_columns=outs,
        grain=[str(x) for x in (c.get("grain") or [])],
        semantic_filters={str(k): str(v) for k, v in (c.get("semantic_filters") or {}).items()},
        depends_on=[str(x) for x in (c.get("input_ctes") or [])],
        description=" | ".join(desc_bits))


# --------------------------------------------------------------------------- #
# Prompt C — execution-grounded validation + repair, in dependency order
# --------------------------------------------------------------------------- #
REPAIR_SYS = load_prompt("coldstart/repair_sys.txt")
REPAIR_USER = load_prompt("coldstart/repair_user.txt")


def _repair(llm: LLM, spec: ViewSpec, existing_names: List[str], error: str,
            tag: str = "cs_repair") -> Optional[str]:
    txt = llm.ask(REPAIR_SYS, REPAIR_USER.format(
        name=spec.name, category=spec.category, outputs=spec.output_columns,
        deps=existing_names or "(none)", body=spec.body_sql, error=error), tag=tag, max_tokens=1100)
    body = extract_code(txt, langs=("sql", "cte"))
    return _clean_body(body) if body else None


def _signature(spec: ViewSpec) -> Tuple:
    return (spec.category, tuple(sorted(o.lower() for o in spec.output_columns)),
            tuple(sorted(g.lower() for g in spec.grain)))


def _order_candidates(specs: List[ViewSpec]) -> List[ViewSpec]:
    """Topologically order candidates so a view's declared deps are built first (deps not present in this batch are ignored — they must already be in the registry)."""
    by_name = {s.name: s for s in specs}
    ordered, visiting, done = [], set(), set()

    def visit(n: str):
        if n in done or n not in by_name or n in visiting:
            return
        visiting.add(n)
        for d in by_name[n].depends_on:
            visit(d)
        visiting.discard(n)
        done.add(n)
        ordered.append(by_name[n])

    for s in specs:
        visit(s.name)
    return ordered


def validate_and_register(con: sqlite3.Connection, registry: SkillRegistry, llm: LLM,
                          candidates: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Turn candidates into validated, non-redundant ViewSpecs and register them in `registry`. Returns (accepted_records, rejected_records)."""
    specs = [s for s in (_to_spec(c) for c in candidates) if s is not None]
    specs = _order_candidates(specs)
    accepted, rejected = [], []
    seen_sigs = {_signature(v): v.name for v in registry.views.values()}

    for spec in specs:
        # keep only deps that actually exist in the registry already (or earlier accepted)
        spec.depends_on = [d for d in spec.depends_on if registry.has(d)]
        # dedup / redundancy prune
        sig = _signature(spec)
        if sig in seen_sigs:
            rejected.append({"name": spec.name, "category": spec.category,
                             "reason": f"redundant with {seen_sigs[sig]}"})
            continue

        ok, msg, attempts = False, "", 0
        cur = spec
        for attempts in range(MAX_REPAIR + 1):
            registry.add_view(cur)
            ok, msg = sqlview.validate_view(con, registry, cur)
            if ok:
                break
            registry.remove_view(cur.name)
            fixed = _repair(llm, cur, list(registry.views.keys()), msg)
            if not fixed or fixed == cur.body_sql:
                break
            cur.body_sql = fixed

        if ok:
            sqlview.enforce_contract(cur, "sqlite")       # derive Φ/G from SQL (accurate guard)
            seen_sigs[sig] = cur.name
            rec = asdict(cur)
            rec["repair_attempts"] = attempts
            accepted.append(rec)
        else:
            rejected.append({"name": spec.name, "category": spec.category,
                             "reason": f"validation failed: {msg}", "attempts": attempts})
    return accepted, rejected


# --------------------------------------------------------------------------- #
# Orchestration for one database
# --------------------------------------------------------------------------- #
def build_db(llm: LLM, con: sqlite3.Connection, db_id: str, *, max_per_cat: int = 2,
             rounds: int = 1) -> Tuple[SkillRegistry, Dict]:
    schema = datasets.render_schema(con)
    profile = profile_db(con)
    analysis = analyse_schema(llm, schema, profile)

    registry = SkillRegistry(db_id=db_id)
    all_accepted, all_rejected, all_unsupported = [], [], []
    for _r in range(max(1, rounds)):
        cands, unsupported = generate_candidates(
            llm, analysis, list(registry.views.values()), schema=schema, max_per_cat=max_per_cat)
        all_unsupported = unsupported
        acc, rej = validate_and_register(con, registry, llm, cands)
        all_accepted += acc
        all_rejected += rej
        if not acc:
            break

    from skiewsql.skillify import attach_skills                  # skillify: attach reuse contract
    attach_skills(llm, registry, dialect="SQLite")
    cats = sorted({v.category for v in registry.views.values()})
    report = {
        "db_id": db_id,
        "database_summary": analysis.get("database_summary", ""),
        "n_accepted": len(all_accepted), "n_rejected": len(all_rejected),
        "categories_covered": cats,
        "categories_unsupported": [u.get("category") for u in all_unsupported],
        "accepted": all_accepted, "rejected": all_rejected,
        "depends_on_edges": registry.n_edges("DEPENDS_ON"),
        "instantiates_edges": registry.n_views(),          # one INSTANTIATES edge per view in the old registry
    }
    return registry, report


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _pick_dbs(questions, spec: str) -> List[str]:
    import collections
    counts = collections.Counter(q.db_id for q in questions)
    if spec.startswith("top:"):
        k = int(spec.split(":")[1])
        return [db for db, _ in counts.most_common(k)]
    return [s.strip() for s in spec.split(",") if s.strip()]


def main():
    ap = argparse.ArgumentParser(description="Build frozen cold-start CTE registries (no test questions).")
    ap.add_argument("--dataset", default="spider", choices=["spider", "bird", "bird_minidev", "spider2lite", "sqlflow_spider", "sqlflow_bird"])
    ap.add_argument("--dbs", default="top:3", help="'top:N' or comma list of db_ids")
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--max_per_cat", type=int, default=2)
    ap.add_argument("--rounds", type=int, default=1, help="generate/validate rounds per DB")
    ap.add_argument("--seed_root", default="", help="override seed-registry output root (e.g. /mnt/win_d/...)")
    ap.add_argument("--tag", default="seed")
    args = ap.parse_args()

    if args.dataset == "spider":
        questions, _t, db_root = datasets.load_spider("dev")
    elif args.dataset == "bird":
        questions, _t, db_root = datasets.load_bird("dev")
    elif args.dataset == "bird_minidev":
        questions, _t, db_root = datasets.load_bird_minidev()
    elif args.dataset.startswith("sqlflow_"):
        questions, _t, db_root = datasets.load_sqlflow(args.dataset.split("_",1)[1])
    else:  # spider2lite (local-SQLite subset)
        from skiewsql import spider2lite
        questions, db_root = spider2lite.load_local()
    dbs = _pick_dbs(questions, args.dbs)

    out_dir = os.path.join(args.seed_root or SEED_ROOT, f"{args.tag}_{args.dataset}")
    os.makedirs(out_dir, exist_ok=True)
    llm = LLM(model=args.model, temperature=0.0)
    USAGE.reset()

    print(f"Cold-start build — dataset={args.dataset} dbs={dbs} model={args.model} "
          f"max_per_cat={args.max_per_cat} rounds={args.rounds}")
    summary = {}
    for db_id in dbs:
        path = datasets.db_path(db_root, db_id, args.dataset)
        con = datasets.connect(path)
        tok0 = USAGE.total
        registry, report = build_db(llm, con, db_id, max_per_cat=args.max_per_cat, rounds=args.rounds)
        report["build_tokens"] = USAGE.total - tok0
        con.close()

        seed_path = os.path.join(out_dir, f"{db_id}.json")
        sqlview.save_registry(registry, seed_path)
        json.dump(report, open(os.path.join(out_dir, f"{db_id}.report.json"), "w"), indent=2)
        summary[db_id] = {"views": registry.n_views(), "accepted": report["n_accepted"],
                          "rejected": report["n_rejected"], "cats": report["categories_covered"],
                          "tokens": report["build_tokens"]}
        print(f"  [{db_id}] views={registry.n_views():2d} accepted={report['n_accepted']} "
              f"rejected={report['n_rejected']} cats={','.join(report['categories_covered'])} "
              f"deps={report['depends_on_edges']} tok={report['build_tokens']}")

    json.dump({"dataset": args.dataset, "model": args.model, "dbs": dbs, "summary": summary,
               "usage": USAGE.snapshot()},
              open(os.path.join(out_dir, "_build_summary.json"), "w"), indent=2)
    print(f"\nSeed registries written to {out_dir}/  (frozen. Load with sqlview.load_registry)")


if __name__ == "__main__":
    main()
