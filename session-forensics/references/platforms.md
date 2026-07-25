# 多平台适配

心智模型、签名表、失效表**全部与平台无关**——它们只依赖「两条流」这个抽象。
平台差异只在一件事上：**如何把一行原始记录映射成规范化事件**。

## 规范化事件

每个适配器只需产出这一种事件流，之后所有指标计算共用同一份代码：

```
(line_no, flow, kind, name, size)

flow   ∈ narrative | evidence | lifecycle | meta
kind   ∈ user_msg | assistant_msg | thinking | tool_call | tool_output
         | compaction | turn_complete | turn_aborted | token_count | session_meta | subagent
name     工具名 / 角色 / 事件名
size     字符数（tool_output 用它算 flood；token_count 用 input_tokens）
```

映射规则（各平台通用）：

```
narrative   assistant 文本、thinking/reasoning、计划、摘要
evidence    工具调用与其输出、补丁目标、失败/超时、用户消息
lifecycle   轮次开始/结束/中断、压缩
```

## Codex（已实现）

见 `references/codex-jsonl.md`。要点：

```
type=response_item  payload.type=message            → user_msg / assistant_msg
                    payload.type=reasoning          → thinking
                    payload.type=function_call      → tool_call   (name, arguments)
                    payload.type=custom_tool_call   → tool_call   ⚠️ 易漏
                    payload.type=*_output           → tool_output (output)
type=event_msg      payload.type=token_count        → token_count (info.last_token_usage.input_tokens)
                    payload.type=task_complete
                                 /turn_aborted
                                 /thread_rolled_back → lifecycle
                    payload.type=sub_agent_activity → subagent    (agent_path, agent_thread_id)
type=compacted                                      → compaction  (payload.replacement_history)
type=session_meta                                   → session_meta ⚠️ 单文件可有数十个
```

存储：`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`（5548 个 / 48 GB）+
`~/.codex/archived_sessions/`（扁平 / 13 GB）。索引 `session_index.jsonl` 仅覆盖 2980/5548。

## Claude Code（已实现）

存储：`~/.claude/projects/<escaped-cwd>/<session-uuid>.jsonl`
实测规模：**1307 个文件 / 2.2 GB**（比 Codex 小一个量级，全量扫描可行）。

顶层记录是**扁平**的，没有 Codex 那层 `payload`：

```
top-level keys: cwd, entrypoint, gitBranch, isSidechain, message,
                parentUuid, requestId|promptId, sessionId, type
```

映射：

```
type=user        message.role=user      message.content[]
type=assistant   message.role=assistant message.content[]
type=system                                            → lifecycle/meta
type=attachment                                        → evidence（文件/图片附带物）
type=ai-title / last-prompt / queue-operation          → meta（噪声，过滤）

message.content[] 的 item.type:
   text        → narrative
   thinking    → narrative      （对应 Codex 的 reasoning）
   tool_use    → tool_call      item.name, item.input
   tool_result → tool_output    item.content
```

实测某 400 行样本：`thinking 66 / text 62 / tool_use 94 / tool_result 93`，
工具 `Bash 56 / Edit 17 / Read 16 / Write 3 / mcp__* / AskUserQuestion`。

平台差异要点：

- **`isSidechain: true` 标记子 agent 记录** —— 这是 Claude Code 的 subagent 信号，
  对应 Codex 的 `sub_agent_activity`。子会话与主会话在**同一文件内**交织，
  统计时必须能按 `isSidechain` 拆分，否则主/子指标混算。
- **补丁目标从 `Edit`/`Write` 的 `input.file_path` 取**，不是从 `*** Update File:` 文本取。
  Codex 那条正则陷阱在此不适用，但要注意 `MultiEdit` 类工具的批量结构。
- **exec 对应 `Bash` 的 `input.command`。**
- **token 用量在 assistant 记录的 `message.usage`**，不是独立的 `token_count` 事件。
- **压缩标记已确认两种**：顶层 `isCompactSummary: true`，以及
  `type=system / subtype=compact_boundary`。二者都映射为 `compaction`。
- **轮次结束是近似值**：`type=system / subtype=stop_hook_summary` 映射为 `turn_complete`；
  `api_error` 与 `model_refusal_fallback` 映射为 `turn_aborted`。
- `parentUuid` 构成消息树，可用于重建分支/重试，Codex 没有等价物。

## Kimi Code（已实现）

存储：`~/.kimi-code/sessions/**/session_<uuid>/agents/<agent>/wire.jsonl`。
每个 agent 一份独立文件；需要完整主/子 agent 图时必须遍历同一 `agents/` 目录。

映射：

```
type=metadata                                      → session_meta
type=turn.prompt                                   → user_msg
type=context.append_message                        → user_msg / assistant_msg
type=context.append_loop_event
  event.type=tool.call                             → tool_call
  event.type=tool.result                           → tool_output
  event.type=content.part / part.type=think|text   → thinking / assistant_msg
  event.type=step.end                              → token_count + turn lifecycle
```

平台差异要点：

- 工具补丁目标从 `args.path` 或 `args.file_path` 取；命令从 `args.command` 取。
- `tool.result` 不重复工具名，只给 `toolCallId`；适配器用该 ID 与先前的 `tool.call`
  关联，不能靠“最近一次调用”猜测（同一步可先发多次 call、再批量返回 result）。
- token 用量来自 `step.end.usage` 的 `inputOther + inputCacheRead + inputCacheCreation`。
- `finishReason=stop|end_turn` 映射为 `turn_complete`；
  `aborted|cancelled|error` 映射为 `turn_aborted`。
- 当前实测语料没有可确认的压缩标记，所以 `compactions` 必须返回 `null`，不能返回 `0`。

## 适配器变更闸

⚠️ 修改 `iter_events` 或任何平台适配器后，既有代表会话的指标必须逐项对齐。
重构测量仪器却不校准，正是本 skill 反复检出的 B 类病
（仪器变更使全部历史证据失效）。**改完 `iter_events` 后，三个已审会话的指标必须与本文档记录的
数值完全一致，否则视为回归。**
