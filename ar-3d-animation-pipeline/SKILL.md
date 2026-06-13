---
name: ar-3d-animation-pipeline
description: >-
  从 0 到 1 制作浏览器 WebAR 的 3D 动画角色/场景的完整流程、技术原理与已验证工具链。
  当任务涉及"把一个 IP 形象/吉祥物做成「扫描识别卡或冰箱贴 → 3D 角色临现并做动作(倒茶/挥手/提灯等)」的 AR 体验",
  或需要:概念图(art direction)定调、AI 图生3D(Tripo/TRELLIS)、给 Q版角色自动绑骨(Mixamo)、
  移动端模型优化(gltf-transform meshopt)、react-three-fiber 场景装配、手作骨骼动画、
  给程序化动画做客观精度评估(几何 + 视觉 agent 双评估)、MindAR 图像追踪接入、AR 资产部署真机 —— 时,
  务必使用本 skill。涉及 codex/FLUX 生成对版参照图、Tripo API 自动建模绑骨、TRELLIS、rembg 抠图、
  GLB 减面压缩、骨骼蒙皮、扫贴/识别卡 AR、3D 吉祥物动起来、AR 冰箱贴 等关键词时也应触发,
  即使用户没明说"流程"或"skill"。
---

# 从 0 到 1 制作 AR 3D 动画(角色/场景)

把一个 2D IP 形象,变成"扫描识别卡 → 真 3D 角色临现并做动作"的浏览器 WebAR 体验的完整方法。
本 skill 是经实战验证的流程 + 工具链 + 踩坑记录。配套的 `references/` 是一个 **markdown 支撑的知识图谱**(结构约定见 `references/_schema.md`),三层:
- **原理层** `references/pipeline-detail.md` —— 每种技术为什么能 work。
- **检查层** `references/invariants.md` —— 每个门必须满足什么,blocker 不过就停工(这是过去"工作流发现不了自己脚下坑"的根治)。
- **选型层(世界地图)** `references/world-map.md` + `references/paths/{char-gen,rigging,animation}.md` —— 从 0→1 有哪些路、各路原理、实际效果差、何时选谁;G0/G2 决策门动工前查这里。

**所有知识都是可证伪主张,不是事实**:每条带 `status/scope/falsifier/last_validated`,假设变了就翻(见 `_schema.md` 修订纪律)。
**Tripo 自动建模/绑骨/动画的现成驱动脚本见 `scripts/tripo_gen.py`**(`resolve_model()` 已固化 INV-TRIPO-VER)。

## 第一性原理(先读,避免最常见的错误)
1. **概念先行(reference-first)**。先用 2D 概念图定"最终要什么"(场景、构图、动作分镜、氛围),
   再做 3D 去对齐。**跳过概念层直接盲做 3D = IP 与场景结合差**(最常见失败)。
2. **2D 概念图 ≠ 3D 投料口**。一个可渲染 3D 场景 = scene graph = 独立网格 + 骨架 + 材质 + 灯 + 相机。
   **不能把整张"角色+桌+道具+背景"的场景图丢进 Tripo**——会糊成一坨连体几何,不可绑骨、不可动。
   Tripo/图生3D **一次只吃一个干净单主体**(一个角色 / 一把壶 / 一组杯)。
3. **素材分工**:自定义 IP 角色 → AI 生成(只能这条);通用道具/家具/环境/贴图/基础动作 → **现成素材站**
   (CC0 优先,质量+省事);**自定义动作(如倒茶)→ 手作骨骼动画**(没有任何 AI/预置能直接给你)。
4. **动画分两类**。**基础/通用动作(挥手/打招呼/idle/走)→ 直接用 Mixamo 预制动作库重定向**(我们的 Tripo 骨架就是 Mixamo 命名,可直接套);**只有自定义语义动作(精确"倒茶"这类道具交互)才需手作**(Cascadeur 关键帧 / 程序化)。Tripo 自带 `animate` 只有 idle/walk,别指望它做语义动作。
5. **先易后难、先跑通再追美(MVP 分期)**。第一期做"扫贴→角色临现→**打招呼/挥手(Mixamo 预制)**"——可靠好看,先把 扫贴→3D→动画→AR 整条链端到端验收;自定义动作(倒茶)放第二期用 Cascadeur 打磨。别一上来啃最难的自定义动作。
5.5. **🚪 Gate 0:生成前先定"资产要做什么动作",再决定怎么生成(2026-06 血泪)**。
   **渲染资产(图生3D给的,为静态好看而生)≠ 动画资产(为变形而构建)**——两者不同流程产出,任何技术都无法在裸资产上跨越鸿沟。
   - **身体动作(临现/招手/手势/idle)**:Tripo API 身体骨架够用 ✓。
   - **面部/口型/表情**:Tripo API `animate_rig` **只给身体骨架、没有面部骨/blendshape/viseme** → 在裸模型上手接下巴/morph **必败**(三角乱流无嘴周loop→扯歪;口腔是贴图画死的平红→血盆大口;UV碎片→没法重绘嘴)。要口型 **必须生成阶段就解决面部**(Tripo **Studio**(GUI)有 viseme blendshape / 生产级头 / 头单独高精度生成),**绝不事后硬接**。
   - **生成后立刻机检"动画就绪性"**(不达标不做面部):口腔有真几何还是画死的红 / UV 单岛还是碎片 / 嘴周有 loop 吗 / 四边面占比。详见 `tripo-api` skill「面部/口型动画就绪性」。
6. **双评估**:几何评估测"对错"(客观、可自动),视觉 agent 测"美/像"(对照概念分镜)。两者互补。**评估必须含"整体合理性"维度**(脸:眼>鼻>嘴比例、整脸连贯)——别只孤立评单个部件(口型评了半天没发现整张脸垮了=2026-06 实错)。
7. **AR 约束**:AR 是叠在实时相机上 → **透明背景、无满屏底图**、单 WebGL 上下文、性能分档、永不黑屏。
   满背景场景留给"概念图/分享图",不进 AR 叠加层。
8. **世界模型只做"场景/背景",不做"角色"**。Genie/Sora/Decart 出像素流不可导出;World Labs Marble/腾讯 HunyuanWorld 出**场景级网格**(无绑骨)、Spark 2.0 出 **3DGS splat 背景**(同 THREE.js 栈、跑手机)——这些顶多做**茶室场景/背景**,产不了"会动的 IP 角色"。角色永远走 图生3D+绑骨 那条线。

## 总数据流
```
概念图+动作分镜(2D) → 拆件 → 逐件3D(角色: turnaround→图生3D→自动绑骨→优化 / 道具: 单图或素材站)
→ R3F 装配(道具 parent 到手骨,对齐概念) → 手作骨骼动画 + 道具/粒子 → 双评估收敛
→ MindAR 识别卡接入(位姿锚定) → GCE+cloudflare 部署 → iOS/微信真机验收
```

## 完整管线 Big Picture(每步 + 替代选项)
> 从"一张概念图"到"手机扫贴看到会讲解的 3D 角色"的完整流水线。`★`=实战默认选择,后面是潜在替代。
> **数据驱动层**(每张识别卡/贴一份 config:识别图/文案/配音/字幕/手势;共享一个多-clip 模型)包在最外面 → 加新卡=加配置+识别图+跑 TTS,不改代码。
```
[0] 概念图    ★codex 图生图(锁IP)   | FLUX文生图 / Midjourney / SD / 手绘 ;+ rembg 抠白底单主体
      ↓ 干净正面参考图
[1] 建模      ★Tripo v3.1(detailed+quad+cartoon) | Meshy / Rodin(更精) / 腾讯Hunyuan3D·微软TRELLIS(开源免费) / Blender·ZBrush手工(天花板)
      ↓ 带贴图模型(quad→FBX)
[2] 绑骨      ★Tripo rig spec=mixamo(出Mixamo标准骨,解锁Mixamo库) | Mixamo自动 / AccuRIG(免费·蒙皮常更好) / UniRig·Make-It-Animatable(开源) / Blender Rigify·手动
      ↓ Mixamo命名骨(无Jaw)   ✅验证:①骨架体检(骨数/层级/命名) ②诊断姿势扫描(肘肩膝/帽子等附属物/权重外溢) ③套一个真Mixamo动作播一遍
[3] 动画  ┬ 通用(挥手/交谈/指点) ★Mixamo免费库 | 视频动捕Move.ai·DeepMotion·Plask / Rokoko / AI文生动作MotionGPT(精度差)
          ├ 自定义交互(倒茶/端菜) ★Cascadeur(物理手K·免费档) | Blender纯手K
          ├ 微动(呼吸/点头) ★程序化烘焙(bake_*.mjs·零成本)
          └ ★★枢纽=Blender:导入任意FBX/GLB→重定向到角色骨(Auto-Rig Pro/Rokoko/Mixamo插件)→NLA合成多clip→导出GLB(几乎所有动画路线都过它)
      ↓ 多-clip GLB(Greet/Idle/Talk/Pour/Point…)
[4] 配音      ★edge-tts(普通话·免费无key) | ElevenLabs(克隆专属音·付费) / 火山·Azure·腾讯云 / GPT-SoVITS(开源克隆) / 真人(方言唯一路)
      ↓ narration.mp3
[5] 字幕      ★edge-tts SentenceBoundary→cues.json | 强制对齐aeneas·MFA(真人配音无时间轴时) / WebVTT
      ↓ cues.json [{start,end,text}]
[6] 口型      ★不做(模型无blendshape)→"说话身体动画+字幕"承载 | 加viseme blendshape(Didimo·ReadyPlayerMe·Blender shape key)+音频→口型(Rhubarb·wawa-lipsync·Audio2Face)
[7] 优化      ★gltf-transform webp+texture2048+非meshopt(iOS A-Frame要求) | meshopt(仅three.js直连可用) / KTX2·Basis(更省显存) / Draco(被墙慎用)
      ↓ AR用GLB(~5MB,多clip+蒙皮)
[8] AR运行时  ★MindAR+A-Frame(图像追踪) | MindAR+three.js(更可控·能meshopt) / 8thWall(付费·最强) / Babylon.js ;播放=AnimationMixer多clip+crossFade,字幕按audio.currentTime取cue,默认静音
      ↓ 状态机:Greet→Idle→Talk(配音+字幕)→Idle
[9] 部署      ★GCE+cloudflare quick tunnel(staging) | Vercel·Netlify / 国内CDN+OSS(正式·国内访问快)
```
**枢纽认知**:① **Blender=动画万能枢纽**(重定向/合成/导出几乎都过它,免费,值得立成标准管线;可用 blender-mcp 驱动);② **Tripo 只管[1]建模+[2]绑骨,无任何自定义动画能力**(retarget 只有固定预制,且需 spec=tripo——但预制窄;要丰富手势就 spec=mixamo + Mixamo库);③ **数据驱动 config** 让内容能批量、AR 按 slug 动态加载。
**成本**:核心链(Blender+Mixamo+Cascadeur免费档+edge-tts+gltf-transform+MindAR)≈**零成本**;只 Tripo积分([1][2])+可选 ElevenLabs/8thWall/真人配音 要钱。详见 `tripo-api` skill。

## 阶段流程 + 已验证做法

### Stage 1 — 概念层(2D 美术方向,务必先做)
产出:① 最终场景图;② **动作分镜**(动作的几个关键帧);③ 背景/色彩气氛;④ 角色多视图 turnaround。
- **对版 IP 用 codex 图生图**(参考图做条件锁角色长相):
  `codex exec --sandbox workspace-write --skip-git-repo-check "<prompt 放最前>" -i ref1.png ref2.png`
  ⚠️ `-i` 是可变参数会吞掉后面的位置参数,**prompt 必须放最前、`-i` 放最后**。出图落 `~/.codex/generated_images/<uuid>/ig_*.png`,编排者再 `cp` 取走。
- **兜底/非 IP 构图**用 HF serverless 文生图(FLUX.1-schnell),需 token 带 "Inference Providers" 权限:
  `InferenceClient(model="black-forest-labs/FLUX.1-schnell", token=…).text_to_image(prompt, width=832, height=1216)`
- codex 图像后端偶发 `ServerError`(瞬时),重试或改用兜底。

### Stage 2 — 资产分解
把概念图拆成离散资产清单:角色、各道具、桌/家具、背景、粒子(烟/汽/光)。每件单独生产。

### Stage 3 — 角色:图 → 3D 网格
- 准备**干净、正面/多视图、姿势良好(近 A-pose、手脚分开)、纯白底**的角色参考(rembg 抠图)。
  rembg 用库 API 绕过 CLI 缺失依赖:`from rembg import remove,new_session; remove(img,session=new_session("u2net"))`。
  ⚠️ 满构图照片直接喂会把动态姿势/飘带/背景烘成废几何 → 必须干净单主体。
- 图生3D:**Tripo API**(`scripts/tripo_gen.py i2m <cut.png> <out.glb>`,带贴图);备选 **Meshy**、**SPAR3D**(Stability,单图→UV+roughness/metallic 的 GLB,但**商用受 $1M 营收阈值的 Community License 限制,要记账**)、TRELLIS(HF Space)。
  原理:图编码→3D 生成网络→抽带贴图网格;**姿势被烘死**。
- ⭐⭐ **质量天花板其实是"参数没开对",不是 AI 不行(本轮最大教训)**。Tripo API 默认参数偏低,务必显式指定:
  - **`model_version`**:**API 默认是旧的 `v2.5-20250123`(明显糙)** → 一定改 **`v3.0-20250812`**(脸更灵动、刺绣/几何细节翻倍)。光这一项就从"糙"变"精美"。
  - **`texture_quality`**:默认 `standard` → 用 **`detailed`** 更细。⚠️ **没有 `HD` 这个值(传 HD 会 1004 报错)**,正确是 `standard`/`detailed`/`no`。
  - **`quad: true`**:四边面拓扑,绑骨后形变更自然。⚠️ **quad 模型 Tripo 按 FBX 导出(GLB 存不了四边面)**——见 Stage 4 的处理。
  - **`style`**:可选风格化,如 `"person:person2cartoon"`(卡通化,你要"精美卡通"可试;输入已是卡通时变化不大)、`object:clay`、`person2cartoon` 等。
  - **`face_limit`**、`smart_low_poly` 控面数。
  - 例:`{"type":"image_to_model","model_version":"v3.0-20250812","texture":true,"pbr":true,"texture_quality":"detailed","quad":true,"style":"person:person2cartoon"}`
- ⚠️ **多视图 turnaround 输入(正/左/后/右)理论上背面更全**,但实测有坑:① **多视图重建慢且易卡 99%**(单图 i2m ~1min,多视图能 10-25min 甚至超时,要 task_id + 长轮询/重取);② **4 张分开生成的视图易不一致 → 重建出鬼影/五官变柔**。**结论:优先"单张精美正面图 + v3.0",比多视图更稳更可控**;只有当背面信息确实关键、且 4 图能保证严格一致时才上多视图。
- 💰 **积分(实测 2026-06)**:v3.0 带 PBR 一次 ≈ **25-30 积分**;再加 `detailed`+`quad` ≈ **~40 积分/个**;绑骨 ≈ **10-20 积分**。⚠️ **扣分分情况**:图生成在 **create 阶段被拒(参数错)不扣分**;但**处理阶段才失败的任务(retarget/rig 等)会小额扣分**——探参数别用后者。
- ⭐ **Tripo API 一切细节(端点/参数/模型版本 v2.5→v3.0→`v3.1-20260211`→P1/quad-FBX/绑骨/retarget 实测/积分)统一见独立 skill `tripo-api`**。两条铁律:**① 显式 pin 最新 `model_version`(默认会回落到糙的 v2.5);② create 不校验参数,必须 poll 到 success 才算数。**

### Stage 4 — 自动绑骨
- 先验可绑性:`tripo_gen.py prerig <i2m_task_id>` → `RIGGABLE: True, biped` 才继续(Q版大头+帽子也常可绑)。
- 绑骨:`tripo_gen.py rig <i2m_task_id> <out_rigged.glb> mixamo` → 输出 **Mixamo 命名人形骨架**
  (`mixamorigHips/Spine/RightArm/RightForeArm/RightHand/...`)。
  原理:学习模型预测骨架+蒙皮权重,**线性混合蒙皮 LBS** 让骨动带动网格。
  Mixamo 命名 = 能重定向 Mixamo mocap + 程序化精确驱动某根骨。three GLTFLoader 会把 `:` 去掉→ `mixamorigRightArm`。
- ⭐ **绑骨吃的是 task_id(服务端),不是本地文件 → quad 的 FBX 根本不用我们碰**。`rig` 传 `original_model_task_id` + `out_format:"glb"`,Tripo 在服务端对四边面网格绑骨、直接吐**绑好骨的 GLB**(正常材质)。四边面的形变好处在服务端已吃到,网页 GLB 三角化无所谓。
- ⚠️ **升级了模型就要重绑骨**。绑骨质量 ≈ 输入网格质量(quad + 干净 A-pose),所以**先把模型做到最好(v3.0/detailed/quad)再绑**;别在旧 v2.5 上绑完才发现网格糙——白绑。
- **只有要"网页预览未绑骨的纯模型"时才需把 quad 的 FBX 转 GLB**:`node_modules/fbx2gltf/bin/<OS>/FBX2glTF -i x.fbx -o y --binary`(三角化)→ 再 gltf-transform 优化。⚠️ **`fbx2gltf` 和 `@gltf-transform/cli` 用 `--no-save` 装会互相 prune 掉**,需要哪个就临时重装;且 **gltf-transform CLI 要 Node ≥20**(shell 若是 18 会 ESM 报错,用 `~/.nvm/.../v2x/bin/node` 跑)。
- **备选(Tripo 对 Q版/卡通绑骨质量不行时,务实测验证)**:开源 **UniRig**(VAST/Tripo,MIT 可商用,覆盖人/兽/二次元/异形+spring bone)、**Make-It-Animatable**(亚秒级,输出 **52 骨 Mixamo 标准骨架**)。三者都出 **Mixamo 标准骨架** → **顺带解锁整个 Mixamo 动作库**(挥手/idle/坐等直接套)。
  ⚠️ 研究结论:**卡通/Q版角色的自动绑骨质量"不可假定,必须实测"**(肘/肩权重、附属物如帽子/披帛/尾巴变形)——用 Stage 9 几何评估器盯。

### Stage 5 — 移动端优化(必做,否则 WebGL 上下文会爆)
`npx -y @gltf-transform/cli optimize in.glb out.glb --compress meshopt --texture-compress webp --texture-size 1024`
(若 `npx` 链不到 bin:`npm i --no-save @gltf-transform/cli` 后用 `node_modules/.bin/gltf-transform`)。
21MB→~2.6MB,蒙皮保留。**用 meshopt 不用 Draco**(Draco 解码器走 gstatic,大陆可能被墙;meshopt 解码器随包内置,drei `useGLTF` 默认支持)。
- ⭐ **别过度降贴图(实测)**:`--texture-size` 从 2048→1024 **文件几乎不变**(webp 压得好:单角色 2048 版 4.8MB vs 1024 版 4.3MB)——清晰度却差不少。**真正代价是显存**(每张 2048 贴图解码后 ~22MB GPU,base+normal 两张 ~45MB)。**单个 hero 角色用 2048 在新手机完全 OK**;老机型/多模型场景才降到 1536/1024。先上 2048,真机黑屏/卡再降——别一上来就降糊。
- iOS A-Frame 路线**不能用 meshopt**(见踩坑),所以 AR 版 = `--compress false --texture-compress webp --texture-size 2048`(非 meshopt);R3F 预览版才用 meshopt。

### Stage 6 — 道具与环境
- 通用件(茶具/家具)优先**素材站现成 GLB**(见下"素材站"),次选逐件 Tripo;背景用 **HDRI(IBL 基于图像光照)** 或 2D 贴片。
- **AR 透明背景**;满背景只给概念/分享图。

### Stage 7 — 场景装配(react-three-fiber)
- 复用模式:`React.lazy` 懒加载 R3F 舞台 + WebGL 能力探测 + 无 WebGL 回落 2D;tier 分档 full/lite/2d。
- 关键技巧:**把道具(如茶壶)`parent` 到角色的手骨节点**(`rightHandBone.add(propGroup)`)→ 蒙皮后手骨世界矩阵随动画更新,道具自动跟手。
- `useGLTF` 默认带 meshopt 解码;`<Canvas onCreated>` 里设 `gl.toneMappingExposure≈1.5` 提亮(Tripo 贴图偏暗)。

### Stage 8 — 动画(分两类:预制重定向 vs 自定义手作)
**先做基础动作(预制,可靠好看),自定义语义动作放后期。**
- **基础/通用动作(挥手/打招呼/idle/走)= Mixamo 预制重定向(首选 MVP)**:从 Mixamo 下动作 FBX → 重定向到我们的 Mixamo 命名骨架。两条路:
  (a) 骨名对齐(`mixamorig:Hips`↔`mixamorigHips`)直接把 clip 应用到现有优化 GLB 的骨架,用 three `AnimationMixer` + `SkeletonUtils.retargetClip` 播;
  (b) 把网格上传 Mixamo 自动绑骨+选动作→下载带动画 FBX→ gltf-transform 转 GLB(更省但重绑、Q版有风险)。
- **自定义语义动作(精确"倒茶"等)= Cascadeur(推荐,替盲调程序化)**:Cascadeur 导入 Mixamo 标准骨架(FBX/DAE),AI 辅助物理关键帧做优雅动作,**导出 glTF/GLB 动画轨**直接进 three.js。比纯程序化更有美感。
- **程序化(运行时,快速原型/微调)**:每帧设骨骼四元数 = `rest × baseOffset`,按相位 `slerp`;道具跟手骨;茶汤=细长 mesh、茶汽=加色 billboard、杯满=缩放/shader。暴露 `window.__rig.setPose(bone,[x,y,z])` **运行时调参**,配合 Stage 9 评估器在**同一浏览器不导航**地快速收敛。
- 多动作播放:`AnimationMixer` 管多个 clip(临现/挥手/idle 循环/倒茶),按相位机切换+交叉淡入。

### Stage 9 — 双评估器(把"动画准不准/美不美"变成可迭代)
**这是核心,单张截图测不了时间维度的动作。** 详见 `references/pipeline-detail.md` 的评估器代码模式。
- **几何评估(客观,自动)**:把动画时间与挂钟解耦 `pose=f(t)`(确定性 scrub);埋点暴露关键点(如壶嘴尖)与目标(茶杯)的 Object3D;
  一个 `sweep(t0,t1,step)` 函数循环 t:`applyPose(t)`→`scene.updateMatrixWorld(true)`(正向运动学)→读世界坐标→算"壶嘴到最近杯的水平距/高于杯口"→返回整条轨迹+判定。
  **一次 eval 出客观精度报告,无需截图。**
- **视觉评估(美学/对齐)**:确定性逐帧 scrub→截图→拼连环图/GIF → 交 **codex/claude 视觉 agent 对照概念分镜**打分 + 给具体调整量 → 用运行时调参接口应用 → 重渲 → 收敛。
- 可编排为多 agent workflow(codex 生图+判图、claude 综合)。

### Stage 10 — AR 接入(MindAR 图像追踪)
- 把识别卡/冰箱贴图编译成 `.mind`(多尺度特征点/描述子);运行时相机帧提特征→匹配→PnP 估 6DoF 位姿→锚定 3D。
- 卡面/识别牌/`.mind`/URL **四版本号强一致**;容器 `absolute inset-0` 防 a-scene 塌成 width:0(iOS 黑屏头号雷);
  微信 WKWebView 默认无 `getUserMedia` → 相机 AR 当彩蛋 + 2.5D/2D 降级;`images:{unoptimized:true}` 防 next/image iOS 空白。
- 详细 iOS-WebKit 坑参考 `webar-mindar-ios` skill。

### Stage 11 — 部署 + 真机
tarball → GCE → cloudflare quick tunnel(URL 不变);Playwright-WebKit 无头验证入口/降级可达;
**CI 绿 ≠ 识别可用**,真机识别是独立最后一公里(iOS Safari / 微信 / 安卓矩阵 + 强光弱光)。

## 素材站(通用道具/环境/动作/贴图;商用必看授权)
| 类别 | 站点 | 授权 |
|---|---|---|
| 3D 模型 | **Sketchfab**(筛 CC0/CC-BY)、**Poly Haven**(CC0)、Quaternius/Kenney(CC0)、CGTrader/TurboSquid(逐件核对)、中文 爱给网/cgmodel(授权含糊,核实) | 见标注 |
| 人形动作(基础) | **Mixamo**(免费可商用;我们骨架就是 Mixamo 命名→直接重定向挥手/idle/坐) | 免费 |
| 自定义动作精修 | **Cascadeur**(AI 辅助物理关键帧,导入 Mixamo 骨、导出 glTF/GLB→three.js;做"倒茶"这类优雅动作) | 有免费档 |
| 开源自动绑骨 | **UniRig**(MIT)、**Make-It-Animatable**(Mixamo 标准 52 骨) | 可商用 |
| HDRI/贴图 | **Poly Haven / ambientCG** | CC0 |
| 场景/背景(非角色) | World Labs **Marble**(场景 GLB)、腾讯 **HunyuanWorld**(场景网格)、**Spark 2.0**(3DGS,同 THREE.js 栈、跑手机) | 见各自 |
| 2D 概念参考 | ArtStation/Pinterest(看姿势/构图,非直接用) | — |
- **优先 CC0**;CC-BY 要署名;**建 `assets-manifest` 记 来源/授权/署名**(商用上线前合规需要)。
- 格式优先 **glTF/GLB**;Mixamo FBX → gltf-transform/Blender 转;骨架保 Mixamo 命名。

## 踩过的坑(hard-won)
- **整场景图喂 Tripo = 糊成一坨**;Tripo 只吃干净单主体,绑骨只对单个 biped 角色。
- **Tripo `animate_retarget` —— 可用但有 spec 陷阱**(2026-06 实测,详见 `tripo-api` skill):预制只有 `idle/walk/run/dive/climb/jump/slash/shoot/hurt/fall/turn`(**无挥手/打招呼/倒茶**)。⭐ **retarget 只认 `spec:"tripo"` 绑骨**——用 `spec:"mixamo"` 绑骨去 retarget 会一律 `error_code:1004`(我们当初就栽在这,误判成"不可用";换 tripo spec 后 `preset:idle` 立刻成功)。**spec 取舍**:要 Mixamo 动作/程序化(挥手/倒茶)→ `spec:mixamo`(则放弃 Tripo 预制);要 Tripo 通用循环(idle/walk)→ `spec:tripo`(则接不了 Mixamo)。→ 我们要"打招呼/倒茶",Tripo 预制给不了,所以仍走 **Mixamo "Waving" 重定向** / **Cascadeur** / **程序化 `bake_wave.mjs`**;只有想加 idle 待机才值得用 tripo spec。
- **codex `-i` 参数贪婪**:prompt 放最前、`-i` 放最后,否则 prompt 被当图吞掉走 stdin 变空。
- **codex 图像后端偶发 ServerError**(瞬时);**HF 匿名额度易耗尽**,token 走 serverless 需 "Inference Providers" 权限。
- **git worktree 开发**:`node_modules` 软链 + 任何指向项目外的软链(如 `D:`)会让 **Turbopack 报 "leaves the filesystem root"** → 把软链换成真实目录(本地 rsync 复制,免网络)。
- **无头预览浏览器(Preview MCP)对重 WebGL 易丢上下文/不稳**;真渲染验证以**用户真实浏览器/真机**为准;几何评估器不依赖渲染、最可靠。
- **Tripo/TRELLIS 模型偏大偏暗**:必做 gltf-transform 优化 + 提高 toneMappingExposure。
- **rembg CLI 缺依赖**就用库 API(`from rembg import remove`)。
- **Mixamo 重定向骨名**:Mixamo FBX 是 `mixamorig:Hips`,three GLTFLoader 把冒号去掉成 `mixamorigHips` → 重定向前需统一命名(或用 `SkeletonUtils.retargetClip` 的骨名映射)。
- **世界模型不产可绑骨角色**(已核实:Genie/Sora/Decart 出像素流;Marble/HunyuanWorld 出场景网格无骨;3DGS 出 splat 无 mesh)→ 角色永远走 图生3D+绑骨;世界模型最多做场景/背景。

## 0→1 快速检查清单
- [ ] Stage1 概念图 + 动作分镜已产出并由人确认(别跳过)
- [ ] 角色干净参考:**精美 + A-pose(手臂离身~40°、空手、腿微分)+ 道具改"穿戴"非"手持" + 白底 + rembg**。多视图能提背面质量,但**视图不一致反而坑**;不确定就用**单张干净正面**(对绑骨更稳)。先过"概念图 QA 门禁"(见下)再进 3D
- [ ] 图生3D → prerig 通过 → 绑骨(Tripo Mixamo;Q版不行换 UniRig/Make-It-Animatable)→ gltf-transform(meshopt)优化 <~3MB
- [ ] **MVP 第一期:扫贴→临现→挥手/打招呼(Mixamo 预制重定向)** 端到端跑通验收
- [ ] 第二期:自定义动作(倒茶)用 **Cascadeur** 烘 glTF clip,几何评估 sweep() 通过 + 视觉 agent 对照分镜
- [ ] 道具:素材站现成(CC0)或逐件 Tripo;环境 HDRI;场景背景可选 Marble/Spark;AR 透明背景
- [ ] R3F 装配(`AnimationMixer` 管多 clip:临现/挥手/idle/倒茶,相位切换交叉淡入),道具 parent 到手骨
- [ ] MindAR `.mind` + 四版本一致 + 三级降级
- [ ] GCE+cloudflare 部署 + iOS/微信真机识别验收
- [ ] assets-manifest 授权合规

## 当前实战版本快照(揭小贤·功夫茶,2026-06,会持续迭代)
**模型迭代史(关键)**:v3(Tripo 旧默认 **v2.5** → 偏糙)→ 发现"糙=参数没开对" → **v6c = `v3.0-20250812` + `texture_quality:detailed` + `quad:true` + `style:person:person2cartoon`**(用户拍板"v6c 更好")。v6c 已 Tripo 服务端绑骨出正常材质 GLB(7.71MB),**准备接进 AR**。
**已跑通(端到端真机可扫)**:扫功夫茶冰箱贴 → 揭小贤**站在贴上、临现+挥手**;全屏 AR;GCE strategy-cs2 + cloudflare 稳定 URL。`/ar/magnets/gongfucha/compare` 做并排转盘对比页(选模型很有用)。
**仍不完美(待迭代)**:① 升级到 v3.0 后精美度上了一大台阶,但 AI 图生3D 仍非美术级天花板(要再上得 Blender/手工);② AR 角色**朝向/大小靠 URL 参数手调**(rx/ry/rz/s/px/py/pz),未在真机定死默认;③ A-Frame 版 GLB 偏大;④ 文字胶囊触发后不复位(MindAR targetLost 不稳);⑤ `.mind` 可能误触发;⑥ **动画**:Tripo 无挥手预置 → 当前是手烘程序化挥手;升级需 Mixamo "Waving" 重定向或 Cascadeur(倒茶);v6c 重绑后动画要重新接。

## 新增实战经验(本轮血泪)
- **概念图 QA 门禁(强烈推荐)**:进 Tripo 前,用一个 **vision-agent workflow** 评审 2D 概念/多视图,维度=对版/精美度/多视图一致/图生3D-绑骨就绪/细节清晰,**有 blocker 就先改 prompt 重生,通过了才花钱建模**。本轮它精准抓出"表情呆/眼睛小/手指糊/手持道具会烘进网格/贴身手臂蒙皮粘连/巨帽破人形"等——省了无效建模。
- **IP 立绘 ≠ 建模图(关键认知)**:满细节立绘(巨大帽子、手持道具、贴身手臂、悬浮流苏)**对图生3D+自动绑骨是毒**(破人形 silhouette、道具烘进手、腋下/腿间蒙皮粘连、悬浮碎片破面)。建模图要:**A-pose 手臂张开留缝、空手五指分开、腿微分、道具改"穿戴在身上"、大帽必要时后期作"独立刚性件"装到头骨**(不进蒙皮)。
- **精美度从 2D 源头决定**:3D 超不过输入图。prompt 锚 **POP MART / Pixar 级**:大水亮眼+双高光、张嘴笑、腮红、圆脸、glossy vinyl + rim light;负面词 `flat shading, dull lifeless eyes, blank expression, mitten hands`。
- **A-Frame iOS 加载坑**:A-Frame 核心 GLTFLoader 在 iOS 上**解不了 EXT_meshopt** → AR 路线出**非 meshopt 版**(simplify+webp,仅 `EXT_texture_webp`);meshopt 版只给 R3F。⚠️ `gltf-transform quantize` 会**prune 掉 skin**(蒙皮没了)→ 给 AR 用就别量化,改"中等 simplify(ratio~0.35)+ 不压缩"。也可给 a-scene 设 `gltf-model="meshoptDecoderPath: …"` + vendored decoder 用 meshopt 版,但 iOS 上不稳,非 meshopt 更省心。
- **程序化动画→烘成 glTF clip**:A-Frame 核心不自动播 clip,写个小组件 `jyx-clip`(model-loaded 时建 `THREE.AnimationMixer` 播命名 clip,tick 更新);程序化 pose 用脚本按帧采样四元数写进 glTF 动画轨(`scripts/bake_wave.mjs`),A-Frame/three 都能播。
- **全屏 AR**:相机激活时容器 `fixed inset-0 z-40`,退出键浮动、状态用顶部不挡画面的胶囊(别用占满屏的 2D 覆盖层挡住 3D)。
- **运行时可调变换**:AR 里角色 `rotation/scale/position` 做成 **URL query 可调**(`?rx=&ry=&rz=&s=&px=&py=&pz=`),真机上不重部署即可拨正朝向/大小,定好再写死默认。MindAR 锚定 = **绕着贴移动手机就能看各角度(体感),无需陀螺仪代码**。
- **🗣️ 口型正路:动画不友好的 3D 资产 → 2D 会说话的脸(本轮验证通过,血泪)**。Tripo 等图生3D 资产做不了 3D 口型(已证 4 法皆败,见 Gate 0 / `tripo-api` skill)。**正解=2D 叠加,且 sprite 用 AI 图生图供"美术手感"**(我手画 PIL 嘴丑)。完整配方:
  - **codex 图生图**(`codex exec --sandbox workspace-write "<prompt最前>" -i 参考图`)锁 IP,生对版可爱的几个**口型态**(闭/微张/中开/大笑)。⚠️ codex 生图**慢**(读完内置 imagegen skill→规划→生成,几~30min),**必须在 prompt 里要它最后输出保存的绝对路径**(否则你找不到文件;别过早 kill,它会成功);harness worker 默认 5min 超时会杀它→在主循环跑或调高 timeout。
  - **锁定底脸 + 只换嘴 ROI**:codex 各帧是独立重画整脸 → 非嘴部(眼/帽/腮红)帧间漂移 → 切帧**全脸抖**(致命,agent loop 评审在部署前抓到)。修:取一张定底脸,PIL 把各帧的嘴 ROI **羽化贴**到同一底脸 → 只嘴变。
  - **抠白底→透明**(border flood-fill 去连通白、保留牙/眼内部白)+ resize/webp(~46KB/帧)。
  - **AR 叠加**:讲解时一个 `a-image` plane 叠在 3D 头部(位置/大小 URL 可调真机定),按振幅切帧;讲完隐藏。身体仍走 3D。
  - **振幅档位按真实配音分位校准**(说话段 p33/p66 做阈值),否则只在 0/1 帧切=只见 2 个嘴型。
- **📵 iOS 配音被截断坑(本轮血泪)**:为取振幅做口型而用 `AudioContext.createMediaElementSource(audio)→analyser→destination` 改道播放,**iOS 的 AudioContext 易被中断 → 配音播一小段就停**(还把 `<audio>` 的默认输出夺走)。**正解:固定音频文件就别用 Web Audio**——**离线预计算振幅包络**(同管线,存 `narration.amp.json {fps,amp[]}`),运行时**普通 `<audio>` 直接播**(iOS 稳)+ 按 `audio.currentTime` 查包络驱动嘴。同一 `currentTime` 也驱字幕=零漂移。(Range 206 不是这坑;cloudflare/Next 默认支持 Range。)
- **部署坑(GCE+cloudflare)**:① 项目若有 `.npmrc cache=D:/…`(Windows 路径)会让 npm 把缓存写进项目 + 在 Linux 造怪目录 → 部署脚本里 `rm -f .npmrc` + `npm ci --cache $HOME/.npm-xxx`;② VM 可能**磁盘满**(共享生产机,只清绝对安全的 journald 日志 `journalctl --vacuum-size=200M` + 自己的旧部署,**别碰别人的 /var/lib 数据**);③ IAP SSH 抖(255):**关沙箱 + 单发 SSH 在 VM 后台跑自包含脚本(起隧道→写 URL 到文件)→ 另一次 SSH 读文件**,别一条命令里又起又读;④ `KEEP_TUNNEL=1` 只重启 next 保 URL 不变;⑤ codex 内置图像后端**时好时坏(ServerError)**,重试即可。
