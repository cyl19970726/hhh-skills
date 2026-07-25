# Codex rollout JSONL 字段真值表

全部条目为实测所得。标 ⚠️ 的与既有文档/既有 skill 的假设不符——上一代 skill 正是死在这些点上。

## 环境（2026-07 实测）

```
~/.codex/sessions/YYYY/MM/DD/rollout-<ISO>-<thread-id>.jsonl    5548 个   48 GB
~/.codex/archived_sessions/rollout-...jsonl                              13 GB   ⚠️ 扁平目录，无年月分层
~/.codex/session_index.jsonl                                    2980 行   ⚠️ 仅覆盖 2980/5548
最大单文件                                                       1.5 GB
```

⚠️ 不要对 61 GB 跑全库 `rg`。定位走 `session_index.jsonl`（含 `thread_name`）+ `find -name '*<id>*'`。

## 顶层记录类型

| type | 说明 |
|---|---|
| `session_meta` | 会话元信息。⚠️ **单文件可含数十个**（实测 11 / 48）——"一文件 = 一会话"假设是错的 |
| `response_item` | 消息、reasoning、工具调用与输出 |
| `event_msg` | 生命周期事件 |
| `turn_context` | 每轮环境元数据 |
| `world_state` | ⚠️ 存在但未被任何既有文档记录 |
| `compacted` | 上下文压缩标记，`payload.replacement_history` 为压缩后保留项 |

⚠️ 因为存在多个 `session_meta`，对全文件取 `min/max timestamp` 会跨线程混算出假的时间范围。

## `response_item` 的 payload.type

| payload.type | 关键字段 |
|---|---|
| `message` | `role` ∈ {user, assistant, developer}，`content[]`（`text` / `input_text`） |
| `reasoning` | 模型思考项，属**叙事流** |
| `function_call` | `name`, `arguments`(JSON 字符串) ⚠️ 上一代 skill 只抓 output 不抓 call → 有结果无动作 |
| `function_call_output` | `output` |
| `custom_tool_call` / `custom_tool_call_output` | ⚠️ 上一代 skill **整类丢弃**（实测单会话各 20 次） |

常见 `name`：`exec` `exec_command` `apply_patch` `view_image` `update_plan`
`spawn_agent` `wait_agent` `list_agents` `send_message` `read_thread` `interrupt_agent`
`followup_task` `create_goal` `get_goal` `write_stdin`

`apply_patch` 的目标从 `arguments` 里用 `\*\*\* (Update|Add|Delete) File: (.+)` 提取。

## `event_msg` 的 payload.type

| payload.type | 关键字段 |
|---|---|
| `token_count` | `info.last_token_usage.input_tokens`（当轮上下文长度）、`info.model_context_window` |
| `agent_message` | ⚠️ 键为 `(memory_citation, message, phase, type)` — **没有 `author`**。上一代 skill 在 `response_item/agent_message` 里找 `author`，结果恒为空且不报错，会被误读为"无 subagent" |
| `sub_agent_activity` | `agent_thread_id`, `agent_path`, `kind` — ⚠️ **这才是真正的 subagent 信号**，两个既有脚本都没用 |
| `user_message` `agent_reasoning` `task_started` `task_complete` `context_compacted` `thread_settings_applied` | |

⚠️ `sub_agent_activity.agent_thread_id` 在 `sessions/` 下**找不到对应文件**——子 agent 记录被 inline
进父文件（这也解释了多个 `session_meta`）。机制未完全验证，但现象稳定复现。

## 伪装成 user 的注入块

以下带 `role: user` 但**不是用户**。漏过任何一类都会污染目标演化判定：

```
<in-app-browser-context     <recommended_plugins>     <environment_context>
<codex_internal_context     <system-reminder          <INSTRUCTIONS>
AGENTS.md instructions for  # Files mentioned by the user:
```

实证：某会话粗筛得 57 条"用户消息"，正确过滤后仅 35 条实质消息 + 15 条纯"继续" + 11 条注入。

## 上下文动态的读法

`token_count` 的 `last_token_usage.input_tokens` ≈ 当轮上下文长度。
按 `compacted` 行号切段，取每段首值为 floor、最大值为 peak：

```
段   压缩后地板   峰值      turns        window = 258,400
 0     26,280   234,840     60
 9     34,640   228,024    234
18     42,224   206,325    183
```

结论：**上下文不会越来越长**（每段回落），地板 18 次仅涨 61%；
致命的是每段丢约 195k 物证换约 900 token 叙事 = **~200:1**。

## 安全约束

- 必须流式逐行解析。⚠️ 既有 `session_extract.py` 用 `records = list(...)` 全量入内存，GB 级文件必炸。
- 绝不用 Read 工具打开 rollout 文件。
- Session JSONL 含系统/开发者指令、工具输出、本地路径、用户粘贴的密钥与加密内容。
  外发前脱敏，永远汇总而非转储原文。
- 加密的 compaction 摘要不可重建——**不要声称精确还原**。
