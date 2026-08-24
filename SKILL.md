---
name: clipped-bookmarks-master
description: 收藏夹整理师 - 对小红书、微信视频号、微信公众号、知乎中收藏/点赞过的内容，抓取文字或视频并清洗，输出为标准 Markdown 笔记（核心观点+高赞补充；视频类额外生成逐字稿与时间戳）。当用户给出上述平台的链接、或说"整理收藏夹/整理我的收藏/把收藏转成笔记"时触发。
version: "1.0.0"
author: "CodeBuddy AI"
created: "2026-08-19"
updated: "2026-08-24"
---

# 收藏夹整理师 (Clipped Bookmarks Master)

> **Goal**：把散落在各平台的「收藏 / 点赞」变成**统一、干净、可检索**的 Markdown 笔记。

文字类内容 → 抓取正文 → 清洗广告与噪声 → 保留核心观点 + 高信号评论。  
视频类内容 → 获取用户提供的视频/音频/转写文件或下载受支持媒体 → 转逐字稿 → AI 提炼成结构化笔记（重点 / 步骤 / 清单），并保留时间戳。

## When to Use

满足任一条件即触发：

- 用户给出了以下平台的链接或文件：
  - 微信公众号 `mp.weixin.qq.com/s/...`
  - 知乎 `zhihu.com/question/.../answer/...` / `zhuanlan.zhihu.com/p/...`
  - 小红书 `xiaohongshu.com` / `xhslink.cn` / `xhslink.com`
  - 小红书收藏合集 `xiaohongshu.com/collection/item/...`
  - 微信视频号链接、或用户上传/导出的视频、音频、转写文件
- 用户说：「整理我的收藏」「把收藏夹转成笔记」「收藏的内容总结一下」「帮我把点赞过的保存成笔记」

## When NOT to Use

- 用户给的是非上述平台的普通网页：走通用网页抓取流程，不加载本 Skill。
- 用户给的是 B站 / `b23.tv` 链接：当前核心架构明确不支持，应告知 unsupported，不要绕过 router。
- 用户只是想浏览链接，没有「保存 / 整理 / 转笔记」意图。
- 链接为付费墙 / 登录后才能看、且无法获取内容时：如实告知用户，不要编造内容。

## 总体处理流程

```
用户给链接 / 文件 / 说“整理收藏”
        │
        ▼
1. 通过 clipped_bookmarks.router.route_url() 识别平台与内容类型，得到统一 BookmarkItem
        │
        ├─ 文字类（公众号 / 知乎） ──► 步骤 A
        ├─ 小红书笔记/合集 ──► 对应 extractor / OCR / 下载流程
        └─ 视频类（小红书、微信视频号文件） ──► 步骤 B
        │
        ▼
2. 抓取 / 下载 / 文件转写（调用本 Skill 的 scripts）
        │
        ▼
3. 清洗 + AI 提炼（由你 = 大模型完成）
        │
        ▼
4. 输出标准 Markdown 笔记（保存到 <output_dir>）
```

### 步骤 A：文字类处理（公众号 / 知乎）

1. 用 `scripts/fetch_text.py <url>` 抓取正文 HTML 并提取结构化内容。
2. 清洗规则（必须执行）：
   - 删除广告、推广卡片、二维码引流、"相关推荐"、"更多回答"区块。
   - 删除与主题无关的评论；仅保留 2-5 条高信号评论。
   - 删除导航栏、页脚、登录引导等噪声。
3. 提炼为 Markdown：
   - **核心观点**：作者的主要论点，用要点 / 小标题组织。
   - **高赞补充**：精选评论，标注「高赞补充」。
   - 保留原文关键引用（用 `>` 引用块，并注明来源）。
4. 套用「文字类 Markdown 模板」（见 `references/templates.md`）。

### 步骤 B：视频类处理（小红书 / 微信视频号）

1. 小红书用 `scripts/download_media.sh <url>` 下载视频/音频；图文笔记进入图片/OCR/正文抽取流程。
2. 微信视频号不下载公开链接；必须要求用户上传/导出视频、音频或转写文件。
3. 用 `scripts/extract_audio.sh <video_file>` 分离音频；若用户已上传音频或转写文件，可跳过对应步骤。
4. 用 `scripts/transcribe.sh <audio_file>` 生成带时间戳逐字稿。
5. 基于逐字稿提炼结构化笔记：重点、步骤、清单、关键时间戳。
6. 套用「视频类 Markdown 模板」（见 `references/templates.md`）。

## 各平台特殊处理要点

| 平台 | 类型 | 抓取方式 | 特别处理 |
|------|------|----------|----------|
| 微信公众号 | 文字 | `route_url()` → `fetch_text.py` → `wechat_article` extractor | 清洗二维码引流、阅读原文引导；保留作者、发布时间、图片、风险标记。 |
| 知乎 | 文字 | `route_url()` → `fetch_text.py` / 平台 extractor | 支持回答与专栏文章；清洗盐选/广告/相关推荐；多回答页面按高信号内容拆分。 |
| 小红书笔记 | 视频/图文 | `route_url()` → extractor / OCR / 下载流程 | `xhslink.cn` / `xhslink.com` 标记为需展开；图文走 OCR + 正文；视频走步骤 B。 |
| 小红书收藏合集 | Collection | `route_url()` → collection extractor | 仅 `xiaohongshu.com/collection/item/...` 属于当前核心支持。 |
| 微信视频号 | 文件/视频链接 | 用户上传文件；链接只路由不下载 | 无官方稳定下载 API；公开链接必须要求用户上传/导出文件。 |
| B站 / b23.tv | — | Unsupported | Router 必须报 unsupported，不新增 B站支持。 |

## 核心中间层

- `BookmarkItem`：所有平台统一输出字段，包括 `platform`、`source_type`、`url`、`title`、`author`、`published_at`、`content`、`summary`、`tags`、`assets`、`metadata`、`status`、`errors`。
- `route_url(source)`：只接受微信公众号、小红书笔记、小红书收藏合集、微信视频号文件/视频、知乎问题/回答/文章；B站返回 unsupported。
- `render_markdown(item)`：输出带 YAML frontmatter 的标准 Markdown。
- `ObsidianExportConfig` / `export_to_obsidian(...)`：Obsidian 导出骨架；写入 vault 前必须显式 `confirm=True` 或 CLI `--confirm-obsidian`。
- CLI：`python3 -m clipped_bookmarks.cli <source> [--out note.md] [--obsidian-vault PATH --confirm-obsidian]`。

## 工具脚本（位于 `<skill-directory>/scripts/`）

| 脚本 | 作用 | 用法 |
|------|------|------|
| `fetch_text.py` | 抓取文字类正文并初步提取 | `python3 scripts/fetch_text.py <url> [--out raw.json]` |
| `download_media.sh` | 下载受支持视频/音频 | `bash scripts/download_media.sh <url> [--dir ./downloads]` |
| `extract_audio.sh` | 视频 → 音频 mp3 | `bash scripts/extract_audio.sh <video_file>` |
| `transcribe.sh` | 音频 → 逐字稿（带时间戳） | `bash scripts/transcribe.sh <audio_file> [--api openai|local]` |
| `batch_process.sh` | 批量处理一组链接 | `bash scripts/batch_process.sh links.txt [--out ./notes]` |
| `install_deps.sh` | 安装依赖 | `bash scripts/install_deps.sh` |

## 依赖与安全

- 首次使用建议先跑 `bash scripts/install_deps.sh`。
- 禁止抓取任何需付费 / 明确禁止爬取的内容；遇到反爬（验证码、登录墙）应停止并告知用户。
- 下载或上传的视频/音频仅用于个人笔记整理，不二次分发。
- 支持平台仅限：知乎、小红书、微信视频号、微信公众号；不要添加其他平台入口。

## 输出目录约定

- 单次整理：保存到用户指定目录，默认 `./bookmarks_notes/`，文件名 `<平台>_<标题前20字>.md`。
- 批量整理：`batch_process.sh` 会在输出目录下按平台分子目录：`zhihu/`、`weixin/`、`xiaohongshu/`、`wechat_channels/`。

## 示例

### 示例 1：知乎回答（文字类）

用户给出：`https://www.zhihu.com/question/123456/answer/789012`

1. `python3 scripts/fetch_text.py "https://www.zhihu.com/question/123456/answer/789012" --out raw.json`
2. 清洗广告与无关评论，保留作者核心观点。
3. 按文字类模板输出 `bookmarks_notes/zhihu/知乎_xxxx.md`。

### 示例 2：微信视频号文件（视频类，需时间戳）

用户上传：`./wechat-channel-video.mp4`

1. `python3 -m clipped_bookmarks.cli ./wechat-channel-video.mp4 --out routed.md`
2. `bash scripts/extract_audio.sh ./wechat-channel-video.mp4`
3. `bash scripts/transcribe.sh ./wechat-channel-video.mp3 --api openai`
4. 提炼笔记，每个重点前标注 `[MM:SS]` 时间戳。
5. 输出 `bookmarks_notes/wechat_channels/xxx.md`。

### 示例 3：批量整理收藏夹

```bash
bash scripts/batch_process.sh links.txt --out ./bookmarks_notes
```

Skill 自动识别每个链接的平台与类型，分别走对应流程。

## 错误处理

| 现象 | 原因 | 处理 |
|------|------|------|
| `fetch_text.py` 返回空 / 反爬 | 需登录态或反爬 | 提示用户手动复制正文，或登录后重试；不编造内容。 |
| `download_media.sh` 失败 | 平台限制 / 链接失效 | 告知用户，建议上传文件；微信视频号优先走文件方式。 |
| `transcribe.sh` 报错 | 无 ASR 依赖/密钥 | 引导安装依赖或配置 API Key；可先产出「未转写」占位笔记。 |
| 内容含敏感/违规 | — | 拒绝整理并说明原因。 |
