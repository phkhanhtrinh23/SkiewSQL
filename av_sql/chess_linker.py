"""CHESS schema linker ported into AV-SQL.

Replaces AV-SQL's blind schema-split (the N×M/N×1 chunking) with CHESS's question-aware schema selection: select_tables -> select_columns -> one focused sub-schema. Returns a filtered schema_dict (same shape as schema_dict_dbid) that the normal AV-SQL pipeline (CTE agent + LSH + skill-graph + planner + SQL + revise) then runs on unchanged.

Prompts are faithful ports of CHESS templates (template_select_tables.txt / template_select_columns.txt). Run via AV-SQL's ChatLLM."""
import json, os, re
from .chat import ChatLLM

SELECT_TABLES_TMPL = """You are an expert and very smart data analyst.
Your task is to analyze the provided database schema, comprehend the posed question, and leverage the hint to identify which tables are needed to generate a SQL query for answering the question.

Database Schema Overview:
{DATABASE_SCHEMA}

This schema provides a detailed definition of the database's structure, including tables, their columns, primary keys, foreign keys, and any relevant details about relationships or constraints.
For key phrases mentioned in the question, we have provided the most similar values within the columns denoted by "-- examples" in front of the corresponding column names. This is a critical hint to identify the tables that will be used in the SQL query.

Question:
{QUESTION}

Hint:
{HINT}

The hint aims to direct your focus towards the specific elements of the database schema that are crucial for answering the question effectively.

Task:
Based on the database schema, question, and hint provided, your task is to determine the tables that should be used in the SQL query formulation.
For each of the selected tables, explain why exactly it is necessary for answering the question.

Please respond with a JSON object structured as follows:

```json
{{
  "chain_of_thought_reasoning": "Explanation of the logical analysis that led to the selection of the tables.",
  "table_names": ["Table1", "Table2", "Table3"]
}}
```

Note that you should choose all and only the tables that are necessary to write a SQL query that answers the question effectively.
Only output a json as your response."""

SELECT_COLUMNS_TMPL = """You are an expert and very smart data analyst.
Your task is to examine the provided database schema, understand the posed question, and use the hint to pinpoint the specific columns within tables that are essential for crafting a SQL query to answer the question.

Database Schema Overview:
{DATABASE_SCHEMA}

This schema offers an in-depth description of the database's architecture. Special attention should be given to the examples listed beside each column, as they directly hint at which columns are relevant to our query.

Question:
{QUESTION}

Hint:
{HINT}

Task:
Based on the database schema, question, and hint provided, your task is to identify all and only the columns that are essential for crafting a SQL query to answer the question.
Tip: If you are choosing a column for filtering a value within that column, make sure that column has the value as an example.

Please respond with a JSON object structured as follows:

```json
{{
  "chain_of_thought_reasoning": "Your reasoning for selecting the columns, be concise and clear.",
  "table_name1": ["column1", "column2"],
  "table_name2": ["column1", "column2"]
}}
```

Make sure your response includes the table names as keys, each associated with a list of column names that are necessary for writing a SQL query to answer the question.
Only output a json as your response."""


def _parse_json(txt: str) -> dict:
    if not txt:
        return {}
    m = re.search(r"```json\s*(.*?)\s*```", txt, re.DOTALL)
    if m:
        txt = m.group(1)
    else:
        m = re.search(r"```\s*(.*?)\s*```", txt, re.DOTALL)
        if m:
            txt = m.group(1)
    # last-ditch: grab the outermost {...}
    s, e = txt.find("{"), txt.rfind("}")
    if s != -1 and e != -1 and e > s:
        txt = txt[s:e + 1]
    try:
        return json.loads(txt)
    except Exception:
        return {}


def render_chess_schema(schema_dict_dbid: dict, selected_tables=None) -> str:
    """Render AV-SQL schema into CHESS's CREATE-TABLE-with-`-- Example Values` format."""
    tables = list(schema_dict_dbid.keys())
    if selected_tables is not None:
        sel = {t.lower() for t in selected_tables}
        tables = [t for t in tables if t.lower() in sel]
    blocks = []
    for t in tables:
        info = schema_dict_dbid[t]
        names = info.get("columns_name", [])
        types = info.get("columns_type", [])
        descs = info.get("columns_description", [])
        exs = info.get("example_values", [])
        lines = [f"CREATE TABLE {t}", "("]
        for i, cn in enumerate(names):
            typ = types[i] if i < len(types) else ""
            frag = f"\t{cn} {typ},"
            comment = ""
            ev = exs[i] if i < len(exs) else []
            if ev:
                vals = ", ".join(f"`{str(v)}`" for v in ev[:5])
                comment += f" Example Values: {vals}"
            d = descs[i] if i < len(descs) else ""
            if d and str(d).strip().lower() != str(cn).strip().lower():
                comment += f" | Column Description: {d}"
            if comment:
                frag += f" --{comment}"
            lines.append(frag)
        for pk in info.get("primary_key", []) or []:
            lines.append(f"\tPRIMARY KEY ({pk}),")
        for fk in info.get("foreign_keys", []) or []:
            try:
                (ft, fc), (rt, rc) = fk
                if str(ft).lower() == str(t).lower():
                    lines.append(f"\tFOREIGN KEY ({fc}) REFERENCES {rt}({rc}),")
            except Exception:
                pass
        lines.append(");")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _llm(config):
    sl = config.get("schema_linker", config.get("cte_agent", {}))
    return ChatLLM(model_name=sl.get("model_name", "gpt-5-mini"),
                   temperature=sl.get("temperature", 1.0),
                   max_tokens=sl.get("max_tokens", 4096), stream=False)


def chess_link(config, question: str, evidence: str, schema_dict_dbid: dict, log_dir: str = None) -> dict:
    """CHESS schema linking -> filtered schema_dict (subset of tables/columns), same shape."""
    llm = _llm(config)
    all_tables = list(schema_dict_dbid.keys())

    # 1) select_tables
    schema_str = render_chess_schema(schema_dict_dbid)
    msg = [{"role": "user", "content": SELECT_TABLES_TMPL.format(
        DATABASE_SCHEMA=schema_str[:60000], QUESTION=question, HINT=evidence or "")}]
    resp = llm.get_model_response_txt(msg)
    d = _parse_json(resp)
    lut = {t.lower(): t for t in all_tables}
    selected_tables = []
    for t in d.get("table_names", []) or []:
        tl = str(t).strip().strip("`").lower()
        if tl in lut and lut[tl] not in selected_tables:
            selected_tables.append(lut[tl])
    if not selected_tables:                       # linker failed -> fall back to full schema
        selected_tables = all_tables

    # 2) select_columns (schema restricted to selected tables = CHESS "tentative" schema)
    schema_str2 = render_chess_schema(schema_dict_dbid, selected_tables)
    msg2 = [{"role": "user", "content": SELECT_COLUMNS_TMPL.format(
        DATABASE_SCHEMA=schema_str2[:60000], QUESTION=question, HINT=evidence or "")}]
    resp2 = llm.get_model_response_txt(msg2)
    d2 = _parse_json(resp2)
    sel_lut = {t.lower(): t for t in selected_tables}
    selected_cols = {}
    for k, v in (d2 or {}).items():
        if k == "chain_of_thought_reasoning":
            continue
        tl = str(k).strip().strip("`").lower()
        if tl in sel_lut and isinstance(v, list):
            selected_cols[sel_lut[tl]] = [str(c).strip().strip("`") for c in v]

    # 3) build filtered part-dict (same shape). Subset columns keeping parallel lists aligned
    filtered = {}
    for t in selected_tables:
        orig = schema_dict_dbid[t]
        names = orig.get("columns_name", [])
        want = [c.lower() for c in selected_cols.get(t, [])]
        if want:
            idxs = [i for i, cn in enumerate(names) if cn.lower() in want]
        else:
            idxs = list(range(len(names)))        # no columns picked -> keep all
        if not idxs:
            idxs = list(range(len(names)))
        kept_names = {names[i] for i in idxs}

        def _slice(key):
            lst = orig.get(key, [])
            return [lst[i] for i in idxs if i < len(lst)]

        filtered[t] = {
            "db_type": orig.get("db_type", ""),
            "db_id": orig.get("db_id", ""),
            "table_to_tablefullname": orig.get("table_to_tablefullname", t),
            "columns_name": _slice("columns_name"),
            "columns_type": _slice("columns_type"),
            "columns_description": _slice("columns_description"),
            "example_values": _slice("example_values"),
            "primary_key": orig.get("primary_key", []),
            "foreign_keys": orig.get("foreign_keys", []),
            "sample_rows": [{c: r[c] for c in r if c in kept_names} for r in orig.get("sample_rows", [])],
        }
    if log_dir:
        try:
            json.dump({"selected_tables": selected_tables, "selected_cols": selected_cols},
                      open(os.path.join(log_dir, "chess_link.json"), "w"), indent=2)
        except Exception:
            pass
    return filtered
