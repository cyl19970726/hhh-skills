---
name: ai-ip-series-design
description: >-
  用 AI 做「可控的 IP 系列形象」的完整方法论与实战提示词 —— 把一个吉祥物/IP 角色扩展成一整套
  风格统一、角色一致、可延展(换装/动作/入景/周边)的系列，而不是只出一张惊艳的单图。
  当任务涉及:设计一套 IP/吉祥物/虚拟人系列、做 IP 家族(多角色同风格)、AI 出图"第一张惊艳但成不了系列/
  一致性崩"、角色三视图/转身/表情包/换装/动作设计/把角色融进场景、黏土风/羊毛毡/盲盒手办质感、
  多图参考锁角色一致性、2D 形象转 3D 质感、给 IP 做周边延展、品牌吉祥物落地 —— 时使用本 skill。
  出现 IP设计/IP系列/吉祥物/虚拟人/角色一致性/character consistency/IP family/换装设计/动作设计/
  黏土风/羊毛毡/即梦/Lovart/Nano Banana/Seedream/多图参考 等关键词也应触发，即使用户没说"skill"。
  它管的是【二维形象设计层】:产出一套锁死的一致角色 + 转身/姿势/场景图。要把这些图真正做成可绑骨的
  3D 角色/AR 资产,接 [[ar-3d-animation-pipeline]] / [[tripo-api]] / [[hunyuan-3d]];多版本横向择优用
  [[parallel-concepts-tournament]];给一致性/美感立评审用 [[evaluator-design]]。
  ⚠️ 活文档:每做一个新 IP,把新踩的坑/新验证的提示词追加进 §6、§7。
---

# ai-ip-series-design — 用 AI 做「可控的 IP 系列形象」

> 方法论来源:**拉片小红书 @行野Design《用了AI，就不必追求一键生成（教程附提示词）》**(88s, 2026-06)。
> 完整逐段拉片报告 + 抽帧素材见 `multi-agent-harness/.lapian/6a33e41e/`(本机)。本 skill 是把那条
> 录屏教程的隐性工作流提炼成可复用 SOP + 参数化提示词 + 我们项目的接法。

---

## §1 核心命题:做的是「系列」,不是「单图」

90% 的人用 AI 做 IP **不是不会出图,而是做不成系列** —— 第一张很惊艳,一延展(换姿势/换装/进场景/出周边)就**露相、跑风格、角色变样**。

所以本 skill 的全部重量在一句话:**先锁一致性,再谈惊艳。**

把"做 IP"从"抽一张好图"重构成"**像远古手搓艺术家一样走完整流程**":定家族 → 拆分 → 材质 → 换装 → 动作 → 入景。AI 只是把每步的"手搓"加速了,流程本身不能省。**谁掌握流程 + 一致性技术,谁有壁垒;单图 prompt 不值钱。**

### 反模式(一眼判废)
- ❌ 一个角色一个角色单独生,生完发现彼此**不像一家人**(画风/线条/比例/质感各跑各的)。
- ❌ 家族 4 个角色**高矮胖瘦雷同**(都差不多大),没有对比 → 没有节奏感 → 没有记忆点。
- ❌ 换装/换动作时**重新生成整角色** → 脸崩、配色漂移、像换了个 IP。
- ❌ 追求"一键生成全套" → 越想一步到位越不可控。

---

## §2 六步管线(照着走,别跳)

| 步 | 名 | 干什么 | 产出 | 一致性靠 |
|---|---|---|---|---|
| 0 | **定调** | 选插画风参考当垫图 + 列物种清单 | 1 张风格基准图 + 角色清单 | 风格图 = 全程"图2" |
| 1 | **草图(定家族)** | 一次性出**全家 N 角色组合图**,刻意拉开高矮胖瘦 | 1 张全家草图(❌雷同/✅差异 对照) | 同一次生成 → 天然同风格 |
| 2 | **提取拆分** | 转扁平矢量插画风、提亮、去服装,逐角色抠成白底卡 | N 张单角色干净底图(可独立加工) | 从同一张草图切出 |
| 3 | **材质渲染(2D→3D)** | 备 2~3 张目标质感参考,逐角色做风格迁移立体化 | N 张带质感的"伪 3D"角色 | 图1=角色 / 图2=质感参考 |
| 4 | **换装** | 把灵感站(花瓣/Pinterest)当衣帽间,逐角色垫图换装 | 每角色 ×M 套穿搭 | "参考身形**重设计**,不照搬" |
| 5 | **动作** | 用"大透视 / JOJO 立"prompt 打破呆板,多机位 | 每角色 ×K 个动态姿势 | "保持角色一致 + 出 2 方案" |
| 6 | **入景** | 多图参考把角色融进统一场景,最后来张全家福 | 场景成片 + 全家福合影 | 图1角色严格不变 / 图2=场景氛围 |

> 顺序的道理:**先把"全家"在一张图里定死(第1步)**,再拆开各自精修。颠倒过来(先精修单个再凑一家)必然不一致。

### 各步要点

**0 定调** —— 找一张你真心喜欢的插画/质感参考(黏土、羊毛毡、盲盒手办、扁平矢量…),它从头到尾当"图2 风格参考"。同时把角色物种/数量定下来(如:鹳·熊·蛙·萌芽·桃,一高一矮一胖一小)。

**1 草图(最关键)** —— 用**提示词① 一次出全家组合图**。诀窍是在 prompt 里**明令拉开头身比(3~9 头身混搭)、有高有矮有大有小、造型偏几何组合、避免杂碎细节**。先有意生一版"雷同的"当 ❌ 反例,再生"差异化的"当 ✅,这组对照本身就是好内容素材(也是教程钩子)。

**2 提取拆分** —— 把草图**转扁平矢量插画风 + 提亮 + 去掉服装**(裸模更好后续换装),再**逐一把每个角色单独抠出来**放白底。理由:后面换装/材质/动作都要**逐角色独立加工**,不能一锅烩。

**3 材质渲染** —— 这步是"2D 平面 → 立体质感"。准备 2~3 张目标材质参考图,**图1 喂角色、图2 喂质感**,做风格迁移(黏土风/硅胶/羊毛毡都可试)。注意:这产出的是**带 3D 质感的平面图(伪 3D)**,不是真三维模型 —— 要真模型见 §8。

**4 换装** —— **把灵感网站当衣帽间**:在花瓣/Pinterest 截一版穿搭灵感板当垫图,逐角色生穿搭。prompt 必须强调"**参考角色身形重新设计服装,而不是照搬模特**",否则会把真人衣服硬糊上去。

**5 动作** —— "呆呆的站姿拯救不了吸引力"。用**提示词②**出大透视 / JOJO 立 / 夸张前缩(伸向镜头的部位特写放大)、多机位(仰拍/俯拍/虫眼/45°侧身)。一次出 2 个方案挑。

**6 入景** —— 用**提示词③**把角色"种"进场景:**严格锁住图1角色的大小/位置/一致性不变,只在留白处加背景**,场景氛围/配色参考图2,强景深+虚焦前景。收尾出一张**全家福合影**作为系列的"集体照"。

---

## §3 三个实战提示词模板(直接抄,带占位符)

> 占位符用 `{…}` 标出,替换即用。这三条是从拉片里逐字还原 + 参数化的,**已在原视频成片验证**。

### 模板① 草图 · 一次定全家族
```
根据参考图风格,生成一组完全不同的 IP 角色组合图,共 {N=4} 个角色,物种/职业各异:{鹳/熊/蛙/萌芽…}。
要求:每个角色的头身比都不一样,可以有夸张、不协调的身材比例(3~9 头身混搭);有高有矮、有大有小;
角色造型偏几何图形的组合;避免出现杂碎细节,画面柔和、让角色更干净立体。
风格:{你喜欢的插画风,如"温暖手绘绘本风"}。宽高比 1:1。
```
要点:**"头身比都不一样 + 有高有矮有大有小"是拉开节奏感的命门**;"几何组合 + 避免杂碎细节"保证可被后续 3D 化。

### 模板② 动作 · 大透视 / JOJO 立(打破呆板)
```
{附:该角色的定稿图作为图1}
保持角色一致性,保持背景色。让角色做不同的 JOJO 立浮夸动作;如果某个部位伸向镜头,请使用大透视并特写该部位。
拍摄角色的不同角度:侧身、45° 侧身、背对镜头等;用低角度仰拍、高角度俯拍、虫眼视角、大透视等非常规角度;
角色可看向镜头或不看。出 2 个方案。保持角色服装不变,真实的服装细节质感。1:1 画幅,2K。
```
要点:**"保持角色一致性 + 服装不变 + 出 2 方案"是防漂移三件套**;动态全靠"大透视/JOJO 立/非常规机位"这几个词。

### 模板③ 入景 · 多图锁一致性合成
```
{图1 = 角色定稿;图2 = 场景/氛围参考}
严格保持图1角色在画面中的大小和位置不变(完全不能改变角色在画幅中的大小,只能在留白区域添加背景与元素)。
给图1加入场景以及渲染打光。场景元素与氛围参考图2;场景配色根据图1角色来搭配({莫兰迪配色},突出图1角色为主角)。
不要出现明显的地面;场景元素需匹配图1角色的拍摄角度;画面具有强烈的景深效果,可适当加入虚焦的前景。
严格保持图1的角色一致性,保持服装不变,真实的服装细节质感。不出现文字与 logo。{3:4} 画幅,2K。
```
要点:**"严格保持图1大小位置不变 + 只在留白加元素"** 是把角色精确"种"进场景、不被场景吞掉的关键约束。

---

## §4 一致性的命门:多图参考锁定法

这套流程能成系列,底层就一招 —— **双图分工**:

- **图1 = 主体(不许动)**:要保持身份的那个角色。prompt 里反复写"**严格保持图1角色一致性 / 大小位置不变 / 服装不变**"。
- **图2 = 风格/场景参考(只借不抄)**:质感、配色、氛围从这儿来。prompt 写"**参考图2的{质感/氛围/配色}**"。

配套口令(哪条缺了就会崩):
- 锁身份:`严格保持图N角色一致性`
- 锁构图:`保持角色在画幅中的大小/位置不变,只在留白区域添加元素`
- 锁服装:`保持服装不变,真实服装细节质感`
- 借风格:`{质感/配色/氛围}参考图M` / `参考身形重新设计,而不是照搬`
- 控规格:把 `画幅(1:1 / 3:4)` 和 `2K` 直接写进 prompt 尾巴

> 这是 2025–2026 多图参考生图模型(Nano Banana / 即梦 Seedream 一类)的标准玩法:**模型本身能维持一致性,但你必须用文字把"哪张不许变、哪张只借风格"说死。**

---

## §5 工具链(带置信度 + 替代 + 怎么自证)

> ✅事实 ｜ ⚠️推断 ｜ ❓不知道

- ⚠️ **生图主力 = AI 设计 Agent 的「暗色网格无限画布 + 对话生图」**。原视频 UI 指纹:黑色细网格画布、生成图以卡片浮在画布、提示词是**聊天气泡**且可挂**自动命名的参考图 chip**(`🐱 image`、`🦢 图1`、`🌸 felt_flower…`)、画幅/2K 写进 prompt。**最像 Lovart(设计 Agent,标志性暗色网格画布)**,其次**即梦(Jimeng/Dreamina)的对话画布 / Liblib 星流**。无标题栏露出,锁不死具体产品。
- ⚠️ **底层模型 = 强"多图一致性"的对话生图模型**(Nano Banana / Gemini image、即梦 Seedream 一类)。证据:全程"图1不变 + 图2风格参考"。❓ 具体模型不可考。
- ✅ **灵感/换装素材源 = 花瓣 / Pinterest**(原视频换装步是 Pinterest 风瀑布流灵感板,且画面自标"来源花瓣")。

**选型建议(我们落地用)**:
- 要**画布 + 多图参考 + 中文 prompt 友好** → 先试 **即梦(对话画布)**(国内、免费额度、Seedream 一致性强)或 **Lovart**(设计 agent、画布体验最接近原视频)。
- 只要**纯多图一致性出图** → **Nano Banana / 即梦 Seedream** 任一支持多图参考的对话生图都行,UI 无所谓。
- **怎么把 ⚠️ 变 ✅**:去 @行野Design 主页翻其他帖/评论区找其工具自述,或看是否有标题栏露出;确认后回来更新本节。

### §5.1 实证更新(codex 核验 · 2026-06-20)

- ⚠️纠错｜工具身份不要再写成“最像 Lovart”单一判断；本轮核验后的可插入排序是：1）即梦/Dreamina 对话画布/无限画布，2）Lovart，3）Liblib 星流/Canvas（未核到本轮硬截图），4）Whisk，5）奇域。理由：即梦官网已坐实“智能画布 多图AI融合”、同画布多元素拼接、局部重绘、扩图、消除、抠图；第三方教程还出现“点击图片，添加到对话，重新生成”和 Agent 产物自动汇集到画板、图片/视频/文本/画板可拖拽排布。Lovart 官网坐实 AI Design Agent、New Chat、Touch Edit、Style Consistency；Tom’s Guide 坐实 text box + infinite canvas，但未核到“添加到对话”这种中文对话画布指纹。源：https://jimeng.jianying.com/ ; https://www.szxn.com/55105.html ; https://www.lovart.ai/ ; https://www.tomsguide.com/ai/with-one-prompt-i-built-an-entire-brand-kit-in-an-hour-using-lovart
- ❓不知道｜仍未核到 @行野Design 在公开帖子/简介/评论中自述具体工具或模型；原视频无标题栏/浏览器 tab 露出，所以只能写“UI 指纹更像即梦对话画布或 Lovart”，不能写“作者使用了某工具”。源：https://www.xiaohongshu.com/explore/6a33e41e000000001702f475
- ✅事实｜静态 IP 系列一致性模型建议更新：不应只写 Nano Banana/Gemini 2.5 Flash Image。Google 当前图像文档列出 Gemini 3 Pro Image/Nano Banana Pro 面向 professional asset production，支持最多 14 张参考图，其中最多 5 张角色参考、3 张风格参考；Gemini 2.5 Flash Image 官方建议“最多 3 张输入图效果最好”。落地：多角色、多风格参考、品牌物料同场时，优先试 Gemini 3 Pro Image。源：https://ai.google.dev/gemini-api/docs/image-generation
- ✅事实｜Seedream 4.0 的新增定位不是“神秘更稳”，而是“批量输入/输出 + reference consistency + 4K + 快速迭代”：ByteDance 官方页写明 reference consistency、Batch Input & Output、最高 4K；技术报告摘要写明支持 multi-image reference 和 multiple output images。源：https://seed.bytedance.com/seedream4_0 ; https://arxiv.org/abs/2509.20427
- ✅事实｜GPT Image 当前官方图像文档以 `gpt-image-2` 为主；它支持多轮生成、多张 reference image、mask 编辑，且 `gpt-image-2` 的输入图默认高保真处理。定位建议：它更适合 IP 定稿后的局部修脸、修 logo、补服装细节、mask 修复，不应写成“系列一致性首选生成器”。源：https://platform.openai.com/docs/guides/image-generation

### §5.2 我们自己的出图引擎:codex 内置 image_gen(✅本机实测 2026-06-20)

- ✅事实｜**codex 自带 `image_gen` 工具,免 `OPENAI_API_KEY`、免联网配置**,自然语言"生成/编辑一张图"即自动触发(底层 gpt-image)。本机已实测出图正常(红圆白底 1024×1024 PNG,落 `$CODEX_HOME/generated_images/`)。完整用法见 **[[codex-imagegen]]**。
- 含义:本管线的"出图"这一步**不必依赖外部画布工具(即梦/Lovart)**,可以直接用 codex 跑 —— 尤其适合**我们在 harness 里 fan-out 多 codex 并行批量出图**(见 §7)。即梦/Lovart 仍是"人手在画布上精修"的好选择;codex image_gen 是"可编程、可批量、可复现"的工程化选择。
- ⚠️ 取舍:codex 内置工具不收 size/quality/真透明参数(那些是 CLI-only,需 key);要 4K/精确画幅/原生透明/大并发,走 [[codex-imagegen]] §5 的 CLI(`gpt-image-2`/`1.5`)。多图参考锁一致性(§4)在 codex 里靠给 worker 传 `image=[...]` + prompt 按编号点名。

---

## §6 关键判断 / 踩坑(活文档,持续追加)

- **先定全家再拆分**:第 1 步就把 N 个角色生在同一张图里 —— 同一次生成天然同风格,这是一致性最便宜的来源。颠倒(先精修单个)必崩。
- **拉开体型 = 系列的灵魂**:头身比/高矮胖瘦不拉开,4 个角色像 4 个克隆,没记忆点。prompt 里把"有高有矮有大有小、头身比都不一样"写死。
- **去服装再换装**:第 2 步先脱成"裸模",换装才干净;不脱直接糊衣服会叠层穿帮。
- **换装别照搬**:必须写"参考身形**重新设计**",否则把真人模特的衣服硬贴上去,比例全错。
- **入景别让场景吃掉角色**:不加"严格保持图1大小位置不变 + 只在留白加元素",角色会被场景重绘/缩放/挪位。
- **材质渲染只是"伪 3D"**:第 3 步产出的是带立体质感的**平面图**,不是可绑骨的三维模型 —— 别拿它当 3D 资产,要真模型见 §8。
- **机器字幕会写错别字**(原视频:"手搓→手拖""矢量→史料""垫图→电图"),别被带偏术语。
- ✅事实｜多参考图超过 2 张时必须显式分槽，不要只写“图1主体/图2风格”。可直接加口令：`Refs A-C are identity refs; preserve face, body ratio, outfit silhouette. Refs D-E are pose refs only; do not copy identity. Refs F-G are style refs only; do not import their characters.` 依据是 Gemini 3 图像模型官方把 object / character / style reference 分开计数。源：https://ai.google.dev/gemini-api/docs/image-generation
- ⚠️推断｜给角色建“身份胶囊”，比只喊“保持一致”更可控。可插入口令：`角色代号=JXX-01；不可变特征：头冠轮廓/脸型/眼距/主色/标志物/材质/比例/鞋帽；可变项：姿势/表情/场景/光线。` 依据：Google 建议关键细节要具体描述，Seedream 4.0 技术报告强调 multi-image reference/一致性任务；“身份胶囊”是生产写法，不是官方参数。源：https://ai.google.dev/gemini-api/docs/image-generation ; https://arxiv.org/abs/2509.20427
- ✅事实｜做转身/三视图不要只赌一次“三视图大图”。Google 官方建议 360 视图用迭代法：生成新角度时带上前面已批准图，复杂姿势另加 pose reference。可插入口令：`same character, orthographic studio turnaround, front / 3-4 / profile / back, identical outfit, identical proportions, white background`。源：https://ai.google.dev/gemini-api/docs/image-generation
- ⚠️推断｜长系列不要“上一张改下一张”一路滚；建议从“角色母版图 + 身份胶囊 + 当次姿势/场景参考”分叉生成。依据：Banana100 论文显示 Nano Banana Pro 的 100 次迭代编辑会累积噪声并降低指令跟随；这能支持“少走长编辑链”的工作流约束，但不能证明所有模型、所有短链都会崩。源：https://arxiv.org/abs/2604.03400
- ✅事实｜Seedream API 的 `seed` 只应写成“随机性/回归测试控件”，不能写成跨 prompt、跨场景的角色一致性保证。fal 文档写明 `seed` controls stochasticity，`max_images` 可多图生成，且输入+输出总数不超过 15；未承诺换动作/换场景后身份必然不漂。源：https://fal.ai/models/fal-ai/bytedance/seedream/v4/edit/api
- ✅事实｜GPT Image 的 mask 不是像素级选区保证。官方写明 mask 是 prompt-based guidance，模型可能不会完全按 mask 形状精确执行；IP 定稿后局部修补必须留人工复核。源：https://platform.openai.com/docs/guides/image-generation
- ❓不知道｜未在 Google/OpenAI/Seedream/fal 已核文档中看到通用数值型 `reference_weight` / `character_weight` 参数；不要把“参考权重 0.8”写成这些闭源对话生图模型的通用参数。源：https://ai.google.dev/gemini-api/docs/image-generation ; https://platform.openai.com/docs/guides/image-generation ; https://fal.ai/models/fal-ai/bytedance/seedream/v4/edit/api

<!-- 新坑往这里加:
- (日期) 现象 / 原因 / 解法
-->

---

## §7 接到我们的 3D / AR 管线(本 skill 的位置)

本 skill 只做**二维形象设计层**:产出一套**锁死一致的角色 + 转身/姿势/场景图**。要把它变成真能动、能扫的资产,往下接:

```
[本 skill] 定一致角色 + 转身/姿势图
   │  (拿干净单角色图 + 多视角)
   ▼
[[tripo-api]] / [[hunyuan-3d]]  图生 3D + 自动绑骨   ← 用第2步抠好的干净底图 + 第5步多机位图喂多视图重建
   ▼
[[blender-mcp]] 动作重定向 / IK / 导 glTF
   ▼
[[ar-3d-animation-pipeline]] 减面→r3f→MindAR→真机   /   [[scenic-spot-ar]] 景点 AR 落地
```

衔接要点:
- 第 2 步的**白底干净单角色图**正好是图生 3D 的理想输入(背景干净、角色完整)。
- 第 5 步的**多机位/转身图**可喂 Tripo `multiview_to_model` 做更准的多视图重建。
- 选型/择优(多版角色横向比、选 1 可杂交)走 [[parallel-concepts-tournament]];给"像不像一家人/美不美"立评审走 [[evaluator-design]]。
- 一开始想并行孵化多个 IP 创意方向,发散用 [[exploration-judgment]] 的判断力别过早收敛。

### §7.1 把六步「跑起来」:codex 出图引擎 + workflow fan-out

本 skill 不止是"写提示词",它可以被 **codex 真正执行**(见 §5.2 / [[codex-imagegen]]):codex 内置 `image_gen` 能出图,所以在 [[author-workflow]] 的 `.star` 里:

- **草图(第1步)** = 1 个 codex slot 出全家组合图;**拆分/材质/换装/动作(第2–5步)** = `parallel([...])` 每角色一个 `writable=True` codex slot 并行出图;**入景(第6步)** = 给 worker 传 `image=[角色定稿, 场景参考]` 锁一致性。
- **存盘坑**:codex 写到全局 `$CODEX_HOME/generated_images/`(在 worktree 外,**worktree 丢弃也不丢图**);让每个 worker 再 `cp` 到固定绝对输出目录。
- 这样一条 `.star` 就能把"定家族→逐角色延展→入景→全家福"批量产出,run 落 dashboard、可复现 —— 即梦/Lovart 画布则留给"最后人手精修"。落地配方见 [[codex-imagegen]] §6。

---

## §8 用在揭小贤(我们的 worked example)

揭小贤角色 bible(见项目记忆 [[jiexiaoxian-fold-card-design]]):**头冠庙顶 + 金匾「揭小贤」+ 集章册 + 潮汕红袍**,已选定 **m1/v1 美术方向**,产出在 `ai-luodi/jieyanggucheng-materials/`。

把六步套到揭小贤:
1. **定调**:风格走**温暖羊毛毡 / 黏土手作感**(呼应揭阳古城非遗温度);图2 风格参考用现有 m1/v1 定稿。
2. **草图(定家族)**:用模板① 一次定**揭小贤 + 潮汕系列伙伴**(如:英歌槌少年、潮剧花旦、工夫茶童…),刻意拉开高矮胖瘦,锁"庙顶头冠 + 红袍"作为家族统一记号。
3. **提取**:逐角色抠白底,保留头冠/金匾这些**身份锚点**别丢。
4. **材质**:羊毛毡质感迁移 → 做成"能当冰箱贴/盲盒"的立体感(下游真 3D 走 [[tripo-api]])。
5. **动作**:用模板② 出揭小贤的招牌动作(作揖、举集章册、提灯),为 AR 临现动作打底(接 [[beat-performance-pipeline]])。
6. **入景**:用模板③ 把揭小贤种进**进贤门/古城**场景,出一张潮汕系列全家福 —— 既是周边主视觉,又是涨粉内容。

> 顺带产内容:这套"AI 把非遗 IP 做成一整套形象"的过程本身就是一条**同结构爆款短视频**(痛点钩子 + 6步流程 + 提示词糊脸 + 价值观收尾)。一鱼两吃:作品 + 教程涨粉。拍法直接抄原视频结构(见 `.lapian/6a33e41e/拉片报告.md`)。

### §8.1 2D→3D 喂图规范(codex 核验)

- ✅事实｜Tripo `multiview_to_model` 不是泛泛“正/侧/背三视图”，而是 `files` 必须正好 4 个槽位，顺序固定为 `[front, left, back, right]`；front 不能省，且不要少于 2 张图。揭小贤标准包：`jxx_front.png`、`jxx_left.png`、`jxx_back.png`、`jxx_right.png`。源：https://docs.tripo3d.ai/model-generation/multiview-to-model-v3-0-v3-1.html
- ✅事实｜Tripo 单张角色图走 `image_to_model`；已有四方向视图走 `multiview_to_model`。不要把四视图拼成一张四宫格再丢进单图入口；四宫格给人看，API 要独立文件/槽位。源：https://docs.tripo3d.ai/model-generation/image-to-model-v3-0-v3-1.html ; https://docs.tripo3d.ai/model-generation/multiview-to-model-v3-0-v3-1.html
- ✅事实｜Tripo 图像输入直链支持 JPEG/PNG，最大 20MB；官方更推荐上传后传 `object/resource_uri`。落地：从本 skill 导出的喂图统一 PNG/JPEG、小于 20MB，不用 PSD/WEBP/带图层文件直接喂。源：https://docs.tripo3d.ai/model-generation/image-to-model-v3-0-v3-1.html
- ✅事实｜Hunyuan3D 官方 Gradio 的 Image Prompt 使用 RGBA，默认有 Remove Background；多视图 UI 暴露 Front/Back/Left/Right 四个输入位。落地：白底不是唯一可行，透明底 PNG 也符合管线；但不要喂场景图、投影地面、花丛背景，否则先被抠图/误抠。源：https://raw.githubusercontent.com/Tencent-Hunyuan/Hunyuan3D-2/main/gradio_app.py
- ✅事实｜Hunyuan3D-2mv 是 Multiview Image to Shape Model。给混元也按正/背/左/右拆独立文件上传，不要只给一张四宫格转身表。源：https://hunyuan3d-2.readthedocs.io/en/latest/modelzoo.html
- ✅事实｜Tripo `texture_alignment` 可在 `original_image` 和 `geometry` 间取舍：前者更像原图但可能有 3D 不一致，后者更重结构准确但可能偏离原图。验收建议跑两轮：先用 `original_image` 查“像不像揭小贤”，再用 `geometry` 查“能不能动/结构顺不顺”。源：https://docs.tripo3d.ai/model-generation/image-to-model-v3-0-v3-1.html
- ✅事实｜Tripo `smart_low_poly` 对低复杂度输入效果最好，复杂模型存在失败可能。揭小贤喂图负面约束写死：`no tiny accessories, no dense embroidery, no hair strands, no fuzzy edge, no transparent lace, no thin dangling tassels`；AR/自动绑骨优先大块几何、清晰轮廓、可分离四肢。源：https://docs.tripo3d.ai/model-generation/image-to-model-v3-0-v3-1.html
- ✅事实｜Tripo 自动绑骨前先跑 `animate_prerigcheck`，看 `riggable` 和 `rig_type`；支持 biped/quadruped/hexapod/octopod/avian/serpentine/aquatic。揭小贤人形默认按 `biped`，鸟类伙伴按 `avian`，四足伙伴按 `quadruped`；不是 riggable 就回到 2D 减复杂/补四视图，不要直接进动画。源：https://docs.tripo3d.ai/animation/pre-rig-check-v2-0-20250506.html ; https://docs.tripo3d.ai/animation/rig-v2-5-20260210.html
- ⚠️推断｜揭小贤 Q 版可以大头短身，但不能“圆到没有关节”。肩、肘、腕、胯、膝、踝至少在轮廓上可分辨；手臂和身体之间、双腿之间留白；庙顶头冠、金匾、集章册不要和身体粘连。依据是 Tripo 预绑骨按 rig_type 判断可绑性、复杂输入低模可能失败；具体阈值需项目实测。源：https://docs.tripo3d.ai/animation/pre-rig-check-v2-0-20250506.html ; https://docs.tripo3d.ai/model-generation/image-to-model-v3-0-v3-1.html
- ⚠️推断｜揭小贤 2D 喂图验收表：主体完整不裁切；白底或透明底；正视图站立中性姿势；左右基本对称；四视图同画幅/同高度/同焦距；无阴影地面/背景物；四肢与躯干分离；配饰不穿插身体；没有文字/logo；每张只放一个角色。除 Tripo 槽位、格式、复杂度和 Hunyuan 去背景机制外，其余是把官方约束翻译成生产规范。源：https://docs.tripo3d.ai/model-generation/multiview-to-model-v3-0-v3-1.html ; https://raw.githubusercontent.com/Tencent-Hunyuan/Hunyuan3D-2/main/gradio_app.py

---

## §9 来源与产出
- 拉片源:小红书 note `6a33e41e000000001702f475` · @行野Design · 88s。
- 本机产出:`multi-agent-harness/.lapian/6a33e41e/`(`拉片报告.md` + `aligned.md` + 抽帧)。
- 配套 skill:视频拉片法 [[video-understand]];3D 化 [[ar-3d-animation-pipeline]]/[[tripo-api]]/[[hunyuan-3d]];择优 [[parallel-concepts-tournament]];评审 [[evaluator-design]]。
