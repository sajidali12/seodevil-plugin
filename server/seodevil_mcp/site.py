"""Site-wide checks: robots.txt, XML sitemaps, llms.txt and AI-crawler access."""
from __future__ import annotations

import gzip
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from . import http
from .dom import Document, word_list

# --- robots.txt (RFC 9309) -------------------------------------------------------


class Robots:
    def __init__(self, text: str):
        self.groups: List[Tuple[List[str], List[Tuple[bool, str]], Optional[float]]] = []
        self.sitemaps: List[str] = []
        self.problems: List[str] = []
        agents: List[str] = []
        rules: List[Tuple[bool, str]] = []
        delay: Optional[float] = None
        last_was_agent = False
        for n, raw in enumerate((text or "").splitlines(), 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if ":" not in line:
                self.problems.append(f"line {n}: no colon: {raw.strip()[:80]!r}")
                continue
            key, val = (x.strip() for x in line.split(":", 1))
            key = key.lower()
            if key in ("user-agent", "useragent"):
                if not last_was_agent and agents:
                    self.groups.append((agents, rules, delay))
                    agents, rules, delay = [], [], None
                agents.append(val.lower())
                last_was_agent = True
                continue
            last_was_agent = False
            if key in ("allow", "disallow"):
                if not agents:
                    self.problems.append(f"line {n}: {key} before any User-agent")
                    continue
                if val:
                    rules.append((key == "allow", val))
            elif key == "crawl-delay":
                try:
                    delay = float(val)
                except ValueError:
                    self.problems.append(f"line {n}: bad crawl-delay {val!r}")
            elif key == "sitemap":
                self.sitemaps.append(val)
            elif key not in ("host", "clean-param", "noindex", "request-rate", "visit-time", "content-signal"):
                self.problems.append(f"line {n}: unknown directive {key!r}")
            if key == "noindex":
                self.problems.append(f"line {n}: 'noindex' in robots.txt has been unsupported by Google since 2019")
        if agents:
            self.groups.append((agents, rules, delay))

    def _rules_for(self, token: str) -> Tuple[List[Tuple[bool, str]], Optional[str]]:
        token = token.lower()
        matched = [g for g in self.groups if any(a == token or (a != "*" and token.startswith(a)) for a in g[0])]
        label = token
        if not matched:
            matched = [g for g in self.groups if "*" in g[0]]
            label = "*" if matched else None
        rules: List[Tuple[bool, str]] = []
        for g in matched:
            rules += g[1]
        return rules, label

    @staticmethod
    def _match(pattern: str, path: str) -> bool:
        rx = "".join(".*" if c == "*" else ("$" if c == "$" and i == len(pattern) - 1 else re.escape(c)) for i, c in enumerate(pattern))
        return re.match(rx, path) is not None

    def check(self, token: str, url_or_path: str) -> Dict:
        p = urllib.parse.urlsplit(url_or_path)
        path = (p.path or "/") + (f"?{p.query}" if p.query else "")
        if path.startswith("/robots.txt"):
            return {"allowed": True, "group": None, "rule": None}
        rules, label = self._rules_for(token)
        best: Optional[Tuple[bool, str]] = None
        for allow, pat in rules:
            if self._match(pat, path) or self._match(urllib.parse.unquote(pat), urllib.parse.unquote(path)):
                if best is None or len(pat) > len(best[1]) or (len(pat) == len(best[1]) and allow):
                    best = (allow, pat)
        return {
            "allowed": True if best is None else best[0],
            "group": label,
            "rule": None if best is None else f"{'Allow' if best[0] else 'Disallow'}: {best[1]}",
        }

    def blocks_everything(self, token: str) -> bool:
        rules, _ = self._rules_for(token)
        return any(not a and p in ("/", "/*") for a, p in rules) and not any(a and p in ("/", "/*") for a, p in rules)

    def crawl_delay(self, token: str) -> Optional[float]:
        token = token.lower()
        for agents, _, d in self.groups:
            if token in agents or "*" in agents:
                if d:
                    return d
        return None


def get_robots(base_url: str) -> Tuple[Optional[Robots], Dict]:
    url = http.origin(http.normalize_input_url(base_url)) + "/robots.txt"
    r = http.fetch(url, timeout=15)
    info = {"url": url, "status": r.status, "error": r.error}
    if r.error:
        return None, info
    if r.status == 404 or r.status == 410:
        info["exists"] = False
        return Robots(""), info
    if r.status >= 500 or r.status == 429:
        info["note"] = "Google treats a 5xx robots.txt as 'disallow everything' for up to 30 days."
        return None, info
    if r.status >= 400:
        info["exists"] = False
        return Robots(""), info
    if r.is_html or "<html" in r.text[:500].lower():
        info["exists"] = False
        info["note"] = "robots.txt returns an HTML page (probably a soft 404 / SPA fallback)."
        return Robots(""), info
    info["exists"] = True
    info["size_bytes"] = len(r.body)
    if len(r.body) > 500 * 1024:
        info["note"] = "Larger than Google's 500 KiB limit; rules after that are ignored."
    return Robots(r.text), info


# --- AI crawlers -----------------------------------------------------------------

AI_BOTS = [
    # token, vendor, purpose
    ("GPTBot", "OpenAI", "training"),
    ("OAI-SearchBot", "OpenAI", "search (ChatGPT search results)"),
    ("ChatGPT-User", "OpenAI", "user-triggered fetch"),
    ("ClaudeBot", "Anthropic", "training"),
    ("Claude-SearchBot", "Anthropic", "search"),
    ("Claude-User", "Anthropic", "user-triggered fetch"),
    ("PerplexityBot", "Perplexity", "search"),
    ("Perplexity-User", "Perplexity", "user-triggered fetch"),
    ("Google-Extended", "Google", "Gemini training/grounding (not Search)"),
    ("Applebot-Extended", "Apple", "Apple Intelligence training"),
    ("Bingbot", "Microsoft", "Bing + Copilot search"),
    ("CCBot", "Common Crawl", "open dataset used for training"),
    ("meta-externalagent", "Meta", "training"),
    ("Bytespider", "ByteDance", "training"),
    ("Amazonbot", "Amazon", "Alexa / AI"),
    ("DuckAssistBot", "DuckDuckGo", "AI answers"),
    ("MistralAI-User", "Mistral", "user-triggered fetch"),
]
SEARCH_BOTS = ["Googlebot", "Bingbot", "OAI-SearchBot", "Claude-SearchBot", "PerplexityBot"]


def robots_report(url: str, test_paths: Optional[List[str]] = None, user_agents: Optional[List[str]] = None) -> Dict:
    url = http.normalize_input_url(url)
    robots, info = get_robots(url)
    out: Dict = {"robots_txt": info}
    if robots is None:
        out["issues"] = [info.get("note") or f"robots.txt could not be fetched: {info.get('error') or info.get('status')}"]
        return out
    paths = test_paths or [urllib.parse.urlsplit(url).path or "/"]
    agents = user_agents or ["Googlebot", "Bingbot"] + [b[0] for b in AI_BOTS if b[0] != "Bingbot"]
    out["groups"] = [{"user_agents": g[0], "rules": [f"{'Allow' if a else 'Disallow'}: {p}" for a, p in g[1]][:40],
                      **({"crawl_delay": g[2]} if g[2] else {})} for g in robots.groups][:30]
    out["sitemaps"] = robots.sitemaps
    out["problems"] = robots.problems[:20]
    out["checks"] = {ua: {p: robots.check(ua, p) for p in paths} for ua in agents}
    issues = []
    if not info.get("exists"):
        issues.append("No robots.txt. Not required, but it's where you list your sitemap and set AI-crawler rules.")
    if robots.blocks_everything("Googlebot"):
        issues.append("CRITICAL: robots.txt blocks Googlebot from the whole site.")
    for ua in ("Googlebot", "Bingbot"):
        for pth, res in out["checks"].get(ua, {}).items():
            if not res["allowed"]:
                issues.append(f"{ua} is blocked from {pth} by '{res['rule']}'.")
    if info.get("exists") and not robots.sitemaps:
        issues.append("robots.txt doesn't reference a sitemap. Add 'Sitemap: https://.../sitemap.xml'.")
    if any(p.endswith((".css", ".js")) or "/wp-includes" in p or "/assets" in p for g in robots.groups for a, p in g[1] if not a):
        issues.append("CSS/JS/asset paths are disallowed; Google needs them to render the page.")
    out["issues"] = issues
    return out


# --- sitemaps ----------------------------------------------------------------------

def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


def parse_sitemap(body: bytes) -> Dict:
    if body[:2] == b"\x1f\x8b":
        try:
            body = gzip.decompress(body)
        except OSError:
            return {"error": "invalid gzip"}
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        return {"error": f"XML parse error: {e}"}
    kind = _strip_ns(root.tag)
    entries = []
    for child in root:
        rec = {}
        for f in child:
            name = _strip_ns(f.tag)
            if name in ("loc", "lastmod", "changefreq", "priority"):
                rec[name] = (f.text or "").strip()
            elif name == "link" and f.get("hreflang"):
                rec.setdefault("alternates", []).append({"hreflang": f.get("hreflang"), "href": f.get("href")})
            elif name in ("image", "video", "news"):
                rec[name] = rec.get(name, 0) + 1
        if rec.get("loc"):
            entries.append(rec)
    return {"kind": kind, "entries": entries}


def discover_sitemaps(url: str) -> Tuple[List[str], bool]:
    """Sitemaps from robots.txt, else common locations. Returns (candidates, guessed)."""
    robots, _ = get_robots(url)
    base = http.origin(http.normalize_input_url(url))
    if robots and robots.sitemaps:
        return list(robots.sitemaps), False
    return [f"{base}/sitemap.xml", f"{base}/sitemap_index.xml", f"{base}/wp-sitemap.xml", f"{base}/sitemap-index.xml"], True


def collect_sitemap_urls(url: str, sitemap_url: Optional[str] = None, max_urls: int = 50000, max_files: int = 60) -> Dict:
    cands, guessed = ([sitemap_url], False) if sitemap_url else discover_sitemaps(url)
    queue = list(cands)
    files: List[Dict] = []
    urls: List[Dict] = []
    seen = set()
    found_any = False
    while queue and len(files) < max_files and len(urls) < max_urls:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        r = http.fetch(sm, timeout=25, max_bytes=60 * 1024 * 1024)
        rec: Dict = {"url": sm, "status": r.status}
        if r.error or r.status != 200:
            rec["error"] = r.error or f"HTTP {r.status}"
            if not guessed:
                files.append(rec)
            continue
        parsed = parse_sitemap(r.body)
        if "error" in parsed:
            rec["error"] = parsed["error"]
            files.append(rec)
            continue
        found_any = True
        rec["type"] = parsed["kind"]
        rec["entries"] = len(parsed["entries"])
        if parsed["kind"] == "sitemapindex":
            queue += [e["loc"] for e in parsed["entries"]]
        else:
            if len(parsed["entries"]) > 50000:
                rec["warning"] = "More than 50,000 URLs; split into multiple sitemaps."
            if len(r.body) > 50 * 1024 * 1024:
                rec["warning"] = "Larger than 50 MB uncompressed."
            urls += [dict(e, sitemap=sm) for e in parsed["entries"]]
        files.append(rec)
        if guessed and sm in cands:
            # When guessing common locations, stop at the first one that works.
            queue = [q for q in queue if q not in cands]
    return {"files": files, "urls": urls[:max_urls], "found": found_any}


def sitemap_report(url: str, sitemap_url: Optional[str] = None, sample: int = 25) -> Dict:
    url = http.normalize_input_url(url)
    data = collect_sitemap_urls(url, sitemap_url)
    urls = data["urls"]
    out: Dict = {"sitemap_files": data["files"], "url_count": len(urls)}
    issues: List[str] = []
    if not data["found"]:
        out["issues"] = ["No XML sitemap found (checked robots.txt and common locations)."]
        return out
    host = urllib.parse.urlsplit(url).hostname or ""
    other_host = [u["loc"] for u in urls if http.strip_www(urllib.parse.urlsplit(u["loc"]).hostname or "") != http.strip_www(host)]
    if other_host:
        issues.append(f"{len(other_host)} URLs are on a different host (e.g. {other_host[0]}); sitemaps may only list URLs on their own host.")
    scheme = urllib.parse.urlsplit(url).scheme
    wrong_scheme = [u["loc"] for u in urls if not u["loc"].startswith(scheme + "://")]
    if wrong_scheme and not other_host:
        issues.append(f"{len(wrong_scheme)} URLs use a different scheme (e.g. {wrong_scheme[0]}).")
    lastmods = [u.get("lastmod") for u in urls if u.get("lastmod")]
    out["with_lastmod_pct"] = round(100 * len(lastmods) / len(urls), 1) if urls else 0
    if urls and not lastmods:
        issues.append("No <lastmod> dates. Google uses accurate lastmod to schedule recrawls.")
    if lastmods and len(set(lastmods)) == 1 and len(lastmods) > 10:
        issues.append("Every URL has the same lastmod; Google ignores lastmod it can't trust. Use each page's real modification date.")
    if any("priority" in u or "changefreq" in u for u in urls):
        out["note"] = "priority and changefreq are ignored by Google (harmless)."
    dupes = len(urls) - len({u["loc"] for u in urls})
    if dupes:
        issues.append(f"{dupes} duplicate URLs.")
    out["sample_urls"] = [u["loc"] for u in urls[:10]]

    if sample and urls:
        step = max(1, len(urls) // sample)
        picks = [u["loc"] for u in urls[::step][:sample]]

        def probe(u: str) -> Dict:
            r = http.fetch(u, timeout=15, max_bytes=400_000)
            d: Dict = {"url": u, "status": r.status}
            if r.redirects:
                d["redirects_to"] = r.final_url
            if r.error:
                d["error"] = r.error
            elif r.is_html and r.status == 200:
                doc = Document(r.text)
                rob = ",".join(doc.meta("robots")).lower() + r.headers.get("x-robots-tag", "").lower()
                if "noindex" in rob:
                    d["noindex"] = True
                c = doc.links("canonical")
                if c and c[0].get("href"):
                    cu = urllib.parse.urljoin(r.final_url, c[0].get("href"))
                    if cu.rstrip("/") != r.final_url.rstrip("/"):
                        d["canonical_elsewhere"] = cu
            return d

        res = http.pmap(probe, picks, workers=6)
        bad = [x for x in res if x["status"] != 200 or x.get("redirects_to") or x.get("noindex") or x.get("canonical_elsewhere") or x.get("error")]
        out["sample_checked"] = len(res)
        out["sample_problems"] = bad
        if bad:
            issues.append(f"{len(bad)} of {len(res)} sampled sitemap URLs are not clean 200, indexable, self-canonical pages. "
                          "A sitemap should only list URLs you want indexed.")
    out["issues"] = issues
    return out


# --- llms.txt / AI readiness ------------------------------------------------------

def llms_txt(url: str) -> Dict:
    base = http.origin(http.normalize_input_url(url))
    out = {}
    for name in ("llms.txt", "llms-full.txt"):
        r = http.fetch(f"{base}/{name}", timeout=12)
        ok = r.status == 200 and not r.is_html and r.text.strip() != ""
        rec: Dict = {"url": f"{base}/{name}", "status": r.status, "exists": ok}
        if ok:
            rec["size_bytes"] = len(r.body)
            lines = r.text.strip().splitlines()
            rec["starts_with_h1"] = bool(lines) and lines[0].startswith("# ")
            rec["links"] = len(re.findall(r"\[[^\]]+\]\([^)]+\)", r.text))
            rec["preview"] = "\n".join(lines[:12])
        out[name] = rec
    return out


def js_dependency(html: str) -> Dict:
    doc = Document(html)
    words = len(word_list(doc.body.text()))
    roots = [n for n in doc.find_all("div") if n.get("id") in ("root", "app", "__next", "__nuxt", "svelte", "q-app") and len(n.text()) < 50]
    scripts = len([s for s in doc.find_all("script") if s.get("src")])
    likely_csr = words < 120 and (bool(roots) or scripts >= 2)
    return {"words_in_initial_html": words, "spa_root_found": bool(roots), "external_scripts": scripts, "likely_client_rendered": likely_csr}


def ai_readiness(url: str) -> Dict:
    url = http.normalize_input_url(url)
    page = http.fetch(url, timeout=20)
    robots, rinfo = get_robots(url)
    out: Dict = {"url": url, "robots_txt": rinfo}
    issues: List[Dict] = []

    bots = []
    for token, vendor, purpose in AI_BOTS:
        res = robots.check(token, url) if robots else {"allowed": None}
        bots.append({"bot": token, "vendor": vendor, "purpose": purpose, "allowed": res["allowed"], "rule": res.get("rule"), "group": res.get("group")})
    out["ai_crawlers"] = bots
    blocked_search = [b["bot"] for b in bots if b["allowed"] is False and ("search" in b["purpose"] or "user" in b["purpose"] or b["bot"] == "Bingbot")]
    blocked_training = [b["bot"] for b in bots if b["allowed"] is False and "training" in b["purpose"]]
    if blocked_search:
        issues.append({"severity": "high", "title": f"AI search/answer bots blocked: {', '.join(blocked_search)}",
                       "fix": "These bots fetch pages to cite them in ChatGPT, Claude, Perplexity and Copilot answers. Blocking them removes you from those answers."})
    if blocked_training:
        issues.append({"severity": "info", "title": f"AI training crawlers blocked: {', '.join(blocked_training)}",
                       "fix": "A business choice. Blocking training bots does not remove you from AI search answers if the search bots are allowed."})

    # Firewall / CDN blocks: same URL, AI user agents.
    probes = [("GPTBot", "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; GPTBot/1.2; +https://openai.com/gptbot"),
              ("ClaudeBot", "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)"),
              ("PerplexityBot", "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)")]
    results = http.pmap(lambda p: (p[0], http.fetch(url, ua=p[1], timeout=15, use_cache=False, max_bytes=300_000)), probes, workers=3)
    probe_out = []
    for name, r in results:
        rec = {"bot": name, "status": r.status, "error": r.error}
        if page.status == 200 and (r.status in (401, 403, 429, 503) or r.error):
            rec["blocked_by_server"] = True
            issues.append({"severity": "high", "title": f"Server/CDN blocks {name} (HTTP {r.status or r.error})",
                           "fix": "Your firewall or CDN bot protection blocks this crawler even though robots.txt may allow it. "
                                  "Allow verified AI bots in Cloudflare (Security → Bots) or your WAF."})
        probe_out.append(rec)
    out["user_agent_probes"] = probe_out
    out["note_on_probes"] = "Probes come from your IP, not the vendors' IPs, so IP-based allowlists can still differ."

    if page.ok and page.is_html:
        js = js_dependency(page.text)
        out["javascript"] = js
        if js["likely_client_rendered"]:
            issues.append({"severity": "high", "title": f"Content needs JavaScript ({js['words_in_initial_html']} words in the HTML)",
                           "fix": "Most AI crawlers (GPTBot, ClaudeBot, PerplexityBot) don't run JavaScript. Server-render or prerender the content (SSR/SSG)."})
        doc = Document(page.text)
        rob = ",".join(doc.meta("robots")).lower()
        if "noai" in rob or "noimageai" in rob:
            out["noai_meta"] = True
        if "nosnippet" in rob:
            issues.append({"severity": "high", "title": "nosnippet stops Google AI Overviews and AI Mode from quoting this page"})
        has_schema = any(s.get("type") == "application/ld+json" for s in doc.find_all("script"))
        out["structured_data"] = has_schema
        if not has_schema:
            issues.append({"severity": "medium", "title": "No JSON-LD structured data", "fix": "Entities (Organization, Product, Article, author) help AI systems understand and attribute your content."})
        if not doc.find_all({"h2", "h3"}):
            issues.append({"severity": "low", "title": "No subheadings", "fix": "Question-style H2/H3s with a direct answer below are easy for AI systems to quote."})
    elif not page.ok:
        issues.append({"severity": "critical", "title": f"Page itself returns {page.status or page.error}"})

    out["llms_txt"] = llms_txt(url)
    if not out["llms_txt"]["llms.txt"]["exists"]:
        issues.append({"severity": "low", "title": "No /llms.txt",
                       "fix": "Optional proposal (llmstxt.org): a Markdown index of your key pages for LLMs. No major AI search engine has confirmed using it yet, so treat it as low priority."})
    out["issues"] = issues
    return out
