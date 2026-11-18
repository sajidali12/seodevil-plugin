---
description: Generate an llms.txt (and optionally llms-full.txt) for a website
argument-hint: <url> [output path]
---

Generate `/llms.txt` for: $ARGUMENTS

1. Call `crawl_site` (max 100 pages) to discover the important pages, and `analyze_content` on the homepage.
2. Write the file following the llmstxt.org format:
   ```
   # Site or Company Name

   > One or two sentences: what this is, who it's for.

   Optional short paragraph with key facts (what you offer, where, pricing model, important constraints).

   ## Docs / Products / Services (pick sections that fit)
   - [Page title](https://full-url): one-line description of what's on the page

   ## Optional
   - [Less important page](https://url): description
   ```
   Use only indexable 200 pages, absolute URLs and factual descriptions. No marketing fluff, and skip legal/login/cart pages.
3. Save it to the output path (default: the static/public folder of this project if there is one, else `./llms.txt`) and tell the user to serve it at `https://domain/llms.txt` as text/plain or text/markdown.
4. Be honest about its value: it's a proposal, and the major AI search engines haven't confirmed using it. It is cheap to add and harmless.
