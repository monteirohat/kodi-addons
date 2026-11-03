"""TV guide style screen and the modal list manager."""

import os
import re
import threading
from urllib.parse import urlsplit

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib import github, m3u, probe, storage, tv_menu
from resources.lib.watcher import Watcher


ADDON = storage.ADDON
TITLE = ADDON.getAddonInfo("name")
PATH = ADDON.getAddonInfo("path")
MEDIA = os.path.join(PATH, "resources", "skins", "default", "media")
ACTION_LEFT, ACTION_RIGHT = 1, 2
ACTION_BACK = (10, 92)
ACTION_CONTEXT_MENU = 117
# Buttons reached with Right on a channel row. An empty value means the row itself.
ROW_ACTIONS = ["", "favorite", "remove"]
TOOLBAR, GROUPS, CHANNELS, PREVIEW = 100, 200, 300, 500
GROUP_TITLE, GROUP_COUNT, CHANNELS_EMPTY = 401, 402, 403
MANAGER_LISTS, MANAGER_EMPTY = 100, 300
MANAGER_ADD, MANAGER_SETTINGS, MANAGER_CLOSE, MANAGER_GITHUB = 201, 202, 203, 204
# Above this many lists, a repository search first asks for a filter such as a country code.
FILTER_ABOVE = 30
# Delay before the channel column follows the highlighted group, so fast scrolling stays smooth.
FOLLOW_DELAY = 0.3

# Toolbar above the groups: icon, label and the MainWindow method it runs. Add new tools here.
TOOLS = [
    ("gear.png", 30061, "open_manager"),
    ("search.png", 30002, "search"),
    ("check.png", 30016, "check_group"),
    ("trash.png", 30001, "show_removed"),
]


def text(string_id, *arguments):
    return ADDON.getLocalizedString(string_id).format(*arguments)


def notify(message):
    xbmcgui.Dialog().notification(TITLE, message, ADDON.getAddonInfo("icon"), 4000)


def busy(active):
    xbmc.executebuiltin("ActivateWindow(busydialognocancel)" if active else "Dialog.Close(busydialognocancel)")


def suggested_name(source):
    if source.lower().startswith(("http://", "https://")):
        parts = urlsplit(source)
        stem = os.path.splitext(os.path.basename(parts.path))[0]
        return parts.hostname + (" - " + stem if stem and stem.lower() not in ("get", "playlist", "index") else "")
    return os.path.splitext(os.path.basename(source.rstrip("/")))[0] or source


def add_list():
    """Ask for a list and add it. Returns True when a list was added."""
    dialog = xbmcgui.Dialog()
    choice = dialog.select(text(30006), [text(30004), text(30005)])
    if choice == 0:
        source = dialog.input(text(30007), "http://").strip()
        if not source.lower().startswith(("http://", "https://")) or len(source) < 12:
            return False
    elif choice == 1:
        source = dialog.browseSingle(1, text(30008), "files", ".m3u|.m3u8|.txt")
        if not source:
            return False
    else:
        return False
    default_name = suggested_name(source)
    name = dialog.input(text(30009), default_name).strip() or default_name
    busy(True)
    try:
        item, channels = storage.add_list(name, source)
    except Exception as error:
        busy(False)
        dialog.ok(TITLE, text(30011, error))
        return False
    busy(False)
    storage.update_list(item["id"], count=len(channels))
    notify(text(30010, name, len(channels)))
    return True


def export_list(item):
    removed = storage.get_removed()
    try:
        channels = storage.load_channels(item, ADDON.getSettingInt("refresh_hours"))
    except Exception as error:
        xbmcgui.Dialog().ok(TITLE, text(30011, error))
        return
    folder = xbmcgui.Dialog().browseSingle(3, text(30034), "files")
    if not folder:
        return
    file_name = re.sub(r'[\\/:*?"<>|]+', "_", item["name"]).strip() + ".m3u"
    path = folder.rstrip("/\\") + "/" + file_name
    output = xbmcvfs.File(path, "w")
    try:
        written = output.write(bytearray(m3u.write(
            [channel for channel in channels if channel["id"] not in removed]).encode("utf-8")))
    finally:
        output.close()
    xbmcgui.Dialog().ok(TITLE, text(30035 if written else 30047, path))


class MainWindow(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loaded = False
        self.all_entries = []
        self.groups = []
        self.entries = []
        self.shown_index = -1
        self.shown_name = None
        self.follow_timer = None
        self.watcher = Watcher(self.on_failure)

    def onInit(self):
        # Also called when returning from full screen video. Keep the current state then.
        if self.loaded:
            return
        self.loaded = True
        self.toolbar = self.getControl(TOOLBAR)
        self.group_list = self.getControl(GROUPS)
        self.channel_list = self.getControl(CHANNELS)
        tools = []
        for icon, label, _ in TOOLS:
            item = xbmcgui.ListItem(text(label))
            item.setArt({"icon": os.path.join(MEDIA, icon)})
            tools.append(item)
        self.toolbar.addItems(tools)
        self.reload()
        if not storage.get_lists():
            self.open_manager()
        self.setFocusId(GROUPS)

    # Data

    def reload(self):
        """Load every list again and rebuild the groups, keeping the current position."""
        position = self.channel_list.getSelectedPosition()
        removed = storage.get_removed()
        hours = ADDON.getSettingInt("refresh_hours")
        entries, failed = [], []
        busy(True)
        try:
            for item in storage.get_lists():
                try:
                    channels = storage.load_channels(item, hours)
                except Exception:
                    failed.append(item["name"])
                    continue
                visible = [channel for channel in channels if channel["id"] not in removed]
                if item.get("count") != len(visible):
                    storage.update_list(item["id"], count=len(visible))
                entries += [{"channel": channel, "list": item["id"], "list_name": item["name"]} for channel in visible]
        finally:
            busy(False)
        if failed:
            notify(text(30064, ", ".join(failed)))
        groups = {}
        for entry in entries:
            for name in m3u.groups_of(entry["channel"]):
                groups.setdefault(name, []).append(entry)
        self.all_entries = entries
        self.groups = [(text(30065), self.favorite_entries()), (text(30003), entries)]
        self.groups += [(name, members) for name, members in groups.items() if name]
        if "" in groups:
            self.groups.append((text(30043), groups[""]))
        self.group_list.reset()
        self.group_list.addItems([xbmcgui.ListItem(name, str(len(members))) for name, members in self.groups])
        names = [name for name, _ in self.groups]
        if self.shown_name in names:
            index = names.index(self.shown_name)
        else:
            index = 0 if self.groups[0][1] else 1
        self.group_list.selectItem(index)
        self.show_group(index, max(position, 0))

    def favorite_entries(self):
        by_id = {}
        for entry in self.all_entries:
            by_id.setdefault(entry["channel"]["id"], entry)
        return [by_id[channel_id] for channel_id in storage.get_favorites() if channel_id in by_id]

    def show_group(self, index, position=0):
        name, members = self.groups[index]
        self.shown_index, self.shown_name = index, name
        self.show_entries(name, members, position)

    def show_entries(self, title, entries, position=0):
        self.entries = entries
        self.getControl(GROUP_TITLE).setLabel(title)
        # Name the group on the check tool, so it is clear which channels it will test.
        check_tool = [method for _, _, method in TOOLS].index("check_group")
        self.toolbar.getListItem(check_tool).setLabel(text(30095, title))
        self.getControl(GROUP_COUNT).setLabel(text(30036, len(entries)))
        favorites = set(storage.get_favorites())
        items = []
        for number, entry in enumerate(entries, 1):
            channel = entry["channel"]
            item = xbmcgui.ListItem(channel["name"], entry["list_name"])
            if channel["logo"]:
                item.setArt({"icon": channel["logo"], "thumb": channel["logo"]})
            item.setProperty("number", str(number))
            item.setProperty("favorite", "true" if channel["id"] in favorites else "false")
            item.setProperty("group", "  ·  ".join(name for name in m3u.groups_of(channel) if name) or text(30043))
            items.append(item)
        self.channel_list.reset()
        self.channel_list.addItems(items)
        if entries:
            self.channel_list.selectItem(min(position, len(entries) - 1))
            self.getControl(CHANNELS_EMPTY).setLabel("")
        elif not storage.get_lists():
            self.getControl(CHANNELS_EMPTY).setLabel(text(30048))
        else:
            self.getControl(CHANNELS_EMPTY).setLabel(text(30066 if entries is self.groups[0][1] else 30046))

    def selected_entry(self):
        position = self.channel_list.getSelectedPosition()
        return self.entries[position] if 0 <= position < len(self.entries) else None

    # Navigation

    def focus_channels(self):
        self.setProperty("row_action", "")
        if self.entries:
            self.setFocusId(CHANNELS)

    def onAction(self, action):
        action_id = action.getId()
        focus = self.getFocusId()
        row_action = ROW_ACTIONS.index(self.getProperty("row_action"))
        if focus == PREVIEW:
            # The preview is reached with Right after the last row button, and only while a channel plays.
            if action_id in ACTION_BACK or action_id == ACTION_LEFT or not xbmc.getCondVisibility("Player.HasVideo"):
                self.focus_channels()
        elif action_id in ACTION_BACK:
            if focus == CHANNELS:
                self.setFocusId(GROUPS)
            else:
                self.shutdown()
        elif focus == CHANNELS and action_id == ACTION_RIGHT:
            if row_action < len(ROW_ACTIONS) - 1:
                self.setProperty("row_action", ROW_ACTIONS[row_action + 1])
            elif xbmc.getCondVisibility("Player.HasVideo"):
                self.setFocusId(PREVIEW)
        elif focus == CHANNELS and action_id == ACTION_LEFT:
            if row_action:
                self.setProperty("row_action", ROW_ACTIONS[row_action - 1])
            else:
                self.setFocusId(GROUPS)
        elif action_id == ACTION_CONTEXT_MENU and focus == CHANNELS:
            self.channel_menu()
        elif focus == GROUPS and action_id == ACTION_LEFT:
            # Reach the toolbar without scrolling through the groups above, which would change the group.
            if self.follow_timer:
                self.follow_timer.cancel()
            self.follow_group()
            self.setFocusId(TOOLBAR)
        elif focus in (GROUPS, TOOLBAR) and action_id == ACTION_RIGHT:
            if focus == GROUPS:
                self.follow_group()
                self.focus_channels()
        elif focus == GROUPS:
            if self.follow_timer:
                self.follow_timer.cancel()
            self.follow_timer = threading.Timer(FOLLOW_DELAY, self.follow_group)
            self.follow_timer.start()

    def follow_group(self):
        index = self.group_list.getSelectedPosition()
        if 0 <= index < len(self.groups) and index != self.shown_index:
            self.show_group(index)

    def onClick(self, control_id):
        if control_id == PREVIEW:
            xbmc.executebuiltin("ActivateWindow(fullscreenvideo)")
        elif control_id == TOOLBAR:
            getattr(self, TOOLS[self.toolbar.getSelectedPosition()][2])()
        elif control_id == GROUPS:
            self.follow_group()
            self.focus_channels()
        elif control_id == CHANNELS:
            entry = self.selected_entry()
            row_action = self.getProperty("row_action")
            if entry is None:
                return
            if row_action == "favorite":
                self.toggle_favorite(entry)
            elif row_action == "remove":
                if xbmcgui.Dialog().yesno(TITLE, text(30067, entry["channel"]["name"]),
                                          nolabel=text(30040), yeslabel=text(30022)):
                    self.remove([entry])
            else:
                self.play(entry)

    def shutdown(self):
        if self.follow_timer:
            self.follow_timer.cancel()
        self.watcher.shutdown()
        self.close()

    # Channels

    def play(self, entry):
        if entry is None:
            return
        # The channel already playing is shown in full screen instead of opening it again.
        if self.watcher.is_playing(entry):
            xbmc.executebuiltin("ActivateWindow(fullscreenvideo)")
            return
        channel = entry["channel"]
        if ADDON.getSettingBool("check_before_play"):
            busy(True)
            reason = probe.check(channel["url"], ADDON.getSettingInt("check_timeout"))
            busy(False)
            if reason:
                answer = xbmcgui.Dialog().yesnocustom(
                    TITLE, text(30038, channel["name"], reason), customlabel=text(30039),
                    nolabel=text(30040), yeslabel=text(30022))
                if answer == 1:
                    self.remove([entry])
                if answer != 2:
                    return
        self.watcher.play_channel(entry)

    def on_failure(self, entry):
        """Called by the watcher when a channel did not play."""
        if not ADDON.getSettingBool("offer_remove"):
            return
        answer = xbmcgui.Dialog().yesnocustom(
            TITLE, text(30021, entry["channel"]["name"]), customlabel=text(30024),
            nolabel=text(30023), yeslabel=text(30022))
        if answer == 1:
            self.remove([entry])
        elif answer == 2:
            self.watcher.play_channel(entry)

    def toggle_favorite(self, entry):
        added = storage.toggle_favorite(entry["channel"]["id"])
        notify(text(30068 if added else 30069))
        favorites = self.favorite_entries()
        self.groups[0] = (self.groups[0][0], favorites)
        self.group_list.getListItem(0).setLabel2(str(len(favorites)))
        position = self.channel_list.getSelectedPosition()
        if self.shown_index == 0:
            self.show_entries(self.groups[0][0], favorites, position)
            if not favorites:
                self.setFocusId(GROUPS)
        else:
            self.channel_list.getListItem(position).setProperty("favorite", "true" if added else "false")

    def remove(self, entries):
        by_list = {}
        for entry in entries:
            by_list.setdefault(entry["list"], []).append(entry["channel"])
        for list_id, channels in by_list.items():
            storage.remove_channels(channels, list_id)
        notify(text(30030) if len(entries) == 1 else text(30029, len(entries)))
        self.reload()

    def channel_menu(self):
        entry = self.selected_entry()
        if entry is None:
            return
        favorite = entry["channel"]["id"] in storage.get_favorites()
        choice = xbmcgui.Dialog().contextmenu([text(30071 if favorite else 30070), text(30018), text(30019)])
        if choice == 0:
            self.toggle_favorite(entry)
        elif choice == 1:
            self.remove([entry])
        elif choice == 2:
            busy(True)
            reason = probe.check(entry["channel"]["url"], ADDON.getSettingInt("check_timeout"))
            busy(False)
            notify(text(30033, reason) if reason else text(30032))

    # Tools

    def open_manager(self):
        manager = ListManager("script-m3u-channels-manager.xml", PATH, "default", "1080i")
        manager.on_change = self.reload
        manager.doModal()
        del manager

    def search(self):
        query = xbmcgui.Dialog().input(text(30044)).strip()
        if not query:
            return
        needle = query.casefold()
        results = [entry for entry in self.all_entries if needle in entry["channel"]["name"].casefold()]
        self.shown_index, self.shown_name = -1, None
        self.show_entries(text(30042, query), results)
        if results:
            self.setFocusId(CHANNELS)
        else:
            notify(text(30045))

    def check_group(self):
        entries = list(self.entries)
        if not entries:
            return
        progress = xbmcgui.DialogProgress()
        progress.create(text(30025), "")

        def report(done, failed):
            progress.update(done * 100 // len(entries), text(30026, done, len(entries), failed))
            return not progress.iscanceled()

        by_channel = {id(entry["channel"]): entry for entry in entries}
        failed = probe.check_many([entry["channel"] for entry in entries], ADDON.getSettingInt("check_timeout"),
                                  ADDON.getSettingInt("check_workers"), report)
        progress.close()
        if not failed:
            xbmcgui.Dialog().ok(TITLE, text(30027))
            return
        answer = xbmcgui.Dialog().yesnocustom(
            TITLE, text(30072, len(failed), len(entries)), customlabel=text(30073),
            nolabel=text(30023), yeslabel=text(30074))
        if answer == 1:
            selected = range(len(failed))
        elif answer == 2:
            labels = [channel["name"] + "  [COLOR grey]" + reason + "[/COLOR]" for channel, reason in failed]
            selected = xbmcgui.Dialog().multiselect(text(30028), labels, preselect=list(range(len(failed)))) or []
        else:
            return
        if selected:
            self.remove([by_channel[id(failed[index][0])] for index in selected])

    def show_removed(self):
        removed = storage.get_removed()
        if not removed:
            notify(text(30037))
            return
        names = {item["id"]: item["name"] for item in storage.get_lists()}
        channel_ids = sorted(removed, key=lambda channel_id: removed[channel_id]["name"].casefold())
        labels = []
        for channel_id in channel_ids:
            details = removed[channel_id]
            list_name = names.get(details.get("list"))
            labels.append(details["name"] + ("  [COLOR grey]" + list_name + "[/COLOR]" if list_name else ""))
        selected = xbmcgui.Dialog().multiselect(text(30020), labels)
        if selected:
            storage.restore_channels([channel_ids[index] for index in selected])
            notify(text(30031, len(selected)))
            self.reload()


class ListManager(xbmcgui.WindowXMLDialog):
    """Modal window for adding and managing M3U lists. Calls on_change after every change."""

    def onInit(self):
        self.list_control = self.getControl(MANAGER_LISTS)
        self.populate()

    def populate(self):
        self.lists = storage.get_lists()
        position = self.list_control.getSelectedPosition()
        self.list_control.reset()
        for item in self.lists:
            detail = text(30036, item["count"]) + "  ·  " if "count" in item else ""
            self.list_control.addItem(xbmcgui.ListItem(item["name"], detail + item["source"]))
        self.getControl(MANAGER_EMPTY).setLabel("" if self.lists else text(30049))
        if self.lists:
            self.list_control.selectItem(min(max(position, 0), len(self.lists) - 1))
        else:
            self.setFocusId(MANAGER_ADD)

    def changed(self):
        self.populate()
        self.on_change()

    def onAction(self, action):
        if action.getId() in ACTION_BACK:
            self.close()

    def onClick(self, control_id):
        if control_id == MANAGER_ADD:
            if add_list():
                self.changed()
                self.setFocusId(MANAGER_LISTS)
        elif control_id == MANAGER_SETTINGS:
            ADDON.openSettings()
        elif control_id == MANAGER_GITHUB:
            repos = RepoManager("script-m3u-channels-repos.xml", PATH, "default", "1080i")
            repos.on_change = self.changed
            repos.doModal()
            del repos
        elif control_id == MANAGER_CLOSE:
            self.close()
        elif control_id == MANAGER_LISTS:
            position = self.list_control.getSelectedPosition()
            if 0 <= position < len(self.lists):
                self.list_menu(self.lists[position])

    def list_menu(self, item):
        dialog = xbmcgui.Dialog()
        choice = dialog.contextmenu([text(30012), text(30013), text(30017), text(30014)])
        if choice == 0:
            busy(True)
            try:
                channels = storage.refresh(item)
            except Exception as error:
                busy(False)
                dialog.ok(TITLE, text(30011, error))
                return
            busy(False)
            notify(text(30041, len(channels)))
            self.changed()
        elif choice == 1:
            name = dialog.input(text(30009), item["name"]).strip()
            if name:
                storage.update_list(item["id"], name=name)
                self.changed()
        elif choice == 2:
            export_list(item)
        elif choice == 3 and dialog.yesno(TITLE, text(30015, item["name"])):
            storage.delete_list(item["id"])
            self.changed()


class RepoManager(xbmcgui.WindowXMLDialog):
    """Modal window for GitHub repositories. Searching one adds the lists it contains."""

    def onInit(self):
        self.list_control = self.getControl(MANAGER_LISTS)
        self.populate()

    def populate(self):
        self.repos = storage.get_repos()
        position = self.list_control.getSelectedPosition()
        self.list_control.reset()
        for repo in self.repos:
            detail = "github.com/" + repo["owner"] + "/" + repo["repo"]
            if repo.get("branch"):
                detail += "  ·  " + repo["branch"]
            self.list_control.addItem(xbmcgui.ListItem(github.label(repo), detail))
        self.getControl(MANAGER_EMPTY).setLabel("" if self.repos else text(30094))
        if self.repos:
            self.list_control.selectItem(min(max(position, 0), len(self.repos) - 1))
        else:
            self.setFocusId(MANAGER_ADD)

    def onAction(self, action):
        if action.getId() in ACTION_BACK:
            self.close()

    def onClick(self, control_id):
        if control_id == MANAGER_ADD:
            self.add_repo()
        elif control_id == MANAGER_CLOSE:
            self.close()
        elif control_id == MANAGER_LISTS:
            position = self.list_control.getSelectedPosition()
            if 0 <= position < len(self.repos):
                self.repo_menu(self.repos[position])

    def repo_menu(self, repo):
        choice = xbmcgui.Dialog().contextmenu([text(30078), text(30079)])
        if choice == 0:
            self.search(repo)
        elif choice == 1 and xbmcgui.Dialog().yesno(TITLE, text(30080, github.label(repo)),
                                                    nolabel=text(30040), yeslabel=text(30022)):
            storage.save_repos([item for item in self.repos if item is not repo])
            self.populate()

    def add_repo(self):
        answer = xbmcgui.Dialog().input(text(30077)).strip()
        if not answer:
            return
        repo = github.parse_repo(answer)
        if repo is None:
            xbmcgui.Dialog().ok(TITLE, text(30088))
            return
        if any(github.label(item).casefold() == github.label(repo).casefold() for item in self.repos):
            notify(text(30092))
        else:
            storage.save_repos(self.repos + [repo])
            self.populate()
            self.list_control.selectItem(len(self.repos) - 1)
        self.search(repo)

    def search(self, repo):
        name = github.label(repo)
        busy(True)
        try:
            found = github.find_lists(repo)
        except github.RateLimited:
            busy(False)
            xbmcgui.Dialog().ok(TITLE, text(30090))
            return
        except Exception as error:
            busy(False)
            xbmcgui.Dialog().ok(TITLE, text(30087, error))
            return
        busy(False)
        existing = {item["source"] for item in storage.get_lists()}
        candidates = [item for item in found if item["url"] not in existing]
        if not candidates:
            xbmcgui.Dialog().ok(TITLE, text(30082, name))
            return
        if len(candidates) > FILTER_ABOVE:
            query = xbmcgui.Dialog().input(text(30084, len(candidates))).strip().casefold()
            if query:
                candidates = [item for item in candidates if query in item["path"].casefold()]
                if not candidates:
                    notify(text(30091, query))
                    return
        labels = ["%s  [COLOR grey]%d KB[/COLOR]" % (item["path"], max(item["size"] // 1024, 1)) for item in candidates]
        selected = xbmcgui.Dialog().multiselect(text(30083, name), labels)
        if not selected:
            return
        progress = xbmcgui.DialogProgress()
        progress.create(text(30085), "")
        added = ignored = 0
        for done, index in enumerate(selected):
            if progress.iscanceled():
                break
            item = candidates[index]
            progress.update(done * 100 // len(selected), item["path"])
            list_name = repo["owner"] + " - " + os.path.splitext(os.path.basename(item["path"]))[0]
            try:
                added_list, channels = storage.add_list(list_name, item["url"])
            except Exception:
                # Empty lists, single stream playlists and unreachable files are skipped.
                ignored += 1
                continue
            storage.update_list(added_list["id"], count=len(channels))
            added += 1
        progress.close()
        xbmcgui.Dialog().ok(TITLE, text(30086, added, ignored))
        if added:
            self.on_change()


def run():
    # Tells the TV menu service that Easy Channel is already on screen.
    home = xbmcgui.Window(10000)
    home.setProperty(tv_menu.RUNNING_PROPERTY, "open")
    try:
        window = MainWindow("script-m3u-channels-main.xml", PATH, "default", "1080i")
        window.doModal()
        del window
    finally:
        home.clearProperty(tv_menu.RUNNING_PROPERTY)
