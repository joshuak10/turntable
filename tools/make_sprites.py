"""Generate pixel-art rotating disc sprite sheets and backdrops for the Turntable canvas.

Each disc is re-rasterised on a fixed 64x64 grid for every frame (like an LED panel),
so the pixels never rotate - only the artwork moves across them.
"""
import math
import sys
from PIL import Image

N = 64            # grid size
FRAMES = 36       # 10 degrees per frame -> 1.8 s per turn = 33 1/3 rpm
C = (N - 1) / 2.0


def hexc(h, a=255):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


CLEAR = (0, 0, 0, 0)
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def dither(x, y, t):
    """True if a pixel at (x, y) should take the 'next' colour for blend t in 0..1."""
    return t * 16 > BAYER[y % 4][x % 4] + 0.5


def polar(x, y):
    dx, dy = x - C, C - y          # y up
    r = math.hypot(dx, dy)
    th = math.degrees(math.atan2(dy, dx)) % 360
    return r, th, dx, dy


def unrotate(dx, dy, ang):
    """Map a screen pixel back into the disc's own coordinates for rotation ang (clockwise)."""
    a = math.radians(ang)
    u = dx * math.cos(a) - dy * math.sin(a)
    v = dx * math.sin(a) + dy * math.cos(a)
    return u, v


def in_wedge(th, a0, a1):
    return a0 <= th <= a1


# ---------------- A: vinyl, label art rotates, grooves + sheen fixed -------------
A_BASE, A_RING, A_GAP, A_RIM = hexc('#17141C'), hexc('#241F2C'), hexc('#0E0C12'), hexc('#2E2938')
A_HI1, A_HI2 = hexc('#4A4357'), hexc('#363042')
A_CORAL, A_NAVY, A_CREAM, A_DEEP = hexc('#E07A5F'), hexc('#3D5A80'), hexc('#F2E3C6'), hexc('#24395A')


def vinyl_px(x, y, ang):
    r, th, dx, dy = polar(x, y)
    if r > 31.4:
        return CLEAR
    if r > 30.2:
        return A_RIM
    if r > 13.2:
        ring = int(r) % 3 == 0
        gap = int(r) in (19, 25)
        col = A_GAP if gap else (A_RING if ring else A_BASE)
        if in_wedge(th, 38, 62) and 14.5 < r < 29.5 and not gap:
            col = A_HI1 if ring else A_HI2
        elif in_wedge(th, 218, 236) and 16 < r < 28 and ring and not gap:
            col = A_HI2
        return col
    if r < 1.6:
        return CLEAR                       # spindle hole
    u, v = unrotate(dx, dy, ang)
    if r > 12.2:
        return A_DEEP                      # label edge
    if abs(v) < 1.3:
        return A_CREAM                     # band across the label
    if v > 0:
        if (u - 5) ** 2 + (v - 6) ** 2 < 4.5:
            return A_CREAM                 # small mark, makes the turn readable
        return A_CORAL
    return A_NAVY


# ---------------- B: printed CD, print rotates, hub + sheen fixed ------------------
B_SKY = [hexc('#F6C453'), hexc('#F29E4C'), hexc('#E8743F'), hexc('#C8553D')]
B_SUN, B_SEA, B_SEA2, B_FOAM = hexc('#FFF1C9'), hexc('#2F5D62'), hexc('#1F3D36'), hexc('#A7D3C9')
B_SILVER, B_SILVER2, B_CLEAR1, B_CLEAR2, B_WHITE = (
    hexc('#C9CED8'), hexc('#9AA2B1'), hexc('#E3E7EE'), hexc('#B8C0CC'), hexc('#FFFFFF'))


def sunset_art(u, v, x, y, scale=1.0):
    """Shared print art in art coordinates (u right, v up), roughly -31..31."""
    u, v = u / scale, v / scale
    if v < -6:
        if int((u * 0.5 + v * 1.0)) % 5 == 0 and v > -20:
            return B_FOAM
        return B_SEA if v > -16 else B_SEA2
    if (u + 8) ** 2 + (v - 6) ** 2 < 110:
        return B_SUN
    t = min(max((v + 6) / 34.0, 0), 0.999) * (len(B_SKY) - 1)
    i = int(t)
    nxt = min(i + 1, len(B_SKY) - 1)
    return B_SKY[nxt] if dither(x, y, t - i) else B_SKY[i]


def lighten(c, k):
    return tuple(int(c[i] + (255 - c[i]) * k) for i in range(3)) + (c[3],)


def cd_px(x, y, ang, art=sunset_art, panel_bg=None):
    r, th, dx, dy = polar(x, y)
    bg = panel_bg if panel_bg else CLEAR
    if r > 31.4:
        return bg
    if r > 30.0:
        return B_SILVER
    if r < 2.4:
        return bg                           # hole
    if r < 6.2:
        return B_CLEAR1 if int(r * 2) % 3 else B_CLEAR2
    if r < 7.4:
        return B_SILVER2
    u, v = unrotate(dx, dy, ang)
    col = art(u, v, x, y)
    if in_wedge(th, 40, 56) and 9 < r < 29:
        col = lighten(col, 0.45)            # fixed glint
    elif in_wedge(th, 222, 230) and 11 < r < 27:
        col = lighten(col, 0.25)
    return col


# ---------------- C: LED panel CD with a dusk print ------------------------------
C_BANDS = [hexc('#2B1B4F'), hexc('#5B2A86'), hexc('#A23B9C'), hexc('#E0607E'), hexc('#F59E7A')]
C_MOON, C_GRID, C_GROUND, C_UNLIT = hexc('#FDF0D5'), hexc('#3BD1C8'), hexc('#120A24'), hexc('#141414')


def dusk_art(u, v, x, y):
    if v < -4:
        # perspective grid on the ground
        depth = (-v + 1)
        if int(depth) % 6 == 0 or abs((u / (depth * 0.22 + 0.8)) % 4) < 0.5:
            return C_GRID
        return C_GROUND
    if (u - 7) ** 2 + (v - 12) ** 2 < 42:
        return C_MOON
    t = min(max((v + 4) / 30.0, 0), 0.999)
    t = (1 - t) * (len(C_BANDS) - 1)
    i = int(t)
    nxt = min(i + 1, len(C_BANDS) - 1)
    return C_BANDS[nxt] if dither(x, y, t - i) else C_BANDS[i]


def sheet(px_fn, **kw):
    img = Image.new('RGBA', (N * FRAMES, N), CLEAR)
    p = img.load()
    for f in range(FRAMES):
        ang = f * 360.0 / FRAMES
        for y in range(N):
            for x in range(N):
                p[f * N + x, y] = px_fn(x, y, ang, **kw)
    return img


def sleeve():
    img = Image.new('RGBA', (N, N), CLEAR)
    p = img.load()
    for y in range(N):
        for x in range(N):
            if x in (0, N - 1) or y in (0, N - 1):
                p[x, y] = hexc('#1A0F0A')
                continue
            p[x, y] = sunset_art(x - C, C - y, x, y, scale=1.0)
    # small title block, bottom left
    for y in range(52, 59):
        for x in range(5, 27):
            if y in (52, 58) or x in (5, 26):
                continue
            p[x, y] = hexc('#F2E3C6') if (x - 7) % 3 != 2 and y in (54, 56) else p[x, y]
    return img


def night_backdrop(w=180, h=113):
    top, bot = hexc('#0E0B1A'), hexc('#2A1B45')
    mid = hexc('#1B1430')
    img = Image.new('RGBA', (w, h))
    p = img.load()
    import random
    rnd = random.Random(7)
    stars = {(rnd.randrange(w), rnd.randrange(int(h * 0.7))) for _ in range(70)}
    for y in range(h):
        t = y / (h - 1)
        if t < 0.5:
            a, b, tt = top, mid, t / 0.5
        else:
            a, b, tt = mid, bot, (t - 0.5) / 0.5
        for x in range(w):
            p[x, y] = b if dither(x, y, tt) else a
    for (x, y) in stars:
        p[x, y] = hexc('#C9BEE8') if (x + y) % 5 else hexc('#FFFFFF')
    return img


if __name__ == '__main__':
    OUT = sys.argv[1]
    sheet(vinyl_px).save(f'{OUT}/a_vinyl.png')
    night_backdrop().save(f'{OUT}/a_bg.png')
    sheet(cd_px).save(f'{OUT}/b_cd.png')
    sleeve().save(f'{OUT}/b_sleeve.png')
    sheet(cd_px, art=dusk_art, panel_bg=C_UNLIT).save(f'{OUT}/c_led.png')
    # preview strip: frame 0 and 4 of each, scaled 6x
    prev = Image.new('RGBA', (N * 6 * 3 + 40, N * 6), (40, 40, 40, 255))
    for i, name in enumerate(['a_vinyl', 'b_cd', 'c_led']):
        s = Image.open(f'{OUT}/{name}.png').crop((N * 4, 0, N * 5, N)).resize((N * 6, N * 6), Image.NEAREST)
        prev.alpha_composite(s, (i * (N * 6 + 20), 0))
    prev.save(f'{OUT}/preview.png')
    print('ok')
