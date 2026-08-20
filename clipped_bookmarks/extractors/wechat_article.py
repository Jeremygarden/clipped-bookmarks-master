# -*- coding: utf-8 -*-
"""WeChat Official Account article extractor returning BookmarkItem-compatible raw data."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import unquote

from bs4 import BeautifulSoup, Tag

PLATFORM = "weixin"
RISK_PATTERNS = {
    "requires_login": ("请在微信客户端打开", "请使用微信扫描二维码", "登录", "login"),
    "anti_bot": ("环境异常", "访问过于频繁", "安全验证", "captcha", "操作频繁", "请输入验证码"),
    "deleted_or_unavailable": ("该内容已被发布者删除", "此内容因违规无法查看", "此内容已被删除", "内容已过期", "页面不存在"),
    "empty_article": ("当前页面无法打开", "获取内容失败"),
}
PROMO_TEXT_PATTERNS = (
    r"长按(?:识别)?(?:上方|下方)?二维码", r"扫码(?:关注|添加|进群|回复)",
    r"扫描(?:上方|下方)?二维码", r"关注(?:公众号|我们|我吧)",
    r"点击(?:上方|下方)?蓝字关注", r"星标(?:我们|本公众号)",
    r"商务合作", r"广告合作", r"转载(?:须|请)联系", r"点赞[、，]?在看[、，]?转发",
)
QR_IMAGE_PATTERNS = ("qrcode", "qr_code", "barcode", "二维码")
COMMENT_SELECTORS = ("#js_comment .comment_item", "#js_comment .comment-card", ".appmsg_comment .comment_item", ".comment_item")


def clean_text(value: str) -> str:
    return re.sub(r"[ \t\r\f\v]+", " ", value or "").strip()


def compact_text(value: str) -> str:
    lines = [clean_text(line) for line in re.split(r"[\n\u2028]+", value or "")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(line for line in lines if line)).strip()


def _json_loads(candidate: str) -> Optional[Any]:
    try:
        return json.loads(candidate)
    except Exception:
        return None


def _script_var(html: str, names: Iterable[str]) -> str:
    for name in names:
        m = re.search(rf"(?:var\s+|window\.)?{re.escape(name)}\s*=\s*(['\"])(.*?)\1", html, re.S)
        if m:
            return clean_text(unquote(m.group(2)))
        m = re.search(rf"(?:var\s+|window\.)?{re.escape(name)}\s*=\s*(\d+)", html)
        if m:
            return m.group(1)
    return ""


def _timestamp(value: Any) -> str:
    text = clean_text(str(value or ""))
    if not text:
        return ""
    if re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", text):
        return text.replace("/", "-")[:16]
    try:
        ivalue = int(float(text))
    except Exception:
        return ""
    if ivalue > 10_000_000_000:
        ivalue //= 1000
    return datetime.fromtimestamp(ivalue).strftime("%Y-%m-%d %H:%M") if ivalue > 0 else ""


def _meta(soup: BeautifulSoup, *names: str) -> str:
    for name in names:
        node = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        if node and node.get("content"):
            return clean_text(node.get("content", ""))
    return ""


def extract_title(soup: BeautifulSoup, html: str) -> str:
    for selector in ("#activity-name", "h1.rich_media_title", "h1", ".rich_media_title"):
        node = soup.select_one(selector)
        if node:
            title = clean_text(node.get_text(" ", strip=True))
            if title:
                return title
    title = _meta(soup, "og:title", "twitter:title") or _script_var(html, ("msg_title", "title"))
    if not title and soup.title:
        title = clean_text(soup.title.get_text(" ", strip=True))
    return re.sub(r"\s*[|_-]\s*微信公众平台\s*$", "", title or "").strip()


def extract_author(soup: BeautifulSoup, html: str) -> str:
    for selector in ("#js_name", "#profileBt .profile_nickname", ".profile_nickname", ".rich_media_meta_nickname"):
        node = soup.select_one(selector)
        if node:
            author = clean_text(node.get_text(" ", strip=True))
            if author:
                return author
    return _meta(soup, "author", "og:article:author") or _script_var(html, ("nickname", "user_name"))


def extract_publish_time(soup: BeautifulSoup, html: str) -> str:
    for selector in ("#publish_time", "em#publish_time", ".rich_media_meta_text"):
        node = soup.select_one(selector)
        if node:
            text = clean_text(node.get_text(" ", strip=True))
            if re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", text):
                return _timestamp(text)
    return _timestamp(_meta(soup, "article:published_time", "publishdate", "pubdate", "date") or _script_var(html, ("ct", "publish_time", "ori_create_time")))


def _node_text(node: Tag) -> str:
    return clean_text(node.get_text(" ", strip=True))


def _looks_like_promo(text: str) -> bool:
    return bool(text and any(re.search(pattern, text, re.I) for pattern in PROMO_TEXT_PATTERNS))


def _looks_like_qr_image(node: Tag) -> bool:
    attrs = " ".join(str(node.get(attr, "")) for attr in ("src", "data-src", "data-original", "alt", "class", "id")).lower()
    return any(pattern in attrs for pattern in QR_IMAGE_PATTERNS)


def _remove_noise(root: Tag) -> Dict[str, int]:
    removed = {"hidden": 0, "script_style": 0, "promo_blocks": 0, "qr_blocks": 0}
    for bad in list(root.select("script, style, noscript, iframe, mp-common-profile, wx-open-launch-app")):
        bad.decompose(); removed["script_style"] += 1
    for node in list(root.find_all(True)):
        style = (node.get("style") or "").lower().replace(" ", "")
        if "display:none" in style or "visibility:hidden" in style or node.get("hidden") is not None:
            node.decompose(); removed["hidden"] += 1
    for node in list(root.find_all(["p", "section", "div"])):
        if not node.parent:
            continue
        text = _node_text(node)
        imgs = node.find_all("img")
        if len(text) <= 120 and _looks_like_promo(text):
            node.decompose(); removed["promo_blocks"] += 1
        elif imgs and len(text) <= 80 and any(_looks_like_qr_image(img) for img in imgs):
            node.decompose(); removed["qr_blocks"] += 1
    return removed


def extract_content(soup: BeautifulSoup) -> Dict[str, Any]:
    root = soup.select_one("#js_content") or soup.select_one(".rich_media_content") or soup.select_one("article")
    if not root:
        return {"content": "", "cleaning": {}}
    clone_soup = BeautifulSoup(str(root), "html.parser")
    clone_root = clone_soup.select_one("#js_content") or clone_soup.select_one(".rich_media_content") or clone_soup
    cleaning = _remove_noise(clone_root)
    blocks, seen = [], set()
    for node in clone_root.find_all(["p", "li", "blockquote", "h2", "h3"]):
        text = _node_text(node)
        if text and text not in seen and not _looks_like_promo(text):
            seen.add(text); blocks.append(text)
    if not blocks:
        blocks = [line for line in (clean_text(x) for x in clone_root.get_text("\n", strip=True).splitlines()) if line and not _looks_like_promo(line)]
    return {"content": compact_text("\n".join(blocks)), "cleaning": cleaning}


def _normalise_image_url(value: str) -> str:
    value = clean_text(value)
    return "https:" + value if value.startswith("//") else value


def extract_images(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    root = soup.select_one("#js_content") or soup.select_one(".rich_media_content") or soup
    images, seen = [], set()
    for img in root.find_all("img"):
        src = _normalise_image_url(img.get("data-src") or img.get("data-original") or img.get("src") or "")
        if not src or src.startswith("data:") or src in seen:
            continue
        seen.add(src)
        parent_text = _node_text(img.parent) if isinstance(img.parent, Tag) else ""
        if _looks_like_qr_image(img) or (len(parent_text) <= 100 and _looks_like_promo(parent_text)):
            continue
        alt = clean_text(img.get("alt") or "")
        images.append({"url": src, "alt": alt, "index": len(images), "source_attr": "data-src" if img.get("data-src") else "src", "needs_ocr": alt == "", "ocr_hook": {"enabled": False, "reason": "image_text_ocr_not_implemented"}})
    for node in root.find_all(style=True):
        for _, raw in re.findall(r"url\((['\"]?)(.*?)\1\)", node.get("style") or ""):
            src = _normalise_image_url(raw)
            if src and not src.startswith("data:") and src not in seen:
                seen.add(src)
                images.append({"url": src, "alt": "", "index": len(images), "source_attr": "style.background-image", "needs_ocr": True, "ocr_hook": {"enabled": False, "reason": "image_text_ocr_not_implemented"}})
    return images


def _parse_like_count(text: str) -> int:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(万|千|k|K)?", clean_text(text))
    if not m:
        return 0
    value = float(m.group(1)); unit = m.group(2)
    if unit == "万": value *= 10000
    elif unit in {"千", "k", "K"}: value *= 1000
    return int(value)


def extract_comments(soup: BeautifulSoup, html: str) -> Dict[str, Any]:
    comments = []
    for selector in COMMENT_SELECTORS:
        for node in soup.select(selector):
            text_node = node.select_one(".comment_content, .comment_text, .discuss_message, .comment_detail") or node
            text = clean_text(text_node.get_text(" ", strip=True))
            if len(text) < 6: continue
            author_node = node.select_one(".nickname, .comment_nickname, .user_name")
            like_node = node.select_one(".like_num, .comment_like_num, [class*='like']")
            comments.append({"author": clean_text(author_node.get_text(" ", strip=True)) if author_node else "", "likes": _parse_like_count(like_node.get_text(" ", strip=True)) if like_node else _parse_like_count(text), "text": text[:500]})
    for m in re.finditer(r"comment(?:_list|List)?\s*[:=]\s*(\[.*?\])", html, re.S):
        data = _json_loads(m.group(1))
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    text = clean_text(str(item.get("content") or item.get("text") or item.get("comment") or ""))
                    if len(text) >= 6:
                        comments.append({"author": clean_text(str(item.get("nick_name") or item.get("nickname") or item.get("author") or "")), "likes": _parse_like_count(str(item.get("like_num") or item.get("like_count") or 0)), "text": text[:500]})
    deduped, seen = [], set()
    for comment in comments:
        key = (comment["author"], comment["text"])
        if key not in seen:
            seen.add(key); deduped.append(comment)
    deduped.sort(key=lambda item: item["likes"], reverse=True)
    status = "extracted" if deduped else ("unavailable_in_static_html" if "精选留言" in html or "js_comment" in html else "not_present")
    return {"comments": deduped[:5], "status": status}


def detect_risks(html: str, soup: BeautifulSoup, content: str) -> List[str]:
    haystack = (html[:200000] + " " + soup.get_text(" ", strip=True)[:5000]).lower()
    flags = [flag for flag, patterns in RISK_PATTERNS.items() if any(pattern.lower() in haystack for pattern in patterns)]
    if not content and (soup.select_one("#js_content") is None or len(soup.get_text(" ", strip=True)) < 200):
        flags.append("empty_article")
    return sorted(set(flags))


def extract_wechat_article(html: str, url: str = "") -> Dict[str, Any]:
    soup = BeautifulSoup(html or "", "html.parser")
    title, author = extract_title(soup, html or ""), extract_author(soup, html or "")
    publish_time = extract_publish_time(soup, html or "")
    content_result = extract_content(soup); content = content_result["content"]
    images = extract_images(soup); comment_result = extract_comments(soup, html or "")
    risk_flags = detect_risks(html or "", soup, content)
    raw_data = {"url": url, "source_url": url, "canonical_url": _meta(soup, "og:url") or url, "platform": PLATFORM, "title": title, "author": author, "publish_time": publish_time, "content": content, "images": images, "top_comments": comment_result["comments"], "risk_flags": risk_flags, "comment_status": comment_result["status"]}
    return {"platform": PLATFORM, "title": title, "author": author, "publish_time": publish_time, "content": content, "top_comments": comment_result["comments"], "raw_html_len": len(html or ""), "images": images, "risk_flags": risk_flags, "raw_data": raw_data, "extra": {"content_type": "wechat_article", "comment_status": comment_result["status"], "cleaning": content_result["cleaning"], "image_ocr_hook": "images[].ocr_hook", "requires_login": "requires_login" in risk_flags, "anti_bot": "anti_bot" in risk_flags, "sample_url_supported": "mp.weixin.qq.com/s/" in url}}
