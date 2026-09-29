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

from skiewsql import agents, datasets, sqlview, valuelink, compose_guards
from skiewsql.core import ViewGraph
from skiewsql.llm import LLM, Embedder, USAGE

RESULTS_DIR = os.path.join(_ROOT, "skiewsql", "results_real")
VIEW_VALIDATE_ATTEMPTS = 3
SQL_REPAIR_ATTEMPTS = 5          # AV-SQL T_max
CHUNK_BUDGET = 8000
PER_QUESTION_TIMEOUT = int(os.environ.get("SKIEW_PER_Q", "240"))  # per-question wall-clock cap (SIGALRM); bounds any hang. Raise via SKIEW_PER_Q for slow providers (Together A ~11min/q)


class _QTimeout(BaseException):
    # BaseException, NOT Exception: the SIGALRM almost always fires while we're inside an LLM call,
    # and LLM.chat / the repair / compose blocks all use bare `except Exception` with a retry loop.
    # If _QTimeout were an Exception those blocks would SWALLOW the per-question timeout and retry,
    # so a question could loop for hours (observed: f1/bank_sales hung 3-4h despite the 240s alarm).
    # As a BaseException it unwinds straight past every `except Exception` to the per-question loop,
    # which catches it explicitly. Same rationale as KeyboardInterrupt being a BaseException.
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


def _attach_card(llm, graph, spec, skill_cards):
    """Give a freshly generated view the SAME rich skill card a seeded view has (when_to_use /
    output_schema / grounded_columns / metric / composition), so online-grown and seeded views are
    retrievable and selectable on equal footing. Costs 1 LLM call per accepted new view."""
    if not skill_cards or spec is None:
        return
    from skiewsql import skillify
    skillify.attach_skill_one(llm, spec, list(graph.views.values()))


def _generate_view(llm, embedder, graph, con, full_schema, req, vindex, gen_topk=0, skill_cards=False,
                   reforce="", nx1=False):
    """Generate one CTE, repairing on execution error AND on value-linking mismatches."""
    hints, prior_err, last_ok = None, None, None
    for _ in range(VIEW_VALIDATE_ATTEMPTS):
        if nx1:      # AV-SQL-style: exploratory per-chunk CTE (full_schema here is the chunk schema)
            cand = agents.av_view(llm, full_schema, req.text, req.want_name)
        else:
            cand = agents.generate_view(llm, full_schema, req,
                                    _relevant_views(graph, req, embedder, gen_topk),
                                    value_hints=hints, prior_error=prior_err, reforce=reforce)
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
        _attach_card(llm, graph, cand, skill_cards)
        return cand                              # clean success (already in graph)
    if last_ok is not None:                      # best executing version, keep it
        if graph.has(last_ok.name):
            last_ok.name = f"{last_ok.name}_{len(graph.views)}"
        graph.add_view(last_ok)
        _attach_card(llm, graph, last_ok, skill_cards)
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
def _result_sig(rows):
    """Order-insensitive canonical signature of a result set, for voting. None if unhashable."""
    try:
        return tuple(sorted(tuple(str(c) for c in r) for r in rows))
    except Exception:  # noqa: BLE001
        return None


def _self_consistent_finalize(llm, con, schema, rewrite_text, question, evidence, composed, k):
    """Semantic self-check + self-consistency over the FINAL query. Candidate 0 is the composed query
    as-is; the rest are independent semantic re-derivations. Execute each, group by result-set
    signature, and return the SQL of the plurality result (ties keep the earliest → the original stays
    unless a majority of re-derivations agree on a different answer). k<=1 keeps the old single-pass
    behaviour. Never returns something that fails to execute."""
    try:
        preview = str(datasets.run_sql(con, composed)[:3])[:300]
    except datasets.ExecError:
        preview = "(did not execute)"
    candidates = [composed]
    for _ in range(max(0, k - 1)):
        sem = agents.semantic_revise(llm, schema, rewrite_text, question, evidence, composed, preview)
        if sem and sem not in candidates:
            candidates.append(sem)
    if len(candidates) == 1:
        return composed
    # vote by executed result set; keep a representative SQL + first-seen order per signature
    tally, rep, order = {}, {}, {}
    for i, c in enumerate(candidates):
        try:
            sig = _result_sig(datasets.run_sql(con, c))
        except datasets.ExecError:
            continue
        if sig is None:
            continue
        tally[sig] = tally.get(sig, 0) + 1
        if sig not in rep:
            rep[sig], order[sig] = c, i
    if not tally:
        return composed                                    # nothing executed cleanly → keep original
    best = max(tally, key=lambda s: (tally[s], -order[s]))  # most votes, tie → earliest candidate
    return rep[best]


def answer_question(llm, embedder, graph, con, full_schema, chunks, vindex, q, *,
                    use_memory, use_guard, tau, max_views, scorer, gen_topk=0, retrieve_fn=None,
                    n_verify=0, self_consistency=1, skill_cards=False, label_free=False, use_reforce=False,
                    nxm=False, max_subgoals=8, nx1=False):
    retrieve_fn = retrieve_fn or sqlview.retrieve
    t0, tok0 = time.time(), USAGE.total

    # Stage 1: question rewriting
    _rw, rewrite_text = agents.rewrite_question(llm, "", q.question, q.evidence)  # schema-free rewrite

    # Stage 2a: view proposal + schema selection (union -> S_filtered)
    per_tables: Dict[str, set] = {}
    if nx1:
        # N×1 (AV-SQL / SkiewSQL v2m): one whole-question view per schema chunk; NO sub-goal
        # decomposition. Each chunk's view is generated against that chunk's tables.
        reqs, per_tables = agents.nx1_requests(chunks, rewrite_text)
        sel_tables = set().union(*per_tables.values()) if per_tables else set()
    elif nxm:
        # N×M: decompose once (whole-DB table index), then align each of M sub-goals against all N
        # chunks. No cap at max_views.
        table_index = ", ".join(sorted({t for _c, tabs in chunks for t in (tabs or [])}))
        chunk_texts = [c for c, _t in chunks]
        reqs, per_tables, _ncalls = agents.decompose_and_align(
            llm, chunk_texts, rewrite_text, table_index, max_subgoals=max_subgoals)
        sel_tables = set().union(*per_tables.values()) if per_tables else set()
    else:
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
    reforce_q = ""
    if use_reforce:
        from skiewsql import reforce_modules
        _fmt = reforce_modules.format_answer(llm, q.question)
        if _fmt:
            reforce_q = ("\nREQUIRED ANSWER FORMAT (return EXACTLY these columns, in this order, "
                         "nothing more):\n" + _fmt + "\n")
    chosen, reused, generated, diag = [], 0, 0, []
    reused_names, reused_specs = [], []
    verify_reject = 0
    for req in reqs:
        spec = None
        if use_memory:
            if sqlview.deterministic_reuse_on():          # Zero-Mem: guard+embedding, no LLM verify
                spec, d = sqlview.select_reuse(graph, req, embedder, tau=tau, use_guard=use_guard)
            else:
                spec, d = retrieve_fn(graph, req, embedder, tau=tau, use_guard=use_guard)
            diag.append({req.want_name: d})
        if spec is not None and n_verify > 0 and not sqlview.deterministic_reuse_on():
            spec, vreason = _verify_gate(llm, embedder, spec, req, n_verify)
            if spec is None:
                verify_reject += 1
                diag.append({req.want_name: {"verify_reject": vreason}})
        if spec is not None:
            chosen.append(spec)
            reused += 1
            reused_names.append(spec.name)
            reused_specs.append(spec)
            continue
        # N×M: each sub-goal generates against ONLY its aligned tables; else the full schema.
        req_schema = (_filtered_schema(con, full_schema, per_tables[req.want_name])
                      if per_tables.get(req.want_name) else full_schema)
        sub_rf = reforce_q + (compose_guards.CARRY_CLAUSE if compose_guards.ON else "")
        if use_reforce:
            from skiewsql import reforce_modules
            def _probe(q, _c=con):
                return str(datasets.run_sql(_c, q)[:5])[:500]
            pre_info, _n = reforce_modules.exploration(
                llm, _probe,
                f"{req.text} (required outputs: {req.required_outputs}; grain: {req.required_grain})",
                req_schema[:6000], api="sqlite")
            if pre_info:
                sub_rf += ("\nColumn exploration — VALUES observed for this sub-goal:\n"
                           + pre_info[:4000] + "\n")
        new_spec = _generate_view(llm, embedder, graph, con, req_schema, req, vindex, gen_topk,
                                  skill_cards=skill_cards, reforce=sub_rf, nx1=nx1)
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
        fixed = agents.revise_sql(llm, sfiltered, q.question, q.evidence, composed,
                                  run_err + compose_guards.unknown_col_hint(run_err, full_schema),
                                  value_hints=vh)
        if not fixed:
            break
        composed = fixed

    # Stage 5: semantic self-check with SELF-CONSISTENCY (Revisor, Eq 9). Unlike the reuse guards
    # (which only touch questions where reuse fired), this runs on EVERY question and targets the
    # dominant failure mode — a query that executes but returns the WRONG rows (wrong aggregation
    # direction, mis-computed derived value, wrong grain). We sample `self_consistency` independently
    # re-derived variants of the composed query, execute each, and keep the query whose RESULT SET has
    # plurality agreement across the samples — the answer the model most consistently arrives at.
    if composed is not None:
        composed = _self_consistent_finalize(
            llm, con, sfiltered, rewrite_text, q.question, q.evidence, composed, self_consistency)

    # LABEL-FREE evidence (no gold): when reuse fired, independently re-answer the question WITHOUT
    # the memory (fresh direct SQL) and compare RESULT SETS. Agreement is evidence the reuse was
    # sound; disagreement flags it as suspect. This replaces the gold-derived signal that L4 /
    # skill-review / dream would otherwise need — which is unavailable in deployment. `None` when the
    # check could not be run (no reuse, no SQL, or the cross-query failed to execute).
    lf_agree = None
    if label_free and composed is not None and reused > 0:
        try:
            alt = agents.direct_sql(llm, full_schema, rewrite_text, q.question, q.evidence)
            if alt:
                a = _result_sig(datasets.run_sql(con, alt))
                b = _result_sig(datasets.run_sql(con, composed))
                if a is not None and b is not None:
                    lf_agree = bool(a == b)
        except Exception:  # noqa: BLE001 — the cross-check is best-effort, never fails a question
            lf_agree = None

    # Weak-model compose guards (#1 arity + #6 compose-vs-direct race); no-op unless enabled.
    if compose_guards.ON:
        def _cg_probe(sql, _con=con):
            try:
                rows = list(datasets.run_sql(_con, sql))
                return (len(rows[0]) if rows else None, rows)
            except Exception:  # noqa: BLE001
                return None
        _wn, _wc, _grain = compose_guards.contract(llm, q.question, q.evidence)
        _best = compose_guards.guarded_finalize(
            _cg_probe, composed,
            lambda: agents.direct_sql(llm, full_schema, rewrite_text, q.question, q.evidence),
            lambda s, instr: agents.revise_sql(llm, sfiltered, q.question, q.evidence, s, instr),
            _wn, _wc, _grain)
        if _best:
            composed = _best

    correct, err_msg = scorer(con, composed, q) if composed else (False, "no sql")
    used_reuse = reused > 0
    # A wrong answer only counts as NEGATIVE reuse when a *causally-capable* view was reused. Trivial
    # single-table projections are semantically identical to querying the base table, so their presence
    # in a wrong answer is innocent-bystander (the error is downstream); counting them inflated the
    # metric ~9x and — as the ablation showed — blocking them RAISED cost with no accuracy gain. Only
    # a non-trivial (JOIN/aggregation/window) reuse can distort results, so only it can be "negative".
    used_nontrivial_reuse = any(not sqlview.is_trivial_projection(s) for s in reused_specs)
    return {
        "qid": q.qid, "db_id": q.db_id, "question": q.question,
        "n_views": len(reqs), "reused": reused, "generated": generated,
        "no_new_cte": (generated == 0),
        "coverage": (reused / len(reqs)) if reqs else 1.0,
        "used_views": used_views, "used_reuse": used_reuse, "reused_names": reused_names,
        "used_nontrivial_reuse": used_nontrivial_reuse,
        "verify_reject": verify_reject,
        "correct": bool(correct),
        "lf_agree": lf_agree,          # label-free evidence: reuse-answer == fresh-answer (None=n/a)
        "negative_reuse": bool(used_nontrivial_reuse and not correct),   # causally-capable reuse only
        "negative_reuse_raw": bool(used_reuse and not correct),          # old defn (any reuse) — kept for audit
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
            "used_nontrivial_reuse": False,
            "correct": False, "negative_reuse": False, "negative_reuse_raw": False,
            "error": f"{type(err).__name__}: {err}", "tokens": 0, "secs": 0.0,
            "pred_sql": None, "diag": []}


def run_config(name, by_db, *, use_memory, use_guard, tau, model, max_views, db_root, dataset,
               seed=False, seed_dir=None, gen_topk=0, retriever="dense", n_verify=0, self_consistency=1,
               no_valuelink=False, reuse_policy="aggressive", skill_cards=False,
               skill_review=False, skill_review_min=1, label_free=False, use_reforce=False,
               grown_dir="", nxm=False, max_subgoals=8, nx1=False):
    from skiewsql import retriever as retriever_mod
    if reuse_policy != "auto":
        sqlview.set_reuse_policy(reuse_policy)          # fixed policy for the whole run
    llm = LLM(model=model, temperature=0.0)
    embedder = Embedder()
    scorer = _make_scorer(dataset)
    retrieve_fn = retriever_mod.get_retriever(retriever)
    rows, final_graph_sizes = [], {}
    for db_id, qs in by_db.items():
        path = datasets.db_path(db_root, db_id, dataset)
        con = datasets.connect(path)
        if reuse_policy == "auto":                      # per-DB: pick atomic on high-ambiguity schemas
            from skiewsql import schema_complexity
            sc = schema_complexity.score(con, embedder=embedder)
            sqlview.set_reuse_policy(sc["suggested_policy"])
            print(f"  [{db_id}] schema complexity={sc['score']} {sc['signals']} "
                  f"-> reuse_policy={sc['suggested_policy']}", flush=True)
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
                if skill_cards:                 # bring seed cards up to date (any view missing one)
                    from skiewsql import skillify
                    nref = skillify.refresh_missing_skills(llm, graph)
                    if nref:
                        print(f"  [{db_id}] refreshed skill cards on {nref} seed view(s)", flush=True)
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
                                    retrieve_fn=retrieve_fn, n_verify=n_verify,
                                    self_consistency=self_consistency, skill_cards=skill_cards,
                                    label_free=label_free, use_reforce=use_reforce,
                                    nxm=nxm, max_subgoals=max_subgoals, nx1=nx1)
            except (_QTimeout, Exception) as e:  # noqa: BLE001 — one bad/slow question must not kill a long run
                # _QTimeout is a BaseException so it is listed explicitly; it reaches here only after
                # the 240s SIGALRM, having unwound past every inner `except Exception`.
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
            # GOLD (default) uses the scorer's correctness — an ORACLE signal unavailable in
            # deployment, so it is an upper bound. LABEL-FREE uses `lf_agree` (does the memory-based
            # answer agree with an independent fresh answer?), which needs no labels.
            if label_free:
                good, bad = (r.get("lf_agree") is True), (r.get("lf_agree") is False)
            else:
                good, bad = r["correct"], r["negative_reuse"]
            for nm in r["reused_names"]:
                v = graph.views.get(nm)
                if v is None:
                    continue
                if good and q.question not in v.validated_on:
                    v.validated_on = (v.validated_on + [q.question])[-10:]
                elif bad and q.question not in v.counter_examples:
                    v.counter_examples = (v.counter_examples + [q.question])[-10:]
            print(f"  [{name}] {db_id}#{i:02d} chunks={len(chunks)} reuse={r['reused']} "
                  f"(seed={r['seed_reuse']}) gen={r['generated']} vrej={r.get('verify_reject', 0)} "
                  f"graph={r['graph_views']} ok={int(r['correct'])} tok={r['tokens']}")
        final_graph_sizes[db_id] = graph.n_views()
        # POST-RUN SKILL REVIEW: now that this DB's questions are answered, revise each skill's card
        # from what actually happened — the questions where reusing it was CORRECT sharpen
        # `when_to_use`, the ones where it was WRONG become `when_not_to_use` with the reason. Applied
        # uniformly to seeded and online-grown views: a skill is a skill, evidence is evidence.
        if skill_review and use_memory:
            from skiewsql import skillify
            nrev = skillify.review_graph_skills(llm, graph, min_evidence=skill_review_min)
            print(f"  [{db_id}] reviewed {nrev} skill card(s) from run outcomes", flush=True)
        # Persist the GROWN graph (online-added views + validated_on / counter_examples learned
        # this run) so the learning survives the process, instead of being discarded in-memory.
        if use_memory and grown_dir:
            os.makedirs(grown_dir, exist_ok=True)
            sqlview.save_graph(graph, os.path.join(grown_dir, f"{db_id}.json"))
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

    # reuse-conditional accuracy: the honest, ungameable reuse signal — does reuse firing correlate
    # with getting the question right? (Unlike negative_reuse it can't be inflated by inert hits.)
    reuse_q = [r for r in rows if r.get("used_reuse")]
    noreuse_q = [r for r in rows if not r.get("used_reuse")]

    return {
        "config": name, "questions": n,
        "exec_accuracy": acc(rows),
        "cold_start_acc": acc(cold), "warm_acc": acc(warm),
        "acc_when_reuse_fired": acc(reuse_q), "acc_when_no_reuse": acc(noreuse_q),
        "n_reuse_fired": len(reuse_q),
        "exact_reuse_rate": round(total_reused / total_views, 4) if total_views else 0.0,
        "seed_reuse_rate": round(total_seed_reuse / total_views, 4) if total_views else 0.0,
        "seed_reuse_count": total_seed_reuse,
        "pct_no_new_cte": round(sum(r["no_new_cte"] for r in rows) / n, 4),
        "total_views_generated": total_gen,
        "avg_new_views_per_q": round(total_gen / n, 3),
        "real_total_tokens": usage_snapshot["total_tokens"],
        "real_tokens_by_stage": usage_snapshot["by_tag"],
        "negative_reuse_count": sum(r["negative_reuse"] for r in rows),          # non-trivial reuse only
        "negative_reuse_raw_count": sum(r.get("negative_reuse_raw", False) for r in rows),  # old (any reuse)
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
    ap.add_argument("--dataset", default="spider", choices=["spider", "bird", "bird_minidev", "spider2lite", "sqlflow_spider", "sqlflow_bird", "spider_fusion", "bird_fusion"])
    ap.add_argument("--dbs", default="top:4", help="'top:N' or comma list of db_ids")
    ap.add_argument("--limit", type=int, default=30, help="max questions per db")
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--tau", type=float, default=0.6)
    ap.add_argument("--max_views", type=int, default=3)
    ap.add_argument("--nxm", type=int, default=0,
                    help="1 = N×M decomposition: decompose once (whole-DB table index), align each of "
                         "M sub-goals against all N chunks (no cap at max_views)")
    ap.add_argument("--nx1", type=int, default=0,
                    help="1 = N×1 (AV-SQL / SkiewSQL v2m): one whole-question view per chunk, no "
                         "sub-goal decomposition. Overrides --nxm when set.")
    ap.add_argument("--max_subgoals", type=int, default=4, help="N×M mode: cap on M sub-goals")
    ap.add_argument("--gen_topk", type=int, default=0,
                    help="views injected into the generate prompt: 0=whole graph (old), "
                         "k>0=top-k most relevant (bounds prompt size vs graph)")
    ap.add_argument("--retriever", default="dense", choices=["dense", "hybrid"],
                    help="dense=embedding cosine; hybrid=RRF(dense, BM25) over contract candidates")
    ap.add_argument("--skill_cards", type=int, default=0,
                    help="1 = give every ONLINE-generated view a full skill card, and refresh any "
                         "seed view missing one, so seeded and grown views are on equal footing")
    ap.add_argument("--reforce", type=int, default=0,
                    help="1 = ReFoRCE format restriction + per-sub-goal column exploration")
    ap.add_argument("--label_free", type=int, default=0,
                    help="1 = derive reuse evidence WITHOUT gold: cross-check the memory-based "
                         "answer against an independent fresh answer and use agreement/disagreement "
                         "as validated_on/counter_example. 0 = gold-derived (ORACLE upper bound)")
    ap.add_argument("--skill_review", type=int, default=0,
                    help="1 = after each DB, REVISE every skill card from run outcomes: correct "
                         "reuses sharpen when_to_use, wrong reuses become when_not_to_use. Applied "
                         "uniformly to seeded and online-grown views")
    ap.add_argument("--skill_review_min", type=int, default=1,
                    help="min outcome records a view needs before its card is reviewed")
    ap.add_argument("--reuse_policy", default="aggressive",
                    choices=["aggressive", "atomic", "balanced", "auto"],
                    help="reuse gating: aggressive (default), atomic (SEL/NORM only), balanced "
                         "(join reuse + base-table check), or auto (per-DB: atomic if schema "
                         "join/grain ambiguity score >= 0.5, else aggressive)")
    ap.add_argument("--self_consistency", type=int, default=1,
                    help="final-query semantic self-check with self-consistency: number of independently "
                         "re-derived variants to execute and majority-vote on (1=single-pass, no voting)")
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
    ap.add_argument("--results_dir", default="", help="override output dir (e.g. /mnt/win_d/...) to keep results off a full home disk")
    ap.add_argument("--tag", default="run")
    args = ap.parse_args()

    if args.dataset == "spider":
        questions, _tables, db_root = datasets.load_spider("dev")
    elif args.dataset == "spider_fusion":
        questions, _tables, db_root = datasets.load_spider_fusion()
    elif args.dataset == "bird_fusion":
        questions, _tables, db_root = datasets.load_bird_fusion()
    elif args.dataset == "bird":
        questions, _tables, db_root = datasets.load_bird("dev")
    elif args.dataset == "bird_minidev":
        questions, _tables, db_root = datasets.load_bird_minidev()
    elif args.dataset.startswith("sqlflow_"):
        questions, _tables, db_root = datasets.load_sqlflow(args.dataset.split("_",1)[1])
    else:  # spider2lite: local-SQLite subset, CSV-scored
        from skiewsql import spider2lite
        questions, db_root = spider2lite.load_local()
    by_db = pick_dbs(questions, args.dbs, args.limit)
    print(f"Dataset={args.dataset} model={args.model} dbs={list(by_db)} "
          f"counts={ {k: len(v) for k, v in by_db.items()} } tau={args.tau}")

    if args.results_dir:
        globals()["RESULTS_DIR"] = args.results_dir
        os.makedirs(RESULTS_DIR, exist_ok=True)
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
        grown_dir = os.path.join(RESULTS_DIR, "grown_graphs", f"{args.tag}_{args.dataset}_{cname}")
        rows, fsizes = run_config(cname, by_db, tau=args.tau, model=args.model,
                                  max_views=args.max_views, db_root=db_root,
                                  dataset=args.dataset, seed_dir=seed_dir,
                                  nxm=bool(args.nxm), max_subgoals=args.max_subgoals, nx1=bool(args.nx1),
                                  gen_topk=args.gen_topk, retriever=args.retriever,
                                  n_verify=args.verify, self_consistency=args.self_consistency,
                                  reuse_policy=args.reuse_policy, skill_cards=bool(args.skill_cards),
                                  label_free=bool(args.label_free), use_reforce=bool(args.reforce),
                                  skill_review=bool(args.skill_review),
                                  skill_review_min=args.skill_review_min,
                                  no_valuelink=args.no_valuelink,
                                  grown_dir=grown_dir, **kw)
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
