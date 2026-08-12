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

import threading
import numpy as np
from openai import OpenAI

_CLIENT = None

# --- Provider switch: OpenAI (default) or Together AI --------------------------------------------
# SKIEW_LLM_PROVIDER=together routes CHAT to Together AI (client reads TOGETHER_API_KEY). Embeddings
# stay on OpenAI (cheap) unless SKIEW_EMBED_PROVIDER=together. Together's FREE tier is ~3 req/min
# (dynamic), so we throttle chat to <= SKIEW_TOGETHER_RPM to avoid 429s.
_PROVIDER = os.environ.get("SKIEW_LLM_PROVIDER", "openai").lower()
_TOGETHER_MODEL = os.environ.get("SKIEW_TOGETHER_MODEL", "Prism-ML/Ternary-Bonsai-27B")
_TOGETHER_RPM = float(os.environ.get("SKIEW_TOGETHER_RPM", "3"))     # free tier ≈ 3 rpm
# Prism-ML/Ternary-Bonsai-27B is a REASONING model: it spends completion tokens on hidden reasoning
# before the answer. Give big headroom so `content` is actually produced (else finish_reason=Length).
# The reasoning trace alone eats ~4-7k tokens on config-A's complex (big-schema) prompts; at a 5k cap
# the model hits finish_reason=Length with EMPTY content (no SQL -> gen=0). 7000 leaves room to emit
# the answer after reasoning (verified: has_sql=True at ~8k max_tokens). A larger cap does not slow
# calls that finish early — it only prevents truncation.
_TOGETHER_REASON_BUDGET = int(os.environ.get("SKIEW_TOGETHER_REASON_BUDGET", "7000"))
_MIN_INTERVAL = 60.0 / max(_TOGETHER_RPM, 0.1)
_rl_lock = threading.Lock()
_last_call = [0.0]

# Per-call timeout, enforced by the OpenAI SDK's own httpx timeout (see client()). This aborts a
# stalled read and raises, which the chat() retry loop handles — no thread hacks, no pool leak.
_CALL_TIMEOUT = float(os.environ.get("SKIEW_CALL_TIMEOUT", "220"))


def _throttle():
    """Global min-interval throttle — only when using Together (its low free-tier rate limit)."""
    if _PROVIDER != "together":
        return
    with _rl_lock:
        wait = _MIN_INTERVAL - (time.monotonic() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.monotonic()


def client():
    """The CHAT client — Together AI or OpenAI depending on SKIEW_LLM_PROVIDER."""
    global _CLIENT
    if _CLIENT is None:
        if _PROVIDER == "together":
            # Together via its OpenAI-COMPATIBLE endpoint, driven by the OpenAI SDK — whose timeout
            # ACTUALLY aborts a stalled read. The native `together` SDK's timeout= does NOT: a hung
            # socket sits in do_poll forever (that was the 21-min "hang"). max_retries=0 — our chat()
            # loop does the retrying.
            _CLIENT = OpenAI(api_key=os.environ["TOGETHER_API_KEY"],
                             base_url="https://api.together.xyz/v1",
                             timeout=_CALL_TIMEOUT, max_retries=0)
        else:
            # timeout: a stalled connection otherwise BLOCKS FOREVER; 120s turns a hang into a
            # retryable timeout error.
            _CLIENT = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=120.0, max_retries=2)
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
def is_reasoning_model(model: str) -> bool:
    """GPT-5 / o-series reasoning models: no custom temperature, and they use
    `max_completion_tokens` (which also covers hidden reasoning tokens)."""
    m = (model or "").lower().replace("_", "-")
    return m.startswith(("gpt-5", "o1", "o3", "o4"))


class LLM:
    def __init__(self, model: str = "gpt-5-mini", temperature: float = 0.0,
                 max_tokens: int = 1500, reasoning_effort: str = "minimal"):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort
        self.is_reasoning = is_reasoning_model(model)

    def chat(self, messages: List[Dict], tag: str = "misc",
             temperature: Optional[float] = None, max_tokens: Optional[int] = None,
             retries: int = 4) -> str:
        want = self.max_tokens if max_tokens is None else max_tokens
        last = None
        for attempt in range(retries):
            try:
                _throttle()                                  # Together free-tier rate limit
                if _PROVIDER == "together":
                    params: Dict = {"model": _TOGETHER_MODEL, "messages": messages,
                                    "temperature": self.temperature if temperature is None else temperature,
                                    "max_tokens": want + _TOGETHER_REASON_BUDGET}   # headroom for reasoning tokens
                else:
                    params = {"model": self.model, "messages": messages}
                    if self.is_reasoning:
                        # reasoning models: budget must also cover hidden reasoning tokens,
                        # so add headroom; custom temperature is unsupported -> omit it.
                        params["max_completion_tokens"] = want + 512
                        if self.reasoning_effort:
                            params["reasoning_effort"] = self.reasoning_effort
                    else:
                        params["temperature"] = self.temperature if temperature is None else temperature
                        params["max_tokens"] = want
                _t0 = time.monotonic()
                resp = client().chat.completions.create(**params)
                u = getattr(resp, "usage", None)
                USAGE.add(tag, getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0)
                if os.environ.get("SKIEW_LLM_DEBUG"):
                    _c = resp.choices[0]
                    print(f"[llm {tag}] {time.monotonic()-_t0:.1f}s finish={getattr(_c,'finish_reason','?')} "
                          f"compl={getattr(u,'completion_tokens',0)} content_len={len(_c.message.content or '')}",
                          flush=True)
                return resp.choices[0].message.content or ""
            except Exception as e:  # noqa: BLE001
                last = e
                m = str(e).lower()
                if any(k in m for k in ("rate", "429", "quota", "too many")):
                    time.sleep(max(_MIN_INTERVAL, 20.0) * (attempt + 1))   # rate-limit backoff
                else:
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
_EMBED_CLIENT: Optional[OpenAI] = None


def _embed_client() -> OpenAI:
    """Embeddings ALWAYS use OpenAI (cheap ~$0), independent of the chat provider — so switching
    chat to Together does not break retrieval, and does not burn Together's low free-tier rate limit."""
    global _EMBED_CLIENT
    if _EMBED_CLIENT is None:
        _EMBED_CLIENT = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""), timeout=60.0, max_retries=2)
    return _EMBED_CLIENT


class Embedder:
    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self._cache: Dict[str, np.ndarray] = {}

    def encode(self, text: str) -> np.ndarray:
        text = (text or "").strip() or "(empty)"
        if text in self._cache:
            return self._cache[text]
        resp = _embed_client().embeddings.create(model=self.model, input=[text])
        USAGE.add("embed", resp.usage.prompt_tokens, 0)
        v = np.asarray(resp.data[0].embedding, dtype=np.float32)
        self._cache[text] = v
        return v

    def sim(self, a: str, b: str) -> float:
        va, vb = self.encode(a), self.encode(b)
        denom = (np.linalg.norm(va) * np.linalg.norm(vb)) or 1.0
        return float(np.dot(va, vb) / denom)
