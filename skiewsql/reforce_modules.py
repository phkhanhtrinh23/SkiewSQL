"""reforce_modules.py — 1:1 replication of two ReFoRCE modules (Snowflake-Labs/ReFoRCE, arXiv 2502.00675):
* FORMAT RESTRICTION  (prompt.get_format_prompt + agent.format_answer) Before any SQL exists, a DEDICATED call asks the model for the answer's table shape as a
        ```csv``` header (column names, no rows, SQL explicitly forbidden). Only the FIRST LINE of
        the reply is kept — that header becomes the output contract the SQL must satisfy.
        This is why it works where an in-prompt instruction fails: the shape is fixed *before*
        generation instead of being pleaded for *during* it.

  * ITERATIVE COLUMN EXPLORATION  (prompt.get_exploration_prompt + agent.exploration/execute_sqls)
        The model writes <=10 simple SELECT DISTINCT probes, they are EXECUTED against the live DB,
        and the (sql, result) pairs are fed back as `pre_info`. The agent therefore chooses columns
        from observed VALUES, not from DDL names alone — the fix for a `*_CODE` vs `*_NAME` mix-up.

Ported verbatim from the reference implementation (prompt strings, <=10 queries, >=3 required,
max_try=3, 500-char result cap, 1e5 pre_info cap, self-correction on error), with a `mysql` dialect
added to the three dialect helpers, which upstream defines only for snowflake/bigquery/sqlite."""
from __future__ import annotations

import re
from typing import List, Tuple

from skiewsql.prompt_loader import load_prompt

MAX_TRY = 3              # agent.py: self.max_try
CSV_MAX_LEN = 500        # agent.py: self.csv_max_len — per-result character cap
MAX_EXPLORE_RESULTS = 10 # execute_sqls: break once >10 results collected
PRE_INFO_CAP = int(1e5)  # exploration(): retry if pre_info exceeds 1e5 chars


# --------------------------------------------------------------------------- #
# Dialect helpers (prompt.py) — mysql added for BEAVER
# --------------------------------------------------------------------------- #
def get_prompt_dialect_basic(api: str) -> str:
    if api not in {"snowflake", "bigquery", "sqlite", "mysql"}:
        raise NotImplementedError("Unsupported API.")
    return load_prompt(f"reforce_modules/dialect_basic_{api}.txt")


def get_prompt_dialect_nested(api: str) -> str:
    if api not in {"snowflake", "bigquery", "sqlite", "mysql"}:
        return ""
    return load_prompt(f"reforce_modules/dialect_nested_{api}.txt")


def get_prompt_dialect_string_matching(api: str) -> str:
    if api not in {"snowflake", "bigquery", "sqlite", "mysql"}:
        return ""
    return load_prompt(f"reforce_modules/string_matching_{api}.txt")


# --------------------------------------------------------------------------- #
# FORMAT RESTRICTION  (prompt.get_format_prompt / agent.format_answer)
# --------------------------------------------------------------------------- #
def get_format_prompt() -> str:
    return load_prompt("reforce_modules/format_instructions.txt")


def _extract_block(txt: str, lang: str) -> str:
    m = re.findall(rf"```{lang}\s*(.*?)```", txt or "", re.S)
    if m:
        return m[0].strip()
    m = re.findall(r"```\s*(.*?)```", txt or "", re.S)
    return m[0].strip() if m else (txt or "").strip()


def format_answer(llm, task: str, tag: str = "reforce_format") -> str:
    """agent.format_answer: one dedicated call, SQL forbidden, keep ONLY the first line (the header)."""
    try:
        txt = llm.ask(load_prompt("reforce_modules/format_sys.txt"),
                      load_prompt("reforce_modules/format_user.txt").format(
                          task=task, instructions=get_format_prompt()),
                      tag=tag, max_tokens=400)
        csv = _extract_block(txt, "csv")
        first = csv.split("\n")[0].strip()
        return f"```csv\n{first}\n```" if first else ""
    except Exception:  # noqa: BLE001
        return ""


# --------------------------------------------------------------------------- #
# ITERATIVE COLUMN EXPLORATION  (prompt.get_exploration_prompt / agent.exploration)
# --------------------------------------------------------------------------- #
def get_exploration_prompt(api: str, table_struct=None) -> str:
    return load_prompt("reforce_modules/exploration_instructions.txt").format(
        api=api, dialect_basic=get_prompt_dialect_basic(api),
        dialect_nested=get_prompt_dialect_nested(api))


def _extract_sqls(txt: str) -> List[str]:
    blocks = re.findall(r"```sql\s*(.*?)```", txt or "", re.S)
    if not blocks:
        return []
    if len(blocks) == 1:                       # agent.split_sql: one block may hold several queries
        parts = [s.strip() for s in blocks[0].split(";") if s.strip()]
        return parts if len(parts) > 1 else [blocks[0].strip()]
    return [b.strip() for b in blocks]


def exploration(llm, run_sql, task: str, table_info: str, api: str = "mysql",
                tag: str = "reforce_explore") -> Tuple[str, int]:
    """agent.exploration: ask for <=10 probes, EXECUTE them, accumulate `pre_info` = (sql, result) pairs. Requires >=3 queries. Retries up to max_try. Caps each result at CSV_MAX_LEN chars and the whole pre_info at 1e5. `run_sql(sql) -> str` executes and returns a printable result (or raises). Returns (pre_info, n_executed)."""
    pre_info, n_ok, max_try = "", 0, MAX_TRY
    base = load_prompt("reforce_modules/exploration_user.txt").format(
        table_info=table_info, task=task, instructions=get_exploration_prompt(api))
    while max_try > 0:
        pre_info, n_ok = "", 0
        try:
            txt = llm.ask(load_prompt("reforce_modules/exploration_sys.txt"),
                          base, tag=tag, max_tokens=1200)
        except Exception:  # noqa: BLE001
            break
        sqls = _extract_sqls(txt)[:10]
        if len(sqls) < 3:                       # agent.py: "Few sqls, retry preparation."
            max_try -= 1
            continue
        for sql in sqls:
            if n_ok >= MAX_EXPLORE_RESULTS:
                break
            try:
                res = str(run_sql(sql))[:CSV_MAX_LEN]
                pre_info += f"Query:\n{sql}\nAnswer:\n{res}\n"
                n_ok += 1
            except Exception as e:              # self-correct once, as execute_sqls does
                try:
                    fix = llm.ask(load_prompt("reforce_modules/fix_sys.txt"),
                                  load_prompt("reforce_modules/fix_user.txt").format(
                                      sql=sql, error=str(e)[:300]),
                                  tag=tag + "_fix", max_tokens=500)
                    cand = _extract_sqls(fix)
                    if cand:
                        res = str(run_sql(max(cand, key=len)))[:CSV_MAX_LEN]
                        pre_info += f"Query:\n{max(cand, key=len)}\nAnswer:\n{res}\n"
                        n_ok += 1
                except Exception:  # noqa: BLE001
                    continue
        if n_ok == 0:                           # "Inadequate preparation, break."
            break
        if len(pre_info) < PRE_INFO_CAP:
            break
        max_try -= 1                            # "Too long, retry preparation."
    return pre_info, n_ok
