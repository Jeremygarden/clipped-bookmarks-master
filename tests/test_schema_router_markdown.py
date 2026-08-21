from clipped_bookmarks.router import route_url
from clipped_bookmarks.schema import Platform, SourceType, UnsupportedPlatformError

WECHAT_SAMPLE = "https://mp.weixin.qq.com/s/ENwXC3hEbXnq-5hGEE6keA"
XHS_SAMPLE = "https://xhslink.cn/o/2HSnq3KBHMZ"
XHS_COLLECTION_SAMPLE = "https://www.xiaohongshu.com/collection/item/68930d3b02f5000000000001?xhsshare=&appuid=5e7f4c87000000000100a104&apptime=1787213955&share_id=b4a00b1e38444f21b696260e9df07c6b&share_channel=copy_link"


def test_routes_zhihu_answer_sample():
    item = route_url("https://www.zhihu.com/question/633780178/answer/1997868452766058023")
    assert item.platform == Platform.ZHIHU
    assert item.source_type == SourceType.ZHIHU_ANSWER


def test_routes_wechat_article_sample():
    item = route_url(WECHAT_SAMPLE)
    assert item.platform == Platform.WECHAT_OFFICIAL_ACCOUNT
    assert item.source_type == SourceType.WECHAT_ARTICLE
    assert item.url == WECHAT_SAMPLE


def test_routes_xhs_short_link_sample_as_note_requiring_expansion():
    item = route_url(XHS_SAMPLE)
    assert item.platform == Platform.XIAOHONGSHU
    assert item.source_type == SourceType.XIAOHONGSHU_NOTE
    assert item.metadata["requires_expansion"] is True


def test_routes_xhslink_com_short_link_as_note_requiring_expansion():
    item = route_url("https://xhslink.com/a/abc")
    assert item.platform == Platform.XIAOHONGSHU
    assert item.source_type == SourceType.XIAOHONGSHU_NOTE
    assert item.metadata["requires_expansion"] is True


def test_routes_xhs_collection_sample():
    item = route_url(XHS_COLLECTION_SAMPLE)
    assert item.platform == Platform.XIAOHONGSHU
    assert item.source_type == SourceType.XIAOHONGSHU_COLLECTION


def test_routes_wechat_channels_local_file():
    item = route_url("/tmp/channel-save.mp4")
    assert item.platform == Platform.WECHAT_CHANNELS
    assert item.source_type == SourceType.WECHAT_CHANNELS_FILE


def test_bilibili_is_unsupported():
    try:
        route_url("https://www.bilibili.com/video/BV1xx411c7mD")
    except UnsupportedPlatformError as exc:
        assert "Bilibili" in str(exc)
    else:
        raise AssertionError("Bilibili should be unsupported")

from pathlib import Path

from clipped_bookmarks.renderers.markdown import render_markdown
from clipped_bookmarks.renderers.obsidian import ObsidianExportConfig, export_to_obsidian
from clipped_bookmarks.schema import BookmarkItem


def test_markdown_renderer_outputs_yaml_frontmatter():
    item = BookmarkItem(
        url=WECHAT_SAMPLE,
        platform=Platform.WECHAT_OFFICIAL_ACCOUNT,
        source_type=SourceType.WECHAT_ARTICLE,
        title="Sample Article",
        author="Author A",
        published_at="2026-08-20",
        content="Body text",
        tags=["wechat", "bookmark notes"],
    )
    markdown = render_markdown(item)
    assert markdown.startswith("---\n")
    assert 'title: "Sample Article"' in markdown
    assert 'platform: "wechat_official_account"' in markdown
    assert "## Content\n\nBody text" in markdown
    assert "#wechat #bookmark-notes" in markdown


def test_obsidian_export_requires_confirmation(tmp_path: Path):
    item = route_url(WECHAT_SAMPLE)
    item.title = "Needs Confirmation"
    config = ObsidianExportConfig(vault_path=tmp_path)
    try:
        export_to_obsidian(item, config)
    except PermissionError as exc:
        assert "confirm=True" in str(exc)
    else:
        raise AssertionError("Obsidian export should require explicit confirmation")

    written = export_to_obsidian(item, config, confirm=True)
    assert written.exists()
    assert written.parent == tmp_path / "Clipped Bookmarks"

from clipped_bookmarks.cli import main as cli_main


def test_cli_renders_markdown_to_stdout(capsys):
    code = cli_main([WECHAT_SAMPLE])
    captured = capsys.readouterr()
    assert code == 0
    assert 'source_type: "wechat_article"' in captured.out
    assert WECHAT_SAMPLE in captured.out


def test_cli_rejects_unsupported_bilibili(capsys):
    code = cli_main(["https://www.bilibili.com/video/BV1xx411c7mD"])
    captured = capsys.readouterr()
    assert code == 2
    assert "Bilibili" in captured.err


def test_cli_obsidian_requires_confirmation(tmp_path: Path, capsys):
    code = cli_main([WECHAT_SAMPLE, "--obsidian-vault", str(tmp_path)])
    captured = capsys.readouterr()
    assert code == 4
    assert "confirm=True" in captured.err

    code = cli_main([WECHAT_SAMPLE, "--obsidian-vault", str(tmp_path), "--confirm-obsidian"])
    assert code == 0
    assert list((tmp_path / "Clipped Bookmarks").glob("*.md"))


def test_router_host_matching_rejects_xiaohongshu_suffix_spoof():
    for url in ["https://notxiaohongshu.com/explore/66abcdef000000001f03abcd", "https://notxhslink.com/a/abc"]:
        try:
            route_url(url)
        except UnsupportedPlatformError:
            pass
        else:
            raise AssertionError(f"spoofed host should be unsupported: {url}")
