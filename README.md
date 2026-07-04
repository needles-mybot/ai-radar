# AI Radar

Public dashboard tracking AI industry news. Collects from RSS feeds and Hacker News (Algolia API), deduplicates, enriches with summaries and money angles, and publishes to GitHub Pages.

## Structure

| File | Purpose |
|---|---|
| `collect_ai_news.py` | News collector — reads feeds/HN, dedupes against `data/news.json`, prints new candidates to stdout |
| `index.html` | GitHub Pages dashboard (static HTML) |
| `sources.json` | Agent-editable source list (feeds + HN) |
| `data/news.json` | Enriched news feed (summary + money angle, written by cron agent) |
| `CHANGELOG.md` | Change log |

## How it works

1. The weekly cron runs `collect_ai_news.py` — it queries configured RSS feeds and Hacker News Algolia, dedupes against existing `data/news.json`, and prints new candidates as JSON to stdout.
2. The enrichment agent reads stdout, fetches summaries via LLM, writes `data/news.json`, and pushes to the `gh-pages` branch.
3. `index.html` serves the live dashboard from GitHub Pages.

## Configuration

- `sources.json` — the live source list. The cron agent tunes this monthly based on hit-rate.
- Default sources are hardcoded in `collect_ai_news.py` as a fallback if `sources.json` is missing or corrupt.

## Anti-fabrication

Every candidate carries its real source URL, title, timestamp, and the feed's own snippet. Nothing is invented at the collection stage.
