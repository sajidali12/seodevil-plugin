---
description: Audit an XML sitemap or generate a clean one
argument-hint: <url> [generate] [output path]
---

Sitemap task: $ARGUMENTS

- **Audit** (default): call `check_sitemap` with `sample: 50`. Report files, URL count, lastmod quality, wrong host/scheme URLs, and sampled URLs that aren't clean (redirects, 4xx, noindex, canonicalized). Explain that a sitemap should only list canonical, indexable 200 URLs, and that Google ignores `priority`/`changefreq`.
- **Generate** (if the user says generate): call `generate_sitemap` with the output path (default `./sitemap.xml`, or the project's public/static folder) and a sensible `max_pages`.
- **In a codebase**: prefer generating it at build time with the framework's tool (Next.js `app/sitemap.ts`, `@astrojs/sitemap`, `nuxt-simple-sitemap`/`@nuxtjs/sitemap`, WordPress core `wp-sitemap.xml` or the SEO plugin, Django `django.contrib.sitemaps`, Laravel `spatie/laravel-sitemap`) so it stays current, and make sure robots.txt references it.

Finish with: submit it in Google Search Console and Bing Webmaster Tools.
