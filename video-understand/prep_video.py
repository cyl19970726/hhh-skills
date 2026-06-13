#!/usr/bin/env python3
"""
prep_video.py — 小红书视频理解管线(确定性部分,带音画时间轴对齐)

给一个 note_id / 视频直链 / 本地 mp4,自动完成:
  下载 → 抽 16k 单声道音轨 → whisper 口播(带时间戳分段) → ffmpeg 抽关键帧(记录每帧时间戳)
  → 把"关键帧时间"和"口播分段时间"按时间轴对齐
产出目录:
  clip.mp4 / audio.wav / audio.txt(逐字稿) / audio.json(带时间戳分段)
  kf-*.jpg(关键帧) / kf_times.txt(ffmpeg 原始帧时间) / aligned.md(★音画对齐时间轴) / manifest.json

这一步只做"机器能确定做的事"。最后的"理解/合成"由 agent 完成:
按时间顺序 Read 关键帧 + 看 aligned.md 里每帧对应的口播,按 SKILL.md 模板写《视频拆解》。

依赖外部命令: ffmpeg、whisper(openai-whisper CLI)。
note_id 模式复用 ../xhs-crawler/rnote_xhs.py。

用法:
  python3 prep_video.py --note 6a0b295c00000000350296a1
  python3 prep_video.py --url  http://...rednotecdn.com/...mp4
  python3 prep_video.py --file ./clip.mp4
  # 可选: --out-dir DIR --model small|medium --lang zh --frames 12 --scene 0.25
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
XHS = HERE.parent / "xhs-crawler"


def _rnote():
    sys.path.insert(0, str(XHS))
    import rnote_xhs  # noqa: E402
    return rnote_xhs


def run(cmd):
    subprocess.run(cmd, check=True)


def download_from_note(note_id, out_mp4):
    r = _rnote()
    info = r.extract_video(r.note_video(note_id))
    if not info or not info.get("best_url"):
        sys.exit("取视频直链失败(note 非视频/限流/API 故障)。可改用 --url 或 --file。")
    urls = [info["best_url"]] + [u for u in info.get("all_urls", []) if u != info["best_url"]]
    last = None
    for u in urls:
        try:
            r.download_video(u, out_mp4)
            return info
        except Exception as e:  # noqa: BLE001
            last = e
    sys.exit(f"所有直链下载失败(可能已过期): {last}")


def parse_frame_times(path):
    """从 ffmpeg metadata=print 输出里按顺序抽出每个被保留帧的 pts_time(秒)。"""
    times = []
    if not path.exists():
        return times
    for line in path.read_text(errors="ignore").splitlines():
        m = re.search(r"pts_time:([0-9.]+)", line)
        if m:
            times.append(round(float(m.group(1)), 2))
    return times


def extract_keyframes(mp4, out, frames, scene):
    """抽关键帧并记录每帧时间戳。返回 [(jpg_path, t_seconds), ...]。"""
    times_file = out / "kf_times.txt"
    for f in list(out.glob("kf-*.jpg")) + ([times_file] if times_file.exists() else []):
        f.unlink()

    def _ff(vf):
        run(["ffmpeg", "-y", "-v", "error", "-i", str(mp4),
             "-vf", vf, "-vsync", "vfr", "-frames:v", str(frames), str(out / "kf-%03d.jpg")])

    # 场景切变;metadata=print 把每个保留帧的 pts_time 写进 kf_times.txt
    _ff(f"select='gt(scene,{scene})',metadata=print:file={times_file},scale=640:-1")
    kfs = sorted(out.glob("kf-*.jpg"))
    if len(kfs) < 5:  # 场景帧太少 → 定频回退
        for f in kfs:
            f.unlink()
        _ff(f"fps=1/9,metadata=print:file={times_file},scale=640:-1")
        kfs = sorted(out.glob("kf-*.jpg"))
    times = parse_frame_times(times_file)
    pairs = []
    for i, k in enumerate(kfs):
        pairs.append((k, times[i] if i < len(times) else None))
    return pairs


def spoken_at(t, segments, window=2.0):
    """返回时间 t 处(±window)正在说的口播文本。"""
    if t is None:
        return ""
    hits = [s for s in segments if s["start"] - window <= t <= s["end"] + window]
    if not hits:
        # 退而求其次:取时间中点最接近 t 的一段
        if not segments:
            return ""
        s = min(segments, key=lambda s: abs((s["start"] + s["end"]) / 2 - t))
        hits = [s]
    return " ".join(s["text"].strip() for s in hits).strip()


def fmt_ts(t):
    if t is None:
        return "??:??"
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


def write_aligned(out, pairs, segments):
    """生成 aligned.md:① 按关键帧时间交织的音画时间轴 ② 全量带时间戳逐字稿。"""
    lines = ["# 音画对齐时间轴\n",
             "按关键帧时间排序;每帧标注该时刻正在说的口播。agent 请配合实际 Read 的图片看。\n",
             "| 时间 | 关键帧 | 此刻口播 |", "|---|---|---|"]
    for k, t in sorted(pairs, key=lambda p: (p[1] is None, p[1] or 0)):
        spoken = spoken_at(t, segments).replace("|", "/").replace("\n", " ")
        lines.append(f"| {fmt_ts(t)} | {k.name} | {spoken} |")
    lines += ["", "## 全量逐字稿(带时间戳)", ""]
    for s in segments:
        lines.append(f"[{fmt_ts(s['start'])}–{fmt_ts(s['end'])}] {s['text'].strip()}")
    (out / "aligned.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="小红书视频理解管线(下载+音轨+whisper+抽帧+音画对齐)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--note", help="小红书 note_id(走 rnote 取直链)")
    g.add_argument("--url", help="视频直链(mp4)")
    g.add_argument("--file", help="本地视频文件")
    ap.add_argument("--out-dir", help="输出目录(默认 /tmp/xhs_video_<tag>)")
    ap.add_argument("--model", default="small", help="whisper 模型(small/medium/...)")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--frames", type=int, default=12, help="关键帧上限")
    ap.add_argument("--scene", type=float, default=0.25, help="场景切变阈值")
    a = ap.parse_args()

    tag = a.note or (Path(a.file).stem if a.file else "url")
    out = Path(a.out_dir or f"/tmp/xhs_video_{tag}")
    out.mkdir(parents=True, exist_ok=True)

    info = None
    if a.file:
        mp4 = Path(a.file)
        if not mp4.exists():
            sys.exit(f"文件不存在: {mp4}")
    else:
        mp4 = out / "clip.mp4"
        if a.note:
            info = download_from_note(a.note, str(mp4))
        else:
            _rnote().download_video(a.url, str(mp4))
    print(f"[1/4] 视频就绪: {mp4}")

    wav = out / "audio.wav"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(mp4),
         "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
    print(f"[2/4] 音轨: {wav}")

    pairs = extract_keyframes(mp4, out, a.frames, a.scene)
    print(f"[3/4] 关键帧: {len(pairs)} 张(带时间戳)")

    # whisper:输出 all → 同时得到 txt(可读) 与 json(带时间戳分段)
    run(["whisper", str(wav), "--language", a.lang, "--model", a.model,
         "--output_format", "all", "--output_dir", str(out),
         "--fp16", "False", "--verbose", "False",
         "--initial_prompt", "以下是简体中文普通话内容。"])
    wj = out / (wav.stem + ".json")
    segments = []
    if wj.exists():
        data = json.loads(wj.read_text(errors="ignore"))
        segments = [{"start": s.get("start"), "end": s.get("end"), "text": s.get("text", "")}
                    for s in data.get("segments", [])]
    print(f"[4/4] 逐字稿: {out/(wav.stem + '.txt')} | 分段 {len(segments)} 段")

    write_aligned(out, pairs, segments)

    manifest = {
        "source": a.note or a.url or a.file,
        "mp4": str(mp4),
        "transcript_txt": str(out / (wav.stem + ".txt")),
        "transcript_json": str(wj),
        "aligned_md": str(out / "aligned.md"),
        "keyframes": [{"file": str(k), "t": t} for k, t in pairs],
        "segments": segments,
        "info": info,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))

    print("\n== 素材就绪(音画已对齐),交给 agent 合成 ==")
    print(f"  ★ 对齐时间轴: {out/'aligned.md'}")
    print(f"  关键帧:       {len(pairs)} 张  ({out}/kf-*.jpg)")
    print(f"  逐字稿:       {out/(wav.stem + '.txt')}  (+ .json 带时间戳)")
    print("\n下一步(agent): 按时间顺序 Read kf-*.jpg,对照 aligned.md 里每帧的口播,按 SKILL.md 模板合成。")


if __name__ == "__main__":
    main()
