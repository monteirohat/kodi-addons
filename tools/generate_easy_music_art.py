"""Easy Music artwork: add-on icon, header mark, fanart and the icons of the toolbar, the songs and the player bar.

Uses the colors and shapes of the other Easy add-ons. Requires Pillow and the Inter font (SIL Open Font License,
https://rsms.me/inter/). Run with the folder that holds Inter-Bold.ttf and Inter-Medium.ttf:

    python3 tools/generate_easy_music_art.py path/to/inter/extras/ttf
"""

import math
import os
import shutil
import sys

from PIL import Image, ImageDraw, ImageFont

FONTS = sys.argv[1]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ADDON = os.path.join(ROOT, "script.easy.music")
RESOURCES = os.path.join(ADDON, "resources")
MEDIA = os.path.join(RESOURCES, "skins", "default", "media")
BG = (14, 15, 17)
BLUE = (59, 139, 255)
BLUE_DARK = (43, 108, 214)
WHITE = (255, 255, 255)
GREY = (156, 158, 166)
SCALE = 4  # draw large, then reduce for smooth edges


def mark(draw, x, y, size):
    """A blue record sleeve with a white pair of notes, over a second sleeve. (x, y) is the top left of a size x size box."""
    u = size / 512
    p = lambda value: value * u
    box = lambda a, b, c, d: (x + p(a), y + p(b), x + p(c), y + p(d))
    draw.rounded_rectangle(box(120, 64, 448, 360), radius=p(40), fill=BLUE_DARK)
    draw.rounded_rectangle(box(64, 128, 400, 448), radius=p(44), fill=BLUE)
    # Two notes joined by a beam.
    draw.polygon([(x + p(196), y + p(212)), (x + p(328), y + p(184)), (x + p(328), y + p(222)), (x + p(196), y + p(250))], fill=WHITE)
    draw.rounded_rectangle(box(184, 220, 208, 360), radius=p(12), fill=WHITE)
    draw.rounded_rectangle(box(316, 192, 340, 332), radius=p(12), fill=WHITE)
    draw.ellipse(box(132, 322, 208, 386), fill=WHITE)
    draw.ellipse(box(264, 294, 340, 358), fill=WHITE)


def render(width, height, paint, background, mode="RGB"):
    image = Image.new(mode, (width * SCALE, height * SCALE), background)
    paint(ImageDraw.Draw(image), SCALE)
    return image.resize((width, height), Image.LANCZOS)


def fanart(draw, s):
    mark(draw, 120 * s, 210 * s, 300 * s)
    title = ImageFont.truetype(FONTS + "/Inter-Bold.ttf", 92 * s)
    tagline = ImageFont.truetype(FONTS + "/Inter-Medium.ttf", 34 * s)
    draw.text((452 * s, 268 * s), "Easy Music", font=title, fill=WHITE)
    draw.text((456 * s, 392 * s), "Your music, folder by folder", font=tagline, fill=GREY)
    draw.rounded_rectangle((456 * s, 456 * s, 536 * s, 464 * s), radius=4 * s, fill=BLUE)


# Icons: white shapes on transparent, colored by the window.

def glyph(name, paint):
    image = Image.new("L", (128 * 8, 128 * 8), 0)
    paint(ImageDraw.Draw(image), lambda value: value * 8)
    alpha = image.resize((128, 128), Image.LANCZOS)
    out = Image.new("RGBA", (128, 128), (255, 255, 255, 0))
    out.putalpha(alpha)
    out.save(os.path.join(MEDIA, name), optimize=True)


def note(d, p):
    """A single note, the placeholder of a song or playlist without a cover."""
    d.rounded_rectangle((p(70), p(18), p(84), p(92)), radius=p(6), fill=255)
    d.polygon([(p(78), p(18)), (p(110), p(30)), (p(110), p(52)), (p(78), p(40))], fill=255)
    d.ellipse((p(30), p(76), p(84), p(116)), fill=255)


def playing(d, p):
    """Three bars of different heights: the song that is playing."""
    for left, top in ((22, 50), (54, 20), (86, 70)):
        d.rounded_rectangle((p(left), p(top), p(left + 20), p(108)), radius=p(6), fill=255)


def previous(d, p):
    d.rounded_rectangle((p(22), p(24), p(36), p(104)), radius=p(5), fill=255)
    d.polygon([(p(106), p(24)), (p(106), p(104)), (p(40), p(64))], fill=255)


def next_song(d, p):
    d.rounded_rectangle((p(92), p(24), p(106), p(104)), radius=p(5), fill=255)
    d.polygon([(p(22), p(24)), (p(22), p(104)), (p(88), p(64))], fill=255)


def play(d, p):
    d.polygon([(p(36), p(18)), (p(36), p(110)), (p(112), p(64))], fill=255)


def pause(d, p):
    d.rounded_rectangle((p(28), p(20), p(54), p(108)), radius=p(6), fill=255)
    d.rounded_rectangle((p(74), p(20), p(100), p(108)), radius=p(6), fill=255)


def shuffle(d, p):
    """Two crossing arrows."""
    width = p(11)
    d.line([(p(12), p(36)), (p(40), p(36)), (p(84), p(92)), (p(104), p(92))], fill=255, width=width, joint="curve")
    d.line([(p(12), p(92)), (p(40), p(92)), (p(84), p(36)), (p(104), p(36))], fill=255, width=width, joint="curve")
    for y in (36, 92):
        d.polygon([(p(98), p(y - 18)), (p(120), p(y)), (p(98), p(y + 18))], fill=255)


def repeat(d, p, one=False):
    """A loop of two arrows. With one, a small 1 in the middle: repeat one song."""
    width = p(11)
    d.line([(p(22), p(70)), (p(22), p(40)), (p(98), p(40))], fill=255, width=width, joint="curve")
    d.polygon([(p(92), p(22)), (p(114), p(40)), (p(92), p(58))], fill=255)
    d.line([(p(106), p(58)), (p(106), p(88)), (p(30), p(88))], fill=255, width=width, joint="curve")
    d.polygon([(p(36), p(70)), (p(14), p(88)), (p(36), p(106))], fill=255)
    if one:
        d.rounded_rectangle((p(58), p(52), p(70), p(78)), radius=p(3), fill=255)
        d.polygon([(p(52), p(58)), (p(64), p(50)), (p(64), p(60))], fill=255)


def heart_shape(d, p, fill):
    d.ellipse((p(12), p(22), p(66), p(76)), fill=fill)
    d.ellipse((p(62), p(22), p(116), p(76)), fill=fill)
    d.polygon([(p(15), p(58)), (p(113), p(58)), (p(64), p(112))], fill=fill)


def heart(d, p):
    heart_shape(d, p, 255)


def heart_outline(d, p):
    heart_shape(d, p, 255)
    # The same heart, smaller, cut out of it.
    small = lambda value: 64 + (value - 64) * 0.78
    d.ellipse((p(small(12)), p(small(22) + 4), p(small(66)), p(small(76) + 4)), fill=0)
    d.ellipse((p(small(62)), p(small(22) + 4), p(small(116)), p(small(76) + 4)), fill=0)
    d.polygon([(p(small(15)), p(small(58) + 4)), (p(small(113)), p(small(58) + 4)), (p(64), p(small(112) + 2))], fill=0)


def folders(d, p):
    d.rounded_rectangle((p(8), p(22), p(56), p(42)), radius=p(8), fill=255)
    d.rounded_rectangle((p(8), p(32), p(120), p(104)), radius=p(10), fill=255)
    d.rounded_rectangle((p(58), p(48), p(70), p(92)), radius=p(4), fill=0)
    d.rounded_rectangle((p(42), p(64), p(86), p(76)), radius=p(4), fill=0)


def main():
    os.makedirs(MEDIA, exist_ok=True)
    render(512, 512, lambda d, s: mark(d, 0, 8 * s, 512 * s), BG).save(os.path.join(RESOURCES, "icon.png"), optimize=True)
    render(256, 256, lambda d, s: mark(d, 0, 4 * s, 256 * s), (0, 0, 0, 0), "RGBA").save(os.path.join(MEDIA, "logo.png"), optimize=True)
    render(1280, 720, fanart, BG).save(os.path.join(RESOURCES, "fanart.jpg"), quality=90, optimize=True)
    for name, paint in (("note.png", note), ("playing.png", playing), ("previous.png", previous), ("next.png", next_song),
                        ("play.png", play), ("pause.png", pause), ("shuffle.png", shuffle), ("repeat.png", repeat),
                        ("repeat-one.png", lambda d, p: repeat(d, p, True)), ("heart.png", heart),
                        ("heart-outline.png", heart_outline), ("folders.png", folders)):
        glyph(name, paint)
    # Shared textures and icons of the Monteiro add-ons.
    channels = os.path.join(ROOT, "script.m3u.channels", "resources", "skins", "default", "media")
    picture = os.path.join(ROOT, "script.easy.picture", "resources", "skins", "default", "media")
    movies = os.path.join(ROOT, "script.m3u.movies", "resources", "skins", "default", "media")
    for folder, names in ((channels, ["white.png", "panel.png", "search.png"]), (picture, ["refresh.png"]), (movies, ["circle.png"])):
        for name in names:
            shutil.copy2(os.path.join(folder, name), os.path.join(MEDIA, name))


if __name__ == "__main__":
    main()
