---
name: core-web-vitals
description: Diagnose and fix Core Web Vitals (LCP, INP, CLS) and page speed, using field vs lab data, the LCP element, render-blocking resources, images, fonts, JavaScript and third-party scripts. Use for page speed, PageSpeed Insights, Lighthouse performance, CWV failures or slow sites.
---

# Core Web Vitals

## Thresholds (75th percentile of real users, mobile and desktop separately)
| Metric | Good | Poor |
|---|---|---|
| LCP (loading) | ≤ 2.5 s | > 4 s |
| INP (responsiveness) | ≤ 200 ms | > 500 ms |
| CLS (visual stability) | ≤ 0.1 | > 0.25 |

**Field data (CrUX) is what Google uses**, a 28-day rolling window. Lab data (Lighthouse) is for debugging. Page experience is a light ranking factor: it decides between otherwise similar results; it won't rescue weak content. Fast pages do convert better.

## LCP
Break it into: TTFB → resource load delay → resource load time → render delay.
- **TTFB** > 800 ms: page caching, CDN, fewer redirects, slow backend/DB.
- **The LCP image**: don't lazy-load it; add `fetchpriority="high"`; preload if it's a CSS background; serve AVIF/WebP at the right size with `srcset`/`sizes`; same origin or `preconnect`.
- **Render-blocking CSS/JS**: inline critical CSS, `defer` scripts, remove unused CSS/JS.
- **Fonts**: `font-display: swap` or `optional`, preload the main font, self-host, subset.
- **Client-side rendering** delays LCP: SSR/SSG the above-the-fold content.

## INP
Long main-thread tasks block input: split long tasks (`scheduler.yield()` / `setTimeout`), reduce JavaScript and hydration cost (islands, partial hydration, React Server Components), debounce handlers, avoid layout thrashing, move work to web workers, audit third parties (chat widgets, tag managers, A/B testing, ads are common culprits).

## CLS
Give images/video/iframes `width`+`height` or `aspect-ratio`. Reserve space for ads, embeds, banners and cookie notices. Don't insert content above existing content after load. Fonts: `size-adjust`/metric overrides or `font-display: optional`. Animate with `transform`, not top/left.

## Framework tools
- Next.js: `next/image` with `priority` on the LCP image, `next/font`, `next/script` with `strategy="lazyOnload"`, RSC to cut client JS.
- Nuxt: `@nuxt/image`, `@nuxtjs/fontaine`, `useScript`. Astro: islands by default, `<Image />`.
- WordPress: page cache plugin + CDN, fewer plugins, a lighter theme, delay third-party JS, image optimization plugin, disable unused block CSS.
- Shopify: fewer apps (each injects JS), theme image sizes, lazy-load below the fold.

## Workflow
`pagespeed` mobile → read `field_data_url` (fall back to `field_data_origin`) → check `diagnostics` for the LCP element and layout shifts → `opportunities` by savings → fix in code → re-run (lab improves right away; field takes up to 28 days).
