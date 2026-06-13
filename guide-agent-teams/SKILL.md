---
name: guide-agent-teams
description: |
  Claude Code Agent Teams 完整使用指南：多 session 协作、共享任务、inter-agent 通信。
  包含 Lead 管理方法论（Spawn 设计原则、协调模式、纠正策略、知识提取时机）。

  使用场景：(1) 创建和管理 agent team (2) 设计 spawn prompt 和角色分工
  (3) 理解 tools API（TeamCreate/SendMessage/Task*/EnterPlanMode）
  (4) 排查 agent teams 问题（teammate 不出现、权限、shutdown）
  (5) 对比 subagents vs agent teams 选型
  (6) Lead 准备创建 agent team 前参考 spawn prompt 设计清单
  (7) 协调并行 agents 时选择合适的协调模式
  (8) Agent 偏离任务时应用 3-level 纠正策略
  (9) 决定何时提取知识到 guide-*/observe-* skills
status: active
domain: pm
depends_on: [workflow-pm]
blocks: []
updated: 2026-04-20
---

# guide-agent-teams — Agent Team 完整指南

> 两大功能：(1) 理解 Agent Teams 原理  (2) 构建新的 Agent Team Workflow

---

## 快速导航

### 理解原理（essence/）

| 需求 | 文档 |
|------|------|
| 核心概念 + Subagents vs Teams | [essence/overview.md](essence/overview.md) |
| Tools API 完整参考 | [essence/tools-api.md](essence/tools-api.md) |
| 最佳实践 + 排障 + 已知限制 | [essence/best-practices.md](essence/best-practices.md) |
| Lead 管理方法论（spawn/协调/纠正） | [essence/lead-methodology.md](essence/lead-methodology.md) |
| 反模式（6条实盘验证） | [essence/anti-patterns.md](essence/anti-patterns.md) |

### 构建 Workflow（create/）

| 需求 | 文档 |
|------|------|
| 判断是否需要 Agent Team | [create/decision-matrix.md](create/decision-matrix.md) |
| 角色设计（Lead/Domain/Monitor/Fix） | [create/role-templates.md](create/role-templates.md) |
| 状态机设计 | [create/state-machine.md](create/state-machine.md) |
| 消息协议设计 | [create/message-protocol.md](create/message-protocol.md) |
| Spawn Prompt 8-item checklist + **Agent Definition Files** | [create/spawn-prompt-guide.md](create/spawn-prompt-guide.md) |
| Member vs Subagent 判断树 | [create/spawn-decision-tree.md](create/spawn-decision-tree.md) |
| CS2 实盘 Workflow 模板 | [create/workflow-templates/live-ops-template.md](create/workflow-templates/live-ops-template.md) |
| 回测 Workflow 模板 | [create/workflow-templates/backtest-template.md](create/workflow-templates/backtest-template.md) |

---

## 启用

```json
{ "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" } }
```
