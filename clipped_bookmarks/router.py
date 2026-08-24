"""URL/source router for the core Clipped Bookmarks architecture."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from .schema import BookmarkItem, Platform, SourceType, UnsupportedPlatformError, UNSUPPORTED_PLATFORMS

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
WECHAT_CHANNELS_HINTS = ("channels.weixin.qq.com", "finder.video.qq.com", "weixin.qq.com/channels")


def route_url(source: str) -> BookmarkItem:
    """Return a skeleton BookmarkItem for a supported URL or local media file.

    Supported core sources are limited to:
    - WeChat Official Account articles (mp.weixin.qq.com/s/...)
    - Xiaohongshu note links (xhslink.cn/xhslink.com, xiaohongshu.com/explore|discovery/item)
    - Xiaohongshu collection item links (xiaohongshu.com/collection/item/...)
    - WeChat Channels local uploaded files or channel video links
    - Zhihu questions, answers, and Zhuanlan articles
    """

    if not source or not source.strip():
        raise ValueError("source is required")
    source = source.strip()
    lower = source.lower()

    _raise_if_unsupported(lower, source)

    if _looks_like_local_video(source):
        return BookmarkItem(
            url=source,
            platform=Platform.WECHAT_CHANNELS,
            source_type=SourceType.WECHAT_CHANNELS_FILE,
            title=Path(source).name or "WeChat Channels upload",
            metadata={"input_kind": "file"},
        )

    parsed = urlparse(source)
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    if host == "mp.weixin.qq.com" and path.startswith("/s"):
        return BookmarkItem(
            url=source,
            platform=Platform.WECHAT_OFFICIAL_ACCOUNT,
            source_type=SourceType.WECHAT_ARTICLE,
            metadata={"input_kind": "url"},
        )

    if host.endswith(("xhslink.cn", "xhslink.com")):
        return BookmarkItem(
            url=source,
            platform=Platform.XIAOHONGSHU,
            source_type=SourceType.XIAOHONGSHU_NOTE,
            metadata={"input_kind": "short_url", "requires_expansion": True},
        )

    if host.endswith("xiaohongshu.com"):
        if path.startswith("/collection/item/"):
            return BookmarkItem(
                url=source,
                platform=Platform.XIAOHONGSHU,
                source_type=SourceType.XIAOHONGSHU_COLLECTION,
                metadata={"input_kind": "url"},
            )
        if path.startswith(("/explore/", "/discovery/item/", "/user/profile/")):
            return BookmarkItem(
                url=source,
                platform=Platform.XIAOHONGSHU,
                source_type=SourceType.XIAOHONGSHU_NOTE,
                metadata={"input_kind": "url"},
            )

    if any(hint in lower for hint in WECHAT_CHANNELS_HINTS):
        return BookmarkItem(
            url=source,
            platform=Platform.WECHAT_CHANNELS,
            source_type=SourceType.WECHAT_CHANNELS_VIDEO,
            metadata={"input_kind": "url"},
        )

    if host.endswith("zhihu.com"):
        if path.startswith("/question/") and "/answer/" in path:
            return BookmarkItem(
                url=source,
                platform=Platform.ZHIHU,
                source_type=SourceType.ZHIHU_ANSWER,
                metadata={"input_kind": "url"},
            )
        if path.startswith("/question/"):
            return BookmarkItem(
                url=source,
                platform=Platform.ZHIHU,
                source_type=SourceType.ZHIHU_QUESTION,
                metadata={"input_kind": "url", "may_contain_multiple_answers": True},
            )
        if host == "zhuanlan.zhihu.com" or path.startswith("/p/"):
            return BookmarkItem(
                url=source,
                platform=Platform.ZHIHU,
                source_type=SourceType.ZHIHU_ARTICLE,
                metadata={"input_kind": "url"},
            )

    raise UnsupportedPlatformError(f"Unsupported source: {source}")


def _raise_if_unsupported(lower: str, source: str) -> None:
    for marker, reason in UNSUPPORTED_PLATFORMS.items():
        if marker in lower:
            raise UnsupportedPlatformError(f"Unsupported source '{source}': {reason}")


def _looks_like_local_video(source: str) -> bool:
    parsed = urlparse(source)
    if parsed.scheme and parsed.scheme != "file":
        return False
    path = Path(parsed.path if parsed.scheme == "file" else source)
    return path.suffix.lower() in VIDEO_EXTENSIONS
