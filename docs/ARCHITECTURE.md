# Architecture

`sources.py` reads public feeds; `seo.py` creates a source-linked original
explanation; `tts.py` optionally calls the existing ElevenLabs rotating-key
helper; `render.py` produces a 9:16 MP4; and `publish.py` sends that asset to
YouTube and TikTok through their official APIs. The manifest makes retries and
future analytics joins deterministic.

The free path uses RSS, deterministic fallback copy, local Pillow rendering,
FFmpeg, and silent audio. Optional LLM and TTS adapters improve quality without
changing the pipeline contract.
