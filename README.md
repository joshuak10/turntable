# Turntable prototype — screens and asset tools

Two music display screens and the Python scripts that generate their pixel art.
The three albums are original stand-ins; in the app, covers come from Spotify at runtime
and go through the same pipeline.

## Open the screens

Open either file in a browser (double-click works; Screen 2 loads its fonts from Google Fonts):

- `screens/screen1-minimal.html` — the CD in the middle, pixel progress bar, back / pause / forward,
  and an album-themed pixel backdrop. No text.
- `screens/screen2-details.html` — the LED-panel CD with title, artist, groove-bar progress and controls.

Keys: **Space** play/pause, **← / →** previous/next. On Screen 1, **B** tries the next backdrop scene
for the current album (to compare against the AI's pick).

Both screens spin at the same speed: `SPIN_SECONDS = 3` (20 rpm) in `tools/build_assets.py`,
written into `screens/assets/manifest.js`.

## Rebuild the assets

Needs Python 3.10+ and Pillow (`pip install pillow`).

```
cd tools
python3 build_assets.py            # uses Claude to pick scenes if ANTHROPIC_API_KEY is set
python3 build_assets.py --no-api   # keyword fallback only
```

| Script | What it makes |
| --- | --- |
| `make_sprites.py` | Shared pixel-art helpers and palettes (and the first-round vinyl/CD sprites if run directly) |
| `cover_to_cd.py` | Cover → 64×64 pixel CD, 60 frames per turn; LED background or transparent |
| `backdrops.py` | The scene catalog (hills, ocean, city_night, desert, forest), each recoloured from the cover |
| `scene_picker.py` | Picks the scene for an album with Claude; cached per album; keyword fallback |
| `build_assets.py` | Runs all of the above for the demo albums and writes `screens/assets/manifest.js` |

## The AI backdrop picker

`scene_picker.py` sends the track title, artist, album and genres (and, with `--cover`, a 64×64
thumbnail of the cover) to Claude, which must answer through a `pick_backdrop` tool whose
`scene` is one of the catalog ids. The model only chooses; the app draws the scene, so the
pixel look stays consistent.

- Model: `claude-haiku-5-5` by default (override with `TURNTABLE_MODEL`).
- Cache: one answer per album in `~/.turntable/scene_cache.json` (override with `TURNTABLE_SCENE_CACHE`).
- Fallback: with no key, offline, or on any error or invalid answer, a keyword match picks the scene,
  and fallback answers are not cached so the model is asked again later.
- Privacy: this sends listening data to Anthropic, so the app should keep it off until the user turns it on.

## Bring your own API key

The backdrop picker is optional, and Turntable does not ship with a key. Anyone who wants the AI pick
creates their own Anthropic API key and gives it to the app; usage is billed to that person's own
Anthropic account.

1. Create a key in the Anthropic Console (console.anthropic.com), under API keys.
2. Give it to Turntable. Today that means `export ANTHROPIC_API_KEY=...` before running the tools.
   In the app it should be a settings field that stores the key in the macOS Keychain (planned, not built).
3. Turn the picker on. It is off by default.

What the picker sends: the track title, artist, album, genres and year when known, and (only with `--cover`)
a 64×64 thumbnail of the cover. Nothing else leaves the machine.

Without a key, offline, or on any error, Turntable uses the keyword fallback, so the screens always work.
Answers are cached per album in `~/.turntable/scene_cache.json`, so each album costs at most one request.

See `DESIGN.md` for the reasoning behind this choice.

Try it for one album:

```
pip install anthropic
export ANTHROPIC_API_KEY=...
python3 tools/scene_picker.py --title "Slow Bloom" --artist "Marlow Kei" --album "Afterhours, Vol. 2" \
    --genre "indie soul" --cover screens/assets/cover_sunset.png
```

To use a real cover with the disc pipeline: `python3 tools/cover_to_cd.py OUT_DIR path/to/cover.png`.

Ideas for later live in `extra_features.txt`.
