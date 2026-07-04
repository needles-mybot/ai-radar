#!/usr/bin/env python3
"""
AI Radar — news collector.

Pulls fresh AI news candidates from RSS/Atom feeds + Hacker News (Algolia),
dedupes against items already on the dashboard (data/news.json), and prints
a JSON array of NEW candidates to stdout. Read-only: never writes files.

The enrichment step (summaries + money angles) is done by the cron agent,
which then writes data/news.json and pushes to GitHub Pages.

Anti-fabrication: every candidate carries its REAL source URL, title,
timestamp, and the feed's own snippet. Nothing is invented here.
"""
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
NEWS_JSON = os.path.join(HERE, "data", "news.json")

# Default sources — used only if sources.json is missing/corrupt.
# The LIVE source list is ~/ai-radar/sources.json (agent-editable; the cron
# tunes it monthly based on hit-rate). Bitter-Lesson note: knowledge of WHERE
# to look lives in data, not code, so the agent can improve it without a deploy.
DEFAULT_FEEDS = [
    ("TechCrunch", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("VentureBeat", "https://venturebeat.com/category/ai/feed/"),
    ("The Verge", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("Ars Technica", "https://arstechnica.com/ai/feed/"),
    ("Simon Willison", "https://simonwillison.net/atom/everything/"),
]
DEFAULT_HN_URLS = [
    "https://hn.algolia.com/api/v1/search?tags=front_page&query=AI",
    "https://hn.algolia.com/api/v1/search?tags=front_page&query=LLM",
]
SOURCES_JSON = os.path.expanduser("~/ai-radar/sources.json")

def load_sources() -> tuple:
    """Read agent-editable sources.json; fall back to defaults on any problem."""
    try:
        with open(SOURCES_JSON, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
        feeds = [(f["name"], f["url"]) for f in cfg.get("feeds", []) if f.get("url")]
        hn = [u for u in cfg.get("hn_queries", []) if isinstance(u, str) and u]
        if feeds:
            return feeds, hn
    except Exception as exc:
        print(f"[warn] sources.json unusable ({exc}); using defaults", file=sys.stderr)
    return DEFAULT_FEEDS, DEFAULT_HN_URLS

FEEDS, HN_URLS = load_sources()

def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

def _id_for(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]

def existing_urls() -> set:
    try:
        with open(NEWS_JSON, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return {it.get("url", "") for it in data.get("items", [])}
    except Exception:
        return set()

def fetch_feeds(cutoff: datetime) -> list:
    import feedparser
    out = []
    for source, url in FEEDS:
        try:
            parsed = feedparser.parse(url)
        except Exception as exc:
            print(f"[warn] {source}: {exc}", file=sys.stderr)
            continue
        for e in parsed.entries[:25]:
            link = getattr(e, "link", "") or ""
            title = _strip_html(getattr(e, "title", ""))
            if not link or not title:
                continue
            t = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
            if t:
                when = datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
                if when < cutoff:
                    continue
                ts = when.isoformat()
            else:
                ts = ""
            snippet = _strip_html(getattr(e, "summary", ""))[:600]
            out.append({"id": _id_for(link), "source": source, "title": title,
                        "url": link, "published": ts, "snippet": snippet})
    return out

def fetch_hn(cutoff: datetime) -> list:
    out, seen = [], set()
    for api in HN_URLS:
        try:
            req = urllib.request.Request(api, headers={"User-Agent": "ai-radar/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            print(f"[warn] HN: {exc}", file=sys.stderr)
            continue
        for hit in data.get("hits", []):
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            if url in seen:
                continue
            seen.add(url)
            created = hit.get("created_at", "")
            try:
                when = datetime.fromisoformat(created.replace("Z", "+00:00"))
                if when < cutoff:
                    continue
            except Exception:
                pass
            out.append({
                "id": _id_for(url), "source": "Hacker News",
                "title": _strip_html(hit.get("title", "")), "url": url,
                "published": created,
                "snippet": f"{hit.get('points', 0)} points, {hit.get('num_comments', 0)} comments on HN",
                "hn_comments": f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            })
    return out

def main() -> int:
    hours = 36
    for i, a in enumerate(sys.argv):
        if a == "--hours" and i + 1 < len(sys.argv):
            hours = int(sys.argv[i + 1])
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    known = existing_urls()
    candidates = fetch_feeds(cutoff) + fetch_hn(cutoff)
    fresh, seen = [], set()
    for c in candidates:
        if c["url"] in known or c["url"] in seen or not c["title"]:
            continue
        seen.add(c["url"])
        fresh.append(c)
    fresh.sort(key=lambda c: c.get("published", ""), reverse=True)
    print(json.dumps({"generated": datetime.now(timezone.utc).isoformat(),
                      "window_hours": hours, "count": len(fresh),
                      "candidates": fresh}, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
