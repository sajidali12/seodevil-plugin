---
description: Create an SEO content brief that can outrank the current top results
argument-hint: <target keyword> [competitor URLs...]
---

Create a content brief for: $ARGUMENTS

Follow the `content-seo` skill.

1. Run `keyword_ideas` on the keyword (`depth: "standard"`) to collect sub-topics and the questions people ask.
2. If competitor URLs are given, run `compare_pages` (put the user's page first if they have one), then `analyze_content` with `include_text: true` on the best 1-2 to study their structure. Without URLs, ask the user for the top 3-5 ranking URLs, or build the brief from the autocomplete data and say that you did.
3. The brief:
   - Search intent and the reader's real job-to-be-done
   - Title (checked with `serp_preview`), meta description, URL slug, H1
   - Full H2/H3 outline that covers everything competitors cover, plus a clear **information gain** section: something they lack (data, examples, a tool, an opinion from experience)
   - Questions to answer, with a direct 40-60 word answer under each question heading (good for featured snippets and AI answers)
   - Terms and entities to cover (from the `gaps` in compare_pages), target length range (from the competitor median, not a magic number)
   - E-E-A-T: whose first-hand experience to show, sources to cite, author bio
   - Internal links to and from existing pages, schema type, image/media ideas
4. Save it as `brief-<slug>.md` if the user wants a file.
