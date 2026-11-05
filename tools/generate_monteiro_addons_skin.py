"""Generate the Monteiro Add-ons window layout with the palette and parts shared with Easy Channel and Easy Movie."""

import os

import generate_m3u_channels_skin as skin
from generate_m3u_channels_skin import (ACCENT, BG, FOCUS, ON_FOCUS, ON_FOCUS2, RAISED, SURFACE, TEXT, TEXT2, TEXT3, has, image,
                                        join, label, panel, window)


ADDON_ID = "script.monteiro.addons"
list_focus = has(300)
installed = "!String.IsEmpty(ListItem.Property(state))"
both = lambda *conditions: " + ".join(condition for condition in conditions if condition)


def addons():
    """The add-ons: icon, name and summary, and the category, state and version on the right."""
    row = lambda name, detail, category, condition=None, scroll=False: [
        image(18, 16, 72, 72, "$INFO[ListItem.Icon]", None, condition, keep=True, fallback="puzzle.png"),
        label(112, 8, 760, 48, "$INFO[ListItem.Label]", "font13", name, condition, scroll=scroll),
        label(112, 54, 760, 40, "$INFO[ListItem.Label2]", "font12", detail, condition),
        label(890, 8, 340, 48, "$INFO[ListItem.Property(category)]", "font12", category, condition, align="right"),
        # Installed add-ons have a green check after the version, which then ends before it.
        image(1204, 59, 30, 30, "installed.png", None, both(condition, installed)),
        label(840, 54, 352, 40, "$INFO[ListItem.Property(state_label),,  ·  ]$INFO[ListItem.Property(version)]", "font12",
              detail, both(condition, installed), align="right"),
        label(890, 54, 340, 40, "$INFO[ListItem.Property(version)]", "font12", detail, both(condition, "!" + installed), align="right")]
    return f"""<!-- Add-ons. Left returns to the repositories, and holding OK opens the options, handled in gui.py. -->
<control type="list" id="300">
  <left>600</left>
  <top>222</top>
  <width>1260</width>
  <height>808</height>
  <onleft>noop</onleft>
  <onright>noop</onright>
  <onup>noop</onup>
  <scrolltime>120</scrolltime>
  <itemlayout height="104">
{join(*row(TEXT, TEXT2, ACCENT), spaces=4)}
  </itemlayout>
  <focusedlayout height="104">
{join(panel(0, 2, 1260, 100, FOCUS, list_focus), panel(0, 2, 1260, 100, RAISED, "!" + list_focus),
      *row(ON_FOCUS, ON_FOCUS2, ON_FOCUS, list_focus, True), *row(TEXT, TEXT2, ACCENT, "!" + list_focus), spaces=4)}
  </focusedlayout>
</control>"""


def main_screen():
    return join(
        image(0, 0, 1920, 1080, "white.png", BG),
        image(56, 30, 56, 56, "logo.png"),
        label(1360, 28, 500, 60, "$INFO[System.Time]", "font32_title", TEXT2, align="right"),
        "<!-- Toolbar. Tools are added from Python, see TOOLS in gui.py. -->",
        skin.make_toolbar(104),
        label(44, 212, 516, 36, "$INFO[Container(100).ListItem.Label]", "font12", ACCENT, has(100)),
        "<!-- Repositories -->",
        panel(40, 256, 520, 784, SURFACE),
        skin.groups,
        "<!-- Add-ons of the repository, with its name, the add-on count and the keys in the header -->",
        panel(580, 110, 1300, 930, SURFACE),
        label(612, 114, 940, 56, "", "font32_title", TEXT, control_id=401),
        label(1560, 114, 290, 56, "", "font12", TEXT2, align="right", control_id=402),
        label(612, 166, 1240, 32, f"$ADDON[{ADDON_ID} 30007]", "font12", TEXT3),
        image(604, 206, 1252, 2, "white.png", RAISED),
        label(620, 360, 1220, 300, "", "font13", TEXT2, align="center", center=False, control_id=404, wrap=True),
        addons(),
        spaces=0)


def details_button(control_id, string_id, condition=None):
    return f"""<control type="button" id="{control_id}">
  <width>auto</width>
  <height>76</height>
  <font>font13</font>
  <textoffsetx>40</textoffsetx>
  <align>center</align>
  <aligny>center</aligny>
  <textcolor>{TEXT}</textcolor>
  <focusedcolor>{ON_FOCUS}</focusedcolor>
  <texturefocus border="16" colordiffuse="{FOCUS}">panel.png</texturefocus>
  <texturenofocus border="16" colordiffuse="{RAISED}">panel.png</texturenofocus>
  <label>$ADDON[{ADDON_ID} {string_id}]</label>{skin.visible(condition)}
</control>"""


def details_screen():
    """Details of an add-on: icon, name, version, author, category, description and screenshots, with its actions."""
    prop = lambda name: f"$INFO[Window.Property({name})]"
    is_set = lambda name: f"!String.IsEmpty(Window.Property({name}))"
    installed_here = "String.IsEqual(Window.Property(installed),true)"
    shots_focus = has(500)
    # A list draws nothing outside itself, so each screenshot sits 6 inside its item, where the focus border fits.
    shot = lambda condition=None: [panel(6, 6, 448, 252, RAISED, condition),
                                   image(6, 6, 448, 252, "$INFO[ListItem.Icon]", None, condition, keep=True)]
    shots = f"""<!-- Screenshots. OK shows one in full screen, handled in gui.py. -->
<control type="list" id="500">
  <left>114</left>
  <top>598</top>
  <width>1692</width>
  <height>264</height>
  <orientation>horizontal</orientation>
  <onup>noop</onup>
  <ondown>9000</ondown>
  <onleft>noop</onleft>
  <onright>noop</onright>
  <scrolltime>150</scrolltime>
  <itemlayout width="472" height="264">
{join(*shot(), spaces=4)}
  </itemlayout>
  <focusedlayout width="472" height="264">
{join(panel(0, 0, 460, 264, FOCUS, shots_focus), *shot(), spaces=4)}
  </focusedlayout>{skin.visible(is_set("screenshots"))}
</control>"""
    buttons = f"""<control type="grouplist" id="9000">
  <left>120</left>
  <top>904</top>
  <width>1680</width>
  <height>76</height>
  <orientation>horizontal</orientation>
  <itemgap>16</itemgap>
  <onup>500</onup>
  <ondown>noop</ondown>
{join(details_button(201, 30014, "!" + installed_here), details_button(203, 30018, is_set("update")),
      details_button(202, 30012, installed_here + " + " + is_set("opens")), details_button(204, 30013, installed_here),
      details_button(205, 30020), spaces=2)}
</control>"""
    zoom = f"""<control type="group">{skin.visible(is_set("zoom"))}
{join(image(0, 0, 1920, 1080, "white.png", "F2000000"), image(0, 0, 1920, 1080, prop("zoom"), None, keep=True), spaces=2)}
</control>"""
    return join(
        image(0, 0, 1920, 1080, "white.png", "E6000000"),
        panel(80, 50, 1760, 980, SURFACE),
        panel(120, 90, 210, 210, RAISED),
        image(135, 105, 180, 180, prop("icon"), None, keep=True, fallback="puzzle.png"),
        label(370, 86, 1430, 76, prop("name"), "font45_title", TEXT),
        label(370, 162, 1430, 44, prop("details"), "font13", TEXT2),
        label(370, 210, 1000, 44, prop("category"), "font13", ACCENT),
        image(370, 266, 32, 32, "installed.png", None, installed_here),
        label(414, 258, 1000, 48, f"$ADDON[{ADDON_ID} 30004]", "font13", TEXT2, installed_here),
        label(370, 258, 1000, 48, prop("update_label"), "font13", ACCENT, "!" + installed_here),
        image(120, 330, 1680, 2, "white.png", RAISED),
        f"""<control type="textbox">
  <left>120</left>
  <top>352</top>
  <width>1680</width>
  <height>{224}</height>
  <font>font13</font>
  <textcolor>{TEXT2}</textcolor>
  <label>{prop("description")}</label>
  <autoscroll time="3000" delay="8000" repeat="8000">true</autoscroll>
</control>""",
        shots,
        buttons,
        zoom,
        spaces=0)


def main():
    skin.ADDON_ID, skin.GENERATOR = ADDON_ID, "generate_monteiro_addons_skin.py"
    files = {
        "script-monteiro-addons-main.xml": window("Main screen: toolbar and repositories on the left, their add-ons on the right.", 200,
                                                  main_screen()),
        "script-monteiro-addons-details.xml": window("Modal details of an add-on, opened from the list.", 9000, details_screen(), always=True),
    }
    folder = skin.skin_folder(ADDON_ID)
    os.makedirs(folder, exist_ok=True)
    for name, content in files.items():
        with open(os.path.join(folder, name), "w") as output:
            output.write(content)


if __name__ == "__main__":
    main()
