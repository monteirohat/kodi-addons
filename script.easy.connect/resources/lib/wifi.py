"""Wi-Fi through connman, the network manager of LibreELEC, with its command line tool connmanctl.

connman keeps each known network in a folder of its storage, with a settings file that holds its name, whether it
connects by itself and its password. Connecting to a new network with a password needs an agent that answers the
question of connman for it; connect() runs connmanctl in a pseudo terminal and answers it.

Does not import Kodi modules, so it can be tested with a regular Python 3 interpreter:

    python3 resources/lib/wifi.py
"""

import json
import os
import pty
import re
import select
import shutil
import subprocess
import time

TIMEOUT = 15
CONNECT_TIMEOUT = 45
# Where LibreELEC keeps the state of connman; other systems use /var/lib/connman.
STORAGE = next((folder for folder in ("/storage/.cache/connman", "/var/lib/connman") if os.path.isdir(folder)),
               "/var/lib/connman")
CONNECTED_STATES = ("online", "ready")
# Kinds of security of connman, for the screen: open, WEP, a personal password, or the enterprise login of a company.
SECURITY = {"none": "open", "wep": "wep", "psk": "wpa", "ieee8021x": "enterprise"}


class WifiError(Exception):
    pass


def available():
    return shutil.which("connmanctl") is not None


def run(*args, timeout=TIMEOUT):
    """Run connmanctl and return what it printed. Raises WifiError when it reports an error."""
    try:
        result = subprocess.run(["connmanctl", *args], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as error:
        raise WifiError(str(error))
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0 or output.startswith("Error"):
        raise WifiError(output or "connmanctl %s failed" % args[0])
    return output


def properties(text):
    """The "Key = value" lines of connmanctl, with [ ... ] values as lists, or as dicts when they hold key=value."""
    found = {}
    for line in text.splitlines():
        if " = " not in line:
            continue
        key, value = line.strip().split(" = ", 1)
        if value.startswith("[") and value.endswith("]"):
            items = [item.strip() for item in value[1:-1].replace(",", " ").split() if item.strip()]
            if items and all("=" in item for item in items):
                value = dict(item.split("=", 1) for item in items)
            else:
                value = items
        found[key] = value
    return found


def powered():
    """Whether the Wi-Fi is on, or None when the device has no Wi-Fi."""
    for block in run("technologies").split("/net/connman/technology/")[1:]:
        if block.startswith("wifi"):
            return properties(block).get("Powered") == "True"
    return None


def set_powered(on):
    run("enable" if on else "disable", "wifi")


def scan():
    """Look for networks again. The list of services has them a few seconds later."""
    run("scan", "wifi", timeout=30)


def networks():
    """The Wi-Fi networks in range, strongest first: [{"id", "name", "known", "autoconnect", "connected", "state"}].
    Hidden networks, which have no name, are left out."""
    found = []
    for line in run("services").splitlines():
        fields = line.split()
        if not fields or not fields[-1].startswith("wifi_"):
            continue
        service_id = fields[-1]
        flags = line[:4]
        name = line[4:line.rindex(service_id)].strip()
        if not name:
            continue
        state = {"O": "online", "R": "ready", "a": "association", "c": "configuration", "d": "disconnect"}.get(flags[2], "idle")
        found.append({"id": service_id, "name": name, "known": flags[0] == "*", "autoconnect": flags[1] == "A",
                      "connected": state in CONNECTED_STATES, "state": state})
    return found


def details(service_id):
    """The properties of a network: Strength, Security, State, IPv4, Nameservers, Ethernet and more."""
    return properties(run("services", service_id))


def security(info):
    """"open", "wep", "wpa" or "enterprise", from the Security property of a network."""
    kinds = info.get("Security") or []
    for kind in ("ieee8021x", "psk", "wep", "none"):
        if kind in kinds:
            return SECURITY[kind]
    return "wpa"


def link(interface="wlan0"):
    """The radio link of the connection, from iw: {"frequency" in MHz, "signal" in dBm, "bitrate" in Mbps}."""
    try:
        output = subprocess.run(["iw", "dev", interface, "link"], capture_output=True, text=True, timeout=TIMEOUT).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    found = {}
    for key, pattern in (("frequency", r"freq:\s*([\d.]+)"), ("signal", r"signal:\s*(-?\d+)"), ("bitrate", r"tx bitrate:\s*([\d.]+)")):
        match = re.search(pattern, output)
        if match:
            found[key] = float(match.group(1))
    return found


def band(frequency):
    """(band, channel) of a frequency in MHz, as ("5 GHz", 108)."""
    if not frequency:
        return "", None
    if frequency < 2500:
        return "2.4 GHz", 14 if round(frequency) == 2484 else round((frequency - 2407) / 5)
    if frequency < 5925:
        return "5 GHz", round((frequency - 5000) / 5)
    return "6 GHz", round((frequency - 5950) / 5)


def read_settings(service_id):
    """The settings file of a known network, as a dict, or {}."""
    values = {}
    try:
        with open(os.path.join(STORAGE, service_id, "settings"), encoding="utf-8", errors="replace") as settings:
            for line in settings:
                if "=" in line and not line.startswith("["):
                    key, value = line.rstrip("\n").split("=", 1)
                    values[key] = value
    except OSError:
        pass
    return values


def password(service_id):
    """The password connman keeps for a network, or "" for an open network or one it does not know."""
    return read_settings(service_id).get("Passphrase", "")


def known():
    """The networks connman knows, in range or not, by name: [{"id", "name", "autoconnect", "modified"}]. A name
    known by more than one Wi-Fi adapter shows once, by the adapter of the device when it has it."""
    adapter = adapter_prefix()
    by_name = {}
    try:
        folders = sorted(os.listdir(STORAGE))
    except OSError:
        return []
    for folder in folders:
        if not folder.startswith("wifi_"):
            continue
        settings = read_settings(folder)
        if settings.get("Favorite") != "true" or not settings.get("Name"):
            continue
        entry = {"id": folder, "name": settings["Name"], "autoconnect": settings.get("AutoConnect") == "true",
                 "modified": settings.get("Modified", "")}
        current = by_name.get(entry["name"])
        if current is None or (adapter and folder.startswith(adapter) and not current["id"].startswith(adapter)):
            by_name[entry["name"]] = entry
    return sorted(by_name.values(), key=lambda entry: entry["name"].casefold())


def adapter_prefix():
    """The start of the service names of the Wi-Fi adapter of the device, as "wifi_dca6326d352a_", or ""."""
    for interface in sorted(os.listdir("/sys/class/net")) if os.path.isdir("/sys/class/net") else []:
        if os.path.isdir("/sys/class/net/%s/wireless" % interface):
            try:
                with open("/sys/class/net/%s/address" % interface) as address:
                    return "wifi_%s_" % address.read().strip().replace(":", "").lower()
            except OSError:
                pass
    return ""


def disconnect(service_id):
    run("disconnect", service_id)


def forget(service_id):
    """Remove a known network and its password."""
    run("config", service_id, "--remove")


def set_autoconnect(service_id, on):
    run("config", service_id, "--autoconnect", "yes" if on else "no")


def connect(service_id, passphrase=None):
    """Connect to a network. Without a passphrase, connman uses the one it knows, or none for an open network.
    Returns None when it connected, or the reason it did not: "password" when connman asked for a password it did
    not get or did not accept, or the message of connman."""
    if passphrase is None:
        try:
            run("connect", service_id, timeout=CONNECT_TIMEOUT)
        except WifiError as error:
            return "password" if "passphrase" in str(error).lower() or "invalid" in str(error).lower() else str(error)
        return None
    return connect_with_agent(service_id, passphrase)


def spawn(command):
    """Run an interactive command in a pseudo terminal, as at a terminal. Returns the process and the terminal to read
    and write. Kodi runs add-ons in subinterpreters, where os.fork and pty.fork are not allowed, so it uses subprocess."""
    terminal, child = pty.openpty()
    try:
        process = subprocess.Popen([command], stdin=child, stdout=child, stderr=child, start_new_session=True)
    finally:
        os.close(child)
    return process, terminal


def stop(process):
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def connect_with_agent(service_id, passphrase):
    """connmanctl in interactive mode, with its agent on, answering the question of the password."""
    process, fd = spawn("connmanctl")
    output = ""

    def read_until(patterns, seconds):
        nonlocal output
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            ready, _, _ = select.select([fd], [], [], 0.2)
            if ready:
                try:
                    output += os.read(fd, 4096).decode("utf-8", "replace")
                except OSError:
                    return None
            for pattern in patterns:
                if pattern in output:
                    return pattern
        return None

    def send(text):
        os.write(fd, (text + "\n").encode("utf-8"))

    try:
        read_until(["connmanctl>"], 5)
        send("agent on")
        read_until(["Agent registered"], 5)
        output = ""
        send("connect " + service_id)
        asked = False
        while True:
            found = read_until(["Passphrase?", "Retry (yes/no)?", "Connected " + service_id, "Error"], CONNECT_TIMEOUT)
            if found == "Passphrase?" and not asked:
                asked = True
                output = ""
                send(passphrase)
            elif found and found.startswith("Connected"):
                return None
            elif found == "Retry (yes/no)?" or found == "Passphrase?":
                # A wrong password: connman asks again.
                send("no")
                return "password"
            elif found == "Error":
                read_until(["\n"], 1)
                message = output[output.index("Error"):].splitlines()[0].strip()
                return "password" if "invalid" in message.lower() or "passphrase" in message.lower() else message
            else:
                return "timeout"
    finally:
        try:
            send("quit")
            read_until(["\x00"], 0.5)
        except OSError:
            pass
        try:
            os.close(fd)
        except OSError:
            pass
        stop(process)


if __name__ == "__main__":
    # Prints what the window shows, without the passwords.
    current = next((network for network in networks() if network["connected"]), None)
    report = {"powered": powered(), "networks": networks()[:8], "known": known()}
    if current:
        report["current"] = dict(details(current["id"]), link=link(), password_saved=bool(password(current["id"])))
    print(json.dumps(report, indent=2, ensure_ascii=False))
