# 通用状态机模板

## 基础模板

```
IDLE
  ↓ 收到 ASSIGN
PREPARE（前置检查，超时: 60min → PREPARE_TIMEOUT）
  ↓ 全部通过
EXECUTE（主要工作，定时 loop）
  ↓ 检测到完成信号
FINALIZE（发送报告 → 必须完成才能退出）
  ↓
IDLE

异常出口（任意状态均可触发）：
  → RECOVERY（自修复 1 次）
    ↓ 成功 → 返回原状态
    ↓ 失败 → BUG_DETECTED severity=CRIT/HIGH → 等待 Lead 指令
```

## 设计原则

1. **每个状态必须有超时出口**：防止永久卡死（PREPARE 60min，EXECUTE 按业务定）
2. **RECOVERY 分支必须存在**：异常 → 自修复 1 次 → 失败再上报（减少误报）
3. **FINALIZE 不可跳过**：关键消息设为 FINALIZE 硬前置条件
4. **状态转换只由消息或事件触发**：不能靠时间猜测状态
5. **loop 频率自适应**：正常期放慢（480s），接近完成加速（240s），数据停滞降频（300s）

## CS2 实盘实例

```
IDLE → GATE_CHECK(300s/6项/60min超时) → STARTUP(pm2+3min验证)
→ MAP_LIVE(480s/4项检查) → [map_end?]
  ├─ series继续 → MAP_NEXT → [ASSIGN_NEXT] → STARTUP
  └─ series结束 → POSTMATCH(LIFECYCLE_SUMMARY必须 → pm2 stop → POSTMATCH_COMPLETE) → IDLE
```

## 回测实例

```
IDLE → DATA_PULL(30min超时) → STRATEGY_RUN → RESULT_READY(发摘要) → IDLE
```
