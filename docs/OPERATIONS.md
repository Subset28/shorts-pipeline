# Operations

Start with `python -m shorts_pipeline run --dry-run`. Keep `DRY_RUN=true` until
the output and source citations are acceptable. Store OAuth tokens, client
secrets, and ElevenLabs `keys.json` outside Git.

YouTube requires OAuth with `youtube.upload`; unverified API projects make
uploads private until audit. TikTok Direct Post requires an approved app and
the `video.publish` scope; unaudited clients are private-only. Use the
platform-specific privacy values returned by TikTok creator-info rather than
assuming public access.
