"""Core schema for Clipped Bookmarks Master.

This module intentionally has no platform-extractor dependencies. Extractors should
produce or enrich :class:`BookmarkItem` instances so downstream renderers can stay
stable across platforms.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal


class UnsupportedPlatformError(ValueError):
    """Raised when a URL/source is outside the supported core scope."""


class Platform(str, Enum):
    WECHAT_OFFICIAL_ACCOUNT = "wechat_official_account"
    ZHIHU = "zhihu"
    XIAOHONGSHU = "xiaohongshu"
    WECHAT_CHANNELS = "wechat_channels"


class SourceType(str, Enum):
    WECHAT_ARTICLE = "wechat_article"
    ZHIHU_ANSWER = "zhihu_answer"
    ZHIHU_ARTICLE = "zhihu_article"
    XIAOHONGSHU_NOTE = "xiaohongshu_note"
    XIAOHONGSHU_COLLECTION = "xiaohongshu_collection"
    WECHAT_CHANNELS_FILE = "wechat_channels_file"
    WECHAT_CHANNELS_VIDEO = "wechat_channels_video"


SUPPORTED_SOURCE_TYPES: tuple[SourceType, ...] = (
    SourceType.WECHAT_ARTICLE,
    SourceType.ZHIHU_ANSWER,
    SourceType.ZHIHU_ARTICLE,
    SourceType.XIAOHONGSHU_NOTE,
    SourceType.XIAOHONGSHU_COLLECTION,
    SourceType.WECHAT_CHANNELS_FILE,
    SourceType.WECHAT_CHANNELS_VIDEO,
)

UNSUPPORTED_PLATFORMS: dict[str, str] = {
    "bilibili": "Bilibili support is intentionally out of scope.",
    "b23": "Bilibili short links are intentionally unsupported.",
}


Status = Literal["new", "fetched", "rendered", "error", "unsupported"]


@dataclass(slots=True)
class BookmarkAsset:
    """Media or attachment associated with a bookmark."""

    url: str
    kind: str = "image"
    title: str | None = None
    local_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BookmarkItem:
    """Unified bookmark item passed between routers, extractors, and renderers."""

    url: str
    platform: Platform
    source_type: SourceType
    title: str = "Untitled Bookmark"
    author: str | None = None
    published_at: str | datetime | None = None
    content: str = ""
    summary: str | None = None
    tags: list[str] = field(default_factory=list)
    assets: list[BookmarkAsset] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    status: Status = "new"
    errors: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if isinstance(self.platform, str):
            self.platform = Platform(self.platform)
        if isinstance(self.source_type, str):
            self.source_type = SourceType(self.source_type)
        if self.source_type not in SUPPORTED_SOURCE_TYPES:
            raise UnsupportedPlatformError(f"Unsupported source type: {self.source_type}")
        if isinstance(self.published_at, datetime):
            self.published_at = self.published_at.isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "platform": self.platform.value,
            "source_type": self.source_type.value,
            "title": self.title,
            "author": self.author,
            "published_at": self.published_at,
            "content": self.content,
            "summary": self.summary,
            "tags": list(self.tags),
            "assets": [asset.to_dict() for asset in self.assets],
            "metadata": dict(self.metadata),
            "status": self.status,
            "errors": list(self.errors),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def unsupported(cls, url: str, reason: str) -> "BookmarkItem":
        return cls(
            url=url,
            platform=Platform.WECHAT_OFFICIAL_ACCOUNT,
            source_type=SourceType.WECHAT_ARTICLE,
            title="Unsupported bookmark",
            status="unsupported",
            errors=[reason],
            metadata={"unsupported_reason": reason},
        )
