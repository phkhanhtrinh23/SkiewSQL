"""Composition-step guards for WEAK models (Together/OpenRouter/Nemotron, etc.). Gated ENTIRELY behind SKIEW_COMPOSE_GUARDS=1 so strong-model runs (OpenAI/Claude/GPT) are unaffected. Rationale: config A's correctness is a *conjunction* over independently generated views + the final composition, so it collapses super-linearly as per-piece SQL quality drops. On a weak model, free-form "revise this error" calls also fail, so we enforce the parts of the contract we ALREADY know deterministically and hedge the conjunction:

# 1  output-arity contract   — check the final query's real column count vs the question's required outputs. Targeted-repair on mismatch. #2  unknown-column hint      — turn an "Unknown column X" execution error into a precise hint naming the base table holding X (instead of a blind revise). #3  carry-through columns    — instruct each view to project every column its WHERE/JOIN uses. #4  grain contract           — DETERMINISTICALLY detect wrong-grain output (duplicate grain-key values in the result rows) and collapse to one row per grain via a targeted repair, accepted only if it executes, keeps arity, and does not add rows. Targets the "result mismatch" caused by over-grouping. #6  compose-vs-direct race   — run the composed query AND a direct single-shot. Pick by executes -> arity-match -> non-empty."""
import os
import re
import json
from typing import Optional, List, Tuple, Callable

ON = os.environ.get("SKIEW_COMPOSE_GUARDS", "0") == "1"

# #3 — appended to the view-generation system prompt when guards are ON.
CARRY_CLAUSE = (
    " CARRY-THROUGH (required): in this view's SELECT, ALSO project every column you reference in any "
    "WHERE / JOIN / ON / GROUP BY, aliased to its bare name, so a downstream query can filter or join "
    "on it. A view must never hide a column that its own predicates depend on.")

# probe(sql) -> (ncols|None, rows:list[tuple]) or None on execution error
Probe = Callable[[str], Optional[Tuple[Optional[int], list]]]

_contract_cache: dict = {}
_UNK = re.compile(r"[Uu]nknown column ['\"`]?([\w.]+)")
_CREATE = re.compile(r'CREATE TABLE\s+["`]?(\w+)["`]?\s*\((.*?)\n\s*\)\s*;', re.DOTALL | re.IGNORECASE)
_AGG = re.compile(r'\bGROUP\s+BY\b|\bSELECT\s+DISTINCT\b', re.IGNORECASE)


def _norm(s: str) -> str:
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def contract(llm, question: str, evidence: str = "") -> Tuple[Optional[int], List[str], List[str]]:
    """#1 + #4 source: one focused call → (n_outputs, output_cols, grain_cols). (None, [], []) when unsure so both checks fail-safe (skipped)."""
    if not ON:
        return None, [], []
    key = (question or "").strip()
    if key in _contract_cache:
        return _contract_cache[key]
    res = (None, [], [])
    try:
        sys = ("From the question, extract two things as JSON: `outputs` = the columns the query must "
               "RETURN in the SELECT (in order, excluding filter/sort-only columns), and `grain` = the "
               "column(s) that define ONE output row (the 'for each ...' dimension). Use short labels. "
               'Respond ONLY as {"outputs": [...], "grain": [...]}. Use [] if unsure.')
        txt = llm.ask(sys, f"Question: {question}\n" + (f"Evidence: {evidence}\n" if evidence else "")
                      + 'JSON only, e.g. {"outputs":["subject title","total cost"],"grain":["subject title"]}',
                      tag="cg_contract", max_tokens=250)
        m = re.search(r"\{.*\}", txt or "", re.DOTALL)
        obj = json.loads(m.group(0)) if m else {}
        outs = [str(x) for x in (obj.get("outputs") or []) if str(x).strip()]
        grain = [str(x) for x in (obj.get("grain") or []) if str(x).strip()]
        res = (len(outs) if outs else None, outs, grain)
    except Exception:  # noqa: BLE001 — best-effort. Never fail a question
        res = (None, [], [])
    _contract_cache[key] = res
    return res


def unknown_col_hint(err: str, ddl_text: str) -> str:
    """#2: if `err` is an unknown-column error, name the base table that holds the column."""
    if not ON or not err or not ddl_text:
        return ""
    m = _UNK.search(err)
    if not m:
        return ""
    col = m.group(1).split(".")[-1]
    for tm in _CREATE.finditer(ddl_text):
        if re.search(rf'["`\s(,]{re.escape(col)}["`\s,)]', tm.group(2)):
            return (f" HINT: column `{col}` is not exposed by any CTE. It lives in base table "
                    f"`{tm.group(1)}`. Add `{col}` to that CTE's SELECT, or read it from the base "
                    f"table directly.")
    return f" HINT: column `{col}` is not exposed by any CTE — add it to the relevant CTE's SELECT."


def _arity_instruction(want_n: int, want_cols: List[str]) -> str:
    cols = (" (exactly these, in order: " + ", ".join(want_cols) + ")") if want_cols else ""
    return (f"Your query returns the wrong number of output columns. Return EXACTLY {want_n} "
            f"column(s){cols}. Any column used only to filter/group/sort must NOT appear in SELECT.")


def _grain_col_index(grain: List[str], out_cols: List[str]) -> Optional[int]:
    """Map the (first) grain label to the output column index, so we can test its values. Exact match, or substring only when BOTH labels are >=4 chars (avoids short-label false hits)."""
    for gl in grain:
        ng = _norm(gl)
        if not ng:
            continue
        for ci, ol in enumerate(out_cols):
            no = _norm(ol)
            if not no:
                continue
            if ng == no:
                return ci
            if len(ng) >= 4 and len(no) >= 4 and (ng in no or no in ng):
                return ci
    return None


def _has_dup(rows: list, idx: int) -> bool:
    try:
        vals = [r[idx] for r in rows]
        return len(vals) != len(set(vals))
    except Exception:  # noqa: BLE001
        return False


def _pick_best(cands: List[str], probe: Probe, want_n: Optional[int]) -> Optional[str]:
    """#6: choose by executes -> arity-match -> non-empty -> first-listed (composed wins ties)."""
    scored = []
    for i, c in enumerate(cands):
        if not c:
            continue
        p = probe(c)
        executes = p is not None
        ncols = p[0] if p else None
        nrows = len(p[1]) if p else 0
        arity_ok = (want_n is None) or (ncols == want_n)
        scored.append((executes, arity_ok, nrows > 0, -i, c))
    if not scored:
        return cands[0] if cands else None
    scored.sort(reverse=True)
    return scored[0][4]


def guarded_finalize(probe: Probe, composed: Optional[str], make_direct: Callable[[], Optional[str]],
                     revise_fn: Callable[[str, str], Optional[str]],
                     want_n: Optional[int], want_cols: List[str],
                     grain: Optional[List[str]] = None) -> Optional[str]:
    """#1 + #4 + #6 at the composition site. `probe(sql)` -> (ncols|None, rows) or None on error."""
    if not ON:
        return composed
    cands = [composed] if composed else []
    try:
        d = make_direct()
        if d:
            cands.append(d)
    except Exception:  # noqa: BLE001
        pass
    best = _pick_best(cands, probe, want_n) or composed
    if not best:
        return composed

    # #1 targeted arity repair
    if want_n:
        p = probe(best)
        if p is not None and p[0] is not None and p[0] != want_n:
            try:
                fx = revise_fn(best, _arity_instruction(want_n, want_cols))
            except Exception:  # noqa: BLE001
                fx = None
            if fx:
                pf = probe(fx)
                if pf is not None and pf[0] == want_n:
                    best = fx

    # #4 grain contract — trigger ONLY on deterministic evidence of over-grouping (duplicate grain-key values), so correct queries are never disturbed.
    if grain and _AGG.search(best or ""):
        p = probe(best)
        idx = _grain_col_index(grain, want_cols) if want_cols else None
        if p is not None and idx is not None and idx < (p[0] or 0) and _has_dup(p[1], idx):
            instr = ("Return EXACTLY one row per " + ", ".join(grain) + ". Your result has repeated "
                     f"'{', '.join(grain)}' values, so it is too fine-grained. Aggregate to that grain. "
                     "the GROUP BY keys must be exactly that grain and no other dimension.")
            try:
                fx = revise_fn(best, instr)
            except Exception:  # noqa: BLE001
                fx = None
            if fx:
                pf = probe(fx)
                # accept only if it executes, keeps arity, stays non-empty, and does not ADD rows
                if (pf is not None and pf[0] == p[0] and len(pf[1]) > 0
                        and len(pf[1]) <= len(p[1])):
                    best = fx
    return best
