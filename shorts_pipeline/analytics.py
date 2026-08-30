from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _number(row: dict[str, str], name: str) -> float:
    value = (row.get(name) or "0").strip().replace(",", "")
    try:
        return max(0.0, float(value))
    except ValueError:
        return 0.0


def build_report(events_path: Path, metrics_path: Path) -> dict[str, Any]:
    """Join exported platform metrics to local draft telemetry.

    The metrics CSV must include source_url, platform, and views. Optional
    likes/comments/shares columns are accepted. Source URLs are used as the
    stable join key because platform exports use different video IDs.
    """
    event_index: dict[str, dict[str, str]] = {}
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("event") == "draft_created" and event.get("source_url"):
                event_index[str(event["source_url"])] = {
                    "category": str(event.get("category", "unknown")),
                    "format_name": str(event.get("format_name", "unknown")),
                    "title": str(event.get("title", "")),
                }

    aggregates: dict[tuple[str, str, str], dict[str, float]] = defaultdict(lambda: {"videos": 0.0, "views": 0.0, "likes": 0.0, "comments": 0.0, "shares": 0.0})
    unmatched = 0
    with metrics_path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            source_url = (row.get("source_url") or "").strip()
            if source_url not in event_index:
                unmatched += 1
                continue
            event = event_index[source_url]
            platform = (row.get("platform") or "unknown").strip().lower()
            key = (event["category"], event["format_name"], platform)
            bucket = aggregates[key]
            bucket["videos"] += 1
            for field in ("views", "likes", "comments", "shares"):
                bucket[field] += _number(row, field)

    rows = []
    for (category, format_name, platform), values in sorted(aggregates.items()):
        views = values["views"]
        rows.append({
            "category": category,
            "format_name": format_name,
            "platform": platform,
            "videos": int(values["videos"]),
            "views": int(views),
            "avg_views": round(views / values["videos"], 2) if values["videos"] else 0,
            "engagement_rate": round((values["likes"] + values["comments"] + values["shares"]) / views, 4) if views else 0,
        })
    return {"rows": rows, "matched_rows": sum(row["videos"] for row in rows), "unmatched_rows": unmatched}


def write_report(report: dict[str, Any], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return output
