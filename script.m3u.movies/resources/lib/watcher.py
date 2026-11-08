"""Plays movies and episodes, reports the ones that fail to open, and keeps track of how far they were watched.

They play from the video playlist of Kodi. When an episode starts, the next one is queued after it, so Kodi goes on to
it at the end without leaving the video, as with any playlist.
"""

import threading
import time

import xbmc
import xbmcgui

from resources.lib import controls, m3u, probe


OPEN_TIMEOUT = 120
# A live channel that ends on its own this soon after starting is treated as broken, unless it played to its end.
EARLY_END = 60
# A video that played to this many seconds before its end ended normally, as after a skip to its end.
NEAR_END = 30
# A channel still opening after this many seconds is checked, so a dead server does not keep Kodi waiting.
CHECK_AFTER = 15
CHECK_TIMEOUT = 8
# Seconds Kodi waits to connect to a stream server. Kodi's default keeps a dead server busy for over a minute.
CONNECT_TIMEOUT = 8
# Seconds between progress reports while a movie plays, so a power cut loses little.
PROGRESS_EVERY = 15


def playable_url(url):
    """Stream address with a short connection timeout for HTTP streams."""
    if not url.lower().startswith(("http://", "https://")) or "connection-timeout=" in url:
        return url
    return url + ("&" if "|" in url else "|") + "connection-timeout=" + str(CONNECT_TIMEOUT)


class Watcher(xbmc.Player):
    def __init__(self, on_failure, on_progress, following=None):
        super().__init__()
        self.on_failure = on_failure
        # Called with the entry, position and total in seconds, and whether playback is over.
        self.on_progress = on_progress
        # Gives what plays after an episode, as (entry, start, subtitles), or None after the last one.
        self.following = following
        self.playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self.monitor = xbmc.Monitor()
        self.lock = threading.Lock()
        self.events = []
        self.watched = None
        # Set when Kodi reports that playback stopped, ended or failed.
        self.stop_seen = threading.Event()
        self.closed = False
        self.controls = None
        self.online = None
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def onAVStarted(self):
        self.push("started")

    def onPlayBackError(self):
        self.push("error")

    def onPlayBackEnded(self):
        self.push("ended")

    def onPlayBackStopped(self):
        self.push("stopped")

    def push(self, event):
        if event != "started":
            self.stop_seen.set()
        with self.lock:
            self.events.append(event)

    def play_channel(self, entry, start=0, subtitles=None):
        """Play an entry, from start seconds when resuming. subtitles tells which movie or episode it is, to look up
        its subtitles online, see controls.OnlineSubtitles."""
        with self.lock:
            previous, self.watched = self.watched, None
        self.close_controls()
        # Keep how far the movie being replaced was watched.
        if previous and previous["started"]:
            self.on_progress(previous, previous["position"], previous["total"], True)
        # Stop the current movie first so its events are not mistaken for the new one. Kodi reports the stop
        # a moment after the player closes, so wait for that report. Taken for the new movie, it stopped it.
        if self.isPlaying():
            self.stop_seen.clear()
            self.stop()
            for _ in range(30):
                if self.stop_seen.is_set() or self.monitor.waitForAbort(0.1):
                    break
            self.monitor.waitForAbort(0.2)
        with self.lock:
            self.events = []
            self.watched = self.watching(entry, start, subtitles)
        url, item = self.list_item(entry)
        # From the playlist, so the next episode can be queued after this one. See queue.
        self.playlist.clear()
        self.playlist.add(url, item)
        self.play(self.playlist, startpos=0)

    def watching(self, entry, start=0, subtitles=None):
        """The entry about to play, with what is followed of it while it plays."""
        return dict(entry, opened=time.time(), started=None, start=start, position=0, total=0, reported=0,
                    subtitles=subtitles or entry.get("subtitles"))

    def list_item(self, entry):
        """The address and list item Kodi plays an entry with."""
        channel = entry["channel"]
        url = playable_url(channel["url"])
        item = xbmcgui.ListItem(channel["name"], path=url)
        item.getVideoInfoTag().setTitle(channel["name"])
        if channel["logo"]:
            item.setArt({"icon": channel["logo"], "thumb": channel["logo"]})
        for key, value in channel["properties"].items():
            item.setProperty(key, value)
        # Skip Kodi's extra request to detect the stream type, which blocks for a long time on dead servers.
        item.setContentLookup(False)
        if ".m3u8" in m3u.base_url(channel["url"]).lower():
            item.setMimeType("application/vnd.apple.mpegurl")
        return url, item

    def loop(self):
        while not self.closed and not self.monitor.waitForAbort(0.5):
            with self.lock:
                events, self.events = self.events, []
                watched = self.watched
            if watched is None:
                continue
            failed = finished = ended = False
            remaining = []
            for index, event in enumerate(events):
                if event == "started":
                    self.on_started(watched)
                elif event == "stopped":
                    # Stopping a movie that never started usually means it was not working.
                    failed = watched["started"] is None
                    finished = True
                elif event == "error":
                    failed = True
                elif event == "ended":
                    near_end = watched["total"] > 0 and watched["total"] - watched["position"] <= NEAR_END
                    # The next episode button skips to the end, which is not an early end.
                    early = watched["started"] is None or time.time() - watched["started"] < EARLY_END
                    failed = early and not near_end and not watched.get("skipped")
                    finished = ended = True
                if failed or finished:
                    remaining = events[index + 1:]
                    break
            if watched["started"] and not finished:
                self.sample(watched)
            elif not watched["started"] and not (failed or finished):
                finished = time.time() - watched["opened"] > OPEN_TIMEOUT
                if not watched.get("checked") and time.time() - watched["opened"] > CHECK_AFTER:
                    watched["checked"] = True
                    failed = probe.check(watched["channel"]["url"], CHECK_TIMEOUT) is not None
            # At the end of an episode, Kodi goes on by itself to the next one queued after it.
            following = watched.get("next") if ended and watched.get("queued") else None
            if failed or finished:
                self.close_controls()
                with self.lock:
                    # A movie requested meanwhile replaces this one.
                    if self.watched is not watched:
                        continue
                    self.watched = self.watching(*following) if following else None
                    if following:
                        # The start of the next episode may be among the events already taken.
                        self.events = remaining + self.events
            if finished and not failed and watched["started"]:
                if ended:
                    watched["position"] = watched["total"]
                self.on_progress(watched, watched["position"], watched["total"], True)
            if failed and following:
                # It ended before its end, as an incomplete file, and Kodi went on anyway. Say so without a question
                # that would stop the next episode.
                self.report_incomplete(watched)
            elif failed and not self.closed:
                if self.isPlaying() and watched["started"] is None:
                    self.stop()
                # Ask only after Kodi gave up opening the channel and closed its own error notice.
                self.monitor.waitForAbort(1)
                for _ in range(240):
                    if self.closed or self.monitor.waitForAbort(0.5):
                        return
                    if not self.isPlaying() and not xbmc.getCondVisibility("System.HasActiveModalDialog"):
                        break
                self.on_failure(watched)

    def on_started(self, watched):
        watched["started"] = time.time()
        if watched["start"]:
            self.seekTime(watched["start"])
        if watched.get("episode") and "next" not in watched:
            watched["next"] = self.following(watched) if self.following else None
            if watched["next"] and controls.autoplay():
                self.queue(watched)
        if watched["subtitles"] and self.online is None and self.isPlayingVideo():
            self.online = controls.OnlineSubtitles(self, watched["subtitles"])
            self.online.start()
        if controls.enabled() and self.controls is None and self.isPlayingVideo():
            self.open_controls(watched)

    def queue(self, watched):
        """Queue the next episode after the one playing, so Kodi goes on to it at its end without leaving the video."""
        if watched.get("queued") or not watched.get("next"):
            return
        url, item = self.list_item(watched["next"][0])
        self.playlist.add(url, item)
        watched["queued"] = True

    def skip_to_next(self, watched):
        """Go on to the next episode now: skip to the end of the episode, and Kodi goes on as at any end."""
        if self.watched is not watched:
            return
        self.queue(watched)
        watched["skipped"] = True
        try:
            self.seekTime(max(self.getTotalTime() - 1, 0))
        except RuntimeError:
            pass

    def report_incomplete(self, watched):
        episode = watched["episode"]
        name = "%s S%02dE%02d" % (episode["show"], episode["season"], episode["number"])
        xbmcgui.Dialog().notification(controls.ADDON.getAddonInfo("name"), controls.text(30383, name),
                                      xbmcgui.NOTIFICATION_WARNING, 8000)

    def sample(self, watched):
        """Remember the playback position, and report it from time to time."""
        try:
            if not self.isPlayingVideo():
                return
            watched["position"], watched["total"] = self.getTime(), self.getTotalTime()
        except RuntimeError:
            return
        if time.time() - watched["reported"] > PROGRESS_EVERY:
            watched["reported"] = time.time()
            self.on_progress(watched, watched["position"], watched["total"], False)

    def open_controls(self, watched):
        episode = watched.get("episode")
        if episode:
            title = episode["show"]
            detail = "S%02dE%02d" % (episode["season"], episode["number"]) + ("  ·  " + episode["title"] if episode["title"] else "")
        else:
            title, detail = watched["channel"]["name"], ""
        next_episode = on_next = None
        if watched.get("next"):
            entry = watched["next"][0]
            next_episode = (entry["episode"]["season"], entry["episode"]["number"])
            on_next = lambda: self.skip_to_next(watched)
        self.controls = controls.open_controls(self, title, detail, self.online, next_episode, on_next)

    def close_controls(self):
        window, self.controls = self.controls, None
        if window is not None:
            window.shutdown()
        online, self.online = self.online, None
        if online is not None:
            online.closed = True

    def shutdown(self):
        self.close_controls()
        self.closed = True
        self.thread.join(2)
