# Backtest Agent Team 模板

> 适用于：参数组合回测、多策略对比、时间段扫描

## 角色配置

| Agent | 模型 | 类型 | 职责 |
|-------|------|------|------|
| backtest-manager | Sonnet | 持久 Member | 参数分配 + 进度跟踪 |
| data-agent | Haiku | 按需 Subagent | 拉取历史数据 |
| backtest-domain-1..N | Haiku | 持久 Member | 单参数组执行 |
| result-aggregator | Sonnet | 按需 Subagent | PnL 汇总 + 推荐 |

## 并发模式：Work-Stealing

```
manager 维护 paramQueue[]

domain-N 完成 → BACKTEST_COMPLETE → manager 立即分配下一组
→ 无空转，最大化并发利用率
```

## Domain 状态机

```
IDLE → DATA_PULL(30min超时) → STRATEGY_RUN → RESULT_READY(发摘要) → IDLE
```

## 消息协议

```
manager ──BACKTEST_ASSIGN {paramSet, dateRange}──→ domain-N
domain-N ──DATA_READY {rowCount}──→ manager
domain-N ──BACKTEST_COMPLETE {pnl, winRate, sharpe}──→ aggregator
aggregator ──RESULT_SUMMARY {topN, recommendation}──→ manager
```

## 与实盘的差异

| 维度 | 实盘 | 回测 |
|------|------|------|
| 时间压力 | 有 kickoff window | 无 |
| Wallet 操作 | 必需 | 不需要 |
| Fix Agent | 必需 | 可选 |
| 数据来源 | Mars WS 实时 | InfluxDB 历史 |
| 并发模式 | 比赛驱动 | work-stealing |
