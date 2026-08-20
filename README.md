# Clipped Bookmarks Master

> Turn your scattered "likes" and "bookmarks" from Chinese social platforms into clean, searchable Markdown notes.

## Overview

**Clipped Bookmarks Master** is a CodeBuddy Skill that fetches content from your saved/liked posts across **Zhihu, Xiaohongshu (RED), Bilibili, WeChat Video Channels, and WeChat Official Accounts**, cleans them up, and outputs structured Markdown notes.

| Content Type | Platforms | What It Does |
|-------------|-----------|--------------|
| **Text** | Zhihu (Q&A, articles), WeChat Official Accounts | Fetches body text → strips ads/noise → keeps core arguments + top-voted comments |
| **Video** | Xiaohongshu, Bilibili, WeChat Video Channels | Downloads video → extracts audio → transcribes with timestamps → AI-summarizes into structured notes (key points / steps / checklists) |

## Supported Platforms

| Platform | Type | Notes |
|----------|------|-------|
| [Zhihu](https://www.zhihu.com) | Text | Q&A answers, articles. Supports multi-answer pages. |
| [Xiaohongshu](https://www.xiaohongshu.com) | Video / Image-Text | Video notes go through transcription pipeline. Image-text notes use OCR + body text. |
| [Bilibili](https://www.bilibili.com) | Video | **Timestamps preserved** for key-frame jumping. Can also fetch video description and top danmu/comments. |
| WeChat Video Channels | Video | No official download API — user uploads the video file directly. |
| WeChat Official Accounts | Text | Strips QR-code promotions and "read more" blocks. |

## Directory Structure

```
clipped-bookmarks-master/
├── SKILL.md                    # Skill definition (trigger rules, flow, examples)
├── README.md                   # This file
├── scripts/
│   ├── install_deps.sh         # Install yt-dlp, whisper, ffmpeg, Python deps
│   ├── fetch_text.py           # Fetch & extract text content (Zhihu / WeChat OA)
│   ├── download_media.sh       # Download video/audio (yt-dlp)
│   ├── extract_audio.sh        # Video → 16k mono MP3 (ffmpeg)
│   ├── transcribe.sh           # Audio → timestamped transcript (OpenAI API or local whisper)
│   └── batch_process.sh        # Batch-process a list of URLs
└── references/
    ├── templates.md            # Markdown output templates (text & video)
    └── field_spec.md           # Per-platform field specs & cleaning rules
```

## Quick Start

### 1. Install Dependencies

```bash
bash scripts/install_deps.sh
```

This installs:
- `yt-dlp` — video/audio downloader
- `requests`, `beautifulsoup4`, `trafilatura` — Python scraping stack
- Optional: `openai-whisper` — local speech-to-text (heavy; skip if using OpenAI API)

Make sure `ffmpeg` is available:
```bash
# Ubuntu/Debian
sudo apt-get install -y ffmpeg
```

### 2. Process a Zhihu Answer (Text)

```bash
# Fetch raw content
python3 scripts/fetch_text.py "https://www.zhihu.com/question/633780178/answer/1997868452766058023" \
  --out raw.json

# The Agent then cleans ads/noise and produces a Markdown note
# from the raw JSON using references/templates.md
```

### 3. Process a Bilibili Video (Video)

```bash
# Download
bash scripts/download_media.sh "https://www.bilibili.com/video/BV1xx411c7mD" \
  --dir ./downloads

# Extract audio
bash scripts/extract_audio.sh downloads/some_video.mp4

# Transcribe (OpenAI Whisper API — requires OPENAI_API_KEY)
export OPENAI_API_KEY="sk-..."
bash scripts/transcribe.sh downloads/some_video.mp3 --api openai

# The Agent then summarizes the transcript into a structured Markdown note
# with [MM:SS] timestamps for key moments
```

### 4. Batch Process a Collection

Create `links.txt` (one URL per line):

```
https://www.zhihu.com/question/633780178/answer/1997868452766058023
https://www.bilibili.com/video/BV1xx411c7mD
https://mp.weixin.qq.com/s/xxxxxxxx
```

Run:

```bash
bash scripts/batch_process.sh links.txt --out ./bookmarks_notes
```

The script auto-detects each platform and routes to the appropriate pipeline.

## Output Templates

### Text Note (Zhihu / WeChat OA)

```markdown
# {Title}

> Source: {Platform} · {Author} · {Date}
> Original: {URL}

## Core Arguments
- {Main point 1}
- {Main point 2}

### {Sub-topic A}
{Elaboration with `>` blockquotes for key original sentences}

## Top-Voted Comments
> **@{Nickname}** ({upvotes} upvotes): {Core insight}

## Tags
#bookmarks #{platform} #{topic}
```

### Video Note (Bilibili / Xiaohongshu / Video Channels)

```markdown
# {Video Title}

> Source: {Platform} · Creator: {Author} · Duration: {MM:SS}
> Original: {URL}

## Key Points
- {Core conclusion 1}
- {Key data / quote}

## Steps
1. {Step 1}
2. {Step 2}

## Checklist
- [ ] {Action item 1}
- [ ] {Action item 2}

## Key Timestamps
- [00:45] {What happens here}
- [03:12] {What happens here}
- [08:30] {What happens here}

## Tags
#bookmarks #{platform} #{topic}
```

> **Note:** Bilibili and WeChat Video Channels **must** include the "Key Timestamps" section for easy key-frame jumping.

## Environment Variables

| Variable | Required For | Description |
|----------|-------------|-------------|
| `OPENAI_API_KEY` | `--api openai` transcription | OpenAI API key for Whisper transcription |

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `fetch_text.py` returns empty | Anti-bot / login wall | Add `--cookies cookies.txt` with logged-in cookies, or paste content manually |
| `download_media.sh` fails | Platform restriction / geo-block | Try `--cookies-from-browser chrome` for Bilibili; for Video Channels, upload the file directly |
| `transcribe.sh` errors | Missing ASR deps / no API key | Run `install_deps.sh` or set `OPENAI_API_KEY` |
| Content behind paywall | — | Stop and inform user; **never fabricate content** |

## Safety & Compliance

- **No fabrication**: If anti-bot or login walls block access, the script returns empty data and the Agent informs the user — never makes up content.
- **Personal use only**: Downloaded media is for personal note-taking only; do not redistribute.
- **Respect platform TOS**: Do not scrape paywalled or explicitly forbidden content.

## License

MIT

## Contributing

This is a CodeBuddy Skill. To use it in your own CodeBuddy workspace, copy the `clipped-bookmarks-master/` directory into your project's `.codebuddy/skills/` folder.

---

*Built with CodeBuddy · Made for obsessive bookmark hoarders who actually want to read their saves.*
