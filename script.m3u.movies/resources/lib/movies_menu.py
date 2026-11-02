"""Background service that opens Easy Movie from the Movies and TV shows entries of the main menu."""

import time

import xbmc
import xbmcaddon
import xbmcgui


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


class Monitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        self.read_settings()

    def onSettingsChanged(self):
        self.read_settings()

    def read_settings(self):
        addon = xbmcaddon.Addon(ADDON_ID)
        self.enabled = {setting: addon.getSettingBool(setting) for setting, _, _ in ENTRIES.values()}


def run():
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
