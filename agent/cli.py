"""Command line entry point: python -m agent.cli "帮我算 12*(3+4)" """

from __future__ import annotations

import argparse
import sys

from .core import Agent
from .llm import build_llm
from .tools import builtin_registry


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="mini-agent", description="A minimal tool-using agent.")
    parser.add_argument("task", nargs="?", help="what you want the agent to do")
    parser.add_argument("--backend", choices=["auto", "mock", "deepseek"], default="auto",
                        help="auto = deepseek if DEEPSEEK_API_KEY is set, otherwise mock")
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--max-steps", type=int, default=6)
    parser.add_argument("--session", help="remember the conversation in .sessions/<name>.json")
    parser.add_argument("--trace", help="append a JSONL trace of every step to this file")
    parser.add_argument("--tools", action="store_true", help="list the registered tools and exit")
    args = parser.parse_args(argv)

    registry = builtin_registry()
    if args.tools:
        print(registry.describe())
        return 0
    if not args.task:
        parser.error("a task is required unless --tools is given")

    llm = build_llm(args.backend, model=args.model)
    memory = ".sessions/%s.json" % args.session if args.session else None
    agent = Agent(registry=registry, llm=llm, max_steps=args.max_steps,
                  trace_path=args.trace, memory_path=memory)

    print("backend: %s | tools: %s" % (getattr(llm, "name", "?"), ", ".join(registry.tools)))
    answer = agent.run(args.task)
    for step in agent.steps:
        if step.kind == "tool":
            print("  step %d  %s(%s) -> %s" % (step.index, step.tool,
                                               ", ".join("%s=%s" % kv for kv in step.args.items()),
                                               step.observation[:120]))
        elif step.kind == "error":
            print("  step %d  %s failed -> %s" % (step.index, step.tool, step.observation[:120]))
    print("answer:", answer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
