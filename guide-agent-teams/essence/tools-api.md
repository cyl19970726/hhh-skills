# Agent Teams Tools API

## TeamCreate

创建团队 + 对应 task list。

```json
{
  "team_name": "my-project",
  "description": "Working on feature X",
  "agent_type": "researcher"  // 可选：lead 角色类型
}
```

创建后：
- `~/.claude/teams/{team-name}/config.json`（成员列表）
- `~/.claude/tasks/{team-name}/`（共享 task list）

## TeamDelete

删除团队和 task 目录。**必须先 shutdown 所有 teammates**，否则失败。

## SendMessage

### message（DM 单人，首选）

```json
{
  "to": "researcher",             // teammate name（必须，不是 agentId）
  "message": "请检查 auth 模块",  // 消息内容字符串（必须）
  "summary": "请求检查 auth 模块" // 5-10 字预览（必须）
}
```

### broadcast（发给所有人，慎用）

```json
{
  "to": "*",
  "message": "发现关键阻塞，请暂停",
  "summary": "关键阻塞通知"
}
```

### shutdown_request（请求 teammate 关闭）

```json
{
  "to": "researcher",
  "message": { "type": "shutdown_request", "reason": "任务完成，关闭 session" }
}
```

### shutdown_response（回应关闭请求）

```json
// 同意关闭
{ "type": "shutdown_response", "request_id": "abc-123", "approve": true }

// 拒绝关闭
{
  "type": "shutdown_response",
  "request_id": "abc-123",
  "approve": false,
  "content": "还在处理 task #3"
}
```

**关键**：收到 shutdown_request 后必须用此 tool 回应，不能只文本回复。

### plan_approval_response（审批 plan）

```json
// 批准
{
  "type": "plan_approval_response",
  "request_id": "abc-123",
  "recipient": "architect",
  "approve": true
}

// 驳回
{
  "type": "plan_approval_response",
  "request_id": "abc-123",
  "recipient": "architect",
  "approve": false,
  "content": "请补充错误处理方案"
}
```

## Task 工具

### TaskCreate

```json
{
  "subject": "重构 auth 模块",           // 祈使句标题
  "description": "详细描述...",           // 上下文和验收标准
  "activeForm": "重构 auth 模块中"        // 进行时形式（spinner 显示）
}
```

新任务默认 status=pending，无 owner。

### TaskUpdate

```json
{
  "taskId": "1",
  "status": "in_progress",    // pending → in_progress → completed | deleted
  "owner": "executor-1",      // 分配给 teammate
  "addBlockedBy": ["2"],      // 依赖关系
  "addBlocks": ["3"]          // 被依赖关系
}
```

### TaskList

无参数。返回所有任务摘要（id, subject, status, owner, blockedBy）。

### TaskGet

```json
{ "taskId": "1" }
```

返回完整详情（含 description, blocks, blockedBy）。

## Task tool (Spawn Teammates)

通过 Task tool 的 `team_name` 参数 spawn teammate 加入团队：

```json
{
  "subagent_type": "general-purpose",
  "name": "executor-1",
  "team_name": "my-project",
  "mode": "plan",              // 可选：要求 plan approval
  "prompt": "你是 Executor...",
  "description": "执行重构任务"
}
```

**mode 选项**：
- `"default"` — 正常模式
- `"plan"` — plan mode，只读直到 lead approve
- `"delegate"` — 只能协调，不能写代码
- `"bypassPermissions"` — 跳过权限确认

## Hooks（质量门控）

### TeammateIdle

teammate 即将 idle 时触发。exit code 2 → 发送反馈并让 teammate 继续工作。

### TaskCompleted

任务被标记 completed 时触发。exit code 2 → 阻止完成并发送反馈。

## 团队发现

Teammates 读取 config 发现其他成员：

```json
// ~/.claude/teams/{team-name}/config.json
{
  "members": [
    { "name": "executor-1", "agentId": "uuid", "agentType": "general-purpose" }
  ]
}
```

**始终用 name 引用 teammate**，不用 agentId。
