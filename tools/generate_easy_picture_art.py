"""Easy Picture artwork: add-on icon, header mark, fanart and the icons of the toolbar and the gallery.

Uses the colors and shapes of the other Easy add-ons. Requires Pillow and the Inter font (SIL Open Font License,
https://rsms.me/inter/). Run with the folder that holds Inter-Bold.ttf and Inter-Medium.ttf:

    python3 tools/generate_easy_picture_art.py path/to/inter/extras/ttf
"""

import os
import shutil
import sys

from PIL import Image, ImageDraw, ImageFont

FONTS = sys.argv[1]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ADDON = os.path.join(ROOT, "script.easy.picture")
RESOURCES = os.path.join(ADDON, "resources")
MEDIA = os.path.join(RESOURCES, "skins", "default", "media")
BG = (14, 15, 17)
BLUE = (59, 139, 255)
BLUE_DARK = (43, 108, 214)
WHITE = (255, 255, 255)
GREY = (156, 158, 166)
SCALE = 4  # draw large, then reduce for smooth edges


def mark(draw, x, y, size):
    """A blue photo with white hills and a sun, over a second photo behind it. (x, y) is the top left of a size x size box."""
    u = size / 512
    p = lambda value: value * u
    box = lambda a, b, c, d: (x + p(a), y + p(b), x + p(c), y + p(d))
    draw.rounded_rectangle(box(112, 72, 448, 328), radius=p(40), fill=BLUE_DARK)
    draw.rounded_rectangle(box(64, 136, 400, 424), radius=p(44), fill=BLUE)
    draw.polygon([(x + p(104), y + p(384)), (x + p(196), y + p(268)), (x + p(252), y + p(332)), (x + p(292), y + p(292)),
                  (x + p(360), y + p(384))], fill=WHITE)
    draw.ellipse(box(270, 184, 334, 248), fill=WHITE)


def render(width, height, paint, background, mode="RGB"):
    image = Image.new(mode, (width * SCALE, height * SCALE), background)
    paint(ImageDraw.Draw(image), SCALE)
    return image.resize((width, height), Image.LANCZOS)


def fanart(draw, s):
    mark(draw, 120 * s, 210 * s, 300 * s)
    title = ImageFont.truetype(FONTS + "/Inter-Bold.ttf", 92 * s)
    tagline = ImageFont.truetype(FONTS + "/Inter-Medium.ttf", 34 * s)
    draw.text((452 * s, 268 * s), "Easy Picture", font=title, fill=WHITE)
    draw.text((456 * s, 392 * s), "Your photos, on the big screen", font=tagline, fill=GREY)
    draw.rounded_rectangle((456 * s, 456 * s, 536 * s, 464 * s), radius=4 * s, fill=BLUE)


# Icons: white shapes on transparent, colored by the window.

def glyph(name, paint):
    image = Image.new("L", (128 * 8, 128 * 8), 0)
    paint(ImageDraw.Draw(image), lambda value: value * 8)
    alpha = image.resize((128, 128), Image.LANCZOS)
    out = Image.new("RGBA", (128, 128), (255, 255, 255, 0))
    out.putalpha(alpha)
    out.save(os.path.join(MEDIA, name), optimize=True)


def picture(d, p):
    """A photo with hills and a sun, the placeholder of a picture that is still loading."""
    d.rounded_rectangle((p(8), p(18), p(120), p(110)), radius=p(14), fill=255)
    d.rounded_rectangle((p(20), p(30), p(108), p(98)), radius=p(6), fill=0)
    d.polygon([(p(22), p(96)), (p(52), p(54)), (p(72), p(80)), (p(84), p(66)), (p(106), p(96))], fill=255)
    d.ellipse((p(80), p(36), p(98), p(54)), fill=255)


def folders(d, p):
    """A folder with a plus: the folders the gallery is made of."""
    d.rounded_rectangle((p(8), p(22), p(56), p(42)), radius=p(8), fill=255)
    d.rounded_rectangle((p(8), p(32), p(120), p(104)), radius=p(10), fill=255)
    d.rounded_rectangle((p(58), p(48), p(70), p(92)), radius=p(4), fill=0)
    d.rounded_rectangle((p(42), p(64), p(86), p(76)), radius=p(4), fill=0)


def refresh(d, p):
    """Two arrows in a circle: look for new pictures."""
    d.arc((p(16), p(16), p(112), p(112)), start=-60, end=150, fill=255, width=p(13))
    d.arc((p(16), p(16), p(112), p(112)), start=120, end=330, fill=255, width=p(13))
    d.polygon([(p(98), p(4)), (p(110), p(46)), (p(70), p(36))], fill=255)
    d.polygon([(p(30), p(124)), (p(18), p(82)), (p(58), p(92))], fill=255)


def main():
    os.makedirs(MEDIA, exist_ok=True)
    render(512, 512, lambda d, s: mark(d, 0, 8 * s, 512 * s), BG).save(os.path.join(RESOURCES, "icon.png"), optimize=True)
    render(256, 256, lambda d, s: mark(d, 0, 4 * s, 256 * s), (0, 0, 0, 0), "RGBA").save(os.path.join(MEDIA, "logo.png"), optimize=True)
    render(1280, 720, fanart, BG).save(os.path.join(RESOURCES, "fanart.jpg"), quality=90, optimize=True)
    for name, paint in (("picture.png", picture), ("folders.png", folders), ("refresh.png", refresh)):
        glyph(name, paint)
    # Shared textures and icons of the Easy add-ons.
    channels = os.path.join(ROOT, "script.m3u.channels", "resources", "skins", "default", "media")
    movies = os.path.join(ROOT, "script.m3u.movies", "resources", "skins", "default", "media")
    for folder, names in ((channels, ["white.png", "panel.png"]), (movies, ["gear.png", "star.png", "shade.png"])):
        for name in names:
            shutil.copy2(os.path.join(folder, name), os.path.join(MEDIA, name))


if __name__ == "__main__":
    main()
