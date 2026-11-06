"""Keeps the icon of the connection for the home screen of the Monteiro skin: the Wi-Fi signal, a cable, or no
connection. The skin reads it from the window property EasyConnect.Icon of the home screen."""

import xbmc
import xbmcgui

from resources.lib import status

UPDATE_SECONDS = 10


def main():
    home = xbmcgui.Window(10000)
    monitor = xbmc.Monitor()
    shown = None
    while not monitor.abortRequested():
        icon = status.icon()
        if icon != shown:
            home.setProperty("EasyConnect.Icon", icon)
            shown = icon
        if monitor.waitForAbort(UPDATE_SECONDS):
            break
    home.clearProperty("EasyConnect.Icon")


main()
