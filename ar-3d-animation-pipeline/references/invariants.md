# AR 3D 管线 · 检查层:可机检不变量(每个门禁逐条校验)

> 配套 `_schema.md`(图+生命周期约定)、`pipeline-detail.md`(原理层,讲为什么)、`world-map.md`(选型层)。
> **这一层只回答"每个门必须满足什么、不满足就停"。** 起因:多视图建模长期悄悄回落 Tripo 2.5
> (脚本不传 `model_version`、也不打印),质量长期不达标却无人发现 → 教训:**散文知识不拦 bug,
> 编码成可机检不变量才拦。** 但不变量自己也是可证伪主张(见下 INV-TRIPO-VER 的修订:`v3.*` 白名单
> 会误拒未来 v4 → 已改为"地板而非白名单"),所以每条带 `status/scope/falsifier`,假设变了就翻。

## 怎么用
- 进每个门前,workflow/人按该门不变量逐条校验;**任何 `blocker` 不过 → 停,先修。**
- `检查`:`auto`(脚本可断言,优先固化进代码)/ `geom`(几何 sweep,见 pipeline-detail §2)/ `vision`(视觉 agent 对照概念分镜)/ `manual`(只能人/真机)。
- `状态`:`✅validated` / `⚠contested-prone`(scope 依赖外部现状,易翻)/ `proposed`;后跟信心 `high/med/low`。
- `严重度`:`blocker`(停工)/ `blocker(条件)`(仅在 scope 满足时为 blocker)/ `warn`。
- 标 `[代码已固化]` = 断言已落进脚本,不靠人记得查。
- **新踩的坑 → 回写成新不变量**;推翻旧的 → 按 `_schema.md` 修订纪律(refutes→contested→supersedes)。

---

## 门 0 · 方向门(动工前的元决策)
| ID | 不变量(失败模式) | 检查 | 严重度 | 状态·信心 | scope / falsifier |
|---|---|---|---|---|---|
| INV-DIR-1 | 开新 IP/新效果前必须显式评估 2D叠层 / AI-3D / 混合 / 手工 四路并记录选型理由(城隍庙曾连打磨 8 轮 2D 才被真机反馈"不是真3D") | manual / judge | blocker | ✅high | 稳定 |

## 门 1 · 概念层(进 Tripo 之前)
| ID | 不变量(失败模式) | 检查 | 严重度 | 状态·信心 | scope / falsifier |
|---|---|---|---|---|---|
| INV-CONCEPT-1 | 概念/多视图先过"概念图 QA 门"(对版/精美/多视图一致/绑骨就绪/细节),有 blocker 先改 prompt 重生(3D 超不过输入图) | vision | blocker | ✅high | 稳定 |
| INV-CONCEPT-2 | 对版角色必须图生图带参考(codex `-i`,prompt 放最前、`-i` 放最后),纯文生锁不住长相 | auto(命令形态) | warn | ✅med | 稳定 |
| INV-CONCEPT-3 | 建模图须 A-pose 手臂留缝 + 空手五指分开 + 腿微分 + 道具改"穿戴" + 大帽留作后期独立刚性件(满细节立绘会让道具烘进手/腋下粘连/碎片破面) | vision | blocker | ⚠med | scope=当前自动绑骨质量;falsifier=出现能处理手持道具/松散肢体/附属物的绑骨 → 届时可放宽 |

## 门 2 · 图生 3D
| ID | 不变量(失败模式) | 检查 | 严重度 | 状态·信心 | scope / falsifier |
|---|---|---|---|---|---|
| **INV-TRIPO-VER** | 所有出几何的 Tripo 任务(i2m/mv/mv4)必须显式传 `model_version` 且**主版本 ≥ 3**,并打印实际版本(**API 默认 = v2.5-20250123**,省略必降质) | auto **[代码已固化]** `tripo_gen.py:resolve_model()` 默认 **v3.1-20260211**、断言 major≥MIN_MAJOR、打印、拒 2.x | blocker | ✅high | scope=**地板而非白名单**(原 `v3.*` 会误拒未来 v4,已修;`P1-*` 非数字主版本暂被拒);falsifier=出现更优新 major / P1 经实测更优 |
| **INV-TRIPO-MESH** | hero/角色资产必须显式设几何模式,**别用默认 standard**:`geometry_quality=detailed` + `quad`(干净拓扑利好绑骨)+ 按需 `style`(揭小贤=`person:person2cartoon`)。v6c 已遵守;旧档曾全跑默认 standard 无 quad | auto(env `TRIPO_GEOMETRY_QUALITY=detailed`/`TRIPO_QUAD=1`/`TRIPO_STYLE=…` → `mesh_opts()`)+ geom/vision 验提升 | blocker(角色) | ⚠med | scope=主角/英雄资产;次要道具可 standard 省 credit;quad/style 最优组合 🔬待 A/B 后升 validated |
| INV-TRIPO-1 | 投料图=单主体、纯白底、rembg 抠净、近 A-pose(整场景图会糊成连体几何不可绑骨) | vision | blocker | ✅high | 稳定 |
| INV-TRIPO-2 | 投料姿势必须是想要的静止基准姿势(输入姿势被烘进几何,生成后改不动) | vision | blocker | ✅high | 稳定 |
| INV-TRIPO-3 | 用多视图时三视角必须互相一致,不确定就退回单张干净正面(视图不一致反而坑) | vision | warn | ✅med | 稳定 |

## 门 3 · 自动绑骨
| ID | 不变量(失败模式) | 检查 | 严重度 | 状态·信心 | scope / falsifier |
|---|---|---|---|---|---|
| INV-RIG-1 | `prerig` 返回 `riggable==true`(且 biped)才进绑骨 | auto(`tripo_gen.py prerig`) | blocker | ✅high | 稳定 |
| INV-RIG-2 | 绑骨产物骨名为 `mixamorig*`(three GLTFLoader 去冒号→`mixamorigRightArm`) | auto(遍历骨名) | blocker(条件) | ✅high | scope=**仅当动画走 Mixamo 重定向/程序化按 Mixamo 骨名驱动**;若动画另走他路则非 blocker |
| INV-RIG-3 | Q版/卡通必须实测肘肩与附属物(帽/披帛/尾巴)变形(LBS 极端姿势/附属物易挤压;Tripo 不行换 UniRig/Make-It-Animatable) | geom + vision | warn | ✅med | scope=卡通/Q版;"不可假定必须实测" |

## 门 4 · 移动端优化
| ID | 不变量(失败模式) | 检查 | 严重度 | 状态·信心 | scope / falsifier |
|---|---|---|---|---|---|
| INV-OPT-1 | 优化前后**蒙皮网格数守恒**;给 AR 用别量化(`gltf-transform quantize` 会 prune 掉 skin → 不会动) | auto(对比 GLB skin 数) | blocker | ✅high | 稳定 |
| INV-OPT-2 | 优化后 GLB ≲ 3MB(meshopt+webp1024);过大手机 WebGL 上下文易爆 | auto(文件大小) | warn | ✅med | scope=设备档位启发式,非硬线;高端机可放宽 |
| INV-OPT-3 | 几何压缩用 **meshopt 不用 Draco**(Draco 解码器常走 gstatic CDN,大陆可能被墙) | auto(检查 extensions) | blocker | ✅high | falsifier=Draco 解码器可自托管且大陆可达 → 届时不再禁 |
| INV-OPT-4 | AR/iOS(A-Frame)版用"中等 simplify(~0.35)+webp、不 meshopt 不量化";meshopt 版只给 R3F(A-Frame 核心 GLTFLoader 在 iOS 解不了 EXT_meshopt) | auto(按目标平台分版) | blocker | ⚠high | scope=**A-Frame 核心 + iOS + 当下**;falsifier=A-Frame 支持 meshopt 或 vendored 解码器在 iOS 稳定 |

## 门 5 · 动画
| ID | 不变量(失败模式) | 检查 | 严重度 | 状态·信心 | scope / falsifier |
|---|---|---|---|---|---|
| INV-ANIM-1 | 语义动作(倒茶等)必须手作(Cascadeur/程序化);基础动作(挥手/idle)走 Mixamo 重定向(别指望 Tripo `animate`) | manual(选型) | blocker | ⚠high | scope=Tripo `animate` 当前只 idle/walk;falsifier=Tripo/某服务能产语义动作 |
| INV-ANIM-2 | 几何 sweep() 通过:工具出口对准目标 + 不穿模 + 接触相位脚底世界坐标不平移(脚不滑)(动作准不准是时间维度,单图测不了) | geom(pipeline-detail §2) | blocker | ✅high | 稳定 |
| INV-ANIM-3 | 视觉 agent 对照分镜:确定性逐帧 scrub→密集帧条→打分+给调整量(美/像只能对照分镜判) | vision | warn | ✅med | scope=Opus 不能直接吃视频→用帧条;micro-timing 自然度需要时再上原生视频模型 |

## 门 6 · AR 接入 / iOS-WebKit / 部署
| ID | 不变量(失败模式) | 检查 | 严重度 | 状态·信心 | scope / falsifier |
|---|---|---|---|---|---|
| INV-AR-1 | AR 容器 `absolute inset-0`(相机激活时 `fixed inset-0 z-40`),否则 a-scene 塌成 width:0(iOS 黑屏头号雷) | auto(类名/样式) | blocker | ✅high | 稳定 |
| INV-AR-2 | `next.config` `images:{ unoptimized:true }`(next/image 优化管线在 iOS 让图空白) | auto(config) | warn | ✅med | scope=next/image + iOS 当下 |
| INV-AR-3 | 卡面 / 识别牌 / `.mind` / URL **四版本号强一致**(任一不一致就扫不出) | auto(版本串比对) | blocker | ✅high | 稳定 |
| INV-AR-4 | 每阶段 iOS Safari/微信/安卓 + 强光弱光真机验收(**CI 绿 ≠ 识别可用**,CV 识别受光照/角度/真机摄像头影响) | manual | blocker | ✅high | 稳定(认识论:headless 测不出真机识别) |

---

## 待办:把 `auto + blocker` 的不变量固化成 checker
目前只 INV-TRIPO-VER 落进代码。下一步写 `scripts/check_invariants.py`(或并进 workflow 门),机械化:
INV-OPT-1(skin 守恒)、INV-OPT-3(无 Draco)、INV-OPT-4(AR 版无 meshopt)、INV-RIG-2(Mixamo 骨名)、INV-AR-3(四版本一致)。
