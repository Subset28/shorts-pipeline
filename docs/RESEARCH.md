# Evidence-backed production rules

The pipeline treats platform guidance as a constraint and analytics as the
feedback loop. It does not assume that a particular font, color, lane, or
posting schedule guarantees reach.

## Rules implemented

- **Deliver the promised value immediately.** YouTube says viewers decide in
  the initial seconds whether to stay, and recommends a concise intro that
  matches the title and delivers value. Fallback narration therefore starts
  with a plain-language claim or question, followed by evidence and a payoff.
- **Use retention evidence to iterate.** YouTube exposes stayed-to-watch,
  engaged views, average percentage viewed, spikes, and dips. The telemetry and
  variant fields preserve the source, lane, and treatment so platform exports
  can be compared rather than relying on anecdotes.
- **Do not treat a format as inherently favored.** YouTube states that Shorts
  are not ranked by a preferred format; performance and viewer personalization
  matter. The lane selector therefore uses formats as controlled treatments,
  and only enables a specialized lane when the source supports its promise.
- **Keep captions readable and accurate.** Captions are burned into the video,
  limited to short bursts, and can use local Whisper timing when available.
  Speaker colors are used only when diarization supplies speaker labels.

## Sources

- [YouTube: recommendation performance](https://support.google.com/youtube/answer/16559650?hl=en)
- [YouTube: Shorts search and discovery](https://support.google.com/youtube/answer/11914225?co=YOUTUBE._YTVideoType%3Dshorts&hl=en)
- [YouTube: retention analytics](https://support.google.com/youtube/answer/9314415?hl=en)
- [YouTube: Shorts analytics metrics](https://support.google.com/youtube/answer/12942217?co=YOUTUBE._YTVideoType%3Dshorts&hl=en)

These sources support the workflow and measurement choices; they do not support
any forecast of a particular view count.
