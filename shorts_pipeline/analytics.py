from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

ARCHIVE_FIELDS = (
    "category",
    "format_name",
    "platform",
    "variant",
    "videos",
    "views",
    "impressions",
    "avg_views",
    "ctr",
    "avg_view_duration",
    "avg_view_percentage",
    "watch_minutes",
    "engagement_rate",
)


def _metric_value(value: object) -> float:
    try:
        metric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, metric) if math.isfinite(metric) else 0.0


def _raw_number(row: dict[str, Any], name: str, *aliases: str) -> tuple[float, bool]:
    value = next((row.get(key) for key in (name, *aliases) if row.get(key) not in (None, "")), "0")
    text = str(value).strip().replace(",", "")
    return _metric_value(text.removesuffix("%")), text.endswith("%")


def _number(row: dict[str, Any], name: str, *aliases: str) -> float:
    return _raw_number(row, name, *aliases)[0]


def _rate(row: dict[str, Any], name: str, *aliases: str) -> float:
    value, has_percent_sign = _raw_number(row, name, *aliases)
    if has_percent_sign:
        return value / 100
    return value / 100 if value > 1 else value


def _metric_bucket() -> dict[str, float]:
    return {
        "videos": 0.0,
        "views": 0.0,
        "impressions": 0.0,
        "likes": 0.0,
        "comments": 0.0,
        "shares": 0.0,
        "watch_minutes": 0.0,
        "ctr_weight": 0.0,
        "ctr_base": 0.0,
        "duration_weight": 0.0,
        "duration_base": 0.0,
        "percentage_weight": 0.0,
        "percentage_base": 0.0,
    }


def _add_metrics(bucket: dict[str, float], row: dict[str, Any]) -> None:
    views = _number(row, "views")
    impressions = _number(
        row,
        "impressions",
        "thumbnail_impressions",
        "videoThumbnailImpressions",
        "video_thumbnail_impressions",
    )
    watch_minutes = _number(row, "watch_minutes", "estimated_minutes_watched", "estimatedMinutesWatched")
    bucket["views"] += views
    bucket["impressions"] += impressions
    bucket["watch_minutes"] += watch_minutes
    for field in ("likes", "comments", "shares"):
        bucket[field] += _number(row, field)
    ctr = _rate(
        row,
        "ctr",
        "impressions_ctr",
        "impressionsCtr",
        "videoThumbnailImpressionsClickRate",
        "video_thumbnail_impressions_ctr",
    )
    ctr_base = impressions or views
    bucket["ctr_weight"] += ctr * ctr_base
    bucket["ctr_base"] += ctr_base
    duration = _number(row, "avg_view_duration", "average_view_duration", "averageViewDuration")
    bucket["duration_weight"] += duration * views
    bucket["duration_base"] += views
    percentage = _number(row, "avg_view_percentage", "average_view_percentage", "averageViewPercentage")
    bucket["percentage_weight"] += percentage * views
    bucket["percentage_base"] += views


def _metric_row(bucket: dict[str, float]) -> dict[str, Any]:
    views = bucket["views"]
    return {
        "videos": int(bucket["videos"]),
        "views": int(views),
        "impressions": int(bucket["impressions"]),
        "avg_views": round(views / bucket["videos"], 2) if bucket["videos"] else 0,
        "ctr": round(bucket["ctr_weight"] / bucket["ctr_base"], 4) if bucket["ctr_base"] else 0,
        "avg_view_duration": round(bucket["duration_weight"] / bucket["duration_base"], 2)
        if bucket["duration_base"]
        else 0,
        "avg_view_percentage": round(bucket["percentage_weight"] / bucket["percentage_base"], 2)
        if bucket["percentage_base"]
        else 0,
        "watch_minutes": round(bucket["watch_minutes"], 2),
        "engagement_rate": round((bucket["likes"] + bucket["comments"] + bucket["shares"]) / views, 4) if views else 0,
    }


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

    aggregates: dict[tuple[str, str, str, int], dict[str, float]] = defaultdict(_metric_bucket)
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
            _add_metrics(bucket, row)

    rows = []
    for (category, format_name, platform, variant), values in sorted(aggregates.items()):
        rows.append(
            {
                "category": category,
                "format_name": format_name,
                "platform": platform,
                "variant": variant,
                **_metric_row(values),
            }
        )
    report = {"rows": rows, "matched_rows": sum(row["videos"] for row in rows), "unmatched_rows": unmatched}
    report["recommendations"] = tuning_recommendations(report)
    report["experiment_brief"] = build_experiment_brief(report)
    return report


def tuning_recommendations(report: dict[str, Any], min_videos: int = 2) -> list[str]:
    """Translate repeated lane performance into conservative next actions."""
    rows = [row for row in report.get("rows", []) if int(row.get("videos", 0)) >= min_videos]
    if not rows:
        return ["Collect at least two videos per lane before changing the content mix."]
    by_views = max(rows, key=lambda row: _metric_value(row.get("avg_views", 0)))
    by_engagement = max(rows, key=lambda row: _metric_value(row.get("engagement_rate", 0)))
    recommendations = [
        f"Keep testing {by_views['category']} / {by_views['format_name']}; it leads repeated lanes by average views.",
        f"Study the hook and pacing of {by_engagement['category']} / {by_engagement['format_name']}; it leads repeated lanes by engagement rate.",
    ]
    ctr_rows = [row for row in rows if _metric_value(row.get("ctr", 0)) > 0]
    if ctr_rows:
        weakest_ctr = min(ctr_rows, key=lambda row: _metric_value(row.get("ctr", 0)))
        recommendations.append(
            f"Revise the thumbnail/title promise for {weakest_ctr['category']} / {weakest_ctr['format_name']}; it has the weakest measured CTR."
        )
    retention_rows = [row for row in rows if _metric_value(row.get("avg_view_percentage", 0)) > 0]
    if retention_rows:
        strongest_retention = max(retention_rows, key=lambda row: _metric_value(row.get("avg_view_percentage", 0)))
        recommendations.append(
            f"Reuse the opening and pacing pattern from {strongest_retention['category']} / {strongest_retention['format_name']}; it leads measured retention."
        )
    if by_views["category"] != by_engagement["category"] or by_views["format_name"] != by_engagement["format_name"]:
        recommendations.append(
            "Views and engagement favor different lanes; keep both in rotation instead of optimizing for one metric."
        )
    return recommendations


def _lane(row: dict[str, Any]) -> str:
    return f"{row.get('category', 'unknown')} / {row.get('format_name', 'unknown')}"


def _comparison_key(row: dict[str, Any]) -> tuple[str, str, int]:
    return (_lane(row), str(row.get("platform", "unknown")), int(row.get("variant", 0)))


def _experiment_row(row: dict[str, Any], metric: str, duplicate_lanes: set[str]) -> dict[str, Any]:
    lane = _lane(row)
    if lane in duplicate_lanes:
        lane = f"{lane} / {row.get('platform', 'unknown')} / variant {int(row.get('variant', 0))}"
    return {
        "lane": lane,
        "category": str(row.get("category", "unknown")),
        "format_name": str(row.get("format_name", "unknown")),
        "platform": str(row.get("platform", "unknown")),
        "variant": int(row.get("variant", 0)),
        metric: row.get(metric, 0),
        "videos": int(row.get("videos", 0)),
    }


def build_experiment_brief(report: dict[str, Any], min_videos: int = 2) -> dict[str, Any]:
    """Turn repeated lane metrics into bounded, testable editorial changes."""
    rows = [row for row in report.get("rows", []) if isinstance(row, dict) and int(row.get("videos", 0)) >= min_videos]
    comparison_keys = {_comparison_key(row) for row in rows}
    brief: dict[str, Any] = {
        "status": "ready" if len(comparison_keys) >= 2 else "insufficient_sample",
        "min_videos": min_videos,
        "eligible_lanes": len(comparison_keys),
        "experiments": [],
    }
    if len(comparison_keys) < 2:
        return brief
    lane_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        lane_counts[_lane(row)] += 1
    duplicate_lanes = {lane for lane, count in lane_counts.items() if count > 1}

    comparisons = (
        (
            "packaging",
            "ctr",
            "Rewrite the next low-CTR title and thumbnail around one clear technical promise, then compare it with the stronger lane.",
        ),
        (
            "opening_and_pacing",
            "avg_view_percentage",
            "Use the stronger lane's first-second hook and information pacing as the control for the next treatment.",
        ),
    )
    for area, metric, change in comparisons:
        measured = [row for row in rows if _metric_value(row.get(metric, 0)) > 0]
        if len(measured) < 2:
            continue
        baseline = min(measured, key=lambda row: _metric_value(row.get(metric, 0)))
        reference = max(measured, key=lambda row: _metric_value(row.get(metric, 0)))
        if _comparison_key(baseline) == _comparison_key(reference):
            continue
        brief["experiments"].append(
            {
                "area": area,
                "metric": metric,
                "baseline": _experiment_row(baseline, metric, duplicate_lanes),
                "reference": _experiment_row(reference, metric, duplicate_lanes),
                "change": change,
            }
        )
    return brief


def write_report(report: dict[str, Any], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return output


def archive_report(report: dict[str, Any], output: Path, week_of: str) -> Path:
    """Write a repository-safe weekly snapshot with no source event payloads."""
    rows = [
        {field: row[field] for field in ARCHIVE_FIELDS if field in row}
        for row in report.get("rows", [])
        if isinstance(row, dict)
    ]
    payload = {
        "week_of": week_of,
        "rows": rows,
        "recommendations": [str(item) for item in report.get("recommendations", []) if str(item).strip()],
        "experiment_brief": report.get("experiment_brief", build_experiment_brief(report)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output


def tuning_log(report: dict[str, Any], week_of: str) -> str:
    """Render a repository-safe record of measured results and next tests."""
    rows = [row for row in report.get("rows", []) if isinstance(row, dict)]
    lines = [f"# Analytics tuning log — {week_of}", "", "Generated from aggregate platform analytics.", ""]
    if rows:
        lines.extend(
            [
                "## Measured lanes",
                "",
                "| Lane | Videos | Views | CTR | Retention | Watch minutes | Engagement |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in rows:
            lines.append(
                "| {lane} | {videos} | {views} | {ctr:.2%} | {retention:.1f}% | {watch:.2f} | {engagement:.2%} |".format(
                    lane=_lane(row),
                    videos=int(row.get("videos", 0)),
                    views=int(_metric_value(row.get("views", 0))),
                    ctr=_metric_value(row.get("ctr", 0)),
                    retention=_metric_value(row.get("avg_view_percentage", 0)),
                    watch=_metric_value(row.get("watch_minutes", 0)),
                    engagement=_metric_value(row.get("engagement_rate", 0)),
                )
            )
    else:
        lines.extend(["## Evidence", "", "No matched analytics rows were available."])
    lines.extend(["", "## Recommendations", ""])
    recommendations = [str(item).strip() for item in report.get("recommendations", []) if str(item).strip()]
    lines.extend(f"- {item}" for item in recommendations or ["Collect more data before changing the content mix."])
    lines.extend(
        [
            "",
            "## Experiment brief",
            "",
            "```json",
            json.dumps(report.get("experiment_brief", {}), indent=2),
            "```",
            "",
            "Treat these recommendations as the next test plan; do not infer causality from lane aggregates alone.",
            "",
        ]
    )
    return "\n".join(lines)


def write_tuning_log(report: dict[str, Any], output: Path, week_of: str) -> Path:
    """Write the repository-safe weekly tuning log."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(tuning_log(report, week_of), encoding="utf-8")
    return output


def build_youtube_report(weekly: dict[str, Any]) -> dict[str, Any]:
    """Aggregate the latest checkpoint for each video into editorial lanes."""
    latest: dict[str, dict[str, Any]] = {}
    for snapshot in weekly.get("snapshots", []):
        video_id = str(snapshot.get("video_id", "")).strip()
        if not video_id:
            continue
        current = latest.get(video_id)
        if not current or str(snapshot.get("collected_at", "")) > str(current.get("collected_at", "")):
            latest[video_id] = snapshot
    buckets: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for snapshot in latest.values():
        buckets[
            (
                str(snapshot.get("category", "unknown")),
                str(snapshot.get("format_name", "unknown")),
                max(0, int(snapshot.get("variant", 0) or 0)),
            )
        ].append(snapshot)
    rows = []
    for (category, format_name, variant), snapshots in sorted(buckets.items()):
        bucket = _metric_bucket()
        for snapshot in snapshots:
            bucket["videos"] += 1
            _add_metrics(bucket, snapshot.get("metrics", {}))
        rows.append(
            {
                "category": category,
                "format_name": format_name,
                "platform": "youtube",
                "variant": variant,
                **_metric_row(bucket),
            }
        )
    report = {"rows": rows, "matched_rows": len(latest), "unmatched_rows": 0}
    report["recommendations"] = tuning_recommendations(report)
    report["experiment_brief"] = build_experiment_brief(report)
    return report
