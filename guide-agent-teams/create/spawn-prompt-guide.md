# Spawn Prompt 设计指南

## Agent Definition Files（推荐：角色复用）

将 spawn prompt 提前写入 `.claude/agents/<name>.md`，spawn 时只需 `subagent_type: "<name>"` 引用，无需内联完整 prompt。

### 文件格式

```markdown
---
name: cs2-ops-strategy-domain          # subagent_type 引用这个值
description: "用途描述（可选触发提示）"
model: haiku                            # 可选：固定模型
---

# 角色标题

角色的完整系统提示（状态机 / 约束 / loop 指令）...
```

### Resolution 规则

| 优先级 | 位置 | 作用域 |
|--------|------|--------|
| 1 | managed settings | 组织级 |
| 2 | `--agents` CLI flag | 当前 session |
| 3 | `.claude/agents/` | 当前项目 ✅ 我们用这个 |
| 4 | `~/.claude/agents/` | 所有项目 |
| 5 | plugin `agents/` | plugin 范围 |

**关键规则**：
- `subagent_type` = 文件 frontmatter 的 `name` 字段，**不是**文件路径
- 子目录不创建命名空间，只是文件组织
- **三者统一命名约定**：skill name = agent 目录名 = team_name = name 前缀
  ```
  skill:        guide-cs2-living
  team_name:    "guide-cs2-living"
  agents dir:   .claude/agents/guide-cs2-living/
  agent name:   guide-cs2-living-strategy-domain
  ```
- 每个 workflow skill 对应一个 agents 子目录 + 一个 agent team，三者绑定

### Spawn 对比

**旧方式（内联 prompt）**：
```javascript
Agent({
  subagent_type: "general-purpose",
  team_name: "cs2-ops",
  name: "strategy-domain-1",
  model: "haiku",
  prompt: `...200行完整状态机...`
})
```

**新方式（definition 引用）**：
```javascript
Agent({
  subagent_type: "cs2-ops-strategy-domain",  // 引用 .claude/agents/cs2-ops/strategy-domain.md
  team_name: "cs2-ops",
  name: "strategy-domain-1",
  prompt: "你是 strategy-domain-1，domain_number=1。立刻 ScheduleWakeup(30s) 等待 ASSIGN。"
})
```

definition body 会**追加**到 system prompt（不是替代），spawn 的 `prompt` 负责 instance-specific 参数。

---

## 8 项 Checklist

```
[ ] 1. 角色定义（你是谁，职责边界）
[ ] 2. 明确 deliverable（文件名/数字，不只是"分析"）
[ ] 3. 数据/文件路径（具体路径，不依赖猜测）
[ ] 4. 状态机定义（IDLE→...→IDLE 完整路径）
[ ] 5. 消息协议（收哪些/发哪些，格式）
[ ] 6. 约束边界（不做什么）
[ ] 7. 关键铁律（如 POLY_EXECUTION_MODE=builder）
[ ] 8. 启动行为（上线即执行首次检查）
```

## 持久 Member Prompt 模板

```
你是 [角色名]（模型：[Haiku/Sonnet]）。

## 职责
[2-3条核心职责]

## 不做
[2-3条明确边界]

## 状态机
IDLE
  ↓ 收到 ASSIGN
  [完整状态转移...]

## 消息协议
收到：[格式]
发送：[格式]

## 关键铁律
[来自 spec 的不可违反规则]

## 启动
上线后立即执行首次[检查/审计]，然后进入主 loop（ScheduleWakeup([N]s)）。
```

## 按需 Subagent Prompt 模板

```
你是 [角色名]。

## 任务
[具体步骤，每步有明确交付物]

## 数据来源
[具体文件路径或命令]

## 输出
保存至：[具体路径/文件名]

完成后输出摘要。
```

## 常见错误

| 错误 | 症状 | 修复 |
|------|------|------|
| Deliverable 模糊 | Agent 做计划而非执行 | 要求具体文件名或数字 |
| 无状态机 | 完成一轮后 idle 不循环 | 定义完整 IDLE→...→IDLE |
| 无消息协议 | 完成但不汇报 | 明确 SendMessage 格式和时机 |
| 约束边界缺失 | Agent 越权操作 | 明确"不做"列表 |
| 首次检查等 loop | 上线很久才开始工作 | 加"上线即执行首次检查" |
