from __future__ import annotations

import argparse
import json
import math
import time
import traceback
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

from .analytics import archive_report, build_report, build_youtube_report, write_report
from .asset_library import sync_backgrounds
from .captions import create_captions
from .config import load_settings
from .content_calendar import build_weekly_plan
from .editorial import build_research_week
from .history import load_publish_state, load_seen, mark_seen, save_publish_state
from .llm import create_package
from .longform import create_longform_package, render_longform_video
from .media import build_background_reel, ensure_background_video, select_backgrounds, split_authorized_clip
from .publish import (
    enforce_metadata_quality_gate,
    fetch_tiktok_status,
    quality_gate,
    save_manifest,
    set_youtube_thumbnail,
    upload_tiktok,
    upload_youtube,
)
from .reddit import discover_reddit_topics, load_approved_reddit_topics
from .render import render_thumbnail, render_video
from .sources import discover_topics
from .telemetry import record_event
from .tts import synthesize, tts_configuration_issues
from .youtube_analytics import collect_due, write_weekly_report

YOUTUBE_QUOTA_RETRY_HOURS = 24.0
REDDIT_URL_PREFIXES = ("https://www.reddit.com/", "https://old.reddit.com/", "https://redd.it/")


def _interval_seconds(interval_hours: float) -> float:
    if not math.isfinite(interval_hours) or interval_hours <= 0:
        raise ValueError("interval_hours must be finite and greater than zero")
    return max(interval_hours, 0.25) * 3600


def _is_reddit_url(source_url: str) -> bool:
    return source_url.lower().startswith(REDDIT_URL_PREFIXES)


def _discover_topics(settings, limit: int, reddit_only: bool = False, private_drafts: bool = False):
    if reddit_only:
        if private_drafts:
            topics = discover_reddit_topics(
                settings.reddit_subreddits,
                settings.reddit_client_id,
                settings.reddit_client_secret,
                settings.reddit_user_agent,
                limit,
            )
            # Private review drafts may use discovered posts in memory, while
            # normal publishing continues to require explicit reuse approval.
            topics = [replace(topic, sources=(replace(topic.sources[0], reuse_permission=True),)) for topic in topics]
            return topics
        return load_approved_reddit_topics(settings.reddit_approved_file)
    topics = discover_topics(limit)
    topics.extend(load_approved_reddit_topics(settings.reddit_approved_file))
    return topics


def _next_batch_dir(output_dir: Path) -> Path:
    """Allocate a non-destructive batch directory for experiment history."""
    output_dir.mkdir(parents=True, exist_ok=True)
    index = 1
    while True:
        candidate = output_dir / f"batch-{index:02d}"
        if not candidate.exists():
            return candidate
        index += 1


def _publish_state_key(source_url: str, variant: int) -> str:
    """Keep legacy variant-zero state compatible while isolating experiments."""
    return source_url if variant == 0 else f"{source_url}#variant={variant}"


def _select_topic(topics, seen: set[str], reddit_only: bool = False):
    unseen = [item for item in topics if item.sources[0].url not in seen]
    if unseen:
        return max(unseen, key=lambda item: item.score)
    if reddit_only:
        raise RuntimeError("No unseen Reddit topics available; waiting for new stories")
    return topics[0]


def _should_pause_after_success(reddit_only: bool, private_drafts: bool) -> bool:
    return not reddit_only or private_drafts


def _should_upload_tiktok(private_drafts: bool, youtube_only: bool) -> bool:
    return not private_drafts and not youtube_only


def _select_backgrounds_for_topic(
    settings,
    directory: Path,
    key: str,
    category: str | None,
    provenance: str | None,
    limit: int = 3,
):
    return select_backgrounds(
        directory,
        key,
        limit=limit,
        category=category,
        provenance=provenance,
        manifest=settings.background_manifest,
    )


def _build_background_reel_for_render(sources: list[Path], output: Path, source_url: str, variant: int) -> Path | None:
    """Tie reel motion variation to the source treatment being rendered."""
    return build_background_reel(
        sources,
        output,
        variation_key=f"{source_url}|variant={max(0, variant)}",
    )


def _background_for_render(
    settings, sources: list[Path], fallback: Path | None, output: Path, source_url: str, variant: int
):
    """Use one moving source by default; opt into the expensive reel graph."""
    if not sources:
        return fallback
    if not getattr(settings, "background_reel_enabled", False):
        return sources[0]
    return _build_background_reel_for_render(sources, output, source_url, variant)


def is_youtube_upload_limit_error(error: Exception) -> bool:
    return "uploadLimitExceeded" in str(error)


def _has_unseen_reddit_topic(settings) -> bool:
    topics = load_approved_reddit_topics(settings.reddit_approved_file)
    seen = load_seen(settings.data_dir / "seen_sources.json")
    return any(topic.sources[0].url not in seen for topic in topics)


def run_preflight(reddit_only: bool = False, private_drafts: bool = False, youtube_only: bool = False) -> int:
    """Validate local production inputs without TTS, rendering, or uploads."""
    settings = load_settings()
    issues: list[str] = []
    if reddit_only:
        if not settings.reddit_approved_file.exists():
            issues.append("reddit_approved_file_missing")
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            issues.append("reddit_credentials_missing")
    if not settings.reddit_background_dir.exists() or not any(settings.reddit_background_dir.iterdir()):
        issues.append("reddit_backgrounds_missing")
    if not settings.youtube_client_secrets.exists():
        issues.append("youtube_client_secrets_missing")
    if not settings.youtube_token_file.exists():
        issues.append("youtube_token_missing")
    issues.extend(tts_configuration_issues(settings))
    if issues:
        raise RuntimeError(f"Preflight failed: {', '.join(issues)}")
    privacy = "private" if private_drafts else settings.youtube_privacy_status
    destination = "YouTube only" if youtube_only else "configured platforms"
    print(f"Preflight passed: privacy={privacy}, destination={destination}; no media or uploads started")
    return 0


def run_worker(
    force_dry_run: bool = False,
    reddit_only: bool = False,
    private_drafts: bool = False,
    youtube_only: bool = False,
    interval_hours: float = 6.0,
) -> int:
    retry_seconds = _interval_seconds(interval_hours)
    quota_retry_seconds = max(YOUTUBE_QUOTA_RETRY_HOURS, interval_hours) * 3600
    while True:
        if reddit_only and not private_drafts and not _has_unseen_reddit_topic(load_settings()):
            print("Reddit queue complete")
            return 0
        try:
            run(
                force_dry_run=force_dry_run,
                reddit_only=reddit_only,
                private_drafts=private_drafts,
                youtube_only=youtube_only,
            )
        except Exception as exc:
            print(f"Pipeline run failed; will retry: {exc}")
            traceback.print_exc()
            delay = quota_retry_seconds if is_youtube_upload_limit_error(exc) else retry_seconds
            print(f"Retrying in {delay / 3600:g} hours", flush=True)
            time.sleep(delay)
        else:
            if _should_pause_after_success(reddit_only, private_drafts):
                time.sleep(retry_seconds)


def run(
    force_dry_run: bool = False,
    topic_override=None,
    output_dir_override: Path | None = None,
    variant: int = 0,
    reddit_only: bool = False,
    private_drafts: bool = False,
    youtube_only: bool = False,
    publish_at: str | None = None,
    editorial_brief: dict[str, Any] | None = None,
) -> int:
    settings = load_settings()
    dry_run = force_dry_run or (settings.dry_run and not private_drafts)
    topics = (
        [topic_override]
        if topic_override
        else _discover_topics(settings, settings.topic_limit, reddit_only, private_drafts)
    )
    if not topics:
        raise RuntimeError("No source-backed topics were discovered")
    seen_path = settings.data_dir / "seen_sources.json"
    publish_path = settings.data_dir / "publish_state.json"
    events_path = settings.data_dir / "events.jsonl"
    seen = load_seen(seen_path)
    topic = _select_topic(topics, seen, reddit_only=reddit_only)
    source_url = topic.sources[0].url
    output_dir = output_dir_override or settings.output_dir
    package = create_package(topic, settings.openai_api_key, settings.openai_model, variant, editorial_brief)
    state_key = _publish_state_key(source_url, package.variant)
    published = load_publish_state(publish_path).get(state_key, {})
    audio = synthesize(package.narration, settings, output_dir / "narration.mp3")
    if not audio or not audio.exists() or audio.stat().st_size == 0:
        raise RuntimeError("TTS produced no audio; refusing to create a silent short")
    captions = (
        create_captions(package.narration, audio, output_dir / "captions.srt", settings.caption_model)
        if settings.captions_enabled
        else None
    )
    fallback_background = ensure_background_video(settings.background_video_url, settings.background_video)
    background_dir = (
        settings.reddit_background_dir
        if package.format_name == "reddit_story" and settings.reddit_background_dir.exists()
        else settings.background_dir
    )
    background_sources = _select_backgrounds_for_topic(
        settings,
        background_dir,
        f"{source_url}|{package.variant}",
        category=package.category,
        provenance=topic.sources[0].community,
    )
    background = _background_for_render(
        settings,
        background_sources,
        fallback_background,
        output_dir / "background-reel.mp4",
        source_url,
        package.variant,
    )
    video = render_video(package, output_dir, audio, captions, background)
    thumbnail = render_thumbnail(package, output_dir / "thumbnail.jpg")
    manifest = save_manifest(
        package, video, output_dir, background, background_sources, audio, captions, thumbnail, background_looped=True
    )
    record_event(
        events_path,
        "draft_created",
        source_url=source_url,
        category=package.category,
        format_name=package.format_name,
        variant=package.variant,
        title=package.title,
        video=str(video),
        dry_run=dry_run,
    )
    print(f"Created {manifest}")
    if dry_run:
        print("Dry run: YouTube and TikTok uploads skipped")
        return 0
    quality_gate(manifest)
    enforce_metadata_quality_gate(manifest)
    privacy = "private" if private_drafts else settings.youtube_privacy_status
    youtube_id = published.get("youtube_id")
    if youtube_id:
        thumbnail_ready = set_youtube_thumbnail(
            youtube_id,
            thumbnail,
            settings.youtube_client_secrets,
            settings.youtube_token_file,
        )
    else:
        youtube_id = upload_youtube(
            video,
            package,
            settings.youtube_client_secrets,
            settings.youtube_token_file,
            privacy,
            publish_at,
        )
        thumbnail_ready = set_youtube_thumbnail(
            youtube_id,
            thumbnail,
            settings.youtube_client_secrets,
            settings.youtube_token_file,
        )
    save_publish_state(publish_path, state_key, youtube_id=youtube_id)
    record_event(
        events_path,
        "youtube_scheduled" if publish_at else "youtube_published",
        source_url=source_url,
        category=package.category,
        format_name=package.format_name,
        variant=package.variant,
        platform_id=youtube_id,
        publish_at=publish_at,
    )
    if not thumbnail_ready:
        print("Thumbnail is pending; source will be retried later")
        return 0
    if private_drafts:
        mark_seen(seen_path, source_url)
        print(f"Uploaded private YouTube draft: {youtube_id}")
        return 0
    if not _should_upload_tiktok(private_drafts, youtube_only):
        if private_drafts:
            return 0
        mark_seen(seen_path, source_url)
        print(f"Uploaded YouTube only: {youtube_id}")
        return 0
    tiktok_id = published.get("tiktok_id")
    if not tiktok_id:
        tiktok_id = upload_tiktok(video, package, settings.tiktok_access_token, settings.tiktok_privacy_level)
        save_publish_state(publish_path, state_key, tiktok_id=tiktok_id, tiktok_status="PROCESSING_UPLOAD")
        record_event(
            events_path,
            "tiktok_upload_started",
            source_url=source_url,
            category=package.category,
            format_name=package.format_name,
            variant=package.variant,
            platform_id=tiktok_id,
        )
        print(f"Uploaded to TikTok; processing status pending: {tiktok_id}")
        return 0
    tiktok_status = fetch_tiktok_status(settings.tiktok_access_token, tiktok_id)
    if tiktok_status == "FAILED":
        raise RuntimeError(f"TikTok rejected publish {tiktok_id}")
    if tiktok_status != "PUBLISH_COMPLETE":
        save_publish_state(publish_path, state_key, tiktok_status=tiktok_status)
        record_event(
            events_path,
            "tiktok_processing",
            source_url=source_url,
            category=package.category,
            format_name=package.format_name,
            variant=package.variant,
            platform_id=tiktok_id,
            status=tiktok_status,
        )
        print(f"TikTok still processing ({tiktok_status}); will check again next run")
        return 0
    save_publish_state(publish_path, state_key, tiktok_status=tiktok_status)
    record_event(
        events_path,
        "tiktok_published",
        source_url=source_url,
        category=package.category,
        format_name=package.format_name,
        variant=package.variant,
        platform_id=tiktok_id,
    )
    mark_seen(seen_path, source_url)
    print(f"Published YouTube={youtube_id} TikTok={tiktok_id}")
    return 0


def run_batch(count: int, force_dry_run: bool = False, variants: int = 1) -> int:
    settings = load_settings()
    topics = _discover_topics(settings, max(settings.topic_limit, count))
    if not topics:
        raise RuntimeError(
            "No source-backed topics were discovered; RSS feeds may be unavailable. Check network access and feed health before retrying."
        )
    seen = load_seen(settings.data_dir / "seen_sources.json")
    unique = []
    selected_urls = set()
    for topic in topics:
        source_url = topic.sources[0].url
        if source_url not in seen and source_url not in selected_urls:
            unique.append(topic)
            selected_urls.add(source_url)
        if len(unique) == count:
            break
    if len(unique) < count:
        raise RuntimeError(f"Only {len(unique)} unseen topics available; requested {count}")
    batch_dir = _next_batch_dir(settings.output_dir)
    for index, topic in enumerate(unique, 1):
        for variant in range(max(1, variants)):
            suffix = f"-v{variant + 1:02d}" if variants > 1 else ""
            run(
                force_dry_run=force_dry_run,
                topic_override=topic,
                output_dir_override=batch_dir / f"item-{index:02d}{suffix}",
                variant=variant,
            )
    return 0


def run_schedule(schedule_path: Path, force_dry_run: bool = False) -> int:
    records = json.loads(schedule_path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Schedule file must contain a list")
    settings = load_settings()
    topics = {topic.sources[0].url: topic for topic in load_approved_reddit_topics(settings.reddit_approved_file)}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Schedule entries must be objects")
        source_url = str(record.get("source_url", "")).strip()
        publish_at = str(record.get("publish_at", "")).strip()
        topic = topics.get(source_url)
        if not topic:
            raise ValueError(f"Schedule source is not approved: {source_url}")
        run(force_dry_run=force_dry_run, topic_override=topic, youtube_only=True, publish_at=publish_at)
    return 0


def run_longform(
    source_url: str | None,
    output_dir: Path,
    editorial_brief: dict[str, Any] | None = None,
    upload_private: bool = False,
    publish_at: str | None = None,
) -> int:
    settings = load_settings()
    topics = discover_topics(max(settings.topic_limit, 10))
    topics.extend(load_approved_reddit_topics(settings.reddit_approved_file))
    topic = next((item for item in topics if not source_url or item.sources[0].url == source_url), None)
    if not topic:
        raise ValueError("No source-backed topic matched the requested long-form topic")
    package = create_longform_package(topic, editorial_brief=editorial_brief)
    audio = synthesize(package.narration, settings, output_dir / "narration.mp3")
    if not audio or not audio.exists() or audio.stat().st_size == 0:
        raise RuntimeError("TTS produced no audio for long-form video")
    captions = (
        create_captions(package.narration, audio, output_dir / "captions.srt", settings.caption_model)
        if settings.captions_enabled
        else None
    )
    background = _select_backgrounds_for_topic(
        settings,
        settings.background_dir,
        topic.sources[0].url,
        limit=1,
        category=topic.category,
        provenance=topic.sources[0].community,
    )
    video = render_longform_video(package, output_dir, audio, captions, background[0] if background else None)
    thumbnail = render_thumbnail(package, output_dir / "thumbnail.jpg")
    save_manifest(
        package,
        video,
        output_dir,
        background[0] if background else None,
        background,
        audio,
        captions,
        thumbnail,
    )
    print(f"Created {video}")
    if not upload_private:
        return 0
    quality_gate(output_dir / "manifest.json")
    enforce_metadata_quality_gate(output_dir / "manifest.json")
    publish_path = settings.data_dir / "publish_state.json"
    events_path = settings.data_dir / "events.jsonl"
    published = load_publish_state(publish_path).get(source_url or topic.sources[0].url, {})
    youtube_id = published.get("youtube_id")
    if youtube_id:
        thumbnail_ready = set_youtube_thumbnail(
            youtube_id, thumbnail, settings.youtube_client_secrets, settings.youtube_token_file
        )
    else:
        youtube_id = upload_youtube(
            video,
            package,
            settings.youtube_client_secrets,
            settings.youtube_token_file,
            "private",
            publish_at,
        )
        thumbnail_ready = set_youtube_thumbnail(
            youtube_id, thumbnail, settings.youtube_client_secrets, settings.youtube_token_file
        )
    state_key = source_url or topic.sources[0].url
    save_publish_state(publish_path, state_key, youtube_id=youtube_id)
    record_event(
        events_path,
        "youtube_scheduled" if publish_at else "youtube_published",
        source_url=state_key,
        category=package.category,
        format_name=package.format_name,
        variant=package.variant,
        platform_id=youtube_id,
        publish_at=publish_at,
    )
    if not thumbnail_ready:
        print("Long-form thumbnail is pending; source will be retried later")
        return 0
    mark_seen(settings.data_dir / "seen_sources.json", state_key)
    print(f"Uploaded private long-form YouTube draft: {youtube_id}")
    return 0


def run_weekly_plan(
    week_of: str,
    shorts_count: int,
    output: Path,
    include_longform: bool = True,
    analytics_path: Path | None = None,
    research_path: Path | None = None,
) -> int:
    try:
        week_start = date.fromisoformat(week_of)
    except ValueError as exc:
        raise ValueError("week_of must be an ISO date") from exc
    settings = load_settings()
    brief: dict[str, Any] | None = None
    report_path = analytics_path or getattr(settings, "data_dir", Path("data")) / "analytics_report.json"
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if isinstance(report, dict) and isinstance(report.get("experiment_brief"), dict):
                brief = report["experiment_brief"]
        except (OSError, json.JSONDecodeError) as exc:
            if analytics_path is not None:
                raise ValueError(f"Could not read analytics report: {analytics_path}") from exc
    elif analytics_path is not None:
        raise ValueError(f"Analytics report does not exist: {analytics_path}")
    topics = discover_topics(max(settings.topic_limit, shorts_count + 3))
    approved_topics = load_approved_reddit_topics(settings.reddit_approved_file)
    topics.extend(approved_topics)
    entries = build_weekly_plan(topics, week_start, shorts_count, include_longform, topics, brief)
    if not entries:
        raise RuntimeError("No source-backed topics were available for the weekly plan")
    editorial_by_url: dict[str, Any] = {}
    if research_path is not None:
        try:
            research = json.loads(research_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not read research slate: {research_path}") from exc
        if not isinstance(research, dict):
            raise ValueError("Research slate must be a JSON object")
        research_shorts = research.get("shorts", [])
        research_longform = research.get("longform", [])
        if not isinstance(research_shorts, list) or not isinstance(research_longform, list):
            raise ValueError("Research slate shorts and longform fields must be lists")
        for item in research_shorts + research_longform:
            if not isinstance(item, dict) or not isinstance(item.get("source"), dict):
                raise ValueError("Each research entry must contain a source URL")
            url = item["source"].get("url")
            if not isinstance(url, str) or not url.strip():
                raise ValueError("Each research entry must contain a source URL")
            editorial_by_url[url.strip()] = item
        if research.get("privacy_status") != "private":
            raise ValueError("Research slate must declare private privacy_status")
    for entry in entries:
        brief_item = editorial_by_url.get(entry["source_url"])
        if brief_item is not None:
            entry["editorial_brief"] = brief_item
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {"week_of": week_of, "privacy_status": "private", "entries": entries, "experiment_brief": brief}, indent=2
        ),
        encoding="utf-8",
    )
    print(f"Wrote {output} ({len(entries)} entries)")
    return 0


def run_research_week(
    week_of: str,
    shorts_count: int,
    output: Path,
    include_longform: bool = True,
    analytics_path: Path | None = None,
) -> int:
    try:
        week_start = date.fromisoformat(week_of)
    except ValueError as exc:
        raise ValueError("week_of must be an ISO date") from exc
    settings = load_settings()
    topics = discover_topics(max(settings.topic_limit, shorts_count + 3))
    topics.extend(load_approved_reddit_topics(settings.reddit_approved_file))
    experiment_brief = None
    report_path = analytics_path or getattr(settings, "data_dir", Path("data")) / "analytics_report.json"
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            if analytics_path is not None:
                raise ValueError(f"Could not read analytics report: {analytics_path}") from exc
        else:
            if isinstance(report, dict) and isinstance(report.get("experiment_brief"), dict):
                experiment_brief = report["experiment_brief"]
    elif analytics_path is not None:
        raise ValueError(f"Analytics report does not exist: {analytics_path}")
    payload = build_research_week(topics, week_start, shorts_count, include_longform, experiment_brief)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {output} ({len(payload['shorts'])} Shorts, {len(payload['longform'])} long-form)")
    return 0


def run_prepare_week(
    week_of: str,
    shorts_count: int,
    research_output: Path,
    plan_output: Path,
    include_longform: bool = True,
    analytics_path: Path | None = None,
    reddit_only: bool = False,
) -> int:
    """Discover once and write a private research slate plus production plan."""
    try:
        week_start = date.fromisoformat(week_of)
    except ValueError as exc:
        raise ValueError("week_of must be an ISO date") from exc
    settings = load_settings()
    approved_topics = load_approved_reddit_topics(settings.reddit_approved_file)
    topics = approved_topics if reddit_only else discover_topics(max(settings.topic_limit, shorts_count + 3))
    if not reddit_only:
        topics.extend(approved_topics)
    experiment_brief = None
    report_path = analytics_path or getattr(settings, "data_dir", Path("data")) / "analytics_report.json"
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            if analytics_path is not None:
                raise ValueError(f"Could not read analytics report: {analytics_path}") from exc
        else:
            if isinstance(report, dict) and isinstance(report.get("experiment_brief"), dict):
                experiment_brief = report["experiment_brief"]
    elif analytics_path is not None:
        raise ValueError(f"Analytics report does not exist: {analytics_path}")
    research = build_research_week(topics, week_start, shorts_count, include_longform, experiment_brief)
    researched_urls = {
        item["source"]["url"]
        for item in research["shorts"] + research["longform"]
        if isinstance(item, dict) and isinstance(item.get("source"), dict) and item["source"].get("url")
    }
    researched_topics = [topic for topic in topics if topic.sources and topic.sources[0].url in researched_urls]
    entries = build_weekly_plan(
        researched_topics, week_start, shorts_count, include_longform, researched_topics, experiment_brief
    )
    briefs = {item["source"]["url"]: item for item in research["shorts"] + research["longform"] if item.get("source")}
    for entry in entries:
        brief = briefs.get(entry["source_url"])
        if brief:
            entry["editorial_brief"] = brief
    if not entries:
        raise RuntimeError("No source-backed topics were available for the weekly plan")
    research_output.parent.mkdir(parents=True, exist_ok=True)
    plan_output.parent.mkdir(parents=True, exist_ok=True)
    research_output.write_text(json.dumps(research, indent=2), encoding="utf-8")
    plan_output.write_text(
        json.dumps(
            {
                "week_of": week_of,
                "privacy_status": "private",
                "reddit_only": reddit_only,
                "editorial_reviewed": True,
                "entries": entries,
                "experiment_brief": experiment_brief,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Prepared {research_output} and {plan_output} ({len(entries)} entries)")
    return 0


def run_weekly_production(
    plan_path: Path, output_dir: Path, upload_private: bool = False, preflight_only: bool = False
) -> int:
    """Render a reviewed private plan without allowing public or TikTok publishing."""
    try:
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read weekly plan: {plan_path}") from exc
    if not isinstance(payload, dict) or payload.get("privacy_status") != "private":
        raise ValueError("Weekly plan must declare private privacy_status")
    requires_editorial_review = payload.get("editorial_reviewed") is True
    entries = payload.get("entries")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 8:
        raise ValueError("Weekly plan must contain 1 to 8 entries")
    if sum(isinstance(entry, dict) and entry.get("kind") == "short" for entry in entries) > 7:
        raise ValueError("Weekly plan cannot contain more than 7 Shorts")
    if sum(isinstance(entry, dict) and entry.get("kind") == "longform" for entry in entries) > 1:
        raise ValueError("Weekly plan cannot contain more than 1 long-form entry")
    settings = load_settings()
    topics = discover_topics(max(settings.topic_limit, 10))
    approved_topics = load_approved_reddit_topics(settings.reddit_approved_file)
    approved_by_url = {
        topic.sources[0].url: topic for topic in approved_topics if topic.sources and topic.sources[0].url
    }
    topics.extend(approved_topics)
    topic_by_url = {topic.sources[0].url: topic for topic in topics if topic.sources and topic.sources[0].url}
    prepared: list[tuple[str, str, object, dict[str, Any] | None, str | None]] = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("privacy_status") != "private":
            raise ValueError("Every weekly plan entry must be private")
        kind = entry.get("kind")
        if kind not in {"short", "longform"}:
            raise ValueError(f"Unsupported weekly plan entry kind: {kind}")
        source_url = str(entry.get("source_url", "")).strip()
        if source_url not in topic_by_url:
            raise ValueError(f"Weekly plan source is unavailable: {source_url}")
        if kind == "longform" and _is_reddit_url(source_url) and source_url not in approved_by_url:
            raise ValueError(f"Long-form source is not approved: {source_url}")
        editorial_brief = entry.get("editorial_brief")
        _validate_weekly_editorial_brief(editorial_brief, source_url, kind, requires_editorial_review)
        prepared.append(
            (
                kind,
                source_url,
                approved_by_url.get(source_url, topic_by_url[source_url]),
                editorial_brief,
                entry.get("publish_at"),
            )
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    if preflight_only:
        print(f"Preflight passed for {len(prepared)} weekly entries")
        return 0
    for index, (kind, source_url, topic, editorial_brief, publish_at) in enumerate(prepared, 1):
        if kind == "short":
            run(
                force_dry_run=not upload_private,
                topic_override=topic,
                output_dir_override=output_dir / f"short-{index:02d}",
                private_drafts=upload_private,
                youtube_only=True,
                publish_at=publish_at,
                editorial_brief=editorial_brief,
            )
        elif kind == "longform":
            run_longform(
                source_url,
                output_dir / f"longform-{index:02d}",
                editorial_brief=editorial_brief,
                upload_private=upload_private,
                publish_at=publish_at,
            )
        else:
            raise ValueError(f"Unsupported weekly plan entry kind: {kind}")
    print(f"Produced {len(entries)} weekly entries")
    return 0


def _validate_weekly_editorial_brief(brief: object, source_url: str, kind: str, required: bool = False) -> None:
    """Require reviewed, source-linked packaging before weekly production."""
    if not required:
        return
    if not isinstance(brief, dict):
        raise ValueError("Every weekly entry requires an editorial_brief")
    if brief.get("privacy_status") != "private":
        raise ValueError("Weekly editorial brief must be private")
    source = brief.get("source")
    if not isinstance(source, dict) or source.get("url") != source_url:
        raise ValueError("Weekly editorial brief source URL does not match plan")
    creative = brief.get("creative")
    metadata = brief.get("metadata")
    if not isinstance(creative, dict) or not isinstance(metadata, dict):
        raise ValueError("Weekly editorial brief requires creative and metadata objects")
    if not all(isinstance(creative.get(key), str) and creative[key].strip() for key in ("format_name", "hook")):
        raise ValueError("Weekly editorial brief creative fields are incomplete")
    if not all(isinstance(metadata.get(key), str) and metadata[key].strip() for key in ("title", "description")):
        raise ValueError("Weekly editorial brief metadata fields are incomplete")
    if source_url not in metadata["description"]:
        raise ValueError("Weekly editorial brief metadata is not source-linked")
    if not isinstance(metadata.get("tags"), list) or not any(str(tag).strip() for tag in metadata["tags"]):
        raise ValueError("Weekly editorial brief requires metadata tags")
    if kind == "longform":
        bridge = brief.get("longform_bridge")
        if (
            not isinstance(bridge, dict)
            or not isinstance(bridge.get("question"), str)
            or not bridge["question"].strip()
        ):
            raise ValueError("Long-form weekly entry requires a reviewed question")
        chapters = bridge.get("chapters")
        if not isinstance(chapters, list) or len(chapters) < 3 or not all(str(chapter).strip() for chapter in chapters):
            raise ValueError("Long-form weekly entry requires at least three reviewed chapters")


def run_analytics(authorize: bool = False, weekly: bool = False) -> int:
    settings = load_settings()
    snapshots = settings.data_dir / "youtube_analytics.json"
    collected = collect_due(
        settings.data_dir / "events.jsonl",
        snapshots,
        settings.youtube_client_secrets,
        settings.youtube_analytics_token_file,
        authorize,
        reporting_job_path=getattr(settings, "youtube_reporting_job_file", None),
    )
    if weekly:
        weekly_path = settings.data_dir / "youtube_weekly_report.json"
        write_weekly_report(settings.data_dir / "events.jsonl", snapshots, weekly_path)
        try:
            weekly_payload = json.loads(weekly_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Could not read weekly YouTube report: {weekly_path}") from exc
        if not isinstance(weekly_payload, dict):
            raise RuntimeError("Weekly YouTube report must be a JSON object")
        report_path = settings.data_dir / "analytics_report.json"
        write_report(build_youtube_report(weekly_payload), report_path)
        print(f"Wrote {report_path}")
    print(f"Collected analytics for {len(collected)} due videos")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--preflight", action="store_true", help="Validate production inputs without media work")
    run_parser.add_argument("--reddit-only", action="store_true")
    run_parser.add_argument(
        "--private-drafts",
        action="store_true",
        help="Generate discovered Reddit stories and upload them privately to YouTube",
    )
    run_parser.add_argument(
        "--youtube-only", action="store_true", help="Upload to YouTube only; never upload to TikTok"
    )
    run_parser.add_argument("--publish-at", help="Schedule YouTube publication at a future RFC 3339 time")
    run_parser.add_argument("--daemon", action="store_true")
    run_parser.add_argument("--interval-hours", type=float, default=24.0)
    split_parser = sub.add_parser("split")
    split_parser.add_argument("--input", required=True)
    split_parser.add_argument("--out", default="output/series")
    split_parser.add_argument("--parts", type=int, default=4)
    batch_parser = sub.add_parser("batch")
    batch_parser.add_argument("--count", type=int, default=3)
    batch_parser.add_argument("--dry-run", action="store_true")
    batch_parser.add_argument(
        "--variants", type=int, default=1, help="Treatments per source for controlled hook/format experiments"
    )
    report_parser = sub.add_parser("report")
    report_parser.add_argument(
        "--metrics", required=True, help="CSV export with source_url, platform, and views columns"
    )
    report_parser.add_argument("--events", default="data/events.jsonl")
    report_parser.add_argument("--out", default="data/analytics_report.json")
    archive_parser = sub.add_parser("archive-analytics")
    archive_parser.add_argument("--input", required=True, help="Aggregate analytics JSON report")
    archive_parser.add_argument("--out", default="docs/analytics/weekly.json")
    archive_parser.add_argument("--week-of", required=True, help="ISO date identifying the report week")
    schedule_parser = sub.add_parser("schedule")
    schedule_parser.add_argument("--file", required=True)
    schedule_parser.add_argument("--dry-run", action="store_true")
    longform_parser = sub.add_parser("longform")
    longform_parser.add_argument("--source-url")
    longform_parser.add_argument("--out", default="output/longform")
    weekly_parser = sub.add_parser("plan-week")
    weekly_parser.add_argument("--week-of", required=True, help="Monday ISO date for the planned week")
    weekly_parser.add_argument("--shorts", type=int, default=7)
    weekly_parser.add_argument("--out", default="data/weekly_plan.json")
    weekly_parser.add_argument("--no-longform", action="store_true")
    weekly_parser.add_argument("--analytics", help="Analytics report used to shape the next slate")
    weekly_parser.add_argument("--research", help="Private editorial research slate to attach to the plan")
    research_parser = sub.add_parser("research-week")
    research_parser.add_argument("--week-of", required=True, help="Monday ISO date for the research slate")
    research_parser.add_argument("--shorts", type=int, default=7)
    research_parser.add_argument("--out", default="data/research_week.json")
    research_parser.add_argument("--no-longform", action="store_true")
    research_parser.add_argument("--analytics", help="Analytics report used to shape the next treatments")
    prepare_parser = sub.add_parser("prepare-week")
    prepare_parser.add_argument("--week-of", required=True, help="Monday ISO date for the prepared week")
    prepare_parser.add_argument("--shorts", type=int, default=7)
    prepare_parser.add_argument("--research-out", default="data/research_week.json")
    prepare_parser.add_argument("--plan-out", default="data/weekly_plan.json")
    prepare_parser.add_argument("--no-longform", action="store_true")
    prepare_parser.add_argument("--analytics", help="Analytics report used to shape the next treatments")
    prepare_parser.add_argument(
        "--reddit-only", action="store_true", help="Build the slate only from the approved Reddit queue"
    )
    production_parser = sub.add_parser("produce-week")
    production_parser.add_argument("--plan", required=True)
    production_parser.add_argument("--out", default="output/weekly")
    production_parser.add_argument(
        "--upload-private", action="store_true", help="Upload Shorts as private YouTube drafts; TikTok stays disabled"
    )
    production_parser.add_argument(
        "--preflight", action="store_true", help="Validate the private plan without TTS, rendering, or uploads"
    )
    analytics_parser = sub.add_parser("analytics")
    analytics_parser.add_argument(
        "--authorize", action="store_true", help="Perform one-time read-only YouTube Analytics OAuth"
    )
    analytics_parser.add_argument("--weekly", action="store_true", help="Also write the current Monday-Sunday report")
    assets_parser = sub.add_parser("backgrounds")
    assets_parser.add_argument("--manifest", default="assets/backgrounds.json")
    assets_parser.add_argument("--out", default="data/backgrounds")
    reddit_parser = sub.add_parser("reddit")
    reddit_parser.add_argument("--out", default="data/reddit_candidates.json")
    reddit_parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()
    if args.command == "split":
        for part in split_authorized_clip(Path(args.input), Path(args.out), args.parts):
            print(part)
        return
    if args.command == "batch":
        raise SystemExit(run_batch(max(1, args.count), force_dry_run=args.dry_run, variants=max(1, args.variants)))
    if args.command == "report":
        report = build_report(Path(args.events), Path(args.metrics))
        output = write_report(report, Path(args.out))
        print(f"Wrote {output} ({report['matched_rows']} matched rows, {report['unmatched_rows']} unmatched)")
        return
    if args.command == "archive-analytics":
        report = json.loads(Path(args.input).read_text(encoding="utf-8"))
        if "snapshots" in report:
            report = build_youtube_report(report)
        output = archive_report(report, Path(args.out), args.week_of)
        print(f"Archived {output}")
        return
    if args.command == "schedule":
        raise SystemExit(run_schedule(Path(args.file), force_dry_run=args.dry_run))
    if args.command == "longform":
        raise SystemExit(run_longform(args.source_url, Path(args.out)))
    if args.command == "plan-week":
        raise SystemExit(
            run_weekly_plan(
                args.week_of,
                args.shorts,
                Path(args.out),
                not args.no_longform,
                Path(args.analytics) if args.analytics else None,
                Path(args.research) if args.research else None,
            )
        )
    if args.command == "research-week":
        raise SystemExit(
            run_research_week(
                args.week_of,
                args.shorts,
                Path(args.out),
                not args.no_longform,
                Path(args.analytics) if args.analytics else None,
            )
        )
    if args.command == "prepare-week":
        raise SystemExit(
            run_prepare_week(
                args.week_of,
                args.shorts,
                Path(args.research_out),
                Path(args.plan_out),
                not args.no_longform,
                Path(args.analytics) if args.analytics else None,
                args.reddit_only,
            )
        )
    if args.command == "produce-week":
        raise SystemExit(run_weekly_production(Path(args.plan), Path(args.out), args.upload_private, args.preflight))
    if args.command == "analytics":
        raise SystemExit(run_analytics(authorize=args.authorize, weekly=args.weekly))
    if args.command == "backgrounds":
        for path in sync_backgrounds(Path(args.manifest), Path(args.out)):
            print(path)
        return
    if args.command == "reddit":
        settings = load_settings()
        topics = discover_reddit_topics(
            settings.reddit_subreddits,
            settings.reddit_client_id,
            settings.reddit_client_secret,
            settings.reddit_user_agent,
            max(1, args.count),
        )
        output = Path(args.out)
        if output.resolve() == settings.reddit_approved_file.resolve():
            raise ValueError("Reddit discovery output cannot overwrite the approved queue; choose a separate path")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                [{"title": topic.title, "source": topic.sources[0].__dict__, "score": topic.score} for topic in topics],
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Wrote {output} ({len(topics)} candidates; none are cleared for publishing)")
        return
    if args.daemon:
        if args.preflight:
            raise SystemExit("--preflight cannot be combined with --daemon")
        raise SystemExit(
            run_worker(
                force_dry_run=args.dry_run,
                reddit_only=args.reddit_only,
                private_drafts=args.private_drafts,
                youtube_only=args.youtube_only,
                interval_hours=args.interval_hours,
            )
        )
    if args.preflight:
        raise SystemExit(run_preflight(args.reddit_only, args.private_drafts, args.youtube_only))
    raise SystemExit(
        run(
            force_dry_run=args.dry_run,
            reddit_only=args.reddit_only,
            private_drafts=args.private_drafts,
            youtube_only=args.youtube_only,
            publish_at=args.publish_at,
        )
    )
