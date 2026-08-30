# Architecture

`sources.py` reads public feeds; `seo.py` creates a source-linked original
explanation; `tts.py` optionally calls the existing ElevenLabs rotating-key
helper; `render.py` produces a 9:16 MP4; and `publish.py` sends that asset to
YouTube and TikTok through their official APIs. The manifest makes retries and
future analytics joins deterministic.

`media.py` provides an explicit yt-dlp adapter for rights-cleared source media.
It is never part of topic discovery and never downloads playlists by default.

`captions.py` uses local faster-whisper when installed and falls back to timing
the known narration text. The resulting SRT is burned into the final MP4 by
FFmpeg, so platform uploads do not depend on sidecar-caption support.

The free path uses RSS, deterministic fallback copy, local Pillow rendering,
FFmpeg, and silent audio. Optional LLM and TTS adapters improve quality without
changing the pipeline contract.
