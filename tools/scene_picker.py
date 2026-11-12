"""Pick which pixel backdrop fits the current album, using Claude (opt-in) with a local fallback.

The model only CHOOSES from the catalog in backdrops.py; the app still draws the scene, so
the pixel look is always consistent. Answers are cached per album, so each album costs one
call at most. Without an API key, offline, or on any error, a keyword fallback answers.

Usage:
  export ANTHROPIC_API_KEY=...            # optional; without it the fallback is used
  python3 scene_picker.py --title "Slow Bloom" --artist "Marlow Kei" --album "Afterhours, Vol. 2" \
      [--genre "indie soul"] [--cover cover.png] [--no-api] [--cache scene_cache.json]

Privacy: with the API on, the track title, artist, album, genres and (only with --cover) a
64x64 thumbnail of the cover are sent to Anthropic. Keep this off by default in the app.
"""
import argparse
import base64
import io
import json
import os
import re

from backdrops import CATALOG

MODEL = os.environ.get('TURNTABLE_MODEL', 'claude-haiku-5-5')
CACHE_PATH = os.path.expanduser(os.environ.get('TURNTABLE_SCENE_CACHE', '~/.turntable/scene_cache.json'))

TOOL = {
    'name': 'pick_backdrop',
    'description': 'Choose the one backdrop scene that best fits the mood of the album.',
    'input_schema': {
        'type': 'object',
        'properties': {
            'scene': {'type': 'string', 'enum': list(CATALOG)},
            'reason': {'type': 'string', 'description': 'One short sentence.'},
        },
        'required': ['scene', 'reason'],
    },
}

SYSTEM = (
    'You pick a pixel-art backdrop for a music player that shows the current album as a spinning CD. '
    'Choose the scene whose mood best matches the music. Judge from the metadata and, if given, the '
    'cover\'s colours and subject. Always call pick_backdrop exactly once.'
)

KEYWORDS = [  # fallback: first match wins
    ('city_night', r'night|neon|city|midnight|street|club|r&b|rnb|hip.?hop|rap|synth|electro|house|techno|afterdark'),
    ('ocean',      r'ocean|sea|tide|wave|surf|beach|shore|coast|water|summer|island|blue'),
    ('desert',     r'desert|sun|dust|western|country|cowboy|heat|sand|psych|mirage|gold'),
    ('forest',     r'forest|wood|pine|winter|snow|fog|ambient|folk|quiet|cold|moss'),
]


def cache_key(track):
    return '|'.join((track.get('album_id') or '', track.get('artist', ''), track.get('album', ''))).lower()


def load_cache(path=CACHE_PATH):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_cache(cache, path=CACHE_PATH):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(cache, f, indent=2)
    os.replace(tmp, path)


def fallback(track):
    text = ' '.join([track.get('title', ''), track.get('album', ''), track.get('artist', '')] + track.get('genres', [])).lower()
    for scene, pattern in KEYWORDS:
        if re.search(pattern, text):
            return {'scene': scene, 'reason': f'keyword match ({scene})', 'source': 'fallback'}
    return {'scene': 'hills', 'reason': 'default calm scene', 'source': 'fallback'}


def _cover_block(cover_path):
    from PIL import Image
    im = Image.open(cover_path).convert('RGB').resize((64, 64), Image.BOX)
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    return {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                        'data': base64.b64encode(buf.getvalue()).decode()}}


def ask_claude(track, cover_path=None, client=None):
    if client is None:
        import anthropic                     # pip install anthropic
        # Bring-your-own-key: Turntable never ships a key. The user creates their own in the Anthropic
        # Console and provides it (env var today; a Keychain-backed settings field in the app).
        # Requests are billed to that user's account.
        client = anthropic.Anthropic()       # reads ANTHROPIC_API_KEY
    catalog = '\n'.join(f'- {k}: {v}' for k, v in CATALOG.items())
    meta = json.dumps({k: track.get(k) for k in ('title', 'artist', 'album', 'genres', 'year') if track.get(k)})
    content = []
    if cover_path:
        content.append(_cover_block(cover_path))
    content.append({'type': 'text', 'text': f'Scenes:\n{catalog}\n\nNow playing: {meta}'})
    resp = client.messages.create(
        model=MODEL, max_tokens=200, system=SYSTEM, tools=[TOOL],
        tool_choice={'type': 'tool', 'name': 'pick_backdrop'},
        messages=[{'role': 'user', 'content': content}],
    )
    for block in resp.content:
        if getattr(block, 'type', None) == 'tool_use' and block.name == 'pick_backdrop':
            scene = block.input.get('scene')
            if scene in CATALOG:
                return {'scene': scene, 'reason': block.input.get('reason', ''), 'source': MODEL}
    raise ValueError('no valid pick in response')


def pick_scene(track, cover_path=None, use_api=True, cache_path=CACHE_PATH, client=None):
    """track: {'title','artist','album', optional 'album_id','genres','year'} -> {'scene','reason','source'}"""
    cache = load_cache(cache_path)
    key = cache_key(track)
    if key in cache:
        return dict(cache[key], cached=True)
    result = None
    # No key means no request: the picker stays off and the keyword fallback answers.
    # In the app this call should also be gated on the user having turned the picker on.
    if use_api and (client is not None or os.environ.get('ANTHROPIC_API_KEY')):
        try:
            result = ask_claude(track, cover_path, client)
        except Exception as e:               # offline, rate limit, bad answer... never break the display
            result = dict(fallback(track), error=type(e).__name__)
    if result is None:
        result = fallback(track)
    if result['source'] != 'fallback':       # only cache real model answers
        cache[key] = result
        save_cache(cache, cache_path)
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--title', required=True)
    ap.add_argument('--artist', required=True)
    ap.add_argument('--album', required=True)
    ap.add_argument('--genre', action='append', default=[])
    ap.add_argument('--cover')
    ap.add_argument('--no-api', action='store_true')
    ap.add_argument('--cache', default=CACHE_PATH)
    a = ap.parse_args()
    track = {'title': a.title, 'artist': a.artist, 'album': a.album, 'genres': a.genre}
    print(json.dumps(pick_scene(track, a.cover, not a.no_api, a.cache), indent=2))
