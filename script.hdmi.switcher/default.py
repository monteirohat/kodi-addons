import fcntl
import glob
import os
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import xbmc
import xbmcgui
import xbmcvfs


TITLE = "HDMI Switcher"
DISPLAYS = [
    ("Small display (7-inch) — HDMI 1", "HDMI-A-1"),
    ("External monitor — HDMI 2", "HDMI-A-2"),
]


def atomic_write(path, data):
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=".hdmi-switcher-", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_path, str(path))
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def configure_monitor(original, connector):
    if original is None:
        root = ET.Element("advancedsettings")
    else:
        # Keep comments and existing settings when updating the connector.
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        root = ET.fromstring(original, parser=parser)
    if root.tag != "advancedsettings":
        raise ValueError("Unexpected root element in advancedsettings.xml.")

    sections = root.findall("videoscreen")
    if len(sections) > 1:
        raise ValueError("Multiple videoscreen sections found. Review advancedsettings.xml.")
    section = sections[0] if sections else ET.SubElement(root, "videoscreen")
    monitors = section.findall("monitor")
    if len(monitors) > 1:
        raise ValueError("Multiple monitor settings found. Review advancedsettings.xml.")
    monitor = monitors[0] if monitors else ET.SubElement(section, "monitor")
    monitor.text = connector
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def switch_display(dialog, profile_directory):
    os_release = Path("/etc/os-release")
    if not os_release.is_file() or 'ID="libreelec"' not in os_release.read_text():
        dialog.ok(TITLE, "This add-on requires LibreELEC.")
        return

    boot_options = Path("/proc/cmdline").read_text().split()
    disabled_outputs = {"video=HDMI-A-1:d", "video=HDMI-A-2:d"}
    if disabled_outputs.intersection(boot_options):
        dialog.ok(
            TITLE,
            "An HDMI output is disabled at boot. Remove the HDMI video overrides "
            "from /flash/cmdline.txt and reboot once. See the README for instructions.",
        )
        return

    selected_index = dialog.select(TITLE, [display[0] for display in DISPLAYS])
    if selected_index < 0:
        return
    label, connector = DISPLAYS[selected_index]
    status_files = glob.glob("/sys/class/drm/*-" + connector + "/status")
    connected = any(
        Path(status_file).read_text().strip() == "connected"
        for status_file in status_files
    )
    if not connected:
        dialog.ok(TITLE, "The selected display was not detected. Turn it on and check its HDMI cable.")
        return
    if not dialog.yesno(
        TITLE,
        "Switch to " + label + "? Kodi will restart and stop any current playback.",
    ):
        return

    settings_path = profile_directory / "advancedsettings.xml"
    original = settings_path.read_bytes() if settings_path.exists() else None
    updated = configure_monitor(original, connector)
    if original is not None:
        backup_path = profile_directory / "advancedsettings.xml.hdmi-switcher.bak"
        try:
            with backup_path.open("xb") as output:
                output.write(original)
        except FileExistsError:
            pass

    atomic_write(settings_path, updated)
    try:
        # Submit the restart without waiting for the Kodi process to terminate.
        subprocess.run(
            ["systemctl", "--no-block", "restart", "kodi.service"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except Exception:
        if original is None:
            settings_path.unlink()
        else:
            atomic_write(settings_path, original)
        raise


def main():
    dialog = xbmcgui.Dialog()
    profile_directory = Path(xbmcvfs.translatePath("special://profile/"))
    profile_directory.mkdir(parents=True, exist_ok=True)
    with (profile_directory / ".hdmi-switcher.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            dialog.ok(TITLE, "Another display switch is already in progress.")
            return
        try:
            switch_display(dialog, profile_directory)
        except Exception as error:
            xbmc.log("HDMI Switcher: " + str(error), xbmc.LOGERROR)
            dialog.ok(TITLE, "Unable to switch displays. " + str(error))


if __name__ == "__main__":
    main()
