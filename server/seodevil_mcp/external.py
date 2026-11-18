"""Free external data sources: Google PageSpeed Insights (Core Web Vitals) and search autocomplete."""
from __future__ import annotations

import json
import os
import string
import urllib.parse
from collections import defaultdict
from typing import Dict, List, Optional

from . import http

# --- PageSpeed Insights / CrUX ------------------------------------------------------

PSI = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
FIELD_METRICS = {
    "LARGEST_CONTENTFUL_PAINT_MS": ("LCP", "ms", 2500, 4000),
    "INTERACTION_TO_NEXT_PAINT": ("INP", "ms", 200, 500),
    "CUMULATIVE_LAYOUT_SHIFT_SCORE": ("CLS", "", 0.1, 0.25),
    "FIRST_CONTENTFUL_PAINT_MS": ("FCP", "ms", 1800, 3000),
    "EXPERIMENTAL_TIME_TO_FIRST_BYTE": ("TTFB", "ms", 800, 1800),
}
LAB = ["largest-contentful-paint", "cumulative-layout-shift", "total-blocking-time", "first-contentful-paint", "speed-index", "server-response-time"]


def _field(block: Optional[Dict]) -> Optional[Dict]:
    if not block or not block.get("metrics"):
        return None
    out = {"overall": block.get("overall_category")}
    for key, (name, unit, _, _) in FIELD_METRICS.items():
        m = block["metrics"].get(key)
        if m:
            p = m.get("percentile")
            if key == "CUMULATIVE_LAYOUT_SHIFT_SCORE" and p is not None:
                p = p / 100
            out[name] = {"p75": p, "unit": unit, "rating": (m.get("category") or "").lower()}
    return out


def pagespeed(url: str, strategy: str = "mobile") -> Dict:
    url = http.normalize_input_url(url)
    key = os.environ.get("PAGESPEED_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    q = {"url": url, "strategy": strategy if strategy in ("mobile", "desktop") else "mobile", "category": "performance"}
    if key:
        q["key"] = key
    r = http.fetch(f"{PSI}?{urllib.parse.urlencode(q)}", timeout=120, use_cache=False, headers={"Accept": "application/json"}, max_bytes=30_000_000)
    if r.error:
        return {"error": r.error}
    try:
        data = json.loads(r.text)
    except ValueError:
        return {"error": f"Unexpected response (HTTP {r.status})"}
    if "error" in data:
        msg = data["error"].get("message", "")
        hint = "" if key else " Without an API key PageSpeed Insights is heavily rate-limited; set PAGESPEED_API_KEY (free in Google Cloud console)."
        return {"error": f"PageSpeed Insights: {msg}.{hint}"}
    lh = data.get("lighthouseResult", {})
    audits = lh.get("audits", {})
    perf = (lh.get("categories", {}).get("performance") or {}).get("score")
    lab = {k: {"value": audits[k].get("displayValue"), "score": audits[k].get("score")} for k in LAB if k in audits}
    opps = []
    for a in audits.values():
        det = a.get("details") or {}
        if det.get("type") == "opportunity" and (a.get("score") or 0) < 0.9 and (det.get("overallSavingsMs") or 0) > 50:
            items = [i.get("url") or i.get("source", {}).get("url") for i in det.get("items", [])[:5]]
            opps.append({"id": a["id"], "title": a.get("title"), "savings_ms": round(det.get("overallSavingsMs", 0)),
                         "savings_kb": round((det.get("overallSavingsBytes") or 0) / 1024), "items": [i for i in items if i]})
    opps.sort(key=lambda o: -o["savings_ms"])
    diags = []
    for aid in ("largest-contentful-paint-element", "layout-shifts", "long-tasks", "third-party-summary", "dom-size",
                "bootup-time", "mainthread-work-breakdown", "uses-long-cache-ttl", "font-display", "unsized-images", "lcp-lazy-loaded",
                "prioritize-lcp-image", "render-blocking-resources", "unused-javascript", "unused-css-rules", "modern-image-formats",
                "uses-responsive-images", "offscreen-images", "total-byte-weight"):
        a = audits.get(aid)
        if a and a.get("score") is not None and a["score"] < 0.9:
            d = {"id": aid, "title": a.get("title"), "value": a.get("displayValue")}
            det = a.get("details") or {}
            if aid == "largest-contentful-paint-element":
                try:
                    node = det["items"][0]["items"][0]["node"]
                    d["element"] = node.get("snippet")
                    d["selector"] = node.get("selector")
                except (KeyError, IndexError, TypeError):
                    pass
            diags.append(d)
    return {
        "url": url, "strategy": q["strategy"],
        "field_data_url": _field(data.get("loadingExperience")),
        "field_data_origin": _field(data.get("originLoadingExperience")),
        "performance_score": round(perf * 100) if perf is not None else None,
        "lab": lab, "opportunities": opps[:12], "diagnostics": diags[:15],
        "thresholds": "Good: LCP ≤ 2.5s, INP ≤ 200ms, CLS ≤ 0.1 at the 75th percentile (field data). Field data is what Google uses for ranking.",
    }


# --- keyword ideas from autocomplete --------------------------------------------------

QUESTION = ["how", "what", "why", "when", "where", "which", "who", "can", "is", "does", "are", "should"]
COMMERCIAL = ["best", "top", "cheap", "price", "cost", "review", "vs", "alternative", "buy", "near me", "for", "without", "with"]
INTENT_WORDS = {
    "transactional": {"buy", "price", "pricing", "cost", "cheap", "deal", "discount", "coupon", "order", "hire", "quote", "booking", "book", "rent", "for sale", "near me", "subscription", "free trial"},
    "commercial": {"best", "top", "review", "reviews", "vs", "versus", "alternative", "alternatives", "compare", "comparison", "worth it", "pros and cons"},
    "navigational": {"login", "sign in", "download", "official", "contact", "customer service", "phone number"},
}


def _intent(q: str) -> str:
    ql = f" {q.lower()} "
    for intent, words in INTENT_WORDS.items():
        if any(f" {w} " in ql for w in words):
            return intent
    if ql.split()[0] in QUESTION or ql.strip().endswith("?"):
        return "informational (question)"
    return "informational"


def _suggest(q: str, lang: str, country: str) -> List[str]:
    out = []
    g = http.fetch("https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode(
        {"client": "firefox", "hl": lang, "gl": country, "q": q, "ie": "utf-8", "oe": "utf-8"}), timeout=10, ua=http.BROWSER_UA)
    try:
        out += json.loads(g.text)[1]
    except (ValueError, IndexError, TypeError):
        pass
    if not out:
        d = http.fetch("https://duckduckgo.com/ac/?" + urllib.parse.urlencode({"q": q, "type": "list", "kl": f"{country}-{lang}"}), timeout=10, ua=http.BROWSER_UA)
        try:
            out += json.loads(d.text)[1]
        except (ValueError, IndexError, TypeError):
            pass
    return [s.strip() for s in out if isinstance(s, str) and s.strip()]


def keyword_ideas(seed: str, lang: str = "en", country: str = "us", depth: str = "standard") -> Dict:
    seed = seed.strip()
    if not seed:
        return {"error": "seed is required"}
    queries = [seed] + [f"{w} {seed}" for w in QUESTION[:8]] + [f"{seed} {w}" for w in COMMERCIAL]
    if depth == "deep":
        queries += [f"{seed} {c}" for c in string.ascii_lowercase]
    elif depth == "quick":
        queries = queries[:6]
    hits: Dict[str, Dict] = {}
    results = http.pmap(lambda q: (q, _suggest(q, lang, country)), queries, workers=4)
    for q, sugg in results:
        for pos, s in enumerate(sugg):
            k = s.lower()
            h = hits.setdefault(k, {"keyword": s, "seen": 0, "best_position": pos + 1})
            h["seen"] += 1
            h["best_position"] = min(h["best_position"], pos + 1)
    groups: Dict[str, List] = defaultdict(list)
    seed_words = set(seed.lower().split())
    for h in sorted(hits.values(), key=lambda x: (-x["seen"], x["best_position"], x["keyword"])):
        if h["keyword"].lower() == seed.lower():
            continue
        h["intent"] = _intent(h["keyword"])
        h["words"] = len(h["keyword"].split())
        h["modifier"] = " ".join(w for w in h["keyword"].lower().split() if w not in seed_words)[:60]
        groups[h["intent"]].append(h)
    return {
        "seed": seed, "lang": lang, "country": country, "queries_sent": len(queries), "ideas": sum(len(v) for v in groups.values()),
        "by_intent": dict(groups),
        "note": "From Google/DuckDuckGo autocomplete: real searches, but no volumes. 'seen' = how many expansions surfaced it "
                "(a rough popularity signal). Validate volume/difficulty in Search Console, Keyword Planner or a paid tool.",
    }
