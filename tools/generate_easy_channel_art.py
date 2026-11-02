"""Easy Channel artwork: add-on icon, header mark and fanart.

Requires Pillow and the Inter font (SIL Open Font License, https://rsms.me/inter/). Run with the folder
that holds Inter-Bold.ttf and Inter-Medium.ttf:

    python3 tools/generate_easy_channel_art.py path/to/inter/extras/ttf
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONTS = sys.argv[1]
ADDON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "script.m3u.channels")
RESOURCES = os.path.join(ADDON, "resources")
MEDIA = os.path.join(RESOURCES, "skins", "default", "media")
BG = (14, 15, 17)
BLUE = (59, 139, 255)
BLUE_DARK = (43, 108, 214)
WHITE = (255, 255, 255)
GREY = (156, 158, 166)
SCALE = 4  # draw large, then reduce for smooth edges


def mark(draw, x, y, size):
    """TV screen with a playlist glyph. (x, y) is the top left of a size x size box."""
    u = size / 512
    p = lambda value: value * u
    box = lambda a, b, c, d: (x + p(a), y + p(b), x + p(c), y + p(d))
    draw.rounded_rectangle(box(76, 92, 436, 360), radius=p(60), fill=BLUE)
    draw.rounded_rectangle(box(230, 372, 282, 400), radius=p(6), fill=BLUE_DARK)
    draw.rounded_rectangle(box(176, 396, 336, 420), radius=p(12), fill=BLUE)
    # Play triangle with rounded corners.
    triangle = [(x + p(144), y + p(176)), (x + p(144), y + p(276)), (x + p(226), y + p(226))]
    draw.polygon(triangle, fill=WHITE)
    draw.line(triangle + [triangle[0]], fill=WHITE, width=round(p(18)), joint="curve")
    for corner in triangle:
        r = p(9)
        draw.ellipse((corner[0] - r, corner[1] - r, corner[0] + r, corner[1] + r), fill=WHITE)
    # List lines, shorter towards the bottom.
    for top, right in ((180, 380), (215, 352), (250, 320)):
        draw.rounded_rectangle(box(256, top, right, top + 22), radius=p(11), fill=WHITE)


def render(width, height, paint, background, mode="RGB"):
    image = Image.new(mode, (width * SCALE, height * SCALE), background)
    paint(ImageDraw.Draw(image), SCALE)
    return image.resize((width, height), Image.LANCZOS)


icon = render(512, 512, lambda d, s: mark(d, 0, 8 * s, 512 * s), BG)
icon.save(os.path.join(RESOURCES, "icon.png"), optimize=True)

logo = render(256, 256, lambda d, s: mark(d, 0, 4 * s, 256 * s), (0, 0, 0, 0), "RGBA")
logo.save(os.path.join(MEDIA, "logo.png"), optimize=True)


def fanart(draw, s):
    mark(draw, 120 * s, 210 * s, 300 * s)
    title = ImageFont.truetype(FONTS + "/Inter-Bold.ttf", 92 * s)
    tagline = ImageFont.truetype(FONTS + "/Inter-Medium.ttf", 34 * s)
    draw.text((452 * s, 268 * s), "Easy Channel", font=title, fill=WHITE)
    draw.text((456 * s, 392 * s), "M3U lists made easy", font=tagline, fill=GREY)
    draw.rounded_rectangle((456 * s, 456 * s, 536 * s, 464 * s), radius=4 * s, fill=BLUE)


render(1280, 720, fanart, BG).save(os.path.join(RESOURCES, "fanart.jpg"), quality=90, optimize=True)
