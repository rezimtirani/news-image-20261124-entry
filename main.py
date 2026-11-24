#!/usr/bin/env python3
"""The World in One Day — 24 November 2026.

Draws a one-page newspaper front page (1024x1024 PNG) summing up the
world news of Tuesday 24 November 2026, using Pillow only. No network
access, no downloaded images: every glyph is drawn with Pillow shapes.

Run:  python3 main.py
Writes: $MAKEFUN_OUTPUT_DIR/entry.png (default: ./output/entry.png)
        The graded run mounts the repository read-only, so nothing is
        written next to this script.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

PAGE = 1024
MARGIN = 36
INK = (24, 24, 22)
PAPER = (247, 241, 227)
RED = (178, 34, 34)
TEAL = (14, 94, 94)
NAVY = (28, 52, 96)
OCHRE = (164, 104, 12)
GREY = (96, 96, 92)
RULE = (180, 172, 150)

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def load_font(name, size):
    """Load a DejaVu font, falling back to Pillow's built-in bitmap font."""
    try:
        return ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    except OSError:
        return ImageFont.load_default()


SERIF_BIG = lambda s: load_font("DejaVuSerif-Bold.ttf", s)
SERIF = lambda s: load_font("DejaVuSerif.ttf", s)
SANS_B = lambda s: load_font("DejaVuSans-Bold.ttf", s)
SANS = lambda s: load_font("DejaVuSans.ttf", s)


def wrap(draw, text, font, width):
    """Greedy word wrap returning a list of lines fitting `width` pixels."""
    lines, current = [], ""
    for word in text.split():
        trial = (current + " " + word).strip()
        if draw.textlength(trial, font=font) <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_masthead(canvas):
    """Newspaper nameplate, date line and double rule."""
    draw = canvas["draw"]
    draw.text((PAGE // 2, 62), "THE WORLD IN ONE DAY",
              font=SERIF_BIG(64), fill=INK, anchor="mm")
    draw.text((PAGE // 2, 112), "TUESDAY, 24 NOVEMBER 2026  ·  ONE PAGE, THE WHOLE PLANET",
              font=SANS_B(17), fill=RED, anchor="mm")
    draw.line([(MARGIN, 132), (PAGE - MARGIN, 132)], fill=INK, width=4)
    draw.line([(MARGIN, 138), (PAGE - MARGIN, 138)], fill=INK, width=1)


def draw_globe(draw, cx, cy, colour, r=52):
    """Simple globe glyph: circle, meridians and a latitude band."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=colour, width=4)
    draw.ellipse([cx - r // 2, cy - r, cx + r // 2, cy + r], outline=colour, width=3)
    draw.line([(cx - r, cy), (cx + r, cy)], fill=colour, width=3)
    draw.arc([cx - r, cy - r // 2, cx + r, cy + r // 2], 200, 340, fill=colour, width=3)


def draw_ship(draw, cx, cy, colour):
    """Simple warship glyph: hull, deck and a mast."""
    draw.polygon([(cx - 52, cy + 6), (cx + 52, cy + 6), (cx + 38, cy + 26),
                  (cx - 38, cy + 26)], fill=colour)
    draw.rectangle([cx - 26, cy - 14, cx + 14, cy + 6], fill=colour)
    draw.line([(cx + 26, cy - 34), (cx + 26, cy - 12)], fill=colour, width=4)
    draw.line([(cx - 52, cy + 34), (cx + 52, cy + 34)], fill=colour, width=3)
    draw.line([(cx - 40, cy + 42), (cx + 40, cy + 42)], fill=colour, width=2)


def draw_scales(draw, cx, cy, colour):
    """Simple scales-of-justice glyph: post, beam and two pans."""
    draw.line([(cx, cy - 34), (cx, cy + 30)], fill=colour, width=4)
    draw.line([(cx - 44, cy - 26), (cx + 44, cy - 26)], fill=colour, width=4)
    draw.line([(cx - 44, cy - 26), (cx - 44, cy + 2)], fill=colour, width=3)
    draw.line([(cx + 44, cy - 26), (cx + 44, cy + 2)], fill=colour, width=3)
    draw.polygon([(cx - 58, cy + 2), (cx - 30, cy + 2), (cx - 44, cy + 20)], fill=colour)
    draw.polygon([(cx + 30, cy + 2), (cx + 58, cy + 2), (cx + 44, cy + 20)], fill=colour)
    draw.line([(cx - 22, cy + 30), (cx + 22, cy + 30)], fill=colour, width=4)


def draw_chip(draw, cx, cy, colour):
    """Simple microchip glyph: square body, pins and a core."""
    draw.rectangle([cx - 30, cy - 30, cx + 30, cy + 30], outline=colour, width=5)
    draw.rectangle([cx - 14, cy - 14, cx + 14, cy + 14], fill=colour)
    for offset in (-20, 0, 20):
        draw.line([(cx + offset, cy - 44), (cx + offset, cy - 30)], fill=colour, width=4)
        draw.line([(cx + offset, cy + 30), (cx + offset, cy + 44)], fill=colour, width=4)
        draw.line([(cx - 44, cy + offset), (cx - 30, cy + offset)], fill=colour, width=4)
        draw.line([(cx + 30, cy + offset), (cx + 44, cy + offset)], fill=colour, width=4)


GLYPHS = {"globe": draw_globe, "ship": draw_ship, "scales": draw_scales, "chip": draw_chip}

STORIES = [
    {
        "kicker": "CLIMATE  ·  ANTALYA",
        "colour": TEAL,
        "glyph": "globe",
        "headline": "COP31 ENDS WITH NO DEAL",
        "deck": "UN climate talks collapse after a fossil-fuel deadlock; "
                "negotiations may resume next year with nothing agreed.",
    },
    {
        "kicker": "WAR AT SEA  ·  LIBYA",
        "colour": NAVY,
        "glyph": "ship",
        "headline": "UKRAINE SINKS RUSSIAN WARSHIP",
        "deck": "Kyiv says naval drones sank the Merkury off Libya and "
                "damaged a sanctioned cargo ship — the war reaches the Med.",
    },
    {
        "kicker": "JUSTICE  ·  THE HAGUE",
        "colour": OCHRE,
        "glyph": "scales",
        "headline": "COURT: MYANMAR COMMITTED GENOCIDE",
        "deck": "The International Court of Justice rules Myanmar committed "
                "genocide against the Rohingya minority.",
    },
    {
        "kicker": "TECH  ·  WALL STREET",
        "colour": RED,
        "glyph": "chip",
        "headline": "HUANG IS BACK — NVIDIA SOARS",
        "deck": "Jensen Huang returns and Nvidia's value climbs by almost "
                "$1 trillion as tech stocks rally.",
    },
]

ALSO_TODAY = [
    ("GAZA", "Winter storms flood shelters of over a million displaced people in Gaza."),
    ("FOOTBALL", "FIFA Congress picks the hosts for the 2031 and 2035 Women's World Cups."),
    ("NATO", "Allies meet after Russian missiles cross Polish airspace; chief vows defence."),
]


def draw_story_card(canvas, box, story):
    """One hero card: colour band, glyph, kicker, headline and deck."""
    draw = canvas["draw"]
    x0, y0, x1, y1 = box
    draw.rectangle([x0, y0, x1, y1], outline=RULE, width=2)
    draw.rectangle([x0, y0, x1, y0 + 8], fill=story["colour"])
    GLYPHS[story["glyph"]](draw, (x0 + x1) // 2, y0 + 78, story["colour"])
    draw.text(((x0 + x1) // 2, y0 + 152), story["kicker"],
              font=SANS_B(15), fill=story["colour"], anchor="mm")
    headline_font = SERIF_BIG(30)
    for i, line in enumerate(wrap(draw, story["headline"], headline_font, x1 - x0 - 36)):
        draw.text(((x0 + x1) // 2, y0 + 190 + i * 35), line,
                  font=headline_font, fill=INK, anchor="mm")
    deck_font = SERIF(16)
    deck_lines = wrap(draw, story["deck"], deck_font, x1 - x0 - 36)
    for i, line in enumerate(deck_lines[:3]):
        draw.text(((x0 + x1) // 2, y0 + 254 + i * 22), line,
                  font=deck_font, fill=(64, 64, 60), anchor="mm")


def draw_also_today(canvas, y):
    """Three-column strip of supporting stories under the hero grid."""
    draw = canvas["draw"]
    draw.text((PAGE // 2, y + 8), "—  ALSO TODAY  —",
              font=SANS_B(16), fill=RED, anchor="mm")
    col_w = (PAGE - 2 * MARGIN) // 3
    for i, (tag, text) in enumerate(ALSO_TODAY):
        x0 = MARGIN + i * col_w
        draw.text((x0 + 12, y + 40), tag, font=SANS_B(15), fill=INK)
        body_font = SERIF(15)
        for j, line in enumerate(wrap(draw, text, body_font, col_w - 24)[:3]):
            draw.text((x0 + 12, y + 66 + j * 21), line, font=body_font, fill=(64, 64, 60))
        if i:
            draw.line([(x0, y + 36), (x0, y + 140)], fill=RULE, width=1)


def draw_footer(canvas):
    """Source line and the day's sign-off at the bottom of the page."""
    draw = canvas["draw"]
    draw.line([(MARGIN, 958), (PAGE - MARGIN, 958)], fill=INK, width=2)
    draw.text((PAGE // 2, 978),
              "Sources: BBC · AP · The Guardian · Euronews · Reuters  —  drawn with Pillow, no photos",
              font=SANS(13), fill=GREY, anchor="mm")
    draw.text((PAGE // 2, 1000), "THE WORLD IN ONE DAY · 24 NOVEMBER 2026",
              font=SANS_B(12), fill=GREY, anchor="mm")


def build_frontpage():
    """Compose the whole 1024x1024 front page and return the image."""
    image = Image.new("RGB", (PAGE, PAGE), PAPER)
    canvas = {"image": image, "draw": ImageDraw.Draw(image)}
    draw_masthead(canvas)
    grid_top, grid_gap = 150, 16
    cell_w = (PAGE - 2 * MARGIN - grid_gap) // 2
    cell_h = 320
    for i, story in enumerate(STORIES):
        col, row = i % 2, i // 2
        x0 = MARGIN + col * (cell_w + grid_gap)
        y0 = grid_top + row * (cell_h + grid_gap)
        draw_story_card(canvas, (x0, y0, x0 + cell_w, y0 + cell_h), story)
    draw_also_today(canvas, grid_top + 2 * cell_h + grid_gap + 8)
    draw_footer(canvas)
    return image


def verify_png(path):
    """Check the rendered file is a real 1024x1024 PNG under 1 MiB."""
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG file"
    assert data[-12:] == b"\x00\x00\x00\x00IEND\xaeB`\x82", "PNG missing IEND"
    assert len(data) <= 1024 * 1024, "PNG over 1 MiB"
    from PIL import Image as _Image
    with _Image.open(path) as shot:
        assert shot.size == (PAGE, PAGE), "wrong page size: %s" % (shot.size,)
    print("Verified %s: %d bytes, 1024x1024, valid PNG" % (path, len(data)))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)
    image = build_frontpage()
    image.save(os.path.join(out_dir, "entry.png"))
    verify_png(os.path.join(out_dir, "entry.png"))
    print("Wrote entry.png (1024x1024)")


if __name__ == "__main__":
    main()
