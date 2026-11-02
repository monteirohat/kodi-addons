"""Background service that opens Easy Movie when the Movies entry of the main menu is selected."""

import time

import xbmc
import xbmcaddon
import xbmcgui


ADDON_ID = "script.m3u.movies"
RUNNING_PROPERTY = ADDON_ID + ".running"
# Estuary's main menu is container 9000, and its Movies entry has the id movies.
MENU_ENTRY = "Container(9000).ListItem.Property(id)"
# With an empty movie library, the Movies entry opens the video sources. Kodi's own library is left alone.
MOVIES_SCREEN = "Window.IsActive(videos) + !Library.HasContent(movies)"
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
        self.enabled = xbmcaddon.Addon(ADDON_ID).getSettingBool("movies_menu")


def run():
    monitor = Monitor()
    home = xbmcgui.Window(10000)
    menu_entry, seen = "", 0
    while not monitor.waitForAbort(POLL_SECONDS):
        if not monitor.enabled or home.getProperty(RUNNING_PROPERTY):
            continue
        if xbmc.getCondVisibility("Window.IsActive(home) + !System.HasActiveModalDialog"):
            menu_entry, seen = xbmc.getInfoLabel(MENU_ENTRY), time.time()
            continue
        if menu_entry != "movies" or time.time() - seen > MENU_SECONDS:
            continue
        if not xbmc.getCondVisibility(MOVIES_SCREEN):
            continue
        menu_entry = ""
        xbmc.executebuiltin("ActivateWindow(home)")
        home.setProperty(RUNNING_PROPERTY, "starting")
        xbmc.executebuiltin("RunAddon(" + ADDON_ID + ")")
        # Wait until the add-on has taken over, so the same screen is not handled twice.
        for _ in range(50):
            if monitor.waitForAbort(0.2) or home.getProperty(RUNNING_PROPERTY) == "open":
                break
        if home.getProperty(RUNNING_PROPERTY) == "starting":
            home.clearProperty(RUNNING_PROPERTY)
