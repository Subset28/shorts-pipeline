from __future__ import annotations

import json
from pathlib import Path

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from .models import ScriptPackage

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def metadata(package: ScriptPackage) -> dict:
    return {"title": package.title, "description": package.description, "tags": package.tags, "sources": package.sources, "format_name": package.format_name}


def save_manifest(package: ScriptPackage, video: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = output_dir / "manifest.json"
    manifest.write_text(json.dumps({"video": str(video), **metadata(package)}, indent=2), encoding="utf-8")
    return manifest


def upload_youtube(video: Path, package: ScriptPackage, client_secrets: Path, token_file: Path, privacy: str) -> str:
    credentials = None
    if token_file.exists():
        credentials = Credentials.from_authorized_user_file(str(token_file), YOUTUBE_SCOPES)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), YOUTUBE_SCOPES)
            credentials = flow.run_local_server(port=0)
        token_file.write_text(credentials.to_json(), encoding="utf-8")
    youtube = build("youtube", "v3", credentials=credentials)
    request = youtube.videos().insert(
        part="snippet,status",
        body={"snippet": {"title": package.title, "description": package.description, "tags": package.tags, "categoryId": "28"}, "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}},
        media_body=MediaFileUpload(str(video), mimetype="video/mp4", resumable=True),
    )
    return request.execute()["id"]


def upload_tiktok(video: Path, package: ScriptPackage, access_token: str, privacy: str) -> str:
    if not access_token:
        raise RuntimeError("TIKTOK_ACCESS_TOKEN is not configured")
    data = video.read_bytes()
    with httpx.Client(timeout=120) as client:
        creator = client.post(
            "https://open.tiktokapis.com/v2/post/publish/creator_info/query/",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        )
        creator.raise_for_status()
        allowed_privacy = creator.json().get("data", {}).get("privacy_level_options", [])
        if privacy not in allowed_privacy:
            raise RuntimeError(f"TikTok privacy level {privacy!r} is not available for this account")
        init = client.post(
            "https://open.tiktokapis.com/v2/post/publish/video/init/",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"post_info": {"title": f"{package.title} #shorts", "privacy_level": privacy, "disable_comment": False, "disable_duet": False, "disable_stitch": False}, "source_info": {"source": "FILE_UPLOAD", "video_size": len(data), "chunk_size": len(data), "total_chunk_count": 1}},
        )
        init.raise_for_status()
        payload = init.json()["data"]
        response = client.put(payload["upload_url"], content=data, headers={"Content-Range": f"bytes 0-{len(data)-1}/{len(data)}", "Content-Type": "video/mp4"})
        response.raise_for_status()
        return payload["publish_id"]
