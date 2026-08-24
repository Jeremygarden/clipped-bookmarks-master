"""Clipped Bookmarks Master core package."""

from .platforms import PlatformDescriptor, descriptor_for_source_type, is_supported_platform, supported_platforms
from .router import route_url
from .schema import BookmarkAsset, BookmarkItem, Platform, SourceType, UnsupportedPlatformError

__all__ = [
    "BookmarkAsset",
    "BookmarkItem",
    "Platform",
    "PlatformDescriptor",
    "SourceType",
    "UnsupportedPlatformError",
    "descriptor_for_source_type",
    "is_supported_platform",
    "route_url",
    "supported_platforms",
]
