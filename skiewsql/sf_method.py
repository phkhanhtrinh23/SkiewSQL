"""sf_method.py — run the SkiewSQL view-memory method (retrieve-or-generate reusable CTEs) WITH the optional Layer 3 adversarial verifier, natively on Snowflake, for the Spider 2.0-lite `sf*` tasks. Direct port of bq_method.py to the Snowflake backend:
  * CTE validation uses `cursor.describe()` (compilation only, NO execution, no warehouse time — the exact analogue of the FREE BigQuery dry-run): it confirms the CTE is valid Snowflake SQL and exposes the declared output columns, which is all validation needs.
  * Only the FINAL composed query per question is actually executed (statement-timeout guarded, with a sleep between executions to be gentle on the shared participant warehouse).

Reuses: core.SkillRegistry / ViewSpec / ViewRequest / compose_sql, sqlview.retrieve, agents (rewrite, propose_views, planner, verify_reuse), and SFClient / render_sf_schema / load_sf_tasks / score from spider2sf. Generation of executable SQL (view bodies + final query) is Snowflake-dialect here."""
from __future__ import annotations
from skiewsql.prompt_loader import load_prompt

EXISTING_VIEWS = load_prompt("shared/existing_views.txt")

import argparse
import json
import os
from collections import Counter
from typing import Dict, List, Optional, Tuple

from skiewsql import agents, sqlview, table_catalog, reforce_modules
from skiewsql.core import SkillRegistry, ViewSpec, ViewRequest, compose_sql
from skiewsql.llm import LLM, Embedder, extract_code, extract_json, USAGE
from skiewsql.spider2sf import (SFClient, render_sf_schema, sf_table_blocks, load_sf_tasks, score, _evidence)
from skiewsql.paths import SNOWFLAKE_RUNS_DIR, ensure_dir


def _pack_blocks(blocks: Dict[str, str], budget: int = 12000) -> List[str]:
    """Char-pack whole table-DDL blocks into <=budget chunks (N×M alignment chunks for Snowflake)."""
    chunks, cur, cur_len = [], [], 0
    for blk in blocks.values():
        if cur_len + len(blk) > budget and cur:
            chunks.append("\n\n".join(cur)); cur, cur_len = [], 0
        cur.append(blk); cur_len += len(blk)
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks or [""]

RESULTS_DIR = ensure_dir(SNOWFLAKE_RUNS_DIR)

SQL_REPAIR_ATTEMPTS = 5          # AV-SQL T_max (matches realrun.py)

SF_RULES = load_prompt("sf_method/sf_rules.txt")

# --------------------------------------------------------------------------- #
# Snowflake-dialect generation (view body, final query, direct, repair)
# --------------------------------------------------------------------------- #
VIEW_SYS = load_prompt("sf_method/view_sys.txt")
VIEW_USER = load_prompt("sf_method/view_user.txt")

FINAL_SYS = load_prompt("sf_method/final_sys.txt")
FINAL_USER = load_prompt("sf_method/final_user.txt")

DIRECT_SYS = load_prompt("sf_method/direct_sys.txt")
DIRECT_USER = load_prompt("sf_method/direct_user.txt")


def gen_sf_view(llm, schema, req, existing) -> Optional[ViewSpec]:
    ex = ""
    if existing:
        ex = EXISTING_VIEWS.format(views="\n".join(
            f"- {v.name} ({v.category}): {v.output_columns}" for v in existing[:6]))
    txt = llm.ask(VIEW_SYS, VIEW_USER.format(schema=schema[:14000], name=req.want_name,
                  category=req.category, desc=req.text, outs=req.required_outputs,
                  grain=req.required_grain, existing=ex, error=""), tag="sf_view", max_tokens=1400)
    body = extract_code(txt, langs=("sql", "cte"))
    meta = extract_json(txt) or {}
    if not body:
        return None
    outs = [str(x) for x in (meta.get("output_columns") or req.required_outputs)]
    low = {o.lower() for o in outs}
    for r in req.required_outputs:
        if r.lower() not in low:
            outs.append(r)
    deps = [str(d) for d in (meta.get("depends_on") or []) if any(d == v.name for v in existing)]
    return ViewSpec(name=req.want_name, category=req.category, body_sql=body.strip().rstrip(";"),
                    source_tables=[str(x) for x in (meta.get("source_tables") or [])],
                    output_columns=outs, grain=[str(x) for x in (meta.get("grain") or req.required_grain)],
                    semantic_filters={str(k): str(v) for k, v in (req.required_filters or {}).items()},
                    depends_on=deps, description=req.text)


def compose_sf_final(llm, schema, question, evidence, chosen, plan) -> Optional[str]:
    if not chosen:
        return None
    vs = "\n".join(f"- {v.name} (cols: {', '.join(v.output_columns)}) — {v.description}" for v in chosen)
    txt = llm.ask(FINAL_SYS, FINAL_USER.format(schema=schema[:12000], views=vs, question=question,
                  evidence=evidence, plan=plan), tag="sf_compose", max_tokens=1000)
    sql = extract_code(txt, langs=("sql",))
    return sql.strip().rstrip(";") if sql else None


def gen_sf_direct(llm, schema, question, evidence, prior_error=None) -> Optional[str]:
    err = f"\nPrevious query failed: {prior_error}\nFix it." if prior_error else ""
    txt = llm.ask(DIRECT_SYS, DIRECT_USER.format(schema=schema[:14000], question=question,
                  evidence=evidence, error=err), tag="sf_direct", max_tokens=1400)
    sql = extract_code(txt, langs=("sql",))
    return sql.strip().rstrip(";") if sql else None


# --------------------------------------------------------------------------- #
# AV-SQL Stage 3 — execution-repair (revisor) + semantic revisor, Snowflake dialect. These mirror agents.revise_sql / agents.semantic_revise verbatim in ROLE (the config-B baseline must be a faithful AV-SQL), specialised only for Snowflake dialect + quoting.
# --------------------------------------------------------------------------- #
REVISE_SYS = load_prompt("sf_method/revise_sys.txt")
REVISE_USER = load_prompt("sf_method/revise_user.txt")

SEM_SYS = load_prompt("sf_method/sem_sys.txt")
SEM_USER = load_prompt("sf_method/sem_user.txt")


def revise_sf_sql(llm, schema, question, evidence, sql, error) -> Optional[str]:
    ev = f"External knowledge: {evidence}" if evidence.strip() else ""
    txt = llm.ask(REVISE_SYS, REVISE_USER.format(schema=schema[:14000], question=question,
                  evidence=ev, sql=sql, error=error), tag="sf_revise", max_tokens=1400)
    out = extract_code(txt, langs=("sql",))
    return out.strip().rstrip(";") if out else None


def semantic_revise_sf(llm, schema, rewrite_text, question, evidence, sql, preview) -> Optional[str]:
    ev = f"External knowledge: {evidence}" if evidence.strip() else ""
    txt = llm.ask(SEM_SYS, SEM_USER.format(schema=schema[:12000], rewrite=rewrite_text,
                  question=question, evidence=ev, sql=sql, preview=preview),
                  tag="sf_semantic", max_tokens=1400)
    out = extract_code(txt, langs=("sql",))
    return out.strip().rstrip(";") if out else None


# --------------------------------------------------------------------------- #
# FREE describe-based validation of a generated CTE against Snowflake
# --------------------------------------------------------------------------- #
def validate_sf_view(client: SFClient, registry: SkillRegistry, spec: ViewSpec) -> Tuple[bool, str]:
    try:
        dep_specs = registry.topo_closure(spec.depends_on) if spec.depends_on else []
        chosen = {s.name: s for s in dep_specs}
        chosen[spec.name] = spec
        ordered = sqlview._order_specs(list(chosen.values()))
        with_clause = ",\n".join(s.cte_clause() for s in ordered)
        prefix = "WITH RECURSIVE" if any(s.category == "REC" for s in ordered) else "WITH"
        sql = f"{prefix} {with_clause}\nSELECT * FROM {spec.name} LIMIT 5"
        ok, err, cols = client.describe(sql)              # FREE (compilation only)
        if not ok:
            return False, err
        low = {c.lower() for c in cols}
        missing = [c for c in spec.output_columns if c.lower() not in low]
        return (not missing), ("ok" if not missing else f"declared outputs missing: {missing}")
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


# --------------------------------------------------------------------------- #
# The method loop (online view memory + Layer-3 verify) on Snowflake
# --------------------------------------------------------------------------- #
def _save(tag, rows, client, verify, registries=None):
    out = os.path.join(RESULTS_DIR, f"{tag}_sf_method.json")
    json.dump({"verify": verify, "rows": rows, "n_ok": sum(r["correct"] for r in rows),
               "reuse": sum(r["reused"] for r in rows), "gen": sum(r["generated"] for r in rows),
               "sf_exec_seconds": client.exec_seconds, "sf_n_run": client.n_run,
               "llm_usage": USAGE.snapshot()}, open(out, "w"), indent=2)
    # dump the final per-DB view registries (every CTE body + edges) for later inspection
    if registries:
        from dataclasses import asdict
        gdump = {db: {"views": {n: asdict(v) for n, v in g.views.items()},
                      "n_views": g.n_views()} for db, g in registries.items()}
        json.dump(gdump, open(os.path.join(RESULTS_DIR, f"{tag}_sf_registrys.json"), "w"), indent=2)
    return out


def _init_registry(db: str, seed_dir: str) -> Tuple[SkillRegistry, set]:
    """Config S: load the frozen cold-start seed registry for this DB if present, else empty (config A). Returns (registry, seed_view_names) so reuse can be split seed-vs-online."""
    if seed_dir:
        sp = os.path.join(seed_dir, f"{db}.json")
        if os.path.exists(sp):
            g = sqlview.load_registry(sp)
            return g, set(g.views.keys())
    return SkillRegistry(db_id=db), set()


def run(n, dbs, verify, sleep, max_views, model, tag, seed_dir="", nxm=False, max_subgoals=4,
        use_reforce=False, architecture="legacy", focused_budget=6000):
    tasks = load_sf_tasks(n, dbs)
    client = SFClient()
    llm = LLM(model=model)
    emb = Embedder()
    registries: Dict[str, SkillRegistry] = {}
    seed_names: Dict[str, set] = {}
    rows = []
    cfg = "S(seed)" if seed_dir else ("A" if verify > 0 else "B")
    print(f"SF method run [{cfg}]: {len(tasks)} tasks | verify={verify} seed_dir={seed_dir or '-'}\n")
    for ti, t in enumerate(tasks):
        if ti and ti % 20 == 0:                          # periodic checkpoint
            _save(tag, rows, client, verify, registries)
        db = t["db"]
        ev = _evidence(t)
        # Schema selection: description-catalog shortlist over per-table blocks (replaces the fatal 16k render_sf_schema truncation — Snowflake schemas are large). Same path as BigQuery.
        blocks = sf_table_blocks(db)
        catalog = table_catalog.build_catalog(llm, db, blocks)
        picked = table_catalog.shortlist(llm, t["question"], catalog, k=8, evidence=ev)
        schema = table_catalog.render_selected(blocks, picked, budget=24000) if blocks else render_sf_schema(db)
        # Memory scoping (mirrors realrun.py:324): config B (verify==0) RESETS the registry every question (faithful AV-SQL, no cross-question memory). Config A/S (verify>0) PERSIST the registry across a DB's questions. Config S additionally LOADS a frozen cold-start seed registry at each DB's first question, so reuse can fire from question 1 (no cold start).
        if verify <= 0:
            registries[db] = SkillRegistry(db_id=db)
        elif db not in registries:
            registries[db], seed_names[db] = _init_registry(db, seed_dir)
        g = registries.setdefault(db, SkillRegistry(db_id=db))
        _rw, rw = agents.rewrite_question(llm, "", t["question"], ev)   # schema-free rewrite
        per_tables: Dict[str, set] = {}
        architecture_route = ("nxm" if nxm else architecture)
        direct_route, adaptive_selected = False, set()
        packed = _pack_blocks(blocks)
        packed_with_tables = [
            (chunk, [name for name, block in blocks.items() if block in chunk])
            for chunk in packed]
        if architecture == "auto":
            reqs, per_tables, adaptive_route, adaptive_selected, _nc = agents.adaptive_requests(
                llm, packed_with_tables, rw, ", ".join(blocks.keys()),
                render_selected=lambda tabs: table_catalog.render_selected(
                    blocks, list(tabs), budget=10**9),
                estimate_tokens=lambda text: max(1, len(text) // 4),
                focused_budget=focused_budget, max_subgoals=max_subgoals,
                qualify_outputs=False, tag_prefix="sf_")
            direct_route = adaptive_route == "direct_sql"
            architecture_route = (adaptive_route if direct_route else
                                  f"{adaptive_route}_{'registry' if verify > 0 else 'nomemory'}")
        elif nxm or architecture == "nxm":
            # N×M: decompose the question (schema-free) into M sub-goals, then align each against every DDL chunk to gather its real tables. Mirrors bq_method.
            table_index = ", ".join(blocks.keys())
            reqs, per_tables, _nc = agents.decompose_and_align(
                llm, packed, rw, table_index, max_subgoals=max_subgoals,
                qualify_outputs=False, tag_prefix="sf_")
        else:
            reqs, _raw, _sel = agents.propose_views(llm, schema, rw, max_views=max_views)

        chosen, reused, gen, vrej, seed_reused = [], 0, 0, 0, 0
        reused_names = []                                # views reused this question (for Layer-4 learning)
        sn = seed_names.get(db, set())
        subgoals = []                                    # full per-sub-goal trace (decision + CTE)
        resolved_reqs = {}
        for req in reqs:
            # Reuse decision is made by the LLM over a candidate LIST (embedding is only a coarse list-trimmer, never the final decider). Reject-biased: reuse only on a strict majority of `verify` voters agreeing on the SAME view. Any split / abstention => generate fresh. verify == 0 is an explicit "never reuse" mode (config B: regenerate every sub-goal).
            spec = None
            # embedding-free shortlist: mechanical guard + lexical top-k (emb=None), then LLM decides
            cands = sqlview.retrieve_candidates(g, req, embedder=None, k=6) if verify > 0 else []
            votes = []
            if cands:
                picks = [agents.choose_reuse(llm, req, cands) for _ in range(verify)]
                votes = [{"choice": p[0], "reason": p[1], "confidence": p[2]} for p in picks]
                names = [p[0] for p in picks if p[0]]
                if names:
                    top, cnt = Counter(names).most_common(1)[0]
                    if cnt * 2 > verify:                          # strict majority of ALL voters
                        spec = next(c for c in cands if c.name == top)
                if spec is None:
                    vrej += 1                                     # candidates existed, LLM chose fresh
            if spec is not None:
                chosen.append(spec)
                reused += 1
                reused_names.append(spec.name)
                if spec.name in sn:
                    seed_reused += 1
                resolved_reqs[req.want_name] = spec
                subgoals.append({"subgoal": req.text, "category": req.category,
                                 "decision": "REUSE", "view": spec.name, "from_seed": spec.name in sn,
                                 "candidates": [c.name for c in cands], "votes": votes,
                                 "cte": spec.body_sql})
                continue
            # N×M: generate against ONLY this sub-goal's aligned tables. Else the shortlisted schema.
            req_schema = (table_catalog.render_selected(blocks, list(per_tables[req.want_name]), budget=24000)
                          if per_tables.get(req.want_name) else schema)
            declared = [resolved_reqs[n] for n in req.depends_on if n in resolved_reqs]
            missing_deps = [n for n in req.depends_on if n not in resolved_reqs]
            if missing_deps and not req.may_read_base_tables:
                subgoals.append({"subgoal": req.text, "category": req.category,
                                 "decision": "MISSING_DEPENDENCY", "missing": missing_deps})
                continue
            offered = declared if req.depends_on else list(g.views.values())
            cand = (agents.av_view(llm, req_schema, rw, req.want_name, evidence=ev,
                                   dialect="Snowflake")
                    if req.holistic else gen_sf_view(llm, req_schema, req, offered))
            if cand is None:
                subgoals.append({"subgoal": req.text, "category": req.category,
                                 "decision": "GEN_FAILED", "candidates": [c.name for c in cands],
                                 "votes": votes})
                continue
            if req.depends_on and not req.may_read_base_tables:
                cand.depends_on = list(dict.fromkeys(cand.depends_on + [v.name for v in declared]))
            if g.has(cand.name):
                cand.name = f"{cand.name}_{len(g.views)}"
            g.add_view(cand)
            ok, vmsg = validate_sf_view(client, g, cand)          # FREE describe
            if ok:
                chosen.append(cand)
                gen += 1
                resolved_reqs[req.want_name] = cand
                subgoals.append({"subgoal": req.text, "category": req.category,
                                 "decision": "GENERATE", "view": cand.name,
                                 "candidates": [c.name for c in cands], "votes": votes,
                                 "output_columns": cand.output_columns, "grain": cand.grain,
                                 "cte": cand.body_sql})
            else:
                g.remove_view(cand.name)
                subgoals.append({"subgoal": req.text, "category": req.category,
                                 "decision": "GEN_INVALID", "view": cand.name,
                                 "validate_error": vmsg, "candidates": [c.name for c in cands],
                                 "votes": votes, "cte": cand.body_sql})

        # compose final query
        composed = None
        plan = None
        if chosen:
            plan = agents.planner(llm, schema, rw, chosen)
            final = compose_sf_final(llm, schema, t["question"], ev, chosen, plan)
            if final:
                try:
                    composed = compose_sql(g, [v.name for v in chosen], final)
                except Exception:  # noqa: BLE001
                    composed = None
        if composed is None:
            direct_schema = (table_catalog.render_selected(
                blocks, list(adaptive_selected), budget=24000)
                if direct_route and adaptive_selected else schema)
            composed = gen_sf_direct(llm, direct_schema, t["question"], ev)

        # AV-SQL Stage 3 execution-repair loop: REVISE the composed view-SQL with error feedback (agents.revise_sql role), NOT regenerate a fresh direct query — this preserves the view structure across repair, exactly like realrun.py. Free `describe` compile-check first so a compile error is caught without spending warehouse time.
        df, err = None, "no sql"
        for attempt in range(SQL_REPAIR_ATTEMPTS):
            if not composed:
                break
            ok, derr, _c = client.describe(composed)
            if not ok:
                err = derr[:200]
                if attempt < SQL_REPAIR_ATTEMPTS - 1:
                    composed = revise_sf_sql(llm, schema, t["question"], ev, composed, err) or composed
                continue
            try:
                df = client.run(composed, sleep_s=sleep)
                err = ""
                break
            except Exception as e:  # noqa: BLE001
                err = str(e)[:200]
                df = None
                if attempt < SQL_REPAIR_ATTEMPTS - 1:
                    composed = revise_sf_sql(llm, schema, t["question"], ev, composed, err) or composed

        # AV-SQL Stage 3 semantic Revisor: verify the executing query truly answers the intent. accept the revision only if it still executes (mirrors realrun.py).
        revised = False
        if df is not None and composed:
            preview = str(df.head(3).values.tolist())[:300]
            sem = semantic_revise_sf(llm, schema, rw, t["question"], ev, composed, preview)
            if sem and sem.strip() != composed.strip():
                try:
                    df2 = client.run(sem, sleep_s=sleep)
                    composed, df, revised = sem, df2, True
                except Exception:  # noqa: BLE001
                    pass                                  # keep the pre-revision query
        correct, serr = (score(df, t) if df is not None else (False, err))
        correct_b = bool(correct)
        # Layer 4: learn each reused view's boundary from this question's outcome — a correct reuse is a validated_on example. A reuse that led to a wrong answer is a counter_example. Mirrors realrun.py:346-354. The grown registry is persisted per DB below.
        for nm in reused_names:
            v = g.views.get(nm)
            if v is None:
                continue
            if correct_b and t["question"] not in v.validated_on:
                v.validated_on = (v.validated_on + [t["question"]])[-10:]
            elif (not correct_b) and t["question"] not in v.counter_examples:
                v.counter_examples = (v.counter_examples + [t["question"]])[-10:]
        rows.append({"instance_id": t["instance_id"], "db": db, "correct": correct_b,
                     "reused": reused, "seed_reused": seed_reused, "generated": gen,
                     "verify_reject": vrej, "sem_revised": revised, "registry_views": g.n_views(),
                     "seed_views": len(sn), "error": err or serr,
                     "architecture_route": architecture_route,
                     # full trace for later inspection of CTEs + model reasoning:
                     "question": t["question"], "rewrite": rw, "plan": plan,
                     "subgoals": subgoals, "chosen_views": [v.name for v in chosen],
                     "pred_sql": composed})
        print(f"  {t['instance_id']:10} {db[:18]:18} ok={int(correct_b)} reuse={reused}"
              f"(seed={seed_reused}) gen={gen} vrej={vrej} route={architecture_route} registry={g.n_views()} "
              f"exec={client.exec_seconds:6.1f}s {('' if correct_b else (err or serr)[:44])}", flush=True)

    n_ok = sum(r["correct"] for r in rows)
    tot_reuse = sum(r["reused"] for r in rows)
    tot_gen = sum(r["generated"] for r in rows)
    print(f"\n=== SF method summary (verify={verify}) ===")
    print(f"  tasks {len(rows)} | correct {n_ok} ({100*n_ok/max(1,len(rows)):.1f}%) | "
          f"reuse {tot_reuse} | gen {tot_gen} | verify_rejects {sum(r['verify_reject'] for r in rows)}")
    print(f"  Snowflake executed {client.n_run} queries | {client.exec_seconds:.1f}s warehouse-attached")
    out = _save(tag, rows, client, verify, registries)
    print(f"  wrote {out}")
    client.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--dbs", default="")
    ap.add_argument("--verify", type=int, default=3,
                    help="number of LLM reuse-selector voters (reject-biased strict majority). "
                         "0 disables reuse entirely (config B: always generate fresh)")
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--max_views", type=int, default=3)
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--architecture", default="legacy", choices=["legacy", "auto", "nxm"])
    ap.add_argument("--focused_budget", type=int, default=6000,
                    help="deprecated compatibility knob. Auto now routes by semantic difficulty")
    ap.add_argument("--tag", default="sfm")
    ap.add_argument("--seed_dir", default="",
                    help="config S: dir of frozen cold-start seed registries ({db}.json). Requires verify>0.")
    ap.add_argument("--nxm", type=int, default=0, help="N×M decompose-and-align (schema-free rewrite)")
    ap.add_argument("--max_subgoals", type=int, default=4, help="N×M: cap on M sub-goals")
    ap.add_argument("--reforce", type=int, default=0, help="ReFoRCE modules (reserved)")
    args = ap.parse_args()
    if args.nxm:
        args.architecture = "nxm"
    dbs = [d.strip() for d in args.dbs.split(",") if d.strip()] or None
    run(args.n, dbs, args.verify, args.sleep, args.max_views, args.model, args.tag,
        seed_dir=args.seed_dir, nxm=bool(args.nxm), max_subgoals=args.max_subgoals,
        use_reforce=bool(args.reforce), architecture=args.architecture,
        focused_budget=args.focused_budget)


if __name__ == "__main__":
    main()
