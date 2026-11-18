---
name: keyword-research
description: Keyword research and topic clustering without paid tools, using autocomplete data, search intent, SERP analysis and Search Console. Use when the user wants keywords, topic ideas, content plans, clustering, search intent analysis or keyword mapping to pages.
---

# Keyword research

## Data honesty
`keyword_ideas` returns **real autocomplete queries without volumes**. `seen` (how many expansions surfaced a query) and `best_position` are rough popularity hints only. Never fabricate monthly volumes or difficulty scores. For numbers, point to Google Search Console (queries already earning impressions, the best data there is), Google Keyword Planner (ranges, free with an Ads account), Bing Webmaster Tools keyword research, or a paid tool the user has.

## Process
1. **Seeds**: products/services, problems the customer has, audience language (not internal jargon), competitor names.
2. **Expand**: `keyword_ideas` with `depth: "deep"` on 2-5 seeds. Use the right `country`/`lang`.
3. **Classify intent**:
   - Informational ("how to…", "what is…") → guide, tutorial, glossary
   - Commercial ("best…", "…vs…", "…review", "…alternatives") → comparison, listicle, review
   - Transactional ("buy…", "…price", "…near me", "hire…") → product, category, service, landing page
   - Navigational (brand + login/app) → make sure the brand page ranks
   - Local ("…near me", "… in <city>") → location/service pages + Google Business Profile
   The SERP decides intent: if the top results are all listicles, a product page won't rank for that query.
4. **Cluster**: queries that the same page would satisfy (same intent, same answer) go together. Rule of thumb: if Google shows mostly the same URLs for two queries, they're one cluster.
5. **Map to pages**: one cluster → one URL. Check existing pages (`crawl_site`) to avoid cannibalization; prefer updating a page that already has some authority.
6. **Prioritize** by business value × realistic ranking chance × effort. Realistic chance: run `compare_pages` on the current top results. Thin, outdated, or forum results mean an opening. Big brands with deep content mean you'd need a differentiated angle or a long-tail entry point.

## Long-tail and question mining
Questions (who/what/why/how/can/is) become H2s and FAQ entries. They're also the queries AI answers handle, so answer them directly in 40-60 words under a question heading.

## Output
Table: cluster · primary keyword · secondary keywords · intent · page type · existing URL or "new" · priority + reason.
