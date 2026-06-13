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
        # scale=...:-2 保证偶数高、-pix_fmt yuvj420p 避开 tv-range/奇数高视频上 mjpeg 编码器崩溃;
        # 失败返回 False 而非抛异常,让"场景帧→定频"的回退在失败时也能触发
        try:
            run(["ffmpeg", "-y", "-v", "error", "-i", str(mp4),
                 "-vf", vf, "-fps_mode", "vfr", "-pix_fmt", "yuvj420p",
                 "-frames:v", str(frames), str(out / "kf-%03d.jpg")])
            return True
        except subprocess.CalledProcessError:
            return False

    # 场景切变;metadata=print 把每个保留帧的 pts_time 写进 kf_times.txt
    _ff(f"select='gt(scene,{scene})',metadata=print:file={times_file},scale=640:-2")
    kfs = sorted(out.glob("kf-*.jpg"))
    if len(kfs) < 5:  # 场景帧太少/抽帧失败(口播·录屏类画面变化小,scene 检不到切变) → 定频回退
        for f in kfs:
            f.unlink()
        _ff(f"fps=1/9,metadata=print:file={times_file},scale=640:-2")
        kfs = sorted(out.glob("kf-*.jpg"))
    times = parse_frame_times(times_file)
    if len(times) < len(kfs):
        # 定频回退时 metadata=print 常写不出 pts;fps=1/9 是均匀的,按 i*9 推算时间戳
        times = [round(i * 9.0, 2) for i in range(len(kfs))]
    pairs = []
    for i, k in enumerate(kfs):
        pairs.append((k, times[i] if i < len(times) else None))
    return pairs


def densify(mp4, out, ranges, fps=5.0):
    """二次细看:对粗览标记的"有戏/看不懂"时间段密集抽帧(默认每秒 5 帧)。
    ranges: [(start_s, end_s), ...];跨所有段顺序编号 d-001.jpg…,返回 [(jpg_path, t), ...]。
    -ss 在 -i 前做快速 seek;第 j 帧时间 ≈ start + j/fps。"""
    for f in out.glob("d-*.jpg"):
        f.unlink()
    pairs, idx = [], 1
    for (s, e) in ranges:
        for f in out.glob("__dz-*.jpg"):
            f.unlink()
        try:
            run(["ffmpeg", "-y", "-v", "error", "-ss", str(s), "-to", str(e), "-i", str(mp4),
                 "-vf", f"fps={fps},scale=640:-2", "-pix_fmt", "yuvj420p", str(out / "__dz-%04d.jpg")])
        except subprocess.CalledProcessError:
            continue
        for j, t in enumerate(sorted(out.glob("__dz-*.jpg"))):
            new = out / f"d-{idx:03d}.jpg"
            t.rename(new)
            pairs.append((new, round(s + j / fps, 2)))
            idx += 1
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


def write_dense(out, pairs, segments):
    """二次细看密帧的音画对齐 → dense.md。"""
    lines = ["# 密帧二次细看(自适应抽帧)\n",
             "对粗览标记的'有戏/看不懂'时间段密集抽帧;每帧标注该时刻口播。agent 请配合实际 Read 图片看。\n",
             "| 时间 | 密帧 | 此刻口播 |", "|---|---|---|"]
    for k, t in pairs:
        spoken = spoken_at(t, segments).replace("|", "/").replace("\n", " ")
        lines.append(f"| {fmt_ts(t)} | {k.name} | {spoken} |")
    (out / "dense.md").write_text("\n".join(lines), encoding="utf-8")


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
    ap.add_argument("--densify", help="二次细看:只对这些时间段密集抽帧,如 '65-80,120-135'(秒);跳过音轨/whisper")
    ap.add_argument("--densify-fps", type=float, default=5.0, help="densify 抽帧频率(帧/秒,默认 5)")
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

    # 二次细看(B):只对指定时间段密抽,复用已有 whisper 分段做对齐,然后退出
    if a.densify:
        ranges = []
        for part in a.densify.split(","):
            part = part.strip()
            if part:
                s, e = part.split("-")
                ranges.append((float(s), float(e)))
        dpairs = densify(mp4, out, ranges, a.densify_fps)
        segs = []
        wj0 = out / "audio.json"
        if wj0.exists():
            data = json.loads(wj0.read_text(errors="ignore"))
            segs = [{"start": s.get("start"), "end": s.get("end"), "text": s.get("text", "")}
                    for s in data.get("segments", [])]
        write_dense(out, dpairs, segs)
        print(f"[densify] 密帧 {len(dpairs)} 张(段: {a.densify})-> {out}/dense.md")
        return

    wav = out / "audio.wav"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(mp4),
         "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
    print(f"[2/4] 音轨: {wav}")

    # 关键帧抽取做成非致命:即便 ffmpeg 抽帧整体失败,也不能连累后面的 whisper 逐字稿
    try:
        pairs = extract_keyframes(mp4, out, a.frames, a.scene)
        print(f"[3/4] 关键帧: {len(pairs)} 张(带时间戳)")
    except Exception as e:
        pairs = []
        print(f"[3/4] 关键帧抽取失败(已跳过,不影响逐字稿): {e}")

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
