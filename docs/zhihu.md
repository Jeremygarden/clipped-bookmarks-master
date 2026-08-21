# 知乎抓取支持

当前知乎支持由 `clipped_bookmarks.extractors.zhihu.extract_zhihu` 提供，并通过 `scripts/fetch_text.py` 在检测到 `zhihu.com` URL 时调用。输出保持既有 `BookmarkItem` 原始字典兼容字段：

- `platform`: 固定为 `zhihu`
- `title`, `author`, `publish_time`, `content`
- `top_comments`: DOM 中可见评论的前 5 条
- `raw_html_len`
- `upvote_count`: 与 `publish_time` 分离，不再误写入发布时间
- `raw_data`: BookmarkItem-compatible 原始补充数据（URL、类型、ID、fallback 状态等），键集合在空页/登录墙/问题页/回答页/文章页之间保持稳定
- `extra`: 知乎专用补充数据，包含 `raw_data` 的同源细节以及 `items`

## 支持场景

1. 回答页：`https://www.zhihu.com/question/<qid>/answer/<aid>`
2. 文章页：`https://zhuanlan.zhihu.com/p/<article_id>` / `https://www.zhihu.com/p/<article_id>`
3. 问题页多回答：`https://www.zhihu.com/question/<qid>`，会在 `extra.items` 中返回多个回答候选

解析优先级：

1. Zhihu SSR/initial JSON (`#js-initialData`, `#initialData`, `window.__INITIAL_STATE__`, `window.__INITIAL_DATA__`)；同一回答在 `entities`、列表分页等多棵 state 树中重复出现时按 type+id 去重
2. DOM fallback (`.AnswerCard`, `.AnswerItem`, `.Post-RichTextContainer`, `article`)
3. 如果页面只返回动态空壳，设置 `extra.dynamic_fallback = true`；如果命中不存在页面文案，设置 `extra.not_found = true` 且 `extra.fallbacks.content = "not_found"`

## raw_data 稳定字段

顶层 `raw_data` 与 `extra.raw_data` 内容一致，固定包含以下键，便于后续 `BookmarkItem` 入库逻辑按白名单读取：

- `url`, `content_type`
- `question_id`, `answer_id`, `article_id`, `primary_id`
- `item_count`
- `requires_login`, `anti_bot`, `not_found`
- `dynamic_fallback`, `comments_fallback`

`extra.items[*].raw_data` 保存单个回答/文章候选的 `id`, `type`, `url`, `question_id`。

## 登录墙 / 反爬

检测到登录、验证码、安全验证或 unhuman/captcha 标记时：

- `extra.requires_login = true`
- `extra.anti_bot = true`（仅验证码/安全验证类）
- `extra.login_wall_markers` 记录命中的提示

这类页面通常需要人工导出的 Netscape cookies，通过：

```bash
python3 scripts/fetch_text.py 'https://www.zhihu.com/question/...' --cookies cookies.txt
```

## 评论 fallback

知乎评论经常由接口动态加载。当前实现只解析 HTML 中已出现的评论；否则：

- `extra.comments_fallback = "dom"`: HTML 已含评论并完成解析
- `extra.comments_fallback = "login_required"`: 页面命中登录墙/反爬，评论也需要登录态或人工授权
- `extra.comments_fallback = "api_or_dynamic_required"`: HTML 无评论，需要后续接口/动态内容能力

`extra.fallbacks` 与顶层 `raw_data` 会同步记录 content/comments fallback，方便后续 BookmarkItem 入库或人工复查。

后续如接入评论接口，应保持现有顶层字段不变，把接口状态放入 `extra`。


## 不存在页面

当知乎返回「页面不存在」「内容不存在」「你似乎来到了没有知识存在的荒原」等文案时，解析器会把它与登录墙、动态空壳区分开：

- `extra.not_found = true`
- `extra.dynamic_fallback = false`
- `extra.fallbacks.content = "not_found"`
- 顶层 `raw_data.not_found` 同步记录，方便批处理跳过重试。

## 平台边界

本项目当前只支持：小红书、微信视频号短视频/文件、微信公众号、知乎。知乎 URL 检测使用严格 host 匹配，仅接受 `zhihu.com`、`www.zhihu.com`、`zhuanlan.zhihu.com`，避免把第三方链接参数中包含 `zhihu.com` 的页面误判为知乎内容。本文档中的知乎提取范围限定为问题 / 回答 / 文章；其他知乎页面不声明为已支持。

知乎解析覆盖：

- 问题 / 回答：`https://www.zhihu.com/question/<question_id>`、`/answer/<answer_id>`
- 文章：`https://zhuanlan.zhihu.com/p/<article_id>` 或知乎站内 `/p/<article_id>`
- 动态空壳和登录墙：不伪造正文，通过 `extra.fallbacks`、`extra.requires_login`、`extra.dynamic_fallback` 标注后续处理需求

计数字段会归一化常见中文单位，例如 `1.2 万赞同`、`3K`、`1 万 2 千赞同`。
