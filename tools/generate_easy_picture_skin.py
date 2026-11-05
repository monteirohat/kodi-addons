"""Generate the Easy Picture window layouts with the palette and parts shared with Easy Channel and Easy Movie."""

import os

import generate_m3u_channels_skin as skin
from generate_m3u_channels_skin import (ACCENT, BG, FOCUS, ON_FOCUS, RAISED, STAR, SURFACE, TEXT, TEXT2, TEXT3, has, image, join,
                                        label, panel, window)


ADDON_ID = "script.easy.picture"
gallery_focus = has(300)
favorite = "String.IsEqual(ListItem.Property(favorite),true)"
TILE_WIDTH, TILE_HEIGHT = 315, 214


def thumb(left, top, width, height, texture):
    """A picture cropped to fill its tile, loaded in the background so the gallery scrolls smoothly."""
    return f"""<control type="image">
  <left>{left}</left>
  <top>{top}</top>
  <width>{width}</width>
  <height>{height}</height>
  <aspectratio>scale</aspectratio>
  <fadetime>150</fadetime>
  <texture background="true">{texture}</texture>
</control>"""


def tile():
    return [panel(10, 10, 295, 194, RAISED),
            image(117, 72, 80, 70, "picture.png", TEXT3),
            thumb(10, 10, 295, 194, "$INFO[ListItem.Art(thumb)]"),
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
    """A picture in full screen. Python sets the pictures; the details show for a moment after each change."""
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
  <animation effect="fade" start="0" end="100" time="200">Visible</animation>
  <animation effect="fade" start="100" end="0" time="400">Hidden</animation>{skin.visible(shown)}
{join(image(0, 0, 1920, 200, "shade.png", "FF000000"),
      label(64, 40, 1400, 60, "$INFO[Window.Property(name)]", "font32_title", TEXT),
      label(64, 100, 1400, 40, "$INFO[Window.Property(album)]$INFO[Window.Property(date),  ·  ]", "font12", TEXT2),
      label(1460, 40, 400, 60, "$INFO[Window.Property(position)]", "font32_title", TEXT2, align="right"),
      label(64, 1010, 1792, 40, f"$ADDON[{ADDON_ID} 30060]", "font12", TEXT2, align="center"), spaces=2)}
</control>"""
    return join(
        image(0, 0, 1920, 1080, "white.png", "FF000000"),
        "<!-- The next and previous pictures load behind the black background, so moving to them is quick. -->",
        picture(11), picture(12),
        image(0, 0, 1920, 1080, "white.png", "FF000000"),
        picture(10),
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
