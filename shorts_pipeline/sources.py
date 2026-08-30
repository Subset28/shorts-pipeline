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
    "Finance": "https://news.google.com/rss/search?q=technology%20finance%20markets%20AI&hl=en-US&gl=US&ceid=US:en",
}

_CATEGORY_TERMS = {
    "AI": ("artificial intelligence", " ai ", "llm", "language model", "neural", "agent", "generative"),
    "ML": ("machine learning", "deep learning", "neural", "model", "training", "inference", "dataset", "classifier"),
    "CS": ("software", "programming", "developer", "code", "database", "browser", "linux", "computer", "open source", "api", "algorithm"),
    "AI News": ("artificial intelligence", " ai ", "llm", "robot", "neural", "model", "algorithm", "machine learning"),
    "Aerospace": ("space", "rocket", "launch", "orbit", "satellite", "spacecraft", "nasa", "lunar", "mars", "astronaut"),
    "Cyber": ("cve", "vulnerability", "security", "cyber", "malware", "ransomware", "exploit", "patch", "breach", "authentication"),
    "Finance": ("finance", "market", "stock", "invest", "fund", "earnings", "bank", "economy", "revenue", "valuation"),
}

_HIGH_SIGNAL_TERMS = re.compile(
    r"\b(launch(?:es|ed)?|new|first|breakthrough|hacked|hack|breach|"
    r"vulnerability|discovers?|reveals?|goes online|deploy(?:s|ed)?|fails?|"
    r"record|challenge|mission|test(?:s|ed)?|upgrade|change(?:s|d)?)\b",
    re.IGNORECASE,
)
_LOW_SIGNAL_TERMS = re.compile(
    r"\b(ribbon[- ]cutting|honors?|honour|ceremony|event|statement|"
    r"congratulations?|remarks?|recognition)\b",
    re.IGNORECASE,
)


def is_relevant(category: str, source: Source) -> bool:
    """Keep a feed item only when its text supports the advertised lane."""
    text = f" {source.title} {source.summary} ".lower()
    terms = _CATEGORY_TERMS.get(category)
    return bool(terms and any(term in text for term in terms))


def is_usable_source(source: Source) -> bool:
    """Reject feed navigation labels and entries too thin to explain."""
    title = re.sub(r"\s+", " ", source.title).strip().lower()
    if re.fullmatch(r"(markets|news|latest news|home|front page)(\s*[-|].*)?", title):
        return False
    title_words = re.findall(r"[a-z0-9]+", title)
    summary_words = re.findall(r"[a-z0-9]+", source.summary.lower())
    # A headline alone is not enough for a source-backed short: it produces
    # the exact shallow, prematurely-ended narration the non-Reddit lane was
    # generating. Require enough source text to explain a concrete result.
    return len(title_words) >= 4 and len(summary_words) >= 5


def _clean_summary(value: str) -> str:
    value = html.unescape(value)
    # Some feeds decode smart punctuation as the replacement character.
    value = value.replace("\ufffd", "'")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"https?://\S+", " ", value)
    value = re.sub(r"\b(?:article|comments?)\s+url\s*:\s*", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"(?:\bpoints|#\s*comments?)\s*:\s*\d+", " ", value, flags=re.IGNORECASE)
    # Technology Review's newsletter feed prepends a reusable newsletter
    # description to the actual item. It is not source-specific context and
    # sounds like an advertisement when sent to narration.
    value = re.sub(
        r"^this is today[’']s edition of the download,.*?world of technology\.\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", value).strip(" .-")


def _clean_title(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value).replace("\ufffd", "'")).strip()


def _source_score(source: Source, published: str, now: datetime) -> float:
    """Score narrative potential, not popularity or expected views."""
    score = 1.0 + min(len(source.summary.split()) / 120, 0.8)
    if _HIGH_SIGNAL_TERMS.search(source.title):
        score += 0.45
    if _LOW_SIGNAL_TERMS.search(source.title):
        score -= 0.45
    if re.search(r"\b\d+(?:\.\d+)?(?:%|[- ]year|[- ]meter|[- ]month)?\b", source.title, re.IGNORECASE):
        score += 0.2
    if published and now.year >= 2020:
        score += 0.1
    return score


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
                title=_clean_title(str(entry.get("title", "Untitled"))),
                url=link,
                summary=_clean_summary(str(entry.get("summary", entry.get("description", "")))),
                published=published,
            )
            if not is_relevant(category, source) or not is_usable_source(source):
                continue
            # Do not turn RSS truncation markers into spoken cliffhangers.
            summary_words = source.summary.split()
            if len(summary_words) < 20 or source.summary.endswith(("...", "…")):
                continue
            # Prefer current, well-described entries. The exact popularity
            # signal comes later from channel analytics, not fake view counts.
            score = _source_score(source, published, now)
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
