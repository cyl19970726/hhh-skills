# 图生 3D · 自定义 IP 角色(类别深度页)

```node
type: Stage
id: stage/char-gen
implements: [principle/diffusion-to-3d, principle/multiview-constraint]
triggers: [INV-TRIPO-VER, INV-TRIPO-1, INV-TRIPO-2, INV-TRIPO-3, INV-CONCEPT-1, INV-CONCEPT-3]
status: proposed
confidence: medium
scope: "自定义 IP 角色;输出 mesh 供绑骨"
last_validated: 2026-06-09
```

**它解决什么**:把一张/几张 2D 角色概念图,变成一个带贴图、可绑骨的 **mesh**。自定义 IP 角色没有第二条路(素材库没有你的 IP;手工建模成本另算见 [[rigging]] 旁注)。

## 决策对比表(各选项 × 决策轴 · 多为 `待填`)
> ⚑=我们实测(金标准);其余=待 research(填时标 source/date/confidence)。质量上限**禁止**写厂商宣传。

| 选项 | 输入 | 表示/拓扑 | 绑骨就绪 | 质量上限 | 可控性 | 成本·速度 | 授权 | 成熟度 |
|---|---|---|---|---|---|---|---|---|
| **Tripo** | 单图/多视图/文 | mesh(tri,需减面) | 自带 prerig+rig | ⚑ 见下"我们的实测" | 抽卡;多视图加约束 | API 计费,分钟级 | 商用见官网 | ⚑ 我们主力用过 |
| Meshy | 单图/文 | mesh | 需另绑 | 待填 | 待填 | 待填 | 待填 | 待填 |
| Rodin / Hyper3D | 单图/多视图 | mesh | 待填 | 待填(传闻几何更干净) | 待填 | 待填 | 待填 | 未实测 |
| 腾讯 Hunyuan3D | 单图 | mesh | 待填 | 待填 | 待填 | 开源/可自托管? 待填 | 待填 | 未实测 |
| TRELLIS | 单图 | structured latent→mesh | 需另绑 | ⚑ 城隍庙守护神用过 | 待填 | HF Space/自托管 | 待填 | ⚑ 用过(守护神) |
| SPAR3D (Stability) | 单图 | mesh(UV+PBR) | 需另绑 | 待填 | 待填 | 待填 | **Community License 有 $1M 营收阈值** | 未实测 |

## Tripo 选项面(深挖 · 来源 docs.tripo3d.ai · 更新于 2026-06-09)
```node
type: Path
id: path/tripo
parent: stage/char-gen
triggers: [INV-TRIPO-VER, INV-TRIPO-MESH, INV-TRIPO-1, INV-TRIPO-2, INV-TRIPO-3]
status: validated
confidence: high
scope: "原生 API api.tripo3d.ai/v2/openapi;参数现状随官方变,带日期"
last_validated: 2026-06-09
```
**历史的"双重降档"早期失败**(已被我们修过):最初省略 `model_version` → 跑了 `v2.5`;且网格全走默认 `standard`、无 quad。**揭小贤 v6c 现已用 `v3.0-20250812 + texture_quality:detailed + quad:true + style:person:person2cartoon`**(用户拍板更好)。

**当前仍可拿的提升(本轮新发现)**:
1. **`model_version`**:可选 `v3.1-20260211`(最新 3.x,官方"recommended")/ `v3.0-20250812`(v6c 在用)/ `v2.5-20250123`(**API 默认,坑**)/ v2.0 / v1.4 / `Turbo-v1.0` / **`P1-20260311`**(更新的线,身份未验)。→ **v6c 还在 v3.0,值得试 v3.1**;脚本默认已升 v3.1、拒 <3.x(→ INV-TRIPO-VER)。
2. **网格/几何模式参数全集**:
   - `geometry_quality`: `standard`(默认)/ **`detailed`**(高精度,慢,+40cr)— v6c 已用
   - `quad`: bool(四边面重拓扑,+10cr,与 parts 互斥,拓扑更干净利好绑骨)— v6c 已用。⚠注:quad 模型按 FBX 导出,但绑骨走 task_id 服务端出 GLB,不用碰 FBX
   - `style`: 如 `person:person2cartoon`(Q版卡通化)— v6c 已用,**之前漏记**
   - `smart_low_poly`: bool(智能低模,+20cr)= "智能网格模式",简单输入用,复杂模型可能失败 — 未试
   - `generate_parts`: bool(可编辑分件,+40cr,需 texture=false/pbr=false)— 未试
   - `texture_quality`: standard/detailed(+20);`texture_alignment`: original_image / geometry;`face_limit`: 500–500,000
脚本经 env 全开:`TRIPO_GEOMETRY_QUALITY=detailed TRIPO_QUAD=1 TRIPO_TEXTURE_QUALITY=detailed TRIPO_STYLE=person:person2cartoon`(见 `tripo_gen.py:mesh_opts()`)。积分参考:v3.0+detailed+quad ≈40/个,绑骨 ≈10-20。

## 原理(耐久 · 详见 pipeline-detail.md §1)
- 输入图编码 → 3D 生成网络预测一种表示(隐空间/3DGS/隐式占据场)→ 抽带贴图网格(marching cubes + UV 烘焙)。
- **输入姿势被烘进几何**(→ INV-TRIPO-2);多视图给更多约束、背面更可信(→ INV-TRIPO-3)。
- 输出单个静态 tri-mesh,拓扑不规整 → 必减面优化,且**不是动画级拓扑**(与手工 retopo 的本质差距)。

## 我们的实测(金标准 · 大多 `待填`,这是地图最该长出来的部分)
- ⚑ **现状**:v6c = `v3.0 + detailed + quad + style:person2cartoon`,用户拍板比旧档好,已绑骨出 GLB。
- 🔬 **待跑 A/B**(G2 路线门要用,直接提质):
  1. **v3.0 vs v3.1**(同图同参数 detailed+quad+style)—— v6c 还在 v3.0,这条最该先跑,几乎零成本提质。
  2. **P1-20260311** 值不值得验(更新的线,身份未知;脚本现按非数字主版本拒,验明更优再放行)。
  3. `v3.1-detailed` vs **Rodin** vs **Hunyuan3D**(同一张揭小贤投料图)。
  4. `quad=on` vs `off` 对 Tripo auto-rig 蒙皮质量的影响(quad 是否真利好绑骨)。
  5. 满细节立绘 vs A-pose 清理图 对绑骨成功率的影响(验 INV-CONCEPT-3 的 scope)。
- 跑完每条 → 写成 `Evidence` 节点,`supports`/`refutes` 上面对比表里的格子。

## 选型现状 / SOTA(易腐 · 独立节 · 待 research,填时标"更新于 YYYY-MM + 来源")
- _待 research workflow 填:当下图生3D 第一梯队、各家几何/绑骨/授权/价格、开源可自托管者。_

## 触发的不变量
INV-CONCEPT-1/3(进料前 QA)、INV-TRIPO-VER/1/2/3。

## 坑
- 整场景图喂进去=糊成连体几何(INV-TRIPO-1)。模型偏大偏暗 → 必 gltf-transform + 提 toneMappingExposure。
