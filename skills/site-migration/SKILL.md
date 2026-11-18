---
name: site-migration
description: Plan, execute and verify website migrations (domain change, HTTPS move, URL restructure, redesign, CMS or platform change, site merge) while protecting rankings, including redirect maps, pre-launch checks, launch day and post-launch monitoring. Use for any migration, relaunch, replatforming or large URL change.
---

# Site migration

Most traffic losses come from: missing redirects, redirect chains, noindex/robots blocks carried over from staging, lost content or internal links, and changed titles on the pages that rank.

## 1. Inventory (before anything changes)
- `crawl_site` the live site at full size with `output_path` (keep it as the baseline).
- `check_sitemap` for every listed URL.
- Ask for Search Console exports: top pages and queries (last 12-16 months), links report. Add analytics landing pages and URLs with backlinks; these are the URLs that must not 404.
- Record baselines: rankings for key queries, organic sessions per page, CWV.

## 2. Redirect map
- Every old URL that has traffic, links or is indexed → the **most relevant** new URL, 1:1. Redirecting everything to the homepage is treated as a soft 404.
- Match by exact path → slug → title/H1 → manual. Put it in a CSV: `old_url,new_url,status,method`.
- 301 in one hop. Fix legacy redirects so they point at the final URLs too (no chains).
- Pages with no equivalent and no value: 410/404 are fine.

## 3. Pre-launch checks on staging
Staging blocked by auth (not only robots.txt/noindex, which tends to get copied to production). Then check on staging: titles/descriptions/H1 carried over for top pages, canonicals pointing at the **new production** domain, hreflang, schema, internal links using new URLs (not redirects), the robots.txt and sitemap you'll ship, analytics/tag manager, CWV not worse. Use `audit_directory` or `crawl_site` on staging.

## 4. Launch day
Deploy the redirects together with the site. Remove staging noindex/auth from production. Submit the new sitemap. Domain move: Search Console Change of Address and keep both properties verified. Spot-check redirects with `trace_redirects` on a sample of the top 100 old URLs. Watch server logs for 404s/5xx.

## 5. After launch
- Daily for 2 weeks: 404s in logs and Search Console, indexing status of the new URLs, crawl stats.
- Keep the old sitemap available briefly so Google re-crawls the redirects. Keep redirects (and the old domain) for at least a year, ideally forever.
- Expect fluctuation for 2-8 weeks. A steady drop beyond that means something's wrong: compare per-page traffic against the baseline.
- Update external profiles, important backlinks you control, GBP, ad landing pages.
