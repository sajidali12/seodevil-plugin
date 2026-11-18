# Contributing

Thanks for helping improve SEODevil!

## Layout

```
.claude-plugin/plugin.json      plugin manifest (and marketplace.json, so the repo installs directly)
.mcp.json                       starts the MCP server with python3
commands/*.md                   slash commands (/seodevil:<name>)
skills/<name>/SKILL.md          SEO knowledge Claude loads when relevant
agents/*.md                     subagents (auditor, fixer, content strategist, competitor analyst)
server/seodevil_mcp/            MCP server + analyzers (Python standard library only)
server/tests/                   offline unit tests
```

## Rules

- **No third-party Python dependencies.** The server must run on a stock `python3` (3.9+) on macOS, Linux and Windows. This is the reason the plugin installs with zero setup.
- Analyzers must not make network calls (`onpage.py`, `schema.py`), so they also work on local files. Network checks go in `audit.py`, `site.py`, `crawler.py` or `external.py`.
- Every issue needs an `id`, a `severity` (critical/high/medium/low/info), a plain-language `title` and an actionable `fix`. Keep severities honest: reserve critical for things that stop a page from ranking.
- Claims in skills must be accurate and current. Cite Google Search Central or vendor docs in the PR description when changing guidance.
- Add a test in `server/tests/test_offline.py` for new checks (no network in tests).

## Run locally

```bash
python3 -m unittest discover -s server/tests -v
python3 server/run.py audit https://example.com          # CLI
claude --plugin-dir .                                      # load the plugin in Claude Code from this checkout
claude plugin validate .
```
