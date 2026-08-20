#!/usr/bin/env bash
# download_media.sh - 收藏夹整理师 · 视频/音频下载
# 自动选择下载方式：小红书优先专用 extractor，其他公开视频尝试 yt-dlp。B站 / b23.tv 明确不支持。
# 用法: bash scripts/download_media.sh <url> [--dir ./downloads]
set -euo pipefail

URL=""
DIR="./downloads"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) DIR="$2"; shift 2;;
    -*) echo "未知参数: $1"; exit 1;;
    *) URL="$1"; shift;;
  esac
done

if [[ -z "$URL" ]]; then
  echo "用法: bash download_media.sh <url> [--dir ./downloads]"
  exit 1
fi

mkdir -p "$DIR"

if [[ "$URL" == *"bilibili.com"* || "$URL" == *"b23.tv"* ]]; then
  echo "[错误] B站 / b23.tv 已从本 Skill 移除，不支持下载或转写。"
  exit 4
fi

if [[ "$URL" == *"xiaohongshu.com"* || "$URL" == *"xhslink.cn"* || "$URL" == *"xhslink.com"* ]]; then
  echo "==> 处理小红书媒体: $URL"
  python3 "$PWD/scripts/xhs_download_media.py" "$URL" --out "$DIR"
  exit $?
fi

# 微信视频号无公开下载 API：提示用户上传文件
if [[ "$URL" == *"finder.video.qq.com"* || "$URL" == *"weixin.qq.com"*"finder"* ]]; then
  echo "[提示] 微信视频号无官方下载接口。"
  echo "       请将视频文件直接发送给我（Agent），我会用 extract_audio.sh + transcribe.sh 处理。"
  echo "       若你已有本地视频文件，可直接: bash extract_audio.sh <你的视频文件>"
  exit 0
fi

if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "[错误] 未找到 yt-dlp，请先运行: bash scripts/install_deps.sh"
  exit 2
fi

echo "==> 下载媒体: $URL"
# 优先下载 bestvideo+bestaudio 合并 mp4；无合并能力则退回 best
yt-dlp -f "bv*+ba/best" --merge-output-format mp4 \
  -o "$DIR/%(title)s.%(ext)s" \
  --no-playlist \
  --restrict-filenames \
  "$URL" || {
  echo "[!] 下载失败。可能原因：登录限制 / 地区限制 / 链接失效。"
  echo "    微信视频号建议直接上传视频文件；小红书可尝试登录态 Playwright / cookies 流程。"
  exit 3
}

echo "[ok] 下载完成，文件在 $DIR"
