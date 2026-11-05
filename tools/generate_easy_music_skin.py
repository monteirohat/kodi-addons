"""Generate the Easy Music window layout with the palette and parts shared with Easy Channel and Easy Movie."""

import os

import generate_m3u_channels_skin as skin
from generate_m3u_channels_skin import (ACCENT, BG, FOCUS, ON_FOCUS, ON_FOCUS2, RAISED, RAISED2, SURFACE, TEXT, TEXT2, TEXT3,
                                        has, image, join, label, panel, window)


ADDON_ID = "script.easy.music"
songs_focus = has(300)
playing = "String.IsEqual(ListItem.Property(playing),true)"
liked = "String.IsEqual(ListItem.Property(liked),true)"
# Top of the player bar. The playlists and the songs end above it.
BAR = 904
BUTTONS = 600


def songs():
    """The songs of the playlist: number, or bars while it plays, title and artist, album, and a heart when liked."""
    def parts(title, detail, condition=None, scroll=False):
        # The song that plays shows bars instead of its number, and its title in the accent color.
        return [label(10, 0, 60, 72, "$INFO[ListItem.Property(number)]", "font12", detail, both(condition, "!" + playing), align="center"),
                image(24, 20, 32, 32, "playing.png", ACCENT if title != ON_FOCUS else ON_FOCUS, both(condition, playing)),
                label(84, 4, 700, 40, "$INFO[ListItem.Label]", "font13", title, both(condition, "!" + playing), scroll=scroll),
                label(84, 4, 700, 40, "$INFO[ListItem.Label]", "font13", ACCENT if title != ON_FOCUS else ON_FOCUS,
                      both(condition, playing), scroll=scroll),
                label(84, 40, 700, 28, "$INFO[ListItem.Label2]", "font12", detail, condition),
                label(810, 0, 380, 72, "$INFO[ListItem.Property(album)]", "font12", detail, condition),
                image(1206, 22, 28, 28, "heart.png", ACCENT if title != ON_FOCUS else ON_FOCUS, both(condition, liked))]
    return f"""<!-- Songs. Left returns to the playlists, Down after the last song reaches the player, handled in gui.py. -->
<control type="list" id="300">
  <left>600</left>
  <top>222</top>
  <width>1260</width>
  <height>648</height>
  <onleft>noop</onleft>
  <onright>noop</onright>
  <onup>noop</onup>
  <ondown>{BUTTONS + 3}</ondown>
  <scrolltime>120</scrolltime>
  <itemlayout height="72">
{join(*parts(TEXT, TEXT2), spaces=4)}
  </itemlayout>
  <focusedlayout height="72">
{join(panel(0, 2, 1260, 68, FOCUS, songs_focus), panel(0, 2, 1260, 68, RAISED, "!" + songs_focus),
      *parts(ON_FOCUS, ON_FOCUS2, songs_focus, True), *parts(TEXT, TEXT2, "!" + songs_focus), spaces=4)}
  </focusedlayout>
</control>"""


def both(*conditions):
    return " + ".join(condition for condition in conditions if condition) or None


def player_button(control_id, left, size, icons, onleft, onright, onclick=None, filled=False):
    """A round button of the player. Buttons cannot hold images, so the icon is drawn over it.

    icons is a list of (texture, condition). A filled button, play and pause, is white when it has no focus."""
    focus = has(control_id)
    click = f"\n  <onclick>{onclick}</onclick>" if onclick else ""
    nofocus = f'<texturenofocus colordiffuse="{TEXT}">circle.png</texturenofocus>' if filled else "<texturenofocus />"
    controls = [f"""<control type="button" id="{control_id}">
  <left>{left}</left>
  <top>{BAR + 22 + (72 - size) // 2}</top>
  <width>{size}</width>
  <height>{size}</height>
  <label></label>
  <onup>300</onup>
  <ondown>noop</ondown>
  <onleft>{onleft}</onleft>
  <onright>{onright}</onright>{click}
  <texturefocus colordiffuse="{FOCUS}">circle.png</texturefocus>
  {nofocus}
</control>"""]
    inset = size * 3 // 10
    for texture, condition, color in icons:
        top = BAR + 22 + (72 - size) // 2 + inset
        controls.append(image(left + inset, top, size - 2 * inset, size - 2 * inset, texture, ON_FOCUS, both(focus, condition)))
        controls.append(image(left + inset, top, size - 2 * inset, size - 2 * inset, texture, BG if filled else color,
                              both("!" + focus, condition)))
    return controls


def player_bar():
    """The player at the bottom: the song, its controls and progress, and its place in the queue."""
    # Kodi groups conditions with square brackets.
    paused = "!Player.Playing | Player.Paused"
    playing_now = "Player.HasAudio"
    shuffle_on, repeat_all, repeat_one = "Playlist.IsRandom", "Playlist.IsRepeat", "Playlist.IsRepeatOne"
    center = 960
    buttons = (
        player_button(BUTTONS + 1, center - 228, 56, [("shuffle.png", shuffle_on, ACCENT), ("shuffle.png", "!" + shuffle_on, TEXT2)],
                        "noop", BUTTONS + 2, "PlayerControl(Random)")
        + player_button(BUTTONS + 2, center - 128, 56, [("previous.png", None, TEXT)], BUTTONS + 1, BUTTONS + 3, "PlayerControl(Previous)")
        + player_button(BUTTONS + 3, center - 36, 72, [("pause.png", "![%s]" % paused, TEXT), ("play.png", paused, TEXT)],
                        BUTTONS + 2, BUTTONS + 4, filled=True)
        + player_button(BUTTONS + 4, center + 72, 56, [("next.png", None, TEXT)], BUTTONS + 3, BUTTONS + 5, "PlayerControl(Next)")
        + player_button(BUTTONS + 5, center + 172, 56, [("repeat-one.png", repeat_one, ACCENT), ("repeat.png", repeat_all, ACCENT),
                                                        ("repeat.png", "!%s + !%s" % (repeat_all, repeat_one), TEXT2)],
                        BUTTONS + 4, BUTTONS + 6, "PlayerControl(Repeat)")
        # The heart likes the song that plays, after a gap that keeps it apart from the playback buttons.
        + player_button(BUTTONS + 6, center + 296, 56, [("heart.png", "String.IsEqual(Window.Property(liked),true)", ACCENT),
                                                        ("heart-outline.png", "!String.IsEqual(Window.Property(liked),true)", TEXT2)],
                        BUTTONS + 5, "noop"))
    return join(
        "<!-- Player bar. Play and pause and the heart are handled in gui.py, the other buttons by Kodi. -->",
        panel(24, BAR, 1872, 160, SURFACE),
        panel(48, BAR + 16, 128, 128, RAISED),
        image(80, BAR + 48, 64, 64, "note.png", TEXT3),
        image(48, BAR + 16, 128, 128, "$INFO[Player.Art(thumb)]", None, playing_now, keep=True),
        label(200, BAR + 30, 480, 44, "$INFO[MusicPlayer.Title]", "font13", TEXT, playing_now, scroll=True),
        label(200, BAR + 74, 480, 36, "$INFO[MusicPlayer.Artist]", "font12", TEXT2, playing_now),
        label(200, BAR + 30, 480, 80, f"$ADDON[{ADDON_ID} 30023]", "font12", TEXT3, "!" + playing_now),
        *buttons,
        label(center - 330, BAR + 106, 100, 36, "$INFO[MusicPlayer.Time]", "font12", TEXT2, playing_now, align="right"),
        f"""<control type="progress">
  <left>{center - 216}</left>
  <top>{BAR + 120}</top>
  <width>432</width>
  <height>8</height>
  <texturebg colordiffuse="{RAISED2}">white.png</texturebg>
  <midtexture colordiffuse="{ACCENT}">white.png</midtexture>
  <info>Player.Progress</info>
  <visible>{playing_now}</visible>
</control>""",
        label(center + 230, BAR + 106, 100, 36, "$INFO[MusicPlayer.Duration]", "font12", TEXT2, playing_now),
        label(1440, BAR + 30, 416, 44, "$INFO[MusicPlayer.Album]", "font12", TEXT2, playing_now, align="right"),
        label(1440, BAR + 74, 416, 36, f"$INFO[MusicPlayer.PlaylistPosition]$INFO[MusicPlayer.PlaylistLength, / ]", "font12", TEXT3,
              playing_now, align="right"),
        spaces=0)


def main_screen():
    # The playlists end above the player bar, and Down after the last one reaches the player.
    playlists = skin.groups.replace("<height>748</height>", "<height>600</height>").replace(
        "<onup>100</onup>", f"<onup>100</onup>\n  <ondown>{BUTTONS + 3}</ondown>")
    return join(
        image(0, 0, 1920, 1080, "white.png", BG),
        image(56, 30, 56, 56, "logo.png"),
        label(1360, 28, 500, 60, "$INFO[System.Time]", "font32_title", TEXT2, align="right"),
        "<!-- Toolbar. Tools are added from Python, see TOOLS in gui.py. -->",
        skin.make_toolbar(104),
        label(44, 212, 516, 36, "$INFO[Container(100).ListItem.Label]", "font12", ACCENT, has(100)),
        "<!-- Playlists -->",
        panel(40, 256, 520, 630, SURFACE),
        playlists,
        "<!-- Songs of the playlist, with its name, the song count and the keys in the header -->",
        panel(580, 110, 1300, 776, SURFACE),
        label(612, 114, 940, 56, "", "font32_title", TEXT, control_id=401),
        label(1560, 114, 290, 56, "", "font12", TEXT2, align="right", control_id=402),
        label(612, 166, 1240, 32, f"$ADDON[{ADDON_ID} 30020]", "font12", TEXT3),
        image(604, 206, 1252, 2, "white.png", RAISED),
        label(620, 360, 1220, 300, "", "font13", TEXT2, align="center", center=False, control_id=404, wrap=True),
        songs(),
        player_bar(),
        spaces=0)


def main():
    skin.ADDON_ID, skin.GENERATOR = ADDON_ID, "generate_easy_music_skin.py"
    files = {
        "script-easy-music-main.xml": window("Main screen: toolbar and playlists on the left, songs on the right, the player at the bottom.",
                                             200, main_screen()),
    }
    folder = skin.skin_folder(ADDON_ID)
    os.makedirs(folder, exist_ok=True)
    for name, content in files.items():
        with open(os.path.join(folder, name), "w") as output:
            output.write(content)


if __name__ == "__main__":
    main()
