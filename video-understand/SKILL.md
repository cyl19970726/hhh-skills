---
name: video-understand
description: 拉片——把一条对标视频拆成可复刻 SOP。管线:下载→whisper逐字稿→抽帧(粗览+按需密抽)→判型→逐段填表→产出①逐段拉片报告(它怎么做的,工具链带置信度)+②复现SOP(你怎么抄)。用于"学习/复刻优秀博主的爆款视频"。触发词:"拉片"、"拉这条视频"、"拆解爆款视频"、"复刻对标博主"、"理解这条视频"、"这个视频在讲什么"、"学习博主视频"、"video understand"、"看懂小红书视频"。
metadata:
  deps: ffmpeg, whisper(openai-whisper); note 模式复用同仓库 xhs-crawler
---

# video-understand — 小红书视频理解管线

crawler 只能拿到视频的**直链 + 元数据**,给不了"理解"。真正读懂一条视频要走**多模态管线**,
而且分工明确:**口播交给 whisper,画面交给视觉模型(就是你/agent 直接 Read 关键帧)**,两条模态合起来才叫理解。

## 何时用
- 想"学习某个博主的爆款视频/同类视频"的钩子、选题、视觉、工作流、卖点
- 拿到一个小红书 note_id / 视频直链 / 本地 mp4,要产出一份结构化《视频拆解》
- 给我们(揭小贤文创)做**创意参考**(视觉/工作流)+ **内容分析**(该做什么/对标谁)

## 核心:拉片 = 拉两样东西

"拉片"= 把一条对标视频拆成**可复刻的 SOP**。它拉的是两层:
- **拉内容**(讲了什么):选题 / 开头钩子 / 段落结构 / 每句话时间轴 / punchline —— *看一遍就能复刻个大概,不难。*
- **拉技术**(怎么做出来的):怎么拍 / 什么图形动效 / 怎么剪 / 什么节奏 / 用了什么 AI 工具 —— *盯着成片一百遍也看不出来,这才值钱。本 skill 主攻这层。*

## 标准拉片六步

`STEP1 定维度 → STEP2 拆素材(脚本) → STEP3 判型 → STEP4 两遍细看(粗览→密抽) → STEP5 逐段填表 → STEP6 双报告+复现SOP`

### STEP1 定维度
先定这次要拉哪些维度,勾什么出什么:**台词 / 节奏卡点 / 特效动效 / 版式镜头 / 字体 / 调色 / 配乐 / 工具链**。默认全勾;只关心某几个就只拉那几个(省 token、更聚焦)。

### STEP2 拆素材(确定性脚本)
```bash
# 三选一来源;note 模式自动取直链下载(需 RNOTE_API_KEY)
python3 prep_video.py --note 6a0b295c00000000350296a1
python3 prep_video.py --url  http://...rednotecdn.com/...mp4
python3 prep_video.py --file ./clip.mp4
# 可选: --model medium(更准) --frames 12 --scene 0.25 --out-dir DIR
```
产出 `clip.mp4 / audio.txt / audio.json(带时间戳) / kf-*.jpg(粗帧) / aligned.md(★音画对齐) / manifest.json`。
**音画对齐**:帧时间戳(ffmpeg)+ 口播分段时间(whisper json)融合进 `aligned.md`——每帧标"该时刻在说什么"。

### STEP3 判型(★判错后面全白拆)
先判这是哪类片,选对应"眼光"——三类三套拆法:
| 类型 | 长什么样 | 重点看什么 |
|---|---|---|
| **口播/教程** | 录屏 ± 露脸、讲操作 | 工具链 / 操作步骤 / 屏幕信息 → 配合下面【枚举软件模式】抓工具指纹 |
| **叙事/剧情/vlog** | 实景、有情节 | 镜头/运镜/转场/配乐/情绪曲线 → 重画面与节奏,whisper 次要 |
| **混剪/图文卡点** | 快切、卡点、大字版式 | 卡点节奏 / 字体版式 / 转场样式 |

### STEP4 两遍细看(自适应抽帧)★ 本 skill 最值钱的一步
均匀稀疏抽帧会**漏关键段**(实测漏过绑骨段、视频里展示的 blog 段)且贵。改两遍:
1. **粗览**:读 `aligned.md` + 粗帧(`kf-*.jpg`,约每 9s),标出**有戏/看不懂的时间段**(动效在变、版式在切、出现新软件 UI、信息密集处)。
2. **密抽**:只对这些段密集抽帧再看懂:
   ```bash
   python3 prep_video.py --file clip.mp4 --out-dir <与粗览同目录> --densify "65-80,120-135" --densify-fps 5
   ```
   → `dense.md`(密帧 `d-*.jpg` ↔ 时间 ↔ 口播,复用同目录 whisper 分段)。还看不懂就调高 `--densify-fps` 或缩窄区间。

### STEP5 逐段填表
按段对齐成表,每段一行:`时间码 | 画面(代表帧) | 台词 | 图形/特效 | 节奏 | 作用`。

### STEP6 双报告 + 复现 SOP(两份产出)

**产出① 逐段拉片报告(它怎么做的)**
- 封面:标题 / 时长·段数·切点 / 一句话定性
- 一句话结论:这片到底怎么做的,说死
- **可复刻度评分**(分维度 0–10):拍摄 / 图形层 / 节奏 / 工具链
- 关键发现 ×3–5(如:0 切点、1.5s 一句、语义卡点)
- 配帧逐段表(STEP5)
- 图形层部件清单 + **工具链推断,每项带置信度**:✅**事实**(画面水印/UI 铁证)| ⚠️**推断**(像但无铁证)| ❓**不知道**。三者划清,别糊成一团。

**产出② 复现 SOP(你怎么抄)**
- 适用场景 + 工具栈(每环节给推断)
- 流水线分段(按型不同,如口播型:`逐字稿 → 实拍 → 图形层 → 剪辑 → 收尾`)
- 每段写清:素材怎么备 / 怎么拍 / 图形怎么做 / 节奏怎么卡
- 可抄要点 ×5(开场 N 秒钩子 / 结构套路 / 降门槛 …)
- **对揭小贤项目**:① 创意参考(视觉/3D工作流)② 内容分析(选题/对标)③ 直接复刻成自己的视频

> 方法论来源:对标博主 **yan的ai世界《用 Claude Code 拉片》**(2026-06)。成本参考:30min 视频全量拉片 ≈ $25(Opus 主力 + Haiku 跑杂活),普通视频约 40 万 token;拆一个博主 3–5 条即可摸清其工作流。

## 枚举视频用到的「所有软件」(工具清单模式) ★

**这是一个独立模式,不要用上面的稀疏关键帧来做。** 实测教训:要列全一条教程视频用到的所有软件
(如"混元3D网页 + 桌面DCC + ..."),稀疏场景帧(十来张、还缩到640宽)**必漏**——因为软件常出现在
静态/过渡帧,而判定软件靠的是**窗口标题栏/菜单栏**这种**小字**,缩放后糊掉、稀疏采样跳过。
症状就是"软件一个一个挤出来、永远列不全"。

正确三步:
1. **密集 + 原生分辨率抽帧**:`bash enumerate_tools.sh <video.mp4> <out> 1/2`(每2秒一帧,**不缩放**)。
2. **逐帧 OCR**:脚本用 `ocr.swift`(macOS Vision,中英)抓屏上文字/面板名 → `<out>/ocr.txt`。
   OCR 抓得到网页面板文字,但**桌面软件的窗口标题/菜单是小字,OCR 常漏** → 必须第3步。
3. **逐帧视觉枚举(必须)**:让 agent / **Workflow fan-out** 分批 `Read` 所有 `d-*.jpg`,
   对每帧判"哪个软件的UI"(窗口标题/菜单/面板布局/时间线样式);桌面 DCC 判到具体是
   Blender/Maya/C4D/3ds Max/Houdini/ZBrush 哪个;最后**合并去重**。

**两种并行编排方式**(都验证过,结论一致=本视频2个软件:混元3D网页+Cinema 4D):

A. **harness dynamic workflow(首选,可复现+落 dashboard)**:`video_understand.star`,一条命令跑完
   全片视觉枚举 + 内容理解,run 被 journal、能在 Agent Dashboard 回看:
   > 需先安装 `harness` CLI(workflow 工具),来自 **https://github.com/cyl19970726/multi-agent-harness**;
   > 见 `author-workflow` skill 与该仓库 README。版本要与该仓库的 workflow API 对应。
   ```bash
   # 1) 先抽密集帧+OCR
   bash skills/video-understand/enumerate_tools.sh <video.mp4> /tmp/vu_dense 1/2
   # 2) 从 harness 仓库 cwd 跑(run 才落到 dashboard 的 store)
   harness workflow run-script <此目录>/video_understand.star \
     --args '{"frames_dir":"/tmp/vu_dense/","frame_count":72,"aligned":"/tmp/vu_hunyuan/aligned.md","batch":8}' \
     --start-runtime --progress
   # 结果在 stdout 的 run.final_output.result(software_count/all_software/desktop_dcc/steps/...)
   ```
   程序里:视觉 scan 批用 `provider="claude"`,合并去重 + 读逐字稿做内容理解用 `provider="codex"`(省成本)。
   `--dry-run` 可先验证语法;`--start-runtime` 自动拉起 provider runtime。

B. **Workflow 工具(ultracode 下临时 fan-out)**:`parallel` 分批,`schema` 用**标准 JSON Schema**
   (`{type:'object',properties:{...},required:[...]}`),再一个 synthesize agent 合并。

⚠️ 两个坑:① **codex 不能读图**,视觉枚举必须 `claude`;codex 只跑文本/合成步。
② **schema 约定不同**:harness `run-script` 用扁平 `{key:"hint"}`(列表靠"每行一个"+`splitlines`);
Workflow 工具用标准 JSON Schema。别混。

## 坑(实测)
- **直链有时效 + 防盗链**:`download_video` 已带 UA+Referer;`note` 模式会逐个试 best+backup 直链。rnote API 偶发 502/503/429 时,可改用上一轮抓到的 CDN 直链走 `--url`。
- **取视频直链兼容性**:note 结构有两种(note/image=`data.data[0].note_list[0]`、note/video=`data.data[0]`直接是note);mp4 有的在 `n['video']` 有的散在别处。`_find_note`/`extract_video` 已兼容(搜整条 note)。
- **whisper 输出可能是繁体**:脚本已加 `--initial_prompt` 引导简体;要更准用 `--model medium`。
- **关键帧 token 成本**:默认场景切变抽 ≤12 张并缩到 640 宽;别无脑加密集帧。封面图是最便宜的"先看一眼"。
- **真·剪辑/节奏理解**(转场/运镜/卡点)关键帧给不全,需要时换原生视频模型(Gemini 2.x / Qwen2.5-VL video),只对要复刻形式的 top 爆款用。
