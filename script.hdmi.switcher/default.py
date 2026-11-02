import fcntl
import glob
import os
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs


ADDON = xbmcaddon.Addon()
PATH = ADDON.getAddonInfo("path")
CARDS = 100
ACTION_BACK = (10, 92)
# Name and port description string IDs, and the connector of each display card.
DISPLAYS = [
    (30010, 30012, "HDMI-A-1"),
    (30011, 30013, "HDMI-A-2"),
]


def text(string_id, *arguments):
    return ADDON.getLocalizedString(string_id).format(*arguments)


TITLE = text(30000)


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


def is_connected(connector):
    status_files = glob.glob("/sys/class/drm/*-" + connector + "/status")
    return any(Path(status_file).read_text().strip() == "connected" for status_file in status_files)


def active_connector(original):
    """Connector configured in advancedsettings.xml, or None when Kodi uses its default display."""
    if original is None:
        return None
    try:
        root = ET.fromstring(original)
    except ET.ParseError:
        return None
    monitor = root.find("videoscreen/monitor")
    return monitor.text.strip() if monitor is not None and monitor.text else None


class DisplayPicker(xbmcgui.WindowXMLDialog):
    """One card for each display. Sets choice to the selected index, or None when closed."""

    def onInit(self):
        cards = self.getControl(CARDS)
        cards.reset()
        start = None
        for index, (name_id, port_id, connector) in enumerate(DISPLAYS):
            item = xbmcgui.ListItem(text(name_id), text(port_id))
            if connector == self.active:
                state, status = "active", text(30020)
            elif is_connected(connector):
                state, status = "connected", text(30021)
            else:
                state, status = "missing", text(30022)
            item.setProperty("state", state)
            item.setProperty("status", status)
            cards.addItem(item)
            # Start on the first display that is not active, the likely choice.
            if connector != self.active and start is None:
                start = index
        cards.selectItem(start or 0)
        self.setFocusId(CARDS)

    def onAction(self, action):
        if action.getId() in ACTION_BACK:
            self.close()

    def onClick(self, control_id):
        if control_id == CARDS:
            self.choice = self.getControl(CARDS).getSelectedPosition()
            self.close()


def choose_display(active):
    picker = DisplayPicker("script-hdmi-switcher-main.xml", PATH, "default", "1080i")
    picker.active, picker.choice = active, None
    picker.doModal()
    choice = picker.choice
    del picker
    return choice


def switch_display(dialog, profile_directory):
    os_release = Path("/etc/os-release")
    if not os_release.is_file() or 'ID="libreelec"' not in os_release.read_text():
        dialog.ok(TITLE, text(30030))
        return

    boot_options = Path("/proc/cmdline").read_text().split()
    disabled_outputs = {"video=HDMI-A-1:d", "video=HDMI-A-2:d"}
    if disabled_outputs.intersection(boot_options):
        dialog.ok(TITLE, text(30031))
        return

    settings_path = profile_directory / "advancedsettings.xml"
    original = settings_path.read_bytes() if settings_path.exists() else None
    active = active_connector(original)
    selected_index = choose_display(active)
    if selected_index is None or selected_index < 0:
        return
    name_id, _, connector = DISPLAYS[selected_index]
    label = text(name_id)
    if connector == active:
        dialog.ok(TITLE, text(30034, label))
        return
    if not is_connected(connector):
        dialog.ok(TITLE, text(30032))
        return
    if not dialog.yesno(TITLE, text(30033, label), nolabel=text(30038), yeslabel=text(30037)):
        return

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
            dialog.ok(TITLE, text(30035))
            return
        try:
            switch_display(dialog, profile_directory)
        except Exception as error:
            xbmc.log("HDMI Switcher: " + str(error), xbmc.LOGERROR)
            dialog.ok(TITLE, text(30036, error))


if __name__ == "__main__":
    main()
