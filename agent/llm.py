"""LLM backends for mini-agent.

Two backends share one tiny interface:

    plan(messages, tools) -> {"tool": name, "args": {...}}  or  {"final": text}

MockLLM is a deterministic, dependency-free planner used by the tests, the
offline demo and CI. DeepSeekLLM talks to any OpenAI-compatible chat-completions
endpoint (DeepSeek, Moonshot, local vLLM, ...) and uses the model's native
tool-calling field; it is only imported when a key is present.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any, Dict, List


class LLMError(Exception):
    """Raised when a backend cannot produce a plan."""


class MockLLM:
    """Rule-based planner: no network, no key, fully deterministic."""

    name = "mock"

    def __init__(self, notes_path: str = "notes.md") -> None:
        self.notes_path = notes_path

    def _already_wrote(self, messages: List[Dict[str, Any]]) -> bool:
        return any(m.get("role") == "tool" for m in messages)

    def plan(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        user = ""
        for message in reversed(messages):
            if message.get("role") == "user":
                user = message.get("content", "")
                break
        text = user.strip()

        # One tool call per turn: after a tool observation, summarise.
        if self._already_wrote(messages):
            last = [m for m in messages if m.get("role") == "tool"][-1]
            return {"final": "完成。工具返回：%s" % last.get("content", "")}

        match = re.search(r"([0-9][0-9\s+\-*/().%]*[0-9)])", text)
        if match and (re.search(r"[+\-*/%]", match.group(1)) or "算" in text or "计算" in text):
            return {"tool": "calc", "args": {"expression": match.group(1).strip()}}

        if any(k in text for k in ("几点", "时间", "date", "time", "今天")):
            return {"tool": "now", "args": {}}

        if text.startswith("记") or "笔记" in text:
            body = re.sub(r"^(记录|记一下|记)\s*[:：]?\s*", "", text)
            return {"tool": "note_write", "args": {"text": body, "path": self.notes_path}}

        if re.search(r"(?is)\bselect\b", text):
            sql = re.search(r"(?is)(select[\s\S]+)$", text).group(1).strip()
            return {"tool": "sqlite_query", "args": {"sql": sql}}

        return {"final": "这个我做不到（mock 后端只支持算术、时间、记笔记、SQL 查询四种意图）。"}


class DeepSeekLLM:
    """OpenAI-compatible chat-completions backend that uses native tool calling."""

    name = "deepseek"

    def __init__(self, model: str = "deepseek-chat",
                 base_url: str | None = None,
                 api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url = (base_url or os.environ.get("DEEPSEEK_BASE_URL")
                         or "https://api.deepseek.com").rstrip("/")
        self.model = model
        if not self.api_key:
            raise LLMError("DEEPSEEK_API_KEY is not set")

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + self.api_key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise LLMError("request failed: %s" % exc) from exc

    def plan(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": [{"type": "function", "function": t} for t in tools],
            "tool_choice": "auto",
            "temperature": 0.2,
        }
        body = self._post(payload)
        try:
            message = body["choices"][0]["message"]
        except (KeyError, IndexError) as exc:
            raise LLMError("unexpected response shape: %s" % body) from exc

        calls = message.get("tool_calls") or []
        if calls:
            call = calls[0]
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
            except json.JSONDecodeError as exc:
                raise LLMError("model returned invalid JSON arguments") from exc
            return {"tool": call["function"]["name"], "args": args,
                    "assistant": message}
        return {"final": (message.get("content") or "").strip(), "assistant": message}


def build_llm(mode: str = "auto", model: str = "deepseek-chat"):
    """Pick a backend: explicit 'mock'/'deepseek', or 'auto' = deepseek if keyed."""
    if mode == "mock":
        return MockLLM()
    if mode == "deepseek":
        return DeepSeekLLM(model=model)
    if os.environ.get("DEEPSEEK_API_KEY"):
        try:
            return DeepSeekLLM(model=model)
        except LLMError:
            return MockLLM()
    return MockLLM()
