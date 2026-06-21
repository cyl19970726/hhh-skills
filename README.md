# hhh-skills

一组用于 **Claude Code / agent** 的可复用 skill —— 覆盖 AI 3D/AR 制作管线、多 agent 编排方法论、小红书内容研究等。每个目录是一个独立 skill(含 `SKILL.md` 描述 + 配套脚本/参考)。

## ⚠️ 前置依赖:workflow 工具(harness CLI)

其中 **`author-workflow`** 和 **`video-understand`** 的 `.star` 编排都依赖 **`harness` CLI**(`harness workflow run-script`)。这个 workflow 工具来自配套仓库,**请下载并安装对应版本**:

> **https://github.com/cyl19970726/multi-agent-harness**

```bash
# 构建 harness CLI(workflow 运行时)
git clone https://github.com/cyl19970726/multi-agent-harness.git
cd multi-agent-harness
cargo build -p harness-cli                 # 产出 target/debug/harness
cp target/debug/harness ~/.local/bin/      # 放进 PATH(或 cargo build --release)

# author-workflow 这个 skill 的"出厂地"也是该仓库,可直接装:
scripts/install-skill.sh --agent both
#   或 Claude Code 插件市场:
#   /plugin marketplace add cyl19970726/multi-agent-harness && /plugin install author-workflow
```

> 注意**版本要对应**:本仓库这些 skill 写法对应的是 multi-agent-harness 当前的 workflow API(Starlark `run-script`、`workflow()/agent()/parallel()` 等)。harness 升级后若 API 变动,以该仓库 README 为准。

## 用法

把需要的 skill 目录放进 `~/.claude/skills/`(或整仓 clone 进去):

```bash
git clone https://github.com/cyl19970726/hhh-skills.git ~/hhh-skills
ln -s ~/hhh-skills/<skill-name> ~/.claude/skills/<skill-name>   # 单个软链
# 或直接整目录拷贝你要的那几个
```

Claude Code 启动时会按各 `SKILL.md` 的 description 自动判断何时触发。

## Skills

### 3D / AR / 视频 管线
| Skill | 作用 |
|---|---|
| [ai-ip-series-design](ai-ip-series-design) | 用 AI 做「可控的 IP 系列形象」:把一个吉祥物扩成风格统一/角色一致/可换装可入景的系列(六步管线 + 参考对标GATE + 世界级IP范例库 + 三个实战提示词 + 多图锁一致性),上游接 3D/AR |
| [codex-imagegen](codex-imagegen) | 用 codex 生成/编辑高质量位图:内置 `image_gen` 工具(免 OPENAI_API_KEY)自动触发,高质量提示词法 + 透明抠图 + CLI 兜底(gpt-image-2/1.5)+ 在 workflow 里 fan-out 多 codex 并行生图 |
| [ar-3d-animation-pipeline](ar-3d-animation-pipeline) | 浏览器 WebAR 3D 角色/场景从 0 到 1 的完整流程与已验证工具链(图生3D→绑骨→减面→r3f→MindAR→真机) |
| [tripo-api](tripo-api) | Tripo3D REST API 实战:图/文生3D、多视图重建、自动绑骨、预制动画重定向(端点/参数/积分/踩坑)+ 驱动脚本 |
| [blender-mcp](blender-mcp) | 用 Blender MCP 程序化驱动 Blender 做动画管线:Mixamo 重定向、IK、NLA、glTF 导出 + evaluator |
| [beat-performance-pipeline](beat-performance-pipeline) | 把"角色一段连续表演"拆成与配音对齐的 Beat,逐 beat 设计→实现→多维评审→loop(共享坐标契约) |
| [webar-mindar-ios](webar-mindar-ios) | 构建/调试浏览器图像追踪 AR(MindAR + A-Frame + Three.js),专治 iOS-Safari/WebKit 独有的黑屏/塌缩坑 |
| [video-understand](video-understand) | 小红书/教程视频理解:下载→抽帧→whisper→音画对齐;含"枚举全片软件"模式(密集帧+OCR+逐帧视觉) |

### 多 Agent 编排 / 方法论
| Skill | 作用 |
|---|---|
| [author-workflow](author-workflow) | 运行时用 Starlark 编写动态多 agent workflow,经 harness `run-script` 跑并回看 WorkflowRun |
| [guide-agent-teams](guide-agent-teams) | Claude Code Agent Teams 完整使用指南:多 session 协作、共享任务、inter-agent 通信、Lead 管理方法论 |
| [decision-closure](decision-closure) | 决策闭包方法论:执行前重建任务的全部必做决策,用覆盖表暴露"被意外决定/无人决定"的决策类 |
| [exploration-judgment](exploration-judgment) | "探索的判断力":在沉成本前判断哪个节点值得深挖、哪个够用即走,把知识当可证伪、会过时来持有 |

### 工具
| Skill | 作用 |
|---|---|
| [agent-browser](agent-browser) | 面向 agent 的浏览器自动化 CLI:导航/填表/点击/截图/抓数据/测试 web app |
| [xhs-crawler](xhs-crawler) | 小红书帖子/视频抓取(rnote.dev API):搜索/笔记/评论/视频直链(API Key 走环境变量,不入仓) |

## 约定

- **不提交密钥**:所有 skill 的 API Key 一律走环境变量(如 `TRIPO_KEY`、`RNOTE_API_KEY`);`.gitignore` 已挡掉 `.env`/`*.key` 等。
- 多数 `SKILL.md` 是**活文档** —— 实践有新经验就往对应章节追加。

## License

MIT
