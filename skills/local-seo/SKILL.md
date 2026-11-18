---
name: local-seo
description: Local SEO for businesses serving a geographic area, covering Google Business Profile, NAP consistency, LocalBusiness schema, location and service-area pages, reviews, citations and "near me" queries. Use for local businesses, multi-location brands, map pack rankings or local search.
---

# Local SEO

## Ranking factors (Google's own words): relevance, distance, prominence
- **Google Business Profile** is the biggest lever for the map pack: the correct primary category (most important), secondary categories, services/products, hours (including holiday hours), photos, description, posts, Q&A, attributes.
- **Reviews**: quantity, recency, rating, keywords in reviews, owner replies. Ask every happy customer with a direct review link. Never buy or gate reviews (illegal in some countries, and against Google policy).
- **NAP consistency**: exact same name, address, phone on the site (as crawlable text, not only an image), GBP, and major citations.
- **Website**: location pages, LocalBusiness schema, city in titles/H1 where natural, embedded map, local content (projects, case studies, staff, photos from the area).

## Location pages
One page per real location with unique content: address, hours, phone, map, directions/parking, area photos, staff, local reviews, services offered there. City-swap pages with identical text are doorway pages and get ignored or penalized. Service-area businesses without a storefront: hide the address on GBP and build pages for the main areas you really serve, each with real local proof (jobs done there).

## Schema
The most specific LocalBusiness subtype, with `@id`, name, address, geo, telephone, openingHoursSpecification, url, image, priceRange, areaServed, sameAs (GBP/Maps URL, social). Multi-location brands: one LocalBusiness per location page, all linked to the parent Organization via `parentOrganization`. Template in the `schema-markup` skill.

## Citations
The country's main directories (e.g. US: Apple Business Connect, Bing Places, Yelp, BBB, Facebook, industry directories; UK: Yell, Thomson Local; plus chamber of commerce and niche directories). Consistency beats volume.

## Keywords
"service + city", "service near me", "best service in city", plus neighbourhood names. Check with `keyword_ideas` using the right country code.

## Tracking
GBP Insights (calls, directions, website clicks), Search Console with UTM-tagged GBP website link (`?utm_source=google&utm_medium=organic&utm_campaign=gbp`), and rank checks from the target location (the map pack depends on the searcher's location).
