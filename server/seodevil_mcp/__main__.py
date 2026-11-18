"""Entry point.

    python3 -m seodevil_mcp                 # MCP server on stdio (what Claude Code runs)
    python3 -m seodevil_mcp audit URL       # one-off JSON output, handy for CI
    python3 -m seodevil_mcp crawl URL --max-pages 100
    python3 -m seodevil_mcp dir ./dist --base-url https://example.com --min-score 80
"""
from __future__ import annotations

import argparse
import json
import sys


def cli(argv) -> int:
    from . import audit, crawler

    ap = argparse.ArgumentParser(prog="seodevil")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="audit one URL")
    a.add_argument("url")
    a.add_argument("--keyword")
    a.add_argument("--check-links", action="store_true")
    c = sub.add_parser("crawl", help="crawl a site")
    c.add_argument("url")
    c.add_argument("--max-pages", type=int, default=50)
    c.add_argument("--output")
    d = sub.add_parser("dir", help="audit a folder of built HTML files")
    d.add_argument("path")
    d.add_argument("--base-url")
    for p in (a, c, d):
        p.add_argument("--min-score", type=int, default=0, help="exit 1 if the score is below this (CI gate)")
    args = ap.parse_args(argv)

    if args.cmd == "audit":
        out = audit.audit_page(args.url, args.keyword, args.check_links)
        score = out.get("score", 0)
    elif args.cmd == "crawl":
        out = crawler.crawl(args.url, max_pages=args.max_pages, output_path=args.output)
        out.pop("_pages_full", None)
        score = out.get("summary", {}).get("site_score", 0)
    else:
        out = audit.audit_directory(args.path, args.base_url)
        score = out.get("average_score") or 0
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False, default=str)
    sys.stdout.write("\n")
    if "error" in out:
        return 2
    return 1 if score < args.min_score else 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("audit", "crawl", "dir"):
        sys.exit(cli(sys.argv[1:]))
    from .server import main

    main()
