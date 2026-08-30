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


def _variant(row: dict[str, str], name: str = "variant") -> int:
    try:
        return max(0, int((row.get(name) or "0").strip()))
    except (TypeError, ValueError):
        return 0


def build_report(events_path: Path, metrics_path: Path) -> dict[str, Any]:
    """Join exported platform metrics to local draft telemetry.

    The metrics CSV must include source_url, platform, and views. Optional
    likes/comments/shares columns are accepted. Source URLs are used as the
    stable join key because platform exports use different video IDs.
    """
    event_index: dict[tuple[str, int], dict[str, str]] = {}
    variants_by_source: dict[str, set[int]] = defaultdict(set)
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("event") == "draft_created" and event.get("source_url"):
                source_url = str(event["source_url"])
                variant = _variant({"variant": str(event.get("variant", 0))})
                event_index[(source_url, variant)] = {
                    "category": str(event.get("category", "unknown")),
                    "format_name": str(event.get("format_name", "unknown")),
                    "title": str(event.get("title", "")),
                }
                variants_by_source[source_url].add(variant)

    aggregates: dict[tuple[str, str, str, int], dict[str, float]] = defaultdict(lambda: {"videos": 0.0, "views": 0.0, "likes": 0.0, "comments": 0.0, "shares": 0.0})
    unmatched = 0
    with metrics_path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            source_url = (row.get("source_url") or "").strip()
            variant = _variant(row)
            event = event_index.get((source_url, variant))
            # Older exports do not contain variant. Preserve their behavior
            # when exactly one draft exists for the source, but never guess
            # when multiple treatments need to be distinguished.
            if event is None and len(variants_by_source.get(source_url, set())) == 1:
                only_variant = next(iter(variants_by_source[source_url]))
                event = event_index.get((source_url, only_variant))
                variant = only_variant
            if event is None:
                unmatched += 1
                continue
            platform = (row.get("platform") or "unknown").strip().lower()
            key = (event["category"], event["format_name"], platform, variant)
            bucket = aggregates[key]
            bucket["videos"] += 1
            for field in ("views", "likes", "comments", "shares"):
                bucket[field] += _number(row, field)

    rows = []
    for (category, format_name, platform, variant), values in sorted(aggregates.items()):
        views = values["views"]
        rows.append({
            "category": category,
            "format_name": format_name,
            "platform": platform,
            "variant": variant,
            "videos": int(values["videos"]),
            "views": int(views),
            "avg_views": round(views / values["videos"], 2) if values["videos"] else 0,
            "engagement_rate": round((values["likes"] + values["comments"] + values["shares"]) / views, 4) if views else 0,
        })
    report = {"rows": rows, "matched_rows": sum(row["videos"] for row in rows), "unmatched_rows": unmatched}
    report["recommendations"] = tuning_recommendations(report)
    return report


def tuning_recommendations(report: dict[str, Any], min_videos: int = 2) -> list[str]:
    """Translate repeated lane performance into conservative next actions."""
    rows = [row for row in report.get("rows", []) if int(row.get("videos", 0)) >= min_videos]
    if not rows:
        return ["Collect at least two videos per lane before changing the content mix."]
    by_views = max(rows, key=lambda row: float(row.get("avg_views", 0)))
    by_engagement = max(rows, key=lambda row: float(row.get("engagement_rate", 0)))
    recommendations = [
        f"Keep testing {by_views['category']} / {by_views['format_name']}; it leads repeated lanes by average views.",
        f"Study the hook and pacing of {by_engagement['category']} / {by_engagement['format_name']}; it leads repeated lanes by engagement rate.",
    ]
    if by_views["category"] != by_engagement["category"] or by_views["format_name"] != by_engagement["format_name"]:
        recommendations.append("Views and engagement favor different lanes; keep both in rotation instead of optimizing for one metric.")
    return recommendations


def write_report(report: dict[str, Any], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return output


def archive_report(report: dict[str, Any], output: Path, week_of: str) -> Path:
    """Write a repository-safe weekly snapshot with no source event payloads."""
    payload = {
        "week_of": week_of,
        "rows": report.get("rows", []),
        "recommendations": report.get("recommendations", []),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output
