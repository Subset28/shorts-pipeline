#!/usr/bin/env python3
"""Notify the local Mac when the repository receives new GitHub activity."""

import json
import subprocess
from pathlib import Path

REPO = "Subset28/shorts-pipeline"
STATE = Path("/Volumes/n2me/Developer/shorts-pipeline/data/github_monitor_state.json")


def fetch_events() -> list[dict]:
    result = subprocess.run(
        ["gh", "api", f"repos/{REPO}/events?per_page=30"],
        check=True,
        capture_output=True,
        text=True,
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
    )


def main() -> None:
    events = fetch_events()
    STATE.parent.mkdir(parents=True, exist_ok=True)
    previous = set(json.loads(STATE.read_text(encoding="utf-8"))) if STATE.exists() else set()
    current = {str(event["id"]) for event in events}
    new_events = [event for event in reversed(events) if str(event["id"]) not in previous]
    STATE.write_text(json.dumps(sorted(current)), encoding="utf-8")
    if not previous:
        return
    for event in new_events:
        actor = event.get("actor", {}).get("display_login") or event.get("actor", {}).get("login") or "Someone"
        event_type = str(event.get("type", "GitHub activity")).removesuffix("Event")
        notify("Shorts Pipeline GitHub activity", f"{actor}: {event_type}")


if __name__ == "__main__":
    main()
