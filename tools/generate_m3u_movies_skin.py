"""Generate the Easy Movie window layouts with the palette and parts shared with Easy Channel."""

import os

import generate_m3u_channels_skin as skin
from generate_m3u_channels_skin import (ACCENT, BG, DANGER, FOCUS, ON_FOCUS, ON_FOCUS2, RAISED, RAISED2, STAR, SURFACE,
                                        TEXT, TEXT2, TEXT3, has, image, join, label, panel, textbox, window)


ADDON_ID = "script.m3u.movies"
favorite = "String.IsEqual(ListItem.Property(favorite),true)"
watched = "String.IsEqual(ListItem.Property(watched),true)"
catalog_focus = has(300)


def poster_item(title_color, detail_color, scroll=False):
    return [label(9, 308, 192, 40, "$INFO[ListItem.Label]", "font12", title_color, center=False, scroll=scroll),
            label(9, 346, 192, 32, "$INFO[ListItem.Property(duration)]", "font12", detail_color, center=False)]


def poster():
    return [panel(9, 10, 192, 288, RAISED),
            image(9, 10, 192, 288, "$INFO[ListItem.Art(poster)]", keep=True, fallback="film.png"),
            image(166, 18, 28, 28, "star.png", STAR, favorite),
            # Watched badge: a check mark on a dark disc, readable on any poster.
            panel(15, 16, 38, 38, BG, watched),
            image(18, 19, 32, 32, "check.png", ACCENT, watched)]


def catalog():
    return f"""<!-- Movie posters. Left in the first column returns to the groups, handled in gui.py. -->
<control type="panel" id="300">
  <left>600</left>
  <top>220</top>
  <width>1260</width>
  <height>816</height>
  <onup>100</onup>
  <onleft>noop</onleft>
  <onright>noop</onright>
  <orientation>vertical</orientation>
  <scrolltime>150</scrolltime>
  <itemlayout width="210" height="408">
{join(*poster(), *poster_item(TEXT2, TEXT3), spaces=4)}
  </itemlayout>
  <focusedlayout width="210" height="408">
{join(panel(1, 2, 208, 304, ACCENT, catalog_focus), panel(1, 2, 208, 304, RAISED, "!" + catalog_focus),
      *poster(), *poster_item(TEXT, TEXT2, scroll=True), spaces=4)}
  </focusedlayout>
</control>"""


def main_screen():
    return join(
        image(0, 0, 1920, 1080, "white.png", BG),
        image(56, 30, 56, 56, "logo.png"),
        label(128, 28, 900, 60, f"$ADDON[{ADDON_ID} 30050]", "font32_title", TEXT),
        label(1360, 28, 500, 60, "$INFO[System.Time]", "font32_title", TEXT2, align="right"),
        "<!-- Toolbar. Tools are added from Python, see TOOLS in gui.py. -->",
        skin.toolbar,
        label(44, 212, 516, 36, "$INFO[Container(100).ListItem.Label]", "font12", ACCENT, has(100)),
        "<!-- Groups -->",
        panel(40, 256, 520, 784, SURFACE),
        skin.groups,
        "<!-- Catalog, with the group name, movie count and hints in the header -->",
        panel(580, 110, 1300, 930, SURFACE),
        label(612, 114, 940, 56, "", "font32_title", TEXT, control_id=401),
        label(1560, 114, 290, 56, "", "font12", TEXT2, align="right", control_id=402),
        label(612, 166, 1240, 32, f"$ADDON[{ADDON_ID} 30051]", "font12", TEXT3, "!Player.HasVideo"),
        image(612, 176, 12, 12, "panel.png", ACCENT, "Player.HasVideo"),
        label(636, 166, 1216, 32, f"$ADDON[{ADDON_ID} 30052]: $INFO[VideoPlayer.Title]", "font12", ACCENT, "Player.HasVideo"),
        image(604, 206, 1252, 2, "white.png", RAISED),
        label(620, 300, 1220, 300, "", "font13", TEXT2, align="center", center=False, control_id=403, wrap=True),
        catalog(),
        spaces=0)


def details_button(control_id, left, onleft, onright, string_id, focus_color, focus_text, top=840, width=270, ondown="noop"):
    label_text = f"\n  <label>$ADDON[{ADDON_ID} {string_id}]</label>" if string_id else ""
    return f"""<control type="button" id="{control_id}">
  <left>{left}</left>
  <top>{top}</top>
  <width>{width}</width>
  <height>76</height>
  <onup>noop</onup>
  <ondown>{ondown}</ondown>
  <onleft>{onleft}</onleft>
  <onright>{onright}</onright>
  <font>font13</font>
  <align>center</align>
  <aligny>center</aligny>
  <textcolor>{TEXT}</textcolor>
  <focusedcolor>{focus_text}</focusedcolor>
  <texturefocus border="16" colordiffuse="{focus_color}">panel.png</texturefocus>
  <texturenofocus border="16" colordiffuse="{RAISED}">panel.png</texturenofocus>{label_text}
</control>"""


def details_screen():
    favorite_on = "String.IsEqual(Window.Property(favorite),true)"
    return join(
        image(0, 0, 1920, 1080, "white.png", "D9000000"),
        panel(260, 130, 1400, 820, SURFACE),
        panel(310, 180, 400, 600, RAISED),
        image(310, 180, 400, 600, "$INFO[Window.Property(poster)]", keep=True, fallback="film.png"),
        image(660, 196, 36, 36, "star.png", STAR, favorite_on),
        textbox(760, 180, 850, 120, "$INFO[Window.Property(title)]", "font36_title", TEXT),
        label(760, 310, 850, 44, "$INFO[Window.Property(group)]", "font13", ACCENT),
        label(760, 360, 850, 40, "$INFO[Window.Property(duration)]", "font12", TEXT2),
        label(760, 404, 850, 40, "$INFO[Window.Property(list)]", "font12", TEXT2),
        "<!-- Description from Cinemeta, for the videos of folders -->",
        textbox(760, 460, 850, 340, "$INFO[Window.Property(plot)]", "font12", TEXT2),
        details_button(201, 760, 203, 202, 30110, FOCUS, ON_FOCUS),
        details_button(202, 1050, 201, 203, None, FOCUS, ON_FOCUS),
        details_button(203, 1340, 202, 201, 30018, DANGER, TEXT),
        spaces=0)


def series_screen():
    seasons_focus, episodes_focus = has(300), has(400)
    season_label = lambda color, condition=None: label(0, 0, 208, 64, "$INFO[ListItem.Label]", "font13", color, condition, align="center")
    seasons = f"""<control type="list" id="300">
  <left>620</left>
  <top>444</top>
  <width>1100</width>
  <height>64</height>
  <orientation>horizontal</orientation>
  <onup>201</onup>
  <ondown>400</ondown>
  <scrolltime>120</scrolltime>
  <itemlayout width="222" height="64">
{join(panel(0, 0, 208, 64, RAISED), season_label(TEXT2), spaces=4)}
  </itemlayout>
  <focusedlayout width="222" height="64">
{join(panel(0, 0, 208, 64, FOCUS, seasons_focus), panel(0, 0, 208, 64, RAISED2, "!" + seasons_focus),
      season_label(ON_FOCUS, seasons_focus), season_label(ACCENT, "!" + seasons_focus), spaces=4)}
  </focusedlayout>
</control>"""
    episode = lambda name, detail, condition=None, scroll=False: [
        image(22, 19, 32, 32, "check.png", ACCENT, watched + (" + " + condition if condition else "")),
        label(72, 0, 780, 70, "$INFO[ListItem.Label]", "font13", name, condition, scroll=scroll),
        label(860, 0, 216, 70, "$INFO[ListItem.Label2]", "font12", detail, condition, align="right")]
    episodes = f"""<control type="list" id="400">
  <left>620</left>
  <top>528</top>
  <width>1100</width>
  <height>420</height>
  <onup>300</onup>
  <onleft>noop</onleft>
  <onright>noop</onright>
  <scrolltime>120</scrolltime>
  <itemlayout height="70">
{join(*episode(TEXT2, TEXT3), spaces=4)}
  </itemlayout>
  <focusedlayout height="70">
{join(panel(0, 2, 1100, 66, FOCUS, episodes_focus), panel(0, 2, 1100, 66, RAISED, "!" + episodes_focus),
      *episode(ON_FOCUS, ON_FOCUS2, episodes_focus, True), *episode(TEXT, TEXT2, "!" + episodes_focus), spaces=4)}
  </focusedlayout>
</control>"""
    return join(
        image(0, 0, 1920, 1080, "white.png", "D9000000"),
        panel(160, 80, 1600, 920, SURFACE),
        panel(210, 130, 360, 540, RAISED),
        image(210, 130, 360, 540, "$INFO[Window.Property(poster)]", keep=True, fallback="film.png"),
        image(522, 146, 34, 34, "star.png", STAR, "String.IsEqual(Window.Property(favorite),true)"),
        textbox(620, 126, 1100, 110, "$INFO[Window.Property(title)]", "font36_title", TEXT),
        label(620, 240, 1100, 40, "$INFO[Window.Property(info)]", "font12", TEXT2),
        label(620, 282, 1100, 40, "$INFO[Window.Property(group)]", "font13", ACCENT),
        "<!-- Description from Cinemeta, below the poster -->",
        textbox(210, 696, 360, 280, "$INFO[Window.Property(plot)]", "font12", TEXT2),
        details_button(201, 620, 203, 202, None, FOCUS, ON_FOCUS, top=340, width=360, ondown="300"),
        details_button(202, 1000, 201, 203, None, FOCUS, ON_FOCUS, top=340, width=340, ondown="300"),
        details_button(203, 1360, 202, 201, 30122, DANGER, TEXT, top=340, width=360, ondown="300"),
        seasons,
        episodes,
        spaces=0)


def main():
    skin.ADDON_ID, skin.GENERATOR = ADDON_ID, "generate_m3u_movies_skin.py"
    files = {
        "script-m3u-movies-main.xml": window("Main screen: toolbar and groups on the left, movie posters on the right.", 200, main_screen()),
        "script-m3u-movies-details.xml": window("Modal movie details opened from a poster.", 201, details_screen(), always=True),
        "script-m3u-movies-series.xml": window("Modal series details with seasons and episodes, opened from a series poster.", 201,
                                               series_screen(), always=True),
        "script-m3u-movies-manager.xml": skin.manager("Modal list manager opened from the gear icon.", "gear.png", 30060, "film.png",
            [skin.button(201, 440, 248, 203, 204, 30000), skin.button(204, 704, 248, 201, 202, 30093),
             skin.button(202, 968, 248, 204, 203, 30062), skin.button(203, 1232, 248, 202, 201, 30063)]),
        "script-m3u-movies-repos.xml": skin.manager("Modal GitHub repository manager opened from the list manager.", "search.png", 30075, "search.png",
            [skin.button(201, 440, 512, 203, 203, 30076), skin.button(203, 968, 512, 201, 201, 30063)]),
    }
    folder = skin.skin_folder(ADDON_ID)
    os.makedirs(folder, exist_ok=True)
    for name, content in files.items():
        with open(os.path.join(folder, name), "w") as output:
            output.write(content)


if __name__ == "__main__":
    main()
