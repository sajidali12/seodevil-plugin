---
name: framework-seo
description: Where and how to implement SEO (titles, meta descriptions, canonical, robots, Open Graph, JSON-LD, sitemap, robots.txt, redirects, hreflang) in specific frameworks and CMSs, including Next.js, Nuxt, Astro, SvelteKit, Remix, Gatsby, React SPA, Vue, Angular, Hugo, Jekyll, Eleventy, WordPress, Shopify, Django, Flask, Laravel, Rails and static HTML. Use when applying SEO fixes in a codebase.
---

# SEO by framework

First detect the stack (package.json deps, config files, folder layout). Fix the **shared layout/template or metadata helper**, then per-page data.

## Next.js (App Router)
- Metadata: `export const metadata` or `export async function generateMetadata({ params })` in `layout.tsx`/`page.tsx`; `metadataBase: new URL('https://example.com')` in the root layout so relative URLs resolve; `title: { template: '%s | Brand', default: 'Brand' }`; `alternates: { canonical: '/path', languages: { 'en-US': '/en-US' } }`; `robots: { index: false }`; `openGraph`, `twitter`.
- JSON-LD: `<script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, '\\u003c') }} />` in the page component.
- `app/sitemap.ts`, `app/robots.ts`, `app/manifest.ts`; redirects in `next.config.js` `redirects()` (permanent: true → 308) or middleware.
- Pages Router: `next/head`, `next-seo`, `getServerSideProps`/`getStaticProps` so meta is in the HTML.
- Images: `next/image` (`priority` on the LCP image, `alt` always).

## Nuxt 3
`useSeoMeta({ title, description, ogTitle, ogImage, twitterCard })`, `useHead({ link: [{ rel: 'canonical', href }], htmlAttrs: { lang } })`; `@nuxtjs/seo` (sitemap, robots, schema.org, OG images); `routeRules` for redirects; render mode SSR/SSG, not SPA.

## Astro
A `BaseHead.astro`/layout component with `<title>`, meta, canonical (`new URL(Astro.url.pathname, Astro.site)`); `site` in `astro.config.mjs`; `@astrojs/sitemap`; JSON-LD via `<script type="application/ld+json" set:html={JSON.stringify(data)} />`; `redirects` in config.

## SvelteKit
`<svelte:head>` in `+page.svelte`/`+layout.svelte` with data from `+page.ts` `load`; keep SSR on; `prerender = true` for static pages; sitemap/robots as `+server.ts` endpoints.

## Remix / React Router v7
`export const meta: MetaFunction` per route (includes `{ tagName: 'link', rel: 'canonical', href }`); `links` export; sitemap as a resource route.

## Gatsby
`export const Head = () => <SEO … />` (Gatsby 4.19+); `gatsby-plugin-sitemap`, `gatsby-plugin-robots-txt`.

## Plain React (Vite/CRA) / Vue / Angular SPAs
Client-side meta (`react-helmet-async`, `@unhead/vue`, Angular `Meta`/`Title`) only works for Google after rendering and fails for social/AI crawlers. Real fix: prerender (vite-plugin-ssr/Vike, `vite-react-ssg`, Angular SSR/prerender, react-snap) or move to an SSR framework. Make sure unknown routes return a 404 status, not a 200 SPA fallback.

## Static site generators
- Hugo: `layouts/partials/head.html` (or the theme's), `.Title`, `.Description`, `.Permalink`; built-in sitemap; `enableRobotsTXT = true`; `aliases` for redirects.
- Jekyll: `jekyll-seo-tag` (`{% seo %}`), `jekyll-sitemap`, `jekyll-redirect-from`.
- Eleventy: a base layout with front-matter data; sitemap via a template.

## WordPress
- An SEO plugin (Yoast, Rank Math, SEOPress, AIOSEO) owns titles, descriptions, canonical, schema and sitemaps. Change settings/templates there, and don't add a second plugin or duplicate tags in the theme.
- Theme: `add_theme_support('title-tag')`, no hardcoded `<title>`, `wp_head()` in header.php.
- Settings → Reading → "Discourage search engines" must be **off** in production.
- Redirects: the Redirection plugin or the SEO plugin's redirect manager; core sitemap at `/wp-sitemap.xml`.
- Programmatic: `wp_get_document_title` filter, `wpseo_title`/`wpseo_metadesc` (Yoast), `rank_math/frontend/title` (Rank Math).

## Shopify
Theme `layout/theme.liquid` head: `{{ page_title }}`, `{{ page_description }}`, `{{ canonical_url }}`; per-product/collection SEO fields in admin; JSON-LD in `sections/main-product.liquid` (check the theme doesn't already output Product schema, to avoid duplicates); robots via `templates/robots.txt.liquid`; URL redirects in admin. The sitemap is automatic.

## Django / Flask / Laravel / Rails
Base template blocks: Django `{% block title %}`/`{% block meta_description %}` in `base.html` + `django.contrib.sitemaps`; Flask/Jinja `{% block head %}`; Laravel Blade `@section('title')`/`@stack('meta')`, `spatie/laravel-sitemap`, `artesaos/seotools`; Rails `content_for :title`, `meta-tags` gem, `sitemap_generator`. Redirects in routes (`redirect()` / `RedirectView` / `Route::permanentRedirect`).

## Static HTML
Edit each file's `<head>`; for many files, script it, and then verify with `audit_directory`.

## Server config
Apache `.htaccess` (`Redirect 301`, `RewriteRule … [R=301,L]`), Nginx (`return 301 https://example.com$request_uri;`), Netlify `_redirects`, Vercel `vercel.json` `redirects`, Cloudflare Redirect Rules / Bulk Redirects. Headers like `X-Robots-Tag` and HSTS go in the same places.
