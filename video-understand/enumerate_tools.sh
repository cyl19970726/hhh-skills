#!/usr/bin/env bash
# enumerate_tools.sh — 枚举一条视频里用到的「所有软件」(工具清单模式)
#
# 为什么单独一个模式:理解视频的稀疏关键帧(场景切变,十来张)对"列全软件"是错的——
# 软件出现在静态/过渡帧、窗口标题/菜单是小字,稀疏帧+缩放640会漏。本模式专门:
#   1. 全片【密集】抽帧(每 1-2 秒一张)
#   2. 【原生分辨率】不缩放(窗口标题/菜单这种小字才认得出)
#   3. 逐帧 Vision OCR(ocr.swift,中英) 抓屏上文字/软件名
#   4. 再让 agent/Workflow 逐帧【视觉】识别(OCR 抓不全桌面软件的窗口 chrome)
#
# 用法: enumerate_tools.sh <video.mp4|或已下好的 clip.mp4> [out_dir] [fps]
#   fps 默认 1/2(每2秒一帧);要更密用 1(每秒一帧)。
# 产出: <out>/d-*.jpg(密集帧) + <out>/ocr.txt(逐帧OCR)
# 之后(关键): 把 d-*.jpg 分批交给 agent 逐帧 Read 识别软件 → 合并去重(见 SKILL.md)。
set -euo pipefail
VIDEO="${1:?用法: enumerate_tools.sh <video.mp4> [out_dir] [fps]}"
OUT="${2:-/tmp/vu_tools}"
FPS="${3:-1/2}"
HERE="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$OUT"
rm -f "$OUT"/d-*.jpg
# 原生分辨率,不加 scale —— 缩放会糊掉窗口标题/菜单这类小字
ffmpeg -y -v error -i "$VIDEO" -vf "fps=$FPS" "$OUT/d-%03d.jpg"
N=$(ls "$OUT"/d-*.jpg | wc -l | tr -d ' ')
echo "[1/2] 密集帧: $N 张 (fps=$FPS, 原生分辨率) -> $OUT"

if command -v swift >/dev/null 2>&1; then
  swift "$HERE/ocr.swift" "$OUT"/d-*.jpg > "$OUT/ocr.txt" 2>/dev/null
  echo "[2/2] 逐帧 OCR -> $OUT/ocr.txt ($(grep -c '^=== ' "$OUT/ocr.txt") 帧)"
else
  echo "[2/2] 跳过 OCR(无 swift/macOS Vision);仅密集帧"
fi

cat <<EOF

== 下一步(必须): 逐帧视觉枚举软件 ==
OCR 抓得到面板文字,但桌面软件的【窗口标题/菜单栏】是小字常漏 —— 必须再做一遍视觉:
让 agent/Workflow 分批 Read $OUT/d-*.jpg,对每帧判定"哪个软件的UI"(看窗口标题栏/菜单/
面板布局/时间线样式),桌面 DCC 要判定具体是 Blender/Maya/C4D/3ds Max/Houdini/ZBrush 哪个,
最后【合并去重】出全部软件。模板与 Workflow 写法见 SKILL.md「枚举所有软件」节。
EOF
