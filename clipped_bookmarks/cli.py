"""Command line entrypoint for the core Clipped Bookmarks architecture."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .renderers.markdown import render_markdown
from .renderers.obsidian import ObsidianExportConfig, export_to_obsidian
from .router import route_url
from .schema import UnsupportedPlatformError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Route a clipped bookmark source and render Markdown.")
    parser.add_argument("source", help="Supported URL or WeChat Channels media file")
    parser.add_argument("--out", type=Path, help="Write rendered Markdown to this path instead of stdout")
    parser.add_argument("--obsidian-vault", type=Path, help="Obsidian vault path for export")
    parser.add_argument("--obsidian-folder", default="Clipped Bookmarks", help="Obsidian folder name")
    parser.add_argument("--confirm-obsidian", action="store_true", help="Confirm writing into the Obsidian vault")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting an existing output/export file")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

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
        config = ObsidianExportConfig(
            vault_path=args.obsidian_vault,
            folder=args.obsidian_folder,
            overwrite=args.overwrite,
        )
        try:
            path = export_to_obsidian(item, config, confirm=args.confirm_obsidian)
        except Exception as exc:  # keep CLI error readable and non-destructive
            print(f"error: obsidian export failed: {exc}", file=sys.stderr)
            return 4
        print(f"exported: {path}", file=sys.stderr)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
