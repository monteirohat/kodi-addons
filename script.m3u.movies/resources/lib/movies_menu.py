"""Background service that opens Easy Movie from the Movies and TV shows entries of the main menu.

It also runs the torrent engine: unfinished downloads resume when Kodi starts, and the engine stops with Kodi. It
keeps the files picked from torrents, as episodes of a season pack, downloading alone once their metadata arrives. And
it downloads the direct links of the catalog, so they go on after Easy Movie closes.
"""

import os
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import direct, torrents


ADDON_ID = "script.m3u.movies"
RUNNING_PROPERTY = ADDON_ID + ".running"
# Estuary's main menu is container 9000. Its Movies and TV shows entries have the ids movies and tvshows.
MENU_ENTRY = "Container(9000).ListItem.Property(id)"
# With an empty library, these entries open the video sources. Kodi's own library is left alone.
ENTRIES = {
    "movies": ("movies_menu", "Window.IsActive(videos) + !Library.HasContent(movies)", "RunAddon(" + ADDON_ID + ")"),
    "tvshows": ("series_menu", "Window.IsActive(videos) + !Library.HasContent(tvshows)", "RunScript(" + ADDON_ID + ",series)"),
}
POLL_SECONDS = 0.2
# The videos screen counts as opened from the menu only when it appears this soon after leaving it.
MENU_SECONDS = 3
# Seconds between checks of the files picked from torrents.
PICKS_SECONDS = 15


class Monitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        self.read_settings()

    def onSettingsChanged(self):
        self.read_settings()

    def read_settings(self):
        addon = xbmcaddon.Addon(ADDON_ID)
        self.enabled = {setting: addon.getSettingBool(setting) for setting, _, _ in ENTRIES.values()}


def downloads_engine():
    """The torrent engine when there are saved downloads to resume, or None."""
    addon = xbmcaddon.Addon(ADDON_ID)
    data_path = os.path.join(xbmcvfs.translatePath(addon.getAddonInfo("profile")), "torrest")
    folder = addon.getSetting("download_folder")
    saved = os.path.join(data_path, "torrents")
    if not folder or not os.path.isdir(saved) or not os.listdir(saved):
        return None
    return torrents.Engine(addon.getAddonInfo("path"), data_path, android=xbmc.getCondVisibility("System.Platform.Android"))


def resume_downloads():
    addon = xbmcaddon.Addon(ADDON_ID)
    engine = downloads_engine()
    if engine and addon.getSettingBool("resume_downloads"):
        try:
            engine.start(addon.getSetting("download_folder"), {"max_upload_rate": max(addon.getSettingInt("upload_limit"), 0) * 1024})
        except torrents.EngineError as error:
            xbmc.log("Easy Movie: could not resume downloads: %s" % error, xbmc.LOGWARNING)


def stop_downloads():
    """Stop the engine, whoever started it, so the downloads are saved before Kodi quits."""
    addon = xbmcaddon.Addon(ADDON_ID)
    data_path = os.path.join(xbmcvfs.translatePath(addon.getAddonInfo("profile")), "torrest")
    torrents.Engine(addon.getAddonInfo("path"), data_path).stop()


def picked_files():
    """Download the files picked from torrents and stop the others, as the metadata of a torrent arrives after Easy
    Movie closed. See torrents.read_picks."""
    addon = xbmcaddon.Addon(ADDON_ID)
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    path = os.path.join(profile, "picks.json")
    engine = torrents.Engine(addon.getAddonInfo("path"), os.path.join(profile, "torrest"))
    monitor = xbmc.Monitor()
    while not monitor.waitForAbort(PICKS_SECONDS):
        picks = torrents.read_picks(path)
        if not picks or not engine.running():
            continue
        for info_hash, pick in picks.items():
            try:
                engine.apply_picks(info_hash, pick)
            except torrents.EngineError as error:
                xbmc.log("Easy Movie: could not apply the files picked from %s: %s" % (info_hash, error), xbmc.LOGWARNING)


def direct_downloads():
    """Download the queued direct links, one at a time, until Kodi quits."""
    addon = xbmcaddon.Addon(ADDON_ID)
    monitor = xbmc.Monitor()
    runner = direct.Runner(os.path.join(xbmcvfs.translatePath(addon.getAddonInfo("profile")), "direct"), monitor.abortRequested)
    while not monitor.abortRequested():
        try:
            busy = runner.step()
        except Exception as error:
            xbmc.log("Easy Movie: direct download failed: %s" % error, xbmc.LOGWARNING)
            busy = False
        if not busy and monitor.waitForAbort(2):
            break


def run():
    threading.Thread(target=resume_downloads, daemon=True).start()
    threading.Thread(target=direct_downloads, daemon=True).start()
    threading.Thread(target=picked_files, daemon=True).start()
    try:
        watch_menu()
    finally:
        stop_downloads()


def watch_menu():
    monitor = Monitor()
    home = xbmcgui.Window(10000)
    menu_entry, seen = "", 0
    while not monitor.waitForAbort(POLL_SECONDS):
        if home.getProperty(RUNNING_PROPERTY):
            continue
        if xbmc.getCondVisibility("Window.IsActive(home) + !System.HasActiveModalDialog"):
            menu_entry, seen = xbmc.getInfoLabel(MENU_ENTRY), time.time()
            continue
        if menu_entry not in ENTRIES or time.time() - seen > MENU_SECONDS:
            continue
        setting, screen, command = ENTRIES[menu_entry]
        if not monitor.enabled[setting] or not xbmc.getCondVisibility(screen):
            continue
        menu_entry = ""
        xbmc.executebuiltin("ActivateWindow(home)")
        home.setProperty(RUNNING_PROPERTY, "starting")
        xbmc.executebuiltin(command)
        # Wait until the add-on has taken over, so the same screen is not handled twice.
        for _ in range(50):
            if monitor.waitForAbort(0.2) or home.getProperty(RUNNING_PROPERTY) == "open":
                break
        if home.getProperty(RUNNING_PROPERTY) == "starting":
            home.clearProperty(RUNNING_PROPERTY)
