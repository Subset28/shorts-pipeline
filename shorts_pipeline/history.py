from __future__ import annotations

import json
from pathlib import Path


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
