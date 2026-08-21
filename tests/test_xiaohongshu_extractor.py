from __future__ import annotations

from clipped_bookmarks.extractors.xiaohongshu import (
    XiaohongshuExtractor,
    detect_access_wall,
    extract_note_id,
    extract_note_urls_from_html,
    normalize_xhs_url,
    parse_xhs_html,
)
from clipped_bookmarks.schema import Platform, SourceType

XHS_SAMPLE = "https://xhslink.cn/o/2HSnq3KBHMZ"
COLLECTION_SAMPLE = "https://www.xiaohongshu.com/collection/item/68930d3b02f5000000000001?xhsshare=&appuid=5e7f4c87000000000100a104&apptime=1787213955&share_id=b4a00b1e38444f21b696260e9df07c6b&share_channel=copy_link"
NOTE_URL = "https://www.xiaohongshu.com/explore/66abcdef000000001f03abcd?xsec_token=abc&share_id=def"
NOTE_HTML = '''
<html><head>
<meta property="og:title" content="周末徒步路线｜风景很好">
<meta name="description" content="路线记录 #徒步 #周末">
<meta name="author" content="山野小王">
</head><body>
<img src="https://ci.xiaohongshu.com/image-a.jpg?imageView2/2/w/1080">
<script id="__INITIAL_STATE__" type="application/json">{"note":{"video":{"masterUrl":"https://sns-video.xhscdn.com/video-a.mp4"}}}</script>
</body></html>
'''
COLLECTION_HTML = '''
<html><head><title>我的收藏 - 小红书</title></head><body>
<a href="https://www.xiaohongshu.com/explore/66abcdef000000001f03abcd?xsec_token=1">a</a>
<script>{"noteUrl":"https:\\/\\/www.xiaohongshu.com\\/discovery\\/item\\/77abcdef000000001f03abcd?share_id=2"}</script>
</body></html>
'''


class FakeResponse:
    def __init__(self, text="", status_code=200, headers=None, url=None, content=b"bytes"):
        self.text = text
        self.status_code = status_code
        self.headers = headers or {}
        self.url = url
        self.content = content


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


class FakePlaywright:
    def __init__(self, html):
        self.html = html
        self.calls = []

    def fetch_html(self, url):
        self.calls.append(url)
        return self.html


def test_normalize_strips_tracking_query():
    assert normalize_xhs_url(NOTE_URL) == "https://www.xiaohongshu.com/explore/66abcdef000000001f03abcd"


def test_short_link_expands_via_redirect_location():
    session = FakeSession([FakeResponse(status_code=302, headers={"Location": NOTE_URL})])
    extractor = XiaohongshuExtractor(session=session, rate_limit_seconds=0)
    assert extractor.expand_short_link(XHS_SAMPLE) == "https://www.xiaohongshu.com/explore/66abcdef000000001f03abcd"


def test_xhslink_com_short_link_expands_too():
    session = FakeSession([FakeResponse(status_code=302, headers={"Location": NOTE_URL})])
    extractor = XiaohongshuExtractor(session=session, rate_limit_seconds=0)
    assert extractor.expand_short_link("https://xhslink.com/a/abc") == "https://www.xiaohongshu.com/explore/66abcdef000000001f03abcd"



def test_short_link_host_matching_does_not_accept_suffix_spoof():
    session = FakeSession([FakeResponse(status_code=302, headers={"Location": NOTE_URL})])
    extractor = XiaohongshuExtractor(session=session, rate_limit_seconds=0)
    assert extractor.expand_short_link("https://notxhslink.com/a/abc") == "https://notxhslink.com/a/abc"
    assert session.calls == []

def test_parse_note_html_extracts_title_author_tags_and_media():
    parsed = parse_xhs_html(NOTE_HTML)
    assert parsed["title"] == "周末徒步路线｜风景很好"
    assert parsed["author"] == "山野小王"
    assert parsed["tags"] == ["周末", "徒步"]
    assert parsed["images"] == ["https://ci.xiaohongshu.com/image-a.jpg?imageView2/2/w/1080"]
    assert parsed["videos"] == ["https://sns-video.xhscdn.com/video-a.mp4"]


def test_extract_note_prefers_playwright_login_state_before_requests():
    session = FakeSession([FakeResponse(text="should not be used")])
    extractor = XiaohongshuExtractor(session=session, playwright=FakePlaywright(NOTE_HTML), rate_limit_seconds=0)
    item = extractor.extract(NOTE_URL)
    assert item.platform == Platform.XIAOHONGSHU
    assert item.source_type == SourceType.XIAOHONGSHU_NOTE
    assert item.status == "fetched"
    assert item.metadata["note_type"] == "video"
    assert len(item.assets) == 2
    assert session.calls == []


def test_collection_expands_note_urls():
    urls = extract_note_urls_from_html(COLLECTION_HTML)
    assert "https://www.xiaohongshu.com/explore/66abcdef000000001f03abcd" in urls
    assert "https://www.xiaohongshu.com/discovery/item/77abcdef000000001f03abcd" in urls


def test_extract_collection_returns_bookmark_with_note_urls():
    extractor = XiaohongshuExtractor(session=FakeSession([FakeResponse(text=COLLECTION_HTML)]), rate_limit_seconds=0)
    item = extractor.extract(COLLECTION_SAMPLE)
    assert item.source_type == SourceType.XIAOHONGSHU_COLLECTION
    assert item.status == "fetched"
    assert len(item.metadata["note_urls"]) == 2


def test_login_wall_detection_returns_failed_item():
    wall = "<html><body>请登录后查看完整笔记</body></html>"
    extractor = XiaohongshuExtractor(session=FakeSession([FakeResponse(text=wall)]), rate_limit_seconds=0)
    item = extractor.extract(NOTE_URL)
    assert item.status == "error"
    assert item.metadata["requires_login"] is True
    assert item.metadata["xhs_status"] == "login_or_antibot_wall"
    assert detect_access_wall(wall)


def test_download_media_populates_local_path(tmp_path):
    extractor = XiaohongshuExtractor(session=FakeSession([FakeResponse(content=b"img")]), rate_limit_seconds=0)
    item = extractor.extract(NOTE_URL) if False else None
    from clipped_bookmarks.schema import BookmarkAsset

    [asset] = extractor.download_media([BookmarkAsset(url="https://ci.xiaohongshu.com/a.jpg", kind="image")], tmp_path)
    assert asset.local_path
    assert (tmp_path / "xhs_001.jpg").read_bytes() == b"img"


def test_ocr_hook_is_pluggable_and_stubbed():
    assert XiaohongshuExtractor(rate_limit_seconds=0).ocr_image(b"image") is None
    extractor = XiaohongshuExtractor(ocr_hook=lambda b, mime: "识别文本", rate_limit_seconds=0)
    assert extractor.ocr_image(b"image", "image/png") == "识别文本"


def test_parse_json_state_variants_and_media_metadata():
    html = '''<script id="__NEXT_DATA__" type="application/json">{
      "note": {"displayTitle":"JSON标题", "desc":"正文 #标签", "user":{"nickName":"作者"},
        "imageList":[{"urlDefault":"https:\\/\\/sns-img.xhscdn.com\\/abc.jpg?x=1", "width":1080, "height":1440}],
        "video":{"media":{"streamUrl":"https:\\/\\/sns-video.xhscdn.com\\/abc.m3u8", "duration":12}}
      }}
    </script>'''
    parsed = parse_xhs_html(html)
    assert parsed["title"] == "JSON标题"
    assert parsed["author"] == "作者"
    assert parsed["images"] == ["https://sns-img.xhscdn.com/abc.jpg?x=1"]
    assert parsed["videos"] == ["https://sns-video.xhscdn.com/abc.m3u8"]
    assert parsed["image_assets"][0]["metadata"]["width"] == 1080
    assert parsed["video_assets"][0]["metadata"]["duration"] == 12


def test_canonical_search_result_note_url_parsing_and_escaped_collection_url():
    url = "https://www.xiaohongshu.com/search_result/66abcdef000000001f03abcd?xsec_source=pc_feed&xsec_token=t"
    assert normalize_xhs_url(url) == "https://www.xiaohongshu.com/explore/66abcdef000000001f03abcd"
    assert extract_note_id(url) == "66abcdef000000001f03abcd"
    html = r'{"url":"https:\/\/www.xiaohongshu.com\/search_result\/66abcdef000000001f03abcd?xsec_source=pc_feed"}'
    assert extract_note_urls_from_html(html) == ["https://www.xiaohongshu.com/explore/66abcdef000000001f03abcd"]


def test_short_video_url_without_extension_is_kept_from_state():
    html = '''<script id="__INITIAL_STATE__" type="application/json">{
      "note": {"video": {"media": {"h265Url": "https:\\/\\/sns-video.xhscdn.com\\/stream\\/abc?sign=1", "fileSize": 12345}}}
    }</script>'''
    parsed = parse_xhs_html(html)
    assert parsed["videos"] == ["https://sns-video.xhscdn.com/stream/abc?sign=1"]
    assert parsed["video_assets"][0]["metadata"]["fileSize"] == 12345


def test_encoded_redirect_path_collection_urls_are_extracted():
    html = "https://www.xiaohongshu.com/router?redirectPath=https%3A%2F%2Fwww.xiaohongshu.com%2Fexplore%2F66abcdef000000001f03abcd%3Fxsec_token%3Dt"
    assert extract_note_urls_from_html(html) == ["https://www.xiaohongshu.com/explore/66abcdef000000001f03abcd"]

def test_normalize_encoded_redirect_path_to_note_url():
    url = "https://www.xiaohongshu.com/router?redirectPath=https%3A%2F%2Fwww.xiaohongshu.com%2Fdiscovery%2Fitem%2F77abcdef000000001f03abcd%3Fshare_id%3D2"
    assert normalize_xhs_url(url) == "https://www.xiaohongshu.com/discovery/item/77abcdef000000001f03abcd"


def test_rate_limit_wall_is_reported_distinctly_with_retry_hint():
    extractor = XiaohongshuExtractor(session=FakeSession([FakeResponse(text="<html>Too Many Requests</html>")]), rate_limit_seconds=7)
    item = extractor.extract(NOTE_URL)
    assert item.status == "error"
    assert "rate-limit" in item.errors[0]
    assert item.metadata["retry_after"] == 7
