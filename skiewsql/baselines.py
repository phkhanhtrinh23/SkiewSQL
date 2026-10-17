"""Faithful re-implementations of four Text-to-SQL baselines on SkiewSQL's shared infra (LLM client, per-benchmark schema / executor / scorer). Each `method(llm, schema, question, evidence, api, ...)` returns a single predicted SQL string (or None). They reuse the *same* schema string, dialect (`api`), executor and scorer as configs A/S, so results are directly comparable.
- DIN-SQL   (Pourreza & Rafiei, 2023): schema-link -> difficulty-classify -> decompose -> self-correct
- DAIL-SQL  (Gao et al., 2023):        masked-question example selection + code-repr few-shot + self-consistency
- CHESS     (Talaei et al., 2024):     keyword IR -> schema selection -> candidate gen -> execution-based revise
- ReFoRCE   (2025):                    format restriction -> column exploration -> generate -> self-refine (majority)"""
from __future__ import annotations
from collections import Counter
from typing import Callable, List, Optional, Tuple

from skiewsql.llm import LLM, extract_code
from skiewsql import reforce_modules
from skiewsql.prompt_loader import load_prompt

DIN_LINK_SYS = load_prompt("baselines/din_link_sys.txt")
DIN_LINK_USER = load_prompt("baselines/din_link_user.txt")
DIN_CLASS_SYS = load_prompt("baselines/din_class_sys.txt")
DIN_CLASS_USER = load_prompt("baselines/din_class_user.txt")
DIN_DECOMP_SYS = load_prompt("baselines/din_decomp_sys.txt")
DIN_DECOMP_USER = load_prompt("baselines/din_decomp_user.txt")
DIN_GEN_NESTED_SYS = load_prompt("baselines/din_gen_nested_sys.txt")
DIN_GEN_NESTED_USER = load_prompt("baselines/din_gen_nested_user.txt")
DIN_GEN_SYS = load_prompt("baselines/din_gen_sys.txt")
DIN_GEN_USER = load_prompt("baselines/din_gen_user.txt")
DIN_CORRECT_SYS = load_prompt("baselines/din_correct_sys.txt")
DIN_CORRECT_USER = load_prompt("baselines/din_correct_user.txt")
DAIL_SYS = load_prompt("baselines/dail_sys.txt")
DAIL_USER = load_prompt("baselines/dail_user.txt")
CHESS_IR_SYS = load_prompt("baselines/chess_ir_sys.txt")
CHESS_IR_USER = load_prompt("baselines/chess_ir_user.txt")
CHESS_SELECT_SYS = load_prompt("baselines/chess_select_sys.txt")
CHESS_SELECT_USER = load_prompt("baselines/chess_select_user.txt")
CHESS_GEN_SYS = load_prompt("baselines/chess_gen_sys.txt")
CHESS_GEN_USER = load_prompt("baselines/chess_gen_user.txt")
CHESS_UNIT_SYS = load_prompt("baselines/chess_unit_sys.txt")
CHESS_UNIT_USER = load_prompt("baselines/chess_unit_user.txt")
CHESS_REVISE_SYS = load_prompt("baselines/chess_revise_sys.txt")
CHESS_REVISE_USER = load_prompt("baselines/chess_revise_user.txt")
REFORCE_SYS = load_prompt("baselines/reforce_sys.txt")
REFORCE_USER = load_prompt("baselines/reforce_user.txt")

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
        DIN_LINK_SYS,
        DIN_LINK_USER.format(dialect=d, schema=schema, question=question, evidence=ev),
        tag="din_link", max_tokens=400) or ""
    # 2) difficulty classification
    cls = (llm.ask(
        DIN_CLASS_SYS,
        DIN_CLASS_USER.format(dialect=d, links=link, question=question),
        tag="din_class", max_tokens=10) or "").upper()
    cls = "NESTED" if "NEST" in cls and "NON" not in cls else ("NON-NESTED" if "NON" in cls else ("EASY" if "EASY" in cls else "NON-NESTED"))
    # 3) generation conditioned on class
    if cls == "NESTED":
        subq = llm.ask(
            DIN_DECOMP_SYS,
            DIN_DECOMP_USER.format(dialect=d, links=link, question=question, evidence=ev),
            tag="din_decomp", max_tokens=400) or ""
        gen = llm.ask(
            DIN_GEN_NESTED_SYS,
            DIN_GEN_NESTED_USER.format(dialect=d, schema=schema, links=link,
                                       subquestions=subq, question=question, evidence=ev),
            tag="din_gen_nested", max_tokens=1400)
    else:
        gen = llm.ask(
            DIN_GEN_SYS,
            DIN_GEN_USER.format(dialect=d, schema=schema, links=link, difficulty=cls,
                                question=question, evidence=ev), tag="din_gen", max_tokens=1200)
    sql = _sql(gen)
    # 4) self-correction (execute-aware if we have an executor)
    ok, err, _ = _exec_ok(executor, sql)
    corr = llm.ask(
        DIN_CORRECT_SYS,
        DIN_CORRECT_USER.format(dialect=d, schema=schema, question=question, evidence=ev,
                                sql=sql, error=("Execution error: " + err) if (sql and not ok) else ""),
        tag="din_correct", max_tokens=1200)
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
    user = DAIL_USER.format(dialect=d, schema=schema,
                            examples=("Solved examples:" + shots) if shots else "",
                            question=question, evidence=ev)
    # self-consistency: sample a few, vote by execution-result signature (fallback: normalized SQL)
    cands = []
    for j in range(max(1, self_consistency)):
        g = _sql(llm.ask(DAIL_SYS, user, tag="dail_gen", temperature=(0.0 if j == 0 else 0.5), max_tokens=1200))
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
    kw = llm.ask(CHESS_IR_SYS, CHESS_IR_USER.format(question=question, evidence=ev),
                 tag="chess_ir", max_tokens=200) or ""
    # SS: schema selection -> keep only relevant tables (agent prunes the schema)
    sel = llm.ask(
        CHESS_SELECT_SYS,
        CHESS_SELECT_USER.format(dialect=d, schema=schema, keywords=kw, question=question), tag="chess_ss",
        max_tokens=1200) or schema
    pruned = sel if "CREATE" in sel.upper() else schema
    # CG: candidate generation
    gen = llm.ask(
        CHESS_GEN_SYS,
        CHESS_GEN_USER.format(dialect=d, schema=pruned, question=question, evidence=ev),
        tag="chess_cg", max_tokens=1400)
    sql = _sql(gen)
    # UT: execution-based unit test + revision loop
    for _ in range(max_revise):
        ok, err, df = _exec_ok(executor, sql)
        if ok:
            # a light "unit test": ask the agent if the result plausibly answers the question
            verdict = (llm.ask(
                CHESS_UNIT_SYS,
                CHESS_UNIT_USER.format(dialect=d, question=question, sql=sql,
                                       result=str(getattr(df, 'head', lambda n: df)(3))[:400]),
                tag="chess_ut", max_tokens=120) or "YES").upper()
            if verdict.startswith("YES"):
                return sql
            fix_hint = verdict
        else:
            fix_hint = f"Execution error: {err}"
        rev = llm.ask(
            CHESS_REVISE_SYS,
            CHESS_REVISE_USER.format(dialect=d, schema=pruned, question=question,
                                     evidence=ev, sql=sql, feedback=fix_hint),
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
    base_user = REFORCE_USER.format(dialect=d, schema=schema, answer_format=fmt_txt,
                                    exploration=explore, question=question, evidence=ev, feedback="")
    # 3) generate + self-refine (execution repair), a few votes
    cands = []
    for j in range(max(1, votes)):
        sql = _sql(llm.ask(REFORCE_SYS, base_user, tag="reforce_gen", temperature=(0.0 if j == 0 else 0.5), max_tokens=1400))
        for _ in range(max_revise):
            ok, err, _df = _exec_ok(executor, sql)
            if ok or not sql:
                break
            repair_user = REFORCE_USER.format(dialect=d, schema=schema, answer_format=fmt_txt,
                                              exploration=explore, question=question, evidence=ev,
                                              feedback=f"\nPrevious SQL failed: {err}\nFix it.")
            sql = _sql(llm.ask(REFORCE_SYS, repair_user,
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
