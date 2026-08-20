# -*- coding: utf-8 -*-
"""Shared lightweight schema for clipped bookmark extractors."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Platform(str, Enum):
    ZHIHU = "zhihu"
    XIAOHONGSHU = "xiaohongshu"
    WECHAT_CHANNELS = "wechat_channels"
    WECHAT_OFFICIAL_ACCOUNT = "weixin"


class SourceType(str, Enum):
    ZHIHU_TEXT = "zhihu_text"
    XIAOHONGSHU_VIDEO = "xiaohongshu_video"
    XIAOHONGSHU_IMAGE_TEXT = "xiaohongshu_image_text"
    WECHAT_ARTICLE = "wechat_article"
    WECHAT_CHANNELS_VIDEO = "wechat_channels_video"
    WECHAT_CHANNELS_FILE = "wechat_channels_file"


@dataclass(slots=True)
class BookmarkAsset:
    url: str
    kind: str
    title: str = ""
    local_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BookmarkItem:
    url: str
    platform: Platform
    source_type: SourceType
    title: str = ""
    content: str = ""
    author: str = ""
    publish_time: str = ""
    assets: list[BookmarkAsset] = field(default_factory=list)
    status: str = "new"
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
