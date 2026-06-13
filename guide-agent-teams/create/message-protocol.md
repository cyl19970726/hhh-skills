# 消息协议设计模板

## 三系列消息

### ASSIGN 系列（Lead/Manager → Domain）

| 消息 | 触发时机 | 关键字段 |
|------|---------|---------|
| ASSIGN | 分配新工作单元 | id, params, resources |
| ASSIGN_NEXT | 同 domain 切换到下一单元 | next_id, updated_params |
| SCALE_UP | 升级参数 | new_params |
| ABORT | 终止 | reason |

### STATUS 系列（Domain → Lead）

| 消息 | 触发时机 | 关键字段 |
|------|---------|---------|
| ASSIGN_ACK | 收到 ASSIGN 后立即回复 | domain, match |
| GATE_PASSED | 前置检查通过 | domain |
| GATE_TIMEOUT | 前置检查超时 | domain, failed_check |
| STARTUP_COMPLETE | 进程启动验证通过 | domain, pid |
| PHASE1_VERIFIED | Phase-1 验证通过 | domain, match |
| HEARTBEAT | 定期心跳 | domain, state, last_event_ts |
| MAP_NEXT | 工作单元切换信号 | domain, completed, next, score |
| LIFECYCLE_SUMMARY | 执行摘要（FINALIZE硬前置） | signals, orders, fills, position, notes |
| POSTMATCH_COMPLETE | 完全结束 | domain, match, result |

### BUG 系列

| 消息 | 字段 |
|------|------|
| BUG_DETECTED | domain, symptom, evidence(200字内), severity(CRIT/HIGH/MID/LOW) |
| FIX_COMPLETE | bug_ref, fix_desc, verification |
| WALLET_ACTION_REQUIRED | domain, action_type, amount |

## 消息设计原则

1. **自验证后再上报**：BUG_DETECTED 前重试 1 次 + 备用命令确认
2. **关键消息设为前置条件**：LIFECYCLE_SUMMARY 不发 = 不能进入下一状态
3. **ACK 关键 ASSIGN**：防止消息丢失导致 domain 双重执行
4. **severity 分级执行**：CRIT = 立即；HIGH = 本轮；MID/LOW = 记录待处理
