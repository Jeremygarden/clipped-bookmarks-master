# -*- coding: utf-8 -*-
"""Zhihu extractor returning BookmarkItem-compatible raw data.

The project currently stores raw text fetch results as dictionaries consumed by the
existing scripts.  This module keeps that public shape intact while adding Zhihu-
specific fields under ``extra`` so callers can opt in without breaking older
BookmarkItem ingestion.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from bs4 import BeautifulSoup

LOGIN_WALL_PATTERNS = (
    "登录后你可以",
    "登录知乎",
    "注册知乎",
    "安全验证",
    "请完成验证",
    "unhuman",
    "captcha",
    "403 Forbidden",
)

ARTICLE_RE = re.compile(r"(?:zhihu\.com|zhuanlan\.zhihu\.com)/p/(\d+)")
ZVIDEO_RE = re.compile(r"zhihu\.com/zvideo/(\d+)")
PIN_RE = re.compile(r"zhihu\.com/pin/(\d+)")
YANXUAN_RE = re.compile(r"zhihu\.com/(?:market/(?:paid_)?column|xen)/(\d+)")
QUESTION_RE = re.compile(r"zhihu\.com/question/(\d+)(?:/answer/(\d+))?")


def clean_text(value: str) -> str:
    return re.sub(r"[ \t\r\f\v]+", " ", value or "").strip()


def compact_text(value: str) -> str:
    value = re.sub(r"\n{3,}", "\n\n", value or "")
    return "\n".join(clean_text(line) for line in value.splitlines() if clean_text(line))


def parse_count(value: Any) -> Optional[int]:
    """Parse Zhihu count text such as '1,234', '1.2K', '3 万赞同'."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = clean_text(str(value)).replace(",", "")
    if not text:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(万|千|k|K)?", text)
    if not m:
        return None
    number = float(m.group(1))
    unit = m.group(2)
    if unit == "万":
        number *= 10000
    elif unit in {"千", "k", "K"}:
        number *= 1000
    return int(number)


def detect_content_type(url: str, soup: BeautifulSoup) -> str:
    if ZVIDEO_RE.search(url):
        return "video"
    if PIN_RE.search(url):
        return "pin"
    if YANXUAN_RE.search(url):
        return "yanxuan"
    if ARTICLE_RE.search(url):
        return "article"
    question_match = QUESTION_RE.search(url)
    if question_match:
        return "answer" if question_match.group(2) else "question"
    if soup.select_one(".Post-RichTextContainer, article"):
        return "article"
    if soup.select_one(".QuestionHeader, .QuestionPage"):
        return "question"
    return "answer" if soup.select_one(".AnswerCard, .AnswerItem") else "unknown"


def detect_login_wall(html: str, soup: BeautifulSoup) -> Dict[str, Any]:
    body_text = soup.get_text(" ", strip=True)[:4000]
    markers = [p for p in LOGIN_WALL_PATTERNS if p.lower() in (html + body_text).lower()]
    has_modal = bool(soup.select_one(".SignFlow, .Modal, .Captcha, .Unhuman"))
    return {
        "requires_login": bool(markers or has_modal),
        "anti_bot": any(p.lower() in (html + body_text).lower() for p in ("安全验证", "请完成验证", "unhuman", "captcha")),
        "markers": sorted(set(markers)),
    }


def _json_loads(candidate: str) -> Optional[Any]:
    try:
        return json.loads(candidate)
    except Exception:
        return None


def _balanced_json_after(html: str, marker: str) -> str:
    start = html.find(marker)
    if start < 0:
        return ""
    brace = html.find("{", start + len(marker))
    if brace < 0:
        return ""
    depth = 0
    in_string = False
    escape = False
    for pos in range(brace, len(html)):
        ch = html[pos]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return html[brace:pos + 1]
    return ""


def initial_state(html: str) -> Dict[str, Any]:
    """Extract JSON state embedded by Zhihu's server-rendered pages."""
    soup = BeautifulSoup(html, "html.parser")
    for selector in ("#js-initialData", "#initialData"):
        node = soup.select_one(selector)
        if node:
            data = _json_loads(node.get_text(strip=True) or node.string or "")
            if isinstance(data, dict):
                return data
    for marker in ("window.__INITIAL_STATE__", "window.__INITIAL_DATA__"):
        candidate = _balanced_json_after(html, marker)
        data = _json_loads(candidate) if candidate else None
        if isinstance(data, dict):
            return data
    return {}


def iter_dicts(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def strip_html(html_fragment: Any) -> str:
    if not html_fragment:
        return ""
    soup = BeautifulSoup(str(html_fragment), "html.parser")
    for bad in soup.select("script, style, noscript, .Advert, .Promotion, .KfeCollection-PurchaseBtn"):
        bad.decompose()
    blocks = [node.get_text(" ", strip=True) for node in soup.find_all(["p", "li", "blockquote", "h2", "h3"])]
    return compact_text("\n".join(blocks) or soup.get_text("\n", strip=True))


def _author_name(obj: Dict[str, Any]) -> str:
    author = obj.get("author") or obj.get("member") or obj.get("user") or {}
    if isinstance(author, dict):
        return clean_text(author.get("name") or author.get("fullname") or author.get("url_token") or "")
    return clean_text(str(author))


def _timestamp(value: Any) -> str:
    try:
        ivalue = int(value)
    except Exception:
        return ""
    if ivalue <= 0:
        return ""
    return datetime.fromtimestamp(ivalue).strftime("%Y-%m-%d %H:%M")


def _item_from_json(obj: Dict[str, Any], fallback_title: str = "") -> Optional[Dict[str, Any]]:
    content = strip_html(obj.get("content") or obj.get("excerpt") or obj.get("detail") or obj.get("description"))
    if not content and not (obj.get("title") or obj.get("question")):
        return None
    question = obj.get("question") if isinstance(obj.get("question"), dict) else {}
    title = clean_text(obj.get("title") or question.get("title") or fallback_title)
    publish_time = _timestamp(obj.get("created_time") or obj.get("created") or obj.get("updated_time"))
    upvote_count = parse_count(obj.get("voteup_count") or obj.get("upvoteCount") or obj.get("upvote_count") or obj.get("thanks_count"))
    item_type = obj.get("type") or obj.get("content_type") or obj.get("target_type") or ("answer" if question else "article")
    raw_url = obj.get("url") or obj.get("origin_url") or ""
    raw_id = obj.get("id") or obj.get("answer_id") or obj.get("article_id") or ""
    return {
        "type": item_type,
        "id": str(obj.get("id") or obj.get("answer_id") or obj.get("article_id") or ""),
        "title": title,
        "author": _author_name(obj),
        "publish_time": publish_time,
        "upvote_count": upvote_count,
        "content": content,
        "url": raw_url,
        "raw_data": {"id": raw_id, "type": item_type, "url": raw_url},
    }


def json_items(state: Dict[str, Any], fallback_title: str = "") -> List[Dict[str, Any]]:
    seen = set()
    items: List[Dict[str, Any]] = []
    for obj in iter_dicts(state):
        if not any(k in obj for k in ("content", "excerpt", "question", "voteup_count", "created_time")):
            continue
        item = _item_from_json(obj, fallback_title=fallback_title)
        if not item or not item.get("content"):
            continue
        key = (item.get("type"), item.get("id"), item.get("content")[:80])
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
    return items


def dom_items(soup: BeautifulSoup, fallback_title: str = "") -> List[Dict[str, Any]]:
    selectors = [".AnswerCard", ".AnswerItem", ".List-item .ContentItem", ".Post-RichTextContainer", "article"]
    items: List[Dict[str, Any]] = []
    seen_content = set()
    for selector in selectors:
        for node in soup.select(selector):
            for bad in node.select("script, style, noscript, .Advert, .Promotion, .KfeCollection-PurchaseBtn"):
                bad.decompose()
            rich = node.select_one(".RichText, .RichContent-inner, .Post-RichTextContainer") or node
            paras = [p.get_text(" ", strip=True) for p in rich.find_all(["p", "li", "blockquote", "h2", "h3"])]
            content = compact_text("\n".join(paras) or rich.get_text("\n", strip=True))
            if not content or content in seen_content:
                continue
            seen_content.add(content)
            author_node = node.select_one(".AuthorInfo-name, .UserLink-name, [itemprop='name']")
            time_node = node.select_one("meta[itemprop='dateCreated'], meta[itemprop='datePublished'], time")
            vote_node = node.select_one("meta[itemprop='upvoteCount'], .VoteButton--up, button[aria-label*='赞同']")
            publish_time = ""
            if time_node:
                publish_time = clean_text(time_node.get("content") or time_node.get("datetime") or time_node.get_text(" ", strip=True))
            upvote_count = None
            if vote_node:
                upvote_count = parse_count(vote_node.get("content") or vote_node.get("aria-label") or vote_node.get_text(" ", strip=True))
            items.append({
                "type": "article" if "Post" in " ".join(node.get("class", [])) or node.name == "article" else "answer",
                "id": node.get("data-za-extra-module") or node.get("data-id") or "",
                "title": fallback_title,
                "author": clean_text(author_node.get_text(" ", strip=True)) if author_node else "",
                "publish_time": publish_time,
                "upvote_count": upvote_count,
                "content": content,
                "url": "",
                "raw_data": {
                    "id": node.get("data-za-extra-module") or node.get("data-id") or "",
                    "type": "article" if "Post" in " ".join(node.get("class", [])) or node.name == "article" else "answer",
                    "url": "",
                },
            })
    return items


def extract_comments(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    comments: List[Dict[str, Any]] = []
    for node in soup.select(".CommentItem, .List-item[data-type='Comment'], [class*='CommentItem']"):
        text_node = node.select_one(".CommentContent, .RichText") or node
        text = clean_text(text_node.get_text(" ", strip=True))
        if len(text) < 10:
            continue
        author_node = node.select_one(".UserLink-name, .CommentItem-name, [itemprop='name']")
        vote_node = node.select_one(".CommentItem-voteCount, [class*='voteCount']")
        likes = parse_count(vote_node.get_text(" ", strip=True)) if vote_node else parse_count(text)
        comments.append({
            "author": clean_text(author_node.get_text(" ", strip=True)) if author_node else "",
            "likes": likes or 0,
            "text": text[:500],
        })
    comments.sort(key=lambda x: x["likes"], reverse=True)
    return comments[:5]


def extract_zhihu(html: str, url: str = "") -> Dict[str, Any]:
    soup = BeautifulSoup(html or "", "html.parser")
    wall = detect_login_wall(html or "", soup)
    title_node = soup.find("h1") or soup.select_one(".QuestionHeader-title, .Post-Title, title")
    title = clean_text(title_node.get_text(" ", strip=True)) if title_node else ""
    if title.endswith(" - 知乎"):
        title = title[:-4].strip()

    state = initial_state(html or "")
    items = json_items(state, fallback_title=title) + dom_items(soup, fallback_title=title)
    # Dedupe JSON + DOM while preserving order.
    deduped: List[Dict[str, Any]] = []
    seen = set()
    for item in items:
        key = (item.get("id"), item.get("content", "")[:120])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    primary = deduped[0] if deduped else {}
    content = primary.get("content", "") if primary else ""
    if not content:
        rich = soup.select_one(".RichText, .Post-RichTextContainer, .QuestionRichText")
        content = strip_html(str(rich)) if rich else ""

    content_type = detect_content_type(url, soup)
    question_match = QUESTION_RE.search(url or "")
    article_match = ARTICLE_RE.search(url or "")
    zvideo_match = ZVIDEO_RE.search(url or "")
    pin_match = PIN_RE.search(url or "")
    yanxuan_match = YANXUAN_RE.search(url or "")
    has_comment_dom = bool(soup.select_one(".CommentItem, [class*='CommentItem']"))
    dynamic_fallback = not bool(deduped) and not wall["requires_login"]
    if has_comment_dom:
        comments_fallback = "dom"
    elif wall["requires_login"] or wall["anti_bot"]:
        comments_fallback = "login_required"
    else:
        comments_fallback = "api_or_dynamic_required"

    extra = {
        "content_type": content_type,
        "question_id": question_match.group(1) if question_match else "",
        "answer_id": question_match.group(2) if question_match and question_match.group(2) else (primary.get("id", "") if content_type == "answer" else ""),
        "article_id": article_match.group(1) if article_match else (primary.get("id", "") if content_type == "article" else ""),
        "video_id": zvideo_match.group(1) if zvideo_match else (primary.get("id", "") if content_type == "video" else ""),
        "pin_id": pin_match.group(1) if pin_match else (primary.get("id", "") if content_type == "pin" else ""),
        "yanxuan_id": yanxuan_match.group(1) if yanxuan_match else (primary.get("id", "") if content_type == "yanxuan" else ""),
        "upvote_count": primary.get("upvote_count"),
        "items": deduped,
        "requires_login": wall["requires_login"],
        "anti_bot": wall["anti_bot"],
        "login_wall_markers": wall["markers"],
        "dynamic_fallback": dynamic_fallback,
        "comments_fallback": comments_fallback,
        "fallbacks": {
            "content": "json_or_dom" if deduped else ("login_required" if wall["requires_login"] else "dynamic_required"),
            "comments": comments_fallback,
        },
        "raw_data": {
            "url": url,
            "content_type": content_type,
            "question_id": question_match.group(1) if question_match else "",
            "answer_id": question_match.group(2) if question_match and question_match.group(2) else (primary.get("id", "") if content_type == "answer" else ""),
            "article_id": article_match.group(1) if article_match else (primary.get("id", "") if content_type == "article" else ""),
            "video_id": zvideo_match.group(1) if zvideo_match else (primary.get("id", "") if content_type == "video" else ""),
            "pin_id": pin_match.group(1) if pin_match else (primary.get("id", "") if content_type == "pin" else ""),
            "yanxuan_id": yanxuan_match.group(1) if yanxuan_match else (primary.get("id", "") if content_type == "yanxuan" else ""),
            "item_count": len(deduped),
            "requires_login": wall["requires_login"],
            "anti_bot": wall["anti_bot"],
            "dynamic_fallback": dynamic_fallback,
            "comments_fallback": comments_fallback,
        },
    }

    return {
        "platform": "zhihu",
        "title": title or primary.get("title", ""),
        "author": primary.get("author", ""),
        "publish_time": primary.get("publish_time", ""),
        "upvote_count": primary.get("upvote_count"),
        "content": content,
        "top_comments": extract_comments(soup),
        "raw_html_len": len(html or ""),
        "raw_data": extra["raw_data"],
        "extra": extra,
    }


# Backwards-compatible alias for scripts/tests that expect parse-style naming.
def parse_zhihu(html: str, url: str = "") -> Dict[str, Any]:
    return extract_zhihu(html, url=url)
