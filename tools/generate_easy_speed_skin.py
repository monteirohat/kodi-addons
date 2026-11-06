"""Generate the Easy Speed window layout with the palette and parts shared with Easy Channel and Easy Movie."""

import os

import generate_m3u_channels_skin as skin
from generate_m3u_channels_skin import (ACCENT, BG, DANGER, FOCUS, ON_FOCUS, ON_FOCUS2, RAISED, STAR, SURFACE, TEXT, TEXT2,
                                        TEXT3, has, image, join, label, panel, textbox, window)


ADDON_ID = "script.easy.speed"
GOOD = "FF3DD68C"
section = lambda name: f"String.IsEqual(Window.Property(section),{name})"
# The Monteiro skin has a font for the large speed; other skins show it smaller. Set by gui.py.
big_font = "String.IsEqual(Window.Property(big_font),true)"
# The speedometer, in the middle of the results panel.
GAUGE_LEFT, GAUGE_TOP, GAUGE = 960, 214, 540
SPEED_BUTTON, CHECK_BUTTON, CHECKS, HISTORY = 501, 502, 300, 400


def groups():
    """The sections on the left. Without a toolbar above, they start at the top of the panel."""
    return (skin.groups.replace("<top>266</top>", "<top>130</top>").replace("<height>748</height>", "<height>204</height>")
            .replace("<onup>100</onup>", "<onup>noop</onup>"))


def connection_card():
    """The connection and the last test, under the sections."""
    has_last = "!String.IsEmpty(Window.Property(last_download))"
    return [image(60, 358, 480, 2, "white.png", RAISED),
            label(64, 378, 470, 36, f"$ADDON[{ADDON_ID} 30002]", "font12", ACCENT),
            image(64, 428, 56, 56, "$INFO[Window.Property(link_icon)]", TEXT2),
            label(140, 416, 400, 40, "$INFO[Window.Property(link_title)]", "font13", TEXT),
            label(140, 456, 400, 34, "$INFO[Window.Property(link_detail)]", "font12", TEXT2),
            label(64, 526, 470, 36, f"$ADDON[{ADDON_ID} 30090]", "font12", ACCENT, has_last),
            image(64, 576, 28, 28, "download.png", TEXT2, has_last),
            label(104, 568, 430, 44, "$INFO[Window.Property(last_download)]", "font13", TEXT),
            image(64, 620, 28, 28, "upload.png", TEXT2, has_last),
            label(104, 612, 430, 44, "$INFO[Window.Property(last_upload)]", "font13", TEXT),
            label(64, 660, 470, 34, "$INFO[Window.Property(last_detail)]", "font12", TEXT2)]


def button(control_id, condition):
    return f"""<control type="button" id="{control_id}">
  <left>1030</left>
  <top>956</top>
  <width>400</width>
  <height>64</height>
  <onup>noop</onup>
  <ondown>noop</ondown>
  <onleft>200</onleft>
  <onright>noop</onright>
  <font>font13</font>
  <align>center</align>
  <aligny>center</aligny>
  <textcolor>{TEXT}</textcolor>
  <focusedcolor>{ON_FOCUS}</focusedcolor>
  <texturefocus border="16" colordiffuse="{FOCUS}">panel.png</texturefocus>
  <texturenofocus border="16" colordiffuse="{RAISED}">panel.png</texturenofocus>{skin.visible(condition)}
</control>"""


def card(index, icon, title_id, value):
    left = 612 + index * 315
    return [panel(left, 770, 295, 110, RAISED),
            image(left + 20, 788, 32, 32, icon, ACCENT),
            label(left + 64, 782, 220, 44, f"$ADDON[{ADDON_ID} {title_id}]", "font12", TEXT2),
            label(left + 20, 826, 260, 50, f"$INFO[Window.Property({value})]", "font32_title", TEXT)]


def speed_section():
    box = lambda texture, color, condition=None: image(GAUGE_LEFT, GAUGE_TOP, GAUGE, GAUGE, texture, color, condition)
    number = "$INFO[Window.Property(speed)]"
    return [box("gauge-track.png", RAISED),
            box("$INFO[Window.Property(fill)]", FOCUS, "!String.IsEmpty(Window.Property(fill))"),
            box("gauge-scale.png", TEXT3),
            label(GAUGE_LEFT, 404, GAUGE, 150, number, "font100_title", TEXT, big_font, align="center"),
            label(GAUGE_LEFT, 424, GAUGE, 110, number, "font52_title", TEXT, "!" + big_font, align="center"),
            label(GAUGE_LEFT, 550, GAUGE, 40, "$INFO[Window.Property(unit)]", "font13", TEXT2, align="center"),
            label(GAUGE_LEFT, 680, GAUGE, 44, "$INFO[Window.Property(phase)]", "font13", TEXT2, align="center"),
            *card(0, "download.png", 30030, "download"),
            *card(1, "upload.png", 30031, "upload"),
            *card(2, "latency.png", 30032, "latency"),
            *card(3, "loaded.png", 30033, "loaded"),
            label(612, 892, 1240, 48, "$INFO[Window.Property(quality)]", "font13", TEXT2, align="center"),
            button(SPEED_BUTTON, None)]


def checks():
    """The checks of the connection, one row each. The list only shows them; the focus stays on the button."""
    state = lambda name: f"String.IsEqual(ListItem.Property(state),{name})"
    row = join(panel(0, 4, 1240, 112, RAISED),
               image(28, 36, 48, 48, "check.png", GOOD, state("ok")),
               image(28, 36, 48, 48, "warning.png", STAR, state("warning")),
               image(28, 36, 48, 48, "failed.png", DANGER, state("failed")),
               image(28, 36, 48, 48, "white.png", "00000000", state("waiting")),
               label(104, 14, 800, 44, "$INFO[ListItem.Label]", "font13", TEXT),
               label(104, 58, 900, 40, "$INFO[ListItem.Label2]", "font12", TEXT2),
               label(900, 4, 310, 112, "$INFO[ListItem.Property(value)]", "font13", TEXT, align="right"), spaces=4)
    return f"""<control type="list" id="{CHECKS}">
  <left>612</left>
  <top>226</top>
  <width>1240</width>
  <height>480</height>
  <scrolltime>0</scrolltime>
  <itemlayout height="120">
{row}
  </itemlayout>
  <focusedlayout height="120">
{row}
  </focusedlayout>{skin.visible(section("connection"))}
</control>"""


def history():
    focus = has(HISTORY)
    # The download, the upload and the latency, each in a column with its icon.
    column = lambda left, icon, value, color, condition: [
        image(left, 36, 28, 28, icon, color, condition),
        label(left + 40, 0, 160, 100, f"$INFO[ListItem.Property({value})]", "font13", color, condition)]
    item = lambda name, detail, condition=None: [
        label(28, 10, 580, 44, "$INFO[ListItem.Label]", "font13", name, condition),
        label(28, 54, 580, 36, "$INFO[ListItem.Label2]", "font12", detail, condition),
        *column(640, "download.png", "download", name, condition),
        *column(850, "upload.png", "upload", name, condition),
        *column(1060, "latency.png", "latency", name, condition)]
    return f"""<control type="list" id="{HISTORY}">
  <left>612</left>
  <top>226</top>
  <width>1240</width>
  <height>800</height>
  <onup>noop</onup>
  <ondown>noop</ondown>
  <onleft>200</onleft>
  <onright>noop</onright>
  <scrolltime>120</scrolltime>
  <itemlayout height="100">
{join(*item(TEXT, TEXT2), spaces=4)}
  </itemlayout>
  <focusedlayout height="100">
{join(panel(0, 2, 1240, 96, FOCUS, focus), panel(0, 2, 1240, 96, RAISED, "!" + focus),
      *item(ON_FOCUS, ON_FOCUS2, focus), *item(TEXT, TEXT2, "!" + focus), spaces=4)}
  </focusedlayout>{skin.visible(section("history"))}
</control>"""


def main_screen():
    # The speed test also shows before gui.py sets the section, so its button can take the focus when the window opens.
    speed = f"!{section('connection')} + !{section('history')}"
    connection = section("connection")
    return join(
        image(0, 0, 1920, 1080, "white.png", BG),
        image(56, 30, 56, 56, "logo.png"),
        label(128, 28, 900, 60, f"$ADDON[{ADDON_ID} 30000]", "font32_title", TEXT),
        label(1360, 28, 500, 60, "$INFO[System.Time]", "font32_title", TEXT2, align="right"),
        "<!-- Sections, the connection and the last test -->",
        panel(40, 110, 520, 930, SURFACE),
        groups(),
        *connection_card(),
        "<!-- The selected section, with its title and a line under it -->",
        panel(580, 110, 1300, 930, SURFACE),
        label(612, 114, 1240, 56, "$INFO[Window.Property(title)]", "font32_title", TEXT),
        label(612, 166, 1240, 32, "$INFO[Window.Property(subtitle)]", "font12", TEXT2),
        image(604, 206, 1252, 2, "white.png", RAISED),
        "<!-- Speed test -->",
        f'<control type="group">{skin.visible(speed)}\n{join(*speed_section(), spaces=2)}\n</control>',
        "<!-- Connection: the checks and what to do -->",
        checks(),
        textbox(612, 730, 1240, 210, "$INFO[Window.Property(diagnosis)]", "font13", TEXT, connection),
        button(CHECK_BUTTON, connection),
        "<!-- History -->",
        history(),
        label(612, 400, 1240, 100, f"$ADDON[{ADDON_ID} 30080]", "font13", TEXT2,
              section("history") + f" + Integer.IsEqual(Container({HISTORY}).NumItems,0)", align="center"),
        spaces=0)


def main():
    skin.ADDON_ID, skin.GENERATOR = ADDON_ID, "generate_easy_speed_skin.py"
    folder = skin.skin_folder(ADDON_ID)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "script-easy-speed-main.xml"), "w") as output:
        output.write(window("Main screen: the sections on the left, the speed test, the connection or the history on the right.",
                            SPEED_BUTTON, main_screen()))


if __name__ == "__main__":
    main()
