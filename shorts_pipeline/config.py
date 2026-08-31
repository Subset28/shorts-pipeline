import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .reddit import RANKED_STORY_SUBREDDITS


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    openai_api_key: str
    openai_model: str
    dry_run: bool
    youtube_privacy_status: str
    youtube_client_secrets: Path
    youtube_token_file: Path
    youtube_analytics_token_file: Path
    youtube_reporting_job_file: Path
    tiktok_access_token: str
    tiktok_privacy_level: str
    elevenlabs_rotator_path: Path
    elevenlabs_voice_id: str
    elevenlabs_model_id: str
    edge_tts_voice: str
    captions_enabled: bool
    caption_model: str
    background_video: Path
    background_dir: Path
    reddit_background_dir: Path
    background_reel_enabled: bool
    background_manifest: Path
    background_video_url: str
    topic_limit: int
    output_dir: Path
    data_dir: Path
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str
    reddit_subreddits: tuple[str, ...]
    reddit_approved_file: Path


def load_settings(dotenv_path: str | None = None) -> Settings:
    load_dotenv(dotenv_path or os.getenv("DOTENV_PATH"))
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "fallback"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        dry_run=os.getenv("DRY_RUN", "true").lower() in {"1", "true", "yes"},
        youtube_privacy_status=os.getenv("YOUTUBE_PRIVACY_STATUS", "private"),
        youtube_client_secrets=Path(os.getenv("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")),
        youtube_token_file=Path(os.getenv("YOUTUBE_TOKEN_FILE", "token.json")),
        youtube_analytics_token_file=Path(os.getenv("YOUTUBE_ANALYTICS_TOKEN_FILE", "youtube_analytics_token.json")),
        youtube_reporting_job_file=Path(os.getenv("YOUTUBE_REPORTING_JOB_FILE", "data/youtube_reporting_job.json")),
        tiktok_access_token=os.getenv("TIKTOK_ACCESS_TOKEN", ""),
        tiktok_privacy_level=os.getenv("TIKTOK_PRIVACY_LEVEL", "SELF_ONLY"),
        elevenlabs_rotator_path=Path(os.getenv("ELEVENLABS_ROTATOR_PATH", "")),
        elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID", ""),
        elevenlabs_model_id=os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
        edge_tts_voice=os.getenv("EDGE_TTS_VOICE", "en-US-GuyNeural"),
        captions_enabled=os.getenv("CAPTIONS_ENABLED", "true").lower() in {"1", "true", "yes"},
        caption_model=os.getenv("CAPTION_MODEL", "base"),
        background_video=Path(os.getenv("BACKGROUND_VIDEO", "")),
        background_dir=Path(os.getenv("BACKGROUND_VIDEO_DIR", "data/backgrounds")),
        reddit_background_dir=Path(os.getenv("REDDIT_BACKGROUND_DIR", "data/backgrounds/minecraft_parkour_chunks")),
        background_reel_enabled=os.getenv("BACKGROUND_REEL_ENABLED", "false").lower() in {"1", "true", "yes"},
        background_manifest=Path(os.getenv("BACKGROUND_MANIFEST", "assets/backgrounds.json")),
        background_video_url=os.getenv("BACKGROUND_VIDEO_URL", ""),
        topic_limit=int(os.getenv("TOPIC_LIMIT", "10")),
        output_dir=Path(os.getenv("OUTPUT_DIR", "output")),
        data_dir=Path(os.getenv("DATA_DIR", "data")),
        reddit_client_id=os.getenv("REDDIT_CLIENT_ID", ""),
        reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
        reddit_user_agent=os.getenv("REDDIT_USER_AGENT", "shorts-pipeline/1.0"),
        reddit_subreddits=tuple(
            item.strip()
            for item in os.getenv("REDDIT_SUBREDDITS", ",".join(RANKED_STORY_SUBREDDITS)).split(",")
            if item.strip()
        ),
        reddit_approved_file=Path(os.getenv("REDDIT_APPROVED_FILE", "data/reddit_candidates.json")),
    )
