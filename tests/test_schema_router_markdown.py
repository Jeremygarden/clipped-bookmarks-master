from clipped_bookmarks.router import route_url
from clipped_bookmarks.schema import Platform, SourceType, UnsupportedPlatformError

WECHAT_SAMPLE = "https://mp.weixin.qq.com/s/ENwXC3hEbXnq-5hGEE6keA"
XHS_SAMPLE = "https://xhslink.cn/o/2HSnq3KBHMZ"
XHS_COLLECTION_SAMPLE = "https://www.xiaohongshu.com/collection/item/68930d3b02f5000000000001?xhsshare=&appuid=5e7f4c87000000000100a104&apptime=1787213955&share_id=b4a00b1e38444f21b696260e9df07c6b&share_channel=copy_link"


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


def test_bilibili_is_unsupported():
    try:
        route_url("https://www.bilibili.com/video/BV1xx411c7mD")
    except UnsupportedPlatformError as exc:
        assert "Bilibili" in str(exc)
    else:
        raise AssertionError("Bilibili should be unsupported")
