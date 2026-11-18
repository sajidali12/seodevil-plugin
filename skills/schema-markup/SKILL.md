---
name: schema-markup
description: Structured data (JSON-LD / schema.org) for Google rich results and AI search, with templates for Organization, WebSite, Article, Product, LocalBusiness, BreadcrumbList, FAQPage, Event, Recipe, JobPosting, SoftwareApplication, VideoObject, Person. Use when adding, fixing or reviewing schema markup or rich results.
---

# Structured data

## Rules
- JSON-LD in `<head>` or `<body>`, one `@graph` per page is cleanest.
- Mark up only what's **visible on the page**. Fake reviews/ratings, or marking up content users can't see, is a spam-policy violation and can cause a manual action.
- Use stable `@id`s to connect entities: `https://example.com/#organization`, `https://example.com/#website`, `<page-url>#article`.
- Absolute URLs, ISO 8601 dates (`2026-03-01` or `2026-03-01T09:00:00+00:00`), numeric prices without currency symbols.
- Use the most specific type (`Dentist` not `LocalBusiness`, `BlogPosting` or `NewsArticle` not `Article`).
- Validate every block you write with `validate_schema` (`json`), then tell the user to check Google's Rich Results Test after deploying.

## Current Google rich-result reality
- Supported and useful: Product (merchant listings, review snippets), Article, BreadcrumbList, LocalBusiness, Event, JobPosting, Recipe, VideoObject, Organization (logo, knowledge panel), SoftwareApplication, Course, Dataset, DiscussionForumPosting, ProfilePage, Review snippets.
- FAQPage rich results: only for well-known government/health sites since 2023. Still fine to add for other engines and AI.
- HowTo rich results: removed in 2023. Sitelinks search box: retired in 2024. Don't sell these as rich-result wins.
- Structured data never guarantees a rich result, and it isn't a direct ranking factor. It helps eligibility and entity understanding (incl. AI answers).

## Templates
Homepage (Organization + WebSite):
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {"@type": "Organization", "@id": "https://example.com/#organization", "name": "Example Co",
     "url": "https://example.com/", "logo": "https://example.com/logo.png",
     "sameAs": ["https://www.linkedin.com/company/example", "https://x.com/example"]},
    {"@type": "WebSite", "@id": "https://example.com/#website", "url": "https://example.com/", "name": "Example Co",
     "publisher": {"@id": "https://example.com/#organization"}}
  ]
}
```
Article:
```json
{"@context": "https://schema.org", "@type": "BlogPosting", "@id": "https://example.com/blog/post#article",
 "headline": "…", "description": "…", "image": ["https://example.com/img/post-1200x675.jpg"],
 "datePublished": "2026-01-10T08:00:00+00:00", "dateModified": "2026-02-01T08:00:00+00:00",
 "author": {"@type": "Person", "name": "Jane Doe", "url": "https://example.com/authors/jane"},
 "publisher": {"@id": "https://example.com/#organization"}, "mainEntityOfPage": "https://example.com/blog/post"}
```
Product:
```json
{"@context": "https://schema.org", "@type": "Product", "name": "…", "image": ["https://…"], "description": "…",
 "sku": "…", "brand": {"@type": "Brand", "name": "…"},
 "offers": {"@type": "Offer", "url": "https://…", "price": 49.99, "priceCurrency": "USD",
            "availability": "https://schema.org/InStock", "itemCondition": "https://schema.org/NewCondition",
            "shippingDetails": {"@type": "OfferShippingDetails", "…": "…"},
            "hasMerchantReturnPolicy": {"@type": "MerchantReturnPolicy", "…": "…"}},
 "aggregateRating": {"@type": "AggregateRating", "ratingValue": 4.6, "reviewCount": 132}}
```
(aggregateRating only if real reviews are shown on the page.)

LocalBusiness:
```json
{"@context": "https://schema.org", "@type": "Plumber", "@id": "https://example.com/#business", "name": "…",
 "url": "https://example.com/", "telephone": "+1-555-000-0000", "image": "https://…",
 "address": {"@type": "PostalAddress", "streetAddress": "…", "addressLocality": "…", "addressRegion": "…", "postalCode": "…", "addressCountry": "US"},
 "geo": {"@type": "GeoCoordinates", "latitude": 0.0, "longitude": 0.0},
 "openingHoursSpecification": [{"@type": "OpeningHoursSpecification", "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"], "opens": "08:00", "closes": "18:00"}],
 "areaServed": "…", "priceRange": "$$", "sameAs": ["https://maps.google.com/?cid=…"]}
```
BreadcrumbList:
```json
{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
  {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://example.com/"},
  {"@type": "ListItem", "position": 2, "name": "Blog", "item": "https://example.com/blog/"},
  {"@type": "ListItem", "position": 3, "name": "Post title"}]}
```
FAQPage: `{"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": "…?", "acceptedAnswer": {"@type": "Answer", "text": "…"}}]}`. The questions and answers must be visible on the page.

## In code
Generate from the page's data (CMS fields, product objects), not hardcoded strings. Framework placement is in the `framework-seo` skill. Escape `</script>` inside JSON (`JSON.stringify(data).replace(/</g, '\\u003c')`).
