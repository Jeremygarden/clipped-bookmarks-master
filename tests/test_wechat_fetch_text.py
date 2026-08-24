# -*- coding: utf-8 -*-
import pytest

from clipped_bookmarks.schema import UnsupportedPlatformError
from scripts.fetch_text import detect_platform, parse_weixin


def test_detect_platform_wechat_article():
    assert detect_platform("https://mp.weixin.qq.com/s/ENwXC3hEbXnq-5hGEE6keA") == "weixin"


@pytest.mark.parametrize("source", ["https://channels.weixin.qq.com/video/123", "https://finder.video.qq.com/foo"])
def test_detect_platform_wechat_channels_is_not_article(source):
    with pytest.raises(UnsupportedPlatformError):
        detect_platform(source)


def test_fetch_text_parse_weixin_uses_wechat_extractor():
    html = '''<h1 id="activity-name">标题</h1><span id="js_name">作者</span><script>var ct = "1700000000";</script><div id="js_content"><p>正文</p><img data-src="https://mmbiz.qpic.cn/a.png" /></div>'''
    data = parse_weixin(html, "https://mp.weixin.qq.com/s/ENwXC3hEbXnq-5hGEE6keA")
    assert data["title"] == "标题"
    assert data["author"] == "作者"
    assert data["publish_time"] == "2023-11-14 22:13"
    assert data["content"] == "正文"
    assert data["images"][0]["url"] == "https://mmbiz.qpic.cn/a.png"
    assert data["raw_data"]["platform"] == "weixin"
