"""Generate the Easy Connect window layout with the palette and parts shared with Easy Channel and Easy Movie."""

import os

import generate_m3u_channels_skin as skin
from generate_m3u_channels_skin import (ACCENT, BG, FOCUS, ON_FOCUS, ON_FOCUS2, RAISED, SURFACE, TEXT, TEXT2, has,
                                        image, join, label, panel, window)


ADDON_ID = "script.easy.connect"
GOOD = "FF3DD68C"
section = lambda name: f"String.IsEqual(Window.Property(section),{name})"
POWER_BUTTON, PASSWORD_BUTTON, DISCONNECT_BUTTON, SCAN_BUTTON = 210, 501, 502, 503
DETAILS, NETWORKS, KNOWN = 300, 400, 450


def groups():
    """The sections on the left. Without a toolbar above, they start at the top of the panel; Down after the last one
    reaches the Wi-Fi switch."""
    return (skin.groups.replace("<top>266</top>", "<top>130</top>").replace("<height>748</height>", "<height>204</height>")
            .replace("<onup>100</onup>", f"<onup>noop</onup>\n  <ondown>{POWER_BUTTON}</ondown>"))


def button(control_id, left, width, top, nav, condition=None):
    up, down, left_to, right_to = nav
    return f"""<control type="button" id="{control_id}">
  <left>{left}</left>
  <top>{top}</top>
  <width>{width}</width>
  <height>64</height>
  <onup>{up}</onup>
  <ondown>{down}</ondown>
  <onleft>{left_to}</onleft>
  <onright>{right_to}</onright>
  <font>font13</font>
  <align>center</align>
  <aligny>center</aligny>
  <textcolor>{TEXT}</textcolor>
  <focusedcolor>{ON_FOCUS}</focusedcolor>
  <texturefocus border="16" colordiffuse="{FOCUS}">panel.png</texturefocus>
  <texturenofocus border="16" colordiffuse="{RAISED}">panel.png</texturenofocus>{skin.visible(condition)}
</control>"""


def power_card():
    """The state of the Wi-Fi and its switch, at the bottom of the left panel."""
    return [image(60, 358, 480, 2, "white.png", RAISED),
            label(64, 378, 470, 36, f"$ADDON[{ADDON_ID} 30005]", "font12", ACCENT),
            image(64, 428, 56, 56, "$INFO[Window.Property(link_icon)]", TEXT2),
            label(140, 416, 400, 40, "$INFO[Window.Property(link_title)]", "font13", TEXT),
            label(140, 456, 400, 34, "$INFO[Window.Property(link_detail)]", "font12", TEXT2),
            button(POWER_BUTTON, 60, 480, 956, (200, "noop", "noop", "noop"))]


def current_section():
    """The network the device is connected to: a row for each detail, the password hidden until asked."""
    shown = section("current")
    connected = "String.IsEqual(Window.Property(connected),true)"
    row = join(label(24, 0, 400, 72, "$INFO[ListItem.Label]", "font13", TEXT2),
               label(440, 0, 776, 72, "$INFO[ListItem.Label2]", "font13", TEXT, align="right"),
               image(16, 71, 1208, 1, "white.png", RAISED), spaces=4)
    details = f"""<control type="list" id="{DETAILS}">
  <left>612</left>
  <top>226</top>
  <width>1240</width>
  <height>720</height>
  <scrolltime>0</scrolltime>
  <itemlayout height="72">
{row}
  </itemlayout>
  <focusedlayout height="72">
{row}
  </focusedlayout>{skin.visible(shown + " + " + connected)}
</control>"""
    return [details,
            label(612, 380, 1240, 200, "$INFO[Window.Property(empty)]", "font13", TEXT2, f"{shown} + !{connected}",
                  align="center", wrap=True),
            button(PASSWORD_BUTTON, 836, 380, 956, ("noop", "noop", 200, DISCONNECT_BUTTON), f"{shown} + {connected}"),
            button(DISCONNECT_BUTTON, 1244, 380, 956, ("noop", "noop", PASSWORD_BUTTON, "noop"), f"{shown} + {connected}")]


def network_list(control_id, condition, bottom_button=None):
    """Networks with their signal, a lock on the ones with a password, and their state under the name."""
    focus = has(control_id)
    locked = "String.IsEqual(ListItem.Property(locked),true)"
    item = lambda name, detail, icon_color, condition=None, scroll=False: [
        image(26, 22, 52, 52, "$INFO[ListItem.Icon]", icon_color, condition),
        label(100, 8, 860, 44, "$INFO[ListItem.Label]", "font13", name, condition, scroll=scroll),
        label(100, 50, 860, 36, "$INFO[ListItem.Label2]", "font12", detail, condition),
        image(1172, 32, 32, 32, "lock.png", detail, skin.both(condition, locked)),
        label(900, 0, 252, 96, "$INFO[ListItem.Property(value)]", "font12", detail, condition, align="right")]
    down = f"\n  <ondown>{bottom_button}</ondown>" if bottom_button else ""
    return f"""<control type="list" id="{control_id}">
  <left>612</left>
  <top>226</top>
  <width>1240</width>
  <height>{700 if bottom_button else 800}</height>
  <onup>noop</onup>{down}
  <onleft>200</onleft>
  <onright>noop</onright>
  <scrolltime>120</scrolltime>
  <itemlayout height="100">
{join(*item(TEXT, TEXT2, TEXT2), spaces=4)}
  </itemlayout>
  <focusedlayout height="100">
{join(panel(0, 2, 1240, 96, FOCUS, focus), panel(0, 2, 1240, 96, RAISED, "!" + focus),
      *item(ON_FOCUS, ON_FOCUS2, ON_FOCUS, focus, True), *item(TEXT, TEXT2, TEXT2, "!" + focus), spaces=4)}
  </focusedlayout>{skin.visible(condition)}
</control>"""


def main_screen():
    available = section("available")
    known = section("known")
    return join(
        image(0, 0, 1920, 1080, "white.png", BG),
        image(56, 30, 56, 56, "logo.png"),
        label(128, 28, 900, 60, f"$ADDON[{ADDON_ID} 30000]", "font32_title", TEXT),
        label(1360, 28, 500, 60, "$INFO[System.Time]", "font32_title", TEXT2, align="right"),
        "<!-- Sections and the Wi-Fi switch -->",
        panel(40, 110, 520, 930, SURFACE),
        groups(),
        *power_card(),
        "<!-- The selected section, with its title and a line under it -->",
        panel(580, 110, 1300, 930, SURFACE),
        label(612, 114, 1240, 56, "$INFO[Window.Property(title)]", "font32_title", TEXT),
        label(612, 166, 1240, 32, "$INFO[Window.Property(subtitle)]", "font12", TEXT2),
        image(604, 206, 1252, 2, "white.png", RAISED),
        "<!-- Current network -->",
        *current_section(),
        "<!-- Networks in range, with a button to look for them again -->",
        network_list(NETWORKS, available, SCAN_BUTTON),
        button(SCAN_BUTTON, 1030, 400, 956, (NETWORKS, "noop", 200, "noop"), available),
        "<!-- Known networks -->",
        network_list(KNOWN, known),
        label(612, 380, 1240, 200, "$INFO[Window.Property(empty)]", "font13", TEXT2,
              f"[{available} | {known}] + !String.IsEmpty(Window.Property(empty))", align="center", wrap=True),
        spaces=0)


def main():
    skin.ADDON_ID, skin.GENERATOR = ADDON_ID, "generate_easy_connect_skin.py"
    folder = skin.skin_folder(ADDON_ID)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "script-easy-connect-main.xml"), "w") as output:
        output.write(window("Main screen: the sections and the Wi-Fi switch on the left, the current, available or known "
                            "networks on the right.", 200, main_screen()))


if __name__ == "__main__":
    main()
