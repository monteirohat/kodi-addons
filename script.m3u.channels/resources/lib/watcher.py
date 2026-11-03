"""Plays channels and reports the ones that fail to open or stop right after starting."""

import threading
import time

import xbmc
import xbmcgui

from resources.lib import m3u, probe


OPEN_TIMEOUT = 120
# A live channel that ends on its own this soon after starting is treated as broken.
EARLY_END = 60
# A channel still opening after this many seconds is checked, so a dead server does not keep Kodi waiting.
CHECK_AFTER = 15
CHECK_TIMEOUT = 8
# Seconds Kodi waits to connect to a stream server. Kodi's default keeps a dead server busy for over a minute.
CONNECT_TIMEOUT = 8


def playable_url(url):
    """Stream address with a short connection timeout for HTTP streams."""
    if not url.lower().startswith(("http://", "https://")) or "connection-timeout=" in url:
        return url
    return url + ("&" if "|" in url else "|") + "connection-timeout=" + str(CONNECT_TIMEOUT)


class Watcher(xbmc.Player):
    def __init__(self, on_failure, on_started=None):
        super().__init__()
        self.on_failure = on_failure
        # Called with the entry when its video starts, used by the TV player to update its channel bar.
        self.on_started = on_started
        self.current = None
        self.monitor = xbmc.Monitor()
        self.lock = threading.Lock()
        self.events = []
        self.watched = None
        # Set when Kodi reports that playback stopped, ended or failed.
        self.stop_seen = threading.Event()
        self.closed = False
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

    def play_channel(self, entry, windowed=False):
        """Play a channel. windowed keeps Kodi from switching to its own full screen player."""
        channel = entry["channel"]
        self.current = entry
        # A channel replaced while still opening did not fail, so it is no longer watched.
        with self.lock:
            self.watched = None
        # Stop the current channel first so its events are not mistaken for the new one. Kodi reports the stop
        # a moment after the player closes, so wait for that report. Taken for the new channel, it stopped it.
        if self.isPlaying():
            self.stop_seen.clear()
            self.stop()
            for _ in range(30):
                if self.stop_seen.is_set() or self.monitor.waitForAbort(0.1):
                    break
            self.monitor.waitForAbort(0.2)
        with self.lock:
            self.events = []
            self.watched = dict(entry, opened=time.time(), started=None, windowed=windowed)
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
        self.play(url, item, windowed)

    def is_playing(self, entry):
        """Whether this channel is the one playing now, or still opening."""
        try:
            playing = self.isPlaying() and m3u.base_url(self.getPlayingFile())
        except RuntimeError:
            return False
        return playing == m3u.base_url(entry["channel"]["url"])

    def loop(self):
        while not self.closed and not self.monitor.waitForAbort(0.5):
            with self.lock:
                events, self.events = self.events, []
                watched = self.watched
            if watched is None:
                continue
            failed = finished = started = False
            for event in events:
                if event == "started":
                    watched["started"] = time.time()
                    started = True
                elif event == "stopped":
                    # Stopping a channel that never started usually means it was not working.
                    failed = watched["started"] is None
                    finished = True
                elif event == "error":
                    failed = True
                elif event == "ended":
                    failed = watched["started"] is None or time.time() - watched["started"] < EARLY_END
                if failed or finished:
                    break
            if started and self.on_started:
                self.on_started(watched)
            if watched["started"]:
                finished = finished or time.time() - watched["started"] > EARLY_END
            elif not (failed or finished):
                finished = time.time() - watched["opened"] > OPEN_TIMEOUT
                if not watched.get("checked") and time.time() - watched["opened"] > CHECK_AFTER:
                    watched["checked"] = True
                    failed = probe.check(watched["channel"]["url"], CHECK_TIMEOUT) is not None
            if failed or finished:
                with self.lock:
                    # A channel requested meanwhile replaces this one.
                    if self.watched is not watched:
                        continue
                    self.watched = None
            if failed and not self.closed:
                if self.isPlaying() and watched["started"] is None:
                    self.stop()
                self.monitor.waitForAbort(1)
                if watched["windowed"]:
                    # The TV player reports the failure on its channel bar, so Kodi's own error notice is closed.
                    for _ in range(10):
                        if xbmc.getCondVisibility("Window.IsActive(okdialog)"):
                            xbmc.executebuiltin("Dialog.Close(okdialog,true)")
                            break
                        if self.closed or self.monitor.waitForAbort(0.3):
                            return
                else:
                    # Ask only after Kodi gave up opening the channel and closed its own error notice.
                    for _ in range(240):
                        if self.closed or self.monitor.waitForAbort(0.5):
                            return
                        if not self.isPlaying() and not xbmc.getCondVisibility("System.HasActiveModalDialog"):
                            break
                self.on_failure(watched)

    def shutdown(self):
        self.closed = True
        self.thread.join(2)
