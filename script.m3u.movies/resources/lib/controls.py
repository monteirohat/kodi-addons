"""Playback controls over the video: play and pause, back and forward 10 seconds, subtitles and audio.

The window stays open while a movie plays, so it gets the keys of the remote. Keys it does not use, such as
volume, play and stop, go on to Kodi.
"""

import json
import os
import shutil
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import cinemeta, subtitles


ADDON = xbmcaddon.Addon()
PATH = ADDON.getAddonInfo("path")
# Subtitles downloaded from OpenSubtitles, for the movie playing.
SUBTITLES_FOLDER = os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo("profile")), "subtitles")
# Online subtitles listed in the subtitles panel.
MAX_ONLINE = 15

ACTION_LEFT, ACTION_RIGHT, ACTION_UP, ACTION_DOWN, ACTION_SELECT = 1, 2, 3, 4, 7
ACTION_BACK = (10, 92)
# Keys that show the controls: info, the OSD key, the menu key, and play and pause, fast forward and rewind, which
# Kodi handles itself.
ACTION_SHOW = (11, 12, 24, 68, 77, 78, 117, 229)
SUBTITLES, BACK, PLAY, FORWARD, AUDIO, NEXT = 201, 202, 203, 204, 205, 206
PROGRESS, TRACKS = 300, 400
SKIP = 10
# Seconds without keys before the controls hide, and before the time bar of a skip hides.
HIDE_AFTER, BAR_HIDE_AFTER = 5, 3
# Skips pressed within this many seconds add up to one seek, as the player is slow to seek over and over.
SEEK_DELAY = 0.6
# Seconds the target of a seek is shown, while the player gets there.
SEEK_SETTLE = 2
# The next episode is offered in the last minute of an episode, or in its last tenth when it is short.
NEXT_BEFORE, NEXT_SHARE = 60, 0.1
LANGUAGES = {"por": 30330, "pt": 30330, "pob": 30331, "pb": 30331, "pt-br": 30331, "eng": 30332, "en": 30332,
             "spa": 30333, "es": 30333, "fre": 30334, "fra": 30334, "fr": 30334, "ita": 30335, "it": 30335,
             "ger": 30336, "deu": 30336, "de": 30336, "jpn": 30337, "ja": 30337, "kor": 30338, "ko": 30338,
             "chi": 30339, "zho": 30339, "zh": 30339, "rus": 30340, "ru": 30340}
# Language codes of Kodi and of subtitle files, as the codes of OpenSubtitles.
CODES = {"pt": "por", "pt-br": "pob", "pb": "pob", "en": "eng", "es": "spa", "fr": "fre", "fra": "fre", "it": "ita",
         "de": "ger", "deu": "ger", "ja": "jpn", "ko": "kor", "zh": "chi", "zho": "chi", "ru": "rus"}
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


def normalized_code(code):
    code = (code or "").strip().lower()
    return CODES.get(code, code)


def subtitle_code(stream):
    """Language of a subtitle track, as an OpenSubtitles code.

    Kodi names a subtitle file such as Movie.pt-BR.srt "pt (External)" and takes BR for Breton, so a language
    code at the end of the name, before the parentheses, comes first."""
    code = name_parts(stream)[1]
    if code not in LANGUAGES:
        return normalized_code(stream.get("language"))
    if code in ("pt", "por") and stream.get("language") in ("bre", "pob"):
        return "pob"
    return normalized_code(code)


def name_parts(stream):
    """The name of a subtitle track in three parts, as ("OpenSubtitles", "pt", "External") for
    "OpenSubtitles pt (External)"."""
    head, _, rest = (stream.get("name") or "").partition(" (")
    words = head.split()
    return " ".join(words[:-1]), words[-1].lower() if words else "", rest.rstrip(")")


def subtitle_name(stream, number):
    """Language and detail of a subtitle track."""
    prefix, code, rest = name_parts(stream)
    if code not in LANGUAGES:
        return language_name(stream.get("language"), number), stream.get("name") or ""
    return text(LANGUAGES[subtitle_code(stream)]), "  ·  ".join(part for part in (prefix, rest) if part)


def notify(message, heading=None):
    xbmcgui.Dialog().notification(heading or ADDON.getAddonInfo("name"), message, os.path.join(PATH, "resources", "icon.png"), 4000)


def wanted_languages():
    orders = subtitles.LANGUAGE_ORDERS
    return orders[min(max(ADDON.getSettingInt("subtitle_language"), 0), len(orders) - 1)]


class OnlineSubtitles:
    """Subtitles of the movie playing, from OpenSubtitles.

    They are looked up when the movie starts. With the setting on, a subtitle in the chosen language is turned on
    when the audio is in another language: one of the video, or else the best one online. target has kind,
    imdb, title, year, path, and season and episode for an episode."""

    def __init__(self, player, target):
        self.player, self.target = player, target
        self.languages = wanted_languages()
        # None while searching.
        self.results = None
        self.downloaded = {}
        self.closed = False

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        # Subtitles of the previous movie are not needed any more.
        if os.path.isdir(SUBTITLES_FOLDER):
            shutil.rmtree(SUBTITLES_FOLDER, ignore_errors=True)
        try:
            self.results = self.find()
        except Exception as error:
            xbmc.log("Easy Movie: online subtitles failed: %s" % error, xbmc.LOGWARNING)
            self.results = []
        if ADDON.getSettingBool("subtitles_auto") and not self.closed:
            self.choose_automatically()

    def find(self):
        target = self.target
        imdb_id = target.get("imdb") or ""
        if not imdb_id.startswith("tt"):
            # A movie of a web list: its IMDb id comes from a Cinemeta search by name and year.
            meta = cinemeta.best(cinemeta.search(target["kind"], target["title"]), target["title"], target.get("year") or 0)
            imdb_id = (meta or {}).get("imdb_id") or (meta or {}).get("id") or ""
            if not imdb_id.startswith("tt"):
                return []
        path = target.get("path") or ""
        file_hash = None
        if path.startswith("/") and os.path.isfile(path):
            try:
                file_hash = subtitles.file_hash(path)
            except OSError:
                pass
        filename = os.path.basename(path)
        found = subtitles.search(target["kind"], subtitles.video_id(imdb_id, target.get("season"), target.get("episode")),
                                 file_hash, filename or None)
        return subtitles.ranked(found, self.languages, filename)[:MAX_ONLINE]

    def choose_automatically(self):
        player_id = video_player()
        properties = rpc("Player.GetProperties", playerid=player_id,
                         properties=["subtitles", "currentsubtitle", "subtitleenabled", "currentaudiostream"]) or {}
        first = self.languages[0]
        audio = normalized_code((properties.get("currentaudiostream") or {}).get("language"))
        if audio in subtitles.FAMILIES.get(first, {first}):
            return
        current = properties.get("currentsubtitle") if properties.get("subtitleenabled") else None
        tracks = {}
        for stream in properties.get("subtitles") or []:
            tracks.setdefault(subtitle_code(stream), stream["index"])
        # The best language first, from the video itself before online.
        for language in self.languages:
            if current and subtitle_code(current) == language:
                return
            if language in tracks:
                rpc("Player.SetSubtitle", playerid=player_id, subtitle=tracks[language], enable=True)
                return
            index = next((index for index, subtitle in enumerate(self.results) if subtitle["lang"] == language), None)
            if index is not None:
                if self.apply(index):
                    notify(text(30345, language_name(language, 1)), "OpenSubtitles")
                return

    def apply(self, index):
        """Download an online subtitle and turn it on."""
        subtitle = self.results[index]
        path = self.downloaded.get(subtitle["id"])
        if not path:
            try:
                path = self.downloaded[subtitle["id"]] = subtitles.download(subtitle, SUBTITLES_FOLDER)
            except Exception as error:
                xbmc.log("Easy Movie: subtitle download failed: %s" % error, xbmc.LOGWARNING)
                notify(text(30346))
                return False
        if self.closed or not self.player.isPlayingVideo():
            return False
        self.player.setSubtitles(path)
        return True


class PlayerControls(xbmcgui.WindowXMLDialog):
    """Opened with open_controls when a movie starts, closed with shutdown when it ends."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.player = kwargs["player"]
        self.title, self.detail = kwargs.get("title", ""), kwargs.get("detail", "")
        self.online = kwargs.get("online")
        # The (season, number) of the next episode, and what plays it, when there is one.
        self.following, self.on_next = kwargs.get("following"), kwargs.get("on_next")
        # Whether the next episode is offered, and whether Back put the offer away.
        self.offering = self.dismissed = False
        # Whether the subtitles panel shows the online search still running.
        self.online_waiting = False
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
        if self.following:
            self.setProperty("next_label", text(30373, text(30133, *self.following)))
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
            # Near the end of an episode, the next episode button is the one to press.
            self.focus(NEXT if self.offering else PLAY)

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
            if self.panel == "subtitles" and self.online_waiting and self.online.results is not None:
                self.open_panel("subtitles", self.track_list.getSelectedPosition())
            if self.on_next and not self.dismissed:
                self.offer_next()
            if not self.mode:
                continue
            self.update_time()
            idle = now - self.last_key
            if self.mode == "bar" and idle > BAR_HIDE_AFTER and self.seek_target is None:
                self.set_mode("")
            elif self.mode == "full" and idle > HIDE_AFTER and not self.panel and not self.offering \
                    and not xbmc.getCondVisibility("Player.Paused"):
                self.set_mode("")

    def offer_next(self):
        """Show the next episode button near the end of the episode, and hide it again after a seek back."""
        try:
            position, total = self.player.getTime(), self.player.getTotalTime()
        except RuntimeError:
            return
        offering = total > 0 and 0 < total - position <= min(NEXT_BEFORE, total * NEXT_SHARE)
        if offering == self.offering:
            return
        self.offering = offering
        self.setProperty("next", "true" if offering else "")
        if offering and not self.panel:
            # The controls show with the button, and stay while it is offered.
            if self.mode == "full":
                self.focus(NEXT)
            else:
                self.set_mode("full")
        elif not offering and self.getFocusId() == NEXT:
            self.focus(PLAY)

    def hide_next(self):
        self.dismissed, self.offering = True, False
        self.setProperty("next", "")
        if self.getFocusId() == NEXT:
            self.focus(PLAY)

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
                # Back also puts away the next episode, which would otherwise bring the controls back.
                if self.offering:
                    self.hide_next()
                self.set_mode("")
            return
        if action_id in (ACTION_LEFT, ACTION_RIGHT):
            # The controls show while skipping, with the back or forward button lit, and the arrows keep skipping.
            self.skip(-SKIP if action_id == ACTION_LEFT else SKIP)
            self.set_mode("bar")
            self.focus(BACK if action_id == ACTION_LEFT else FORWARD)
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
        elif control_id == NEXT:
            if self.offering:
                self.hide_next()
                self.on_next()
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

    def open_panel(self, kind, position=None):
        """Open the subtitles or audio panel, or show it again at position."""
        player_id = video_player()
        properties = rpc("Player.GetProperties", playerid=player_id,
                         properties=["subtitles", "currentsubtitle", "subtitleenabled", "audiostreams", "currentaudiostream"]) or {}
        items = []
        if kind == "subtitles":
            current = (properties.get("currentsubtitle") or {}).get("index") if properties.get("subtitleenabled") else None
            self.tracks = ["off"] + [stream["index"] for stream in properties.get("subtitles") or []]
            items.append(self.track_item(text(30322), "" if properties.get("subtitles") else text(30325), current is None))
            for number, stream in enumerate(properties.get("subtitles") or [], 1):
                name, detail = subtitle_name(stream, number)
                if stream.get("isforced"):
                    name += "  ·  " + text(30324)
                items.append(self.track_item(name, detail, stream["index"] == current))
            items += self.online_items()
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
        self.track_list.selectItem(selected if position is None else min(position, len(items) - 1))
        if position is not None:
            return
        self.setProperty("panel_title", text(30320 if kind == "subtitles" else 30321))
        self.setProperty("panel", kind)
        self.focus(TRACKS)

    def online_items(self):
        """Subtitles from OpenSubtitles, after the ones of the video. Tracks are ("online", index), or None for a
        line that only informs."""
        online = self.online
        self.online_waiting = online is not None and online.results is None
        if online is None:
            return []
        if online.results is None or not online.results:
            self.tracks.append(None)
            return [self.track_item(text(30342 if online.results is None else 30343), "OpenSubtitles", False)]
        items = []
        for index, subtitle in enumerate(online.results):
            details = ["OpenSubtitles", subtitles.release_name(subtitle)]
            if subtitle.get("m") == "h":
                details.append(text(30344))
            self.tracks.append(("online", index))
            items.append(self.track_item(language_name(subtitle["lang"], index + 1), "  ·  ".join(d for d in details if d), False))
        return items

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
                # A line that only informs.
                return
            if isinstance(track, tuple):
                self.online.apply(track[1])
            elif track == "off":
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


def open_controls(player, title, detail="", online=None, following=None, on_next=None):
    """Show the controls over the video that just started. Returns the window, to close with shutdown. following is
    the (season, number) of the next episode, which on_next plays, offered near the end of an episode."""
    window = PlayerControls("script-m3u-movies-player.xml", PATH, "default", "1080i", player=player, title=title, detail=detail,
                            online=online, following=following, on_next=on_next)
    threading.Thread(target=window.doModal, daemon=True).start()
    return window
