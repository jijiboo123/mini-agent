import json
import os
import sqlite3

import pytest

from agent.core import Agent
from agent.llm import MockLLM
from agent.tools import Tool, ToolError, ToolRegistry, builtin_registry


class AlwaysCallsTool:
    name = "always"

    def plan(self, messages, tools):
        return {"tool": "now", "args": {}}


class NeverFinishes:
    name = "never"

    def plan(self, messages, tools):
        return {"tool": "calc", "args": {"expression": "1+1"}}


def test_calc_runs_through_the_loop():
    agent = Agent(llm=MockLLM(), max_steps=4)
    answer = agent.run("帮我算 12*(3+4)")
    assert "84" in answer
    assert agent.steps[0].tool == "calc"


def test_now_tool():
    agent = Agent(llm=MockLLM(), max_steps=4)
    answer = agent.run("现在几点了")
    assert "iso" in answer


def test_note_write_appends(tmp_path):
    notes = tmp_path / "notes.md"
    agent = Agent(llm=MockLLM(notes_path=str(notes)), max_steps=4)
    agent.run("记一下：明天投金一禾测试岗")
    assert notes.exists()
    assert "明天投金一禾测试岗" in notes.read_text(encoding="utf-8")


def test_unknown_tool_raises():
    registry = builtin_registry()
    with pytest.raises(ToolError):
        registry.call("rm_rf", {})


def test_missing_argument_is_reported():
    registry = builtin_registry()
    with pytest.raises(ToolError):
        registry.call("calc", {})


def test_wrong_type_is_reported():
    registry = builtin_registry()
    with pytest.raises(ToolError):
        registry.call("sqlite_query", {"sql": "select 1", "limit": "ten"})


def test_unknown_argument_is_reported():
    registry = builtin_registry()
    with pytest.raises(ToolError):
        registry.call("calc", {"expression": "1+1", "verbose": "yes"})


def test_tool_error_becomes_an_observation():
    agent = Agent(llm=MockLLM(), max_steps=3)

    class BadPlanner:
        name = "bad"

        def plan(self, messages, tools):
            return {"tool": "calc", "args": {}}

    agent.llm = BadPlanner()
    answer = agent.run("算点东西")
    assert "step limit" in answer
    assert agent.steps[0].kind == "error"
    assert "missing required argument" in agent.steps[0].observation


def test_max_steps_bounds_the_run():
    agent = Agent(llm=NeverFinishes(), max_steps=3)
    answer = agent.run("一直算")
    assert "step limit" in answer
    assert len([s for s in agent.steps if s.kind == "tool"]) == 3


def test_trace_file_has_every_step(tmp_path):
    trace = tmp_path / "trace.jsonl"
    agent = Agent(llm=MockLLM(), max_steps=4, trace_path=str(trace))
    agent.run("帮我算 6*7")
    lines = [json.loads(l) for l in trace.read_text(encoding="utf-8").splitlines()]
    assert lines[0]["tool"] == "calc"
    assert lines[-1]["kind"] == "final"
    assert "42" in json.dumps(lines, ensure_ascii=False)


def test_memory_roundtrip(tmp_path):
    memory = tmp_path / "session.json"
    first = Agent(llm=MockLLM(), max_steps=3, memory_path=str(memory))
    first.run("现在几点")
    assert memory.exists()

    second = Agent(llm=MockLLM(), max_steps=3, memory_path=str(memory))
    assert any(m["role"] == "user" and "现在几点" in m["content"] for m in second.messages)


def test_sqlite_tool_reads_a_database(tmp_path, monkeypatch):
    db = tmp_path / "demo.db"
    connection = sqlite3.connect(db)
    connection.execute("create table jobs (company text, role text, status text)")
    connection.executemany("insert into jobs values (?,?,?)", [
        ("金一禾", "软件测试实习", "已投"),
        ("中芯量宇", "工程师助理", "未投"),
    ])
    connection.commit()
    connection.close()
    monkeypatch.setenv("MINI_AGENT_DB", str(db))

    registry = builtin_registry()
    result = json.loads(registry.call("sqlite_query", {"sql": "select company, role from jobs"}))
    assert result["rows"][0] == ["金一禾", "软件测试实习"]


def test_sqlite_tool_refuses_writes(tmp_path, monkeypatch):
    db = tmp_path / "demo.db"
    sqlite3.connect(db).close()
    monkeypatch.setenv("MINI_AGENT_DB", str(db))
    registry = builtin_registry()
    with pytest.raises(ToolError):
        registry.call("sqlite_query", {"sql": "delete from jobs"})


def test_duplicate_registration_is_rejected():
    registry = ToolRegistry()
    tool = Tool("echo", "echo text", {"type": "object", "properties": {"text": {"type": "string"}},
                                      "required": ["text"]}, lambda text: text)
    registry.register(tool)
    with pytest.raises(ToolError):
        registry.register(tool)
