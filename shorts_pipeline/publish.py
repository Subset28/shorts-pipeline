from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from .models import ScriptPackage
from .quality import assess_render

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
_TAG_STOPWORDS = {"about", "after", "because", "from", "into", "that", "this", "what", "when", "with"}
_CATEGORY_TAGS = {
    "AI": ("artificial intelligence", "machine learning", "AI news"),
    "AI News": ("artificial intelligence", "machine learning", "AI news"),
    "ML": ("machine learning", "ML news", "AI research"),
    "CS": ("computer science", "software engineering", "programming"),
    "Cyber": ("cybersecurity", "information security", "infosec"),
    "Aerospace": ("aerospace engineering", "space technology", "engineering"),
}


def youtube_status(privacy: str, publish_at: str | None = None) -> dict:
    if not publish_at:
        return {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}
    try:
        scheduled = datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("publish_at must be RFC 3339 datetime") from exc
    if scheduled.tzinfo is None or scheduled <= datetime.now(timezone.utc):
        raise ValueError("publish_at must be a future timezone-aware datetime")
    return {"privacyStatus": "private", "publishAt": publish_at, "selfDeclaredMadeForKids": False}


def _safe_title(value: str) -> str:
    title = " ".join(value.split()).strip()
    if len(title) <= 100:
        return title
    prefix = title[:97].rsplit(" ", 1)[0].rstrip(" ,:;-—")
    return (prefix or title[:97]) + "..."


def _seo_tags(package: ScriptPackage) -> list[str]:
    candidates = [*package.tags, *_CATEGORY_TAGS.get(package.category, ()), package.category]
    candidates.extend(
        term
        for term in re.findall(r"[A-Za-z0-9][A-Za-z0-9+./-]{2,}", package.title)
        if term.casefold() not in _TAG_STOPWORDS
    )
    tags: list[str] = []
    used: set[str] = set()
    length = 0
    for candidate in candidates:
        tag = re.sub(r"\s+", " ", str(candidate)).strip(" #,\n\r\t")
        key = tag.casefold()
        if not tag or key in used or len(tag) > 100:
            continue
        added = len(tag) + (1 if tags else 0)
        if length + added > 450:
            break
        tags.append(tag)
        used.add(key)
        length += added
    return tags


def _safe_description(package: ScriptPackage, tags: list[str]) -> str:
    description = unicodedata.normalize("NFKD", package.description).encode("ascii", "ignore").decode("ascii")
    description = "".join(
        " " if unicodedata.category(char) in {"Zl", "Zp"} else char
        for char in description
        if unicodedata.category(char)[0] != "C" or char in {"\n", "\r", "\t"}
    )
    description = description.translate(str.maketrans("", "", ">*<"))
    paragraphs = [" ".join(part.split()) for part in re.split(r"\n\s*\n", description) if part.strip()]
    title = _safe_title(package.title)
    if not paragraphs or not paragraphs[0].casefold().startswith(title.casefold()):
        paragraphs.insert(0, title)
    if tags:
        paragraphs.append(f"Topics: {', '.join(tags[:8])}")
    return "\n\n".join(paragraphs)[:5000].rstrip()


def metadata(package: ScriptPackage) -> dict:
    title = _safe_title(package.title)
    tags = _seo_tags(package)
    return {
        "title": title,
        "description": _safe_description(package, tags),
        "tags": tags,
        "sources": package.sources,
        "format_name": package.format_name,
        "category": package.category,
        "variant": package.variant,
    }


def save_manifest(
    package: ScriptPackage,
    video: Path,
    output_dir: Path,
    background: Path | None = None,
    background_sources: list[Path] | None = None,
    audio: Path | None = None,
    captions: Path | None = None,
    thumbnail: Path | None = None,
    background_looped: bool = False,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = output_dir / "manifest.json"
    payload = {"video": str(video), **metadata(package)}
    if audio:
        payload["audio"] = str(audio)
    if captions:
        payload["captions"] = str(captions)
    if thumbnail:
        payload["thumbnail"] = str(thumbnail)
    if background:
        payload["background"] = str(background)
    if background_sources:
        payload["background_sources"] = [str(path) for path in background_sources]
    payload["quality"] = assess_render(video, audio, captions, background, background_looped=background_looped)
    manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest


def quality_gate(manifest: Path) -> dict:
    """Reject uploads whose deterministic render evidence did not pass."""
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        quality = payload["quality"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Quality report unavailable: {manifest}") from exc
    if not isinstance(quality, dict) or quality.get("passed") is not True:
        issues = quality.get("issues", []) if isinstance(quality, dict) else ["quality_report_invalid"]
        raise RuntimeError(f"Render quality gate failed: {', '.join(str(item) for item in issues) or 'unknown issue'}")
    return quality


def metadata_quality_gate(manifest: Path) -> dict[str, object]:
    """Validate source-backed packaging before a platform upload."""
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Metadata report unavailable: {manifest}") from exc
    issues: list[str] = []
    sources = payload.get("sources")
    title = payload.get("title")
    description = payload.get("description")
    tags = payload.get("tags")
    category = payload.get("category")
    format_name = payload.get("format_name")
    if not isinstance(sources, list) or not any(isinstance(url, str) and url.strip() for url in sources):
        issues.append("sources_missing")
    if not isinstance(title, str) or not title.strip() or len(title) > 100:
        issues.append("title_invalid")
    if not isinstance(description, str) or not description.strip():
        issues.append("description_missing")
    elif isinstance(sources, list) and any(isinstance(url, str) and url not in description for url in sources if url):
        issues.append("description_missing_source")
    if not isinstance(tags, list) or not any(str(tag).strip() for tag in tags):
        issues.append("tags_missing")
    if not isinstance(category, str) or not category.strip():
        issues.append("category_missing")
    if not isinstance(format_name, str) or not format_name.strip():
        issues.append("format_missing")
    if not isinstance(payload.get("captions"), str) or not payload["captions"].strip():
        issues.append("captions_missing")
    if format_name != "longform_explainer" and not isinstance(payload.get("background"), str):
        issues.append("background_missing")
    return {"passed": not issues, "issues": issues}


def enforce_metadata_quality_gate(manifest: Path) -> dict[str, object]:
    result = metadata_quality_gate(manifest)
    if result["passed"] is not True:
        issues = ", ".join(str(issue) for issue in result["issues"])
        raise RuntimeError(f"Content metadata gate failed: {issues or 'unknown issue'}")
    return result


def _youtube_credentials(client_secrets: Path, token_file: Path) -> Credentials:
    credentials = None
    if token_file.exists():
        credentials = Credentials.from_authorized_user_file(str(token_file), YOUTUBE_SCOPES)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), YOUTUBE_SCOPES)
            credentials = flow.run_local_server(port=0)
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(credentials.to_json(), encoding="utf-8")
    return credentials


def _set_youtube_thumbnail(youtube, video_id: str, thumbnail: Path) -> bool:
    try:
        if not thumbnail.exists() or not thumbnail.stat().st_size:
            return False
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumbnail), mimetype="image/jpeg"),
        ).execute()
    except Exception:
        print("YouTube thumbnail upload failed; it will be retried later")
        return False
    return True


def set_youtube_thumbnail(
    video_id: str,
    thumbnail: Path,
    client_secrets: Path,
    token_file: Path,
) -> bool:
    """Retry thumbnail setup without uploading the video again."""
    try:
        youtube = build("youtube", "v3", credentials=_youtube_credentials(client_secrets, token_file))
    except Exception:
        print("YouTube thumbnail authorization failed; it will be retried later")
        return False
    return _set_youtube_thumbnail(youtube, video_id, thumbnail)


def upload_youtube(
    video: Path,
    package: ScriptPackage,
    client_secrets: Path,
    token_file: Path,
    privacy: str,
    publish_at: str | None = None,
) -> str:
    credentials = _youtube_credentials(client_secrets, token_file)
    youtube = build("youtube", "v3", credentials=credentials)
    safe_metadata = metadata(package)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": safe_metadata["title"],
                "description": safe_metadata["description"],
                "tags": safe_metadata["tags"],
                "categoryId": "28",
            },
            "status": youtube_status(privacy, publish_at),
        },
        media_body=MediaFileUpload(str(video), mimetype="video/mp4", resumable=True),
    )
    video_id = request.execute()["id"]
    return video_id


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
            json={
                "post_info": {
                    "title": f"{package.title} #shorts",
                    "privacy_level": privacy,
                    "disable_comment": False,
                    "disable_duet": False,
                    "disable_stitch": False,
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": len(data),
                    "chunk_size": len(data),
                    "total_chunk_count": 1,
                },
            },
        )
        init.raise_for_status()
        payload = init.json()["data"]
        response = client.put(
            payload["upload_url"],
            content=data,
            headers={"Content-Range": f"bytes 0-{len(data) - 1}/{len(data)}", "Content-Type": "video/mp4"},
        )
        response.raise_for_status()
        return payload["publish_id"]


def fetch_tiktok_status(access_token: str, publish_id: str) -> str:
    """Fetch the asynchronous TikTok post state for a previously uploaded ID."""
    if not access_token:
        raise RuntimeError("TIKTOK_ACCESS_TOKEN is not configured")
    with httpx.Client(timeout=30) as client:
        response = client.post(
            "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"publish_id": publish_id},
        )
        response.raise_for_status()
        payload = response.json()
    error = payload.get("error", {})
    if error.get("code") not in (None, "ok"):
        raise RuntimeError(f"TikTok status check failed: {error.get('code')}: {error.get('message', '')}".strip())
    status = payload.get("data", {}).get("status")
    if not status:
        raise RuntimeError("TikTok status response did not include a status")
    return str(status)
