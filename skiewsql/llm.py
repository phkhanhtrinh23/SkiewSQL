"""
llm.py — thin OpenAI client for the real SkiewSQL pipeline.

Provides:
  * LLM(model).chat(messages)  -> text, with global token accounting (real API usage).
  * extract_code(text, lang)   -> first fenced code block of a language (sql/json/cte).
  * extract_json(text)         -> parsed JSON object from a response (fenced or bare).
  * Embedder(model).encode(texts) -> list[np.ndarray], cached, via OpenAI embeddings.

All token usage flows through the module-level USAGE accumulator so the harness can
report *real* prompt/completion token counts per configuration (not a proxy).
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
from openai import OpenAI

_CLIENT: Optional[OpenAI] = None


def client() -> OpenAI:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _CLIENT


# --------------------------------------------------------------------------- #
# Token accounting
# --------------------------------------------------------------------------- #
@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    calls: int = 0
    by_tag: Dict[str, List[int]] = field(default_factory=dict)  # tag -> [prompt, completion, calls]

    def add(self, tag: str, p: int, c: int):
        self.prompt_tokens += p
        self.completion_tokens += c
        self.calls += 1
        slot = self.by_tag.setdefault(tag, [0, 0, 0])
        slot[0] += p
        slot[1] += c
        slot[2] += 1

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def snapshot(self) -> Dict:
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total,
            "by_tag": {k: {"prompt": v[0], "completion": v[1], "calls": v[2]}
                       for k, v in self.by_tag.items()},
        }

    def reset(self):
        self.prompt_tokens = self.completion_tokens = self.calls = 0
        self.by_tag = {}


USAGE = Usage()


# --------------------------------------------------------------------------- #
# Chat
# --------------------------------------------------------------------------- #
class LLM:
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0,
                 max_tokens: int = 1500):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def chat(self, messages: List[Dict], tag: str = "misc",
             temperature: Optional[float] = None, max_tokens: Optional[int] = None,
             retries: int = 4) -> str:
        last = None
        for attempt in range(retries):
            try:
                resp = client().chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature if temperature is None else temperature,
                    max_tokens=self.max_tokens if max_tokens is None else max_tokens,
                )
                u = resp.usage
                USAGE.add(tag, u.prompt_tokens, u.completion_tokens)
                return resp.choices[0].message.content or ""
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"LLM call failed after {retries} retries: {last}")

    def ask(self, system: str, user: str, **kw) -> str:
        return self.chat([{"role": "system", "content": system},
                          {"role": "user", "content": user}], **kw)


# --------------------------------------------------------------------------- #
# Extraction helpers
# --------------------------------------------------------------------------- #
_FENCE = re.compile(r"```([a-zA-Z0-9_]*)\s*\n(.*?)```", re.DOTALL)


def _blocks(text: str) -> List[tuple]:
    return [(m.group(1).lower().strip(), m.group(2).strip()) for m in _FENCE.finditer(text)]


def extract_code(text: str, langs=("sql", "cte")) -> Optional[str]:
    blocks = _blocks(text)
    for lang, body in blocks:
        if lang in langs:
            return body
    # fall back: any fenced block that is not json
    for lang, body in blocks:
        if lang != "json":
            return body
    return None


def extract_json(text: str) -> Optional[dict]:
    # 1) prefer a fenced ```json block
    for lang, body in _blocks(text):
        if lang == "json":
            try:
                return json.loads(body)
            except Exception:  # noqa: BLE001
                pass
    # 2) any fenced block that parses as json
    for _lang, body in _blocks(text):
        try:
            return json.loads(body)
        except Exception:  # noqa: BLE001
            pass
    # 3) first {...} span in the text
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    chunk = text[start:i + 1]
                    try:
                        return json.loads(chunk)
                    except Exception:  # noqa: BLE001
                        break
        start = text.find("{", start + 1)
    return None


# --------------------------------------------------------------------------- #
# Embeddings (OpenAI, cached)
# --------------------------------------------------------------------------- #
class Embedder:
    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self._cache: Dict[str, np.ndarray] = {}

    def encode(self, text: str) -> np.ndarray:
        text = (text or "").strip() or "(empty)"
        if text in self._cache:
            return self._cache[text]
        resp = client().embeddings.create(model=self.model, input=[text])
        USAGE.add("embed", resp.usage.prompt_tokens, 0)
        v = np.asarray(resp.data[0].embedding, dtype=np.float32)
        self._cache[text] = v
        return v

    def sim(self, a: str, b: str) -> float:
        va, vb = self.encode(a), self.encode(b)
        denom = (np.linalg.norm(va) * np.linalg.norm(vb)) or 1.0
        return float(np.dot(va, vb) / denom)
