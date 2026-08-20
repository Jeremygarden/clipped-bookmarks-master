#!/usr/bin/env python3
"""Download media from a Xiaohongshu note into a local directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from clipped_bookmarks.extractors.xiaohongshu import XiaohongshuExtractor


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Xiaohongshu note or xhslink URL")
    parser.add_argument("--out", default="xhs_media", help="output directory")
    args = parser.parse_args()

    extractor = XiaohongshuExtractor(download_dir=Path(args.out), rate_limit_seconds=0)
    item = extractor.extract(args.url)
    if item.status == "error":
        print(json.dumps(item.to_dict(), ensure_ascii=False, indent=2))
        return 2
    assets = extractor.download_media(item.assets)
    item.assets = assets
    print(json.dumps(item.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
