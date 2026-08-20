#!/usr/bin/env bash
# batch_process.sh - 收藏夹整理师 · 批量整理链接
# 读取 links.txt（每行一个链接），自动识别平台与类型，逐个整理为 Markdown 笔记。
# 支持：小红书、微信视频号文件/短视频、微信公众号、知乎。
# 明确不支持：B站 / b23.tv。
# 用法: bash scripts/batch_process.sh links.txt [--out ./bookmarks_notes] [--cookies cookies.txt]
set -euo pipefail

LINKS=""
OUT="./bookmarks_notes"
COOKIES=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT="$2"; shift 2;;
    --cookies) COOKIES="$2"; shift 2;;
    -*) echo "未知参数: $1"; exit 1;;
    *) LINKS="$1"; shift;;
  esac
done

if [[ -z "$LINKS" || ! -f "$LINKS" ]]; then
  echo "用法: bash batch_process.sh links.txt [--out ./bookmarks_notes]"
  exit 1
fi

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$OUT"/zhihu "$OUT"/weixin "$OUT"/xiaohongshu "$OUT"/videochannel

count=0
while IFS= read -r line; do
  url="$(echo "$line" | xargs)"
  [[ -z "$url" || "$url" == \#* ]] && continue
  count=$((count+1))
  echo "=========================================="
  echo "[$count] 处理: $url"

  if [[ "$url" == *"bilibili.com"* || "$url" == *"b23.tv"* ]]; then
    echo "    [不支持] B站 / b23.tv 已从本 Skill 移除，请不要绕过 router。"
  elif [[ "$url" == *"zhihu.com"* || "$url" == *"mp.weixin.qq.com"* ]]; then
    # 文字类：知乎 / 微信公众号
    plat=$( [[ "$url" == *"zhihu"* ]] && echo zhihu || echo weixin )
    raw="$OUT/$plat/_raw_$count.json"
    if [[ -n "$COOKIES" ]]; then
      python3 "$SKILL_DIR/fetch_text.py" "$url" --out "$raw" --cookies "$COOKIES"
    else
      python3 "$SKILL_DIR/fetch_text.py" "$url" --out "$raw"
    fi
    echo "    [文字类] 已抓取原始内容 -> $raw （交由 Agent 提炼为 Markdown）"
  elif [[ "$url" == *"xiaohongshu.com"* || "$url" == *"xhslink.cn"* || "$url" == *"xhslink.com"* ]]; then
    bash "$SKILL_DIR/download_media.sh" "$url" --dir "$OUT/xiaohongshu"
    echo "    [小红书] 已处理媒体/链接。图文笔记可继续 OCR + 正文提炼；视频笔记继续转写。"
  elif [[ "$url" == *"finder.video.qq.com"* || "$url" == *"channels.weixin.qq.com"* || "$url" == *"weixin.qq.com"*"finder"* ]]; then
    bash "$SKILL_DIR/download_media.sh" "$url" --dir "$OUT/videochannel"
    echo "    [微信视频号] 请用用户上传文件或已下载文件继续转写提炼。"
  elif [[ "$url" == *.mp4 || "$url" == *.mov || "$url" == *.m4v || "$url" == *.webm || "$url" == *.mkv ]]; then
    echo "    [微信视频号文件] 本地/上传视频文件，请用 extract_audio.sh + transcribe.sh 完成转写后提炼。"
  else
    echo "    [跳过] 不支持的平台链接"
  fi
done < "$LINKS"

echo "=========================================="
echo "[完成] 共处理 $count 条链接。原始数据在 $OUT，待 Agent 提炼为标准 Markdown 笔记。"
