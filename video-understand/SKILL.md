---
name: video-understand
description: 理解一条小红书(或任意)视频:下载→whisper口播逐字稿→ffmpeg抽关键帧→多模态合成一份《视频拆解》。用于"学习优秀博主的爆款视频"——拆解钩子/选题/视觉/工作流/卖点,产出可复用打法。触发词:"理解这条视频"、"拆解爆款视频"、"这个视频在讲什么"、"学习博主视频"、"video understand"、"看懂小红书视频"。
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

## 两步用法

### ① 跑确定性管线(脚本)
```bash
# 三选一来源;note 模式会自动取直链下载(需 RNOTE_API_KEY)
python3 prep_video.py --note 6a0b295c00000000350296a1
python3 prep_video.py --url  http://...rednotecdn.com/...mp4
python3 prep_video.py --file ./clip.mp4
# 可选: --model medium(更准) --frames 12 --scene 0.25 --out-dir DIR
```
产出 `clip.mp4 / audio.txt(逐字稿) / audio.json(带时间戳分段) / kf-*.jpg(关键帧) / aligned.md(★音画对齐时间轴) / manifest.json`。

**音画对齐**:关键帧时间戳来自 ffmpeg `metadata=print`,口播分段时间来自 whisper `json`,
脚本把两者按时间轴融合进 `aligned.md`——每张关键帧标注"该时刻正在说的口播",再附全量带时间戳逐字稿。

### ② 合成(agent 做,脚本做不了)
- **打开 `aligned.md`** 看时间轴(每帧 ↔ 该刻口播),**按时间顺序 Read `kf-*.jpg`** 对照画面。
- 这样音(口播)画(帧)是**对齐**的:能判断"这句话配的是这个画面",而不是各看各的。
- 按下面模板写《视频拆解》。

## 《视频拆解》输出模板
1. **是什么**:主题 / 主角(工具/产品/做法)/ 一句话定性。
2. **产品或内容逻辑**(口播提炼):它解决什么、怎么做、关键技术/步骤、卖点。
3. **画面验证**:关键帧看到的(演示/界面/成片/屏幕字),验证口播有没有吹。
4. **互动结构归因**:赞/藏/转 + **转赞比**(高=工具干货/收藏型;赞高藏低=冲动娱乐型)。
5. **可复用范式**(学博主):钩子写法 / 结构节奏 / 视觉风格 / 字幕口播形式。
6. **对揭小贤项目的意义**:① 创意参考(视觉/3D工作流) ② 内容分析(选题/对标)。
7. **诚实标注**:工具名以画面水印为准(whisper 可能听错);不确定的别当结论。

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
