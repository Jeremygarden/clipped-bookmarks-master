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
    lower = url.lower()
    if "bilibili.com" in lower or "b23.tv" in lower:
        return "unsupported"
    if "zhihu.com" in lower:
        return "zhihu"
    if "mp.weixin.qq.com" in lower or "weixin.qq.com" in lower:
        return "weixin"
    if "xiaohongshu.com" in lower or "xhslink.cn" in lower or "xhslink.com" in lower:
        return "xiaohongshu"
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
            cj = requests.cookies.MozillaCookieJar(cookies_path)
            cj.load(ignore_discard=True, ignore_expires=True)
            sess.cookies = cj
        except Exception as e:  # noqa
            sys.stderr.write(f"[警告] 读取 cookies 失败: {e}\n")
    resp = sess.get(url, timeout=30)
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


# ---------------- 知乎 ----------------
def parse_zhihu(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    out = {"platform": "zhihu", "title": "", "author": "", "publish_time": "",
           "content": "", "top_comments": [], "raw_html_len": len(html)}

    # 标题
    t = soup.find("h1")
    if t:
        out["title"] = _clean_text(t.get_text())

    # 回答正文（RichText / 多段落）
    answer = soup.select_one(".AnswerCard, .RichText, .Post-RichTextContainer")
    if answer:
        # 移除广告/推广节点
        for bad in answer.select(".Advert, .Promotion, .KfeCollection-..."):
            bad.decompose()
        paras = [p.get_text(" ", strip=True) for p in answer.find_all(["p", "li"])]
        out["content"] = "\n".join(_clean_text(p) for p in paras if p)

    # 答主与赞同
    au = soup.select_one(".AuthorInfo-name, .UserLink-name")
    if au:
        out["author"] = _clean_text(au.get_text())
    vote = soup.select_one(".VoteButton--up, .ContentItem-actions [itemprop='upvoteCount']")
    if vote:
        out["publish_time"] = _clean_text(vote.get("content", ""))

    # 高赞评论：知乎评论区有 data-vote 或 .CommentItem-voteCount
    comments = []
    for c in soup.select(".CommentItem, .List-item[data-type='Comment']"):
        txt = c.get_text(" ", strip=True)
        # 粗略提取点赞数
        m = re.search(r"(\d[\d,]*)\s*赞|赞同\s*(\d[\d,]*)", txt)
        likes = int(m.group(1).replace(",", "")) if m else 0
        if len(txt) > 15:
            comments.append({"author": "", "likes": likes, "text": _clean_text(txt[:500])})
    # 取点赞最高 5 条
    comments.sort(key=lambda x: x["likes"], reverse=True)
    out["top_comments"] = comments[:5]
    return out


# ---------------- 小红书 ----------------
def parse_xiaohongshu(url: str, html: str) -> dict:
    # Reuse the Xiaohongshu extractor parser without changing the legacy
    # fetch_text JSON contract. Network fetching/cookies still come from this
    # script; the extractor parser handles public HTML/embedded state.
    from clipped_bookmarks.extractors.xiaohongshu import (
        detect_access_wall,
        extract_collection_id,
        extract_note_id,
        extract_note_urls_from_html,
        is_collection_url,
        normalize_xhs_url,
        parse_xhs_html,
    )

    final_url = normalize_xhs_url(url)
    parsed = parse_xhs_html(html)
    wall = detect_access_wall(html)
    note_urls = extract_note_urls_from_html(html) if is_collection_url(final_url) else []
    content = parsed["description"] or parsed["title"] or ""
    if note_urls:
        content = (content + "\n" if content else "") + "\n".join(note_urls)
    status = "error" if wall else "fetched"
    return {
        "platform": "xiaohongshu",
        "title": parsed["title"],
        "author": parsed["author"] or "",
        "publish_time": "",
        "content": content,
        "top_comments": [],
        "raw_html_len": len(html),
        "tags": parsed["tags"],
        "assets": parsed["image_assets"] + parsed["video_assets"],
        "note_urls": note_urls,
        "status": status,
        "errors": [wall] if wall else [],
        "metadata": {
            "canonical_url": final_url,
            "source_type": "xiaohongshu_collection" if is_collection_url(final_url) else "xiaohongshu_note",
            "note_id": extract_note_id(final_url),
            "collection_id": extract_collection_id(final_url),
            "requires_login": bool(wall),
        },
    }


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
    if platform == "unsupported":
        sys.stderr.write("[错误] 不支持的平台：Bilibili/b23.tv 不在当前核心范围内\n")
        sys.exit(2)

    try:
        html = fetch_html(args.url, args.cookies)
    except Exception as e:  # noqa
        sys.stderr.write(f"[错误] 抓取失败: {e}\n")
        sys.exit(3)

    if platform == "zhihu":
        data = parse_zhihu(html)
    elif platform == "weixin":
        data = parse_weixin(html)
    elif platform == "xiaohongshu":
        data = parse_xiaohongshu(args.url, html)
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
