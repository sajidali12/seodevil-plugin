---
name: international-seo
description: International and multilingual SEO, covering hreflang, URL structures (ccTLD, subdirectory, subdomain), language vs country targeting, x-default, translation quality and geo-redirects. Use for multilingual sites, hreflang errors, or expanding to new countries or languages.
---

# International SEO

## URL structure
- **Subdirectories** (`example.com/de/`) are the usual best choice: they share the domain's authority and are simple to run.
- **ccTLDs** (`example.de`) give the strongest local signal, but each domain builds authority separately and costs more to run.
- **Subdomains** (`de.example.com`) work, and are mostly an infrastructure choice.
- Never rely on parameters (`?lang=de`) or cookies alone, and never on automatic IP redirects. Googlebot crawls mostly from the US and would only ever see one version. Show a dismissible language banner instead.

## hreflang rules
- Every version lists **all** versions **including itself**, and every listed page lists back (return tags). One missing return link invalidates the pair.
- Codes: ISO 639-1 language (`en`, `de`, `pt`) + optional ISO 3166-1 alpha-2 region (`en-GB`, `pt-BR`). `en-UK` is wrong (it's `en-GB`), `jp` is wrong (it's `ja`). A region alone is invalid.
- `x-default` for the fallback (language selector or global English).
- Targets: absolute, canonical, 200, indexable URLs. hreflang to a redirect or a noindex page is ignored.
- Canonical stays self-referencing per language. Never canonicalize all languages to one.
- Implement in `<head>`, in the XML sitemap (`xhtml:link`, better for large sites), or in HTTP headers (for PDFs). Pick one method.
- `check_hreflang` validates all of the above for a URL.

## Content
- Real translations (human or reviewed MT), with localized currency, units, examples, addresses and phone numbers. Same-language pages for different countries (en-US/en-GB) need real differences (pricing, spelling, shipping) or they compete as duplicates.
- Translate slugs, titles, descriptions, alt text and schema too.
- `<html lang>` should match the hreflang language.
- Do keyword research per market (`keyword_ideas` with `lang`/`country`); people search differently, not just in another language.

## Other signals
Local links and mentions, a local address/phone, and Search Console verification of each property. The international targeting report is gone; hreflang and content are the main signals.
