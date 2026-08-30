from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_seen(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return set()


def mark_seen(path: Path, url: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = load_seen(path)
    seen.add(url)
    path.write_text(json.dumps(sorted(seen), indent=2), encoding="utf-8")


def load_publish_state(path: Path) -> dict[str, dict[str, Any]]:
    """Load resumable per-source platform IDs, tolerating an absent/corrupt file."""
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def save_publish_state(path: Path, source_url: str, **platform_ids: str) -> None:
    """Atomically persist successful platform uploads so retries do not duplicate them."""
    path.parent.mkdir(parents=True, exist_ok=True)
    state = load_publish_state(path)
    current = dict(state.get(source_url, {}))
    current.update({key: value for key, value in platform_ids.items() if value})
    state[source_url] = current
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)
