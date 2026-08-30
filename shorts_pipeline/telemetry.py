from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def record_event(path: Path, event: str, **fields: Any) -> None:
    """Append a small local event record; no secrets or personal viewer data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
