# Core Handoff Boundary

The core layer owns only routing, schema validation, platform registry metadata, and Markdown/export rendering contracts.

## Active supported platforms

Only these platforms are in scope for the core architecture:

1. Xiaohongshu notes and collection item links
2. WeChat Channels short video URLs and user-supplied video files
3. WeChat Official Account article URLs
4. Zhihu answers and Zhuanlan articles

Bilibili, including `bilibili.com`, `b23.tv`, and app share domains, is intentionally unsupported. Core code must reject those inputs with `UnsupportedPlatformError`; platform extractors should not implement Bilibili handling in this branch.

## Extractor contract

Platform-specific extractors may enrich `BookmarkItem` content, assets, tags, and metadata, but they should preserve the platform/source-type pair produced by `route_url()` and validated by `BookmarkItem.__post_init__()`.
