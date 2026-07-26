---
name: session-forensics
description: |
  读 agent 会话历史（Codex ~/.codex/sessions 的 rollout JSONL、Claude Code transcript、subagent/team 日志），
  用「物证流 vs 叙事流」的对质方法找出执行 agent 自己看不见的问题，并把结果变成可继承的资产。
  三种用法：① 审计一个 agent 的求解过程是否病态（卡住、空转、目标漂移、修工具循环、假通过）；
  ② 会话被压缩/中断/换人时生成 handoff packet；③ 从历史里挖出该沉淀成 skill/harness/gate 的东西。
  当出现：读 session 历史、复盘会话、审核另一个 agent 的实现方法、为什么进度这么慢、
  为什么一直失败、agent 卡住了、compaction 之后丢了什么、要交接给下一个 agent、
  ~/.codex/sessions、rollout jsonl、session 复盘、agent 复盘 —— 时使用本 skill。
  ⚠️ 不要用向量检索/RAG/agent-memory 读 session（见 §禁止事项，此路线已被实证判定失败）。
---

# Session Forensics

把 agent 会话当**物证记录**读，不当聊天记录读。

## 心智模型（一分钟版；完整版见 references/mental-model.md）

一份会话里有两条流：

```
叙事流  reasoning / assistant message / plan / 摘要 / compaction summary   = 辩护，永远自洽
物证流  exec / apply_patch / 测试输出 / 耗时 / 失败 / commit / 用户纠正     = 事实，不自洽但不说谎
```

**所有失败都是两条流之间的裂缝。裂缝是本 skill 唯一的一等对象。**

```
A 类 时序裂缝   宣称 vs 自己的动作        局部可查    原理上可自察（虽难）
B 类 代际裂缝   引用 vs 被引用物的现状     全局才可查   原理上不可自察   ← 本 skill 存在的理由
```

B 类通用形式：**引用了一个已不再成立的东西，而系统没有失效传播机制**（cache invalidation 缺失）。

执行 agent 看不见 B 类，有三条互相独立的机制（任何一条单独成立就够）：
**判据封闭性**（计划里没有"计划错了"这个类别）、**类型不足**（计划类型是 `[Action]`，风险住在
`Action → PastConclusions → Invalid`，而计划在 t=0 制定时结论集为空）、**压缩致盲**（实测 ~200:1，
摘要保留"做了什么"、丢弃"做了多少次/在几个副本里"，而后者就是全部病理信号）。

→ 外部 agent 的不可替代性 = **工作集是全局的**。这是复杂度分工，不是"第二双眼睛"。

## 唯一不变量

> **任何结论都必须由物证流支撑；叙事流只能作为「待质证的宣称」进入分析。**

"读两遍"是手段不是目的。禁止的是"只读上一遍的摘要"，不是"没读完全文"。

## 上下文边界纪律（违反即失败）

```
GB 级物证  →  [脚本进程内消化]  →  KB 级指标  →  [上下文]
```

**任何原始 JSONL 不许穿过这条边界。** 绝不用 Read 打开 rollout 文件——它们最大 1.5 GB。
实测：读一个 72 MB session 只耗约 4 KB 上下文（~20000:1）。钻取时按行号取窗口，每次 ≤50 行。

⚠️ **不要用 Codex 原生 `read_thread` 读整个会话。** 实测单次调用（已设 `turnLimit:10`、
`includeOutputs:false`、`maxOutputCharsPerItem:20000`）仍返回 **554 万字符 ≈ 138 万 token**，
是上下文窗口的 5.4 倍。同一件事本脚本花约 4 KB —— **相差约 2000 倍**。
`read_thread` 只允许用于有界钻取（指定 cursor + 极小 turnLimit）。

⚠️ **`view_image` 传未降采样 PNG，实测单次约 120 万字符 ≈ 30 万 token**，超过整个窗口。
两个被审会话里它分别占全部工具输出量的 **57%** 和 **87%**。看图前先降采样。

⚠️ **`imagegen` 比 `view_image` 单次更贵**：本机语料均值 **225 万字符/次**（view_image 仅 81.6 万），
是仅次于 `read_thread` 的第二贵工具，在 3 个会话里是主洪水源。`019f93b3` 里**两次调用就烧掉
411 万字符 ≈ 103 万 token ≈ 4 个上下文窗口**。生成图后落盘取路径，不要把返回体带进上下文。
按 **per-call 成本**排序洪水源，不要按 share 排（share 已降级，见 `local/falsified.md`）。

⚠️ **不要在 `exec_command` 里跑 `--watch` / `-f` / `tail -f`**。自刷新进度条每次刷新都进 stdout，
`write_stdin` 每次拉回全量缓冲 → O(n²)。`019f93b3` 实测 `wait` 331 次 **5564 万字符 ≈ 1400 万 token
花在等 CI 上**，最后答案来自一次 `gh run view --json status,conclusion`。等待用有界轮询。

## 结构：探针 + 装配

```
探针（可独立跑、可组合）          装配
  P1  裂缝 / 失效边检测            audit report   = P1 (+P3) (+P2)
  P2  可复用序列提取（沉淀）        harvest report = P2
  P3  目标演化追踪                 handoff packet = S + P1 + P2 + P3   ← 超集
  S   状态重建（完整版仅 handoff）
```

## 流程

运行脚本前，把当前加载到的 skill 根目录设为绝对路径：

```bash
SESSION_FORENSICS_DIR="<absolute path to session-forensics>"
```

### 0. 定位

```bash
python3 "$SESSION_FORENSICS_DIR/scripts/session_locate.py" <thread-id>
python3 "$SESSION_FORENSICS_DIR/scripts/session_locate.py" --since 2026-07-24 --min-mb 20 --deep
```
按最便宜优先搜：文件名 → 索引 thread_name → 时间窗+体积（只 stat）→ 首条用户消息（只读文件头）。
⚠️ 索引覆盖不全（2980/5548），索引未命中不等于不存在。不要对 51 GB 跑全库 `rg`。

### 1. 本地校准（首次使用必做一次）

```bash
python3 "$SESSION_FORENSICS_DIR/scripts/calibrate.py" ~/.codex/sessions ~/.claude/projects
```

基线、不满句式、洪水画像**都是环境属性，不是通用常数**。skill 分发方法，数字必须本地生成到
`<skill>/local/`。**用别人的基线读自己的会话，正是本 skill 要检测的 B 类裂缝。**
之后只用「在你自己语料里的分位」解读指标，绝对值不可解释。

### 2. 测量（零阈值假设）

```bash
python3 "$SESSION_FORENSICS_DIR/scripts/session_metrics.py" <session.jsonl> --json-out /tmp/metrics.json
```

多个会话可一次传入横向对比。**必须用绝对路径**——相对路径正是让上一代 skill 零执行率的原因。

### 3. 首尾一刀（audit 模式先做这个，成本近零）

把 `objective_trace.first_substantive`（初始真实目标，已过滤 ambient 注入）和最后 20% 的动作
放在一起看：**现在在干的事，和最初要的东西还有关系吗？**

```
最终目标 ≠ 初始目标
  ├─ 变更可追溯到某条 user message → 合法演化，动作是「重新对齐」
  └─ 追溯不到                      → agent 自漂，动作是「纠正」
```
依据：user message 是唯一来自系统外部的物证，叙事流吸收不掉它。
**用户改需求本身是一条失效边**——旧目标下的结论/证据/已完成工作需重新估值。

⚠️ **「重新对齐」是动作，不是判定标签。** 判出"合法演化"就停手 = 只做了诊断，任务没续上。
重新对齐 = 用**当前目标**重排后续工作，并显式写出「当前目标 ≠ 初始目标」这张演化图。
实证（`019f9a28`，用户当场指出"你都没有真正的把任务续上"）：审计员正确判出目标已从
"误封申诉"演化到"做成文章+视频"，却仍把 §10 第 1、2 项排成自己发现的工具问题，
把用户的交付物压到第 3、4 项。**审计员发现的问题属于"支撑项"，不自动获得优先级。**
见 `references/handoff-packet.md` §实战修订记录 第 6 条。

### 4. 提供证据，不做判定

见 `references/signatures.md`。给出 top-N 异常项及其**本地基线分位**（`local/baseline.json`）。

⚠️ **本 skill 不是分类器。** n=101 全语料验证：没有任何结构指标能预测「会话是否有问题」
（全部 |r|<0.22，排序榜也不富集）。指标能说清**发生了什么**——预算流向哪、哪个文件在几个
工作树分叉、地板涨到多少——但**说不了这个会话是好是坏**。判断由读它的人或审计 agent 做。

定性签名（仪器分叉、定义分叉、无证宣称、目标失联）无阈值问题，发生即命中，也仍然只是证据。

### 5. 有界钻取

只对命中项回原文，按行号取窗口，每会话 ≤3 个窗口。

### 6. 终点是一个动作，不是报告

```
继续 / 干预（回到第 K 个决策点）/ 升层（问题被误当成执行问题）/ 停止（交回给人 + 必须由人回答的问题）
```

### 7. 交接与晋升

```bash
python3 "$SESSION_FORENSICS_DIR/scripts/handoff_packet.py" <session.jsonl> --out handoff.md
```
脚本填 §1/§2/§4/§5 与附录（纯物证），其余留 TODO 桩。
**§6 已证伪留空 = packet 未完成**——不写，接手方会把前任的错误结论当既定事实继承。


```
观察 1 次                  → handoff packet（模板见 references/handoff-packet.md）
跨会话复发 2 次             → 失效边 / gate      （禁止性："别做 X / X 之后 Y 失效"）
复发 ≥3 次且有稳定操作序列   → skill（+harness）  （生成性："要做 Z 就按此序列"）
```

### 8. 自我升级（每次使用后必做，不可跳过）

读完任何会话，给结论**之前**回答四问：出现新洪水源/新签名了吗？有阈值被反例推翻吗？
数字不合理吗（优先怀疑解析 bug）？有东西跨会话复发第 2 次吗（是则立即晋升 gate，不等第 3 次）？

有则按 `references/self-upgrade.md` 的路由写回文件。**不写回 = 知识只留在叙事流里，下次归零——
那正是本 skill 用来诊断别人的病。** 纪律：每条新增带实测数字与来源会话 id；已证伪条目只增不删；
n=1 只记为单例观察；结论有边界就补边界，不要覆盖旧结论。

## 禁止事项

- **禁止解题。** 审计员不得解决被审对象的技术问题——一解题就掉回序列空间，失去全部价值。
  只回答"这个求解过程是否病态"，不回答"这个 bug 怎么修"。
- **禁止 RAG / 向量检索 / agent-memory 路线读 session。** 已实证失败（用户判定"基本上没有做到
  任何我们想要的"）。原因：向量检索只能检索叙事流——只有叙事流是自然语言、才可嵌入；而价值在
  物证流（某文件改了 12 次、某命令跑了 39 次、仪器分叉 4 个副本），这些东西嵌入之后什么都不是。
  **它和 compaction 犯的是同一个错误，只是换了实现。**
- **禁止用绝对计数下判断。** 已被反例推翻两次，一律用 rate。
- **禁止把 dossier 当作第二遍的输入。** dossier 本身已是一条新的叙事流。
- **不足 3 次复发不晋升为 skill**（防过早抽象）。

## 质量闸（不满足则分析作废）

- 结论只有编年史，没有裂缝
- 用户目标从 assistant 摘要推断，而非从 user message 物证
- "通过"未绑定 revision 与验证表面
- 遗漏 reviewer / subagent 的反证
- 失败被记录但没有隐藏假设与预防机制
- 报告答不出"当前路线为何存在、备选为何被否"

## 支持的平台

| 平台 | 状态 | 存储 | 能力缺口 |
|---|---|---|---|
| Codex | 已实现 | `~/.codex/sessions/**` + `archived_sessions/`（5548 / 48 GB） | 无 |
| Claude Code | 已实现 | `~/.claude/projects/<cwd>/<uuid>.jsonl`（1307 / 2.2 GB） | 无 context_window；轮次生命周期为近似（`stop_hook_summary`） |
| Kimi Code | 已实现 | `~/.kimi-code/sessions/**/agents/<agent>/wire.jsonl`（221 / 679 MB） | **无压缩标记**（报 `null` 不报 0）；子 agent 在独立文件 |

格式自动探测（`session_events.detect_format`）。平台不支持的指标一律返回 `null`，
**绝不返回 0**——Kimi 的 `compactions=0` 会让一个会话看起来毫无压缩问题。

心智模型与签名表**与平台无关**，差异只在「原始记录 → 规范化事件」这一层。详见 `references/platforms.md`。

## 参考

- `references/mental-model.md` — 完整心智模型、失效表、为何 RAG 路线必然失败
- `references/signatures.md` — 签名表、实测基线、洪水画像、gate 清单、已证伪与解析陷阱
- `references/self-upgrade.md` — 四问、写入路由、纪律、对自己做审计
- `references/platforms.md` — 多平台适配层与各平台字段映射
- `references/codex-jsonl.md` — Codex rollout JSONL 字段真值表（含与官方文档不符处）
- `references/handoff-packet.md` — handoff packet 模板与实战修订记录
