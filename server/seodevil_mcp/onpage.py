"""On-page analyzers. Each takes a Page and a Report and records issues + data.

None of these make network requests, so they also run on local HTML files.
"""
from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import textstats as ts
from .dom import Document, Node, word_list
from .report import Report


@dataclass
class Page:
    url: str
    html: str
    status: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    elapsed_ms: int = 0
    redirects: list = field(default_factory=list)
    local: bool = False
    _doc: Optional[Document] = None

    @property
    def doc(self) -> Document:
        if self._doc is None:
            self._doc = Document(self.html)
        return self._doc

    @property
    def size_bytes(self) -> int:
        return len(self.html.encode("utf-8", "ignore"))

    @property
    def host(self) -> str:
        return (urllib.parse.urlsplit(self.url).hostname or "").lower()

    @property
    def is_https(self) -> bool:
        return self.url.lower().startswith("https://")

    def abs(self, href: str) -> str:
        base = self.doc.find("base")
        root = urllib.parse.urljoin(self.url, base.get("href")) if base is not None and base.get("href") else self.url
        return urllib.parse.urljoin(root, (href or "").strip())

    def robots_directives(self) -> List[str]:
        vals = []
        for name in ("robots", "googlebot"):
            for v in self.doc.meta(name):
                vals += [x.strip().lower() for x in v.split(",") if x.strip()]
        hdr = self.headers.get("x-robots-tag", "")
        for part in hdr.split(","):
            part = part.strip().lower()
            if ":" in part and not part.startswith(("max-", "unavailable_after")):
                part = part.split(":", 1)[1].strip()  # "googlebot: noindex"
            if part:
                vals.append(part)
        return vals

    @property
    def noindex(self) -> bool:
        d = self.robots_directives()
        return "noindex" in d or "none" in d


def _clip(s: str, n: int = 120) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


# --- meta / head ----------------------------------------------------------------

def analyze_meta(p: Page, r: Report) -> None:
    doc = p.doc
    titles = [t.text(skip=set()) for t in doc.find_all("title") if not any(a.tag == "svg" for a in t.ancestors())]
    title = titles[0].strip() if titles else ""
    descs = doc.meta("description")
    desc = descs[0] if descs else ""
    r.data["title"] = title
    r.data["meta_description"] = desc

    if not title:
        r.add("title_missing", "critical", "meta", "Missing <title> tag",
              fix="Add a unique, descriptive <title> (about 50-60 characters) inside <head>.")
    else:
        prev = ts.serp_preview(title, desc, p.url)
        px = prev["title"]["pixels"]
        r.data["title_length"] = len(title)
        r.data["title_pixels"] = px
        if len(titles) > 1:
            r.add("title_multiple", "medium", "meta", f"{len(titles)} <title> tags found",
                  detail="Browsers and Google use the first one; the rest are ignored or cause confusion.",
                  fix="Keep exactly one <title> in <head>.", affected=titles)
        if len(title) < 20:
            r.add("title_too_short", "medium", "meta", f"Title is short ({len(title)} chars)",
                  detail=f'"{title}"', fix="Expand it to describe the page and include the main keyword (aim for 50-60 chars).")
        elif px > ts.TITLE_PX_LIMIT:
            r.add("title_too_long", "low", "meta", f"Title will likely be truncated ({len(title)} chars, ~{px}px)",
                  detail=f'Google shows about {ts.TITLE_PX_LIMIT}px: "{prev["title"]["displayed"]}"',
                  fix="Move the important words to the front and trim to about 50-60 characters.")
        else:
            r.ok("Title length is good")
        if title.isupper() and len(title) > 10:
            r.add("title_all_caps", "low", "meta", "Title is in all caps", fix="Use sentence or title case; Google may rewrite shouting titles.")
        if re.search(r"^(home|untitled|index|welcome|new page|document)$", title.strip(), re.I):
            r.add("title_generic", "high", "meta", f'Title is a placeholder: "{title}"', fix="Write a title that names the business/topic of this page.")

    if not desc:
        r.add("description_missing", "high", "meta", "Missing meta description",
              fix='Add <meta name="description" content="..."> with a 120-155 character summary that invites the click.')
    else:
        dpx = ts.pixel_width(desc, ts.DESC_FONT)
        r.data["description_length"] = len(desc)
        if len(descs) > 1:
            r.add("description_multiple", "medium", "meta", f"{len(descs)} meta descriptions found", fix="Keep one.", affected=descs)
        if len(desc) < 70:
            r.add("description_too_short", "low", "meta", f"Meta description is short ({len(desc)} chars)",
                  fix="Aim for 120-155 characters: what the page offers and why to click.")
        elif dpx > ts.DESC_PX_LIMIT or len(desc) > 165:
            r.add("description_too_long", "low", "meta", f"Meta description may be truncated ({len(desc)} chars)",
                  fix="Keep it under ~155 characters with the key point first.")
        else:
            r.ok("Meta description length is good")
        if title and desc.strip().lower() == title.strip().lower():
            r.add("description_equals_title", "low", "meta", "Meta description is identical to the title", fix="Write a description that adds detail.")

    html_el = doc.find("html")
    lang = html_el.get("lang") if html_el is not None else ""
    r.data["lang"] = lang
    if not lang:
        r.add("lang_missing", "low", "meta", "Missing lang attribute on <html>",
              fix='Add the page language, e.g. <html lang="en">. It helps search engines and screen readers.')

    if not doc.find("meta", charset=True) and not any("charset" in m.get("content").lower() for m in doc.find_all("meta", http_equiv="content-type")):
        r.add("charset_missing", "low", "meta", "No character encoding declared", fix='Add <meta charset="utf-8"> as the first element in <head>.')

    if not p.local and not doc.doctype:
        r.add("doctype_missing", "low", "technical", "Missing <!DOCTYPE html>", fix="Without a doctype browsers render in quirks mode.")

    if not doc.links("icon") and not doc.links("shortcut") and not doc.links("apple-touch-icon"):
        r.add("favicon_missing", "low", "meta", "No favicon declared",
              detail="Google shows the favicon next to results on mobile.",
              fix='Add <link rel="icon" href="/favicon.ico"> (square, at least 48x48).')

    if doc.meta("keywords"):
        r.add("meta_keywords", "info", "meta", "meta keywords tag present",
              detail="Google ignores it and it reveals your target keywords to competitors.", fix="Safe to remove.")


# --- indexability / canonical ---------------------------------------------------

def analyze_indexability(p: Page, r: Report) -> None:
    directives = p.robots_directives()
    r.data["robots_directives"] = directives
    if p.noindex:
        r.add("noindex", "critical", "indexability", "Page is set to noindex",
              detail="Search engines will drop this page from results. Source: "
              + ("X-Robots-Tag header" if "noindex" in p.headers.get("x-robots-tag", "").lower() else "meta robots"),
              fix="Remove noindex if this page should rank. Leave it only on pages you deliberately hide.")
    if "nofollow" in directives or "none" in directives:
        r.add("nofollow_page", "medium", "indexability", "Page-level nofollow is set",
              fix="Search engines won't follow any link on this page. Remove unless intentional.")
    if "nosnippet" in directives or "max-snippet:0" in directives:
        r.add("nosnippet", "medium", "indexability", "nosnippet blocks text snippets and AI Overviews from using this page")
    if "noarchive" in directives or "noimageindex" in directives:
        r.add("restrictive_robots", "info", "indexability", "Restrictive robots directives: " + ", ".join(d for d in directives if d in ("noarchive", "noimageindex")))

    canon = p.doc.links("canonical")
    hrefs = [c.get("href").strip() for c in canon if c.get("href").strip()]
    if not hrefs:
        r.add("canonical_missing", "medium", "indexability", "No canonical tag",
              fix=f'Add <link rel="canonical" href="{p.url.split("?")[0].split("#")[0]}"> so duplicate URLs (tracking params, http/www variants) consolidate.')
        r.data["canonical"] = None
        return
    target = p.abs(hrefs[0])
    r.data["canonical"] = target
    if len(set(hrefs)) > 1:
        r.add("canonical_multiple", "high", "indexability", f"{len(hrefs)} different canonical tags",
              detail="Google ignores all of them when they conflict.", fix="Keep exactly one canonical.", affected=hrefs)
    if not re.match(r"^https?://", hrefs[0], re.I):
        r.add("canonical_relative", "low", "indexability", "Canonical URL is relative", detail=hrefs[0], fix="Use an absolute URL.")
    if any(c for c in canon if any(a.tag == "body" for a in c.ancestors())):
        r.add("canonical_in_body", "high", "indexability", "Canonical tag is in <body>", fix="Google only reads rel=canonical in <head>.")
    norm = lambda u: u.split("#")[0].rstrip("/").lower()
    if norm(target) != norm(p.url):
        tgt_host = (urllib.parse.urlsplit(target).hostname or "").lower()
        if tgt_host and tgt_host != p.host:
            r.add("canonical_other_host", "medium", "indexability", "Canonical points to another host",
                  detail=f"{target}", fix="Fine for syndicated content; otherwise make it self-referencing.")
        else:
            r.add("canonicalized", "info", "indexability", "Canonical points to a different URL",
                  detail=f"This page defers to {target}. It will not rank on its own.")
        if target.startswith("http://") and p.is_https:
            r.add("canonical_http", "medium", "indexability", "Canonical points to an http:// URL from an https page", fix="Use the https URL.")
    else:
        r.ok("Self-referencing canonical")


# --- headings -------------------------------------------------------------------

def analyze_headings(p: Page, r: Report) -> None:
    hs = p.doc.find_all({"h1", "h2", "h3", "h4", "h5", "h6"})
    outline = [{"level": int(h.tag[1]), "text": _clip(h.text(skip={"script", "style"}), 150)} for h in hs]
    r.data["headings"] = outline[:60]
    h1 = [o["text"] for o in outline if o["level"] == 1]
    r.data["h1"] = h1
    if not h1:
        r.add("h1_missing", "high", "headings", "No H1 heading",
              fix="Add one <h1> that states the page's main topic (usually close to the title).")
    else:
        if len(h1) > 1:
            r.add("h1_multiple", "low", "headings", f"{len(h1)} H1 headings", detail="Allowed in HTML5 but one clear H1 is easier for search engines.",
                  affected=h1)
        if any(not t.strip() for t in h1):
            r.add("h1_empty", "high", "headings", "Empty H1", detail="Often an H1 that only wraps a logo image without alt text.",
                  fix="Give the H1 visible text.")
        if any(len(t) > 90 for t in h1):
            r.add("h1_too_long", "low", "headings", "H1 is very long", detail=h1[0][:120])
    prev = 0
    skips = []
    for o in outline:
        if prev and o["level"] > prev + 1:
            skips.append(f'H{prev} → H{o["level"]}: "{o["text"][:60]}"')
        prev = o["level"]
    if skips:
        r.add("heading_skips", "low", "headings", "Heading levels are skipped",
              fix="Use headings in order (H2 under H1, H3 under H2) so the outline makes sense.", affected=skips)
    empty = [h for h in outline if not h["text"]]
    if empty:
        r.add("heading_empty", "low", "headings", f"{len(empty)} empty heading(s)", fix="Remove empty heading tags or give them text.")
    if len([o for o in outline if o["level"] == 2]) == 0 and len(word_list(p.doc.main_text())) > 600:
        r.add("no_subheadings", "low", "headings", "Long content without H2 subheadings",
              fix="Break the content into sections with descriptive H2s; they help skimming and featured snippets.")


# --- images ---------------------------------------------------------------------

GENERIC_IMG = re.compile(r"(?:^|/)(?:img|image|dsc|dscn|pxl|photo|screenshot|screen shot|untitled|whatsapp image)[-_ ]?\d", re.I)


def analyze_images(p: Page, r: Report) -> None:
    imgs = p.doc.body.find_all("img")
    r.data["images"] = len(imgs)
    if not imgs:
        return
    no_alt, empty_alt, no_dims, no_lazy, generic, legacy, bad_alt = [], [], [], [], [], [], []
    for idx, img in enumerate(imgs):
        src = img.get("src") or img.get("data-src") or img.get("srcset").split(" ")[0]
        label = src[:150] or f"<img> #{idx + 1}"
        if not img.has("alt"):
            if img.get("role") != "presentation" and img.get("aria-hidden") != "true":
                no_alt.append(label)
        elif not img.get("alt").strip():
            empty_alt.append(label)
        else:
            alt = img.get("alt").strip()
            if re.match(r"^(image|img|photo|picture|logo|icon|banner|untitled)\d*$", alt, re.I) or re.search(r"\.(jpe?g|png|webp|gif)$", alt, re.I):
                bad_alt.append(f'{label} (alt="{alt}")')
        if not (img.get("width") and img.get("height")) and "aspect-ratio" not in img.get("style"):
            no_dims.append(label)
        if idx >= 3 and img.get("loading").lower() != "lazy" and not img.has("data-src"):
            no_lazy.append(label)
        path = urllib.parse.urlsplit(src).path
        if GENERIC_IMG.search(path):
            generic.append(label)
        if re.search(r"\.(bmp|tiff?)$", path, re.I):
            legacy.append(label)
    if no_alt:
        r.add("img_alt_missing", "medium", "images", f"{len(no_alt)} of {len(imgs)} images have no alt attribute",
              fix='Describe what each image shows in alt text; use alt="" only for purely decorative images.', affected=no_alt)
    if bad_alt:
        r.add("img_alt_poor", "low", "images", f"{len(bad_alt)} images have meaningless alt text", affected=bad_alt,
              fix="Replace file names and words like 'image' with a short description.")
    if empty_alt and len(empty_alt) == len(imgs) and len(imgs) > 2:
        r.add("img_alt_all_empty", "low", "images", "Every image has empty alt text", detail="Fine for decoration, but content images need descriptions.")
    if no_dims:
        r.add("img_dimensions_missing", "low", "images", f"{len(no_dims)} images lack width/height attributes",
              detail="Causes layout shift (CLS) while the page loads.", fix="Set width and height (or CSS aspect-ratio).", affected=no_dims)
    if len(no_lazy) >= 3:
        r.add("img_no_lazy", "low", "images", f"{len(no_lazy)} below-the-fold images are not lazy-loaded",
              fix='Add loading="lazy" to images after the first screen (never to the hero/LCP image).', affected=no_lazy)
    if generic:
        r.add("img_generic_filenames", "low", "images", f"{len(generic)} images have camera/default file names",
              fix="Rename to descriptive, hyphenated names (e.g. red-running-shoes.webp).", affected=generic)
    if legacy:
        r.add("img_legacy_format", "low", "images", "BMP/TIFF images found", fix="Convert to WebP or AVIF.", affected=legacy)
    first = imgs[0]
    if first.get("loading").lower() == "lazy":
        r.add("img_hero_lazy", "low", "performance", "First image is lazy-loaded",
              detail="If it's the LCP image this delays Largest Contentful Paint.", fix='Remove loading="lazy" and consider fetchpriority="high".')


# --- links ----------------------------------------------------------------------

GENERIC_ANCHORS = {
    "click here", "here", "read more", "more", "learn more", "this", "link", "this link", "click", "go",
    "details", "more info", "continue", "continue reading", "see more", "view more",
}


def extract_links(p: Page) -> List[Dict]:
    out = []
    for a in p.doc.find_all("a"):
        href = a.get("href").strip()
        if not href or href.startswith("#"):
            continue
        low = href.lower()
        if low.startswith(("mailto:", "tel:", "sms:", "javascript:", "data:", "whatsapp:", "skype:")):
            out.append({"href": href, "kind": low.split(":")[0], "text": _clip(a.text(), 80)})
            continue
        url = p.abs(href).split("#")[0]
        if not url.startswith(("http://", "https://")):
            continue
        img = a.find("img")
        text = a.text()
        out.append({
            "url": url,
            "text": _clip(text, 80),
            "img_alt": img.get("alt") if img is not None else None,
            "aria": a.get("aria-label") or a.get("title"),
            "rel": a.get("rel").lower(),
            "internal": (urllib.parse.urlsplit(url).hostname or "").lower().removeprefix("www.") == p.host.removeprefix("www."),
            "in_nav": any(x.tag in ("nav", "header", "footer") for x in a.ancestors()),
        })
    return out


def analyze_links(p: Page, r: Report) -> List[Dict]:
    links = extract_links(p)
    web = [l for l in links if "url" in l]
    internal = [l for l in web if l["internal"]]
    external = [l for l in web if not l["internal"]]
    r.data["links"] = {
        "internal": len(internal), "external": len(external),
        "unique_internal": len({l["url"] for l in internal}), "unique_external": len({l["url"] for l in external}),
    }
    js = [l["href"] for l in links if l.get("kind") == "javascript"]
    if js:
        r.add("links_javascript", "low", "links", f"{len(js)} javascript: links", detail="Search engines can't follow them.",
              fix="Use real <a href> URLs; attach behaviour with event listeners.")
    empty = [l["url"] for l in web if not l["text"] and not (l["img_alt"] or "").strip() and not (l["aria"] or "").strip()]
    if empty:
        r.add("links_no_anchor_text", "medium", "links", f"{len(empty)} links have no anchor text",
              detail="Usually an icon or image link without alt/aria-label.", fix="Give every link descriptive text, alt or aria-label.", affected=empty)
    generic = [f'{l["text"]} → {l["url"]}' for l in web if l["text"].lower().strip(" .!→>»") in GENERIC_ANCHORS]
    if generic:
        r.add("links_generic_anchor", "low", "links", f"{len(generic)} links use generic anchor text",
              fix='Replace "click here"/"read more" with words that describe the target page.', affected=generic)
    nofollow_int = [l["url"] for l in internal if "nofollow" in l["rel"].split()]
    if nofollow_int:
        r.add("links_internal_nofollow", "low", "links", f"{len(nofollow_int)} internal links are nofollow",
              fix="Don't nofollow your own pages; it wastes internal link equity.", affected=nofollow_int)
    if p.is_https:
        http_int = [l["url"] for l in internal if l["url"].startswith("http://")]
        if http_int:
            r.add("links_internal_http", "medium", "links", f"{len(http_int)} internal links point to http://",
                  fix="Link straight to the https URLs to avoid a redirect on every click.", affected=http_int)
    blank_unsafe = [a.get("href") for a in p.doc.find_all("a", target="_blank") if "noopener" not in a.get("rel") and "noreferrer" not in a.get("rel") and a.get("href").startswith("http")]
    if len(web) > 300:
        r.add("links_too_many", "low", "links", f"{len(web)} links on one page", detail="Dilutes internal link value and overwhelms users.")
    if not internal and not p.local:
        r.add("links_no_internal", "medium", "links", "No internal links",
              fix="Link to related pages on your site so crawlers and users can continue.")
    r.data["links"]["target_blank_without_noopener"] = len(blank_unsafe)
    return links


# --- social ---------------------------------------------------------------------

def analyze_social(p: Page, r: Report) -> None:
    doc = p.doc
    og = {k: doc.meta1(f"og:{k}") for k in ("title", "description", "image", "url", "type", "site_name")}
    tw = {k: doc.meta1(f"twitter:{k}") for k in ("card", "title", "description", "image", "site")}
    r.data["open_graph"] = {k: v for k, v in og.items() if v}
    r.data["twitter"] = {k: v for k, v in tw.items() if v}
    missing = [f"og:{k}" for k in ("title", "description", "image", "url", "type") if not og[k]]
    if len(missing) == 5:
        r.add("og_missing", "medium", "social", "No Open Graph tags",
              detail="Links shared on Facebook, LinkedIn, Slack, WhatsApp, iMessage show no image or a random one.",
              fix="Add og:title, og:description, og:image (1200x630), og:url and og:type.")
    elif missing:
        sev = "medium" if "og:image" in missing else "low"
        r.add("og_incomplete", sev, "social", "Open Graph tags incomplete", affected=missing,
              fix="Add the missing tags; og:image matters most for click-through on shares.")
    if og["image"] and not re.match(r"^https?://", og["image"]):
        r.add("og_image_relative", "medium", "social", "og:image is not an absolute URL", detail=og["image"],
              fix="Most scrapers need an absolute https URL.")
    if not tw["card"]:
        r.add("twitter_card_missing", "low", "social", "No twitter:card tag",
              detail="X falls back to Open Graph but defaults to a small summary card.",
              fix='Add <meta name="twitter:card" content="summary_large_image">.')


# --- mobile ---------------------------------------------------------------------

def analyze_mobile(p: Page, r: Report) -> None:
    vp = p.doc.meta1("viewport")
    r.data["viewport"] = vp or None
    if not vp:
        r.add("viewport_missing", "high", "mobile", "No viewport meta tag",
              detail="Phones render the page at desktop width; Google indexes the mobile version.",
              fix='Add <meta name="viewport" content="width=device-width, initial-scale=1">.')
        return
    v = vp.lower().replace(" ", "")
    if "width=device-width" not in v:
        r.add("viewport_fixed", "medium", "mobile", "Viewport doesn't use width=device-width", detail=vp)
    if "user-scalable=no" in v or "user-scalable=0" in v or re.search(r"maximum-scale=1(\.0)?(,|$)", v):
        r.add("viewport_no_zoom", "low", "mobile", "Viewport blocks zooming", detail=vp,
              fix="Remove user-scalable=no / maximum-scale=1; blocking zoom fails accessibility guidelines.")
    if p.doc.find_all("embed") or [o for o in p.doc.find_all("object") if "flash" in o.get("type")]:
        r.add("plugins_used", "medium", "mobile", "Uses <embed>/<object> plugins that phones can't run")


# --- content --------------------------------------------------------------------

PLACEHOLDER = re.compile(r"lorem ipsum|dolor sit amet|\[insert|your text here|sample text", re.I)


def analyze_content(p: Page, r: Report, keyword: Optional[str] = None) -> None:
    text = p.doc.main_text()
    words = word_list(text)
    all_words = word_list(p.doc.body.text())
    r.data["word_count"] = len(words)
    r.data["word_count_total"] = len(all_words)
    if p.size_bytes:
        r.data["text_to_html_ratio_pct"] = round(100 * len(p.doc.body.text()) / p.size_bytes, 1)
    if len(words) < 300 and not p.noindex:
        sev = "medium" if len(words) < 150 else "low"
        r.add("thin_content", sev, "content", f"Thin content ({len(words)} words in main content)",
              detail="Not a hard rule, but short pages rarely rank for competitive queries unless the intent is simple (contact, login...).",
              fix="Cover the topic fully: answer the questions a searcher has, add specifics, examples, FAQs.")
    if PLACEHOLDER.search(text):
        r.add("placeholder_text", "high", "content", "Placeholder text found (lorem ipsum)", fix="Replace with real content before publishing.")
    rd = ts.readability(text)
    r.data["readability"] = rd
    if rd.get("flesch_reading_ease") is not None and rd["flesch_reading_ease"] < 30 and (p.doc.find("html") or p.doc.root).get("lang", "en")[:2] in ("en", ""):
        r.add("hard_to_read", "low", "content", f'Text is hard to read (Flesch {rd["flesch_reading_ease"]})',
              fix="Shorter sentences, plainer words, more paragraphs and lists.")
    if keyword:
        hs = r.data.get("headings") or []
        usage = ts.keyword_usage(
            keyword,
            title=r.data.get("title", ""),
            description=r.data.get("meta_description", ""),
            h1=[h["text"] for h in hs if h["level"] == 1],
            headings=[h["text"] for h in hs if h["level"] > 1],
            url=p.url,
            body_text=text,
            alts=[i.get("alt") for i in p.doc.find_all("img") if i.get("alt")],
        )
        usage["relevance_score"] = ts.score_keyword_relevance(usage)
        r.data["keyword"] = usage
        ts.keyword_issues(usage, r.add)


# --- technical (header- and markup-based; no extra requests) -------------------

def analyze_technical(p: Page, r: Report) -> None:
    doc = p.doc
    if not p.local:
        r.data["status"] = p.status
        r.data["response_ms"] = p.elapsed_ms
        if p.status >= 400:
            r.add("http_error", "critical", "technical", f"Page returns HTTP {p.status}", fix="Fix the page or 301-redirect it to the closest working URL.")
        if not p.is_https:
            r.add("no_https", "critical", "security", "Page is served over plain HTTP",
                  fix="Install a TLS certificate and 301-redirect all http:// URLs to https://.")
        if len(p.redirects) > 1:
            r.add("redirect_chain", "medium", "technical", f"Reached through {len(p.redirects)} redirects",
                  affected=[f'{h["status"]} {h["url"]}' for h in p.redirects], fix="Link and redirect straight to the final URL.")
        elif len(p.redirects) == 1 and p.redirects[0]["status"] in (302, 307):
            r.add("temporary_redirect", "low", "technical", f'Temporary {p.redirects[0]["status"]} redirect to this page',
                  detail=p.redirects[0]["url"], fix="Use 301 for permanent moves so ranking signals pass.")
        if p.elapsed_ms > 1800:
            r.add("slow_response", "medium", "performance", f"Slow server response ({p.elapsed_ms} ms incl. download)",
                  fix="Check hosting, caching (page cache/CDN) and slow database queries. Aim for under 800 ms TTFB.")
        enc = p.headers.get("content-encoding", "")
        if p.size_bytes > 1400 and not enc:
            r.add("no_compression", "medium", "performance", "HTML is not compressed",
                  fix="Enable gzip or Brotli on the server/CDN; text shrinks ~70%.")
        cc = p.headers.get("cache-control", "")
        r.data["cache_control"] = cc or None

    if p.size_bytes > 500_000:
        r.add("html_too_large", "medium", "performance", f"HTML is {p.size_bytes // 1024} KB",
              detail="Usually inlined data/JSON from a framework, or huge inline SVG/CSS.", fix="Keep HTML under ~100 KB where possible.")

    url_path = urllib.parse.urlsplit(p.url).path
    url_issues = []
    if len(p.url) > 115:
        url_issues.append(f"long ({len(p.url)} chars)")
    if "_" in url_path:
        url_issues.append("underscores (use hyphens)")
    if re.search(r"[A-Z]", url_path):
        url_issues.append("uppercase letters")
    if re.search(r"%20| ", url_path):
        url_issues.append("spaces")
    if url_path.count("/") > 6:
        url_issues.append("deeply nested")
    if url_issues and not p.local:
        r.add("url_format", "low", "technical", "URL could be cleaner: " + ", ".join(url_issues), detail=p.url,
              fix="Short, lowercase, hyphenated URLs. Only change live URLs with a 301 redirect.")

    # hreflang (markup only; check_hreflang verifies return links)
    alts = [l for l in doc.links("alternate") if l.get("hreflang")]
    if alts:
        codes = [l.get("hreflang").strip() for l in alts]
        r.data["hreflang"] = [{"lang": l.get("hreflang"), "href": p.abs(l.get("href"))} for l in alts]
        bad = [c for c in codes if not valid_hreflang(c)]
        if bad:
            r.add("hreflang_invalid", "high", "international", "Invalid hreflang codes", affected=bad,
                  fix="Use ISO 639-1 language (+ optional ISO 3166-1 region), e.g. en, en-GB, pt-BR, x-default. 'en-UK' is wrong (en-GB).")
        hrefs = {p.abs(l.get("href")).rstrip("/") for l in alts}
        if p.url.rstrip("/") not in hrefs:
            r.add("hreflang_no_self", "medium", "international", "hreflang set doesn't include this page itself",
                  fix="Each language version must list itself as well as the others.")
        if "x-default" not in [c.lower() for c in codes]:
            r.add("hreflang_no_xdefault", "low", "international", "No x-default hreflang", fix="Add x-default for users whose language you don't target.")
        dup = {c for c in codes if codes.count(c) > 1}
        if dup:
            r.add("hreflang_duplicate", "medium", "international", "Duplicate hreflang codes", affected=sorted(dup))

    # mixed content
    if p.is_https:
        mixed = []
        for tag, attr in (("img", "src"), ("script", "src"), ("link", "href"), ("iframe", "src"), ("source", "src"), ("video", "src"), ("audio", "src")):
            for n in doc.find_all(tag):
                v = n.get(attr)
                if v.startswith("http://") and not (tag == "link" and n.get("rel").lower() in ("canonical", "alternate")):
                    mixed.append(f"<{tag}> {v[:140]}")
        if mixed:
            r.add("mixed_content", "high", "security", f"{len(mixed)} resources load over http:// on an https page",
                  detail="Browsers block or warn about these.", fix="Change them to https:// (or protocol-relative).", affected=mixed)

    deprecated = sorted({n.tag for n in doc.find_all({"font", "center", "marquee", "blink", "frameset", "frame"})})
    if deprecated:
        r.add("deprecated_html", "low", "technical", "Deprecated HTML tags: " + ", ".join(deprecated))
    if doc.find("meta", http_equiv="refresh"):
        r.add("meta_refresh", "medium", "technical", "Meta refresh found",
              fix="Use a server-side 301 redirect instead; meta refresh is slow and confusing for crawlers.")

    # render-blocking & weight hints
    head = doc.head
    blocking = [s.get("src") for s in head.find_all("script") if s.get("src") and not s.has("async") and not s.has("defer") and s.get("type") != "module"]
    if blocking:
        r.add("render_blocking_scripts", "low", "performance", f"{len(blocking)} render-blocking scripts in <head>",
              fix="Add defer (or async for independent scripts) so the page can paint sooner.", affected=blocking)
    scripts = doc.find_all("script")
    css = [l for l in doc.links("stylesheet")]
    r.data["resources"] = {
        "scripts_external": len([s for s in scripts if s.get("src")]),
        "scripts_inline_kb": round(sum(len("".join(c for c in s.children if isinstance(c, str))) for s in scripts if not s.get("src")) / 1024, 1),
        "stylesheets": len(css),
        "iframes": len(doc.find_all("iframe")),
        "html_kb": round(p.size_bytes / 1024, 1),
    }
    if len(css) > 8:
        r.add("many_stylesheets", "low", "performance", f"{len(css)} separate stylesheets", fix="Bundle CSS and inline the critical part.")


def analyze_security_headers(p: Page, r: Report) -> None:
    if p.local or not p.headers:
        return
    h = p.headers
    missing = []
    if p.is_https and "strict-transport-security" not in h:
        missing.append("Strict-Transport-Security")
    if "x-content-type-options" not in h:
        missing.append("X-Content-Type-Options: nosniff")
    if "x-frame-options" not in h and "frame-ancestors" not in h.get("content-security-policy", ""):
        missing.append("X-Frame-Options or CSP frame-ancestors")
    if "content-security-policy" not in h:
        missing.append("Content-Security-Policy")
    if "referrer-policy" not in h:
        missing.append("Referrer-Policy")
    r.data["security_headers_missing"] = missing
    if missing:
        r.add("security_headers", "low", "security", f"{len(missing)} security headers missing", affected=missing,
              detail="Not a ranking factor, but HSTS also saves an http→https redirect for returning visitors.",
              fix="Set them at the web server or CDN.")
    server = h.get("x-powered-by") or ""
    if re.search(r"\d", server):
        r.add("version_disclosure", "low", "security", f"X-Powered-By reveals version: {server}", fix="Remove the header.")


ANALYZERS = [analyze_meta, analyze_indexability, analyze_headings, analyze_images, analyze_links,
             analyze_social, analyze_mobile, analyze_technical, analyze_security_headers]


def run_onpage(p: Page, keyword: Optional[str] = None) -> Report:
    from . import schema  # local import avoids a cycle

    r = Report()
    for fn in ANALYZERS:
        fn(p, r)
    analyze_content(p, r, keyword)
    schema.analyze_schema(p, r)
    return r


_HREFLANG = re.compile(r"^(x-default|[a-z]{2,3}(-[a-z]{4})?(-([a-z]{2}|\d{3}))?)$", re.I)
_BAD_REGIONS = {"en-uk": "en-gb", "jp": "ja", "cn": "zh", "kr": "ko", "dk": "da", "se": "sv", "gr": "el", "cz": "cs"}


def valid_hreflang(code: str) -> bool:
    c = code.strip().lower()
    if not _HREFLANG.match(c):
        return False
    lang = c.split("-")[0]
    region = c.split("-")[-1] if "-" in c else ""
    if c in _BAD_REGIONS or lang in ("jp", "cn", "kr", "dk", "se", "gr", "cz") or region == "uk":
        return False
    return True
