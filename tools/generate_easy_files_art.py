"""Easy Files artwork: add-on icon, header mark, fanart and the icons of places and file kinds.

Uses the colors and shapes of the other Easy add-ons. Requires Pillow and the Inter font (SIL Open Font License,
https://rsms.me/inter/). Run with the folder that holds Inter-Bold.ttf and Inter-Medium.ttf:

    python3 tools/generate_easy_files_art.py path/to/inter/extras/ttf
"""

import os
import shutil
import sys

from PIL import Image, ImageDraw, ImageFont

FONTS = sys.argv[1]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ADDON = os.path.join(ROOT, "script.easy.files")
RESOURCES = os.path.join(ADDON, "resources")
MEDIA = os.path.join(RESOURCES, "skins", "default", "media")
BG = (14, 15, 17)
BLUE = (59, 139, 255)
BLUE_DARK = (43, 108, 214)
WHITE = (255, 255, 255)
GREY = (156, 158, 166)
SCALE = 4  # draw large, then reduce for smooth edges


def mark(draw, x, y, size):
    """A blue folder with a white document in it. (x, y) is the top left of a size x size box."""
    u = size / 512
    p = lambda value: value * u
    box = lambda a, b, c, d: (x + p(a), y + p(b), x + p(c), y + p(d))
    draw.rounded_rectangle(box(64, 96, 256, 176), radius=p(36), fill=BLUE_DARK)
    draw.rounded_rectangle(box(64, 136, 448, 416), radius=p(48), fill=BLUE)
    # A document coming out of the folder, with lines of text.
    draw.rounded_rectangle(box(176, 196, 336, 372), radius=p(18), fill=WHITE)
    for top, right in ((236, 296), (272, 296), (308, 264)):
        draw.rounded_rectangle(box(208, top, right, top + 16), radius=p(8), fill=BLUE)


def render(width, height, paint, background, mode="RGB"):
    image = Image.new(mode, (width * SCALE, height * SCALE), background)
    paint(ImageDraw.Draw(image), SCALE)
    return image.resize((width, height), Image.LANCZOS)


def fanart(draw, s):
    mark(draw, 120 * s, 210 * s, 300 * s)
    title = ImageFont.truetype(FONTS + "/Inter-Bold.ttf", 92 * s)
    tagline = ImageFont.truetype(FONTS + "/Inter-Medium.ttf", 34 * s)
    draw.text((452 * s, 268 * s), "Easy Files", font=title, fill=WHITE)
    draw.text((456 * s, 392 * s), "Your files, from the couch", font=tagline, fill=GREY)
    draw.rounded_rectangle((456 * s, 456 * s, 536 * s, 464 * s), radius=4 * s, fill=BLUE)


# Icons of places and file kinds: white shapes on transparent, colored by the window.

def glyph(name, paint):
    image = Image.new("L", (128 * 8, 128 * 8), 0)
    paint(ImageDraw.Draw(image), lambda value: value * 8)
    alpha = image.resize((128, 128), Image.LANCZOS)
    out = Image.new("RGBA", (128, 128), (255, 255, 255, 0))
    out.putalpha(alpha)
    out.save(os.path.join(MEDIA, name), optimize=True)


def folder(d, p):
    d.rounded_rectangle((p(10), p(24), p(58), p(44)), radius=p(8), fill=255)
    d.rounded_rectangle((p(10), p(34), p(118), p(104)), radius=p(10), fill=255)


def page(d, p, inner=None):
    """A sheet with its top right corner folded, and a symbol of the kind cut out of it."""
    d.rounded_rectangle((p(24), p(10), p(104), p(118)), radius=p(12), fill=255)
    d.polygon([(p(76), p(10)), (p(104), p(10)), (p(104), p(38))], fill=0)
    d.polygon([(p(76), p(10)), (p(104), p(38)), (p(82), p(38)), (p(76), p(32))], fill=0)
    d.rounded_rectangle((p(76), p(10), p(104), p(38)), radius=p(6), fill=0)
    d.polygon([(p(76), p(10)), (p(76), p(32)), (p(82), p(38)), (p(104), p(38))], fill=255)
    if inner:
        inner(d, p)


def video(d, p):
    page(d, p, lambda d, p: d.polygon([(p(52), p(58)), (p(52), p(94)), (p(82), p(76))], fill=0))


def audio(d, p):
    def note(d, p):
        d.ellipse((p(44), p(80), p(64), p(100)), fill=0)
        d.rounded_rectangle((p(58), p(50), p(66), p(92)), radius=p(4), fill=0)
        d.polygon([(p(62), p(50)), (p(84), p(56)), (p(84), p(66)), (p(62), p(60))], fill=0)
    page(d, p, note)


def picture(d, p):
    def scene(d, p):
        d.polygon([(p(42), p(100)), (p(62), p(70)), (p(74), p(86)), (p(82), p(78)), (p(92), p(100))], fill=0)
        d.ellipse((p(72), p(48), p(86), p(62)), fill=0)
    page(d, p, scene)


def archive(d, p):
    def zipper(d, p):
        for top in range(40, 90, 12):
            d.rectangle((p(58), p(top), p(66), p(top + 6)), fill=0)
        d.rounded_rectangle((p(54), p(88), p(70), p(106)), radius=p(4), fill=0)
    page(d, p, zipper)


def text_page(d, p):
    def lines(d, p):
        for top, right in ((50, 86), (64, 86), (78, 86), (92, 70)):
            d.rounded_rectangle((p(44), p(top), p(right), p(top + 6)), radius=p(3), fill=0)
    page(d, p, lines)


def plain(d, p):
    page(d, p)


def drive(d, p):
    d.rounded_rectangle((p(12), p(36), p(116), p(92)), radius=p(14), fill=255)
    d.ellipse((p(88), p(58), p(100), p(70)), fill=0)
    d.rounded_rectangle((p(28), p(60), p(72), p(68)), radius=p(4), fill=0)


def home(d, p):
    d.polygon([(p(64), p(14)), (p(118), p(60)), (p(104), p(60)), (p(104), p(112)), (p(24), p(112)), (p(24), p(60)), (p(10), p(60))], fill=255)
    d.rounded_rectangle((p(54), p(78), p(74), p(112)), radius=p(4), fill=0)


def network(d, p):
    d.rounded_rectangle((p(22), p(14), p(106), p(70)), radius=p(10), fill=255)
    d.rounded_rectangle((p(58), p(70), p(70), p(92)), radius=p(2), fill=255)
    d.rounded_rectangle((p(14), p(92), p(114), p(104)), radius=p(6), fill=255)
    d.ellipse((p(50), p(84), p(78), p(112)), fill=255)


def kodi(d, p):
    d.rounded_rectangle((p(14), p(14), p(114), p(114)), radius=p(22), fill=255)
    for cx, cy in ((44, 44), (84, 44), (44, 84), (84, 84)):
        d.rounded_rectangle((p(cx - 14), p(cy - 14), p(cx + 14), p(cy + 14)), radius=p(6), fill=0)


def main():
    os.makedirs(MEDIA, exist_ok=True)
    render(512, 512, lambda d, s: mark(d, 0, 8 * s, 512 * s), BG).save(os.path.join(RESOURCES, "icon.png"), optimize=True)
    render(256, 256, lambda d, s: mark(d, 0, 4 * s, 256 * s), (0, 0, 0, 0), "RGBA").save(os.path.join(MEDIA, "logo.png"), optimize=True)
    render(1280, 720, fanart, BG).save(os.path.join(RESOURCES, "fanart.jpg"), quality=90, optimize=True)
    for name, paint in (("folder.png", folder), ("video.png", video), ("audio.png", audio), ("image.png", picture),
                        ("archive.png", archive), ("text.png", text_page), ("file.png", plain), ("drive.png", drive),
                        ("home.png", home), ("network.png", network), ("kodi.png", kodi)):
        glyph(name, paint)
    # Shared textures of the Easy add-ons.
    channels = os.path.join(ROOT, "script.m3u.channels", "resources", "skins", "default", "media")
    for name in ("white.png", "panel.png"):
        shutil.copy2(os.path.join(channels, name), os.path.join(MEDIA, name))


if __name__ == "__main__":
    main()
