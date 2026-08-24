"""Supported platform registry for the shared core architecture.

The registry is deliberately small and extractor-agnostic. Platform agents can use
these descriptors to validate handoff boundaries without importing router or CLI
implementation details.
"""

from __future__ import annotations

from dataclasses import dataclass

from .schema import Platform, SourceType


@dataclass(frozen=True, slots=True)
class PlatformDescriptor:
    """Shared metadata for a platform supported by core routing/rendering."""

    platform: Platform
    display_name: str
    source_types: tuple[SourceType, ...]
    url_hosts: tuple[str, ...] = ()
    accepts_local_files: bool = False
    notes: str = ""


ACTIVE_PLATFORM_SCOPE: tuple[Platform, ...] = (
    Platform.XIAOHONGSHU,
    Platform.WECHAT_CHANNELS,
    Platform.WECHAT_OFFICIAL_ACCOUNT,
    Platform.ZHIHU,
)


SUPPORTED_PLATFORM_REGISTRY: dict[Platform, PlatformDescriptor] = {
    Platform.XIAOHONGSHU: PlatformDescriptor(
        platform=Platform.XIAOHONGSHU,
        display_name="小红书",
        source_types=(SourceType.XIAOHONGSHU_NOTE, SourceType.XIAOHONGSHU_COLLECTION),
        url_hosts=("xhslink.cn", "xhslink.com", "xiaohongshu.com"),
        notes="Supports notes, xhslink.cn/xhslink.com short links requiring expansion, and collection item links.",
    ),
    Platform.WECHAT_CHANNELS: PlatformDescriptor(
        platform=Platform.WECHAT_CHANNELS,
        display_name="微信视频号",
        source_types=(SourceType.WECHAT_CHANNELS_FILE, SourceType.WECHAT_CHANNELS_VIDEO),
        url_hosts=("channels.weixin.qq.com", "finder.video.qq.com"),
        accepts_local_files=True,
        notes="Short video URLs and user-supplied local media files.",
    ),
    Platform.WECHAT_OFFICIAL_ACCOUNT: PlatformDescriptor(
        platform=Platform.WECHAT_OFFICIAL_ACCOUNT,
        display_name="微信公众号",
        source_types=(SourceType.WECHAT_ARTICLE,),
        url_hosts=("mp.weixin.qq.com",),
        notes="Public account article URLs.",
    ),
    Platform.ZHIHU: PlatformDescriptor(
        platform=Platform.ZHIHU,
        display_name="知乎",
        source_types=(SourceType.ZHIHU_ANSWER, SourceType.ZHIHU_ARTICLE),
        url_hosts=("zhihu.com", "zhuanlan.zhihu.com"),
        notes="Question answers and Zhuanlan articles; extraction remains platform-agent work.",
    ),
}


def supported_platforms() -> tuple[PlatformDescriptor, ...]:
    """Return supported platform descriptors in a stable documentation order."""

    return tuple(SUPPORTED_PLATFORM_REGISTRY[platform] for platform in ACTIVE_PLATFORM_SCOPE)


def is_supported_platform(platform: Platform | str) -> bool:
    """Return whether a platform is in the active supported core scope."""

    if isinstance(platform, str):
        try:
            platform = Platform(platform)
        except ValueError:
            return False
    return platform in SUPPORTED_PLATFORM_REGISTRY


def descriptor_for_source_type(source_type: SourceType | str) -> PlatformDescriptor | None:
    """Return the active platform descriptor that owns a source type, if any."""

    if isinstance(source_type, str):
        try:
            source_type = SourceType(source_type)
        except ValueError:
            return None
    for descriptor in supported_platforms():
        if source_type in descriptor.source_types:
            return descriptor
    return None
