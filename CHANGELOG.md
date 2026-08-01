# AI Radar changelog

- 2026-07-04: monthly self-tune — no changes. Repo is 1 day old, no engagement data yet (~/.hermes/distiller_log.md doesn't exist). All 5 feeds + HN queries verified alive via curl (200, items present); VentureBeat/Ars produced 0 candidates this window but feeds are healthy. Revisit with real engagement data in August.
- 2026-08-01: monthly self-tune — changed VentureBeat’s feed URL only by removing its trailing slash. The old URL now returns HTTP 308, which the collector’s parser does not follow; the canonical URL returns the live XML feed. Kept every source: no engagement callbacks exist, and TechCrunch, Verge, Ars, Simon, and HN all produced published candidates in the 7-day collection run.
