"""Generate the Easy Files window layouts with the palette and parts shared with Easy Channel and Easy Movie."""

import os

import generate_m3u_channels_skin as skin
from generate_m3u_channels_skin import (ACCENT, BG, FOCUS, ON_FOCUS, ON_FOCUS2, RAISED, SURFACE, TEXT, TEXT2, TEXT3, has, image, join,
                                        label, panel, window)


ADDON_ID = "script.easy.files"
places_focus, items_focus = has(200), has(300)


def places():
    """Places: an icon, the name and the free space of the drive."""
    row = lambda name, detail, icon, condition=None: [
        image(22, 20, 44, 44, "$INFO[ListItem.Icon]", icon, condition),
        label(84, 6, 400, 44, "$INFO[ListItem.Label]", "font13", name, condition),
        label(84, 46, 400, 32, "$INFO[ListItem.Label2]", "font12", detail, condition)]
    return f"""<!-- Places. Right moves to the folder, handled in gui.py. -->
<control type="list" id="200">
  <left>50</left>
  <top>180</top>
  <width>500</width>
  <height>840</height>
  <onleft>noop</onleft>
  <onright>noop</onright>
  <onup>noop</onup>
  <scrolltime>120</scrolltime>
  <itemlayout height="90">
{join(*row(TEXT2, TEXT3, TEXT3), spaces=4)}
  </itemlayout>
  <focusedlayout height="90">
{join(panel(0, 2, 500, 84, FOCUS, places_focus), panel(0, 2, 500, 84, RAISED, "!" + places_focus),
      image(10, 30, 5, 28, "white.png", ACCENT, "!" + places_focus),
      *row(ON_FOCUS, ON_FOCUS2, ON_FOCUS, places_focus), *row(TEXT, TEXT2, TEXT2, "!" + places_focus), spaces=4)}
  </focusedlayout>
</control>"""


def items():
    """The folders and files of the folder shown: an icon, the name, and the size and date on the right."""
    row = lambda name, detail, icon, condition=None, scroll=False: [
        image(24, 18, 48, 48, "$INFO[ListItem.Icon]", icon, condition),
        label(96, 0, 760, 84, "$INFO[ListItem.Label]", "font13", name, condition, scroll=scroll),
        label(880, 0, 370, 84, "$INFO[ListItem.Label2]", "font12", detail, condition, align="right")]
    return f"""<!-- Folders and files. Left returns to the places, and holding OK opens the options, handled in gui.py. -->
<control type="list" id="300">
  <left>590</left>
  <top>222</top>
  <width>1280</width>
  <height>728</height>
  <onleft>noop</onleft>
  <onright>noop</onright>
  <scrolltime>120</scrolltime>
  <itemlayout height="91">
{join(*row(TEXT, TEXT2, TEXT2), spaces=4)}
  </itemlayout>
  <focusedlayout height="91">
{join(panel(0, 2, 1280, 86, FOCUS, items_focus), panel(0, 2, 1280, 86, RAISED, "!" + items_focus),
      *row(ON_FOCUS, ON_FOCUS2, ON_FOCUS, items_focus, True), *row(TEXT, TEXT2, TEXT2, "!" + items_focus), spaces=4)}
  </focusedlayout>
</control>"""


def main_screen():
    clipboard = "!String.IsEmpty(Window.Property(clipboard))"
    return join(
        image(0, 0, 1920, 1080, "white.png", BG),
        image(56, 30, 56, 56, "logo.png"),
        label(128, 28, 900, 60, f"$ADDON[{ADDON_ID} 30000]", "font32_title", TEXT),
        label(1360, 28, 500, 60, "$INFO[System.Time]", "font32_title", TEXT2, align="right"),
        "<!-- Places -->",
        panel(40, 110, 520, 930, SURFACE),
        label(70, 124, 460, 44, f"$ADDON[{ADDON_ID} 30070]", "font12", ACCENT),
        places(),
        "<!-- Folder, with its name, path and contents in the header -->",
        panel(580, 110, 1300, 930, SURFACE),
        label(612, 114, 900, 56, "", "font32_title", TEXT, control_id=401),
        label(1520, 114, 330, 56, "", "font12", TEXT2, align="right", control_id=403),
        label(612, 166, 1240, 32, "", "font12", TEXT3, control_id=402),
        image(604, 206, 1252, 2, "white.png", RAISED),
        label(620, 360, 1220, 200, "", "font13", TEXT2, align="center", center=False, control_id=404, wrap=True),
        items(),
        image(604, 960, 1252, 2, "white.png", RAISED),
        label(612, 970, 1240, 56, "$INFO[Window.Property(clipboard)]", "font12", ACCENT, clipboard),
        label(612, 970, 1240, 56, f"$ADDON[{ADDON_ID} 30071]", "font12", TEXT3, "!" + clipboard),
        spaces=0)


def info_screen():
    rows = [(30072, "kind"), (30073, "size"), (30074, "contents"), (30075, "modified"), (30076, "place"), (30077, "free")]
    lines = []
    for index, (string_id, key) in enumerate(rows):
        top = 400 + index * 64
        condition = f"!String.IsEmpty(Window.Property({key}))"
        lines += [label(500, top, 260, 56, f"$ADDON[{ADDON_ID} {string_id}]", "font12", TEXT3, condition),
                  label(780, top, 640, 56, f"$INFO[Window.Property({key})]", "font13", TEXT, condition, scroll=True)]
    close = f"""<control type="button" id="201">
  <left>810</left>
  <top>820</top>
  <width>300</width>
  <height>76</height>
  <onup>noop</onup>
  <ondown>noop</ondown>
  <onleft>noop</onleft>
  <onright>noop</onright>
  <font>font13</font>
  <align>center</align>
  <aligny>center</aligny>
  <textcolor>{TEXT}</textcolor>
  <focusedcolor>{ON_FOCUS}</focusedcolor>
  <texturefocus border="16" colordiffuse="{FOCUS}">panel.png</texturefocus>
  <texturenofocus border="16" colordiffuse="{RAISED}">panel.png</texturenofocus>
  <label>$ADDON[{ADDON_ID} 30078]</label>
</control>"""
    return join(
        image(0, 0, 1920, 1080, "white.png", "D9000000"),
        panel(460, 180, 1000, 760, SURFACE),
        panel(500, 220, 140, 140, RAISED),
        image(530, 250, 80, 80, "$INFO[Window.Property(icon)]", TEXT2),
        skin.textbox(670, 220, 750, 140, "$INFO[Window.Property(name)]", "font32_title", TEXT),
        image(484, 380, 952, 2, "white.png", RAISED),
        *lines,
        close,
        spaces=0)


def main():
    skin.ADDON_ID, skin.GENERATOR = ADDON_ID, "generate_easy_files_skin.py"
    files = {
        "script-easy-files-main.xml": window("Main screen: places on the left, the folder on the right.", 200, main_screen()),
        "script-easy-files-info.xml": window("Modal details of a file or folder.", 201, info_screen(), always=True),
    }
    folder = skin.skin_folder(ADDON_ID)
    os.makedirs(folder, exist_ok=True)
    for name, content in files.items():
        with open(os.path.join(folder, name), "w") as output:
            output.write(content)


if __name__ == "__main__":
    main()
