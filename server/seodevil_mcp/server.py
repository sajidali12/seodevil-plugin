"""MCP server over stdio (JSON-RPC 2.0, newline-delimited). Standard library only."""
from __future__ import annotations

import json
import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict

from . import __version__, audit, crawler, external, http, schema, site
from . import textstats as ts

PROTOCOL_VERSIONS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]

INSTRUCTIONS = (
    "SEODevil gives you real measurements for SEO work: on-page audits, site crawls, robots.txt, sitemaps, "
    "redirects, hreflang, structured data, Core Web Vitals, AI-crawler readiness and keyword ideas. "
    "Always base findings on tool output, quote the evidence (URL, tag, value) and give a concrete fix. "
    "For a codebase, find where the tag is generated (framework metadata, templates, CMS) and fix it there."
)


def S(props: Dict[str, Any], required=()) -> Dict:
    return {"type": "object", "properties": props, "required": list(required), "additionalProperties": False}


STR = {"type": "string"}
URL = {"type": "string", "description": "Page URL (https:// is added if missing)"}
KW = {"type": "string", "description": "Optional target keyword to check on-page usage for"}


def _strip_private(d: Dict) -> Dict:
    d.pop("_pages_full", None)
    return d


TOOLS: Dict[str, Dict] = {
    "audit_page": {
        "description": "Full SEO audit of one live URL: meta tags, canonical, indexability, headings, images, links, Open Graph, "
                       "structured data, mobile, content/readability, HTTPS, mixed content, redirects, compression, security headers, "
                       "plus site checks (robots.txt, sitemap, http/www variants, JS rendering, AI bots). Returns a 0-100 score and "
                       "issues with fixes.",
        "schema": S({"url": URL, "keyword": KW,
                     "check_links": {"type": "boolean", "description": "Also check status of every link on the page (slower). Default false."},
                     "site_checks": {"type": "boolean", "description": "Include robots/sitemap/host-variant checks. Default true."}}, ["url"]),
        "fn": lambda a: audit.audit_page(a["url"], a.get("keyword"), a.get("check_links", False), a.get("site_checks", True)),
    },
    "audit_html": {
        "description": "Audit HTML without fetching it: pass raw html or a local file path (e.g. a build output or template). "
                       "Runs all on-page checks; no network checks.",
        "schema": S({"html": {"type": "string"}, "path": {"type": "string", "description": "Path to a local .html file"},
                     "base_url": {"type": "string", "description": "URL the page will live at (for resolving links/canonical)"}, "keyword": KW}),
        "fn": lambda a: audit.audit_html(a.get("html"), a.get("path"), a.get("base_url"), a.get("keyword")),
    },
    "audit_directory": {
        "description": "Audit every .html file in a static build folder (dist/, out/, build/, public/, _site/): per-page scores, "
                       "issues aggregated across files, duplicate titles/descriptions and internal links to files that don't exist.",
        "schema": S({"path": STR, "base_url": {"type": "string", "description": "Production origin, e.g. https://example.com"},
                     "max_files": {"type": "integer", "default": 500}}, ["path"]),
        "fn": lambda a: audit.audit_directory(a["path"], a.get("base_url"), a.get("max_files", 500)),
    },
    "crawl_site": {
        "description": "Crawl a website breadth-first (same host) and audit every page. Finds duplicate titles/descriptions/content, "
                       "broken internal links, redirect chains, orphan pages (in sitemap, not linked), dirty sitemap entries, noindex/"
                       "canonicalized pages, deep and weakly linked pages, slow pages. Aggregates page issues across the site.",
        "schema": S({"url": URL,
                     "max_pages": {"type": "integer", "default": 50, "description": "Up to 2000"},
                     "max_depth": {"type": "integer", "default": 5},
                     "respect_robots": {"type": "boolean", "default": True},
                     "include_query": {"type": "boolean", "default": False, "description": "Crawl URLs with query strings"},
                     "use_sitemap": {"type": "boolean", "default": True, "description": "Also crawl sitemap URLs to find orphans"},
                     "check_external": {"type": "boolean", "default": False, "description": "Check external link statuses"},
                     "keyword": KW,
                     "output_path": {"type": "string", "description": "Save full JSON results here (recommended for >150 pages)"}}, ["url"]),
        "fn": lambda a: _strip_private(crawler.crawl(
            a["url"], a.get("max_pages", 50), a.get("max_depth", 5), a.get("respect_robots", True), a.get("include_query", False),
            a.get("use_sitemap", True), a.get("check_external", False), keyword=a.get("keyword"), output_path=a.get("output_path"))),
    },
    "check_robots": {
        "description": "Fetch and parse robots.txt. Shows groups, sitemaps, syntax problems and whether Googlebot, Bingbot and each AI "
                       "crawler (GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, Google-Extended...) may fetch the given paths.",
        "schema": S({"url": URL, "test_paths": {"type": "array", "items": STR, "description": "Paths or URLs to test, e.g. ['/', '/blog/']"},
                     "user_agents": {"type": "array", "items": STR}}, ["url"]),
        "fn": lambda a: site.robots_report(a["url"], a.get("test_paths"), a.get("user_agents")),
    },
    "check_sitemap": {
        "description": "Find and parse XML sitemaps (robots.txt, common paths, sitemap indexes, .gz). Reports URL count, lastmod quality, "
                       "wrong hosts, duplicates, and samples URLs to verify they are 200, indexable and self-canonical.",
        "schema": S({"url": URL, "sitemap_url": {"type": "string"}, "sample": {"type": "integer", "default": 25}}, ["url"]),
        "fn": lambda a: site.sitemap_report(a["url"], a.get("sitemap_url"), a.get("sample", 25)),
    },
    "trace_redirects": {
        "description": "Follow a URL hop by hop (status codes, Location, meta refresh, loops) and test http/https × www/non-www variants.",
        "schema": S({"url": URL, "check_variants": {"type": "boolean", "default": True}}, ["url"]),
        "fn": lambda a: audit.trace_redirects(a["url"], a.get("check_variants", True)),
    },
    "check_links": {
        "description": "Check the HTTP status of every link on a page: broken links, redirects, nofollow, anchor text.",
        "schema": S({"url": URL, "internal_only": {"type": "boolean", "default": False}, "max_links": {"type": "integer", "default": 200}}, ["url"]),
        "fn": lambda a: audit.check_links(a["url"], a.get("internal_only", False), a.get("max_links", 200)),
    },
    "check_hreflang": {
        "description": "Validate hreflang: codes, self reference, x-default, and fetch every alternate to confirm 200, return links, "
                       "self-canonical and indexable.",
        "schema": S({"url": URL}, ["url"]),
        "fn": lambda a: audit.check_hreflang(a["url"]),
    },
    "validate_schema": {
        "description": "Extract and validate structured data (JSON-LD, microdata, RDFa) against Google rich-result requirements. "
                       "Pass a url, or json (a JSON-LD string you wrote), or html.",
        "schema": S({"url": {"type": "string"}, "json": {"type": "string"}, "html": {"type": "string"}}),
        "fn": lambda a: _validate_schema(a),
    },
    "ai_readiness": {
        "description": "AI search readiness (ChatGPT, Claude, Perplexity, Gemini, Copilot): robots.txt rules per AI crawler, firewall/CDN "
                       "blocks tested with AI user agents, JavaScript dependence, llms.txt, structured data, nosnippet.",
        "schema": S({"url": URL}, ["url"]),
        "fn": lambda a: site.ai_readiness(a["url"]),
    },
    "pagespeed": {
        "description": "Core Web Vitals from Google PageSpeed Insights: real-user CrUX field data (LCP, INP, CLS, FCP, TTFB) for the URL "
                       "and origin, Lighthouse lab metrics, top opportunities and the LCP element. Set PAGESPEED_API_KEY for reliable use.",
        "schema": S({"url": URL, "strategy": {"type": "string", "enum": ["mobile", "desktop"], "default": "mobile"}}, ["url"]),
        "fn": lambda a: external.pagespeed(a["url"], a.get("strategy", "mobile")),
    },
    "serp_preview": {
        "description": "Preview how a title and meta description look in Google: pixel widths, truncation and the displayed text. "
                       "Use it to test candidate titles/descriptions before writing them.",
        "schema": S({"title": STR, "description": STR, "url": STR}, ["title"]),
        "fn": lambda a: ts.serp_preview(a["title"], a.get("description", ""), a.get("url", "")),
    },
    "analyze_content": {
        "description": "Content analysis of a URL or raw text: word count, heading outline, readability, top terms and phrases, "
                       "question headings, and keyword placement/density. include_text returns the main text for rewriting.",
        "schema": S({"url": STR, "text": STR, "keyword": KW, "include_text": {"type": "boolean", "default": False}}),
        "fn": lambda a: audit.analyze_content(a.get("url"), a.get("text"), a.get("keyword"), a.get("include_text", False)),
    },
    "compare_pages": {
        "description": "Compare your page (first URL) with up to 5 competitor pages: titles, headings, word count, schema, readability, "
                       "keyword usage, and terms/sections competitors cover that you don't (content gap).",
        "schema": S({"urls": {"type": "array", "items": STR, "minItems": 2, "maxItems": 6}, "keyword": KW}, ["urls"]),
        "fn": lambda a: audit.compare_pages(a["urls"], a.get("keyword")),
    },
    "keyword_ideas": {
        "description": "Keyword ideas from Google/DuckDuckGo autocomplete (free, no key): questions, comparisons, commercial and long-tail "
                       "variants grouped by search intent. No search volumes.",
        "schema": S({"seed": STR, "lang": {"type": "string", "default": "en"}, "country": {"type": "string", "default": "us"},
                     "depth": {"type": "string", "enum": ["quick", "standard", "deep"], "default": "standard"}}, ["seed"]),
        "fn": lambda a: external.keyword_ideas(a["seed"], a.get("lang", "en"), a.get("country", "us"), a.get("depth", "standard")),
    },
    "generate_sitemap": {
        "description": "Crawl a site and write a clean sitemap.xml (only 200, indexable, self-canonical pages) to output_path.",
        "schema": S({"url": URL, "output_path": STR, "max_pages": {"type": "integer", "default": 500},
                     "include_query": {"type": "boolean", "default": False}}, ["url", "output_path"]),
        "fn": lambda a: crawler.generate_sitemap(a["url"], a["output_path"], a.get("max_pages", 500), a.get("include_query", False)),
    },
    "fetch_page": {
        "description": "Fetch a URL and return status, redirect hops, response headers, timing and (optionally) the raw HTML. "
                       "Use user_agent to see what a specific crawler gets.",
        "schema": S({"url": URL, "user_agent": STR, "include_html": {"type": "boolean", "default": False},
                     "max_html_chars": {"type": "integer", "default": 40000}}, ["url"]),
        "fn": lambda a: _fetch_page(a),
    },
}


def _validate_schema(a: Dict) -> Dict:
    if a.get("json"):
        return schema.validate_any(a["json"])
    if a.get("html"):
        return schema.validate_any(a["html"])
    if a.get("url"):
        r = http.fetch(a["url"])
        if r.error or not r.is_html:
            return {"error": r.error or f"Not HTML ({r.status})"}
        out = schema.validate_any(r.text)
        out["url"] = r.final_url
        return out
    return {"error": "Provide url, json or html"}


def _fetch_page(a: Dict) -> Dict:
    r = http.fetch(a["url"], ua=a.get("user_agent") or None, use_cache=False)
    out = r.summary()
    out["headers"] = r.headers
    out["content_type"] = r.content_type
    out["bytes"] = len(r.body)
    if a.get("include_html"):
        n = int(a.get("max_html_chars", 40000))
        out["html"] = r.text[:n]
        out["html_truncated"] = len(r.text) > n
    return out


# --- JSON-RPC plumbing --------------------------------------------------------------

_write_lock = threading.Lock()


def _send(msg: Dict) -> None:
    data = json.dumps(msg, ensure_ascii=False, default=str)
    with _write_lock:
        sys.stdout.write(data + "\n")
        sys.stdout.flush()


def _result(id_, result) -> None:
    _send({"jsonrpc": "2.0", "id": id_, "result": result})


def _error(id_, code: int, message: str) -> None:
    _send({"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}})


def call_tool(name: str, args: Dict) -> Dict:
    tool = TOOLS.get(name)
    if not tool:
        return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}
    try:
        out = tool["fn"](args or {})
        text = json.dumps(out, ensure_ascii=False, default=str)
        is_err = isinstance(out, dict) and "error" in out and len(out) <= 4
        return {"content": [{"type": "text", "text": text}], "isError": bool(is_err)}
    except Exception as e:  # report the failure to the model instead of crashing the server
        traceback.print_exc(file=sys.stderr)
        return {"content": [{"type": "text", "text": f"{name} failed: {type(e).__name__}: {e}"}], "isError": True}


def handle(msg: Dict, pool: ThreadPoolExecutor) -> None:
    method = msg.get("method")
    id_ = msg.get("id")
    params = msg.get("params") or {}
    if method == "initialize":
        req = params.get("protocolVersion")
        _result(id_, {
            "protocolVersion": req if req in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "seodevil", "title": "SEODevil", "version": __version__},
            "instructions": INSTRUCTIONS,
        })
    elif method == "ping":
        _result(id_, {})
    elif method == "tools/list":
        _result(id_, {"tools": [{"name": n, "description": t["description"], "inputSchema": t["schema"],
                                 "annotations": {"readOnlyHint": n not in ("generate_sitemap", "crawl_site"), "openWorldHint": n not in ("audit_html", "audit_directory", "serp_preview")}}
                                for n, t in TOOLS.items()]})
    elif method == "tools/call":
        def run():
            _result(id_, call_tool(params.get("name", ""), params.get("arguments") or {}))
        pool.submit(run)
    elif method in ("resources/list", "prompts/list"):
        _result(id_, {method.split("/")[0]: []})
    elif id_ is not None:
        _error(id_, -32601, f"Method not found: {method}")
    # notifications (initialized, cancelled...) need no reply


def main() -> None:
    if "--version" in sys.argv:
        print(__version__)
        return
    pool = ThreadPoolExecutor(max_workers=4)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            _error(None, -32700, "Parse error")
            continue
        for m in msg if isinstance(msg, list) else [msg]:
            try:
                handle(m, pool)
            except Exception as e:  # pragma: no cover
                traceback.print_exc(file=sys.stderr)
                if m.get("id") is not None:
                    _error(m.get("id"), -32603, str(e))
    pool.shutdown(wait=True)


if __name__ == "__main__":
    main()
