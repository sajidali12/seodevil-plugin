---
name: seo-audit
description: How to run, prioritize and report an SEO audit of a page or website with the SEODevil tools. Use whenever the user asks for an SEO audit, SEO check, site review, "why am I not ranking", SEO score, or a list of SEO issues to fix.
---

# SEO audit method

## Pick the right tools
| Question | Tool |
|---|---|
| One page, live | `audit_page` (add `check_links: true` for broken links, `keyword` for on-page targeting) |
| Whole site | `crawl_site` (pass `output_path` above ~150 pages) |
| Local files / build output | `audit_html`, `audit_directory` |
| Speed / Core Web Vitals | `pagespeed` |
| AI search visibility | `ai_readiness` |
| Crawl control | `check_robots`, `check_sitemap`, `trace_redirects`, `check_hreflang` |

Run independent tools in parallel.

## Triage order (what actually moves rankings)
1. **Can it be indexed?** HTTP errors, noindex, robots.txt blocks, canonical pointing elsewhere, JS-only content, redirect loops. One of these makes everything else irrelevant.
2. **Is it the right page for the query?** Title, H1 and content match search intent. Thin, duplicate or cannibalizing pages.
3. **Can Google understand and trust it?** Internal links, structured data, E-E-A-T signals, freshness.
4. **Is it a good experience?** Core Web Vitals, mobile, HTTPS, intrusive interstitials.
5. **Polish**: alt text, description length, OG tags, security headers.

The tool's severities follow this order, but use judgment. A `noindex` on `/cart` is correct. A missing meta description on a login page doesn't matter. "Thin content" on a contact page is fine.

## Interpreting the score
Score = 100 minus points per issue (critical 15, high 8, medium 4, low 1). It measures **technical hygiene**, not ranking ability. A 95 can rank nowhere if the content doesn't satisfy intent, and a 70 can rank first. Say this when the user fixates on the number.

## Reporting rules
- Evidence for every issue: the actual tag/value/URL from tool output (`affected`, `data`).
- Each issue gets **why it matters** in one sentence and the **exact fix** (code when relevant).
- Group repeated issues by cause: "38 pages lack descriptions → the blog post template has no description field".
- Separate "fix now" from "nice to have". Don't bury a noindex under 30 low-severity items.
- List what's good, briefly.
- Never invent traffic, rankings or search volumes. Search Console is the source for those; ask for an export if they're needed.

## Common false positives to sanity-check
- `links_no_internal` on a one-page site, `thin_content` on utility pages, `canonicalized` on paginated/filter URLs (often intended).
- Security headers are not a ranking factor. Keep them low priority.
- Broken external links that return 403/999 (LinkedIn, Amazon, Cloudflare) are usually bot protection.
- `h1_multiple` is fine in HTML5 if the structure is clear.
- Lighthouse's own "SEO" category is superficial and not used here. Don't quote it.
