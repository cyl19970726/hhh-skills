# 动画(类别深度页)

```node
type: Stage
id: stage/animation
implements: [principle/skeletal-animation]
triggers: [INV-ANIM-1, INV-ANIM-2, INV-ANIM-3]
status: proposed
confidence: medium
scope: "绑好 Mixamo 骨的角色;基础动作 + 自定义语义动作两类"
last_validated: 2026-06-09
```

**它解决什么**:让绑好骨的角色动起来。**两类动作本质不同**(→ INV-ANIM-1):
- **基础/通用**(挥手/idle/走)= 现成 mocap 重定向,可靠好看,做 MVP。
- **自定义语义**(精确"倒茶"等道具交互)= 没有现成,必须手作。

## 决策对比表(各选项 × 决策轴)
| 选项 | 适用动作 | 可控性 | 质量 | 成本·速度 | 授权 | 成熟度 |
|---|---|---|---|---|---|---|
| **Mixamo 重定向** | 基础(挥手/idle/坐/走) | 选预制 | 好(专业 mocap) | 免费,分钟级 | 免费可商用 | ⚑ 我们骨架即 Mixamo 命名,直接套 |
| **Cascadeur** | 自定义语义 | 高,AI 辅助物理 K 帧 | 高(有美感) | 人工,有免费档 | 有免费档 | 未实测,推荐 |
| **程序化(运行时)** | 自定义/微调原型 | 最高(代码) | 看功夫 | 即时 | — | ⚑ 揭小贤挥手=烘焙的程序化 clip |
| Tripo `animate` | 仅 idle/walk 预置 | 无 | — | API | — | ⚑ 证实做不了语义动作 |

## 原理(耐久 · pipeline-detail.md §1)
- pose = 各骨局部变换的函数。程序化=每帧写骨四元数;烘焙=glTF 动画轨(关键帧+插值),`AnimationMixer` 按时间采样。
- **动作准不准是时间维度的**,单张截图测不了 → 确定性 scrub `pose=f(t)` + 正向运动学读关键点(→ INV-ANIM-2,几何评估器是核心复用件)。

## 我们的实测(金标准 · 待填)
- ⚑ 揭小贤挥手:程序化 pose 按帧采样烘成 glTF clip(`scripts/bake_wave.mjs`),A-Frame 用 `jyx-clip` 组件播。
- ⚑ Tripo `animate` 实测只有 idle/walk,产不出"倒茶"。
- 🔬 待跑:倒茶动作走 **Cascadeur** vs **纯程序化**,几何 sweep(壶嘴对准杯口/不穿模/手稳)+ 视觉分镜评分对比。

## 评估(回链 INV-ANIM-2/3)
- **几何(客观/自动)**:`sweep(t0,t1,step)` 扫整段,读壶嘴↔杯世界坐标,断言对准/不穿模/脚不滑。代码模式见 pipeline-detail §2。
- **视觉(美/像)**:确定性逐帧 scrub→密集帧条→视觉 agent 对照分镜打分+给调整量。**Opus 不能直接吃视频**;micro-timing 自然度需要时再上原生视频模型(Gemini 等)当第三评委。

## 选型现状 / SOTA(易腐 · 待 research)
- _待填:AI 辅助角色动画/语义动作生成的当下选项(text-to-motion、视频驱动重定向等)是否已能产可用语义动作。_

## 触发的不变量
INV-ANIM-1(两类动作选型)、INV-ANIM-2(几何 sweep 过)、INV-ANIM-3(视觉对照分镜)。

## 坑
- A-Frame 核心不自动播 clip → 写组件建 `AnimationMixer`。多动作(临现/挥手/idle/倒茶)用 mixer 相位切换交叉淡入。
- 道具 parent 到手骨,蒙皮后随手骨世界矩阵自动跟手。
