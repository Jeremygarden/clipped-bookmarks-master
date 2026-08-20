"""WeChat Channels short-video/file helpers.

WeChat Channels does not expose a stable public download API. This helper keeps
support explicit and safe: local uploaded video files become processable
BookmarkItems, while channel URLs/hints return an item that asks for a user-
provided file instead of pretending to download the video.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from clipped_bookmarks.schema import BookmarkAsset, BookmarkItem, Platform, SourceType

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}
CHANNEL_URL_HOSTS = {"channels.weixin.qq.com", "finder.video.qq.com"}
CHANNEL_HINTS = ("channels.weixin.qq.com", "finder.video.qq.com", "weixin.qq.com/channels", "视频号", "wechat channels")


@dataclass(slots=True)
class WeChatVideoExtractor:
    """Create BookmarkItems for WeChat Channels URLs or uploaded files."""

    allowed_extensions: frozenset[str] = frozenset(VIDEO_EXTENSIONS)

    def extract(self, source: str) -> BookmarkItem:
        source = (source or "").strip()
        if not source:
            raise ValueError("source is required")
        if is_local_video_file(source, self.allowed_extensions):
            return self.extract_file(source)
        return self.extract_url_or_hint(source)

    def extract_file(self, source: str) -> BookmarkItem:
        parsed = urlparse(source)
        raw_path = parsed.path if parsed.scheme == "file" else source
        path = Path(raw_path).expanduser()
        suffix = path.suffix.lower()
        if suffix not in self.allowed_extensions:
            raise ValueError(f"Unsupported WeChat Channels file type: {suffix or 'unknown'}")
        asset = BookmarkAsset(url=source, kind="video", title=path.name, local_path=str(path), metadata={"extension": suffix})
        return BookmarkItem(
            url=source,
            platform=Platform.WECHAT_CHANNELS,
            source_type=SourceType.WECHAT_CHANNELS_FILE,
            title=path.name or "WeChat Channels video file",
            content="Local WeChat Channels video file is ready for audio extraction/transcription.",
            assets=[asset],
            status="fetched",
            metadata={"input_kind": "file", "requires_upload": False, "extension": suffix, "exists": path.exists()},
        )

    def extract_url_or_hint(self, source: str) -> BookmarkItem:
        if not is_wechat_channels_hint(source):
            raise ValueError(f"Unsupported WeChat Channels source: {source}")
        return BookmarkItem(
            url=source,
            platform=Platform.WECHAT_CHANNELS,
            source_type=SourceType.WECHAT_CHANNELS_VIDEO,
            title="WeChat Channels video",
            content="WeChat Channels links do not have a supported public downloader; ask the user to upload the video file.",
            status="error",
            errors=["WeChat Channels URL requires upload of a user-provided video file for processing"],
            metadata={"input_kind": "url_or_hint", "requires_upload": True, "download_supported": False},
        )


def is_local_video_file(source: str, extensions: Iterable[str] = VIDEO_EXTENSIONS) -> bool:
    parsed = urlparse((source or "").strip())
    if parsed.scheme and parsed.scheme != "file":
        return False
    raw_path = parsed.path if parsed.scheme == "file" else source
    return Path(raw_path).suffix.lower() in set(extensions)


def is_wechat_channels_hint(source: str) -> bool:
    source = (source or "").strip()
    parsed = urlparse(source)
    host = parsed.netloc.lower()
    lowered = source.lower()
    return host in CHANNEL_URL_HOSTS or any(hint in lowered for hint in CHANNEL_HINTS)
