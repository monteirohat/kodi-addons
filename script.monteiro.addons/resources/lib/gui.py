"""Add-ons of the repositories: a toolbar and the repositories on the left, and the add-ons on the right, each one with its
category. OK shows the details of an add-on, with its screenshots, to install or open it."""

import json
import os
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import catalog


ADDON = xbmcaddon.Addon()
TITLE = ADDON.getAddonInfo("name")
PATH = ADDON.getAddonInfo("path")
MEDIA = os.path.join(PATH, "resources", "skins", "default", "media")
DATABASE_FOLDER = xbmcvfs.translatePath("special://database")
ACTION_LEFT, ACTION_RIGHT, ACTION_UP, ACTION_DOWN = 1, 2, 3, 4
ACTION_BACK = (10, 92)
ACTION_CONTEXT_MENU = 117
TOOLBAR, GROUPS, ADDONS = 100, 200, 300
GROUP_TITLE, GROUP_COUNT, GROUP_EMPTY = 401, 402, 404
# Delay before the list follows the highlighted repository, so fast scrolling stays smooth.
FOLLOW_DELAY = 0.3
# How long an installation is watched, to mark the add-on as installed when it ends.
INSTALL_WATCH = 180
# Kinds that open with RunAddon.
OPENS = ("xbmc.python.pluginsource", "xbmc.python.script")

# Toolbar above the repositories: icon, label and the MainWindow method it runs.
TOOLS = [
    ("search.png", 30005, "search"),
    ("refresh.png", 30006, "update_repositories"),
]


def text(string_id, *arguments):
    return ADDON.getLocalizedString(string_id).format(*arguments)


def kodi_text(string_id):
    return xbmc.getLocalizedString(string_id)


def notify(message):
    xbmcgui.Dialog().notification(TITLE, message, ADDON.getAddonInfo("icon"), 3000)


def busy(active):
    xbmc.executebuiltin("ActivateWindow(busydialognocancel)" if active else "Dialog.Close(busydialognocancel)")


def rpc(method, **params):
    request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    return json.loads(xbmc.executeJSONRPC(json.dumps(request))).get("result") or {}


def installed_versions():
    """Versions of the installed add-ons, to show which ones have an update."""
    result = rpc("Addons.GetAddons", installed=True, properties=["version"])
    return {addon["addonid"]: addon.get("version", "") for addon in result.get("addons", [])}


def repository_name(repo_id, fallback):
    try:
        return xbmcaddon.Addon(repo_id).getAddonInfo("name") or fallback
    except Exception:
        return fallback


def count_label(count):
    return text(30003) if count == 1 else text(30002, count)


class MainWindow(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loaded = False
        self.groups, self.shown = [], []
        self.shown_index = -1
        self.follow_timer = None
        self.query = ""

    def onInit(self):
        if self.loaded:
            return
        self.loaded = True
        self.toolbar = self.getControl(TOOLBAR)
        self.group_list = self.getControl(GROUPS)
        self.addon_list = self.getControl(ADDONS)
        tools = []
        for icon, label, _ in TOOLS:
            item = xbmcgui.ListItem(text(label))
            item.setArt({"icon": os.path.join(MEDIA, icon)})
            tools.append(item)
        self.toolbar.addItems(tools)
        self.reload(self.start)
        self.setFocusId(ADDONS if self.shown else GROUPS)

    # Repositories and add-ons

    def reload(self, keep=None):
        """Read the repositories again. keep is the repository to show afterwards, by its id."""
        busy(True)
        try:
            path = catalog.database(DATABASE_FOLDER)
            repositories = catalog.read(path) if path else []
            versions = installed_versions()
        except Exception as error:
            busy(False)
            xbmcgui.Dialog().ok(TITLE, text(30009, error))
            self.close()
            return
        busy(False)
        everything = []
        for repository in repositories:
            repository["name"] = repository_name(repository["id"], repository["name"])
            for addon in repository["addons"]:
                addon["update"] = catalog.newer(addon["version"], versions.get(addon["id"], ""))
                addon["installed"] = addon["installed"] or addon["id"] in versions
            everything += repository["addons"]
        everything.sort(key=lambda addon: addon["name"].lower())
        self.groups = [{"key": "all", "name": text(30001), "addons": everything}]
        self.groups += [{"key": repository["id"], "name": repository["name"], "addons": repository["addons"]}
                        for repository in repositories]
        if self.query:
            self.groups.insert(0, self.results_group(everything))
        items = []
        for group in self.groups:
            item = xbmcgui.ListItem(group["name"])
            item.setLabel2(str(len(group["addons"])))
            items.append(item)
        self.group_list.reset()
        self.group_list.addItems(items)
        keys = [group["key"] for group in self.groups]
        index = keys.index(keep) if keep in keys else 0
        self.group_list.selectItem(index)
        self.shown_index = -1
        self.show_group(index)

    def results_group(self, everything):
        words = self.query.lower().split()
        return {"key": "search", "name": text(30011, self.query),
                "addons": [addon for addon in everything if catalog.matches(addon, words)]}

    def show_group(self, index, select=0):
        self.shown_index = index
        group = self.groups[index]
        self.shown = group["addons"]
        items = []
        for addon in self.shown:
            item = xbmcgui.ListItem(addon["name"])
            item.setLabel2(addon["summary"])
            item.setArt({"icon": addon["icon"] or os.path.join(MEDIA, "puzzle.png")})
            item.setProperty("category", kodi_text(addon["category"]))
            item.setProperty("version", addon["version"])
            self.set_state(item, addon)
            items.append(item)
        self.addon_list.reset()
        self.addon_list.addItems(items)
        if self.shown:
            self.addon_list.selectItem(min(max(select, 0), len(self.shown) - 1))
        self.getControl(GROUP_TITLE).setLabel(group["name"])
        self.getControl(GROUP_COUNT).setLabel(count_label(len(self.shown)) if self.shown else "")
        self.getControl(GROUP_EMPTY).setLabel("" if self.shown else (text(30008, self.query) if group["key"] == "search" else ""))

    def set_state(self, item, addon):
        state = "update" if addon.get("update") else ("installed" if addon["installed"] else "")
        item.setProperty("state", state)
        # Installed add-ons show a green check. Those with an update also say so.
        item.setProperty("state_label", text(30017) if state == "update" else "")

    def follow_group(self):
        index = self.group_list.getSelectedPosition()
        if 0 <= index < len(self.groups) and index != self.shown_index:
            self.show_group(index)

    def selected_addon(self):
        position = self.addon_list.getSelectedPosition()
        return self.shown[position] if 0 <= position < len(self.shown) else None

    # Keys

    def onAction(self, action):
        action_id = action.getId()
        focus = self.getFocusId()
        if action_id in ACTION_BACK:
            if focus == ADDONS:
                self.setFocusId(GROUPS)
            else:
                self.close()
        elif action_id == ACTION_CONTEXT_MENU and focus == ADDONS and self.shown:
            self.addon_menu(self.selected_addon())
        elif focus == ADDONS and action_id == ACTION_LEFT:
            self.setFocusId(GROUPS)
        elif focus == GROUPS and action_id == ACTION_LEFT:
            if self.follow_timer:
                self.follow_timer.cancel()
            self.follow_group()
            self.setFocusId(TOOLBAR)
        elif focus == GROUPS and action_id == ACTION_RIGHT:
            if self.follow_timer:
                self.follow_timer.cancel()
            self.follow_group()
            if self.shown:
                self.setFocusId(ADDONS)
        elif focus == GROUPS and action_id in (ACTION_UP, ACTION_DOWN):
            if self.follow_timer:
                self.follow_timer.cancel()
            self.follow_timer = threading.Timer(FOLLOW_DELAY, self.follow_group)
            self.follow_timer.start()

    def onClick(self, control_id):
        if control_id == TOOLBAR:
            getattr(self, TOOLS[self.toolbar.getSelectedPosition()][2])()
        elif control_id == GROUPS:
            if self.follow_timer:
                self.follow_timer.cancel()
            self.follow_group()
            if self.shown:
                self.setFocusId(ADDONS)
        elif control_id == ADDONS:
            addon = self.selected_addon()
            if addon:
                self.activate(addon)

    # Add-ons

    def activate(self, addon):
        """Show the details of an add-on, and run the action chosen there."""
        details = Details("script-monteiro-addons-details.xml", PATH, "default", "1080i")
        details.addon, details.choice = addon, None
        details.doModal()
        choice = details.choice
        del details
        if choice == "install":
            self.install(addon)
        elif choice == "updates":
            xbmc.executebuiltin("ActivateWindow(addonbrowser,addons://outdated/,return)")
        elif choice == "open":
            xbmc.executebuiltin("RunAddon(%s)" % addon["id"])
        elif choice == "settings":
            xbmc.executebuiltin("Addon.OpenSettings(%s)" % addon["id"])

    def addon_menu(self, addon):
        options = []
        if not addon["installed"]:
            options.append((30014, lambda: self.install(addon)))
        else:
            if addon.get("update"):
                # Kodi updates an add-on from its list of updates.
                options.append((30018, lambda: xbmc.executebuiltin("ActivateWindow(addonbrowser,addons://outdated/,return)")))
            if addon["kind"] in OPENS:
                options.append((30012, lambda: xbmc.executebuiltin("RunAddon(%s)" % addon["id"])))
            options.append((30013, lambda: xbmc.executebuiltin("Addon.OpenSettings(%s)" % addon["id"])))
        choice = xbmcgui.Dialog().contextmenu([text(string_id) for string_id, _ in options])
        if choice >= 0:
            options[choice][1]()

    def install(self, addon):
        # Kodi asks before installing, and installs the dependencies too.
        xbmc.executebuiltin("InstallAddon(%s)" % addon["id"], True)
        threading.Thread(target=self.watch_install, args=(addon,), daemon=True).start()

    def watch_install(self, addon):
        """Mark the add-on once Kodi has installed it."""
        monitor = xbmc.Monitor()
        deadline = time.time() + INSTALL_WATCH
        while time.time() < deadline and not monitor.abortRequested():
            if xbmc.getCondVisibility("System.HasAddon(%s)" % addon["id"]):
                break
            monitor.waitForAbort(2)
        else:
            return
        addon["installed"], addon["update"] = True, False
        for index, shown in enumerate(self.shown):
            if shown is addon:
                self.set_state(self.addon_list.getListItem(index), addon)
        notify(text(30016, addon["name"]))

    # Tools

    def search(self):
        query = xbmcgui.Dialog().input(text(30010)).strip()
        if not query:
            return
        self.query = query
        self.reload("search")
        self.setFocusId(ADDONS if self.shown else GROUPS)

    def update_repositories(self):
        keep = self.groups[self.shown_index]["key"] if 0 <= self.shown_index < len(self.groups) else None
        notify(text(30015))
        xbmc.executebuiltin("UpdateAddonRepos")
        # Kodi checks the repositories in the background. Its database is read again once that has had time to finish.
        monitor = xbmc.Monitor()
        for _ in range(10):
            if monitor.waitForAbort(1):
                return
        self.reload(keep)


class Details(xbmcgui.WindowXMLDialog):
    """Details of an add-on with its screenshots. The chosen action is left in choice for the main window."""
    BUTTONS = {201: "install", 203: "updates", 202: "open", 204: "settings", 205: None}

    def onInit(self):
        addon = self.addon
        self.zoomed = False
        self.setProperty("icon", addon["icon"] or os.path.join(MEDIA, "puzzle.png"))
        self.setProperty("name", addon["name"])
        self.setProperty("details", text(30022, addon["version"], addon["author"]) if addon["author"] else text(30021, addon["version"]))
        self.setProperty("category", kodi_text(addon["category"]))
        self.setProperty("installed", "true" if addon["installed"] else "false")
        self.setProperty("update", "true" if addon.get("update") else "")
        self.setProperty("update_label", "")
        self.setProperty("opens", "true" if addon["kind"] in OPENS else "")
        self.setProperty("description", addon["description"])
        shots = self.getControl(500)
        shots.reset()
        shots.addItems([self.screenshot(path) for path in addon["screenshots"]])
        self.setProperty("screenshots", "true" if addon["screenshots"] else "")
        self.setFocusId(9000)

    @staticmethod
    def screenshot(path):
        item = xbmcgui.ListItem()
        item.setArt({"icon": path})
        return item

    def onAction(self, action):
        if action.getId() in ACTION_BACK:
            if self.zoomed:
                self.zoomed = False
                self.setProperty("zoom", "")
            else:
                self.close()

    def onClick(self, control_id):
        if self.zoomed:
            self.zoomed = False
            self.setProperty("zoom", "")
        elif control_id == 500:
            position = self.getControl(500).getSelectedPosition()
            if 0 <= position < len(self.addon["screenshots"]):
                self.zoomed = True
                self.setProperty("zoom", self.addon["screenshots"][position])
        elif control_id in self.BUTTONS:
            self.choice = self.BUTTONS[control_id]
            self.close()


def run(start=None):
    window = MainWindow("script-monteiro-addons-main.xml", PATH, "default", "1080i")
    window.start = start
    window.doModal()
    del window
