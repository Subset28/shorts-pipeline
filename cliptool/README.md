# cliptool

Bounded-clip scout & extractor for Twitch and YouTube. Turns a
channel/video/VOD/clip URL into a list of short (8-90s, configurable)
candidate segments — not whole videos — ready to feed a shorts pipeline.

See [SPEC.md](./SPEC.md) for the full design (schema, scoring, error
handling).

## Setup (Mac mini M4 / macOS, Apple Silicon)

```
cd projects/cliptool
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in TWITCH_CLIENT_ID/SECRET, YOUTUBE_API_KEY
```

Install yt-dlp and ffmpeg via Homebrew (native Apple Silicon builds —
don't use an x86 install under Rosetta, it's slower and unnecessary):

```
brew install yt-dlp ffmpeg
```

If Homebrew itself isn't installed yet:
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
On Apple Silicon Homebrew lives at `/opt/homebrew` — the installer
prints an `eval "$(/opt/homebrew/bin/brew shellenv)"` line to add to
your `~/.zshrc`; run it (or restart your terminal) before `brew install`.

Getting Twitch credentials: [dev.twitch.tv/console/apps](https://dev.twitch.tv/console/apps) →
Register Your Application → any OAuth Redirect URL (e.g.
`http://localhost:3000`, unused by this tool — we only use the
Client Credentials flow) → Client Type: **Confidential**.

## CLI usage

Activate the venv once per shell (`source .venv/bin/activate`), then
run everything from `projects/cliptool/` with `python3 -m`:

```
# find candidate segments
python3 -m cliptool.cli scout --source "https://www.youtube.com/watch?v=XXXX" --min 8 --max 90 --out candidates.json

# download one candidate's exact bounded segment + preview frames
python3 -m cliptool.cli fetch --candidates-file candidates.json --candidate "yt:XXXX:145-210" --out outputs/clip1.mp4

# run the local HTTP API (for agents to read/edit config, or drive scout/fetch)
python3 -m cliptool.cli serve --port 8787
```

To keep the API running persistently on the Mac mini (so other agents
can hit it any time), use the included `launchd` template instead of a
login-shell process — it survives reboots without a logged-in terminal:

```
cp launchd/com.cliptool.api.plist.example ~/Library/LaunchAgents/com.cliptool.api.plist
# edit the copy: replace YOURUSER and the repo path with the real ones
launchctl load ~/Library/LaunchAgents/com.cliptool.api.plist
```

Check it's up: `curl http://127.0.0.1:8787/health`. Logs land at
`/tmp/cliptool-api.log` / `.err.log` (paths set in the plist).
To stop it: `launchctl unload ~/Library/LaunchAgents/com.cliptool.api.plist`.

## API (for agents)

Local-only, binds `127.0.0.1:8787` by default:

- `GET /health`
- `GET /config` / `PUT /config` (`{"patch": {...}}`) / `GET /config/schema`
- `POST /scout` — `{"source": "...", "min": 8, "max": 90, "out": "candidates.json"}`
- `POST /fetch` — `{"candidates_file": "candidates.json", "candidate_id": "...", "frames": true}`

Secrets (`TWITCH_CLIENT_ID/SECRET`, `YOUTUBE_API_KEY`) are never
readable or writable through this API — they live only in `.env`.

## Candidate output

`candidates.json` and `selected_for_render.json` share one schema —
see SPEC.md's "Candidate schema" section. Selection into
`selected_for_render.json` is a downstream step (ranking/filtering);
this tool's job ends at `candidates.json`.

## Testing

```
pip install pytest
python3 -m pytest tests/ -v
```

Tests use fixture transcripts and a throwaway config copy — no live
network calls, no YouTube quota consumed.

## Notes

- Twitch clips are pre-bounded by the creator — no windowing needed.
- YouTube videos: transcript-scored windowing when a transcript
  exists; falls back to fixed-interval chunking otherwise.
- Twitch VODs: fixed-interval chunking only in v1 (rarely captioned) —
  flagged as low-confidence in `why_selected`.
- YouTube Data API v3 free tier = 10,000 units/day; `youtube_daily_quota_cap`
  (default 9000) hard-stops calls before you'd hit a paid tier.
