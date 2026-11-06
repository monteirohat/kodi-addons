"""Bluetooth window: the sections and the Bluetooth switch on the left, and the paired or found devices on the right."""

import os
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib import bluetooth


ADDON = xbmcaddon.Addon()
TITLE = ADDON.getAddonInfo("name")
PATH = ADDON.getAddonInfo("path")
MEDIA = os.path.join(PATH, "resources", "skins", "default", "media")
ACTION_BACK = (10, 92)
ACTION_RIGHT, ACTION_UP, ACTION_DOWN = 2, 3, 4
ACTION_CONTEXT_MENU = 117
GROUPS, DEVICES, FOUND = 200, 400, 450
POWER_BUTTON, SCAN_BUTTON = 210, 503
OPTIONS, CONNECT_OPTION, TRUST_OPTION, FORGET_OPTION = 600, 601, 602, 603
SECTIONS = [("devices", 30001), ("search", 30002)]
UPDATE_SECONDS = 3
# BlueZ stops looking after a while; the search looks again for as long as it shows.
SCAN_SECONDS = 60
KIND_NAMES = {"headphones": 30030, "speaker": 30031, "keyboard": 30032, "mouse": 30033, "gamepad": 30034, "phone": 30035,
              "computer": 30036, "tv": 30037, "printer": 30038, "other": 30039}
KIND_ICONS = {"headphones": "headphones.png", "speaker": "speaker.png", "keyboard": "keyboard.png", "mouse": "mouse.png",
              "gamepad": "gamepad.png", "phone": "phone.png", "computer": "computer.png", "tv": "tv.png",
              "printer": "printer.png", "other": "bluetooth.png"}


def text(string_id, *arguments):
    return ADDON.getLocalizedString(string_id).format(*arguments)


def notify(message, seconds=4):
    xbmcgui.Dialog().notification(TITLE, message, ADDON.getAddonInfo("icon"), seconds * 1000)


def busy(active):
    xbmc.executebuiltin("ActivateWindow(busydialognocancel)" if active else "Dialog.Close(busydialognocancel)")


def kind_icon(device):
    return os.path.join(MEDIA, KIND_ICONS.get(device["kind"], "bluetooth.png"))


def signal_icon(rssi):
    """Bars for the signal of a device found nearby, from its RSSI in dBm, or "" without it."""
    if rssi is None:
        return ""
    lit = 3 if rssi >= -60 else 2 if rssi >= -70 else 1 if rssi >= -80 else 0
    return os.path.join(MEDIA, "bars-%d.png" % lit)


def device_state(device):
    """Connected or paired, with the battery when the device reports it."""
    state = text(30040 if device["connected"] else 30041)
    if device.get("battery") is not None:
        state += "  ·  " + text(30042, device["battery"])
    return state


class MainWindow(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loaded = False
        self.closing = False
        self.section = "devices"
        self.adapter = None
        self.paired = []
        self.found = []
        self.session = None
        self.scan_started = 0
        self.lock = threading.Lock()
        self.monitor = xbmc.Monitor()
        self.worker = None

    def onInit(self):
        if self.loaded:
            return
        self.loaded = True
        self.group_list = self.getControl(GROUPS)
        self.device_list = self.getControl(DEVICES)
        self.found_list = self.getControl(FOUND)
        self.getControl(SCAN_BUTTON).setLabel(text(30011))
        self.group_list.addItems([xbmcgui.ListItem(text(label)) for _, label in SECTIONS])
        self.update()
        self.show_section("devices")
        self.setFocusId(GROUPS)
        self.worker = threading.Thread(target=self.loop, daemon=True)
        self.worker.start()

    def loop(self):
        while not self.closing and not self.monitor.waitForAbort(UPDATE_SECONDS):
            if self.closing:
                break
            self.update()
            if self.section == "search":
                if self.adapter and self.adapter["powered"] and time.time() - self.scan_started > SCAN_SECONDS:
                    self.start_scan()
                self.show_found()

    # Sections

    def show_section(self, name):
        self.section = name
        self.setProperty("section", name)
        self.group_list.selectItem([key for key, _ in SECTIONS].index(name))
        if name == "search":
            self.open_session()
            self.start_scan()
            self.show_found()
        else:
            if self.session:
                self.session.scan(False)
            self.show_paired()
        self.show_title()

    def show_title(self):
        powered = bool(self.adapter and self.adapter["powered"])
        if self.section == "devices":
            count = len(self.paired)
            self.setProperty("title", text(30001))
            self.setProperty("subtitle", "" if not count else text(30012) if count == 1 else text(30013, count))
            self.setProperty("empty", "" if count else text(30014 if powered else 30015))
        else:
            count = len(self.found)
            self.setProperty("title", text(30002))
            self.setProperty("subtitle", text(30016) if not count else text(30017) if count == 1 else text(30018, count))
            self.setProperty("empty", "" if count else text(30019 if powered else 30015))

    def follow_group(self):
        index = self.group_list.getSelectedPosition()
        if 0 <= index < len(SECTIONS) and SECTIONS[index][0] != self.section:
            self.show_section(SECTIONS[index][0])

    def focus_section(self):
        self.follow_group()
        if self.section == "devices" and self.paired:
            self.setFocusId(DEVICES)
        elif self.section == "search":
            self.setFocusId(FOUND if self.found else SCAN_BUTTON)

    def onAction(self, action):
        action_id = action.getId()
        try:
            focus = self.getFocusId()
        except RuntimeError:
            focus = 0
        if action_id in ACTION_BACK:
            if focus in (GROUPS, POWER_BUTTON, 0):
                self.close_window()
            else:
                self.setFocusId(GROUPS)
        elif focus == GROUPS and action_id in (ACTION_UP, ACTION_DOWN):
            self.follow_group()
        elif focus == GROUPS and action_id == ACTION_RIGHT:
            self.focus_section()
        elif action_id == ACTION_CONTEXT_MENU and focus == DEVICES:
            self.device_menu(self.device_list.getSelectedPosition())

    def onClick(self, control_id):
        if control_id == GROUPS:
            self.focus_section()
        elif control_id == POWER_BUTTON:
            self.toggle_power()
        elif control_id == SCAN_BUTTON:
            self.start_scan()
            notify(text(30016))
        elif control_id == DEVICES:
            self.device_menu(self.device_list.getSelectedPosition())
        elif control_id == FOUND:
            position = self.found_list.getSelectedPosition()
            if 0 <= position < len(self.found):
                self.pair(self.found[position])

    def close_window(self):
        self.closing = True
        if self.session:
            self.session.close()
        self.close()

    # The adapter

    def update(self):
        with self.lock:
            self.adapter = bluetooth.adapter()
        if not self.adapter:
            self.setProperty("adapter_name", text(30006))
            self.setProperty("adapter_state", "")
        else:
            self.setProperty("adapter_name", self.adapter["name"])
            connected = sum(1 for device in self.paired if device["connected"])
            state = text(30007 if self.adapter["powered"] else 30008)
            if self.adapter["powered"] and connected:
                state += "  ·  " + (text(30009) if connected == 1 else text(30010, connected))
            self.setProperty("adapter_state", state)
        self.getControl(POWER_BUTTON).setLabel(text(30021 if self.adapter and self.adapter["powered"] else 30022))
        # The icon of the home screen follows at once, without waiting for the service.
        icon = bluetooth.icon()
        xbmcgui.Window(10000).setProperty("EasyBluetooth.Icon", icon)
        self.setProperty("adapter_icon", os.path.join(MEDIA, icon))
        if self.section == "devices":
            self.show_paired()

    def toggle_power(self):
        if not self.adapter:
            return
        powered = self.adapter["powered"]
        if powered and any(device["connected"] for device in self.paired) and not xbmcgui.Dialog().yesno(
                TITLE, text(30023), nolabel=text(30024), yeslabel=text(30021)):
            return
        try:
            bluetooth.set_powered(not powered)
        except bluetooth.BluetoothError as error:
            xbmcgui.Dialog().ok(TITLE, text(30025, error))
        self.update()
        self.show_section(self.section)

    # Paired devices

    def show_paired(self):
        selected = self.paired[self.device_list.getSelectedPosition()]["address"] \
            if 0 <= self.device_list.getSelectedPosition() < len(self.paired) else None
        try:
            self.paired = bluetooth.paired()
        except bluetooth.BluetoothError:
            self.paired = []
        items = []
        for device in self.paired:
            item = xbmcgui.ListItem(device["name"] or device["address"], device_state(device))
            item.setArt({"icon": kind_icon(device)})
            item.setProperty("value", text(KIND_NAMES[device["kind"]]))
            items.append(item)
        self.device_list.reset()
        self.device_list.addItems(items)
        addresses = [device["address"] for device in self.paired]
        if selected in addresses:
            self.device_list.selectItem(addresses.index(selected))
        if self.section == "devices":
            self.show_title()
            if not self.paired and self.getFocusId() == DEVICES:
                self.setFocusId(GROUPS)

    def device_menu(self, position):
        if not 0 <= position < len(self.paired):
            return
        device = self.paired[position]
        dialog = DeviceDialog("script-easy-bluetooth-device.xml", PATH, "default", "1080i", device=device)
        dialog.doModal()
        forget = dialog.choice == "forget"
        del dialog
        if forget and xbmcgui.Dialog().yesno(TITLE, text(30063, device["name"] or device["address"]), nolabel=text(30024),
                                             yeslabel=text(30062)):
            try:
                bluetooth.remove(device["address"])
            except bluetooth.BluetoothError as error:
                xbmcgui.Dialog().ok(TITLE, text(30025, error))
        self.show_paired()

    # Devices found nearby

    def open_session(self):
        if self.session is None and self.adapter and self.adapter["powered"]:
            self.session = bluetooth.Session()

    def start_scan(self):
        self.open_session()
        if self.session:
            self.session.scan(True)
            self.scan_started = time.time()

    def show_found(self):
        """The named devices found nearby that are not paired, strongest first."""
        if not self.session:
            self.found = []
        else:
            paired = {device["address"] for device in self.paired}
            found = []
            for address in list(self.session.found):
                if address in paired:
                    continue
                try:
                    device = bluetooth.info(address)
                except bluetooth.BluetoothError:
                    continue
                if device["name"] and not device["paired"]:
                    found.append(device)
            self.found = sorted(found, key=lambda device: -(device["rssi"] if device["rssi"] is not None else -999))
        selected = self.found_list.getSelectedPosition()
        items = []
        for device in self.found:
            item = xbmcgui.ListItem(device["name"], text(KIND_NAMES[device["kind"]]))
            item.setArt({"icon": kind_icon(device)})
            item.setProperty("signal", signal_icon(device["rssi"]))
            items.append(item)
        self.found_list.reset()
        self.found_list.addItems(items)
        if 0 <= selected < len(items):
            self.found_list.selectItem(selected)
        if self.section == "search":
            self.show_title()

    def pair(self, device):
        """Pair a device found nearby, trust it so it connects by itself, and connect to it."""
        name = device["name"]
        self.session.scan(False)
        busy(True)

        def ask(kind, value):
            busy(False)
            try:
                if kind == "confirm":
                    return xbmcgui.Dialog().yesno(TITLE, text(30070, value, name), nolabel=text(30071), yeslabel=text(30072))
                if kind in ("pin", "passkey"):
                    typed = xbmcgui.Dialog().input(text(30073, name),
                                                   type=xbmcgui.INPUT_NUMERIC if kind == "passkey" else xbmcgui.INPUT_ALPHANUM)
                    return typed or None
                notify(text(30074, value, name), 30)
                return None
            finally:
                busy(True)

        try:
            problem = self.session.pair(device["address"], ask)
            if problem is None:
                bluetooth.set_trusted(device["address"], True)
                try:
                    bluetooth.connect(device["address"])
                except bluetooth.BluetoothError as error:
                    xbmc.log("Easy Bluetooth: paired, not connected: %s" % error, xbmc.LOGWARNING)
        except bluetooth.BluetoothError as error:
            problem = str(error)
        finally:
            busy(False)
        if problem is None:
            notify(text(30075, name))
            self.show_section("devices")
            self.setFocusId(DEVICES if self.paired else GROUPS)
            return
        if problem == "rejected":
            xbmcgui.Dialog().ok(TITLE, text(30076, name))
        elif problem in ("timeout", "gone"):
            xbmcgui.Dialog().ok(TITLE, text(30077, name))
        else:
            xbmcgui.Dialog().ok(TITLE, text(30078, name, problem))
        self.start_scan()


class DeviceDialog(xbmcgui.WindowXMLDialog):
    """The options of a paired device: connect or disconnect, connect by itself, forget. choice is "forget" when the
    window has to ask and do it after the modal closes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.device = kwargs["device"]
        self.choice = None

    def onInit(self):
        self.setProperty("icon", kind_icon(self.device))
        self.setProperty("name", self.device["name"] or self.device["address"])
        self.setProperty("kind", text(KIND_NAMES[self.device["kind"]]))
        self.setProperty("address", self.device["address"])
        self.show_state()
        self.setFocusId(CONNECT_OPTION)

    def show_state(self):
        self.setProperty("state", device_state(self.device))
        self.getControl(CONNECT_OPTION).setLabel(text(30064 if self.device["connected"] else 30060))
        self.getControl(TRUST_OPTION).setLabel(text(30061), label2=text(30065 if self.device["trusted"] else 30066))

    def refresh(self):
        try:
            self.device.update(bluetooth.info(self.device["address"]))
        except bluetooth.BluetoothError:
            pass
        self.show_state()

    def onClick(self, control_id):
        address = self.device["address"]
        if control_id == CONNECT_OPTION:
            busy(True)
            try:
                if self.device["connected"]:
                    bluetooth.disconnect(address)
                else:
                    bluetooth.connect(address)
            except bluetooth.BluetoothError:
                busy(False)
                xbmcgui.Dialog().ok(TITLE, text(30067 if not self.device["connected"] else 30068,
                                                self.device["name"] or address))
            finally:
                busy(False)
            self.refresh()
        elif control_id == TRUST_OPTION:
            try:
                bluetooth.set_trusted(address, not self.device["trusted"])
            except bluetooth.BluetoothError as error:
                xbmcgui.Dialog().ok(TITLE, text(30025, error))
            self.refresh()
        elif control_id == FORGET_OPTION:
            self.choice = "forget"
            self.close()

    def onAction(self, action):
        if action.getId() in ACTION_BACK:
            self.close()


def run():
    if not bluetooth.available():
        xbmcgui.Dialog().ok(TITLE, text(30090))
        return
    if not bluetooth.service_active():
        if not os.path.isdir(os.path.dirname(bluetooth.SERVICE_FILE)) or not xbmcgui.Dialog().yesno(
                TITLE, text(30091), nolabel=text(30024), yeslabel=text(30022)):
            return
        busy(True)
        try:
            bluetooth.start_service()
        finally:
            busy(False)
    if not bluetooth.adapter():
        xbmcgui.Dialog().ok(TITLE, text(30092))
        return
    window = MainWindow("script-easy-bluetooth-main.xml", PATH, "default", "1080i")
    window.doModal()
    # The updates stop when the window closes; wait for the last one, as it still changes the window.
    if window.worker:
        window.worker.join(10)
    if window.session:
        window.session.close()
    del window
