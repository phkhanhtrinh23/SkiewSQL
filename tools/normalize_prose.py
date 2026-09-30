#!/usr/bin/env python3
"""Normalize repository prose without changing code examples or executable syntax."""

from __future__ import annotations

import argparse
import ast
import inspect
import io
import re
import tokenize
from pathlib import Path


PROTECTED_INLINE = re.compile(r"(`+[^`\n]*`+|\$[^$\n]+\$|&(?:#\d+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]+);)")
FENCE = re.compile(r"^\s*(```|~~~)")
LIST_ITEM = re.compile(r"^(\s*)(?:[-+*]|\d+[.)])\s+")
COMMENT_LINE = re.compile(r"^(\s*)#\s?(.*)$")
STRUCTURAL = re.compile(
    r"^(?:\s*$|#{1,6}(?:\s|$)|\s*(?:```|~~~)|\s*\||\s*>|\s*<|\s*!?\[[^]]+\]:|\s*[-*_]{3,}\s*$|\s*\$\$|\s*\\\[|\s*\\\]|\s*\{[A-Z][A-Z0-9_]*\}\s*$|\s*/\*.*\*/\s*$|[^.?!]+:\s*$)"
)


def _replace_semicolons(fragment: str) -> str:
    fragment = re.sub(
        r";(\s+)([*_\"'(\[]*)([a-z])",
        lambda match: "." + match.group(1) + match.group(2) + match.group(3).upper(),
        fragment,
    )
    return fragment.replace(";", ".")


def clean_prose(text: str) -> str:
    """Replace prose semicolons while preserving inline code, inline math, and HTML entities."""
    pieces = PROTECTED_INLINE.split(text)
    return "".join(piece if PROTECTED_INLINE.fullmatch(piece or "") else _replace_semicolons(piece) for piece in pieces)


def _flush(buffer: list[str], output: list[str]) -> None:
    if not buffer:
        return
    first = buffer[0].rstrip()
    rest = [line.strip() for line in buffer[1:]]
    output.append(" ".join([first, *rest]))
    buffer.clear()


def normalize_markdown(text: str, preserve_indented_code: bool = True) -> str:
    """Unwrap prose paragraphs and clean punctuation outside fenced code blocks."""
    output: list[str] = []
    buffer: list[str] = []
    in_fence = False
    fence_marker = ""
    buffer_kind = ""

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        fence = FENCE.match(line)
        if fence:
            _flush(buffer, output)
            marker = fence.group(1)
            output.append(line)
            if in_fence and marker == fence_marker:
                in_fence = False
                fence_marker = ""
            elif not in_fence:
                in_fence = True
                fence_marker = marker
            continue
        if in_fence:
            output.append(raw_line)
            continue

        line = clean_prose(line)
        if not line.strip():
            _flush(buffer, output)
            if output and output[-1] != "":
                output.append("")
            buffer_kind = ""
            continue

        item = LIST_ITEM.match(line)
        if item:
            _flush(buffer, output)
            buffer.append(line.strip() if not item.group(1) else line)
            buffer_kind = "list"
            continue

        if line.lstrip().startswith(">"):
            quote_text = line.lstrip()[1:].lstrip()
            if buffer_kind != "quote":
                _flush(buffer, output)
                buffer.append("> " + quote_text)
                buffer_kind = "quote"
            else:
                buffer.append(quote_text)
            continue

        if buffer_kind == "list" and not STRUCTURAL.match(line) and not LIST_ITEM.match(line):
            buffer.append(line)
            continue

        if STRUCTURAL.match(line) or (preserve_indented_code and (line.startswith("    ") or line.startswith("\t"))):
            _flush(buffer, output)
            output.append(line)
            buffer_kind = ""
            continue

        if buffer_kind and buffer_kind != "paragraph":
            _flush(buffer, output)
        buffer.append(line)
        buffer_kind = "paragraph"

    _flush(buffer, output)
    return "\n".join(output).rstrip() + "\n"


def normalize_prompt(text: str) -> str:
    """Normalize authored prompt prose while retaining template field boundaries."""
    text = text.replace(" ### ", "\n###\n")
    text = re.sub(r"(\*/)\s+", r"\1\n", text)
    text = re.sub(r"(?m)^### (?=(?:【|CTE |Hint |External |Question:|/\*))", "###\n", text)
    text = re.sub(r"(【[^】\n]+】) (?=\{[A-Z][A-Z0-9_]*\})", r"\1\n", text)
    text = re.sub(
        r"((?:External knowledge if exists|Hint or External knowledge if exists|Hint or external knowledge if exists|Target step / sub-question \(optional\)|Question|SQL query generated to answer the question|Output of the SQL query):) (?=\{[A-Z][A-Z0-9_]*\})",
        r"\1\n",
        text,
    )
    text = text.replace(
        "{EXTERNAL_KNOWLEDGE_STR} You could use information from external knowledge",
        "{EXTERNAL_KNOWLEDGE_STR}\nYou could use information from external knowledge",
    )
    return normalize_markdown(text)


def _line_offsets(text: str) -> list[int]:
    offsets = [0]
    for match in re.finditer(r"\n", text):
        offsets.append(match.end())
    return offsets


def _absolute(offsets: list[int], position: tuple[int, int]) -> int:
    line, column = position
    return offsets[line - 1] + column


def _docstring_starts(tree: ast.AST) -> set[tuple[int, int]]:
    starts: set[tuple[int, int]] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not body or not isinstance(body, list):
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
            starts.add((first.value.lineno, first.value.col_offset))
    return starts


def _comment_barrier(text: str) -> bool:
    stripped = text.strip()
    return (
        not stripped
        or bool(re.fullmatch(r"[-=#*\s]{3,}", stripped))
        or stripped.startswith(("!", "noqa", "type:", "pylint:", "fmt:", "nosec"))
        or _is_code_comment(stripped)
    )


def _is_code_comment(text: str) -> bool:
    stripped = text.lstrip()
    return (
        "pdb.set_trace" in stripped
        or stripped.startswith((
            "import ", "from ", "def ", "class ", "return ", "raise ", "yield ", "SELECT ",
            "WITH ", "CREATE ", "ALTER ", "DROP ", "INSERT ", "UPDATE ", "DELETE ", "@",
        ))
    )


def normalize_comment_paragraphs(text: str) -> str:
    """Join wrapped standalone comment paragraphs and preserve comment lists and dividers."""
    output: list[str] = []
    buffer: list[str] = []
    indentation = ""
    list_mode = False

    def flush() -> None:
        nonlocal list_mode
        if buffer:
            output.append(indentation + "# " + " ".join(part.strip() for part in buffer))
            buffer.clear()
        list_mode = False

    for line in text.splitlines():
        match = COMMENT_LINE.match(line)
        if match:
            collapsed = re.fullmatch(r"([-=_*]{3,}) # (.*?) ([-=_*]{3,}) #", match.group(2))
            if collapsed:
                flush()
                current_indent = match.group(1)
                output.extend([
                    current_indent + "# " + collapsed.group(1) + " #",
                    current_indent + "# " + collapsed.group(2),
                    current_indent + "# " + collapsed.group(3) + " #",
                ])
                continue
        if not match or _comment_barrier(match.group(2)):
            flush()
            output.append(line)
            continue
        current_indent, content = match.groups()
        is_list = bool(re.match(r"(?:[-+*]|\d+[.)])\s+", content))
        if buffer and (current_indent != indentation or is_list or (list_mode and is_list)):
            flush()
        if not buffer:
            indentation = current_indent
            list_mode = is_list
        buffer.append(content)
    flush()
    return "\n".join(output) + ("\n" if text.endswith("\n") else "")


def _clean_string_token(token_text: str) -> str:
    match = re.match(r"(?is)^([rubf]*)(\"\"\"|'''|\"|')", token_text)
    if not match:
        return token_text
    opening = match.group(0)
    quote = match.group(2)
    if not token_text.endswith(quote):
        return token_text
    body = token_text[len(opening):-len(quote)]
    return opening + clean_prose(body) + quote


def _normalize_docstring_token(token_text: str, indentation: str) -> str:
    match = re.match(r"(?is)^([rubf]*)(\"\"\"|'''|\"|')", token_text)
    if not match:
        return token_text
    opening = match.group(0)
    quote = match.group(2)
    if not token_text.endswith(quote):
        return token_text
    body = inspect.cleandoc(token_text[len(opening):-len(quote)])
    if not body:
        return opening + quote
    normalized = normalize_markdown(body, preserve_indented_code=False).rstrip()
    lines = normalized.split("\n")
    normalized = lines[0]
    if len(lines) > 1:
        normalized += "\n" + "\n".join(indentation + line if line else "" for line in lines[1:])
    if normalized.endswith(quote[0]):
        return opening + normalized + "\n" + indentation + quote
    return opening + normalized + quote


def _is_executable_string(token_text: str) -> bool:
    match = re.match(r"(?is)^([rubf]*)(\"\"\"|'''|\"|')", token_text)
    if not match:
        return True
    if "r" in match.group(1).lower():
        return True
    opening = match.group(0)
    quote = match.group(2)
    body = token_text[len(opening):-len(quote)] if token_text.endswith(quote) else token_text
    if body.strip() in {";", "; ", ");", r"\n);"}:
        return True
    if body.strip().startswith(";"):
        return True
    if "CREATE TABLE" in body and ");" in body:
        return True
    if re.search(r"\b(?:SELECT|WITH)\b[\s\S]*;\s*$", body, re.IGNORECASE):
        return True
    if re.match(r"^[A-Za-z_][A-Za-z0-9_.]*;\\n", body):
        return True
    sql_markers = (
        "LATERAL FLATTEN",
        "UNNEST(",
        "json_each(",
        "FROM `table_name`",
        "LIMIT 5;",
        "VALUES (?, ?) IF NOT EXISTS;",
    )
    return any(marker in body for marker in sql_markers)


def _is_executable_fstring_fragment(fragment: str) -> bool:
    """Identify f-string fragments whose semicolons are executable or structured syntax."""
    return (
        "\n);" in fragment
        or r"\n);" in fragment
        or "VALUES (?, ?) IF NOT EXISTS;" in fragment
        or fragment.strip() == ";"
        or "SELECT \"col1\"" in fragment
    )


def normalize_python(text: str) -> str:
    """Clean semicolon punctuation in comments and prose strings while preserving executable strings."""
    had_final_newline = text.endswith("\n")
    text = "\n".join(line.rstrip() for line in text.splitlines())
    if had_final_newline:
        text += "\n"
    text = normalize_comment_paragraphs(text)
    try:
        tree = ast.parse(text)
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (SyntaxError, tokenize.TokenError):
        return text
    docstrings = _docstring_starts(tree)
    offsets = _line_offsets(text)
    replacements: list[tuple[int, int, str]] = []
    fstring_middle = getattr(tokenize, "FSTRING_MIDDLE", -1)
    for token in tokens:
        replacement = None
        if token.type == tokenize.COMMENT and ";" in token.string and not _is_code_comment(token.string.lstrip("# ")):
            replacement = clean_prose(token.string)
        elif token.type == tokenize.STRING and token.start in docstrings:
            replacement = _normalize_docstring_token(token.string, " " * token.start[1])
        elif token.type == tokenize.STRING and ";" in token.string and not _is_executable_string(token.string):
            replacement = _clean_string_token(token.string)
        elif token.type == fstring_middle and ";" in token.string and not _is_executable_fstring_fragment(token.string):
            replacement = clean_prose(token.string)
        if replacement is None or replacement == token.string:
            continue
        start = _absolute(offsets, token.start)
        end = _absolute(offsets, token.end)
        replacements.append((start, end, replacement))
    for start, end, replacement in reversed(replacements):
        text = text[:start] + replacement + text[end:]
    return text


def iter_files(roots: list[Path]):
    for root in roots:
        if root.is_file():
            yield root
            continue
        yield from root.rglob("*.md")
        yield from root.rglob("*.py")
        for path in root.rglob("*.txt"):
            if "prompt_templates" in path.parts and "examples" in path.parts:
                continue
            yield path


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize prose punctuation and Markdown wrapping.")
    parser.add_argument("paths", nargs="*", default=["skiewsql"], help="files or directories to normalize")
    parser.add_argument("--check", action="store_true", help="report files that would change without writing them")
    args = parser.parse_args()

    changed = []
    seen = set()
    for path in iter_files([Path(value) for value in args.paths]):
        path = path.resolve()
        if path in seen or "__pycache__" in path.parts:
            continue
        seen.add(path)
        old = path.read_text()
        if path.suffix == ".txt":
            new = normalize_prompt(old)
        elif path.suffix == ".md":
            new = normalize_markdown(old)
        else:
            new = normalize_python(old)
        if new == old:
            continue
        changed.append(path)
        if not args.check:
            path.write_text(new)
    for path in changed:
        print(path)
    if args.check and changed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
