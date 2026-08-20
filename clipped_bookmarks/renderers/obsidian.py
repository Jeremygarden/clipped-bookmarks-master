"""Obsidian export skeleton.

The exporter is intentionally conservative: callers must opt in with
``confirm=True`` before a file is written to a vault path.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from clipped_bookmarks.schema import BookmarkItem
from .markdown import render_markdown


@dataclass(slots=True)
class ObsidianExportConfig:
    vault_path: Path
    folder: str = "Clipped Bookmarks"
    overwrite: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ObsidianExportConfig":
        return cls(
            vault_path=Path(str(data["vault_path"])),
            folder=str(data.get("folder", "Clipped Bookmarks")),
            overwrite=bool(data.get("overwrite", False)),
        )


def export_to_obsidian(item: BookmarkItem, config: ObsidianExportConfig, *, confirm: bool = False) -> Path:
    """Render and write a note into an Obsidian vault after explicit confirmation."""

    if not confirm:
        raise PermissionError("Obsidian export requires confirm=True before writing to the vault")

    target_dir = config.vault_path / config.folder
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{_safe_filename(item.title)}.md"
    if target.exists() and not config.overwrite:
        raise FileExistsError(f"Refusing to overwrite existing Obsidian note: {target}")
    target.write_text(render_markdown(item), encoding="utf-8")
    return target


def _safe_filename(title: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]+", "-", title).strip().strip(".")
    return cleaned[:80] or "Untitled Bookmark"
