# -*- coding: utf-8 -*-
import json
from clipped_bookmarks.extractors.wechat_article import extract_wechat_article
SAMPLE_URL = "https://mp.weixin.qq.com/s/ENwXC3hEbXnq-5hGEE6keA"

def test_wechat_article_extracts_core_fields_images_and_raw_data():
    html = '''<html><head><meta property="og:title" content="备用标题" /><meta property="og:description" content="文章摘要" /><meta property="og:url" content="https://mp.weixin.qq.com/s/canonical" /><script>var ct = "1700000000"; var nickname = "备用号";</script></head><body><h1 id="activity-name"> 公众号文章标题 </h1><span id="js_name"> clipped bookmarks </span><em id="publish_time">2023-11-14 22:13</em><div id="js_content" class="rich_media_content"><p>第一段正文，有明确内容。</p><section><p>第二段正文，保留。</p></section><p>长按识别二维码关注我们</p><section><img data-src="https://mmbiz.qpic.cn/mmbiz_png/article-image?wx_fmt=png" alt="配图" /></section><section><span>扫码关注</span><img data-src="https://mmbiz.qpic.cn/qrcode?wx_fmt=png" alt="二维码" /></section></div><div id="js_comment"><div class="comment_item"><span class="nickname">读者甲</span><span class="like_num">1.2万</span><span class="comment_content">这是一条精选留言，很适合作为 fallback。</span></div></div></body></html>'''
    data = extract_wechat_article(html, SAMPLE_URL)
    assert data["platform"] == "weixin"
    assert data["title"] == "公众号文章标题"
    assert data["author"] == "clipped bookmarks"
    assert data["publish_time"] == "2023-11-14 22:13"
    assert "第一段正文" in data["content"] and "第二段正文" in data["content"]
    assert "二维码" not in data["content"]
    assert data["images"] == [{"url": "https://mmbiz.qpic.cn/mmbiz_png/article-image?wx_fmt=png", "alt": "配图", "index": 0, "source_attr": "data-src", "needs_ocr": False, "ocr_hook": {"enabled": False, "reason": "image_text_ocr_not_implemented"}}]
    assert data["top_comments"][0]["author"] == "读者甲" and data["top_comments"][0]["likes"] == 12000
    assert data["raw_data"]["source_url"] == SAMPLE_URL and data["raw_data"]["images"] == data["images"]
    assert data["raw_data"]["description"] == "文章摘要"
    assert data["extra"]["canonical_url"] == "https://mp.weixin.qq.com/s/canonical"
    assert data["extra"]["content_type"] == "wechat_article" and data["extra"]["image_ocr_hook"] == "images[].ocr_hook"

def test_wechat_article_uses_script_publish_time_and_comment_json_fallback():
    comments = [{"nick_name": "读者乙", "like_num": "88", "content": "隐藏在脚本里的精选留言内容。"}]
    html = f'''<html><head><script>var ct = "1700000000"; var nickname = "脚本公众号"; var comment_list = {json.dumps(comments, ensure_ascii=False)};</script></head><body><h1 id="activity-name">脚本时间标题</h1><div id="js_content"><p>正文内容足够明确。</p><img data-src="//mmbiz.qpic.cn/mmbiz_jpg/no-alt" /></div></body></html>'''
    data = extract_wechat_article(html, SAMPLE_URL)
    assert data["author"] == "脚本公众号"
    assert data["publish_time"] == "2023-11-14 22:13"
    assert data["top_comments"][0] == {"author": "读者乙", "likes": 88, "text": "隐藏在脚本里的精选留言内容。"}
    assert data["images"][0]["url"].startswith("https://") and data["images"][0]["needs_ocr"] is True

def test_wechat_article_detects_empty_login_and_antibot_risks():
    html = "<html><body><div>请在微信客户端打开</div><div>访问过于频繁，请完成安全验证 captcha</div></body></html>"
    data = extract_wechat_article(html, SAMPLE_URL)
    assert data["content"] == ""
    assert {"requires_login", "anti_bot", "empty_article"}.issubset(set(data["risk_flags"]))
    assert data["extra"]["requires_login"] is True and data["extra"]["anti_bot"] is True

def test_wechat_article_deleted_unavailable_flag():
    data = extract_wechat_article("<html><body>该内容已被发布者删除</body></html>", SAMPLE_URL)
    assert "deleted_or_unavailable" in data["risk_flags"]


def test_wechat_article_keeps_metadata_cover_image_when_body_image_missing():
    html = '<html><head><meta property="og:title" content="元数据标题" /><meta property="og:image" content="//mmbiz.qpic.cn/cover.jpg" /></head><body><div id="js_content"><p>只有正文，没有正文图片。</p></div></body></html>'
    data = extract_wechat_article(html, SAMPLE_URL)
    assert data["images"][0]["url"] == "https://mmbiz.qpic.cn/cover.jpg"
    assert data["images"][0]["source_attr"] == "meta.og:image"
    assert data["images"][0]["index"] == 0
