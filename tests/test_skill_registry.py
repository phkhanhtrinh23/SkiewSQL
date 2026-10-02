"""Tests for the skill registry: contracts, five-stage retrieval, reuse modes, admission, credit assignment, ablation, episodes, schema refresh, portability, and the realrun registry pipeline."""
import json
import re
import sqlite3

import pytest

from skiewsql import agents, contracts, datasets, evidence, realrun, registry, sqlview
from skiewsql.core import ViewGraph, ViewRequest, ViewSpec


# --------------------------------------------------------------------------- #
# Fixtures and fakes
# --------------------------------------------------------------------------- #
def make_db():
    con = sqlite3.connect(":memory:")
    con.executescript("""
        CREATE TABLE events_table(event_id INTEGER PRIMARY KEY, entity_id INTEGER, amount INTEGER,
                                  status TEXT, odate TEXT);
        CREATE TABLE entities_table(entity_id INTEGER PRIMARY KEY, name TEXT, region TEXT);
        INSERT INTO events_table VALUES (1, 1, 5, 'done', '2020-01-05'), (2, 1, 3, 'done', '2021-03-01'),
                                        (3, 2, 7, 'done', '2020-06-01'), (4, 2, 4, 'open', '2020-02-01');
        INSERT INTO entities_table VALUES (1, 'a', 'N'), (2, 'b', 'S');
    """)
    return con


class HitEmbedder:
    def sim(self, *_args):
        return 1.0


class TableEmbedder:
    """sim from a fixed table of (a, b) pairs (1.0 for identical text, else 0 unless listed)."""

    def __init__(self, table, default=0.0):
        self.table = {frozenset(k): v for k, v in table.items()}
        self.default = default

    def sim(self, a, b):
        if a == b:
            return 1.0
        return self.table.get(frozenset((a, b)), self.default)


class Fake:
    """Tag-dispatching fake LLM. `handlers[tag]` is a string or a callable(user) -> string."""

    def __init__(self, handlers):
        self.handlers = handlers
        self.calls = []

    def ask(self, _system, user, tag="", **_kwargs):
        self.calls.append(tag)
        if tag not in self.handlers:
            raise AssertionError(f"unexpected tag {tag}")
        h = self.handlers[tag]
        return h(user) if callable(h) else h


def choose_first(user):
    m = re.search(r"- name: (\S+) \(category", user)
    return json.dumps({"choice": m.group(1) if m else "NONE", "reason": "ok", "confidence": 0.9})


def admit_view(graph, con, scope, name, category, body, **kw):
    spec = ViewSpec(name, category, body, [], [], list(kw.pop("grain", [])), **kw)
    graph.add_view(spec)
    outcome, detail = registry.admit(graph, spec, con, scope)
    assert outcome == "admitted", detail
    return spec


def req(name, category, outputs=(), grain=(), filters=None, text="relation", **kw):
    return ViewRequest(name, category, list(outputs), list(grain), dict(filters or {}), text, **kw)


# --------------------------------------------------------------------------- #
# Contracts
# --------------------------------------------------------------------------- #
def test_grain_kinds_are_derived_not_guessed():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    agg = admit_view(g, con, scope, "totals", "AGG",
                     "SELECT entity_id, SUM(amount) AS total FROM events_table GROUP BY entity_id")
    assert (agg.grain_kind, agg.grain, agg.provenance["grain_basis"]) == ("keyed", ["entity_id"], "group_by")
    scalar = admit_view(g, con, scope, "grand", "AGG", "SELECT SUM(amount) AS t FROM events_table")
    assert (scalar.grain_kind, scalar.grain) == ("scalar", [])
    pk = admit_view(g, con, scope, "ev", "SEL", "SELECT event_id, amount FROM events_table")
    assert (pk.grain_kind, pk.grain, pk.provenance["grain_basis"]) == ("keyed", ["event_id"], "primary_key")
    # no key exposed and nothing unique -> unknown -> not admitted
    nokey = ViewSpec("amounts", "SEL", "SELECT entity_id, amount FROM events_table", [], [], [])
    g.add_view(nokey)
    outcome, detail = registry.admit(g, nokey, con, scope)
    assert outcome == "rejected" and "unknown grain" in detail


def test_outputs_come_from_execution_and_validation_catches_false_grain():
    con = make_db()
    g = ViewGraph("db")
    spec = ViewSpec("x", "SEL", "SELECT entity_id, amount FROM events_table", [], ["bogus"], ["entity_id"],
                    grain_kind="keyed")
    g.add_view(spec)
    rec = contracts.validate(con, g, spec)
    assert not rec["passed"]
    assert any("declared outputs missing" in f for f in rec["failures"])
    assert rec["grain_check"] == "fail"


def test_filters_time_windows_and_containment():
    facts = contracts.analyze_sql(
        "SELECT * FROM events_table WHERE status = 'done' AND odate >= '2020-01-01' AND odate < '2021-01-01' "
        "AND amount BETWEEN 2 AND 9")
    assert facts.filters == {"status": "done", "odate": ">=2020-01-01;<2021-01-01", "amount": ">=2;<=9"}
    assert contracts.interval_contains(">=2020-01-01", ">=2020-01-01;<2021-01-01")
    assert not contracts.interval_contains(">=2020-06-01", ">=2020-01-01")
    assert contracts.interval_contains(">=2;<=9", ">=3;<5")
    assert not contracts.interval_contains(">=2", "<=5")


def test_sql_hash_is_stable_across_formatting():
    a = ViewSpec("a", "SEL", "SELECT  entity_id , amount FROM events_table WHERE status='done'", [], [], [])
    b = ViewSpec("b", "SEL", "select entity_id, amount\nfrom EVENTS_TABLE where status = 'done'", [], [], [])
    assert contracts.sql_hash(a) == contracts.sql_hash(b)


def test_question_constants_detects_lifted_literals():
    body = "SELECT player_id FROM players WHERE birth_year = 1990 AND name = 'Ahmed Samir' AND kind = 'active'"
    found = contracts.question_constants(body, "Players born in 1990 named Ahmed Samir")
    assert "1990" in found and "Ahmed Samir" in found and "active" not in found


def test_compact_relational_provenance_tracks_columns_operators_and_parameters():
    con = make_db()
    graph = ViewGraph("db")
    body = ("SELECT e.entity_id, SUM(e.amount) AS total FROM events_table e "
            "JOIN entities_table p ON p.entity_id = e.entity_id "
            "WHERE p.region = :region GROUP BY e.entity_id")
    spec = ViewSpec("regional_totals", "AGG", body, [], ["entity_id", "total"], ["entity_id"])
    facts = contracts.analyze_sql(body)
    prov = contracts.relational_provenance(con, graph, spec, facts, spec.output_columns)
    assert prov["operators"] == ["filter", "join", "project", "aggregate"]
    assert prov["output_lineage"]["entity_id"] == ["events_table.entity_id"]
    assert prov["output_lineage"]["total"] == ["events_table.amount"]
    assert prov["parameter_bindings"] == {"region": "entities_table.region"}
    assert {"events_table.amount", "entities_table.region"} <= set(prov["source_columns"])


# --------------------------------------------------------------------------- #
# Eligibility (Stage 1) — the BIRD failure mode
# --------------------------------------------------------------------------- #
def test_empty_contract_av_view_is_never_reused():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    g.add_view(ViewSpec("chunk_view_0", "SEL", "SELECT COUNT(*) AS n FROM events_table", ["events_table"],
                        [], [], description="how many events"))
    r = req("chunk_view_1", "SEL", text="how many events", holistic=True, source_tables=["events_table"])
    spec, diag = registry.retrieve(g, g, r, HitEmbedder(), scope=scope, con=con, deterministic=True)
    assert spec is None
    assert "incomplete contract" in diag["stage1_rejected"]["chunk_view_0"]


def test_source_domain_and_same_question_exclusion():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    admit_view(g, con, scope, "people", "SEL", "SELECT entity_id, name FROM entities_table")
    admit_view(g, con, scope, "people_events", "JOIN",
               "SELECT e.event_id, p.name FROM events_table e JOIN entities_table p ON p.entity_id = e.entity_id")
    r = req("chunk_view_0", "SEL", holistic=True, source_tables=["events_table"])
    spec, diag = registry.retrieve(g, g, r, HitEmbedder(), scope=scope, con=con, deterministic=True)
    # the table index never proposes `people` (no events_table); the partial overlap fails Stage 1
    assert spec is None and diag["index_candidates"] == 1
    assert "outside the request domain" in diag["stage1_rejected"]["people_events"]
    r2 = req("chunk_view_1", "SEL", holistic=True, source_tables=["entities_table"])
    spec, _ = registry.retrieve(g, g, r2, HitEmbedder(), scope=scope, con=con, deterministic=True,
                                exclude={"people"})
    assert spec is None


def test_qualified_output_provenance_rejects_same_named_column_from_wrong_table():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    events = admit_view(g, con, scope, "event_entities", "SEL",
                        "SELECT event_id, entity_id FROM events_table")
    admit_view(g, con, scope, "people", "SEL", "SELECT entity_id, name FROM entities_table")
    request = req("wanted", "SEL", ["events_table.entity_id"], text="entity identifiers",
                  source_tables=["events_table", "entities_table"])
    spec, diag = registry.retrieve(g, g, request, HitEmbedder(), scope=scope, con=con,
                                   deterministic=True)
    assert spec is events
    assert "column lineage mismatch" in diag["provenance_rejected"]["people"]


def test_schema_change_makes_skill_ineligible():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    s = admit_view(g, con, scope, "people", "SEL", "SELECT entity_id, name FROM entities_table")
    assert registry.eligible(s, g, scope)[0]
    con.execute("ALTER TABLE entities_table ADD COLUMN extra TEXT")
    scope2 = contracts.make_scope(con, "db")
    ok, why = registry.eligible(s, g, scope2)
    assert not ok and "schema changed" in why


# --------------------------------------------------------------------------- #
# Stage 2 + 4: reuse modes
# --------------------------------------------------------------------------- #
def _setup_modes():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    ev = admit_view(g, con, scope, "events", "SEL", "SELECT event_id, entity_id, amount, status FROM events_table")
    tot = admit_view(g, con, scope, "status_totals", "AGG",
                     "SELECT entity_id, status, SUM(amount) AS total, AVG(amount) AS mean "
                     "FROM events_table GROUP BY entity_id, status")
    return con, scope, g, ev, tot


def test_exact_reuse():
    con, scope, g, ev, _ = _setup_modes()
    spec, d = registry.retrieve(g, g, req("rows", "SEL", ["entity_id", "amount"]), HitEmbedder(),
                                scope=scope, con=con, deterministic=True)
    assert spec is ev and d["mode"] == "exact"


def test_specialization_applies_filter_downstream():
    con, scope, g, ev, _ = _setup_modes()
    spec, d = registry.retrieve(g, g, req("done_rows", "SEL", ["entity_id", "amount"],
                                          filters={"status": "done"}), HitEmbedder(),
                                scope=scope, con=con, deterministic=True)
    assert d["mode"] == "specialization" and spec.depends_on == ["events"]
    rows = datasets.run_sql(con, sqlview.compose_sql(g, [spec.name], f"SELECT COUNT(*) FROM {spec.name}"))
    assert rows == [(3,)]


def test_rollup_is_exact_for_sum_and_refused_for_avg():
    con, scope, g, _, tot = _setup_modes()
    spec, d = registry.retrieve(g, g, req("per_entity", "AGG", ["entity_id", "total"], ["entity_id"]),
                                HitEmbedder(), scope=scope, con=con, deterministic=True)
    assert d["mode"] == "rollup"
    rows = datasets.run_sql(con, sqlview.compose_sql(g, [spec.name],
                                                     f"SELECT entity_id, total FROM {spec.name} ORDER BY 1"))
    assert rows == [(1, 8), (2, 11)]
    spec, d = registry.retrieve(g, g, req("mean_per_entity", "AGG", ["entity_id", "mean"], ["entity_id"]),
                                HitEmbedder(), scope=scope, con=con, deterministic=True)
    assert spec is None and "not re-aggregable" in d["stage2_rejected"]["status_totals"]


def test_aggregated_view_is_not_specialized_on_non_key_column():
    con, scope, g, _, _ = _setup_modes()
    m, why = registry.stage2(g.views["status_totals"],
                             req("x", "AGG", ["entity_id", "total"], ["entity_id", "status"], {"amount": ">3"}))
    assert m is None and "cannot specialize" in why


def test_composition_joins_two_skills_one_to_one():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    admit_view(g, con, scope, "names", "SEL", "SELECT entity_id, name FROM entities_table")
    admit_view(g, con, scope, "regions", "SEL", "SELECT entity_id, region FROM entities_table")
    spec, d = registry.retrieve(g, g, req("profile", "SEL", ["entity_id", "name", "region"], ["entity_id"]),
                                HitEmbedder(), scope=scope, con=con, deterministic=True)
    assert d["mode"] == "composition" and set(d["base"]) == {"names", "regions"}
    rows = datasets.run_sql(con, sqlview.compose_sql(g, [spec.name], f"SELECT * FROM {spec.name} ORDER BY 1"))
    assert rows == [(1, "a", "N"), (2, "b", "S")]


def test_stage5_selector_may_reject_every_candidate():
    con, scope, g, _, _ = _setup_modes()
    llm = Fake({"choose": json.dumps({"choice": "NONE", "reason": "not guaranteed"})})
    spec, d = registry.retrieve(g, g, req("rows", "SEL", ["entity_id", "amount"]), HitEmbedder(),
                                scope=scope, con=con, llm=llm)
    assert spec is None and d["decision"] == "verifier chose NONE"


def test_known_misuse_vetoes_candidate():
    con, scope, g, ev, _ = _setup_modes()
    ev.evidence = {"negative_subgoals": ["relation"]}
    spec, d = registry.retrieve(g, g, req("rows", "SEL", ["entity_id", "amount"]), HitEmbedder(),
                                scope=scope, con=con, deterministic=True)
    assert spec is None and "known misuse" in d["stage3_rejected"]["events"]


# --------------------------------------------------------------------------- #
# Admission: dedup, equivalence, conflicts, subsumption, retirement
# --------------------------------------------------------------------------- #
def test_admission_dedups_by_hash_and_merges_equivalents():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    admit_view(g, con, scope, "people", "SEL", "SELECT entity_id, name FROM entities_table")
    dup = ViewSpec("people2", "SEL", "select entity_id, name from entities_table", [], [], [])
    g.add_view(dup)
    assert registry.admit(g, dup, con, scope) == ("duplicate", "people")
    eq = ViewSpec("people3", "SEL", "SELECT entity_id, name FROM entities_table WHERE entity_id > 0", [], [], [])
    g.add_view(eq)
    outcome, _ = registry.admit(g, eq, con, scope)
    assert outcome == "admitted"                      # extra filter -> different contract, not equivalent


def test_admission_uses_provenance_structure_for_equivalence():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    admit_view(g, con, scope, "people", "SEL", "SELECT entity_id, name FROM entities_table")
    alias = ViewSpec("people_alias", "SEL",
                     "SELECT e.entity_id, e.name FROM entities_table AS e", [], [], [])
    g.add_view(alias)
    assert registry.admit(g, alias, con, scope) == ("equivalent", "people")
    grouped = ViewSpec("people_grouped", "SEL",
                       "SELECT entity_id, name FROM entities_table GROUP BY entity_id", [], [], [])
    g.add_view(grouped)
    outcome, _ = registry.admit(g, grouped, con, scope)
    assert outcome == "admitted"
    assert contracts.provenance_signature(grouped) != contracts.provenance_signature(g.views["people"])


def test_provenance_equivalence_canonicalizes_reversed_join_keys():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    admit_view(g, con, scope, "event_people", "JOIN",
               "SELECT e.event_id, p.name FROM events_table e "
               "LEFT JOIN entities_table p ON e.entity_id = p.entity_id")
    reverse = ViewSpec("event_people_reverse", "JOIN",
                       "SELECT e.event_id, p.name FROM events_table e "
                       "LEFT JOIN entities_table p ON p.entity_id = e.entity_id", [], [], [])
    g.add_view(reverse)
    assert registry.admit(g, reverse, con, scope) == ("equivalent", "event_people")


def test_final_query_contribution_provenance_records_columns_and_roles():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    events = admit_view(g, con, scope, "events", "SEL",
                        "SELECT event_id, entity_id, amount FROM events_table")
    sql = sqlview.compose_sql(g, [events.name],
                              "SELECT SUM(amount) FROM events WHERE entity_id = 1")
    contributions = evidence.skill_contributions(sql, g, [events.name])
    assert set(contributions["events"]["columns"]) == {"amount", "entity_id"}
    assert set(contributions["events"]["roles"]) == {"aggregate", "filter"}


def test_subsumption_and_supersession_edges():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    broad = admit_view(g, con, scope, "all_events", "SEL",
                       "SELECT event_id, entity_id, amount, status FROM events_table")
    narrow = admit_view(g, con, scope, "done_events", "SEL",
                        "SELECT event_id, entity_id, amount, status FROM events_table WHERE status = 'done'")
    assert "done_events" in g.related("all_events", "SUBSUMES")
    assert g.related("done_events", "SUBSUMES") == []          # one direction only, no inverse edge
    narrow.evidence = {"negative": 2, "positive": 0}
    assert registry.retire_if_harmful(g, narrow)
    assert narrow.status == "retired" and not registry.eligible(narrow, g, scope)[0]
    assert broad.status == "active"


def test_persistence_round_trip_keeps_contract_and_relations(tmp_path):
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    admit_view(g, con, scope, "all_events", "SEL", "SELECT event_id, entity_id, amount, status FROM events_table")
    admit_view(g, con, scope, "done_events", "SEL",
               "SELECT event_id, entity_id, amount, status FROM events_table WHERE status = 'done'")
    p = tmp_path / "db.json"
    sqlview.save_graph(g, str(p))
    loaded = sqlview.load_graph(str(p))
    assert loaded.views["done_events"].grain_kind == "keyed"
    assert loaded.views["done_events"].skill_id == g.views["done_events"].skill_id
    assert ("all_events", "done_events", "SUBSUMES") in loaded.relations()
    assert registry.eligible(loaded.views["done_events"], loaded, scope)[0]
    assert loaded.topo_closure(["done_events"])[0].name == "done_events"


# --------------------------------------------------------------------------- #
# Schema versioning and portability
# --------------------------------------------------------------------------- #
def test_refresh_upgrades_legacy_and_marks_av_and_broken_views_stale():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    g.add_view(ViewSpec("legacy_totals", "AGG",
                        "SELECT entity_id, SUM(amount) AS total FROM events_table GROUP BY entity_id",
                        ["events_table"], ["entity_id", "total"], ["entity_id"]))
    g.add_view(ViewSpec("chunk_view_0", "SEL", "SELECT * FROM events_table", ["events_table"], [], []))
    g.add_view(ViewSpec("broken", "SEL", "SELECT nope FROM events_table", ["events_table"], ["nope"], []))
    stats = registry.refresh(g, con, scope)
    assert g.views["legacy_totals"].status == "active" and g.views["legacy_totals"].grain_kind == "keyed"
    assert g.views["chunk_view_0"].status == "stale" and g.views["broken"].status == "stale"
    assert stats == {"current": 0, "upgraded": 1, "stale": 2}


def test_port_requires_identical_table_interface():
    src_con, dst_con, other_con = make_db(), make_db(), sqlite3.connect(":memory:")
    other_con.execute("CREATE TABLE entities_table(entity_id INTEGER PRIMARY KEY, name TEXT)")  # no region
    src_scope = contracts.make_scope(src_con, "src")
    src = ViewGraph("src")
    admit_view(src, src_con, src_scope, "people", "SEL", "SELECT entity_id, name FROM entities_table")
    dst = ViewGraph("dst")
    res = registry.port(src, dst, dst_con, contracts.make_scope(dst_con, "dst"))
    assert res == {"people": "admitted"}
    assert dst.views["people"].provenance["origin"] == "ported"
    assert dst.views["people"].provenance["db_id"] == "dst"
    other = ViewGraph("other")
    assert registry.port(src, other, other_con, contracts.make_scope(other_con, "other")) == {"people": "tables differ"}


# --------------------------------------------------------------------------- #
# Credit assignment
# --------------------------------------------------------------------------- #
def test_credit_only_for_ctes_the_outer_query_reads():
    g = ViewGraph("db")
    g.add_view(ViewSpec("base", "SEL", "SELECT entity_id, amount FROM events_table", [], [], []))
    g.add_view(ViewSpec("tot", "AGG", "SELECT entity_id, SUM(amount) AS t FROM base GROUP BY entity_id",
                        [], [], [], depends_on=["base"]))
    g.add_view(ViewSpec("dead", "SEL", "SELECT 1 AS x", [], [], []))
    sql = sqlview.compose_sql(g, ["tot", "dead"], "SELECT SUM(t) FROM tot")
    credit = evidence.assign_credit(g, sql, True, ["tot", "dead"])
    assert credit["tot"]["executed"] and credit["base"]["executed"]
    assert credit["dead"]["included"] and not credit["dead"]["referenced"]
    # A repair that rewrote a CTE body breaks the link to the stored skill.
    repaired = sql.replace("SUM(amount) AS t", "SUM(amount) * 2 AS t")
    credit = evidence.assign_credit(g, repaired, True, ["tot"])
    assert credit["tot"]["modified_by_repair"] and not credit["tot"]["executed"]


def test_skill_outcome_rules():
    assert evidence.skill_outcome(False, "causal_win") == "positive"
    assert evidence.skill_outcome(True, "causal_loss") == "negative"
    assert evidence.skill_outcome(False, "neutral") == "none"
    assert evidence.skill_outcome(True, None) == "positive"
    assert evidence.skill_outcome(False, None, trivial=True) == "none"
    assert evidence.skill_outcome(None, None) == "none"


def test_replace_cte_body_is_verbatim_when_possible():
    sql = "WITH a AS (\nSELECT 1 AS x\n)\nSELECT x FROM a"
    assert evidence.replace_cte_body(sql, "a", "SELECT 1 AS x", "SELECT 2 AS x") == \
        "WITH a AS (\nSELECT 2 AS x\n)\nSELECT x FROM a"


# --------------------------------------------------------------------------- #
# Retrieval before alignment
# --------------------------------------------------------------------------- #
def test_prefetch_grounds_hits_before_skipping_alignment():
    """Fix 1: a prefetch hit skips full alignment only after alignment on its lineage chunk confirms the skill's tables."""
    llm = Fake({
        "decompose": json.dumps({"subgoals": [
            {"name": "a", "category": "SEL", "description": "a"},
            {"name": "b", "category": "SEL", "description": "b"},
            {"name": "c", "category": "SEL", "description": "c"}]}),
        "align": lambda user: '{"tables": ["orders"]}' if "CREATE TABLE orders" in user else '{"tables": []}',
    })
    chunks = ["CREATE TABLE orders (id INT)", "CREATE TABLE people (id INT)"]
    rejected = []
    reqs, per, calls = agents.decompose_and_align(
        llm, chunks, "q", "", prefetch=lambda rs: {"b": ["orders"], "c": ["people"]},
        on_ungrounded=rejected.append)
    # b grounded with 1 call on its lineage chunk. c's skill reads `people` but alignment rejects it -> full alignment.
    assert per["b"] == {"orders"} and rejected == ["c"]
    assert calls == 1 + 1 + 2 * 2          # b grounding + c grounding attempt + full alignment for a and c


# --------------------------------------------------------------------------- #
# End to end through realrun (fake LLM, in-memory SQLite)
# --------------------------------------------------------------------------- #
HARD = {
    "rewrite": json.dumps({"task": "total done amount", "required_outputs": ["total"]}),
    "difficulty": json.dumps({"difficulty": "hard", "relevant_tables": ["events_table"],
                              "independent_grains": 2, "needs_dependent_relations": True,
                              "operations": ["nested_aggregation"], "confidence": 0.95}),
    "decompose": json.dumps({"subgoals": [
        {"name": "done_events", "category": "SEL", "description": "completed events",
         "required_outputs": ["event_id", "entity_id", "amount"], "grain": ["event_id"],
         "view_filters": {"status": "done"}, "depends_on": [], "may_read_base_tables": True},
        {"name": "entity_totals", "category": "AGG", "description": "completed amount per entity",
         "required_outputs": ["entity_id", "total"], "grain": ["entity_id"],
         "depends_on": ["done_events"], "join_keys": ["entity_id"],
         "relationship": "aggregate_input", "may_read_base_tables": False}]}),
    "align": lambda user: ('{"tables":["events_table"]}' if "events_table" in user else '{"tables":[]}'),
    "generate": lambda user: (
        '```sql\nSELECT event_id, entity_id, amount, status FROM events_table WHERE status = \'done\'\n```\n'
        '```json\n{"output_columns":["event_id","entity_id","amount","status"],"grain":["event_id"],'
        '"source_tables":["events_table"]}\n```') if "`done_events`" in user else (
        '```sql\nSELECT entity_id, SUM(amount) AS total FROM done_events GROUP BY entity_id\n```\n'
        '```json\n{"output_columns":["entity_id","total"],"grain":["entity_id"],"depends_on":["done_events"]}\n```'),
    "choose": choose_first,
    "plan": "sum entity_totals.total",
    "review_plan": json.dumps({"reject": [], "plan": "sum entity_totals.total"}),
    "compose": "```sql\nSELECT SUM(total) AS total FROM entity_totals\n```",
    "gen_tests": json.dumps({"tests": [{"purpose": "no null keys",
                                        "sql": "SELECT COUNT(*) FROM entity_totals WHERE entity_id IS NULL"}]}),
    "extract_final": json.dumps({"reusable": False, "reason": "one-off"}),
    "ablation_generate": lambda user: (
        # the regenerated view forgets the status filter -> the ablated answer is wrong
        '```sql\nSELECT event_id, entity_id, amount, status FROM events_table\n```\n'
        '```json\n{"output_columns":["event_id","entity_id","amount","status"]}\n```')
        if "`done_events`" in user else
        '```sql\nSELECT entity_id, SUM(amount) AS total FROM done_events GROUP BY entity_id\n```\n```json\n{}\n```',
}


def _chunks(con):
    return [(datasets.table_block(con, "events_table"), ["events_table"]),
            (datasets.table_block(con, "entities_table"), ["entities_table"])]


def _run(llm, graph, con, q, scope, gold, *, use_memory=True, ledger=None, episodes=None, **cfg):
    reg = realrun.RegistryConfig(scope=scope, **cfg)
    ledger = ledger if ledger is not None else evidence.EvidenceLedger()
    episodes = episodes if episodes is not None else evidence.EpisodeStore()

    def scorer(db, sql, _q):
        return db.execute(sql).fetchall() == gold, ""
    before = set(graph.views)
    r = realrun.answer_question(llm, HitEmbedder(), graph, con, datasets.render_schema(con), _chunks(con), None, q,
                                use_memory=use_memory, use_guard=True, tau=0.6, max_views=3, scorer=scorer,
                                architecture="auto", registry_cfg=reg)
    ctx = r.pop("_learn")
    if use_memory:
        r.update(realrun._learn(llm, graph, con, datasets.render_schema(con), q, r, ctx, reg, label_free=False,
                                scorer=scorer, ledger=ledger, episodes=episodes))
        realrun._drop_uncommitted(graph, before)
    return r


def test_hard_route_grows_registry_then_reuses_before_alignment():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    graph = ViewGraph("db")
    ledger, episodes = evidence.EvidenceLedger(), evidence.EpisodeStore()
    llm = Fake(HARD)
    q1 = datasets.Question("q1", "db", "What is the total completed amount?", "")
    r1 = _run(llm, graph, con, q1, scope, [(15,)], ledger=ledger, episodes=episodes)
    assert r1["correct"] and r1["alignment_calls"] == 4 and r1["generated"] == 2
    assert {o.split(":")[0] for o in r1["admitted"].values() if not o.startswith("not")} == {"admitted"}
    assert graph.views["entity_totals"].status == "active"
    assert graph.views["entity_totals"].validation["tests"][0]["result"] == "pass"
    assert graph.views["done_events"].provenance["question_id"] == "q1"

    q2 = datasets.Question("q2", "db", "Total completed amount again?", "")
    r2 = _run(llm, graph, con, q2, scope, [(15,)], ledger=ledger, episodes=episodes)
    # both hits grounded on the events chunk only: 2 calls instead of 2 subgoals x 2 chunks
    assert r2["correct"] and r2["prefetch_hits"] == 2 and r2["alignment_calls"] == 2
    assert r2["prefetch_ungrounded"] == 0
    assert r2["reused"] == 2 and r2["generated"] == 0
    assert set(r2["reuse_executed"]) == {"done_events", "entity_totals"}
    # the regenerated done_events drops the filter -> total 19 -> the reuse was causal
    assert r2["ablation"]["done_events"] == "causal_win"
    assert graph.views["done_events"].evidence["positive"] == 1
    assert "Total completed amount again?" in graph.views["done_events"].validated_on
    assert len(episodes.records) == 2 and episodes.records[1]["executed"]
    assert any(rec.get("name") == "done_events" and rec.get("skill_outcome") == "positive"
               for rec in ledger.records)
    assert not any(d.get("kind") == "episode" for _n, d in graph.g.nodes(data=True))   # episodes live in JSONL
    assert episodes.records[1]["credit"]["done_events"]["executed"]


def test_dead_reused_cte_gets_no_credit():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    graph = ViewGraph("db")
    llm = Fake(HARD)
    _run(llm, graph, con, datasets.Question("q1", "db", "total", ""), scope, [(15,)])
    dead = dict(HARD, compose="```sql\nSELECT SUM(amount) AS total FROM events_table WHERE status = 'done'\n```")
    r = _run(Fake(dead), graph, con, datasets.Question("q2", "db", "total?", ""), scope, [(15,)])
    assert r["reused"] == 2 and r["reuse_executed"] == []
    assert graph.views["done_events"].evidence.get("positive", 0) == 0
    assert graph.views["done_events"].evidence["included"] == 1


def test_moderate_route_promotes_only_referenced_chunk_views():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    graph = ViewGraph("db")
    llm = Fake({
        "rewrite": json.dumps({"task": "sum event amounts"}),
        "difficulty": json.dumps({"difficulty": "moderate", "relevant_tables": ["events_table"],
                                  "independent_grains": 1, "needs_dependent_relations": False,
                                  "operations": ["aggregate"], "confidence": 0.9}),
        "av_view": lambda user: ('```sql\nSELECT event_id, entity_id, amount FROM events_table\n```\n'
                                 '```json\n{"events_table": ["event_id", "entity_id", "amount"]}\n```'
                                 if "events_table" in user else
                                 '```sql\nSELECT entity_id, name FROM entities_table\n```\n'
                                 '```json\n{"entities_table": ["entity_id", "name"]}\n```'),
        "plan": "sum", "review_plan": json.dumps({"reject": [], "plan": "sum"}),
        "compose": "```sql\nSELECT SUM(amount) FROM chunk_view_0\n```",
        "promote_describe": json.dumps({"name": "event_amounts", "description": "one row per event with its amount",
                                        "when_to_use": ["event amounts"], "when_not_to_use": ["per entity totals"]}),
        "gen_tests": json.dumps({"tests": []}),
        "extract_final": json.dumps({"reusable": False}),
    })
    r = _run(llm, graph, con, datasets.Question("m1", "db", "Total event amount?", ""), scope, [(19,)])
    assert r["correct"] and r["architecture_route"] == "av_nx1_graph"
    assert r["admitted"]["chunk_view_0"] == "admitted:event_amounts"
    assert r["admitted"]["chunk_view_1"].startswith("discarded")
    spec = graph.views["event_amounts"]
    assert spec.description == "one row per event with its amount" and spec.params["when_not_to_use"]
    assert spec.grain_kind == "keyed" and spec.provenance["origin"] == "av_chunk"
    assert set(graph.views) == {"event_amounts"}


def test_final_sql_is_an_episode_and_extraction_rejects_question_constants():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    graph = ViewGraph("db")
    llm = Fake({
        "rewrite": json.dumps({"task": "amount of entity a"}),
        "difficulty": json.dumps({"difficulty": "easy", "relevant_tables": ["events_table"],
                                  "independent_grains": 1, "needs_dependent_relations": False,
                                  "operations": ["filter"], "confidence": 0.95}),
        "direct": "```sql\nSELECT SUM(amount) FROM events_table WHERE entity_id = 2\n```",
        "extract_final": json.dumps({"reusable": True, "name": "entity_two_events", "category": "SEL",
                                     "description": "events of entity 2",
                                     "body_sql": "SELECT event_id, amount FROM events_table WHERE entity_id = 2"}),
    })
    episodes = evidence.EpisodeStore()
    r = _run(llm, graph, con, datasets.Question("e1", "db", "What did entity 2 spend?", ""), scope, [(11,)],
             episodes=episodes)
    assert r["correct"] and graph.n_views() == 0
    assert "question-specific constants" in r["admitted"]["<final_sql>"]
    assert episodes.records[0]["final_sql"].startswith("SELECT SUM(amount)")


def test_no_memory_config_never_learns_or_retrieves():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    graph = ViewGraph("db")
    r = _run(Fake(HARD), graph, con, datasets.Question("q1", "db", "total", ""), scope, [(15,)],
             use_memory=False)
    assert r["correct"] and r["reused"] == 0 and "prefetch_hits" in r and r["prefetch_hits"] == 0


def test_run_config_defaults_to_registry_and_persists_ledger_and_episodes(tmp_path, monkeypatch):
    db_file = tmp_path / "regtest_db.sqlite"
    disk = sqlite3.connect(str(db_file))
    make_db().backup(disk)
    disk.close()
    fake = Fake(HARD)
    monkeypatch.setattr(realrun, "LLM", lambda **_kw: fake)
    monkeypatch.setattr(realrun, "Embedder", HitEmbedder)
    monkeypatch.setattr(datasets, "db_path", lambda *_a, **_k: str(db_file))
    gold = "SELECT SUM(amount) FROM events_table WHERE status = 'done'"
    qs = [datasets.Question(f"q{i}", "regtest_db", f"Total completed amount {i}?", gold) for i in range(2)]
    grown = tmp_path / "grown"
    rows, sizes = realrun.run_config(
        "A_SkiewSQL", {"regtest_db": qs}, use_memory=True, use_guard=True, tau=0.6, model="fake",
        max_views=3, db_root=str(tmp_path), dataset="spider", no_valuelink=True, architecture="auto",
        grown_dir=str(grown))
    assert [r["correct"] for r in rows] == [True, True]
    # one chunk: grounding each hit on its lineage chunk costs the same as aligning it
    assert rows[1]["prefetch_hits"] == 2 and rows[1]["alignment_calls"] == 2
    assert all("_learn" not in r for r in rows)
    json.dumps(rows)                                   # rows stay JSON-serializable
    assert (grown / "regtest_db.json").exists()
    assert len(evidence.JsonlStore.load(str(grown / "regtest_db.episodes.jsonl"))) == 2
    assert evidence.JsonlStore.load(str(grown / "regtest_db.ledger.jsonl"))
    summary = realrun.summarize("A", rows, sizes, {"total_tokens": 0, "by_tag": {}})
    assert summary["alignment_calls_total"] == 4 and summary["prefetch_hits"] == 2   # 2 subgoals x 1 chunk, then 2 groundings
    assert summary["skills_admitted"] == 2 and summary["causal_positive_reuse_count"] == 1
    reloaded = sqlview.load_graph(str(grown / "regtest_db.json"))
    assert all(v.status == "active" for v in reloaded.views.values())


def test_failing_generated_test_blocks_admission_before_description():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    spec = ViewSpec("people", "SEL", "SELECT entity_id, name FROM entities_table", [], [], [])
    g.add_view(spec)
    described = []
    seen_outputs = []

    def tests_fn(s):
        seen_outputs.append(list(s.output_columns))      # contract is derived before tests are written
        return [{"purpose": "names are never 'b'", "sql": "SELECT COUNT(*) FROM people WHERE name = 'b'"}]
    outcome, detail = registry.admit(g, spec, con, scope, tests_fn=tests_fn, describe_fn=described.append)
    assert outcome == "rejected" and "test failed" in detail
    assert seen_outputs == [["entity_id", "name"]] and described == []


def test_dependents_of_a_retired_skill_become_ineligible():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    base = admit_view(g, con, scope, "done_events", "SEL",
                      "SELECT event_id, entity_id, amount FROM events_table WHERE status = 'done'")
    top = admit_view(g, con, scope, "done_totals", "AGG",
                     "SELECT entity_id, SUM(amount) AS total FROM done_events GROUP BY entity_id",
                     depends_on=["done_events"])
    assert registry.eligible(top, g, scope)[0]
    base.evidence = {"negative": 3, "positive": 1}
    assert registry.retire_if_harmful(g, base)
    ok, why = registry.eligible(top, g, scope)
    assert not ok and "dependency done_events" in why


def test_view_over_a_view_has_base_table_lineage_only():
    """Regression: a view reading only another view used to keep the model's self-reported source_tables (the dependency's name), which then looked like a changed table and made the skill ineligible."""
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    admit_view(g, con, scope, "done_events", "SEL",
               "SELECT event_id, entity_id, amount FROM events_table WHERE status = 'done'")
    top = ViewSpec("done_totals", "AGG", "SELECT entity_id, SUM(amount) AS total FROM done_events GROUP BY entity_id",
                   ["done_events"], [], [], depends_on=["done_events"])
    g.add_view(top)
    assert registry.admit(g, top, con, scope)[0] == "admitted"
    assert top.source_tables == [] and top.provenance["lineage"] == ["events_table"]
    assert set(top.provenance["table_fingerprints"]) == {"events_table"}
    assert registry.eligible(top, g, scope)[0]



# --------------------------------------------------------------------------- #
# Review fixes 2-8
# --------------------------------------------------------------------------- #
def test_dependency_filters_enter_the_effective_contract():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    admit_view(g, con, scope, "done_events", "SEL",
               "SELECT event_id, entity_id, amount FROM events_table WHERE status = 'done'")
    top = admit_view(g, con, scope, "done_totals", "AGG",
                     "SELECT entity_id, SUM(amount) AS total FROM done_events GROUP BY entity_id",
                     depends_on=["done_events"])
    assert top.semantic_filters == {"status": "done"} and top.provenance["inherited_filters"] == {"status": "done"}
    all_rows = req("totals", "AGG", ["entity_id", "total"], ["entity_id"])
    assert "narrower" in registry.stage2(top, all_rows)[1]              # not reusable for all events
    done_rows = req("totals", "AGG", ["entity_id", "total"], ["entity_id"], inherited_filters={"status": "done"})
    assert registry.stage2(top, done_rows)[0].mode == "exact"


def test_decomposer_propagates_filters_to_dependent_subgoals():
    llm = Fake({"decompose": json.dumps({"subgoals": [
        {"name": "done", "category": "SEL", "description": "d", "view_filters": {"status": "done"}},
        {"name": "tot", "category": "AGG", "description": "t", "depends_on": ["done"]},
        {"name": "top", "category": "RANK", "description": "r", "depends_on": ["tot"]}]})})
    reqs = agents.decompose_subgoals(llm, "", "q")
    assert reqs[1].inherited_filters == {"status": "done"} and reqs[2].inherited_filters == {"status": "done"}
    assert reqs[1].required_filters == {}                              # the generator never sees them


def test_graph_edge_types_and_single_source_of_truth(tmp_path):
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    admit_view(g, con, scope, "base", "SEL", "SELECT event_id, amount FROM events_table")
    g.add_view(ViewSpec("child", "SEL", "SELECT event_id FROM base", ["events_table"], ["event_id"], ["event_id"],
                        depends_on=["base"]))
    g.add_relation("base", "child", "SUBSUMES")
    kinds = {d["etype"] for _u, v, d in g.g.edges("view::child", data=True)}
    assert kinds == {"DEPENDS_ON", "READS_TABLE"}
    assert {d["etype"] for _u, v, d in g.g.edges("view::base", data=True)} >= {"SUBSUMES", "READS_TABLE"}
    assert g.check_consistency() == []
    # dependencies change only through the graph, which keeps the list and the edges in step
    g.add_view(ViewSpec("other", "SEL", "SELECT 1 AS x", [], ["x"], ["x"]))
    g.set_depends_on("child", ["base", "other"])
    assert g.views["child"].depends_on == ["base", "other"] and g.check_consistency() == []
    g.views["child"].depends_on = ["base"]                       # a direct edit is detected ...
    assert g.check_consistency()
    g.reindex("child")                                           # ... and re-derived from the ViewSpec
    assert g.check_consistency() == []
    # removed relation types are refused, and old files that contain them still load
    g.add_relation("base", "child", "SPECIALIZES")
    g.add_relation("base", "child", "EQUIVALENT_TO")
    assert {e for *_x, e in g.relations()} == {"SUBSUMES"}
    p = tmp_path / "g.json"
    sqlview.save_graph(g, str(p))
    data = json.loads(p.read_text())
    data["relations"].append(["child", "base", "SPECIALIZES"])
    data["episodes"] = [{"id": "e1", "links": {"USED_SKILL": ["base"]}}]
    p.write_text(json.dumps(data))
    loaded = sqlview.load_graph(str(p))
    assert loaded.relations() == [("base", "child", "SUBSUMES")] and loaded.check_consistency() == []
    assert {d.get("kind") for _n, d in loaded.g.nodes(data=True)} <= {"view", "table"}


def test_low_confidence_or_minority_verifier_votes_abstain():
    con, scope, g, _, _ = _setup_modes()
    low = Fake({"choose": json.dumps({"choice": "events", "confidence": 0.2})})
    spec, d = registry.retrieve(g, g, req("rows", "SEL", ["entity_id", "amount"]), HitEmbedder(),
                                scope=scope, con=con, llm=low)
    assert spec is None and d["decision"] == "verifier confidence too low"
    answers = iter([json.dumps({"choice": "status_totals", "confidence": 0.9}),
                    json.dumps({"choice": "NONE"}), json.dumps({"choice": "NONE"})])
    split = Fake({"choose": lambda _u: next(answers)})
    spec, d = registry.retrieve(g, g, req("t", "AGG", ["entity_id", "status", "total"], ["entity_id", "status"]),
                                HitEmbedder(), scope=scope, con=con, llm=split)
    assert spec is None and split.calls.count("choose") == 3 and d["decision"] == "no verifier majority"


def test_lowercase_question_constants_are_caught():
    found = contracts.question_constants("SELECT id FROM t WHERE country = 'france' AND kind = 'active'",
                                         "Which customers are in france?")
    assert found == ["france"]
    assert contracts.question_constants("SELECT id FROM t WHERE work_rate = 'low'", "players",
                                        extra_texts=["low means attacking work rate is low"]) == ["low"]


def test_observed_grain_is_invalidated_by_new_data():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    g = ViewGraph("db")
    s = admit_view(g, con, scope, "firsts", "SEL", "SELECT DISTINCT entity_id, status FROM events_table")
    assert s.provenance["grain_basis"] == "distinct" and s.provenance["data_fingerprints"]
    con.execute("INSERT INTO events_table VALUES (9, 3, 1, 'done', '2022-01-01')")
    scope2 = contracts.make_scope(con, "db")
    ok, why = registry.eligible(s, g, scope2)
    assert not ok and "data changed" in why
    registry.refresh(g, con, scope2)                                   # re-derived on the new data
    assert registry.eligible(s, g, scope2)[0]
    pk = admit_view(g, con, scope2, "ev", "SEL", "SELECT event_id, amount FROM events_table")
    assert pk.provenance["data_fingerprints"] == {}                    # structural key: no data stamp


def test_fingerprint_covers_keys_and_constraints():
    con = make_db()
    before = contracts.table_fingerprint(con, "entities_table")
    con.execute("CREATE UNIQUE INDEX u_name ON entities_table(name)")
    assert contracts.table_fingerprint(con, "entities_table") != before


def test_retrieval_uses_structural_indexes():
    con, scope, g, ev, tot = _setup_modes()
    r = req("rows", "SEL", ["entity_id", "amount"])
    assert [c.name for c in registry.index_candidates(g, r)] == ["events"]
    r2 = req("x", "SEL", ["no_such_column"])
    spec, d = registry.retrieve(g, g, r2, TableEmbedder({}), scope=scope, con=con, deterministic=True)
    assert spec is None and d["index_candidates"] == 0 and "stage1_rejected" not in d



# --------------------------------------------------------------------------- #
# Stage 0: output-name mapping
# --------------------------------------------------------------------------- #
def test_name_mapping_rules():
    emb = TableEmbedder({("num students", "student count"): 0.61, ("month", "year"): 0.65})
    vocab = ["balance", "student_count", "year", "customer_id"]
    m = registry.map_names(["net_balance", "num_students", "month", "customer_id"], vocab, emb, 0.6)
    assert m == {"net_balance": "balance", "num_students": "student_count", "month": "year"}
    # grain keys use the strict threshold: month -> year (0.65) is refused
    assert registry.map_names(["month"], vocab, emb, registry.GRAIN_MAP_EMB) == {}


def test_mapped_match_is_found_but_needs_the_verifier():
    con, scope, g, ev, tot = _setup_modes()
    r = req("per_entity", "AGG", ["entity_id", "sum_amount"], ["entity_id"], text="relation")
    e = TableEmbedder({("sum amount", "total"): 0.7,                      # the rename
                       ("relation", registry.describe_text(tot)): 1.0})  # the skill is on topic
    spec, d = registry.retrieve(g, g, r, e, scope=scope, con=con, deterministic=True)
    assert d["name_map"] == {"sum_amount": "total"} and spec is None
    assert d["decision"] == "name mapping needs LLM verification"
    seen = []

    def choose(user):
        seen.append(user)
        return json.dumps({"choice": "status_totals", "confidence": 0.9})
    spec, d = registry.retrieve(g, g, r, e, scope=scope, con=con, llm=Fake({"choose": choose}))
    assert d["hit"] and d["mode"] == "rollup" and "sum_amount -> total" in seen[0]



# --------------------------------------------------------------------------- #
# Per-question reasons and planner rejection
# --------------------------------------------------------------------------- #
def test_reasons_reach_planner_and_composer_but_not_the_skill():
    con = make_db()
    scope = contracts.make_scope(con, "db")
    graph = ViewGraph("db")
    _run(Fake(HARD), graph, con, datasets.Question("q1", "db", "total", ""), scope, [(15,)])
    seen = {}

    def grab(tag, reply):
        def f(user):
            seen.setdefault(tag, []).append(user)
            return reply(user) if callable(reply) else reply
        return f
    llm = Fake(dict(HARD, plan=grab("plan", HARD["plan"]),
                    compose=grab("compose", HARD["compose"]),
                    choose=lambda u: json.dumps({"choice": re.search(r"- name: (\S+) \(category", u).group(1),
                                                 "reason": "same cohort and grain", "confidence": 0.9})))
    _run(llm, graph, con, datasets.Question("q2", "db", "total?", ""), scope, [(15,)])
    for tag in ("plan", "compose"):
        assert "why it is here: reused stored skill done_events" in seen[tag][0]
        assert "Verifier: same cohort and grain" in seen[tag][0]
    assert "same cohort and grain" not in json.dumps(dataclasses_asdict(graph.views["done_events"]))


def dataclasses_asdict(v):
    import dataclasses
    return dataclasses.asdict(v)


def _av_case(responses):
    con = make_db()
    calls = []
    it = iter(responses)

    def av(user):
        calls.append(user)
        return next(it)
    graph = ViewGraph("db")
    r = ViewRequest("chunk_view_0", "SEL", [], [], {}, "total amount per entity", holistic=True)
    spec = realrun._generate_av_view(Fake({"av_view": av}), HitEmbedder(), graph, con,
                                     datasets.table_block(con, "events_table"), r, None)
    return spec, calls, graph


def test_av_view_repairs_execution_and_consistency_then_keeps_only_valid():
    """AV-SQL §4.3: execution error and CTE/JSON inconsistency are fed back. The view is kept once it executes and is consistent."""
    spec, calls, graph = _av_case([
        '```sql\nSELECT entity_id, amout FROM events_table\n```\n```json\n{"events_table": ["entity_id", "amout"]}\n```',
        '```sql\nSELECT entity_id, amount FROM events_table WHERE status = \'done\'\n```\n'
        '```json\n{"events_table": ["entity_id", "amount"]}\n```',
        '```sql\nSELECT entity_id, amount FROM events_table WHERE status = \'done\'\n```\n'
        '```json\n{"events_table": ["entity_id", "amount", "status"]}\n```',
    ])
    assert spec is not None and graph.has(spec.name) and len(calls) == 3
    assert "Execution error" in calls[1] and "amout" in calls[1]
    assert "events_table.status" in calls[2] and "Inconsistency" in calls[2]


def test_av_view_irrelevant_chunk_and_failed_attempts_give_no_view():
    spec, calls, _g = _av_case(['```json\n{"think": "no", "events_table": "drop_all"}\n```'])
    assert spec is None and len(calls) == 1                       # rule 1: irrelevant -> no CTE, no retry
    bad = '```sql\nSELECT entity_id FROM events_table\n```\n```json\n{"events_table": "drop_all"}\n```'
    spec, calls, graph = _av_case([bad] * realrun.VIEW_VALIDATE_ATTEMPTS)
    assert spec is None and len(calls) == realrun.VIEW_VALIDATE_ATTEMPTS and graph.n_views() == 0
    assert "selects no table or column" in calls[1]               # rules 1+2 fed back


def test_selection_consistency_rules():
    con = make_db()
    body = "SELECT e.event_id, p.name FROM events_table e JOIN entities_table p ON p.entity_id = e.entity_id"
    ok = {"events_table": ["event_id", "entity_id"], "entities_table": ["entity_id", "name"]}
    assert contracts.selection_consistency(body, ok, con) == []
    probs = contracts.selection_consistency(body, {"events_table": ["event_id", "entity_id"]}, con)
    assert any("entities_table" in p for p in probs)
    assert contracts.selection_consistency(body, {}, con)
    assert contracts.selection_consistency("", {}, con) == []
