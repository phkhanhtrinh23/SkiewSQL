"""
realrun.py — the REAL SkiewSQL experiment on Spider / BIRD with a real LLM, using the
full AV-SQL pipeline (rewrite -> chunked view proposal -> value-linked view generation /
graph retrieval -> S_filtered -> planner -> SQL generator -> execution repair -> semantic
revisor).

Sequential, per-database protocol (the only protocol under which CTE reuse can occur):
for each database D, the view graph starts EMPTY and grows after every question. The three
configurations share the exact same agents; the only difference is memory:

  (A) SkiewSQL          : graph persists across D's questions  -> retrieve-or-generate
  (B) Baseline (AV-SQL) : graph reset before every question    -> always generate, discard
  (C) SkiewSQL no-guard : memory on, compatibility guard off   -> exposes negative reuse

Usage:
  python -m skiewsql.realrun --dataset spider --dbs top:4 --limit 30 --model gpt-4o-mini
  python -m skiewsql.realrun --dataset bird   --dbs financial,superhero --limit 20
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import signal
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from skiewsql import agents, datasets, sqlview, valuelink
from skiewsql.core import ViewGraph
from skiewsql.llm import LLM, Embedder, USAGE

RESULTS_DIR = os.path.join(_ROOT, "skiewsql", "results_real")
VIEW_VALIDATE_ATTEMPTS = 3
SQL_REPAIR_ATTEMPTS = 5          # AV-SQL T_max
CHUNK_BUDGET = 8000
PER_QUESTION_TIMEOUT = 240       # hard wall-clock cap per question (SIGALRM); bounds any hang


class _QTimeout(Exception):
    pass


def _alarm_handler(signum, frame):
    raise _QTimeout(f"question exceeded {PER_QUESTION_TIMEOUT}s wall-clock")


# --------------------------------------------------------------------------- #
# Value-link-aware view generation (Stage 2b) — used on a graph miss
# --------------------------------------------------------------------------- #
def _verify_gate(llm, embedder, spec, req, n_verify):
    """Layer 4 (cheap counter-example reject) + Layer 3 (N skeptical verifiers, majority-allow).
    Returns the spec if reuse is allowed, else None (-> treat as a miss and generate)."""
    for ce in getattr(spec, "counter_examples", []):
        try:
            if embedder.sim(req.text, ce) >= 0.6:   # sub-goal ~ a known bad-reuse case
                return None, "counter-example"
        except Exception:  # noqa: BLE001
            pass
    allows = 0
    for _ in range(n_verify):
        ok, _r = agents.verify_reuse(llm, spec, req, counter_examples=getattr(spec, "counter_examples", []))
        allows += int(ok)
    return (spec, "verified") if allows * 2 >= n_verify else (None, "verifier-reject")


def _relevant_views(graph, req, embedder, gen_topk):
    """Views to offer the generator as composable building blocks. With whole-graph injection
    (gen_topk<=0 or >=|graph|) the generate prompt grows with the graph — the token overhead that
    made config S cost more. Selective injection returns only the top-k views by embedding
    similarity to the sub-goal, bounding the prompt size regardless of graph size."""
    views = list(graph.views.values())
    if gen_topk is None or gen_topk <= 0 or len(views) <= gen_topk:
        return views
    scored = []
    for v in views:
        try:
            s = embedder.sim(req.text, v.description or v.name)
        except Exception:  # noqa: BLE001
            s = 0.0
        scored.append((s, v))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [v for _, v in scored[:gen_topk]]


def _generate_view(llm, embedder, graph, con, full_schema, req, vindex, gen_topk=0):
    """Generate one CTE, repairing on execution error AND on value-linking mismatches."""
    hints, prior_err, last_ok = None, None, None
    for _ in range(VIEW_VALIDATE_ATTEMPTS):
        cand = agents.generate_view(llm, full_schema, req,
                                    _relevant_views(graph, req, embedder, gen_topk),
                                    value_hints=hints, prior_error=prior_err)
        if cand is None:
            prior_err = "no SQL produced"
            continue
        if graph.has(cand.name):
            cand.name = f"{cand.name}_{len(graph.views)}"
        graph.add_view(cand)
        ok, msg = sqlview.validate_view(con, graph, cand)
        if not ok:
            graph.remove_view(cand.name)
            prior_err, hints = msg, None
            continue
        vh = vindex.ground(cand.body_sql, embedder=embedder) if vindex else []
        if vh:                                   # executes but a filter literal is off
            last_ok = cand
            graph.remove_view(cand.name)
            prior_err, hints = None, vh
            continue
        return cand                              # clean success (already in graph)
    if last_ok is not None:                      # best executing version, keep it
        if graph.has(last_ok.name):
            last_ok.name = f"{last_ok.name}_{len(graph.views)}"
        graph.add_view(last_ok)
        return last_ok
    return None


def _filtered_schema(con, full_schema, tables):
    """Render S_filtered = blocks of the selected tables (case-insensitive match)."""
    actual = {t.lower(): t for t in datasets.list_tables(con)}
    picked, seen = [], set()
    for t in tables:
        a = actual.get(str(t).lower())
        if a and a not in seen:
            seen.add(a)
            picked.append(a)
    if not picked:
        return full_schema
    return "\n\n".join(datasets.table_block(con, t) for t in picked)


# --------------------------------------------------------------------------- #
# One question — the full pipeline
# --------------------------------------------------------------------------- #
def answer_question(llm, embedder, graph, con, full_schema, chunks, vindex, q, *,
                    use_memory, use_guard, tau, max_views, scorer, gen_topk=0, retrieve_fn=None,
                    n_verify=0):
    retrieve_fn = retrieve_fn or sqlview.retrieve
    t0, tok0 = time.time(), USAGE.total

    # Stage 1: question rewriting
    _rw, rewrite_text = agents.rewrite_question(llm, full_schema, q.question, q.evidence)

    # Stage 2a: per-chunk view proposal + schema selection (union -> S_filtered)
    reqs, sel_tables = [], set()
    seen_names = set()
    for chunk_text, _tabs in chunks:
        creqs, _raw, selection = agents.propose_views(llm, chunk_text, rewrite_text,
                                                       max_views=max_views)
        for t in selection.get("tables", []):
            sel_tables.add(t)
        for r in creqs:
            if r.want_name.lower() in seen_names:
                continue
            seen_names.add(r.want_name.lower())
            reqs.append(r)
    reqs = reqs[:max_views]

    # Stage 2b: for each sub-goal, retrieve (SkiewSQL) or generate (value-link aware)
    chosen, reused, generated, diag = [], 0, 0, []
    reused_names = []
    verify_reject = 0
    for req in reqs:
        spec = None
        if use_memory:
            spec, d = retrieve_fn(graph, req, embedder, tau=tau, use_guard=use_guard)
            diag.append({req.want_name: d})
        if spec is not None and n_verify > 0:            # Layer 3/4 gate on a retrieval hit
            spec, vreason = _verify_gate(llm, embedder, spec, req, n_verify)
            if spec is None:
                verify_reject += 1
                diag.append({req.want_name: {"verify_reject": vreason}})
        if spec is not None:
            chosen.append(spec)
            reused += 1
            reused_names.append(spec.name)
            continue
        new_spec = _generate_view(llm, embedder, graph, con, full_schema, req, vindex, gen_topk)
        if new_spec is not None:
            chosen.append(new_spec)
            generated += 1
            for t in new_spec.source_tables:
                sel_tables.add(t)

    sfiltered = _filtered_schema(con, full_schema, sel_tables)

    # Stage 3: planner -> SQL generator
    composed, used_views = None, []
    if chosen:
        plan = agents.planner(llm, sfiltered, rewrite_text, chosen)
        final_select = agents.compose_final(llm, sfiltered, rewrite_text, q.question,
                                            q.evidence, chosen, plan)
        if final_select:
            try:
                composed = sqlview.compose_sql(graph, [v.name for v in chosen], final_select)
                used_views = [v.name for v in chosen]
            except Exception:  # noqa: BLE001
                composed = None
    if composed is None:
        composed = agents.direct_sql(llm, full_schema, rewrite_text, q.question, q.evidence)
        used_views = []

    # Stage 3: execution-grounded repair loop (+ value linking on the final query).
    # Skip entirely when no SQL was produced at all (hard questions) — nothing to run/repair.
    value_fixed = False
    for attempt in range(SQL_REPAIR_ATTEMPTS if composed else 0):
        try:
            datasets.run_sql(con, composed)
            ran, run_err = True, None
        except datasets.ExecError as e:
            ran, run_err = False, str(e)
        if ran:
            vh = vindex.ground(composed, embedder=embedder) if vindex else []
            if vh and not value_fixed and attempt < SQL_REPAIR_ATTEMPTS - 1:
                value_fixed = True
                fixed = agents.revise_sql(llm, sfiltered, q.question, q.evidence, composed,
                                          "a filter value is not in the DB", value_hints=vh)
                if fixed and fixed != composed:
                    composed = fixed
                    continue
            break
        vh = vindex.ground(composed, embedder=embedder) if vindex else None
        fixed = agents.revise_sql(llm, sfiltered, q.question, q.evidence, composed, run_err,
                                  value_hints=vh)
        if not fixed:
            break
        composed = fixed

    # Stage 3: semantic verification pass (Revisor, Eq 9) — adopt only if it still executes
    try:
        preview = str(datasets.run_sql(con, composed)[:3])[:300]
        sem = agents.semantic_revise(llm, sfiltered, rewrite_text, q.question, q.evidence,
                                     composed, preview)
        if sem and sem != composed:
            try:
                datasets.run_sql(con, sem)
                composed = sem
            except datasets.ExecError:
                pass
    except datasets.ExecError:
        pass

    correct, err_msg = scorer(con, composed, q) if composed else (False, "no sql")
    used_reuse = reused > 0
    return {
        "qid": q.qid, "db_id": q.db_id, "question": q.question,
        "n_views": len(reqs), "reused": reused, "generated": generated,
        "no_new_cte": (generated == 0),
        "coverage": (reused / len(reqs)) if reqs else 1.0,
        "used_views": used_views, "used_reuse": used_reuse, "reused_names": reused_names,
        "verify_reject": verify_reject,
        "correct": bool(correct), "negative_reuse": bool(used_reuse and not correct),
        "error": err_msg, "tokens": USAGE.total - tok0,
        "secs": round(time.time() - t0, 2), "pred_sql": composed, "diag": diag,
    }


# --------------------------------------------------------------------------- #
# One configuration over (db_id -> ordered questions)
# --------------------------------------------------------------------------- #
_SCHEMA_MEMO, _CHUNK_MEMO, _VINDEX = {}, {}, {}


def _prep_db(con, db_id, path, no_valuelink=False):
    if db_id not in _SCHEMA_MEMO:
        _SCHEMA_MEMO[db_id] = datasets.render_schema(con)
        _CHUNK_MEMO[db_id] = datasets.chunk_schema(con, budget_tokens=CHUNK_BUDGET)
    if no_valuelink:                                   # skip the CPU-heavy LSH build + sqlglot linking
        return _SCHEMA_MEMO[db_id], _CHUNK_MEMO[db_id], None
    if path not in _VINDEX:
        try:
            _VINDEX[path] = valuelink.get_index(con, path)
        except Exception as e:  # noqa: BLE001
            print(f"  (value index unavailable for {db_id}: {e})")
            _VINDEX[path] = None
    return _SCHEMA_MEMO[db_id], _CHUNK_MEMO[db_id], _VINDEX[path]


def _make_scorer(dataset):
    if dataset == "spider2lite":
        from skiewsql import spider2lite
        return spider2lite.score
    return lambda con, sql, q: datasets.ex_match(con, sql, q.gold_sql)


def _failed_row(q, err):
    """A safe placeholder row so a single crashing question is scored wrong and the run continues."""
    return {"qid": q.qid, "db_id": q.db_id, "question": q.question,
            "n_views": 0, "reused": 0, "generated": 0, "no_new_cte": True, "coverage": 0.0,
            "used_views": [], "used_reuse": False, "reused_names": [],
            "correct": False, "negative_reuse": False,
            "error": f"{type(err).__name__}: {err}", "tokens": 0, "secs": 0.0,
            "pred_sql": None, "diag": []}


def run_config(name, by_db, *, use_memory, use_guard, tau, model, max_views, db_root, dataset,
               seed=False, seed_dir=None, gen_topk=0, retriever="dense", n_verify=0, no_valuelink=False):
    from skiewsql import retriever as retriever_mod
    llm = LLM(model=model, temperature=0.0)
    embedder = Embedder()
    scorer = _make_scorer(dataset)
    retrieve_fn = retriever_mod.get_retriever(retriever)
    rows, final_graph_sizes = [], {}
    for db_id, qs in by_db.items():
        path = datasets.db_path(db_root, db_id, dataset)
        con = datasets.connect(path)
        full_schema, chunks, vindex = _prep_db(con, db_id, path, no_valuelink=no_valuelink)
        # Cold-start seed: load the frozen prebuilt graph for this DB (config S). The seed set is
        # captured now, before any online growth, so reuse hits can be split seed-vs-online.
        graph = ViewGraph(db_id=db_id)
        seed_names = set()
        if seed and seed_dir:
            sp = os.path.join(seed_dir, f"{db_id}.json")
            if os.path.exists(sp):
                graph = sqlview.load_graph(sp)
                seed_names = set(graph.views.keys())
            else:
                print(f"  (no seed graph for {db_id} at {sp}; starting empty)")
        for i, q in enumerate(qs):
            if not use_memory:
                graph = ViewGraph(db_id=db_id)
            signal.signal(signal.SIGALRM, _alarm_handler)
            signal.alarm(PER_QUESTION_TIMEOUT)
            try:
                r = answer_question(llm, embedder, graph, con, full_schema, chunks, vindex, q,
                                    use_memory=use_memory, use_guard=use_guard, tau=tau,
                                    max_views=max_views, scorer=scorer, gen_topk=gen_topk,
                                    retrieve_fn=retrieve_fn, n_verify=n_verify)
            except Exception as e:  # noqa: BLE001 — one bad/slow question must not kill a long run
                r = _failed_row(q, e)
                print(f"  [{name}] {db_id}#{i:02d} ERROR (counted wrong, continuing): "
                      f"{type(e).__name__}: {str(e)[:80]}")
            finally:
                signal.alarm(0)
            r["db_index"] = i
            r["graph_views"] = graph.n_views()
            r["seed_views"] = len(seed_names)
            r["online_views"] = max(0, graph.n_views() - len(seed_names))
            r["seed_reuse"] = sum(1 for n in r["reused_names"] if n in seed_names)
            rows.append(r)
            # Layer 4: learn each reused view's boundary from this question's outcome.
            for nm in r["reused_names"]:
                v = graph.views.get(nm)
                if v is None:
                    continue
                if r["correct"] and q.question not in v.validated_on:
                    v.validated_on = (v.validated_on + [q.question])[-10:]
                elif r["negative_reuse"] and q.question not in v.counter_examples:
                    v.counter_examples = (v.counter_examples + [q.question])[-10:]
            print(f"  [{name}] {db_id}#{i:02d} chunks={len(chunks)} reuse={r['reused']} "
                  f"(seed={r['seed_reuse']}) gen={r['generated']} vrej={r.get('verify_reject', 0)} "
                  f"graph={r['graph_views']} ok={int(r['correct'])} tok={r['tokens']}")
        final_graph_sizes[db_id] = graph.n_views()
        con.close()
    return rows, final_graph_sizes


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def summarize(name, rows, final_graph_sizes, usage_snapshot):
    n = len(rows)
    cold = [r for r in rows if r["db_index"] == 0]
    warm = [r for r in rows if r["db_index"] > 0]
    with_views = [r for r in rows if r["n_views"] > 0]
    total_views = sum(r["n_views"] for r in with_views)
    total_reused = sum(r["reused"] for r in with_views)
    total_seed_reuse = sum(r.get("seed_reuse", 0) for r in with_views)
    total_gen = sum(r["generated"] for r in rows)
    seed_sizes = {db: rs[0].get("seed_views", 0)
                  for db, rs in _group_by_db(rows).items() if rs}

    def acc(rs):
        return round(sum(r["correct"] for r in rs) / len(rs), 4) if rs else None

    return {
        "config": name, "questions": n,
        "exec_accuracy": acc(rows),
        "cold_start_acc": acc(cold), "warm_acc": acc(warm),
        "exact_reuse_rate": round(total_reused / total_views, 4) if total_views else 0.0,
        "seed_reuse_rate": round(total_seed_reuse / total_views, 4) if total_views else 0.0,
        "seed_reuse_count": total_seed_reuse,
        "pct_no_new_cte": round(sum(r["no_new_cte"] for r in rows) / n, 4),
        "total_views_generated": total_gen,
        "avg_new_views_per_q": round(total_gen / n, 3),
        "real_total_tokens": usage_snapshot["total_tokens"],
        "real_tokens_by_stage": usage_snapshot["by_tag"],
        "negative_reuse_count": sum(r["negative_reuse"] for r in rows),
        "verify_reject_count": sum(r.get("verify_reject", 0) for r in rows),
        "final_graph_sizes": final_graph_sizes,
        "seed_graph_sizes": seed_sizes,
        "avg_secs_per_q": round(sum(r["secs"] for r in rows) / n, 2),
    }


def _group_by_db(rows):
    out = collections.OrderedDict()
    for r in rows:
        out.setdefault(r["db_id"], []).append(r)
    return out


def pct(x):
    return f"{100*x:5.1f}%" if isinstance(x, (int, float)) else str(x)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def pick_dbs(questions, spec, limit):
    by_db = collections.OrderedDict()
    counts = collections.Counter(q.db_id for q in questions)
    if spec.startswith("top:"):
        k = int(spec.split(":")[1])
        chosen_dbs = [db for db, _ in counts.most_common(k)]
    else:
        chosen_dbs = [s.strip() for s in spec.split(",") if s.strip()]
    for db in chosen_dbs:
        qs = [q for q in questions if q.db_id == db][:limit]
        if qs:
            by_db[db] = qs
    return by_db


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="spider", choices=["spider", "bird", "spider2lite"])
    ap.add_argument("--dbs", default="top:4", help="'top:N' or comma list of db_ids")
    ap.add_argument("--limit", type=int, default=30, help="max questions per db")
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--tau", type=float, default=0.6)
    ap.add_argument("--max_views", type=int, default=3)
    ap.add_argument("--gen_topk", type=int, default=0,
                    help="views injected into the generate prompt: 0=whole graph (old), "
                         "k>0=top-k most relevant (bounds prompt size vs graph)")
    ap.add_argument("--retriever", default="dense", choices=["dense", "hybrid"],
                    help="dense=embedding cosine; hybrid=RRF(dense, BM25) over contract candidates")
    ap.add_argument("--verify", type=int, default=0,
                    help="N skeptical reuse-verifiers on each hit (majority-allow) + counter-example "
                         "reject; 0=off. Guards against negative reuse (Layer 3/4).")
    ap.add_argument("--repair", type=int, default=SQL_REPAIR_ATTEMPTS, help="SQL execution-repair attempts (lower=faster)")
    ap.add_argument("--view_attempts", type=int, default=VIEW_VALIDATE_ATTEMPTS, help="view validation attempts (lower=faster)")
    ap.add_argument("--no_valuelink", action="store_true", help="skip value-linking (LSH+sqlglot) to speed up heavy DBs")
    ap.add_argument("--no_guard", action="store_true",
                    help="force the symbolic compatibility guard OFF for all configs (to isolate "
                         "the neural verifier's protective value).")
    ap.add_argument("--configs", default="A,B", help="subset of A,B,C,S")
    ap.add_argument("--seed_tag", default="seed", help="tag of the cold-start seed graphs (config S)")
    ap.add_argument("--seed_dir", default="", help="explicit seed-graph dir (overrides --seed_tag)")
    ap.add_argument("--tag", default="run")
    args = ap.parse_args()

    if args.dataset == "spider":
        questions, _tables, db_root = datasets.load_spider("dev")
    elif args.dataset == "bird":
        questions, _tables, db_root = datasets.load_bird("dev")
    else:  # spider2lite: local-SQLite subset, CSV-scored
        from skiewsql import spider2lite
        questions, db_root = spider2lite.load_local()
    by_db = pick_dbs(questions, args.dbs, args.limit)
    print(f"Dataset={args.dataset} model={args.model} dbs={list(by_db)} "
          f"counts={ {k: len(v) for k, v in by_db.items()} } tau={args.tau}")

    globals()["SQL_REPAIR_ATTEMPTS"] = args.repair
    globals()["VIEW_VALIDATE_ATTEMPTS"] = args.view_attempts
    cfg_defs = {
        "A": ("A_SkiewSQL", dict(use_memory=True, use_guard=True)),
        "B": ("B_Baseline_AVSQL", dict(use_memory=False, use_guard=True)),
        "C": ("C_SkiewSQL_noguard", dict(use_memory=True, use_guard=False)),
        "S": ("S_ColdStart_Seed", dict(use_memory=True, use_guard=True, seed=True)),
    }
    seed_dir = args.seed_dir or os.path.join(RESULTS_DIR, "seed_graphs",
                                             f"{args.seed_tag}_{args.dataset}")
    if "S" in [k.strip() for k in args.configs.split(",")]:
        print(f"Cold-start seed graphs: {seed_dir}")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    summaries, all_rows = {}, {}
    for key in args.configs.split(","):
        key = key.strip()
        if key not in cfg_defs:
            continue
        cname, kw = cfg_defs[key]
        if args.no_guard:
            cname, kw = cname + "_noguard", {**kw, "use_guard": False}
        USAGE.reset()
        print(f"\n=== Running {cname} ===")
        rows, fsizes = run_config(cname, by_db, tau=args.tau, model=args.model,
                                  max_views=args.max_views, db_root=db_root,
                                  dataset=args.dataset, seed_dir=seed_dir,
                                  gen_topk=args.gen_topk, retriever=args.retriever,
                                  n_verify=args.verify, no_valuelink=args.no_valuelink, **kw)
        snap = USAGE.snapshot()
        summaries[cname] = summarize(cname, rows, fsizes, snap)
        all_rows[cname] = rows
        out = os.path.join(RESULTS_DIR, f"{args.tag}_{args.dataset}_{cname}.json")
        json.dump({"summary": summaries[cname], "rows": rows}, open(out, "w"), indent=2)

    # ---- comparison table ----------------------------------------------------
    print("\n" + "=" * 92)
    print(f"SUMMARY — dataset={args.dataset}, dbs={list(by_db)}, model={args.model}")
    print("=" * 92)
    keys = [
        ("exec_accuracy", "Execution accuracy", True),
        ("cold_start_acc", "Cold-start EX (Q#0/db)", True),
        ("warm_acc", "Warm EX (later Qs)", True),
        ("exact_reuse_rate", "Exact view-reuse rate", True),
        ("seed_reuse_rate", "Seed view-reuse rate", True),
        ("pct_no_new_cte", "% Q with no new CTE", True),
        ("total_views_generated", "Total CTE generations", False),
        ("avg_new_views_per_q", "Avg new views / Q", False),
        ("real_total_tokens", "REAL total tokens", False),
        ("negative_reuse_count", "Negative-reuse count", False),
        ("avg_secs_per_q", "Avg secs / Q", False),
    ]
    cols = list(summaries)
    print(f"{'metric':26} " + " ".join(f"{c:>22}" for c in cols))
    for k, label, ispct in keys:
        vals = [pct(summaries[c][k]) if ispct else str(summaries[c][k]) for c in cols]
        print(f"{label:26} " + " ".join(f"{x:>22}" for x in vals))

    json.dump(summaries, open(os.path.join(RESULTS_DIR, f"{args.tag}_{args.dataset}_summary.json"), "w"),
              indent=2)
    print(f"\nWrote results to {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
