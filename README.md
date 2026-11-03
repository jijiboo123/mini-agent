# mini-agent

一个从零实现的**最小可用 Agent 运行时**（Python 3.11+，零第三方运行时依赖）。
不是调用某个 Agent 框架的壳子，而是把 Agent 最核心的四件事自己写了一遍：

1. **工具注册与参数校验**：工具用 JSON Schema 描述，调用前校验必填项、类型、未知参数；
2. **ReAct 循环**：`规划 → 调工具 → 读观察 → 再规划`，最大步数有上界，工具报错不炸循环；
3. **可插拔 LLM 后端**：`MockLLM`（规则规划器，离线/测试用）+ `DeepSeekLLM`（OpenAI 兼容接口，原生 `tool_calls`）；
4. **可观测性**：每一步写 JSONL trace，会话可持久化到 JSON。

## 为什么做这个

学 Agent 应用开发最容易停在"会调 API"，难的是讲清**一次工具调用在系统里怎么流动**：
谁决定调哪个工具、参数错了谁兜、工具失败后模型怎么恢复、怎么复现一次失败的运行。
这个项目把这条链路压缩到约 500 行，可以完整读懂并向别人解释。

## 快速开始

```bash
# 1) 不需要任何 key，先用离线后端跑通
python -m agent.cli "帮我算 12*(3+4)" --backend mock

# 2) 看看注册了哪些工具
python -m agent.cli --tools

# 3) 接真实模型（任何 OpenAI 兼容端点：DeepSeek / Moonshot / 本地 vLLM）
export DEEPSEEK_API_KEY=sk-xxx          # Windows: set DEEPSEEK_API_KEY=sk-xxx
python -m agent.cli "现在几点，然后把时间记到笔记里" --backend deepseek --session demo

# 4) 跑测试
pip install pytest && python -m pytest tests -q
```

输出示例：

```
backend: mock | tools: calc, now, note_write, sqlite_query
  step 1  calc(expression=12*(3+4)) -> {"expression": "12*(3+4)", "value": 84}
answer: 完成。工具返回：{"expression": "12*(3+4)", "value": 84}
```

## 结构

```
agent/
  tools.py   Tool / ToolRegistry / 四个内置工具（calc、now、note_write、sqlite_query）
  llm.py     MockLLM（规则规划器）+ DeepSeekLLM（OpenAI 兼容 tool_calls）+ build_llm
  core.py    Agent：ReAct 循环、步数上界、错误兜底、JSONL trace、会话记忆
  cli.py     命令行入口
tests/
  test_agent.py  14 个用例：工具校验 / 循环 / 步数上限 / trace / 记忆 / SQLite 只读
docs/
  面试问答.md    这个项目的 12 个必答问题
```

## 内置工具

| 工具 | 作用 | 安全约束 |
|---|---|---|
| `calc` | 算术表达式求值 | 白名单字符 + 空 `__builtins__`，不用裸 `eval` |
| `now` | 当前时间（ISO + 星期） | 无副作用 |
| `note_write` | 追加一行到笔记文件 | 只能追加，不改历史 |
| `sqlite_query` | 对本地 SQLite 跑 `SELECT`/`WITH` | 只读连接（`mode=ro`）+ 语句前缀校验 + 行数上限 |

## 三个设计决定（面试常问）

1. **工具错误为什么变成 observation 而不是异常？** Agent 的价值在于"出错后能自我纠正"。如果工具异常直接抛出，循环就断了；返回 `ERROR: ...` 作为观察，模型下一步有机会换个参数或换个工具重试。
2. **为什么要有 `max_steps`？** 没有上界的 Agent 会烧钱、会死循环。上界让"跑不完"成为一种明确的结果（`Reached the step limit`），而不是进程挂住。
3. **为什么同时保留 Mock 和真实后端？** 测试和 CI 不能依赖网络和 API key。Mock 是确定性的规则规划器，用同一套 `plan()` 接口，于是循环、校验、trace 全部可以离线测。

## 已知限制

- Mock 后端只认四种意图，不是真正的语言理解，它存在的意义是让测试确定、离线可跑；
- 单轮只执行一个工具调用（多工具并行/嵌套留给后续版本）；
- 记忆是整段 messages 的 JSON 快照，没有压缩和检索；
- 没有沙箱隔离：工具函数拥有当前进程的全部文件权限。

## License

MIT
