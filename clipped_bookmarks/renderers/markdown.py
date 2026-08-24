"""Markdown renderer with YAML frontmatter for BookmarkItem."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from clipped_bookmarks.schema import BookmarkItem


def render_structured_markdown(item: BookmarkItem) -> str:
    """Render text or local media bookmarks with stable, structured sections.

    This is intentionally renderer-only: extractors mark failure states and
    attach local audio/video/transcript assets; this function turns that into a
    predictable Markdown note without invoking platform downloaders.
    """

    lines = render_markdown(item).rstrip().splitlines()
    if item.status in {"error", "unsupported"} or item.errors:
        lines.extend(["", "## Extraction Status", "", f"- Status: {item.status}"])
        lines.extend(f"- Failure: {error}" for error in item.errors)

    transcript_assets = [asset for asset in item.assets if asset.kind == "transcript"]
    if transcript_assets:
        transcript_text = _read_first_local_text(transcript_assets)
        if transcript_text:
            lines.extend(["", "## Transcript", "", _format_timestamped_transcript(transcript_text)])

    return "\n".join(lines).rstrip() + "\n"



def render_markdown(item: BookmarkItem) -> str:
    """Render a BookmarkItem as Markdown with a small YAML frontmatter block."""

    frontmatter = {
        "title": item.title,
        "source": item.url,
        "platform": item.platform.value,
        "source_type": item.source_type.value,
        "author": item.author,
        "published_at": item.published_at,
        "status": item.status,
        "tags": item.tags,
    }
    lines = ["---", *_yaml_lines(frontmatter), "---", "", f"# {item.title}", ""]

    source_bits = [item.platform.value]
    if item.author:
        source_bits.append(str(item.author))
    if item.published_at:
        source_bits.append(str(item.published_at))
    lines.append(f"> Source: {' · '.join(source_bits)}")
    lines.append(f"> Original: {item.url}")
    lines.append("")

    if item.summary:
        lines.extend(["## Summary", "", item.summary.strip(), ""])

    if item.content:
        lines.extend(["## Content", "", item.content.strip(), ""])
    else:
        lines.extend(["## Content", "", "_Content has not been fetched yet._", ""])

    if item.assets:
        lines.extend(["## Assets", ""])
        for asset in item.assets:
            label = asset.title or asset.kind
            lines.append(f"- [{label}]({asset.url})")
        lines.append("")

    if item.errors:
        lines.extend(["## Errors", ""])
        lines.extend(f"- {error}" for error in item.errors)
        lines.append("")

    if item.tags:
        lines.extend(["## Tags", "", " ".join(f"#{_tag_slug(tag)}" for tag in item.tags), ""])

    return "\n".join(lines).rstrip() + "\n"


def _yaml_lines(data: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in data.items():
        if value is None:
            lines.append(f"{key}: null")
        elif isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                lines.extend(f"  - {_yaml_scalar(v)}" for v in value)
        else:
            lines.append(f"{key}: {_yaml_scalar(value)}")
    return lines


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, datetime):
        value = value.isoformat()
    text = str(value)
    escaped = text.replace('"', '\\"')
    return f'"{escaped}"'


def _tag_slug(tag: str) -> str:
    return tag.strip().replace(" ", "-").replace("#", "")


def _read_first_local_text(assets: list) -> str:
    for asset in assets:
        if not asset.local_path:
            continue
        try:
            from pathlib import Path
            path = Path(asset.local_path)
            if path.exists() and path.is_file():
                return path.read_text(encoding="utf-8").strip()
        except UnicodeDecodeError:
            return ""
    return ""


def _format_timestamped_transcript(text: str) -> str:
    # Preserve SRT/VTT timing as readable timestamped bullets for video notes.
    import re
    blocks = re.split(r"\n\s*\n", text.strip())
    bullets = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines and lines[0].isdigit():
            lines = lines[1:]
        if not lines:
            continue
        timing = lines[0]
        body = " ".join(lines[1:]).strip()
        m = re.match(r"([0-9:,\.]+)\s*-->\s*([0-9:,\.]+)", timing)
        if m and body:
            bullets.append(f"- [{m.group(1).replace(',', '.')}] {body}")
        else:
            bullets.append("- " + " ".join(lines))
    return "\n".join(bullets) if bullets else text.strip()
