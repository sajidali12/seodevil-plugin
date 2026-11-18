"""Page-level tools: audit a URL, local HTML or a build folder; links, redirects, hreflang, comparisons."""
from __future__ import annotations

import os
import re
import urllib.parse
from collections import defaultdict
from typing import Dict, List, Optional

from . import http, site
from . import textstats as ts
from .dom import Document, word_list
from .onpage import Page, extract_links, run_onpage, valid_hreflang
from .report import Report, grade, score_for, severity_counts


def _finish(r: Report, extra: Optional[Dict] = None) -> Dict:
    issues = r.sorted_issues()
    score = score_for(issues)
    out = {"score": score, "grade": grade(score), "issue_counts": severity_counts(issues), "issues": issues, "data": r.data}
    if r.passed:
        out["passed"] = r.passed
    if extra:
        out.update(extra)
    return out


def page_from_response(res: http.Response) -> Page:
    return Page(url=res.final_url, html=res.text, status=res.status, headers=res.headers,
                elapsed_ms=res.elapsed_ms, redirects=res.redirects)


# --- site-wide checks bundled into audit_page --------------------------------------

def _site_checks(p: Page, r: Report) -> None:
    url = p.url
    robots, info = site.get_robots(url)
    r.data["robots_txt"] = {"exists": info.get("exists"), "status": info.get("status")}
    if robots is None:
        r.add("robots_unreachable", "high", "crawlability", "robots.txt can't be fetched",
              detail=info.get("note") or str(info.get("error") or info.get("status")), scope="site",
              fix="Return 200 with rules, or 404 if you have none. 5xx makes Google pause crawling.")
    else:
        g = robots.check("Googlebot", url)
        if not g["allowed"]:
            r.add("robots_blocks_page", "critical", "crawlability", "robots.txt blocks Googlebot from this page",
                  detail=g["rule"], fix="Remove or narrow the Disallow rule.", scope="site")
        blocked_ai = [b for b, _, purpose in site.AI_BOTS if ("search" in purpose or "user" in purpose) and not robots.check(b, url)["allowed"]]
        if blocked_ai:
            r.add("robots_blocks_ai_search", "medium", "ai", f"robots.txt blocks AI search bots: {', '.join(blocked_ai)}",
                  fix="These bots fetch pages for cited answers in ChatGPT/Claude/Perplexity. Allow them unless you mean to opt out.", scope="site")
        if info.get("exists") and not robots.sitemaps:
            r.add("robots_no_sitemap", "low", "crawlability", "robots.txt doesn't list a sitemap", scope="site",
                  fix="Add a line: Sitemap: https://yourdomain.com/sitemap.xml")
        if not info.get("exists"):
            r.add("robots_missing", "low", "crawlability", "No robots.txt", scope="site",
                  fix="Add one with your Sitemap: line (and any AI-crawler rules).")
    cands, guessed = site.discover_sitemaps(url)
    found = None
    for c in cands[:4]:
        res = http.fetch(c, timeout=15, max_bytes=2_000_000)
        if res.status == 200 and ("xml" in res.content_type or res.text.lstrip().startswith("<?xml") or res.body[:2] == b"\x1f\x8b"):
            found = c
            break
    r.data["sitemap"] = found
    if not found:
        r.add("sitemap_missing", "medium", "crawlability", "No XML sitemap found", scope="site",
              detail="Checked robots.txt and /sitemap.xml, /sitemap_index.xml, /wp-sitemap.xml.",
              fix="Generate a sitemap of your indexable URLs and submit it in Google Search Console and Bing Webmaster Tools.")

    # http -> https and www consistency
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname or ""
    variants = {f"http://{host}/"}
    alt_host = host[4:] if host.startswith("www.") else f"www.{host}"
    variants.add(f"https://{alt_host}/")
    results = http.pmap(lambda v: (v, http.fetch(v, timeout=12, max_bytes=50_000)), sorted(variants), workers=3)
    target_origin = f"{parts.scheme}://{host}"
    bad = []
    for v, res in results:
        if res.error:
            if v.startswith("https://") and "DNS" not in (res.error or ""):
                bad.append(f"{v} → {res.error}")
            continue
        if not res.final_url.startswith(target_origin):
            bad.append(f"{v} → {res.final_url} ({res.status})")
        elif not res.redirects:
            bad.append(f"{v} serves content without redirecting (duplicate)")
        elif res.redirects[0]["status"] in (302, 307):
            bad.append(f"{v} uses a temporary {res.redirects[0]['status']} redirect")
    if bad:
        r.add("host_variants", "medium", "technical", "http/https or www/non-www versions don't all 301 to one URL", affected=bad, scope="site",
              fix=f"301-redirect every variant to {target_origin}/ in one hop.")

    llms = http.fetch(f"{http.origin(url)}/llms.txt", timeout=10, max_bytes=200_000)
    r.data["llms_txt"] = llms.status == 200 and not llms.is_html
    js = site.js_dependency(p.html)
    r.data["javascript_dependency"] = js
    if js["likely_client_rendered"]:
        r.add("client_rendered", "high", "ai", f"Content is rendered by JavaScript ({js['words_in_initial_html']} words in raw HTML)",
              detail="Google renders JS (with delay); most AI crawlers and social scrapers don't.",
              fix="Use SSR/SSG/prerendering so the HTML response contains the content.")


def _check_link_statuses(links: List[Dict], r: Report, max_links: int = 150) -> None:
    urls = []
    seen = set()
    for l in links:
        u = l.get("url")
        if u and u not in seen:
            seen.add(u)
            urls.append(u)
    urls = urls[:max_links]
    res = http.pmap(http.check_status, urls, workers=8)
    broken, redirected = [], []
    for u, x in zip(urls, res):
        if x.error or x.status >= 400:
            if x.status in (401, 403, 429, 999) and not http.same_site(u, r.data.get("_url", u)):
                continue  # bot protection on third-party sites (LinkedIn returns 999) - not reliable
            broken.append(f"{x.status or x.error} {u}")
        elif x.redirects and http.same_site(u, r.data.get("_url", u)):
            redirected.append(f"{u} → {x.final_url}")
    r.data["links"]["checked"] = len(urls)
    if broken:
        r.add("broken_links", "high", "links", f"{len(broken)} broken link(s)", affected=broken,
              fix="Update or remove them; point internal ones at the right page.")
    if redirected:
        r.add("internal_links_redirect", "low", "links", f"{len(redirected)} internal link(s) go through a redirect", affected=redirected,
              fix="Link directly to the final URL.")


def audit_page(url: str, keyword: Optional[str] = None, check_links: bool = False, site_checks: bool = True) -> Dict:
    res = http.fetch(url)
    if res.error and not res.status:
        return {"url": url, "error": res.error}
    if not res.is_html:
        return {"url": url, "final_url": res.final_url, "status": res.status, "error": f"Not an HTML page (content-type {res.content_type or 'unknown'})"}
    p = page_from_response(res)
    r = run_onpage(p, keyword)
    r.data["_url"] = p.url
    if site_checks:
        _site_checks(p, r)
    if check_links:
        _check_link_statuses(extract_links(p), r)
    r.data.pop("_url", None)
    return _finish(r, {"url": url, "final_url": p.url, "status": p.status, "response_ms": p.elapsed_ms,
                       "redirects": p.redirects, "keyword": keyword})


def audit_html(html: Optional[str] = None, path: Optional[str] = None, base_url: Optional[str] = None, keyword: Optional[str] = None) -> Dict:
    if path:
        path = os.path.expanduser(path)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()
    if not html:
        return {"error": "Provide html or path"}
    url = base_url or "http://localhost/"
    p = Page(url=url, html=html, local=True)
    r = run_onpage(p, keyword)
    return _finish(r, {"source": path or "inline html", "base_url": url})


# --- build folder audits --------------------------------------------------------------

SKIP_DIRS = {"node_modules", ".git", ".next", ".svelte-kit", ".nuxt", "__pycache__", ".venv", "venv", ".cache", "vendor"}


def _file_url(root: str, file: str, base: str) -> str:
    rel = os.path.relpath(file, root).replace(os.sep, "/")
    if rel.endswith("index.html"):
        rel = rel[: -len("index.html")]
    return urllib.parse.urljoin(base, rel)


def audit_directory(path: str, base_url: Optional[str] = None, max_files: int = 500) -> Dict:
    root = os.path.abspath(os.path.expanduser(path))
    if not os.path.isdir(root):
        return {"error": f"Not a directory: {root}"}
    base = (base_url or "http://localhost/").rstrip("/") + "/"
    files = []
    for d, dirs, names in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(".")]
        for n in names:
            if n.endswith((".html", ".htm")):
                files.append(os.path.join(d, n))
    files.sort()
    truncated = len(files) > max_files
    files = files[:max_files]
    existing_paths = set()
    for f in files:
        u = urllib.parse.urlsplit(_file_url(root, f, base)).path
        existing_paths.add(u)
        existing_paths.add(u.rstrip("/"))
        if u.endswith(".html"):
            existing_paths.add(u[:-5])
    all_files = set()
    for d, dirs, names in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for n in names:
            all_files.add("/" + os.path.relpath(os.path.join(d, n), root).replace(os.sep, "/"))

    pages, agg = [], defaultdict(lambda: {"severity": "", "title": "", "files": []})
    titles, descs = defaultdict(list), defaultdict(list)
    broken = []
    for f in files:
        with open(f, "r", encoding="utf-8", errors="replace") as fh:
            html = fh.read()
        url = _file_url(root, f, base)
        p = Page(url=url, html=html, local=True)
        r = run_onpage(p)
        rel = os.path.relpath(f, root)
        for i in r.issues:
            a = agg[i["id"]]
            a["severity"], a["title"], a["category"] = i["severity"], i["title"].split(" (")[0], i["category"]
            a["files"].append(rel)
        t, dsc = r.data.get("title"), r.data.get("meta_description")
        if t and not p.noindex:
            titles[t].append(rel)
        if dsc and not p.noindex:
            descs[dsc].append(rel)
        for l in extract_links(p):
            u = l.get("url")
            if not u or not u.startswith(base):
                continue
            path_ = urllib.parse.urlsplit(u).path
            if path_ in existing_paths or path_.rstrip("/") in existing_paths or path_ in all_files or urllib.parse.unquote(path_) in all_files:
                continue
            broken.append(f"{rel} → {path_}")
        pages.append({"file": rel, "url": url, "score": r.score(), "title": t, "words": r.data.get("word_count"),
                      "issues": len(r.issues), "noindex": p.noindex})
    issues = [{"id": k, "severity": v["severity"], "category": v["category"], "title": v["title"], "files_affected": len(v["files"]),
               "files": v["files"][:12]} for k, v in agg.items()]
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    issues.sort(key=lambda x: (order.get(x["severity"], 9), -x["files_affected"]))
    site_issues = []
    dt = {k: v for k, v in titles.items() if len(v) > 1}
    dd = {k: v for k, v in descs.items() if len(v) > 1}
    if dt:
        site_issues.append({"id": "duplicate_titles", "severity": "high", "title": f"{len(dt)} titles are shared by several pages",
                            "groups": [{"title": k, "files": v[:8]} for k, v in list(dt.items())[:15]]})
    if dd:
        site_issues.append({"id": "duplicate_descriptions", "severity": "medium", "title": f"{len(dd)} meta descriptions are shared by several pages",
                            "groups": [{"description": k[:120], "files": v[:8]} for k, v in list(dd.items())[:15]]})
    if broken:
        site_issues.append({"id": "broken_internal_links", "severity": "high", "title": f"{len(broken)} internal links point to files that don't exist in the build",
                            "affected": broken[:40], "note": "Routes served by a server/router (not files) can show up here too."})
    scores = [x["score"] for x in pages]
    return {
        "root": root, "base_url": base, "html_files": len(pages), "truncated": truncated,
        "average_score": round(sum(scores) / len(scores)) if scores else None,
        "site_issues": site_issues, "issues": issues,
        "pages": sorted(pages, key=lambda x: x["score"])[:200],
        "note": "Local audit: no network checks (status codes, headers, robots.txt, speed). Run audit_page on the deployed URL for those.",
    }


# --- link / redirect / hreflang tools ------------------------------------------------

def check_links(url: str, internal_only: bool = False, max_links: int = 200) -> Dict:
    res = http.fetch(url)
    if res.error or not res.is_html:
        return {"url": url, "error": res.error or f"Not HTML ({res.status})"}
    p = page_from_response(res)
    links = [l for l in extract_links(p) if "url" in l and (l["internal"] or not internal_only)]
    uniq: Dict[str, Dict] = {}
    for l in links:
        uniq.setdefault(l["url"], l)
    urls = list(uniq)[:max_links]
    results = http.pmap(http.check_status, urls, workers=10)
    rows = []
    for u, x in zip(urls, results):
        rows.append({"url": u, "status": x.status, "final_url": x.final_url if x.redirects else None,
                     "redirects": len(x.redirects), "error": x.error, "internal": uniq[u]["internal"],
                     "anchor": uniq[u]["text"] or uniq[u]["img_alt"] or uniq[u]["aria"], "nofollow": "nofollow" in uniq[u]["rel"]})
    broken = [x for x in rows if x["error"] or x["status"] >= 400]
    return {
        "url": p.url, "links_checked": len(rows), "links_total": len(links), "truncated": len(uniq) > max_links,
        "broken": broken, "redirected": [x for x in rows if x["redirects"] and not x["error"] and x["status"] < 400],
        "ok": len(rows) - len(broken),
        "note": "401/403/429/999 from big third-party sites (LinkedIn, Amazon...) usually means bot protection, not a broken link.",
    }


def trace_redirects(url: str, check_variants: bool = True) -> Dict:
    url = http.normalize_input_url(url)
    hops = []
    current = url
    seen = set()
    for _ in range(15):
        r = http.fetch(current, follow=False, timeout=15, use_cache=False, max_bytes=200_000)
        hop = {"url": current, "status": r.status, "ms": r.elapsed_ms}
        if r.error:
            hop["error"] = r.error
            hops.append(hop)
            break
        loc = r.headers.get("location")
        if r.status in http.REDIRECT_CODES and loc:
            nxt = urllib.parse.urljoin(current, loc)
            hop["location"] = nxt
            hops.append(hop)
            if nxt in seen:
                hops.append({"url": nxt, "error": "redirect loop"})
                break
            seen.add(current)
            current = nxt
            continue
        if r.is_html and r.status == 200:
            m = Document(r.text).find("meta", http_equiv="refresh")
            if m is not None:
                c = m.get("content")
                mm = re.search(r"url\s*=\s*['\"]?([^'\";]+)", c, re.I)
                if mm:
                    nxt = urllib.parse.urljoin(current, mm.group(1).strip())
                    hop["meta_refresh"] = nxt
                    hops.append(hop)
                    if nxt in seen or len(hops) > 12:
                        break
                    seen.add(current)
                    current = nxt
                    continue
        hops.append(hop)
        break
    final = hops[-1]
    issues = []
    n = len([h for h in hops if "location" in h or "meta_refresh" in h])
    if n > 1:
        issues.append(f"Redirect chain of {n} hops; link/redirect directly to {final['url']}.")
    if any(h.get("status") in (302, 307) for h in hops):
        issues.append("Uses temporary redirects (302/307); use 301/308 for permanent moves.")
    if any("meta_refresh" in h for h in hops):
        issues.append("Uses meta refresh; replace with a server-side 301.")
    if any(h.get("url", "").startswith("http://") and h is not hops[0] for h in hops):
        issues.append("Passes through an http:// URL mid-chain.")
    if final.get("status", 0) >= 400 or final.get("error"):
        issues.append(f"Ends in {final.get('status') or final.get('error')}.")
    out: Dict = {"url": url, "hops": hops, "final_url": final["url"], "final_status": final.get("status"), "issues": issues}
    if check_variants:
        p = urllib.parse.urlsplit(url)
        host = http.strip_www(p.hostname or "")
        path = p.path or "/"
        vs = [f"{s}://{h}{path}" for s in ("http", "https") for h in (host, "www." + host)]

        def go(v):
            r = http.fetch(v, timeout=12, max_bytes=50_000, use_cache=False)
            return {"variant": v, "final_url": r.final_url, "status": r.status, "hops": len(r.redirects),
                    "codes": [h["status"] for h in r.redirects], "error": r.error}

        variants = http.pmap(go, vs, workers=4)
        finals = {v["final_url"] for v in variants if not v["error"]}
        out["variants"] = variants
        if len(finals) > 1:
            out["issues"].append(f"Variants end on {len(finals)} different URLs: {', '.join(sorted(finals))}. Pick one and 301 the rest.")
    return out


def check_hreflang(url: str, max_alternates: int = 20) -> Dict:
    res = http.fetch(url)
    if res.error or not res.is_html:
        return {"url": url, "error": res.error or f"Not HTML ({res.status})"}
    p = page_from_response(res)
    alts = [(l.get("hreflang").strip(), p.abs(l.get("href"))) for l in p.doc.links("alternate") if l.get("hreflang")]
    if not alts:
        return {"url": p.url, "hreflang": [], "issues": ["No hreflang annotations in <head>. (They can also live in the sitemap or HTTP headers.)"]}
    issues = []
    for code, _ in alts:
        if not valid_hreflang(code):
            issues.append(f"Invalid code '{code}'.")
    if p.url.rstrip("/") not in {h.rstrip("/") for _, h in alts}:
        issues.append("No self-referencing entry for this page.")
    if "x-default" not in {c.lower() for c, _ in alts}:
        issues.append("No x-default.")

    def visit(item):
        code, href = item
        r = http.fetch(href, timeout=15)
        rec = {"hreflang": code, "url": href, "status": r.status}
        if r.redirects:
            rec["redirects_to"] = r.final_url
        if r.error or not r.is_html or r.status != 200:
            rec["error"] = r.error or f"HTTP {r.status}"
            return rec
        q = page_from_response(r)
        back = {h.rstrip("/") for c, h in ((l.get("hreflang"), q.abs(l.get("href"))) for l in q.doc.links("alternate") if l.get("hreflang"))}
        rec["returns_link"] = p.url.rstrip("/") in back
        c = q.doc.links("canonical")
        if c and c[0].get("href"):
            cu = q.abs(c[0].get("href")).rstrip("/")
            rec["self_canonical"] = cu == q.url.rstrip("/")
        rec["noindex"] = q.noindex
        lang = (q.doc.find("html") or q.doc.root).get("lang")
        rec["html_lang"] = lang
        return rec

    checked = http.pmap(visit, alts[:max_alternates], workers=6)
    for c in checked:
        if c.get("error"):
            issues.append(f"{c['hreflang']}: {c['url']} → {c['error']}")
        elif c.get("redirects_to"):
            issues.append(f"{c['hreflang']}: points to a redirect ({c['url']} → {c['redirects_to']}). Use final URLs.")
        if c.get("returns_link") is False:
            issues.append(f"{c['hreflang']}: {c['url']} doesn't link back (missing return tag, so Google ignores the pair).")
        if c.get("self_canonical") is False:
            issues.append(f"{c['hreflang']}: {c['url']} canonicalizes elsewhere; hreflang must point to canonical URLs.")
        if c.get("noindex"):
            issues.append(f"{c['hreflang']}: {c['url']} is noindex.")
    return {"url": p.url, "hreflang": checked, "issues": issues}


# --- content tools -------------------------------------------------------------------

def _outline(doc) -> List[Dict]:
    return [{"level": int(h.tag[1]), "text": h.text()[:150]} for h in doc.find_all({"h1", "h2", "h3", "h4"})][:80]


def analyze_content(url: Optional[str] = None, text: Optional[str] = None, keyword: Optional[str] = None, include_text: bool = False) -> Dict:
    out: Dict = {}
    if url:
        res = http.fetch(url)
        if res.error or not res.is_html:
            return {"url": url, "error": res.error or f"Not HTML ({res.status})"}
        doc = Document(res.text)
        body = doc.main_text()
        out.update({"url": res.final_url, "title": (doc.find("title").text(skip=set()) if doc.find("title") else ""),
                    "meta_description": doc.meta1("description"), "outline": _outline(doc)})
        alts = [i.get("alt") for i in doc.find_all("img") if i.get("alt")]
        links = len(doc.main_content().find_all("a"))
        out["images_in_content"] = len(doc.main_content().find_all("img"))
        out["links_in_content"] = links
        out["lists"] = len(doc.main_content().find_all({"ul", "ol"}))
        out["tables"] = len(doc.main_content().find_all("table"))
        faq = [h["text"] for h in out["outline"] if h["text"].endswith("?")]
        out["question_headings"] = faq[:20]
    elif text:
        body, alts = text, []
        out["outline"] = []
    else:
        return {"error": "Provide url or text"}
    out["word_count"] = len(word_list(body))
    out["readability"] = ts.readability(body)
    out["top_terms"] = ts.top_terms(body)
    if keyword:
        hs = out.get("outline", [])
        out["keyword"] = ts.keyword_usage(keyword, title=out.get("title", ""), description=out.get("meta_description", ""),
                                          h1=[h["text"] for h in hs if h["level"] == 1], headings=[h["text"] for h in hs if h["level"] > 1],
                                          url=out.get("url", ""), body_text=body, alts=alts)
        out["keyword"]["relevance_score"] = ts.score_keyword_relevance(out["keyword"])
    if include_text:
        out["text"] = body[:30000]
    return out


def compare_pages(urls: List[str], keyword: Optional[str] = None) -> Dict:
    urls = urls[:6]

    def one(u):
        res = http.fetch(u)
        if res.error or not res.is_html:
            return {"url": u, "error": res.error or f"Not HTML ({res.status})"}
        p = page_from_response(res)
        r = run_onpage(p, keyword)
        body = p.doc.main_text()
        return {
            "url": p.url, "status": p.status, "response_ms": p.elapsed_ms, "score": r.score(),
            "title": r.data.get("title"), "meta_description": r.data.get("meta_description"),
            "h1": r.data.get("h1"), "h2": [h["text"] for h in r.data.get("headings", []) if h["level"] == 2][:30],
            "word_count": r.data.get("word_count"), "images": r.data.get("images"),
            "links": r.data.get("links"), "schema_types": r.data.get("schema", {}).get("jsonld_types"),
            "readability": r.data.get("readability", {}).get("flesch_reading_ease"),
            "keyword": r.data.get("keyword"), "html_kb": r.data.get("resources", {}).get("html_kb"),
            "_terms": {t for t, _ in ts.top_terms(body, 60)["terms"]} | {t for t, _ in ts.top_terms(body, 60)["phrases"]},
        }

    rows = http.pmap(one, urls, workers=4)
    ok = [x for x in rows if "error" not in x]
    gaps: Dict = {}
    if len(ok) >= 2 and "error" not in rows[0]:
        mine = rows[0]["_terms"]
        others = [x["_terms"] for x in ok[1:]]
        counts: Dict[str, int] = defaultdict(int)
        for s in others:
            for t in s:
                counts[t] += 1
        need = max(1, (len(others) + 1) // 2)
        gaps["terms_competitors_use_that_first_url_lacks"] = sorted([t for t, c in counts.items() if c >= need and t not in mine], key=lambda t: (-counts[t], t))[:40]
        wc = [x["word_count"] or 0 for x in ok[1:]]
        gaps["competitor_median_words"] = sorted(wc)[len(wc) // 2]
        gaps["first_url_words"] = rows[0]["word_count"]
        st = set()
        for x in ok[1:]:
            st |= set(x["schema_types"] or [])
        gaps["schema_types_competitors_have"] = sorted(st - set(rows[0]["schema_types"] or []))
    for x in rows:
        x.pop("_terms", None)
    return {"pages": rows, "gaps": gaps, "note": "The first URL is treated as 'yours'; the rest as competitors."}
