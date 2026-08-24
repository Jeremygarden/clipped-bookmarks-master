#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_text.py - 收藏夹整理师 · 文字类抓取
抓取知乎 / 微信公众号等文字内容，初步提取正文与高赞评论。
"""
import argparse
import json
import re
import sys
from datetime import datetime
from http.cookiejar import MozillaCookieJar
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from clipped_bookmarks.router import route_url
from clipped_bookmarks.schema import Platform, SourceType, UnsupportedPlatformError

try:
    from clipped_bookmarks.extractors.zhihu import extract_zhihu
except ImportError:  # pragma: no cover - keeps standalone script usable
    extract_zhihu = None

try:
    from clipped_bookmarks.extractors.wechat_article import extract_wechat_article
except ImportError:  # pragma: no cover - keeps standalone script usable
    extract_wechat_article = None

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.stderr.write("[错误] 缺少依赖，请运行 bash scripts/install_deps.sh\n")
    sys.exit(2)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def detect_platform(url: str) -> str:
    """Return the fetch_text parser key for supported text URLs.

    Scope is delegated to the shared router so this script stays aligned with the
    product core. Only text-like sources are accepted here: WeChat Official
    Account articles and Zhihu answers/articles.
    """

    item = route_url(url)
    if item.platform == Platform.ZHIHU and item.source_type in {SourceType.ZHIHU_QUESTION, SourceType.ZHIHU_ANSWER, SourceType.ZHIHU_ARTICLE}:
        return "zhihu"
    if item.platform == Platform.WECHAT_OFFICIAL_ACCOUNT and item.source_type == SourceType.WECHAT_ARTICLE:
        return "weixin"
    raise UnsupportedPlatformError(
        f"fetch_text only supports Zhihu and WeChat official account article URLs; "
        f"got {item.platform.value}/{item.source_type.value}"
    )


def _clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def fetch_html(url: str, cookies_path: str = None) -> str:
    sess = requests.Session()
    sess.headers.update(HEADERS)
    if cookies_path:
        try:
            cj = MozillaCookieJar(cookies_path)
            cj.load(ignore_discard=True, ignore_expires=True)
            sess.cookies.update(cj)
        except Exception as e:  # noqa
            sys.stderr.write(f"[警告] 读取 cookies 失败: {e}\n")
    resp = sess.get(url, timeout=30)
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


# ---------------- 知乎 ----------------
def parse_zhihu(html: str, url: str = "") -> dict:
    if extract_zhihu is not None:
        return extract_zhihu(html, url=url)

    soup = BeautifulSoup(html, "html.parser")
    out = {"platform": "zhihu", "title": "", "author": "", "publish_time": "",
           "upvote_count": None, "content": "", "top_comments": [],
           "raw_html_len": len(html), "extra": {"requires_login": False, "anti_bot": False}}
    t = soup.find("h1") or soup.select_one(".QuestionHeader-title, .Post-Title, title")
    if t:
        out["title"] = _clean_text(t.get_text())
    answer = soup.select_one(".AnswerCard, .RichText, .Post-RichTextContainer")
    if answer:
        for bad in answer.select(".Advert, .Promotion, .KfeCollection-PurchaseBtn"):
            bad.decompose()
        paras = [p.get_text(" ", strip=True) for p in answer.find_all(["p", "li"])]
        out["content"] = "\n".join(_clean_text(p) for p in paras if p)
    au = soup.select_one(".AuthorInfo-name, .UserLink-name")
    if au:
        out["author"] = _clean_text(au.get_text())
    vote = soup.select_one("meta[itemprop='upvoteCount'], .VoteButton--up, .ContentItem-actions [itemprop='upvoteCount']")
    if vote:
        out["upvote_count"] = vote.get("content") or _clean_text(vote.get_text())
    return out


# ---------------- 微信公众号 ----------------
def parse_weixin(html: str, url: str = "") -> dict:
    if extract_wechat_article is not None:
        return extract_wechat_article(html, url=url)

    soup = BeautifulSoup(html, "html.parser")
    out = {"platform": "weixin", "title": "", "author": "", "publish_time": "",
           "content": "", "top_comments": [], "raw_html_len": len(html)}

    t = soup.find("h1") or soup.select_one("#activity-name")
    if t:
        out["title"] = _clean_text(t.get_text())

    rich = soup.select_one("#js_content") or soup.select_one(".rich_media_content")
    if rich:
        for bad in rich.select("script, style"):
            bad.decompose()
        paras = [p.get_text(" ", strip=True) for p in rich.find_all(["p", "li", "section"])]
        out["content"] = "\n".join(_clean_text(p) for p in paras if p)

    au = soup.select_one("#js_name, .rich_media_meta_text")
    if au:
        out["author"] = _clean_text(au.get_text())
    m = re.search(r'var\s+ct\s*=\s*["\']?(\d+)', html)
    if m:
        try:
            out["publish_time"] = datetime.fromtimestamp(int(m.group(1))).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass

    for c in soup.select("#js_comment .comment_item, .appmsg_comment"):
        txt = _clean_text(c.get_text(" ", strip=True))
        if len(txt) > 10:
            out["top_comments"].append({"author": "", "likes": 0, "text": txt[:400]})
    out["top_comments"] = out["top_comments"][:5]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", help="原始结果 JSON 输出路径")
    ap.add_argument("--cookies", help="cookies.txt (Netscape 格式)，用于登录态内容")
    args = ap.parse_args()

    try:
        platform = detect_platform(args.url)
    except (UnsupportedPlatformError, ValueError) as e:
        sys.stderr.write(f"[错误] 不支持的来源: {e}\n")
        sys.exit(2)

    try:
        html = fetch_html(args.url, args.cookies)
    except Exception as e:  # noqa
        sys.stderr.write(f"[错误] 抓取失败: {e}\n")
        sys.exit(3)

    if platform == "zhihu":
        data = parse_zhihu(html, args.url)
    elif platform == "weixin":
        data = parse_weixin(html, args.url)
    else:  # pragma: no cover - detect_platform keeps this unreachable
        raise UnsupportedPlatformError(f"Unsupported fetch_text platform: {platform}")

    payload = json.dumps(data, ensure_ascii=False, indent=2)
    print(payload)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload)
        sys.stderr.write(f"[ok] 已写入 {args.out}\n")


if __name__ == "__main__":
    main()
