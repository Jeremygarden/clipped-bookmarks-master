"""Knowledge-base output helpers for batch bookmark processing."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Iterable

from .renderers.markdown import render_markdown
from .router import route_url
from .schema import BookmarkItem, Platform, SourceType

LAYOUT_DIRS = ("sources", "weixin", "zhihu", "xiaohongshu", "topics", "batches", "assets")
PLATFORM_DIR = {
    Platform.WECHAT_OFFICIAL_ACCOUNT: "weixin",
    Platform.ZHIHU: "zhihu",
    Platform.XIAOHONGSHU: "xiaohongshu",
    Platform.WECHAT_CHANNELS: "sources",
}

@dataclass(slots=True)
class BatchResult:
    batch_id: str
    out_dir: Path
    successes: list[Path] = field(default_factory=list)
    failures: list[tuple[str, str]] = field(default_factory=list)

    @property
    def summary_path(self) -> Path:
        return self.out_dir / "batches" / f"{self.batch_id}.md"


def ensure_kb_layout(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in LAYOUT_DIRS:
        (out_dir / name).mkdir(parents=True, exist_ok=True)
    for file_name, title in (("index.md", "Knowledge Base Index"), ("failed.md", "Failed Bookmarks")):
        path = out_dir / file_name
        if not path.exists():
            path.write_text(f"# {title}\n\n", encoding="utf-8")


def write_item_note(item: BookmarkItem, out_dir: Path, *, overwrite: bool = True) -> Path:
    ensure_kb_layout(out_dir)
    subdir = PLATFORM_DIR.get(item.platform, "sources")
    path = out_dir / subdir / f"{_slug(item.title or item.url)}.md"
    if path.exists() and not overwrite:
        path = out_dir / subdir / f"{_slug(item.title or item.url)}-{_short_hash(item.url)}.md"
    path.write_text(render_markdown(item), encoding="utf-8")
    return path


def process_batch(sources: Iterable[str], out_dir: Path, *, batch_id: str | None = None, overwrite: bool = True) -> BatchResult:
    ensure_kb_layout(out_dir)
    batch_id = batch_id or datetime.now(timezone.utc).strftime("batch-%Y%m%dT%H%M%SZ")
    result = BatchResult(batch_id=batch_id, out_dir=out_dir)
    for raw in sources:
        source = raw.strip()
        if not source or source.startswith("#"):
            continue
        try:
            item = route_url(source)
            path = write_item_note(item, out_dir, overwrite=overwrite)
            result.successes.append(path)
        except Exception as exc:  # batch output should capture individual failures
            result.failures.append((source, str(exc)))
    write_indexes(result)
    return result


def write_indexes(result: BatchResult) -> None:
    ensure_kb_layout(result.out_dir)
    all_notes = sorted(_relative(p, result.out_dir) for p in _iter_note_files(result.out_dir))
    index_lines = ["# Knowledge Base Index", "", "## All Notes", ""]
    index_lines += [f"- [{p}]({p})" for p in all_notes] or ["_No notes yet._"]
    index_lines += ["", "## Batches", ""]
    batches = sorted(p.relative_to(result.out_dir).as_posix() for p in (result.out_dir / "batches").glob("*.md"))
    index_lines += [f"- [{p}]({p})" for p in batches] or ["_No batches yet._"]
    (result.out_dir / "index.md").write_text("\n".join(index_lines).rstrip() + "\n", encoding="utf-8")

    failed_lines = ["# Failed Bookmarks", ""]
    if result.failures:
        for source, error in result.failures:
            failed_lines.append(f"- `{source}` — {error}")
    else:
        failed_lines.append("_No failures in latest batch._")
    (result.out_dir / "failed.md").write_text("\n".join(failed_lines) + "\n", encoding="utf-8")

    summary = [
        f"# Batch Summary: {result.batch_id}", "",
        f"- Successes: {len(result.successes)}",
        f"- Failures: {len(result.failures)}", "",
        "## Success List", "",
    ]
    summary += [f"- [{_relative(p, result.out_dir)}]({_relative(p, result.out_dir)})" for p in result.successes] or ["_No successes._"]
    summary += ["", "## Failure List", ""]
    summary += [f"- `{s}` — {e}" for s, e in result.failures] or ["_No failures._"]
    summary += ["", "## All Notes Index", ""]
    summary += [f"- [{p}]({p})" for p in all_notes] or ["_No notes yet._"]
    result.summary_path.write_text("\n".join(summary).rstrip() + "\n", encoding="utf-8")


def _iter_note_files(out_dir: Path):
    for name in ("weixin", "zhihu", "xiaohongshu", "sources", "topics"):
        yield from (out_dir / name).glob("*.md")

def _relative(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()

def _slug(text: str) -> str:
    value = re.sub(r"[^\w\u4e00-\u9fff.-]+", "-", text.lower(), flags=re.UNICODE).strip("-._")
    return value[:80] or "bookmark"

def _short_hash(text: str) -> str:
    import hashlib
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
