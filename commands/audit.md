---
description: Full SEO audit of a URL with a prioritized fix list (technical, on-page, content, schema, AI search)
argument-hint: <url> [target keyword]
---

Run a complete SEO audit of: $ARGUMENTS

The first argument is the URL; anything after it is the target keyword (optional).

1. Call the SEODevil `audit_page` tool with `check_links: true` (and `keyword` if given).
2. In parallel, call `ai_readiness` and `pagespeed` (mobile) for the same URL. If PageSpeed fails because of rate limits, say so and carry on.
3. If the page has hreflang tags, also call `check_hreflang`.

Then write the report using the `seo-audit` skill's format:

- **Score and verdict**: score/grade plus one sentence on the biggest problem.
- **Fix first**: the critical and high issues, each with the evidence (the actual tag, value or URL) and the exact fix.
- **Quick wins**: medium/low issues that take minutes.
- **Core Web Vitals**: field data first (that's what Google ranks on), lab data second, top 3 opportunities.
- **AI search**: crawler access, JS dependence, structured data.
- **What's already good**: a short list, so nobody "fixes" things that work.

If the current directory is the site's codebase, end by offering to apply the fixes (`/seodevil:fix`). Don't edit files during an audit.
