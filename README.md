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
process supervisor. The default free mode uses RSS, fallback copy, Pillow,
FFmpeg, and free edge-tts narration. An OpenAI API key and ElevenLabs rotator are optional quality upgrades;
a ChatGPT Plus subscription is not an API credential.

The included `Dockerfile` and `docker-compose.yml` provide a restart-on-failure
runtime for a NAS or other always-on host. Keep `.env` and the mounted `secrets`
directory local and private.

The visual defaults and footage/caption rules are documented in
`docs/STYLE_GUIDE.md`.

For a rights-cleared local clip, create bounded series parts with
`python -m shorts_pipeline split --input path\to\clip.mp4 --parts 4`.

Generate a queue of distinct drafts with `python -m shorts_pipeline batch
--count 3 --dry-run`; each asset is written to its own `output/batch-NN`
folder (with `item-NN` children; reruns allocate a new batch) and uses the
source/format telemetry path.

Provision the tracked, rights-documented background library with
`python -m shorts_pipeline backgrounds`. The command downloads only URLs in
`assets/backgrounds.json` and skips files already present.

After publishing, export platform metrics to a CSV containing `source_url`,
`platform`, and `views` (optionally `likes`, `comments`, and `shares`), then
run `python -m shorts_pipeline report --metrics metrics.csv`. The report joins
metrics to category/format telemetry so future batches can follow evidence.
