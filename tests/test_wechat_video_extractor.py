from clipped_bookmarks.extractors.wechat_video import WeChatVideoExtractor, is_local_video_file, is_wechat_channels_hint
from clipped_bookmarks.schema import Platform, SourceType


def test_local_video_file_becomes_fetched_bookmark_item(tmp_path):
    video = tmp_path / "channel-save.mp4"
    video.write_bytes(b"fake mp4")
    item = WeChatVideoExtractor().extract(str(video))
    assert item.platform == Platform.WECHAT_CHANNELS
    assert item.source_type == SourceType.WECHAT_CHANNELS_FILE
    assert item.status == "fetched"
    assert item.metadata["requires_upload"] is False
    assert item.metadata["exists"] is True
    assert item.assets[0].kind == "video"
    assert item.assets[0].local_path == str(video)


def test_file_url_is_recognized_as_local_video():
    assert is_local_video_file("file:///tmp/wechat-channel.mov") is True
    assert is_local_video_file("https://example.com/video.mp4") is False


def test_wechat_channels_url_requires_uploaded_file():
    item = WeChatVideoExtractor().extract("https://channels.weixin.qq.com/video/123")
    assert item.platform == Platform.WECHAT_CHANNELS
    assert item.source_type == SourceType.WECHAT_CHANNELS_VIDEO
    assert item.status == "error"
    assert item.metadata["requires_upload"] is True
    assert item.metadata["download_supported"] is False
    assert "upload" in item.errors[0]


def test_wechat_channels_hint_detection():
    assert is_wechat_channels_hint("微信视频号短视频") is True
    assert is_wechat_channels_hint("https://finder.video.qq.com/foo") is True
    assert is_wechat_channels_hint("https://www.xiaohongshu.com/explore/abc") is False
