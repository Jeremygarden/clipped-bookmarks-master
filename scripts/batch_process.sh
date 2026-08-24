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
mkdir -p "$OUT"/zhihu "$OUT"/weixin "$OUT"/xiaohongshu "$OUT"/wechat_channels

count=0
while IFS= read -r line; do
  url="$(echo "$line" | xargs)"
  [[ -z "$url" || "$url" == \#* ]] && continue
  count=$((count+1))
  echo "=========================================="
  echo "[$count] 处理: $url"

  if ! route_json=$(python3 -m clipped_bookmarks.cli "$url" 2>/tmp/cbm_batch_route_error.$$); then
    echo "    [跳过] 不支持的平台链接: $(cat /tmp/cbm_batch_route_error.$$)"
    rm -f /tmp/cbm_batch_route_error.$$
    continue
  fi
  rm -f /tmp/cbm_batch_route_error.$$

  source_type=$(python3 -c 'import re,sys; text=sys.stdin.read(); m=re.search(r"^source_type: \"([^\"]+)\"", text, re.M); print(m.group(1) if m else "")' <<<"$route_json")
  platform=$(python3 -c 'import re,sys; text=sys.stdin.read(); m=re.search(r"^platform: \"([^\"]+)\"", text, re.M); print(m.group(1) if m else "")' <<<"$route_json")

  if [[ "$source_type" == "zhihu_answer" || "$source_type" == "zhihu_article" || "$source_type" == "wechat_article" ]]; then
    plat=$( [[ "$platform" == "zhihu" ]] && echo zhihu || echo weixin )
    raw="$OUT/$plat/_raw_$count.json"
    if [[ -n "$COOKIES" ]]; then
      python3 "$SKILL_DIR/fetch_text.py" "$url" --out "$raw" --cookies "$COOKIES"
    else
      python3 "$SKILL_DIR/fetch_text.py" "$url" --out "$raw"
    fi
    echo "    [文字类] 已抓取原始内容 -> $raw （交由 Agent 提炼为 Markdown）"
  elif [[ "$source_type" == "xiaohongshu_note" || "$source_type" == "xiaohongshu_collection" ]]; then
    bash "$SKILL_DIR/download_media.sh" "$url" --dir "$OUT/xiaohongshu"
    echo "    [小红书] 已下载/路由。请按平台 extractor/OCR/转写流程提炼。"
  elif [[ "$source_type" == "wechat_channels_file" || "$source_type" == "wechat_channels_video" ]]; then
    echo "$route_json" > "$OUT/wechat_channels/_routed_$count.md"
    echo "    [视频号] 已路由 -> $OUT/wechat_channels/_routed_$count.md。视频号链接不下载；请使用用户上传/导出的视频、音频或转写文件继续。"
  else
    echo "    [跳过] 不支持的平台链接"
  fi
done < "$LINKS"

echo "=========================================="
echo "[完成] 共处理 $count 条链接。原始数据在 $OUT，待 Agent 提炼为标准 Markdown 笔记。"
