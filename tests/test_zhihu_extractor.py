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
