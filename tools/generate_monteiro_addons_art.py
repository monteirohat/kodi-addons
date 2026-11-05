"""Monteiro Add-ons artwork: add-on icon, header mark and fanart, with the icons it shares with the other add-ons.

Uses the colors and shapes of the Easy add-ons. Requires Pillow and the Inter font (SIL Open Font License,
https://rsms.me/inter/). Run with the folder that holds Inter-Bold.ttf and Inter-Medium.ttf:

    python3 tools/generate_monteiro_addons_art.py path/to/inter/extras/ttf
"""

import os
import shutil
import sys

from PIL import Image, ImageDraw, ImageFont

FONTS = sys.argv[1]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ADDON = os.path.join(ROOT, "script.monteiro.addons")
RESOURCES = os.path.join(ADDON, "resources")
MEDIA = os.path.join(RESOURCES, "skins", "default", "media")
BG = (14, 15, 17)
BLUE = (59, 139, 255)
BLUE_DARK = (43, 108, 214)
WHITE = (255, 255, 255)
GREY = (156, 158, 166)
GREEN = (46, 160, 67)
SCALE = 4  # draw large, then reduce for smooth edges


def mark(draw, x, y, size):
    """A blue box with its lid open, and a white puzzle piece coming out of it. (x, y) is the top left of a size x size box."""
    u = size / 512
    p = lambda value: value * u
    box = lambda a, b, c, d: (x + p(a), y + p(b), x + p(c), y + p(d))
    # The lid behind the piece, then the piece, then the front of the box over its lower part.
    draw.rounded_rectangle(box(80, 196, 432, 260), radius=p(24), fill=BLUE_DARK)
    draw.rounded_rectangle(box(176, 92, 336, 252), radius=p(26), fill=WHITE)
    draw.ellipse(box(222, 52, 290, 120), fill=WHITE)
    draw.ellipse(box(304, 138, 372, 206), fill=WHITE)
    draw.rounded_rectangle(box(64, 240, 448, 440), radius=p(44), fill=BLUE)
    # A down arrow on the front: the piece goes into the box when installed.
    draw.rounded_rectangle(box(238, 278, 274, 360), radius=p(14), fill=WHITE)
    draw.polygon([(x + p(206), y + p(338)), (x + p(306), y + p(338)), (x + p(256), y + p(398))], fill=WHITE)


def installed(draw, s):
    """A white check on a green disc, the mark of an installed add-on. Colored here, so it reads on any row."""
    draw.ellipse((2 * s, 2 * s, 62 * s, 62 * s), fill=GREEN)
    draw.line([(18 * s, 33 * s), (28 * s, 43 * s), (46 * s, 22 * s)], fill=WHITE, width=7 * s, joint="curve")
    for x, y in ((18, 33), (46, 22)):
        draw.ellipse(((x - 3.5) * s, (y - 3.5) * s, (x + 3.5) * s, (y + 3.5) * s), fill=WHITE)


def render(width, height, paint, background, mode="RGB"):
    image = Image.new(mode, (width * SCALE, height * SCALE), background)
    paint(ImageDraw.Draw(image), SCALE)
    return image.resize((width, height), Image.LANCZOS)


def fanart(draw, s):
    mark(draw, 120 * s, 210 * s, 300 * s)
    title = ImageFont.truetype(FONTS + "/Inter-Bold.ttf", 92 * s)
    tagline = ImageFont.truetype(FONTS + "/Inter-Medium.ttf", 34 * s)
    draw.text((452 * s, 268 * s), "Monteiro Add-ons", font=title, fill=WHITE)
    draw.text((456 * s, 392 * s), "Every add-on of your repositories, in one list", font=tagline, fill=GREY)
    draw.rounded_rectangle((456 * s, 456 * s, 536 * s, 464 * s), radius=4 * s, fill=BLUE)


def main():
    os.makedirs(MEDIA, exist_ok=True)
    render(512, 512, lambda d, s: mark(d, 0, 8 * s, 512 * s), BG).save(os.path.join(RESOURCES, "icon.png"), optimize=True)
    render(256, 256, lambda d, s: mark(d, 0, 4 * s, 256 * s), (0, 0, 0, 0), "RGBA").save(os.path.join(MEDIA, "logo.png"), optimize=True)
    render(1280, 720, fanart, BG).save(os.path.join(RESOURCES, "fanart.jpg"), quality=90, optimize=True)
    render(64, 64, installed, (0, 0, 0, 0), "RGBA").save(os.path.join(MEDIA, "installed.png"), optimize=True)
    # Shared textures and icons of the Monteiro add-ons.
    channels = os.path.join(ROOT, "script.m3u.channels", "resources", "skins", "default", "media")
    movies = os.path.join(ROOT, "script.m3u.movies", "resources", "skins", "default", "media")
    picture = os.path.join(ROOT, "script.easy.picture", "resources", "skins", "default", "media")
    for folder, names in ((channels, ["white.png", "panel.png", "search.png"]), (movies, ["puzzle.png"]), (picture, ["refresh.png"])):
        for name in names:
            shutil.copy2(os.path.join(folder, name), os.path.join(MEDIA, name))


if __name__ == "__main__":
    main()
