# Content formats

The channel should rotate formats while keeping one recognizable lens: useful,
surprising technology stories told quickly.

1. **News breakdown** — one current source, one surprising claim, a plain-English
   explanation, and a concrete “why it matters” payoff.
2. **Technical joke / POV** — a relatable joke about debugging, AI agents,
   security, or ML culture, followed by a real fact so it is still on-topic.
3. **Cleared clip commentary** — a bounded summit, interview, demo, or creator
   clip selected through cliptool, with original narration/context and speaker
   colors when diarization is available.
4. **Series** — split one cleared long-form clip into 2–4 independently useful
   parts. Every part needs its own hook, `Part N of M` marker, source credit,
   and payoff; splitting alone is not transformation.

The deterministic fallback rotates formats by source URL. An LLM provider may
choose among the same formats, but it must preserve source links, avoid claims
not supported by the source, and avoid instructions that enable wrongdoing.

The multipart helper requires an explicit local input path and is not connected
to discovery. This prevents arbitrary downloads from silently becoming uploads;
the operator must establish that each clip is public-domain, licensed, or
otherwise authorized.

Speaker-colored captions are emitted by `write_speaker_ass` when a future
WhisperX/diarization stage supplies speaker labels. The default generated
narrator intentionally remains one color.
