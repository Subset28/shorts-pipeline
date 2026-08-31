from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .analytics_schedule import _snapshots, due_videos, week_videos

ANALYTICS_SCOPE = "https://www.googleapis.com/auth/yt-analytics.readonly"
METRICS = ",".join(
    (
        "views",
        "engagedViews",
        "likes",
        "comments",
        "shares",
        "subscribersGained",
        "subscribersLost",
        "estimatedMinutesWatched",
        "averageViewDuration",
        "averageViewPercentage",
    )
)


def _credentials(client_secrets: Path, token_file: Path, authorize: bool = False) -> Credentials:
    credentials = (
        Credentials.from_authorized_user_file(str(token_file), [ANALYTICS_SCOPE]) if token_file.exists() else None
    )
    if credentials and credentials.valid:
        return credentials
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        token_file.write_text(credentials.to_json(), encoding="utf-8")
        return credentials
    if not authorize:
        raise RuntimeError("YouTube Analytics OAuth is not configured; run analytics with --authorize once")
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), [ANALYTICS_SCOPE])
    credentials = flow.run_local_server(port=0)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(credentials.to_json(), encoding="utf-8")
    return credentials


def fetch_video_metrics(
    client_secrets: Path, token_file: Path, video: dict[str, Any], authorize: bool = False, today: date | None = None
) -> dict[str, Any]:
    credentials = _credentials(client_secrets, token_file, authorize)
    service = build("youtubeAnalytics", "v2", credentials=credentials)
    uploaded = datetime.fromisoformat(video["uploaded_at"].replace("Z", "+00:00"))
    end_date = today or datetime.now(timezone.utc).date()
    response = (
        service.reports()
        .query(
            ids="channel==MINE",
            startDate=uploaded.date().isoformat(),
            endDate=end_date.isoformat(),
            metrics=METRICS,
            dimensions="video",
            filters=f"video=={video['video_id']}",
        )
        .execute()
    )
    headers = [item["name"] for item in response.get("columnHeaders", [])]
    values = response.get("rows", [[]])
    row = dict(zip(headers, values[0] if values else []))
    return {**video, "collected_at": datetime.now(timezone.utc).isoformat(), "metrics": row}


def collect_due(
    events_path: Path,
    snapshots_path: Path,
    client_secrets: Path,
    token_file: Path,
    authorize: bool = False,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    collected = [
        fetch_video_metrics(client_secrets, token_file, video, authorize)
        for video in due_videos(events_path, snapshots_path, now)
    ]
    existing = {}
    if snapshots_path.exists():
        try:
            existing = json.loads(snapshots_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
    for item in collected:
        existing.setdefault(item["video_id"], []).append(item)
    snapshots_path.parent.mkdir(parents=True, exist_ok=True)
    snapshots_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    return collected


def write_weekly_report(events_path: Path, snapshots_path: Path, output: Path, now: datetime | None = None) -> Path:
    current = {item["video_id"] for item in week_videos(events_path, now)}
    snapshots = _snapshots(snapshots_path)
    rows = [snapshot for video_id in current for snapshot in snapshots.get(video_id, [])]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "week_of": (now or datetime.now(timezone.utc)).date().isoformat(),
                "videos": sorted(current),
                "snapshots": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return output
