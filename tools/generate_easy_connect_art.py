"""Easy Connect artwork: add-on icon, header mark, fanart and the icons of the signal, the lock and the networks.

Uses the colors and shapes of the other Easy add-ons. Requires Pillow and the Inter font (SIL Open Font License,
https://rsms.me/inter/). Run with the folder that holds Inter-Bold.ttf and Inter-Medium.ttf:

    python3 tools/generate_easy_connect_art.py path/to/inter/extras/ttf
"""

import os
import shutil
import sys

from PIL import Image, ImageDraw, ImageFont

FONTS = sys.argv[1]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ADDON = os.path.join(ROOT, "script.easy.connect")
RESOURCES = os.path.join(ADDON, "resources")
MEDIA = os.path.join(RESOURCES, "skins", "default", "media")
BG = (14, 15, 17)
BLUE = (59, 139, 255)
BLUE_DARK = (43, 108, 214)
WHITE = (255, 255, 255)
GREY = (156, 158, 166)
SCALE = 4  # draw large, then reduce for smooth edges
# Arcs of the signal that are not lit are drawn faint, so the icon keeps its shape.
FAINT = 70


def waves(draw, cx, cy, unit, lit=3, fill=255, faint=FAINT):
    """A dot and three arcs above it, centered on (cx, cy), the bottom of the dot. lit arcs are drawn full."""
    p = lambda value: value * unit
    draw.ellipse((cx - p(10), cy - p(20), cx + p(10), cy), fill=fill if lit >= 0 else faint)
    for index, radius in enumerate((36, 62, 88)):
        color = fill if index < lit else faint
        box = (cx - p(radius), cy - p(radius) - p(10), cx + p(radius), cy + p(radius) - p(10))
        draw.arc(box, start=225, end=315, fill=color, width=round(p(13)))


def mark(draw, x, y, size):
    """A blue card with white Wi-Fi waves, over a second card. (x, y) is the top left of a size x size box."""
    u = size / 512
    p = lambda value: value * u
    box = lambda a, b, c, d: (x + p(a), y + p(b), x + p(c), y + p(d))
    draw.rounded_rectangle(box(112, 72, 448, 328), radius=p(40), fill=BLUE_DARK)
    draw.rounded_rectangle(box(64, 136, 400, 424), radius=p(44), fill=BLUE)
    waves(draw, x + p(232), y + p(362), u * 1.55, fill=WHITE)


def render(width, height, paint, background, mode="RGB"):
    image = Image.new(mode, (width * SCALE, height * SCALE), background)
    paint(ImageDraw.Draw(image), SCALE)
    return image.resize((width, height), Image.LANCZOS)


def fanart(draw, s):
    mark(draw, 120 * s, 210 * s, 300 * s)
    title = ImageFont.truetype(FONTS + "/Inter-Bold.ttf", 92 * s)
    tagline = ImageFont.truetype(FONTS + "/Inter-Medium.ttf", 34 * s)
    draw.text((452 * s, 268 * s), "Easy Connect", font=title, fill=WHITE)
    draw.text((456 * s, 392 * s), "Your Wi-Fi, from the couch", font=tagline, fill=GREY)
    draw.rounded_rectangle((456 * s, 456 * s, 536 * s, 464 * s), radius=4 * s, fill=BLUE)


# Icons: white shapes on transparent, colored by the window.

def glyph(name, paint):
    image = Image.new("L", (128 * 8, 128 * 8), 0)
    paint(ImageDraw.Draw(image), lambda value: value * 8)
    out = Image.new("RGBA", (128, 128), (255, 255, 255, 0))
    out.putalpha(image.resize((128, 128), Image.LANCZOS))
    out.save(os.path.join(MEDIA, name), optimize=True)


def signal(lit):
    """The Wi-Fi icon with lit of its three arcs full: wifi-0.png to wifi-3.png."""
    return lambda d, p: waves(d, p(64), p(112), p(1), lit)


def wifi_off(d, p):
    """The Wi-Fi icon, faint, crossed by a line: the Wi-Fi is off or not connected."""
    waves(d, p(64), p(112), p(1), lit=-1, faint=110)
    d.line([(p(18), p(14)), (p(110), p(116))], fill=0, width=p(26))
    d.line([(p(18), p(14)), (p(110), p(116))], fill=255, width=p(12))


def lock(d, p):
    """A padlock: a network with a password."""
    d.arc((p(36), p(8), p(92), p(72)), start=180, end=360, fill=255, width=p(13))
    d.rectangle((p(36), p(38), p(49), p(58)), fill=255)
    d.rectangle((p(79), p(38), p(92), p(58)), fill=255)
    d.rounded_rectangle((p(20), p(54), p(108), p(122)), radius=p(14), fill=255)
    d.ellipse((p(54), p(74), p(74), p(94)), fill=0)
    d.rounded_rectangle((p(59), p(86), p(69), p(106)), radius=p(4), fill=0)


def key(d, p):
    """A key: the password of a network."""
    d.ellipse((p(8), p(36), p(64), p(92)), fill=255)
    d.ellipse((p(24), p(52), p(48), p(76)), fill=0)
    d.rounded_rectangle((p(56), p(56), p(122), p(72)), radius=p(6), fill=255)
    d.rounded_rectangle((p(90), p(64), p(104), p(92)), radius=p(5), fill=255)
    d.rounded_rectangle((p(108), p(64), p(122), p(84)), radius=p(5), fill=255)


def refresh(d, p):
    """Two arrows in a circle: look for networks again."""
    d.arc((p(16), p(16), p(112), p(112)), start=-60, end=150, fill=255, width=p(13))
    d.arc((p(16), p(16), p(112), p(112)), start=120, end=330, fill=255, width=p(13))
    d.polygon([(p(98), p(4)), (p(110), p(46)), (p(70), p(36))], fill=255)
    d.polygon([(p(30), p(124)), (p(18), p(82)), (p(58), p(92))], fill=255)


def main():
    os.makedirs(MEDIA, exist_ok=True)
    render(512, 512, lambda d, s: mark(d, 0, 8 * s, 512 * s), BG).save(os.path.join(RESOURCES, "icon.png"), optimize=True)
    render(256, 256, lambda d, s: mark(d, 0, 4 * s, 256 * s), (0, 0, 0, 0), "RGBA").save(os.path.join(MEDIA, "logo.png"), optimize=True)
    render(1280, 720, fanart, BG).save(os.path.join(RESOURCES, "fanart.jpg"), quality=90, optimize=True)
    for lit in range(4):
        glyph("wifi-%d.png" % lit, signal(lit))
    for name, paint in (("wifi-off.png", wifi_off), ("lock.png", lock), ("key.png", key), ("refresh.png", refresh)):
        glyph(name, paint)
    # Shared textures and icons of the Monteiro add-ons.
    channels = os.path.join(ROOT, "script.m3u.channels", "resources", "skins", "default", "media")
    speed = os.path.join(ROOT, "script.easy.speed", "resources", "skins", "default", "media")
    for folder, names in ((channels, ["white.png", "panel.png"]), (speed, ["check.png", "cable.png"])):
        for name in names:
            shutil.copy2(os.path.join(folder, name), os.path.join(MEDIA, name))


if __name__ == "__main__":
    main()
