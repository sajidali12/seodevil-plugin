---
description: Review or write robots.txt (search engines, AI crawlers, crawl budget)
argument-hint: <url> [goal, e.g. "block AI training but allow AI search"]
---

robots.txt task: $ARGUMENTS

1. Call `check_robots` with the URL, testing important paths (home, a category, a product/article, `/wp-admin/`, search and filter URLs if relevant).
2. Explain what's currently blocked/allowed for Googlebot, Bingbot and every AI crawler, and any syntax problems.
3. If asked (or if there are problems), write an improved robots.txt:
   - Never block CSS/JS or pages you want indexed. robots.txt doesn't remove pages from Google; noindex does.
   - Block infinite spaces (internal search, faceted filters, cart/checkout, session parameters) only when they're crawl-budget problems.
   - AI bots: separate **search/user-triggered** bots (OAI-SearchBot, ChatGPT-User, Claude-SearchBot, Claude-User, PerplexityBot, Perplexity-User) from **training** bots (GPTBot, ClaudeBot, Google-Extended, Applebot-Extended, CCBot, meta-externalagent, Bytespider). Blocking training does not remove the site from AI search answers.
   - Include `Sitemap:` lines.
4. Test the new rules mentally against the same paths and show a before/after table. If this is the codebase, write the file in the right place (e.g. `public/robots.txt`, Next.js `app/robots.ts`, WordPress filters).
