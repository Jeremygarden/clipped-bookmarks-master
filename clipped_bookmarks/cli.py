"""Command line entrypoint for the core Clipped Bookmarks architecture."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
import sys
from urllib.parse import urlparse

from .extractors.wechat_article import extract_wechat_article
from .extractors.wechat_video import WeChatVideoExtractor, is_local_video_file
from .extractors.zhihu import extract_zhihu
from .renderers.markdown import render_markdown
from .renderers.obsidian import ObsidianExportConfig, export_to_obsidian
from .router import route_url
<<<<<<< HEAD
from .schema import BookmarkAsset, BookmarkItem, Platform, SourceType, UnsupportedPlatformError
=======
from .schema import UnsupportedPlatformError
from .kb import process_batch
>>>>>>> 0e42546 (Ralph iteration 3: work in progress)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Route a clipped bookmark source and render Markdown.")
    parser.add_argument("source", help="Supported URL or WeChat Channels media file")
    parser.add_argument("--out", type=Path, help="Write rendered Markdown to this path instead of stdout")
    parser.add_argument("--obsidian-vault", type=Path, help="Obsidian vault path for export")
    parser.add_argument("--obsidian-folder", default="Clipped Bookmarks", help="Obsidian folder name")
    parser.add_argument("--confirm-obsidian", action="store_true", help="Confirm writing into the Obsidian vault")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting an existing output/export file")
    return parser


<<<<<<< HEAD
def _build_process_url_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process one URL or local fixture/file into Markdown")
    parser.add_argument("source", help="Supported URL, local HTML/text fixture, or media/transcript file")
    parser.add_argument("--out", type=Path, required=True, help="Output directory for Markdown notes")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting an existing note")
    return parser


def _build_process_batch_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process newline-delimited sources into Markdown")
    parser.add_argument("links", type=Path, help="Text file containing one source per line")
    parser.add_argument("--out", type=Path, required=True, help="Output directory for Markdown notes")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting existing notes")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "process-url":
        args = _build_process_url_parser().parse_args(argv[1:])
        return _process_url_command(args.source, args.out, overwrite=args.overwrite)
    if argv and argv[0] == "process-batch":
        args = _build_process_batch_parser().parse_args(argv[1:])
        return _process_batch_command(args.links, args.out, overwrite=args.overwrite)
=======
def build_batch_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process bookmark URLs into a knowledge-base layout.")
    parser.add_argument("links", type=Path, help="Text file with one source URL/path per line")
    parser.add_argument("--out", type=Path, default=Path("bookmarks_notes"), help="Knowledge-base output directory")
    parser.add_argument("--batch-id", help="Stable batch id for reproducible summaries")
    parser.add_argument("--overwrite", action="store_true", default=True, help="Overwrite existing generated notes")
    return parser

def main(argv: list[str] | None = None) -> int:
    argv = list(argv) if argv is not None else sys.argv[1:]
    if argv and argv[0] == "process-batch":
        args = build_batch_parser().parse_args(argv[1:])
        if not args.links.exists():
            print(f"error: links file not found: {args.links}", file=sys.stderr)
            return 2
        result = process_batch(args.links.read_text(encoding="utf-8").splitlines(), args.out, batch_id=args.batch_id, overwrite=args.overwrite)
        print(f"batch: {result.summary_path}")
        print(f"successes: {len(result.successes)}")
        print(f"failures: {len(result.failures)}")
        return 1 if result.failures else 0
>>>>>>> 0e42546 (Ralph iteration 3: work in progress)

    parser = build_parser()
    args = parser.parse_args(argv)
    return _legacy_render(args)

def _legacy_render(args: argparse.Namespace) -> int:
    try:
        item = route_url(args.source)
    except (UnsupportedPlatformError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    markdown = render_markdown(item)
    if args.out:
        if args.out.exists() and not args.overwrite:
            print(f"error: output exists (use --overwrite): {args.out}", file=sys.stderr)
            return 3
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(markdown, encoding="utf-8")
    else:
        print(markdown, end="")

    if args.obsidian_vault:
        config = ObsidianExportConfig(vault_path=args.obsidian_vault, folder=args.obsidian_folder, overwrite=args.overwrite)
        try:
            path = export_to_obsidian(item, config, confirm=args.confirm_obsidian)
        except Exception as exc:
            print(f"error: obsidian export failed: {exc}", file=sys.stderr)
            return 4
        print(f"exported: {path}", file=sys.stderr)
    return 0


def _process_batch_command(links: Path, out_dir: Path, *, overwrite: bool = False) -> int:
    if not links.exists():
        _write_failure(out_dir, str(links), f"links file not found: {links}")
        return 1
    rc = 0
    for line in links.read_text(encoding="utf-8").splitlines():
        source = line.strip()
        if not source or source.startswith("#"):
            continue
        if _process_url_command(source, out_dir, overwrite=overwrite) != 0:
            rc = 1
    return rc


def _process_url_command(source: str, out_dir: Path, *, overwrite: bool = False) -> int:
    try:
        item = process_source(source)
        markdown = render_markdown(item)
        if not markdown.strip() or "_Content has not been fetched yet._" in markdown:
            raise ValueError("extraction produced empty content")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = _unique_note_path(out_dir, item, overwrite=overwrite)
        path.write_text(markdown, encoding="utf-8")
        print(path)
        return 0
    except Exception as exc:
        _write_failure(out_dir, source, str(exc))
        print(f"error: {source}: {exc}", file=sys.stderr)
        return 1


def process_source(source: str) -> BookmarkItem:
    local = _local_path(source)
    if local and local.exists() and local.is_file():
        suffix = local.suffix.lower()
        if suffix in {".html", ".htm"}:
            html = local.read_text(encoding="utf-8")
            hinted_url = _extract_source_url(html) or source
            return _item_from_html(html, hinted_url)
        if suffix in {".txt", ".md", ".srt", ".vtt", ".json"}:
            return _transcript_item(source, local)
        if is_local_video_file(source):
            return WeChatVideoExtractor().extract(source)
    return route_url(source)


def _item_from_html(html: str, url: str) -> BookmarkItem:
    routed = route_url(url)
    if routed.source_type == SourceType.WECHAT_ARTICLE:
        return _wechat_dict_to_item(extract_wechat_article(html, url), url)
    if routed.platform == Platform.ZHIHU:
        return _zhihu_dict_to_item(extract_zhihu(html, url), url, routed.source_type)
    raise UnsupportedPlatformError(f"No offline HTML extractor for: {url}")


def _wechat_dict_to_item(data: dict, url: str) -> BookmarkItem:
    assets = [BookmarkAsset(url=i.get("url", ""), kind="image", title=i.get("alt") or None, metadata=i) for i in data.get("images", []) if i.get("url")]
    errors = list(data.get("risk_flags") or [])
    return BookmarkItem(url=url, platform=Platform.WECHAT_OFFICIAL_ACCOUNT, source_type=SourceType.WECHAT_ARTICLE, title=data.get("title") or "WeChat article", author=data.get("author") or None, published_at=data.get("publish_time") or None, content=data.get("content") or data.get("extra", {}).get("description") or "", assets=assets, status="fetched" if data.get("content") else "error", errors=errors, metadata={"raw_data": data.get("raw_data", {}), "top_comments": data.get("top_comments", [])})


def _zhihu_dict_to_item(data: dict, url: str, source_type: SourceType) -> BookmarkItem:
    errors = []
    extra = data.get("extra", {})
    for flag in ("requires_login", "anti_bot", "not_found", "dynamic_fallback"):
        if extra.get(flag):
            errors.append(flag)
    return BookmarkItem(url=url, platform=Platform.ZHIHU, source_type=source_type, title=data.get("title") or "Zhihu bookmark", author=data.get("author") or None, published_at=data.get("publish_time") or None, content=data.get("content") or "", status="fetched" if data.get("content") else "error", errors=errors, metadata={"raw_data": data.get("raw_data", {}), "top_comments": data.get("top_comments", []), "upvote_count": data.get("upvote_count")})


def _transcript_item(source: str, path: Path) -> BookmarkItem:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"transcript/local file is empty: {path}")
    return BookmarkItem(url=source, platform=Platform.WECHAT_CHANNELS, source_type=SourceType.WECHAT_CHANNELS_FILE, title=path.stem or path.name, content=text, status="fetched", metadata={"input_kind": "file", "asset_kind": "transcript", "filename": path.name})


def _local_path(source: str) -> Path | None:
    parsed = urlparse(source)
    if parsed.scheme == "file":
        return Path(parsed.path)
    if not parsed.scheme:
        return Path(source).expanduser()
    return None


def _extract_source_url(html: str) -> str:
    m = re.search(r'<meta[^>]+(?:property|name)=["\'](?:og:url|source)["\'][^>]+content=["\']([^"\']+)', html, re.I)
    if m:
        return m.group(1)
    for pattern in (r'https://mp\.weixin\.qq\.com/s/[\w\-]+', r'https://(?:www\.)?zhihu\.com/question/\d+(?:/answer/\d+)?', r'https://zhuanlan\.zhihu\.com/p/\d+'):
        m = re.search(pattern, html)
        if m:
            return m.group(0)
    raise UnsupportedPlatformError("local HTML fixture does not contain a supported source URL")


def _unique_note_path(out_dir: Path, item: BookmarkItem, *, overwrite: bool) -> Path:
    slug = _slugify(item.title) or _slugify(Path(urlparse(item.url).path).name) or "bookmark"
    path = out_dir / f"{slug}.md"
    if overwrite or not path.exists():
        return path
    for i in range(2, 1000):
        candidate = out_dir / f"{slug}-{i}.md"
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"too many duplicate output files for {slug}")


def _slugify(value: str) -> str:
    value = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value or "", flags=re.UNICODE).strip("-_")
    return value[:80]


def _write_failure(out_dir: Path, source: str, message: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "failed.md").open("a", encoding="utf-8") as fh:
        fh.write(f"## Failed: {source}\n\n{message}\n\n")


if __name__ == "__main__":
    raise SystemExit(main())
