#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_text.py - 收藏夹整理师 · 文字类抓取
抓取知乎 / 微信公众号 等文字内容，初步提取正文与高赞评论。

用法:
    python3 fetch_text.py <url> [--out raw.txt] [--cookies cookies.txt]
输出:
    打印 JSON 到 stdout，同时若指定 --out 则写入文件。
    JSON 字段:
      platform    : zhihu / weixin / unknown
      title       : 标题
      author      : 作者
      publish_time: 发布时间
      content     : 正文纯文本（已去除广告/导航噪声）
      top_comments: [{author, likes, text}] 高赞评论（已初步筛选）
      raw_html_len: 原始 HTML 长度（调试用）
依赖:
    requests, beautifulsoup4, trafilatura(可选)
"""
import sys
import json
import argparse
import re
from datetime import datetime
from http.cookiejar import MozillaCookieJar

try:
    from clipped_bookmarks.extractors.zhihu import extract_zhihu, is_zhihu_url
except ImportError:  # pragma: no cover - keeps standalone script usable
    extract_zhihu = None
    is_zhihu_url = None

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
    if is_zhihu_url is not None and is_zhihu_url(url):
        return "zhihu"
    if is_zhihu_url is None and "zhihu.com" in url:
        return "zhihu"
    if "mp.weixin.qq.com" in url or "weixin.qq.com" in url:
        return "weixin"
    return "unknown"


def _clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fetch_html(url: str, cookies_path: str = None) -> str:
    sess = requests.Session()
    sess.headers.update(HEADERS)
    if cookies_path:
        # Netscape cookie jar 格式
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

    # Minimal fallback if the package import is unavailable.
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
    vote = soup.select_one(".VoteButton--up, .ContentItem-actions [itemprop='upvoteCount']")
    if vote:
        out["upvote_count"] = vote.get("content") or _clean_text(vote.get_text())
    return out


# ---------------- 微信公众号 ----------------
def parse_weixin(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    out = {"platform": "weixin", "title": "", "author": "", "publish_time": "",
           "content": "", "top_comments": [], "raw_html_len": len(html)}

    t = soup.find("h1") or soup.select_one("#activity-name")
    if t:
        out["title"] = _clean_text(t.get_text())

    # 正文
    rich = soup.select_one("#js_content") or soup.select_one(".rich_media_content")
    if rich:
        for bad in rich.select("script, style"):
            bad.decompose()
        paras = [p.get_text(" ", strip=True) for p in rich.find_all(["p", "li", "section"])]
        out["content"] = "\n".join(_clean_text(p) for p in paras if p)

    # 作者 / 时间
    au = soup.select_one("#js_name, .rich_media_meta_text")
    if au:
        out["author"] = _clean_text(au.get_text())
    # 发布时间藏在 js var
    m = re.search(r'var\s+ct\s*=\s*["\']?(\d+)', html)
    if m:
        try:
            out["publish_time"] = datetime.fromtimestamp(int(m.group(1))).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass

    # 公众号文章评论（精选）有时在 #js_comment
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

    platform = detect_platform(args.url)
    try:
        html = fetch_html(args.url, args.cookies)
    except Exception as e:  # noqa
        sys.stderr.write(f"[错误] 抓取失败: {e}\n")
        sys.exit(3)

    if platform == "zhihu":
        data = parse_zhihu(html, args.url)
    elif platform == "weixin":
        data = parse_weixin(html)
    else:
        # 兜底：用 trafilatura 抽取
        try:
            import trafilatura
            txt = trafilatura.extract(html)
            data = {"platform": "unknown", "title": "", "author": "",
                    "publish_time": "", "content": txt or "", "top_comments": [],
                    "raw_html_len": len(html)}
        except Exception:
            data = {"platform": "unknown", "title": "", "author": "",
                    "publish_time": "", "content": "", "top_comments": [],
                    "raw_html_len": len(html)}

    payload = json.dumps(data, ensure_ascii=False, indent=2)
    print(payload)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload)
        sys.stderr.write(f"[ok] 已写入 {args.out}\n")


if __name__ == "__main__":
    main()
