#!/usr/bin/env python3
"""The World in One Day - 24 November 2026.

A one-page newspaper front page (1024x1024 PNG) summing up the world
news of Tuesday 24 November 2026. Rendered with the standard library
only: the picture lives in a plain RGB bytearray, the letters come from
a built-in 5x7 bitmap font, and the PNG file is encoded by hand with
zlib - no Pillow, no font files, no network, no downloaded images.

Run:  python3 main.py
Writes: $MAKEFUN_OUTPUT_DIR/entry.png (default: ./output/entry.png)
        The graded run mounts the repository read-only, so nothing is
        written next to this script.
"""

import os
import struct
import sys
import zlib

W = 1024
EDGE = 36

INK = (24, 24, 22)
PAPER = (247, 241, 227)
RED = (178, 34, 34)
TEAL = (14, 94, 94)
NAVY = (28, 52, 96)
OCHRE = (164, 104, 12)
GREY = (96, 96, 92)
RULE = (180, 172, 150)
BODY = (64, 64, 60)


class Sheet:
    """An RGB framebuffer with a handful of drawing primitives."""

    def __init__(self, w, h, base):
        self.w = w
        self.h = h
        self.buf = bytearray(bytes(base) * (w * h))

    def _off(self, x, y):
        return (y * self.w + x) * 3

    def dot(self, x, y, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            o = self._off(x, y)
            self.buf[o:o + 3] = bytes(rgb)

    def bar(self, x0, y0, x1, y1, rgb):
        """Filled rectangle with inclusive, clipped bounds."""
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w - 1, x1)
        y1 = min(self.h - 1, y1)
        if x1 < x0 or y1 < y0:
            return
        row = bytes(rgb) * (x1 - x0 + 1)
        for y in range(y0, y1 + 1):
            o = self._off(x0, y)
            self.buf[o:o + len(row)] = row

    def rule_h(self, x0, x1, y, rgb, thick=1):
        self.bar(x0, y - thick // 2, x1, y + (thick - 1) // 2, rgb)

    def rule_v(self, x, y0, y1, rgb, thick=1):
        self.bar(x - thick // 2, y0, x + (thick - 1) // 2, y1, rgb)

    def frame(self, x0, y0, x1, y1, rgb, thick=1):
        """Hollow rectangle outline."""
        self.bar(x0, y0, x1, y0 + thick - 1, rgb)
        self.bar(x0, y1 - thick + 1, x1, y1, rgb)
        self.bar(x0, y0, x0 + thick - 1, y1, rgb)
        self.bar(x1 - thick + 1, y0, x1, y1, rgb)

    def _stamp(self, x, y, rgb, thick):
        half = thick // 2
        self.bar(x - half, y - half, x + (thick - 1) // 2,
                 y + (thick - 1) // 2, rgb)

    def stroke(self, x0, y0, x1, y1, rgb, thick=1):
        """Bresenham line, stamping a thick x thick block per step."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self._stamp(x, y, rgb, thick)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def ring(self, cx, cy, r, rgb, thick=1):
        """Circle outline via the midpoint algorithm."""
        for rr in range(r - thick + 1, r + 1):
            if rr <= 0:
                continue
            x, y = 0, rr
            d = 1 - rr
            while x <= y:
                for sx, sy in ((x, y), (y, x), (-x, y), (-y, x),
                               (x, -y), (y, -x), (-x, -y), (-y, -x)):
                    self.dot(cx + sx, cy + sy, rgb)
                if d < 0:
                    d += 2 * x + 3
                else:
                    d += 2 * (x - y) + 5
                    y -= 1
                x += 1

    def oval(self, cx, cy, rx, ry, rgb, thick=1):
        """Ellipse outline by parametric sampling."""
        import math
        steps = max(48, int(6.28318 * max(rx, ry)))
        for i in range(steps + 1):
            a = 6.28318 * i / steps
            x = int(round(cx + rx * math.cos(a)))
            y = int(round(cy + ry * math.sin(a)))
            self._stamp(x, y, rgb, thick)

    def arc(self, cx, cy, rx, ry, a0, a1, rgb, thick=1):
        """Elliptical arc, angles in degrees."""
        import math
        steps = max(8, int(abs(a1 - a0) * max(rx, ry) / 40.0))
        for i in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * i / steps)
            x = int(round(cx + rx * math.cos(a)))
            y = int(round(cy + ry * math.sin(a)))
            self._stamp(x, y, rgb, thick)

    def poly(self, pts, rgb):
        """Scanline-filled polygon."""
        ys = [p[1] for p in pts]
        ymin = max(0, min(ys))
        ymax = min(self.h - 1, max(ys))
        n = len(pts)
        for y in range(ymin, ymax + 1):
            xs = []
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.bar(int(round(xs[i])), y, int(round(xs[i + 1])), y, rgb)

    def stamp(self, x, y, text, scale, rgb):
        """Blit 5x7 glyphs; x, y is the top-left corner."""
        cx = x
        for ch in text:
            rows = GLYPHS.get(ch, GLYPHS["?"])
            for r, line in enumerate(rows):
                for c, bit in enumerate(line):
                    if bit == "#":
                        self.bar(cx + c * scale, y + r * scale,
                                 cx + c * scale + scale - 1,
                                 y + r * scale + scale - 1, rgb)
            cx += 6 * scale

    def stamp_mid(self, cx, y, text, scale, rgb):
        """Horizontally centred text; y is the top edge."""
        self.stamp(cx - text_w(text, scale) // 2, y, text, scale, rgb)


def text_w(text, scale):
    """Pixel width of a string at the given glyph scale."""
    if not text:
        return 0
    return (len(text) * 6 - 1) * scale


def wrap_text(text, scale, max_w):
    """Greedy word wrap returning lines that fit max_w pixels."""
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if text_w(trial, scale) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines

# Built-in 5x7 bitmap font: each glyph is 7 rows of 5 cells,
# "#" marks ink. Lowercase letters sit on the same 7-row grid with
# descenders on the bottom rows.
GLYPHS = {
    "A": (".###.",
          "#...#",
          "#...#",
          "#####",
          "#...#",
          "#...#",
          "#...#"),
    "B": ("####.",
          "#...#",
          "#...#",
          "####.",
          "#...#",
          "#...#",
          "####."),
    "C": (".####",
          "#....",
          "#....",
          "#....",
          "#....",
          "#....",
          ".####"),
    "D": ("####.",
          "#...#",
          "#...#",
          "#...#",
          "#...#",
          "#...#",
          "####."),
    "E": ("#####",
          "#....",
          "#....",
          "####.",
          "#....",
          "#....",
          "#####"),
    "F": ("#####",
          "#....",
          "#....",
          "####.",
          "#....",
          "#....",
          "#...."),
    "G": (".####",
          "#....",
          "#....",
          "#..##",
          "#...#",
          "#...#",
          ".###."),
    "H": ("#...#",
          "#...#",
          "#...#",
          "#####",
          "#...#",
          "#...#",
          "#...#"),
    "I": ("#####",
          "..#..",
          "..#..",
          "..#..",
          "..#..",
          "..#..",
          "#####"),
    "J": ("..###",
          "...#.",
          "...#.",
          "...#.",
          "...#.",
          "#..#.",
          ".##.."),
    "K": ("#...#",
          "#..#.",
          "#.#..",
          "##...",
          "#.#..",
          "#..#.",
          "#...#"),
    "L": ("#....",
          "#....",
          "#....",
          "#....",
          "#....",
          "#....",
          "#####"),
    "M": ("#...#",
          "##.##",
          "#.#.#",
          "#.#.#",
          "#...#",
          "#...#",
          "#...#"),
    "N": ("#...#",
          "##..#",
          "#.#.#",
          "#..##",
          "#...#",
          "#...#",
          "#...#"),
    "O": (".###.",
          "#...#",
          "#...#",
          "#...#",
          "#...#",
          "#...#",
          ".###."),
    "P": ("####.",
          "#...#",
          "#...#",
          "####.",
          "#....",
          "#....",
          "#...."),
    "Q": (".###.",
          "#...#",
          "#...#",
          "#...#",
          "#.#.#",
          "#..#.",
          ".##.#"),
    "R": ("####.",
          "#...#",
          "#...#",
          "####.",
          "#.#..",
          "#..#.",
          "#...#"),
    "S": (".####",
          "#....",
          "#....",
          ".###.",
          "....#",
          "....#",
          "####."),
    "T": ("#####",
          "..#..",
          "..#..",
          "..#..",
          "..#..",
          "..#..",
          "..#.."),
    "U": ("#...#",
          "#...#",
          "#...#",
          "#...#",
          "#...#",
          "#...#",
          ".###."),
    "V": ("#...#",
          "#...#",
          "#...#",
          "#...#",
          "#...#",
          ".#.#.",
          "..#.."),
    "W": ("#...#",
          "#...#",
          "#...#",
          "#.#.#",
          "#.#.#",
          "##.##",
          "#...#"),
    "X": ("#...#",
          "#...#",
          ".#.#.",
          "..#..",
          ".#.#.",
          "#...#",
          "#...#"),
    "Y": ("#...#",
          "#...#",
          ".#.#.",
          "..#..",
          "..#..",
          "..#..",
          "..#.."),
    "Z": ("#####",
          "....#",
          "...#.",
          "..#..",
          ".#...",
          "#....",
          "#####"),
    "0": (".###.",
          "#...#",
          "#..##",
          "#.#.#",
          "##..#",
          "#...#",
          ".###."),
    "1": ("..#..",
          ".##..",
          "..#..",
          "..#..",
          "..#..",
          "..#..",
          ".###."),
    "2": (".###.",
          "#...#",
          "....#",
          "...#.",
          "..#..",
          ".#...",
          "#####"),
    "3": ("####.",
          "....#",
          "....#",
          ".###.",
          "....#",
          "....#",
          "####."),
    "4": ("...#.",
          "..##.",
          ".#.#.",
          "#..#.",
          "#####",
          "...#.",
          "...#."),
    "5": ("#####",
          "#....",
          "####.",
          "....#",
          "....#",
          "#...#",
          ".###."),
    "6": (".###.",
          "#....",
          "#....",
          "####.",
          "#...#",
          "#...#",
          ".###."),
    "7": ("#####",
          "....#",
          "...#.",
          "..#..",
          "..#..",
          "..#..",
          "..#.."),
    "8": (".###.",
          "#...#",
          "#...#",
          ".###.",
          "#...#",
          "#...#",
          ".###."),
    "9": (".###.",
          "#...#",
          "#...#",
          ".####",
          "....#",
          "....#",
          ".###."),
    "a": (".....",
          ".....",
          ".###.",
          "....#",
          ".####",
          "#...#",
          ".####"),
    "b": ("#....",
          "#....",
          "####.",
          "#...#",
          "#...#",
          "#...#",
          "####."),
    "c": (".....",
          ".....",
          ".####",
          "#....",
          "#....",
          "#....",
          ".####"),
    "d": ("....#",
          "....#",
          ".####",
          "#...#",
          "#...#",
          "#...#",
          ".####"),
    "e": (".....",
          ".....",
          ".###.",
          "#...#",
          "#####",
          "#....",
          ".###."),
    "f": ("..##.",
          ".#...",
          ".#...",
          "####.",
          ".#...",
          ".#...",
          ".#..."),
    "g": (".....",
          ".....",
          ".####",
          "#...#",
          "#...#",
          ".####",
          "....#"),
    "h": ("#....",
          "#....",
          "####.",
          "#...#",
          "#...#",
          "#...#",
          "#...#"),
    "i": ("..#..",
          ".....",
          ".##..",
          "..#..",
          "..#..",
          "..#..",
          ".###."),
    "j": ("...#.",
          ".....",
          "..##.",
          "...#.",
          "...#.",
          "...#.",
          "#.#.."),
    "k": ("#....",
          "#....",
          "#..#.",
          "#.#..",
          "##...",
          "#.#..",
          "#..#."),
    "l": (".##..",
          "..#..",
          "..#..",
          "..#..",
          "..#..",
          "..#..",
          ".###."),
    "m": (".....",
          ".....",
          "##.#.",
          "#.#.#",
          "#.#.#",
          "#.#.#",
          "#.#.#"),
    "n": (".....",
          ".....",
          "####.",
          "#...#",
          "#...#",
          "#...#",
          "#...#"),
    "o": (".....",
          ".....",
          ".###.",
          "#...#",
          "#...#",
          "#...#",
          ".###."),
    "p": (".....",
          ".....",
          "####.",
          "#...#",
          "#...#",
          "####.",
          "#...."),
    "q": (".....",
          ".....",
          ".####",
          "#...#",
          "#...#",
          ".####",
          "....#"),
    "r": (".....",
          ".....",
          "#.##.",
          "##..#",
          "#....",
          "#....",
          "#...."),
    "s": (".....",
          ".....",
          ".####",
          "#....",
          ".###.",
          "....#",
          "####."),
    "t": (".#...",
          ".#...",
          "####.",
          ".#...",
          ".#...",
          ".#...",
          "..##."),
    "u": (".....",
          ".....",
          "#...#",
          "#...#",
          "#...#",
          "#..##",
          ".##.#"),
    "v": (".....",
          ".....",
          "#...#",
          "#...#",
          "#...#",
          ".#.#.",
          "..#.."),
    "w": (".....",
          ".....",
          "#...#",
          "#.#.#",
          "#.#.#",
          "#.#.#",
          ".#.#."),
    "x": (".....",
          ".....",
          "#...#",
          ".#.#.",
          "..#..",
          ".#.#.",
          "#...#"),
    "y": (".....",
          ".....",
          "#...#",
          "#...#",
          "#...#",
          ".####",
          "....#"),
    "z": (".....",
          ".....",
          "#####",
          "...#.",
          "..#..",
          ".#...",
          "#####"),
    " ": (".....",
          ".....",
          ".....",
          ".....",
          ".....",
          ".....",
          "....."),
    ".": (".....",
          ".....",
          ".....",
          ".....",
          ".....",
          ".##..",
          ".##.."),
    ",": (".....",
          ".....",
          ".....",
          ".....",
          ".##..",
          ".##..",
          ".#..."),
    ":": (".....",
          ".##..",
          ".##..",
          ".....",
          ".##..",
          ".##..",
          "....."),
    ";": (".....",
          ".##..",
          ".##..",
          ".....",
          ".##..",
          ".##..",
          ".#..."),
    "!": ("..#..",
          "..#..",
          "..#..",
          "..#..",
          "..#..",
          ".....",
          "..#.."),
    "?": (".###.",
          "#...#",
          "....#",
          "...#.",
          "..#..",
          ".....",
          "..#.."),
    "'": ("..#..",
          "..#..",
          ".#...",
          ".....",
          ".....",
          ".....",
          "....."),
    '"': (".#.#.",
          ".#.#.",
          ".#.#.",
          ".....",
          ".....",
          ".....",
          "....."),
    "-": (".....",
          ".....",
          ".....",
          "#####",
          ".....",
          ".....",
          "....."),
    "/": ("....#",
          "....#",
          "...#.",
          "..#..",
          ".#...",
          "#....",
          "#...."),
    "(": ("...##",
          "..#..",
          ".#...",
          ".#...",
          ".#...",
          "..#..",
          "...##"),
    ")": ("##...",
          "..#..",
          "...#.",
          "...#.",
          "...#.",
          "..#..",
          "##..."),
    "&": (".##..",
          "#..#.",
          "#..#.",
          ".#...",
          "#.#.#",
          "#..#.",
          ".##.#"),
    "$": ("..#..",
          ".####",
          "#.#..",
          ".###.",
          "..#.#",
          "####.",
          "..#.."),
    "%": ("#...#",
          "#..#.",
          "...#.",
          "..#..",
          ".#...",
          "#..#.",
          "#...#"),
    "+": (".....",
          "..#..",
          "..#..",
          "#####",
          "..#..",
          "..#..",
          "....."),
    "=": (".....",
          ".....",
          "#####",
          ".....",
          "#####",
          ".....",
          "....."),
    "*": (".....",
          "#.#.#",
          ".###.",
          "#####",
          ".###.",
          "#.#.#",
          "....."),
    "_": (".....",
          ".....",
          ".....",
          ".....",
          ".....",
          ".....",
          "#####"),
    "@": (".###.",
          "#...#",
          "#.###",
          "#.#.#",
          "#.#..",
          "#....",
          ".###."),
    "#": (".#.#.",
          ".#.#.",
          "#####",
          ".#.#.",
          "#####",
          ".#.#.",
          ".#.#."),
    "·": (".....",
          ".....",
          ".....",
          ".##..",
          ".##..",
          ".....",
          "....."),
    "•": (".....",
          ".....",
          ".....",
          ".##..",
          ".##..",
          ".....",
          "....."),
    "—": (".....",
          ".....",
          ".....",
          "#####",
          ".....",
          ".....",
          "....."),
    "–": (".....",
          ".....",
          ".....",
          "#####",
          ".....",
          ".....",
          "....."),
    "’": ("..#..",
          "..#..",
          ".#...",
          ".....",
          ".....",
          ".....",
          "....."),
    "‘": ("..#..",
          "..#..",
          ".#...",
          ".....",
          ".....",
          ".....",
          "....."),
    "“": (".#.#.",
          ".#.#.",
          ".#.#.",
          ".....",
          ".....",
          ".....",
          "....."),
    "”": (".#.#.",
          ".#.#.",
          ".#.#.",
          ".....",
          ".....",
          ".....",
          "....."),
    "…": (".....",
          ".....",
          ".....",
          ".....",
          ".....",
          ".##..",
          ".##.."),
}

def paint_globe(page, cx, cy, hue):
    """Globe mark: rim, meridians and a latitude band."""
    page.ring(cx, cy, 40, hue, 4)
    page.oval(cx, cy, 20, 40, hue, 3)
    page.rule_h(cx - 40, cx + 40, cy, hue, 3)
    page.arc(cx, cy, 40, 20, 200, 340, hue, 3)


def paint_ship(page, cx, cy, hue):
    """Warship mark: hull, deck, mast and two water lines."""
    page.poly([(cx - 40, cy + 5), (cx + 40, cy + 5),
               (cx + 30, cy + 20), (cx - 30, cy + 20)], hue)
    page.bar(cx - 20, cy - 11, cx + 11, cy + 5, hue)
    page.stroke(cx + 20, cy - 26, cx + 20, cy - 9, hue, 4)
    page.rule_h(cx - 40, cx + 40, cy + 26, hue, 3)
    page.rule_h(cx - 31, cx + 31, cy + 32, hue, 2)


def paint_scales(page, cx, cy, hue):
    """Scales-of-justice mark: post, beam, hangers and two pans."""
    page.stroke(cx, cy - 26, cx, cy + 24, hue, 4)
    page.stroke(cx - 34, cy - 20, cx + 34, cy - 20, hue, 4)
    page.stroke(cx - 34, cy - 20, cx - 34, cy + 2, hue, 3)
    page.stroke(cx + 34, cy - 20, cx + 34, cy + 2, hue, 3)
    page.poly([(cx - 45, cy + 2), (cx - 23, cy + 2), (cx - 34, cy + 16)], hue)
    page.poly([(cx + 23, cy + 2), (cx + 45, cy + 2), (cx + 34, cy + 16)], hue)
    page.rule_h(cx - 17, cx + 17, cy + 24, hue, 4)


def paint_chip(page, cx, cy, hue):
    """Microchip mark: square body, core and pins on four sides."""
    page.frame(cx - 24, cy - 24, cx + 24, cy + 24, hue, 4)
    page.bar(cx - 11, cy - 11, cx + 11, cy + 11, hue)
    for off in (-16, 0, 16):
        page.rule_v(cx + off, cy - 35, cy - 24, hue, 4)
        page.rule_v(cx + off, cy + 24, cy + 35, hue, 4)
        page.rule_h(cx - 35, cx - 24, cy + off, hue, 4)
        page.rule_h(cx + 24, cx + 35, cy + off, hue, 4)


MARKS = {"globe": paint_globe, "ship": paint_ship,
         "scales": paint_scales, "chip": paint_chip}

NEWS = [
    {
        "tag": "CLIMATE  ·  ANTALYA",
        "hue": TEAL,
        "mark": "globe",
        "head": "COP31 ENDS WITH NO DEAL",
        "body": "UN climate talks collapse after a fossil-fuel deadlock; "
                "negotiations may resume next year with nothing agreed.",
    },
    {
        "tag": "WAR AT SEA  ·  LIBYA",
        "hue": NAVY,
        "mark": "ship",
        "head": "UKRAINE SINKS RUSSIAN WARSHIP",
        "body": "Kyiv says naval drones sank the Merkury off Libya and "
                "damaged a sanctioned cargo ship — the war reaches the Med.",
    },
    {
        "tag": "JUSTICE  ·  THE HAGUE",
        "hue": OCHRE,
        "mark": "scales",
        "head": "COURT: MYANMAR COMMITTED GENOCIDE",
        "body": "The International Court of Justice rules Myanmar committed "
                "genocide against the Rohingya minority.",
    },
    {
        "tag": "TECH  ·  WALL STREET",
        "hue": RED,
        "mark": "chip",
        "head": "HUANG IS BACK — NVIDIA SOARS",
        "body": "Jensen Huang returns and Nvidia's value climbs by almost "
                "$1 trillion as tech stocks rally.",
    },
]

ALSO = [
    {"tag": "GAZA",
     "text": "Winter storms flood shelters of over a million displaced "
             "people in Gaza."},
    {"tag": "FOOTBALL",
     "text": "FIFA Congress picks the hosts for the 2031 and 2035 "
             "Women's World Cups."},
    {"tag": "NATO",
     "text": "Allies meet after Russian missiles cross Polish airspace; "
             "chief vows defence."},
]


def paint_masthead(page):
    """Nameplate, date line and double rule."""
    page.stamp_mid(W // 2, 36, "THE WORLD IN ONE DAY", 7, INK)
    page.stamp_mid(W // 2, 100,
                   "TUESDAY, 24 NOVEMBER 2026  ·  ONE PAGE, THE WHOLE PLANET",
                   2, RED)
    page.rule_h(EDGE, W - EDGE, 132, INK, 4)
    page.rule_h(EDGE, W - EDGE, 138, INK, 1)


def paint_card(page, box, story):
    """One hero card: colour band, mark, tag, headline and deck."""
    x0, y0, x1, y1 = box
    page.frame(x0, y0, x1, y1, RULE, 2)
    page.bar(x0, y0, x1, y0 + 8, story["hue"])
    cx = (x0 + x1) // 2
    MARKS[story["mark"]](page, cx, y0 + 62, story["hue"])
    page.stamp_mid(cx, y0 + 116, story["tag"], 2, story["hue"])
    head_lines = wrap_text(story["head"], 4, x1 - x0 - 36)
    for i, line in enumerate(head_lines[:2]):
        page.stamp_mid(cx, y0 + 140 + i * 33, line, 4, INK)
    deck_lines = wrap_text(story["body"], 2, x1 - x0 - 36)
    for i, line in enumerate(deck_lines[:4]):
        page.stamp_mid(cx, y0 + 210 + i * 20, line, 2, BODY)


def paint_also(page, y):
    """Three-column strip of supporting stories under the hero grid."""
    page.stamp_mid(W // 2, y + 8, "—  ALSO TODAY  —", 2, RED)
    col_w = (W - 2 * EDGE) // 3
    for i, item in enumerate(ALSO):
        x0 = EDGE + i * col_w
        page.stamp(x0 + 12, y + 40, item["tag"], 2, INK)
        body_lines = wrap_text(item["text"], 2, col_w - 24)
        for j, line in enumerate(body_lines[:4]):
            page.stamp(x0 + 12, y + 66 + j * 19, line, 2, BODY)
        if i:
            page.rule_v(x0, y + 36, y + 134, RULE, 1)


def paint_footer(page):
    """Source line and the day's sign-off at the bottom of the page."""
    page.rule_h(EDGE, W - EDGE, 958, INK, 2)
    page.stamp_mid(W // 2, 971,
                   "Sources: BBC · AP · The Guardian · Euronews · Reuters",
                   2, GREY)
    page.stamp_mid(W // 2, 993, "THE WORLD IN ONE DAY · 24 NOVEMBER 2026",
                   2, GREY)


def compose_page():
    """Lay out the whole 1024x1024 front page on a fresh sheet."""
    page = Sheet(W, W, PAPER)
    paint_masthead(page)
    top, gap = 150, 16
    cell_w = (W - 2 * EDGE - gap) // 2
    cell_h = 320
    for i, story in enumerate(NEWS):
        col, row = i % 2, i // 2
        x0 = EDGE + col * (cell_w + gap)
        y0 = top + row * (cell_h + gap)
        paint_card(page, (x0, y0, x0 + cell_w, y0 + cell_h), story)
    paint_also(page, top + 2 * cell_h + gap + 8)
    paint_footer(page)
    return page


def _chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return out


def encode_png(sheet):
    """Encode the sheet as a PNG: raw scanlines, zlib, IHDR/IDAT/IEND."""
    raw = bytearray()
    row_bytes = sheet.w * 3
    for y in range(sheet.h):
        raw.append(0)
        raw += sheet.buf[y * row_bytes:(y + 1) * row_bytes]
    comp = zlib.compress(bytes(raw), 6)
    ihdr = struct.pack(">IIBBBBB", sheet.w, sheet.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", comp) + _chunk(b"IEND", b""))


def check_png(path):
    """Stdlib-only check: PNG signature, IEND, size, 1024x1024."""
    with open(path, "rb") as fh:
        data = fh.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG file"
    assert data[-12:] == b"\x00\x00\x00\x00IEND\xaeB`\x82", "PNG missing IEND"
    assert len(data) <= 1024 * 1024, "PNG over 1 MiB"
    w, h = struct.unpack(">II", data[16:24])
    assert (w, h) == (W, W), "wrong page size: %dx%d" % (w, h)
    print("Verified %s: %d bytes, 1024x1024, valid PNG" % (path, len(data)))


def run():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)
    data = encode_png(compose_page())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(data)
    check_png(path)
    print("Wrote entry.png (1024x1024)")


if __name__ == "__main__":
    run()
