"""Generate the Easy Bluetooth window layouts with the palette and parts shared with Easy Channel and Easy Connect."""

import os

import generate_m3u_channels_skin as skin
from generate_m3u_channels_skin import (ACCENT, BG, DANGER, FOCUS, ON_FOCUS, ON_FOCUS2, RAISED, SURFACE, TEXT, TEXT2, has,
                                        image, join, label, panel, window)


ADDON_ID = "script.easy.bluetooth"
section = lambda name: f"String.IsEqual(Window.Property(section),{name})"
POWER_BUTTON, SCAN_BUTTON = 210, 503
DEVICES, FOUND = 400, 450
# The modal of a paired device: its buttons, in a column.
OPTIONS, CONNECT_OPTION, TRUST_OPTION, FORGET_OPTION = 600, 601, 602, 603


def groups():
    """The sections on the left. Without a toolbar above, they start at the top of the panel; Down after the last one
    reaches the Bluetooth switch."""
    return (skin.groups.replace("<top>266</top>", "<top>130</top>").replace("<height>748</height>", "<height>136</height>")
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


def adapter_card():
    """The Bluetooth of this device and its switch, under the sections."""
    return [image(60, 290, 480, 2, "white.png", RAISED),
            label(64, 310, 470, 36, f"$ADDON[{ADDON_ID} 30005]", "font12", ACCENT),
            image(64, 360, 56, 56, "$INFO[Window.Property(adapter_icon)]", TEXT2),
            label(140, 348, 400, 40, "$INFO[Window.Property(adapter_name)]", "font13", TEXT),
            label(140, 388, 400, 34, "$INFO[Window.Property(adapter_state)]", "font12", TEXT2),
            textbox_hint(),
            button(POWER_BUTTON, 60, 480, 956, (200, "noop", "noop", "noop"))]


def textbox_hint():
    """How to pair, while the search shows."""
    return f"""<control type="textbox">
  <left>64</left>
  <top>470</top>
  <width>470</width>
  <height>300</height>
  <font>font12</font>
  <textcolor>{TEXT2}</textcolor>
  <label>$ADDON[{ADDON_ID} 30020]</label>{skin.visible(section("search"))}
</control>"""


def device_list(control_id, condition, bottom_button=None):
    """Devices with the icon of their kind, their state under the name, and their signal or battery on the right."""
    focus = has(control_id)
    item = lambda name, detail, icon_color, condition=None, scroll=False: [
        image(26, 22, 52, 52, "$INFO[ListItem.Icon]", icon_color, condition),
        label(100, 8, 860, 44, "$INFO[ListItem.Label]", "font13", name, condition, scroll=scroll),
        label(100, 50, 860, 36, "$INFO[ListItem.Label2]", "font12", detail, condition),
        image(1172, 32, 32, 32, "$INFO[ListItem.Property(signal)]", detail, condition),
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
    devices = section("devices")
    search = section("search")
    return join(
        image(0, 0, 1920, 1080, "white.png", BG),
        image(56, 30, 56, 56, "logo.png"),
        label(128, 28, 900, 60, f"$ADDON[{ADDON_ID} 30000]", "font32_title", TEXT),
        label(1360, 28, 500, 60, "$INFO[System.Time]", "font32_title", TEXT2, align="right"),
        "<!-- Sections, the Bluetooth of this device and its switch -->",
        panel(40, 110, 520, 930, SURFACE),
        groups(),
        *adapter_card(),
        "<!-- The selected section, with its title and a line under it -->",
        panel(580, 110, 1300, 930, SURFACE),
        label(612, 114, 1240, 56, "$INFO[Window.Property(title)]", "font32_title", TEXT),
        label(612, 166, 1240, 32, "$INFO[Window.Property(subtitle)]", "font12", TEXT2),
        image(604, 206, 1252, 2, "white.png", RAISED),
        "<!-- Paired devices -->",
        device_list(DEVICES, devices),
        "<!-- Devices found nearby, with a button to look for them again -->",
        device_list(FOUND, search, SCAN_BUTTON),
        button(SCAN_BUTTON, 1030, 400, 956, (FOUND, "noop", 200, "noop"), search),
        label(612, 380, 1240, 200, "$INFO[Window.Property(empty)]", "font13", TEXT2, "!String.IsEmpty(Window.Property(empty))",
              align="center", wrap=True),
        spaces=0)


def device_screen():
    """A paired device: its icon, name and state, its kind, address and battery, and a button for each option."""
    left, top, width, height = 560, 210, 800, 652
    inner = width - 80

    def option(control_id, string_id, color=TEXT):
        return f"""<control type="button" id="{control_id}">
  <width>{inner}</width>
  <height>80</height>
  <font>font13</font>
  <aligny>center</aligny>
  <textoffsetx>32</textoffsetx>
  <textcolor>{color}</textcolor>
  <focusedcolor>{ON_FOCUS}</focusedcolor>
  <texturefocus border="16" colordiffuse="{FOCUS}">panel.png</texturefocus>
  <texturenofocus border="16" colordiffuse="{RAISED}">panel.png</texturenofocus>
  <label>$ADDON[{ADDON_ID} {string_id}]</label>
</control>"""

    row = lambda y, title_id, value: [
        label(left + 40, y, 300, 56, f"$ADDON[{ADDON_ID} {title_id}]", "font13", TEXT2),
        label(left + 340, y, inner - 300, 56, f"$INFO[Window.Property({value})]", "font13", TEXT, align="right")]
    options = f"""<control type="grouplist" id="{OPTIONS}">
  <left>{left + 40}</left>
  <top>{top + 330}</top>
  <width>{inner}</width>
  <height>{3 * 88}</height>
  <itemgap>8</itemgap>
  <orientation>vertical</orientation>
  <onleft>noop</onleft>
  <onright>noop</onright>
{join(option(CONNECT_OPTION, 30060), option(TRUST_OPTION, 30061), option(FORGET_OPTION, 30062, DANGER), spaces=2)}
</control>"""
    controls = join(
        image(0, 0, 1920, 1080, "white.png", "D9000000"),
        panel(left, top, width, height, SURFACE),
        image(left + 40, top + 44, 64, 64, "$INFO[Window.Property(icon)]", TEXT),
        label(left + 128, top + 30, inner - 88, 60, "$INFO[Window.Property(name)]", "font32_title", TEXT),
        label(left + 128, top + 86, inner - 88, 36, "$INFO[Window.Property(state)]", "font12", TEXT2),
        image(left + 30, top + 150, width - 60, 2, "white.png", RAISED),
        *row(top + 168, 30050, "kind"),
        *row(top + 228, 30051, "address"),
        image(left + 30, top + 304, width - 60, 2, "white.png", RAISED),
        options, spaces=0)
    return window("Modal options of a paired device, opened from Devices.", OPTIONS, controls, always=True)


def main():
    skin.ADDON_ID, skin.GENERATOR = ADDON_ID, "generate_easy_bluetooth_skin.py"
    folder = skin.skin_folder(ADDON_ID)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "script-easy-bluetooth-main.xml"), "w") as output:
        output.write(window("Main screen: the sections and the Bluetooth switch on the left, the paired or found devices on "
                            "the right.", 200, main_screen()))
    with open(os.path.join(folder, "script-easy-bluetooth-device.xml"), "w") as output:
        output.write(device_screen())


if __name__ == "__main__":
    main()
