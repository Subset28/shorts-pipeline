from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

import httpx
from googleapiclient.discovery import build

REACH_REPORT_TYPE = "channel_reach_basic_a1"


def _load_job_id(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(payload.get("job_id", "")).strip() if isinstance(payload, dict) else ""


def _save_job_id(path: Path, job_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"report_type": REACH_REPORT_TYPE, "job_id": job_id}, indent=2), encoding="utf-8")


def _reach_job(service) -> str:
    response = service.jobs().list().execute()
    for job in response.get("jobs", []):
        if isinstance(job, dict) and job.get("reportTypeId") == REACH_REPORT_TYPE and job.get("id"):
            return str(job["id"])
    created = service.jobs().create(body={"reportTypeId": REACH_REPORT_TYPE, "name": "shorts-pipeline reach"}).execute()
    job_id = str(created.get("id", "")).strip()
    if not job_id:
        raise RuntimeError("YouTube Reporting API returned no reach job ID")
    return job_id


def _reports(service, job_id: str) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    page_token = ""
    while True:
        request = service.jobs().reports().list(jobId=job_id, pageSize=100, pageToken=page_token)
        response = request.execute()
        reports.extend(
            item for item in response.get("reports", []) if isinstance(item, dict) and item.get("downloadUrl")
        )
        page_token = str(response.get("nextPageToken", "")).strip()
        if not page_token:
            return reports


def _parse_reach_report(content: str, minimum_dates: dict[str, str] | None = None) -> dict[str, dict[str, Any]]:
    rows = csv.DictReader(io.StringIO(content))
    totals: dict[str, dict[str, float]] = {}
    for row in rows:
        video_id = str(row.get("video_id", "")).strip()
        if not video_id or (minimum_dates and row.get("date", "") < minimum_dates.get(video_id, "")):
            continue
        try:
            impressions = max(0.0, float(str(row.get("video_thumbnail_impressions", 0)).replace(",", "")))
            ctr = max(0.0, float(str(row.get("video_thumbnail_impressions_ctr", 0)).removesuffix("%")))
        except (TypeError, ValueError):
            continue
        if str(row.get("video_thumbnail_impressions", "")).strip().endswith("%"):  # defensive, not expected
            impressions /= 100
        if str(row.get("video_thumbnail_impressions_ctr", "")).strip().endswith("%") or ctr > 1:
            ctr /= 100
        current = totals.setdefault(video_id, {"impressions": 0.0, "ctr_weight": 0.0})
        current["impressions"] += impressions
        current["ctr_weight"] += impressions * ctr
    return {
        video_id: {
            "video_thumbnail_impressions": int(values["impressions"]),
            "video_thumbnail_impressions_ctr": values["ctr_weight"] / values["impressions"]
            if values["impressions"]
            else 0.0,
        }
        for video_id, values in totals.items()
    }


def collect_reach_metrics(
    client_secrets: Path,
    token_file: Path,
    job_path: Path,
    authorize: bool = False,
    videos: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Aggregate available daily Reach Basic reports, creating the job once."""
    from .youtube_analytics import _credentials

    credentials = _credentials(client_secrets, token_file, authorize)
    service = build("youtubereporting", "v1", credentials=credentials)
    job_id = _load_job_id(job_path)
    if not job_id:
        job_id = _reach_job(service)
        _save_job_id(job_path, job_id)
    minimum_dates = {
        str(video.get("video_id")): str(video.get("uploaded_at", ""))[:10]
        for video in videos or []
        if video.get("video_id") and video.get("uploaded_at")
    }
    aggregate: dict[str, dict[str, float]] = {}
    for report in _reports(service, job_id):
        response = httpx.get(
            report["downloadUrl"],
            headers={"Authorization": f"Bearer {credentials.token}"},
            follow_redirects=True,
            timeout=60,
        )
        response.raise_for_status()
        for video_id, metrics in _parse_reach_report(response.text, minimum_dates).items():
            current = aggregate.setdefault(video_id, {"impressions": 0.0, "ctr_weight": 0.0})
            impressions = float(metrics["video_thumbnail_impressions"])
            current["impressions"] += impressions
            current["ctr_weight"] += impressions * float(metrics["video_thumbnail_impressions_ctr"])
    return {
        video_id: {
            "video_thumbnail_impressions": int(values["impressions"]),
            "video_thumbnail_impressions_ctr": values["ctr_weight"] / values["impressions"]
            if values["impressions"]
            else 0.0,
        }
        for video_id, values in aggregate.items()
    }
