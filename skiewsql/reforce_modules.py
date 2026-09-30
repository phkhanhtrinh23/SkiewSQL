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

MAX_TRY = 3              # agent.py: self.max_try
CSV_MAX_LEN = 500        # agent.py: self.csv_max_len — per-result character cap
MAX_EXPLORE_RESULTS = 10 # execute_sqls: break once >10 results collected
PRE_INFO_CAP = int(1e5)  # exploration(): retry if pre_info exceeds 1e5 chars


# --------------------------------------------------------------------------- #
# Dialect helpers (prompt.py) — mysql added for BEAVER
# --------------------------------------------------------------------------- #
def get_prompt_dialect_basic(api: str) -> str:
    if api == "snowflake":
        return ("```sql\nSELECT \"COLUMN_NAME\" FROM DATABASE.SCHEMA.TABLE WHERE ... ``` (Adjust "
                "\"DATABASE\", \"SCHEMA\", and \"TABLE\" to match actual names, ensure all column "
                "names are enclosed in double quotations)")
    elif api == "bigquery":
        return ("```sql\nSELECT `column_name` FROM `database.schema.table` WHERE ... ``` (Replace "
                "`database`, `schema`, and `table` with actual names. Enclose column names and table "
                "identifiers with backticks.)")
    elif api == "sqlite":
        return ("```sql\nSELECT DISTINCT \"column_name\" FROM \"table_name\" WHERE ... ``` (Replace "
                "\"table_name\" with the actual table name. Enclose table and column names with double "
                "quotations if they contain special characters or match reserved keywords.)")
    elif api == "mysql":
        return ("```sql\nSELECT DISTINCT `column_name` FROM `table_name` WHERE ... ``` (Replace "
                "`table_name` with the actual table name. Enclose table and column names with "
                "backticks if they contain special characters or match reserved keywords.)")
    raise NotImplementedError("Unsupported API.")


def get_prompt_dialect_nested(api: str) -> str:
    if api == "snowflake":
        return ("For columns in json nested format: e.g. SELECT t.\"column_name\", f.value::VARIANT:"
                "\"key_name\"::STRING AS \"abstract_text\" FROM PATENTS.PATENTS.PUBLICATIONS t, "
                "LATERAL FLATTEN(input => t.\"json_column_name\") f; DO NOT directly answer the task "
                "and ensure all column names are enclosed in double quotations. For nested columns "
                "like event_params, when you don't know the structure of it, first watch the whole "
                "column: SELECT f.value FROM table, LATERAL FLATTEN(input => t.\"event_params\") f;\n")
    elif api == "bigquery":
        return ("Extract a specific key from a nested JSON column: SELECT t.\"column_name\", "
                "JSON_EXTRACT_SCALAR(f.value, \"$.key_name\") AS \"abstract_text\" FROM "
                "`database.schema.table` AS t, UNNEST(JSON_EXTRACT_ARRAY(t.\"json_column_name\")) AS "
                "f;\nWhen the structure of the nested column (e.g., event_params) is unknown, first "
                "inspect the whole column: SELECT f.value FROM `project.dataset.table` AS t, "
                "UNNEST(JSON_EXTRACT_ARRAY(t.\"event_params\")) AS f;\n")
    elif api == "sqlite":
        return ("Extract a specific key from a nested JSON column: SELECT t.\"column_name\", "
                "json_extract(f.value, '$.key_name') AS \"abstract_text\" FROM \"table_name\" AS t, "
                "json_each(t.\"json_column_name\") AS f;\nWhen the structure of the nested column "
                "(e.g., event_params) is unknown, first inspect the whole column: SELECT f.value FROM "
                "\"table_name\" AS t, json_each(t.\"event_params\") AS f;\n")
    elif api == "mysql":
        return ("Extract a specific key from a nested JSON column: SELECT t.`column_name`, "
                "JSON_UNQUOTE(JSON_EXTRACT(t.`json_column_name`, '$.key_name')) AS `abstract_text` "
                "FROM `table_name` AS t;\nWhen the structure of a JSON column is unknown, first "
                "inspect the whole column: SELECT `json_column_name` FROM `table_name` LIMIT 5;\n")
    return ""


def get_prompt_dialect_string_matching(api: str) -> str:
    if api == "snowflake":
        return ("Do not directly match strings if you are not convinced. Use fuzzy query first: WHERE "
                "str ILIKE \"%target_str%\" For string matching, e.g. meat lovers, you should use % to "
                "replace space. e.g. ILKIE %meat%lovers%.\n")
    elif api == "bigquery":
        return ("Do not directly match strings if you are not convinced. Use LOWER for fuzzy queries: "
                "WHERE LOWER(str) LIKE LOWER('%target_str%'). For example, to match 'meat lovers', use "
                "LOWER(str) LIKE '%meat%lovers%'.\n")
    elif api == "sqlite":
        return ("Do not directly match strings if you are not convinced. For fuzzy queries, use: WHERE "
                "str LIKE '%target_str%'. For example, to match 'meat lovers', use WHERE str LIKE "
                "'%meat%lovers%'. If case sensitivity is needed, add COLLATE BINARY: WHERE str LIKE "
                "'%target_str%' COLLATE BINARY.\n")
    elif api == "mysql":
        return ("Do not directly match strings if you are not convinced. For fuzzy queries, use: WHERE "
                "LOWER(str) LIKE LOWER('%target_str%'). For example, to match 'meat lovers', use WHERE "
                "LOWER(str) LIKE '%meat%lovers%'.\n")
    return ""


# --------------------------------------------------------------------------- #
# FORMAT RESTRICTION  (prompt.get_format_prompt / agent.format_answer)
# --------------------------------------------------------------------------- #
def get_format_prompt() -> str:
    p = "This is an SQL task. Please provide the simplest possible answer format in ```csv``` format like a table.\n"
    p += ("e.g.1. Including the travel coordinates and the cumulative travel distance at each point. "
          "Format: ```csv\ntravel_coordinates,cumulative_travel_distance\nPOINT(longitude1 latitude1),"
          "distance1:int\nPOINT(longitude2 latitude2),distance2:int\n...```\n")
    p += ("When asked something without specifying name or id, provide both. e.g.2. Which products had "
          "a seasonality-adjusted sales ratio that stayed consistently above 2 for every month in the "
          "year 2017? Format: ```csv\nproduct_name,product_id\nproduct_name1:str,product_id1:int\n...```\n")
    p += "Do not output any SQL queries.\n"
    return p


def _extract_block(txt: str, lang: str) -> str:
    m = re.findall(rf"```{lang}\s*(.*?)```", txt or "", re.S)
    if m:
        return m[0].strip()
    m = re.findall(r"```\s*(.*?)```", txt or "", re.S)
    return m[0].strip() if m else (txt or "").strip()


def format_answer(llm, task: str, tag: str = "reforce_format") -> str:
    """agent.format_answer: one dedicated call, SQL forbidden, keep ONLY the first line (the header)."""
    try:
        txt = llm.ask("You output only a csv answer format.", "Task: " + task + get_format_prompt(),
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
    p = (f"Write at most 10 {api} simple SQL queries in format like:\n "
         f"{get_prompt_dialect_basic(api)}\nin ```sql``` code block to have an understanding of "
         "values in related columns.\n")
    p += ("Each query should be different. Don't query about any SCHEMA or checking data types. You "
          "can write SELECT query only. Try to use DISTINCT. Don't output the final answer.\n")
    p += "Write annotations to describe each SQL, format like ```sql\n--Description: \n```.\n"
    p += get_prompt_dialect_nested(api)
    return p


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
    base = table_info + "\nTask: " + task + "\n"
    while max_try > 0:
        pre_info, n_ok = "", 0
        try:
            txt = llm.ask("You write read-only exploratory SQL.",
                          base + get_exploration_prompt(api), tag=tag, max_tokens=1200)
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
                    fix = llm.ask("You fix one read-only SQL. Output one ```sql block.",
                                  f"Input sql:\n{sql}\nThe error information is:\n{str(e)[:300]}\n"
                                  "Please correct it and output only 1 complete SQL query.",
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
