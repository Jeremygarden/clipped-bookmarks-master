# 知乎抓取支持

当前知乎支持由 `clipped_bookmarks.extractors.zhihu.extract_zhihu` 提供，并通过 `scripts/fetch_text.py` 在检测到 `zhihu.com` URL 时调用。输出保持既有 `BookmarkItem` 原始字典兼容字段：

- `platform`: 固定为 `zhihu`
- `title`, `author`, `publish_time`, `content`
- `top_comments`: DOM 中可见评论的前 5 条
- `raw_html_len`
- `upvote_count`: 与 `publish_time` 分离，不再误写入发布时间
- `extra`: 知乎专用补充数据

## 支持场景

1. 回答页：`https://www.zhihu.com/question/<qid>/answer/<aid>`
2. 文章页：`https://zhuanlan.zhihu.com/p/<article_id>` / `https://www.zhihu.com/p/<article_id>`
3. 问题页多回答：`https://www.zhihu.com/question/<qid>`，会在 `extra.items` 中返回多个回答候选

解析优先级：

1. Zhihu SSR/initial JSON (`#js-initialData`, `window.__INITIAL_STATE__`)
2. DOM fallback (`.AnswerCard`, `.AnswerItem`, `.Post-RichTextContainer`, `article`)
3. 如果页面只返回动态空壳，设置 `extra.dynamic_fallback = true`

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

- `extra.comments_fallback = "api_or_login_required"`

后续如接入评论接口，应保持现有顶层字段不变，把接口状态放入 `extra`。
