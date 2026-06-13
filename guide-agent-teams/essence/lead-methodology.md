# Lead 管理方法论

> 从 BTC 5m 研究 agent team 实战经验提炼。以下内容面向 Lead，指导如何高效协调 agent teams。

## 何时 Spawn Agent（决策框架）

| Task 特征 | 操作 | 理由 |
|-----------|------|------|
| <1h + 单一 action | Lead 自己做 | Spawn overhead 浪费 |
| >2h + 多步骤 | Spawn agent | 并行加速 + 专注 |
| 需要深度探索 | Spawn agent | Agent 可连续工作数小时 |
| 简单信息查询 | Lead 自己做 | Read/Grep 即可完成 |
| 多个独立研究方向 | Spawn multiple agents | 并行验证 + 风险隔离 |

## Spawn Prompt 设计 Checklist（8 项）

```
[ ] 明确 deliverable（文件名/数字，不只是"分析"）
[ ] 数据量要求（至少 N 个 markets/samples）
[ ] Pre-flight check（列出需要 scan 的 existing skills）
[ ] Simple 命名（Task A/B/C，避免 Option/Direction/Stage 混淆）
[ ] Execution 原则（Planning 不超过 30% 时间）
[ ] Timeline（每个 milestone 预期时间）
[ ] Context injection（显式列出相关 skill paths）
[ ] Shared log（如果多 agents，指定 observe-* shared log）
```

**Spawn Prompt 模板**:

```
你是 [角色名]，负责 [具体任务]。

## 核心任务（明确 deliverable）
1. [具体步骤1] - 输出：[具体文件/数字]
2. [具体步骤2] - 输出：[具体文件/数字]

## 数据要求
- 使用 **至少 N 个 markets**
- 不要小样本，要 robust validation

## Pre-flight Check
扫描 existing research 避免重复：
- [skill 1 path]

## Execution 原则
- Planning 不超过 30% 时间
- 每个 milestone 完成后立即报告（SendMessage）

## Timeline
- Milestone 1 (Xh): [deliverable]
- Final report (Xh): [完整结果]

## Shared Research Log（如果多 agents）
在 /observe-[project]-research-log 记录跨策略发现。

开始执行！
```

## 协调模式

| 模式 | 使用场景 | 关键工具 |
|------|---------|---------|
| **Shared Log** | 2+ agents 研究相关主题，共享发现 | `/observe-*` skill |
| **Milestone 报告** | 长时间任务（>2h），实时监控进度 | SendMessage after each phase |
| **Cross-validation** | 同一参数由多个独立方法验证 | 2+ agents, different methods |

**Shared Log 模板**:
```markdown
## Discovery N: [Pattern Name]
**Source**: [Agent Name]
**Description**: [发现内容]
**Evidence**: [数据或实验结果]
**Action**: [已采取/待采取]
```

## 纠正策略（3 级升级）

| Level | 触发条件 | 操作 | 消息模板 |
|-------|---------|------|---------|
| **Level 1** | Agent idle 或轻微偏离 | 明确指令 | "不要 idle，继续执行！你的任务是执行+报告结果，不是做计划。" |
| **Level 2** | Agent 执行错误任务 | 停止 Emoji + 对比 | "STOP - 任务方向错误。你应该做：[具体]。你不需要做：[列举]。" |
| **Level 3** | 2 次纠正失败 | 重新 spawn 或 Lead 自己做 | 停止 agent，评估 output 是否仍有价值 |

**何时停止（Level 3）**:
- Task 完全错误，output 无价值
- 其他 agent 已完成相同任务
- 时间超出预算 2x

**何时继续**:
- Output 仍可作为对比或验证
- Agent 接近完成（<1h 剩余）

## 知识提取时机

| 发现类型 | 创建 | 理由 |
|---------|------|------|
| 跨研究通用 pattern | observe-* | 适用于 3+ 未来任务 |
| 方法论可复用 >3 次 | guide-* | 减少重复学习 |
| 任务特定内容 | task-*/strategy-* references/ | 不通用，不需要独立 skill |
| Agent 独立发现 | observe-* (Agent 创建) | 实时记录，避免遗忘 |

**提取 Checklist**（创建 guide-*/observe-* 前检查）:
- [ ] 通用性：适用于 3+ 未来任务？
- [ ] 验证：至少 1 个实战案例验证？
- [ ] 独立性：不依赖特定 task context？
- [ ] 避免重复：没有现有 skill 覆盖？

## 关键教训（BTC 5m 实战）

**Spawn prompt 质量 > 事后纠正**。90% 的协调问题可以通过更好的 spawn prompt 避免：

1. **Deliverable 模糊导致 idle**: "探索"被理解为"做探索计划"。修复：明确要求文件/数字结果。
2. **数据量缺失导致小样本**: 未明确最少数据量，agent 用 13 markets。修复：显式要求 "至少 N 个 markets"。
3. **命名混淆导致执行错误任务**: Option 1 vs Direction 1 vs Stage 1 混淆。修复：用 Task A/B/C 简单命名。
4. **并行研究加速**：2 agents 并行 = 1.5 天 vs 3+ 天串行。即使一个失败，另一个仍可成功。
5. **跨研究验证提高置信度**：同一 pattern 由 2 个独立 agents 发现 → 高置信度（BTC 5m≈15m 动量分布）。
