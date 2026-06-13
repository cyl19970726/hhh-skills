# Agent Teams 核心概念

## 启用

```json
// settings.json
{ "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" } }
```

## 核心概念

| 组件 | 职责 |
|------|------|
| **Team Lead** | 创建团队、spawn teammates、协调分配、综合结果 |
| **Teammates** | 独立 Claude Code 实例，各自处理分配的任务 |
| **Task List** | 共享任务列表，teammates 认领和完成 |
| **Mailbox** | Agent 间通信系统，消息自动送达 |

**存储位置**：
- Team config: `~/.claude/teams/{team-name}/config.json`
- Task list: `~/.claude/tasks/{team-name}/`

## Subagents vs Agent Teams

| | Subagents | Agent Teams |
|---|---|---|
| **通信** | 只能向 caller 汇报 | Teammates 间直接通信 |
| **协调** | 主 agent 管理 | 共享 task list + 自协调 |
| **适用** | 聚焦任务，只需结果 | 需要讨论、挑战、协作 |
| **Token** | 低（结果摘要回主上下文） | 高（每 teammate 独立实例） |

**选择原则**：workers 需要互相通信 → Agent Teams；否则 → Subagents。

## Tools 速查

### 团队管理

```
TeamCreate    → 创建团队（自动创建 task list）
TeamDelete    → 删除团队（必须先 shutdown 所有 teammates）
```

### 通信（SendMessage）

```
type: "message"              → DM 单个 teammate（首选）
type: "broadcast"            → 发送给所有（谨慎，N 个 teammate = N 次送达）
type: "shutdown_request"     → 请求 teammate 关闭
type: "shutdown_response"    → 响应关闭请求（approve/reject + request_id）
type: "plan_approval_response" → 审批 teammate 的 plan（approve/reject + request_id）
```

### 任务管理

```
TaskCreate    → 创建任务（subject + description + activeForm）
TaskUpdate    → 更新状态/所有者/依赖（status: pending→in_progress→completed）
TaskList      → 列出所有任务
TaskGet       → 获取任务详情
```

### Plan 模式

Spawn teammate 时设置 `mode: "plan"`，teammate 只能读取不能修改，直到 lead approve plan。

## 关键工作流

### 1. 创建团队并分配任务

```
TeamCreate → TaskCreate (多个) → Task tool spawn teammates (带 team_name)
→ TaskUpdate 分配 owner → teammates 工作 → TaskUpdate completed
→ SendMessage shutdown_request → TeamDelete
```

### 2. Spawn Prompt 模板

```
你是 {角色名}。

任务：{具体描述}
相关文件：{关键路径列表}

使用 {skill 名} 按流程执行。
完成后 message {目标 teammate/lead}，附上结论摘要。
完成后请 shutdown。
```

**关键**：teammates 不继承 lead 的对话历史，必须在 spawn prompt 中包含所有必要上下文。

### 3. Plan Approval 流程

```
Lead spawn teammate (mode: "plan")
→ Teammate 探索代码、制定 plan、调用 ExitPlanMode
→ Lead 收到 plan_approval_request
→ Lead 发送 plan_approval_response (approve: true/false)
→ Teammate 退出 plan mode，开始实现
```

## 显示模式

| 模式 | 说明 | 快捷键 |
|------|------|--------|
| **In-process**（默认） | 全部在主终端 | Shift+Up/Down 选 teammate，Enter 查看，Escape 中断 |
| **Split panes** | 每个 teammate 独立面板 | 点击面板直接交互 |

```json
// settings.json
{ "teammateMode": "in-process" }  // 或 "tmux" 或 "auto"
```

Delegate mode（Shift+Tab）：限制 lead 只做协调，不写代码。
