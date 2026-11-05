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
    31018: ("Videos", "Vídeos"),
    31019: ("Music", "Música"),
    31020: ("Pictures", "Imagens"),
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
    # Kodi draws a selected item with selectedcolor, white by default, which vanishes on a focused white row.
    return control("label", control_id, left=left, top=top, width=width, height=height, align=align, aligny="center", font=font,
                   textcolor=color, selectedcolor=color, scroll=scroll, wrapmultiline=wrap, label=text, visible=visible)


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
    <orientation>horizontal</orientation>
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
  <top>300</top>
  <width>%d</width>
  <height>%d</height>
  <orientation>horizontal</orientation>
  <scrolltime>0</scrolltime>
  <onup>9100</onup>
  <ondown>9200</ondown>
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
        label(left, 640, width, 50, "$INFO[Container(9000).ListItem.Label2]", "font14", TEXT2, align="center"),
        shortcuts(),
        label(left, 990, width, 40, "$INFO[System.Date]", "font12", TEXT3, align="center"),
        *top_buttons,
    ], default=9000, extra="<menucontrol>9000</menucontrol>\n<backgroundcolor>%s</backgroundcolor>" % BG)


SHORTCUTS = [(31018, "film.png", "ActivateWindow(Videos,sources://video/,return)", None),
             (31019, "audio.png", "ActivateWindow(Music,sources://music/,return)", None),
             (31020, "folder.png", "ActivateWindow(Pictures,sources://pictures/,return)", None),
             (31031, "folder.png", "RunAddon(script.easy.files)", "System.HasAddon(script.easy.files)")]


def shortcuts():
    """Videos, music and pictures of Kodi, in a smaller row under the add-ons."""
    pill, gap = 300, 24
    width = len(SHORTCUTS) * (pill + gap)
    focus = "Control.HasFocus(9200)"
    def parts(focused, condition=None):
        return [panel(0, 0, pill, 90, FOCUS if focused else SURFACE, condition),
                image(28, 25, 40, 40, "$INFO[ListItem.Icon]", ON_FOCUS if focused else TEXT2, condition),
                label(88, 0, pill - 110, 90, "$INFO[ListItem.Label]", "font13", ON_FOCUS if focused else TEXT, visible=condition)]
    items = "\n".join("<item>\n  <label>$LOCALIZE[%d]</label>\n  <icon>%s</icon>\n  <onclick>%s</onclick>%s\n</item>"
                      % (label_id, icon, action, "\n  <visible>%s</visible>" % condition if condition else "")
                      for label_id, icon, action, condition in SHORTCUTS)
    return '''<control type="list" id="9200">
  <left>%d</left>
  <top>760</top>
  <width>%d</width>
  <height>90</height>
  <orientation>horizontal</orientation>
  <scrolltime>0</scrolltime>
  <onup>9000</onup>
  <ondown>noop</ondown>
  <onleft>noop</onleft>
  <onright>noop</onright>
  <itemlayout width="%d" height="90">
%s
  </itemlayout>
  <focusedlayout width="%d" height="90">
%s
  </focusedlayout>
  <content>
%s
  </content>
</control>''' % ((1920 - width + gap) // 2, width, pill + gap, indent("\n".join(parts(False)), 4), pill + gap,
                  indent("\n".join(parts(True, focus) + parts(False, "!" + focus)), 4), indent(items, 4))


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
    # A row of buttons is centered. A column starts at the top, so the controls under it stay clear.
    horizontal = orientation == "horizontal"
    return control("grouplist", control_id, left=left, top=top, width=width, height=76 if horizontal else len(buttons) * 96,
                   orientation=orientation, align="center" if horizontal else None, itemgap=20, onup=nav.get("up"), ondown=nav.get("down"),
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
    # Kodi writes the heading in control 1 and the number being typed in control 4.
    controls = [dim(), *dialog_frame(left, top, 700, 760, heading_id=1),
                label(left + 40, top + 120, 620, 60, "", "font36_title", control_id=4, align="center")]
    # A label made only of a number is read as the number of a string, so the digits are written in bold tags.
    keys = [(11, "1"), (12, "2"), (13, "3"), (14, "4"), (15, "5"), (16, "6"), (17, "7"), (18, "8"), (19, "9"), (20, "‹"), (10, "0"), (22, "›")]
    keys = [(control_id, "[B]%s[/B]" % text) for control_id, text in keys]
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
               # Easy Files replaces the file manager of Kodi when it is installed.
               ("$LOCALIZE[7]", "RunAddon(script.easy.files)", "System.HasAddon(script.easy.files)"),
               ("$LOCALIZE[7]", "ActivateWindow(filemanager)", "!System.HasAddon(script.easy.files)"),
               ("$LOCALIZE[130]", "ActivateWindow(systeminfo)", None), ("$LOCALIZE[13200]", "ActivateWindow(Profiles)", None),
               ("$LOCALIZE[14111]", "ActivateWindow(eventlog)", "!System.HasAddon(service.libreelec.settings)"),
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
    # Kodi opens this window by itself while its condition holds, so the condition is on the window.
    shown = "[Player.Seeking | Player.DisplayAfterSeek | Player.Paused | Player.Forwarding | Player.Rewinding] + !Window.IsActive(videoosd)"
    return window("Time bar while seeking or paused, for videos outside the Easy add-ons.", [
        image(0, 760, 1920, 320, "shade.png", "F2000000"),
        label(120, 880, 1200, 50, "$INFO[Player.Title]", "font30_title"),
        label(120, 930, 600, 40, "$INFO[Player.Time]", "font12", TEXT),
        label(1200, 930, 600, 40, "$INFO[Player.Duration]", "font12", TEXT2, align="right"),
        control("progress", left=120, top=980, width=1680, height=8, info="Player.Progress",
                texturebg=('colordiffuse="4DFFFFFF"', "white.png"), midtexture=('colordiffuse="%s"' % ACCENT, "white.png")),
        label(120, 1000, 1680, 40, "$INFO[Player.SeekOffset]", "font12", TEXT2, control_id=40000),
        control("slider", 401, left=-2000, top=0, width=10, height=10),
        control("slider", 403, left=-2000, top=0, width=10, height=10),
    ], extra=fade() + "\n<visible>%s</visible>\n<depth>DepthOSD</depth>" % shown)


def video_osd():
    # Round icon buttons, as in the player of Easy Movie. Buttons cannot hold images, so the icons are drawn over them.
    size, gap, top = 104, 40, 900
    buttons = [(600, "back10.png", "Seek(-10)"), (601, None, "PlayerControl(Play)"), (602, "forward10.png", "Seek(10)"),
               (603, "stop.png", "PlayerControl(Stop)")]
    left = (1920 - len(buttons) * size - (len(buttons) - 1) * gap) // 2
    controls = []
    for index, (control_id, icon, action) in enumerate(buttons):
        x = left + index * (size + gap)
        nav = {"left": buttons[index - 1][0] if index else buttons[-1][0], "right": buttons[(index + 1) % len(buttons)][0]}
        if icon:
            controls += round_button(control_id, x, top, icon, action, size, nav)
        else:
            parts = round_button(control_id, x, top, "pause.png", action, size, nav)
            controls += [parts[0]] + [part.replace("</visible>", " + !Player.Paused</visible>") for part in parts[1:]]
            controls += [part.replace("pause.png", "player_play.png").replace("</visible>", " + Player.Paused</visible>")
                         for part in round_button(control_id, x, top, "pause.png", action, size, nav)[1:]]
    return window("Player controls for videos outside the Easy add-ons. Easy Movie shows its own.", [
        image(0, 640, 1920, 440, "shade.png", "F2000000"),
        label(120, 680, 1680, 60, "$INFO[Player.Title]", "font36_title"),
        label(120, 760, 600, 40, "$INFO[Player.Time]", "font12"),
        label(1200, 760, 600, 40, "$INFO[Player.Duration]", "font12", TEXT2, align="right"),
        control("progress", left=120, top=810, width=1680, height=8, info="Player.Progress",
                texturebg=('colordiffuse="4DFFFFFF"', "white.png"), midtexture=('colordiffuse="%s"' % ACCENT, "white.png")),
        *controls,
    ], default=601, extra=fade() + "\n<depth>DepthOSD</depth>")


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

def media_rows(control_id, left, top, width, height, onleft=None, onright=None, fallback="folder.png"):
    """A list of files or library items: a picture, the name and details. It looks focused only while focused."""
    focus = "Control.HasFocus(%d)" % control_id
    def row(focused, condition=None):
        return [panel(0, 0, width, 100, FOCUS if focused else RAISED, condition) if condition or focused else "",
                image(16, 10, 80, 80, "$INFO[ListItem.Icon]", visible=condition, keep=True, fallback=fallback),
                label(120, 4, width - 400, 56, "$INFO[ListItem.Label]", "font13", ON_FOCUS if focused else TEXT, visible=condition),
                label(120, 52, width - 400, 40, "$INFO[ListItem.Label2]", "font12", ON_FOCUS2 if focused else TEXT2, visible=condition),
                image(width - 60, 32, 36, 36, "check.png", ON_FOCUS if focused else ACCENT,
                      "ListItem.IsSelected" + (" + " + condition if condition else ""))]
    focused_parts = row(True, focus) + row(False, "!" + focus)
    return '''<control type="list" id="%d">
  <left>%d</left>
  <top>%d</top>
  <width>%d</width>
  <height>%d</height>
  <onleft>%s</onleft>
  <onright>%s</onright>
  <pagecontrol>60</pagecontrol>
  <scrolltime>120</scrolltime>
  <viewtype label="535">list</viewtype>
  <itemlayout height="108" width="%d">
%s
  </itemlayout>
  <focusedlayout height="108" width="%d">
%s
  </focusedlayout>
</control>''' % (control_id, left, top, width, height, onleft or "noop", onright or "noop", width,
                  indent("\n".join(part for part in row(False) if part), 4), width,
                  indent("\n".join(part for part in focused_parts if part), 4))


def media_window(comment, icon):
    """Videos, music and pictures: the folder or library section shown as a list."""
    return window(comment, [
        image(0, 0, 1920, 1080, "white.png", BG),
        image(64, 48, 64, 64, icon, TEXT2),
        # At the root of a section Kodi gives no folder name, so the name of the window shows instead.
        label(148, 44, 1300, 72, "$INFO[Container.FolderName]", "font45_title", visible="!String.IsEmpty(Container.FolderName)"),
        label(148, 44, 1300, 72, "$INFO[System.CurrentWindow]", "font45_title", visible="String.IsEmpty(Container.FolderName)"),
        label(1300, 44, 560, 72, "$INFO[Container.NumItems] $LOCALIZE[31014]", "font13", TEXT2, align="right"),
        label(64, 120, 1792, 40, "$INFO[Container.FolderPath]", "font12", TEXT3, scroll="true"),
        panel(40, 170, 1840, 880, SURFACE),
        media_rows(50, 60, 190, 1780, 840, onright=60),
        control("scrollbar", 60, left=1856, top=190, width=8, height=840, onleft=50, onright=50),
    ], default=50, extra="<views>50</views>")


def file_manager():
    side = lambda control_id, left, path_id, scroll_id, other: [
        panel(left, 140, 880, 900, SURFACE),
        label(left + 24, 150, 832, 50, "", "font12", TEXT2, control_id=path_id, scroll="true"),
        media_rows(control_id, left + 20, 210, 820, 810, onleft=other, onright=other),
        control("scrollbar", scroll_id, left=left + 852, top=210, width=8, height=810, onleft=control_id, onright=control_id)]
    return window("File manager: two folders side by side, for copying and moving files.", [
        image(0, 0, 1920, 1080, "white.png", BG),
        label(64, 44, 1300, 72, "$LOCALIZE[7]", "font45_title"),
        *side(20, 60, 101, 60, 21), *side(21, 980, 102, 61, 20),
    ], default=20)


def media_source():
    left, top, width, height = 260, 100, 1400, 880
    paths = '''<control type="list" id="10">
  <left>%d</left>
  <top>%d</top>
  <width>980</width>
  <height>300</height>
  <onright>9000</onright>
  <ondown>12</ondown>
  <pagecontrol>60</pagecontrol>
  <itemlayout height="76" width="980">
%s
  </itemlayout>
  <focusedlayout height="76" width="980">
%s
  </focusedlayout>
</control>''' % (left + 40, top + 170, indent(label(20, 0, 940, 76, "$INFO[ListItem.Label]", "font13", TEXT), 4),
                  indent("\n".join([panel(0, 0, 980, 72, FOCUS, "Control.HasFocus(10)"), panel(0, 0, 980, 72, RAISED, "!Control.HasFocus(10)"),
                                    label(20, 0, 940, 72, "$INFO[ListItem.Label]", "font13", ON_FOCUS, visible="Control.HasFocus(10)"),
                                    label(20, 0, 940, 72, "$INFO[ListItem.Label]", "font13", TEXT, visible="!Control.HasFocus(10)")]), 4))
    return window("Adding or editing a media source: its paths and its name.", [
        dim(), *dialog_frame(left, top, width, height, heading=""),
        label(left + 40, top + 24, width - 80, 60, "$LOCALIZE[31023]", "font32_title"),
        image(left + 24, top + 96, width - 48, 2, "white.png", RAISED),
        label(left + 40, top + 116, 980, 44, "$LOCALIZE[1021]", "font12", TEXT2),
        paths,
        control("scrollbar", 60, left=left + 1030, top=top + 170, width=8, height=300, onleft=10, onright=9000),
        dialog_buttons(9000, left + 1080, top + 170, 280, [(11, "$LOCALIZE[1024]"), (13, "$LOCALIZE[15019]"), (14, "$LOCALIZE[1210]")],
                       "vertical", 280, nav={"left": 10, "down": 12}),
        label(left + 40, top + 500, 980, 44, "$LOCALIZE[1022]", "font12", TEXT2),
        control("edit", 12, left=left + 40, top=top + 550, width=width - 80, height=80, onup=10, ondown=9001, font="font13",
                textcolor=TEXT, focusedcolor=ON_FOCUS, textoffsetx=30, aligny="center",
                texturefocus=('border="16" colordiffuse="%s"' % FOCUS, "panel.png"),
                texturenofocus=('border="16" colordiffuse="%s"' % RAISED, "panel.png")),
        dialog_buttons(9001, left, top + height - 116, width, [(18, "$LOCALIZE[186]"), (19, "$LOCALIZE[222]")], nav={"up": 12}),
    ], default=10, extra=pop())


def system_info():
    buttons = [(95, 20037), (94, 13277), (96, 13279), (97, 13280), (98, 13281), (99, 19191), (100, 12389), (101, 12396)]
    return window("System information, by category.", [
        image(0, 0, 1920, 1080, "white.png", BG),
        image(64, 48, 64, 64, "gear.png", TEXT2),
        label(148, 44, 1000, 72, "$LOCALIZE[130]", "font45_title"),
        control("grouplist", 9000, left=60, top=160, width=460, height=880, itemgap=10, onright=30,
                children=[button(cid, 0, 0, 460, 76, "$LOCALIZE[%d]" % string_id, align="left") for cid, string_id in buttons]),
        panel(560, 150, 1300, 890, SURFACE),
        label(600, 170, 1220, 50, "", "font30_title", control_id=53),
        *[label(600, 230 + index * 56, 1220, 52, "", "font13", TEXT2, control_id=control_id) for index, control_id in enumerate(range(2, 14))],
        control("textbox", 30, left=600, top=230, width=1220, height=780, font="font13", textcolor=TEXT2, pagecontrol=60),
        control("scrollbar", 60, left=1836, top=230, width=8, height=780, onleft=9000),
    ], default=95)


def slide_show():
    # Kodi draws the pictures. The name of the picture shows while it is paused.
    return window("Picture slide show.", [
        group(0, 0, 1920, 1080, [image(0, 900, 1920, 180, "shade.png", "F2000000"),
                                 label(120, 980, 1680, 60, "$INFO[Slideshow.Filename]", "font30_title")],
              visible="Slideshow.IsPaused"),
    ])


def music_visualisation():
    return window("Music playback with its visualisation.", [
        control("visualisation", 2, left=0, top=0, width=1920, height=1080),
        image(0, 760, 1920, 320, "shade.png", "F2000000"),
        label(120, 860, 1680, 60, "$INFO[MusicPlayer.Title]", "font36_title"),
        label(120, 930, 1680, 44, "$INFO[MusicPlayer.Artist]  ·  $INFO[MusicPlayer.Album]", "font13", TEXT2),
        label(120, 990, 600, 40, "$INFO[Player.Time]", "font12"),
        label(1200, 990, 600, 40, "$INFO[Player.Duration]", "font12", TEXT2, align="right"),
        control("progress", left=120, top=1036, width=1680, height=8, info="Player.Progress",
                texturebg=('colordiffuse="4DFFFFFF"', "white.png"), midtexture=('colordiffuse="%s"' % ACCENT, "white.png")),
    ])


# Details and other windows --------------------------------------------------------------------------------------------

def info_dialog(comment, buttons, extra_rows=(), poster="$INFO[ListItem.Art(poster)]", default=8):
    """Details of a video, a song or a TV programme: the picture, the title, details, the description and the actions.
    Kodi hides the buttons that do not apply."""
    left, top, width, height = 110, 80, 1700, 920
    row = control("grouplist", 9000, left=left + 40, top=top + height - 116, width=width - 80, height=76, orientation="horizontal",
                  itemgap=12, children=[button(cid, 0, 0, 250, 76, text, "font12", offset=10) for cid, text in buttons])
    return window(comment, [
        dim(), *dialog_frame(left, top, width, height),
        panel(left + 40, top + 40, 380, 570, RAISED),
        image(left + 40, top + 40, 380, 570, poster, keep=True, fallback="$INFO[ListItem.Icon]"),
        label(left + 460, top + 40, width - 500, 70, "$INFO[ListItem.Label]", "font45_title"),
        *extra_rows,
        control("textbox", left=left + 460, top=top + 280, width=width - 500, height=480, font="font13", textcolor=TEXT2,
                label="$INFO[ListItem.Plot]", autoscroll=('time="3000" delay="6000" repeat="6000"', "true")),
        row,
    ], default=9000, extra=pop())


def details_line(top, text, color=TEXT2, font="font13"):
    return label(110 + 460, 80 + top, 1700 - 500, 44, text, font, color)


def video_info():
    return info_dialog("Details of a video of the library.", [(8, ""), (11, "$LOCALIZE[20410]"), (10, "$LOCALIZE[13511]"), (6, "$LOCALIZE[184]")], [
        details_line(120, "$INFO[ListItem.Year]$INFO[ListItem.Duration,  ·  , min]$INFO[ListItem.Rating,  ·  IMDb ]"),
        details_line(170, "$INFO[ListItem.Genre]", ACCENT),
        details_line(220, "$INFO[ListItem.Director]", TEXT3, "font12")])


def music_info():
    return info_dialog("Details of an album or an artist.", [(8, "$LOCALIZE[208]"), (6, "$LOCALIZE[184]"), (10, "$LOCALIZE[13405]"), (12, "")], [
        details_line(120, "$INFO[ListItem.Artist]$INFO[ListItem.Year,  ·  ]"),
        details_line(170, "$INFO[ListItem.Genre]", ACCENT)], poster="$INFO[ListItem.Art(thumb)]", default=8)


def pvr_info():
    return info_dialog("Details of a TV programme.", [(5, "$LOCALIZE[19165]"), (6, ""), (9, "$LOCALIZE[19061]"), (10, "$LOCALIZE[19190]"),
                                                      (8, "$LOCALIZE[19687]"), (11, "$LOCALIZE[826]"), (4, "$LOCALIZE[19003]")], [
        details_line(120, "$INFO[ListItem.ChannelName]  ·  $INFO[ListItem.StartTime] - $INFO[ListItem.EndTime]"),
        details_line(170, "$INFO[ListItem.Genre]", ACCENT)], poster="$INFO[ListItem.Icon]", default=5)


def picture_info():
    row = lambda focused: "\n".join([
        panel(0, 0, 1200, 64, FOCUS) if focused else "",
        label(24, 0, 400, 64, "$INFO[ListItem.Label]", "font12", ON_FOCUS2 if focused else TEXT2),
        label(440, 0, 740, 64, "$INFO[ListItem.Label2]", "font12", ON_FOCUS if focused else TEXT)])
    details = '''<control type="list" id="5">
  <left>360</left>
  <top>230</top>
  <width>1200</width>
  <height>700</height>
  <pagecontrol>60</pagecontrol>
  <itemlayout height="66" width="1200">
%s
  </itemlayout>
  <focusedlayout height="66" width="1200">
%s
  </focusedlayout>
</control>''' % (indent(row(False), 4), indent(row(True), 4))
    return window("Details of a picture.", [dim(), *dialog_frame(320, 110, 1280, 860, heading=""),
                                             label(360, 134, 1200, 60, "$INFO[ListItem.Label]", "font32_title"),
                                             image(344, 206, 1232, 2, "white.png", RAISED), details,
                                             control("scrollbar", 60, left=1576, top=230, width=8, height=700, onleft=5),
                                             control("group", 9000, left=0, top=0, width=1, height=1)], default=5, extra=pop())


def profiles():
    tile = 260
    layout = lambda focused: "\n".join([panel(0, 0, tile - 20, tile + 60, FOCUS if focused else SURFACE),
                                        image(40, 30, tile - 100, tile - 100, "$INFO[ListItem.Icon]", keep=True, fallback="logo.png"),
                                        label(10, tile - 50, tile - 40, 60, "$INFO[ListItem.Label]", "font13", ON_FOCUS if focused else TEXT,
                                              align="center")])
    grid = '''<control type="panel" id="2">
  <left>160</left>
  <top>220</top>
  <width>1600</width>
  <height>620</height>
  <orientation>vertical</orientation>
  <ondown>9001</ondown>
  <itemlayout width="%d" height="%d">
%s
  </itemlayout>
  <focusedlayout width="%d" height="%d">
%s
  </focusedlayout>
</control>''' % (tile, tile + 80, indent(layout(False), 4), tile, tile + 80, indent(layout(True), 4))
    return window("Profiles.", [
        image(0, 0, 1920, 1080, "white.png", BG),
        label(64, 44, 1300, 72, "$LOCALIZE[13200]", "font45_title"),
        grid,
        control("grouplist", 9001, left=160, top=900, width=1600, height=80, orientation="horizontal", itemgap=20, onup=2, children=[
            control("radiobutton", 4, width=640, height=76, label="$LOCALIZE[31024]",
                    texturenofocus=('border="16" colordiffuse="%s"' % RAISED, "panel.png")),
            button(5, 0, 0, 860, 76, "$LOCALIZE[31025]", align="left").replace("<label>", "<label2>[B]$INFO[System.ProfileAutoLogin][/B]</label2>\n  <label>")]),
    ], default=2)


def login_screen():
    tile = 300
    layout = lambda focused: "\n".join([panel(0, 0, tile - 24, tile + 40, FOCUS if focused else SURFACE),
                                        image(48, 36, tile - 120, tile - 120, "$INFO[ListItem.Icon]", keep=True, fallback="logo.png"),
                                        label(10, tile - 40, tile - 44, 60, "$INFO[ListItem.Label]", "font13", ON_FOCUS if focused else TEXT,
                                              align="center")])
    users = '''<control type="fixedlist" id="52">
  <left>210</left>
  <top>340</top>
  <width>1500</width>
  <height>%d</height>
  <orientation>horizontal</orientation>
  <focusposition>2</focusposition>
  <ondown>20</ondown>
  <itemlayout width="%d" height="%d">
%s
  </itemlayout>
  <focusedlayout width="%d" height="%d">
%s
  </focusedlayout>
</control>''' % (tile + 40, tile, tile + 40, indent(layout(False), 4), tile, tile + 40, indent(layout(True), 4))
    return window("Choosing a profile when Kodi starts.", [
        image(0, 0, 1920, 1080, "white.png", BG),
        image(0, 0, 1920, 1080, "fanart.jpg", "40FFFFFF"),
        image(64, 48, 64, 64, "logo.png"),
        label(148, 44, 900, 72, "Monteiro", "font45_title"),
        label(210, 240, 1500, 60, "$LOCALIZE[13200]", "font32_title", align="center"),
        users,
        *round_button(20, 924, 800, "power.png", "ActivateWindow(%d)" % POWER_WINDOW, nav={"up": 52}),
    ], default=52)


def slider_dialog():
    return window("A value chosen with a slider, such as the audio delay.", [
        group(460, 820, 1000, 200, [
            panel(0, 0, 1000, 200, SURFACE),
            label(40, 20, 700, 50, "", "font13", control_id=10),
            label(740, 20, 220, 50, "", "font13", ACCENT, control_id=12, align="right"),
            control("slider", 11, left=40, top=110, width=920, height=24, onleft=11, onright=11, orientation="horizontal",
                    texturesliderbar=('border="4" colordiffuse="%s"' % RAISED2, "slider-bar.png"),
                    textureslidernib=('colordiffuse="%s"' % ACCENT, "slider-nib.png"),
                    textureslidernibfocus=('colordiffuse="%s"' % ACCENT, "slider-nib.png")),
            control("button", 13, left=-2000, top=0, width=10, height=10),
            control("button", 14, left=-2000, top=0, width=10, height=10),
        ]),
    ], default=11, extra=fade())


def subtitle_search():
    """Subtitle search of the subtitle add-ons of Kodi: the services on the left, the subtitles found on the right."""
    service = lambda focused: "\n".join([panel(0, 0, 440, 72, FOCUS) if focused else "",
                                         label(24, 0, 400, 72, "$INFO[ListItem.Label]", "font13", ON_FOCUS if focused else TEXT)])
    result = lambda focused: "\n".join([panel(0, 0, 1040, 90, FOCUS) if focused else "",
                                        label(24, 4, 990, 46, "$INFO[ListItem.Label2]", "font13", ON_FOCUS if focused else TEXT),
                                        label(24, 46, 990, 40, "$INFO[ListItem.Label]", "font12", ON_FOCUS2 if focused else TEXT2)])
    def listing(control_id, left, width, height_item, layout, onleft, onright):
        return '''<control type="list" id="%d">
  <left>%d</left>
  <top>230</top>
  <width>%d</width>
  <height>720</height>
  <onleft>%s</onleft>
  <onright>%s</onright>
  <pagecontrol>73</pagecontrol>
  <itemlayout height="%d" width="%d">
%s
  </itemlayout>
  <focusedlayout height="%d" width="%d">
%s
  </focusedlayout>
</control>''' % (control_id, left, width, onleft, onright, height_item, width, indent(layout(False), 4), height_item, width,
                  indent(layout(True), 4))
    return window("Subtitle search of the subtitle add-ons.", [
        dim(), *dialog_frame(100, 80, 1720, 920, heading=""),
        label(140, 104, 1100, 60, "$LOCALIZE[287]", "font32_title"),
        image(1600, 104, 160, 60, "", keep=True).replace('<control type="image">', '<control type="image" id="110">'),
        label(140, 104, 1620, 60, "", "font12", TEXT2, control_id=100, align="right"),
        image(124, 176, 1672, 2, "white.png", RAISED),
        listing(150, 140, 440, 76, service, "noop", 120),
        listing(120, 620, 1040, 96, result, 150, 73),
        control("scrollbar", 73, left=1680, top=230, width=8, height=720, onleft=120),
        label(620, 230, 1040, 60, "", "font13", TEXT2, control_id=140),
        control("grouplist", 130, left=140, top=900, width=440, height=76, children=[button(160, 0, 0, 440, 76, "$LOCALIZE[24121]")]),
    ], default=150, extra=pop())


def music_osd():
    size, gap, top = 104, 40, 900
    buttons = [(600, "back10.png", "PlayerControl(Previous)"), (601, None, "PlayerControl(Play)"), (602, "forward10.png", "PlayerControl(Next)"),
               (603, "stop.png", "PlayerControl(Stop)")]
    left = (1920 - len(buttons) * size - (len(buttons) - 1) * gap) // 2
    controls = []
    for index, (control_id, icon, action) in enumerate(buttons):
        x = left + index * (size + gap)
        nav = {"left": buttons[index - 1][0] if index else buttons[-1][0], "right": buttons[(index + 1) % len(buttons)][0]}
        if icon:
            controls += round_button(control_id, x, top, icon, action, size, nav)
        else:
            parts = round_button(control_id, x, top, "pause.png", action, size, nav)
            controls += [parts[0]] + [part.replace("</visible>", " + !Player.Paused</visible>") for part in parts[1:]]
            controls += [part.replace("pause.png", "player_play.png").replace("</visible>", " + Player.Paused</visible>") for part in parts[1:]]
    return window("Music player controls.", [
        image(0, 640, 1920, 440, "shade.png", "F2000000"),
        label(120, 690, 1680, 60, "$INFO[MusicPlayer.Title]", "font36_title"),
        label(120, 750, 1680, 44, "$INFO[MusicPlayer.Artist]", "font13", TEXT2),
        label(120, 800, 600, 40, "$INFO[Player.Time]", "font12"),
        label(1200, 800, 600, 40, "$INFO[Player.Duration]", "font12", TEXT2, align="right"),
        control("progress", left=120, top=850, width=1680, height=8, info="Player.Progress",
                texturebg=('colordiffuse="4DFFFFFF"', "white.png"), midtexture=('colordiffuse="%s"' % ACCENT, "white.png")),
        *controls,
    ], default=601, extra=fade() + "\n<depth>DepthOSD</depth>")


def process_info():
    rows = [("Video", "$INFO[Player.Process(videodecoder)]$INFO[Player.Process(pixformat),  ·  ]$INFO[Player.Process(videowidth),  ·  ]$INFO[Player.Process(videoheight),x]"),
            ("FPS", "$INFO[Player.Process(videofps)]"), ("Audio", "$INFO[Player.Process(audiodecoder)]$INFO[Player.Process(audiochannels),  ·  ]"),
            ("Deinterlace", "$INFO[Player.Process(deintmethod)]"), ("CPU", "$INFO[System.CpuUsage]")]
    return window("Information on the decoders of the video playing.", [
        group(60, 60, 900, 120 + 56 * len(rows), [panel(0, 0, 900, 120 + 56 * len(rows), "E617181B"),
                                                  label(30, 20, 840, 60, "$INFO[Player.Title]", "font30_title")] +
              [label(30, 90 + index * 56, 240, 50, name, "font12", TEXT3) for index, (name, _) in enumerate(rows)] +
              [label(280, 90 + index * 56, 590, 50, value, "font12", TEXT) for index, (_, value) in enumerate(rows)]),
        control("button", 5553, left=-2000, top=0, width=10, height=10),
    ], default=5553, extra=fade())


def full_screen_info():
    return window("Details of the video playing, with the Info key.", [
        image(0, 0, 1920, 1080, "white.png", "B3000000"),
        group(160, 120, 1600, 840, [
            panel(0, 0, 1600, 840, SURFACE),
            image(40, 40, 380, 570, "$INFO[VideoPlayer.Cover]", keep=True, fallback="film.png"),
            label(460, 40, 1100, 70, "$INFO[VideoPlayer.Title]", "font45_title"),
            label(460, 120, 1100, 44, "$INFO[VideoPlayer.Year]$INFO[VideoPlayer.Genre,  ·  ]", "font13", TEXT2),
            control("textbox", left=460, top=190, width=1100, height=600, font="font13", textcolor=TEXT2, label="$INFO[VideoPlayer.Plot]"),
        ]),
        control("button", 999, left=-2000, top=0, width=10, height=10, onclick="Action(close)"),
    ], default=999, extra=fade())


def simple_list_window(comment, icon, title, control_type="list"):
    """Favourites, the playlist and the event log: a title and a list."""
    window_xml = media_window(comment, icon)
    window_xml = window_xml.replace("$INFO[Container.FolderName]", title)
    if control_type != "list":
        window_xml = window_xml.replace('<control type="list" id="50">', '<control type="%s" id="50">' % control_type)
    return window_xml


# Live TV ----------------------------------------------------------------------------------------------------------------

def pvr_rows(control_id, left, top, width, height, onleft="noop", onright=60):
    """Channels, recordings, timers and search results: a logo, the name and the programme."""
    focus = "Control.HasFocus(%d)" % control_id
    def row(focused, condition=None):
        return [panel(0, 0, width, 96, FOCUS if focused else RAISED, condition) if condition or focused else "",
                label(16, 0, 90, 96, "$INFO[ListItem.ChannelNumberLabel]", "font13", ON_FOCUS2 if focused else TEXT3, align="right",
                      visible=condition),
                image(126, 12, 120, 72, "$INFO[ListItem.Icon]", keep=True, fallback="tv.png", visible=condition),
                label(270, 4, width - 300, 50, "$INFO[ListItem.Label]", "font13", ON_FOCUS if focused else TEXT, visible=condition),
                label(270, 50, width - 300, 40, "$INFO[ListItem.Title]$INFO[ListItem.StartTime,  ·  ]$INFO[ListItem.Date,  ·  ]", "font12",
                      ON_FOCUS2 if focused else TEXT2, visible=condition)]
    focused_parts = row(True, focus) + row(False, "!" + focus)
    return '''<control type="fixedlist" id="%d">
  <left>%d</left>
  <top>%d</top>
  <width>%d</width>
  <height>%d</height>
  <onleft>%s</onleft>
  <onright>%s</onright>
  <pagecontrol>%s</pagecontrol>
  <focusposition>2</focusposition>
  <movement>4</movement>
  <scrolltime>120</scrolltime>
  <viewtype label="535">list</viewtype>
  <itemlayout height="104" width="%d">
%s
  </itemlayout>
  <focusedlayout height="104" width="%d">
%s
  </focusedlayout>
</control>''' % (control_id, left, top, width, height, onleft, onright, onright, width,
                  indent("\n".join(part for part in row(False) if part), 4), width,
                  indent("\n".join(part for part in focused_parts if part), 4))


def pvr_window(comment, string_id):
    return window(comment, [
        image(0, 0, 1920, 1080, "white.png", BG),
        image(64, 48, 64, 64, "tv.png", TEXT2),
        label(148, 44, 1300, 72, "$LOCALIZE[%d]" % string_id, "font45_title"),
        label(1300, 44, 560, 72, "$INFO[Container.NumItems] $LOCALIZE[31014]", "font13", TEXT2, align="right"),
        label(64, 120, 900, 40, "", "font12", TEXT3, control_id=29),
        label(960, 120, 900, 40, "", "font12", TEXT3, control_id=30, align="right"),
        panel(40, 170, 1840, 880, SURFACE),
        pvr_rows(50, 60, 190, 1780, 840, onright=73),
        control("scrollbar", 73, left=1856, top=190, width=8, height=840, onleft=50),
    ], default=50, extra="<views>50</views>")


def pvr_guide():
    channel = lambda focused: "\n".join([panel(0, 2, 300, 58, FOCUS if focused else RAISED),
                                         label(16, 0, 268, 62, "$INFO[ListItem.ChannelNumberLabel]  $INFO[ListItem.Label]", "font12",
                                               ON_FOCUS if focused else TEXT)])
    # In a guide, Kodi stretches image 2 and label 1 of a programme to its length.
    programme = lambda focused: "\n".join([
        image(2, 2, 36, 58, "panel.png", FOCUS if focused else SURFACE, border=16).replace('<control type="image">', '<control type="image" id="2">'),
        label(14, 0, 26, 62, "$INFO[ListItem.Label]", "font12", ON_FOCUS if focused else TEXT2, control_id=1)])
    guide = '''<control type="epggrid" id="50">
  <left>60</left>
  <top>180</top>
  <width>1800</width>
  <height>860</height>
  <orientation>vertical</orientation>
  <pagecontrol>60</pagecontrol>
  <scrolltime tween="quadratic">300</scrolltime>
  <timeblocks>30</timeblocks>
  <rulerunit>6</rulerunit>
  <viewtype label="19029">list</viewtype>
  <progresstexture border="4" colordiffuse="%s">panel.png</progresstexture>
  <rulerlayout height="45" width="300">
%s
  </rulerlayout>
  <channellayout height="62" width="300">
%s
  </channellayout>
  <focusedchannellayout height="62" width="300">
%s
  </focusedchannellayout>
  <itemlayout height="62" width="40">
%s
  </itemlayout>
  <focusedlayout height="62" width="40">
%s
  </focusedlayout>
</control>''' % (ACCENT, indent(label(10, 0, 280, 45, "$INFO[ListItem.Label]", "font12", TEXT3), 4), indent(channel(False), 4),
                  indent(channel(True), 4), indent(programme(False), 4), indent(programme(True), 4))
    return window("TV guide: channels and their programmes over time.", [
        image(0, 0, 1920, 1080, "white.png", BG),
        image(64, 48, 64, 64, "tv.png", TEXT2),
        label(148, 44, 1300, 72, "$LOCALIZE[31027]", "font45_title"),
        label(1300, 44, 560, 72, "$INFO[ListItem.Title]", "font13", TEXT2, align="right"),
        label(64, 120, 900, 40, "", "font12", TEXT3, control_id=29),
        label(960, 120, 900, 40, "", "font12", TEXT3, control_id=30, align="right"),
        guide,
        control("scrollbar", 60, left=1880, top=180, width=8, height=860, onleft=50),
    ], default=50, extra="<views>50</views>")


def pvr_channels_osd(comment):
    return window(comment, [
        group(1180, 0, 740, 1080, [
            image(0, 0, 740, 1080, "white.png", SURFACE),
            label(40, 40, 660, 60, "", "font32_title", control_id=2),
            pvr_rows(11, 20, 130, 700, 900, onleft="noop", onright=60).replace("<pagecontrol>60</pagecontrol>", "<pagecontrol>60</pagecontrol>"),
            control("scrollbar", 60, left=724, top=130, width=8, height=900, onleft=11),
        ], animation='<animation effect="slide" start="740,0" end="0,0" time="240" tween="cubic" easing="out">WindowOpen</animation>\n'
                     '<animation effect="slide" start="0,0" end="740,0" time="200" tween="cubic" easing="in">WindowClose</animation>'),
    ], default=11)


# Textures ---------------------------------------------------------------------------------------------------------------

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
                          (movies, ["circle.png", "film.png", "puzzle.png", "audio.png", "shade.png", "back10.png", "forward10.png",
                                    "pause.png", "player_play.png"])):
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
    # Stop: a rounded square.
    alpha, draw = canvas(128, 128)
    draw.rounded_rectangle((p(30), p(30), p(98), p(98)), radius=p(12), fill=255)
    save(alpha, 128, 128, "stop.png")
    # Icons of notifications: information, warning and error.
    for name, shape in (("DefaultIconInfo.png", "info"), ("DefaultIconWarning.png", "warning"), ("DefaultIconError.png", "error")):
        alpha, draw = canvas(128, 128)
        if shape == "warning":
            draw.polygon([(p(64), p(10)), (p(122), p(114)), (p(6), p(114))], fill=255)
            draw.rounded_rectangle((p(58), p(44), p(70), p(84)), radius=p(6), fill=0)
            draw.ellipse((p(57), p(92), p(71), p(106)), fill=0)
        else:
            draw.ellipse((p(8), p(8), p(120), p(120)), fill=255)
            if shape == "info":
                draw.ellipse((p(56), p(30), p(72), p(46)), fill=0)
                draw.rounded_rectangle((p(57), p(56), p(71), p(98)), radius=p(7), fill=0)
            else:
                draw.line([(p(42), p(42)), (p(86), p(86))], fill=0, width=p(14))
                draw.line([(p(86), p(42)), (p(42), p(86))], fill=0, width=p(14))
        save(alpha, 128, 128, name)
        color = {"info": ACCENT, "warning": "FFFFC53D", "error": DANGER}[shape]
        icon = Image.open(os.path.join(MEDIA, name))
        tinted = Image.new("RGBA", icon.size, tuple(int(color[i:i + 2], 16) for i in (2, 4, 6)) + (255,))
        tinted.putalpha(icon.getchannel("A"))
        tinted.save(os.path.join(MEDIA, name))
    # Folder of the file browser.
    alpha, draw = canvas(128, 128)
    draw.rounded_rectangle((p(10), p(24), p(58), p(44)), radius=p(8), fill=255)
    draw.rounded_rectangle((p(10), p(34), p(118), p(104)), radius=p(10), fill=255)
    save(alpha, 128, 128, "folder.png")
    # Grey, as lists show it without a color of their own, in place of pictures that are missing.
    folder = Image.open(os.path.join(MEDIA, "folder.png"))
    grey = Image.new("RGBA", folder.size, tuple(int(TEXT2[i:i + 2], 16) for i in (2, 4, 6)) + (255,))
    grey.putalpha(folder.getchannel("A"))
    grey.save(os.path.join(MEDIA, "folder.png"))
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
                 31017: ("Shift", "Shift"), 31021: ("Show", "Mostrar"), 31023: ("Media source", "Fonte de mídia"),
                 31024: ("Show the profiles when Kodi starts", "Mostrar os perfis ao iniciar o Kodi"),
                 31025: ("Log in automatically", "Entrar automaticamente"), 31026: ("Channels", "Canais"), 31027: ("TV guide", "Guia de TV"),
                 31028: ("Recordings", "Gravações"), 31029: ("Timers", "Agendamentos"), 31030: ("Search", "Busca"),
                 31031: ("Files", "Arquivos")}


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
        "MyVideoNav.xml": media_window("Videos: sources, folders and the video library.", "film.png"),
        "MyMusicNav.xml": media_window("Music: sources, folders and the music library.", "audio.png"),
        "MyPics.xml": media_window("Pictures: sources and folders.", "folder.png"),
        "FileManager.xml": file_manager(),
        "DialogMediaSource.xml": media_source(),
        "SettingsSystemInfo.xml": system_info(),
        "SlideShow.xml": slide_show(),
        "MusicVisualisation.xml": music_visualisation(),
        "MusicOSD.xml": music_osd(),
        "DialogVideoInfo.xml": video_info(),
        "DialogMusicInfo.xml": music_info(),
        "DialogPictureInfo.xml": picture_info(),
        "DialogPVRInfo.xml": pvr_info(),
        "SettingsProfile.xml": profiles(),
        "LoginScreen.xml": login_screen(),
        "DialogSlider.xml": slider_dialog(),
        "DialogSubtitles.xml": subtitle_search(),
        "DialogPlayerProcessInfo.xml": process_info(),
        "DialogFullScreenInfo.xml": full_screen_info(),
        "MyFavourites.xml": simple_list_window("Favourites.", "check.png", "$LOCALIZE[1036]"),
        "MyPlaylist.xml": simple_list_window("The playlist playing.", "film.png", "$LOCALIZE[13350]"),
        "EventLog.xml": simple_list_window("Event log.", "gear.png", "$LOCALIZE[14111]"),
        "MyGames.xml": media_window("Games: sources and folders.", "puzzle.png"),
        "MyPVRChannels.xml": pvr_window("Live TV channels.", 31026),
        "MyPVRGuide.xml": pvr_guide(),
        "MyPVRRecordings.xml": pvr_window("Recordings.", 31028),
        "MyPVRTimers.xml": pvr_window("Timers of recordings.", 31029),
        "MyPVRSearch.xml": pvr_window("Searching the TV guide.", 31030),
        "DialogPVRChannelsOSD.xml": pvr_channels_osd("Channel list over the TV playing."),
        "DialogPVRChannelGuide.xml": pvr_channels_osd("Channel guide over the TV playing."),
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
