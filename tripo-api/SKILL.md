---
name: tripo-api
description: >-
  Tripo3D REST API 实战参考与统一驱动 —— 图生3D / 文生3D / 多视图重建 / 自动绑骨 / 预制动画重定向 的
  确切端点、参数、模型版本、积分、以及大量实测踩坑。当任务涉及:用 Tripo 把图/文生成 3D 网格、给模型自动绑骨
  (Mixamo 骨架)、套 Tripo 预制动画、选 Tripo 模型版本(v2.5/v3.0/v3.1/P1)、控制贴图质量/四边面/风格化、
  排查 Tripo 任务失败(1004/2006)、估算 Tripo 积分消耗 —— 时务必使用本 skill。出现 tripo3d、image_to_model、
  multiview_to_model、animate_rig、animate_retarget、tripo api key、图生3D、绑骨、tripo 积分 等关键词也应触发,
  即使用户没说"skill"。配套驱动脚本 `scripts/tripo_gen.py`。
  注:做完整 AR/动画管线请配合 `ar-3d-animation-pipeline`;本 skill 只聚焦 Tripo API 本身。
---

# Tripo3D API 实战参考

经实测(2026-06)整理的 Tripo REST API 用法 + 踩坑。**最大教训:Tripo 的 `create` 几乎不校验参数,
错参数也返回 `code:0`(任务受理),要到处理阶段才以 `error_code:1004` 失败 —— 所以"create 成功"不等于
"参数对",必须 poll 到 `success` 才算数。**

## 基础
- **Base**:`https://api.tripo3d.ai/v2/openapi`
- **Auth**:`Authorization: Bearer <key>`(key 存 gitignore 的 `.tripo-key`)
- **核心端点**:
  | 端点 | 作用 |
  |---|---|
  | `POST /upload` (multipart `file`) | 上传图 → 返回 `data.image_token` |
  | `POST /task` (JSON) | 建任务 → 返回 `data.task_id`(⚠️ 不校验业务参数) |
  | `GET /task/{id}` | 查状态/进度/输出;`status` ∈ running/success/failed/...;失败看 `error_code` |
  | `GET /user/balance` | 余额 `data.balance` |
- **通用流程**:`upload → create(type=...) → poll(/task/{id} 直到 success) → fetch(output.pbr_model/model)`。
- **网络**:常在不稳代理后 → 所有请求加重试。
- **驱动脚本**:`scripts/tripo_gen.py`(命令:`i2m / mv4 / mv / prerig / rig / animate / get / status / balance`)。

## image_to_model(图生3D,主力)
payload:
```json
{"type":"image_to_model","file":{"type":"png","file_token":"<tok>"},
 "model_version":"v3.1-20260211","texture":true,"pbr":true,
 "texture_quality":"detailed","quad":true,"style":"person:person2cartoon"}
```
- ⭐ **`model_version` 一定要显式指定**(下表),否则**回落到旧默认 `v2.5`(明显糙)**——这是"图很美但 3D 糙"的头号原因。
  | 版本字符串 | 说明 | 实测 |
  |---|---|---|
  | `v2.5-20250123` | **旧默认**,几何/贴图糙 | ❌ 别用 |
  | `v3.0-20250812` | 大跃升,脸灵动、细节翻倍 | ✅ |
  | `v3.1-20260211` | 比 v3.0 几何精度/贴图更好(2026-02-11) | ✅ **当前首选** |
  | `P1-20260311` | 生产级,**低面数下几何最精细**,风格化/游戏/AR 轻量资产 | ✅ 备选/对照 |
- **`texture_quality`**:`"standard"`(默认)/ `"detailed"`(更细)/ `"no"`。⚠️ **没有 `"HD"`(传 HD 报 1004)**。
- **`quad":true`**:四边面拓扑(绑骨形变更好)。⚠️ **quad 模型输出是 FBX**(GLB 存不了四边面)——下载的 `.glb` 其实是 FBX("Kaydara FBX")。处理见下「quad/FBX」。
- **`style`**:风格化,如 `"person:person2cartoon"`(卡通化,输入已是卡通时变化不大)、`"object:clay"` 等。
- 其它:`face_limit`(面数)、`smart_low_poly`、`pbr`、`texture`。
- 输出:`output.pbr_model`(优先)或 `output.model` + `output.rendered_image`(webp 预览图,几十 KB,验收很方便)。

## multiview_to_model(多视图重建)
`files:[front,left,back,right]`(每个 `{type:png,file_token}`,缺的给 `{}`)。
⚠️ **实测坑**:① 慢且易**卡 99%**(单图 i2m ~1min;多视图 10–25min 甚至超时)——poll 超时要调到 1500s+,且**记下 task_id**,超时后用 `GET /task/{id}` 重取;② **4 张分开生成的视图易不一致 → 重建出鬼影/五官变柔**。**结论:优先"单张精美正面图 + 高版本",比多视图更稳。**

## animate_rig(自动绑骨)
```json
{"type":"animate_rig","original_model_task_id":"<i2m_task_id>","out_format":"glb","spec":"mixamo"}
```
- 先可选 `animate_prerigcheck`(`{type,original_model_task_id}` → `output.riggable`)。
- ⭐ **服务端绑骨,吃 task_id 不吃本地文件** → quad 的 FBX 根本不用手动处理:传 i2m 的 task_id + `out_format:"glb"`,直接拿绑好骨的模型。
- **`spec`(关键,默认 `"tripo"`)**:
  - `"mixamo"` → 骨架命名 `mixamorig:Hips/...`,**能接 Mixamo 动作库 + 程序化烘焙**,但**用不了 Tripo 预制动画**;
  - `"tripo"`(默认)→ Tripo 自有骨架,**能用 `animate_retarget` 预制动画**,但接不了 Mixamo。
  - **按动画来源选 spec**:要 Mixamo/手烘(挥手/倒茶)→ mixamo;要 Tripo 预制(idle/walk/run)→ tripo。
- `rig_type`:默认 `biped`(还有 quadruped/hexapod/octopod/avian/serpentine/aquatic/others)。
- **rig 也有 `model_version`**:默认旧的 `v1.0-20240301`,有更新的 `v2.0-20250506`(更好的蒙皮,值得指定)。
- 快(~15s)。⚠️ **若源模型是 quad,绑骨输出仍是 FBX 内容**(哪怕要 glb)——要进浏览器得 FBX→GLB(见下)。
- 升级了模型就**要重绑骨**(绑骨质量 ≈ 输入网格质量)。

## animate_retarget(预制动画)—— ⭐ 可用,但**必须配 `spec:"tripo"` 的绑骨**
```json
{"type":"animate_retarget","original_model_task_id":"<spec=tripo 的 RIG task_id>",
 "animation":"preset:idle","out_format":"glb","bake_animation":true}
```
- 预制清单(human biped):`preset:idle / walk / run / dive / climb / jump / slash / shoot / hurt / fall / turn`
  (+ `preset:quadruped:walk` / `hexapod:walk` / `octopod:walk` / `serpentine:march` / `aquatic:march`)。
  **没有挥手/打招呼/倒茶/鼓掌/跳舞**(语义/社交动作得 Mixamo / Cascadeur)。
- ⭐⭐ **1004 的真正原因(实测踩坑,2026-06)**:retarget **只认 `spec:"tripo"` 骨架**。我们为接 Mixamo 而用 `spec:"mixamo"` 绑骨,结果 retarget 一律 `error_code:1004`(create 阶段 `code:0` 是假象,处理才报)。**换成 `spec:"tripo"` 绑骨 → retarget `preset:idle` 立刻成功。** 已穷举验证:与 quad/无前缀/`bake_animation` 都无关,纯粹是 **rig 的 spec**。
- 字段:`original_model_task_id`(**必须是 rig 任务**;传 i2m 任务 → create 即 `2006`)、`animation`(单个用 `animation`,多个用 `animations:[...]`)、`out_format`、`bake_animation`(默认 true)、`export_with_geometry`、`animate_in_place`。
- ⚠️ **spec 二选一的取舍**:
  - `spec:"tripo"` → **能用 Tripo 预制动画**,但骨架是 Tripo 自有命名 → **接不了 Mixamo 动作 / 我们的 mixamo 程序化烘焙**;
  - `spec:"mixamo"` → 能接 **Mixamo 动作库(挥手等)** 和程序化,但**用不了 Tripo 预制**。
  - 因为 Tripo 预制**本就没有挥手/倒茶**,做"打招呼/倒茶"这类仍走 mixamo 那条;只有想要 idle/walk/run/jump 这种通用循环动作,才值得改 tripo spec。
- 只看 **poll 到 success** 才算"能用",别被 create 的 `code:0` 骗了。

## quad/FBX 处理(只在"网页预览未绑骨纯模型"时需要)
- quad 模型 / quad 源的绑骨输出 = **FBX 内容**(文件头 "Kaydara FBX"),`@gltf-transform` 读不了(报 `Unexpected token 'K'`)。
- 转换:`node_modules/fbx2gltf/bin/<OS>/FBX2glTF -i x.fbx -o y --binary`(三角化;蒙皮/材质保留)→ 再 `gltf-transform optimize`。
- ⚠️ `fbx2gltf` 与 `@gltf-transform/cli` 用 `--no-save` 装会**互相 prune**;要么一条命令同装两个,要么用哪个临时重装。`gltf-transform` CLI 要 **Node ≥20**。
- 走 Tripo 全自动绑骨(`rig` 出 glb)时**完全不用碰 FBX**。

## 积分(实测 2026-06,起点 600)
| 操作 | 约 |
|---|---|
| image_to_model（v3.x + pbr） | 25–30 |
| 上面再加 `detailed` + `quad` | ~40 / 个 |
| animate_rig | 10–20 |
| multiview_to_model | 更贵 + 慢 |
- ⚠️ **失败任务的扣分规则不一致**:**图生成 create 被拒(参数错,create 阶段 1004)不扣分**;但**处理阶段才失败的任务(如 retarget 1004、rig)会小额扣分**。探参数优先用"会在 create 阶段被拒"的方式才真免费。
- 探参数小技巧:发请求看 `create.code`(0=受理),但**必须 poll 看 `success`** 才确认参数有效——别浪费在"create 成功但处理失败"上。

## 错误码 & 账号坑(实测)
| 码 | 含义 | 典型触发 |
|---|---|---|
| `1004` | 参数无效(通用,不指明哪个) | `texture_quality:"HD"`;mixamo 骨架去 retarget;错的 model_version(处理阶段才报) |
| `2001` | **任务不存在 / 无权访问** | **换了 API key(=换账号)后引用旧 key 建的 task_id** —— task_id 跟账号绑定! |
| `2006` | 模型类型不符合该操作 | retarget 的 `original_model_task_id` 传了 i2m 任务(必须传 rig 任务) |
- ⚠️⚠️ **task_id 是账号级的**:**换 Tripo key(尤其换号/换余额)后,之前所有 task_id 全部 `2001` 失效** → 必须从图**重新生成**(图在本地就行),不能复用旧 task。换 key 前留好本地源图。
- 余额:`GET /user/balance`。注意失败任务的扣分见上「积分」。

## 一句话决策
- 要质量:**`v3.1-20260211`**(或对照 `P1-20260311`)+ `texture_quality:detailed`(+ `quad` 若后续要绑骨/外部精修)。
- 要绑骨:**先定动画来源再选 spec** —— Mixamo/手烘 → `spec:mixamo`;Tripo 预制 → `spec:tripo`。服务端出 glb,不碰 FBX。
- 要动画:Tripo 预制(idle/walk/run…)**可用,但 rig 必须 `spec:tripo`**(mixamo 骨架 retarget 会 1004);Tripo **没有挥手/倒茶**,这类走 Mixamo / Cascadeur / 程序化。
- 永远 **poll 到 success** 才算成功;多视图记 task_id 防超时丢结果。

## ⚠️ 面部/口型动画就绪性(2026-06 血泪补:在揭小贤上撞了一整轮墙)
**核心教训:Tripo(图生3D)给的是「渲染资产」(为静态好看而生),不是「动画资产」(为变形而构建)。两者由不同流程产出,任何技术都无法在裸资产上跨越这道鸿沟。**

- **API 的 `animate_rig` = 身体骨架(biped),没有任何面部骨/blendshape/viseme。** 绑了骨 ≠ 能动脸。在裸 API 模型上做口型,只能手工硬接下巴骨/形态键 → 必败于三条资产硬伤:
  - **拓扑**:三角面乱流,**嘴周无同心 edge loop** → 单骨一转就扯歪脸、形态键一拉就撕裂。(好口型前提=嘴周环形四边 loop。)
  - **口腔内部**:嘴是「微张+一片平红」**烘进贴图**,**没有真牙/舌/喉几何** → 一张大就露平红"血盆大口"。
  - **UV 碎片化**:嘴的 UV 散落全图、和身体交错 → **没法干净重绘嘴**(一画甩满身);QuadriFlow 自动重拓扑也只出均匀四边、给不了面部 loop。
- ✅ **正路:Tripo 的口型/面部在 STUDIO(GUI)产品里,不在我们调的 API 里。** Studio 有**面部绑定 + blendshape 生成(含语音音素 viseme)+ 重拓扑**。要讲解口型 → 用 Studio 给头做 viseme,**别在裸 API 模型上硬雕**。
- ✅ **"分部件"有效**:API 无 part 参数,但可**单独生成"只有头"的高精度模型**(面数预算全给脸→面部拓扑远好于整身一次生成),头单独绑面部、身体另生成再组装。
- ⚠️ **运行时网格很可能仍是三角面**:`quad:true` 出 FBX,FBX→glTF(浏览器要 GLB)又**三角化** → quad 好布线没保到运行时;要精修/动画就在 FBX/源模型阶段做。

### Gate 0 —— 生成前必答 + 生成后必检(以后第一步就做)
1. **脸要不要动?** 只"临现+身体手势"→ API 路径够用。**要口型/表情 → 必须生成阶段解决面部**(Studio viseme / 生产级头),绝不事后硬接。
2. 要脸动 → **头单独高精度生成**(面数全给脸)。
3. **拓扑锁死**:`quad`(+ 考虑 `P1`),并验证运行时网格是否真可用。
4. **生成后机检(动画就绪性,不达标不做面部)**:① 口腔有真几何还是画死的红 ② UV 单岛还是碎片 ③ 嘴周有 loop 吗 ④ 四边面占比。
5. **小代价先验**:`rendered_image` + 一次拓扑/UV 机检判"就绪性",再决定绑骨/口型。
