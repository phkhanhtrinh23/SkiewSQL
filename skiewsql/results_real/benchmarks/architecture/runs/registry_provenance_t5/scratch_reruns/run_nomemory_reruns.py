"""Answer chosen Spider questions WITHOUT memory (generate every view from scratch), same settings as the
best registry run: gpt-5-mini, N×1, chunk budget 1000, T_max=5 for views and SQL repair, value linking on."""
import json, sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../..")))
os.environ.setdefault("SKIEW_LLM_PROVIDER", "openai")
from skiewsql import realrun, datasets, contracts, agents
from skiewsql.core import SkillRegistry
from skiewsql.llm import LLM, Embedder, USAGE

realrun.VIEW_VALIDATE_ATTEMPTS = 5
realrun.SQL_REPAIR_ATTEMPTS = 5
qs, _, root = datasets.load_spider("dev")
Q = {q.qid: q for q in qs}
db = "student_transcripts_tracking"
path = datasets.db_path(root, db, "spider")
con = datasets.connect(path)
full_schema, chunks, vindex = realrun._prep_db(con, db, path, no_valuelink=False, chunk_budget=1000)
llm, emb = LLM(model="gpt-5-mini"), Embedder()
reg = realrun.RegistryConfig(scope=contracts.make_scope(con, db, model="gpt-5-mini", prompt_version=agents.PROMPT_VERSION))
scorer = lambda c, sql, q: datasets.ex_match(c, sql, q.gold_sql)
out = []
for qid in sys.argv[2:]:
    for rep in range(int(sys.argv[1])):
        USAGE.reset()
        graph = SkillRegistry(db)
        r = realrun.answer_question(llm, emb, graph, con, full_schema, chunks, vindex, Q[qid], use_memory=False,
                                    use_guard=True, tau=0.6, max_views=3, scorer=scorer, architecture="nx1",
                                    registry_cfg=reg)
        r.pop("_learn", None)
        snap = USAGE.snapshot()
        out.append({"qid": qid, "rep": rep, "correct": r["correct"], "tokens": snap["total_tokens"],
                    "calls": sum(v["calls"] for v in snap["by_tag"].values()), "by_tag": snap["by_tag"],
                    "generated": r["generated"], "pred_sql": r["pred_sql"], "error": r["error"],
                    "views": {n: v.body_sql for n, v in graph.views.items()}, "n_repairs": r.get("n_repairs")})
        print(qid, rep, "correct", r["correct"], "tok", snap["total_tokens"], "gen", r["generated"], flush=True)
json.dump(out, open(os.path.join(os.path.dirname(__file__), "scratch_runs.json"), "w"), indent=1)
