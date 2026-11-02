"""HDMI Switcher artwork: add-on icon, header mark, display icon and fanart.

Uses the colors and shapes of Easy Channel's artwork. Requires Pillow and the Inter font (SIL Open Font
License, https://rsms.me/inter/). Run with the folder that holds Inter-Bold.ttf and Inter-Medium.ttf:

    python3 tools/generate_hdmi_switcher_art.py path/to/inter/extras/ttf
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONTS = sys.argv[1]
ADDON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "script.hdmi.switcher")
RESOURCES = os.path.join(ADDON, "resources")
MEDIA = os.path.join(RESOURCES, "skins", "default", "media")
BG = (14, 15, 17)
BLUE = (59, 139, 255)
BLUE_DARK = (43, 108, 214)
WHITE = (255, 255, 255)
GREY = (156, 158, 166)
CLEAR = (0, 0, 0, 0)
SCALE = 4  # draw large, then reduce for smooth edges


def mark(draw, x, y, size, gap=BG):
    """Two displays with switching arrows. (x, y) is the top left of a size x size box.

    gap is the color of the outline that separates the front display from the one behind it.
    """
    u = size / 512
    p = lambda value: value * u
    box = lambda a, b, c, d: (x + p(a), y + p(b), x + p(c), y + p(d))
    point = lambda a, b: (x + p(a), y + p(b))

    def rounded_polygon(points, fill, radius):
        draw.polygon(points, fill=fill)
        draw.line(points + [points[0]], fill=fill, width=round(p(radius * 2)), joint="curve")
        for corner in points:
            r = p(radius)
            draw.ellipse((corner[0] - r, corner[1] - r, corner[0] + r, corner[1] + r), fill=fill)

    def bar(a, b, c, d):
        draw.rounded_rectangle(box(a, b, c, d), radius=p((d - b) / 2), fill=WHITE)

    # Display behind, then the gap and the display in front with its stand.
    draw.rounded_rectangle(box(176, 72, 460, 274), radius=p(46), fill=BLUE_DARK)
    draw.rounded_rectangle(box(40, 150, 392, 398), radius=p(64), fill=gap)
    draw.rounded_rectangle(box(56, 166, 376, 382), radius=p(52), fill=BLUE)
    draw.rounded_rectangle(box(190, 382, 242, 412), radius=p(6), fill=BLUE_DARK)
    draw.rounded_rectangle(box(136, 406, 296, 430), radius=p(12), fill=BLUE)
    # Switching arrows: right on top, left below.
    bar(118, 226, 270, 250)
    rounded_polygon([point(262, 208), point(262, 268), point(306, 238)], WHITE, 6)
    bar(162, 302, 314, 326)
    rounded_polygon([point(170, 284), point(170, 344), point(126, 314)], WHITE, 6)


def display_icon(draw, s):
    """Single color monitor for the display cards, tinted by the skin."""
    draw.rounded_rectangle((10 * s, 16 * s, 118 * s, 92 * s), radius=16 * s, outline=WHITE, width=9 * s)
    draw.rounded_rectangle((56 * s, 92 * s, 72 * s, 104 * s), radius=2 * s, fill=WHITE)
    draw.rounded_rectangle((36 * s, 102 * s, 92 * s, 112 * s), radius=5 * s, fill=WHITE)


def render(width, height, paint, background, mode="RGB"):
    image = Image.new(mode, (width * SCALE, height * SCALE), background)
    paint(ImageDraw.Draw(image), SCALE)
    return image.resize((width, height), Image.LANCZOS)


os.makedirs(MEDIA, exist_ok=True)
icon = render(512, 512, lambda d, s: mark(d, 8 * s, 6 * s, 512 * s), BG)
# New file names make Kodi load this artwork instead of a cached copy of the previous icon.
icon.save(os.path.join(RESOURCES, "hdmi-switcher-icon.png"), optimize=True)

logo = render(256, 256, lambda d, s: mark(d, 4 * s, 3 * s, 256 * s, CLEAR), CLEAR, "RGBA")
logo.save(os.path.join(MEDIA, "logo.png"), optimize=True)

render(128, 128, display_icon, CLEAR, "RGBA").save(os.path.join(MEDIA, "display.png"), optimize=True)


def fanart(draw, s):
    mark(draw, 120 * s, 200 * s, 300 * s)
    title = ImageFont.truetype(FONTS + "/Inter-Bold.ttf", 92 * s)
    tagline = ImageFont.truetype(FONTS + "/Inter-Medium.ttf", 34 * s)
    draw.text((452 * s, 268 * s), "HDMI Switcher", font=title, fill=WHITE)
    draw.text((456 * s, 392 * s), "Pick your display in one click", font=tagline, fill=GREY)
    draw.rounded_rectangle((456 * s, 456 * s, 536 * s, 464 * s), radius=4 * s, fill=BLUE)


render(1280, 720, fanart, BG).save(os.path.join(RESOURCES, "hdmi-switcher-fanart.jpg"), quality=90, optimize=True)
