---
name: blender-mcp
description: >-
  用 Blender MCP(blender-mcp 插件 + socket)程序化驱动 Blender 做 3D 动画管线的实战方法论 + evaluator + 踩坑。
  当任务涉及:用 Blender 给角色做/改动画、重定向 Mixamo 动作、IK 摆姿势、NLA 合成多 clip、导出 glTF/GLB、
  在 Blender 里渲染验证、清理/重绑骨、把 Tripo/FBX 模型加工成带多动作的 AR 模型 —— 时使用本 skill。
  出现 blender、blender-mcp、execute_code、bpy、armature、retarget、IK、glTF导出、骨骼动画、动画评估 等关键词也应触发。
  配套:动画来源/管线的全局地图见 `ar-3d-animation-pipeline`;Tripo 建模绑骨见 `tripo-api`。
  ⚠️ 活文档:每次实践有新经验就往"踩坑/经验"追加。
---

# 用 Blender MCP 程序化做动画(实战方法论 + evaluator)

我(agent)通过 MCP 给运行中的 Blender 发 Python,程序化地导入/绑骨/K帧/重定向/渲染/导出 —— 不靠人手 K,也不依赖 Mixamo 在线。**比纯 JS 程序化烘焙强**:有 IK、约束、曲线缓动、NLA 合成、以及"渲染回环"自己边做边看。

## 0. 设置(一次性,已完成记录)
- `brew install --cask blender`(Blender 5.x)。
- 插件 **blender-mcp**(ahujasid):可无头装+启用 —— `bpy.ops.preferences.addon_install(filepath="addon.py"); bpy.ops.preferences.addon_enable(module="blender_mcp_addon"); bpy.ops.wm.save_userpref()`(插件 raw 在 `raw.githubusercontent.com/ahujasid/blender-mcp/main/addon.py`)。
- 注册 MCP:`claude mcp add blender -- uvx blender-mcp` + `codex mcp add blender -- uvx blender-mcp`(两边连同一个 Blender)。
- **用户必须在 Blender GUI 里启动服务**:`N` 键 → 侧边栏 `BlenderMCP` 标签 → `Connect to Claude`(监听 localhost:9876)。GUI 那步代替不了。
- ⚠️ 原生 `mcp__blender__*` 工具要**重启会话**才出现(MCP 中途加的);在那之前直接走 socket(见下)。

## 1. 连接 & 协议(已验证)
插件在 **localhost:9876** 收**裸 JSON**:`{"type":..., "params":{...}}` → `{"status":"success"|"error", "result"|"message":...}`。
- 命令名(实测):`get_scene_info` / **`execute_code`**(不是 execute_blender_code!)/ `get_viewport_screenshot` / `get_object_info` / 各资产站(polyhaven/hyper3d/sketchfab/hunyuan3d)。
- 助手脚本 `scripts/blender_cmd.py`:`python blender_cmd.py scene|exec <pyfile>|shot <out.png>`。
- ⭐ **场景状态跨调用持久**:同一个 Blender 实例,import 一次后,之后的 execute_code 都能用之前的对象(逐步搭建)。**因此必须幂等**:开新动画前复位 pose、清理临时相机/灯,从干净态来。
- ⚠️ 无 clock/random 概念无所谓,但**别假设场景是空的**——先 `get_scene_info` 看现状。

## 2. 动画授权方法(B 路线核心)
### 导入 / 导出(已验证)
- 导入 FBX(Mixamo/Tripo-quad 绑骨输出常是 FBX):`bpy.ops.import_scene.fbx(filepath=...)`(扩展名最好真是 .fbx)。
- 导出 GLB:`bpy.ops.export_scene.gltf(filepath, export_format='GLB', use_selection=True, export_skins=True, export_animations=True, export_yup=True)`。
- **骨名**:Mixamo `mixamorig:Head` 的**冒号在 glTF 导出里保留**;three.js GLTFLoader 加载时会把 `:`→去掉/净化,重定向/clip 命名要对齐。
### FK 关键帧(最简)
```python
arm=bpy.data.objects['Armature']; bpy.context.view_layer.objects.active=arm
bpy.ops.object.mode_set(mode='POSE')
pb=arm.pose.bones['mixamorig:RightArm']; pb.rotation_mode='XYZ'
sc=bpy.context.scene
for f,(rx,ry,rz) in keyframes:
    sc.frame_set(f); pb.rotation_euler=(rad(rx),rad(ry),rad(rz)); pb.keyframe_insert('rotation_euler')
```
缓动:`fc.keyframe_points[i].interpolation='BEZIER'/'EASE'`;或整条 F-curve 加 modifier。**预备/缓动/重叠要主动设**,否则机械。
### IK(做"够取"类:倒茶/挥手弧线)
- 给小臂加 IK 约束指向一个空物体 target,K target 的位置 → 手自然跟随;
- ⚠️ **导出前必须 bake 成 FK 关键帧**(glTF 不存 IK/约束):`bpy.ops.nla.bake(frame_start,frame_end, only_selected=True, visual_keying=True, clear_constraints=True, bake_types={'POSE'})`,再导出。
### 多 clip
- 每个动作 = 一个 **Action**;用 NLA 或导出时 `export_animation_mode='ACTIONS'` 让每个 Action 成一个 glTF animation(Greet/Idle/Talk/Pour…)。
### 原地动画(AR 必须)
- **hips/root 不能有水平位移**(否则 AR 里角色飘离冰箱贴)→ 锁 hips xy,只做上半身。

## 3. Evaluator(怎么验:三层,缺一不可)
### A. 几何层(Blender Python,客观、确定性 scrub,无需眼睛)
对动画逐帧 `scene.frame_set(f)` + depsgraph 更新,读 evaluated mesh 顶点 / 骨 head-tail 世界坐标,算:
- **自交/穿插**:`mathutils.bvhtree.BVHTree.FromObject` + `bvh.overlap(bvh)` → 手插身体、臂穿帽、脚穿地。
- **落地**:每帧 min 顶点 z ≈ 地面(不飘不陷)。
- **根稳定**:hips 世界 xy 漂移 ≈ 0(原地)。
- **到达度**(倒茶):壶嘴空物体 → 杯口空物体 距离随时间,倒茶段应 < 阈值。
- **关节范围**:bone euler 在合理区间(肘不反折)。
- **速度/加加速度突变**:位置二阶差分尖峰 = 机械跳。
- **循环接缝**:frame[0] vs frame[N] 姿势/速度差 ≈ 0(idle/talk 循环不跳)。
→ 一次出客观报告 + pass/fail,不用截图。
### B. 视觉层(渲染 + 眼睛/视觉 agent)
- Blender 渲关键帧(预备/峰值/收势)+ 几个中间帧 → 拼连环图/GIF → 我(或 codex/claude 视觉 agent)对照**动画十二原理 + 古城向导人设 + 概念分镜**打分 → 给调整量 → 改 → 重渲。
- 多角度(正面 + 3/4 侧)看剪影可读性。⚠️ 相机要摆正(实测易摆成侧面)。
### C. 引擎层(真相,最后一关)
- 导出 GLB → three.js/A-Frame `AnimationMixer` 播 → 确认:骨名解析对、不 T-pose/不炸、循环顺、iOS 能播、移动端性能。Blender 里好看 ≠ 引擎里对(导出保真/插值/性能差异)。
**Evaluator = 闭环**:授权 → 几何门禁 → 渲染+打分 → 修 → 重复;最后引擎实测。

## 4. ⚠️ Blender 程序化动画的潜在问题(我设计的东西哪里会坑)
1. **我看不见,只能靠渲染** → 不渲不看 = 盲飞,必须 eval 闭环。
2. **机械感**:程序化 K 帧 ≠ 自然,缓动/预备/重叠/弧线要主动设,否则和 JS 烘焙一样僵。
3. **我不是动画师** → "解剖正确但没灵魂",时机/夸张/性格欠缺;靠视觉 agent + 十二原理补。
4. **IK→FK bake 坑**:导出前必 bake,bake 可能抖/漏帧/采样过密。
5. **自穿插/穿模**(手插身、臂穿帽、脚穿地)肉眼难察 → 几何检测兜。
6. **Q版比例**:大头短肢,标准幅度会错(够不到脸、撞帽)→ 按 Q版调幅。
7. **极限姿势蒙皮崩**:别把姿势推出绑骨"好用区";配合 Stage1 绑骨验证的好用范围。
8. **刚性帽/附属物**:头大幅转/仰 → 帽甩太远、插肩。
9. **脚滑/浮空 + 根漂移**:AR 里角色会飘离贴 → 原地动画、hips 锁 xy。
10. **循环接缝爆**:首末帧不接 → 跳变;循环动作要首末对齐。
11. **导出保真**:采样率/插值(Blender 贝塞尔常被烘成采样点)、Y-up、scale、`mixamorig:` 净化。
12. **无次级运动**:帽穗/衣摆/青狮饰不会动(除非 spring bone/布料模拟)→ 略死;次级可运行时 spring 或预烘。
13. **性能/体积**:关键帧×骨×时长 → GLB 变大,移动端控量。
14. **可复现性**:授权是一串 Python,场景状态会漂 → 从干净态、幂等脚本来。

## 4.5 与 workflow(多 agent)结合
**核心约束**:workflow 的 codex/claude agent 是**文本 agent**——能读文件/跑 shell,但**看不到图**;且**单个 Blender 实例不能并行驱动**(socket 抢占)。所以分工:
- **Workflow** 管:思考/代码/数值分析(设计关键帧方案、预测失败模式、解读几何评估数值、多视角审方法、并行生成参数变体 .py)。
- **我(主循环)** 管:串行驱动 Blender + **看渲染图做视觉判断** + 编排。**视觉判断永远回到我**(或专门视觉步骤),不丢给文本 agent。
- Workflow 在"动手前"(设计/预测)和"产出后"(评数值/审方法)介入;我在中间执行+看图。
**规划的 workflow**:
- **W1 gesture-design**(做动作前):多 critic 设计关键帧方案 + 12 原理清单 + 预测失败模式 → 我照着授权。
- **W2 eval-interpret**(几何评估后):多 critic 解读数值(自交/落地/根漂/接缝)→ 优先级修复表。
- **W3 anim-review**(渲染后,"每步多 questioner"):多视角审(自然度/技术导出/人设/性能),我喂视觉观察 → 弱点+为何+改进。
- **W4 variant-sweep**:并行生成 N 套关键帧参数(只产 .py,不驱动 Blender)→ 我串行跑 Blender+几何评估按指标选优。
- **W5 pipeline-gate**:每个大 step 收口 go/no-go(如 Step1 绑骨评审)。
**每个动作标准闭环**:`W1设计 → 我授权 → 几何evaluator → W2解读 → 我修 → 我渲染 → W3审(喂视觉) → 我导出 → 引擎实测`。

### ⭐ 重要实测:谁能"看图"(2026-06 probe)
- **codex harness worker 能读本地图片并看懂**(实测:给路径 `/tmp/x.png`,它准确描述了连环图内容)→ **真·agent 视觉评审解锁**:渲染连环图 → 把**文件路径**给 codex critic → 它真看图评。不用我转述!
- ~~claude worker 撞 tool_use bug~~ → **已修(升级 Claude Code 后)**:claude worker 现在稳定 + **也能读本地图片做视觉评审**(实测描述比 codex 更细)。→ **codex + claude 都能读图 = 真·双模型视觉 evaluator**;综合步骤也稳了。
- ⚠️ **静帧 montage 判不准"动"**:实测 greet 的手腕挥动,codex 看到"有小摆"、claude 看到"没明显摆"——**因为隔帧采样的静态连环图抓不全周期性摆动**(混叠)。→ 判"挥/摆/循环"这类周期运动要**渲 GIF 看运动**(给用户看动图),静帧只判姿势/穿插。双模型分歧恰好能暴露"这是动作问题还是静帧采样问题"。
- 🎨 **Q版热情吉祥物 动作配方(实战沉淀)**:程序化/IK 默认都偏"礼貌克制",要"活泼可爱热情"必须**大胆夸张**(比"感觉对"再大 1.5-2x):① 挥手=手腕/前臂 **±25-40° 明确摆 2-3 次**(不是抬手停);② **身体上下弹 2-4% 身高**(卡通 bounce);③ **anticipation 先反向蓄力 + 到顶 overshoot 再回稳**(snappy timing:快进-停-快出);④ 头**侧倾 8-12°** + 顺势点;⑤ **次级运动**:帽穗/衣摆/挂饰延迟 1-2 帧跟随;⑥ 收尾别完全垂回,**留半举"等你"姿态**更亲切;⑦ Q版大头**幅度要给足**否则小屏看像没动。大胆做 → 几何 evaluator 兜穿模/离锚。
- **blender MCP 的 `get_viewport_screenshot` 在 workflow worker 里被 "user cancelled"**(权限/审批),且单 Blender 多 agent 并行会抢 → **不要让 critic 自己截图**;由我(主循环)渲染到文件,codex critic 读文件。
- → **修正版分工**:**视觉评审 = codex 读渲染好的连环图/GIF帧montage(文件路径)**;文本/设计评审 = claude + codex;Blender 驱动/截图 = 主循环串行。`multi-critic-review` 的视觉 lens 应走 codex + 传图片路径。

## 4.6 口型 lip-sync(无面部骨模型的实战可行解)
Tripo 模型无 Jaw/blendshape,但若**嘴是"张嘴笑"建模(有口腔内部)**,可**手加一根下巴骨**做振幅级口型(实测可行):
1. Blender 加 `mixamorig:Jaw`(parent=Head)。**⚠️ 支点(head)高度=头号坑**:必须落在**真实颌关节**=嘴缝线/耳侧高度(rel-height≈0.62=移动区上沿那条),**绝不能放脑门顶**(我曾误放 z=0.724=脑门 → 张嘴时整下半脸绕高支点画大弧、向前甩 → 真机看是"**整张脸歪/斜甩**"而非下巴掀开)。tail 朝**前下到下巴尖**;`roll=0`(开合轴≈world-Y、左右对称)。移动 rest 骨不改静止网格,只改旋转支点/轴,可反复调。
2. 权重:取 Head 组里**前脸 + 下部**顶点,**上边界死压到嘴缝线(rel≈0.62)**:嘴线以上清零、`0.60~0.66` 羽化、**别渗进脸颊/法令区**(渗了→张嘴带动整下脸=另一种"脸抖");被削权重转给 Head(守恒、跟头不动)。
3. 绕本地 X 转 ~10-12° 张嘴(Q版大头别超 ~12-14°,否则下巴尖弧长过大显假);因嘴有口腔内部,不穿帮。
- **驱动 = 运行时 Web Audio 振幅**(AnalyserNode 取播放中 narration 的 RMS → 映射到 Jaw 旋转 0~张开)。**别烘 29.5s 口型轨**——运行时驱动更省、对任意配音通用、和循环的 body clip 解耦。
- 这是**振幅级"说话嘴动"**(开合跟音量),不是音素对口型;配字幕足够。导出 GLB 要包含 Jaw 骨(加骨后需重导)。

### ⚠️ 单骨下巴的本质天花板 → 真正的解是 mouthOpen morph(形态键)
**实战教训(真机)**:单根 Jaw 骨旋转,因为嘴是**静态网格(唇不相对张合)**,看到的永远是"**整下半脸往下沉**",不是"嘴在说话"——再调参也到顶。用户一眼就看穿。**真正的解 = blendshape/morph(让唇真的分开)**,业界(VRM A/I/U/E/O、Oculus viseme、ARKit、Rhubarb、met4citizen/TalkingHead three.js)无一例外。
- **最小可行**:Blender 程序化加 1 个 `mouthOpen` 形态键——下唇缘下拉+上唇微抬(smoothstep 羽化),用**同一振幅**驱动 `mesh.morphTargetInfluences[idx]`(three GLTFLoader 读 `morphTargetDictionary['mouthOpen']`);Jaw 骨降为**微动**(~5°)只做下巴辅助。导出 `export_morph=True`;**优化必须 `--simplify false`**(简化会毁形态键),并验 GLB `extras.targetNames` 有 mouthOpen。
- **定位嘴别用高度带**:Q版大眼,眼睛和嘴可能同处一个 rel-height 区 → 我曾把眼睛圈进去压变形。**用"凹陷顶点"找嘴**:中线附近、X 明显小于同高度前表面(=口腔内部)的点,其 rel-height 区间才是真嘴(本模型嘴 rel≈0.50-0.58,眼≈0.60-0.67)。形态键加**硬性高度上界**保护眼睛绝不动。
- **张多大有上限**:Tripo 口腔**内部很浅**(无真牙/舌/喉深度),张大→露出"扁平黑洞"=突兀。AR 小尺度用**克制开口**(实际观看距离看不出浅)即可;要近景特写才需真**雕口腔内部**(舌/牙/喉)= 实打实建模工作量。

### 下巴绑骨几何 evaluator(自动·可机检不变量) — 建下巴骨后**必跑**
确定性 scrub:rest vs 张嘴(取最大角),算每顶点 world 位移,断言:
- **支点高度**:`jaw_pivot_rel` 应≈移动区**上沿**(嘴线,~0.62);若 pivot 远高于上沿 → 支点过高 → 大弧斜甩(我踩过:pivot 0.73 vs 上沿 0.66 → 真机"脸歪")。
- **移动区上沿** ≤ 嘴线(~0.62~0.66);超了=权重渗脸颊。
- **支点以上移动** = 0%(别糊到眼/额/帽)。
- **左右对称**:moved 顶点按 Y(左右)分半,`asym = |meandispL−meandispR|/max(...)` 应 **<5%**(修好后实测 1.5%;歪时这条会爆)。
- **最大位移** 落在**下巴尖**、且 ≤~3%身高(12°);过大=幅度/杠杆过头。
- 教训:**只查"支点以上=0"不够**——支点本身过高、上沿渗脸颊、左右不对称 这三条我都漏过,各自都能让"嘴动"变成"整脸抖/歪"。三层 evaluator(几何不变量 + 双模型读图 workflow + 人真机)缺一漏判。

### 配音↔口型对应 + 完整 evaluator
**做好(1-DOF 下巴)**:① 运行时 Web Audio AnalyserNode 取**正在播放的同一段音频** RMS → Jaw(时序天然零漂移,别烘长口型轨);② 映射曲线 `jaw=smoothstep((rms−floor)/(ceil−floor))×maxOpen` + 噪声地板(静音闭嘴)+ 上限(别尖叫)+ 时间平滑(attack~50ms/release~120ms 防抖);③ **一个 audio 当唯一时钟**——字幕按 currentTime、嘴按实时振幅、body Talk 独立循环,三者挂同一音频→不相对漂移。
**完整 evaluator(口型对应,四层)**:
- ① **客观映射层(自动,无需耳朵)**:离线算 mp3 的 RMS 包络→模拟 jaw(t)→检 (a) 静音段 jaw≈闭 (b) jaw(t)↔rms(t) 互相关高、lag≈0 (c) 动态范围足 (d) 平滑无抖。
- ② **同步架构层**:确认 jaw+字幕+声共用同一 audio 时钟→结构上不漂移。
- ③ **视听层(人,不可替代)**:渲**带声 mp4**(动模型+音轨)→ 人边听边看判"像不像在说这段话"。⚠️ **agent/主循环都没耳朵→口型对应终审只能是人**;agent 做客观映射 + 产带声视频。
- ④ **引擎层**:真机 runtime 振幅→jaw 不卡/不滞后/性能 OK。
- **铁律**:口型对应需"耳朵",只有人能终审;别让 agent 假装判口型同步。

## 5. 踩坑 & 经验(活文档,持续追加)
- `execute_code` 才是跑 Python 的命令(`execute_blender_code` 报 Unknown command)。
- 读标签可用但 `execute_javascript`/页面内容报 "Chrome not running" = Chrome 的 "Allow JavaScript from Apple Events" 没开(这是 Control_Chrome,非 Blender,记此防混淆)。
- Tripo quad 模型的绑骨输出是 FBX 内容(扩展名可能是 .glb),Blender `import_scene.fbx` 前先确认/改 .fbx。
- 渲染相机别靠"猜朝向":模型朝哪轴要先量包围盒/试渲;实测 Tripo 模型常朝 X 轴,从 -Y 渲会得侧面。
- Workbench 引擎渲染快、看形变足够(不追求美);看质感再用 EEVEE。
- ⭐ **Blender 5.x 移除了 `action.fcurves`**(改分层 action / slot+channelbag)。设关键帧插值要走新 API:`for layer in action.layers: for strip in layer.strips: cb=strip.channelbag(action_slot); cb.fcurves` —— 写带 try/except 兜旧版。`keyframe_insert` 本身不变。
- ⭐ **几何 evaluator 实测可用**(bone-世界坐标版):scrub 每帧读 `(arm.matrix_world @ pose_bone.matrix).translation`,算 根漂移/脚z漂移/手到脊柱轴距/二阶差分jerk/首末帧姿势角差(循环接缝);阈值用"占身高%"做尺度无关。脚本见项目 `scripts/`(bl 内联)。导出的 mixamo GLB **身高被归一到 ~1.0**,相对阈值正好用。
- ⚠️ **几何 evaluator 的已知盲区(实测发现)**:① **骨代理≠网格级** —— "手到脊柱轴距"过关 ≠ 手网格没插袍子/帽子/脸,真穿插要 mesh BVH 自交;② 只测了手-脊柱轴,臂穿帽/手穿腿没覆盖;③ **几何全过 ≠ 好看**,自然度/灵魂必须靠视觉层(渲染+12原理),几何只证"物理合理";④ jerk 只测单手、落地只测 z 漂移(恒定悬空不报)。→ 几何是"第一道门",**视觉层不可省**。
- ⭐⭐ **实锤:几何过 ≠ 姿势对,视觉层抓到了几何漏的**(greet v2):把抬臂 euler 加大(RightArm rz=-98+ForeArm rz=-78)后,**手臂折到脸前**(像捂嘴),读起来全错;但几何评估全过(手到脊柱轴 11.6% 仍"OK")——因为手在脸**前方**,骨心到轴距离够,几何检测不到"手挡脸"。→ ① **视觉层绝不可省**;② **几何要补"手 vs 头球/脸前方"检测**(手世界坐标到 Head 的距离 + 是否落在头的前方锥形里);③ **手臂这种"够到某位置"euler 猜轴极脆**(加大幅度方向就跑偏),**应改用 IK**:设手 IK 目标到"头侧上方",Blender 解算,再 bake。
- ✅ **IK 修复验证**:greet v2 的"手折到脸前"用 **IK**(手腕 IK target 设到"头侧上方"+chain_count=2 解算 Arm+ForeArm,挥手用 Hand 骨 FK 叠加,再 `bpy.ops.nla.bake(visual_keying=True, clear_constraints=True, use_current_action=True)` 烘成纯 FK 导出)一次解决 → 开放的举手挥手。**够取类动作 IK >> 猜 euler**,实锤。
- ⚠️ **几何阈值要按动作意图校准**:新增"手-头球最近距离"检测能抓"手挡脸/插头",但**挥手时手本来就在头侧**(实测 19.5%),用 20% 阈值会误报 → **按动作分阈值**:挥手类 ~10-12%(只抓<10%的真贴脸),静态指点/托腮另设。指标对,阈值别一刀切。
- ✅ **eval 闭环跑通一次**(greet 挥手):Blender 程序化稀疏关键帧+贝塞尔 → 几何全过(原地/不飘/不插身/不机械跳/回正)→ 渲染连环图视觉看=可识别干净的挥手,但"偏淡不够热情"(抬臂幅度/挥手摆幅/二次运动偏弱)→ 进双模型 critique 迭代。**结论:B 路线可行**;程序化默认偏保守,要靠视觉层+critique 推向"生动"。
