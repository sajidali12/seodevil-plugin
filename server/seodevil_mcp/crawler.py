"""Breadth-first site crawler with site-level checks (duplicates, broken links, orphans, depth)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.parse
from collections import defaultdict
from typing import Dict, List, Optional, Set
from xml.sax.saxutils import escape

from . import http, site
from .dom import word_list
from .onpage import Page, extract_links, run_onpage
from .report import SEVERITY_ORDER

SKIP_EXT = re.compile(
    r"\.(pdf|jpe?g|png|gif|svg|webp|avif|ico|bmp|tiff?|zip|gz|rar|7z|tar|mp4|mp3|wav|ogg|webm|mov|avi|css|js|mjs|json|xml|txt|"
    r"woff2?|ttf|eot|otf|docx?|xlsx?|pptx?|csv|exe|dmg|apk|rss|atom)$", re.I)


def normalize(url: str, include_query: bool) -> str:
    p = urllib.parse.urlsplit(url)
    host = (p.hostname or "").lower()
    port = f":{p.port}" if p.port and p.port not in (80, 443) else ""
    path = p.path or "/"
    query = p.query if include_query else ""
    if query:
        query = "&".join(sorted(q for q in query.split("&") if not q.lower().startswith(("utm_", "fbclid", "gclid", "mc_", "_ga"))))
    return urllib.parse.urlunsplit((p.scheme.lower(), host + port, path, query, ""))


def crawl(
    url: str,
    max_pages: int = 50,
    max_depth: int = 5,
    respect_robots: bool = True,
    include_query: bool = False,
    use_sitemap: bool = True,
    check_external: bool = False,
    concurrency: int = 5,
    keyword: Optional[str] = None,
    output_path: Optional[str] = None,
    time_budget_s: int = 420,
) -> Dict:
    started = time.monotonic()
    max_pages = max(1, min(int(max_pages), 2000))
    seed = http.fetch(url)
    if seed.error and not seed.status:
        return {"url": url, "error": seed.error}
    start_url = normalize(seed.final_url, include_query)
    root_host = http.strip_www(urllib.parse.urlsplit(start_url).hostname or "")
    robots, _ = site.get_robots(start_url) if respect_robots else (None, {})

    sitemap_urls: Set[str] = set()
    if use_sitemap:
        sm = site.collect_sitemap_urls(start_url, max_urls=20000)
        sitemap_urls = {normalize(u["loc"], include_query) for u in sm["urls"]
                        if http.strip_www(urllib.parse.urlsplit(u["loc"]).hostname or "") == root_host}

    def in_scope(u: str) -> bool:
        p = urllib.parse.urlsplit(u)
        if p.scheme not in ("http", "https") or http.strip_www(p.hostname or "") != root_host:
            return False
        if SKIP_EXT.search(p.path):
            return False
        if not include_query and p.query:
            return False
        return True

    pages: Dict[str, Dict] = {}
    inlinks: Dict[str, Set[str]] = defaultdict(set)
    link_sources: Dict[str, Set[str]] = defaultdict(set)  # raw link target -> source pages
    external_links: Dict[str, Set[str]] = defaultdict(set)
    blocked: List[str] = []
    depth_of: Dict[str, int] = {start_url: 0}
    frontier = [start_url]
    queued = {start_url}
    stopped_reason = None

    def visit(u: str) -> Dict:
        r = http.fetch(u, timeout=20)
        rec: Dict = {"url": u, "status": r.status, "ms": r.elapsed_ms, "depth": depth_of.get(u, 0)}
        if r.error:
            rec["error"] = r.error
            return rec
        if r.redirects:
            rec["redirects_to"] = r.final_url
            rec["redirect_codes"] = [h["status"] for h in r.redirects]
        if not r.is_html:
            rec["content_type"] = r.content_type
            return rec
        final_norm = normalize(r.final_url, include_query)
        if r.redirects and final_norm != u:
            rec["_follow"] = [r.final_url]  # crawl the destination as its own page
            return rec
        p = Page(url=r.final_url, html=r.text, status=r.status, headers=r.headers, elapsed_ms=r.elapsed_ms, redirects=r.redirects)
        rep = run_onpage(p, keyword)
        links = extract_links(p)
        main = p.doc.main_text()
        words = word_list(main)
        rec.update({
            "title": rep.data.get("title", ""),
            "description": rep.data.get("meta_description", ""),
            "h1": (rep.data.get("h1") or [""])[0],
            "canonical": rep.data.get("canonical"),
            "noindex": p.noindex,
            "words": len(words),
            "score": rep.score(),
            "issues": [{"id": i["id"], "severity": i["severity"], "title": i["title"], "category": i["category"]} for i in rep.issues],
            "schema": rep.data.get("schema", {}).get("jsonld_types", []),
            "content_hash": hashlib.sha1(" ".join(words).encode()).hexdigest() if len(words) > 50 else None,
            "lang": rep.data.get("lang"),
            "last_modified": r.headers.get("last-modified"),
            "_links": [(l["url"], l["internal"], "nofollow" in l["rel"]) for l in links if "url" in l],
        })
        return rec

    while frontier and len(pages) < max_pages:
        if time.monotonic() - started > time_budget_s:
            stopped_reason = f"time budget of {time_budget_s}s reached"
            break
        batch = frontier[: max_pages - len(pages)]
        frontier = frontier[len(batch):]
        allowed = []
        for u in batch:
            if robots and not robots.check("Googlebot", u)["allowed"] and u != start_url:
                blocked.append(u)
            else:
                allowed.append(u)
        results = http.pmap(visit, allowed, workers=concurrency)
        next_level = []
        for rec in results:
            u = rec["url"]
            pages[u] = rec
            for f in rec.pop("_follow", []):
                n = normalize(f, include_query)
                if in_scope(n) and n not in queued:
                    queued.add(n)
                    depth_of[n] = depth_of.get(u, 0)
                    next_level.append(n)
            for target, internal, nofollow in rec.pop("_links", []):
                if internal:
                    n = normalize(target, include_query)
                    inlinks[n].add(u)
                    link_sources[n].add(u)
                    if in_scope(n) and n not in queued and depth_of.get(u, 0) + 1 <= max_depth:
                        queued.add(n)
                        depth_of[n] = depth_of.get(u, 0) + 1
                        next_level.append(n)
                else:
                    external_links[target.split("#")[0]].add(u)
        frontier = frontier + next_level
        if not frontier and sitemap_urls:
            # Pages only reachable from the sitemap (possible orphans) get crawled last.
            extra = [s for s in sorted(sitemap_urls) if s not in queued and in_scope(s)]
            for s in extra:
                queued.add(s)
                depth_of[s] = 99
            frontier = extra
    if frontier and not stopped_reason:
        stopped_reason = f"max_pages ({max_pages}) reached; {len(frontier)} more URLs were queued"

    # ---- site-level analysis -------------------------------------------------------
    html_pages = [p for p in pages.values() if "title" in p]
    indexable = [p for p in html_pages if p["status"] == 200 and not p["noindex"]
                 and (not p.get("canonical") or p["canonical"].rstrip("/") == p["url"].rstrip("/"))]
    site_issues: List[Dict] = []

    def add(id_, severity, title, affected=None, fix="", **extra):
        d = {"id": id_, "severity": severity, "title": title}
        if fix:
            d["fix"] = fix
        if affected:
            d["affected"] = affected[:25]
            d["affected_total"] = len(affected)
        d.update(extra)
        site_issues.append(d)

    def dup_groups(key):
        g = defaultdict(list)
        for p in indexable:
            v = (p.get(key) or "").strip().lower()
            if v:
                g[v].append(p["url"])
        return [{"value": k[:140], "urls": v[:10], "count": len(v)} for k, v in g.items() if len(v) > 1]

    dt, dd, dh = dup_groups("title"), dup_groups("description"), dup_groups("h1")
    if dt:
        add("duplicate_titles", "high", f"{len(dt)} titles are used on more than one page", groups=dt[:20],
            fix="Give every indexable page a unique title that says what's different about it.")
    if dd:
        add("duplicate_descriptions", "medium", f"{len(dd)} meta descriptions are used on more than one page", groups=dd[:20])
    if dh:
        add("duplicate_h1", "low", f"{len(dh)} H1s are used on more than one page", groups=dh[:15])
    hashes = defaultdict(list)
    for p in indexable:
        if p.get("content_hash"):
            hashes[p["content_hash"]].append(p["url"])
    dc = [v for v in hashes.values() if len(v) > 1]
    if dc:
        add("duplicate_content", "high", f"{len(dc)} groups of pages have identical main content", groups=[{"urls": v[:10]} for v in dc[:15]],
            fix="Merge them, make them distinct, or canonicalize the copies to one URL.")

    broken = []
    for u, rec in pages.items():
        if rec.get("error") or rec["status"] >= 400:
            srcs = sorted(link_sources.get(u, []))[:5]
            broken.append(f"{rec.get('status') or rec.get('error')} {u}" + (f"  (linked from {', '.join(srcs)})" if srcs else ""))
    if broken:
        add("broken_internal", "critical" if len(broken) > 5 else "high", f"{len(broken)} internal URLs are broken", broken,
            fix="Fix the links on the source pages or 301-redirect the dead URLs.")
    redirected = [f"{u} → {rec['redirects_to']}  (linked from {len(link_sources.get(u, []))} pages)" for u, rec in pages.items()
                  if rec.get("redirects_to") and link_sources.get(u)]
    if redirected:
        add("internal_redirects", "medium", f"{len(redirected)} internally linked URLs redirect", redirected,
            fix="Update internal links to point at the final URLs.")
    chains = [f"{u} ({'→'.join(map(str, rec['redirect_codes']))})" for u, rec in pages.items() if len(rec.get("redirect_codes", [])) > 1]
    if chains:
        add("redirect_chains", "medium", f"{len(chains)} redirect chains", chains)
    noidx = [p["url"] for p in html_pages if p["noindex"]]
    if noidx:
        add("noindex_pages", "info", f"{len(noidx)} pages are noindex", noidx, fix="Confirm each one is meant to be hidden.")
    canon = [f'{p["url"]} → {p["canonical"]}' for p in html_pages if p.get("canonical") and p["canonical"].rstrip("/") != p["url"].rstrip("/")]
    if canon:
        add("canonicalized_pages", "info", f"{len(canon)} pages canonicalize to another URL", canon)
    if sitemap_urls:
        orphans = [s for s in sitemap_urls if s in pages and not inlinks.get(s) and s != start_url]
        if orphans:
            add("orphan_pages", "high", f"{len(orphans)} sitemap pages have no internal links pointing to them", orphans,
                fix="Link to them from relevant pages/navigation; orphan pages get crawled rarely and rank poorly.")
        bad_sm = [f"{s} ({pages[s].get('status')}{', noindex' if pages[s].get('noindex') else ''}{', redirects' if pages[s].get('redirects_to') else ''})"
                  for s in sitemap_urls if s in pages and (pages[s].get("status") != 200 or pages[s].get("noindex") or pages[s].get("redirects_to"))]
        if bad_sm:
            add("sitemap_dirty", "medium", f"{len(bad_sm)} sitemap URLs are redirects, errors or noindex", bad_sm,
                fix="List only final, 200, indexable, canonical URLs in the sitemap.")
        missing_sm = [p["url"] for p in indexable if p["url"] not in sitemap_urls]
        if missing_sm and len(sitemap_urls) > 0:
            add("not_in_sitemap", "low", f"{len(missing_sm)} indexable pages are missing from the sitemap", missing_sm)
    deep = [f'{p["url"]} (depth {p["depth"]})' for p in indexable if 3 < p.get("depth", 0) < 99]
    if deep:
        add("deep_pages", "low", f"{len(deep)} pages are more than 3 clicks from the start page", deep,
            fix="Surface important pages via navigation, hubs or related links.")
    one_link = [p["url"] for p in indexable if len(inlinks.get(p["url"], ())) == 1 and p["url"] != start_url]
    if len(one_link) > 3:
        add("weakly_linked", "low", f"{len(one_link)} pages have only one internal link pointing to them", one_link)
    slow = [f'{p["url"]} ({p["ms"]} ms)' for p in html_pages if p.get("ms", 0) > 2000]
    if slow:
        add("slow_pages", "medium", f"{len(slow)} pages took over 2s to load (HTML only)", slow)
    if blocked:
        add("robots_blocked", "info", f"{len(blocked)} discovered URLs are blocked by robots.txt", blocked)
    if http.strip_www(urllib.parse.urlsplit(start_url).hostname or "") and any(p["url"].startswith("http://") for p in html_pages) and start_url.startswith("https://"):
        add("http_pages", "high", "Some pages are reachable over http:// without redirecting", [p["url"] for p in html_pages if p["url"].startswith("http://")])

    if check_external and external_links:
        ext = sorted(external_links)[:300]
        res = http.pmap(http.check_status, ext, workers=10)
        bad = [f"{x.status or x.error} {u} (on {sorted(external_links[u])[0]})" for u, x in zip(ext, res)
               if (x.error or x.status >= 400) and x.status not in (401, 403, 429, 999)]
        if bad:
            add("broken_external", "medium", f"{len(bad)} broken external links", bad)

    # Aggregate page-level issues.
    agg: Dict[str, Dict] = {}
    for p in html_pages:
        for i in p["issues"]:
            a = agg.setdefault(i["id"], {"id": i["id"], "severity": i["severity"], "category": i["category"],
                                         "title": re.sub(r"\d+ of \d+ |^\d+ |\(\d+[^)]*\)", "", i["title"]).strip(), "pages": []})
            a["pages"].append(p["url"])
    page_issues = sorted(agg.values(), key=lambda a: (SEVERITY_ORDER.get(a["severity"], 9), -len(a["pages"])))
    for a in page_issues:
        a["pages_affected"] = len(a["pages"])
        a["sample_pages"] = a.pop("pages")[:10]

    status_counts: Dict[str, int] = defaultdict(int)
    for p in pages.values():
        status_counts[str(p.get("status") or "error")] += 1
    scores = [p["score"] for p in html_pages]
    site_issues.sort(key=lambda s: SEVERITY_ORDER.get(s["severity"], 9))
    site_penalty = sum({"critical": 15, "high": 8, "medium": 4, "low": 1}.get(s["severity"], 0) for s in site_issues)
    avg = round(sum(scores) / len(scores)) if scores else 0
    summary = {
        "start_url": start_url,
        "pages_crawled": len(pages),
        "html_pages": len(html_pages),
        "indexable_pages": len(indexable),
        "sitemap_urls": len(sitemap_urls),
        "average_page_score": avg,
        "site_score": max(0, avg - min(40, site_penalty)),
        "status_codes": dict(status_counts),
        "duration_s": round(time.monotonic() - started, 1),
        "stopped": stopped_reason,
    }
    page_rows = [{
        "url": p["url"], "status": p.get("status"), "depth": p.get("depth"), "score": p.get("score"),
        "title": (p.get("title") or "")[:90], "words": p.get("words"), "inlinks": len(inlinks.get(p["url"], ())),
        "issues": len(p.get("issues", [])), **({"noindex": True} if p.get("noindex") else {}),
        **({"redirects_to": p["redirects_to"]} if p.get("redirects_to") else {}),
        **({"error": p["error"]} if p.get("error") else {}),
    } for p in sorted(pages.values(), key=lambda x: (x.get("depth", 0), x["url"]))]

    result = {"summary": summary, "site_issues": site_issues, "page_issues": page_issues, "pages": page_rows[:150]}
    if len(page_rows) > 150:
        result["pages_truncated"] = f"Showing 150 of {len(page_rows)} pages; pass output_path for the full data."
    if output_path:
        path = os.path.abspath(os.path.expanduser(output_path))
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        full = dict(result, pages=[{k: v for k, v in p.items()} for p in pages.values()],
                    inlinks={k: sorted(v) for k, v in inlinks.items()})
        with open(path, "w", encoding="utf-8") as f:
            json.dump(full, f, indent=2, ensure_ascii=False)
        result["saved_to"] = path
    result["_pages_full"] = pages  # used by generate_sitemap; stripped before returning to the client
    return result


def generate_sitemap(url: str, output_path: str, max_pages: int = 500, include_query: bool = False) -> Dict:
    res = crawl(url, max_pages=max_pages, include_query=include_query, use_sitemap=True)
    if "error" in res:
        return res
    pages = res.pop("_pages_full")
    rows = []
    for p in pages.values():
        if p.get("status") != 200 or p.get("noindex") or "title" not in p or p.get("redirects_to"):
            continue
        if p.get("canonical") and p["canonical"].rstrip("/") != p["url"].rstrip("/"):
            continue
        lm = ""
        if p.get("last_modified"):
            try:
                from email.utils import parsedate_to_datetime

                lm = parsedate_to_datetime(p["last_modified"]).date().isoformat()
            except (TypeError, ValueError):
                lm = ""
        rows.append((p["url"], lm))
    rows.sort()
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, lm in rows:
        lines.append(f"  <url><loc>{escape(u)}</loc>" + (f"<lastmod>{lm}</lastmod>" if lm else "") + "</url>")
    lines.append("</urlset>")
    path = os.path.abspath(os.path.expanduser(output_path))
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return {"saved_to": path, "urls": len(rows), "pages_crawled": res["summary"]["pages_crawled"],
            "excluded": res["summary"]["pages_crawled"] - len(rows),
            "note": "Only 200, indexable, self-canonical HTML pages are included. lastmod comes from Last-Modified headers when present."}
