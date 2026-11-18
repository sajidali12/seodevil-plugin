---
description: Trace redirects and chains for one or more URLs, or build a redirect map for a migration
argument-hint: <url> [more urls...]
---

Redirect check: $ARGUMENTS

1. Call `trace_redirects` for each URL (in parallel, `check_variants: true` for the first one).
2. Show each chain hop by hop (status → location), flag chains (>1 hop), temporary redirects used for permanent moves, meta refresh, loops, http hops and dead ends.
3. Confirm that http/https × www/non-www all 301 to a single canonical origin in one hop.
4. Give the fix in the right syntax for the user's stack (Apache `.htaccess`, Nginx, Cloudflare rules, Vercel/Netlify config, Next.js `redirects()`, WordPress plugin), and update internal links that point at redirecting URLs.

For a migration redirect map, use the `site-migration` skill.
