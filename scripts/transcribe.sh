#!/usr/bin/env bash
# transcribe.sh - 收藏夹整理师 · 音频 → 逐字稿(带时间戳)
# 支持两种引擎:
#   --api openai : 调用 OpenAI Whisper API (需 export OPENAI_API_KEY=...)
#   --api local  : 本地 openai-whisper (需先 pip install openai-whisper)
# 用法: bash scripts/transcribe.sh <audio_file> [--api openai|local] [--out transcript.txt] [--lang zh]
set -euo pipefail

IN=""
API="openai"
OUT=""
LANG="zh"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --api) API="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    --lang) LANG="$2"; shift 2;;
    -*) echo "未知参数: $1"; exit 1;;
    *) IN="$1"; shift;;
  esac
done

if [[ -z "$IN" ]]; then
  echo "用法: bash transcribe.sh <audio_file> [--api openai|local] [--out transcript.txt]"
  exit 1
fi
if [[ ! -f "$IN" ]]; then echo "[错误] 文件不存在: $IN"; exit 1; fi
if [[ -z "$OUT" ]]; then OUT="${IN%.*}.transcript.txt"; fi

if [[ "$API" == "openai" ]]; then
  if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "[错误] 未设置 OPENAI_API_KEY。请先: export OPENAI_API_KEY=sk-..."
    exit 2
  fi
  echo "==> 调用 OpenAI Whisper API 转写: $IN"
  python3 - "$IN" "$OUT" "$LANG" <<'PY'
import sys, os, json, urllib.request
audio, out, lang = sys.argv[1], sys.argv[2], sys.argv[3]
api_key = os.environ["OPENAI_API_KEY"]
url = "https://api.openai.com/v1/audio/transcriptions"
import urllib.request as ur
boundary = "----cbmdboundary"
data = []
data.append(f"--{boundary}".encode())
data.append(f'Content-Disposition: form-data; name="model"\r\n\r\nwhisper-1'.encode())
data.append(f"--{boundary}".encode())
data.append(f'Content-Disposition: form-data; name="language"\r\n\r\n{lang}'.encode())
data.append(f"--{boundary}".encode())
data.append(f'Content-Disposition: form-data; name="response_format"\r\n\r\nverbose_json'.encode())
data.append(f"--{boundary}".encode())
data.append(f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(audio)}"'.encode())
data.append(b"Content-Type: audio/mpeg\r\n\r\n")
with open(audio, "rb") as f:
    data.append(f.read())
data.append(f"\r\n--{boundary}--\r\n".encode())
body = b"\r\n".join(data)
req = ur.Request(url, data=body, method="POST")
req.add_header("Authorization", f"Bearer {api_key}")
req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
try:
    with ur.urlopen(req, timeout=600) as r:
        resp = json.loads(r.read().decode())
    segs = resp.get("segments", [])
    lines = []
    for s in segs:
        start = int(s["start"])
        mm, ss = divmod(start, 60)
        hh, mm = divmod(mm, 60)
        ts = f"[{hh:02d}:{mm:02d}:{ss:02d}]" if hh else f"[{mm:02d}:{ss:02d}]"
        lines.append(f"{ts} {s['text'].strip()}")
    text = "\n".join(lines) if lines else resp.get("text", "")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"[ok] 逐字稿(带时间戳)已写入: {out}")
except Exception as e:
    print(f"[错误] 转写失败: {e}")
    sys.exit(3)
PY

elif [[ "$API" == "local" ]]; then
  if ! python3 -c "import whisper" 2>/dev/null; then
    echo "[错误] 本地未安装 openai-whisper，请运行: bash scripts/install_deps.sh 并选择安装"
    exit 2
  fi
  echo "==> 本地 whisper 转写: $IN"
  python3 - "$IN" "$OUT" "$LANG" <<'PY'
import sys, datetime
audio, out, lang = sys.argv[1], sys.argv[2], sys.argv[3]
import whisper
model = whisper.load_model("base")
res = model.transcribe(audio, language=lang, verbose=False)
lines = []
for s in res.get("segments", []):
    start = int(s["start"]); mm, ss = divmod(start, 60); hh, mm = divmod(mm, 60)
    ts = f"[{hh:02d}:{mm:02d}:{ss:02d}]" if hh else f"[{mm:02d}:{ss:02d}]"
    lines.append(f"{ts} {s['text'].strip()}")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"[ok] 逐字稿(带时间戳)已写入: {out}")
PY
else
  echo "[错误] 未知引擎: $API (可选 openai|local)"
  exit 1
fi
