# -*- coding: utf-8 -*-
import json

from clipped_bookmarks.extractors.zhihu import extract_zhihu, parse_count


def test_parse_count_zhihu_units():
    assert parse_count("1,234 赞同") == 1234
    assert parse_count("1.2 万赞同") == 12000
    assert parse_count("3K") == 3000
    assert parse_count(42) == 42


def test_answer_extracts_publish_time_and_upvote_separately():
    html = """
    <html><body>
      <h1>为什么要做收藏整理？</h1>
      <div class="AnswerCard" data-id="999">
        <a class="AuthorInfo-name">张三</a>
        <meta itemprop="dateCreated" content="2024-01-02 10:30" />
        <meta itemprop="upvoteCount" content="1234" />
        <div class="RichText"><p>第一段内容。</p><p>第二段内容。</p></div>
      </div>
      <div class="CommentItem"><a class="UserLink-name">李四</a><span class="CommentItem-voteCount">88</span><span class="CommentContent">这个评论真的很有帮助，值得保留。</span></div>
    </body></html>
    """
    data = extract_zhihu(html, "https://www.zhihu.com/question/1/answer/999")
    assert data["platform"] == "zhihu"
    assert data["title"] == "为什么要做收藏整理？"
    assert data["author"] == "张三"
    assert data["publish_time"] == "2024-01-02 10:30"
    assert data["upvote_count"] == 1234
    assert "第一段内容" in data["content"]
    assert data["extra"]["content_type"] == "answer"
    assert data["extra"]["question_id"] == "1"
    assert data["extra"]["answer_id"] == "999"
    assert data["top_comments"][0]["likes"] == 88
    assert data["raw_data"]["url"].endswith("/answer/999")
    assert data["raw_data"]["item_count"] == 1


def test_bookmark_item_compatible_top_level_fields_are_stable():
    data = extract_zhihu("<title>空页面 - 知乎</title>", "https://www.zhihu.com/question/empty")
    for key in ("platform", "title", "author", "publish_time", "content", "top_comments", "raw_html_len", "raw_data", "extra"):
        assert key in data
    assert data["extra"]["dynamic_fallback"] is True


def test_dynamic_and_comment_fallbacks_are_reported_in_extra_and_raw_data():
    data = extract_zhihu('<html><body><div id="root"></div></body></html>', "https://www.zhihu.com/question/404")
    assert data["extra"]["dynamic_fallback"] is True
    assert data["extra"]["comments_fallback"] == "api_or_dynamic_required"
    assert data["extra"]["fallbacks"]["content"] == "dynamic_required"
    assert data["raw_data"]["dynamic_fallback"] is True
    assert data["raw_data"]["comments_fallback"] == "api_or_dynamic_required"


def test_anti_bot_page_reports_login_required_comment_fallback():
    data = extract_zhihu('<html><body>安全验证 请完成验证 captcha</body></html>', "https://www.zhihu.com/question/1")
    assert data["extra"]["requires_login"] is True
    assert data["extra"]["anti_bot"] is True
    assert data["extra"]["comments_fallback"] == "login_required"
    assert data["raw_data"]["anti_bot"] is True


def test_article_from_initial_state():
    state = {
        "entities": {
            "articles": {
                "321": {
                    "id": 321,
                    "type": "article",
                    "title": "知乎文章标题",
                    "author": {"name": "王五"},
                    "created": 1700000000,
                    "voteup_count": 56,
                    "content": "<p>文章正文 A。</p><p>文章正文 B。</p>",
                }
            }
        }
    }
    html = f'<html><body><script id="js-initialData" type="application/json">{json.dumps(state, ensure_ascii=False)}</script></body></html>'
    data = extract_zhihu(html, "https://zhuanlan.zhihu.com/p/321")
    assert data["title"] == "知乎文章标题"
    assert data["author"] == "王五"
    assert data["upvote_count"] == 56
    assert data["extra"]["content_type"] == "article"
    assert data["extra"]["article_id"] == "321"
    assert "文章正文 A" in data["content"]


def test_window_initial_state_balanced_json_with_nested_braces():
    state = {
        "entities": {
            "answers": {
                "55": {
                    "id": "55",
                    "question": {"title": "嵌套问题"},
                    "author": {"name": "作者"},
                    "content": "<p>包含 { 花括号 } 的回答</p>",
                    "upvote_count": "1.5 万",
                }
            }
        }
    }
    html = f'<script>window.__INITIAL_STATE__ = {json.dumps(state, ensure_ascii=False)};</script>'
    data = extract_zhihu(html, "https://www.zhihu.com/question/7/answer/55")
    assert data["upvote_count"] == 15000
    assert "花括号" in data["content"]
    assert data["extra"]["items"][0]["raw_data"]["id"] == "55"


def test_question_multiple_answers_and_login_wall_detection():
    state = {
        "answers": {
            "a1": {"id": "a1", "question": {"title": "问题标题"}, "author": {"name": "甲"}, "content": "<p>答案一</p>", "voteup_count": 3},
            "a2": {"id": "a2", "question": {"title": "问题标题"}, "author": {"name": "乙"}, "content": "<p>答案二</p>", "voteup_count": 9},
        }
    }
    html = f'<h1>问题标题</h1><script id="js-initialData" type="application/json">{json.dumps(state, ensure_ascii=False)}</script><div>登录后你可以查看更多内容</div>'
    data = extract_zhihu(html, "https://www.zhihu.com/question/123")
    assert data["extra"]["content_type"] == "question"
    assert data["extra"]["question_id"] == "123"
    assert len(data["extra"]["items"]) == 2
    assert data["extra"]["requires_login"] is True
    assert data["extra"]["comments_fallback"] == "login_required"
    assert data["raw_data"]["content_type"] == "question"
    assert data["raw_data"]["requires_login"] is True


def test_video_pin_and_yanxuan_urls_report_fallback_ids_and_types():
    video = extract_zhihu('<title>视频页 - 知乎</title><div id="root"></div>', "https://www.zhihu.com/zvideo/456")
    assert video["extra"]["content_type"] == "video"
    assert video["extra"]["video_id"] == "456"
    assert video["raw_data"]["video_id"] == "456"
    assert video["extra"]["fallbacks"]["content"] == "dynamic_required"

    pin = extract_zhihu('<title>想法页 - 知乎</title><div id="root"></div>', "https://www.zhihu.com/pin/789")
    assert pin["extra"]["content_type"] == "pin"
    assert pin["extra"]["pin_id"] == "789"
    assert pin["raw_data"]["pin_id"] == "789"

    yanxuan = extract_zhihu('<title>盐选页 - 知乎</title><div id="root"></div>', "https://www.zhihu.com/market/paid_column/111")
    assert yanxuan["extra"]["content_type"] == "yanxuan"
    assert yanxuan["extra"]["yanxuan_id"] == "111"
    assert yanxuan["raw_data"]["yanxuan_id"] == "111"


def test_zhuanlan_article_url_detected_as_article():
    data = extract_zhihu('<title>专栏页 - 知乎</title><article><p>专栏正文</p></article>', "https://zhuanlan.zhihu.com/p/222")
    assert data["extra"]["content_type"] == "article"
    assert data["extra"]["article_id"] == "222"
    assert data["raw_data"]["article_id"] == "222"


def test_people_and_collection_urls_report_ids_without_fake_content():
    people = extract_zhihu('<title>用户页 - 知乎</title><div id="root"></div>', "https://www.zhihu.com/people/alice")
    assert people["extra"]["content_type"] == "people"
    assert people["extra"]["people_token"] == "alice"
    assert people["raw_data"]["people_token"] == "alice"
    assert people["extra"]["fallbacks"]["content"] == "dynamic_required"

    collection = extract_zhihu('<title>收藏夹 - 知乎</title><div id="root"></div>', "https://www.zhihu.com/collection/12345")
    assert collection["extra"]["content_type"] == "collection"
    assert collection["extra"]["collection_id"] == "12345"
    assert collection["raw_data"]["collection_id"] == "12345"


def test_not_found_page_is_distinct_from_login_or_dynamic_fallback():
    data = extract_zhihu('<html><title>页面不存在 - 知乎</title><body>你似乎来到了没有知识存在的荒原</body></html>', "https://www.zhihu.com/question/404")
    assert data["extra"]["not_found"] is True
    assert data["extra"]["requires_login"] is False
    assert data["extra"]["dynamic_fallback"] is False
    assert data["extra"]["fallbacks"]["content"] == "not_found"
    assert data["raw_data"]["not_found"] is True
