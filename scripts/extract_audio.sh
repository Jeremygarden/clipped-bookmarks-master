#!/usr/bin/env bash
# extract_audio.sh - 收藏夹整理师 · 视频 → 音频
# 用 ffmpeg 把视频分离为 16k 单声道 mp3（适合语音识别）。
# 用法: bash scripts/extract_audio.sh <video_file> [--out audio.mp3]
set -euo pipefail

IN=""
OUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT="$2"; shift 2;;
    -*) echo "未知参数: $1"; exit 1;;
    *) IN="$1"; shift;;
  esac
done

if [[ -z "$IN" ]]; then
  echo "用法: bash extract_audio.sh <video_file> [--out audio.mp3]"
  exit 1
fi
if [[ ! -f "$IN" ]]; then
  echo "[错误] 文件不存在: $IN"
  exit 1
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "[错误] 未检测到 ffmpeg，请安装: apt-get install -y ffmpeg"
  exit 2
fi

if [[ -z "$OUT" ]]; then
  OUT="${IN%.*}.mp3"
fi

echo "==> 提取音频(16k 单声道): $IN -> $OUT"
ffmpeg -y -i "$IN" -vn -ac 1 -ar 16000 -b:a 64k "$OUT" 2>/dev/null
echo "[ok] 音频已生成: $OUT"
