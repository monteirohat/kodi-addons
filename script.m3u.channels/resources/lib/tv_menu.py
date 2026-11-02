"""Background service that opens Easy Channel when the TV entry of the main menu is selected."""

import xbmc
import xbmcaddon
import xbmcgui


ADDON_ID = "script.m3u.channels"
RUNNING_PROPERTY = ADDON_ID + ".running"
# Kodi's own TV screens, opened by the TV entry when a PVR add-on is enabled.
TV_WINDOWS = "Window.IsActive(tvchannels) | Window.IsActive(tvguide)"
# Without a PVR add-on, the TV entry only shows a notice in an OK dialog over the main menu.
TV_NOTICE = "Window.IsActive(okdialog) + Window.IsVisible(home)"
# Estuary's main menu is container 9000, and its TV entry has the id livetv.
MENU_ENTRY = "Container(9000).ListItem.Property(id)"
POLL_SECONDS = 0.2


class Monitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        self.read_settings()

    def onSettingsChanged(self):
        self.read_settings()

    def read_settings(self):
        self.enabled = xbmcaddon.Addon(ADDON_ID).getSettingBool("tv_menu")


def run():
    monitor = Monitor()
    home = xbmcgui.Window(10000)
    menu_entry = ""
    while not monitor.waitForAbort(POLL_SECONDS):
        if not monitor.enabled or home.getProperty(RUNNING_PROPERTY):
            continue
        # Inside a dialog the menu cannot be read, so remember the entry focused before it opened.
        if xbmc.getCondVisibility("Window.IsActive(home) + !System.HasActiveModalDialog"):
            menu_entry = xbmc.getInfoLabel(MENU_ENTRY)
        if menu_entry == "livetv" and xbmc.getCondVisibility(TV_NOTICE):
            xbmc.executebuiltin("Dialog.Close(okdialog,true)")
        elif xbmc.getCondVisibility(TV_WINDOWS):
            # Leave the TV screen so closing Easy Channel returns to the main menu.
            xbmc.executebuiltin("ActivateWindow(home)")
        else:
            continue
        home.setProperty(RUNNING_PROPERTY, "starting")
        xbmc.executebuiltin("RunAddon(" + ADDON_ID + ")")
        # Wait until the add-on has taken over, so the same TV screen is not handled twice.
        for _ in range(50):
            if monitor.waitForAbort(0.2) or home.getProperty(RUNNING_PROPERTY) == "open":
                break
        if home.getProperty(RUNNING_PROPERTY) == "starting":
            home.clearProperty(RUNNING_PROPERTY)
