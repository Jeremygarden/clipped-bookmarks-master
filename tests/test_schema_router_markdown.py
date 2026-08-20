from clipped_bookmarks.router import route_url
from clipped_bookmarks.schema import Platform, SourceType, UnsupportedPlatformError

WECHAT_SAMPLE = "https://mp.weixin.qq.com/s/ENwXC3hEbXnq-5hGEE6keA"
XHS_SAMPLE = "https://xhslink.cn/o/2HSnq3KBHMZ"
XHS_COLLECTION_SAMPLE = "https://www.xiaohongshu.com/collection/item/68930d3b02f5000000000001?xhsshare=&appuid=5e7f4c87000000000100a104&apptime=1787213955&share_id=b4a00b1e38444f21b696260e9df07c6b&share_channel=copy_link"

ZHIHU_ANSWER_SAMPLE = "https://www.zhihu.com/question/123456/answer/789012"
ZHIHU_ARTICLE_SAMPLE = "https://zhuanlan.zhihu.com/p/123456"


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


def test_routes_xhs_collection_sample():
    item = route_url(XHS_COLLECTION_SAMPLE)
    assert item.platform == Platform.XIAOHONGSHU
    assert item.source_type == SourceType.XIAOHONGSHU_COLLECTION


def test_routes_wechat_channels_local_file():
    item = route_url("/tmp/channel-save.mp4")
    assert item.platform == Platform.WECHAT_CHANNELS
    assert item.source_type == SourceType.WECHAT_CHANNELS_FILE


def test_routes_zhihu_answer_and_article():
    answer = route_url(ZHIHU_ANSWER_SAMPLE)
    article = route_url(ZHIHU_ARTICLE_SAMPLE)
    assert answer.platform == Platform.ZHIHU
    assert answer.source_type == SourceType.ZHIHU_ANSWER
    assert article.platform == Platform.ZHIHU
    assert article.source_type == SourceType.ZHIHU_ARTICLE


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


def test_supported_platform_registry_matches_active_scope():
    from clipped_bookmarks.platforms import ACTIVE_PLATFORM_SCOPE, supported_platforms

    descriptors = supported_platforms()
    assert ACTIVE_PLATFORM_SCOPE == (
        Platform.XIAOHONGSHU,
        Platform.WECHAT_CHANNELS,
        Platform.WECHAT_OFFICIAL_ACCOUNT,
        Platform.ZHIHU,
    )
    assert [descriptor.platform for descriptor in descriptors] == [
        Platform.XIAOHONGSHU,
        Platform.WECHAT_CHANNELS,
        Platform.WECHAT_OFFICIAL_ACCOUNT,
        Platform.ZHIHU,
    ]
    assert all("bilibili" not in descriptor.display_name.lower() for descriptor in descriptors)


def test_bookmark_item_rejects_platform_source_type_mismatch():
    try:
        BookmarkItem(
            url=WECHAT_SAMPLE,
            platform=Platform.ZHIHU,
            source_type=SourceType.WECHAT_ARTICLE,
        )
    except ValueError as exc:
        assert "belongs to platform" in str(exc)
    else:
        raise AssertionError("BookmarkItem should reject mismatched platform/source_type")


def test_bilibili_short_links_are_unsupported():
    for source in ("https://b23.tv/BV1xx411c7mD", "https://bili2233.cn/abc"):
        try:
            route_url(source)
        except UnsupportedPlatformError as exc:
            assert "Bilibili" in str(exc)
        else:
            raise AssertionError(f"Bilibili share link should be unsupported: {source}")


def test_descriptor_for_source_type_maps_active_core_sources():
    from clipped_bookmarks.platforms import descriptor_for_source_type

    assert descriptor_for_source_type(SourceType.ZHIHU_ANSWER).platform == Platform.ZHIHU
    assert descriptor_for_source_type("wechat_channels_file").platform == Platform.WECHAT_CHANNELS
    assert descriptor_for_source_type("unknown") is None
