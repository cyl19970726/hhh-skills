# Live Ops Agent Team 模板

> 适用于：CS2 / 体育 / 任何需要实时数据 + 多并发市场的实盘运营

## 角色配置

| Agent | 模型 | 类型 | 职责 |
|-------|------|------|------|
| team-lead | Sonnet | 主 session | 战略决策 + 资源分配 |
| domain-1..N | Haiku | 持久 Member | 单市场生命周期执行 |
| workflow-agent | Sonnet | 持久 Member | 30min 健康审计 |
| fix-agent | Sonnet | 持久 Member | BUG_DETECTED 分层修复 |

## Domain Agent 状态机

```
IDLE → GATE_CHECK(6项/300s/60min超时) → STARTUP(pm2+3min) → MAP_LIVE(480s)
  → MAP_NEXT → [ASSIGN_NEXT→STARTUP | ABORT→POSTMATCH]
  → POSTMATCH(LIFECYCLE_SUMMARY必须→pm2 stop→POSTMATCH_COMPLETE) → IDLE
```

## GATE_CHECK 6 项（铁律）

1. conditionId active
2. Mars match 可追踪
3. FanOut WS online
4. **Safe USDC ≥ 30**（不是 EOA！Builder 模式 USDC 在 Safe）
5. **EOA MATIC ≥ 0.1**（ERC20 approve 需要 gas）
6. conditionId 在 seed 或 Gamma fallback

## pm2 Start 铁律

```bash
POLY_EXECUTION_MODE=builder MARS_WS_URL=ws://localhost:8282 pm2 start ...
```

## 核心消息流

```
Lead ──ASSIGN──→ domain-N ──ASSIGN_ACK──→ Lead
domain-N ──PHASE1_VERIFIED──→ Lead ──SCALE_UP──→ domain-N
domain-N ──LIFECYCLE_SUMMARY──→ Lead  ← pm2 stop 硬前置
domain-N ──POSTMATCH_COMPLETE──→ Lead
domain-N ──BUG_DETECTED──→ Lead → fix-agent
```
