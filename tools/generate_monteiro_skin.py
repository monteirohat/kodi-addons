"""Generate the Monteiro skin: the windows of Kodi in the design of Easy Channel and Easy Movie.

Written from scratch and released under the MIT license. The window file names and the control ids are the ones Kodi
requires for each window. No file or part of another skin is copied.

Requires Pillow, for the textures. Run with the folder of the Noto Sans font files and their license:

    python3 tools/generate_monteiro_skin.py path/to/noto
"""

import math
import os
import shutil
import sys

from PIL import Image, ImageDraw

from generate_m3u_channels_skin import ACCENT, BG, DANGER, FOCUS, ON_FOCUS, ON_FOCUS2, RAISED, RAISED2, SURFACE, TEXT, TEXT2, TEXT3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIN = os.path.join(ROOT, "skin.monteiro")
XML = os.path.join(SKIN, "xml")
MEDIA = os.path.join(SKIN, "media")
GENERATOR = "generate_monteiro_skin.py"
DIM = "B3000000"  # behind dialogs
LINE = "FF2C2D33"

# Strings of the skin, in its language folder. Kodi gives skins the range 31000 to 31999.
STRINGS = {
    31000: ("TV", "TV"),
    31001: ("Movies", "Filmes"),
    31002: ("Series", "Séries"),
    31003: ("Add-ons", "Add-ons"),
    31004: ("Settings", "Configurações"),
    31005: ("Power", "Energia"),
    31006: ("Live TV from your lists with Easy Channel", "TV ao vivo das suas listas com o Easy Channel"),
    31007: ("Movies of your lists and folders with Easy Movie", "Filmes das suas listas e pastas com o Easy Movie"),
    31008: ("Series and episodes with Easy Movie", "Séries e episódios com o Easy Movie"),
    31009: ("Install and manage add-ons", "Instale e gerencie add-ons"),
    31010: ("Player, interface, system and more", "Player, interface, sistema e mais"),
}


# XML ------------------------------------------------------------------------------------------------------------------

def indent(text, spaces):
    return "\n".join(" " * spaces + line if line else line for line in text.split("\n"))


def tags(**values):
    """Child tags of a control, in order. A value of None leaves the tag out. A tuple gives (attributes, text)."""
    lines = []
    for tag, value in values.items():
        if value is None:
            continue
        tag = tag.rstrip("_")
        if isinstance(value, tuple):
            attributes, text = value
            lines.append("<%s %s>%s</%s>" % (tag, attributes, text, tag))
        else:
            lines.append("<%s>%s</%s>" % (tag, value, tag))
    return "\n".join(lines)


def control(kind, control_id=None, children=(), **values):
    ident = ' id="%s"' % control_id if control_id is not None else ""
    body = [tags(**values)] + [child for child in children if child]
    return '<control type="%s"%s>\n%s\n</control>' % (kind, ident, indent("\n".join(part for part in body if part), 2))


def image(left, top, width, height, texture, color=None, visible=None, border=None, keep=False, animation=None, fallback=None):
    attributes = " ".join(part for part in ('border="%s"' % border if border else "", 'colordiffuse="%s"' % color if color else "",
                                            'fallback="%s"' % fallback if fallback else "") if part)
    return control("image", left=left, top=top, width=width, height=height, aspectratio="keep" if keep else None,
                   texture=(attributes, texture) if attributes else texture, visible=visible,
                   children=[animation] if animation else ())


def panel(left, top, width, height, color, visible=None):
    return image(left, top, width, height, "panel.png", color, visible, border=16)


def label(left, top, width, height, text, font="font13", color=TEXT, control_id=None, align=None, visible=None, scroll=None,
          wrap=None):
    return control("label", control_id, left=left, top=top, width=width, height=height, align=align, aligny="center", font=font,
                   textcolor=color, scroll=scroll, wrapmultiline=wrap, label=text, visible=visible)


def button(control_id, left, top, width, height, text="", font="font13", align="center", nav=None, onclick=None, visible=None,
           offset=30, texture_nofocus=None):
    nav = nav or {}
    return control("button", control_id, left=left, top=top, width=width, height=height, onup=nav.get("up"), ondown=nav.get("down"),
                   onleft=nav.get("left"), onright=nav.get("right"), font=font, align=align, aligny="center", textoffsetx=offset,
                   textcolor=TEXT, focusedcolor=ON_FOCUS, disabledcolor=TEXT3,
                   texturefocus=('border="16" colordiffuse="%s"' % FOCUS, "panel.png"),
                   texturenofocus=('border="16" colordiffuse="%s"' % (texture_nofocus or RAISED), "panel.png"),
                   pulseonselect="false", label=text, onclick=onclick, visible=visible)


def fade(time_in=200, time_out=200):
    return ('<animation effect="fade" start="0" end="100" time="%d">WindowOpen</animation>\n'
            '<animation effect="fade" start="100" end="0" time="%d">WindowClose</animation>' % (time_in, time_out))


def pop():
    """Dialogs open with a short zoom and fade."""
    return ('<animation type="WindowOpen" reversible="false">\n'
            '  <effect type="fade" start="0" end="100" time="180" />\n'
            '  <effect type="zoom" start="94" end="100" center="auto" time="180" tween="cubic" easing="out" />\n'
            '</animation>\n'
            '<animation type="WindowClose" reversible="false">\n'
            '  <effect type="fade" start="100" end="0" time="140" />\n'
            '</animation>')


def window(comment, controls, default=None, always=False, extra="", window_type=None, window_id=None):
    attribute = (' type="%s"' % window_type if window_type else "") + (' id="%s"' % window_id if window_id else "")
    default_tag = '  <defaultcontrol%s>%s</defaultcontrol>\n' % (' always="true"' if always else "", default) if default is not None else ""
    extra = indent(extra, 2) + "\n" if extra else ""
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!-- %s Generated by tools/%s. -->\n<window%s>\n%s%s  <controls>\n%s\n  </controls>\n</window>\n'
            % (comment, GENERATOR, attribute, default_tag, extra, indent("\n".join(controls), 4)))


def group(left, top, width, height, children, visible=None, control_id=None, animation=None):
    return control("group", control_id, left=left, top=top, width=width, height=height, visible=visible,
                   children=([animation] if animation else []) + list(children))


def dim():
    return image(0, 0, 1920, 1080, "white.png", DIM)


def progress(control_id, left, top, width, height=10, info=None, visible=None):
    return control("progress", control_id, left=left, top=top, width=width, height=height,
                   texturebg=('border="4" colordiffuse="%s"' % RAISED2, "panel.png"),
                   midtexture=('border="4" colordiffuse="%s"' % ACCENT, "panel.png"), info=info, visible=visible)


# Defaults: the look of the controls that Kodi creates by itself, such as the buttons of settings and dialogs ----------

def defaults():
    focus = 'border="16" colordiffuse="%s"' % FOCUS
    return """<?xml version="1.0" encoding="utf-8"?>
<!-- Default look of each control type. Generated by tools/%(generator)s. -->
<includes>
  <default type="label">
    <font>font13</font>
    <textcolor>%(text)s</textcolor>
    <aligny>center</aligny>
  </default>
  <default type="fadelabel">
    <font>font13</font>
    <textcolor>%(text)s</textcolor>
  </default>
  <default type="textbox">
    <font>font13</font>
    <textcolor>%(text2)s</textcolor>
  </default>
  <default type="button">
    <font>font13</font>
    <textcolor>%(text)s</textcolor>
    <focusedcolor>%(on_focus)s</focusedcolor>
    <disabledcolor>%(text3)s</disabledcolor>
    <textoffsetx>30</textoffsetx>
    <aligny>center</aligny>
    <texturefocus %(focus)s>panel.png</texturefocus>
    <pulseonselect>false</pulseonselect>
    <texturenofocus />
  </default>
  <default type="togglebutton">
    <font>font13</font>
    <textcolor>%(text)s</textcolor>
    <focusedcolor>%(on_focus)s</focusedcolor>
    <textoffsetx>30</textoffsetx>
    <aligny>center</aligny>
    <texturefocus %(focus)s>panel.png</texturefocus>
    <pulseonselect>false</pulseonselect>
    <texturenofocus />
    <alttexturefocus %(focus)s>panel.png</alttexturefocus>
    <alttexturenofocus />
  </default>
  <default type="radiobutton">
    <font>font13</font>
    <textcolor>%(text)s</textcolor>
    <focusedcolor>%(on_focus)s</focusedcolor>
    <disabledcolor>%(text3)s</disabledcolor>
    <textoffsetx>30</textoffsetx>
    <aligny>center</aligny>
    <texturefocus %(focus)s>panel.png</texturefocus>
    <pulseonselect>false</pulseonselect>
    <texturenofocus />
    <radiowidth>72</radiowidth>
    <radioheight>40</radioheight>
    <textureradioonfocus>toggle-on.png</textureradioonfocus>
    <textureradioonnofocus>toggle-on.png</textureradioonnofocus>
    <textureradioofffocus colordiffuse="%(on_focus2)s">toggle-off.png</textureradioofffocus>
    <textureradiooffnofocus colordiffuse="%(text3)s">toggle-off.png</textureradiooffnofocus>
    <textureradioondisabled colordiffuse="%(text3)s">toggle-on.png</textureradioondisabled>
    <textureradiooffdisabled colordiffuse="%(text3)s">toggle-off.png</textureradiooffdisabled>
  </default>
  <default type="spincontrolex">
    <font>font13</font>
    <textcolor>%(text)s</textcolor>
    <focusedcolor>%(on_focus)s</focusedcolor>
    <disabledcolor>%(text3)s</disabledcolor>
    <textoffsetx>30</textoffsetx>
    <aligny>center</aligny>
    <texturefocus %(focus)s>panel.png</texturefocus>
    <pulseonselect>false</pulseonselect>
    <texturenofocus />
    <spinwidth>36</spinwidth>
    <spinheight>36</spinheight>
    <textureup colordiffuse="%(text2)s">chevron-right.png</textureup>
    <textureupfocus colordiffuse="%(on_focus)s">chevron-right.png</textureupfocus>
    <texturedown colordiffuse="%(text2)s">chevron-left.png</texturedown>
    <texturedownfocus colordiffuse="%(on_focus)s">chevron-left.png</texturedownfocus>
    <textureupdisabled colordiffuse="%(text3)s">chevron-right.png</textureupdisabled>
    <texturedowndisabled colordiffuse="%(text3)s">chevron-left.png</texturedowndisabled>
  </default>
  <default type="spincontrol">
    <font>font13</font>
    <textcolor>%(text)s</textcolor>
    <focusedcolor>%(text)s</focusedcolor>
    <aligny>center</aligny>
    <spinwidth>36</spinwidth>
    <spinheight>36</spinheight>
    <textureup colordiffuse="%(text2)s">chevron-right.png</textureup>
    <textureupfocus colordiffuse="%(accent)s">chevron-right.png</textureupfocus>
    <texturedown colordiffuse="%(text2)s">chevron-left.png</texturedown>
    <texturedownfocus colordiffuse="%(accent)s">chevron-left.png</texturedownfocus>
  </default>
  <default type="sliderex">
    <font>font13</font>
    <textcolor>%(text)s</textcolor>
    <focusedcolor>%(on_focus)s</focusedcolor>
    <disabledcolor>%(text3)s</disabledcolor>
    <textoffsetx>30</textoffsetx>
    <aligny>center</aligny>
    <texturefocus %(focus)s>panel.png</texturefocus>
    <pulseonselect>false</pulseonselect>
    <texturenofocus />
    <sliderwidth>300</sliderwidth>
    <sliderheight>32</sliderheight>
    <texturesliderbar colordiffuse="%(raised2)s">slider-bar.png</texturesliderbar>
    <textureslidernib colordiffuse="%(accent)s">slider-nib.png</textureslidernib>
    <textureslidernibfocus colordiffuse="%(accent)s">slider-nib.png</textureslidernibfocus>
  </default>
  <default type="slider">
    <texturesliderbar colordiffuse="%(raised2)s">slider-bar.png</texturesliderbar>
    <textureslidernib colordiffuse="%(accent)s">slider-nib.png</textureslidernib>
    <textureslidernibfocus colordiffuse="%(accent)s">slider-nib.png</textureslidernibfocus>
  </default>
  <default type="edit">
    <font>font13</font>
    <textcolor>%(text)s</textcolor>
    <focusedcolor>%(on_focus)s</focusedcolor>
    <disabledcolor>%(text3)s</disabledcolor>
    <textoffsetx>30</textoffsetx>
    <aligny>center</aligny>
    <texturefocus %(focus)s>panel.png</texturefocus>
    <pulseonselect>false</pulseonselect>
    <texturenofocus />
  </default>
  <default type="colorbutton">
    <font>font13</font>
    <textcolor>%(text)s</textcolor>
    <focusedcolor>%(on_focus)s</focusedcolor>
    <textoffsetx>30</textoffsetx>
    <aligny>center</aligny>
    <texturefocus %(focus)s>panel.png</texturefocus>
    <pulseonselect>false</pulseonselect>
    <texturenofocus />
    <colorwidth>40</colorwidth>
    <colorheight>40</colorheight>
    <texturecolormask>circle.png</texturecolormask>
    <texturecolordisabledmask colordiffuse="%(text3)s">circle.png</texturecolordisabledmask>
  </default>
  <default type="progress">
    <texturebg border="4" colordiffuse="%(raised2)s">panel.png</texturebg>
    <midtexture border="4" colordiffuse="%(accent)s">panel.png</midtexture>
  </default>
  <default type="scrollbar">
    <texturesliderbackground colordiffuse="%(raised)s">slider-bar.png</texturesliderbackground>
    <texturesliderbar colordiffuse="%(text3)s">slider-bar.png</texturesliderbar>
    <texturesliderbarfocus colordiffuse="%(accent)s">slider-bar.png</texturesliderbarfocus>
    <orientation>vertical</orientation>
    <showonepage>false</showonepage>
  </default>
  <default type="grouplist">
    <orientation>vertical</orientation>
    <itemgap>0</itemgap>
  </default>
</includes>
""" % dict(generator=GENERATOR, text=TEXT, text2=TEXT2, text3=TEXT3, on_focus=ON_FOCUS, on_focus2=ON_FOCUS2, focus=focus,
           accent=ACCENT, raised=RAISED, raised2=RAISED2)


def fonts():
    sizes = [("font10", 23, False), ("font12", 25, False), ("font13", 30, False), ("font14", 33, False), ("font27", 27, False),
             ("font32", 32, False), ("font37", 37, False), ("font45", 45, False), ("font60", 60, False),
             ("font20_title", 20, True), ("font25_title", 25, True), ("font30_title", 30, True), ("font32_title", 32, True),
             ("font36_title", 36, True), ("font40_title", 40, True), ("font45_title", 45, True), ("font52_title", 52, True),
             ("font_clock", 64, False), ("font_menu", 34, True)]
    entries = "\n".join("    <font>\n      <name>%s</name>\n      <filename>%s</filename>\n      <size>%d</size>\n    </font>"
                        % (name, "NotoSans-Bold.ttf" if bold else "NotoSans-Regular.ttf", size) for name, size, bold in sizes)
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!-- Fonts of the skin: Noto Sans, under the SIL Open Font License. '
            'The names and sizes match the ones add-on windows expect. Generated by tools/%s. -->\n'
            '<fonts>\n  <fontset id="Default" idloc="31013">\n%s\n  </fontset>\n</fonts>\n' % (GENERATOR, entries))


# Home -------------------------------------------------------------------------------------------------------------------

HOME_ITEMS = [
    # label, description, icon, action, and the add-on it needs
    (31000, 31006, "tv.png", "RunAddon(script.m3u.channels)", "System.HasAddon(script.m3u.channels)"),
    (31001, 31007, "film.png", "RunAddon(script.m3u.movies)", "System.HasAddon(script.m3u.movies)"),
    (31002, 31008, "series.png", "RunScript(script.m3u.movies,series)", "System.HasAddon(script.m3u.movies)"),
    (31003, 31009, "puzzle.png", "ActivateWindow(addonbrowser)", None),
    (31004, 31010, "gear.png", "ActivateWindow(settings)", None),
]


def home():
    tile, gap = 300, 32
    count = len(HOME_ITEMS)
    width = count * tile + (count - 1) * gap
    left = (1920 - width) // 2
    # Each item takes its tile and the gap after it, so the list holds them all without scrolling.
    list_width = count * (tile + gap)
    focus = "Control.HasFocus(9000)"
    items = []
    for label_id, description_id, icon, action, condition in HOME_ITEMS:
        if condition:
            # Without the add-on, the tile offers to install it from the Monteiro repository.
            addon_id = action[action.index("(") + 1:].split(",")[0].rstrip(")")
            onclick = ('<onclick condition="%s">%s</onclick>\n<onclick condition="!%s">InstallAddon(%s)</onclick>'
                       % (condition, action, condition, addon_id))
        else:
            onclick = "<onclick>%s</onclick>" % action
        description = "$LOCALIZE[%d]" % description_id
        items.append("<item>\n  <label>$LOCALIZE[%d]</label>\n  <label2>%s</label2>\n  <icon>%s</icon>\n%s\n</item>"
                     % (label_id, description, icon, indent(onclick, 2)))
    def tile_parts(focused, condition=None):
        return [panel(0, 0, tile, tile, FOCUS if focused else SURFACE, condition),
                image(90, 64, 120, 120, "$INFO[ListItem.Icon]", ON_FOCUS if focused else TEXT2, condition),
                label(0, 200, tile, 60, "$INFO[ListItem.Label]", "font_menu", ON_FOCUS if focused else TEXT, align="center", visible=condition)]
    # The selected tile looks focused only while the menu has the focus, not while the power button has it.
    layout = lambda focused: "\n".join(tile_parts(True, focus) + tile_parts(False, "!" + focus) if focused else tile_parts(False))
    # A list, so the focus moves between the tiles while they stay in place.
    menu = '''<control type="list" id="9000">
  <left>%d</left>
  <top>390</top>
  <width>%d</width>
  <height>%d</height>
  <orientation>horizontal</orientation>
  <scrolltime>0</scrolltime>
  <onup>9100</onup>
  <ondown>noop</ondown>
  <onleft>noop</onleft>
  <onright>noop</onright>
  <itemlayout width="%d" height="%d">
%s
  </itemlayout>
  <focusedlayout width="%d" height="%d">
%s
  </focusedlayout>
  <content>
%s
  </content>
</control>''' % (left, list_width, tile, tile + gap, tile, indent(layout(False), 4), tile + gap, tile,
                  indent(layout(True), 4), indent("\n".join(items), 4))
    top_buttons = round_button(9100, 1808, 44, "power.png", "ActivateWindow(%d)" % POWER_WINDOW, nav={"down": 9000, "left": 9000})
    return window("Home screen: TV, Movies and Series open the Easy add-ons directly.", [
        image(0, 0, 1920, 1080, "white.png", BG),
        image(0, 0, 1920, 1080, "fanart.jpg", "40FFFFFF"),
        image(0, 0, 1920, 1080, "shade.png", "E60E0F11"),
        image(64, 48, 64, 64, "logo.png"),
        label(148, 44, 900, 72, "Monteiro", "font45_title"),
        label(1100, 44, 520, 72, "$INFO[System.Time]", "font45", TEXT2, align="right"),
        menu,
        label(left, 760, width, 50, "$INFO[Container(9000).ListItem.Label2]", "font14", TEXT2, align="center"),
        label(left, 990, width, 40, "$INFO[System.Date]", "font12", TEXT3, align="center"),
        *top_buttons,
    ], default=9000, extra="<menucontrol>9000</menucontrol>\n<backgroundcolor>%s</backgroundcolor>" % BG)


def round_button(control_id, left, top, icon, onclick, size=72, nav=None):
    """A round icon button. Buttons cannot hold images, so the icon is drawn over it in two colors."""
    nav = nav or {}
    inset = size // 4
    return [control("button", control_id, left=left, top=top, width=size, height=size, onclick=onclick, label="",
                    onup=nav.get("up"), ondown=nav.get("down"), onleft=nav.get("left"), onright=nav.get("right"),
                    texturefocus=('colordiffuse="%s"' % FOCUS, "circle.png"),
                    texturenofocus=('colordiffuse="%s"' % RAISED, "circle.png")),
            image(left + inset, top + inset, size - 2 * inset, size - 2 * inset, icon, ON_FOCUS, "Control.HasFocus(%d)" % control_id),
            image(left + inset, top + inset, size - 2 * inset, size - 2 * inset, icon, TEXT2, "!Control.HasFocus(%d)" % control_id)]


# Dialogs --------------------------------------------------------------------------------------------------------------

def dialog_frame(left, top, width, height, heading_id=None, heading=""):
    parts = [panel(left, top, width, height, SURFACE)]
    if heading_id is not None or heading:
        parts.append(label(left + 40, top + 24, width - 80, 60, heading, "font32_title", control_id=heading_id))
        parts.append(image(left + 24, top + 96, width - 48, 2, "white.png", RAISED))
    return parts


def dialog_buttons(control_id, left, top, width, buttons, orientation="horizontal", button_width=280, nav=None):
    nav = nav or {}
    children = [button(cid, 0, 0, button_width, 76, text) for cid, text in buttons]
    return control("grouplist", control_id, left=left, top=top, width=width, height=76 if orientation == "horizontal" else 600,
                   orientation=orientation, align="center", itemgap=20, onup=nav.get("up"), ondown=nav.get("down"),
                   onleft=nav.get("left"), onright=nav.get("right"), children=children)


def confirm():
    # Yes and no, progress, and the change of skin with its countdown. Kodi sets the heading, text and button labels.
    left, top, width, height = 410, 290, 1100, 500
    return window("Confirmations, messages and progress.", [
        dim(),
        *dialog_frame(left, top, width, height, heading_id=1),
        control("textbox", 9, left=left + 40, top=top + 120, width=width - 80, height=200, font="font13", textcolor=TEXT2,
                autoscroll=('time="3000" delay="4000" repeat="5000"', "true")),
        progress(20, left + 40, top + 336, width - 80, 12, "System.Progressbar"),
        dialog_buttons(9000, left, top + height - 116, width, [(11, ""), (10, ""), (12, "")]),
    ], extra=pop() + "\n<depth>DepthDialog+</depth>")


def context_menu():
    # Kodi moves the window next to the focused control, copies button 1000 into grouplist 996 for each option, and
    # sizes image 999 around them. The dimmed area covers the screen wherever the window lands, and closes the menu.
    return window("Context menus of Kodi and add-ons.", [
        image(-1920, -1080, 5760, 3240, "white.png", DIM),
        control("button", left=-1920, top=-1080, width=5760, height=3240, texturefocus="", texturenofocus="", onclick="Action(close)"),
        # Kodi sizes image 999 by its own rules, so the buttons carry the background instead.
        control("image", 999, left=0, top=0, width=560, height=10, texture=""),
        control("grouplist", 996, left=20, top=20, width=520, height=1000, itemgap=0),
        button(1000, 20, 20, 520, 76, align="left", texture_nofocus=SURFACE),
    ], default=996, extra=pop() + "\n<coordinates>\n  <left>0</left>\n  <top>0</top>\n</coordinates>")


def notification():
    return window("Notifications in the top right corner.", [
        group(1300, 40, 580, 132, [
            panel(0, 0, 580, 132, SURFACE),
            control("image", 400, left=24, top=26, width=80, height=80, aspectratio="keep"),
            control("fadelabel", 401, left=128, top=20, width=430, height=44, font="font13", textcolor=TEXT, scrollout="false",
                    pauseatend="2000"),
            control("fadelabel", 402, left=128, top=66, width=430, height=44, font="font12", textcolor=TEXT2, scrollout="false",
                    pauseatend="2000"),
        ], animation='<animation effect="slide" start="620,0" end="0,0" time="260" tween="cubic" easing="out">WindowOpen</animation>\n'
                     '<animation effect="slide" start="0,0" end="620,0" time="200" tween="cubic" easing="in">WindowClose</animation>'),
    ], extra="<depth>DepthOSDPopout</depth>")


def busy():
    spin = '<animation effect="rotate" end="-360" center="auto" time="900" loop="true" reversible="false" condition="true">Conditional</animation>'
    return window("Busy spinner.", [
        image(900, 480, 120, 120, "circle.png", "CC17181B"),
        image(920, 500, 80, 80, "spinner.png", ACCENT, animation=spin),
    ], extra=fade(300, 150) + "\n<depth>DepthMax</depth>")


def extended_progress():
    return window("Background progress in the top right corner, such as add-on updates.", [
        group(1300, 40, 580, 150, [
            panel(0, 0, 580, 150, SURFACE),
            label(28, 20, 524, 40, "", "font13", control_id=30),
            label(28, 62, 524, 36, "", "font12", TEXT2, control_id=31),
            progress(32, 28, 116, 524, 10),
        ]),
    ], extra="<depth>DepthOSDPopout</depth>")


def keyboard():
    key, step = 100, 108
    rows = [range(100, 113), range(120, 133), range(140, 153), range(160, 173)]
    left, top = 140, 330
    controls = [dim(), *dialog_frame(100, 90, 1720, 900), label(140, 114, 1640, 60, "", "font32_title", control_id=311),
                control("edit", 312, left=140, top=200, width=1640, height=90, font="font14", textcolor=TEXT, focusedcolor=ON_FOCUS,
                        textoffsetx=30, aligny="center", ondown=100, onup=300,
                        texturefocus=('border="16" colordiffuse="%s"' % FOCUS, "panel.png"),
                        texturenofocus=('border="16" colordiffuse="%s"' % RAISED, "panel.png"))]
    for row_index, row in enumerate(rows):
        for column, control_id in enumerate(row):
            up = rows[row_index - 1][column] if row_index else 312
            down = rows[row_index + 1][column] if row_index < 3 else (302 if column < 3 else 32 if column < 9 else 8)
            nav = {"up": up, "down": down, "left": row[column - 1] if column else 300,
                   "right": row[column + 1] if column < len(row) - 1 else 300}
            controls.append(button(control_id, left + column * step, top + row_index * 100, key, 88, "", "font14", nav=nav, offset=0))
    bottom = top + 4 * 100
    # Words rather than symbols, which Noto Sans does not draw.
    specials = [(302, 0, 2, "$LOCALIZE[31017]"), (303, 2, 1, "Aa"), (304, 3, 2, "#@!"), (32, 5, 4, "$LOCALIZE[31015]"),
                (8, 9, 2, "$LOCALIZE[31016]"), (305, 11, 1, "‹"), (306, 12, 1, "›")]
    order = [special[0] for special in specials]
    for index, (control_id, column, span, text) in enumerate(specials):
        nav = {"up": rows[3][column], "down": 312, "left": order[index - 1] if index else 300,
               "right": order[index + 1] if index < len(order) - 1 else 300}
        controls.append(control("radiobutton", control_id, left=left + column * step, top=bottom, width=span * step - 8, height=88,
                                onup=nav["up"], ondown=nav["down"], onleft=nav["left"], onright=nav["right"], font="font14",
                                align="center", textoffsetx=0, label=text, radiowidth=1, radioheight=1,
                                texturenofocus=('border="16" colordiffuse="%s"' % RAISED2, "panel.png")))
    controls.append(control("grouplist", 300, left=1560, top=330, width=220, height=500, itemgap=16, onleft=112, onup=312,
                            children=[button(300, 0, 0, 220, 88, "$LOCALIZE[186]", nav={"left": 112}),
                                      button(301, 0, 0, 220, 88, "$LOCALIZE[222]", nav={"left": 132}),
                                      button(310, 0, 0, 220, 88, "", "font12", nav={"left": 152}, offset=10),
                                      button(309, 0, 0, 220, 88, "", "font12", nav={"left": 172}, offset=10),
                                      button(307, 0, 0, 220, 88, "IP", nav={"left": 172})]).replace(
        '<control type="grouplist" id="300">', '<control type="grouplist" id="95200">'))
    controls += [label(140, 920, 1400, 40, "", "font12", TEXT2, control_id=313), label(140, 950, 1400, 30, "", "font12", TEXT3, control_id=314)]
    return window("On screen keyboard. Kodi sets the key labels for the layout and case.", controls, default=300,
                  extra=pop() + "\n<depth>DepthOSD</depth>")


def numeric():
    left, top = 610, 160
    controls = [dim(), *dialog_frame(left, top, 700, 760, heading_id=4),
                control("textbox", 1, left=left + 40, top=top + 120, width=620, height=60, font="font36_title", textcolor=TEXT, align="center")]
    keys = [(11, "1"), (12, "2"), (13, "3"), (14, "4"), (15, "5"), (16, "6"), (17, "7"), (18, "8"), (19, "9"), (20, "‹"), (10, "0"), (22, "›")]
    for index, (control_id, text) in enumerate(keys):
        row, column = divmod(index, 3)
        kind = "radiobutton" if control_id in (20, 22) else "button"
        nav = {}
        controls.append(control(kind, control_id, left=left + 70 + column * 196, top=top + 210 + row * 100, width=180, height=88,
                                font="font36_title", align="center", textoffsetx=0, label=text,
                                texturenofocus=('border="16" colordiffuse="%s"' % RAISED, "panel.png"),
                                radiowidth=1 if kind == "radiobutton" else None, radioheight=1 if kind == "radiobutton" else None))
    controls.append(dialog_buttons(4000, left, top + 640, 700, [(21, "$LOCALIZE[186]"), (23, "$LOCALIZE[222]")], button_width=260))
    return window("Number entry, such as a PIN or a time.", controls, default=21, extra=pop())


def select():
    left, top, width, height = 360, 110, 1200, 860
    item = lambda focused, detailed: "\n".join([
        panel(0, 0, 900, 84 if not detailed else 110, FOCUS) if focused else "",
        image(20, 22 if not detailed else 25, 40, 40 if not detailed else 60, "check.png", ON_FOCUS if focused else ACCENT,
              "ListItem.IsSelected") if not detailed else image(16, 10, 90, 90, "$INFO[ListItem.Icon]", keep=True),
        label(76 if not detailed else 126, 0 if not detailed else 12, 800 if not detailed else 750, 84 if not detailed else 48,
              "$INFO[ListItem.Label]", "font13", ON_FOCUS if focused else TEXT),
        label(76 if not detailed else 126, 58, 750, 40, "$INFO[ListItem.Label2]", "font12", ON_FOCUS2 if focused else TEXT2) if detailed else "",
    ])
    def selection_list(control_id, detailed):
        height_item = 110 if detailed else 84
        return '''<control type="list" id="%d">
  <left>%d</left>
  <top>%d</top>
  <width>900</width>
  <height>660</height>
  <onright>9001</onright>
  <onleft>9001</onleft>
  <pagecontrol>61</pagecontrol>
  <scrolltime>120</scrolltime>
  <itemlayout height="%d" width="900">
%s
  </itemlayout>
  <focusedlayout height="%d" width="900">
%s
  </focusedlayout>
</control>''' % (control_id, left + 30, top + 120, height_item, indent(item(False, detailed), 4), height_item, indent(item(True, detailed), 4))
    return window("Selection lists of Kodi and add-ons, single or multiple.", [
        dim(), *dialog_frame(left, top, width, height, heading_id=1),
        label(left + width - 300, top + 24, 260, 60, "", "font12", TEXT3, control_id=2, align="right"),
        selection_list(3, False), selection_list(6, True),
        control("scrollbar", 61, left=left + 944, top=top + 120, width=8, height=660, onleft=3, onright=9001),
        dialog_buttons(9001, left + 970, top + 120, 210, [(5, ""), (8, ""), (7, "$LOCALIZE[222]")], "vertical", 210, nav={"left": 3}),
    ], default=3, always=True, extra=pop() + "\n<depth>DepthOSD</depth>")


def text_viewer():
    left, top, width, height = 160, 90, 1600, 900
    return window("Long texts, such as change logs.", [
        dim(), *dialog_frame(left, top, width, height, heading_id=1),
        control("textbox", 5, left=left + 40, top=top + 120, width=width - 120, height=height - 240, font="font13", textcolor=TEXT2,
                pagecontrol=3000),
        control("scrollbar", 3000, left=left + width - 60, top=top + 120, width=8, height=height - 240, onleft=1000, onright=1000),
        dialog_buttons(9000, left, top + height - 104, width, [(1000, "$LOCALIZE[186]")]),
    ], default=1000, extra=pop())


# Settings ---------------------------------------------------------------------------------------------------------------

def setting_templates(width):
    """The controls Kodi copies for each setting: a button, a toggle, a choice, a separator, a text field, a slider, a
    group title and a color."""
    common = dict(width=width, height=72, textoffsetx=30)
    return [
        control("button", 7, label2="", **common),
        control("radiobutton", 8, **common),
        control("spincontrolex", 9, **common),
        control("image", 11, width=width, height=2, texture=('colordiffuse="%s"' % LINE, "white.png")),
        control("edit", 12, **common),
        control("sliderex", 13, **common),
        control("label", 14, width=width, height=64, font="font12", textcolor=ACCENT, textoffsetx=30, aligny="bottom"),
        control("colorbutton", 15, **common),
    ]


def settings_dialog(comment, with_categories, buttons, heading_id=2, level=True):
    left, top, width, height = 100, 60, 1720, 960
    area_left = left + (460 if with_categories else 40)
    area_width = width - (500 if with_categories else 80)
    controls = [dim(), *dialog_frame(left, top, width, height, heading_id=heading_id)]
    if with_categories:
        controls += [control("grouplist", 3, left=left + 30, top=top + 120, width=400, height=640, onright=5, onleft=9000,
                             onup=3, ondown=20 if level else 3, itemgap=6),
                     control("button", 10, width=400, height=76, textoffsetx=30, font="font13",
                             texturenofocus=('border="16" colordiffuse="%s"' % RAISED, "panel.png"))]
    controls += [
        panel(area_left, top + 120, area_width, 640, BG),
        control("grouplist", 5, left=area_left + 10, top=top + 130, width=area_width - 40, height=620, pagecontrol=60,
                onleft=3 if with_categories else 9000, onright=60, onup=5, ondown=5, itemgap=0),
        control("scrollbar", 60, left=area_left + area_width - 20, top=top + 130, width=8, height=620, onleft=5,
                onright=9000 if buttons else 3),
        control("textbox", 6, left=area_left, top=top + 780, width=area_width, height=80, font="font12", textcolor=TEXT2),
        *setting_templates(area_width - 40),
    ]
    if with_categories and level:
        controls.append(control("radiobutton", 20, left=left + 30, top=top + 780, width=400, height=76, onup=3, ondown=3,
                                onright=5, onclick="SettingsLevelChange", font="font12", radiowidth=1, radioheight=1,
                                texturenofocus=('border="16" colordiffuse="%s"' % RAISED, "panel.png")))
    if buttons:
        controls.append(dialog_buttons(9000, area_left, top + height - 96, area_width, buttons, button_width=260,
                                       nav={"up": 5, "left": 3 if with_categories else 9000}))
    return window(comment, controls, default=3 if with_categories else 5, extra=pop())


def settings_menu():
    entries = [("$LOCALIZE[14200]", "ActivateWindow(PlayerSettings)", None), ("$LOCALIZE[14211]", "ActivateWindow(MediaSettings)", None),
               ("$LOCALIZE[14036]", "ActivateWindow(ServiceSettings)", None), ("$LOCALIZE[14206]", "ActivateWindow(InterfaceSettings)", None),
               ("$LOCALIZE[13000]", "ActivateWindow(SystemSettings)", None), ("$LOCALIZE[24001]", "ActivateWindow(addonbrowser)", None),
               ("$LOCALIZE[14204]", "ActivateWindow(PVRSettings)", None),
               ("LibreELEC", "RunAddon(service.libreelec.settings)", "System.AddonIsEnabled(service.libreelec.settings)")]
    items = "\n".join("<item>\n  <label>%s</label>\n  <onclick>%s</onclick>%s\n</item>"
                      % (text, action, "\n  <visible>%s</visible>" % condition if condition else "") for text, action, condition in entries)
    tile_w, tile_h = 400, 160
    layout = lambda focused: "\n".join([panel(0, 0, tile_w - 24, tile_h - 24, FOCUS if focused else SURFACE),
                                        label(30, 0, tile_w - 84, tile_h - 24, "$INFO[ListItem.Label]", "font30_title",
                                              ON_FOCUS if focused else TEXT)])
    grid = '''<control type="panel" id="9000">
  <left>160</left>
  <top>240</top>
  <width>1600</width>
  <height>640</height>
  <orientation>vertical</orientation>
  <scrolltime>120</scrolltime>
  <itemlayout width="%d" height="%d">
%s
  </itemlayout>
  <focusedlayout width="%d" height="%d">
%s
  </focusedlayout>
  <content>
%s
  </content>
</control>''' % (tile_w, tile_h, indent(layout(False), 4), tile_w, tile_h, indent(layout(True), 4), indent(items, 4))
    return window("Settings sections.", [
        image(0, 0, 1920, 1080, "white.png", BG),
        image(64, 48, 64, 64, "gear.png", TEXT2),
        label(148, 44, 900, 72, "$LOCALIZE[5]", "font45_title"),
        label(1100, 44, 760, 72, "$INFO[System.Time]", "font45", TEXT2, align="right"),
        grid,
    ], default=9000)


# Add-ons --------------------------------------------------------------------------------------------------------------

def addon_browser():
    row = lambda focused: "\n".join([
        panel(0, 0, 1240, 100, FOCUS) if focused else "",
        image(16, 10, 80, 80, "$INFO[ListItem.Icon]", keep=True, fallback="puzzle.png"),
        label(120, 6, 860, 50, "$INFO[ListItem.Label]", "font13", ON_FOCUS if focused else TEXT),
        label(120, 50, 860, 40, "$INFO[ListItem.Label2]", "font12", ON_FOCUS2 if focused else TEXT2),
        label(980, 0, 240, 100, "$INFO[ListItem.AddonVersion]", "font12", ON_FOCUS2 if focused else TEXT3, align="right"),
    ])
    view = '''<control type="list" id="50">
  <left>600</left>
  <top>140</top>
  <width>1240</width>
  <height>900</height>
  <onleft>9000</onleft>
  <onright>60</onright>
  <pagecontrol>60</pagecontrol>
  <scrolltime>120</scrolltime>
  <viewtype label="535">list</viewtype>
  <itemlayout height="108" width="1240">
%s
  </itemlayout>
  <focusedlayout height="108" width="1240">
%s
  </focusedlayout>
</control>''' % (indent(row(False), 4), indent(row(True), 4))
    side = control("grouplist", 9000, left=60, top=240, width=480, height=700, onright=50, itemgap=12, children=[
        label(0, 0, 480, 50, "$LOCALIZE[31021]", "font12", TEXT3, control_id=201),
        control("radiobutton", 7, width=480, height=76, label="$LOCALIZE[25001]", font="font12",
                texturenofocus=('border="16" colordiffuse="%s"' % RAISED, "panel.png")),
        control("radiobutton", 8, width=480, height=76, label="$LOCALIZE[24999]", font="font12",
                texturenofocus=('border="16" colordiffuse="%s"' % RAISED, "panel.png")),
        button(9, 0, 0, 480, 76, "$LOCALIZE[24034]", align="left"),
        button(5, 0, 0, 480, 76, "$LOCALIZE[10004]", align="left"),
    ])
    return window("Add-ons: categories, repositories and the add-ons in them.", [
        image(0, 0, 1920, 1080, "white.png", BG),
        image(64, 48, 64, 64, "puzzle.png", TEXT2),
        label(148, 44, 1000, 72, "$INFO[Container.FolderName]", "font45_title"),
        label(1100, 44, 760, 72, "$INFO[Container.NumItems] $LOCALIZE[31014]", "font13", TEXT2, align="right"),
        panel(580, 130, 1280, 920, SURFACE),
        view,
        control("scrollbar", 60, left=1844, top=150, width=8, height=880, onleft=50, onright=9000),
        side,
    ], default=50, extra="<views>50</views>\n<menucontrol>9000</menucontrol>", window_type=None)


def addon_info():
    left, top, width, height = 110, 80, 1700, 920
    buttons = [(12, "$LOCALIZE[518]"), (9, "$LOCALIZE[24020]"), (10, "$LOCALIZE[39024]"), (7, ""), (8, "$LOCALIZE[24138]"),
               (14, "$LOCALIZE[24069]"), (6, "")]
    side = control("grouplist", 9000, left=left + 40, top=top + height - 116, width=width - 80, height=76, orientation="horizontal",
                   itemgap=10, children=[button(cid, 0, 0, 190, 76, text, "font12", offset=10) for cid, text in buttons] + [
                       control("radiobutton", 13, width=330, height=76, label="$LOCALIZE[21340]", font="font12",
                               texturenofocus=('border="16" colordiffuse="%s"' % RAISED, "panel.png"))])
    return window("Details of an add-on, with install, update, settings and the other actions.", [
        dim(), *dialog_frame(left, top, width, height),
        panel(left + 40, top + 40, 240, 240, RAISED),
        image(left + 60, top + 60, 200, 200, "$INFO[ListItem.Icon]", keep=True),
        label(left + 320, top + 40, width - 360, 70, "$INFO[ListItem.AddonName]", "font45_title"),
        label(left + 320, top + 110, width - 360, 44, "$INFO[ListItem.AddonVersion]  ·  $INFO[ListItem.AddonCreator]", "font13", TEXT2),
        label(left + 320, top + 160, width - 360, 44, "$INFO[ListItem.AddonSummary]", "font13", ACCENT),
        control("textbox", left=left + 40, top=top + 320, width=width - 80, height=440, font="font13", textcolor=TEXT2,
                label="$INFO[ListItem.AddonDescription]", autoscroll=('time="3000" delay="6000" repeat="6000"', "true")),
        side,
    ], default=9000, extra=pop())


# Files ----------------------------------------------------------------------------------------------------------------

def file_browser():
    left, top, width, height = 260, 80, 1400, 920
    row = lambda focused: "\n".join([
        panel(0, 0, 1060, 76, FOCUS) if focused else "",
        image(20, 18, 40, 40, "$INFO[ListItem.Icon]", ON_FOCUS if focused else TEXT2, keep=True, fallback="folder.png"),
        label(80, 0, 960, 76, "$INFO[ListItem.Label]", "font13", ON_FOCUS if focused else TEXT)])
    files = '''<control type="list" id="450">
  <left>%d</left>
  <top>%d</top>
  <width>1060</width>
  <height>640</height>
  <onright>9000</onright>
  <onleft>9000</onleft>
  <pagecontrol>60</pagecontrol>
  <scrolltime>120</scrolltime>
  <itemlayout height="80" width="1060">
%s
  </itemlayout>
  <focusedlayout height="80" width="1060">
%s
  </focusedlayout>
</control>''' % (left + 30, top + 170, indent(row(False), 4), indent(row(True), 4))
    return window("Choosing a folder or a file.", [
        dim(), *dialog_frame(left, top, width, height, heading_id=411),
        label(left + 40, top + 110, width - 80, 50, "", "font12", TEXT2, control_id=412, scroll="true"),
        files,
        files.replace('id="450"', 'id="451"').replace("<onright>9000</onright>", "<onright>9000</onright>\n  <visible>false</visible>"),
        control("scrollbar", 60, left=left + 1100, top=top + 170, width=8, height=640, onleft=450, onright=9000),
        dialog_buttons(9000, left + 1130, top + 170, 240, [(413, "$LOCALIZE[186]"), (414, "$LOCALIZE[222]"), (415, "$LOCALIZE[119]"),
                                                           (416, "$LOCALIZE[749]")], "vertical", 240, nav={"left": 450}),
    ], default=450, extra=pop())


POWER_WINDOW = 1100


def power_menu(own=False):
    """The power menu. Kodi opens DialogButtonMenu.xml with its power key. The power button of the home screen opens
    the same menu as a window of the skin, which also closes it before an action."""
    entries = [("$LOCALIZE[13016]", "Powerdown()", "System.CanPowerDown"), ("$LOCALIZE[13013]", "Reset()", "System.CanReboot"),
               ("$LOCALIZE[13011]", "Suspend()", "System.CanSuspend"), ("$LOCALIZE[13012]", "Quit()", "System.ShowExitButton")]
    close = "<onclick>Dialog.Close(%d)</onclick>\n  " % POWER_WINDOW if own else ""
    items = "\n".join("<item>\n  <label>%s</label>\n  %s<onclick>%s</onclick>\n  <visible>%s</visible>\n</item>" % (text, close, action, condition)
                      for text, action, condition in entries)
    layout = lambda focused: "\n".join([panel(0, 0, 560, 80, FOCUS if focused else RAISED),
                                        label(30, 0, 500, 80, "$INFO[ListItem.Label]", "font13", ON_FOCUS if focused else TEXT)])
    menu = '''<control type="panel" id="9000">
  <left>700</left>
  <top>420</top>
  <width>560</width>
  <height>400</height>
  <orientation>vertical</orientation>
  <itemlayout width="560" height="96">
%s
  </itemlayout>
  <focusedlayout width="560" height="96">
%s
  </focusedlayout>
  <content>
%s
  </content>
</control>''' % (indent(layout(False), 4), indent(layout(True), 4), indent(items, 4))
    return window("Power menu.", [dim(), *dialog_frame(660, 300, 640, 520), label(700, 324, 560, 60, "$LOCALIZE[31005]", "font32_title"),
                                  image(684, 396, 592, 2, "white.png", RAISED), menu], default=9000, extra=pop(),
                  window_type="dialog" if own else None, window_id=POWER_WINDOW if own else None)


# Playback ---------------------------------------------------------------------------------------------------------------

def video_full_screen():
    # Kodi draws the video under this window. Add-ons show their own controls over it.
    return window("Full screen video.", [
        control("label", 10, left=-2000, top=0, width=10, height=10),
        control("label", 11, left=-2000, top=0, width=10, height=10),
        control("label", 12, left=-2000, top=0, width=10, height=10),
    ])


def seek_bar():
    shown = "[Player.Seeking | Player.DisplayAfterSeek | Player.Paused | Player.Forwarding | Player.Rewinding]"
    return window("Time bar while seeking or paused, for videos outside the Easy add-ons.", [
        group(0, 0, 1920, 1080, [
            image(0, 760, 1920, 320, "shade.png", "F2000000"),
            label(120, 880, 1200, 50, "$INFO[Player.Title]", "font30_title"),
            label(120, 930, 600, 40, "$INFO[Player.Time]", "font12", TEXT),
            label(1200, 930, 600, 40, "$INFO[Player.Duration]", "font12", TEXT2, align="right"),
            control("progress", left=120, top=980, width=1680, height=8, info="Player.Progress",
                    texturebg=('colordiffuse="4DFFFFFF"', "white.png"), midtexture=('colordiffuse="%s"' % ACCENT, "white.png")),
            label(120, 1000, 1680, 40, "$INFO[Player.SeekOffset]", "font12", TEXT2, control_id=40000),
            control("slider", 401, left=-2000, top=0, width=10, height=10),
            control("slider", 403, left=-2000, top=0, width=10, height=10),
        ], visible=shown, animation='<animation effect="fade" time="200">VisibleChange</animation>'),
    ], extra="<depth>DepthOSD</depth>")


def video_osd():
    buttons = [(600, "⏮", "PlayerControl(Previous)"), (601, "⏪", "PlayerControl(Rewind)"),
               (602, "⏯", "PlayerControl(Play)"), (603, "⏹", "PlayerControl(Stop)"),
               (604, "⏩", "PlayerControl(Forward)"), (605, "⏭", "PlayerControl(Next)")]
    row = control("grouplist", 6000, left=560, top=900, width=800, height=96, orientation="horizontal", align="center", itemgap=20,
                  children=[button(cid, 0, 0, 96, 96, text, "font32_title", onclick=action, offset=0) for cid, text, action in buttons])
    return window("Player controls for videos outside the Easy add-ons. Easy Movie shows its own.", [
        image(0, 640, 1920, 440, "shade.png", "F2000000"),
        label(120, 680, 1680, 60, "$INFO[Player.Title]", "font36_title"),
        label(120, 760, 600, 40, "$INFO[Player.Time]", "font12"),
        label(1200, 760, 600, 40, "$INFO[Player.Duration]", "font12", TEXT2, align="right"),
        control("progress", left=120, top=810, width=1680, height=8, info="Player.Progress",
                texturebg=('colordiffuse="4DFFFFFF"', "white.png"), midtexture=('colordiffuse="%s"' % ACCENT, "white.png")),
        row,
    ], default=602, extra=fade() + "\n<depth>DepthOSD</depth>")


def volume_bar():
    return window("Volume.", [
        group(1500, 40, 380, 90, [
            panel(0, 0, 380, 90, SURFACE),
            image(24, 21, 48, 48, "audio.png", TEXT),
            progress(29999, 96, 40, 250, 10, "Player.Volume"),
        ], visible="!Window.IsVisible(fullscreenvideo) | Player.Paused | true"),
    ], extra=fade() + "\n<depth>DepthOSDPopout</depth>")


def startup():
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!-- Opens the start window chosen in the settings. Generated by tools/%s. -->\n'
            '<window>\n  <onload>ReplaceWindow($INFO[System.StartupWindow])</onload>\n  <controls />\n</window>\n' % GENERATOR)


def pointer():
    return window("Mouse pointer.", [control("image", 1, width=40, height=48, texture="pointer.png"),
                                     control("image", 2, width=40, height=48, texture="pointer.png"),
                                     control("image", 3, width=40, height=48, texture="pointer.png"),
                                     control("image", 4, width=40, height=48, texture="pointer.png")])


# Media ------------------------------------------------------------------------------------------------------------------

K = 8  # draw large, then reduce for smooth edges


def canvas(width, height):
    image_ = Image.new("L", (width * K, height * K), 0)
    return image_, ImageDraw.Draw(image_)


def save(alpha, width, height, name):
    out = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    out.putalpha(alpha.resize((width, height), Image.LANCZOS))
    out.save(os.path.join(MEDIA, name))


def media():
    os.makedirs(MEDIA, exist_ok=True)
    channels = os.path.join(ROOT, "script.m3u.channels", "resources", "skins", "default", "media")
    movies = os.path.join(ROOT, "script.m3u.movies", "resources", "skins", "default", "media")
    for folder, names in ((channels, ["white.png", "panel.png", "tv.png", "gear.png", "check.png", "search.png"]),
                          (movies, ["circle.png", "film.png", "puzzle.png", "audio.png", "shade.png"])):
        for name in names:
            shutil.copy2(os.path.join(folder, name), os.path.join(MEDIA, name))
    shutil.copy2(os.path.join(ROOT, "repository.monteiromedia", "resources", "icon.png"), os.path.join(MEDIA, "logo.png"))
    shutil.copy2(os.path.join(ROOT, "repository.monteiromedia", "resources", "fanart.jpg"), os.path.join(MEDIA, "fanart.jpg"))
    p = lambda value: value * K
    # Series: three stacked cards.
    alpha, draw = canvas(128, 128)
    draw.rounded_rectangle((p(34), p(18), p(94), p(26)), radius=p(4), fill=255)
    draw.rounded_rectangle((p(24), p(32), p(104), p(40)), radius=p(4), fill=255)
    draw.rounded_rectangle((p(14), p(46), p(114), p(110)), radius=p(12), fill=255)
    draw.polygon([(p(54), p(62)), (p(54), p(94)), (p(80), p(78))], fill=0)
    save(alpha, 128, 128, "series.png")
    # Power: a ring open at the top, with a bar.
    alpha, draw = canvas(128, 128)
    draw.arc((p(22), p(26), p(106), p(110)), start=-60, end=240, fill=255, width=p(11))
    draw.rounded_rectangle((p(58), p(12), p(70), p(66)), radius=p(6), fill=255)
    save(alpha, 128, 128, "power.png")
    # Toggles of settings.
    alpha, draw = canvas(72, 40)
    draw.rounded_rectangle((0, 0, p(72) - 1, p(40) - 1), radius=p(20), fill=255)
    draw.ellipse((p(36), p(4), p(68), p(36)), fill=0)
    save(alpha, 72, 40, "toggle-on-mask.png")
    on = Image.new("RGBA", (72, 40), (0, 0, 0, 0))
    track = Image.new("RGBA", (72, 40), tuple(int(ACCENT[i:i + 2], 16) for i in (2, 4, 6)) + (255,))
    knob_alpha, knob_draw = canvas(72, 40)
    knob_draw.ellipse((p(36), p(4), p(68), p(36)), fill=255)
    track_alpha, track_draw = canvas(72, 40)
    track_draw.rounded_rectangle((0, 0, p(72) - 1, p(40) - 1), radius=p(20), fill=255)
    on = Image.composite(track, on, track_alpha.resize((72, 40), Image.LANCZOS))
    on = Image.composite(Image.new("RGBA", (72, 40), (255, 255, 255, 255)), on, knob_alpha.resize((72, 40), Image.LANCZOS))
    on.save(os.path.join(MEDIA, "toggle-on.png"))
    os.remove(os.path.join(MEDIA, "toggle-on-mask.png"))
    alpha, draw = canvas(72, 40)
    draw.rounded_rectangle((0, 0, p(72) - 1, p(40) - 1), radius=p(20), outline=255, width=p(4))
    draw.ellipse((p(8), p(8), p(32), p(32)), fill=255)
    save(alpha, 72, 40, "toggle-off.png")
    # Chevrons of choices.
    for name, points in (("chevron-left.png", [(40, 16), (24, 32), (40, 48)]), ("chevron-right.png", [(24, 16), (40, 32), (24, 48)])):
        alpha, draw = canvas(64, 64)
        draw.line([(p(x), p(y)) for x, y in points], fill=255, width=p(7), joint="curve")
        for x, y in (points[0], points[2]):
            draw.ellipse((p(x) - p(3.5), p(y) - p(3.5), p(x) + p(3.5), p(y) + p(3.5)), fill=255)
        save(alpha, 64, 64, name)
    # Slider bar and nib.
    alpha, draw = canvas(32, 32)
    draw.rounded_rectangle((0, p(12), p(32) - 1, p(20)), radius=p(4), fill=255)
    save(alpha, 32, 32, "slider-bar.png")
    alpha, draw = canvas(32, 32)
    draw.ellipse((p(4), p(4), p(28), p(28)), fill=255)
    save(alpha, 32, 32, "slider-nib.png")
    # Folder of the file browser.
    alpha, draw = canvas(128, 128)
    draw.rounded_rectangle((p(10), p(24), p(58), p(44)), radius=p(8), fill=255)
    draw.rounded_rectangle((p(10), p(34), p(118), p(104)), radius=p(10), fill=255)
    save(alpha, 128, 128, "folder.png")
    # Busy spinner: three quarters of a ring.
    alpha, draw = canvas(128, 128)
    draw.arc((p(12), p(12), p(116), p(116)), start=0, end=270, fill=255, width=p(12))
    save(alpha, 128, 128, "spinner.png")
    # Mouse pointer: an arrow with a dark outline.
    arrow = [(4, 4), (4, 40), (14, 31), (21, 46), (28, 43), (21, 28), (34, 28)]
    pointer_image = Image.new("RGBA", (40 * K, 48 * K), (0, 0, 0, 0))
    draw = ImageDraw.Draw(pointer_image)
    draw.polygon([(p(x), p(y)) for x, y in arrow], fill=(255, 255, 255, 255), outline=(14, 15, 17, 255), width=p(2))
    pointer_image.resize((40, 48), Image.LANCZOS).save(os.path.join(MEDIA, "pointer.png"))


def language(code, index):
    lines = ['# Monteiro skin language file', 'msgid ""', 'msgstr ""', '"Language: %s\\n"' % code, ""]
    for number, values in STRINGS.items():
        lines += ['msgctxt "#%d"' % number, 'msgid "%s"' % values[0], 'msgstr "%s"' % ("" if index == 0 else values[index]), ""]
    return "\n".join(lines)


EXTRA_STRINGS = {31013: ("Monteiro", "Monteiro"), 31014: ("items", "itens"), 31015: ("Space", "Espaço"), 31016: ("Delete", "Apagar"),
                 31017: ("Shift", "Shift"), 31021: ("Show", "Mostrar")}


def main():
    noto = sys.argv[1]
    STRINGS.update(EXTRA_STRINGS)
    os.makedirs(XML, exist_ok=True)
    files = {
        "Startup.xml": startup(),
        "Home.xml": home(),
        "Pointer.xml": pointer(),
        "Font.xml": fonts(),
        "Defaults.xml": defaults(),
        # Kodi reads Includes.xml first. It brings in the default look of the controls.
        "Includes.xml": '<?xml version="1.0" encoding="utf-8"?>\n<!-- Generated by tools/%s. -->\n<includes>\n  <include file="Defaults.xml" />\n</includes>\n' % GENERATOR,
        "DialogConfirm.xml": confirm(),
        "DialogContextMenu.xml": context_menu(),
        "DialogNotification.xml": notification(),
        "DialogBusy.xml": busy(),
        "DialogExtendedProgressBar.xml": extended_progress(),
        "DialogKeyboard.xml": keyboard(),
        "DialogNumeric.xml": numeric(),
        "DialogSelect.xml": select(),
        "DialogTextViewer.xml": text_viewer(),
        "DialogSettings.xml": settings_dialog("Settings dialogs, such as the video and audio settings.", False,
                                              [(28, "$LOCALIZE[186]"), (29, "$LOCALIZE[222]"), (30, "$LOCALIZE[409]")], level=False),
        "SettingsCategory.xml": settings_dialog("The settings of Kodi, by section and category.", True, [], heading_id=2),
        "DialogAddonSettings.xml": settings_dialog("Add-on settings.", True,
                                                   [(28, "$LOCALIZE[186]"), (29, "$LOCALIZE[222]"), (30, "$LOCALIZE[409]")]),
        "Settings.xml": settings_menu(),
        "AddonBrowser.xml": addon_browser(),
        "DialogAddonInfo.xml": addon_info(),
        "FileBrowser.xml": file_browser(),
        "DialogButtonMenu.xml": power_menu(),
        "Custom_1100_PowerMenu.xml": power_menu(own=True),
        "VideoFullScreen.xml": video_full_screen(),
        "DialogSeekBar.xml": seek_bar(),
        "VideoOSD.xml": video_osd(),
        "DialogVolumeBar.xml": volume_bar(),
    }
    for name, content in files.items():
        with open(os.path.join(XML, name), "w", encoding="utf-8") as output:
            output.write(content)
    # Kodi looks for color files in the colors folder. The skin sets its colors in each control.
    os.makedirs(os.path.join(SKIN, "colors"), exist_ok=True)
    with open(os.path.join(SKIN, "colors", "defaults.xml"), "w", encoding="utf-8") as output:
        output.write('<?xml version="1.0" encoding="utf-8"?>\n<colors />\n')
    fonts_folder = os.path.join(SKIN, "fonts")
    os.makedirs(fonts_folder, exist_ok=True)
    for name in ("NotoSans-Regular.ttf", "NotoSans-Bold.ttf", "OFL.txt"):
        shutil.copy2(os.path.join(noto, name), os.path.join(fonts_folder, name))
    for code, folder, index in (("en_GB", "resource.language.en_gb", 0), ("pt_BR", "resource.language.pt_br", 1)):
        # Kodi reads the strings of a skin from its language folder.
        path = os.path.join(SKIN, "language", folder)
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "strings.po"), "w", encoding="utf-8") as output:
            output.write(language(code, index))
    media()


if __name__ == "__main__":
    main()
