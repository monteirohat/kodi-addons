"""The icon of the connection, from /proc and /sys, cheap enough to read every few seconds: wifi-0.png to wifi-3.png
for the Wi-Fi signal, cable.png for a cable, or wifi-off.png without a connection. The names are the ones of the media
of the Monteiro skin.

Does not import Kodi modules, so it can be tested with a regular Python 3 interpreter.
"""

import os


def default_interface():
    """The interface of the default route, from /proc/net/route, or None."""
    try:
        with open("/proc/net/route") as routes:
            next(routes)
            for line in routes:
                fields = line.split()
                if len(fields) > 3 and fields[1] == "00000000" and int(fields[3], 16) & 2:
                    return fields[0]
    except (OSError, ValueError, StopIteration):
        pass
    return None


def wifi_dbm(interface):
    """The signal of a Wi-Fi interface in dBm, from /proc/net/wireless, or None."""
    try:
        with open("/proc/net/wireless") as wireless:
            for line in wireless:
                if line.strip().startswith(interface + ":"):
                    return int(float(line.split()[3]))
    except (OSError, ValueError, IndexError):
        pass
    return None


def icon():
    interface = default_interface()
    if not interface:
        return "wifi-off.png"
    if not os.path.isdir("/sys/class/net/%s/wireless" % interface):
        return "cable.png"
    dbm = wifi_dbm(interface)
    if dbm is None:
        return "wifi-3.png"
    # -90 dBm or less is 0%, -40 dBm or more is 100%, the scale of Easy Speed; the levels are the ones of Easy Connect.
    strength = max(0, min(100, (dbm + 90) * 2))
    return "wifi-%d.png" % (3 if strength >= 70 else 2 if strength >= 45 else 1 if strength >= 20 else 0)
