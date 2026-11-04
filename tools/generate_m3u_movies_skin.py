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
        skin.make_toolbar(104),
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


def details_button(control_id, left, onleft, onright, string_id, focus_color, focus_text, top=840, width=270, ondown="noop",
                   condition=None):
    """A button of a details window. Without onleft and onright, a grouplist places it and moves between its buttons."""
    label_text = f"\n  <label>$ADDON[{ADDON_ID} {string_id}]</label>" if string_id else ""
    sides = f"\n  <onleft>{onleft}</onleft>\n  <onright>{onright}</onright>" if onleft else ""
    return f"""<control type="button" id="{control_id}">
  <left>{left}</left>
  <top>{top}</top>
  <width>{width}</width>
  <height>76</height>
  <onup>noop</onup>
  <ondown>{ondown}</ondown>{sides}
  <font>font13</font>
  <align>center</align>
  <aligny>center</aligny>
  <textcolor>{TEXT}</textcolor>
  <focusedcolor>{focus_text}</focusedcolor>
  <texturefocus border="16" colordiffuse="{focus_color}">panel.png</texturefocus>
  <texturenofocus border="16" colordiffuse="{RAISED}">panel.png</texturenofocus>{label_text}{skin.visible(condition)}
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


def seasons_and_episodes(onup=201, top=444, height=420, condition=None):
    """Seasons as a row of tabs, and the episodes of the selected season below."""
    seasons_focus, episodes_focus = has(300), has(400)
    season_label = lambda color, condition=None: label(0, 0, 208, 64, "$INFO[ListItem.Label]", "font13", color, condition, align="center")
    seasons = f"""<control type="list" id="300">
  <left>620</left>
  <top>{top}</top>
  <width>1100</width>
  <height>64</height>
  <orientation>horizontal</orientation>
  <onup>{onup}</onup>
  <ondown>400</ondown>
  <scrolltime>120</scrolltime>
  <itemlayout width="222" height="64">
{join(panel(0, 0, 208, 64, RAISED), season_label(TEXT2), spaces=4)}
  </itemlayout>
  <focusedlayout width="222" height="64">
{join(panel(0, 0, 208, 64, FOCUS, seasons_focus), panel(0, 0, 208, 64, RAISED2, "!" + seasons_focus),
      season_label(ON_FOCUS, seasons_focus), season_label(ACCENT, "!" + seasons_focus), spaces=4)}
  </focusedlayout>{skin.visible(condition)}
</control>"""
    episode = lambda name, detail, condition=None, scroll=False: [
        image(22, 19, 32, 32, "check.png", ACCENT, watched + (" + " + condition if condition else "")),
        label(72, 0, 780, 70, "$INFO[ListItem.Label]", "font13", name, condition, scroll=scroll),
        label(860, 0, 216, 70, "$INFO[ListItem.Label2]", "font12", detail, condition, align="right")]
    episodes = f"""<control type="list" id="400">
  <left>620</left>
  <top>{top + 84}</top>
  <width>1100</width>
  <height>{height}</height>
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
  </focusedlayout>{skin.visible(condition)}
</control>"""
    return seasons, episodes


def series_screen():
    seasons, episodes = seasons_and_episodes()
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


def catalog_screen():
    """The Cinemeta catalog: Movies and Series tabs, categories on the left and posters on the right."""
    tab_focus = has(100)
    tab_label = lambda color, condition=None: label(0, 0, 200, 96, "$INFO[ListItem.Label]", "font13", color, condition, align="center")
    tabs = f"""<control type="list" id="100">
  <left>40</left>
  <top>110</top>
  <width>416</width>
  <height>96</height>
  <orientation>horizontal</orientation>
  <onleft>noop</onleft>
  <onright>101</onright>
  <ondown>200</ondown>
  <scrolltime>120</scrolltime>
  <itemlayout width="208" height="96">
{join(panel(0, 0, 200, 96, SURFACE), tab_label(TEXT2), spaces=4)}
  </itemlayout>
  <focusedlayout width="208" height="96">
{join(panel(0, 0, 200, 96, FOCUS, tab_focus), panel(0, 0, 200, 96, RAISED, "!" + tab_focus),
      tab_label(ON_FOCUS, tab_focus), tab_label(ACCENT, "!" + tab_focus), spaces=4)}
  </focusedlayout>
</control>"""
    addons_button = f"""<control type="button" id="101">
  <left>456</left>
  <top>110</top>
  <width>104</width>
  <height>96</height>
  <onup>noop</onup>
  <ondown>200</ondown>
  <onleft>100</onleft>
  <onright>300</onright>
  <texturefocus border="16" colordiffuse="{FOCUS}">panel.png</texturefocus>
  <texturenofocus border="16" colordiffuse="{SURFACE}">panel.png</texturenofocus>
</control>"""
    return join(
        image(0, 0, 1920, 1080, "white.png", BG),
        image(56, 30, 56, 56, "catalog.png", ACCENT),
        label(128, 28, 900, 60, f"$ADDON[{ADDON_ID} 30200]", "font32_title", TEXT),
        label(1360, 28, 500, 60, "$INFO[System.Time]", "font32_title", TEXT2, align="right"),
        "<!-- Movies and Series, and the addons button -->",
        tabs,
        addons_button,
        image(482, 132, 52, 52, "puzzle.png", ON_FOCUS, has(101)),
        image(482, 132, 52, 52, "puzzle.png", TEXT2, "!" + has(101)),
        label(44, 212, 516, 36, f"$ADDON[{ADDON_ID} 30213]", "font12", TEXT3, "!" + has(101)),
        label(44, 212, 516, 36, f"$ADDON[{ADDON_ID} 30270]", "font12", ACCENT, has(101)),
        "<!-- Categories, filled from gui.py -->",
        panel(40, 256, 520, 784, SURFACE),
        skin.groups,
        "<!-- Posters, with the category name, title count and hints in the header -->",
        panel(580, 110, 1300, 930, SURFACE),
        label(612, 114, 940, 56, "", "font32_title", TEXT, control_id=401),
        label(1560, 114, 290, 56, "", "font12", TEXT2, align="right", control_id=402),
        label(612, 166, 1240, 32, f"$ADDON[{ADDON_ID} 30212]", "font12", TEXT3),
        image(604, 206, 1252, 2, "white.png", RAISED),
        label(620, 300, 1220, 300, "", "font13", TEXT2, align="center", center=False, control_id=403, wrap=True),
        catalog(),
        spaces=0)


def catalog_details_screen():
    """Details of a catalog title. Series show their seasons and episodes, movies a longer description."""
    is_series = "String.IsEqual(Window.Property(series),true)"
    buttons = f"""<control type="grouplist" id="250">
  <left>620</left>
  <top>380</top>
  <width>1100</width>
  <height>76</height>
  <orientation>horizontal</orientation>
  <itemgap>20</itemgap>
  <onleft>noop</onleft>
  <onright>noop</onright>
{join(details_button(203, 0, None, None, 30300, FOCUS, ON_FOCUS, top=0, width=300, ondown="300",
                     condition="String.IsEqual(Window.Property(sources),true)"),
      details_button(201, 0, None, None, 30110, FOCUS, ON_FOCUS, top=0, width=300, ondown="300",
                     condition="String.IsEqual(Window.Property(playable),true)"),
      details_button(202, 0, None, None, None, FOCUS, ON_FOCUS, top=0, width=440, ondown="300"), spaces=2)}
</control>"""
    seasons, episodes = seasons_and_episodes(onup=250, top=480, height=386, condition=is_series)
    return join(
        image(0, 0, 1920, 1080, "white.png", "D9000000"),
        panel(160, 80, 1600, 920, SURFACE),
        panel(210, 130, 360, 540, RAISED),
        image(210, 130, 360, 540, "$INFO[Window.Property(poster)]", keep=True, fallback="film.png"),
        image(522, 146, 34, 34, "star.png", STAR, "String.IsEqual(Window.Property(favorite),true)"),
        textbox(620, 126, 1100, 110, "$INFO[Window.Property(title)]", "font36_title", TEXT),
        label(620, 240, 1100, 40, "$INFO[Window.Property(info)]", "font12", TEXT2),
        label(620, 282, 1100, 40, "$INFO[Window.Property(people)]", "font12", TEXT2),
        label(620, 324, 1100, 40, "$INFO[Window.Property(library)]", "font13", ACCENT),
        buttons,
        "<!-- Description: below the poster for a series, where it follows the highlighted episode, and below the buttons for a movie -->",
        textbox(210, 696, 360, 280, "$INFO[Window.Property(plot)]", "font12", TEXT2, is_series + " + !" + has(400)),
        textbox(210, 696, 360, 280, "$INFO[Container(400).ListItem.Property(plot)]", "font12", TEXT2, is_series + " + " + has(400)),
        textbox(620, 490, 1100, 460, "$INFO[Window.Property(plot)]", "font13", TEXT2, "!" + is_series),
        seasons,
        episodes,
        spaces=0)


def sources_screen():
    """Sources of a movie or an episode, in a panel that slides in from the right over the details."""
    width = 820
    left = 1920 - width
    focus = has(100)
    kind_icon = lambda color, condition=None: [
        image(24, 31, 48, 48, "download.png", color, skin.both(condition, "String.IsEqual(ListItem.Property(kind),torrent)")),
        image(24, 31, 48, 48, "play.png", color, skin.both(condition, "!String.IsEqual(ListItem.Property(kind),torrent)"))]
    item = lambda name, detail, icon, condition=None, scroll=False: [
        *kind_icon(icon, condition),
        label(92, 12, 664, 44, "$INFO[ListItem.Label]", "font13", name, condition, scroll=scroll),
        label(92, 58, 664, 36, "$INFO[ListItem.Label2]", "font12", detail, condition, scroll=scroll)]
    sources = f"""<control type="list" id="100">
  <left>{left + 20}</left>
  <top>196</top>
  <width>{width - 40}</width>
  <height>798</height>
  <onleft>noop</onleft>
  <onright>noop</onright>
  <scrolltime>120</scrolltime>
  <itemlayout height="114">
{join(*item(TEXT, TEXT2, TEXT2), spaces=4)}
  </itemlayout>
  <focusedlayout height="114">
{join(panel(0, 2, width - 40, 108, FOCUS, focus), panel(0, 2, width - 40, 108, RAISED, "!" + focus),
      *item(ON_FOCUS, ON_FOCUS2, ON_FOCUS, focus, True), *item(TEXT, TEXT2, TEXT2, "!" + focus), spaces=4)}
  </focusedlayout>
</control>"""
    slide = f"""<animation effect="slide" start="{width},0" end="0,0" time="260" tween="cubic" easing="out">WindowOpen</animation>
<animation effect="slide" start="0,0" end="{width},0" time="200" tween="cubic" easing="in">WindowClose</animation>"""
    panel_group = f"""<control type="group">
{skin.indent(slide, 2)}
{join(image(left, 0, width, 1080, "white.png", SURFACE),
      textbox(left + 40, 36, width - 80, 100, "$INFO[Window.Property(title)]", "font32_title", TEXT),
      label(left + 40, 136, width - 80, 36, "$INFO[Window.Property(status)]", "font12", TEXT2),
      image(left + 20, 184, width - 40, 2, "white.png", RAISED),
      label(left + 60, 420, width - 120, 200, "", "font13", TEXT2, align="center", center=False, control_id=300, wrap=True),
      sources,
      label(left + 40, 1012, width - 80, 40, f"$ADDON[{ADDON_ID} 30311]", "font12", TEXT3), spaces=2)}
</control>"""
    return join(
        f"""<control type="image">
  <left>0</left>
  <top>0</top>
  <width>1920</width>
  <height>1080</height>
  <texture colordiffuse="99000000">white.png</texture>
  <animation effect="fade" start="0" end="100" time="200">WindowOpen</animation>
  <animation effect="fade" start="100" end="0" time="200">WindowClose</animation>
</control>""",
        panel_group,
        spaces=0)


def player_screen():
    """Playback controls over the video: the time bar, play and pause between back and forward 10 seconds, and
    subtitles and audio, which open their tracks in a panel from the right. gui.py sets Window.Property(mode) to
    bar, for the time bar alone while seeking, or full."""
    shown = "!String.IsEmpty(Window.Property(mode))"
    full = "String.IsEqual(Window.Property(mode),full)"
    tracks_open = "!String.IsEmpty(Window.Property(panel))"
    fade = """<animation effect="fade" start="0" end="100" time="200">Visible</animation>
<animation effect="fade" start="100" end="0" time="300">Hidden</animation>"""

    def group(condition, *controls):
        return f"""<control type="group">
  <visible>{condition}</visible>
{skin.indent(fade, 2)}
{join(*controls, spaces=2)}
</control>"""

    def round_button(control_id, left, top, size, icons, onleft, onright):
        """A round button: a light disc with a dark icon when focused, a faint disc with a white icon otherwise."""
        focus = has(control_id)
        inset = size // 4
        drawn = []
        for texture, condition in icons:
            drawn += [image(left + inset, top + inset, size - 2 * inset, size - 2 * inset, texture, ON_FOCUS, skin.both(focus, condition)),
                      image(left + inset, top + inset, size - 2 * inset, size - 2 * inset, texture, TEXT, skin.both("!" + focus, condition))]
        return join(f"""<control type="button" id="{control_id}">
  <left>{left}</left>
  <top>{top}</top>
  <width>{size}</width>
  <height>{size}</height>
  <onup>noop</onup>
  <ondown>noop</ondown>
  <onleft>{onleft}</onleft>
  <onright>{onright}</onright>
  <texturefocus colordiffuse="{FOCUS}">circle.png</texturefocus>
  <texturenofocus colordiffuse="33FFFFFF">circle.png</texturenofocus>
  <label></label>
</control>""", *drawn, spaces=0)

    def text_button(control_id, left, string_id, icon, onleft, onright):
        focus = has(control_id)
        return join(f"""<control type="button" id="{control_id}">
  <left>{left}</left>
  <top>920</top>
  <width>340</width>
  <height>84</height>
  <onup>noop</onup>
  <ondown>noop</ondown>
  <onleft>{onleft}</onleft>
  <onright>{onright}</onright>
  <font>font13</font>
  <align>left</align>
  <aligny>center</aligny>
  <textoffsetx>84</textoffsetx>
  <textcolor>{TEXT}</textcolor>
  <focusedcolor>{ON_FOCUS}</focusedcolor>
  <texturefocus border="16" colordiffuse="{FOCUS}">panel.png</texturefocus>
  <texturenofocus border="16" colordiffuse="33FFFFFF">panel.png</texturenofocus>
  <label>$ADDON[{ADDON_ID} {string_id}]</label>
</control>""", image(left + 28, 942, 40, 40, icon, ON_FOCUS, focus), image(left + 28, 942, 40, 40, icon, TEXT, "!" + focus), spaces=0)

    paused = "Player.Paused"
    bar = [
        f"""<control type="image">
  <left>0</left>
  <top>600</top>
  <width>1920</width>
  <height>480</height>
  <texture colordiffuse="F2000000">shade.png</texture>
</control>""",
        f"""<control type="progress" id="300">
  <left>120</left>
  <top>864</top>
  <width>1680</width>
  <height>8</height>
  <texturebg colordiffuse="4DFFFFFF">white.png</texturebg>
  <midtexture colordiffuse="{ACCENT}">white.png</midtexture>
</control>""",
        label(120, 816, 600, 40, "$INFO[Window.Property(elapsed)]", "font12", TEXT),
        label(1200, 816, 600, 40, "$INFO[Window.Property(duration)]", "font12", TEXT2, align="right")]
    controls = [
        f"""<control type="image">
  <left>0</left>
  <top>0</top>
  <width>1920</width>
  <height>300</height>
  <texture flipy="true" colordiffuse="CC000000">shade.png</texture>
</control>""",
        "<!-- Below the time bar that the Kodi skin shows at the top while paused -->",
        label(120, 100, 1680, 64, "$INFO[Window.Property(title)]", "font32_title", TEXT),
        label(120, 166, 1680, 40, "$INFO[Window.Property(detail)]", "font13", TEXT2),
        text_button(201, 120, 30320, "subtitles.png", "noop", 202),
        round_button(202, 744, 914, 96, [("back10.png", None)], 201, 203),
        round_button(203, 900, 902, 120, [("pause.png", "!" + paused), ("player_play.png", paused)], 202, 204),
        round_button(204, 1080, 914, 96, [("forward10.png", None)], 203, 205),
        text_button(205, 1460, 30321, "audio.png", 204, "noop")]
    width = 820
    left = 1920 - width
    focus = has(400)
    track = lambda name, detail, condition=None: [
        image(24, 30, 40, 40, "check.png", name, skin.both(condition, "String.IsEqual(ListItem.Property(current),true)")),
        label(84, 12, width - 140, 44, "$INFO[ListItem.Label]", "font13", name, condition),
        label(84, 56, width - 140, 34, "$INFO[ListItem.Label2]", "font12", detail, condition)]
    tracks = f"""<control type="list" id="400">
  <left>{left + 20}</left>
  <top>196</top>
  <width>{width - 40}</width>
  <height>798</height>
  <onleft>noop</onleft>
  <onright>noop</onright>
  <scrolltime>120</scrolltime>
  <itemlayout height="104">
{join(*track(TEXT, TEXT2), spaces=4)}
  </itemlayout>
  <focusedlayout height="104">
{join(panel(0, 2, width - 40, 98, FOCUS, focus), panel(0, 2, width - 40, 98, RAISED, "!" + focus),
      *track(ON_FOCUS, ON_FOCUS2, focus), *track(TEXT, TEXT2, "!" + focus), spaces=4)}
  </focusedlayout>
</control>"""
    tracks_panel = f"""<control type="group">
  <visible>{tracks_open}</visible>
  <animation effect="slide" start="{width},0" end="0,0" time="260" tween="cubic" easing="out">Visible</animation>
  <animation effect="slide" start="0,0" end="{width},0" time="200" tween="cubic" easing="in">Hidden</animation>
{join(image(left, 0, width, 1080, "white.png", SURFACE),
      label(left + 40, 56, width - 80, 64, "$INFO[Window.Property(panel_title)]", "font32_title", TEXT),
      image(left + 20, 184, width - 40, 2, "white.png", RAISED),
      tracks,
      label(left + 40, 1012, width - 80, 40, f"$ADDON[{ADDON_ID} 30327]", "font12", TEXT3), spaces=2)}
</control>"""
    return join(
        group(shown, *bar),
        group(full, *controls),
        tracks_panel,
        spaces=0)


def progress_bar(top, background, condition=None):
    """Progress of a download, from ListItem.Property(progress), drawn over a background track."""
    return f"""<control type="progress">
  <left>24</left>
  <top>{top}</top>
  <width>1312</width>
  <height>8</height>
  <texturebg colordiffuse="{background}">white.png</texturebg>
  <midtexture colordiffuse="{ACCENT}">white.png</midtexture>
  <info>ListItem.Property(progress)</info>{skin.visible(condition)}
</control>"""


def downloads_screen():
    focus = has(100)
    item = lambda name, detail, track, condition=None, scroll=False: [
        label(24, 8, 1100, 44, "$INFO[ListItem.Label]", "font13", name, condition, scroll=scroll),
        label(1136, 8, 200, 44, "$INFO[ListItem.Property(percent)]", "font13", name, condition, align="right"),
        progress_bar(58, track, condition),
        label(24, 70, 1312, 34, "$INFO[ListItem.Label2]", "font12", detail, condition)]
    downloads = f"""<control type="list" id="100">
  <left>290</left>
  <top>350</top>
  <width>1360</width>
  <height>600</height>
  <onup>201</onup>
  <onleft>noop</onleft>
  <onright>noop</onright>
  <scrolltime>120</scrolltime>
  <itemlayout height="120">
{join(panel(0, 2, 1360, 112, RAISED), *item(TEXT, TEXT2, SURFACE), spaces=4)}
  </itemlayout>
  <focusedlayout height="120">
{join(panel(0, 2, 1360, 112, FOCUS, focus), panel(0, 2, 1360, 112, RAISED, "!" + focus),
      *item(ON_FOCUS, ON_FOCUS2, TEXT2, focus, True), *item(TEXT, TEXT2, SURFACE, "!" + focus), spaces=4)}
  </focusedlayout>
</control>"""
    button = lambda control_id, left, width, onleft, onright, string_id: details_button(
        control_id, left, onleft, onright, string_id, FOCUS, ON_FOCUS, top=250, width=width, ondown="100")
    return join(
        image(0, 0, 1920, 1080, "white.png", "D9000000"),
        panel(250, 80, 1420, 920, SURFACE),
        image(290, 116, 56, 56, "download.png", ACCENT),
        label(368, 114, 900, 60, f"$ADDON[{ADDON_ID} 30160]", "font32_title", TEXT),
        label(1100, 114, 550, 60, "$INFO[Window.Property(summary)]", "font12", TEXT2, align="right"),
        label(290, 190, 1360, 40, "$INFO[Window.Property(folder)]", "font12", TEXT2),
        button(201, 290, 400, 204, 202, 30161),
        button(202, 706, 360, 201, 203, 30162),
        button(203, 1082, 300, 202, 204, 30163),
        button(204, 1398, 252, 203, 201, 30063),
        label(330, 440, 1280, 200, "", "font13", TEXT2, align="center", center=False, control_id=300, wrap=True),
        downloads,
        spaces=0)


def main():
    skin.ADDON_ID, skin.GENERATOR = ADDON_ID, "generate_m3u_movies_skin.py"
    files = {
        "script-m3u-movies-main.xml": window("Main screen: toolbar and groups on the left, movie posters on the right.", 200, main_screen()),
        "script-m3u-movies-details.xml": window("Modal movie details opened from a poster.", 201, details_screen(), always=True),
        "script-m3u-movies-series.xml": window("Modal series details with seasons and episodes, opened from a series poster.", 201,
                                               series_screen(), always=True),
        "script-m3u-movies-catalog.xml": window("Cinemeta catalog opened from the catalog icon: tabs and categories on the left, posters on the right.",
                                                200, catalog_screen()),
        "script-m3u-movies-catalog-details.xml": window("Modal details of a catalog title, with seasons and episodes for a series.", 202,
                                                        catalog_details_screen(), always=True),
        "script-m3u-movies-sources.xml": window("Modal sources of a catalog title, sliding in from the right.", 100, sources_screen(), always=True),
        "script-m3u-movies-player.xml": window("Modal playback controls over the video of a movie or an episode.", 203, player_screen()),
        "script-m3u-movies-downloads.xml": window("Modal torrent downloads opened from the download icon.", 201, downloads_screen(), always=True),
        "script-m3u-movies-manager.xml": skin.manager("Modal list manager opened from the gear icon.", "gear.png", 30060, "film.png",
            [skin.button(201, 290, 256, 203, 204, 30000), skin.button(204, 561, 256, 201, 205, 30093),
             skin.button(205, 832, 256, 204, 202, 30001), skin.button(202, 1103, 256, 205, 203, 30062),
             skin.button(203, 1374, 256, 202, 201, 30063)], width=1400),
        "script-m3u-movies-addons.xml": skin.manager("Modal Stremio addons opened from the catalog.", "puzzle.png", 30270, "puzzle.png",
            [skin.button(201, 440, 512, 203, 203, 30272), skin.button(203, 968, 512, 201, 201, 30063)], logos=True),
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
