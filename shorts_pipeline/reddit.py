from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote

import httpx

from .models import Source, Topic

RANKED_STORY_SUBREDDITS = (
    "TalesFromTechSupport", "AskReddit", "aviation", "flying", "sysadmin",
    "AskEngineers", "cscareerquestions", "AerospaceEngineering", "cybersecurity",
    "MachineLearning", "ExperiencedDevs", "ProgrammerHumor", "rocketry", "SpaceX",
    "aircraft", "netsec", "hacking", "OSINT", "techsupport", "ShittySysAdmin",
)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


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
        token_response = client.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
        )
        token_response.raise_for_status()
        token = token_response.json().get("access_token")
        if not token:
            raise RuntimeError("Reddit OAuth response did not contain an access token")
        client.headers.update({"Authorization": f"bearer {token}"})
        topics: list[Topic] = []
        for subreddit in subreddits:
            response = client.get(
                f"https://oauth.reddit.com/r/{quote(subreddit.strip(), safe='')}/top",
                params={"t": "week", "limit": min(max(limit, 1), 100), "raw_json": 1},
            )
            response.raise_for_status()
            children = response.json().get("data", {}).get("children", [])
            for child in children:
                post = child.get("data", {})
                body = _clean_text(str(post.get("selftext", "")))
                if post.get("stickied") or post.get("over_18"):
                    continue
                author = str(post.get("author", "")).strip()
                permalink = str(post.get("permalink", "")).strip()
                if not author or not permalink:
                    continue
                community = str(post.get("subreddit", subreddit)).strip()
                title = _clean_text(str(post.get("title", "")))
                if title and len(body.split()) >= 40:
                    source = Source(title, f"https://www.reddit.com{permalink}", body, str(post.get("created_utc", "")), author, community, False)
                    topics.append(Topic(source.title, "Reddit Stories", (source,), float(post.get("score", 0))))
                # Prompt threads often contain the best first-person stories in
                # comments rather than in the post body itself.
                prompt_thread = "?" in title or "story" in title.lower() or community.lower() in {"askreddit", "aviation", "flying", "askengineers"}
                post_id = str(post.get("id", "")).strip()
                if not prompt_thread or not post_id:
                    continue
                comments = client.get(f"https://oauth.reddit.com/comments/{quote(post_id, safe='')}", params={"limit": 20, "raw_json": 1})
                comments.raise_for_status()
                listings = comments.json()
                if not isinstance(listings, list) or len(listings) < 2:
                    continue
                for comment_child in listings[1].get("data", {}).get("children", []):
                    comment = comment_child.get("data", {})
                    comment_body = _clean_text(str(comment.get("body", "")))
                    comment_author = str(comment.get("author", "")).strip()
                    comment_permalink = str(comment.get("permalink", "")).strip()
                    if comment.get("stickied") or comment_author in {"", "[deleted]"} or len(comment_body.split()) < 40 or not comment_permalink:
                        continue
                    comment_source = Source(
                        f"{title} — story from u/{comment_author}",
                        f"https://www.reddit.com{comment_permalink}",
                        comment_body,
                        str(comment.get("created_utc", "")),
                        comment_author,
                        community,
                        False,
                    )
                    topics.append(Topic(comment_source.title, "Reddit Stories", (comment_source,), float(comment.get("score", 0))))
        return sorted(topics, key=lambda item: item.score, reverse=True)[: max(1, limit)]


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
            _clean_text(str(data.get("summary", ""))),
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
            and source.url.lower().startswith(("https://www.reddit.com/", "https://old.reddit.com/", "https://redd.it/"))
        ):
            topics.append(Topic(source.title, "Reddit Stories", (source,), float(record.get("score", 0))))
    return topics
