import pytest

from clipped_bookmarks.schema import UnsupportedPlatformError
from scripts.fetch_text import detect_platform


def test_fetch_text_routes_wechat_official_account_article():
    assert detect_platform("https://mp.weixin.qq.com/s/ENwXC3hEbXnq-5hGEE6keA") == "weixin"


def test_fetch_text_routes_zhihu_answer_and_article():
    assert detect_platform("https://www.zhihu.com/question/123456/answer/789012") == "zhihu"
    assert detect_platform("https://zhuanlan.zhihu.com/p/123456") == "zhihu"


@pytest.mark.parametrize(
    "source",
    [
        "https://xhslink.cn/o/2HSnq3KBHMZ",
        "https://xhslink.com/a/abc123",
        "/tmp/channel-save.mp4",
        "https://channels.weixin.qq.com/mobile/video?id=abc",
        "https://www.bilibili.com/video/BV1xx411c7mD",
        "https://example.com/post/1",
    ],
)
def test_fetch_text_rejects_non_text_or_out_of_scope_sources(source):
    with pytest.raises(UnsupportedPlatformError):
        detect_platform(source)
