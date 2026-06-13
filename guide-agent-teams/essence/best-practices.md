# Agent Teams 最佳实践与排障

## 最佳实践

### 1. Spawn Prompt 设计

Teammates 不继承 lead 的对话历史。Spawn prompt 是 teammate 唯一的初始上下文（除了 CLAUDE.md + skills）。

**必须包含**：
- 角色定义（你是谁）
- 具体任务（做什么）
- 关键文件路径（在哪里）
- 完成后通信目标（通知谁）

**示例**：
```
你是安全审查员。

任务：审查 src/auth/ 模块的安全漏洞，重点关注 token 处理、session 管理和输入校验。
背景：App 使用存储在 httpOnly cookie 中的 JWT token。
输出：按 severity（CRIT/HIGH/MID/LOW）排列的问题列表，每项附修复建议。
完成后：SendMessage team-lead 附上摘要，然后 shutdown。
```

### 2. 任务粒度

| 粒度 | 问题 |
|------|------|
| 太小 | 协调开销 > 收益 |
| 太大 | 工作太久不汇报，浪费风险高 |
| 适中 | 自包含、有明确交付物（一个函数、一个测试文件、一份审查报告） |

建议每 teammate 分配 5-6 个任务，保持忙碌同时允许 lead 在卡住时重新分配。

### 3. 避免文件冲突

两个 teammates 编辑同一文件 → 互相覆盖。确保每 teammate 负责不同文件集。

### 4. 防止 Lead 抢活

Lead 容易自己开始做事而不等 teammates。两种对策：
- **Delegate mode**（Shift+Tab）：限制 lead 只能协调
- **明确指令**：`Wait for your teammates to complete their tasks before proceeding`

### 5. 从研究和审查开始

新手建议先用 Agent Teams 做不涉及代码修改的任务：审查 PR、调研技术方案、排查 bug。
这些任务展示并行探索价值，且没有并行实现的协调复杂性。

### 6. 监控和引导

定期检查 teammates 进展，重定向不工作的方案，及时综合发现。
放任团队无人监管太久会增加浪费风险。

### 7. Plan Approval 使用场景

复杂或高风险任务 → spawn 时 `mode: "plan"` → teammate 只读 → plan 提交后 lead 审批。

影响 lead 审批判断的方式：在 prompt 中设定标准，如：
- "only approve plans that include test coverage"
- "reject plans that modify the database schema"

## 排障

### Teammates 不出现

- In-process 模式下可能已在运行但不可见 → Shift+Down 切换
- 任务不够复杂 → Claude 可能没 spawn
- Split panes 需要 tmux：`which tmux` 检查
- iTerm2 需要 `it2` CLI + 启用 Python API

### 权限弹窗太多

Teammate 权限请求冒泡到 lead → 提前在 permission settings 中预批准常用操作。

### Teammates 遇错停止

检查输出（Shift+Up/Down 或点击面板），然后：
- 直接给额外指令
- Spawn 替代 teammate 继续

### Lead 提前结束

Lead 认为完成但实际没完 → 告诉它继续。
或提前指令：`Wait for teammates to finish before proceeding`。

### 孤儿 tmux session

```bash
tmux ls
tmux kill-session -t <session-name>
```

### Task 状态滞后

Teammates 有时忘记标记 completed → 手动更新或让 lead 催促。

## 已知限制总结

| 限制 | 影响 | 缓解 |
|------|------|------|
| 不支持 session resumption | /resume 不恢复 teammates | 告诉 lead spawn 新 teammates |
| Task 状态可能滞后 | 阻塞依赖任务 | 手动更新或 lead 催促 |
| Shutdown 慢 | Teammate 完成当前操作后才关 | 耐心等待 |
| 每 session 一个 team | 不能同时管多个 team | 先 cleanup 再创建新 team |
| 不支持嵌套 teams | Teammates 不能 spawn 自己的 team | 只有 lead 管 team |
| Lead 固定 | 不能转让 leadership | 如需换 lead，重建 team |
| 权限继承 | 不能 per-teammate 设权限 | Spawn 后单独修改 |
| Split panes 环境限制 | 不支持 VS Code/Windows Terminal/Ghostty | 用 in-process 模式 |

## Token 优化

- Agent Teams token 消耗 >> 单 session，随 active teammates 数量线性增长
- 研究、审查、新功能开发：额外 token 值得
- 常规任务：单 session 更划算
- **按需 spawn/shutdown**：不需要的 teammate 及时关闭
- **避免 broadcast**：用 message 代替，只发给需要的人
