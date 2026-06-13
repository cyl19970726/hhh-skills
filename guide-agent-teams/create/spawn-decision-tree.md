# Spawn 决策树

## Member vs Subagent

```
需要 spawn？
  ├─ 任务 < 30min → 按需 Subagent（Agent tool，无 team_name）
  ├─ 需要 ScheduleWakeup loop → 持久 Member（Agent with team_name + name）
  ├─ 需要接收 push 消息（SendMessage） → 持久 Member
  └─ 其他长时任务 → 长时 Subagent（run_in_background: true）
```

## 模型选择

> 代码中 model 字段使用简称：`"sonnet"` = claude-sonnet-4-6，`"haiku"` = claude-haiku-4-5

| 角色 | 模型 | 理由 |
|------|------|------|
| Lead / Fix / Workflow / Evaluator | Sonnet | 需要推理和决策 |
| Domain / Monitor / Data | Haiku | 执行为主，成本优化 |
| 综合报告 / 回顾分析 | Sonnet | 需要跨域综合推理 |

## Spawn 代码模板

```javascript
// 持久 Member
Agent({
  team_name: "my-team",
  name: "domain-1",
  model: "haiku",
  mode: "bypassPermissions",
  prompt: "...",
  run_in_background: true
})

// 按需 Subagent（不加入 team）
Agent({
  model: "sonnet",
  mode: "bypassPermissions",
  prompt: "...",
  run_in_background: true
})
```

## 权限最佳实践

- 持久 Member 用 `mode: "bypassPermissions"` → 避免权限弹窗阻塞 loop
- 按需 Subagent 同上
- **不要依赖 team lead 审批**：Member 的每次 tool 调用都可能需要审批，严重影响自动化
