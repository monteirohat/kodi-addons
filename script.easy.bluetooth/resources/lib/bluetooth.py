"""Bluetooth through BlueZ with its command line tool bluetoothctl.

Short commands, as connect or info, run bluetoothctl once each. Looking for devices and pairing run it in a pseudo
terminal, in a Session: it reports the devices it finds as they appear, and asks the questions of pairing, as a passkey
to confirm or a PIN to type, which Session hands to the window.

Does not import Kodi modules, so it can be tested with a regular Python 3 interpreter:

    python3 resources/lib/bluetooth.py
"""

import json
import os
import pty
import re
import select
import shutil
import subprocess
import threading
import time

TIMEOUT = 15
PAIR_TIMEOUT = 60
# LibreELEC starts its Bluetooth service only while this file exists, which its settings create and delete.
SERVICE_FILE = "/storage/.cache/services/bluez.conf"
ADDRESS = re.compile(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|[\x01\x02]")
# The kind of a device, from the icon name BlueZ gives it.
KINDS = {"audio-headset": "headphones", "audio-headphones": "headphones", "audio-card": "speaker",
         "input-keyboard": "keyboard", "input-mouse": "mouse", "input-tablet": "mouse", "input-gaming": "gamepad",
         "phone": "phone", "computer": "computer", "video-display": "tv", "multimedia-player": "tv", "printer": "printer"}


class BluetoothError(Exception):
    pass


def available():
    return shutil.which("bluetoothctl") is not None


def clean(text):
    return ANSI.sub("", text).replace("\r", "\n")


def run(*args, timeout=TIMEOUT):
    """Run bluetoothctl once and return what it printed, without colors and the notices it prints when it starts."""
    try:
        result = subprocess.run(["bluetoothctl", *args], capture_output=True, text=True, timeout=timeout,
                                stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as error:
        raise BluetoothError(str(error))
    lines = [line for line in clean(result.stdout + result.stderr).splitlines()
             if line.strip() and not line.startswith(("[NEW]", "[CHG]", "[DEL]", "\tSupportedUUIDs"))]
    output = "\n".join(lines).strip()
    if result.returncode != 0 or re.search(r"^(Failed|No default controller|Device .* not available)", output, re.M):
        raise BluetoothError(output or "bluetoothctl %s failed" % args[0])
    return output


def service_active():
    try:
        return subprocess.run(["systemctl", "is-active", "--quiet", "bluetooth"], timeout=TIMEOUT).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def start_service():
    """Turn on the Bluetooth service of LibreELEC, as its settings do, and wait for its adapter."""
    if os.path.isdir(os.path.dirname(SERVICE_FILE)) and not os.path.exists(SERVICE_FILE):
        with open(SERVICE_FILE, "w"):
            pass
    subprocess.run(["systemctl", "start", "bluetooth"], timeout=30)
    for _ in range(20):
        if adapter():
            return
        time.sleep(0.5)


def fields(text):
    """The "Key: value" lines of bluetoothctl. Repeated keys, as UUID, become lists."""
    found = {}
    for line in text.splitlines():
        if ":" not in line or not line.startswith("\t"):
            continue
        key, value = line.strip().split(":", 1)
        value = value.strip()
        if key in found:
            found[key] = (found[key] if isinstance(found[key], list) else [found[key]]) + [value]
        else:
            found[key] = value
    return found


def number(value):
    """The number in parentheses of a value of bluetoothctl, as -60 in "0xffffffc4 (-60)", or None."""
    match = re.search(r"\((-?\d+)\)", value or "")
    return int(match.group(1)) if match else None


def adapter():
    """The Bluetooth adapter of the device: {"address", "name", "powered", "discoverable", "discovering"}, or None."""
    try:
        output = run("show")
    except BluetoothError:
        return None
    match = re.search(r"Controller (%s)" % ADDRESS.pattern, output)
    if not match:
        return None
    values = fields(output)
    return {"address": match.group(1), "name": values.get("Alias") or values.get("Name", ""),
            "powered": values.get("Powered") == "yes", "discoverable": values.get("Discoverable") == "yes",
            "discovering": values.get("Discovering") == "yes"}


def set_powered(on):
    run("power", "on" if on else "off")


def nameless(name, address):
    """BlueZ names a device that has not said its name after its address, with dashes."""
    return not name or name.replace("-", ":").upper() == address.upper()


def devices(which=None):
    """The devices BlueZ knows, or only the "Paired" or "Connected" ones: [(address, name)]."""
    output = run("devices", *([which] if which else []))
    found = []
    for line in output.splitlines():
        match = re.match(r"Device (%s) ?(.*)$" % ADDRESS.pattern, line.strip())
        if match:
            found.append((match.group(1), match.group(2).strip()))
    return found


def info(address):
    """A device: {"address", "name", "kind", "paired", "trusted", "connected", "battery", "rssi"}."""
    values = fields(run("info", address))
    name = values.get("Alias") or values.get("Name") or ""
    return {"address": address, "name": "" if nameless(name, address) else name,
            "kind": KINDS.get(values.get("Icon", ""), "other"), "paired": values.get("Paired") == "yes",
            "trusted": values.get("Trusted") == "yes", "connected": values.get("Connected") == "yes",
            "battery": number(values.get("Battery Percentage")), "rssi": number(values.get("RSSI"))}


def paired():
    """The paired devices, connected first, then by name."""
    found = []
    for address, _ in devices("Paired"):
        try:
            found.append(info(address))
        except BluetoothError:
            continue
    return sorted(found, key=lambda device: (not device["connected"], (device["name"] or device["address"]).casefold()))


def connect(address):
    run("connect", address, timeout=30)


def disconnect(address):
    run("disconnect", address)


def set_trusted(address, on):
    """A trusted device connects by itself when it turns on."""
    run("trust" if on else "untrust", address)


def remove(address):
    """Forget a device: it has to pair again to connect."""
    run("remove", address)


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


class Session:
    """bluetoothctl in interactive mode, with its agent on: looks for devices and pairs them.

    found holds the devices seen while looking, by address: {"address", "name", "rssi"}."""

    def __init__(self):
        self.process, self.fd = spawn("bluetoothctl")
        self.buffer = ""
        self.found = {}
        self.lock = threading.Condition()
        self.closed = False
        threading.Thread(target=self.read, daemon=True).start()
        self.send("agent on")
        self.send("default-agent")

    def send(self, command):
        os.write(self.fd, (command + "\n").encode("utf-8"))

    def read(self):
        pending = ""
        while not self.closed:
            try:
                ready, _, _ = select.select([self.fd], [], [], 0.3)
                if not ready:
                    continue
                data = os.read(self.fd, 65536).decode("utf-8", "replace")
            except OSError:
                break
            text = clean(data)
            pending += text
            *lines, pending = pending.split("\n")
            with self.lock:
                # Questions wait on a line without an end, so the waiting pair reads everything as it comes.
                self.buffer += text
                for line in lines:
                    self.event(line)
                self.lock.notify_all()

    def event(self, line):
        """Keep the devices that appear, change or leave while looking."""
        match = re.search(r"\[(NEW|CHG|DEL)\] Device (%s) ?(.*)$" % ADDRESS.pattern, line)
        if not match:
            return
        change, address, rest = match.groups()
        if change == "DEL":
            self.found.pop(address, None)
            return
        device = self.found.setdefault(address, {"address": address, "name": "", "rssi": None})
        if change == "NEW":
            device["name"] = "" if nameless(rest.strip(), address) else rest.strip()
        elif rest.startswith("RSSI:"):
            device["rssi"] = number(rest)
        elif rest.startswith(("Name:", "Alias:")):
            name = rest.split(":", 1)[1].strip()
            if not nameless(name, address):
                device["name"] = name

    def scan(self, on):
        self.send("scan on" if on else "scan off")

    def wait(self, patterns, seconds):
        """The first pattern found in what bluetoothctl printed since the last wait, with its match, or (None, None)."""
        end = time.monotonic() + seconds
        with self.lock:
            while True:
                for pattern in patterns:
                    match = re.search(pattern, self.buffer)
                    if match:
                        self.buffer = self.buffer[match.end():]
                        return pattern, match
                left = end - time.monotonic()
                if left <= 0 or self.closed:
                    return None, None
                self.lock.wait(left)

    def pair(self, address, ask):
        """Pair a device, answering the questions of the agent with ask(kind, value): "confirm" with a passkey, which
        returns whether it matches; "pin" or "passkey", which return what was typed, or None; "display" with a
        passkey to type on the device, which returns nothing. Returns None when it paired, or the reason it did not."""
        with self.lock:
            self.buffer = ""
        self.send("pair " + address)
        questions = [r"Confirm passkey (\d+)", r"Request confirmation", r"Enter PIN code:", r"Enter passkey[^:]*:",
                     r"(?:Passkey|PIN code): (\d+)", r"Authorize service", r"Accept pairing", r"Pairing successful",
                     r"Failed to pair: (\S+)", r"Device %s not available" % re.escape(address)]
        while True:
            found, match = self.wait(questions, PAIR_TIMEOUT)
            if found is None:
                self.send("no")
                return "timeout"
            if found.startswith("Confirm passkey"):
                self.send("yes" if ask("confirm", match.group(1)) else "no")
            elif found == r"Request confirmation":
                self.send("yes")
            elif found.startswith("Enter PIN"):
                self.send(ask("pin", None) or "")
            elif found.startswith("Enter passkey"):
                self.send(ask("passkey", None) or "")
            elif found.startswith("(?:Passkey"):
                ask("display", match.group(1))
            elif found in (r"Authorize service", r"Accept pairing"):
                self.send("yes")
            elif found == r"Pairing successful":
                return None
            elif found.startswith("Failed"):
                reason = match.group(1)
                return "rejected" if "Authentication" in reason or "Rejected" in reason else reason
            else:
                return "gone"

    def close(self):
        if self.closed:
            return
        try:
            self.send("scan off")
            self.send("quit")
        except OSError:
            pass
        self.closed = True
        time.sleep(0.3)
        try:
            os.close(self.fd)
        except OSError:
            pass
        stop(self.process)


if __name__ == "__main__":
    # Prints the adapter, the paired devices and the named devices found in 10 seconds.
    session = Session()
    session.scan(True)
    time.sleep(10)
    session.scan(False)
    found = [device for device in session.found.values() if device["name"]]
    session.close()
    print(json.dumps({"service": service_active(), "adapter": adapter(), "paired": paired(), "found": found},
                     indent=2, ensure_ascii=False))
