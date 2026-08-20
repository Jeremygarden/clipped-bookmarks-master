from scripts.fetch_text import detect_platform, parse_xiaohongshu


def test_fetch_text_detects_xiaohongshu_urls():
    assert detect_platform("https://xhslink.cn/o/abc") == "xiaohongshu"
    assert detect_platform("https://www.xiaohongshu.com/explore/66abcdef000000001f03abcd") == "xiaohongshu"


def test_parse_xiaohongshu_keeps_fetch_text_contract():
    html = '''<html><head>
    <meta property="og:title" content="标题">
    <meta name="description" content="正文 #标签">
    <meta name="author" content="作者">
    </head><body><img src="https://sns-img.xhscdn.com/a.jpg"></body></html>'''
    data = parse_xiaohongshu("https://www.xiaohongshu.com/explore/66abcdef000000001f03abcd?xsec_token=t", html)
    assert data["platform"] == "xiaohongshu"
    assert data["title"] == "标题"
    assert data["author"] == "作者"
    assert data["content"] == "正文 #标签"
    assert data["tags"] == ["标签"]
    assert data["assets"][0]["url"] == "https://sns-img.xhscdn.com/a.jpg"
    assert data["metadata"]["canonical_url"] == "https://www.xiaohongshu.com/explore/66abcdef000000001f03abcd"
    assert data["status"] == "fetched"


def test_parse_xiaohongshu_reports_login_wall():
    data = parse_xiaohongshu("https://www.xiaohongshu.com/explore/66abcdef000000001f03abcd", "<html>请登录后查看</html>")
    assert data["status"] == "error"
    assert data["metadata"]["requires_login"] is True
    assert data["errors"]
