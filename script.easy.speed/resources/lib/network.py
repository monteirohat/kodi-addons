"""Checks of the connection, from the device to the internet: network, router, DNS and internet.

On Linux, as LibreELEC, the network, the router and the Wi-Fi signal come from /proc and /sys. Elsewhere the window
passes what Kodi knows of them.

Does not import Kodi modules, so it can be tested with a regular Python 3 interpreter:

    python3 resources/lib/network.py
"""

import json
import os
import re
import socket
import struct
import subprocess
import time
import urllib.request

TIMEOUT = 5
DNS_NAME = "fast.com"
# Answers 204 with an empty body. Anything else means a page in the way, as the login of a hotel network.
CONNECTIVITY_URL = "http://connectivitycheck.gstatic.com/generate_204"

OK, WARNING, FAILED = "ok", "warning", "failed"


def default_route():
    """(interface, gateway) of the default route, from /proc/net/route, or (None, None)."""
    try:
        with open("/proc/net/route") as routes:
            next(routes)
            for line in routes:
                fields = line.split()
                if len(fields) > 3 and fields[1] == "00000000" and int(fields[3], 16) & 2:
                    return fields[0], socket.inet_ntoa(struct.pack("<L", int(fields[2], 16)))
    except (OSError, ValueError, StopIteration):
        pass
    return None, None


def local_address():
    """The address the device uses to reach the internet. Connecting a UDP socket sends nothing."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 53))
            return probe.getsockname()[0]
    except OSError:
        return ""


def wifi_signal(interface):
    """The signal of a Wi-Fi interface in dBm, from /proc/net/wireless, or None."""
    try:
        with open("/proc/net/wireless") as wireless:
            for line in wireless:
                if line.strip().startswith(interface + ":"):
                    return int(float(line.split()[3]))
    except (OSError, ValueError, IndexError):
        pass
    return None


def signal_percent(dbm):
    """-90 dBm or less is 0%, -40 dBm or more is 100%."""
    return max(0, min(100, round((dbm + 90) * 2)))


def wifi_name():
    """The name of the Wi-Fi network, from connman on LibreELEC or iw elsewhere, or ""."""
    for command, pattern in ((["connmanctl", "services"], r"^\*A[OR]\s+(.+?)\s+wifi_"), (["iw", "dev"], r"^\s*ssid (.+)$")):
        try:
            output = subprocess.run(command, capture_output=True, text=True, timeout=TIMEOUT).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        found = re.search(pattern, output, re.M)
        if found:
            return found.group(1).strip()
    return ""


def link_speed(interface):
    """The speed of a cable link in Mbps, as 100 or 1000, or None."""
    try:
        with open("/sys/class/net/%s/speed" % interface) as speed:
            value = int(speed.read().strip())
            return value if value > 0 else None
    except (OSError, ValueError):
        return None


def connection(kodi=None):
    """What the device is connected by: {"kind": "wifi" | "cable" | "", "interface", "address", "gateway", "name",
    "signal", "speed"}. kodi holds the address and gateway Kodi knows, used when /proc has none."""
    kodi = kodi or {}
    interface, gateway = default_route()
    info = {"kind": "", "interface": interface or "", "address": local_address() or kodi.get("address", ""),
            "gateway": gateway or kodi.get("gateway", ""), "name": "", "signal": None, "speed": None}
    if interface:
        if os.path.isdir("/sys/class/net/%s/wireless" % interface) or interface.startswith("wl"):
            dbm = wifi_signal(interface)
            info.update(kind="wifi", name=wifi_name(), signal=signal_percent(dbm) if dbm is not None else None)
        else:
            info.update(kind="cable", speed=link_speed(interface))
    return info


def reach(host):
    """The time to reach a host of the local network in milliseconds, or None. Uses ping, or a TCP connection: a
    refused connection still means the host answered."""
    try:
        start = time.monotonic()
        result = subprocess.run(["ping", "-c", "1", "-W", "2", host], capture_output=True, text=True, timeout=TIMEOUT)
        if result.returncode == 0:
            found = re.search(r"time[=<]([\d.]+)", result.stdout)
            return float(found.group(1)) if found else (time.monotonic() - start) * 1000
    except (OSError, subprocess.SubprocessError):
        pass
    for port in (80, 443, 53):
        start = time.monotonic()
        try:
            socket.create_connection((host, port), timeout=2).close()
        except ConnectionRefusedError:
            pass
        except OSError:
            continue
        return (time.monotonic() - start) * 1000
    return None


def resolve(name=DNS_NAME):
    """The time to find the address of a name in milliseconds, or None."""
    start = time.monotonic()
    try:
        socket.getaddrinfo(name, 443, proto=socket.IPPROTO_TCP)
    except OSError:
        return None
    return (time.monotonic() - start) * 1000


def internet():
    """(state, milliseconds): OK when the check page answers as it should, WARNING when another page answers in its
    place, FAILED when nothing answers."""
    start = time.monotonic()
    try:
        with urllib.request.urlopen(CONNECTIVITY_URL, timeout=TIMEOUT) as response:
            status = response.status
            response.read()
    except Exception:
        return FAILED, None
    return (OK if status == 204 else WARNING), (time.monotonic() - start) * 1000


def diagnose(kodi=None):
    """The checks in order: [{"check", "state", ...}]. A check that cannot pass because an earlier one failed is
    skipped, so the first failed check is where the problem is."""
    info = connection(kodi)
    checks = []
    if not info["address"]:
        checks.append(dict(check="network", state=FAILED, **info))
        return checks
    weak = info["kind"] == "wifi" and info["signal"] is not None and info["signal"] < 40
    checks.append(dict(check="network", state=WARNING if weak else OK, **info))
    router = reach(info["gateway"]) if info["gateway"] else None
    checks.append({"check": "router", "state": OK if router is not None else FAILED, "gateway": info["gateway"],
                   "time": router})
    dns = resolve()
    checks.append({"check": "dns", "state": OK if dns is not None else FAILED, "time": dns})
    if dns is None:
        return checks
    state, elapsed = internet()
    checks.append({"check": "internet", "state": state, "time": elapsed})
    if router is None and state == OK:
        # Some routers answer neither ping nor connections, but the internet passing through them shows they work.
        checks[1]["state"] = OK
    return checks


if __name__ == "__main__":
    print(json.dumps(diagnose(), indent=2))
