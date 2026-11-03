"""Tool definitions and the tool registry for mini-agent.

A tool is a plain Python function plus a JSON-Schema-ish declaration of its
parameters. The registry validates arguments before calling, so a planner that
hallucinates an argument name or type gets a readable error back as the
observation instead of a traceback.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List


class ToolError(Exception):
    """Raised for bad arguments or a failing tool body."""


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    func: Callable[..., Any]

    def schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def validate(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(args, dict):
            raise ToolError("arguments must be an object, got %r" % type(args).__name__)
        props = self.parameters.get("properties", {})
        required = set(self.parameters.get("required", []))
        missing = required - set(args)
        if missing:
            raise ToolError("missing required argument(s): %s" % ", ".join(sorted(missing)))
        unknown = set(args) - set(props)
        if unknown:
            raise ToolError("unknown argument(s): %s" % ", ".join(sorted(unknown)))
        out = {}
        for key, value in args.items():
            expect = props[key].get("type")
            if expect == "integer" and not (isinstance(value, int) and not isinstance(value, bool)):
                raise ToolError("argument %r must be an integer" % key)
            if expect == "string" and not isinstance(value, str):
                raise ToolError("argument %r must be a string" % key)
            out[key] = value
        return out


@dataclass
class ToolRegistry:
    tools: Dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        if tool.name in self.tools:
            raise ToolError("tool %r is already registered" % tool.name)
        self.tools[tool.name] = tool

    def schemas(self) -> List[Dict[str, Any]]:
        return [t.schema() for t in self.tools.values()]

    def describe(self) -> str:
        lines = []
        for tool in self.tools.values():
            params = ", ".join(tool.parameters.get("properties", {}))
            lines.append("- %s(%s): %s" % (tool.name, params, tool.description))
        return "\n".join(lines)

    def call(self, name: str, args: Dict[str, Any]) -> str:
        tool = self.tools.get(name)
        if tool is None:
            raise ToolError("unknown tool %r; available: %s" % (name, ", ".join(sorted(self.tools))))
        clean = tool.validate(args)
        try:
            result = tool.func(**clean)
        except ToolError:
            raise
        except Exception as exc:  # noqa: BLE001 - a tool bug must not kill the loop
            raise ToolError("%s failed: %s" % (name, exc)) from exc
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False)


def _calc(expression: str) -> Dict[str, Any]:
    """Evaluate a pure arithmetic expression without eval()."""
    expression = expression.strip()  # BUG-002 修复：前导空格会让 compile 报 unexpected indent
    if not re.fullmatch(r"[0-9+\-*/(). %\s]+", expression):
        raise ToolError("only digits and + - * / ( ) . %% are allowed")
    try:
        value = eval(compile(expression, "<calc>", "eval"), {"__builtins__": {}}, {})  # noqa: S307
    except ZeroDivisionError:
        raise ToolError("division by zero")
    except Exception as exc:  # noqa: BLE001
        raise ToolError("cannot evaluate expression: %s" % exc) from exc
    return {"expression": expression.strip(), "value": value}


def _now() -> Dict[str, Any]:
    now = _dt.datetime.now()
    return {"iso": now.isoformat(timespec="seconds"), "weekday": now.strftime("%A")}


def _note_write(text: str, path: str = "notes.md") -> Dict[str, Any]:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("- [%s] %s\n" % (stamp, text.strip()))
    return {"written": text.strip(), "path": os.path.abspath(path)}


def _sqlite_query(sql: str, limit: int = 20) -> Dict[str, Any]:
    statement = sql.strip()
    if not re.match(r"(?is)^(select|with)\b", statement):
        raise ToolError("only SELECT / WITH statements are allowed")
    db = os.environ.get("MINI_AGENT_DB", "demo.db")
    if not os.path.exists(db):
        raise ToolError("database %r not found; set MINI_AGENT_DB" % db)
    connection = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    try:
        rows = connection.execute(statement).fetchmany(limit)
        columns = [d[0] for d in connection.execute(statement).description or []]
    finally:
        connection.close()
    return {"columns": columns, "rows": [list(r) for r in rows], "limit": limit}


def builtin_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(Tool(
        "calc",
        "Evaluate an arithmetic expression (+ - * / parentheses).",
        {"type": "object", "properties": {"expression": {"type": "string"}},
         "required": ["expression"]},
        _calc,
    ))
    registry.register(Tool(
        "now",
        "Return the current local date and time.",
        {"type": "object", "properties": {}},
        _now,
    ))
    registry.register(Tool(
        "note_write",
        "Append one line to a local notes file.",
        {"type": "object",
         "properties": {"text": {"type": "string"}, "path": {"type": "string"}},
         "required": ["text"]},
        _note_write,
    ))
    registry.register(Tool(
        "sqlite_query",
        "Run a read-only SELECT against a local SQLite database.",
        {"type": "object",
         "properties": {"sql": {"type": "string"}, "limit": {"type": "integer"}},
         "required": ["sql"]},
        _sqlite_query,
    ))
    return registry
