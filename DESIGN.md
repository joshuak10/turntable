# Turntable design notes

Status: draft. Records decisions made so far; items marked *planned* are not built yet.

## Goals

Turntable is a free, open-source project. The goals are a portfolio piece, learning, and real users.
It is not priced, so nothing in the design should create a running cost for the author.

## Decision: users bring their own API key

The AI backdrop picker (`tools/scene_picker.py`) calls the Anthropic API. Turntable does not provide a key.
Users who want the picker create their own key in the Anthropic Console and add it to the app.

Why:
- A shared key on a free app means the author pays for every user's requests.
- It keeps listening data between the user and their own account, not a server the author runs.
- The picker is a nice-to-have. The app must be fully usable without it.

## Behaviour

- **Off by default.** The user turns the picker on. *Planned in the app; the scripts already skip the API when no key is set.*
- **No key, offline, or any error:** use the keyword fallback in `scene_picker.py`. The display never breaks.
- **Cache:** one answer per album in `~/.turntable/scene_cache.json`. Fallback answers are not cached, so the model is asked again later.
- **Key storage:** macOS Keychain, entered in a settings field. *Planned.* Today the key is read from `ANTHROPIC_API_KEY`.
- **Model:** `claude-haiku-5-5` by default; override with `TURNTABLE_MODEL`.

## Data sent to Anthropic (picker on)

Track title, artist, album, genres and year when known. With `--cover`, a 64x64 thumbnail of the cover.
The model only chooses a scene id from the catalog in `tools/backdrops.py`; the app draws the scene.

## Open questions

- Does Spotify's developer policy restrict sending Spotify track data to an AI model? Unconfirmed; check before wide release.
- First-run wording that explains the picker, what it sends, and how to get a key.
- What happens to cached answers if the user removes their key (keep, or clear).
