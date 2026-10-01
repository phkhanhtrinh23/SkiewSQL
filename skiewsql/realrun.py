"""Run the real SkiewSQL experiment on Spider or BIRD with the complete AV-SQL pipeline. The stages are question rewriting, chunked view proposal, value-linked view generation or graph retrieval, filtered-schema construction, planning, SQL generation, execution repair, and semantic revision.

The protocol is sequential within each database, which is the only setting where CTE reuse can occur. The view graph starts empty and grows after every question. Every configuration shares the same agents.

- A, SkiewSQL: persist the graph across questions and retrieve or generate views.
- B, AV-SQL baseline: reset the graph before every question, always generate views, and discard them afterward.
- C, SkiewSQL without the guard: persist memory but disable the compatibility guard to expose negative reuse.

By default the graph is a skill registry (`--skill_registry 1`, see GRAPH_AND_RETRIEVAL.md §10). Retrieval uses five stages and can abstain. Hard questions search the registry before N×M alignment. New views persist only through admission after the question. Credit goes only to CTEs the executed final SQL used, with optional ablation. Each question is stored as an episode with an evidence ledger. `--skill_registry 0` runs the legacy pipeline.

Examples: `python -m skiewsql.realrun --dataset spider --dbs top:4 --limit 30 --model gpt-4o-mini` and `python -m skiewsql.realrun --dataset bird --dbs financial,superhero --limit 20`."""
from __future__ import annotations

import argparse
import collections
import dataclasses
import glob
import json
import os
import signal
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from skiewsql import agents, datasets, sqlview, valuelink, compose_guards
from skiewsql import contracts, evidence, registry
from skiewsql.core import ViewGraph, ViewRequest, ViewSpec
from skiewsql.llm import LLM, Embedder, USAGE
from skiewsql.paths import GROWN_GRAPHS_DIR, SEED_GRAPHS_DIR, ensure_dir, sqlite_run_dir

RESULTS_DIR = str(sqlite_run_dir("spider"))
VIEW_VALIDATE_ATTEMPTS = 3
SQL_REPAIR_ATTEMPTS = 5          # AV-SQL T_max
CHUNK_BUDGET = 8000
PER_QUESTION_TIMEOUT = int(os.environ.get("SKIEW_PER_Q", "240"))  # per-question wall-clock cap (SIGALRM). Bounds any hang. Raise via SKIEW_PER_Q for slow providers (Together A ~11min/q)


class _QTimeout(BaseException):
    # BaseException, NOT Exception: the SIGALRM almost always fires while we're inside an LLM call, and LLM.chat / the repair / compose blocks all use bare `except Exception` with a retry loop. If _QTimeout were an Exception those blocks would SWALLOW the per-question timeout and retry, so a question could loop for hours (observed: f1/bank_sales hung 3-4h despite the 240s alarm). As a BaseException it unwinds straight past every `except Exception` to the per-question loop, which catches it explicitly. Same rationale as KeyboardInterrupt being a BaseException.
    pass


def _alarm_handler(signum, frame):
    raise _QTimeout(f"question exceeded {PER_QUESTION_TIMEOUT}s wall-clock")


# --------------------------------------------------------------------------- #
# Value-link-aware view generation (Stage 2b) — used on a graph miss
# --------------------------------------------------------------------------- #
def _verify_gate(llm, embedder, spec, req, n_verify):
    """Layer 4 (cheap counter-example reject) + Layer 3 (N skeptical verifiers, majority-allow). Returns the spec if reuse is allowed, else None (-> treat as a miss and generate)."""
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
    """Views to offer the generator as composable building blocks. With whole-graph injection (gen_topk<=0 or >=|graph|) the generate prompt grows with the graph — the token overhead that made config S cost more. Selective injection returns only the top-k views by embedding similarity to the sub-goal, bounding the prompt size regardless of graph size."""
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
    """Give a freshly generated view the SAME rich skill card a seeded view has (when_to_use / output_schema / grounded_columns / metric / composition), so online-grown and seeded views are retrievable and selectable on equal footing. Costs 1 LLM call per accepted new view."""
    if not skill_cards or spec is None:
        return
    from skiewsql import skillify
    skillify.attach_skill_one(llm, spec, list(graph.views.values()))


def _contract_feedback(con, graph, cand):
    """Registry mode: cheap contract assertions on a freshly generated view (grain uniqueness, declared filters). Returns a repair message for the generator, or None when the claims hold. A failing view can still serve this question. It just never becomes a reusable skill."""
    probe = dataclasses.replace(cand, grain_kind="keyed" if cand.grain else "unknown")
    rec = contracts.validate(con, graph, probe, timeout=5.0)
    # Only real data violations trigger a regeneration. Naming gaps (logical grain names, missing declared outputs) only keep the view out of the registry.
    fails = [f for f in rec.get("failures", [])
             if f.startswith("duplicate rows") or "violate declared filter" in f]
    if not fails:
        return None
    return ("The view executes, but its contract is wrong: " + "; ".join(fails[:3]) +
            ". Either make the SQL match the declared grain/filters, or declare the true (finer) grain "
            "in the metadata `grain`.")


def _generate_av_view(llm, embedder, graph, con, chunk_schema, req, vindex):
    """AV-SQL view generation with validation and iterative repair (paper §4.3, Algorithm 1), up to T_max = VIEW_VALIDATE_ATTEMPTS attempts. Each attempt: (1) value retrieval for the CTE's literals, (2) execution on the database, (3) rule-based consistency between the CTE and its JSON schema selection. A view is kept only when it executes AND is consistent (Eq. 9). Every problem, plus the matched database values, is fed back to the next attempt. Returns the view (added to `graph`) or None (irrelevant chunk, or never valid)."""
    feedback = None
    for _ in range(VIEW_VALIDATE_ATTEMPTS):
        cand, selection, raw = agents.av_view_selected(llm, chunk_schema, req.text, req.want_name,
                                                       feedback=feedback)
        if cand is None:
            if raw is not None:                  # JSON only: the chunk was judged irrelevant (or no CTE needed)
                return None
            feedback = {"cte": None, "selection": None,
                        "error": "no ```sql or ```json block was produced: output both blocks"}
            continue
        problems = contracts.selection_consistency(cand.body_sql, selection, con)
        # Keyword value extraction and retrieval (tau_edit = tau_semantic = 0.5, as in the paper).
        values = (vindex.ground(cand.body_sql, tau_edit=0.5, embedder=embedder, tau_semantic=0.5)
                  if vindex else [])
        if graph.has(cand.name):
            cand.name = f"{cand.name}_{len(graph.views)}"
        graph.add_view(cand)
        ok, msg = sqlview.validate_view(con, graph, cand)
        if ok and not problems:
            return cand
        graph.remove_view(cand.name)
        feedback = {"cte": cand.body_sql, "selection": raw, "error": None if ok else msg,
                    "consistency": problems, "values": values}
    return None


def _generate_view(llm, embedder, graph, con, full_schema, req, vindex, gen_topk=0, skill_cards=False,
                   reforce="", nx1=False, allowed_views=None, registry_mode=False):
    """Generate one CTE, repairing on execution error AND on value-linking mismatches. In registry mode also on contract-assertion failures, and the view is marked exploratory (it becomes a skill only through admission after the question)."""
    hints, prior_err, last_ok = None, None, None
    holistic = nx1 or req.holistic

    def _mark(v):
        if registry_mode:
            v.status, v.dialect = "exploratory", "sqlite"
            v.provenance = {"origin": "av_chunk" if holistic else "subgoal",
                            "subgoal": dataclasses.asdict(req)}
        return v

    if registry_mode and holistic:
        cand = _generate_av_view(llm, embedder, graph, con, full_schema, req, vindex)
        return _mark(cand) if cand is not None else None
    for _ in range(VIEW_VALIDATE_ATTEMPTS):
        if nx1 or req.holistic:
            cand = agents.av_view(llm, full_schema, req.text, req.want_name)
        else:
            offered = (list(allowed_views) if allowed_views is not None
                       else _relevant_views(graph, req, embedder, gen_topk))
            cand = agents.generate_view(llm, full_schema, req,
                                    offered,
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
        if registry_mode and not holistic:
            fb = _contract_feedback(con, graph, cand)
            if fb:                               # executes, but grain/filter claims are false
                last_ok = cand
                graph.remove_view(cand.name)
                prior_err, hints = fb, None
                continue
        if not registry_mode:
            _attach_card(llm, graph, cand, skill_cards)
        return _mark(cand)                       # clean success (already in graph)
    if last_ok is not None:                      # best executing version, keep it
        if graph.has(last_ok.name):
            last_ok.name = f"{last_ok.name}_{len(graph.views)}"
        graph.add_view(last_ok)
        if not registry_mode:
            _attach_card(llm, graph, last_ok, skill_cards)
        return _mark(last_ok)
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


def _retrieval_snapshot(graph: ViewGraph) -> ViewGraph:
    """Freeze reusable candidates at question start. A view generated for an earlier request in the same question may be consumed only through an explicit dependency. Treating it as a historical retrieval hit makes N×1 reuse its first chunk view for later chunks and inflates online-reuse metrics."""
    frozen = ViewGraph(db_id=graph.db_id)
    for spec in list(graph.views.values()):
        frozen.add_view(spec)
    return frozen


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
    """Semantic self-check + self-consistency over the FINAL query. Candidate 0 is the composed query as-is. The rest are independent semantic re-derivations. Execute each, group by result-set signature, and return the SQL of the plurality result (ties keep the earliest → the original stays unless a majority of re-derivations agree on a different answer). k<=1 keeps the old single-pass behaviour. Never returns something that fails to execute."""
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
    # vote by executed result set. Keep a representative SQL + first-seen order per signature
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
                    nxm=False, max_subgoals=8, nx1=False, architecture="legacy",
                    focused_budget=CHUNK_BUDGET, registry_cfg=None):
    """Answer one question. ``registry_cfg`` (a RegistryConfig) selects the skill-registry pipeline: five-stage retrieval, graph search before N×M alignment, contract assertions on generated views, and a learning context for `_learn` (credit, ablation, admission, episode). None keeps the legacy pipeline exactly."""
    retrieve_fn = retrieve_fn or sqlview.retrieve
    t0, tok0 = time.time(), USAGE.total
    reg = registry_cfg
    retrieval_graph = _retrieval_snapshot(graph) if use_memory else graph
    prefetched, searched, used_bases, retrieval_log, reuse_info = {}, set(), set(), {}, {}
    ungrounded = []

    blocked = {}                                     # request -> skills that failed table grounding

    def _registry_lookup(req, domain=None):
        """Five-stage registry retrieval for one request. Skills already used in this question are excluded, so one stored view cannot stand in for several chunks or subgoals. `domain` (aligned tables) restricts candidates to skills whose lineage lies inside it."""
        det = sqlview.deterministic_reuse_on()
        if domain:
            req = dataclasses.replace(req, source_tables=sorted(domain))
        spec, d = registry.retrieve(retrieval_graph, graph, req, embedder, scope=reg.scope, con=con,
                                    tau=tau, use_guard=use_guard, llm=None if det else llm,
                                    n_votes=reg.n_votes, deterministic=det,
                                    exclude=used_bases | blocked.get(req.want_name, set()),
                                    min_confidence=reg.min_confidence, risky_votes=reg.risky_votes)
        searched.add(req.want_name)
        retrieval_log[req.want_name] = d
        if spec is not None:
            used_bases.update(d.get("base") or [spec.name])
        return spec, d

    prefetch = on_ungrounded = None
    if reg is not None and use_memory:
        def prefetch(subgoals):
            """Search before alignment. Returns {subgoal: lineage tables of the chosen skill(s)} so the caller can ground each hit before skipping its alignment."""
            hits = {}
            for sg in subgoals:
                spec, d = _registry_lookup(sg)
                if spec is not None:
                    prefetched[sg.want_name] = (spec, d)
                    lineage = []
                    for b in d.get("base") or [spec.name]:
                        lineage += (retrieval_graph.views[b].provenance or {}).get("lineage", [])
                    hits[sg.want_name] = lineage
            return hits

        def on_ungrounded(name):
            """The hit's tables were not confirmed by alignment: release it and search again after alignment, restricted to the aligned tables."""
            _spec, d = prefetched.pop(name)
            bases = set(d.get("base") or [])
            used_bases.difference_update(bases)
            blocked.setdefault(name, set()).update(bases)
            searched.discard(name)
            ungrounded.append(name)

    # Stage 1: question rewriting
    _rw, rewrite_text = agents.rewrite_question(llm, "", q.question, q.evidence)  # schema-free rewrite

    # Stage 2a: view proposal + schema selection (union -> S_filtered)
    per_tables: Dict[str, set] = {}
    align_calls = 0
    architecture_route = ("nx1" if nx1 else "nxm" if nxm else architecture)
    direct_route = False
    if architecture == "auto":
        table_index = ", ".join(sorted({t for _c, tabs in chunks for t in (tabs or [])}))
        reqs, per_tables, adaptive_route, sel_tables, align_calls = agents.adaptive_requests(
            llm, chunks, rewrite_text, table_index,
            render_selected=lambda tabs: _filtered_schema(con, full_schema, tabs),
            estimate_tokens=datasets.est_tokens, focused_budget=focused_budget,
            max_subgoals=max_subgoals, prefetch=prefetch, on_ungrounded=on_ungrounded)
        direct_route = adaptive_route == "direct_sql"
        architecture_route = (adaptive_route if direct_route else
                              f"{adaptive_route}_{'graph' if use_memory else 'nograph'}")
    elif nx1 or architecture == "nx1":
        # N×1 (AV-SQL / SkiewSQL v2m): one whole-question view per schema chunk. NO sub-goal decomposition. Each chunk's view is generated against that chunk's tables.
        reqs, per_tables = agents.nx1_requests(chunks, rewrite_text)
        sel_tables = set().union(*per_tables.values()) if per_tables else set()
    elif nxm or architecture == "nxm":
        # N×M: decompose once (whole-DB table index), then align each of M sub-goals against all N chunks. No cap at max_views.
        table_index = ", ".join(sorted({t for _c, tabs in chunks for t in (tabs or [])}))
        chunk_texts = [c for c, _t in chunks]
        reqs, per_tables, align_calls = agents.decompose_and_align(
            llm, chunk_texts, rewrite_text, table_index, max_subgoals=max_subgoals,
            prefetch=prefetch, on_ungrounded=on_ungrounded)
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
    generated_names = []
    resolved_reqs = {}
    # Per-question memory: why each chosen view is here (shown to the planner/composer, never stored on a skill).
    why: Dict[str, str] = {}
    verify_reject = 0
    for req in reqs:
        spec = None
        if reg is not None:
            # Registry pipeline: a hard-route subgoal was already searched before alignment (prefetch). Everything else is searched here once. Stage 5 inside registry.retrieve is the verifier.
            if use_memory:
                if req.want_name in prefetched:
                    spec, d = prefetched[req.want_name]
                elif req.want_name not in searched:
                    spec, d = _registry_lookup(req, per_tables.get(req.want_name))
                else:
                    d = retrieval_log.get(req.want_name, {})
                if spec is None and d.get("decision") in ("verifier chose NONE", "no verifier majority",
                                                          "conflicting near-tie"):
                    verify_reject += 1
                diag.append({req.want_name: registry.compact_diag(d)})
        elif use_memory:
            if sqlview.deterministic_reuse_on():          # Zero-Mem: guard+embedding, no LLM verify
                spec, d = sqlview.select_reuse(
                    retrieval_graph, req, embedder, tau=tau, use_guard=use_guard)
            else:
                spec, d = retrieve_fn(
                    retrieval_graph, req, embedder, tau=tau, use_guard=use_guard)
            diag.append({req.want_name: d})
        if reg is None and spec is not None and n_verify > 0 and not sqlview.deterministic_reuse_on():
            spec, vreason = _verify_gate(llm, embedder, spec, req, n_verify)
            if spec is None:
                verify_reject += 1
                diag.append({req.want_name: {"verify_reject": vreason}})
        if spec is not None:
            chosen.append(spec)
            reused += 1
            if reg is not None:
                bases = list(d.get("base") or [spec.name])
                reuse_info[req.want_name] = {"view": spec.name, "base": bases,
                                             "mode": d.get("mode", "exact")}
                nm = d.get("name_map") or {}
                why[spec.name] = (
                    f"reused stored skill {', '.join(bases)} ({d.get('mode', 'exact')} match) for sub-goal "
                    f"`{req.want_name}`: {req.text[:160]}. Verifier: {d.get('verifier_reason') or 'accepted'}"
                    + (f". Columns renamed: {', '.join(f'{a}->{b}' for a, b in nm.items())}" if nm else "")
                    + (f". {d['mode_note']}" if d.get("mode_note") else ""))
                reused_names.extend(bases)
                reused_specs.extend(graph.views[b] for b in bases if b in graph.views)
            else:
                reused_names.append(spec.name)
                reused_specs.append(spec)
            resolved_reqs[req.want_name] = spec
            continue
        # N×M: each sub-goal generates against ONLY its aligned tables. Else the full schema.
        req_schema = (_filtered_schema(con, full_schema, per_tables[req.want_name])
                      if per_tables.get(req.want_name) else full_schema)
        sub_rf = reforce_q + (compose_guards.CARRY_CLAUSE if compose_guards.ON else "")
        if use_reforce:
            from skiewsql import reforce_modules
            def _probe(q, _c=con):
                return str(datasets.run_sql(_c, q)[:5])[:500]
            pre_info, _n = reforce_modules.exploration(
                llm, _probe,
                f"{req.text} (required outputs: {req.required_outputs}. Grain: {req.required_grain})",
                req_schema[:6000], api="sqlite")
            if pre_info:
                sub_rf += ("\nColumn exploration — VALUES observed for this sub-goal:\n"
                           + pre_info[:4000] + "\n")
        declared = [resolved_reqs[n] for n in req.depends_on if n in resolved_reqs]
        missing_deps = [n for n in req.depends_on if n not in resolved_reqs]
        if missing_deps and not req.may_read_base_tables:
            diag.append({req.want_name: {"skipped": "missing-dependencies", "missing": missing_deps}})
            continue
        gen_req = req
        if req.depends_on:
            gen_req = dataclasses.replace(req, depends_on=[v.name for v in declared])
        new_spec = _generate_view(llm, embedder, graph, con, req_schema, gen_req, vindex, gen_topk,
                                  skill_cards=skill_cards, reforce=sub_rf, nx1=nx1,
                                  allowed_views=(declared if req.depends_on else None),
                                  registry_mode=reg is not None)
        if new_spec is not None:
            chosen.append(new_spec)
            generated += 1
            generated_names.append(new_spec.name)
            resolved_reqs[req.want_name] = new_spec
            if reg is not None:
                rd = retrieval_log.get(req.want_name, {})
                no_reuse = (rd.get("reason") or rd.get("decision") or "no stored skill fits") if use_memory else "memory off"
                why[new_spec.name] = (f"generated fresh for sub-goal `{req.want_name}`: {req.text[:160]}. "
                                      f"Not reused because: {no_reuse}")
            for t in new_spec.source_tables:
                sel_tables.add(t)

    sfiltered = _filtered_schema(con, full_schema, sel_tables)

    # Stage 3: planner -> SQL generator
    composed, used_views = None, []
    if chosen:
        # Registry mode: each view carries a per-question reason for being here (never stored on the skill).
        reasons = why if reg is not None else None
        plan = agents.planner(llm, sfiltered, rewrite_text, chosen, reasons=reasons)
        final_select = agents.compose_final(llm, sfiltered, rewrite_text, q.question,
                                            q.evidence, chosen, plan, reasons=reasons)
        if final_select:
            try:
                composed = sqlview.compose_sql(graph, [v.name for v in chosen], final_select)
                used_views = [v.name for v in chosen]
            except Exception:  # noqa: BLE001
                composed = None
    if composed is None:
        direct_schema = sfiltered if direct_route else full_schema
        composed = agents.direct_sql(llm, direct_schema, rewrite_text, q.question, q.evidence)
        used_views = []

    # Stage 3: execution-grounded repair loop (+ value linking on the final query). Skip entirely when no SQL was produced at all (hard questions) — nothing to run/repair.
    value_fixed = False
    repairs = []                                     # errors and repairs, recorded in the episode
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
                    repairs.append({"attempt": attempt, "kind": "value_link", "error": "; ".join(vh)[:300]})
                    composed = fixed
                    continue
            break
        vh = vindex.ground(composed, embedder=embedder) if vindex else None
        fixed = agents.revise_sql(llm, sfiltered, q.question, q.evidence, composed,
                                  run_err + compose_guards.unknown_col_hint(run_err, full_schema),
                                  value_hints=vh)
        repairs.append({"attempt": attempt, "kind": "execution", "error": run_err[:300],
                        "fixed": bool(fixed)})
        if not fixed:
            break
        composed = fixed

    # Stage 5: semantic self-check with SELF-CONSISTENCY (Revisor, Eq 9). Unlike the reuse guards (which only touch questions where reuse fired), this runs on EVERY question and targets the dominant failure mode — a query that executes but returns the WRONG rows (wrong aggregation direction, mis-computed derived value, wrong grain). We sample `self_consistency` independently re-derived variants of the composed query, execute each, and keep the query whose RESULT SET has plurality agreement across the samples — the answer the model most consistently arrives at.
    if composed is not None:
        before_sc = composed
        composed = _self_consistent_finalize(
            llm, con, sfiltered, rewrite_text, q.question, q.evidence, composed, self_consistency)
        if composed != before_sc:
            repairs.append({"kind": "self_consistency", "changed": True})

    # LABEL-FREE evidence (no gold): when reuse fired, independently re-answer the question WITHOUT the memory (fresh direct SQL) and compare RESULT SETS. Agreement is evidence the reuse was sound. Disagreement flags it as suspect. This replaces the gold-derived signal that L4 / skill-review / dream would otherwise need — which is unavailable in deployment. `None` when the check could not be run (no reuse, no SQL, or the cross-query failed to execute).
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

    # Weak-model compose guards (#1 arity + #6 compose-vs-direct race). No-op unless enabled.
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
            if _best != composed:
                repairs.append({"kind": "compose_guard", "changed": True})
            composed = _best

    correct, err_msg = scorer(con, composed, q) if composed else (False, "no sql")
    used_reuse = reused > 0
    # A wrong answer only counts as NEGATIVE reuse when a *causally-capable* view was reused. Trivial single-table projections are semantically identical to querying the base table, so their presence in a wrong answer is innocent-bystander (the error is downstream). Counting them inflated the metric ~9x and — as the ablation showed — blocking them RAISED cost with no accuracy gain. Only a non-trivial (JOIN/aggregation/window) reuse can distort results, so only it can be "negative".
    used_nontrivial_reuse = any(not sqlview.is_trivial_projection(s) for s in reused_specs)
    extra = {}
    if reg is not None:
        extra = {
            "prefetch_hits": len(prefetched),
            "prefetch_ungrounded": len(ungrounded),
            "reuse_modes": {k: v["mode"] for k, v in reuse_info.items()},
            "n_repairs": sum(1 for x in repairs if x.get("kind") in ("execution", "value_link")),
            # Learning context for `_learn` (objects, popped before the row is saved).
            "_learn": {"reqs": list(reqs), "per_tables": per_tables, "rewrite": rewrite_text,
                       "route": architecture_route, "reuse_info": reuse_info,
                       "generated": generated_names, "retrieval": retrieval_log, "repairs": repairs,
                       "chosen": [v.name for v in chosen]},
        }
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
        "architecture_route": architecture_route,
        "n_schema_chunks": len(chunks),
        "alignment_calls": align_calls,
        "selected_schema_tokens": datasets.est_tokens(sfiltered),
        **extra,
    }


# --------------------------------------------------------------------------- #
# Skill registry: learning from one answered question
# --------------------------------------------------------------------------- #
@dataclasses.dataclass
class RegistryConfig:
    scope: "contracts.Scope"
    n_votes: int = 1                  # Stage-5 selector votes (majority)
    min_confidence: float = 0.6       # a verifier vote counts only at this confidence or above
    risky_votes: int = 3              # minimum votes for JOIN / AGG / WIN / SET / REC candidates
    ablation: bool = True             # regenerate each executed reused subgoal to test causality
    gen_tests: bool = True            # LLM-generated test queries during admission
    promote_final: bool = True        # try to extract a reusable relation from the final SQL
    skill_cards: bool = False         # attach a full skillify card to admitted skills


def _ablate(llm, graph, con, full_schema, q, final_sql, final_rows, base, req, per_tables,
            correct, label_free, scorer):
    """Answer again with the reused skill's CTE body replaced by a freshly generated view for the same subgoal (same CTE name and interface), keeping the rest of the final SQL identical. Returns causal_win | causal_loss | neutral | divergent (label-free) | inconclusive."""
    spec = graph.views[base]
    tables = per_tables.get(req.want_name) or (spec.provenance or {}).get("lineage") or spec.source_tables
    schema = _filtered_schema(con, full_schema, tables)
    try:
        if req.holistic:
            cand = agents.av_view(llm, schema, req.text, spec.name, tag="ablation_av_view")
        else:
            deps = graph.topo_closure(spec.depends_on) if spec.depends_on else []
            areq = dataclasses.replace(req, want_name=spec.name, required_outputs=list(spec.output_columns),
                                       depends_on=list(spec.depends_on))
            cand = agents.generate_view(llm, schema, areq, deps, tag="ablation_generate")
    except Exception:  # noqa: BLE001
        return "inconclusive"
    if cand is None:
        return "inconclusive"
    alt = evidence.replace_cte_body(final_sql, spec.name, spec.body_sql, cand.body_sql)
    if not alt:
        return "inconclusive"
    try:
        alt_rows = datasets.run_sql(con, alt)
    except datasets.ExecError:
        return "inconclusive"
    if label_free:
        same = evidence.result_signature(alt_rows) == evidence.result_signature(final_rows)
        return "neutral" if same else "divergent"
    alt_ok, _e = scorer(con, alt, q)
    if correct and not alt_ok:
        return "causal_win"
    if (not correct) and alt_ok:
        return "causal_loss"
    return "neutral"


def _admit_created(llm, graph, con, full_schema, q, ctx, reg, credit):
    """Promotion: views created in this question become skills only if the executed final SQL used them as generated, their contract is complete and validated, and they are not duplicates. AV chunk views get a question-independent description, known limitations, a category from their SQL, and a real name. Derived reuse-mode views are kept only when an admitted view builds on them. Returns {view: 'outcome:detail'} and a rename map."""
    derived = {i["view"] for i in ctx["reuse_info"].values() if i["mode"] != "exact"}
    created = [n for n in ctx["generated"] + sorted(derived) if n in graph.views]
    executed = {n for n, lv in credit.items() if lv["executed"]}
    cands = [n for n in created if n in executed and n not in derived]
    needed, stack = set(), list(cands)
    while stack:
        for d in graph.views[stack.pop()].depends_on:
            if d in derived and d not in needed:
                needed.add(d)
                stack.append(d)
    outcomes, renames = {}, {}
    subgoal_of = {}
    for req in ctx["reqs"]:
        view = ctx["reuse_info"].get(req.want_name, {}).get("view")
        subgoal_of[view or req.want_name] = req.text
    for n in created:
        if n not in cands and n not in needed:
            outcomes[n] = "discarded:" + ("unreferenced or modified by repair" if n not in executed
                                         else "derived view not needed")
    order = [s.name for s in graph.topo_closure(cands + sorted(needed))] if cands else []
    admitted = set()
    for name in order:
        if name not in created or name not in graph.views:
            continue
        spec = graph.views[name]
        pending = [d for d in spec.depends_on if d in created and d not in admitted]
        if pending:
            outcomes[name] = f"rejected:dependency not admitted {pending}"
            continue
        origin = (spec.provenance or {}).get("origin", "subgoal")
        if origin == "av_chunk":
            old = dataclasses.replace(spec)
            spec.category = contracts.infer_category(contracts.analyze_sql(spec.body_sql, list(graph.views)))
            graph.reindex(name, old)
        lin_schema = _filtered_schema(con, full_schema, contracts.lineage(graph, spec))
        tests_fn = ((lambda s, _t=subgoal_of.get(name, ""), _sch=lin_schema:
                     agents.generate_view_tests(llm, s, _t, _sch)) if reg.gen_tests else None)
        proposed = {}

        def _describe(s, _sch=lin_schema):
            d = agents.describe_skill(llm, s, _sch)
            if d.get("description"):
                s.description = d["description"]
                s.params["description"] = d["description"]
            for k in ("when_to_use", "when_not_to_use"):
                if d.get(k):
                    s.params[k] = d[k]
            proposed["name"] = d.get("name", "")
        outcome, detail = registry.admit(
            graph, spec, con, reg.scope, tests_fn=tests_fn,
            describe_fn=_describe if origin == "av_chunk" else None,
            created={"question_id": q.qid, "question": q.question, "rewrite": ctx["rewrite"],
                     "route": ctx["route"], "model": reg.scope.model,
                     "prompt_version": reg.scope.prompt_version, "created_at": contracts.now_iso(),
                     "schema_fingerprint": contracts.schema_fingerprint(reg.scope)})
        if outcome in ("duplicate", "equivalent"):
            registry.merge_into(graph, name, detail, alias_note=f"{q.qid}:{name}")
            renames[name] = detail
            admitted.add(name)                   # dependents were rewritten onto the existing skill
        elif outcome == "admitted":
            admitted.add(name)
            if proposed.get("name") and registry._LEGACY_AV.match(name):
                new = registry._unique_name(graph, proposed["name"])
                graph.rename_view(name, new)
                renames[name] = new
                detail = new
            if reg.skill_cards:
                from skiewsql import skillify
                skillify.attach_skill_one(llm, graph.views[detail], list(graph.views.values()))
        outcomes[name] = f"{outcome}:{detail}"
    return outcomes, renames


def _promote_final(llm, graph, con, full_schema, q, ctx, reg, final_sql, executed_names, renames):
    """§8: the final SQL is an episode, not a skill. Only a reusable intermediate relation extracted from it (constants lifted, no ORDER BY/LIMIT, not trivial, complete contract, not a duplicate) is admitted."""
    views = [graph.views[renames.get(n, n)] for n in executed_names
             if renames.get(n, n) in graph.views and graph.views[renames.get(n, n)].status == "active"]
    ex = agents.extract_reusable(llm, final_sql, ctx["rewrite"], q.question, views)
    if ex is None:
        return None, "not reusable"
    body = ex["body_sql"]
    for old, new in renames.items():
        body = contracts.rename_table_refs(body, old, new)
    consts = contracts.question_constants(body, q.question, extra_texts=[q.evidence, ctx["rewrite"]])
    if consts:
        return None, f"rejected:question-specific constants kept {consts[:3]}"
    facts = contracts.analyze_sql(body, list(graph.views))
    if not facts.parsed:
        return None, "rejected:unparseable"
    inactive = [v for v in facts.view_refs if graph.views[v].status != "active"]
    if inactive:
        return None, f"rejected:reads views that are not skills {inactive}"
    spec = ViewSpec(name=registry._unique_name(graph, ex["name"]), category=ex["category"], body_sql=body,
                    source_tables=facts.base_tables, output_columns=[], grain=[],
                    depends_on=list(facts.view_refs), description=ex["description"] or ctx["rewrite"][:200],
                    status="exploratory",
                    provenance={"origin": "final_extract", "removed_constants": ex["removed_constants"]})
    if sqlview.is_trivial_projection(spec):
        return None, "rejected:trivial projection"
    graph.add_view(spec)
    tests_fn = ((lambda s: agents.generate_view_tests(
        llm, s, ex["description"], _filtered_schema(con, full_schema, contracts.lineage(graph, s))))
        if reg.gen_tests else None)
    outcome, detail = registry.admit(
        graph, spec, con, reg.scope, tests_fn=tests_fn,
        created={"question_id": q.qid, "question": q.question, "rewrite": ctx["rewrite"],
                 "route": ctx["route"], "model": reg.scope.model,
                 "prompt_version": reg.scope.prompt_version, "created_at": contracts.now_iso(),
                 "schema_fingerprint": contracts.schema_fingerprint(reg.scope)})
    if outcome != "admitted":
        graph.remove_view(spec.name)
        return None, f"{outcome}:{detail}"
    if reg.skill_cards:
        from skiewsql import skillify
        skillify.attach_skill_one(llm, spec, list(graph.views.values()))
    return spec.name, "admitted"


def _learn(llm, graph, con, full_schema, q, r, ctx, reg, *, label_free, scorer, ledger, episodes):
    """After a question is answered and scored: credit only the skills the executed final SQL used, ablate reused ones, update evidence, promote new views, maybe extract a skill from the final SQL, retire net-negative skills, and store the episode. Returns fields merged into the result row."""
    tok0 = USAGE.total
    final_sql = r.get("pred_sql")
    rows, executed, errors = None, False, []
    if final_sql:
        try:
            rows = datasets.run_sql(con, final_sql)
            executed = True
        except datasets.ExecError as e:
            errors.append(str(e)[:300])
    label = r.get("lf_agree") if label_free else bool(r.get("correct"))
    reqs = {req.want_name: req for req in ctx["reqs"]}
    reuse_info = ctx["reuse_info"]
    retrieved = sorted({n for d in ctx["retrieval"].values() for key in d.get("shortlist", [])
                        for n in key.split("+")})
    selected = sorted({b for i in reuse_info.values() for b in i["base"]} |
                      {i["view"] for i in reuse_info.values()} | set(ctx["generated"]))
    credit = evidence.assign_credit(graph, final_sql, executed, selected, retrieved)
    created = set(ctx["generated"]) | {i["view"] for i in reuse_info.values() if i["mode"] != "exact"}

    # Ablation: only for reused skills the executed final SQL really ran as stored.
    ablation = {}
    if reg.ablation and executed:
        for rname, info in reuse_info.items():
            for b in info["base"]:
                if b in ablation or not credit.get(b, {}).get("executed"):
                    continue
                ablation[b] = _ablate(llm, graph, con, full_schema, q, final_sql, rows, b, reqs[rname],
                                      ctx["per_tables"], bool(r.get("correct")), label_free, scorer)

    # Skill-level evidence for pre-existing skills (never for views created in this question).
    served = {b: reqs[rn].text for rn, i in reuse_info.items() for b in i["base"]}
    outcomes = {}
    for name, lv in credit.items():
        spec = graph.views.get(name)
        if spec is None or name in created:
            continue
        outcome = (evidence.skill_outcome(label, ablation.get(name), sqlview.is_trivial_projection(spec))
                   if lv["executed"] else "none")
        outcomes[name] = outcome
        evidence.update_skill(spec, lv, outcome, served.get(name, ""), q.question, ablation.get(name), q.qid)
        ledger.add({"ts": contracts.now_iso(), "qid": q.qid, "db_id": q.db_id, "question": q.question,
                    "skill_id": spec.skill_id, "name": name, "subgoal": served.get(name, ""),
                    **lv, "ablation": ablation.get(name), "question_label": label,
                    "label_source": "label_free" if label_free else "gold", "skill_outcome": outcome})
    for rn, d in ctx["retrieval"].items():
        ledger.add({"ts": contracts.now_iso(), "qid": q.qid, "db_id": q.db_id, "event": "retrieval",
                    "request": rn, **registry.compact_diag(d, examples=20)})

    # Promotion of views created in this question, then an optional skill from the final SQL.
    admitted, renames = _admit_created(llm, graph, con, full_schema, q, ctx, reg, credit)
    if reg.promote_final and executed and final_sql:
        exec_names = [n for n, lv in credit.items() if lv["executed"]]
        name, why = _promote_final(llm, graph, con, full_schema, q, ctx, reg, final_sql, exec_names, renames)
        admitted["<final_sql>"] = f"admitted:{name}" if name else why

    retired = [n for n, o in outcomes.items()
               if o == "negative" and registry.retire_if_harmful(graph, graph.views[n])]

    new_skills = [o.split(":", 1)[1] for o in admitted.values() if o.startswith("admitted:")]
    used = [n for n, lv in credit.items() if lv["executed"] and n not in created]
    subgoal_links = {}
    for rn, req in reqs.items():
        made = [renames.get(v, v) for v in ctx["generated"] if graph.views.get(renames.get(v, v)) is not None
                and (graph.views[renames.get(v, v)].provenance or {}).get("subgoal", {}).get("want_name") == rn]
        subgoal_links[rn] = [m for m in made if m in new_skills]
    ep = evidence.Episode(
        episode_id=f"{q.db_id}:{q.qid}", qid=q.qid, db_id=q.db_id, question=q.question,
        rewrite=ctx["rewrite"], route=ctx["route"],
        subgoals=[dataclasses.asdict(req) for req in ctx["reqs"]],
        retrieved={k: d.get("shortlist", []) for k, d in ctx["retrieval"].items()},
        reused=reuse_info, generated=list(ctx["generated"]), final_sql=final_sql, executed=executed,
        result_signature=evidence.result_signature(rows) if rows is not None else None,
        row_count=len(rows) if rows is not None else None, correct=bool(r.get("correct")),
        label_source="label_free" if label_free else "gold", label=label,
        errors=errors + [x.get("error", "") for x in ctx["repairs"] if x.get("error")],
        repairs=ctx["repairs"], credit=credit, ablation=ablation, admitted=admitted)
    episodes.add(dataclasses.asdict(ep))
    graph.add_episode(ep.episode_id,
                      {"USED_SKILL": used, "GENERATED_SKILL": new_skills,
                       "VALIDATED": [n for n, o in outcomes.items() if o == "positive"]},
                      subgoals=subgoal_links)
    nontrivial_exec = [n for n in used if n in graph.views and
                       not sqlview.is_trivial_projection(graph.views[n])]
    return {
        "reuse_executed": [n for n in used if n in {b for i in reuse_info.values() for b in i["base"]}],
        "skill_outcomes": outcomes, "ablation": ablation, "admitted": admitted, "retired": retired,
        "negative_reuse_referenced": bool(nontrivial_exec and label is False),
        "causal_negative_reuse": any(v == "causal_loss" for v in ablation.values()),
        "causal_positive_reuse": any(v == "causal_win" for v in ablation.values()),
        "tokens_learning": USAGE.total - tok0,
    }


def _drop_uncommitted(graph, before):
    """Remove every view added during a question that did not become an active skill."""
    for n in [n for n in graph.views if n not in before and graph.views[n].status != "active"]:
        graph.remove_view(n)


# --------------------------------------------------------------------------- #
# One configuration over (db_id -> ordered questions)
# --------------------------------------------------------------------------- #
_SCHEMA_MEMO, _CHUNK_MEMO, _VINDEX = {}, {}, {}


def _prep_db(con, db_id, path, no_valuelink=False, chunk_budget=CHUNK_BUDGET):
    chunk_key = (db_id, int(chunk_budget))
    if db_id not in _SCHEMA_MEMO:
        _SCHEMA_MEMO[db_id] = datasets.render_schema(con)
    if chunk_key not in _CHUNK_MEMO:
        _CHUNK_MEMO[chunk_key] = datasets.chunk_schema(con, budget_tokens=chunk_budget)
    if no_valuelink:                                   # skip the CPU-heavy LSH build + sqlglot linking
        return _SCHEMA_MEMO[db_id], _CHUNK_MEMO[chunk_key], None
    if path not in _VINDEX:
        try:
            _VINDEX[path] = valuelink.get_index(con, path)
        except Exception as e:  # noqa: BLE001
            print(f"  (value index unavailable for {db_id}: {e})")
            _VINDEX[path] = None
    return _SCHEMA_MEMO[db_id], _CHUNK_MEMO[chunk_key], _VINDEX[path]


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
            "pred_sql": None, "diag": [], "architecture_route": "failed"}


def run_config(name, by_db, *, use_memory, use_guard, tau, model, max_views, db_root, dataset,
               seed=False, seed_dir=None, gen_topk=0, retriever="dense", n_verify=0, self_consistency=1,
               no_valuelink=False, reuse_policy="aggressive", skill_cards=False,
               skill_review=False, skill_review_min=1, label_free=False, use_reforce=False,
               grown_dir="", nxm=False, max_subgoals=8, nx1=False, architecture="legacy",
               focused_budget=CHUNK_BUDGET, chunk_budget=CHUNK_BUDGET,
               skill_registry=True, ablation=True, gen_tests=True, promote_final=True, port_from="",
):
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
        full_schema, chunks, vindex = _prep_db(
            con, db_id, path, no_valuelink=no_valuelink, chunk_budget=chunk_budget)
        # Cold-start seed: load the frozen prebuilt graph for this DB (config S). The seed set is captured now, before any online growth, so reuse hits can be split seed-vs-online.
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
                print(f"  (no seed graph for {db_id} at {sp}. Starting empty)")
        reg = None
        ledger, episodes = evidence.EvidenceLedger(), evidence.EpisodeStore()
        if skill_registry:
            scope = contracts.make_scope(con, db_id, model=model, prompt_version=agents.PROMPT_VERSION)
            reg = RegistryConfig(scope=scope, n_votes=max(1, n_verify), ablation=ablation,
                                 gen_tests=gen_tests, promote_final=promote_final, skill_cards=skill_cards)
            if use_memory and graph.n_views():
                # Schema versioning: loaded skills are re-derived and re-validated against this DB. Legacy or changed ones that fail become stale (kept, never reused).
                st = registry.refresh(graph, con, scope)
                print(f"  [{db_id}] registry refresh: {st}", flush=True)
            if use_memory and port_from:
                for src_path in sorted(glob.glob(os.path.join(port_from, "*.json"))):
                    if os.path.basename(src_path) in (f"{db_id}.json",) or src_path.endswith(".dream.json"):
                        continue
                    try:
                        res = registry.port(sqlview.load_graph(src_path), graph, con, scope)
                    except Exception as e:  # noqa: BLE001 — an unreadable source graph must not stop the run
                        print(f"  [{db_id}] port from {src_path} failed: {e}")
                        continue
                    n_ok = sum(1 for o in res.values() if o == "admitted")
                    if n_ok:
                        print(f"  [{db_id}] ported {n_ok} skill(s) from {os.path.basename(src_path)}")
            if seed:
                seed_names = {n for n, v in graph.views.items() if v.status == "active"}
        for i, q in enumerate(qs):
            if not use_memory:
                graph = ViewGraph(db_id=db_id)
            before = set(graph.views)
            signal.signal(signal.SIGALRM, _alarm_handler)
            signal.alarm(PER_QUESTION_TIMEOUT)
            try:
                r = answer_question(llm, embedder, graph, con, full_schema, chunks, vindex, q,
                                    use_memory=use_memory, use_guard=use_guard, tau=tau,
                                    max_views=max_views, scorer=scorer, gen_topk=gen_topk,
                                    retrieve_fn=retrieve_fn, n_verify=n_verify,
                                    self_consistency=self_consistency, skill_cards=skill_cards,
                                    label_free=label_free, use_reforce=use_reforce,
                                    nxm=nxm, max_subgoals=max_subgoals, nx1=nx1,
                                    architecture=architecture, focused_budget=focused_budget,
                                    registry_cfg=reg)
            except (_QTimeout, Exception) as e:  # noqa: BLE001 — one bad/slow question must not kill a long run
                # _QTimeout is a BaseException so it is listed explicitly. It reaches here only after the 240s SIGALRM, having unwound past every inner `except Exception`.
                r = _failed_row(q, e)
                print(f"  [{name}] {db_id}#{i:02d} ERROR (counted wrong, continuing): "
                      f"{type(e).__name__}: {str(e)[:80]}")
            finally:
                signal.alarm(0)
            ctx = r.pop("_learn", None)
            if reg is not None and use_memory:
                # Learning gets its own time window so a slow ablation / admission never turns an answered question into a failure.
                if ctx is not None:
                    signal.alarm(PER_QUESTION_TIMEOUT)
                    try:
                        r.update(_learn(llm, graph, con, full_schema, q, r, ctx, reg, label_free=label_free,
                                        scorer=scorer, ledger=ledger, episodes=episodes))
                    except (_QTimeout, Exception) as e:  # noqa: BLE001
                        r["learn_error"] = f"{type(e).__name__}: {str(e)[:200]}"
                        print(f"  [{name}] {db_id}#{i:02d} learning step failed: {r['learn_error'][:80]}")
                    finally:
                        signal.alarm(0)
                _drop_uncommitted(graph, before)
                if grown_dir:
                    ledger.flush(os.path.join(grown_dir, f"{db_id}.ledger.jsonl"))
                    episodes.flush(os.path.join(grown_dir, f"{db_id}.episodes.jsonl"))
            r["db_index"] = i
            r["graph_views"] = graph.n_views()
            r["seed_views"] = len(seed_names)
            r["online_views"] = max(0, graph.n_views() - len(seed_names))
            r["seed_reuse"] = sum(1 for n in r["reused_names"] if n in seed_names)
            rows.append(r)
            # Layer 4 (legacy only; the registry credits skills inside `_learn`): learn each reused view's boundary from this question's outcome. GOLD (default) uses the scorer's correctness — an ORACLE signal unavailable in deployment, so it is an upper bound. LABEL-FREE uses `lf_agree` (does the memory-based answer agree with an independent fresh answer?), which needs no labels.
            if reg is None:
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
            extra = ""
            if reg is not None:
                extra = (f" pre={r.get('prefetch_hits', 0)} align={r.get('alignment_calls', 0)} "
                         f"exec_reuse={len(r.get('reuse_executed', []))} "
                         f"admit={sum(1 for o in (r.get('admitted') or {}).values() if o.startswith('admitted'))}")
            print(f"  [{name}] {db_id}#{i:02d} chunks={len(chunks)} reuse={r['reused']} "
                  f"(seed={r['seed_reuse']}) gen={r['generated']} vrej={r.get('verify_reject', 0)} "
                  f"route={r.get('architecture_route', 'legacy')} graph={r['graph_views']} "
                  f"ok={int(r['correct'])} tok={r['tokens']}{extra}")
        final_graph_sizes[db_id] = graph.n_views()
        # POST-RUN SKILL REVIEW: now that this DB's questions are answered, revise each skill's card from what actually happened — the questions where reusing it was CORRECT sharpen `when_to_use`, the ones where it was WRONG become `when_not_to_use` with the reason. Applied uniformly to seeded and online-grown views: a skill is a skill, evidence is evidence.
        if skill_review and use_memory:
            from skiewsql import skillify
            nrev = skillify.review_graph_skills(llm, graph, min_evidence=skill_review_min)
            print(f"  [{db_id}] reviewed {nrev} skill card(s) from run outcomes", flush=True)
        # Persist the GROWN graph (online-added views + validated_on / counter_examples learned this run) so the learning survives the process, instead of being discarded in-memory.
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

    # reuse-conditional accuracy: the honest, ungameable reuse signal — does reuse firing correlate with getting the question right? (Unlike negative_reuse it can't be inflated by inert hits.)
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
        # Skill-registry metrics (absent keys count as 0 for legacy rows).
        "alignment_calls_total": sum(r.get("alignment_calls", 0) or 0 for r in rows),
        "prefetch_hits": sum(r.get("prefetch_hits", 0) for r in rows),
        "reuse_executed_count": sum(len(r.get("reuse_executed", [])) for r in rows),
        "negative_reuse_referenced_count": sum(bool(r.get("negative_reuse_referenced")) for r in rows),
        "causal_negative_reuse_count": sum(bool(r.get("causal_negative_reuse")) for r in rows),
        "causal_positive_reuse_count": sum(bool(r.get("causal_positive_reuse")) for r in rows),
        "skills_admitted": sum(sum(1 for o in (r.get("admitted") or {}).values() if o.startswith("admitted"))
                               for r in rows),
        "skills_retired": sum(len(r.get("retired", [])) for r in rows),
        "reuse_modes": dict(collections.Counter(m for r in rows for m in (r.get("reuse_modes") or {}).values())),
        "tokens_learning": sum(r.get("tokens_learning", 0) for r in rows),
        "architecture_routes": dict(collections.Counter(
            r.get("architecture_route", "legacy") for r in rows)),
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
    ap.add_argument("--architecture", default="legacy",
                    choices=["legacy", "auto", "nx1", "nxm"],
                    help="query architecture: auto routes easy->direct SQL, moderate->graph-enabled "
                         "AV-SQL N×1, hard->dependency N×M. Nx1/nxm force ablations")
    ap.add_argument("--chunk_budget", type=int, default=CHUNK_BUDGET,
                    help="maximum estimated tokens per original schema chunk")
    ap.add_argument("--focused_budget", type=int, default=CHUNK_BUDGET,
                    help="deprecated compatibility knob retained for historical commands")
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
                    help="dense=embedding cosine. Hybrid=RRF(dense, BM25) over contract candidates")
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
                         "reject. 0=off. Guards against negative reuse (Layer 3/4).")
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
    ap.add_argument("--grown_root", default="",
                    help="override the directory containing per-run grown-graph folders")
    ap.add_argument("--skill_registry", type=int, default=1,
                    help="1 (default) = skill-registry pipeline: five-stage retrieval with abstention, "
                         "graph search before N×M alignment, promotion-only persistence, AST credit "
                         "assignment, episodes and evidence ledger. 0 = the legacy pipeline, unchanged "
                         "(reproduces earlier runs). In registry mode --verify N sets the Stage-5 "
                         "selector votes (min 1) and --retriever is unused")
    ap.add_argument("--ablation", type=int, default=1,
                    help="registry: regenerate each executed reused subgoal to test whether reuse "
                         "caused the outcome (1 extra view generation per executed reuse)")
    ap.add_argument("--gen_tests", type=int, default=1,
                    help="registry: LLM-generated test queries when admitting a new skill")
    ap.add_argument("--promote_final", type=int, default=1,
                    help="registry: try to extract a reusable relation from each final SQL "
                         "(1 LLM call per executed question)")
    ap.add_argument("--port_from", default="",
                    help="registry: directory of other databases' graph JSONs. Skills whose tables "
                         "exist here with identical interfaces are ported (re-validated) before the run")
    ap.add_argument("--tag", default="run")
    args = ap.parse_args()

    # Backward-compatible flags override the newer architecture selector.
    if args.nx1:
        args.architecture = "nx1"
    elif args.nxm:
        args.architecture = "nxm"

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

    globals()["RESULTS_DIR"] = ensure_dir(args.results_dir or sqlite_run_dir(args.dataset))
    grown_root = ensure_dir(args.grown_root or GROWN_GRAPHS_DIR)
    globals()["SQL_REPAIR_ATTEMPTS"] = args.repair
    globals()["VIEW_VALIDATE_ATTEMPTS"] = args.view_attempts
    cfg_defs = {
        "A": ("A_SkiewSQL", dict(use_memory=True, use_guard=True)),
        "B": ("B_Baseline_AVSQL", dict(use_memory=False, use_guard=True)),
        "C": ("C_SkiewSQL_noguard", dict(use_memory=True, use_guard=False)),
        "S": ("S_ColdStart_Seed", dict(use_memory=True, use_guard=True, seed=True)),
    }
    seed_dir = args.seed_dir or os.path.join(str(SEED_GRAPHS_DIR),
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
        grown_dir = os.path.join(grown_root, f"{args.tag}_{args.dataset}_{cname}")
        rows, fsizes = run_config(cname, by_db, tau=args.tau, model=args.model,
                                  max_views=args.max_views, db_root=db_root,
                                  dataset=args.dataset, seed_dir=seed_dir,
                                  nxm=bool(args.nxm), max_subgoals=args.max_subgoals, nx1=bool(args.nx1),
                                  architecture=args.architecture, focused_budget=args.focused_budget,
                                  chunk_budget=args.chunk_budget,
                                  gen_topk=args.gen_topk, retriever=args.retriever,
                                  n_verify=args.verify, self_consistency=args.self_consistency,
                                  reuse_policy=args.reuse_policy, skill_cards=bool(args.skill_cards),
                                  label_free=bool(args.label_free), use_reforce=bool(args.reforce),
                                  skill_review=bool(args.skill_review),
                                  skill_review_min=args.skill_review_min,
                                  no_valuelink=args.no_valuelink,
                                  grown_dir=grown_dir,
                                  skill_registry=bool(args.skill_registry), ablation=bool(args.ablation),
                                  gen_tests=bool(args.gen_tests), promote_final=bool(args.promote_final),
                                  port_from=args.port_from, **kw)
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
