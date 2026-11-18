---
description: Local SEO audit and plan for a business (Google Business Profile, NAP, LocalBusiness schema, local pages)
argument-hint: <url> [business name] [city]
---

Local SEO for: $ARGUMENTS

Follow the `local-seo` skill.

1. Run `audit_page` on the homepage and the contact/location page(s), and `validate_schema` on them.
2. Run `keyword_ideas` for "<main service> <city>" and "<main service> near me" with the right country code.
3. Check and report:
   - NAP (name, address, phone) visible as text on the site, consistent across pages, matching the Google Business Profile
   - LocalBusiness schema (the most specific subtype) with address, geo, phone, openingHoursSpecification, areaServed, sameAs (GBP, social profiles)
   - One location page per real location (no doorway pages for cities you don't serve), with a map embed, directions, local photos and reviews
   - Service pages targeting "service + city" intent; title tags with the city
   - Google Business Profile checklist: primary category, services, photos, posts, Q&A, review strategy (asking, replying)
   - Citations: the main directories for the country, consistent NAP
4. Generate the LocalBusiness JSON-LD from real data (ask for anything missing) and validate it.
