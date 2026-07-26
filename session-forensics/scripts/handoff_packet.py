#!/usr/bin/env python3
"""Generate a handoff packet skeleton from a session's evidence flow.

What this can and cannot do
---------------------------
Sections 1, 2, 4, 5 and the appendix are pure evidence — the script fills them.
Sections 3, 6, 7, 8, 9, 10 require judgement (what was falsified, which
assumptions were never tested, what the next minimal experiment is) and are
emitted as marked stubs for a human or an auditing agent to complete.

**Never delete the stubs to make the packet look finished.** An unfilled §6
（已证伪）is the single most costly omission: without it the next agent inherits
the previous agent's wrong conclusions as established fact.

Per the template's first principle the output is an INDEX, not a summary: every
figure carries a line number or a reproducible command, so the reader can return
to the original instead of trusting this file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from session_metrics import scan  # noqa: E402

STUB = "<!-- TODO 需要判断，不可由脚本填写；留空即视为未完成 -->"


def load_baseline(skill_dir: Path) -> dict[str, Any] | None:
    p = skill_dir / "local" / "baseline.json"
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def quantile_of(value: float, dist: dict[str, Any] | None) -> str:
    """Where does this session sit in the user's OWN corpus? Absolute values are
    not interpretable across environments; only the local percentile is."""
    if not dist or not isinstance(value, (int, float)):
        return ""
    for label in ("p95", "p90", "p75", "p50", "p25"):
        if label in dist and value >= dist[label]:
            return f"≥{label}"
    return "<p25"


def section_resume_point(r: dict[str, Any]) -> str:
    """§0 — the first thing the receiver reads: is the current goal still the initial one?

    §1 records the evolution but nothing forced §10 to inherit it, so an auditor
    would diagnose "legitimate evolution" and then order the next steps by its
    own findings. Measured on 019f9a28: the user's deliverable got pushed to
    item 3 while tool fixes were labelled blocking. Putting the delta at the
    very top makes skipping the re-alignment visible.
    """
    subs = r["objective_trace"]["substantive"]
    first = subs[0] if subs else None
    last = subs[-1] if subs else None
    out = ["## 0. 任务续接点 —— 当前目标是否还是初始目标", "",
           "```"]
    if first:
        out.append(f"初始目标（L{first[0]}）  {first[1][:150]}")
    if last and last is not first:
        out.append(f"最后一条（L{last[0]}）  {last[1][:150]}")
    out += ["```", "",
            "**当前活的目标（逐条对照 §1 后填写，不许照抄初始目标）**：", "", STUB, "",
            "**接手方第一件事**（必须服务当前目标；审计员发现的工具问题属于支撑项）：", "",
            STUB, ""]
    return "\n".join(out)


def section_objectives(r: dict[str, Any]) -> str:
    subs = r["objective_trace"]["substantive"]
    lines = ["## 1. 原始目标（逐字，未转述）", "",
             "| 行号 | 原话 | 性质 |", "|---|---|---|"]
    truncated = False
    for ln, msg in subs[:40]:
        cell = msg[:150].replace("|", "/")
        if len(msg) > 150:
            cell += " …（逐字全文见 §1 附）"
            truncated = True
        lines.append(f"| L{ln} | {cell} | {STUB} |")
    if len(subs) > 40:
        lines.append(f"| … | 另有 {len(subs)-40} 条，见 `objective_trace.substantive` | |")
    pumps = r["objective_trace"]["pump_genuine"]
    resumes = r["objective_trace"]["pump_resume"]
    lines += ["", f"已过滤：ambient 注入 {r['scale']['user_ambient']} 条、"
                  f"纯推进 {len(pumps)} 条、网络续跑 {len(resumes)} 条（后者是环境噪声，非用户意图）。",
              "", "**P3 判定**（目标演化是否全部由 user message 引入；若否，指出 agent 自漂起点）：",
              STUB, ""]
    if truncated:
        # The table is for scanning; it cannot hold a long instruction. But §1's
        # contract is 逐字 — a receiver who inherits a sentence cut at 150 chars
        # inherits a different goal and has no marker telling them so. So the
        # table gets a preview + pointer, and the full text is emitted below.
        lines += ["### §1 附：逐字全文（表格里被截断的那几条）", ""]
        for ln, msg in subs[:40]:
            if len(msg) <= 150:
                continue
            lines += [f"**L{ln}**", "", "> " + msg.replace("\n", "\n> "), ""]
    return "\n".join(lines)


def section_state(r: dict[str, Any]) -> str:
    b = r["b_class"]
    ev = r["evidence_flow"]
    out = ["## 2. 当前真实状态（只从物证重建，不引用 agent 宣称）", "",
           f"格式 `{r['format']}`　能力 `{r['capabilities']}`", "",
           "### 仪器与工作树", ""]
    out.append(f"触及工作树 {len(b['worktrees'])} 个：")
    for w in b["worktrees"][:10]:
        out.append(f"- `{w}`")
    if b["forked_files"]:
        out += ["", f"**跨工作树分叉文件 {b['forked_count']} 个**（同名文件在多处各自演化）：", ""]
        for name, roots in list(b["forked_files"].items())[:12]:
            out.append(f"- `{name}` → {', '.join(roots)}")
    else:
        out += ["", "未检出跨工作树分叉。"]
    out += ["", "### 改动分布", "",
            f"- 仪器 `tools/ scripts/ harness/ tests/`：{ev['instrument_patches']} 次",
            f"- 业务：{ev['business_patches']} 次",
            "", "改动最多的文件：", ""]
    for f, c in ev["top_patched"][:8]:
        out.append(f"- {c:>4}× `{f}`")
    out += ["", "### owner 可见性（同一条命令在各副本的实测结果）", "", STUB,
            "", "### 会话结束后落盘的产物（`stat` 产物目录，mtime > session mtime）", "", STUB, ""]
    return "\n".join(out)


def section_data(r: dict[str, Any], base: dict[str, Any] | None) -> str:
    s, rt, c = r["scale"], r["rates"], r["context"]
    bm = (base or {}).get("metrics", {})
    out = ["## 4. 关键实测数据（会死于压缩的数字全部在此）", "", "```",
           f"lines={s['lines']}  compactions={s['compactions']}  execs={s['execs']}  "
           f"patches={s['patches']} / {s['files_touched']} files",
           f"session_meta={s['session_meta_records']}  malformed={s['malformed']}",
           f"turns: complete={s['turn_complete']}  aborted={s['turn_aborted']}",
           f"narrative: assistant={s['assistant_msgs']} thinking={s['reasoning_items']}",
           f"user: substantive={s['user_substantive']} pump={s['user_pump']} "
           f"resume={s['user_resume']} ambient={s['user_ambient']}", "```", "",
           "| 指标 | 本会话 | 本地语料分位 |", "|---|---|---|"]
    for k, v in rt.items():
        if v is None:
            out.append(f"| `{k}` | 平台不支持 | — |")
        elif isinstance(v, (int, float)):
            out.append(f"| `{k}` | {v} | {quantile_of(v, bm.get(k))} |")
        else:
            out.append(f"| `{k}` | {v} | |")
    out += ["", "### 上下文洪水（预算去哪了）", "", "```"]
    for row in r["evidence_flow"]["output_volume_by_tool"][:6]:
        out.append(f"{row['tool']:<20} {row['calls']:>5} calls  {row['megachars']:>8.2f}M chars  "
                   f"{row['share']*100:>5.1f}%  avg {row['avg_chars']:,}")
    out += ["```", ""]
    if c["segments"]:
        out += ["### 上下文轨迹", "", "```",
                f"window={c['window']}  floor {c['floor_first']} → {c['floor_last']}  peak={c['peak_max']}"]
        segs = c["segments"]
        for i in range(0, len(segs), max(1, len(segs) // 6)):
            g = segs[i]
            out.append(f"  seg{i:<3} after_line={g['after_line']:<7} floor={g['floor']:<8} peak={g['peak']}")
        out += ["```", ""]
    rec = [x for x in r["objective_trace"]["recurring_asks"] if x["verdict"] == "restated"]
    if rec:
        out += ["### 重述诉求（第一次说的没落地；已扣除网络重发）", ""]
        for cl in rec[:5]:
            for ln, m in cl["members"]:
                out.append(f"- L{ln}: {m[:130]}")
            out.append("")
    if r["sub_agents"]:
        out += ["### 子 agent", "", "```"]
        for a, n in r["sub_agents"][:8]:
            out.append(f"{n:>4}  {a}")
        out += ["```", ""]
    return "\n".join(out)


def build(path: Path, skill_dir: Path) -> str:
    r = scan(path)
    base = load_baseline(skill_dir)
    parts = [
        f"# Handoff Packet · {path.name}", "",
        "> 物证优先的**索引**，不是摘要。每条结论挂行号或可复现命令；接手方按指针回原文。",
        "> 带 TODO 标记的小节需要判断，脚本不填。**§6 已证伪留空 = packet 未完成。**", "",
        section_resume_point(r), section_objectives(r), section_state(r),
        "## 3. 心智模型 / 设计定稿\n\n" + STUB + "\n\n（唯一允许以叙事为主的一节，因此必须最短。）\n",
        section_data(r, base),
        "## 5. 基线 / 对照\n\n" +
        (f"来自 `local/baseline.json`：{base.get('sessions_kept','?')} 个会话，"
         f"语料 {base.get('generated_from')}。\n\n"
         "⚠️ 基线是环境属性。换机器、换工具链、换时间段都必须重新校准。\n"
         if base else "⚠️ 未找到 `local/baseline.json`。先跑 `calibrate.py`，否则所有分位为空，"
                      "绝对值不可解释。\n"),
        "## 6. 已证伪 ⚠️ 必需项\n\n"
        "**上一个 agent 说错的话。** 不写，接手方会把错误结论当既定事实继续用。\n"
        "这是唯一一节专门用于阻止叙事流被继承。\n\n"
        "| 提过的 | 被什么证伪 | 状态 |\n|---|---|---|\n| " + STUB + " | | |\n",
        "## 7. 未证伪的假设\n\n一直当真、从未验证的东西；标注为何未验证、决定性证据在哪。\n\n" + STUB + "\n",
        "## 8. 失效表\n\n当前已知失效边 + 本会话违反了哪几条。\n\n" + STUB + "\n",
        "## 9. 明确非目标\n\n" + STUB + "\n",
        "## 10. 下一步 —— 按 **§0 认定的当前目标** 排序，不按审计员优先级\n\n"
        "写完回头对一次：**第 1 项服务的是用户当前目标吗？** 若第 1 项是修工具 / 修副本 /\n"
        "修 parser 而当前目标是产出某个交付物，顺序就错了——除非能说清交付物物理上依赖它。\n"
        "审计员发现的问题写进「支撑项」，不自动获得优先级。\n\n"
        "最后必须有一条：**什么结果会证伪当前整条路线。**\n\n" + STUB + "\n",
        "## 附：可复现命令\n\n```bash\n"
        f"python3 {skill_dir}/scripts/session_metrics.py \\\n  {path} --json-out /tmp/metrics.json\n"
        f"python3 {skill_dir}/scripts/handoff_packet.py \\\n  {path} --out handoff.md\n```\n",
    ]
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("session", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    skill_dir = Path(__file__).resolve().parent.parent
    text = build(args.session.expanduser(), skill_dir)
    if args.out:
        args.out.expanduser().write_text(text, encoding="utf-8")
        todo = text.count(STUB)
        print(f"wrote {args.out}  ({len(text.splitlines())} 行, {todo} 处待填)")
        print("⚠️ 未填完 §6/§7/§8/§10 的 packet 不可交接。")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
