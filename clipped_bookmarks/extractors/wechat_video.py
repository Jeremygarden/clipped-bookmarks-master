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
from urllib.parse import unquote, urlparse

from clipped_bookmarks.schema import BookmarkAsset, BookmarkItem, Platform, SourceType

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}
FILE_EXTENSIONS = VIDEO_EXTENSIONS | {".mp3", ".m4a", ".wav", ".aac", ".flac", ".srt", ".vtt", ".txt", ".md", ".json"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".aac", ".flac"}
TRANSCRIPT_EXTENSIONS = {".srt", ".vtt", ".txt", ".md", ".json"}
CHANNEL_URL_HOSTS = {"channels.weixin.qq.com", "finder.video.qq.com"}
CHANNEL_HINTS = ("channels.weixin.qq.com", "finder.video.qq.com", "weixin.qq.com/channels", "视频号", "wechat channels")


@dataclass(slots=True)
class WeChatVideoExtractor:
    """Create BookmarkItems for WeChat Channels URLs or uploaded files."""

    allowed_extensions: frozenset[str] = frozenset(FILE_EXTENSIONS)

    def extract(self, source: str) -> BookmarkItem:
        source = (source or "").strip()
        if not source:
            raise ValueError("source is required")
        if is_local_video_file(source, self.allowed_extensions):
            return self.extract_file(source)
        return self.extract_url_or_hint(source)

    def extract_file(self, source: str) -> BookmarkItem:
        path = _local_path_from_source(source)
        suffix = path.suffix.lower()
        if suffix not in self.allowed_extensions:
            raise ValueError(f"Unsupported WeChat Channels file type: {suffix or 'unknown'}")
        kind = _asset_kind(suffix)
        file_metadata = _local_file_metadata(path)
        asset = BookmarkAsset(
            url=source,
            kind=kind,
            title=path.name,
            local_path=str(path),
            metadata={"extension": suffix, **file_metadata},
        )
        return BookmarkItem(
            url=source,
            platform=Platform.WECHAT_CHANNELS,
            source_type=SourceType.WECHAT_CHANNELS_FILE,
            title=path.name or "WeChat Channels uploaded file",
            content=_file_content_message(kind),
            assets=[asset],
            status="fetched",
            metadata={
                "input_kind": "file",
                "requires_upload": False,
                "extension": suffix,
                "exists": path.exists(),
                "asset_kind": kind,
                "download_supported": False,
                **file_metadata,
            },
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


def _local_path_from_source(source: str) -> Path:
    parsed = urlparse((source or "").strip())
    raw_path = parsed.path if parsed.scheme == "file" else source
    return Path(unquote(raw_path)).expanduser()


def _local_file_metadata(path: Path) -> dict[str, object]:
    metadata: dict[str, object] = {"filename": path.name, "stem": path.stem}
    if path.exists() and path.is_file():
        stat = path.stat()
        metadata["size_bytes"] = stat.st_size
        metadata["modified_time"] = int(stat.st_mtime)
    return metadata


def _asset_kind(suffix: str) -> str:
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix in TRANSCRIPT_EXTENSIONS:
        return "transcript"
    return "file"


def _file_content_message(kind: str) -> str:
    if kind == "video":
        return "Local WeChat Channels video file is ready for audio extraction/transcription."
    if kind == "audio":
        return "Local WeChat Channels audio file is ready for transcription."
    if kind == "transcript":
        return "Local WeChat Channels transcript/metadata file is ready for note extraction."
    return "Local WeChat Channels uploaded file metadata is ready for processing."


def is_local_video_file(source: str, extensions: Iterable[str] = FILE_EXTENSIONS) -> bool:
    parsed = urlparse((source or "").strip())
    if parsed.scheme and parsed.scheme != "file":
        return False
    return _local_path_from_source(source).suffix.lower() in set(extensions)


def is_wechat_channels_hint(source: str) -> bool:
    source = (source or "").strip()
    parsed = urlparse(source)
    host = parsed.netloc.lower()
    lowered = source.lower()
    return host in CHANNEL_URL_HOSTS or any(hint in lowered for hint in CHANNEL_HINTS)
