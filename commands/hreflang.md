---
description: Validate hreflang / international SEO setup for a multilingual or multi-region site
argument-hint: <url>
---

International SEO check for: $ARGUMENTS

Follow the `international-seo` skill.

1. Call `check_hreflang` for the URL, and `check_sitemap` in case hreflang lives in the sitemap.
2. Report: codes valid? self-reference? x-default? Does every alternate return 200, link back, and canonicalize to itself? Does `html lang` match the hreflang?
3. Explain each error in plain words and give corrected tags. If this is a codebase, fix the generator (i18n routing config, layout `<head>`, sitemap alternates).
