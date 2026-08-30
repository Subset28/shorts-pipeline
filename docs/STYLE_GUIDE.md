# Short-form visual style

The renderer follows the patterns seen in high-performing vertical reference
clips while keeping the channel recognizable as Signal Lab:

- 1080x1920, 30 fps, full-frame motion footage; crop or loop a cleared source
  rather than showing a static card.
- A short, high-contrast headline at the top; never place a raw paper title in
  the hook area.
- Bold sans-serif captions in short bursts of up to four words per line,
  uppercase for scanability, with a yellow fill (`#FFD700`) and black outline.
- Caption baseline around 68-78% of frame height, leaving room for platform
  controls and the description overlay.
- Prefer a new visual event, crop, or source shot every 2-4 seconds when the
  source permits it. The default renderer builds a short reel from multiple
  approved sources when the local library contains enough footage; narration
  and captions must still carry the progression.
- Use white for neutral text and reserve yellow/green accents for the words
  that carry the joke, reveal, or key technical term.

These are production heuristics, not a promise of virality. Every downloaded
clip must be public-domain, licensed, user-authorized, or otherwise cleared for
the intended upload; yt-dlp is a downloader, not a rights grant.

References used for the defaults: [CapCut caption style guidance](https://www.capcut.com/resource/caption-style),
[CapCut subtitle guidance](https://www.capcut.com/resource/add-subtitles-to-video),
and the [NASA SVS media policy](https://svs.gsfc.nasa.gov/help/).
