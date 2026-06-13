# 绑骨(类别深度页)

```node
type: Stage
id: stage/rigging
implements: [principle/lbs-skinning]
triggers: [INV-RIG-1, INV-RIG-2, INV-RIG-3]
status: proposed
confidence: medium
scope: "Q版/卡通人形角色;目标=可被 Mixamo/程序化驱动"
last_validated: 2026-06-09
```

**它解决什么**:给 char-gen 出的静态 mesh 装一副骨架 + 蒙皮权重,让骨头一动网格跟着变形(LBS)。**目标骨架=Mixamo 命名** → 顺带解锁整个 Mixamo 动作库(→ INV-RIG-2,但其 blocker 性依赖动画选型 [[animation]])。

## 决策对比表(各选项 × 决策轴 · 多为 `待填`)
| 选项 | 输入 | 输出骨架 | 卡通/Q版质量 | 附属物(帽/披帛/尾) | 成本·速度 | 授权 | 成熟度 |
|---|---|---|---|---|---|---|---|
| **Tripo auto-rig** | i2m task | Mixamo 命名 | ⚑ 揭小贤可绑(prerig 过) | ⚑ 需实测,易挤压 | API,分钟级 | 见官网 | ⚑ 主力用过 |
| **UniRig** (VAST/Tripo) | mesh | Mixamo 标准 | 传闻覆盖人/兽/二次元/异形+spring bone | 待填 | 开源自托管 | **MIT 可商用** | 未实测 |
| **Make-It-Animatable** | mesh | 52 骨 Mixamo 标准 | 亚秒级 | 待填 | 开源 | 可商用 | 未实测 |
| Mixamo 网页上传 | mesh | Mixamo | 重绑,Q版有风险 | 差 | 免费 | 免费 | 待填 |
| 手工(Blender) | mesh | 任意 | 最高,但贵 | 最可控 | 人工小时级 | 自有 | 兜底 |

## 原理(耐久 · pipeline-detail.md §1)
- 学习模型为任意网格预测骨架(关节层级)+ 蒙皮权重;变形=线性混合蒙皮 LBS:`v' = Σ w_i·(B_i·invBind_i)·v`。
- prerigcheck 先判拓扑可绑性(biped)→ INV-RIG-1。
- **LBS 在肩/肘/附属物处极端姿势易挤压** → 卡通/Q版质量"不可假定必须实测"(INV-RIG-3)。

## 我们的实测(金标准 · 待填)
- ⚑ 揭小贤经 Tripo prerig 判 riggable=biped、Tripo auto-rig 出 Mixamo 骨可用。
- 🔬 待跑:Tripo auto-rig vs **UniRig** vs **Make-It-Animatable** 在同一揭小贤 mesh 上,肘/肩权重 + 帽子/肩饰变形的几何评估(geom)+ 视觉对比。这决定 Q版到底该用哪条绑骨路。

## 选型现状 / SOTA(易腐 · 待 research)
- _待填:当下卡通/Q版自动绑骨第一梯队、开源可商用清单、spring-bone 支持现状。_

## 触发的不变量
INV-RIG-1(prerig 通过)、INV-RIG-2(Mixamo 骨名 · 条件 blocker)、INV-RIG-3(实测变形)。

## 坑
- Mixamo FBX 是 `mixamorig:Hips`,three GLTFLoader 去冒号→`mixamorigHips` → 重定向前统一命名。
- 优化阶段 `quantize` 会 prune skin(→ INV-OPT-1),绑完别量化。
