"""Plays movies and episodes, reports the ones that fail to open, and keeps track of how far they were watched."""

import threading
import time

import xbmc
import xbmcgui

from resources.lib import controls, m3u, probe


OPEN_TIMEOUT = 120
# A live channel that ends on its own this soon after starting is treated as broken.
EARLY_END = 60
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
    def __init__(self, on_failure, on_progress):
        super().__init__()
        self.on_failure = on_failure
        # Called with the entry, position and total in seconds, and whether playback is over.
        self.on_progress = on_progress
        self.monitor = xbmc.Monitor()
        self.lock = threading.Lock()
        self.events = []
        self.watched = None
        # Set when Kodi reports that playback stopped, ended or failed.
        self.stop_seen = threading.Event()
        self.closed = False
        self.controls = None
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

    def play_channel(self, entry, start=0):
        """Play an entry, from start seconds when resuming."""
        channel = entry["channel"]
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
            self.watched = dict(entry, opened=time.time(), started=None, start=start, position=0, total=0, reported=0)
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
        self.play(url, item)

    def loop(self):
        while not self.closed and not self.monitor.waitForAbort(0.5):
            with self.lock:
                events, self.events = self.events, []
                watched = self.watched
            if watched is None:
                continue
            failed = finished = ended = False
            for event in events:
                if event == "started":
                    watched["started"] = time.time()
                    if watched["start"]:
                        self.seekTime(watched["start"])
                    if controls.enabled() and self.controls is None and self.isPlayingVideo():
                        self.open_controls(watched)
                elif event == "stopped":
                    # Stopping a movie that never started usually means it was not working.
                    failed = watched["started"] is None
                    finished = True
                elif event == "error":
                    failed = True
                elif event == "ended":
                    failed = watched["started"] is None or time.time() - watched["started"] < EARLY_END
                    finished = ended = True
                if failed or finished:
                    break
            if watched["started"] and not finished:
                self.sample(watched)
            elif not watched["started"] and not (failed or finished):
                finished = time.time() - watched["opened"] > OPEN_TIMEOUT
                if not watched.get("checked") and time.time() - watched["opened"] > CHECK_AFTER:
                    watched["checked"] = True
                    failed = probe.check(watched["channel"]["url"], CHECK_TIMEOUT) is not None
            if failed or finished:
                self.close_controls()
                with self.lock:
                    # A movie requested meanwhile replaces this one.
                    if self.watched is not watched:
                        continue
                    self.watched = None
            if finished and not failed and watched["started"]:
                if ended:
                    watched["position"] = watched["total"]
                self.on_progress(watched, watched["position"], watched["total"], True)
            if failed and not self.closed:
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
        self.controls = controls.open_controls(self, title, detail)

    def close_controls(self):
        window, self.controls = self.controls, None
        if window is not None:
            window.shutdown()

    def shutdown(self):
        self.close_controls()
        self.closed = True
        self.thread.join(2)
