---
description: Write optimized title tags and meta descriptions for a page or a list of pages
argument-hint: <url or file> [target keyword]
---

Write title tags and meta descriptions for: $ARGUMENTS

1. For a URL, call `analyze_content` with `include_text: true` (and `keyword`). For a local file, read it. For a whole site, use `crawl_site` and work through pages with missing, duplicate, too long or too short titles/descriptions.
2. For each page, write **3 title options** and **2 description options**:
   - Title: about 50-60 characters, main keyword near the start, a specific benefit or differentiator, brand at the end only if there's room (`Primary Keyword: Specific Benefit | Brand`).
   - Description: 120-155 characters, matching the search intent, with a concrete detail (number, feature, price, location) and an implicit call to action. No keyword stuffing, no quote marks (Google cuts them).
3. Run every option through `serp_preview` and show a table: option, chars, pixels, truncated?
4. Recommend one of each and explain why in one line.
5. If this is the site's codebase, offer to apply them where the metadata is defined.
