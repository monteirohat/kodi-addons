"""Generate the Easy Picture window layouts with the palette and parts shared with Easy Channel and Easy Movie."""

import os

import generate_m3u_channels_skin as skin
from generate_m3u_channels_skin import (ACCENT, BG, FOCUS, ON_FOCUS, RAISED, STAR, SURFACE, TEXT, TEXT2, TEXT3, has, image, join,
                                        label, panel, window)


ADDON_ID = "script.easy.picture"
gallery_focus = has(300)
favorite = "String.IsEqual(ListItem.Property(favorite),true)"
TILE_WIDTH, TILE_HEIGHT = 315, 214


# Turns of a picture, clockwise, and whether it is mirrored first. gui.py keeps them as properties, without changing the file.
ROTATIONS = (0, 90, 180, 270)


def turned(left, top, width, height, texture, aspect, prefix, extra=""):
    """A picture drawn turned and mirrored as its properties say: one image for each of the eight positions, and only the
    matching one is shown. A quarter turn uses a box of swapped width and height around the same center, so the turned
    picture fills the original box."""
    controls = []
    for mirror in ("false", "true"):
        for rotation in ROTATIONS:
            quarter = rotation in (90, 270)
            w, h = (height, width) if quarter else (width, height)
            x, y = left + (width - w) // 2, top + (height - h) // 2
            flip = ' flipx="true"' if mirror == "true" else ""
            # Kodi turns anticlockwise for positive angles.
            turn = (f'\n  <animation effect="rotate" start="{-rotation}" end="{-rotation}" center="auto" time="0" condition="true">'
                    f"Conditional</animation>") if rotation else ""
            condition = f"String.IsEqual({prefix}(rotation),{rotation}) + String.IsEqual({prefix}(mirror),{mirror})"
            if rotation == 0:
                condition = f"[String.IsEmpty({prefix}(rotation)) | String.IsEqual({prefix}(rotation),0)] + "\
                            f"{'!' if mirror == 'false' else ''}String.IsEqual({prefix}(mirror),true)"
            controls.append(f"""<control type="image">
  <left>{x}</left>
  <top>{y}</top>
  <width>{w}</width>
  <height>{h}</height>
  <aspectratio>{aspect}</aspectratio>{extra}
  <texture background="true"{flip}>{texture}</texture>{turn}
  <visible>{condition}</visible>
</control>""")
    return controls


def tile():
    return [panel(10, 10, 295, 194, RAISED),
            image(117, 72, 80, 70, "picture.png", TEXT3),
            *turned(10, 10, 295, 194, "$INFO[ListItem.Art(thumb)]", "scale", "ListItem.Property", "\n  <fadetime>150</fadetime>"),
            # Favorite badge: a star on a dark disc, readable on any picture.
            panel(261, 18, 38, 38, BG, favorite),
            image(266, 23, 28, 28, "star.png", STAR, favorite)]


def gallery():
    return f"""<!-- Pictures. Left in the first column returns to the albums, handled in gui.py. -->
<control type="panel" id="300">
  <left>600</left>
  <top>220</top>
  <width>1260</width>
  <height>816</height>
  <onup>noop</onup>
  <onleft>noop</onleft>
  <onright>noop</onright>
  <orientation>vertical</orientation>
  <scrolltime>150</scrolltime>
  <itemlayout width="{TILE_WIDTH}" height="{TILE_HEIGHT}">
{join(*tile(), spaces=4)}
  </itemlayout>
  <focusedlayout width="{TILE_WIDTH}" height="{TILE_HEIGHT}">
{join(panel(0, 0, 315, 214, FOCUS, gallery_focus), panel(0, 0, 315, 214, RAISED, "!" + gallery_focus), *tile(), spaces=4)}
  </focusedlayout>
</control>"""


def main_screen():
    selected = "$INFO[Container(300).ListItem.Label]$INFO[Container(300).ListItem.Label2,  ·  ]"
    return join(
        image(0, 0, 1920, 1080, "white.png", BG),
        image(56, 30, 56, 56, "logo.png"),
        label(128, 28, 900, 60, f"$ADDON[{ADDON_ID} 30000]", "font32_title", TEXT),
        label(1360, 28, 500, 60, "$INFO[System.Time]", "font32_title", TEXT2, align="right"),
        "<!-- Toolbar. Tools are added from Python, see TOOLS in gui.py. -->",
        skin.make_toolbar(104),
        label(44, 212, 516, 36, "$INFO[Container(100).ListItem.Label]", "font12", ACCENT, has(100)),
        "<!-- Albums -->",
        panel(40, 256, 520, 784, SURFACE),
        skin.groups,
        "<!-- Gallery, with the album name, picture count and the selected picture in the header -->",
        panel(580, 110, 1300, 930, SURFACE),
        label(612, 114, 940, 56, "", "font32_title", TEXT, control_id=401),
        label(1560, 114, 290, 56, "", "font12", TEXT2, align="right", control_id=402),
        label(612, 166, 1240, 32, selected, "font12", TEXT2, gallery_focus),
        label(612, 166, 1240, 32, f"$ADDON[{ADDON_ID} 30020]", "font12", TEXT3, "!" + gallery_focus),
        image(604, 206, 1252, 2, "white.png", RAISED),
        label(620, 360, 1220, 300, "", "font13", TEXT2, align="center", center=False, control_id=404, wrap=True),
        gallery(),
        spaces=0)


def viewer_screen():
    """A picture in full screen. Python sets the pictures; a bar with the details shows at the bottom for a moment after
    each change."""
    shown = "String.IsEqual(Window.Property(details),true)"
    picture = lambda control_id: f"""<control type="image" id="{control_id}">
  <left>0</left>
  <top>0</top>
  <width>1920</width>
  <height>1080</height>
  <aspectratio>keep</aspectratio>
  <texture background="true"></texture>
</control>"""
    details = f"""<control type="group">
  <animation effect="slide" start="0,40" end="0,0" time="200" tween="cubic" easing="out">Visible</animation>
  <animation effect="fade" start="0" end="100" time="200">Visible</animation>
  <animation effect="fade" start="100" end="0" time="400">Hidden</animation>{skin.visible(shown)}
{join(panel(40, 940, 1840, 112, SURFACE),
      label(76, 952, 1200, 52, "$INFO[Window.Property(name)]", "font13", TEXT),
      label(76, 1000, 1200, 40, "$INFO[Window.Property(album)]$INFO[Window.Property(date),  ·  ]", "font12", TEXT2),
      label(1290, 952, 554, 52, "$INFO[Window.Property(position)]", "font13", TEXT2, align="right"),
      label(1090, 1000, 754, 40, f"$ADDON[{ADDON_ID} 30060]", "font12", TEXT3, align="right"), spaces=2)}
</control>"""
    return join(
        image(0, 0, 1920, 1080, "white.png", "FF000000"),
        "<!-- The next and previous pictures load behind the black background, so moving to them is quick. -->",
        picture(11), picture(12),
        image(0, 0, 1920, 1080, "white.png", "FF000000"),
        *turned(0, 0, 1920, 1080, "$INFO[Window.Property(picture)]", "keep", "Window.Property"),
        details,
        "<!-- An invisible button holds the focus, as a window needs a control that can take it. Keys are handled in gui.py. -->",
        """<control type="button" id="20">
  <left>0</left>
  <top>0</top>
  <width>1</width>
  <height>1</height>
  <texturefocus />
  <texturenofocus />
  <onup>noop</onup>
  <ondown>noop</ondown>
  <onleft>noop</onleft>
  <onright>noop</onright>
</control>""",
        spaces=0)


def main():
    skin.ADDON_ID, skin.GENERATOR = ADDON_ID, "generate_easy_picture_skin.py"
    files = {
        "script-easy-picture-main.xml": window("Main screen: toolbar and albums on the left, the pictures on the right.", 200, main_screen()),
        "script-easy-picture-viewer.xml": window("Modal picture in full screen, opened from the gallery.", 20, viewer_screen(), always=True),
    }
    folder = skin.skin_folder(ADDON_ID)
    os.makedirs(folder, exist_ok=True)
    for name, content in files.items():
        with open(os.path.join(folder, name), "w") as output:
            output.write(content)


if __name__ == "__main__":
    main()
