---
description: Compare your page against competitors and find content, technical and schema gaps
argument-hint: <your url> <competitor url> [more competitor urls...] [--keyword "kw"]
---

Competitor gap analysis: $ARGUMENTS

1. Call `compare_pages` with the user's URL first, then competitors (max 6 total), and the keyword if given.
2. Call `pagespeed` (mobile) for the user's URL and the strongest competitor in parallel.
3. Report as a side-by-side table: title, H1, words, H2 count, schema types, readability, response time, keyword placement, CWV.
4. Then: **content gaps** (terms/topics competitors cover that the user doesn't, grouped into sections to add), **structural gaps** (FAQ, tables, comparison, tools, media), **technical gaps** (speed, schema), and **what the user does better**.
5. End with a prioritized action list.
