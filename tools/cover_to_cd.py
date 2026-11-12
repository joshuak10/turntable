"""Cover -> pixel LED CD pipeline (prototype of what the app does at runtime).

1. Take any album cover, scale it to 64x64 with a box filter, quantise to a small palette.
2. For each of FRAMES angles, re-rasterise a CD on a fixed 64x64 grid: the printed
   face samples the cover at the un-rotated position; hub, rim and glint stay fixed.
3. Pixels outside the disc are 'unlit LEDs'.

Usage: python3 cover_to_cd.py OUT_DIR [cover.png ...]
With no covers given it renders three original demo covers.
"""
import math
import os
import sys
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import make_sprites as ms  # reuse art + palette helpers

N, FRAMES = 64, 60          # 6 degrees per frame
C = (N - 1) / 2.0
UNLIT = ms.hexc('#141414')
SILVER, SILVER2, CLEAR1, CLEAR2 = ms.B_SILVER, ms.B_SILVER2, ms.B_CLEAR1, ms.B_CLEAR2


def tide_art(u, v, x, y):
    cream, teal, navy, sand = (ms.hexc('#F2E3C6'), ms.hexc('#6FB3C0'),
                               ms.hexc('#1E3A5F'), ms.hexc('#E9C46A'))
    if (u - 9) ** 2 + (v - 11) ** 2 < 60:
        return sand
    band = int((v + 40 + 3 * math.sin(u / 5.0)) // 6)
    return [navy, teal, cream, teal][band % 4]


def render_cover(art):
    img = Image.new('RGBA', (N, N))
    p = img.load()
    for y in range(N):
        for x in range(N):
            p[x, y] = art(x - C, C - y, x, y)
    return img


def load_cover(path, colors=24):
    """Real covers: box-downscale, then quantise so it reads as pixel art."""
    im = Image.open(path).convert('RGB').resize((N, N), Image.BOX)
    im = im.quantize(colors=colors, dither=Image.FLOYDSTEINBERG).convert('RGBA')
    return im


def cd_sheet(cover, clear=False):
    """clear=False: unlit-LED background (Screen 2). clear=True: transparent outside the disc (Screen 1)."""
    cp = cover.load()
    off = (0, 0, 0, 0) if clear else UNLIT
    sheet = Image.new('RGBA', (N * FRAMES, N), off)
    p = sheet.load()
    for f in range(FRAMES):
        ang = f * 360.0 / FRAMES
        for y in range(N):
            for x in range(N):
                r, th, dx, dy = ms.polar(x, y)
                if r > 31.4 or r < 2.4:
                    col = off
                elif r > 30.0:
                    col = SILVER
                elif r < 6.2:
                    col = CLEAR1 if int(r * 2) % 3 else CLEAR2
                elif r < 7.4:
                    col = SILVER2
                else:
                    u, v = ms.unrotate(dx, dy, ang)
                    sx = min(max(int(round(u + C)), 0), N - 1)
                    sy = min(max(int(round(C - v)), 0), N - 1)
                    col = cp[sx, sy]
                    if ms.in_wedge(th, 40, 56) and 9 < r < 29:
                        col = ms.lighten(col, 0.45)
                    elif ms.in_wedge(th, 222, 230) and 11 < r < 27:
                        col = ms.lighten(col, 0.25)
                p[f * N + x, y] = col
    return sheet


if __name__ == '__main__':
    out = sys.argv[1]
    covers = {}
    if len(sys.argv) > 2:
        for path in sys.argv[2:]:
            covers[os.path.splitext(os.path.basename(path))[0]] = load_cover(path)
    else:
        covers = {'sunset': render_cover(lambda u, v, x, y: ms.sunset_art(u, v, x, y)),
                  'dusk': render_cover(ms.dusk_art),
                  'tide': render_cover(tide_art)}
    prev = Image.new('RGBA', ((N * 4) * 2 * len(covers) + 40 * len(covers), N * 4), (0, 0, 0, 255))
    for i, (name, cover) in enumerate(covers.items()):
        cover.save(f'{out}/cover_{name}.png')
        sheet = cd_sheet(cover)
        sheet.save(f'{out}/cd_{name}.png')
        ox = i * (N * 8 + 40)
        prev.alpha_composite(cover.resize((N * 4, N * 4), Image.NEAREST), (ox, 0))
        prev.alpha_composite(sheet.crop((N * 5, 0, N * 6, N)).resize((N * 4, N * 4), Image.NEAREST), (ox + N * 4, 0))
    prev.save(f'{out}/cd_preview.png')
    print('ok', list(covers))
