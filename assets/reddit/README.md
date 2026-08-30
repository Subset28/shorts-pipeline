# Reddit card assets

The Reddit opening card loads these optional transparent PNGs when present:

- `avatar.png` — the account avatar, cropped square
- `verified.png` — the verification mark
- `badge-1.png` through `badge-4.png` — the visible badge row
- `awards/*.png` and `awards/*.gif` — optional Reddit award art; eight deterministic awards are
  selected per post so different stories get different rows

Place the exact assets from the approved reference in this directory. If an
asset is missing, the renderer uses a neutral fallback and continues to work.
These files are local production assets and are not downloaded automatically.

The bundled award PNGs were sourced from the public
`androiddevnotes/reddit-awards` collection supplied for this project.
Review that collection's current licensing and Reddit's brand/award usage
rules before monetized publication; local inclusion here is not a commercial
rights clearance.
