---
description: Audit the static HTML output of this project's build before deploying (CI-style SEO check)
argument-hint: [build folder] [production base url]
---

Pre-deploy SEO check: $ARGUMENTS

1. Find the build folder: the argument, or detect it (`dist/`, `out/`, `build/`, `_site/`, `public/`, `.output/public`). If there's no build, look at the package/build config and ask before running a build command.
2. Call `audit_directory` with the folder and the production `base_url` if known.
3. Report: average score, issues by number of files affected, duplicate titles/descriptions, broken internal links, pages without meta descriptions or H1, noindex pages that shouldn't be.
4. Point each issue at the source template/component that produces it, and offer to fix it.
5. Mention the CI option: `python3 <plugin>/server/run.py dir ./dist --base-url https://example.com --min-score 80` exits non-zero below the threshold.
