"""Easy Bluetooth artwork: add-on icon, header mark, fanart and the icons of the kinds of devices and their signal.

Uses the colors and shapes of the other Easy add-ons. Requires Pillow and the Inter font (SIL Open Font License,
https://rsms.me/inter/). Run with the folder that holds Inter-Bold.ttf and Inter-Medium.ttf:

    python3 tools/generate_easy_bluetooth_art.py path/to/inter/extras/ttf
"""

import os
import shutil
import sys

from PIL import Image, ImageDraw, ImageFont

FONTS = sys.argv[1]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ADDON = os.path.join(ROOT, "script.easy.bluetooth")
RESOURCES = os.path.join(ADDON, "resources")
MEDIA = os.path.join(RESOURCES, "skins", "default", "media")
BG = (14, 15, 17)
BLUE = (59, 139, 255)
BLUE_DARK = (43, 108, 214)
WHITE = (255, 255, 255)
GREY = (156, 158, 166)
SCALE = 4  # draw large, then reduce for smooth edges
FAINT = 70


def rune(draw, cx, top, height, width, fill=255):
    """The Bluetooth rune: a vertical stroke with two arrows on its right, centered on cx, from top for height."""
    h = height
    x0, x1 = cx - h * 0.25, cx + h * 0.25
    points = [(x0, top + h * 0.27), (x1, top + h * 0.73), (cx, top + h), (cx, top), (x1, top + h * 0.27), (x0, top + h * 0.73)]
    draw.line(points, fill=fill, width=round(width), joint="curve")


def mark(draw, x, y, size):
    """A blue card with the white Bluetooth rune, over a second card. (x, y) is the top left of a size x size box."""
    u = size / 512
    p = lambda value: value * u
    box = lambda a, b, c, d: (x + p(a), y + p(b), x + p(c), y + p(d))
    draw.rounded_rectangle(box(112, 72, 448, 328), radius=p(40), fill=BLUE_DARK)
    draw.rounded_rectangle(box(64, 136, 400, 424), radius=p(44), fill=BLUE)
    rune(draw, x + p(232), y + p(184), p(192), p(26), WHITE)


def render(width, height, paint, background, mode="RGB"):
    image = Image.new(mode, (width * SCALE, height * SCALE), background)
    paint(ImageDraw.Draw(image), SCALE)
    return image.resize((width, height), Image.LANCZOS)


def fanart(draw, s):
    mark(draw, 120 * s, 210 * s, 300 * s)
    title = ImageFont.truetype(FONTS + "/Inter-Bold.ttf", 92 * s)
    tagline = ImageFont.truetype(FONTS + "/Inter-Medium.ttf", 34 * s)
    draw.text((452 * s, 268 * s), "Easy Bluetooth", font=title, fill=WHITE)
    draw.text((456 * s, 392 * s), "Your devices, without wires", font=tagline, fill=GREY)
    draw.rounded_rectangle((456 * s, 456 * s, 536 * s, 464 * s), radius=4 * s, fill=BLUE)


# Icons: white shapes on transparent, colored by the window.

def glyph(name, paint):
    image = Image.new("L", (128 * 8, 128 * 8), 0)
    paint(ImageDraw.Draw(image), lambda value: value * 8)
    out = Image.new("RGBA", (128, 128), (255, 255, 255, 0))
    out.putalpha(image.resize((128, 128), Image.LANCZOS))
    out.save(os.path.join(MEDIA, name), optimize=True)


def bluetooth(d, p):
    rune(d, p(64), p(12), p(104), p(12))


def bluetooth_off(d, p):
    """The rune, faint, crossed by a line: the Bluetooth is off."""
    rune(d, p(64), p(12), p(104), p(12), fill=110)
    d.line([(p(18), p(14)), (p(110), p(116))], fill=0, width=p(26))
    d.line([(p(18), p(14)), (p(110), p(116))], fill=255, width=p(12))


def bluetooth_connected(d, p):
    """The rune with a dot on each side: a device is connected."""
    rune(d, p(64), p(12), p(104), p(12))
    for x in (14, 114):
        d.ellipse((p(x - 9), p(55), p(x + 9), p(73)), fill=255)


def headphones(d, p):
    d.arc((p(14), p(14), p(114), p(114)), start=180, end=360, fill=255, width=p(12))
    d.rectangle((p(14), p(62), p(26), p(80)), fill=255)
    d.rectangle((p(102), p(62), p(114), p(80)), fill=255)
    d.rounded_rectangle((p(10), p(68), p(40), p(118)), radius=p(10), fill=255)
    d.rounded_rectangle((p(88), p(68), p(118), p(118)), radius=p(10), fill=255)


def speaker(d, p):
    d.rounded_rectangle((p(26), p(6), p(102), p(122)), radius=p(14), fill=255)
    d.ellipse((p(40), p(54), p(88), p(102)), fill=0)
    d.ellipse((p(54), p(68), p(74), p(88)), fill=255)
    d.ellipse((p(56), p(20), p(72), p(36)), fill=0)


def keyboard(d, p):
    d.rounded_rectangle((p(4), p(28), p(124), p(100)), radius=p(12), fill=255)
    for row, top in enumerate((40, 58)):
        for column in range(7):
            left = 16 + column * 14 + (row * 7)
            d.rounded_rectangle((p(left), p(top), p(left + 9), p(top + 10)), radius=p(2), fill=0)
    d.rounded_rectangle((p(32), p(78), p(96), p(88)), radius=p(3), fill=0)


def mouse(d, p):
    d.rounded_rectangle((p(30), p(8), p(98), p(120)), radius=p(34), fill=255)
    d.rectangle((p(61), p(8), p(67), p(52)), fill=0)
    d.rectangle((p(30), p(50), p(98), p(56)), fill=0)


def gamepad(d, p):
    d.rounded_rectangle((p(6), p(36), p(122), p(96)), radius=p(30), fill=255)
    d.rectangle((p(26), p(60), p(50), p(70)), fill=0)
    d.rectangle((p(33), p(53), p(43), p(77)), fill=0)
    d.ellipse((p(82), p(50), p(94), p(62)), fill=0)
    d.ellipse((p(94), p(64), p(106), p(76)), fill=0)


def phone(d, p):
    d.rounded_rectangle((p(34), p(4), p(94), p(124)), radius=p(12), fill=255)
    d.rounded_rectangle((p(42), p(16), p(86), p(102)), radius=p(4), fill=0)
    d.ellipse((p(58), p(106), p(70), p(118)), fill=0)


def computer(d, p):
    d.rounded_rectangle((p(16), p(18), p(112), p(84)), radius=p(8), fill=255)
    d.rectangle((p(26), p(28), p(102), p(74)), fill=0)
    d.rounded_rectangle((p(4), p(90), p(124), p(104)), radius=p(6), fill=255)


def tv(d, p):
    d.rounded_rectangle((p(6), p(22), p(122), p(94)), radius=p(10), fill=255)
    d.rectangle((p(16), p(32), p(112), p(84)), fill=0)
    d.rounded_rectangle((p(40), p(104), p(88), p(114)), radius=p(4), fill=255)
    d.rectangle((p(58), p(94), p(70), p(106)), fill=255)


def printer(d, p):
    d.rectangle((p(32), p(10), p(96), p(40)), fill=255)
    d.rounded_rectangle((p(6), p(36), p(122), p(96)), radius=p(12), fill=255)
    d.rectangle((p(32), p(72), p(96), p(120)), fill=255)
    d.rectangle((p(40), p(80), p(88), p(112)), fill=0)
    d.ellipse((p(98), p(48), p(110), p(60)), fill=0)


def bars(lit):
    """Four bars of growing height, lit of them full: the signal of a device, bars-0.png to bars-3.png."""
    def paint(d, p):
        for index, height in enumerate((28, 52, 76, 100)):
            left = 10 + index * 30
            d.rounded_rectangle((p(left), p(116 - height), p(left + 20), p(116)), radius=p(5),
                                fill=255 if index <= lit else FAINT)
    return paint


def main():
    os.makedirs(MEDIA, exist_ok=True)
    render(512, 512, lambda d, s: mark(d, 0, 8 * s, 512 * s), BG).save(os.path.join(RESOURCES, "icon.png"), optimize=True)
    render(256, 256, lambda d, s: mark(d, 0, 4 * s, 256 * s), (0, 0, 0, 0), "RGBA").save(os.path.join(MEDIA, "logo.png"), optimize=True)
    render(1280, 720, fanart, BG).save(os.path.join(RESOURCES, "fanart.jpg"), quality=90, optimize=True)
    for name, paint in (("bluetooth.png", bluetooth), ("bluetooth-off.png", bluetooth_off),
                        ("bluetooth-connected.png", bluetooth_connected), ("headphones.png", headphones), ("speaker.png", speaker),
                        ("keyboard.png", keyboard), ("mouse.png", mouse), ("gamepad.png", gamepad), ("phone.png", phone),
                        ("computer.png", computer), ("tv.png", tv), ("printer.png", printer)):
        glyph(name, paint)
    for lit in range(4):
        glyph("bars-%d.png" % lit, bars(lit))
    # Shared textures and icons of the Monteiro add-ons.
    channels = os.path.join(ROOT, "script.m3u.channels", "resources", "skins", "default", "media")
    for name in ("white.png", "panel.png"):
        shutil.copy2(os.path.join(channels, name), os.path.join(MEDIA, name))


if __name__ == "__main__":
    main()
