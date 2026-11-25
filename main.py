#!/usr/bin/env python3
"""news-image-20261124: sum up 24 November 2026 world news in one image.

A deterministic program (Python 3 stdlib only, no network, no external
assets) that draws a newspaper front page of the day's news and writes a
single 1024x1024 PNG to $MAKEFUN_OUTPUT_DIR/image.png.

Everything is drawn programmatically: a hand-rolled PNG encoder (zlib),
a 5x7 bitmap font embedded below, and simple shape primitives.
Run it twice and the output bytes are identical.
"""

import math
import os
import struct
import sys
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
PAPER = (248, 244, 236)
INK = (20, 20, 20)
NAVY = (16, 36, 62)
NAVY_LT = (28, 54, 88)
RED = (180, 35, 24)
GOLD = (201, 162, 39)
GRAY = (90, 90, 90)
RULE = (216, 210, 196)
CARD = (255, 255, 255)
GREEN = (34, 139, 34)
WHITE = (255, 255, 255)
SOFT = (235, 230, 218)

# ---------------------------------------------------------------------------
# 5x7 bitmap font. Each glyph is 7 rows of 5 cells, '#' = on, '.' = off.
# ASCII 32..126. Unknown chars render as a blank. Rows are stored
# separately so a typo can only spoil one row, never the whole glyph.
_FONT_ROWS = {
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '!': ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    '#': (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    '$': ("..#..", ".####", "#.#.#", ".###.", "..#.#", "####.", "..#.."),
    '%': ("##..#", "##.#.", "....#", "...#.", "..#..", ".#.##", "#..##"),
    '&': (".##..", "#..#.", "#..#.", ".#...", "#.#.#", "#..#.", ".##.#"),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '(': ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ')': ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    '*': (".....", ".#.#.", "..#..", "#####", "..#..", ".#.#.", "....."),
    '+': (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    ',': (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    '-': (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    '/': ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    '0': (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    '3': (".###.", "#...#", "....#", "..##.", "....#", "#...#", ".###."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': ("..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."),
    ':': (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ';': (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    '<': ("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    '=': (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    '>': (".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
    '?': (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    '@': (".###.", "#...#", "#.###", "#.#.#", "#.#..", "#....", ".###."),
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    'D': ("###..", "#..#.", "#...#", "#...#", "#...#", "#..#.", "###.."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    'X': ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    'Y': ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    '[': (".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."),
    '\\': ("#....", "#....", ".#...", ".#...", "..#..", "..#..", "...#."),
    ']': (".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."),
    '^': ("..#..", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    '_': (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    '`': ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    'a': (".....", ".....", ".####", "....#", ".####", "#...#", ".####"),
    'b': ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    'c': (".....", ".....", ".###.", "#....", "#....", "#...#", ".###."),
    'd': ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    'e': (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    'f': ("..##.", ".#..#", ".#...", "####.", ".#...", ".#...", ".#..."),
    'g': (".....", ".####", "#...#", "#...#", ".####", "....#", ".###."),
    'h': ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    'i': ("..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."),
    'j': ("...#.", ".....", "..##.", "...#.", "...#.", "...#.", ".##.."),
    'k': ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    'l': (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    'm': (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    'n': (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    'o': (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    'p': (".....", ".....", "####.", "#...#", "#...#", "####.", "#...."),
    'q': (".....", ".....", ".####", "#...#", "#...#", ".####", "....#"),
    'r': (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    's': (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    't': (".#...", ".#...", "####.", ".#...", ".#...", ".#...", "..##."),
    'u': (".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#"),
    'v': (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'w': (".....", ".....", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    'x': (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    'y': (".....", ".....", "#...#", "#...#", ".####", "....#", ".###."),
    'z': (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    '{': ("...##", "..#..", "..#..", ".##..", "..#..", "..#..", "...##"),
    '|': ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    '}': ("##...", "..#..", "..#..", "..##.", "..#..", "..#..", "##..."),
    '~': (".....", ".....", ".##.#", "#.#.#", ".....", ".....", "....."),
}
FONT = {ch: ''.join(rows) for ch, rows in _FONT_ROWS.items()}

# Defensive normalisation: every glyph exactly 35 cells (pad / truncate).
for _ch in list(FONT):
    _g = FONT[_ch]
    FONT[_ch] = (_g + '.' * 35)[:35]


def text_width(text, scale):
    """Pixel width of text at the given scale (6 px per char cell)."""
    return len(text) * 6 * scale


def wrap_text(text, max_w, scale):
    """Greedy word wrap. Returns a list of lines that fit max_w pixels."""
    words = text.split(' ')
    lines = []
    cur = ''
    for word in words:
        trial = word if not cur else cur + ' ' + word
        if text_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------------------
# Canvas: RGB bytearray, origin top-left.
# ---------------------------------------------------------------------------
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def _idx(self, x, y):
        return (y * self.w + x) * 3

    def set_px(self, x, y, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._idx(x, y)
            self.px[i] = rgb[0]
            self.px[i + 1] = rgb[1]
            self.px[i + 2] = rgb[2]

    def fill_rect(self, x, y, w, h, rgb):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(rgb) * (x1 - x0)
        for yy in range(y0, y1):
            i = self._idx(x0, yy)
            self.px[i:i + len(row)] = row

    def rect(self, x, y, w, h, rgb, t=1):
        self.fill_rect(x, y, w, t, rgb)
        self.fill_rect(x, y + h - t, w, t, rgb)
        self.fill_rect(x, y, t, h, rgb)
        self.fill_rect(x + w - t, y, t, h, rgb)

    def hline(self, x, y, w, rgb, t=1):
        self.fill_rect(x, y, w, t, rgb)

    def vline(self, x, y, h, rgb, t=1):
        self.fill_rect(x, y, t, h, rgb)

    def line(self, x0, y0, x1, y1, rgb):
        """Bresenham line, integer only (deterministic)."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set_px(x0, y0, rgb)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, rgb, fill=True):
        if fill:
            for dy in range(-r, r + 1):
                dx = math.isqrt(max(0, r * r - dy * dy))
                self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, rgb)
        else:
            steps = 360
            for i in range(steps):
                a = 2.0 * math.pi * i / steps
                self.set_px(cx + int(r * math.cos(a)),
                            cy + int(r * math.sin(a)), rgb)

    def triangle(self, x0, y0, x1, y1, x2, y2, rgb):
        """Filled triangle, scanline fill with integer interpolation."""
        pts = sorted([(x0, y0), (x1, y1), (x2, y2)], key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy) = pts
        if ay == cy:
            return
        def edge_x(y, p, q):
            if q[1] == p[1]:
                return p[0]
            return p[0] + (q[0] - p[0]) * (y - p[1]) / (q[1] - p[1])
        for y in range(ay, cy + 1):
            if y < by:
                xa = edge_x(y, (ax, ay), (bx, by))
            else:
                xa = edge_x(y, (bx, by), (cx, cy))
            xb = edge_x(y, (ax, ay), (cx, cy))
            lo, hi = (xa, xb) if xa <= xb else (xb, xa)
            self.fill_rect(int(round(lo)), y, int(round(hi)) - int(round(lo)) + 1, 1, rgb)

    def draw_char(self, x, y, ch, scale, rgb):
        g = FONT.get(ch)
        if g is None:
            return
        for row in range(7):
            for col in range(5):
                if g[row * 5 + col] == '#':
                    if scale == 1:
                        self.set_px(x + col, y + row, rgb)
                    else:
                        self.fill_rect(x + col * scale, y + row * scale,
                                       scale, scale, rgb)

    def draw_text(self, x, y, text, scale, rgb):
        cx = x
        for ch in text:
            self.draw_char(cx, y, ch, scale, rgb)
            cx += 6 * scale
        return cx

    def draw_centered(self, y, text, scale, rgb, x0=0, x1=None):
        if x1 is None:
            x1 = self.w
        w = text_width(text, scale)
        self.draw_text(x0 + (x1 - x0 - w) // 2, y, text, scale, rgb)


# ---------------------------------------------------------------------------
# PNG encoder (stdlib zlib). Filter 0 on every scanline; deterministic.
# ---------------------------------------------------------------------------
def png_bytes(canvas):
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)
        raw += canvas.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        out = struct.pack('>I', len(data)) + kind + data
        out += struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack('>IIBBBBB', canvas.w, canvas.h, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', ihdr)
            + chunk(b'IDAT', comp)
            + chunk(b'IEND', b''))


# ---------------------------------------------------------------------------
# Layout: a newspaper front page for Tuesday 24 November 2026.
# ---------------------------------------------------------------------------
M = 28            # side margin
CW = 1024 - 2 * M  # content width = 968


def draw_masthead(c):
    c.fill_rect(0, 0, W, 118, NAVY)
    c.draw_centered(16, "THE WORLD IN ONE PAGE", 5, WHITE)
    c.fill_rect(182, 64, 660, 3, GOLD)
    c.draw_centered(78, "TUESDAY 24 NOVEMBER 2026  |  20 STORIES  |  ONE IMAGE",
                    2, GOLD)


def draw_globe(c, cx, cy, r):
    c.circle(cx, cy, r, NAVY_LT, fill=False)
    c.circle(cx, cy, r, NAVY, fill=False)
    c.hline(cx - r, cy, 2 * r + 1, NAVY, 2)
    c.vline(cx, cy - r, 2 * r + 1, NAVY, 2)
    # meridians: two inner arcs approximated by vertical chords
    for off in (-r // 2, r // 2):
        half = math.isqrt(max(0, r * r - off * off))
        c.vline(cx + off, cy - half, 2 * half + 1, NAVY, 1)
    # latitude arcs
    for off in (-r // 2, r // 2):
        half = math.isqrt(max(0, r * r - off * off))
        c.hline(cx - half, cy + off, 2 * half + 1, NAVY, 1)


def draw_rocket(c, x, y, s):
    # s = unit size; simple side-view rocket, nose up.
    body_w = 6 * s
    body_h = 16 * s
    # flame
    c.triangle(x + s, y + body_h + 10 * s,
               x + 3 * s, y + body_h + 4 * s,
               x + 5 * s, y + body_h + 10 * s, GOLD)
    # fins
    c.triangle(x - 3 * s, y + body_h,
               x, y + body_h - 6 * s,
               x, y + body_h, RED)
    c.triangle(x + body_w + 3 * s, y + body_h,
               x + body_w, y + body_h - 6 * s,
               x + body_w, y + body_h, RED)
    # body
    c.fill_rect(x, y + 4 * s, body_w, body_h, NAVY)
    # nose
    c.triangle(x, y + 4 * s, x + 3 * s, y, x + body_w, y + 4 * s, RED)
    # window
    c.circle(x + 3 * s, y + 10 * s, 2 * s, GOLD, fill=True)


def draw_lead(c):
    y0 = 132
    # --- hero story: ICJ / Myanmar ---
    c.fill_rect(M, y0, 8, 264, RED)
    c.draw_text(M + 20, y0 + 2, "THE HAGUE  |  WORLD COURT", 2, RED)
    c.draw_text(M + 20, y0 + 30, "MYANMAR COMMITTED", 4, INK)
    c.draw_text(M + 20, y0 + 64, "GENOCIDE, COURT RULES", 4, INK)
    deck = [
        "The International Court of Justice rules",
        "Myanmar committed genocide against the",
        "Rohingya. Fourteen nations back the",
        "verdict; Britain adds fresh sanctions.",
    ]
    for i, line in enumerate(deck):
        c.draw_text(M + 20, y0 + 116 + i * 18, line, 2, GRAY)
    draw_globe(c, 566, y0 + 208, 40)
    c.draw_centered(y0 + 252, "THE WORLD COURT SPEAKS", 1, GRAY,
                    x0=500, x1=648)
    # --- vertical divider ---
    c.vline(664, y0, 264, RULE, 2)
    # --- second lead: Shenzhou-24 ---
    c.draw_text(680, y0 + 2, "SPACE  |  TIANGONG", 2, RED)
    c.draw_text(680, y0 + 30, "SHENZHOU-24", 3, INK)
    c.draw_text(680, y0 + 56, "LIFTS OFF WITH", 3, INK)
    c.draw_text(680, y0 + 82, "FIRST FOREIGN", 3, INK)
    c.draw_text(680, y0 + 108, "GUEST ABOARD", 3, INK)
    sdeck = [
        "Two Chinese astronauts and",
        "Pakistan's Zeeshan Ali head",
        "for the Tiangong station -",
        "the first foreign guest",
        "aboard China's space",
        "station.",
    ]
    for i, line in enumerate(sdeck):
        c.draw_text(680, y0 + 140 + i * 18, line, 2, GRAY)
    draw_rocket(c, 946, y0 + 2, 1)
    c.hline(M, 410, CW, INK, 2)


def draw_card(c, x, y, w, h, kicker, headline, summary):
    c.fill_rect(x, y, w, h, CARD)
    c.rect(x, y, w, h, RULE, 1)
    c.draw_text(x + 12, y + 10, kicker, 1, RED)
    lines = wrap_text(headline, w - 24, 2)
    for i, line in enumerate(lines[:2]):
        c.draw_text(x + 12, y + 28 + i * 18, line, 2, INK)
    slines = wrap_text(summary, w - 24, 1)
    base = y + 28 + min(len(lines), 2) * 18 + 4
    for i, line in enumerate(slines[:2]):
        c.draw_text(x + 12, base + i * 10, line, 1, GRAY)


GRID = [
    ("UNITED NATIONS", "Guterres: AI risks need global rules in a year",
     "UN chief calls for a multilateral framework to govern AI."),
    ("TRADE", "US ready to hit China and EU with tariffs",
     "Washington targets subsidised production, AP sources say."),
    ("UKRAINE", "Russian strike kills 2, wounds 48",
     "Kyiv's naval drones hit a Russian warship off Libya."),
    ("YEMEN", "Houthis close in on Aden",
     "Strikes reported on Riyadh as Saudi jets answer."),
    ("GAZA", "Oxfam: Gaza is now 'toxic land'",
     "Israeli strikes kill 3, including a UN worker."),
    ("IRAN", "Singer lashed 74 times over online concert",
     "Tehran rules out talks until US meets 7 conditions."),
    ("COLOMBIA", "25 hostages freed in Cartagena siege",
     "Car bomb rocks Villavicencio the same day."),
    ("VIETNAM", "Hanoi hot-pot blast kills 6",
     "More than a dozen injured in the eatery explosion."),
    ("HEALTH", "Measles epidemic: 9th death in Pennsylvania",
     "Outbreak now spans 46 counties."),
]


def draw_grid(c):
    col_w = 312
    xs = [M, M + col_w + 16, M + 2 * (col_w + 16)]
    ys = [426, 552, 678]
    h = 114
    for i, (kicker, headline, summary) in enumerate(GRID):
        x = xs[i % 3]
        y = ys[i // 3]
        draw_card(c, x, y, col_w, h, kicker, headline, summary)


BRIEF = [
    ("VATICAN", "Pope Francis diary reveals a spiritual crisis and a 'gates of hell' vision."),
    ("USA", "Trump pardons the Thanksgiving turkeys; Democrats clinch a historic House majority."),
    ("BANGLADESH", "Ousted PM Hasina plans her return from exile on 16 December."),
    ("N. KOREA", "Pyongyang demands Switzerland shut its new office; expels a diplomat."),
    ("PACIFIC", "Solomon Islands name Australia their primary security partner."),
    ("NEPAL", "Magnitude 5.6 quake strikes near the China border."),
    ("SPORT & CLIMATE", "COP31 ends with no fossil-fuel call; Senegal regain AFCON; Ronaldo hits 987."),
    ("TECH & SCIENCE", "Nvidia chief reinstated; spy sentenced to death in China; earliest quasar found."),
]


def draw_brief(c):
    y0 = 808
    c.draw_text(M, y0, "IN BRIEF", 2, RED)
    c.hline(M + 96, y0 + 7, CW - 96, RULE, 2)
    col_w = 234
    xs = [M, M + col_w + 12, M + 2 * (col_w + 12), M + 3 * (col_w + 12)]
    ys = [y0 + 26, y0 + 62]
    for i, (tag, text) in enumerate(BRIEF):
        x = xs[i % 4]
        y = ys[i // 4]
        tag_s = tag + " - "
        tag_w = text_width(tag_s, 1)
        c.draw_text(x, y, tag_s, 1, RED)
        # first line shares its row with the tag; later lines use full width
        words = text.split(' ')
        lines = []
        cur = ''
        limit = col_w - tag_w
        for word in words:
            trial = word if not cur else cur + ' ' + word
            if text_width(trial, 1) <= limit or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
                limit = col_w
        if cur:
            lines.append(cur)
        if lines:
            c.draw_text(x + tag_w, y, lines[0], 1, INK)
        for j, line in enumerate(lines[1:3]):
            c.draw_text(x, y + 10 + j * 10, line, 1, INK)


MARKETS = [
    ("S&P 500", "+4.73%", True),
    ("NASDAQ", "+6.51%", True),
    ("NIKKEI", "+3.91%", True),
    ("GOLD", "$3,620.40", True),
    ("BRENT", "$86.70", True),
]


def draw_markets(c):
    y0 = 918
    c.fill_rect(M, y0, CW, 54, NAVY)
    c.draw_text(M + 16, y0 + 20, "MARKETS - 24 NOV CLOSE", 2, GOLD)
    x = M + 300
    for name, val, up in MARKETS:
        c.draw_text(x, y0 + 12, name, 1, (170, 180, 195))
        c.draw_text(x, y0 + 26, val, 2, WHITE)
        # up arrow (small triangle) to the right of the value
        vx = x + text_width(val, 2) + 10
        c.triangle(vx, y0 + 40, vx + 5, y0 + 30, vx + 10, y0 + 40, GREEN)
        x += 136


def draw_footer(c):
    c.draw_centered(986, "THE WORLD IN ONE PAGE  |  TUESDAY 24 NOVEMBER 2026  |  20 STORIES",
                    1, GRAY)


def build():
    c = Canvas(W, H, PAPER)
    c.rect(10, 10, W - 20, H - 20, INK, 2)
    draw_masthead(c)
    draw_lead(c)
    draw_grid(c)
    draw_brief(c)
    draw_markets(c)
    draw_footer(c)
    return c


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "out"
    os.makedirs(out_dir, exist_ok=True)
    canvas = build()
    data = png_bytes(canvas)
    path = os.path.join(out_dir, "image.png")
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes, %dx%d)" % (path, len(data), W, H))
    return 0


if __name__ == "__main__":
    sys.exit(main())
