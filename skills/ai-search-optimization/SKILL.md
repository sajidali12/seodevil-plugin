---
name: ai-search-optimization
description: Generative engine optimization (GEO/AEO) for visibility and citations in ChatGPT search, Claude, Perplexity, Gemini, Copilot and Google AI Overviews / AI Mode. Covers AI crawlers, robots.txt for AI bots, llms.txt, answer-first content and entity optimization. Use for AI search, LLM visibility, AI Overviews, GEO, AEO or AI crawler questions.
---

# AI search optimization (GEO)

## How AI answers find you
- **Google AI Overviews / AI Mode** use Google's index and Googlebot. Normal SEO + snippet eligibility applies. `nosnippet`/`max-snippet` limit what can be quoted. `Google-Extended` controls Gemini training/grounding, **not** AI Overviews.
- **ChatGPT search** uses OAI-SearchBot (index) and ChatGPT-User (live fetches), plus Bing's index. GPTBot is for training only.
- **Claude** uses Claude-SearchBot (search), Claude-User (user-triggered fetches); ClaudeBot is training.
- **Perplexity** uses PerplexityBot (index) and Perplexity-User (live).
- **Copilot** uses Bing (Bingbot). Bing Webmaster Tools + IndexNow help here.

So: blocking training bots (GPTBot, ClaudeBot, Google-Extended, CCBot...) is a business choice that does **not** remove you from AI search answers. Blocking the search/user bots does.

## Technical requirements
1. **Access**: robots.txt allows the search bots (`check_robots`). The firewall/CDN doesn't block them (`ai_readiness` probes: Cloudflare's "Block AI bots" toggle catches search bots too).
2. **Server-rendered content**: most AI crawlers don't execute JavaScript. If `words_in_initial_html` is low, the page is invisible to them.
3. **Fast, clean HTML**: real headings, lists and tables. Avoid content hidden in tabs that load via JS.
4. **Structured data**: Organization, Person (authors), Product, Article give the entities and facts LLMs use.
5. **Bing indexing** matters for ChatGPT and Copilot. Verify in Bing Webmaster Tools and submit the sitemap.

## Content that gets cited
- **Answer first**: a question heading followed by a direct 1-3 sentence answer, then the detail.
- **Specific, checkable facts**: numbers, dates, prices, specs, definitions, with sources. LLMs prefer quotable statements.
- **Original information**: your own data, tests, surveys and expert quotes are what an AI can't get elsewhere.
- **Comparison and "best X for Y" pages** with clear criteria and honest pros/cons.
- **Freshness**: visible "updated" dates and current facts.
- **Entity clarity**: consistent brand name and description everywhere; an About page; `sameAs` links; listings on Wikipedia/Wikidata where notable, plus industry directories.
- **Off-site mentions**: AI answers lean on third-party sources (reviews, Reddit, forums, comparison articles, news). Digital PR and being on "best of" lists matter as much as on-site work.

## llms.txt
A proposed Markdown index of key pages (llmstxt.org). No major AI search engine has confirmed using it. It's cheap and harmless, so add it if the user wants, but never present it as a ranking factor. `/seodevil:llms-txt` generates one.

## Measuring
Ask the actual assistants your customers' questions regularly and record whether you're mentioned or cited. Check referral traffic from chatgpt.com, perplexity.ai, claude.ai, gemini.google.com and copilot in analytics. Server logs show AI-bot crawling.
