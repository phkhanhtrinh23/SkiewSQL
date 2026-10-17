"""Load version-controlled prompt text from the repository-level ``templates`` package."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path, PurePosixPath


_TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "templates"


@lru_cache(maxsize=None)
def load_prompt(relative_path: str) -> str:
    """Return one UTF-8 prompt while preventing paths outside the template tree."""
    path = PurePosixPath(relative_path)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError(f"invalid prompt path: {relative_path!r}")
    target = _TEMPLATE_ROOT.joinpath(*path.parts)
    if target.suffix != ".txt":
        raise ValueError(f"prompt must be a .txt file: {relative_path!r}")
    return target.read_text(encoding="utf-8")
