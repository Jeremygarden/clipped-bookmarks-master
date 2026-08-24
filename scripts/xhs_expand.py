#!/usr/bin/env python3
"""Expand Xiaohongshu short/collection links into canonical note URLs."""

from __future__ import annotations

import argparse
import json

from clipped_bookmarks.extractors.xiaohongshu import XiaohongshuExtractor, is_collection_url


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="xhslink.cn, xiaohongshu note, or collection URL")
    parser.add_argument("--json", action="store_true", help="print structured JSON")
    args = parser.parse_args()

    extractor = XiaohongshuExtractor(rate_limit_seconds=0)
    final_url = extractor.expand_short_link(args.url)
    note_urls = extractor.expand_collection(final_url) if is_collection_url(final_url) else [final_url]
    payload = {"input_url": args.url, "final_url": final_url, "note_urls": note_urls}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for url in note_urls:
            print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
