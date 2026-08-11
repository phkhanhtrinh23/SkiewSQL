"""Faithful re-implementations of four Text-to-SQL baselines on SkiewSQL's shared infra (LLM client,
per-benchmark schema / executor / scorer). Each `method(llm, schema, question, evidence, api, ...)`
returns a single predicted SQL string (or None). They reuse the *same* schema string, dialect (`api`),
executor and scorer as configs A/S, so results are directly comparable.

- DIN-SQL   (Pourreza & Rafiei, 2023): schema-link -> difficulty-classify -> decompose -> self-correct
- DAIL-SQL  (Gao et al., 2023):        masked-question example selection + code-repr few-shot + self-consistency
- CHESS     (Talaei et al., 2024):     keyword IR -> schema selection -> candidate gen -> execution-based revise
- ReFoRCE   (2025):                    format restriction -> column exploration -> generate -> self-refine (majority)
"""
from __future__ import annotations
from collections import Counter
from typing import Callable, List, Optional, Tuple

from skiewsql.llm import LLM, extract_code
from skiewsql import reforce_modules

Executor = Callable[[str], Tuple[object, str]]   # sql -> (df_or_none, err_str)


def _sql(txt: Optional[str]) -> Optional[str]:
    if not txt:
        return None
    code = extract_code(txt, langs=("sql", "cte"))
    if code:
        return code.strip().rstrip(";")
    # bare SELECT with no fence
    for kw in ("WITH ", "SELECT "):
        i = txt.upper().find(kw)
        if i >= 0:
            return txt[i:].strip().rstrip(";")
    return None


def _ev(evidence: str) -> str:
    return f"\nExternal knowledge: {evidence}" if (evidence or "").strip() else ""


def _exec_ok(executor: Optional[Executor], sql: Optional[str]) -> Tuple[bool, str, object]:
    if not executor or not sql:
        return False, "no executor/sql", None
    df, err = executor(sql)
    return (err == "" and df is not None), err, df


# --------------------------------------------------------------------------- #
# DIN-SQL
# --------------------------------------------------------------------------- #
def din_sql(llm: LLM, schema: str, question: str, evidence: str, api: str = "sqlite",
            executor: Optional[Executor] = None, **_) -> Optional[str]:
    d = f"Dialect: {api}."
    ev = _ev(evidence)
    # 1) schema linking
    link = llm.ask(
        "You are a schema-linking module for Text-to-SQL. List ONLY the tables and columns from the "
        "schema that are needed, and the literal condition values. Be exhaustive but minimal.",
        f"{d}\nSchema:\n{schema}\n\nQuestion: {question}{ev}\n\nReturn: \nTables/columns: ...\nConditions: ...",
        tag="din_link", max_tokens=400) or ""
    # 2) difficulty classification
    cls = (llm.ask(
        "Classify the SQL difficulty of the question given the schema links. Answer with exactly one "
        "word: EASY (single table, no join), NON-NESTED (joins but no sub-query), or NESTED (needs "
        "sub-queries / set-ops / grouping-with-having-over-aggregate).",
        f"{d}\nSchema links:\n{link}\n\nQuestion: {question}", tag="din_class", max_tokens=10) or "").upper()
    cls = "NESTED" if "NEST" in cls and "NON" not in cls else ("NON-NESTED" if "NON" in cls else ("EASY" if "EASY" in cls else "NON-NESTED"))
    # 3) generation conditioned on class
    if cls == "NESTED":
        subq = llm.ask(
            "Decompose the question into the minimal ordered list of intermediate sub-questions whose "
            "answers combine into the final query. One per line.",
            f"{d}\nSchema links:\n{link}\n\nQuestion: {question}{ev}", tag="din_decomp", max_tokens=400) or ""
        gen = llm.ask(
            "You are a Text-to-SQL generator. Using the schema links and the sub-questions, write ONE "
            "final SQL query. Think step by step, then output the SQL in a ```sql block.",
            f"{d}\nSchema:\n{schema}\n\nSchema links:\n{link}\n\nSub-questions:\n{subq}\n\n"
            f"Question: {question}{ev}", tag="din_gen_nested", max_tokens=1400)
    else:
        gen = llm.ask(
            "You are a Text-to-SQL generator. Using the schema links, write ONE SQL query. Reason "
            "briefly, then output the SQL in a ```sql block.",
            f"{d}\nSchema:\n{schema}\n\nSchema links:\n{link}\n\nDifficulty: {cls}\n\n"
            f"Question: {question}{ev}", tag="din_gen", max_tokens=1200)
    sql = _sql(gen)
    # 4) self-correction (execute-aware if we have an executor)
    ok, err, _ = _exec_ok(executor, sql)
    corr = llm.ask(
        "You are a SQL self-correction module. Fix bugs (wrong/ambiguous columns, missing joins, "
        "GROUP BY errors, dialect issues). If the query is already correct, return it unchanged. "
        "Output only the SQL in a ```sql block.",
        f"{d}\nSchema:\n{schema}\n\nQuestion: {question}{ev}\n\nSQL:\n{sql}\n"
        f"{('Execution error: ' + err) if (sql and not ok) else ''}", tag="din_correct", max_tokens=1200)
    return _sql(corr) or sql


# --------------------------------------------------------------------------- #
# DAIL-SQL
# --------------------------------------------------------------------------- #
def dail_sql(llm: LLM, schema: str, question: str, evidence: str, api: str = "sqlite",
             executor: Optional[Executor] = None, examples: Optional[List[Tuple[str, str]]] = None,
             self_consistency: int = 3, **_) -> Optional[str]:
    d = f"Dialect: {api}."
    ev = _ev(evidence)
    shots = ""
    for i, (q, s) in enumerate(examples or [], 1):
        shots += f"\n-- Example {i}\nQuestion: {q}\n```sql\n{s}\n```\n"
    sys = ("You are a Text-to-SQL model. Given the schema (as CREATE TABLE statements) and a few "
           "solved examples from the same database, write ONE SQL query for the target question. "
           "Output only the SQL in a ```sql block.")
    user = f"{d}\nSchema:\n{schema}\n{('Solved examples:'+shots) if shots else ''}\n\nTarget question: {question}{ev}"
    # self-consistency: sample a few, vote by execution-result signature (fallback: normalized SQL)
    cands = []
    for j in range(max(1, self_consistency)):
        g = _sql(llm.ask(sys, user, tag="dail_gen", temperature=(0.0 if j == 0 else 0.5), max_tokens=1200))
        if g:
            cands.append(g)
    if not cands:
        return None
    if executor is None or len(cands) == 1:
        return cands[0]
    # vote: group candidates by (executes, first-rows signature)
    sig_map = {}
    for c in cands:
        df, err = executor(c)
        if err == "" and df is not None:
            try:
                sig = str(df.head(5).values.tolist())
            except Exception:
                sig = "ok"
        else:
            sig = f"ERR"
        sig_map.setdefault(sig, []).append(c)
    # pick the largest group that executed (prefer non-ERR)
    good = {k: v for k, v in sig_map.items() if k != "ERR"}
    pool = good or sig_map
    best_sig = max(pool, key=lambda k: len(pool[k]))
    return pool[best_sig][0]


# --------------------------------------------------------------------------- #
# CHESS
# --------------------------------------------------------------------------- #
def chess(llm: LLM, schema: str, question: str, evidence: str, api: str = "sqlite",
          executor: Optional[Executor] = None, max_revise: int = 3, **_) -> Optional[str]:
    d = f"Dialect: {api}."
    ev = _ev(evidence)
    # IR: keywords
    kw = llm.ask("Extract the key entities, columns and literal values mentioned or implied by the "
                 "question (comma-separated).", f"Question: {question}{ev}", tag="chess_ir", max_tokens=200) or ""
    # SS: schema selection -> keep only relevant tables (agent prunes the schema)
    sel = llm.ask(
        "You are a schema-selection agent. Given the full schema and the keywords, list the tables "
        "(and their key columns) actually needed. Output a compact pruned schema as CREATE TABLE "
        "statements, dropping irrelevant tables/columns but keeping join keys.",
        f"{d}\nFull schema:\n{schema}\n\nKeywords: {kw}\n\nQuestion: {question}", tag="chess_ss",
        max_tokens=1200) or schema
    pruned = sel if "CREATE" in sel.upper() else schema
    # CG: candidate generation
    gen = llm.ask(
        "You are a SQL candidate-generation agent. Using the pruned schema, write ONE SQL query. "
        "Reason briefly, then output the SQL in a ```sql block.",
        f"{d}\nPruned schema:\n{pruned}\n\nQuestion: {question}{ev}", tag="chess_cg", max_tokens=1400)
    sql = _sql(gen)
    # UT: execution-based unit test + revision loop
    for _ in range(max_revise):
        ok, err, df = _exec_ok(executor, sql)
        if ok:
            # a light "unit test": ask the agent if the result plausibly answers the question
            verdict = (llm.ask(
                "You are a unit-testing agent. Given the query and a preview of its result, answer YES "
                "if it plausibly answers the question, otherwise NO plus the single biggest flaw.",
                f"{d}\nQuestion: {question}\nSQL:\n{sql}\nResult preview: {str(getattr(df,'head',lambda n: df)(3))[:400]}",
                tag="chess_ut", max_tokens=120) or "YES").upper()
            if verdict.startswith("YES"):
                return sql
            fix_hint = verdict
        else:
            fix_hint = f"Execution error: {err}"
        rev = llm.ask(
            "You are a revision agent. Fix the SQL given the feedback. Output only the SQL in a ```sql block.",
            f"{d}\nPruned schema:\n{pruned}\n\nQuestion: {question}{ev}\nSQL:\n{sql}\nFeedback: {fix_hint}",
            tag="chess_rev", max_tokens=1400)
        nxt = _sql(rev)
        if not nxt or nxt == sql:
            break
        sql = nxt
    return sql


# --------------------------------------------------------------------------- #
# ReFoRCE (standalone — full pipeline, no view-memory / no N×M)
# --------------------------------------------------------------------------- #
def reforce(llm: LLM, schema: str, question: str, evidence: str, api: str = "sqlite",
            executor: Optional[Executor] = None, run_sql: Optional[Callable] = None,
            votes: int = 3, max_revise: int = 2, **_) -> Optional[str]:
    d = f"Dialect: {api}."
    ev = _ev(evidence)
    # 1) format restriction
    fmt = reforce_modules.format_answer(llm, question)
    fmt_txt = ("\nREQUIRED ANSWER FORMAT (exactly these columns, in order):\n" + fmt + "\n") if fmt else ""
    # 2) column exploration (uses the live DB via run_sql if available)
    explore = ""
    if run_sql is not None:
        pre, _n = reforce_modules.exploration(llm, run_sql, question, schema[:6000], api=api)
        if pre:
            explore = "\nColumn exploration — observed VALUES:\n" + pre[:4000] + "\n"
    sys = ("You are the ReFoRCE Text-to-SQL generator. Use the observed column values and the required "
           "answer format. Output only the SQL in a ```sql block.")
    base_user = f"{d}\nSchema:\n{schema}\n{fmt_txt}{explore}\nQuestion: {question}{ev}"
    # 3) generate + self-refine (execution repair), a few votes
    cands = []
    for j in range(max(1, votes)):
        sql = _sql(llm.ask(sys, base_user, tag="reforce_gen", temperature=(0.0 if j == 0 else 0.5), max_tokens=1400))
        for _ in range(max_revise):
            ok, err, _df = _exec_ok(executor, sql)
            if ok or not sql:
                break
            sql = _sql(llm.ask(sys, base_user + f"\nPrevious SQL failed: {err}\nFix it.",
                               tag="reforce_refine", max_tokens=1400)) or sql
        if sql:
            cands.append(sql)
    if not cands:
        return None
    if executor is None or len(cands) == 1:
        return cands[0]
    sig = {}
    for c in cands:
        df, err = executor(c)
        k = (str(df.head(5).values.tolist()) if (err == "" and df is not None) else "ERR")
        sig.setdefault(k, []).append(c)
    good = {k: v for k, v in sig.items() if k != "ERR"} or sig
    return good[max(good, key=lambda k: len(good[k]))][0]


METHODS = {"din": din_sql, "dail": dail_sql, "chess": chess, "reforce": reforce}
