"""Easy Movie artwork: add-on icon, header mark, poster placeholder, the watched and next episode icons and fanart.

Uses the colors and shapes of Easy Channel's artwork. Requires Pillow and the Inter font (SIL Open Font
License, https://rsms.me/inter/). Run with the folder that holds Inter-Bold.ttf and Inter-Medium.ttf:

    python3 tools/generate_easy_movie_art.py path/to/inter/extras/ttf
"""

import math
import os
import shutil
import sys

from PIL import Image, ImageDraw, ImageFont

FONTS = sys.argv[1]
ADDON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "script.m3u.movies")
RESOURCES = os.path.join(ADDON, "resources")
MEDIA = os.path.join(RESOURCES, "skins", "default", "media")
BG = (14, 15, 17)
BLUE = (59, 139, 255)
BLUE_DARK = (43, 108, 214)
WHITE = (255, 255, 255)
GREY = (156, 158, 166)
CLEAR = (0, 0, 0, 0)
SCALE = 4  # draw large, then reduce for smooth edges
# The clapper stick opens upwards around its hinge on the left.
STICK_ANGLE = math.radians(-10)
HINGE = (96, 150)


def mark(draw, x, y, size, body=BLUE, stick=BLUE_DARK, glyph=WHITE, outline=None):
    """Clapperboard with a play glyph. (x, y) is the top left of a size x size box.

    With outline set, the body is drawn as an outline of that width, for single color icons.
    """
    u = size / 512
    p = lambda value: value * u
    point = lambda a, b: (x + p(a), y + p(b))

    def turned(a, b):
        dx, dy = a - HINGE[0], b - HINGE[1]
        return point(HINGE[0] + dx * math.cos(STICK_ANGLE) - dy * math.sin(STICK_ANGLE),
                     HINGE[1] + dx * math.sin(STICK_ANGLE) + dy * math.cos(STICK_ANGLE))

    def rounded_polygon(points, fill, radius):
        draw.polygon(points, fill=fill)
        draw.line(points + [points[0]], fill=fill, width=round(p(radius * 2)), joint="curve")
        for corner in points:
            r = p(radius)
            draw.ellipse((corner[0] - r, corner[1] - r, corner[0] + r, corner[1] + r), fill=fill)

    # Stick with diagonal stripes.
    rounded_polygon([turned(84, 104), turned(428, 104), turned(428, 146), turned(84, 146)], stick, 8)
    for left in (118, 196, 274, 352):
        draw.polygon([turned(left, 98), turned(left + 38, 98), turned(left + 14, 152), turned(left - 24, 152)],
                     fill=glyph if outline is None else CLEAR)
    # Body.
    body_box = (x + p(76), y + p(172), x + p(436), y + p(412))
    if outline is None:
        draw.rounded_rectangle(body_box, radius=p(56), fill=body)
    else:
        draw.rounded_rectangle(body_box, radius=p(56), outline=body, width=round(p(outline)))
    # Play glyph with rounded corners, the same shape as Easy Channel's.
    rounded_polygon([point(214, 240), point(214, 344), point(304, 292)], glyph, 9)


def render(width, height, paint, background, mode="RGB"):
    image = Image.new(mode, (width * SCALE, height * SCALE), background)
    paint(ImageDraw.Draw(image), SCALE)
    return image.resize((width, height), Image.LANCZOS)


icon = render(512, 512, lambda d, s: mark(d, 0, 4 * s, 512 * s), BG)
icon.save(os.path.join(RESOURCES, "icon.png"), optimize=True)

logo = render(256, 256, lambda d, s: mark(d, 0, 2 * s, 256 * s), CLEAR, "RGBA")
logo.save(os.path.join(MEDIA, "logo.png"), optimize=True)

# White single color version, tinted by the skin: poster placeholder and list icon.
film = render(128, 128, lambda d, s: mark(d, 0, 0, 128 * s, WHITE, WHITE, WHITE, outline=34), CLEAR, "RGBA")
film.save(os.path.join(MEDIA, "film.png"), optimize=True)

# Loading spinner, as in the Monteiro skin: three quarters of a ring, turned by the skin while something loads.
spinner = render(128, 128, lambda d, s: d.arc((12 * s, 12 * s, 116 * s, 116 * s), start=0, end=270, fill=WHITE, width=12 * s),
                 CLEAR, "RGBA")
spinner.save(os.path.join(MEDIA, "spinner.png"), optimize=True)


def eye(draw, s):
    """An open eye: the mark of a watched episode, apart from the check of a downloaded one."""
    p = lambda value: value * s
    upper = [(p(6 + 116 * t / 30), p(64 - 46 * math.sin(math.pi * t / 30))) for t in range(31)]
    lower = [(p(122 - 116 * t / 30), p(64 + 46 * math.sin(math.pi * t / 30))) for t in range(31)]
    draw.polygon(upper + lower, fill=WHITE)
    draw.ellipse((p(40), p(40), p(88), p(88)), fill=CLEAR)
    draw.ellipse((p(52), p(52), p(76), p(76)), fill=WHITE)


render(128, 128, eye, CLEAR, "RGBA").save(os.path.join(MEDIA, "eye.png"), optimize=True)

# The next song icon of Easy Music, for the next episode button of the playback controls.
shutil.copy2(os.path.join(ADDON, "..", "script.easy.music", "resources", "skins", "default", "media", "next.png"),
             os.path.join(MEDIA, "next.png"))


def fanart(draw, s):
    mark(draw, 120 * s, 200 * s, 300 * s)
    title = ImageFont.truetype(FONTS + "/Inter-Bold.ttf", 92 * s)
    tagline = ImageFont.truetype(FONTS + "/Inter-Medium.ttf", 34 * s)
    draw.text((452 * s, 268 * s), "Easy Movie", font=title, fill=WHITE)
    draw.text((456 * s, 392 * s), "Movie lists made easy", font=tagline, fill=GREY)
    draw.rounded_rectangle((456 * s, 456 * s, 536 * s, 464 * s), radius=4 * s, fill=BLUE)


render(1280, 720, fanart, BG).save(os.path.join(RESOURCES, "fanart.jpg"), quality=90, optimize=True)
