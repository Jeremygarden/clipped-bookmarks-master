# -*- coding: utf-8 -*-
import json

from clipped_bookmarks.extractors.zhihu import extract_zhihu, is_zhihu_url, parse_count


def test_is_zhihu_url_is_host_strict():
    assert is_zhihu_url("https://www.zhihu.com/question/1") is True
    assert is_zhihu_url("https://zhuanlan.zhihu.com/p/1") is True
    assert is_zhihu_url("https://evil.example/?next=zhihu.com/question/1") is False


def test_parse_count_zhihu_units():
    assert parse_count("1,234 赞同") == 1234
    assert parse_count("1.2 万赞同") == 12000
    assert parse_count("3K") == 3000
    assert parse_count("1 万 2 千赞同") == 12000
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


def test_initial_state_accepts_pretty_printed_json_script():
    html = """
    <script id="js-initialData" type="application/json">
    {
      "answers": {"77": {"id": "77", "question": {"title": "格式化问题"}, "content": "<p>格式化正文</p>"}}
    }
    </script>
    """
    data = extract_zhihu(html, "https://www.zhihu.com/question/1/answer/77")
    assert data["title"] == "格式化问题"
    assert "格式化正文" in data["content"]


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



def test_initial_state_dedupes_answer_entities_by_id_across_trees():
    answer = {
        "id": "dup-1",
        "question": {"id": "88", "title": "去重问题"},
        "author": {"name": "重复作者"},
        "content": "<p>同一答案内容。</p>",
        "voteup_count": 11,
    }
    state = {
        "entities": {"answers": {"dup-1": answer}},
        "paging": {"first": [{**answer, "content": "<p>同一答案内容。</p><p>镜像树轻微差异。</p>"}]},
    }
    html = f'<script id="js-initialData" type="application/json">{json.dumps(state, ensure_ascii=False)}</script>'
    data = extract_zhihu(html, "https://www.zhihu.com/question/88")
    assert len(data["extra"]["items"]) == 1
    assert data["extra"]["items"][0]["raw_data"] == {
        "id": "dup-1",
        "type": "answer",
        "url": "",
        "question_id": "88",
    }
    assert data["raw_data"]["item_count"] == 1


def test_raw_data_keys_are_stable_for_article_answer_question_and_wall():
    expected_keys = [
        "url", "content_type", "question_id", "answer_id", "article_id", "primary_id",
        "item_count", "requires_login", "anti_bot", "not_found", "dynamic_fallback", "comments_fallback",
    ]
    cases = [
        ("<article><p>文章 DOM 正文</p></article>", "https://zhuanlan.zhihu.com/p/42"),
        ('<div class="AnswerCard" data-id="7"><div class="RichText"><p>回答 DOM 正文</p></div></div>', "https://www.zhihu.com/question/1/answer/7"),
        ("<h1>空问题</h1>", "https://www.zhihu.com/question/1"),
        ("<html><body>访问异常 请进行验证 403 - Forbidden</body></html>", "https://www.zhihu.com/question/2"),
    ]
    for html, url in cases:
        data = extract_zhihu(html, url)
        assert list(data["raw_data"].keys()) == expected_keys
        assert data["extra"]["raw_data"] == data["raw_data"]


def test_login_wall_and_forbidden_page_markers_are_reported_without_content_fallback():
    html = """
    <html><body>
      <div class="Unhuman">访问异常</div>
      <p>请进行验证后继续访问</p>
      <p>403 - Forbidden</p>
    </body></html>
    """
    data = extract_zhihu(html, "https://www.zhihu.com/question/404")
    assert data["extra"]["requires_login"] is True
    assert data["extra"]["anti_bot"] is True
    assert "访问异常" in data["extra"]["login_wall_markers"]
    assert "请进行验证" in data["extra"]["login_wall_markers"]
    assert data["extra"]["fallbacks"]["content"] == "login_required"
    assert data["raw_data"]["dynamic_fallback"] is False
    assert data["raw_data"]["comments_fallback"] == "login_required"

def test_dom_publish_time_does_not_use_upvote_time_element():
    html = '''
    <h1>问题</h1>
    <div class="AnswerCard" data-id="1">
      <a class="AuthorInfo-name">作者</a>
      <button class="VoteButton--up"><time>1234</time> 赞同</button>
      <div class="RichText"><p>正文足够长。</p></div>
    </div>
    '''
    data = extract_zhihu(html, "https://www.zhihu.com/question/1/answer/1")
    assert data["publish_time"] == ""
    assert data["upvote_count"] == 1234
