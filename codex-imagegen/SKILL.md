---
name: codex-imagegen
description: >-
  用 codex 生成/编辑高质量位图(照片、插画、产品图、UI mockup、概念图、贴图、IP 形象、透明抠图)的实战方法论 ——
  codex 自带一个 `image_gen` 内置工具(底层 gpt-image,无需 OPENAI_API_KEY、免联网配置),你用自然语言让 codex
  "生成一张图/改这张图",它会【自动触发】系统 imagegen skill 调用该工具。本 skill 教你怎么把它的质量拉满 + 在
  harness 多 agent workflow 里批量驱动 codex 生图。
  当任务涉及:用 codex/AI 生成图片、出概念图/海报/产品图/封面/hero、给图换背景/改光影/抠透明、做一批资产或变体、
  IP 形象/吉祥物出图、给 [[ai-ip-series-design]] 真正"跑图"、文生图/图生图/图改图、gpt-image/透明背景/4K 出图、
  在 .star workflow 里 fan-out 多个 codex 并行生图 —— 时使用本 skill。出现 codex 生图/image_gen/gpt-image-2/
  gpt-image-1.5/imagegen/抠图/chroma key/批量生图/generate-batch 等关键词也应触发,即使没说"skill"。
  ⚠️ codex 专属:claude/kimi 没有这个内置工具。真要做可绑骨的 3D/AR 见 [[ar-3d-animation-pipeline]]/[[tripo-api]];
  多 agent 编排见 [[author-workflow]]。⚠️ 活文档:新踩的坑/新验证的参数往 §7 追加。
---

# codex-imagegen — 用 codex 生成高质量图片

> ✅ 本机实测(2026-06-20):`codex exec "用你的内置 image_gen 工具生成一张红圆白底图"` 直接出图,
> **无需 OPENAI_API_KEY、无需联网配置**,产物落在 `$CODEX_HOME/generated_images/<uuid>/ig_*.png`(1024×1024 PNG)。
> 所以"告诉 codex 生图"即可 —— codex 会自动触发系统 imagegen skill(`$CODEX_HOME/skills/.system/imagegen/`)。

---

## §1 核心:codex 自带一个生图工具,自动触发

codex 内置 `image_gen` 工具,底层是 OpenAI 的 gpt-image。**你不需要调 API、不需要 key、不需要写脚本** ——
直接用自然语言让 codex "生成/编辑一张图",它就会自动加载 `.system/imagegen` skill 并调用 `image_gen`。

这点对我们很关键:**harness 里的 codex worker(`agent(provider="codex")`)天生会生图**。之前以为"codex 出不了图"是错的 —— 它出得了,而且不用 key。于是 [[ai-ip-series-design]] 这类管线可以被 codex **真正执行**,不只是产出提示词(见 §6)。

---

## §2 两条路:内置工具(默认) vs CLI 兜底

| | **内置 `image_gen`(默认,优先)** | **CLI 兜底 `scripts/image_gen.py`** |
|---|---|---|
| 触发 | 自然语言"生成/编辑图",codex 自动调 | 显式说"用 CLI/API"或要真透明 gpt-image-1.5 时 |
| Key | ❌ 不需要 | ✅ 需要 `OPENAI_API_KEY` + 联网 |
| 存盘 | `$CODEX_HOME/generated_images/<uuid>/ig_*.png`,再自行搬进工作区 | `--out` / `--out-dir` 自己指定 |
| 能力 | 生成 / 编辑 / 多图参考 / 简单透明(chroma-key) | 显式 model/quality/size/mask/批量/真透明 |
| 批量 | 每个资产发一次内置调用(一次一张) | `generate-batch` 读 JSONL 并发跑多 prompt |

**默认走内置**;只有要"显式参数控制 / 真·原生透明 / 大批量并发"才用 CLI(且要 key)。
内置工具不暴露 `quality`/`size`/`mask`/`background` 这些参数 —— 那些是 CLI-only(§5)。

---

## §3 把质量拉满(两条路通用的提示词法)

来源:`$CODEX_HOME/skills/.system/imagegen/references/prompting.md` + `sample-prompts.md`。

### 3.1 结构化 prompt(短标签行,别写一坨)
顺序:**场景/背景 → 主体 → 关键细节 → 约束 → 用途**。复杂需求用带标签的行:
```text
Use case: <taxonomy slug，见 3.3>
Asset type: <这图用在哪，如 landing hero / 游戏精灵 / IP 三视图>
Primary request: <一句话主诉求>
Input images: <Image 1: 角色参考; Image 2: 风格参考>   # 可选,多图按编号点名
Subject: <主体>     Style/medium: <photo / 插画 / 3D / 黏土>
Composition/framing: <wide / close-up / top-down; 留白>
Lighting/mood: <光线+情绪>   Color palette: <配色>
Materials/textures: <表面质感,如 羊毛毡纤维/陶瓷釉面>
Text (verbatim): "<要出现的字,逐字>"
Constraints: <必须保留>      Avoid: <必须避免:no logo/no watermark/no text>
```

### 3.2 关键纪律(决定成败)
- **specificity policy**:prompt 已经很细 → 只规整、别乱加;prompt 很泛 → 才补"有用的"细节(构图/用途/质感),**不要凭空加人/物/品牌/标语**。
- **照片真实感**:直接写 `photorealistic` + 具体真实质感(毛孔/布纹磨损/材料颗粒/日常瑕疵)+ 相机语言(镜头/光位/景别)。
- **图里的字**:把文字放进引号或全大写,指定字体/字号/颜色/位置;生僻词**逐字母拼**并要求"逐字渲染,不许多字";密集文字/信息图在 CLI 里用 `quality high`。
- **多图参考 = 一致性**:按编号点名每张图的角色(`Image 1: 编辑目标 / Image 2: 风格参考`),并说清怎么用(`把 Image 2 的主体放进 Image 1`)。这正是 [[ai-ip-series-design]] 锁角色一致性的底层手段。
- **编辑要复述不变量**:`change only X; keep Y unchanged`,每轮迭代都重申,防漂移。
- **小步迭代**:先干净基准 prompt → 每次只改一处 → 再检查。别一次重写整段。

### 3.3 use-case 词表(分类一致,出图更稳)
生成:`photorealistic-natural / product-mockup / ui-mockup / infographic-diagram / scientific-educational / ads-marketing / productivity-visual / logo-brand / illustration-story / stylized-concept / historical-scene`。
编辑:`text-localization / identity-preserve / precise-object-edit / lighting-weather / background-extraction / style-transfer / compositing / sketch-to-render`。

### 3.4 尺寸 & 画质(gpt-image-2)
- quality:`low`(草稿/缩略/快迭代) / `medium` / `high` / `auto`(终稿/密集文字/身份敏感编辑/高分辨率)。
- 常用尺寸:`1024x1024`(方·最快) `1536x1024`(横) `1024x1536`(竖) `2048x2048`(2K方) `2048x1152`(2K横) `3840x2160`(4K横) `2160x3840`(4K竖) `auto`。
- 约束:最长边 ≤3840、两边都是 16 的倍数、长短比 ≤3:1、总像素 65.5万~829万;>2560×1440 算实验性。方图最快。
- ⚠️ 这些 size/quality 是 **CLI 参数**;内置工具靠 prompt 里描述画幅+用途来近似(它不收 size 参数)。

---

## §4 透明背景 / 抠图

**默认走内置 + chroma-key(免 key)**,别上来就用 CLI 真透明:
1. 内置 `image_gen` 生在**纯平 #00ff00 绿幕**上(主体是绿就用 `#ff00ff`,蓝主体别用蓝):
   ```text
   Create <subject> on a perfectly flat solid #00ff00 chroma-key background for background removal.
   背景必须单一纯色,无阴影/渐变/纹理/反光/地面/光照变化。主体边缘清晰、留白充足。主体内不得出现 #00ff00。
   无投影、无接触阴影、无反射、无水印、无文字(除非要求)。
   ```
2. 本地抠掉绿幕(装好的 helper,不要用项目相对路径):
   ```bash
   python "${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/scripts/remove_chroma_key.py" \
     --input <source> --out <final.png> \
     --auto-key border --soft-matte --transparent-threshold 12 --opaque-threshold 220 --despill
   ```
3. 校验:有 alpha、四角透明、主体覆盖合理、无绿边;残留细绿边再 `--edge-contract 1`;明显锯齿且主体不反光才 `--edge-feather 0.25`。

**真·原生透明**(头发/毛发/玻璃/烟/液体/反光/柔影 这种 chroma-key 搞不定的)才上 CLI、且**先问用户**:
`gpt-image-1.5 --background transparent --output-format png`(`gpt-image-2` 不支持 `background=transparent`)。

---

## §5 CLI 兜底速查(需要 `OPENAI_API_KEY` + 联网)

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export IMAGE_GEN="$CODEX_HOME/skills/.system/imagegen/scripts/image_gen.py"
# 依赖: uv pip install openai pillow ;  --dry-run 不需 key/网,先看 payload
```
三个子命令:`generate` / `edit` / `generate-batch`。**别改 `image_gen.py`、别自己造 runner。**

```bash
# 终稿 2K 横
python "$IMAGE_GEN" generate --prompt "<...>" --quality high --size 2048x1152 --out output/imagegen/hero.png
# 编辑(只改背景),多图按顺序传 --image,prompt 里按编号点名;mask 仅编辑可用
python "$IMAGE_GEN" edit --image in.png --prompt "change only the background; keep subject unchanged" --out output/imagegen/edit.png
# 批量:一行一个 prompt 的 JSONL,并发跑(每个不同资产一行;--n 才是同 prompt 出变体)
python "$IMAGE_GEN" generate-batch --input tmp/imagegen/prompts.jsonl --out-dir output/imagegen/batch --concurrency 5
```

模型表:

| 模型 | 何时用 | 透明 | input_fidelity |
|---|---|---|---|
| **gpt-image-2**(默认) | 新工作首选:高质量生成/编辑、文字多、写实、合成、身份敏感 | ❌不支持 | 恒高,**别设** |
| gpt-image-1.5 | 真·原生透明 / 兼容老流程 | ✅ `--background transparent` | low/high |
| gpt-image-1-mini | 省钱草稿批 / 低风险预览 | — | low/high |

其它:`--n`(1-10 变体) `--out-dir`(改名 image_1.ext…) `--downscale-max-dim`(顺手出 web 缩图) `--force`(覆盖) `--no-augment` `--moderation low` `--max-attempts`。masks 仅编辑、需同尺寸同格式带 alpha、提示词引导非像素级。

---

## §6 ★ 在 harness workflow 里批量驱动 codex 生图(我们的主场景)

因为内置 `image_gen` 跑在 **codex worker 内部**,所以在 [[author-workflow]] 的 `.star` 里:

```python
# 一个 writable codex worker 生图并搬进固定绝对路径
agent(
    "用你的内置 image_gen 工具生成:<结构化 prompt,见 §3>。" +
    "生成后把产物从 $CODEX_HOME/generated_images/ 复制到绝对路径 " + OUT + "/jiexiaoxian_front.png,回报最终路径。",
    provider="codex", writable=True, label="gen-front",
)
```
要点 / 坑:
- **必须 `writable=True`** —— 生图要落盘、要跑 `cp`。read-only worker 不能写。
- **存盘点 `$CODEX_HOME/generated_images/` 是全局路径**,在 worktree 之外 —— 所以**即使 writable worker 的 throwaway worktree 被丢弃,生成的 PNG 也还在**;让 worker 再 `cp` 到你要的绝对输出目录(worktree 内的产物才会被清掉)。
- **批量 = fan-out**:`parallel([...])` 每个 slot 一个角色/一个姿势,N 个 codex 并行出图 —— 这就是把 [[ai-ip-series-design]] 六步**真跑起来**的方式(草图×1 → 拆分 → 逐角色材质/换装/动作 各一个 codex slot)。
- **多图参考**:给 worker 传 `image=[ref1, ref2]`(codex 收 `-i`),prompt 里按编号点名锁一致性。
- 内置工具不收 size/quality 参数 → 要 4K/精确画幅/真透明/大并发,改用 §5 CLI(worker 里 `python "$IMAGE_GEN" …`,需 key)。

---

## §7 踩坑(活文档,持续追加)

- ✅(2026-06-20 实测)内置 `image_gen` **免 key 免联网配置**就能出图;产物在 `$CODEX_HOME/generated_images/<uuid>/ig_*.png`。红圆测试图正常渲染。
- **默认存盘不在工作区**:项目要用的图必须从 `$CODEX_HOME/generated_images/...` **搬进工作区/指定路径**,别让项目引用悬在默认路径。别覆盖已有资产,出 `name-v2.png`。
- **内置"编辑"要先让图进对话**:编辑本地文件得先 `view_image` 把它读进上下文,内置工具不保证任意文件路径编辑;要文件路径/mask 级控制就上 CLI。
- **gpt-image-2 不支持 `background=transparent`**:透明默认走 chroma-key(§4);真透明才 gpt-image-1.5,且先问。
- **别把 CLI 参数当内置参数**:`quality/size/input_fidelity/mask/background/output_format` 都是 CLI-only。
- **`gpt-image-2` 别设 `--input-fidelity`**(恒高);`--input-fidelity` 仅 编辑 且仅支持的模型。
- **批量别用 `--n` 代替多 prompt**:`--n` 是同一 prompt 的变体;不同资产要不同 prompt(内置=多次调用,CLI=`generate-batch` JSONL)。
- **别改 `scripts/image_gen.py`**,缺东西先问用户。

<!-- 新坑往这里加:
- (日期) 现象 / 原因 / 解法
-->

---

## §8 来源与关联
- 系统 skill 原文:`$CODEX_HOME/skills/.system/imagegen/`(`SKILL.md` + `references/{prompting,sample-prompts,cli,image-api,codex-network}.md` + `scripts/{image_gen.py,remove_chroma_key.py}`)。
- 消费方:[[ai-ip-series-design]](IP 系列设计 —— 本 skill 是它的"出图引擎");编排:[[author-workflow]];3D/AR 下游:[[ar-3d-animation-pipeline]]/[[tripo-api]]/[[hunyuan-3d]]。
