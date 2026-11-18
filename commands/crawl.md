---
description: Crawl a whole website and find site-wide SEO problems (duplicates, broken links, orphans, redirects, thin pages)
argument-hint: <url> [max pages, default 100]
---

Crawl and audit the site: $ARGUMENTS

1. Call `crawl_site` with the URL, `max_pages` from the arguments (default 100) and `output_path` set to `./seodevil-crawl.json` so the full data is kept. For more than 300 pages, warn that it can take several minutes.
2. Also call `check_robots` and `check_sitemap` for the same site.

Report:
- Summary table: pages crawled, indexable pages, sitemap URLs, status codes, average page score, site score.
- **Site-wide issues** by severity. For each one: how many URLs, 3-5 examples, why it matters, how to fix it. Broken links must list the pages that link to them.
- **Most common page issues** (from `page_issues`) with page counts. Group the fix: when 40 pages miss a meta description, the fix is usually one template, not 40 edits.
- **Architecture**: depth distribution, orphan pages, weakly linked pages, and which sections deserve more internal links.
- **Next steps**: the 5 changes with the biggest impact, in order.

Mention that `stopped` in the summary means the crawl hit its limit, so the numbers cover only part of the site.
