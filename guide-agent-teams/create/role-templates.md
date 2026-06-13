# Agent 角色模板

## 角色体系

```
Lead（战略决策）
  └── Manager（运营调度，可选）
        └── Domain Agent × N（执行层，并发）

  ├── Monitor Agent（健康巡检，持久）
  ├── Fix Agent（故障修复，STANDBY）
  └── Workflow Agent（流程审计，定时）
```

## Lead

**职责**：战略决策 + 资源分配 + 架构审批
**不做**：直接执行运营操作
**模型**：Sonnet | **生命周期**：整个 session

做：决定哪个工作单元值得跑 | 审批修复方案 | 分配资源
不做：直接给出执行命令 | 直接操作钱包/进程

## Manager（可选）

**判断标准**：并发 Domain ≥ 3 时建议独立 Manager；≤ 2 时 Lead 可兼任
**职责**：ASSIGN 分发、状态跟踪、Domain 协调
**模型**：Sonnet | **生命周期**：持久 Member

## Domain Agent

**职责**：单一工作单元完整生命周期
**设计原则**：对外只发消息不做跨域决策；遇到超出能力的问题 → BUG_DETECTED
**模型**：Haiku（执行为主）| **生命周期**：持久 Member，状态机循环

## Monitor / Workflow Agent

**职责**：定时健康巡检，发现问题上报，不处理问题
**铁律**：上线即执行首次检查（不等第一个 interval）
**模型**：Haiku | **生命周期**：持久 Member，定时 loop

## Fix Agent

**职责**：BUG_DETECTED → 分层诊断（10问）→ spawn 子 agent 修复
**铁律**：常驻 STANDBY，不主动 loop；修复后发 FIX_COMPLETE
**模型**：Sonnet | **生命周期**：持久 Member，被动响应

## 持久 Member vs 按需 Subagent

| 标准 | 持久 Member | 按需 Subagent |
|------|------------|--------------|
| 生命周期 | > 1h，跨 session | 单任务，完成即退出 |
| 消息交互 | 需要接收 push 消息 | 只需返回结果 |
| 主动 loop | 有 ScheduleWakeup | 无 loop |
| 典型角色 | Domain / Monitor / Fix | 数据拉取 / 报告生成 |
