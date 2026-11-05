"""Social preview of the GitHub repository: the icons of the three add-ons over the repository fanart, with the name
Monteiro. GitHub shows it when the repository link is shared. Upload it in Settings > Social preview.

Requires Pillow and the Inter font (SIL Open Font License, https://rsms.me/inter/). Run with the folder that holds
Inter-Bold.ttf and Inter-Medium.ttf:

    python3 tools/generate_social_preview.py path/to/inter/extras/ttf
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = sys.argv[1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, ".github", "social-preview.png")
WIDTH, HEIGHT = 1280, 640
WHITE = (255, 255, 255)
GREY = (176, 186, 214)
ICONS = [("script.m3u.channels/resources/icon.png", "Easy Channel"),
         ("script.m3u.movies/resources/icon.png", "Easy Movie"),
         ("script.hdmi.switcher/resources/hdmi-switcher-icon.png", "HDMI Switcher")]
ICON = 150
RADIUS = 34


def rounded(image, size, radius):
    image = image.convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size * 4 - 1, size * 4 - 1), radius=radius * 4, fill=255)
    image.putalpha(mask.resize((size, size), Image.LANCZOS))
    return image


def main():
    fanart = Image.open(os.path.join(ROOT, "repository.monteiromedia", "resources", "fanart.jpg")).convert("RGB")
    # The fanart is 1280 by 720: keep its middle, where the mark of the repository is.
    top = (fanart.height - HEIGHT) // 2
    canvas = fanart.crop((0, top, WIDTH, top + HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    title = ImageFont.truetype(os.path.join(FONTS, "Inter-Bold.ttf"), 96)
    tagline = ImageFont.truetype(os.path.join(FONTS, "Inter-Medium.ttf"), 30)
    caption = ImageFont.truetype(os.path.join(FONTS, "Inter-Medium.ttf"), 24)
    left = 84
    draw.text((left, 92), "Monteiro", font=title, fill=WHITE)
    draw.text((left, 214), "Open-source Kodi add-ons for LibreELEC and Raspberry Pi", font=tagline, fill=GREY)
    gap = 56
    for index, (path, name) in enumerate(ICONS):
        x, y = left + index * (ICON + gap), 316
        icon = rounded(Image.open(os.path.join(ROOT, path)), ICON, RADIUS)
        # A soft shadow lifts the icons from the dark background.
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle((x, y + 10, x + ICON, y + ICON + 10), radius=RADIUS, fill=(0, 0, 0, 150))
        canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(14)))
        canvas.alpha_composite(icon, (x, y))
        draw = ImageDraw.Draw(canvas)
        draw.text((x + ICON // 2, y + ICON + 26), name, font=caption, fill=WHITE, anchor="mt")
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    canvas.convert("RGB").save(OUTPUT, optimize=True)


if __name__ == "__main__":
    main()
