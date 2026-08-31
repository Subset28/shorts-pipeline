#!/usr/bin/env python3
"""Notify the local Mac when the repository receives new GitHub activity."""

import json
import os
import subprocess
from pathlib import Path

REPO = os.getenv("GITHUB_MONITOR_REPO", "Subset28/shorts-pipeline")
STATE = Path(
    os.getenv("GITHUB_MONITOR_STATE", "/Volumes/n2me/Developer/shorts-pipeline/data/github_monitor_state.json")
)
WATCHED_EVENTS = {"PullRequestEvent", "PullRequestReviewEvent", "IssueCommentEvent", "PushEvent"}


def fetch_events() -> list[dict]:
    result = subprocess.run(
        ["gh", "api", f"repos/{REPO}/events?per_page=30"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)
    if not isinstance(payload, list):
        raise RuntimeError("GitHub events response was not a list")
    return [item for item in payload if isinstance(item, dict) and item.get("id")]


def notify(title: str, message: str) -> None:
    subprocess.run(
        ["osascript", "-e", "display notification (item 2 of argv) with title (item 1 of argv)", "--", title, message],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )


def _load_state() -> set[str]:
    if not STATE.exists():
        return set()
    try:
        value = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {str(item) for item in value} if isinstance(value, list) else set()


def _save_state(event_ids: set[str]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix(f"{STATE.suffix}.tmp")
    temporary.write_text(json.dumps(sorted(event_ids)), encoding="utf-8")
    temporary.replace(STATE)


def _event_message(event: dict) -> tuple[str, str]:
    actor_data = event.get("actor") if isinstance(event.get("actor"), dict) else {}
    actor = actor_data.get("display_login") or actor_data.get("login") or "Someone"
    event_type = str(event.get("type", "GitHub activity")).removesuffix("Event")
    payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
    action = payload.get("action")
    pull_request = payload.get("pull_request") or payload.get("issue")
    title = pull_request.get("title") if isinstance(pull_request, dict) else ""
    number = pull_request.get("number") if isinstance(pull_request, dict) else ""
    context = f" #{number} {title}" if number or title else ""
    suffix = f" ({action})" if action else ""
    return "Shorts Pipeline GitHub activity", f"{actor}: {event_type}{context}{suffix}"


def main() -> None:
    events = fetch_events()
    watched = [event for event in events if event.get("type") in WATCHED_EVENTS]
    previous = _load_state()
    current = {str(event["id"]) for event in watched}
    new_events = [event for event in reversed(watched) if str(event["id"]) not in previous]
    _save_state(current)
    if not previous:
        return
    for event in new_events:
        notify(*_event_message(event))


if __name__ == "__main__":
    main()
