"""The agent loop: plan -> call tool -> observe -> repeat, with tracing.

The loop owns three responsibilities and nothing else:

1. keep the message history in one canonical shape (so any backend can consume it),
2. bound the run (max steps, tool errors become observations, never exceptions),
3. record a machine-readable trace of every step for debugging and for the demo.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .llm import build_llm
from .tools import ToolError, ToolRegistry, builtin_registry

SYSTEM_PROMPT = (
    "You are a small tool-using agent. Solve the user's task by calling the "
    "provided tools one at a time, using each observation to decide the next "
    "step. When the task is done, answer with a short final message. Never "
    "claim a result you did not obtain from a tool."
)


@dataclass
class Step:
    index: int
    kind: str                      # "plan" | "tool" | "error" | "final"
    tool: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)
    observation: str = ""
    text: str = ""
    at: str = ""

    def as_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["at"] = self.at or _dt.datetime.now().isoformat(timespec="seconds")
        return data


@dataclass
class Agent:
    registry: ToolRegistry = field(default_factory=builtin_registry)
    llm: Any = None
    max_steps: int = 6
    trace_path: Optional[str] = None
    memory_path: Optional[str] = None
    system_prompt: str = SYSTEM_PROMPT
    messages: List[Dict[str, Any]] = field(default_factory=list)
    steps: List[Step] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.llm is None:
            self.llm = build_llm()
        if not self.messages:
            self.messages = [{"role": "system", "content": self.system_prompt}]
            if self.memory_path:
                self.load_memory()

    # -- memory ---------------------------------------------------------
    def save_memory(self) -> None:
        if not self.memory_path:
            return
        directory = os.path.dirname(os.path.abspath(self.memory_path))
        os.makedirs(directory, exist_ok=True)
        with open(self.memory_path, "w", encoding="utf-8") as fh:
            json.dump(self.messages, fh, ensure_ascii=False, indent=1)

    def load_memory(self) -> None:
        if not self.memory_path or not os.path.exists(self.memory_path):
            return
        with open(self.memory_path, encoding="utf-8") as fh:
            try:
                loaded = json.load(fh)
            except json.JSONDecodeError:
                return
        if isinstance(loaded, list) and loaded:
            self.messages = loaded

    # -- tracing --------------------------------------------------------
    def _trace(self, step: Step) -> None:
        if not self.trace_path:
            return
        directory = os.path.dirname(os.path.abspath(self.trace_path))
        os.makedirs(directory, exist_ok=True)
        with open(self.trace_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(step.as_dict(), ensure_ascii=False) + "\n")

    # -- the loop -------------------------------------------------------
    def run(self, task: str) -> str:
        self.messages.append({"role": "user", "content": task})
        for index in range(1, self.max_steps + 1):
            plan = self.llm.plan(self.messages, self.registry.schemas())
            if "final" in plan:
                text = str(plan["final"])
                step = Step(index, "final", text=text)
                self._finish(step)
                return text

            name = plan.get("tool") or ""
            args = plan.get("args") or {}
            self.messages.append({
                "role": "assistant",
                "content": json.dumps({"tool": name, "args": args}, ensure_ascii=False),
            })
            try:
                observation = self.registry.call(name, args)
                step = Step(index, "tool", tool=name, args=args, observation=observation)
            except ToolError as exc:
                observation = "ERROR: %s" % exc
                step = Step(index, "error", tool=name, args=args, observation=observation)
            self.messages.append({"role": "tool", "name": name, "content": observation})
            self._trace(step)
            self.steps.append(step)

        step = Step(self.max_steps + 1, "final",
                    text="Reached the step limit (%d) without a final answer." % self.max_steps)
        self._finish(step)
        return step.text

    def _finish(self, step: Step) -> None:
        self.steps.append(step)
        self._trace(step)
        self.messages.append({"role": "assistant", "content": step.text})
        self.save_memory()
