# Short-form visual style

`SHORTS_CREATIVE_SPEC_V2.md` governs story structure, visual density, proof,
captions, and creative acceptance for new work. This file remains the palette
and rendering reference. When these documents conflict, v2 governs.

The renderer follows the patterns seen in high-performing vertical reference
clips while keeping the channel recognizable as Signal Lab:

- 720x1280 previews and 1080x1920 public masters, both at 30 fps. Resolution
  never overrides resource safety; a host that cannot render the master safely
  must queue it on the approved fallback worker rather than publish the preview.
- A short, high-contrast headline at the top; never place a raw paper title in
  the hook area.
- Bold sans-serif captions in short bursts of up to four words per line,
  uppercase for scanability, with a yellow fill (`#FFD700`) and black outline.
- Caption baseline around 68-78% of frame height, leaving room for platform
  controls and the description overlay.
- Require at least six distinct visual states and a meaningful pattern change
  every 1.5–3.0 seconds. Source proof and original mechanism visuals carry the
  story; a background reel alone does not satisfy this requirement.
- Use white for neutral text and reserve yellow/green accents for the words
  that carry the joke, reveal, or key technical term.
- Design frame one as a poster for the contradiction. No logo or full Reddit
  headline before the visual promise.
- Show the Reddit card for 0.8–2.0 seconds as a receipt, then return to the
  source-specific visual progression.

These are production heuristics, not a promise of virality. Every downloaded
clip must be public-domain, licensed, user-authorized, or otherwise cleared for
the intended upload; yt-dlp is a downloader, not a rights grant.

The evidence and implementation mapping are recorded in `docs/RESEARCH.md`.
The style choices are production heuristics, not platform ranking rules or a
promise of virality. Also see the [NASA SVS media policy](https://svs.gsfc.nasa.gov/help/)
for source-footage handling.
