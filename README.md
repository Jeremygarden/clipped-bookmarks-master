# Clipped Bookmarks Master

> Turn scattered saved/liked content from Chinese social platforms into clean, searchable Markdown notes.

## Overview

**Clipped Bookmarks Master** is a CodeBuddy Skill with a unified core architecture for routing, extraction handoff, and Markdown rendering across the real supported scope: **WeChat Official Accounts, Zhihu, Xiaohongshu (RED), Xiaohongshu collections, and WeChat Video Channels files/videos**.

| Content Type | Platforms | What It Does |
|-------------|-----------|--------------|
| **Text** | WeChat Official Accounts, Zhihu answers/articles | Fetches body text → strips ads/noise → keeps core arguments and useful high-signal comments |
| **Image/Text/Video** | Xiaohongshu notes and collections | Routes note/collection URLs into the shared `BookmarkItem` schema for extractor/OCR/download stages |
| **Video / Audio / Transcript** | WeChat Video Channels user-provided files, plus routed Channels links | Local file → audio/transcription pipeline → structured notes with timestamps; public Channels links are routed but not downloaded |

## Supported Platforms

| Platform / Source | Type | Core Status | Notes |
|-------------------|------|-------------|-------|
| WeChat Official Accounts (`mp.weixin.qq.com/s/...`) | Text | Supported | Routes as `wechat_article`; extractor removes QR-code promotions, "read more" blocks, login/anti-bot risk signals, and returns images/comment metadata. |
| Zhihu (`zhihu.com/question/.../answer/...`, `zhuanlan.zhihu.com/p/...`) | Text | Supported | Routes as `zhihu_answer` or `zhihu_article`; extraction keeps answer/article content and high-signal comments where available. |
| Xiaohongshu (`xiaohongshu.com`, `xhslink.cn`, `xhslink.com`) | Image/Text/Video | Supported | Routes as `xiaohongshu_note`; short links are marked `requires_expansion`. |
| Xiaohongshu collection item URLs | Collection | Supported | Routes as `xiaohongshu_collection`. |
| WeChat Video Channels local files (`.mp4`, `.m4a`, `.srt`, etc.) | File | Supported | Routes as `wechat_channels_file`; user-uploaded/exported media or transcript is required for processing. |
| WeChat Video Channels public links | Video URL | Routed / upload required | Routes as `wechat_channels_video`; no public downloader is claimed. Ask the user to upload/export the file. |
| Bilibili / `b23.tv` | Video | Unsupported | Router raises `UnsupportedPlatformError`; Bilibili is intentionally outside the current core scope. |

## Core Architecture

The main branch is the product line. Platform-specific extractors feed a standard middle layer, then renderers/exporters consume that stable shape.

- `clipped_bookmarks.schema.BookmarkItem` — unified schema for `url`, `platform`, `source_type`, `title`, `author`, `published_at`, `content`, `summary`, `tags`, `assets`, `metadata`, `status`, and `errors`.
- `clipped_bookmarks.router.route_url(source)` — detects supported URLs/files and rejects unsupported platforms such as Bilibili with `UnsupportedPlatformError`.
- `clipped_bookmarks.renderers.markdown.render_markdown(item)` — renders Markdown with YAML frontmatter for downstream note systems.
- `clipped_bookmarks.renderers.obsidian` — Obsidian export skeleton using `ObsidianExportConfig`; writing to a vault requires explicit `confirm=True`.
- `clipped_bookmarks.cli` — minimal CLI for route → Markdown output and optional confirmed Obsidian export.
- `scripts/fetch_text.py` — text fetch/extraction entrypoint for WeChat Official Accounts and Zhihu.
- `scripts/batch_process.sh` — batch router that uses the same core scope instead of ad-hoc URL matching.
- `references/core_handoff.md` — concise contract for platform-agent handoff boundaries and active platform scope.

Example:

```bash
python3 -m clipped_bookmarks.cli "https://mp.weixin.qq.com/s/ENwXC3hEbXnq-5hGEE6keA" --out note.md
python3 -m clipped_bookmarks.cli "https://www.zhihu.com/question/123456/answer/789012"
python3 -m clipped_bookmarks.cli "https://xhslink.cn/o/2HSnq3KBHMZ"
python3 -m clipped_bookmarks.cli ./wechat-channel-video.mp4 --obsidian-vault ~/Vault --confirm-obsidian
```

## Directory Structure

```
clipped-bookmarks-master/
├── clipped_bookmarks/
│   ├── schema.py                 # Unified BookmarkItem / BookmarkAsset schema
│   ├── router.py                 # Supported platform/source routing
│   ├── platforms.py              # Active platform registry
│   ├── extractors/               # Platform extractors and safe helpers
│   └── renderers/                # Markdown / Obsidian renderers
├── scripts/
│   ├── install_deps.sh           # Install yt-dlp, whisper, ffmpeg, Python deps
│   ├── fetch_text.py             # Fetch & extract WeChat OA / Zhihu text content
│   ├── download_media.sh         # Download supported media sources where allowed
│   ├── extract_audio.sh          # Video → 16k mono MP3
│   ├── transcribe.sh             # Audio → timestamped transcript
│   └── batch_process.sh          # Batch-process a list of URLs through core routing
└── references/
    ├── core_handoff.md           # Core/platform-agent boundary and active scope
    ├── templates.md              # Markdown output templates
    └── field_spec.md             # Per-platform field specs & cleaning rules
```

## Quick Start

### 1. Install Dependencies

```bash
bash scripts/install_deps.sh
```

This installs `yt-dlp`, `requests`, `beautifulsoup4`, `trafilatura`, and optional speech-to-text dependencies. Make sure `ffmpeg` is available for media workflows.

### 2. Process a WeChat Official Account Article

```bash
python3 scripts/fetch_text.py "https://mp.weixin.qq.com/s/ENwXC3hEbXnq-5hGEE6keA" --out raw.json
```

The extractor returns title, author, publish time, cleaned content, images, comment metadata, and risk flags. The Agent then turns `raw.json` into a final Markdown note using `references/templates.md`.

### 3. Process Zhihu Text

```bash
python3 scripts/fetch_text.py "https://www.zhihu.com/question/123456/answer/789012" --out raw.json
python3 scripts/fetch_text.py "https://zhuanlan.zhihu.com/p/123456" --out raw.json
```

### 4. Process a WeChat Video Channels File

WeChat Video Channels has no stable public download API. If the input is a Channels link, first ask the user to upload/export the video, audio, or transcript file; then run the local media pipeline:

```bash
bash scripts/extract_audio.sh downloads/wechat_channels_video.mp4
export OPENAI_API_KEY="sk-..."
bash scripts/transcribe.sh downloads/wechat_channels_video.mp3 --api openai
```

The Agent then summarizes the transcript into a structured note with `[MM:SS]` timestamps.

### 5. Batch Process a Collection

Create `links.txt` (one URL per line):

```
https://mp.weixin.qq.com/s/ENwXC3hEbXnq-5hGEE6keA
https://www.zhihu.com/question/123456/answer/789012
https://xhslink.cn/o/2HSnq3KBHMZ
https://www.xiaohongshu.com/collection/item/68930d3b02f5000000000001
```

Run:

```bash
bash scripts/batch_process.sh links.txt --out ./bookmarks_notes
```

The script routes each source through `clipped_bookmarks.router` and writes raw outputs/handoff files by platform.

## Output Templates

### Text Note

```markdown
# {Title}

> Source: {Platform} · {Author} · {Date}
> Original: {URL}

## Core Arguments
- {Main point 1}
- {Main point 2}

### {Sub-topic A}
{Elaboration with `>` blockquotes for key original sentences}

## High-Signal Comments
> **@{Nickname}** ({upvotes} upvotes): {Core insight}

## Tags
#bookmarks #{platform} #{topic}
```

### Video Note

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

## Tags
#bookmarks #{platform} #{topic}
```

## Environment Variables

| Variable | Required For | Description |
|----------|-------------|-------------|
| `OPENAI_API_KEY` | `--api openai` transcription | OpenAI API key for Whisper transcription |

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `fetch_text.py` returns empty | Anti-bot / login wall | Add `--cookies cookies.txt`, paste content manually, or stop honestly; never fabricate content |
| `download_media.sh` fails | Platform restriction / geo-block | For WeChat Video Channels, upload/export the file directly; Bilibili is unsupported |
| `transcribe.sh` errors | Missing ASR deps / no API key | Run `install_deps.sh` or set `OPENAI_API_KEY` |
| Content behind paywall | Access unavailable | Stop and inform user; never invent content |

## Safety & Compliance

- **No fabrication**: If anti-bot or login walls block access, inform the user instead of making up content.
- **Personal use only**: Downloaded or uploaded media is for personal note-taking only; do not redistribute.
- **Respect platform TOS**: Do not scrape paywalled or explicitly forbidden content.

## License

MIT
