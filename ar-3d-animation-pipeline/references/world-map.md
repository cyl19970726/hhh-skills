# 世界地图 · 从 0→1 做「IP 角色 → 可绑骨 → 可动 → WebAR」(选型层)

> 看结构约定见 `_schema.md`;看原理见 `pipeline-detail.md`;看门禁检查见 `invariants.md`。
> **范围聚焦主线**:自定义 IP 角色这条路(场景/扫描/通用素材库不在主线,从略)。
> **这是 G0 方向门 / G2 路线门 动工前查的作战地图。** 大量格子还是 `待填`:外部资讯靠 research workflow
> 填(带日期/来源),"我们的实测"靠我们自己跑 A/B 填(金标准)。两者共同生长。

```node
type: Stage-map
id: map/main-line
status: proposed
confidence: medium
last_validated: 2026-06-09
note: "骨架已立,内容待填;每条比较主张须带 source/date/confidence"
```

## 主线流(每阶段→深度页)
```
概念图+分镜(2D) → [图生3D] → [绑骨] → [优化] → [动画] → [AR接入] → 部署/真机
                    paths/char-gen   paths/rigging   (见invariants门4)  paths/animation   (见invariants门6)
```
- **概念层**:门禁见 INV-CONCEPT-*(非选型,是必过的 QA 门)。
- **图生3D**:自定义 IP 角色**唯一现实路径**=AI 图生3D → [[char-gen]]。
- **绑骨**:Tripo自动 / UniRig / Make-It-Animatable / Mixamo上传 / 手工 → [[rigging]]。
- **优化**:无选型分叉,规则即 INV-OPT-*(meshopt不Draco、AR版不meshopt、skin守恒、<3MB)。
- **动画**:Mixamo重定向(基础) / Cascadeur(语义) / 程序化 / Tripo animate(边界) → [[animation]]。
- **AR接入/部署**:规则即 INV-AR-*(四版本一致、容器inset-0、真机最后一公里)。

## 决策轴(所有 paths 页同一套列;`rates` 边的投影)
| 轴 | 它决定什么 |
|---|---|
| 输入 | text / 单图 / 多视图 / 实拍 / 现成 —— 前置要准备什么 |
| 表示与拓扑 | mesh(quad/tri) / 3DGS / 隐式 —— **能否绑骨、能否 web 渲染** |
| 绑骨就绪度 | 姿势烘死? 单主体? 拓扑干净? —— 能否动 |
| 质量上限 | 几何 + 贴图精度(**带我们实测**,非厂商宣传) |
| 可控性 | 能否美术指导 / 确定性复现 / 迭代 |
| 成本·速度 | 每件 $ 与分钟 |
| 授权 | CC0 / 商用许可 / 营收阈值(如 SPAR3D) |
| Web·移动适配 | 体积、格式、要不要转换 |
| 成熟度 | 我们实测过 / 只查过资料 / 未知 |

## 表示这条正交轴(横切所有图生3D路,先记着)
- **mesh**:可绑骨、可减面、drei/A-Frame 直接渲 → **角色的默认终态**。
- **3DGS(高斯泼溅)**:同 three.js 栈、跑手机,但**无网格无骨架** → 只配做**场景/背景**,产不了会动的角色。
- **隐式场/NeRF**:研究态,导出仍要转 mesh。
→ 结论沉淀:**角色永远落到 mesh;世界模型(Marble/HunyuanWorld/Spark)最多做场景。**(详见 `pipeline-detail.md`)

## 这张图的消费场景
- **G0 方向门**:这个目标该走 2D / AI-3D / 混合 / 手工?(本图 + INV-DIR-1)
- **G2 图生3D路线门**:Tripo 单图 vs 多视图 vs Rodin vs Hunyuan3D vs 手工?查 [[char-gen]] 的对比表 + 我们的实测。
- 任何门做完决策 → 决策本身可作为一条带日期的 `rates`/选型主张回写。
