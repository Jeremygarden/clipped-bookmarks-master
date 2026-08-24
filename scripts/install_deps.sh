#!/usr/bin/env bash
# 安装收藏夹整理师所需的依赖：yt-dlp（当前支持媒体源下载）、语音识别相关
set -euo pipefail

echo "==> 安装收藏夹整理师依赖..."

# 1. yt-dlp（视频/音频下载，用于小红书等当前支持媒体源）
if command -v yt-dlp >/dev/null 2>&1; then
  echo "[ok] yt-dlp 已存在，尝试升级"
  pip3 install -U yt-dlp >/dev/null 2>&1 || sudo pip3 install -U yt-dlp >/dev/null 2>&1 || true
else
  echo "[+] 安装 yt-dlp"
  pip3 install -U yt-dlp >/dev/null 2>&1 || sudo pip3 install -U yt-dlp
fi

# 2. Python 抓取/解析依赖
echo "[+] 安装 Python 依赖 (requests, beautifulsoup4, trafilatura)"
pip3 install -U requests beautifulsoup4 trafilatura >/dev/null 2>&1 \
  || sudo pip3 install -U requests beautifulsoup4 trafilatura

# 3. 语音识别（可选，local 模式需要）。默认不强制安装（体积大），按需提示。
echo "[?] 本地语音识别(whisper) 体积较大，是否安装？[y/N]"
read -r REPLY
if [[ "$REPLY" =~ ^[Yy]$ ]]; then
  pip3 install -U openai-whisper >/dev/null 2>&1 || sudo pip3 install -U openai-whisper
  echo "[ok] openai-whisper 已安装（local 模式可用）"
else
  echo "[i] 跳过 whisper。视频转写请使用 --api openai（需配置 OPENAI_API_KEY）。"
fi

# 4. ffmpeg 检查
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "[!] 未检测到 ffmpeg，音频分离需要它。请运行: apt-get install -y ffmpeg"
else
  echo "[ok] ffmpeg 已就绪"
fi

echo "==> 依赖安装完成。"
echo "    视频转写: bash scripts/transcribe.sh <audio> --api openai   (需 export OPENAI_API_KEY=...)"
echo "    本地转写: bash scripts/transcribe.sh <audio> --api local    (需先安装 openai-whisper)"
