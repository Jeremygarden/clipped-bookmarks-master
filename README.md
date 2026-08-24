# Clipped Bookmarks Master

> Turn your scattered "likes" and "bookmarks" from Chinese social platforms into clean, searchable Markdown notes.

## Overview

**Clipped Bookmarks Master** is a CodeBuddy Skill that routes and renders saved/liked posts across the current core scope: **WeChat Official Accounts, Xiaohongshu (RED), Xiaohongshu collections, WeChat Video Channels files/videos, and Zhihu**, cleans them up, and outputs structured Markdown notes.

| Content Type | Platforms | What It Does |
|-------------|-----------|--------------|
| **Text** | WeChat Official Accounts, Zhihu | Fetches body text → strips ads/noise → keeps core arguments |
| **Image/Text/Video** | Xiaohongshu notes, Xiaohongshu collections | Routes note/collection URLs into the shared `BookmarkItem` schema for extractor/rendering stages |
| **Video** | WeChat Video Channels files/videos | User-provided file or supported video source → transcription pipeline → structured notes |

## Supported Platforms

| Platform / Source | Type | Core Status | Notes |
|-------------------|------|-------------|-------|
| WeChat Official Accounts (`mp.weixin.qq.com/s/...`) | Text | Supported | Routes as `wechat_article`; strips QR-code promotions and "read more" blocks in extractor stages. |
| [Xiaohongshu](https://www.xiaohongshu.com) notes / `xhslink.cn` / `xhslink.com` | Image/Text/Video | Supported | Routes as `xiaohongshu_note`; short links are marked `requires_expansion`. |
| Xiaohongshu collection item URLs | Collection | Supported | Routes as `xiaohongshu_collection`. |
| WeChat Video Channels | File / Video | Supported | User-provided video files route as `wechat_channels_file`; channel video URLs route as `wechat_channels_video`. |
| Zhihu (`zhihu.com/question/.../answer/...`, `zhuanlan.zhihu.com/p/...`) | Text | Supported | Routes as `zhihu_answer` or `zhihu_article`; extraction remains platform-agent work. |
| Bilibili / `b23.tv` | Video | Unsupported in current core scope | Router raises `UnsupportedPlatformError`; Bilibili is not part of the supported core. |


## Core Architecture

The P0 core adds a standard middle layer that platform extractors and renderers share. The active supported platforms are Xiaohongshu, WeChat Video Channels files/videos, WeChat Official Accounts, and Zhihu; Bilibili is intentionally unsupported.

- `clipped_bookmarks.schema.BookmarkItem` — unified schema for `url`, `platform`, `source_type`, `title`, `author`, `published_at`, `content`, `summary`, `tags`, `assets`, `metadata`, `status`, and `errors`.
- `clipped_bookmarks.router.route_url(source)` — detects supported URLs/files and rejects unsupported platforms such as Bilibili with `UnsupportedPlatformError`.
- `clipped_bookmarks.renderers.markdown.render_markdown(item)` — renders Markdown with YAML frontmatter for downstream note systems.
- `clipped_bookmarks.renderers.obsidian` — Obsidian export skeleton using `ObsidianExportConfig`; writing to a vault requires explicit `confirm=True`.
- `clipped_bookmarks.cli` — minimal CLI for route → Markdown output and optional confirmed Obsidian export.
- `references/core_handoff.md` — concise contract for platform-agent handoff boundaries and the active platform scope.

Example:

```bash
python3 -m clipped_bookmarks.cli "https://mp.weixin.qq.com/s/ENwXC3hEbXnq-5hGEE6keA" --out note.md
python3 -m clipped_bookmarks.cli "https://xhslink.cn/o/2HSnq3KBHMZ"
python3 -m clipped_bookmarks.cli "https://www.zhihu.com/question/123456/answer/789012"
python3 -m clipped_bookmarks.cli ./wechat-channel-video.mp4 --obsidian-vault ~/Vault --confirm-obsidian
```

## Directory Structure

```
clipped-bookmarks-master/
├── SKILL.md                    # Skill definition (trigger rules, flow, examples)
├── README.md                   # This file
├── scripts/
│   ├── install_deps.sh         # Install yt-dlp, whisper, ffmpeg, Python deps
│   ├── fetch_text.py           # Fetch & extract text content (WeChat OA)
│   ├── download_media.sh       # Download video/audio (yt-dlp)
│   ├── extract_audio.sh        # Video → 16k mono MP3 (ffmpeg)
│   ├── transcribe.sh           # Audio → timestamped transcript (OpenAI API or local whisper)
│   └── batch_process.sh        # Batch-process a list of URLs
└── references/
    ├── core_handoff.md         # Core/platform-agent boundary and active scope
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

### 2. Process a WeChat Official Account Article (Text)

```bash
# Fetch raw content
python3 scripts/fetch_text.py "https://mp.weixin.qq.com/s/ENwXC3hEbXnq-5hGEE6keA" \
  --out raw.json

# The Agent then cleans ads/noise and produces a Markdown note
# from the raw JSON using references/templates.md
```

### 3. Process a WeChat Channels Video File (Video)

```bash
# Download
python3 -m clipped_bookmarks.cli ./wechat-channel-video.mp4 --out routed.md

# Then process the uploaded file

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
https://mp.weixin.qq.com/s/ENwXC3hEbXnq-5hGEE6keA
https://xhslink.cn/o/2HSnq3KBHMZ
https://xhslink.com/a/abc123
https://www.xiaohongshu.com/collection/item/68930d3b02f5000000000001
```

Run:

```bash
bash scripts/batch_process.sh links.txt --out ./bookmarks_notes
```

The script auto-detects each platform and routes to the appropriate pipeline.

## Output Templates

### Text Note (WeChat OA)

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

### Video Note (Xiaohongshu / Video Channels)

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

> **Note:** WeChat Video Channels notes should include the "Key Timestamps" section when transcripts include timing data. Bilibili is unsupported in the current core scope.

## Environment Variables

| Variable | Required For | Description |
|----------|-------------|-------------|
| `OPENAI_API_KEY` | `--api openai` transcription | OpenAI API key for Whisper transcription |

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `fetch_text.py` returns empty | Anti-bot / login wall | Add `--cookies cookies.txt` with logged-in cookies, or paste content manually |
| `download_media.sh` fails | Platform restriction / geo-block | For Video Channels, upload the file directly; Bilibili is unsupported in the current core scope |
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
