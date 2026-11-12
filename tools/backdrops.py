"""Backdrop catalog: procedural pixel scenes, each recoloured from the current album cover.

Every scene is drawn at 180 x 113 pixels and shown at 8x (1440 x 904). The scene decides
the *layout* (hills, ocean, city...), the cover decides the *colours*:
  - hue of the cover's light half  -> sky roles
  - hue of the cover's dark half   -> land roles
  - saturation is capped so every theme stays mellow
Each scene fixes the lightness of every role, so the progress bar and controls keep their
contrast whatever the album.

The AI picker (scene_picker.py) chooses WHICH scene; this file only draws them.
"""
import colorsys
import math
import random
from PIL import Image

import make_sprites as ms

W, H = 180, 113

# id -> what the picker is told about the scene
CATALOG = {
    'hills':      'Rolling green-style hills under a soft sky, two clouds, grass tufts. Calm, acoustic, folk, mellow, everyday.',
    'ocean':      'Open sea to the horizon with a low sun and wave glints, a strip of beach. Summer, surf, dreamy, chill, nostalgic.',
    'city_night': 'City skyline at night, lit windows, a moon and stars. Urban, R&B, hip-hop, late night, electronic, moody.',
    'desert':     'Layered sand dunes, a big low sun and a single cactus. Warm, psychedelic, western, slow, hazy.',
    'forest':     'Two rows of pine trees with a band of fog. Indie, ambient, wintery, introspective, quiet.',
}

# role -> (hue source, saturation factor); lightness comes from each scene's table
ROLES = {
    'sky_top': ('sky', 1.0), 'sky_bot': ('sky', 1.0), 'cloud': ('sky', 0.6), 'sun': ('sky', 1.2),
    'far': ('land', 1.0), 'near': ('land', 1.0), 'ground': ('land', 1.0), 'detail': ('land', 1.0),
    'spark': ('sky', 1.4),
    'ui_on': ('sky', 0.9), 'ui_off': ('land', 1.0), 'shadow': ('land', 1.0),
}
LIGHT = {  # per scene lightness for each role
    'hills':      dict(sky_top=.80, sky_bot=.73, cloud=.90, sun=.91, far=.62, near=.55, ground=.46, detail=.38, spark=.91, ui_on=.92, ui_off=.37, shadow=.22),
    'ocean':      dict(sky_top=.82, sky_bot=.74, cloud=.92, sun=.93, far=.58, near=.50, ground=.42, detail=.86, spark=.93, ui_on=.93, ui_off=.33, shadow=.20),
    'city_night': dict(sky_top=.12, sky_bot=.22, cloud=.30, sun=.90, far=.17, near=.09, ground=.07, detail=.72, spark=.85, ui_on=.90, ui_off=.28, shadow=.03),
    'desert':     dict(sky_top=.84, sky_bot=.76, cloud=.92, sun=.94, far=.66, near=.58, ground=.48, detail=.32, spark=.90, ui_on=.93, ui_off=.36, shadow=.22),
    'forest':     dict(sky_top=.80, sky_bot=.72, cloud=.84, sun=.90, far=.56, near=.40, ground=.32, detail=.24, spark=.90, ui_on=.92, ui_off=.22, shadow=.12),
}
DEFAULT_THEME = {'sky': 0.29, 'land': 0.33, 'sat': 0.20}   # the mellow green


def _hue_mean(samples):
    x = sum(w * math.cos(2 * math.pi * h) for h, w in samples)
    y = sum(w * math.sin(2 * math.pi * h) for h, w in samples)
    return (math.atan2(y, x) / (2 * math.pi)) % 1.0


def theme_from_cover(cover):
    """cover: PIL image (any size). Returns {'sky': hue, 'land': hue, 'sat': s}."""
    im = cover.convert('RGB').resize((64, 64), Image.BOX)
    px = [colorsys.rgb_to_hls(r / 255, g / 255, b / 255) for r, g, b in im.getdata()]
    px.sort(key=lambda t: t[1])
    dark, light = px[:len(px) // 2], px[len(px) // 2:]
    land = _hue_mean([(h, s) for h, l, s in dark if s > 0.12] or [(DEFAULT_THEME['land'], 1)])
    sky = _hue_mean([(h, s) for h, l, s in light if s > 0.12] or [(DEFAULT_THEME['sky'], 1)])
    sat = min(max(sum(s for _, _, s in px) / len(px) * 0.45, 0.16), 0.32)
    return {'sky': sky, 'land': land, 'sat': sat}


def colours(theme, scene):
    out = {}
    for role, (which, sf) in ROLES.items():
        r, g, b = colorsys.hls_to_rgb(theme[which], LIGHT[scene][role], min(theme['sat'] * sf, 0.45))
        out[role] = '#%02X%02X%02X' % (round(r * 255), round(g * 255), round(b * 255))
    return out


# ---------------------------------------------------------------- drawing helpers
def _canvas(c, horizon=70):
    img = Image.new('RGBA', (W, H))
    p = img.load()
    top, bot = ms.hexc(c['sky_top']), ms.hexc(c['sky_bot'])
    for y in range(H):
        for x in range(W):
            p[x, y] = bot if ms.dither(x, y, min(y / float(horizon), 1)) else top
    return img, p


def _fill_below(p, fn, col, y_max=H):
    for x in range(W):
        for y in range(max(0, int(fn(x))), y_max):
            p[x, y] = col


def _disc(p, cx, cy, r, col):
    for y in range(int(cy - r), int(cy + r) + 1):
        for x in range(int(cx - r), int(cx + r) + 1):
            if 0 <= x < W and 0 <= y < H and (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                p[x, y] = col


def _cloud(p, cx, cy, w, col):
    for dx in range(w):
        p[cx + dx, cy] = col
    for dx in range(2, w - 2):
        p[cx + dx, cy - 1] = col
    for dx in range(4, w - 5):
        p[cx + dx, cy - 2] = col


# ---------------------------------------------------------------- scenes
def draw_hills(c):
    img, p = _canvas(c)
    hx = ms.hexc
    _fill_below(p, lambda x: 70 + 5 * math.sin(x / 17.0) + 3 * math.sin(x / 7.3 + 1), hx(c['far']))
    _fill_below(p, lambda x: 82 + 4 * math.sin(x / 23.0 + 2) + 2 * math.sin(x / 9.1), hx(c['near']))
    _fill_below(p, lambda x: 96, hx(c['ground']))
    _cloud(p, 28, 14, 14, hx(c['cloud']))
    _cloud(p, 146, 22, 10, hx(c['cloud']))
    rnd = random.Random(3)
    for _ in range(14):
        x, y = rnd.randrange(4, W - 4), rnd.randrange(99, H - 3)
        for dx, dy in ((0, 0), (-1, 1), (1, 1)):
            p[x + dx, y + dy] = hx(c['detail'])
    for _ in range(6):
        p[rnd.randrange(4, W - 4), rnd.randrange(100, H - 2)] = hx(c['spark'])
    return img


def draw_ocean(c):
    img, p = _canvas(c, horizon=62)
    hx = ms.hexc
    _disc(p, 138, 52, 10, hx(c['sun']))
    _cloud(p, 22, 18, 16, hx(c['cloud']))
    for y in range(62, H):
        for x in range(W):
            t = (y - 62) / 36.0
            p[x, y] = hx(c['near']) if ms.dither(x, y, min(t, 1)) else hx(c['far'])
    rnd = random.Random(11)
    for _ in range(60):                       # wave glints, denser near the sun's path
        y = rnd.randrange(64, 98)
        x = rnd.randrange(0, W - 4) if rnd.random() < .6 else rnd.randrange(124, 152)
        for dx in range(rnd.choice((2, 3, 4))):
            p[x + dx, y] = hx(c['detail'])
    _fill_below(p, lambda x: 99 + 1.5 * math.sin(x / 11.0), hx(c['ground']))
    return img


def draw_city_night(c):
    img, p = _canvas(c, horizon=90)
    hx = ms.hexc
    rnd = random.Random(5)
    for _ in range(55):
        p[rnd.randrange(W), rnd.randrange(60)] = hx(c['spark']) if rnd.random() < .3 else hx(c['cloud'])
    _disc(p, 34, 22, 6, hx(c['sun']))
    _disc(p, 36, 20, 5, hx(c['sky_top']))      # crescent
    for layer, base, col, lit in ((0, 64, 'far', 0.08), (1, 78, 'near', 0.14)):
        x = -rnd.randrange(6)
        while x < W:
            w = rnd.randrange(8, 19)
            top = base + rnd.randrange(-14, 10)
            for bx in range(max(x, 0), min(x + w, W)):
                for by in range(top, H):
                    p[bx, by] = hx(c[col])
            for wy in range(top + 3, H - 6, 3):
                for wx in range(x + 2, x + w - 2, 3):
                    if 0 <= wx < W and rnd.random() < lit:
                        p[wx, wy] = hx(c['detail'])
            x += w + (0 if layer else rnd.randrange(0, 3))
    _fill_below(p, lambda x: 104, hx(c['ground']))
    return img


def draw_desert(c):
    img, p = _canvas(c, horizon=74)
    hx = ms.hexc
    _disc(p, 62, 58, 16, hx(c['sun']))
    _cloud(p, 128, 16, 14, hx(c['cloud']))
    _fill_below(p, lambda x: 72 + 6 * math.sin(x / 26.0 + 1), hx(c['far']))
    _fill_below(p, lambda x: 84 + 7 * math.sin(x / 19.0 + 3), hx(c['near']))
    _fill_below(p, lambda x: 97 + 3 * math.sin(x / 13.0), hx(c['ground']))
    cx, base = 142, int(84 + 7 * math.sin(142 / 19.0 + 3))   # a cactus on the near dune
    for y in range(base - 14, base + 1):
        p[cx, y] = p[cx + 1, y] = hx(c['detail'])
    for y in range(base - 9, base - 5):
        p[cx - 3, y] = hx(c['detail'])
    p[cx - 2, base - 6] = p[cx - 1, base - 6] = hx(c['detail'])
    for y in range(base - 11, base - 7):
        p[cx + 4, y] = hx(c['detail'])
    p[cx + 2, base - 8] = p[cx + 3, base - 8] = hx(c['detail'])
    return img


def draw_forest(c):
    img, p = _canvas(c, horizon=80)
    hx = ms.hexc
    _cloud(p, 120, 18, 16, hx(c['cloud']))
    rnd = random.Random(9)

    def pines(base, hmin, hmax, col, step):
        x = -4
        while x < W + 4:
            h = rnd.randrange(hmin, hmax)
            for k in range(h):
                half = int(k * 0.42) + 1
                for dx in range(-half, half + 1):
                    if 0 <= x + dx < W and 0 <= base - h + k < H:
                        p[x + dx, base - h + k] = col
            x += step + rnd.randrange(-2, 3)
    pines(86, 18, 30, hx(c['far']), 9)
    for y in range(83, 88):                    # a low band of mist between the two rows
        for x in range(W):
            p[x, y] = hx(c['cloud'])
    pines(102, 22, 38, hx(c['near']), 12)
    _fill_below(p, lambda x: 100, hx(c['ground']))
    return img


DRAW = {'hills': draw_hills, 'ocean': draw_ocean, 'city_night': draw_city_night,
        'desert': draw_desert, 'forest': draw_forest}


def render(scene, theme):
    """Returns (PIL image 180x113, colour dict with ui_on / ui_off / shadow / sky_bot)."""
    c = colours(theme, scene)
    return DRAW[scene](c), c
