# ip-family.star — 可复用模板:用 harness .star 一条命令 fan-out 多个 codex 并行"开多个角色"
#
# 这是 ai-ip-series-design §1/§2 第1步「一次定全家族」+ 第2步「逐角色出卡」的可复用封装,
# 把本 skill 里散落的一次性脚本(yingge-family / yingge-extract …)沉淀成一个【参数化模板】。
# 依赖 harness CLI(workflow run-script)+ codex 内置 image_gen(见 [[codex-imagegen]],免 API key)。
#
# 用法(从一个 git 仓库 cwd 跑,writable worker 需要 git worktree):
#   harness workflow run-script <此文件> --start-runtime --progress --args '{
#     "out_dir": "/abs/输出/我的IP家族",
#     "style_ref": "/abs/风格基准图.png",            // 可选:每个 worker 的图2风格参考(锁材质/配色)
#     "lock": "统一锁定:配色X+Y+Z三色;收藏手办哑光无塑料光;大块几何四肢分离利3D;纯白底;无文字logo。",
#     "characters": [
#       {"slug":"hero",   "desc":"【主角】高挑健硕,标志记号=...,主色..."},
#       {"slug":"burly",  "desc":"【猛将】魁梧壮硕,..."},
#       {"slug":"lanky",  "desc":"【引路者】瘦长灵动,..."},
#       {"slug":"chibi",  "desc":"【萌点】矮壮童比例(大头短身),..."},
#       {"slug":"beast",  "desc":"【神兽】矮胖团圆非人形,..."}
#     ],
#     "family_variants": 3,   // 先出几张【全家组合图】(同一次生成=天然同风格);0=跳过
#     "per_char": true        // 是否再逐角色出独立白底单卡(第2步提取)
#   }'
#
# 产出落在 out_dir/: family_1.png.. (全家组合图) + char_<slug>.png (逐角色单卡)。
# 一致性靠:① family 同一次生成天然同风格;② 逐角色都以 style_ref(+建议 family 母版)为参考。
# 选最佳 family 母版、把它当后续逐角色参考,见 SKILL.md §4/§6(身份胶囊、多图分槽)。
#
# ⚠️ 本模板【必须带 --args】(本版 harness 不传 --args 时 `args` 全局未绑定会报错);
#    只想验证语法就传空:`--dry-run --args '{}'`(走内置 demo 默认值)。
# ⚠️ writable worker 需要从 git 仓库 cwd 跑(建 worktree);out_dir 用绝对路径(全局 $CODEX_HOME 产物不随 worktree 丢)。

workflow(
    "ip-family",
    "Reusable ai-ip-series-design STEP1+STEP2 template: data-driven fan-out of codex image_gen workers to " +
    "(optionally) generate N whole-family group shots (一次定全家族 = one generation = naturally consistent) " +
    "AND one standalone card per character, all locked to a shared brief + optional style ref. Width is driven " +
    "by args.characters so any IP family runs with one command. Each writable codex worker copies the EXACT " +
    "image_gen path out (avoids the shared generated_images race).",
    success_criterion="family group shot(s) + one clean card per character, design-consistent, saved to out_dir",
)

SPEC = args or {}
OUT = SPEC.get("out_dir", "/tmp/ip-family-demo")
STYLE = SPEC.get("style_ref", "")
LOCK = SPEC.get("lock", "统一锁定:收藏级手办哑光质感、无塑料白高光;大块几何、四肢与躯干分离、利图生3D;纯白背景、无地面无投影;不出现任何文字与 logo。1:1 画幅。")
CHARS = SPEC.get("characters", [
    {"slug": "demo_hero", "desc": "【主角】高挑健硕,一个可注册的标志记号。"},
    {"slug": "demo_chibi", "desc": "【萌点】矮壮童比例(大头短身)。"},
])
FAMILY_VARIANTS = SPEC.get("family_variants", 2)
PER_CHAR = SPEC.get("per_char", True)

IMGS = [STYLE] if STYLE else []
REFNOTE = "\n(以参考图为风格/材质/配色基准,角色设计服从下方描述。)" if STYLE else ""

# 全家角色清单文本(供"一次定全家族"组合图)
roster = ""
for i in range(len(CHARS)):
    roster += str(i + 1) + ". " + CHARS[i]["slug"] + ":" + CHARS[i]["desc"] + "\n"

def cp_step(path):
    return ("\n\n执行:用你的内置 image_gen 工具按上面要求生成(尽量大、纯白背景)。" +
            "image_gen 返回保存路径后,复制【你这次生成的那个确切文件】(勿 ls 取最新,多并发共用 $CODEX_HOME/generated_images/)到绝对路径:\n   " +
            path + "\n回报最终绝对路径 + 文件大小。")

# ---- STEP 1: 一次定全家族(N 张组合图变体) ----
if FAMILY_VARIANTS > 0:
    phase("family")
    fam_specs = []
    for v in range(FAMILY_VARIANTS):
        fam_specs.append({
            "prompt": LOCK + REFNOTE +
                      "\n\n生成一组【全家组合图】:下列 " + str(len(CHARS)) + " 个角色一字排开,同一个世界、画风/材质/打光完全统一(像同一套盲盒),刻意拉开高矮胖瘦、头身比各不同、体型对比强烈。\n\n角色清单:\n" + roster +
                      "\n本版(第 " + str(v + 1) + " 版)可在排布/站位上略作变化,但角色设计保持一致。" +
                      cp_step(OUT + "/family_" + str(v + 1) + ".png"),
            "provider": "codex", "writable": True,
            "label": "family-" + str(v + 1), "phase": "family",
            "image": IMGS,
        })
    fam = parallel(fam_specs)
    for v in range(len(fam)):
        log("family-" + str(v + 1) + " => " + str(fam[v])[:140])

# ---- STEP 2: 逐角色独立单卡 ----
if PER_CHAR:
    phase("chars")
    char_specs = []
    for c in CHARS:
        char_specs.append({
            "prompt": LOCK + REFNOTE +
                      "\n\n单独生成【这一个角色】的独立定稿卡:" + c["desc"] +
                      "\n正面略 3/4、全身、居中、纯白背景、画面里只有这一个角色、无其他角色。设计/配色/材质与统一锁定一致。" +
                      cp_step(OUT + "/char_" + c["slug"] + ".png"),
            "provider": "codex", "writable": True,
            "label": "char-" + c["slug"], "phase": "chars",
            "image": IMGS,
        })
    chars = parallel(char_specs)
    for i in range(len(chars)):
        log("char-" + CHARS[i]["slug"] + " => " + str(chars[i])[:140])

verdict(True, "ip-family 模板:已并行产出全家组合图 + 逐角色单卡(数据驱动 fan-out)")
output({
    "out_dir": OUT,
    "family": [OUT + "/family_" + str(v + 1) + ".png" for v in range(FAMILY_VARIANTS)],
    "chars": [OUT + "/char_" + c["slug"] + ".png" for c in CHARS],
})
