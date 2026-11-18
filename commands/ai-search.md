---
description: Check and improve visibility in AI search (ChatGPT, Claude, Perplexity, Gemini, Google AI Overviews)
argument-hint: <url>
---

AI search (GEO) readiness for: $ARGUMENTS

Follow the `ai-search-optimization` skill.

1. Call `ai_readiness` and `audit_page` for the URL in parallel, and `check_robots` with the URL.
2. Report:
   - **Can AI crawlers get in?** robots.txt rules per bot (search bots vs training bots), firewall/CDN blocks from the user-agent probes, JavaScript-only content.
   - **Can they understand it?** Structured data and entities, heading structure, direct answers, author/organization info, facts and figures.
   - **Will they cite it?** Original data, clear claims with sources, freshness (dates), brand mentions elsewhere.
3. Give a prioritized checklist. Keep llms.txt honest: it's optional and unconfirmed by the big AI search engines, so it's low priority.
4. Offer to: write robots.txt rules for AI bots (allow search bots, choose about training bots), generate `/llms.txt` (`/seodevil:llms-txt`), add schema, or rewrite key sections into answer-first form.
