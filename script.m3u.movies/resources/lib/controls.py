"""Playback controls over the video: play and pause, back and forward 10 seconds, subtitles and audio.

The window stays open while a movie plays, so it gets the keys of the remote. Keys it does not use, such as
volume, play and stop, go on to Kodi.
"""

import json
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui


ADDON = xbmcaddon.Addon()
PATH = ADDON.getAddonInfo("path")

ACTION_LEFT, ACTION_RIGHT, ACTION_UP, ACTION_DOWN, ACTION_SELECT = 1, 2, 3, 4, 7
ACTION_BACK = (10, 92)
# Keys that show the controls: info, the OSD key, the menu key, and play and pause, which Kodi handles itself.
ACTION_SHOW = (11, 12, 24, 68, 117, 229)
SUBTITLES, BACK, PLAY, FORWARD, AUDIO = 201, 202, 203, 204, 205
PROGRESS, TRACKS = 300, 400
SKIP = 10
# Seconds without keys before the controls hide, and before the time bar of a skip hides.
HIDE_AFTER, BAR_HIDE_AFTER = 5, 3
# Skips pressed within this many seconds add up to one seek, as the player is slow to seek over and over.
SEEK_DELAY = 0.6
# Seconds the target of a seek is shown, while the player gets there.
SEEK_SETTLE = 2
LANGUAGES = {"por": 30330, "pt": 30330, "pob": 30331, "pb": 30331, "pt-br": 30331, "eng": 30332, "en": 30332,
             "spa": 30333, "es": 30333, "fre": 30334, "fra": 30334, "fr": 30334, "ita": 30335, "it": 30335,
             "ger": 30336, "deu": 30336, "de": 30336, "jpn": 30337, "ja": 30337, "kor": 30338, "ko": 30338,
             "chi": 30339, "zho": 30339, "zh": 30339, "rus": 30340, "ru": 30340}
CHANNELS = {1: "Mono", 2: "2.0", 6: "5.1", 8: "7.1"}


def text(string_id, *values):
    value = ADDON.getLocalizedString(string_id)
    return value.format(*values) if values else value


def enabled():
    return ADDON.getSettingBool("player_controls")


def clock(seconds):
    seconds = max(int(seconds), 0)
    hours, rest = divmod(seconds, 3600)
    return "%d:%02d:%02d" % (hours, rest // 60, rest % 60) if hours else "%d:%02d" % (rest // 60, rest % 60)


def rpc(method, **params):
    request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    return json.loads(xbmc.executeJSONRPC(json.dumps(request))).get("result")


def video_player():
    players = rpc("Player.GetActivePlayers") or []
    return next((player["playerid"] for player in players if player.get("type") == "video"), 1)


def language_name(code, number):
    code = (code or "").strip().lower()
    if code in LANGUAGES:
        return text(LANGUAGES[code])
    if code and code not in ("und", "unk"):
        return xbmc.convertLanguage(code, xbmc.ENGLISH_NAME) or code.upper()
    return text(30323, number)


def subtitle_name(stream, number):
    """Language and detail of a subtitle track.

    Kodi names a subtitle file such as Movie.pt-BR.srt "pt (External)" and takes BR for Breton, so a language
    code at the start of the name comes first."""
    name = stream.get("name") or ""
    code, _, rest = name.partition(" (")
    code = code.strip().lower()
    if code not in LANGUAGES:
        return language_name(stream.get("language"), number), name
    if code in ("pt", "por") and stream.get("language") in ("bre", "pob"):
        code = "pob"
    return text(LANGUAGES[code]), rest.rstrip(")")


class PlayerControls(xbmcgui.WindowXMLDialog):
    """Opened with open_controls when a movie starts, closed with shutdown when it ends."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.player = kwargs["player"]
        self.title, self.detail = kwargs.get("title", ""), kwargs.get("detail", "")
        self.mode = ""
        self.panel = None
        self.tracks = []
        self.last_key = time.time()
        self.seek_target = None
        self.seek_at = 0
        self.shown_target = None
        self.shown_until = 0
        self.shown_at = 0
        self.closed = False
        self.lock = threading.Lock()
        self.monitor = xbmc.Monitor()

    def onInit(self):
        if self.closed:
            self.close()
            return
        self.setProperty("title", self.title)
        self.setProperty("detail", self.detail)
        self.progress = self.getControl(PROGRESS)
        self.track_list = self.getControl(TRACKS)
        threading.Thread(target=self.loop, daemon=True).start()

    def shutdown(self):
        self.closed = True
        self.close()

    # Showing and hiding

    def set_mode(self, mode):
        if mode == self.mode:
            return
        self.mode = mode
        self.update_time()
        self.setProperty("mode", mode)
        if mode == "full":
            self.focus(PLAY)

    def focus(self, control_id):
        # A control shown by a property can take the focus only once Kodi has drawn it.
        for _ in range(20):
            if xbmc.getCondVisibility("Control.IsVisible(%d)" % control_id):
                break
            self.monitor.waitForAbort(0.02)
        self.setFocusId(control_id)

    def loop(self):
        playing_seen = time.time()
        while not self.closed and not self.monitor.waitForAbort(0.25):
            now = time.time()
            # The watcher closes the controls when playback ends. This also closes them if that report is lost.
            if self.player.isPlayingVideo():
                playing_seen = now
            elif now - playing_seen > 3:
                self.shutdown()
                return
            with self.lock:
                target = self.seek_target if self.seek_target is not None and now - self.seek_at > SEEK_DELAY else None
                if target is not None:
                    self.seek_target = None
                    self.shown_target, self.shown_until = target, now + SEEK_SETTLE
            if target is not None:
                try:
                    self.player.seekTime(target)
                except RuntimeError:
                    pass
            if not self.mode:
                continue
            self.update_time()
            idle = now - self.last_key
            if self.mode == "bar" and idle > BAR_HIDE_AFTER and self.seek_target is None:
                self.set_mode("")
            elif self.mode == "full" and idle > HIDE_AFTER and not self.panel and not xbmc.getCondVisibility("Player.Paused"):
                self.set_mode("")

    def update_time(self):
        try:
            position, total = self.player.getTime(), self.player.getTotalTime()
        except RuntimeError:
            return
        with self.lock:
            if self.seek_target is not None:
                position = self.seek_target
            elif self.shown_target is not None and time.time() < self.shown_until:
                position = self.shown_target
        self.setProperty("elapsed", clock(position))
        self.setProperty("duration", clock(total) if total else "")
        self.progress.setPercent(100.0 * position / total if total else 0)

    # Keys

    def onAction(self, action):
        action_id = action.getId()
        if action_id >= 100 and action_id not in (117, 229):
            # Mouse and other pointer actions.
            return
        self.last_key = time.time()
        if self.panel:
            if action_id in ACTION_BACK or action_id == ACTION_LEFT:
                self.close_panel()
            return
        if self.mode == "full":
            if action_id in ACTION_BACK:
                self.set_mode("")
            return
        if action_id in (ACTION_LEFT, ACTION_RIGHT):
            self.skip(-SKIP if action_id == ACTION_LEFT else SKIP)
            self.set_mode("bar")
        elif action_id in ACTION_BACK:
            # Back leaves the movie, as in streaming apps. The watcher keeps how far it was watched.
            self.player.stop()
        elif action_id in (ACTION_SELECT, ACTION_UP, ACTION_DOWN) + ACTION_SHOW:
            self.shown_at = time.time()
            self.set_mode("full")

    def onClick(self, control_id):
        # Kodi also clicks the focused button with the OK that shows the controls, which only shows them.
        if control_id == TRACKS:
            self.choose_track(self.track_list.getSelectedPosition())
        elif self.mode != "full" or self.panel or time.time() - self.shown_at < 0.5:
            return
        elif control_id == PLAY:
            self.player.pause()
        elif control_id in (BACK, FORWARD):
            self.skip(-SKIP if control_id == BACK else SKIP)
        elif control_id in (SUBTITLES, AUDIO):
            self.open_panel("subtitles" if control_id == SUBTITLES else "audio")

    def skip(self, seconds):
        try:
            position, total = self.player.getTime(), self.player.getTotalTime()
        except RuntimeError:
            return
        with self.lock:
            if self.seek_target is not None:
                position = self.seek_target
            elif self.shown_target is not None and time.time() < self.shown_until:
                position = self.shown_target
            self.seek_target = min(max(position + seconds, 0), max(total - 1, 0))
            self.seek_at = time.time()
        self.update_time()

    # Subtitles and audio

    def open_panel(self, kind):
        player_id = video_player()
        properties = rpc("Player.GetProperties", playerid=player_id,
                         properties=["subtitles", "currentsubtitle", "subtitleenabled", "audiostreams", "currentaudiostream"]) or {}
        items = []
        if kind == "subtitles":
            current = (properties.get("currentsubtitle") or {}).get("index") if properties.get("subtitleenabled") else None
            self.tracks = [None] + [stream["index"] for stream in properties.get("subtitles") or []]
            items.append(self.track_item(text(30322), "" if properties.get("subtitles") else text(30325), current is None))
            for number, stream in enumerate(properties.get("subtitles") or [], 1):
                name, detail = subtitle_name(stream, number)
                if stream.get("isforced"):
                    name += "  ·  " + text(30324)
                items.append(self.track_item(name, detail, stream["index"] == current))
        else:
            current = (properties.get("currentaudiostream") or {}).get("index")
            self.tracks = [stream["index"] for stream in properties.get("audiostreams") or []]
            for number, stream in enumerate(properties.get("audiostreams") or [], 1):
                # The name of a track often already gives its format, as in "AAC-LC stereo".
                details = [stream["name"]] if stream.get("name") else \
                    [(stream.get("codec") or "").upper(), CHANNELS.get(stream.get("channels"), "")]
                items.append(self.track_item(language_name(stream.get("language"), number),
                                             "  ·  ".join(detail for detail in details if detail), stream["index"] == current))
        self.panel = kind
        self.track_list.reset()
        self.track_list.addItems(items)
        selected = next((index for index, item in enumerate(items) if item.getProperty("current") == "true"), 0)
        self.track_list.selectItem(selected)
        self.setProperty("panel_title", text(30320 if kind == "subtitles" else 30321))
        self.setProperty("panel", kind)
        self.focus(TRACKS)

    def track_item(self, name, detail, current):
        item = xbmcgui.ListItem(name, detail)
        item.setProperty("current", "true" if current else "false")
        return item

    def choose_track(self, position):
        if not self.panel or not 0 <= position < len(self.tracks):
            return
        player_id, track = video_player(), self.tracks[position]
        if self.panel == "subtitles":
            if track is None:
                rpc("Player.SetSubtitle", playerid=player_id, subtitle="off")
            else:
                rpc("Player.SetSubtitle", playerid=player_id, subtitle=track, enable=True)
        else:
            rpc("Player.SetAudioStream", playerid=player_id, stream=track)
        self.close_panel()

    def close_panel(self):
        kind, self.panel = self.panel, None
        self.setProperty("panel", "")
        self.last_key = time.time()
        self.focus(SUBTITLES if kind == "subtitles" else AUDIO)


def open_controls(player, title, detail=""):
    """Show the controls over the video that just started. Returns the window, to close with shutdown."""
    window = PlayerControls("script-m3u-movies-player.xml", PATH, "default", "1080i", player=player, title=title, detail=detail)
    threading.Thread(target=window.doModal, daemon=True).start()
    return window
