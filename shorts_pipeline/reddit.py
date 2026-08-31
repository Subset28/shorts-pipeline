from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path
from urllib.parse import quote

import httpx

from .models import Source, Topic

RANKED_STORY_SUBREDDITS = (
    "TalesFromTechSupport",
    "AskReddit",
    "aviation",
    "flying",
    "sysadmin",
    "AskEngineers",
    "cscareerquestions",
    "AerospaceEngineering",
    "cybersecurity",
    "MachineLearning",
    "ExperiencedDevs",
    "ProgrammerHumor",
    "rocketry",
    "SpaceX",
    "netsec",
    "hacking",
    "OSINT",
    "techsupport",
    "ShittySysAdmin",
)

MIN_STORY_WORDS = 80
GENERIC_COMMUNITIES = {"askreddit"}
NICHE_SIGNALS = re.compile(
    r"\b(ai|artificial intelligence|machine learning|software|program(?:mer|ming)|"
    r"coding|computer|database|server|production|devops|sysadmin|cyber|security|"
    r"hacker|malware|pilot|airline|aviation|aircraft|rocket|spacecraft|aerospace|"
    r"engineer|engineering|finance|trading|market|stock)\b",
    re.IGNORECASE,
)
STORY_SIGNALS = re.compile(
    r"\b(after|before|then|eventually|finally|turned out|ended up|restored|fixed|failed|broke|lesson|takeaway|incident|outage)\b",
    re.IGNORECASE,
)
GENERIC_TITLE = re.compile(
    r"\b(anyone else|are we doomed|does anyone|what do you think|thoughts|help me)\b", re.IGNORECASE
)


def _story_category(community: str) -> str:
    """Map narrative communities back to the channel's topical lanes."""
    name = community.lower()
    if name in {"aerospaceengineering", "rocketry", "spacex", "aviation", "flying", "aircraft"}:
        return "Aerospace"
    if name in {"cybersecurity", "netsec", "hacking", "osint"}:
        return "Cyber"
    if name in {"machinelearning", "artificialintelligence", "deeplearning"}:
        return "AI/ML"
    if name in {
        "talesfromtechsupport",
        "sysadmin",
        "shittysysadmin",
        "experienceddevs",
        "programmerhumor",
        "programming",
        "cscareerquestions",
        "techsupport",
    }:
        return "CS"
    return "Technology"


def _is_niche_relevant(community: str, title: str, body: str) -> bool:
    """Reject generic prompt answers that do not fit the channel promise."""
    if community.lower() not in GENERIC_COMMUNITIES:
        return True
    return bool(NICHE_SIGNALS.search(f"{title} {body}"))


def _reddit_quality_score(topic: Topic) -> float:
    source = topic.sources[0]
    text = f"{source.title} {source.summary}"
    score = math.log1p(max(0.0, topic.score)) * 10
    score += min(len(source.summary.split()), 500) * 0.12
    score += len(NICHE_SIGNALS.findall(text)) * 8
    score += len(STORY_SIGNALS.findall(text)) * 14
    score += min(len(source.title.split()), 12) * 2
    if GENERIC_TITLE.search(source.title):
        score -= 35
    if len(source.summary.split()) < 100:
        score -= 45
    return score


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _clean_story_text(value: str) -> str:
    """Remove spoken URL noise while preserving Markdown link labels."""
    value = re.sub(r"\[([^]]+)\]\(https?://[^)]+\)", r"\1", value)
    return _clean_text(re.sub(r"https?://\S+", "", value))


def _listing_children(payload: object) -> list:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    children = data.get("children")
    return children if isinstance(children, list) else []


def _score_value(value: object) -> float:
    """Normalize an optional Reddit score without aborting discovery."""
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return score if math.isfinite(score) else 0.0


def _token_value(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    token = payload.get("access_token")
    return token if isinstance(token, str) and token else ""


def _get_with_retries(client, url: str, params: dict) -> object | None:
    """Fetch a Reddit listing while tolerating stale communities and throttling."""
    for attempt in range(3):
        try:
            response = client.get(url, params=params)
        except httpx.RequestError:
            if attempt == 2:
                return None
            time.sleep(1.0)
            continue
        status = getattr(response, "status_code", None)
        if status in {403, 404}:
            return None
        if status == 429 or isinstance(status, int) and status >= 500:
            if attempt == 2:
                return None
            headers = getattr(response, "headers", {}) or {}
            try:
                delay = float(headers.get("retry-after", "1"))
            except (TypeError, ValueError):
                delay = 1.0
            time.sleep(min(max(delay, 1.0), 8.0))
            continue
        response.raise_for_status()
        return response
    return None


def _post_with_retries(client, url: str, auth, data: dict) -> object | None:
    """Fetch an OAuth response while tolerating transient request failures."""
    for attempt in range(3):
        try:
            response = client.post(url, auth=auth, data=data)
        except httpx.RequestError:
            if attempt == 2:
                return None
            time.sleep(1.0)
            continue
        status = getattr(response, "status_code", None)
        if status == 429 or isinstance(status, int) and status >= 500:
            if attempt == 2:
                return None
            headers = getattr(response, "headers", {}) or {}
            try:
                delay = float(headers.get("retry-after", "1"))
            except (TypeError, ValueError):
                delay = 1.0
            time.sleep(min(max(delay, 1.0), 8.0))
            continue
        response.raise_for_status()
        return response
    return None


def discover_reddit_topics(
    subreddits: tuple[str, ...],
    client_id: str,
    client_secret: str,
    user_agent: str,
    limit: int = 10,
) -> list[Topic]:
    """Collect candidate stories through Reddit's OAuth API.

    Candidates intentionally have ``reuse_permission=False``. Fetching a post
    creates a research candidate, not permission to republish it. An operator
    must verify the rightsholder's permission before the reddit_story lane can
    select it.
    """
    if not client_id or not client_secret:
        return []
    headers = {"User-Agent": user_agent or "shorts-pipeline/1.0 (research client)"}
    with httpx.Client(timeout=30, headers=headers, follow_redirects=True) as client:
        token_response = _post_with_retries(
            client,
            "https://www.reddit.com/api/v1/access_token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
        )
        if token_response is None:
            raise RuntimeError("Reddit OAuth request failed after retries")
        token = _token_value(token_response.json())
        if not token:
            raise RuntimeError("Reddit OAuth response did not contain an access token")
        client.headers.update({"Authorization": f"bearer {token}"})
        topics: list[Topic] = []
        seen_urls: set[str] = set()
        for subreddit in subreddits:
            response = _get_with_retries(
                client,
                f"https://oauth.reddit.com/r/{quote(subreddit.strip(), safe='')}/top",
                {"t": "week", "limit": min(max(limit, 5), 25), "raw_json": 1},
            )
            if response is None:
                continue
            children = _listing_children(response.json())
            for child in children:
                if not isinstance(child, dict):
                    continue
                post = child.get("data", {})
                if not isinstance(post, dict):
                    continue
                body = _clean_story_text(str(post.get("selftext", "")))
                if post.get("stickied") or post.get("over_18"):
                    continue
                author = str(post.get("author", "")).strip()
                permalink = str(post.get("permalink", "")).strip()
                if not author or not permalink:
                    continue
                community = str(post.get("subreddit", subreddit)).strip()
                title = _clean_text(str(post.get("title", "")))
                if not _is_niche_relevant(community, title, body):
                    continue
                if title and len(body.split()) >= MIN_STORY_WORDS:
                    source_url = f"https://www.reddit.com{permalink}"
                    if source_url not in seen_urls:
                        source = Source(
                            title, source_url, body[:4000], str(post.get("created_utc", "")), author, community, False
                        )
                        topics.append(
                            Topic(
                                source.title, _story_category(community), (source,), _score_value(post.get("score", 0))
                            )
                        )
                        seen_urls.add(source_url)
                # Prompt threads often contain the best first-person stories in
                # comments rather than in the post body itself.
                prompt_thread = (
                    "?" in title
                    or "story" in title.lower()
                    or community.lower() in {"askreddit", "aviation", "flying", "askengineers"}
                )
                post_id = str(post.get("id", "")).strip()
                if not prompt_thread or not post_id:
                    continue
                comments = _get_with_retries(
                    client,
                    f"https://oauth.reddit.com/comments/{quote(post_id, safe='')}",
                    {"limit": 20, "raw_json": 1},
                )
                if comments is None:
                    continue
                listings = comments.json()
                if not isinstance(listings, list) or len(listings) < 2:
                    continue
                for comment_child in _listing_children(listings[1]):
                    if not isinstance(comment_child, dict):
                        continue
                    comment = comment_child.get("data", {})
                    if not isinstance(comment, dict):
                        continue
                    comment_body = _clean_story_text(str(comment.get("body", "")))
                    comment_author = str(comment.get("author", "")).strip()
                    comment_permalink = str(comment.get("permalink", "")).strip()
                    if (
                        comment.get("stickied")
                        or comment_author in {"", "[deleted]"}
                        or len(comment_body.split()) < MIN_STORY_WORDS
                        or not comment_permalink
                    ):
                        continue
                    comment_url = f"https://www.reddit.com{comment_permalink}"
                    if comment_url in seen_urls:
                        continue
                    comment_source = Source(
                        f"{title} — story from u/{comment_author}",
                        comment_url,
                        comment_body[:4000],
                        str(comment.get("created_utc", "")),
                        comment_author,
                        community,
                        False,
                    )
                    topics.append(
                        Topic(
                            comment_source.title,
                            _story_category(community),
                            (comment_source,),
                            _score_value(comment.get("score", 0)),
                        )
                    )
                    seen_urls.add(comment_url)
        return sorted(topics, key=_reddit_quality_score, reverse=True)[: max(1, limit)]


def load_approved_reddit_topics(path: Path) -> list[Topic]:
    """Load only locally approved candidate records for the publish pipeline."""
    if not path.exists():
        return []
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Reddit candidate file must contain a list")
    topics = []
    for record in records:
        data = record.get("source", {}) if isinstance(record, dict) else {}
        if not isinstance(data, dict) or data.get("reuse_permission") is not True:
            continue
        source = Source(
            str(data.get("title", "")).strip(),
            str(data.get("url", "")).strip(),
            _clean_story_text(str(data.get("summary", ""))),
            str(data.get("published", "")),
            str(data.get("author", "")).strip(),
            str(data.get("community", "")).strip(),
            True,
        )
        if (
            source.title
            and source.summary
            and source.author
            and source.community
            and source.url.lower().startswith(
                ("https://www.reddit.com/", "https://old.reddit.com/", "https://redd.it/")
            )
        ):
            topics.append(
                Topic(source.title, _story_category(source.community), (source,), _score_value(record.get("score", 0)))
            )
    return topics
