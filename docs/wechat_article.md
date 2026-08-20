# 微信公众号文章支持

本项目支持抓取 `mp.weixin.qq.com/s/...` 公众号文章 HTML，并输出与现有 `BookmarkItem` 摄取流程兼容的 raw dict。

## 范围

- ✅ 公众号图文文章：标题、作者/公众号、发布时间、正文、图片资源、精选留言（静态 HTML 或脚本片段可见时）
- ✅ 风控/空内容检测：登录态、微信客户端打开提示、验证码/访问频繁、删除或不可用页面
- ✅ 二维码、关注引导、推广段落的基础清洗
- ✅ 图片 OCR hook：`images[].ocr_hook` / `extra.image_ocr_hook`，当前只标记入口，不执行 OCR
- ❌ 微信视频号链接下载：视频号通常没有稳定可分享下载链接，本轮不做；用户上传的视频文件仍应进入既有短视频处理流程

## 使用

```bash
python3 scripts/fetch_text.py 'https://mp.weixin.qq.com/s/ENwXC3hEbXnq-5hGEE6keA' --out wechat.json
```

如遇登录态或风控页面，可提供 Netscape cookies：

```bash
python3 scripts/fetch_text.py 'https://mp.weixin.qq.com/s/ENwXC3hEbXnq-5hGEE6keA' --cookies cookies.txt --out wechat.json
```

## 输出字段

顶层保持 `fetch_text.py` 既有结构，新增字段为向后兼容扩展：

- `platform`: 固定为 `weixin`
- `title`: 文章标题，优先 `#activity-name`，再 fallback 到 meta/script/title
- `author`: 公众号名称，优先 `#js_name`
- `publish_time`: 发布时间，优先 DOM，再 fallback 到 `var ct`
- `content`: 清洗后的正文纯文本
- `top_comments`: 精选留言，静态 DOM 不存在时尝试脚本 JSON fallback
- `images`: 正文图片资源列表，二维码/推广图会过滤
- `risk_flags`: `requires_login` / `anti_bot` / `deleted_or_unavailable` / `empty_article`
- `raw_data`: 与 BookmarkItem 摄取兼容的统一 raw data，包含 source/canonical URL、正文、图片、留言和风险信息
- `extra.image_ocr_hook`: 指向 `images[].ocr_hook`，为后续图片 OCR 保留入口

## 需要人工授权或登录态的场景

- 文章要求在微信客户端打开，网页端只返回提示页
- 访问频繁、验证码、安全验证、IP/UA 风控
- 文章删除、违规、过期或仅对特定用户可见
- 精选留言由客户端异步接口返回且静态 HTML/脚本中没有数据时，只能标记 `comment_status=unavailable_in_static_html`，需要登录态或人工导出页面

## 视频号说明

微信视频号本轮不做链接下载支持。若用户上传本地视频文件，应继续走项目已有短视频处理流程，而不是尝试解析视频号分享链接。
