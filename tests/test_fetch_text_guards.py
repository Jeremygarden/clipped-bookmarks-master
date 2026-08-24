# -*- coding: utf-8 -*-
import pytest

from scripts.fetch_text import fetch_html


class FakeResponse:
    def __init__(self, text="<html><body>ok</body></html>", status_error=None, content_type="text/html"):
        self.text = text
        self.apparent_encoding = "utf-8"
        self.encoding = "utf-8"
        self.headers = {"content-type": content_type}
        self._status_error = status_error

    def raise_for_status(self):
        if self._status_error:
            raise self._status_error


class FakeSession:
    def __init__(self, response):
        self.headers = {}
        self.cookies = {}
        self.response = response

    def get(self, url, timeout):
        return self.response


def patch_session(monkeypatch, response):
    import scripts.fetch_text as ft

    monkeypatch.setattr(ft.requests, "Session", lambda: FakeSession(response))


def test_fetch_html_raises_for_http_status(monkeypatch):
    patch_session(monkeypatch, FakeResponse(status_error=RuntimeError("404")))
    with pytest.raises(RuntimeError, match="404"):
        fetch_html("https://www.zhihu.com/question/1")


def test_fetch_html_rejects_non_html_content_type(monkeypatch):
    patch_session(monkeypatch, FakeResponse(text='{"ok":true}', content_type="application/json"))
    with pytest.raises(RuntimeError, match="非 HTML"):
        fetch_html("https://www.zhihu.com/question/1")


def test_fetch_html_rejects_login_wall(monkeypatch):
    patch_session(monkeypatch, FakeResponse(text="<html><body>登录后查看完整内容</body></html>"))
    with pytest.raises(RuntimeError, match="登录墙"):
        fetch_html("https://www.zhihu.com/question/1")


def test_fetch_html_rejects_anti_bot(monkeypatch):
    patch_session(monkeypatch, FakeResponse(text="<html><body>请完成验证 captcha</body></html>"))
    with pytest.raises(RuntimeError, match="反爬"):
        fetch_html("https://www.zhihu.com/question/1")
