---
description: Plan and verify a site migration (domain change, redesign, URL restructure, platform change) without losing rankings
argument-hint: <old site url> [new site url or staging url]
---

Site migration task: $ARGUMENTS

Follow the `site-migration` skill.

1. **Before**: `crawl_site` the old site with `output_path: ./migration-old.json` (as many pages as practical) and `check_sitemap` to get every URL that matters. Ask for the Search Console top-pages export if available.
2. **Map**: if a new/staging URL is given, crawl it too (`./migration-new.json`), then build `redirect-map.csv` (old URL, new URL, match method: exact path, slug, title, or manual). Flag old URLs without a match.
3. **Check the new site**: titles, descriptions, canonicals, noindex left over from staging, robots.txt, hreflang, schema, internal links pointing at old URLs.
4. **Launch checklist**: 301s in one hop, sitemap of new URLs submitted, Search Console change-of-address (domain moves), keep the old domain and redirects for at least a year, monitor 404s.
5. **After**: when given the old URLs, run `trace_redirects` on a sample and confirm each one 301s to the mapped URL with a 200.
