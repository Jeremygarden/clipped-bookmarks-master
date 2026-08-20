#!/usr/bin/env bash
# batch_process.sh - 收藏夹整理师 · 批量整理链接
# 读取 links.txt（每行一个链接），自动识别平台与类型，逐个整理为 Markdown 笔记。
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

  if [[ "$url" == *"zhihu.com"* || "$url" == *"mp.weixin.qq.com"* ]]; then
    # 文字类
    plat=$( [[ "$url" == *"zhihu"* ]] && echo zhihu || echo weixin )
    raw="$OUT/$plat/_raw_$count.json"
    if [[ -n "$COOKIES" ]]; then
      python3 "$SKILL_DIR/fetch_text.py" "$url" --out "$raw" --cookies "$COOKIES"
    else
      python3 "$SKILL_DIR/fetch_text.py" "$url" --out "$raw"
    fi
    echo "    [文字类] 已抓取原始内容 -> $raw （交由 Agent 提炼为 Markdown）"
  elif [[ "$url" == *"xiaohongshu.com"* || "$url" == *"xhslink.com"* ]]; then
    plat=xiaohongshu
    bash "$SKILL_DIR/download_media.sh" "$url" --dir "$OUT/$plat"
    echo "    [视频类] 已下载。请用 extract_audio.sh + transcribe.sh 完成转写后提炼。"
  else
    echo "    [跳过] 不支持的平台链接"
  fi
done < "$LINKS"

echo "=========================================="
echo "[完成] 共处理 $count 条链接。原始数据在 $OUT，待 Agent 提炼为标准 Markdown 笔记。"
