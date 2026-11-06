"""Keeps the icon of the Bluetooth for the home screen of the Monteiro skin: off, on, or with a device connected. The
skin reads it from the window property EasyBluetooth.Icon of the home screen, which the window of Easy Bluetooth also
sets as soon as it turns the Bluetooth on or off."""

import xbmc
import xbmcgui

from resources.lib import bluetooth

UPDATE_SECONDS = 10


def main():
    home = xbmcgui.Window(10000)
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        if bluetooth.available():
            icon = bluetooth.icon()
            if home.getProperty("EasyBluetooth.Icon") != icon:
                home.setProperty("EasyBluetooth.Icon", icon)
        if monitor.waitForAbort(UPDATE_SECONDS):
            break
    home.clearProperty("EasyBluetooth.Icon")


main()
