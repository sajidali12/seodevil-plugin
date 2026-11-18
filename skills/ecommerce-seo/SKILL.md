---
name: ecommerce-seo
description: E-commerce SEO for online stores (Shopify, WooCommerce, Magento, BigCommerce, custom), covering category and product pages, faceted navigation, Product and merchant listing schema, out-of-stock and discontinued products, pagination, duplicate product URLs and Google Merchant Center. Use for online shops, product or category page optimization.
---

# E-commerce SEO

## Category pages (usually the biggest traffic opportunity)
Target the head and commercial terms ("women's trail running shoes"). Unique H1/title, a short helpful intro above the products and buying-guide content/FAQs below, filters that don't create indexable duplicates, links to subcategories, and breadcrumbs (+ BreadcrumbList schema).

## Product pages
- Unique descriptions (not the manufacturer's copy used by every reseller), specs in a table, real photos with descriptive alt text, video, sizing/compatibility info, shipping and returns visible, reviews (UGC adds unique content).
- Title: `Brand Model – Key Attribute | Store`.
- Product schema with Offer (price, priceCurrency, availability, itemCondition), shipping and return policy (`shippingDetails`, `hasMerchantReturnPolicy`), GTIN/MPN/SKU, brand, real aggregateRating/reviews. This makes the page eligible for merchant listings and the Shopping tab. Also submit a Merchant Center feed (free listings).
- Variants: one canonical product URL, or separate URLs per variant when people search for them (colour/size), using `ProductGroup` + `hasVariant` schema.

## Duplicate URL traps
- The same product under several category paths (`/shoes/x`, `/sale/x`): use one canonical product URL and link to it everywhere. Shopify: link to `/products/handle`, not `/collections/c/products/handle`.
- Sort/filter/session parameters: canonical to the clean URL. Block crawl of infinite combinations. Make indexable landing pages only for filter combinations people search for ("red running shoes").
- Internal search result pages: noindex, and don't link them.

## Stock changes
- Temporarily out of stock: keep the page 200, `availability: OutOfStock`, show alternatives and a back-in-stock signup.
- Permanently discontinued: 301 to the replacement or closest category when there is a clear equivalent; otherwise keep the page with alternatives if it has links/traffic, or 410.
- Seasonal pages: keep one evergreen URL (`/black-friday`) and update it each year.

## Pagination
Each page gets a self-canonical, crawlable `<a href="?page=2">` links (not only infinite scroll or "load more" via JS), with unique titles optional. Don't noindex page 2+ if products are only reachable there.

## Platform notes
Shopify: duplicate collection-product paths, `/collections/all`, tag pages (`/collections/x/tag`) should be noindexed if thin, and apps add JS weight. WooCommerce: product-tag/attribute archives, `?add-to-cart=` URLs, cart/checkout noindex. Magento: layered navigation parameters, store-code URLs.

Audit with `crawl_site` (`include_query: true` shows parameter sprawl), `validate_schema` on product pages, and `pagespeed` on a category and a product template.
