import json
import sqlite3
import unittest

from skiewsql import agents, contracts, registry as registry_ops, sqlview
from skiewsql import datasets, realrun
from skiewsql.core import SkillRegistry, ViewRequest, ViewSpec


class FakeLLM:
    def __init__(self, difficulty="hard"):
        self.calls = []
        self.difficulty = difficulty

    def ask(self, _system, user, tag="", **_kwargs):
        self.calls.append(tag)
        if tag.endswith("difficulty"):
            if self.difficulty == "easy":
                return json.dumps({"difficulty": "easy", "relevant_tables": ["events_table"],
                                   "independent_grains": 1,
                                   "needs_dependent_relations": False,
                                   "operations": ["filter"], "confidence": 0.95,
                                   "reason": "one-table lookup"})
            if self.difficulty == "moderate":
                return json.dumps({"difficulty": "moderate",
                                   "relevant_tables": ["events_table", "entities_table"],
                                   "independent_grains": 1,
                                   "needs_dependent_relations": False,
                                   "operations": ["join", "aggregate"], "confidence": 0.9,
                                   "reason": "one coherent plan"})
            return json.dumps({"difficulty": "hard",
                               "relevant_tables": ["events_table", "entities_table"],
                               "independent_grains": 2,
                               "needs_dependent_relations": True,
                               "operations": ["nested_aggregation"], "confidence": 0.95,
                               "reason": "dependent grains"})
        if tag.endswith("decompose"):
            return json.dumps({"subgoals": [
                {"name": "events", "category": "SEL", "description": "event rows",
                 "required_outputs": ["entity_id"], "grain": ["entity_id"],
                 "view_filters": {}, "depends_on": [], "join_keys": [],
                 "relationship": "independent", "may_read_base_tables": True},
                {"name": "entity_totals", "category": "AGG", "description": "totals per entity",
                 "required_outputs": ["entity_id", "total"], "grain": ["entity_id"],
                 "view_filters": {}, "depends_on": ["events"], "join_keys": ["entity_id"],
                 "relationship": "aggregate_input", "may_read_base_tables": False},
            ]})
        if tag.endswith("align"):
            if "events_table" in user and "event rows" in user:
                return '{"tables": ["events_table"]}'
            if "entities_table" in user and "totals per entity" in user:
                return '{"tables": ["entities_table"]}'
            return '{"tables": []}'
        raise AssertionError(f"unexpected tag {tag}")


class AdaptiveArchitectureTests(unittest.TestCase):
    def test_nx1_retrieval_contract_does_not_change_original_requests(self):
        class ContractLLM:
            def __init__(self):
                self.calls = []

            def ask(self, _system, user, tag="", **_kwargs):
                self.calls.append((tag, user))
                if "Departments" in user:
                    return json.dumps({
                        "relevant": True,
                        "name": "department_degree_counts",
                        "category": "AGG",
                        "description": "one row per department with its degree count",
                        "required_outputs": [
                            "Departments.department_id", "Departments.department_name", "degree_count"
                        ],
                        "grain": ["Departments.department_id"],
                        "view_filters": {},
                        "operators": ["join"],
                        "source_tables": ["Departments", "Degree_Programs"],
                    })
                return json.dumps({"relevant": False})

        llm = ContractLLM()
        chunks = [
            ("CREATE TABLE Departments\nCREATE TABLE Degree_Programs", ["Departments", "Degree_Programs"]),
            ("CREATE TABLE Addresses", ["Addresses"]),
        ]
        original, per = agents.nx1_requests(
            chunks, "Find the department with the most degrees")
        contracts, calls, fallbacks = agents.nx1_retrieval_contracts(
            llm, chunks, "Find the department with the most degrees")

        self.assertEqual(calls, 2)
        self.assertEqual(fallbacks, 1)
        self.assertEqual(len(original), 2)
        self.assertTrue(all(req.holistic for req in original))
        self.assertTrue(all(not req.required_outputs for req in original))
        self.assertEqual(per["chunk_view_0"], {"Departments", "Degree_Programs"})
        self.assertEqual(per["chunk_view_1"], {"Addresses"})
        self.assertEqual(set(contracts), {"chunk_view_0"})
        req = contracts["chunk_view_0"]
        self.assertEqual(req.category, "AGG")
        self.assertEqual(req.required_outputs, [
            "Departments.department_id", "Departments.department_name", "degree_count"
        ])
        self.assertEqual(req.required_grain, ["Departments.department_id"])
        self.assertEqual(req.required_operators, ["join", "aggregate"])
        self.assertEqual(req.source_tables, ["Departments", "Degree_Programs"])
        self.assertFalse(req.holistic)

    def test_uncertain_nx1_retrieval_contract_keeps_original_generation_request(self):
        class InvalidLLM:
            def ask(self, *_args, **_kwargs):
                return json.dumps({"relevant": True, "category": "AGG", "source_tables": ["events"]})

        chunks = [("CREATE TABLE events", ["events"])]
        original, per = agents.nx1_requests(chunks, "count events")
        contracts, calls, fallbacks = agents.nx1_retrieval_contracts(
            InvalidLLM(), chunks, "count events")
        self.assertEqual(calls, 1)
        self.assertEqual(fallbacks, 1)
        self.assertEqual(contracts, {})
        self.assertEqual(len(original), 1)
        self.assertTrue(original[0].holistic)
        self.assertEqual(original[0].text, "count events")
        self.assertEqual(per[original[0].want_name], {"events"})

    def test_nx1_retrieval_contract_requires_all_declared_operators(self):
        spec = ViewSpec(
            "degree_counts", "AGG", "SELECT department_id, COUNT(*) AS degree_count FROM degrees GROUP BY department_id",
            ["degrees"], ["department_id", "degree_count"], ["department_id"],
            provenance={"operators": ["aggregate"]})
        request = ViewRequest(
            "chunk", "AGG", ["department_id", "degree_count"], ["department_id"], {},
            "degree counts by department", required_operators=["join", "aggregate"])
        ok, reason = registry_ops.provenance_compatible(registry_ops.Match(spec), request)
        self.assertFalse(ok)
        self.assertIn("join", reason)

        spec.provenance["operators"].append("join")
        ok, reason = registry_ops.provenance_compatible(registry_ops.Match(spec), request)
        self.assertTrue(ok, reason)

    def test_registry_miss_runs_original_av_generation_prompt_unchanged(self):
        class PipelineLLM:
            def __init__(self):
                self.av_prompt = ""

            def ask(self, _system, user, tag="", **_kwargs):
                if tag == "rewrite":
                    return json.dumps({"task": "total amount per entity", "required_outputs": ["entity_id", "total"]})
                if tag == "nx1_retrieval_contract":
                    return json.dumps({
                        "relevant": True,
                        "name": "entity_totals",
                        "category": "AGG",
                        "description": "one row per entity with its total amount",
                        "required_outputs": ["events.entity_id", "total"],
                        "grain": ["events.entity_id"],
                        "view_filters": {},
                        "operators": ["aggregate"],
                        "source_tables": ["events"],
                    })
                if tag == "av_view":
                    self.av_prompt = user
                    return ('```sql\nSELECT entity_id, SUM(amount) AS total FROM events GROUP BY entity_id\n```\n'
                            '```json\n{"events":["entity_id","amount"]}\n```')
                if tag == "plan":
                    return "sum the per-entity totals"
                if tag == "compose":
                    return "```sql\nSELECT SUM(total) FROM chunk_view_0\n```"
                raise AssertionError(f"unexpected tag {tag}")

        class NoopEmbedder:
            def sim(self, *_args):
                return 0.0

        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE events(entity_id INTEGER, amount INTEGER)")
        con.executemany("INSERT INTO events VALUES (?, ?)", [(1, 5), (1, 7), (2, 3)])
        schema = datasets.render_schema(con)
        chunks = [(datasets.table_block(con, "events"), ["events"])]
        question = datasets.Question("q", "db", "What is the total amount across entities?", "")
        registry = SkillRegistry("db")
        con.execute("CREATE TABLE unrelated(note TEXT)")
        registry.add_view(ViewSpec(
            "unrelated_skill", "SEL", "SELECT note FROM unrelated", ["unrelated"],
            ["note"], ["note"], description="unrelated notes"))
        llm = PipelineLLM()

        result = realrun.answer_question(
            llm, NoopEmbedder(), registry, con, schema, chunks, None, question,
            use_memory=True, use_guard=True, tau=0.6, max_views=3,
            scorer=lambda db, sql, _q: (db.execute(sql).fetchall() == [(15,)], ""),
            architecture="nx1",
            registry_cfg=realrun.RegistryConfig(
                scope=contracts.Scope(db_id="db"), ablation=False,
                gen_tests=False, promote_final=False))

        self.assertTrue(result["correct"])
        self.assertEqual(result["architecture_route"], "nx1")
        self.assertEqual(result["retrieval_contract_calls"], 1)
        self.assertEqual(result["detailed_retrieval_requests"], 1)
        self.assertEqual(result["retrieval_contract_fallbacks"], 0)
        self.assertEqual(result["generated"], 1)
        self.assertIn("total amount per entity", llm.av_prompt)
        self.assertNotIn("Required reusable relation contract", llm.av_prompt)
        self.assertNotIn("Required operators", llm.av_prompt)
        con.close()

    def test_retrieval_snapshot_excludes_views_generated_during_question(self):
        registry = SkillRegistry("db")
        old = ViewSpec("old_view", "SEL", "SELECT 1 AS id", [], ["id"], ["id"])
        registry.add_view(old)
        frozen = realrun._retrieval_snapshot(registry)

        new = ViewSpec("same_question_view", "SEL", "SELECT 2 AS id", [], ["id"], ["id"])
        registry.add_view(new)

        self.assertEqual(set(frozen.views), {"old_view"})
        self.assertEqual(set(registry.views), {"old_view", "same_question_view"})

    def test_easy_route_generates_direct_sql_and_does_not_grow_registry(self):
        class DirectLLM:
            def ask(self, _system, user, tag="", **_kwargs):
                if tag == "rewrite":
                    return json.dumps({"task": "list event ids", "required_outputs": ["id"]})
                if tag == "difficulty":
                    return json.dumps({"difficulty": "easy",
                                       "relevant_tables": ["events_table"],
                                       "independent_grains": 1,
                                       "needs_dependent_relations": False,
                                       "operations": ["filter"], "confidence": 0.98})
                if tag == "direct":
                    self.assert_not_in_unrelated(user)
                    return "```sql\nSELECT id FROM events_table ORDER BY id\n```"
                raise AssertionError(f"unexpected direct-route tag: {tag}")

            @staticmethod
            def assert_not_in_unrelated(prompt):
                if "CREATE TABLE unrelated" in prompt:
                    raise AssertionError("easy direct route received an unrelated table")

        class NoopEmbedder:
            def sim(self, *_args):
                return 0.0

        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE events_table(id INTEGER)")
        con.execute("CREATE TABLE unrelated(note TEXT)")
        con.executemany("INSERT INTO events_table VALUES (?)", [(1,), (2,)])
        full_schema = datasets.render_schema(con)
        chunks = [
            (datasets.table_block(con, "events_table"), ["events_table"]),
            (datasets.table_block(con, "unrelated"), ["unrelated"]),
        ]
        registry = SkillRegistry("db")
        q = datasets.Question("easy", "db", "List event ids.", "")

        def scorer(db, sql, _q):
            return (db.execute(sql).fetchall() == [(1,), (2,)], "")

        result = realrun.answer_question(
            DirectLLM(), NoopEmbedder(), registry, con, full_schema, chunks, None, q,
            use_memory=True, use_guard=True, tau=0.6, max_views=3, scorer=scorer,
            architecture="auto")
        self.assertTrue(result["correct"])
        self.assertEqual(result["architecture_route"], "direct_sql")
        self.assertEqual(result["n_views"], 0)
        self.assertEqual(result["generated"], 0)
        self.assertEqual(result["reused"], 0)
        self.assertEqual(registry.n_views(), 0)
        con.close()

    def test_moderate_av_nx1_searches_registry_before_generating(self):
        class GraphLLM:
            def ask(self, _system, user, tag="", **_kwargs):
                if tag == "rewrite":
                    return json.dumps({"task": "sum event amounts", "required_outputs": ["total"]})
                if tag == "difficulty":
                    return json.dumps({"difficulty": "moderate",
                                       "relevant_tables": ["events_table"],
                                       "independent_grains": 1,
                                       "needs_dependent_relations": False,
                                       "operations": ["aggregate"], "confidence": 0.95})
                if tag == "nx1_retrieval_contract":
                    if "events_table" in user:
                        return json.dumps({
                            "relevant": True,
                            "name": "event_rows",
                            "category": "SEL",
                            "description": "event identifiers and amounts",
                            "required_outputs": ["id", "amount"],
                            "grain": ["id"],
                            "view_filters": {},
                            "operators": ["project"],
                            "source_tables": ["events_table"],
                        })
                    return json.dumps({"relevant": False})
                if tag == "av_view":
                    return "IRRELEVANT"
                if tag == "plan":
                    return "sum event_rows.amount"
                if tag == "compose":
                    return "```sql\nSELECT SUM(amount) AS total FROM event_rows\n```"
                raise AssertionError(f"unexpected registry-route tag: {tag}")

        class HitEmbedder:
            def sim(self, *_args):
                return 1.0

        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE events_table(id INTEGER, amount INTEGER)")
        con.execute("CREATE TABLE unrelated(note TEXT)")
        con.executemany("INSERT INTO events_table VALUES (?, ?)", [(1, 5), (2, 7)])
        full_schema = datasets.render_schema(con)
        chunks = [
            (datasets.table_block(con, "events_table"), ["events_table"]),
            (datasets.table_block(con, "unrelated"), ["unrelated"]),
        ]
        registry = SkillRegistry("db")
        registry.add_view(ViewSpec(
            "event_rows", "SEL", "SELECT id, amount FROM events_table", ["events_table"],
            ["id", "amount"], ["id"], description="event identifiers and amounts",
            provenance={"operators": ["project"], "lineage": ["events_table"]}))
        q = datasets.Question("moderate", "db", "What is the total event amount?", "")

        def scorer(db, sql, _q):
            return (db.execute(sql).fetchall() == [(12,)], "")

        old_policy = sqlview.get_reuse_policy()
        sqlview.set_reuse_policy("balanced")
        try:
            result = realrun.answer_question(
                GraphLLM(), HitEmbedder(), registry, con, full_schema, chunks, None, q,
                use_memory=True, use_guard=True, tau=0.6, max_views=3, scorer=scorer,
                architecture="auto")
        finally:
            sqlview.set_reuse_policy(old_policy)
        self.assertTrue(result["correct"])
        self.assertEqual(result["architecture_route"], "av_nx1_registry")
        self.assertEqual(result["reused"], 1)
        self.assertEqual(result["generated"], 0)
        self.assertEqual(result["reused_names"], ["event_rows"])
        self.assertEqual(registry.n_views(), 1)
        con.close()

    def test_moderate_question_runs_av_nx1_end_to_end(self):
        class PipelineLLM:
            def ask(self, _system, user, tag="", **_kwargs):
                if tag == "rewrite":
                    return json.dumps({"task": "sum all event amounts", "required_outputs": ["total"],
                                       "filters": [], "sort_limit": ""})
                if tag == "difficulty":
                    return json.dumps({"difficulty": "moderate",
                                       "relevant_tables": ["events_table"],
                                       "independent_grains": 1,
                                       "needs_dependent_relations": False,
                                       "operations": ["aggregate"], "confidence": 0.95})
                if tag == "av_view":
                    if "events_table" in user:
                        return ('```sql\nSELECT entity_id, amount FROM events_table\n```\n'
                                '```json\n{"output_columns":["entity_id","amount"],'
                                '"source_tables":["events_table"]}\n```')
                    return "IRRELEVANT"
                if tag == "plan":
                    return "sum chunk_view_0.amount"
                if tag == "compose":
                    return "```sql\nSELECT SUM(amount) AS total FROM chunk_view_0\n```"
                raise AssertionError(f"unexpected pipeline tag: {tag}")

        class NoopEmbedder:
            def sim(self, *_args):
                return 0.0

        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE events_table(entity_id INTEGER, amount INTEGER)")
        con.execute("CREATE TABLE entities_table(entity_id INTEGER, name TEXT)")
        con.executemany("INSERT INTO events_table VALUES (?, ?)", [(1, 5), (2, 7)])
        full_schema = datasets.render_schema(con)
        chunks = [
            (datasets.table_block(con, "events_table"), ["events_table"]),
            (datasets.table_block(con, "entities_table"), ["entities_table"]),
        ]
        q = datasets.Question("q1", "db", "What is the total event amount?", "")

        def scorer(db, sql, _q):
            return (db.execute(sql).fetchall() == [(12,)], "")

        result = realrun.answer_question(
            PipelineLLM(), NoopEmbedder(), SkillRegistry("db"), con, full_schema, chunks, None, q,
            use_memory=False, use_guard=True, tau=0.6, max_views=3, scorer=scorer,
            architecture="auto", focused_budget=1000)
        self.assertTrue(result["correct"])
        self.assertEqual(result["architecture_route"], "av_nx1_nomemory")
        self.assertEqual(result["retrieval_contract_calls"], 0)
        self.assertEqual(result["detailed_retrieval_requests"], 0)
        self.assertEqual(result["generated"], 1)
        con.close()

    def test_dependency_nxm_runs_end_to_end_without_rereading_base_table(self):
        class DagLLM:
            def ask(self, _system, user, tag="", **_kwargs):
                if tag == "rewrite":
                    return json.dumps({"task": "sum event totals", "required_outputs": ["total"]})
                if tag == "difficulty":
                    return json.dumps({"difficulty": "hard", "relevant_tables": ["events_table"],
                                       "independent_grains": 2,
                                       "needs_dependent_relations": True,
                                       "operations": ["nested_aggregation"], "confidence": 0.95})
                if tag == "decompose":
                    return json.dumps({"subgoals": [
                        {"name": "events", "category": "SEL", "description": "event rows",
                         "required_outputs": ["entity_id", "amount"], "grain": ["entity_id"],
                         "depends_on": [], "may_read_base_tables": True},
                        {"name": "entity_totals", "category": "AGG", "description": "totals",
                         "required_outputs": ["entity_id", "total"], "grain": ["entity_id"],
                         "depends_on": ["events"], "join_keys": ["entity_id"],
                         "relationship": "aggregate_input", "may_read_base_tables": False},
                    ]})
                if tag == "align":
                    return ('{"tables":["events_table"]}' if "events_table" in user
                            else '{"tables":[]}')
                if tag == "generate" and "`events`" in user:
                    return ('```sql\nSELECT entity_id, amount FROM events_table\n```\n'
                            '```json\n{"output_columns":["entity_id","amount"],'
                            '"source_tables":["events_table"],"grain":["entity_id"]}\n```')
                if tag == "generate" and "`entity_totals`" in user:
                    return ('```sql\nSELECT entity_id, SUM(amount) AS total FROM events GROUP BY entity_id\n```\n'
                            '```json\n{"output_columns":["entity_id","total"],'
                            '"source_tables":[],"grain":["entity_id"],"depends_on":[]}\n```')
                if tag == "plan":
                    return "sum entity_totals.total"
                if tag == "compose":
                    return "```sql\nSELECT SUM(total) AS total FROM entity_totals\n```"
                raise AssertionError(f"unexpected DAG tag: {tag}")

        class NoopEmbedder:
            def sim(self, *_args):
                return 0.0

        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE events_table(entity_id INTEGER, amount INTEGER)")
        con.execute("CREATE TABLE unrelated(id INTEGER)")
        con.executemany("INSERT INTO events_table VALUES (?, ?)", [(1, 5), (2, 7)])
        full_schema = datasets.render_schema(con)
        chunks = [
            (datasets.table_block(con, "events_table"), ["events_table"]),
            (datasets.table_block(con, "unrelated"), ["unrelated"]),
        ]
        q = datasets.Question("q2", "db", "What is the total event amount?", "")
        registry = SkillRegistry("db")

        def scorer(db, sql, _q):
            return (db.execute(sql).fetchall() == [(12,)], "")

        result = realrun.answer_question(
            DagLLM(), NoopEmbedder(), registry, con, full_schema, chunks, None, q,
            use_memory=False, use_guard=True, tau=0.6, max_views=3, scorer=scorer,
            architecture="auto", focused_budget=1)
        self.assertTrue(result["correct"])
        self.assertEqual(result["architecture_route"], "dependency_nxm_nomemory")
        self.assertEqual(result["generated"], 2)
        self.assertEqual(registry.views["entity_totals"].depends_on, ["events"])
        self.assertNotIn("events_table", registry.views["entity_totals"].body_sql)
        con.close()

    def test_mandatory_dependency_is_preserved_when_model_omits_metadata(self):
        class ViewLLM:
            def ask(self, *_args, **_kwargs):
                return ('```sql\nSELECT entity_id, SUM(amount) AS total FROM events '
                        'GROUP BY entity_id\n```\n'
                        '```json\n{"output_columns":["entity_id","total"],'
                        '"source_tables":[],"grain":["entity_id"],"depends_on":[]}\n```')

        dep = ViewSpec("events", "SEL", "SELECT 1 AS entity_id, 2 AS amount", [],
                       ["entity_id", "amount"], ["entity_id"])
        req = ViewRequest("totals", "AGG", ["entity_id", "total"], ["entity_id"], {},
                          "totals", depends_on=["events"], may_read_base_tables=False)
        spec = agents.generate_view(ViewLLM(), "schema", req, [dep])
        self.assertEqual(spec.depends_on, ["events"])

    def test_decomposer_keeps_only_earlier_dependencies(self):
        class CyclicLLM:
            def ask(self, *_args, **_kwargs):
                return json.dumps({"subgoals": [
                    {"name": "first", "category": "SEL", "description": "first",
                     "depends_on": ["second", "first"]},
                    {"name": "second", "category": "AGG", "description": "second",
                     "depends_on": ["first"], "may_read_base_tables": "false"},
                ]})

        reqs = agents.decompose_subgoals(CyclicLLM(), "", "question")
        self.assertEqual(reqs[0].depends_on, [])
        self.assertEqual(reqs[1].depends_on, ["first"])
        self.assertFalse(reqs[1].may_read_base_tables)

    def test_hard_semantic_signals_override_an_easy_label(self):
        class MislabelledLLM:
            def ask(self, *_args, **_kwargs):
                return json.dumps({"difficulty": "easy", "relevant_tables": ["ratings"],
                                   "independent_grains": 2,
                                   "needs_dependent_relations": True,
                                   "operations": ["ratio"], "confidence": 0.99})

        decision = agents.classify_question_difficulty(
            MislabelledLLM(), "percentage of paying raters", ["ratings", "users"])
        self.assertEqual(decision["difficulty"], "hard")

    def test_easy_question_routes_to_direct_sql_without_views(self):
        llm = FakeLLM("easy")
        result = agents.adaptive_requests(
            llm, [("CREATE TABLE events_table", ["events_table"])], "rewritten question",
            "events_table",
            render_selected=lambda tables: " ".join(sorted(tables)),
            estimate_tokens=len, focused_budget=100)
        reqs, per, route, selected, calls = result
        self.assertEqual(route, "direct_sql")
        self.assertEqual(calls, 0)
        self.assertEqual(llm.calls, ["difficulty"])
        self.assertEqual(reqs, [])
        self.assertEqual(per, {})
        self.assertEqual(selected, {"events_table"})

    def test_moderate_question_uses_av_nx1_for_every_chunk(self):
        llm = FakeLLM("moderate")
        chunks = [
            ("CREATE TABLE events_table", ["events_table"]),
            ("CREATE TABLE entities_table", ["entities_table"]),
        ]
        reqs, per, route, selected, calls = agents.adaptive_requests(
            llm, chunks, "rewritten question", "events_table, entities_table",
            render_selected=lambda tables: " ".join(sorted(tables)),
            estimate_tokens=len, focused_budget=1000, tag_prefix="t_")
        self.assertEqual(route, "av_nx1")
        self.assertEqual(calls, 0)
        self.assertEqual(llm.calls, ["t_difficulty"])
        self.assertEqual(selected, {"events_table", "entities_table"})
        self.assertEqual(len(reqs), 2)
        self.assertTrue(all(r.holistic for r in reqs))
        self.assertEqual(per["chunk_view_0"], {"events_table"})
        self.assertEqual(per["chunk_view_1"], {"entities_table"})

    def test_hard_question_uses_dependency_nxm(self):
        llm = FakeLLM("hard")
        chunks = [
            ("CREATE TABLE events_table", ["events_table"]),
            ("CREATE TABLE entities_table", ["entities_table"]),
        ]
        reqs, _per, route, _selected, _calls = agents.adaptive_requests(
            llm, chunks, "rewritten question", "events_table, entities_table",
            render_selected=lambda _tables: "x" * 100,
            estimate_tokens=len, focused_budget=10, tag_prefix="t_")
        self.assertEqual(route, "dependency_nxm")
        self.assertEqual([r.want_name for r in reqs], ["events", "entity_totals"])
        self.assertEqual(reqs[1].depends_on, ["events"])
        self.assertEqual(reqs[1].join_keys, ["entity_id"])
        self.assertEqual(reqs[1].relationship, "aggregate_input")
        self.assertFalse(reqs[1].may_read_base_tables)


if __name__ == "__main__":
    unittest.main()
