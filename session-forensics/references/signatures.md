# 签名表与基线

## 使用方式

**只排序，不判决。** 输出「top-N 异常项 + 其在基线分布中的分位」，把判断留给读的人。
这既符合"审计员不解题"，也让结论不依赖尚未验证的阈值。

> ⚠️ **本文件中的所有具体数字都来自一个特定语料**（`~/.codex/sessions`，2026-07，单一用户）。
> 它们是**示例，不是常数**。基线、不满句式、洪水画像都是环境属性——换一个人、换一套工具链、
> 换一种语言，分布完全不同。**用别人的基线读自己的会话，正是本 skill 要检测的 B 类裂缝。**
>
> 首次使用请先跑本地校准生成 `<skill>/local/baseline.json`：
> ```bash
> python3 "$SESSION_FORENSICS_DIR/scripts/calibrate.py" ~/.codex/sessions ~/.claude/projects
> ```
> 之后只用**分位**解读指标，不用绝对值。详见 `references/self-upgrade.md` §分发层 vs 本地层。

## 示例基线（60 个 session，各取前 6000 行，2026-07，单一用户语料）

```
                 p50     p75     p90     p95     max
compactions       10      20      30      30      30
max patch/file     1       2      16      18      49
max repeat cmd     8      41     189     226     226
exec calls        89     864     921     953    1073
forked files       0       1       4       8      11
```

关键：`exec` 从 p50=89 跳到 p75=864（十倍），会话本身强双峰。
`maxcmd/exec` 归一化后 p50=0.09 → p90=0.21，**24 倍压缩到 2.3 倍**
→ **约 90% 的原始信号是"会话规模"，仅约 10% 是真异常。绝对计数一律禁用。**

## 定性签名（无阈值，发生即命中，判别力最强）

| 签名 | 检测 | 属类 | 检测层 |
|---|---|---|---|
<!-- 检测层：`代码` = 同一性/计数，确定性可全量；`agent` = 等价/意图判断，代码这层做不到；
     `代码→agent` = 脚本出料、判定必须由审计 agent 做。这一列是为了阻止
     「文档说发生即命中、实际要人读」这种无证宣称。 -->
| **仪器分叉** | 同一 basename 在 ≥2 个工作树根下被 patch（基线 p50=0） | B | 代码 |
| **仪器-产物共变** | 同窗口内 patch 同时命中 `tools/` 与业务路径 | B | 代码 |
| **证据代际断裂** | 证据产出时刻 < 其依赖仪器的最后修改时刻 | B | 代码（mtime/stat） |
| **定义分叉** | 同一术语在 ≥2 份权威文档中被独立编辑（需语义判断） | B | **agent**（表内自己写了「需语义判断」） |
| **目标失联** | 最终目标与初始目标无关，且变更点追溯不到 user message | A/P3 | 代码→agent（脚本给首尾，「还有关系吗」要判） |
| **无证宣称** | 出现 fixed/passed/works，前 K 条物证无对应验证动作 | A | **agent**（「对应」是语义等价） |
| **纠正复发** | 同一诉求被用户重述 ≥2 次 **且中间有 assistant 回应** → 方法论失效，非执行问题（见下方混淆项） | A | 代码（近似；trigram 已知会漏，见 §已知实现局限） |
| **假 provenance**（单例观察 n=1） | audit/证据 JSON 里写着 `repo_commit: <sha>`，但产出它的仪器 `git log --all -- <仪器>` 为**空**（从未提交） | B | 代码（一条 git log） |
| **孤儿产物**（单例观察 n=1） | 产物 mtime > session 文件最后 mtime → 子 agent 在父会话终止后仍在写盘，该证据**无人看过** | B | 代码（stat mtime） |
| **owner 视野落后一代**（单例观察 n=1） | owner 常驻目录里的状态板文件与领先分支的同名文件逐行冲突，且落后方是 owner 唯一可见的那份 | B | 代码（跨副本 diff） |
| **实参漂移**（单例观察 n=1） | 同一 derivation 函数被 ≥2 个 caller 调用（生产端 + 独立验证端），新增的作用域/豁免参数只传给了其中一个 → 两端对同一份产物推出**相反的终态** | B | 代码→agent（rg 出 caller，是否漂移要判） |

### 实参漂移的实测来源（`d9993d69-4861-4618-9995-331f9c771263`，Claude Code，2026-07-25 19:40→00:29 本地）

```
机制            status-gate.mjs::summarizeStatus 有两个 caller：run-scenario.mjs（写 manifest）
                与 validate-evidence.mjs（独立复核 manifest）。会话末尾给 summarizeStatus 加了
                新参数 outOfScopeFixtures，只在 run-scenario.mjs 一侧计算并传入。
                → manifest 自报 completed / blockers=[] / maxClaim=auto_verified_candidate；
                  validate-evidence 仍按旧参数推导，判 source_invalid，四条 failure 全是
                  "must be derived as partial"。CLI 终态 blocked。
为何执行 agent 看不见   lint=0、全量 874 test 绿（L1022）→ 单元层完全无信号；
                        差异只在「两个 caller 传参不同」这一跨文件事实上。
                        随后 L1023 跑验收、L1025 会话被 401 掐断，终态从未被任何 agent 读到。
检测成本        rg 出 derivation 函数的全部 caller，比对新增参数是否每个 caller 都传。零解析。
与「定义分叉」的区别    定义分叉是两份**实现**各自演化；实参漂移是**同一份实现**被喂了不同实参，
                        共享代码反而掩盖了它——看 diff 只看到「加了个可选参数，默认值安全」。
```
n=1，记为单例观察，未晋升 gate。但它同时命中既有的 **孤儿产物**（终态产物 mtime 00:29 = 会话死亡时刻，
无人看过）——两条签名叠加时，产物里的自报状态**必然**被下一代当既定事实继承，这是最贵的一种裂缝。

⚠️ **后续修正（同日）：签名定位了缺陷类，但没有定位修复点。**
「补上漏传的实参」是错的解法——独立盲审判 reject：真正的缺陷在**两个 caller 的共同上游**
（runner 给 backend 侧做了作用域过滤、page 侧漏了），补参数等于在闸里豁免一条本就不该产生的记录，
命中该仓「禁为过 CI 改闸」红线。修上游后两端自然一致，闸一行没动。
**通用教训：实参漂移是「两端不一致」的症状，修复点可能在两端之外。看到漂移先问「谁本该产生这份输入」，
不要默认对齐两端即可。** 审计员给出的是缺陷类，不是补丁——这条正是「禁止解题」的实证理由。

### 三条新签名的实测来源（`019f8fa7-57e6-7a71-9d54-35b82ae37db8`，2026-07-23→25，9439 行/83 MB）

```
假 provenance     tools/p072_b00_hero_lock.py 会话内被 patch 11 次、产出 v001–v009 全部证据，
                  git log --all -- 该文件 = 空；而 p072_b00_builder_audit_v009.json 写着
                  "repo_commit": "129ed87…"。同批未提交的还有 compose_plate / finalize_evidence /
                  verify_structure + 其测试。检测成本：一条 git log，零解析。
孤儿产物          session 最后一条记录 L9439 = wait_agent（等 /root/p072_v008_builder），
                  文件 mtime 19:45；audit/blend/20 张渲染的 mtime = 19:46:35–19:46:49。
                  即完整一版证据包在父 agent 断线后落盘，status=BUILDER_CLOSED，无人查看。
                  → 多 agent 会话特有。审计时必须 stat 产物目录，不能只读 session。
owner 视野落后    ROUTE_MATRIX.md 在 main（owner 常驻）与 codex/kiln-durable-promotion-v1 之间
                  30 行差异，且状态口径相反：main=「DRAFT_READY / ⏸ Phase 2A」，
                  分支=「CANONICAL_CLOSED / VERIFIER_CLOSED」。用户在 L8743 问
                  「我希望知道目前的情况」——这个提问本身就是该签名的外部症状。
```
三者共同机制仍是**缺少失效传播**，但检测面各不相同（版本库 / 文件系统时间 / 跨副本 diff），
故分列而不合并。均为 n=1，**记为单例观察，未晋升 gate**。

## 定量签名（用 rate，阈值待标注集确定）

| 指标 | 含义 | 观测样本 |
|---|---|---|
| `instrument_patch_share` | 改仪器占全部改动的比例 | 0.91（"读 session"任务里 91% 在改工具）/ 0.25 |
| `narrative_to_evidence` | (assistant+reasoning) / (exec+patch) | 1.92 / 1.64 — 疑似最佳"空转"度量，缺基线 |
| `timeout_rate` `failure_rate` | 除以 exec 数 | 0.38/0.15、0.26/0.33、e2e 仅 0.04/0.02 |
| `pump_share` | **真** pump / 全部真实用户消息（已扣除网络续跑） | 0.18 |
| `resume_share` | 中断后续跑 / 全部真实用户消息（环境噪声，非病理） | 0.12 |
| `pump_gap_median_lines` | 相邻真 pump 的行距中位数 | 96.5（尾部曾连续 6 次，间隔仅 7 行） |
| `compactions_per_1k_lines` | | 1.46 / 2.04 |
| `max_patch_share` `max_cmd_share` `forked_share` | | |

### "继续"泵（本表最新增）

用户被降格成 while 循环的计数器：agent 每前进极短距离就停下等人踩一脚。
实证：某 session 尾部 `L8777 / 8813 / 8820 / 8827 / 8834 / 8842` 连续 6 次"继续"，间隔 7–8 行。
它与用户主观感受的"进度怎么这么慢"是同一件事的两面——**"慢"的物证形态就是"继续"泵**。

## ⚠️ 环境噪声混淆项（两条签名都栽过，必须先排除再计数）

用户重述与"继续"**大部分可能只是网络中断后的重发/续跑**，与方法论无关。
不做区分就会把环境故障误报成 agent 病理。判据在物证流里是干净的：

**"继续" —— 用轮次生命周期区分**

```
两条用户消息之间有 task_complete 且无 turn_aborted / thread_rolled_back
    → PUMP：agent 正常收工后停下等指令（真信号）
无 task_complete，或出现 turn_aborted / thread_rolled_back
    → RESUME：轮次根本没结束，用户只是把它续上（环境噪声，丢弃）
```

Codex 事件：`task_started` / `task_complete` / `turn_aborted` / `thread_rolled_back`。
实证：某 session `task_started=36` 但 `task_complete=31`，另有 `turn_aborted=2`、`thread_rolled_back=1`。

**重述 —— 用「中间有没有回应」区分**

```
文本归一化后完全相同 且 中间零 assistant 消息 且 零工具调用   → RESEND（网络），丢弃
文本相似但措辞有变   且 中间 ≥1 条 assistant 回应             → RESTATED（回应了仍没解决），计数
其余                                                        → UNCLEAR，展示但不计数
```
依据：人几乎不会一字不差地重打一遍；措辞变化本身就是重新表达的证据。

**修正前后实测差距（同一 session）**

| 指标 | 修正前 | 修正后 |
|---|---|---|
| pump 计数 | 15 | **9**（另 6 条为 RESUME） |
| `pump_share` | 0.30 | **0.18**（新增 `resume_share` 0.12） |
| 重述簇 | 2 | 2（均判为 RESTATED，人工核对一致） |

结论未被推翻，但**量级虚高了 67%**。这是"环境噪声混入病理信号"的通用教训：
任何以"用户不得不再说一次"为基础的签名，都必须先扣掉环境故障。

## 上下文洪水（`flood_share` / `flood_tool`）—— 目前判别力最强的信号

按工具聚合 `function_call_output` 的字符量。它把"压缩为什么这么频繁"从"会话太长"这种
不可行动的解释，变成**一个具名工具的定量归因**。

实测（窗口均为 258,400）：

```
019f9774   view_image    11 calls   13.4M chars  57.2%   avg 1,220,810 chars/次 ≈ 30 万 token
           read_thread    5 calls    8.0M chars  33.9%   avg 1,592,379 chars/次 ≈ 40 万 token
           exec+exec_cmd 178 calls    2.1M chars   8.8%
019f8fa7   view_image    46 calls   55.1M chars  86.8%   avg 1,198,454      ← 会话仍在跑时测的中途值
```

⚠️ **边界修正（不删旧值）**：上面那行 `019f8fa7` 是会话未结束时的快照。当时以为会话终止后的复测为：

```
019f8fa7(终值)  view_image      51 calls  58.34M chars  87.1%  avg 1,143,889
                exec_command   396 calls   2.34M chars   3.5%
                list_agents     99 calls   2.25M chars   3.4%  avg    22,751   ← 新洪水源
                exec           298 calls   1.97M chars   2.9%
                take_screenshot  3 calls   1.37M chars   2.0%  avg   456,012   ← 新洪水源
```

结论方向未变（比例仅动 0.3pp），但**教训是：对仍在运行的会话取的指标是下界，不是终值**；
若要引用绝对值必须标注是否终态。

⚠️ **第二次边界修正（2026-07-26）**：所谓“终值”后来也被续写推翻。同一 session 文件从
9439 行 / 83 MB 增长到 **10045 行 / 88.8 MB**，`view_image` 从 51 次增长为：

```
019f8fa7(后续快照)  view_image  60 calls  63.38M chars  87.8%  avg 1,056,344
```

因此“终态”也必须绑定**采样时间 + 行数或文件哈希**；除非记录已归档且不可再续写，否则绝对值只能称
“截至某时的快照”，不能称终值。这是“引用对象后来变化”的又一个 B 类实例。

**两个新洪水源**（来源 `019f8fa7`，均 n=1）：
- `take_screenshot` avg 456,012 字符 ≈ 11 万 token/次。它与 `view_image` 是**同一机制的第二个实例**
  （未降采样图像进上下文），因此既有的"看图前必须降采样"gate 应按机制而非按工具名执行。
- `list_agents` avg 22,751 字符 × 99 次 = 2.25M。单次不大，**靠频次成为第三大消耗**。
  多 agent 会话特有，与既有 `wait` gate 同源：**编排类工具的轮询必须有界**。

**真正干活的工具只占 4–9% 的上下文预算。** 这两个会话"什么都记不住"不是因为工作复杂，
而是把 87% / 91% 的预算花在了看图与读上一个会话上。

### 三个会话三种洪水画像 —— 这正是该指标有判别力的证据

```
019f9774   view_image 57.2%  + read_thread 33.9%   干活的 exec 仅 8.8%
019f8fa7   view_image 86.8%                        干活的 exec_command 仅 3.7%
019f93b3   exec       79.5%  + wait        16.4%   （多 agent 会话）
```

`flood_tool` 会随会话类型改变，因此它不是"会话长度"的代理变量——它回答的是
**预算到底去哪了**，而这是可行动的。

### 由此晋升的四条 gate（均已跨会话复发 ≥2 次）

```
view_image(未降采样 PNG)   → 单次 ~30 万 token ≈ 1.2 个窗口。看图前必须降采样。
read_thread(turnLimit=10)  → 单次 ~138 万 token ≈ 5.4 个窗口。禁止通读，只许有界钻取。
用 exec 内嵌补丁串打补丁    → exec 输出把补丁全文回显，实测 avg 50,276 字符/次；
                             改用 apply_patch 工具实测 avg 214 字符/次 —— 相差约 235 倍。
                             且补丁全文会进两次上下文（arguments 一次、output 一次）。
wait(等待子 agent)         → 实测 avg 168,100 字符 ≈ 4.2 万 token/次；331 次共约 1390 万 token。
                             多 agent 会话特有。轮询必须有界，不能裸等。
一次看 N 张图              → 不要逐张 view_image / Read。先用 PIL 拼成一张带标签的 contact sheet
                             再读：N 次调用塌成 1 次，且**保留了横向对比**——逐张看时
                             「只有这一张不一样」恰恰是最难发现的。
```

**contact sheet 的实操约束**（来源：`d9993d69` 后续会话，2026-07-26，用户提出）：
拼图不是单纯为省 token，降采样有下限——**要读的证据往往就是图上的小字**。实测按宽 500px
（原图 780px，约 2/3）拼 3 张为 1500×999、676KB，中文错误文案仍清晰可读；再小就读不出了。
所以规则是「拼成一张 + 保住可读比例」，不是「压到最小」。该次拼图直接命中一条业务假绿：
三张里唯一一张显示「兑换资格同步失败」，而它在 manifest 里是 `passed`。

`read_thread` 那次已经设了 `turnLimit:10` + `includeOutputs:false` + `maxOutputCharsPerItem:20000`
**仍然**返回 554 万字符——**它的参数不足以约束体积**，不能依赖参数自保。

### 第五条 gate —— 派生副本失效传播（复发第 2 次，按 SKILL.md §8 提前晋升）

```
改了源副本 → 所有派生副本 + 其中的结论同时作废，必须同批传播才算生效。
```
两次实测，同一根因、不同形态：

```
n=1  scratchpad/session_metrics.py(307 行) 与 skill/scripts/session_metrics.py(473 行) 并存，
     草稿副本落后 166 行                                  → 处置：删非权威副本
n=2  019f9a28：.claude(源) → .codex/skills → hhh-skills(GitHub) 三副本，
     最后三次写回后未 rsync/未 commit，4 文件分叉，
     两条已证伪结论仍在 2/3 副本里生效                     → 见上节 md5 表
```
→ **凡审计"其产物会被复制/发布"的对象（skill、模板、脚本、契约文档），
必须把「源改动 → 派生副本 → 已发布副本」当成一条失效边显式量一次。**
一条被推翻的结论只修了源副本 = **没修**，因为加载派生副本的 agent 会继续传播它。

## 地板抬升：早先结论的边界修正

早先在 18 次压缩的会话上得出"地板抬升不是杀手"（26,280 → 42,224，+61%）。
在 60 次压缩的会话上**该结论不成立**：

```
seg  0  floor 22,480      seg 40  floor 57,680
seg 24  floor 36,675      seg 48  floor 73,695
seg 32  floor 43,470      seg 60  floor 76,979      +242%，且加速
```
前 24 段每段涨约 590，后 8 段每段涨约 2,000。终值 76,979 / 258,400 = **窗口的 30% 在开工前已耗尽**。

→ 修正表述：**地板抬升在 ~20 次压缩内可忽略，超过 ~40 次后成为主要约束，且斜率递增。**
判据用 `floor / window`，不用压缩次数。

### Compaction 与目标漂移：不要混淆因果

实测 `019f93b3` 的第 60 次 compaction：`replacement_history` 仍有 **229 条 role=user 消息**。
因此“目标原话被 compaction 删掉 → 目标漂移”不是 Codex 上的真实机制。

真实风险是**关系退化**：用户目标仍在，但没有结构化 `supersedes` 链；82 个子 agent 的任务与结果又
经历父目标→子任务→子报告→父摘要的多级投影。Compaction 丢弃的是支撑取舍的物证与跨段关系，
使最近局部目标更容易主导当前工作集。故：

```
compaction 多                         ≠ 已证明目标漂移
初始/最终动作不一致且无 user 变更依据   = P3 可确认的 agent 自漂
目标多且全部有 user 依据                = 合法演化，但需要 handoff 重建 supersedes 图
```

## 已知解析陷阱（踩过）

Kimi 同一步可以先连续记录多条 `tool.call`，随后才批量写对应的 `tool.result`。
`tool.result` 没有工具名，只有 `toolCallId`；若只记“最近一次调用”，大部分输出会被归到 `?`。
来源会话 `c813e95c-d5c5-4853-ae93-0612a645e43c` 的修复前后：

```
修复前   ?             13 calls   0.04M chars   74.6%
修复后   按 toolCallId 归属；? = 0 calls
```

补丁可能通过 `exec` 以内嵌 JS 字符串执行（`const patch = "*** Begin Patch\n*** Update File: ..."`），
其中换行是字面的 `\` + `n`。贪婪的 `(.+)` 会吞掉整个补丁体并把它当成文件路径，
**污染 patch 计数、文件数与整个仪器分叉检测**。实测差异：

```
修复前   patches=1370  files=1066  forked_share=0.028
修复后   patches=2063  files= 459  forked_share=0.179     ← 6.4 倍
```
正则必须写成 `([^\n\"\\]+)`。

### ambient 前缀名单会吞掉真目标（双向失真，来源 `019f9a28-21ee-7b01-8de0-92bcfce977c6`，Codex，n=1 单例观察但机制确定）

`is_ambient()` 的实现是 `any(m in text[:400] for m in AMBIENT_MARKERS)` —— **整条二值判定**。
它对"整条都是注入"有效，对"**注入包裹了真请求**"失效：

```
Codex 在用户附图时把真实请求包成：
    # Files mentioned by the user:
    ## <图片路径>
    ## My request for Codex:
    <真正的用户指令>          ← 命中前缀 "# Files mentioned by the user:" 后整条被丢弃
```

实测 `019f9a28`：**L9 是真初始目标**（含"我被 claude 误封了"这一决定全局优先级的约束），
被判为 ambient → `objective_trace.first_substantive` 误报为 L73。
**"首尾一刀"整个建立在 `first_substantive` 上，此陷阱会让初始目标判定系统性错位。**

同一会话反向也错一次：L90「然后继续你的工作」是纯推进，`PUMP_TOKENS` 只收录短应答词、
不含带动词的推进句式 → 计入 substantive，`pump_share` 因此报 0.0（假值）。

⚠️ **最危险的一点：总数看起来是对的。** 该会话 `substantive=9`，而正确成员集
（L9/L73/L121/L276/L365/L400/L514/L526/L552）也恰好是 9 条 —— 一个假阴性与一个假阳性互相抵消，
**计数无异常、成员全错**。因此校验 ambient/pump 必须核对**成员**，不能只核对计数。

**已修复（2026-07-26）**：把包裹型标记从 `AMBIENT_MARKERS` 拆到新的 `WRAPPER_MARKERS`
（`marker → body delimiter` 二元组），新增 `unwrap_user()` 先剥壳再判 ambient；
壳内无正文时才计 ambient。`PUMP_TOKENS` 补入带动词的推进句式，长度上限由白名单自动导出
（原硬编码 `<=8` 恰好卡掉 8 字的「然后继续你的工作」）。修复前后（`019f9a28`）：

```
修复前   substantive=9  ambient=2  pump=0  resume=0
         成员 = [73,90,121,276,365,400,514,526,552]   ← 少 L9、多 L90
修复后   substantive=9  ambient=1  pump=0  resume=1
         成员 = [ 9,   121,276,365,400,514,526,552] + 73  ← 正确成员集
         first_substantive: L9「…我被claude 误封了…」
```
⚠️ **验收时的一处偏差要记住**：预期 L90 落到 `pump`，实测落到 `resume`。
原因是 `is_pump` 先命中、随后被"环境噪声扣除"规则（`task_complete` 邻接）判为网络续跑。
两者都不进 `substantive`，结论不变；但**「pump ≥ 1」这个验收式写错了，正确写法是
`pump + resume ≥ 1` 且 L90 不在 substantive 成员集里**。验收式只盯一个桶，会被合法的桶间再分类误判为失败。

跨平台回归（三平台，无变化）：Claude Code 诞生会话 `64803a4e` 仍为
`substantive=18 pump=4 ambient=2`（命中其 Stage 1 原验收标准）；
Kimi `wire.jsonl` 仍报 `compactions=None`（非 0）；Codex `019f9774` 仍为 `substantive=9 pump=2 resume=3`。

### 上一处修复只堵了一半：`WRAPPER_MARKERS` 绑死前导 marker（来源 `019f93b3-ae93-7c41-b060-12aadf98b3a5`，Codex，777 MB / 40543 行）

2026-07-26 早些时候引入的 `unwrap_user()` 用的是 `marker → delimiter` **二元组**，
要求前导 marker 必须是 `# Files mentioned by the user:` 才剥壳。但 Codex 会在**任意** ambient 块
之后追加同一个分隔符：

```
<in-app-browser-context source="ambient-ui-state">
  ...自动注入的 UI 状态...
</in-app-browser-context>

## My request for Codex:
接下来完整的review下我们这部分的架构还有没有一些架构问题存在      ← 真请求
```

`<in-app-browser-context` 与 `<environment_context>` 都在 `AMBIENT_MARKERS` 里，
而 `# Files mentioned by the user:` 不在 head → `unwrap_user` 不触发 → 整条丢弃。

实测规模：**138 条 ambient 里 108 条携带真请求**，`substantive` 少报 **94 → 187（少 50%）**。

```
修复前   substantive=94   pump=25  resume=6  ambient=138
修复后   substantive=187  pump=37  resume=9  ambient=30
```

⚠️ **这一次的失真不在"首"，在"尾"**——与 `019f9a28` 正好相反。`first_substantive` 恰好正确
（L11 未被包裹），但**最后一条、决定会话终局的指令 L40395 被吞掉**。后果是
「首尾一刀」把一次**用户明确要求的架构 review**读成了 **agent 自漂**：
尾部 20% 全是 review 动作，而可见的最后一条用户指令是 L39871「提交 pr -> review」，
两者对不上 → 会误判为"agent 自己跑去做架构审查"。

→ **纪律：`first_substantive` 正确不代表 objective trace 正确。首尾一刀要两端都验壳。**

**已修复（2026-07-26）**：新增 `STANDALONE_DELIMS = ("## My request for Codex:",)`，
在 `unwrap_user()` 里**先于** `WRAPPER_MARKERS` 全文搜索，命中即剥壳，不看前导 marker。
分隔符本身就是充分条件——它只由 harness 产生，前缀是什么都不影响它后面是真请求。

### `forked_share` 的适用边界（边界修正，不推翻旧值）

`forked_share` 只测**会话内 patch 落在多少个副本路径上**，测不到"**源副本被改、派生副本落后**"。
实测 `019f9a28`：`forked_share=0.0000`（会话内所有 patch 都只打在 `.claude/skills/` 一份上），
而同一时刻磁盘上 3 份副本里 **4 个文件 md5 不同**：

```
                             .claude   .codex   hhh-skills
references/mental-model.md    2b5234   2b5b22   2b5b22     DIVERGED
references/signatures.md      4e6e44   910c4e   910c4e     DIVERGED
references/self-upgrade.md    d61f52   c4f8ec   c4f8ec     DIVERGED
scripts/session_metrics.py    cf26f0   3b8d32   3b8d32     DIVERGED
grep -c "229 条"      →  1        0        0
grep -c "P2 仍是半自动" →  1        0        0
```

即两条**已证伪结论**仍在两个已分发副本里生效。
→ 与 `local/gates.md` G1 同一根因（单会话视野测不到仓库层副本），但形态相反：
G1 是"同名仪器在上百个树里"，这里是"派生副本落后一代"。
**审计任何"改了会被 rsync/发布出去"的对象时，必须在会话外补一次副本 md5 对照，不能只看 `forked_share`。**

## 统计口径纪律（本节由三次连续踩错逼出来）

**1. gate 的依据是单次成本，不是出现频率。**
`view_image` 在某语料 2026-07 的 29 个大会话里只有 2 个用到——但用到的那个是
133 次调用 / 1790 万字符 / 占该会话输出 35.5% / 32 次压缩。
**低频高危正是 gate 最该管的东西**，用"出现频率低"降低 gate 优先级是错的。
对应地，描述一个洪水源要说清**触发条件**（"做图片工作流时"），而不是基础发生率。

**2. 「主导工具」是赢者通吃口径，回答不了「X 花了多少」。**
某月 `exec` 在 73/86 会话里排第一，不代表 `view_image` 不烧钱——它可以占 30% 而
`exec` 占 50%，照样"不主导"。问成本就用**体积占比**，问画像才用主导工具。

**3. 基线必须分时间窗，否则它自己就是过期引用。**
跨 8 个月的语料混合了已经改变的用法，拿它判断本周的会话＝**引用一个不再成立的分布**，
正是本 skill 要检测的 B 类裂缝，出现在校准环节自身。
`local/baseline.json` 应按月/季分层，至少要报告趋势。

**4. 计数 vs 比率必须一致。**
排序榜曾用 `dissat_count`、相关性用 `dissat_rate`，导致 `floor_share` 榜看起来富集不满
（8 个里 4 个），实际只是大会话用户消息多、命中机会多。同一个结论里混用两种口径＝假信号。

## 已证伪（不要重犯）

| 曾提出的阈值 | 被什么推翻 | 状态 |
|---|---|---|
| compaction ≥3 → 强制审计/handoff | **p50 = 10** | 废弃，会命中近 100% 会话 |
| 单点资源饱和 ≥20 次 | 某 case 的 39 次仅在 p75 | 废弃 |
| 66 条 timeout = "实锤" | 归一化后 timeout_rate 仅 0.04，是其他会话的 1/6~1/10 | **结论反转** |
| 修补震荡 ≥5 次 | p75=2 而 p90=16，5 是从单个 case 倒推 | 降级为占位符 |
| "三条签名已在某 case 验证 ✅" | 那是用它调出来的 n=1 自证 | 不构成验证 |
| pump_share = 0.30 | 未扣除网络中断续跑 | 修正为 0.18（虚高 67%） |
| "jq 手搓是上下文元凶" | jq 仅占输出量 1% | **错判**，真凶是原生 `read_thread` / `view_image` |
| "地板抬升不是杀手" | 60 次压缩下 +242%，占窗口 30% | **补边界**：≤20 次可忽略，>40 次成为主要约束 |
| "view_image 是主要洪水源" | 全语料只在 12/110 会话主导 | **改述**：低频高危——只在图片工作流出现，一出现即灾难级（133 次调用 / 1790 万字符 / 35.5%） |
| "12/110 说明它不重要" | 用出现频率给 gate 降权是错的 | **同样废弃**，见 §统计口径纪律 第 1 条 |
| **"结构指标能识别病态会话"** | **n=101 全部 \|r\|<0.22；排序榜不富集；连同源泄漏变量都塌到 ±0.06** | **主张收窄，见下** |

**所有定量阈值当前地位 = 占位符，不是阈值。**

## 最大的一次收窄：这个 skill 不是分类器

n=101 全语料验证结论：**没有任何结构指标能预测「会话是否有问题」。**
`instrument_patch_share`、`forked_share` 的 TOP-8 会话，用户表达的不满全部为零。

关键诊断在泄漏列：`pump_share` 与 `recurring_ask_clusters` 是**从用户消息直接派生的**，
它们也塌到 ±0.06 —— 说明**问题在标签而非预测变量**（标签召回率实测 <50%：某会话有
7 条明确不满「好烂」「很烂」「别人听到都会跑路了」，全部漏检）。

定位因此收窄为 **证据提取器 + 钻取路由器**：

```
仍然成立（直接测量，不需统计支持）
  单次工具成本 / 预算流向 / 仪器分叉的存在 / 地板轨迹 / 200:1 压缩比 / 心智模型
不成立（已放弃）
  用指标判定会话好坏；用指标排序挑出病态会话
```

判断由读它的人或审计 agent 做；指标只负责**把 776 MB 压成 4 KB 可读物证，让判断成为可能**。

⚠️ 遗留：「用户是否表达不满」可能根本不是好的验收标准——用户可能对技术上很糟的会话满意
（因为看不见），也可能对健康会话不满（因为需求变了）。更诚实的标准是**产物质量**
（PR 是否被 revert、测试是否真绿、后续是否返工），但需接外部信号。**当前未验证，不要假装已验证。**

## 尚未验证的前提（最大的方法论缺口）

1. **无对照组**：不知道签名测的是"病理"还是"会话复杂度"。基线里存在比已知卡死会话更极端的样本
   （forked=11 / maxpatch=49 / maxcmd=226），但不知它们是否也卡住了。
2. 唯一出路是**标注集**：标 20–30 个「卡住 / 正常」，算每条签名的精确率与召回率，从标注集反推阈值。
3. **最小可反驳实验**：跑全量指标；若分布呈单峰且与「卡住」标签无关，整条签名路线被证伪，需回到纯语义读法。

## 已知实现局限

- `find_recurring` 用 trigram Jaccard ≥0.45 聚类，措辞差异大的重述会漏（实证：同一授权诉求说了 3 次，
  只聚出 2 条，第 3 次因换了说法未入簇）。宁漏勿误报。
- `is_pump` 只覆盖中英文常见应答词，需随语料扩充。
- `INSTRUMENT_RE` 用路径启发式判定"仪器"，跨项目需校准。
- **P2 仍是半自动。** 当前脚本会给出 `top_tools / top_commands / top_patched /
  output_volume_by_tool`，可发现“高频、昂贵、反复手工执行”的候选，但尚未实现跨会话 tool-sequence
  motif、成功结果绑定与稳定边界提取。“复发 ≥3 次且有稳定操作序列 → skill（+harness）”目前是
  人工/审计 agent 的晋升合同，不是自动判定器。Token 成本只能排候选优先级，不能单独决定是否晋升。
- **目标 trace 当前是 preview，不是逐字档案。** `session_metrics.py` 为控制内存把每条 user message
  截到 400 字，`handoff_packet.py` 表格再截到 150 字；这与 handoff 模板“原始目标逐字、不转述”的
  合同不一致。生成正式 packet 时必须按行号二次流式提取完整 user message；该自动化尚待补齐。
