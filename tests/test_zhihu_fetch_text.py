# -*- coding: utf-8 -*-
import tempfile
from http.cookiejar import MozillaCookieJar, Cookie

from scripts.fetch_text import fetch_html, parse_zhihu


def test_fetch_text_parse_zhihu_uses_extractor():
    html = '<h1>标题</h1><div class="AnswerCard"><a class="AuthorInfo-name">作者</a><meta itemprop="upvoteCount" content="7"/><div class="RichText"><p>正文</p></div></div>'
    data = parse_zhihu(html, "https://www.zhihu.com/question/1/answer/2")
    assert data["upvote_count"] == 7
    assert data["publish_time"] == ""
    assert data["content"] == "正文"


def test_fetch_html_loads_netscape_cookiejar(monkeypatch):
    cookie = Cookie(
        version=0, name="z_c0", value="token", port=None, port_specified=False,
        domain=".zhihu.com", domain_specified=True, domain_initial_dot=True,
        path="/", path_specified=True, secure=False, expires=None, discard=True,
        comment=None, comment_url=None, rest={}, rfc2109=False,
    )
    jar = MozillaCookieJar()
    jar.set_cookie(cookie)
    with tempfile.NamedTemporaryFile("w+", delete=True) as f:
        jar.filename = f.name
        jar.save(ignore_discard=True, ignore_expires=True)

        captured = {}

        class FakeResponse:
            text = "ok"
            apparent_encoding = "utf-8"
            encoding = "utf-8"

        class FakeSession:
            def __init__(self):
                from requests.cookies import RequestsCookieJar
                self.headers = {}
                self.cookies = RequestsCookieJar()

            def get(self, url, timeout):
                captured["cookies"] = self.cookies.get_dict(domain=".zhihu.com") or self.cookies.get_dict()
                return FakeResponse()

        import scripts.fetch_text as ft
        monkeypatch.setattr(ft.requests, "Session", FakeSession)
        assert fetch_html("https://www.zhihu.com/question/1", f.name) == "ok"
        assert captured["cookies"].get("z_c0") == "token"
