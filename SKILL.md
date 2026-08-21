---
name: clipped-bookmarks-master
version: "1.0.0"
author: "CodeBuddy AI"
created: "2026-08-19"
updated: "2026-08-19"
---

# 收藏夹整理师 (Clipped Bookmarks Master)

> **Goal**：把你散落在各平台的「收藏 / 点赞」变成**统一、干净、可检索**的 Markdown 笔记。
> 文字类内容 → 抓取正文 → 清洗广告与无关评论 → 保留核心观点 + 高赞补充。
> 视频类内容 → 获取用户提供的视频/音频文件或下载受支持平台媒体 → 转逐字稿 → AI 提炼成结构化笔记（重点 / 步骤 / 清单），并保留时间戳便于回跳。

## When to Use

满足任一条件即触发：

- 用户给出了以下平台的链接：
  - 知乎 `zhihu.com`（问题 / 回答 / 文章）
  - 小红书 `xiaohongshu.com` / `xhslink.com`
  - 微信视频号（用户直接粘贴的视频号链接 / 文件）
  - 微信公众号 `mp.weixin.qq.com`
- 用户说："整理我的收藏"、"把收藏夹转成笔记"、"收藏的内容总结一下"、"帮我把点赞过的保存成笔记"

## When NOT to Use

- 用户给的是非上述平台的普通网页（此时走通用网页抓取流程，不加载本 Skill）
- 用户只是想浏览链接，没有"保存 / 整理 / 转笔记"意图
- 链接为付费墙 / 登录后才能看、且无法获取内容时——应如实告知用户，不要编造内容

## 总体处理流程

```
用户给链接 / 说"整理收藏"
        │
        ▼
1. 识别平台与内容类型（文字 or 视频）
        │
        ├─ 文字类（知乎回答/文章、公众号） ──► 步骤 A
        └─ 视频类（小红书、视频号）    ──► 步骤 B
        │
        ▼
2. 抓取 / 下载（调用本 Skill 的 scripts）
        │
        ▼
3. 清洗 + AI 提炼（由你 = 大模型 完成）
        │
        ▼
4. 输出标准 Markdown 笔记（保存到 <output_dir>）
```

### 步骤 A：文字类处理（知乎 / 公众号）

1. 用 `scripts/fetch_text.py <url>` 抓取正文 HTML 并提取纯文本/结构化内容。
2. 清洗规则（必须执行）：
   - 删除广告、推广卡片、"相关推荐"、"更多回答"区块
   - 删除与主题无关的评论；仅保留**高赞评论**（点赞数明显高于其他的，或原文明确标注"高赞"的）
   - 删除导航栏、页脚、登录引导等噪声
3. 提炼为 Markdown：
   - **核心观点**：作者的主要论点，用要点 / 小标题组织
   - **高赞补充**：精选 2-5 条高赞评论，标注"高赞补充"
   - 保留原文关键引用（用 `>` 引用块，并注明来源）
4. 套用「文字类 Markdown 模板」（见 references/templates.md）

### 步骤 B：视频类处理（小红书 / 视频号）

1. 小红书用 `scripts/download_media.sh <url>` 下载视频/音频；微信视频号不下载链接，要求用户上传/导出视频、音频或转写文件。
2. 用 `scripts/extract_audio.sh <video_file>` 分离出音频（mp3，16k）；若用户已上传音频或转写文件，可跳过对应步骤。
3. 用 `scripts/transcribe.sh <audio_file>` 调用语音识别生成逐字稿（含时间戳）。
   - 若环境无本地 whisper，调用 OpenAI Whisper API 或用户指定 ASR；脚本会自动判断。
4. 由你（大模型）基于逐字稿提炼结构化笔记：
   - **重点**：核心结论 / 金句
   - **步骤**：可复现的操作步骤（如有教程属性）
   - **清单**：要点 checklist
5. 视频号额外保留**时间戳**（`[MM:SS]`），方便回跳关键帧。
6. 套用「视频类 Markdown 模板」（见 references/templates.md）

## 各平台特殊处理要点

| 平台 | 类型 | 抓取方式 | 特别处理 |
|------|------|----------|----------|
| 知乎 | 文字 | `fetch_text.py` + 需登录态时提示用户 | 多回答问题：每个高赞回答单独成节；保留答主与赞同数 |
| 小红书 | 视频/图文 | `download_media.sh` | 图文笔记：抓取图片OCR+正文；视频：走步骤 B |
| 微信视频号 | 视频/文件 | 用户上传文件 或 粘贴链接 | 无官方 API；链接只做提示并要求上传文件，不尝试下载视频号链接 |
| 微信公众号 | 文字 | `fetch_text.py` | 清洗二维码引流、阅读原文引导；保留作者与发布时间 |

## 工具脚本（位于 `<skill-directory>/scripts/`）

| 脚本 | 作用 | 用法 |
|------|------|------|
| `fetch_text.py` | 抓取文字类正文并初步提取 | `python3 scripts/fetch_text.py <url> [--out raw.txt]` |
| `download_media.sh` | 下载视频/音频（自动选方式） | `bash scripts/download_media.sh <url> [--dir ./downloads]` |
| `extract_audio.sh` | 视频 → 音频 mp3 | `bash scripts/extract_audio.sh <video_file>` |
| `transcribe.sh` | 音频 → 逐字稿(带时间戳) | `bash scripts/transcribe.sh <audio_file> [--api openai\|local]` |
| `batch_process.sh` | 批量处理一组链接 | `bash scripts/batch_process.sh links.txt [--out ./notes]` |
| `install_deps.sh` | 安装依赖（yt-dlp / whisper 等） | `bash scripts/install_deps.sh` |

> `<skill-directory>` 指本 Skill 所在目录（即 `clipped-bookmarks-master/`），不是用户项目目录。

## 依赖与安全

- **首次使用**建议先跑 `bash scripts/install_deps.sh` 安装 `yt-dlp`、语音识别依赖。
- **禁止**用本 Skill 抓取任何需付费 / 明确禁止爬取的内容；遇到反爬（验证码、登录墙）应停止并告知用户。
- 下载或上传的视频/音频仅用于**个人笔记整理**，不二次分发；处理完可提示用户是否删除临时媒体文件以节省空间。
- 支持平台仅限：知乎、小红书、微信视频号、微信公众号；不要添加其他平台入口。

## 输出目录约定

- 单次整理：保存到用户指定目录，默认 `./bookmarks_notes/`，文件名 `<平台>_<标题前20字>.md`
- 批量整理：`batch_process.sh` 会在输出目录下按平台分子目录

## 示例

### 示例 1：知乎回答（文字类）

用户给出：`https://www.zhihu.com/question/633780178/answer/1997868452766058023`

1. `python3 scripts/fetch_text.py "https://www.zhihu.com/question/633780178/answer/1997868452766058023"`
2. 清洗广告与无关评论，保留答主核心观点 + 高赞补充
3. 按文字类模板输出 `bookmarks_notes/知乎_xxxx.md`



2. `bash scripts/extract_audio.sh downloads/xxx.mp4`
3. `bash scripts/transcribe.sh downloads/xxx.mp3 --api openai`
4. 提炼笔记，每个重点前标注 `[MM:SS]` 时间戳

### 示例 3：批量整理收藏夹

用户提供 `links.txt`（每行一个链接），执行：

```bash
bash scripts/batch_process.sh links.txt --out ./bookmarks_notes
```

Skill 自动识别每个链接的平台与类型，分别走步骤 A / B，最终输出一组 Markdown 笔记。

## 错误处理

| 现象 | 原因 | 处理 |
|------|------|------|
| `fetch_text.py` 返回空 / 反爬 | 需登录态或反爬 | 提示用户手动复制正文，或登录后重试；**不编造内容** |
| `download_media.sh` 失败 | 平台限制 / 链接失效 | 告知用户，建议上传文件；视频号优先走文件方式 |
| `transcribe.sh` 报错 | 无 ASR 依赖/密钥 | 引导安装依赖或配置 API Key；可先产出"未转写"占位笔记 |
| 内容含敏感/违规 | — | 拒绝整理并说明原因 |
