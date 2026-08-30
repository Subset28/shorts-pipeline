# Shorts Pipeline

Source-backed, unattended short-form publishing for YouTube Shorts and TikTok.
The pipeline discovers a topic, writes original cited metadata, renders a 9:16
MP4 with FFmpeg, adds ElevenLabs narration through the local rotating-key helper,
burns captions from optional local faster-whisper, and publishes through official APIs.

It defaults to `DRY_RUN=true` and private uploads. No scraped clips or
copyrighted music are used. See `docs/ARCHITECTURE.md` and `docs/OPERATIONS.md`.

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
python -m shorts_pipeline run --dry-run
```

Required tools: `ffmpeg` and `ffprobe`. Install `faster-whisper` with
`pip install -e .[captions]` for audio-aligned local transcription; otherwise
the pipeline uses free text-timed captions. Real publishing requires OAuth
credentials for YouTube and TikTok plus approved posting scopes.

For unattended operation, use `python -m shorts_pipeline run --daemon` with a
process supervisor. The default free mode uses RSS, fallback copy, Pillow, and
FFmpeg. An OpenAI API key and ElevenLabs rotator are optional quality upgrades;
a ChatGPT Plus subscription is not an API credential.

The included `Dockerfile` and `docker-compose.yml` provide a restart-on-failure
runtime for a NAS or other always-on host. Keep `.env` and the mounted `secrets`
directory local and private.

The visual defaults and footage/caption rules are documented in
`docs/STYLE_GUIDE.md`.
