---
description: Keyword research from a seed topic, with intent grouping, clusters and a content plan
argument-hint: <seed keyword> [country code] [language code]
---

Keyword research for: $ARGUMENTS

Follow the `keyword-research` skill.

1. Call `keyword_ideas` with the seed (`depth: "deep"`), plus country/lang if given (default us/en). Then run 2-4 more seeds for the strongest sub-topics you discover.
2. Cluster the ideas by topic and **search intent** (informational, commercial, transactional, navigational, local). One cluster = one page; don't plan separate pages for close variants.
3. For each cluster give: primary keyword, secondary keywords, intent, recommended page type (guide, comparison, category, product, tool, landing page, FAQ) and a working title.
4. If the user has a site, run `crawl_site` (or check the URLs they give) to map clusters to existing pages: **update** vs **new page** vs **cannibalization** (two pages for one cluster).
5. To gauge difficulty, ask the user for the top-ranking URLs of 1-2 priority clusters (or have them paste the SERP) and run `compare_pages` on them. Never present guessed search volumes as data. Autocomplete shows that people search a term, not how often.

Output a prioritized content plan table: cluster, primary keyword, intent, page type, new/update, priority (with a one-line reason).
