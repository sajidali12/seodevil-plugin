---
description: Produce a client-ready SEO report (Markdown file) for a website
argument-hint: <url> [max pages] [output file]
---

Create a full SEO report for: $ARGUMENTS

1. Run in parallel: `crawl_site` (max pages from the arguments, default 100, `output_path: ./seodevil-crawl.json`), `audit_page` on the homepage with `check_links: true`, `pagespeed` mobile + desktop for the homepage, `ai_readiness`, `check_robots`, `check_sitemap`.
2. Write `SEO-REPORT.md` (or the given file name) with:
   1. Executive summary: site score, 3 biggest problems, 3 biggest opportunities, in plain language for a non-technical owner
   2. Scorecard table: technical, on-page, content, structured data, performance, AI search (good / needs work / poor, with evidence)
   3. Critical and high issues: what, where (URLs), why it matters, how to fix, effort (S/M/L)
   4. Technical SEO: indexability, crawlability, redirects, sitemap, robots, HTTPS, duplicates
   5. On-page and content: titles/descriptions, headings, thin/duplicate content, internal linking
   6. Core Web Vitals: field + lab data and fixes
   7. Structured data and AI search readiness
   8. 30/60/90-day action plan
   9. Appendix: page-by-page table (URL, score, issues)
3. Every claim must come from tool output. Don't pad the report, and don't invent traffic or ranking numbers.
