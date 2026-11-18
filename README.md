# SEODevil for Claude Code

**The open-source SEO plugin for Claude Code.** It audits a page or crawls a whole site, finds technical, on-page, content, schema, speed and AI-search problems, explains them in plain language, and fixes them in your codebase.

- **18 SEO tools** in a bundled MCP server: audits, a site crawler, robots.txt, sitemaps, redirects, hreflang, structured data, Core Web Vitals, AI-crawler readiness, keyword ideas, competitor gaps
- **20 slash commands** such as `/seodevil:audit`, `/seodevil:fix`, `/seodevil:crawl` and `/seodevil:schema`
- **13 expert skills** covering technical SEO, schema, content, keywords, local, international, e-commerce, migrations, Core Web Vitals, AI search (GEO), link building, and SEO for every major framework
- **4 subagents**: SEO auditor, SEO fixer, content strategist, competitor analyst
- **Zero setup.** The server uses only the Python standard library, so there's no `pip install`, no API keys and no account. It needs `python3` 3.9+.

## Install

In Claude Code:

```
/plugin marketplace add sajidali12/seodevil-plugin
/plugin install seodevil@seodevil
```

Restart Claude Code, then run `/mcp` and you should see `seodevil` connected.

To try it from a local checkout:

```bash
git clone https://github.com/sajidali12/seodevil-plugin
claude --plugin-dir ./seodevil-plugin
```

Optional: set `PAGESPEED_API_KEY` (free, from the Google Cloud console with the PageSpeed Insights API enabled) for reliable Core Web Vitals data. Without it, Google rate-limits anonymous requests.

## Commands

| Command | What it does |
|---|---|
| `/seodevil:audit <url> [keyword]` | Full audit of a page: technical, on-page, content, schema, links, Core Web Vitals, AI search. Prioritized fixes. |
| `/seodevil:crawl <url> [pages]` | Crawls the site to find duplicate titles/content, broken links, redirect chains, orphan pages, a dirty sitemap, deep pages |
| `/seodevil:fix [url\|folder]` | Finds the issues and fixes them in your code, in the right place for your framework, then re-checks |
| `/seodevil:check-build [dir]` | Pre-deploy audit of your static build output (`dist/`, `out/`...) |
| `/seodevil:report <url>` | Client-ready `SEO-REPORT.md` with a 30/60/90-day plan |
| `/seodevil:meta <url\|file>` | Title and meta description options with pixel-width SERP previews |
| `/seodevil:schema <url\|type>` | Generates or fixes JSON-LD and validates it against rich-result rules |
| `/seodevil:keywords <seed>` | Keyword ideas grouped by intent, clustered into a content plan |
| `/seodevil:content-brief <keyword>` | A brief built to outrank the current results |
| `/seodevil:optimize <url> <keyword>` | Rewrites and content gaps for an existing page |
| `/seodevil:compare <yours> <competitors...>` | Side-by-side content, technical and schema gap analysis |
| `/seodevil:cwv <url>` | Core Web Vitals diagnosis (field + lab data) with code-level fixes |
| `/seodevil:ai-search <url>` | Visibility in ChatGPT, Claude, Perplexity, Gemini and AI Overviews |
| `/seodevil:llms-txt <url>` | Generates `/llms.txt` |
| `/seodevil:robots <url>` | Reviews or writes robots.txt, including rules for AI crawlers |
| `/seodevil:sitemap <url>` | Audits the sitemap or generates a clean one |
| `/seodevil:redirects <urls...>` | Traces chains and loops, checks http/https and www variants |
| `/seodevil:hreflang <url>` | Validates hreflang and return links on international sites |
| `/seodevil:local <url>` | Local SEO: Google Business Profile, NAP, LocalBusiness schema, location pages |
| `/seodevil:migrate <old> [new]` | Migration plan, redirect map and post-launch checks |

You don't have to use commands, though. Ask in plain English ("why isn't my blog post ranking?", "add product schema to this page", "is my site blocking ChatGPT?") and Claude picks the right tools and skills.

## MCP tools

| Tool | |
|---|---|
| `audit_page` | Audits one URL against 80+ checks and returns a 0-100 score, issues with fixes, and the extracted data |
| `audit_html` / `audit_directory` | Audits local HTML or a whole build folder (no network), including duplicate titles and broken internal links between files |
| `crawl_site` | Breadth-first crawler (up to 2,000 pages) with site-level analysis |
| `check_robots` | RFC 9309 parser; per-bot access for Googlebot, Bingbot and 16 AI crawlers |
| `check_sitemap` | Sitemap indexes and .gz files, lastmod quality, plus sample URLs checked for 200, indexability and self-canonical |
| `trace_redirects` | Every hop, including meta refresh, loops and host variants |
| `check_links` | Status of every link on a page |
| `check_hreflang` | Codes, self reference, x-default, and return links verified on every alternate |
| `validate_schema` | JSON-LD, microdata and RDFa checked against Google's required and recommended properties |
| `ai_readiness` | robots.txt per AI bot, firewall blocks probed with AI user agents, JavaScript dependence, llms.txt |
| `pagespeed` | CrUX field data (LCP, INP, CLS, FCP, TTFB), Lighthouse lab metrics, opportunities, the LCP element |
| `serp_preview` | Title and description pixel widths, plus the text Google would display |
| `analyze_content` | Outline, readability, top terms and phrases, keyword placement and density |
| `compare_pages` | You vs. up to 5 competitors, including terms they cover that you don't |
| `keyword_ideas` | Google/DuckDuckGo autocomplete expansion grouped by intent (no volumes, and it says so) |
| `generate_sitemap` | Crawls the site and writes a clean `sitemap.xml` |
| `fetch_page` | Raw response, headers and redirect hops, with any user agent |

## Use it in CI

The same engine runs as a CLI with no Claude involved:

```bash
python3 server/run.py dir ./dist --base-url https://example.com --min-score 85   # exits 1 below the threshold
python3 server/run.py audit https://example.com --check-links
python3 server/run.py crawl https://example.com --max-pages 200 --output crawl.json
```

## What it checks

<details>
<summary>Full list</summary>

- **Indexability**: HTTP status, noindex (meta and X-Robots-Tag), nofollow, nosnippet, canonical (missing, multiple, relative, cross-host, in body, http), robots.txt blocks, soft-404 robots.txt
- **Meta**: title (missing, multiple, length in pixels, placeholder, all caps), description (missing, length, duplicate of the title), lang, charset, doctype, favicon, meta keywords
- **Headings**: H1 missing, empty, multiple or too long; skipped levels; empty headings; long content without H2s
- **Images**: missing or meaningless alt text, missing width/height (CLS), no lazy loading below the fold, a lazy-loaded hero image, camera file names, legacy formats
- **Links**: broken, redirected, javascript:, empty anchors, generic anchors, nofollowed internal links, http internal links, too many links
- **Content**: thin content, placeholder text, readability, keyword placement and stuffing, text/HTML ratio
- **Social**: Open Graph completeness, absolute og:image, Twitter card
- **Mobile**: viewport missing or fixed, zoom blocked, plugins
- **Technical and performance**: HTTPS, mixed content, redirect chains and temporary redirects, response time, compression, HTML size, render-blocking scripts, stylesheet count, URL hygiene, meta refresh, deprecated tags, http/https and www variants
- **Security headers**: HSTS, CSP, X-Content-Type-Options, frame protection, Referrer-Policy, version disclosure
- **Structured data**: invalid JSON, required and recommended properties for 25+ types and every LocalBusiness subtype, nested Offers, ratings and reviews, date and URL formats, deprecated types
- **International**: hreflang code validity, self reference, x-default, duplicates, return links
- **Site-wide (crawl)**: duplicate titles, descriptions, H1s and content; broken internal links with their sources; internal redirects and chains; orphan pages; dirty sitemap entries; pages missing from the sitemap; click depth; weakly linked pages; slow pages; broken external links
- **AI search**: AI crawler access per bot, firewall/CDN blocks, JS-only content, llms.txt, structured data

</details>

## Privacy

Everything runs on your machine. The server only contacts the sites you ask it to check, plus Google PageSpeed Insights (`pagespeed`) and Google/DuckDuckGo autocomplete (`keyword_ideas`) when you use those tools. There's no telemetry and no account. Requests identify themselves as `SEODevil/1.0` (override with `SEODEVIL_USER_AGENT`).

## Hosted version

Want scheduled monitoring, Search Console data, fix tracking, WordPress auto-fixes and GitHub PRs? [seodevil.com](https://seodevil.com) is the hosted app this plugin grew out of.

## Contributing

PRs are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md). MIT licensed.
