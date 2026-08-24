#!/usr/bin/env bash
# 安装收藏夹整理师所需的依赖：yt-dlp（当前支持媒体源下载）、语音识别相关
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-${REPO_ROOT}/requirements.txt}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PIP_ARGS=()
INSTALL_WHISPER="${INSTALL_WHISPER:-0}"
INTERACTIVE=1
if [[ "${CI:-}" == "true" || "${CI:-}" == "1" ]]; then
  INTERACTIVE=0
fi

usage() {
  cat <<'EOF'
Usage: bash scripts/install_deps.sh [--non-interactive] [--with-whisper] [--user]

Installs Python dependencies from requirements.txt without falling back to sudo.
By default it installs into the active virtualenv, or uses pip --user when no
virtualenv is active. Set CI=true or pass --yes/--non-interactive to skip prompts.

Options:
  --non-interactive  Do not prompt; skip optional whisper unless --with-whisper is set
  --with-whisper     Also install openai-whisper for local transcription
  --user             Pass --user to pip (default outside a virtualenv)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --non-interactive|-y|--yes)
      INTERACTIVE=0
      shift
      ;;
    --with-whisper)
      INSTALL_WHISPER=1
      shift
      ;;
    --user)
      PIP_ARGS+=(--user)
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[错误] 未知参数: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

echo "==> 安装收藏夹整理师依赖..."

if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
  echo "[错误] 找不到依赖文件: $REQUIREMENTS_FILE" >&2
  exit 2
fi

if [[ "${#PIP_ARGS[@]}" -eq 0 && -z "${VIRTUAL_ENV:-}" ]]; then
  PIP_ARGS+=(--user)
  echo "[i] 未检测到虚拟环境，使用: $PYTHON_BIN -m pip install --user"
  echo "[i] 如需隔离依赖，可先运行: python3 -m venv .venv && source .venv/bin/activate"
fi

"$PYTHON_BIN" -m pip install -U "${PIP_ARGS[@]}" -r "$REQUIREMENTS_FILE"

if [[ "$INSTALL_WHISPER" != "1" && "$INTERACTIVE" == "1" ]]; then
  echo "[?] 本地语音识别(openai-whisper) 体积较大，是否安装？[y/N]"
  read -r REPLY
  if [[ "$REPLY" =~ ^[Yy]$ ]]; then
    INSTALL_WHISPER=1
  fi
fi

if [[ "$INSTALL_WHISPER" == "1" ]]; then
  "$PYTHON_BIN" -m pip install -U "${PIP_ARGS[@]}" openai-whisper
  echo "[ok] openai-whisper 已安装（local 模式可用）"
else
  echo "[i] 跳过 whisper。视频转写请使用 --api openai（需配置 OPENAI_API_KEY）。"
fi

# 4. ffmpeg 检查
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "[!] 未检测到 ffmpeg，音频分离需要它。请安装 ffmpeg（例如 apt-get install -y ffmpeg）。"
else
  echo "[ok] ffmpeg 已就绪"
fi

echo "==> 依赖安装完成。"
echo "    视频转写: bash scripts/transcribe.sh <audio> --api openai   (需 export OPENAI_API_KEY=...)"
echo "    本地转写: bash scripts/transcribe.sh <audio> --api local    (需先安装 openai-whisper)"
