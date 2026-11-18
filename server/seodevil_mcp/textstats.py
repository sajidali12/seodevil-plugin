"""Text measurements: SERP pixel widths, readability, keyword usage and term extraction."""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Dict, List, Optional

from .dom import word_list

# Arial/Helvetica advance widths in 1/1000 em for printable ASCII (from the Helvetica AFM).
_W = dict(zip(
    " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~",
    [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
     556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
     1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
     667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
     333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
     556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584],
))

TITLE_PX_LIMIT = 580   # Google desktop title, 20px Arial
DESC_PX_LIMIT = 920    # roughly two lines of 14px Arial on desktop
TITLE_FONT, DESC_FONT = 20, 14


def char_width(ch: str) -> int:
    if ch in _W:
        return _W[ch]
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 1000
    base = unicodedata.normalize("NFKD", ch)[:1]
    return _W.get(base, 556)


def pixel_width(text: str, font_px: int) -> int:
    return round(sum(char_width(c) for c in text) * font_px / 1000)


def truncate_px(text: str, font_px: int, limit: int) -> str:
    if pixel_width(text, font_px) <= limit:
        return text
    ell = pixel_width(" ...", font_px)
    out, w = [], 0
    for ch in text:
        w += char_width(ch) * font_px / 1000
        if w + ell > limit:
            break
        out.append(ch)
    cut = "".join(out)
    if " " in cut[-15:]:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,;:-|") + " ..."


def serp_preview(title: str, description: str, url: str = "") -> Dict:
    title, description = (title or "").strip(), (description or "").strip()
    tw, dw = pixel_width(title, TITLE_FONT), pixel_width(description, DESC_FONT)
    crumb = ""
    if url:
        m = re.match(r"https?://([^/]+)(/.*)?", url)
        if m:
            host, path = m.group(1), (m.group(2) or "").split("?")[0]
            segs = [s for s in path.split("/") if s]
            crumb = host + "".join(f" › {s}" for s in segs[:3])
    return {
        "title": {
            "text": title, "chars": len(title), "pixels": tw, "limit_px": TITLE_PX_LIMIT,
            "truncated": tw > TITLE_PX_LIMIT, "displayed": truncate_px(title, TITLE_FONT, TITLE_PX_LIMIT),
        },
        "description": {
            "text": description, "chars": len(description), "pixels": dw, "limit_px": DESC_PX_LIMIT,
            "truncated": dw > DESC_PX_LIMIT, "displayed": truncate_px(description, DESC_FONT, DESC_PX_LIMIT),
        },
        "url_display": crumb,
        "note": "Pixel widths are estimates using Arial metrics. Google may rewrite titles and snippets.",
    }


# --- readability ---------------------------------------------------------------

def _syllables(word: str) -> int:
    word = word.lower().strip("'’")
    if len(word) <= 3:
        return 1
    word = re.sub(r"(?:es|ed|e)$", "", word) or word
    groups = re.findall(r"[aeiouy]+", word)
    return max(1, len(groups))


def sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    return [p for p in (s.strip() for s in parts) if len(word_list(p)) >= 1]


def readability(text: str) -> Dict:
    words = word_list(text)
    sents = sentences(text)
    if len(words) < 30 or not sents:
        return {"words": len(words), "note": "Not enough text to score readability."}
    syll = sum(_syllables(w) for w in words)
    wps = len(words) / len(sents)
    spw = syll / len(words)
    fre = 206.835 - 1.015 * wps - 84.6 * spw
    fk = 0.39 * wps + 11.8 * spw - 15.59
    long_sents = sum(1 for s in sents if len(word_list(s)) > 25)
    if fre >= 70:
        band = "easy"
    elif fre >= 50:
        band = "fairly difficult"
    elif fre >= 30:
        band = "difficult"
    else:
        band = "very difficult"
    return {
        "words": len(words),
        "sentences": len(sents),
        "avg_words_per_sentence": round(wps, 1),
        "flesch_reading_ease": round(fre, 1),
        "flesch_kincaid_grade": round(fk, 1),
        "band": band,
        "long_sentences_pct": round(100 * long_sents / len(sents), 1),
        "note": "Flesch scores are calibrated for English.",
    }


# --- terms ------------------------------------------------------------------

STOPWORDS = set("""
a about above after again against all also am an and any are aren't as at be because been before being below
between both but by can can't cannot could couldn't did didn't do does doesn't doing don't down during each few
for from further get got had hadn't has hasn't have haven't having he he'd he'll he's her here here's hers herself
him himself his how how's i i'd i'll i'm i've if in into is isn't it it's its itself just let's like me more most
mustn't my myself no nor not now of off on once only or other ought our ours ourselves out over own same shan't she
she'd she'll she's should shouldn't so some such than that that's the their theirs them themselves then there
there's these they they'd they'll they're they've this those through to too under until up us very was wasn't we
we'd we'll we're we've were weren't what what's when when's where where's which while who who's whom why why's will
with won't would wouldn't you you'd you'll you're you've your yours yourself yourselves one two use used using new
may many much via per within without yet will make made see see also every across
""".split())


def top_terms(text: str, n: int = 25) -> Dict[str, List]:
    words = word_list(text)
    content = [w for w in words if w not in STOPWORDS and len(w) > 2 and not w.isdigit()]
    uni = Counter(content).most_common(n)
    bi: Counter = Counter()
    tri: Counter = Counter()
    for i in range(len(words) - 1):
        a, b = words[i], words[i + 1]
        if a in STOPWORDS or b in STOPWORDS or a.isdigit() or b.isdigit():
            continue
        bi[f"{a} {b}"] += 1
        if i + 2 < len(words):
            c = words[i + 2]
            if c not in STOPWORDS and not c.isdigit():
                tri[f"{a} {b} {c}"] += 1
    return {
        "terms": [[t, c] for t, c in uni],
        "phrases": [[t, c] for t, c in bi.most_common(n) if c > 1],
        "long_phrases": [[t, c] for t, c in tri.most_common(n // 2) if c > 1],
    }


def count_phrase(text: str, phrase: str) -> int:
    words = word_list(text)
    kw = word_list(phrase)
    if not kw:
        return 0
    n = len(kw)
    return sum(1 for i in range(len(words) - n + 1) if words[i:i + n] == kw)


def contains_phrase(text: str, phrase: str) -> bool:
    return count_phrase(text, phrase) > 0


def partial_match(text: str, phrase: str) -> float:
    """Share of the keyword's (non-stopword) words that appear in text."""
    kw = [w for w in word_list(phrase) if w not in STOPWORDS] or word_list(phrase)
    if not kw:
        return 0.0
    words = set(word_list(text))
    return sum(1 for w in kw if w in words or w.rstrip("s") in words or w + "s" in words) / len(kw)


def keyword_usage(keyword: str, *, title: str, description: str, h1: List[str], headings: List[str],
                  url: str, body_text: str, alts: List[str]) -> Dict:
    words = word_list(body_text)
    occurrences = count_phrase(body_text, keyword)
    kw_len = max(1, len(word_list(keyword)))
    first_100 = " ".join(words[:100])
    slug = re.sub(r"[^a-z0-9]+", " ", url.lower().split("?")[0])
    return {
        "keyword": keyword,
        "in_title": contains_phrase(title, keyword),
        "title_starts_with_keyword": word_list(title)[:kw_len] == word_list(keyword),
        "in_meta_description": contains_phrase(description, keyword),
        "in_h1": any(contains_phrase(h, keyword) for h in h1),
        "in_subheadings": sum(1 for h in headings if contains_phrase(h, keyword) or partial_match(h, keyword) >= 0.75),
        "in_url": contains_phrase(slug, keyword) or partial_match(slug, keyword) >= 0.75,
        "is_homepage": re.sub(r"^https?://[^/]+", "", url.split("?")[0]).strip("/") == "",
        "in_first_100_words": contains_phrase(first_100, keyword),
        "in_image_alt": sum(1 for a in alts if contains_phrase(a, keyword)),
        "exact_occurrences": occurrences,
        "density_pct": round(100 * occurrences * kw_len / len(words), 2) if words else 0.0,
        "body_word_coverage": round(partial_match(body_text, keyword), 2),
    }


def keyword_issues(usage: Dict, add) -> None:
    kw = usage["keyword"]
    if not usage["in_title"]:
        add("keyword_not_in_title", "high", "content", f'Target keyword "{kw}" is not in the title',
            fix="Put the keyword (or a close variant) near the start of the <title>.")
    if not usage["in_h1"]:
        add("keyword_not_in_h1", "medium", "content", f'Target keyword "{kw}" is not in the H1',
            fix="Use the keyword naturally in the page's main heading.")
    if not usage["in_meta_description"]:
        add("keyword_not_in_description", "low", "content", f'Target keyword "{kw}" is not in the meta description',
            fix="Google bolds query words in snippets; include the keyword once in the description.")
    if not usage["in_first_100_words"]:
        add("keyword_not_in_intro", "low", "content", f'Target keyword "{kw}" is not in the first 100 words',
            fix="Mention the topic early so readers and search engines see what the page is about.")
    if not usage["in_url"] and not usage.get("is_homepage"):
        add("keyword_not_in_url", "low", "content", f'Target keyword "{kw}" is not in the URL',
            detail="Only change URLs of new pages, or of existing pages with a 301 redirect.")
    if usage["density_pct"] > 3.5:
        add("keyword_stuffing", "medium", "content", f'Keyword "{kw}" density is {usage["density_pct"]}%',
            fix="Reads as keyword stuffing. Use synonyms and related terms instead of repeating the exact phrase.")
    if usage["exact_occurrences"] == 0 and usage["body_word_coverage"] < 0.5:
        add("keyword_missing_from_body", "high", "content", f'Body text barely covers "{kw}"',
            fix="The page content does not discuss this topic; add a section that answers it.")


def score_keyword_relevance(usage: Optional[Dict]) -> Optional[int]:
    if not usage:
        return None
    pts = 0
    pts += 25 if usage["in_title"] else 0
    pts += 15 if usage["in_h1"] else 0
    pts += 10 if usage["in_meta_description"] else 0
    pts += 10 if usage["in_first_100_words"] else 0
    pts += 10 if usage["in_url"] else 0
    pts += 10 if usage["in_subheadings"] else 0
    pts += 5 if usage["in_image_alt"] else 0
    pts += 15 if 0.3 <= usage["density_pct"] <= 3.5 else (5 if usage["exact_occurrences"] else 0)
    return pts
