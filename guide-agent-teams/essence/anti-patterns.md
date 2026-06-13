# Agent Team 反模式（Anti-Patterns）

> 来源：CS2 实盘运营 2026-04-19，16.5小时、325条 team 通信验证。

## AP-1: Lead 直接操作而不更新 Spec

**现象**：Lead 直接给出 pm2 命令/修代码/发 MATIC，domain agent 未自主执行。
**后果**：同一问题下次 session 重现（本次 EOA/Safe 混淆出现 4 次）。
**正确做法**：每次 Lead 纠正 domain agent = 一次 spec 更新信号。立即写进 spec，下次 agent 自主处理。

## AP-2: 无 HEARTBEAT，无法区分静默和死亡

**现象**：进程 pm2 显示 online，但实际 PID 已死（phantom 状态），Lead 延迟 14 分钟才发现。
**后果**：比赛窗口丢失，持仓风险敞口。
**正确做法**：长时运行 domain agent 必须定期发 HEARTBEAT，或在主 loop 中包含存活验证。

## AP-3: Agent 上线不自检，等第一个 loop interval 才工作

**现象**：workflow-agent 在 session 开始 3 小时后才上线，前 3 小时所有 bug 无人发现。
**后果**：MM WS 接线 bug、FanOut drop、MATIC 缺失在无监控环境下累积。
**正确做法**：持久 Member 上线即执行首次检查，不等第一个 loop interval。

## AP-4: 状态机无 RECOVERY 出口

**现象**：MAP_LIVE 状态只有正常退出（map_end），无法处理"进程活但数据异常"中间态。
**后果**：phantom pm2 在 MAP_LIVE 状态机内无法自动处理，延迟 14 分钟发现。
**正确做法**：每个状态必须有 RECOVERY 分支：异常检测 → 自修复 1 次 → 失败则 BUG_DETECTED。

## AP-5: BUG_DETECTED 无自验证门控，误报消耗 Lead 注意力

**现象**：domain-3 发出 2 次误报（CRIT 查询语法错误 + HIGH CLOB 余额 micro-units）。
**后果**：Lead 注意力被低质量告警消耗，高优先级问题响应延迟。
**正确做法**：BUG_DETECTED 发送前必须自验证：重试 1 次 + 备用命令确认，确认后才上报。

## AP-6: 关键消息无强制前置条件，执行率难以追踪

**现象**：LIFECYCLE_SUMMARY（spec 要求 map_end 后发送）执行率 0%，无检测机制。
**后果**：整个 session 无一条生命周期摘要，事后只能人工从 inbox 重建。
**正确做法**：关键消息设为下一状态的硬前置条件：不发 LIFECYCLE_SUMMARY = 不能 pm2 stop。
