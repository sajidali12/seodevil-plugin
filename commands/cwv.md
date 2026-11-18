---
description: Diagnose Core Web Vitals (LCP, INP, CLS) and fix them in the codebase
argument-hint: <url> [mobile|desktop]
---

Core Web Vitals analysis for: $ARGUMENTS

Follow the `core-web-vitals` skill.

1. Call `pagespeed` for the URL (default mobile). If the user mentioned both, run mobile and desktop in parallel.
2. Lead with **field data** (real users, 28-day CrUX, 75th percentile): it is what Google uses. Lab data explains causes. If there's no field data, say the page doesn't have enough traffic and use lab data.
3. For each failing metric: what the element/cause is (the LCP element, layout shifts, long tasks, render-blocking resources, unused JS), why, and the concrete fix.
4. If this is the site's codebase, find the responsible code (hero image, fonts, third-party scripts, hydration, ads/embeds without reserved space) and propose or apply the fix using framework-native tools (next/image priority, `fetchpriority="high"`, preload, `font-display`, width/height, code splitting, deferring third parties).
5. Remind the user that field data takes up to 28 days to reflect fixes; lab data shows improvement immediately.

If PageSpeed is rate-limited, explain how to set `PAGESPEED_API_KEY` (free key from the Google Cloud console, PageSpeed Insights API enabled).
