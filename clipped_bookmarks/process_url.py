"""Minimal local source processor used by end-to-end tests."""
from __future__ import annotations

from pathlib import Path

from .extractors.wechat_article import extract_wechat_article
from .extractors.zhihu import extract_zhihu
from .renderers.markdown import render_markdown
from .schema import BookmarkItem, Platform, SourceType


def process_source(source: str, failed_path: str | Path | None = None) -> str:
    """Process a fixture/local source into rendered Markdown.

    This intentionally avoids network I/O: HTML fixtures are dispatched by filename,
    and transcript text files are converted to a WeChat Channels file item.
    On failure, write a small failed.md report when requested and re-raise.
    """
    try:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(source)
        text = path.read_text(encoding="utf-8")
        name = path.name.lower()
        if "weixin" in name or "wechat" in name:
            data = extract_wechat_article(text, "https://mp.weixin.qq.com/s/fixture")
            item = BookmarkItem(
                url=data.get("url") or "https://mp.weixin.qq.com/s/fixture",
                platform=Platform.WECHAT_OFFICIAL_ACCOUNT,
                source_type=SourceType.WECHAT_ARTICLE,
                title=data.get("title") or "Weixin article",
                author=data.get("author") or None,
                published_at=data.get("publish_time") or None,
                summary=data.get("summary") or None,
                content=data.get("content") or "",
                status="fetched",
            )
        elif "zhihu" in name:
            data = extract_zhihu(text, "https://www.zhihu.com/question/123/answer/456")
            item = BookmarkItem(
                url=data.get("url") or "https://www.zhihu.com/question/123/answer/456",
                platform=Platform.ZHIHU,
                source_type=SourceType.ZHIHU_ANSWER,
                title=data.get("title") or data.get("question_title") or "Zhihu answer",
                author=data.get("author") or None,
                content=data.get("content") or "",
                status="fetched",
            )
        elif name.endswith(".txt"):
            item = BookmarkItem(
                url=path.name,
                platform=Platform.WECHAT_CHANNELS,
                source_type=SourceType.WECHAT_CHANNELS_FILE,
                title=path.stem.replace("_", " ").title(),
                content=text.strip(),
                status="fetched",
                metadata={"input_kind": "transcript_fixture"},
            )
        else:
            raise ValueError(f"Unsupported fixture source: {source}")
        return render_markdown(item)
    except Exception as exc:
        if failed_path is not None:
            failed = Path(failed_path)
            failed.parent.mkdir(parents=True, exist_ok=True)
            failed.write_text(f"# Failed\n\n{type(exc).__name__}: {exc}\n", encoding="utf-8")
        raise
