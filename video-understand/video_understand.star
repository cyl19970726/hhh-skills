# video_understand.star —— 小红书视频理解 + 全片软件枚举(harness dynamic workflow)
#
# 用 harness run-script 把"视频理解"固化成可复现、可在 dashboard 回看的 run:
#   1. fan-out: 密集关键帧分批,claude 视觉逐帧识别软件UI(codex 读不了图,视觉步必须 claude)
#   2. 合并去重: codex 汇总出"全部不同软件 + 出现帧/依据 + 桌面DCC判定"(纯文本→codex)
#   3. 内容理解: codex 读音画对齐逐字稿,提炼产品/步骤/卖点(纯文本→codex)
#   4. output(): 把软件清单+内容理解打成一个结构化结果,caller 读 final_output.result
#
# 跑(从 harness 仓库 cwd,run 才落到 dashboard 的 store):
#   harness workflow run-script skills/video-understand/video_understand.star \
#     --args '{"frames_dir":"/tmp/vu_dense/","frame_count":72,"aligned":"/tmp/vu_hunyuan/aligned.md","batch":8}' \
#     --start-runtime
# 读结果: stdout 的 run.final_output.result;或 harness dashboard snapshot 看 workflow_runs/steps。

workflow(
    "xhs-video-understand-enumerate",
    "把'小红书视频理解'拆成可并行、可交叉验证的工序:视觉步(逐帧识别软件)用 claude 因为 codex 读不了图," +
    "纯文本步(合并去重软件清单、读逐字稿做内容理解)交给 codex 省成本;最后 output() 出一个结构化拆解。" +
    "这样把之前手动+一次性脚本做的事固化成可复现、可在 dashboard 回看的 run。",
)

A = args if args else {}
FRAMES_DIR = A["frames_dir"] if "frames_dir" in A else "/tmp/vu_dense/"
FRAME_COUNT = A["frame_count"] if "frame_count" in A else 72
ALIGNED = A["aligned"] if "aligned" in A else "/tmp/vu_hunyuan/aligned.md"
BATCH = A["batch"] if "batch" in A else 8

def pad3(i):
    s = str(i)
    if i < 10:
        return "00" + s
    if i < 100:
        return "0" + s
    return s

frames = [FRAMES_DIR + "d-" + pad3(i) + ".jpg" for i in range(1, FRAME_COUNT + 1)]

batches = []
start = 0
for _ in range(FRAME_COUNT):
    if start >= len(frames):
        break
    batches.append(frames[start:start + BATCH])
    start += BATCH

log("帧数 " + str(len(frames)) + ",分 " + str(len(batches)) + " 批,每批 " + str(BATCH) + " 帧")

# ---- 1. 视觉 fan-out:逐帧识别软件(claude) ----
phase("scan")

def scan_prompt(flist):
    return """你在审查一条"3D AI建模教程"录屏视频的关键帧(竖屏),目标=枚举视频里用到的所有软件。
请用 Read 工具逐张打开下面这些图片:
{flist}
对每一帧判断它是哪个软件/应用的界面,依据:窗口标题栏、菜单栏、面板布局、软件专属UI图标、底部时间线样式。
候选:网页应用(腾讯混元3D/Hunyuan:深色面板+"几何生成/低模拓扑/组件拆分/语义UV/动画生成/下载")、
桌面DCC(Blender/Maya/Cinema4D(C4D)/3ds Max/Houdini/ZBrush/Substance:看左上视口相机名、底部动画时间线、菜单栏)、
浏览器、图像工具。桌面DCC务必判定具体哪一个并给依据。只有黑底3D模型而无任何软件UI的标 model-only。
基于实际看到的画面,勿臆测。""".format(flist=flist)

scan_specs = []
for bi in range(len(batches)):
    flist = "\n".join(["- " + f for f in batches[bi]])
    scan_specs.append({
        "prompt": scan_prompt(flist),
        "provider": "claude",
        "label": "scan-b" + str(bi + 1),
        "phase": "scan",
        "schema": {
            "per_frame": "每帧一行: <文件名> — <软件名或model-only> — <识别依据>",
            "distinct_software": "本批识别到的所有不同软件,逗号分隔",
        },
    })

scans = parallel(scan_specs)

dump_parts = []
for i in range(len(scans)):
    s = scans[i]
    if type(s) == "dict":
        dump_parts.append("## 批次 " + str(i + 1) + "\n软件: " + s["distinct_software"] + "\n" + s["per_frame"])
    else:
        dump_parts.append("## 批次 " + str(i + 1) + " (无有效输出)")
dump = "\n\n".join(dump_parts)

# ---- 2. 合并去重软件清单(codex,纯文本) ----
phase("synthesize")
syn = agent(
    """下面是多个 agent 逐帧视觉识别的软件结果。请合并去重,给出这条视频用到的全部不同软件清单,
每个附"出现帧/大致时间 + 识别依据",并明确桌面DCC到底是哪个。只统计画面里真正出现过界面的软件,
口播提到但界面没出现的(如导出到'其他三维软件')不计入软件数、单列说明。

""" + dump,
    provider="codex",
    label="synthesize",
    phase="synthesize",
    schema={
        "all_software": "全部不同软件,每行一个: <软件> — <出现帧/时间> — <依据>",
        "count": "画面真正出现界面的不同软件总数(纯数字)",
        "desktop_dcc_verdict": "桌面DCC是哪个 + 证据",
        "uncertainties": "仍存疑、需更高清再看的帧/软件",
    },
)

# ---- 3. 内容理解:读对齐逐字稿提炼(codex,纯文本) ----
phase("content")
content = agent(
    """请阅读 {aligned}(这条视频的音画对齐逐字稿 + 每个关键帧时刻的口播)。
基于口播逐字稿,提炼这条视频:产品/更新是什么、它优化了哪几个方向、完整操作步骤(按顺序)、每步卖点与注意事项。
纠正 whisper 同音错字:'托谱/拓谱'=拓扑,'展优威'=展UV,'谷歌绑定'=骨骼绑定,'APOS/T-POS'=A-Pose/T-Pose,'细分smose'=细分smooth。""".format(aligned=ALIGNED),
    provider="codex",
    label="content-understand",
    phase="content",
    schema={
        "product": "讲的什么产品/更新",
        "directions": "本次优化的几个方向,每行一个",
        "steps": "完整操作步骤,每步一行,按顺序",
        "selling_points": "卖点与注意事项,每行一个",
    },
)

# ---- 4. 汇总产出 ----
sw = syn["all_software"] if type(syn) == "dict" else "(枚举失败)"
cnt = syn["count"] if type(syn) == "dict" else "?"
dcc = syn["desktop_dcc_verdict"] if type(syn) == "dict" else "?"
unc = syn["uncertainties"] if type(syn) == "dict" else "?"

prod = content["product"] if type(content) == "dict" else "?"
dirs = content["directions"] if type(content) == "dict" else "?"
steps = content["steps"] if type(content) == "dict" else "?"
sp = content["selling_points"] if type(content) == "dict" else "?"

output({
    "software_count": cnt,
    "all_software": sw,
    "desktop_dcc": dcc,
    "uncertainties": unc,
    "product": prod,
    "directions": dirs,
    "steps": steps,
    "selling_points": sp,
})

ok = (type(syn) == "dict") and (type(content) == "dict")
verdict(ok, reason="软件枚举与内容理解均产出" if ok else "部分工序失败,结果不完整")
