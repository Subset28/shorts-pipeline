from __future__ import annotations

import html
import re
from datetime import datetime, timezone

import feedparser

from .models import Source, Topic

FEEDS = {
    "AI": "https://export.arxiv.org/rss/cs.AI",
    "ML": "https://export.arxiv.org/rss/cs.LG",
    "CS": "https://hnrss.org/frontpage",
    "AI News": "https://www.technologyreview.com/feed/",
    "Aerospace": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
    "Cyber": "https://nvd.nist.gov/feeds/xml/cve/mva.xml",
}


def _clean_summary(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def discover_topics(limit: int = 10) -> list[Topic]:
    by_category: dict[str, list[Topic]] = {category: [] for category in FEEDS}
    now = datetime.now(timezone.utc)
    for category, url in FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:limit]:
            published = str(entry.get("published", ""))
            link = str(entry.get("link", "")).strip()
            if not link:
                continue
            source = Source(
                title=str(entry.get("title", "Untitled")).strip(),
                url=link,
                summary=_clean_summary(str(entry.get("summary", entry.get("description", "")))),
                published=published,
            )
            # Prefer current, well-described entries. The exact popularity
            # signal comes later from channel analytics, not fake view counts.
            score = 1.0 if source.summary else 0.0
            if published and now.year >= 2020:
                score += 0.1
            by_category[category].append(Topic(source.title, category, (source,), score))

    # Keep a batch from being dominated by the first feed in the map. Within
    # each category, retain the highest-quality entries, then interleave
    # categories so the queue tests several audience lanes.
    for category in by_category:
        by_category[category].sort(key=lambda item: item.score, reverse=True)
    topics: list[Topic] = []
    while len(topics) < limit:
        added = False
        for category in FEEDS:
            if by_category[category]:
                topics.append(by_category[category].pop(0))
                added = True
                if len(topics) == limit:
                    break
        if not added:
            break
    return topics
