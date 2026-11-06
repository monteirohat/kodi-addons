"""Easy Speed artwork: add-on icon, header mark, fanart, the speedometer and the icons of the results and the checks.

Uses the colors and shapes of the other Easy add-ons. Requires Pillow and the Inter font (SIL Open Font License,
https://rsms.me/inter/). Run with the folder that holds Inter-Bold.ttf and Inter-Medium.ttf:

    python3 tools/generate_easy_speed_art.py path/to/inter/extras/ttf
"""

import math
import os
import shutil
import sys

from PIL import Image, ImageDraw, ImageFont

FONTS = sys.argv[1]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ADDON = os.path.join(ROOT, "script.easy.speed")
RESOURCES = os.path.join(ADDON, "resources")
MEDIA = os.path.join(RESOURCES, "skins", "default", "media")
BG = (14, 15, 17)
BLUE = (59, 139, 255)
BLUE_DARK = (43, 108, 214)
WHITE = (255, 255, 255)
GREY = (156, 158, 166)
SCALE = 4  # draw large, then reduce for smooth edges

# The speedometer: an arc of 270 degrees open at the bottom, with the marks of the scale in speed.py.
GAUGE = 540
RADIUS = 246
TRACK = 24
START, SWEEP = 135, 270  # degrees clockwise from the right, as Pillow draws arcs
MARKS = (0, 5, 10, 25, 50, 100, 250, 500, 1000)
# Fill images, one for each step of 5 degrees: fill-00.png is empty, fill-54.png the whole arc.
FILL_STEPS = 54


def mark(draw, x, y, size):
    """A blue card with a white speedometer, over a second card. (x, y) is the top left of a size x size box."""
    u = size / 512
    p = lambda value: value * u
    box = lambda a, b, c, d: (x + p(a), y + p(b), x + p(c), y + p(d))
    draw.rounded_rectangle(box(112, 72, 448, 328), radius=p(40), fill=BLUE_DARK)
    draw.rounded_rectangle(box(64, 136, 400, 424), radius=p(44), fill=BLUE)
    draw.arc(box(122, 196, 342, 416), start=150, end=390, fill=WHITE, width=round(p(26)))
    for angle in (150, 390):
        cx, cy = x + p(232) + p(97) * math.cos(math.radians(angle)), y + p(306) + p(97) * math.sin(math.radians(angle))
        draw.ellipse((cx - p(13), cy - p(13), cx + p(13), cy + p(13)), fill=WHITE)
    # The needle, pointing up and right, from a hub in the middle.
    angle = math.radians(-50)
    tip = (x + p(232) + p(92) * math.cos(angle), y + p(306) + p(92) * math.sin(angle))
    side = math.radians(-50 + 90)
    draw.polygon([tip, (x + p(232) + p(15) * math.cos(side), y + p(306) + p(15) * math.sin(side)),
                  (x + p(232) - p(15) * math.cos(side), y + p(306) - p(15) * math.sin(side))], fill=WHITE)
    draw.ellipse(box(208, 282, 256, 330), fill=WHITE)


def render(width, height, paint, background, mode="RGB"):
    image = Image.new(mode, (width * SCALE, height * SCALE), background)
    paint(ImageDraw.Draw(image), SCALE)
    return image.resize((width, height), Image.LANCZOS)


def fanart(draw, s):
    mark(draw, 120 * s, 210 * s, 300 * s)
    title = ImageFont.truetype(FONTS + "/Inter-Bold.ttf", 92 * s)
    tagline = ImageFont.truetype(FONTS + "/Inter-Medium.ttf", 34 * s)
    draw.text((452 * s, 268 * s), "Easy Speed", font=title, fill=WHITE)
    draw.text((456 * s, 392 * s), "How fast is your internet?", font=tagline, fill=GREY)
    draw.rounded_rectangle((456 * s, 456 * s, 536 * s, 464 * s), radius=4 * s, fill=BLUE)


def save_alpha(image, size, name):
    out = Image.new("RGBA", size, (255, 255, 255, 0))
    out.putalpha(image.resize(size, Image.LANCZOS))
    out.save(os.path.join(MEDIA, name), optimize=True)


# Speedometer: white on transparent, colored by the window.

def arc(draw, end):
    """The arc from the start to end degrees, with round ends."""
    k = SCALE
    center = GAUGE * k / 2
    outer = RADIUS * k
    draw.arc((center - outer, center - outer, center + outer, center + outer), start=START, end=end, fill=255,
             width=TRACK * k)
    middle = outer - TRACK * k / 2
    for angle in (START, end):
        cx, cy = center + middle * math.cos(math.radians(angle)), center + middle * math.sin(math.radians(angle))
        draw.ellipse((cx - TRACK * k / 2, cy - TRACK * k / 2, cx + TRACK * k / 2, cy + TRACK * k / 2), fill=255)


def gauge():
    k = SCALE
    size = (GAUGE, GAUGE)
    track = Image.new("L", (GAUGE * k, GAUGE * k), 0)
    arc(ImageDraw.Draw(track), START + SWEEP)
    save_alpha(track, size, "gauge-track.png")
    for step in range(1, FILL_STEPS + 1):
        fill = Image.new("L", (GAUGE * k, GAUGE * k), 0)
        arc(ImageDraw.Draw(fill), START + SWEEP * step / FILL_STEPS)
        save_alpha(fill, size, "fill-%02d.png" % step)
    # The numbers of the scale, inside the arc, evenly spaced.
    scale = Image.new("L", (GAUGE * k, GAUGE * k), 0)
    draw = ImageDraw.Draw(scale)
    font = ImageFont.truetype(FONTS + "/Inter-Medium.ttf", 22 * k)
    center = GAUGE * k / 2
    for index, value in enumerate(MARKS):
        angle = math.radians(START + SWEEP * index / (len(MARKS) - 1))
        x, y = center + (RADIUS - 62) * k * math.cos(angle), center + (RADIUS - 62) * k * math.sin(angle)
        draw.text((x, y), str(value), font=font, fill=255, anchor="mm")
    save_alpha(scale, size, "gauge-scale.png")


# Icons: white shapes on transparent, colored by the window.

def glyph(name, paint):
    image = Image.new("L", (128 * 8, 128 * 8), 0)
    paint(ImageDraw.Draw(image), lambda value: value * 8)
    save_alpha(image, (128, 128), name)


def download(d, p):
    """An arrow down onto a line."""
    d.rounded_rectangle((p(54), p(8), p(74), p(78)), radius=p(8), fill=255)
    d.polygon([(p(22), p(56)), (p(106), p(56)), (p(64), p(98))], fill=255)
    d.rounded_rectangle((p(16), p(104), p(112), p(120)), radius=p(8), fill=255)


def upload(d, p):
    """An arrow up from a line."""
    d.rounded_rectangle((p(54), p(40), p(74), p(98)), radius=p(8), fill=255)
    d.polygon([(p(22), p(52)), (p(106), p(52)), (p(64), p(10))], fill=255)
    d.rounded_rectangle((p(16), p(104), p(112), p(120)), radius=p(8), fill=255)


def latency(d, p):
    """A stopwatch: the time of a request."""
    d.ellipse((p(14), p(24), p(114), p(124)), fill=255)
    d.ellipse((p(28), p(38), p(100), p(110)), fill=0)
    d.rounded_rectangle((p(50), p(4), p(78), p(18)), radius=p(5), fill=255)
    d.rounded_rectangle((p(58), p(14), p(70), p(28)), fill=255)
    d.polygon([(p(60), p(76)), (p(68), p(76)), (p(84), p(50)), (p(78), p(46))], fill=255)
    d.ellipse((p(56), p(68), p(72), p(84)), fill=255)


def loaded(d, p):
    """A pulse line: the time of a request while the connection is busy."""
    d.line([(p(8), p(70)), (p(36), p(70)), (p(50), p(30)), (p(72), p(104)), (p(88), p(56)), (p(98), p(70)), (p(120), p(70))],
           fill=255, width=p(12), joint="curve")
    for x, y in ((8, 70), (120, 70)):
        d.ellipse((p(x - 6), p(y - 6), p(x + 6), p(y + 6)), fill=255)


def check(d, p):
    """A tick in a circle: a check that passed."""
    d.ellipse((p(8), p(8), p(120), p(120)), fill=255)
    d.line([(p(36), p(66)), (p(56), p(86)), (p(94), p(44))], fill=0, width=p(14), joint="curve")


def warning(d, p):
    """An exclamation mark in a triangle: a check that passed with a problem."""
    d.polygon([(p(64), p(10)), (p(124), p(116)), (p(4), p(116))], fill=255)
    d.rounded_rectangle((p(57), p(44), p(71), p(86)), radius=p(6), fill=0)
    d.ellipse((p(56), p(94), p(72), p(110)), fill=0)


def failed(d, p):
    """A cross in a circle: a check that failed."""
    d.ellipse((p(8), p(8), p(120), p(120)), fill=255)
    d.line([(p(44), p(44)), (p(84), p(84))], fill=0, width=p(14))
    d.line([(p(84), p(44)), (p(44), p(84))], fill=0, width=p(14))


def cable(d, p):
    """A network plug with its cable."""
    d.rounded_rectangle((p(24), p(14), p(104), p(84)), radius=p(12), fill=255)
    for x in (40, 56, 72, 88):
        d.rectangle((p(x - 4), p(26), p(x + 4), p(44)), fill=0)
    d.rectangle((p(44), p(84), p(84), p(98)), fill=255)
    d.rounded_rectangle((p(56), p(96), p(72), p(124)), radius=p(6), fill=255)


def speedometer(d, p):
    """The speedometer of the icon, for the home screen of the Monteiro skin."""
    d.arc((p(8), p(14), p(120), p(126)), start=150, end=390, fill=255, width=p(14))
    for angle in (150, 390):
        cx, cy = p(64) + p(49) * math.cos(math.radians(angle)), p(70) + p(49) * math.sin(math.radians(angle))
        d.ellipse((cx - p(7), cy - p(7), cx + p(7), cy + p(7)), fill=255)
    angle, side = math.radians(-50), math.radians(40)
    d.polygon([(p(64) + p(46) * math.cos(angle), p(70) + p(46) * math.sin(angle)),
               (p(64) + p(9) * math.cos(side), p(70) + p(9) * math.sin(side)),
               (p(64) - p(9) * math.cos(side), p(70) - p(9) * math.sin(side))], fill=255)
    d.ellipse((p(52), p(58), p(76), p(82)), fill=255)


def main():
    os.makedirs(MEDIA, exist_ok=True)
    render(512, 512, lambda d, s: mark(d, 0, 8 * s, 512 * s), BG).save(os.path.join(RESOURCES, "icon.png"), optimize=True)
    render(256, 256, lambda d, s: mark(d, 0, 4 * s, 256 * s), (0, 0, 0, 0), "RGBA").save(os.path.join(MEDIA, "logo.png"), optimize=True)
    render(1280, 720, fanart, BG).save(os.path.join(RESOURCES, "fanart.jpg"), quality=90, optimize=True)
    gauge()
    for name, paint in (("download.png", download), ("upload.png", upload), ("latency.png", latency),
                        ("loaded.png", loaded), ("check.png", check), ("warning.png", warning), ("failed.png", failed),
                        ("cable.png", cable), ("speed.png", speedometer)):
        glyph(name, paint)
    # Shared textures and icons of the Monteiro add-ons.
    channels = os.path.join(ROOT, "script.m3u.channels", "resources", "skins", "default", "media")
    skin = os.path.join(ROOT, "skin.monteiro", "media")
    for folder, names in ((channels, ["white.png", "panel.png"]), (skin, ["wifi.png"])):
        for name in names:
            shutil.copy2(os.path.join(folder, name), os.path.join(MEDIA, name))


if __name__ == "__main__":
    main()
