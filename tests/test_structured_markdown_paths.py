from pathlib import Path

from clipped_bookmarks.extractors.wechat_article import extract_wechat_article
from clipped_bookmarks.extractors.wechat_video import WeChatVideoExtractor
from clipped_bookmarks.renderers.markdown import render_structured_markdown
from clipped_bookmarks.schema import BookmarkAsset, BookmarkItem, Platform, SourceType


def test_wechat_failure_detection_renders_structured_status():
    data = extract_wechat_article("<html><body>请在微信客户端打开 安全验证 captcha</body></html>", "https://mp.weixin.qq.com/s/demo")
    item = BookmarkItem(
        url="https://mp.weixin.qq.com/s/demo",
        platform=Platform.WECHAT_OFFICIAL_ACCOUNT,
        source_type=SourceType.WECHAT_ARTICLE,
        title=data["title"] or "WeChat article",
        content=data["content"],
        status="error" if data["risk_flags"] else "fetched",
        errors=data["risk_flags"],
    )
    md = render_structured_markdown(item)
    assert "## Extraction Status" in md
    assert "- Failure: anti_bot" in md
    assert "- Failure: requires_login" in md
    assert "_Content has not been fetched yet._" in md


def test_local_transcript_fixture_renders_timestamped_video_note(tmp_path: Path):
    fixture = Path("tests/fixtures/wechat_channel_transcript.srt")
    transcript = tmp_path / fixture.name
    transcript.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
    item = WeChatVideoExtractor().extract(str(transcript))
    md = render_structured_markdown(item)
    expected = Path("tests/snapshots/wechat_channel_transcript_note.md").read_text(encoding="utf-8")
    assert md == expected.replace("{TRANSCRIPT_PATH}", str(transcript))
