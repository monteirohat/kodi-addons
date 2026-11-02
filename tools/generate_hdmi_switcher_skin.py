"""Generate the HDMI Switcher window layout with the palette shared with Easy Channel and Easy Movie."""

import os

import generate_m3u_channels_skin as skin
from generate_m3u_channels_skin import (ACCENT, DANGER, FOCUS, ON_FOCUS, ON_FOCUS2, RAISED, RAISED2, SURFACE, TEXT,
                                        TEXT2, TEXT3, has, image, join, label, panel, window)


ADDON_ID = "script.hdmi.switcher"
cards_focus = has(100)
state = lambda name: "String.IsEqual(ListItem.Property(state),%s)" % name


def card(name_color, detail_color, icon_color, condition=None):
    """Texts and icon of a display card. Each state of the card draws them with its own colors."""
    both = lambda extra: " + ".join(part for part in (condition, extra) if part) or None
    return [
        image(190, 44, 160, 160, "display.png", icon_color, condition),
        label(30, 226, 480, 56, "$INFO[ListItem.Label]", "font30_title", name_color, condition, align="center"),
        label(30, 282, 480, 40, "$INFO[ListItem.Label2]", "font12", detail_color, condition, align="center"),
        # Status line: blue for the active display, red when no display is connected.
        label(30, 332, 480, 40, "$INFO[ListItem.Property(status)]", "font12", ACCENT, both(state("active")), align="center"),
        label(30, 332, 480, 40, "$INFO[ListItem.Property(status)]", "font12", DANGER, both(state("missing")), align="center"),
        label(30, 332, 480, 40, "$INFO[ListItem.Property(status)]", "font12", detail_color, both(state("connected")), align="center"),
    ]


def active_mark():
    """Blue ring and check mark of the active display, shown with or without focus."""
    return [panel(3, -7, 554, 414, ACCENT, state("active")),
            image(470, 26, 48, 48, "check.png", ACCENT, state("active"))]


def cards():
    return f"""<control type="list" id="100">
  <left>400</left>
  <top>356</top>
  <width>1120</width>
  <height>416</height>
  <orientation>horizontal</orientation>
  <onup>noop</onup>
  <ondown>noop</ondown>
  <scrolltime>150</scrolltime>
  <itemlayout width="560" height="410">
{join(active_mark()[0], panel(10, 0, 540, 400, RAISED), active_mark()[1], *card(TEXT, TEXT2, TEXT2), spaces=4)}
  </itemlayout>
  <focusedlayout width="560" height="410">
{join(active_mark()[0], panel(10, 0, 540, 400, FOCUS, cards_focus), panel(10, 0, 540, 400, RAISED2, "!" + cards_focus),
      active_mark()[1], *card(ON_FOCUS, ON_FOCUS2, ON_FOCUS, cards_focus), *card(TEXT, TEXT2, TEXT2, "!" + cards_focus), spaces=4)}
  </focusedlayout>
</control>"""


def main_screen():
    return join(
        image(0, 0, 1920, 1080, "white.png", "D9000000"),
        panel(360, 170, 1200, 740, SURFACE),
        image(400, 206, 64, 64, "logo.png"),
        label(484, 204, 1000, 68, f"$ADDON[{ADDON_ID} 30000]", "font32_title", TEXT),
        label(400, 284, 1120, 40, f"$ADDON[{ADDON_ID} 30001]", "font13", TEXT2),
        cards(),
        label(400, 820, 1120, 40, f"$ADDON[{ADDON_ID} 30002]", "font12", TEXT3, align="center"),
        spaces=0)


def main():
    skin.ADDON_ID, skin.GENERATOR = ADDON_ID, "generate_hdmi_switcher_skin.py"
    folder = skin.skin_folder(ADDON_ID)
    os.makedirs(folder, exist_ok=True)
    content = window("Display picker: one card for each HDMI display.", 100, main_screen(), always=True)
    with open(os.path.join(folder, "script-hdmi-switcher-main.xml"), "w") as output:
        output.write(content)


if __name__ == "__main__":
    main()
