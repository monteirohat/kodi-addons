"""Wi-Fi window: the sections and the Wi-Fi switch on the left, and the current, available or known networks on the right."""

import os
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib import wifi


ADDON = xbmcaddon.Addon()
TITLE = ADDON.getAddonInfo("name")
PATH = ADDON.getAddonInfo("path")
MEDIA = os.path.join(PATH, "resources", "skins", "default", "media")
ACTION_LEFT, ACTION_RIGHT, ACTION_UP, ACTION_DOWN = 1, 2, 3, 4
ACTION_BACK = (10, 92)
ACTION_CONTEXT_MENU = 117
GROUPS, DETAILS, NETWORKS, KNOWN = 200, 300, 400, 450
POWER_BUTTON, PASSWORD_BUTTON, DISCONNECT_BUTTON, SCAN_BUTTON = 210, 501, 502, 503
OPTIONS, CONNECT_OPTION, PASSWORD_OPTION, AUTOCONNECT_OPTION, FORGET_OPTION = 600, 601, 602, 603, 604
SECTIONS = [("current", 30001), ("available", 30002), ("known", 30003)]
# How often the current network is read again, and the networks in range looked for again while they show.
UPDATE_SECONDS = 3
SCAN_SECONDS = 20
HIDDEN_PASSWORD = "••••••••"
SECURITY_NAMES = {"open": 30040, "wep": 30041, "wpa": 30042, "enterprise": 30043}


def text(string_id, *arguments):
    return ADDON.getLocalizedString(string_id).format(*arguments)


def notify(message):
    xbmcgui.Dialog().notification(TITLE, message, ADDON.getAddonInfo("icon"), 4000)


def busy(active):
    xbmc.executebuiltin("ActivateWindow(busydialognocancel)" if active else "Dialog.Close(busydialognocancel)")


def signal_level(strength):
    """The lit arcs of the Wi-Fi icon, 0 to 3, for a strength from 0 to 100."""
    strength = int(strength or 0)
    return 3 if strength >= 70 else 2 if strength >= 45 else 1 if strength >= 20 else 0


def signal_icon(strength):
    return os.path.join(MEDIA, "wifi-%d.png" % signal_level(strength))


def known_state(entry, network):
    """Whether a known network is connected, in range or out of range, and whether it connects by itself."""
    state = text(30060 if network and network["connected"] else 30073 if network else 30074)
    return state + ("  ·  " + text(30075) if entry["autoconnect"] else "")


def known_icon(network):
    strength = network.get("strength") if network else None
    if network and strength is not None:
        return signal_icon(strength)
    return os.path.join(MEDIA, "wifi-3.png" if network else "wifi-off.png")


def security_of(service_id):
    """The security of a network from its service name, which ends in managed_psk, managed_none and so on."""
    return wifi.SECURITY.get(service_id.rsplit("_", 1)[-1], "wpa")


class MainWindow(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loaded = False
        self.closing = False
        self.section = "current"
        self.current = None
        self.show_password = False
        self.powered = None
        self.available = []
        self.known = []
        self.last_scan = 0
        self.lock = threading.Lock()
        self.monitor = xbmc.Monitor()
        self.worker = None

    def onInit(self):
        if self.loaded:
            return
        self.loaded = True
        self.group_list = self.getControl(GROUPS)
        self.details = self.getControl(DETAILS)
        self.network_list = self.getControl(NETWORKS)
        self.known_list = self.getControl(KNOWN)
        self.getControl(PASSWORD_BUTTON).setLabel(text(30030))
        self.getControl(DISCONNECT_BUTTON).setLabel(text(30031))
        self.getControl(SCAN_BUTTON).setLabel(text(30032))
        self.group_list.addItems([xbmcgui.ListItem(text(label)) for _, label in SECTIONS])
        self.show_section("current")
        self.update()
        self.setFocusId(GROUPS)
        self.worker = threading.Thread(target=self.loop, daemon=True)
        self.worker.start()

    def loop(self):
        while not self.closing and not self.monitor.waitForAbort(UPDATE_SECONDS):
            if self.closing:
                break
            self.update()
            if self.section == "available" and time.time() - self.last_scan > SCAN_SECONDS:
                self.scan()

    # Sections

    def show_section(self, name):
        if name != "current" and self.show_password:
            # The password does not stay on the screen after leaving it.
            self.show_password = False
            self.show_details()
        self.section = name
        self.setProperty("section", name)
        self.group_list.selectItem([key for key, _ in SECTIONS].index(name))
        if name == "available":
            self.show_available()
            threading.Thread(target=self.scan, daemon=True).start()
        elif name == "known":
            self.show_known()
        self.show_title()

    def show_title(self):
        if self.section == "current":
            if self.current:
                online = self.current["state"] == "online"
                self.setProperty("title", self.current["name"])
                self.setProperty("subtitle", text(30010 if online else 30011))
            else:
                self.setProperty("title", text(30001))
                self.setProperty("subtitle", "")
                self.setProperty("empty", text(30013 if self.powered is False else 30012))
        elif self.section == "available":
            self.setProperty("title", text(30002))
            count = len(self.available)
            self.setProperty("subtitle", text(30015) if not count else text(30016) if count == 1 else text(30017, count))
            self.setProperty("empty", "" if count else text(30013 if self.powered is False else 30014))
        else:
            self.setProperty("title", text(30003))
            count = len(self.known)
            self.setProperty("subtitle", "" if not count else text(30018) if count == 1 else text(30019, count))
            self.setProperty("empty", "" if count else text(30020))

    def follow_group(self):
        index = self.group_list.getSelectedPosition()
        if 0 <= index < len(SECTIONS) and SECTIONS[index][0] != self.section:
            self.show_section(SECTIONS[index][0])

    def focus_section(self):
        """Move to the buttons or the list of the section, if it has something to select."""
        self.follow_group()
        if self.section == "current" and self.current:
            self.setFocusId(PASSWORD_BUTTON)
        elif self.section == "available":
            self.setFocusId(NETWORKS if self.available else SCAN_BUTTON)
        elif self.section == "known" and self.known:
            self.setFocusId(KNOWN)

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
        elif action_id == ACTION_CONTEXT_MENU and focus == NETWORKS:
            self.network_menu(self.network_list.getSelectedPosition())
        elif action_id == ACTION_CONTEXT_MENU and focus == KNOWN:
            self.known_menu(self.known_list.getSelectedPosition())

    def onClick(self, control_id):
        if control_id == GROUPS:
            self.focus_section()
        elif control_id == POWER_BUTTON:
            self.toggle_power()
        elif control_id == PASSWORD_BUTTON:
            self.show_password = not self.show_password
            self.update()
        elif control_id == DISCONNECT_BUTTON:
            self.disconnect()
        elif control_id == SCAN_BUTTON:
            threading.Thread(target=self.scan, args=(True,), daemon=True).start()
        elif control_id == NETWORKS:
            self.connect_to(self.network_at(self.network_list.getSelectedPosition()))
        elif control_id == KNOWN:
            self.known_menu(self.known_list.getSelectedPosition())

    def close_window(self):
        self.closing = True
        self.close()

    # Current network

    def update(self):
        """Read the current network and show it, on the left and in its section."""
        with self.lock:
            try:
                self.powered = wifi.powered()
                networks = wifi.networks() if self.powered else []
            except wifi.WifiError as error:
                xbmc.log("Easy Connect: %s" % error, xbmc.LOGWARNING)
                return
            current = next((network for network in networks if network["connected"]), None)
            info = wifi.details(current["id"]) if current else {}
            radio = wifi.link((info.get("Ethernet") or {}).get("Interface", "wlan0")) if current else {}
        if current and (not self.current or self.current["id"] != current["id"]):
            self.show_password = False
        self.current = dict(current, info=info, link=radio) if current else None
        self.show_link()
        self.show_details()
        if self.section == "current":
            self.show_title()

    def show_link(self):
        button = self.getControl(POWER_BUTTON)
        button.setLabel(text(30033 if self.powered else 30034))
        if self.powered is None:
            self.setProperty("link_icon", os.path.join(MEDIA, "wifi-off.png"))
            self.setProperty("link_title", text(30006))
            self.setProperty("link_detail", "")
        elif not self.powered:
            self.setProperty("link_icon", os.path.join(MEDIA, "wifi-off.png"))
            self.setProperty("link_title", text(30007))
            self.setProperty("link_detail", "")
        elif self.current:
            strength = self.current["info"].get("Strength", 0)
            name, _ = wifi.band(self.current["link"].get("frequency"))
            self.setProperty("link_icon", signal_icon(strength))
            self.setProperty("link_title", self.current["name"])
            self.setProperty("link_detail", "  ·  ".join(part for part in (text(30035, strength), name) if part))
        else:
            self.setProperty("link_icon", os.path.join(MEDIA, "wifi-off.png"))
            self.setProperty("link_title", text(30008))
            self.setProperty("link_detail", "")

    def show_details(self):
        if not self.current:
            self.setProperty("connected", "false")
            self.details.reset()
            return
        info, radio = self.current["info"], self.current["link"]
        ipv4 = info.get("IPv4") if isinstance(info.get("IPv4"), dict) else {}
        ethernet = info.get("Ethernet") if isinstance(info.get("Ethernet"), dict) else {}
        band_name, channel = wifi.band(radio.get("frequency"))
        kind = wifi.security(info)
        saved = wifi.password(self.current["id"]) if kind != "open" else ""
        if kind == "open":
            password = text(30036)
        elif not saved:
            password = text(30037)
        else:
            password = saved if self.show_password else HIDDEN_PASSWORD
        signal = text(30035, info.get("Strength", 0)) + ("  ·  %d dBm" % radio["signal"] if "signal" in radio else "")
        rows = [(30021, signal),
                (30022, "  ·  ".join(part for part in (band_name, text(30038, channel) if channel else "") if part)),
                (30023, text(30039, round(radio["bitrate"])) if radio.get("bitrate") else ""),
                (30024, text(SECURITY_NAMES[kind])),
                (30025, password),
                (30026, ipv4.get("Address", "")),
                (30027, ipv4.get("Netmask", "")),
                (30028, ipv4.get("Gateway", "")),
                (30029, ", ".join(info.get("Nameservers") or [])),
                (30044, ethernet.get("Address", ""))]
        items = [xbmcgui.ListItem(text(label), value or "—") for label, value in rows]
        self.details.reset()
        self.details.addItems(items)
        self.setProperty("connected", "true")
        self.getControl(PASSWORD_BUTTON).setLabel(text(30045 if self.show_password else 30030))

    def disconnect(self):
        if not self.current:
            return
        if not xbmcgui.Dialog().yesno(TITLE, text(30050, self.current["name"]), nolabel=text(30051), yeslabel=text(30031)):
            return
        try:
            wifi.disconnect(self.current["id"])
        except wifi.WifiError as error:
            xbmcgui.Dialog().ok(TITLE, text(30052, error))
        self.update()
        self.setFocusId(GROUPS)

    def toggle_power(self):
        if self.powered is None:
            return
        if self.powered and not xbmcgui.Dialog().yesno(TITLE, text(30053), nolabel=text(30051), yeslabel=text(30033)):
            return
        busy(True)
        try:
            wifi.set_powered(not self.powered)
            if not self.powered:
                # The networks in range show a few seconds after the Wi-Fi turns on.
                self.monitor.waitForAbort(3)
        except wifi.WifiError as error:
            xbmcgui.Dialog().ok(TITLE, text(30052, error))
        finally:
            busy(False)
        self.update()
        self.last_scan = 0
        self.show_section(self.section)

    # Networks in range

    def scan(self, again=False):
        """Look for networks and show them. With again, the list shows the search first."""
        self.last_scan = time.time()
        if not self.powered:
            self.show_available()
            return
        if again:
            self.setProperty("subtitle", text(30015))
        try:
            wifi.scan()
        except wifi.WifiError as error:
            xbmc.log("Easy Connect: %s" % error, xbmc.LOGWARNING)
        if not self.closing:
            self.show_available()

    def read_available(self):
        """The networks in range with their strength, connected first, then known, then by strength."""
        try:
            networks = wifi.networks() if self.powered else []
        except wifi.WifiError:
            return []
        for network in networks:
            try:
                network["strength"] = int(wifi.details(network["id"]).get("Strength", 0))
            except (wifi.WifiError, ValueError):
                network["strength"] = 0
            network["security"] = security_of(network["id"])
        return sorted(networks, key=lambda network: (not network["connected"], not network["known"], -network["strength"]))

    def show_available(self):
        selected = self.network_at(self.network_list.getSelectedPosition())
        self.available = self.read_available()
        items = []
        for network in self.available:
            if network["connected"]:
                state = text(30060)
            elif network["known"]:
                state = text(30061)
            else:
                state = text(SECURITY_NAMES[network["security"]])
            item = xbmcgui.ListItem(network["name"], state)
            item.setArt({"icon": signal_icon(network["strength"])})
            item.setProperty("value", text(30035, network["strength"]))
            item.setProperty("locked", "true" if network["security"] != "open" else "false")
            items.append(item)
        self.network_list.reset()
        self.network_list.addItems(items)
        ids = [network["id"] for network in self.available]
        if selected and selected["id"] in ids:
            self.network_list.selectItem(ids.index(selected["id"]))
        if self.section == "available":
            self.show_title()
            if not self.available and self.getFocusId() == NETWORKS:
                self.setFocusId(SCAN_BUTTON)

    def network_at(self, position):
        return self.available[position] if 0 <= position < len(self.available) else None

    def network_menu(self, position):
        network = self.network_at(position)
        if not network:
            return
        options = [] if network["connected"] else [(text(30062), lambda: self.connect_to(network))]
        if network["known"]:
            options.append((text(30063), lambda: self.forget(network)))
        if options:
            choice = xbmcgui.Dialog().contextmenu([label for label, _ in options])
            if choice >= 0:
                options[choice][1]()

    def connect_to(self, network):
        """Connect to a network in range, asking for its password when connman does not know it."""
        if not network:
            return
        if network["connected"]:
            notify(text(30064, network["name"]))
            return
        if network["security"] == "enterprise":
            xbmcgui.Dialog().ok(TITLE, text(30065))
            return
        if self.current and not xbmcgui.Dialog().yesno(TITLE, text(30066, network["name"], self.current["name"]),
                                                       nolabel=text(30051), yeslabel=text(30062)):
            return
        passphrase = None
        if not network["known"] and network["security"] != "open":
            passphrase = self.ask_password(network["name"])
            if passphrase is None:
                return
        busy(True)
        try:
            problem = wifi.connect(network["id"], passphrase)
        finally:
            busy(False)
        if problem is None:
            notify(text(30067, network["name"]))
        elif problem == "password":
            xbmcgui.Dialog().ok(TITLE, text(30068, network["name"]))
        elif problem == "timeout":
            xbmcgui.Dialog().ok(TITLE, text(30069, network["name"]))
        else:
            xbmcgui.Dialog().ok(TITLE, text(30070, network["name"], problem))
        self.update()
        self.show_available()

    @staticmethod
    def ask_password(name):
        """The password typed for a network, or None when the keyboard is cancelled. WPA needs at least 8 characters."""
        while True:
            typed = xbmcgui.Dialog().input(text(30071, name), option=xbmcgui.ALPHANUM_HIDE_INPUT)
            if not typed:
                return None
            if len(typed) >= 8:
                return typed
            xbmcgui.Dialog().ok(TITLE, text(30072))

    # Known networks

    def show_known(self):
        self.known = wifi.known()
        in_range = {network["name"]: network for network in self.available}
        if not in_range:
            try:
                in_range = {network["name"]: network for network in (wifi.networks() if self.powered else [])}
            except wifi.WifiError:
                in_range = {}
        items = []
        for entry in self.known:
            network = in_range.get(entry["name"])
            entry["network"] = network
            item = xbmcgui.ListItem(entry["name"], known_state(entry, network))
            item.setArt({"icon": known_icon(network)})
            item.setProperty("locked", "true" if security_of(entry["id"]) != "open" else "false")
            items.append(item)
        self.known_list.reset()
        self.known_list.addItems(items)
        if self.section == "known":
            self.show_title()

    def known_menu(self, position):
        """The modal of a known network. Connecting and forgetting happen after it closes."""
        if not 0 <= position < len(self.known):
            return
        entry = self.known[position]
        dialog = NetworkDialog("script-easy-connect-network.xml", PATH, "default", "1080i", entry=entry, window=self)
        dialog.doModal()
        choice = dialog.choice
        del dialog
        network = entry.get("network")
        if choice == "connect" and network:
            self.connect_to(dict(network, security=security_of(network["id"])))
        elif choice == "forget":
            self.forget(entry)
        else:
            self.show_known()
            self.known_list.selectItem(position)

    def toggle_autoconnect(self, entry):
        """Returns whether it changed."""
        try:
            wifi.set_autoconnect(entry["id"], not entry["autoconnect"])
        except wifi.WifiError as error:
            xbmcgui.Dialog().ok(TITLE, text(30052, error))
            return False
        entry["autoconnect"] = not entry["autoconnect"]
        return True

    def forget(self, entry):
        connected = bool(self.current and self.current["name"] == entry["name"])
        if not xbmcgui.Dialog().yesno(TITLE, text(30080 if connected else 30079, entry["name"]), nolabel=text(30051),
                                      yeslabel=text(30063)):
            return
        try:
            wifi.forget(entry["id"])
        except wifi.WifiError as error:
            xbmcgui.Dialog().ok(TITLE, text(30052, error))
        self.update()
        self.show_known()
        if self.section == "available":
            self.show_available()
        if not self.known and self.getFocusId() == KNOWN:
            self.setFocusId(GROUPS)


class NetworkDialog(xbmcgui.WindowXMLDialog):
    """The options of a known network: connect, show the password, connect by itself, forget. choice is "connect" or
    "forget" when the window has to do it after the modal closes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.entry, self.window = kwargs["entry"], kwargs["window"]
        self.choice = None
        self.show_password = False
        self.saved = ""

    def onInit(self):
        network = self.entry.get("network")
        self.saved = wifi.password(self.entry["id"])
        self.setProperty("name", self.entry["name"])
        self.setProperty("icon", known_icon(network))
        self.setProperty("security", text(SECURITY_NAMES[security_of(self.entry["id"])]))
        self.setProperty("has_password", "true" if self.saved else "false")
        self.setProperty("can_connect", "true" if network and not network["connected"] else "false")
        self.show_state()
        first = CONNECT_OPTION if network and not network["connected"] else PASSWORD_OPTION if self.saved else AUTOCONNECT_OPTION
        # A button shown by a property can take the focus only once Kodi has drawn it.
        monitor = xbmc.Monitor()
        for _ in range(20):
            if xbmc.getCondVisibility("Control.IsVisible(%d)" % first):
                break
            monitor.waitForAbort(0.02)
        self.setFocusId(first)

    def show_state(self):
        self.setProperty("state", known_state(self.entry, self.entry.get("network")))
        if not self.saved:
            password = text(30036 if security_of(self.entry["id"]) == "open" else 30037)
        else:
            password = self.saved if self.show_password else HIDDEN_PASSWORD
        self.setProperty("password", password)
        self.getControl(PASSWORD_OPTION).setLabel(text(30045 if self.show_password else 30030))
        self.getControl(AUTOCONNECT_OPTION).setLabel(text(30081), label2=text(30083 if self.entry["autoconnect"] else 30084))

    def onClick(self, control_id):
        if control_id == CONNECT_OPTION:
            self.choice = "connect"
            self.close()
        elif control_id == PASSWORD_OPTION:
            self.show_password = not self.show_password
            self.show_state()
        elif control_id == AUTOCONNECT_OPTION:
            if self.window.toggle_autoconnect(self.entry):
                self.show_state()
        elif control_id == FORGET_OPTION:
            self.choice = "forget"
            self.close()

    def onAction(self, action):
        if action.getId() in ACTION_BACK:
            self.close()


def run():
    if not wifi.available():
        xbmcgui.Dialog().ok(TITLE, text(30090))
        return
    window = MainWindow("script-easy-connect-main.xml", PATH, "default", "1080i")
    window.doModal()
    # The updates stop when the window closes; wait for the last one, as it still changes the window.
    if window.worker:
        window.worker.join(10)
    del window
