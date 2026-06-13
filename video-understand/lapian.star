# lapian.star —— 拉片(把一条对标视频拆成可复刻 SOP)的 harness dynamic workflow
#
# 前置:先用 prep_video.py 备好素材(aligned.md + kf-*.jpg;可选 dense.md + d-*.jpg)。
# 本 workflow 编排 拉片三步:STEP3 判型 → STEP6 产出① 逐段拉片报告 → 产出② 复现SOP。
# (STEP4 两遍细看的"密抽"是 shell 步,由调用方先跑 prep_video.py --densify,见 SKILL.md)
#
# 跑(从 harness 仓库 cwd):
#   harness workflow run-script <此目录>/lapian.star \
#     --args '{"aligned":"/tmp/vu_xhs2/aligned.md","frames_dir":"/tmp/vu_xhs2/","frame_count":30,
#              "meta":"标题:用Claudecode拉片 | 赞151/藏290/评8 | 270s"}' \
#     --start-runtime --progress
#   结果在 stdout 的 run.final_output.result(vtype / report / sop)
#
# ⚠️ 视觉步(判型/报告)必须 provider="claude"(codex 读不了图);复现SOP 是纯文本→codex 省成本。

workflow(
    "lapian-deconstruct",
    "把'拉片'拆成可交叉验证的工序:先判型(口播/叙事/混剪 三类三套眼光,判错后面全白拆)," +
    "再按型产出逐段拉片报告(它怎么做的,工具链带事实/推断/不知道三级置信度),最后由报告生成复现SOP(你怎么抄)。" +
    "视觉步用 claude(codex读不了图),纯文本的SOP步用 codex 省成本。固化成可复现、可在 dashboard 回看的 run。",
)

A = args if args else {}
ALIGNED = A["aligned"] if "aligned" in A else "/tmp/vu_xhs2/aligned.md"
FRAMES_DIR = A["frames_dir"] if "frames_dir" in A else "/tmp/vu_xhs2/"
N = A["frame_count"] if "frame_count" in A else 30
META = A["meta"] if "meta" in A else "(无元数据)"
DIMS = A["dimensions"] if "dimensions" in A else "台词/节奏卡点/特效动效/版式镜头/字体/调色/配乐/工具链(默认全勾)"

def pad3(i):
    s = str(i)
    if i < 10:
        return "00" + s
    if i < 100:
        return "0" + s
    return s

frames = [FRAMES_DIR + "kf-" + pad3(i) + ".jpg" for i in range(1, N + 1)]
flist = "\n".join(["- " + f for f in frames])
# 判型只需扫一眼:取均匀 6 张
probe = []
step = N // 6 if N >= 6 else 1
for i in range(0, N, step):
    probe.append(frames[i])
plist = "\n".join(["- " + f for f in probe])

# ---- STEP3 判型 ----
phase("判型")
ft = agent(
    """你是拉片师,先给这条视频判型(判错后面全白拆)。
读逐字稿/音画对齐:{aligned}
再 Read 这几张代表帧扫一眼画面:
{plist}
判定它属于哪一类,并给"该型重点看什么"的眼光:
- 口播/教程(录屏±露脸,讲操作):重 工具链/操作步骤/屏幕信息
- 叙事/剧情/vlog(实景有情节):重 镜头/运镜/转场/配乐/情绪曲线
- 混剪/图文卡点(快切大字):重 卡点/字体版式/转场""".format(aligned=ALIGNED, plist=plist),
    provider="claude",
    label="判型",
    phase="判型",
    schema={
        "vtype": "口播/教程 | 叙事/vlog | 混剪/图文卡点 之一",
        "lens": "该型这次重点看什么(一句)",
        "why": "判型依据",
    },
)
vtype = ft["vtype"] if type(ft) == "dict" else "口播/教程"
lens = ft["lens"] if type(ft) == "dict" else "工具链/操作步骤/屏幕信息"

# ---- STEP6 产出① 逐段拉片报告 ----
phase("拉片报告")
report = agent(
    """你是拉片师。视频元数据:{meta}。判型={vtype};本次眼光={lens};要拉的维度={dims}。
先读音画对齐全文:{aligned}
再按时间顺序 Read 全部关键帧:
{flist}
产出【逐段拉片报告】(它是怎么做出来的),诚实区分事实/推断。""".format(
        meta=META, vtype=vtype, lens=lens, dims=DIMS, aligned=ALIGNED, flist=flist),
    provider="claude",
    label="拉片报告",
    phase="拉片报告",
    schema={
        "cover": "封面:标题 / 时长·段数·切点 / 一句话定性",
        "verdict": "一句话结论:这片到底怎么做的",
        "score": "可复刻度评分(0-10),分维度:拍摄 / 图形层 / 节奏 / 工具链",
        "findings": "关键发现,每行一条(如 0切点 / 1.5s一句 / 语义卡点)",
        "segment_table": "配帧逐段表,每行: 时间码 | 代表帧 | 台词要点 | 图形/特效 | 节奏 | 作用",
        "toolchain": "图形层部件清单+工具链推断,每行: <工具/部件> — <置信度:事实/推断/不知道> — <依据>",
    },
)

# ---- 产出② 复现 SOP(纯文本→codex) ----
phase("复现SOP")
rep_text = json.encode(report) if type(report) == "dict" else "(报告生成失败)"
sop = agent(
    """基于下面这份逐段拉片报告,产出【复现 SOP】(别人照着就能抄出同款视频)。判型={vtype}。

报告(JSON):
{rep}""".format(vtype=vtype, rep=rep_text),
    provider="codex",
    label="复现SOP",
    phase="复现SOP",
    schema={
        "scene": "适用场景(一句)",
        "stack": "工具栈,每环节给推断,每行一个",
        "pipeline": "流水线分段,每段一行(如 逐字稿→实拍→图形层→剪辑→收尾)",
        "per_stage": "每段怎么做:素材怎么备/怎么拍/图形怎么做/节奏怎么卡,每段一行",
        "copyables": "可抄要点×5,每行一条(开场钩子/结构套路/降门槛...)",
    },
)

out = {"vtype": vtype, "lens": lens}
if type(report) == "dict":
    for k in report:
        out["report_" + k] = report[k]
if type(sop) == "dict":
    for k in sop:
        out["sop_" + k] = sop[k]
output(out)

ok = (type(report) == "dict") and (type(sop) == "dict")
verdict(ok, reason="判型+拉片报告+复现SOP 均产出" if ok else "部分工序失败")
