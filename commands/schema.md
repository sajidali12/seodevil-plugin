---
description: Generate, validate or fix JSON-LD structured data for rich results and AI search
argument-hint: <url | file | page type> [extra details]
---

Structured data task: $ARGUMENTS

Follow the `schema-markup` skill.

1. If given a URL or file, extract and validate the current markup with `validate_schema` and list errors and warnings.
2. Decide which types fit the page from its actual content: Organization + WebSite (home), Article/BlogPosting, Product + Offer, LocalBusiness subtype, BreadcrumbList, FAQPage, Event, Recipe, JobPosting, SoftwareApplication, VideoObject, Course, ProfilePage... Never mark up content that isn't visible on the page.
3. Write one JSON-LD `@graph` with stable `@id`s (e.g. `https://example.com/#organization`) that connect the entities (publisher → Organization, author → Person, breadcrumb → BreadcrumbList).
4. Validate your output with `validate_schema` (`json` argument) and iterate until there are no errors.
5. Use only real data. If something required is unknown (price, address, rating), ask or leave a `TODO` and say so. Fabricated ratings or reviews are a Google spam-policy violation.
6. In a codebase, put it where the framework renders `<head>` (see the `framework-seo` skill) and generate values from the page's data instead of hardcoding them.

Finally, tell the user to confirm with Google's Rich Results Test after deploying.
