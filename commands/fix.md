---
description: Find and fix SEO issues directly in this codebase (meta tags, canonical, schema, sitemap, robots, images, links)
argument-hint: [live url or build folder] [issue to focus on]
---

Fix SEO issues in the current project. Arguments: $ARGUMENTS

1. **Find the issues.**
   - If a URL is given, run `audit_page` on it (`check_links: true`). For a whole site, use `crawl_site` with up to 50 pages.
   - If a folder is given, or the project has a static build (`dist/`, `out/`, `build/`, `_site/`, `public/`), run `audit_directory` on it.
   - With nothing given, detect the framework and build or inspect what you can. Ask for the production URL if you need it.
2. **Find where each tag is generated.** Use the `framework-seo` skill: for example Next.js `metadata`/`generateMetadata`, Nuxt `useSeoMeta`, Astro layouts, SvelteKit `<svelte:head>`, React Helmet, Django/Jinja/Blade/ERB templates, WordPress theme/Yoast/Rank Math, Shopify Liquid. Fix the template or shared layout, not every page by hand.
3. **Fix**, in this order: indexability blockers (noindex, robots, canonical) → titles/descriptions/H1 → structured data → images (alt, width/height, lazy) → links → sitemap/robots.txt → performance hints.
   - Write titles and descriptions for real: check every candidate with `serp_preview` before writing it.
   - Validate every JSON-LD block you write with `validate_schema` (`json` argument).
   - Never invent facts (prices, ratings, addresses, reviews) for schema or copy. Use what's in the code or content, or leave a clearly marked TODO.
   - Don't change live URLs without adding a 301 redirect.
4. **Verify**: re-run `audit_html`/`audit_directory` on the changed output (or tell the user what to re-run after deploying) and show the before → after score.

Finish with a short changelog: file, what changed, which issue it fixes.
