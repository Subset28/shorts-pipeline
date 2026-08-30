import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    openai_api_key: str
    openai_model: str
    dry_run: bool
    youtube_privacy_status: str
    youtube_client_secrets: Path
    youtube_token_file: Path
    tiktok_access_token: str
    tiktok_privacy_level: str
    elevenlabs_rotator_path: Path
    elevenlabs_voice_id: str
    elevenlabs_model_id: str
    edge_tts_voice: str
    captions_enabled: bool
    caption_model: str
    background_video: Path
    background_video_url: str
    topic_limit: int
    output_dir: Path
    data_dir: Path


def load_settings(dotenv_path: str | None = None) -> Settings:
    load_dotenv(dotenv_path)
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "fallback"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        dry_run=os.getenv("DRY_RUN", "true").lower() in {"1", "true", "yes"},
        youtube_privacy_status=os.getenv("YOUTUBE_PRIVACY_STATUS", "private"),
        youtube_client_secrets=Path(os.getenv("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")),
        youtube_token_file=Path(os.getenv("YOUTUBE_TOKEN_FILE", "token.json")),
        tiktok_access_token=os.getenv("TIKTOK_ACCESS_TOKEN", ""),
        tiktok_privacy_level=os.getenv("TIKTOK_PRIVACY_LEVEL", "SELF_ONLY"),
        elevenlabs_rotator_path=Path(os.getenv("ELEVENLABS_ROTATOR_PATH", "")),
        elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID", ""),
        elevenlabs_model_id=os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
        edge_tts_voice=os.getenv("EDGE_TTS_VOICE", "en-US-GuyNeural"),
        captions_enabled=os.getenv("CAPTIONS_ENABLED", "true").lower() in {"1", "true", "yes"},
        caption_model=os.getenv("CAPTION_MODEL", "base"),
        background_video=Path(os.getenv("BACKGROUND_VIDEO", "data/backgrounds/nasa_moon_to_earth.mp4")),
        background_video_url=os.getenv("BACKGROUND_VIDEO_URL", "https://svs.gsfc.nasa.gov/vis/a000000/a005000/a005039/moon_to_earth_1080p30.mp4"),
        topic_limit=int(os.getenv("TOPIC_LIMIT", "10")),
        output_dir=Path(os.getenv("OUTPUT_DIR", "output")),
        data_dir=Path(os.getenv("DATA_DIR", "data")),
    )
