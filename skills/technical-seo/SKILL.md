---
name: technical-seo
description: Technical SEO knowledge: crawling, indexing, canonicals, redirects, robots.txt, sitemaps, status codes, JavaScript rendering, pagination, faceted navigation, crawl budget, HTTPS and duplicate URLs. Use when fixing or explaining indexation, crawl or duplicate-content problems.
---

# Technical SEO reference

## Indexing controls (they do different things)
| Want | Use | Not |
|---|---|---|
| Keep a page out of Google | `<meta name="robots" content="noindex">` or `X-Robots-Tag: noindex` | robots.txt Disallow (Google can't see the noindex and may still index the URL) |
| Stop crawling (crawl budget) | robots.txt `Disallow` | noindex |
| Consolidate duplicates | `rel=canonical` to the main URL (a hint) or a 301 (a directive) | noindex on duplicates |
| Remove urgently | Search Console Removals (temporary) + noindex/404 | |

Never combine robots.txt Disallow with noindex on the same URL. Remove the Disallow until the noindex has been seen.

## Canonicals
- Every indexable page: absolute self-referencing canonical, in `<head>`, exactly one.
- The canonical target must return 200, be indexable, and not redirect.
- Parameters (utm, sort, session): canonical to the clean URL.
- Pagination: each page canonicals to itself (not page 1). `rel=next/prev` is not used by Google.
- Cross-domain canonical is fine for syndication.

## Redirects
- Permanent: 301/308. Temporary: 302/307. All pass signals, but 301 states your intent.
- One hop, from every variant (http/https, www/non-www, trailing slash, uppercase) to the canonical URL.
- Update internal links to final URLs. Don't rely on redirects internally.
- Use server-side redirects, not meta refresh or JS redirects.

## Status codes
200 OK · 301/308 moved · 404/410 gone (410 drops a little faster) · 5xx and 429 slow Googlebot down · **soft 404** = a 200 "not found" page (fix: return a real 404). An SPA's catch-all route returning 200 for everything is a common soft-404 source.

## JavaScript sites
- Google renders JS in a second wave (usually minutes to days). Bing does less, and most AI crawlers and social scrapers run no JS at all.
- `ai_readiness`/`audit_page` report `words_in_initial_html`; if it's tiny, the content is client-rendered. Fix with SSR/SSG/prerendering.
- Links must be `<a href>`: `onClick` navigation isn't crawled. Metadata must be in the server HTML (use Next.js `metadata`, not client-side `document.title`).
- Don't block JS/CSS in robots.txt.

## Sitemaps
Only canonical, indexable, 200 URLs. Accurate `<lastmod>` (Google ignores lastmod it can't trust, and ignores priority/changefreq). Max 50,000 URLs / 50 MB per file; use an index for more. Reference it in robots.txt and submit it in Search Console + Bing Webmaster Tools.

## Faceted navigation and crawl budget
Crawl budget only matters for large sites (≈10k+ URLs) or ones with infinite URL spaces. For filters: decide which combinations deserve indexing (search demand exists), give those clean URLs; for the rest, use canonical to the parent and/or a robots.txt Disallow on the parameter patterns, and `nofollow` isn't a crawl control.

## Duplicate content
Causes: http/https/www variants, trailing slash, parameters, printer pages, staging sites indexed, near-identical location/product pages. `crawl_site` flags duplicate titles, descriptions and identical main content. Fix: consolidate (301), canonicalize, or make pages genuinely different.

## HTTPS
Whole site on HTTPS, HSTS once stable, no mixed content, certificate valid for every hostname variant.

## Verification
After fixing: re-run the tool, then URL Inspection → "Test live URL" in Search Console, and request indexing for key pages.
