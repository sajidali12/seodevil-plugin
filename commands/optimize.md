---
description: Optimize an existing page's content for a target keyword (rewrite suggestions, gaps, on-page fixes)
argument-hint: <url or file> <target keyword> [competitor URLs...]
---

Optimize this page's content: $ARGUMENTS

1. Run `audit_page` with the `keyword` (or `audit_html` for a file) and `analyze_content` with `include_text: true`.
2. If competitor URLs are given, run `compare_pages` with the user's page first to get the content gap.
3. Deliver:
   - Keyword placement scorecard (title, H1, description, URL, intro, subheadings, density) from the `keyword` data
   - Rewritten title, meta description and H1 (checked with `serp_preview`)
   - A rewritten intro that answers the query in the first two sentences
   - Missing sections/subtopics to add (from competitor gaps and questions), each with a short outline
   - Paragraphs to tighten (from the readability data), internal links to add, and image/alt improvements
   - Structured data to add
4. Never stuff keywords; the density should stay natural. Keep the author's voice.
5. If it's in this codebase/CMS content, offer to apply the edits.
