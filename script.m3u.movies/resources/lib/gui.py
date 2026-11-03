"""Movie and series catalog, movie and series details, and the modal list and repository managers."""

import os
import re
import threading
from urllib.parse import urlsplit

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib import github, m3u, movies_menu, probe, series, storage
from resources.lib.watcher import Watcher


ADDON = storage.ADDON
TITLE = ADDON.getAddonInfo("name")
PATH = ADDON.getAddonInfo("path")
MEDIA = os.path.join(PATH, "resources", "skins", "default", "media")
ACTION_LEFT, ACTION_RIGHT = 1, 2
ACTION_BACK = (10, 92)
ACTION_CONTEXT_MENU = 117
TOOLBAR, GROUPS, CHANNELS = 100, 200, 300
DETAILS_PLAY, DETAILS_FAVORITE, DETAILS_REMOVE = 201, 202, 203
SERIES_SEASONS, SERIES_EPISODES = 300, 400
# Fixed groups at the top of the list, in this order.
CONTINUE_GROUP, FAVORITES_GROUP, MOVIES_GROUP, SERIES_GROUP = 0, 1, 2, 3
# A movie stopped before this many seconds starts from the beginning next time.
RESUME_AFTER = 60
GROUP_TITLE, GROUP_COUNT, CHANNELS_EMPTY = 401, 402, 403
MANAGER_LISTS, MANAGER_EMPTY = 100, 300
MANAGER_ADD, MANAGER_SETTINGS, MANAGER_CLOSE, MANAGER_GITHUB = 201, 202, 203, 204
# Above this many lists, a repository search first asks for a filter such as a country code.
FILTER_ABOVE = 30
# Delay before the catalog follows the highlighted group, so fast scrolling stays smooth.
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


def item_id(item):
    """Identity of a catalog item for favorites: the stream of a movie or the key of a series."""
    return "series:" + item["key"] if item.get("series") else item["channel"]["id"]


def item_name(item):
    return item["name"] if item.get("series") else item["channel"]["name"]


def item_entries(item):
    """Playable entries of a catalog item: the movie itself or the episodes of a series."""
    return item["episodes"] if item.get("series") else [item]


def time_text(seconds):
    hours, rest = divmod(int(seconds), 3600)
    return "%d:%02d:%02d" % (hours, rest // 60, rest % 60) if hours else "%d:%02d" % (rest // 60, rest % 60)


def resumable(state):
    return bool(state) and not state.get("watched") and state.get("position", 0) >= RESUME_AFTER


def next_episode(show, progress):
    """Episode to continue with: the one stopped midway, or the first unwatched after the last watched one."""
    episodes = show["episodes"]
    states = [progress.get(entry["channel"]["id"], {}) for entry in episodes]
    touched = [(state["time"], index) for index, state in enumerate(states)
               if state.get("watched") or resumable(state)]
    if not touched:
        return episodes[0], False
    last = max(touched)[1]
    if not states[last].get("watched"):
        return episodes[last], True
    for index in list(range(last + 1, len(episodes))) + list(range(last)):
        if not states[index].get("watched"):
            return episodes[index], True
    return episodes[0], True


CANCELLED = object()


def display_name(entry):
    """Name shown in messages: the movie name, or the series and episode code for an episode."""
    if "episode" in entry:
        return entry["episode"]["show"] + " " + episode_code(entry)
    return entry["channel"]["name"]


def reason_text(reason):
    """Short reason in the interface language. Network errors are reported as no answer."""
    return reason if reason.startswith("HTTP") else text(30137)


def check_with_progress(channel, name):
    """Check a stream while showing a dialog that can be cancelled. Returns None, a reason, or CANCELLED."""
    result = []
    worker = threading.Thread(target=lambda: result.append(probe.check(channel["url"], ADDON.getSettingInt("check_timeout"))),
                              daemon=True)
    worker.start()
    # Most streams answer at once, so the dialog only appears for slow ones.
    worker.join(0.7)
    if result:
        return result[0]
    progress = xbmcgui.DialogProgress()
    progress.create(TITLE, text(30136, name))
    monitor = xbmc.Monitor()
    while worker.is_alive():
        if progress.iscanceled() or monitor.waitForAbort(0.1):
            progress.close()
            return CANCELLED
    progress.close()
    return result[0] if result else None


def episode_code(entry):
    return text(30133, entry["episode"]["season"], entry["episode"]["number"])


def duration_text(seconds):
    if seconds < 60:
        return ""
    hours, minutes = divmod(seconds // 60, 60)
    return text(30112, hours, minutes) if hours else text(30113, minutes)


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
        self.grid_position = -1
        self.start_group = None
        self.movies, self.shows, self.catalog, self.progress = [], [], [], {}
        self.watcher = Watcher(self.on_failure, self.on_progress)

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
        self.all_entries = entries
        self.movies, self.shows = series.build(entries)
        self.catalog = self.movies + self.shows
        self.build_groups(position)

    def build_groups(self, position=None):
        """Rebuild the groups from the loaded catalog, for example after playback changed the progress."""
        if position is None:
            position = self.channel_list.getSelectedPosition()
        groups = {}
        for movie in self.movies:
            for name in series.movie_groups(movie["channel"]):
                groups.setdefault(name, []).append(movie)
        for show in self.shows:
            for name in show["groups"]:
                groups.setdefault(name, []).append(show)
        self.progress = storage.get_progress()
        self.groups = [(text(30116), self.continue_items()), (text(30065), self.favorite_entries()),
                       (text(30003), self.movies), (text(30117), self.shows)]
        self.groups += [(name, members) for name, members in groups.items() if name]
        if "" in groups:
            self.groups.append((text(30043), groups[""]))
        self.group_list.reset()
        self.group_list.addItems([xbmcgui.ListItem(name, str(len(members))) for name, members in self.groups])
        names = [name for name, _ in self.groups]
        if self.shown_name in names:
            index = names.index(self.shown_name)
        elif self.start_group == "series":
            index = SERIES_GROUP
        else:
            index = next(index for index in (CONTINUE_GROUP, FAVORITES_GROUP, MOVIES_GROUP)
                         if self.groups[index][1] or index == MOVIES_GROUP)
        self.group_list.selectItem(index)
        self.show_group(index, max(position, 0))

    def favorite_entries(self):
        by_id = {item_id(item): item for item in self.catalog}
        return [by_id[favorite] for favorite in storage.get_favorites() if favorite in by_id]

    def continue_items(self):
        """Movies stopped midway and series with watched episodes left to watch, most recent first."""
        started = []
        for movie in self.movies:
            state = self.progress.get(movie["channel"]["id"])
            if resumable(state):
                started.append((state["time"], movie))
        for show in self.shows:
            states = [self.progress.get(entry["channel"]["id"], {}) for entry in show["episodes"]]
            if all(state.get("watched") for state in states):
                continue
            times = [state["time"] for state in states if state.get("watched") or resumable(state)]
            if times:
                started.append((max(times), show))
        return [item for _, item in sorted(started, key=lambda pair: -pair[0])]

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
        self.getControl(GROUP_COUNT).setLabel(text(30135) if len(entries) == 1 else text(30132, len(entries)))
        favorites = set(storage.get_favorites())
        items = [self.card(entry, favorites) for entry in entries]
        self.channel_list.reset()
        self.channel_list.addItems(items)
        if entries:
            self.channel_list.selectItem(min(position, len(entries) - 1))
            self.getControl(CHANNELS_EMPTY).setLabel("")
        elif not storage.get_lists():
            self.getControl(CHANNELS_EMPTY).setLabel(text(30048))
        else:
            empty = {CONTINUE_GROUP: 30130, FAVORITES_GROUP: 30066}.get(self.shown_index, 30046)
            self.getControl(CHANNELS_EMPTY).setLabel(text(empty))

    def card(self, entry, favorites):
        """Catalog card of a movie or a series, with its detail line and badges."""
        item = xbmcgui.ListItem(item_name(entry), entry["list_name"])
        logo = entry["logo"] if entry.get("series") else entry["channel"]["logo"]
        if logo:
            item.setArt({"icon": logo, "thumb": logo, "poster": logo})
        if entry.get("series"):
            episode, started = next_episode(entry, self.progress)
            count = len(entry["episodes"])
            detail = episode_code(episode) if started else (text(30134) if count == 1 else text(30127, count))
            watched = all(self.progress.get(each["channel"]["id"], {}).get("watched") for each in entry["episodes"])
        else:
            state = self.progress.get(entry["channel"]["id"], {})
            detail = text(30126, time_text(state["position"])) if resumable(state) else duration_text(entry["channel"]["duration"])
            watched = state.get("watched", False)
        item.setProperty("duration", detail)
        item.setProperty("favorite", "true" if item_id(entry) in favorites else "false")
        item.setProperty("watched", "true" if watched else "false")
        return item

    def selected_entry(self):
        position = self.channel_list.getSelectedPosition()
        return self.entries[position] if 0 <= position < len(self.entries) else None

    # Navigation

    def focus_channels(self):
        if self.entries:
            self.setFocusId(CHANNELS)
            self.grid_position = self.channel_list.getSelectedPosition()

    def onAction(self, action):
        action_id = action.getId()
        focus = self.getFocusId()
        if focus == CHANNELS:
            # Left in the first column does not move the selection, so it leads back to the groups.
            previous, self.grid_position = self.grid_position, self.channel_list.getSelectedPosition()
            if action_id == ACTION_LEFT and self.grid_position == previous:
                self.setFocusId(GROUPS)
                return
        if action_id in ACTION_BACK:
            if focus == CHANNELS:
                self.setFocusId(GROUPS)
            else:
                self.shutdown()
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
        if control_id == TOOLBAR:
            getattr(self, TOOLS[self.toolbar.getSelectedPosition()][2])()
        elif control_id == GROUPS:
            self.follow_group()
            self.focus_channels()
        elif control_id == CHANNELS:
            entry = self.selected_entry()
            if entry is not None:
                self.open_details(entry)

    def open_details(self, entry):
        if entry.get("series"):
            details = SeriesDetails("script-m3u-movies-series.xml", PATH, "default", "1080i")
        else:
            details = MovieDetails("script-m3u-movies-details.xml", PATH, "default", "1080i")
        details.window, details.entry, details.choice, details.episode, details.start = self, entry, None, None, 0
        details.doModal()
        choice, episode, start = details.choice, details.episode, details.start
        del details
        if choice == "play":
            self.watcher.play_channel(episode or entry, start)
        elif choice == "remove":
            self.remove([entry])

    def shutdown(self):
        if self.follow_timer:
            self.follow_timer.cancel()
        self.watcher.shutdown()
        self.close()

    # Movies

    def prepare(self, entry):
        """Ask where to start and check the stream. Returns the start position, or None to stay.

        Kodi waits for an unreachable server on its interface thread before it plays, which freezes the
        screen. Checking the stream first, with a dialog that can be cancelled, avoids that.
        """
        channel = entry["channel"]
        start = 0
        state = storage.get_progress().get(channel["id"])
        if resumable(state):
            choice = xbmcgui.Dialog().contextmenu([text(30124, time_text(state["position"])), text(30125)])
            if choice < 0:
                return None
            start = state["position"] if choice == 0 else 0
        name = display_name(entry)
        reason = check_with_progress(channel, name)
        if reason is CANCELLED:
            return None
        if reason:
            answer = xbmcgui.Dialog().yesnocustom(
                TITLE, text(30038, name, reason_text(reason)), customlabel=text(30039),
                nolabel=text(30040), yeslabel=text(30022))
            if answer == 1:
                self.remove([entry])
            if answer != 2:
                return None
        return start

    def on_progress(self, entry, position, total, finished):
        """Called by the watcher while a movie plays and when it stops."""
        if total <= 0:
            return
        storage.save_progress(entry["channel"]["id"], position, total)
        if finished:
            self.build_groups()

    def on_failure(self, entry):
        """Called by the watcher when a channel did not play."""
        if not ADDON.getSettingBool("offer_remove"):
            return
        answer = xbmcgui.Dialog().yesnocustom(
            TITLE, text(30021, display_name(entry)), customlabel=text(30024),
            nolabel=text(30023), yeslabel=text(30022))
        if answer == 1:
            self.remove([entry])
        elif answer == 2:
            self.watcher.play_channel(entry)

    def toggle_favorite(self, entry):
        added = storage.toggle_favorite(item_id(entry))
        notify(text(30068 if added else 30069))
        favorites = self.favorite_entries()
        self.groups[FAVORITES_GROUP] = (self.groups[FAVORITES_GROUP][0], favorites)
        self.group_list.getListItem(FAVORITES_GROUP).setLabel2(str(len(favorites)))
        position = self.channel_list.getSelectedPosition()
        if self.shown_index == FAVORITES_GROUP:
            self.show_entries(self.groups[FAVORITES_GROUP][0], favorites, position)
            if not favorites:
                self.setFocusId(GROUPS)
        else:
            self.channel_list.getListItem(position).setProperty("favorite", "true" if added else "false")

    def remove(self, items):
        entries = [entry for item in items for entry in item_entries(item)]
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
        favorite = item_id(entry) in storage.get_favorites()
        remove_label = text(30122 if entry.get("series") else 30018)
        choice = xbmcgui.Dialog().contextmenu([text(30071 if favorite else 30070), remove_label, text(30019)])
        if choice == 0:
            self.toggle_favorite(entry)
        elif choice == 1:
            self.remove([entry])
        elif choice == 2 and entry.get("series"):
            self.check_entries(entry["episodes"])
        elif choice == 2:
            busy(True)
            reason = probe.check(entry["channel"]["url"], ADDON.getSettingInt("check_timeout"))
            busy(False)
            notify(text(30033, reason) if reason else text(30032))

    # Tools

    def open_manager(self):
        manager = ListManager("script-m3u-movies-manager.xml", PATH, "default", "1080i")
        manager.on_change = self.reload
        manager.doModal()
        del manager

    def search(self):
        query = xbmcgui.Dialog().input(text(30044)).strip()
        if not query:
            return
        needle = query.casefold()
        results = [movie for movie in self.movies if needle in movie["channel"]["name"].casefold()]
        results += [show for show in self.shows if needle in show["name"].casefold()
                    or any(needle in entry["channel"]["name"].casefold() for entry in show["episodes"])]
        self.shown_index, self.shown_name = -1, None
        self.show_entries(text(30042, query), results)
        if results:
            self.setFocusId(CHANNELS)
        else:
            notify(text(30045))

    def check_group(self):
        self.check_entries([entry for item in self.entries for entry in item_entries(item)])

    def check_entries(self, entries):
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


class MovieDetails(xbmcgui.WindowXMLDialog):
    """Poster and details of a movie, with play, favorite and remove buttons. Sets choice for the catalog."""

    def onInit(self):
        movie = self.entry["channel"]
        groups = "  ·  ".join(name for name in series.movie_groups(movie) if name) or text(30043)
        self.setProperty("title", movie["name"])
        self.setProperty("poster", movie["logo"])
        self.setProperty("group", groups)
        self.setProperty("list", self.entry["list_name"])
        self.setProperty("duration", duration_text(movie["duration"]))
        self.update_favorite()
        self.setFocusId(DETAILS_PLAY)

    def update_favorite(self):
        favorite = self.entry["channel"]["id"] in storage.get_favorites()
        self.setProperty("favorite", "true" if favorite else "false")
        self.getControl(DETAILS_FAVORITE).setLabel(text(30115 if favorite else 30114))

    def onAction(self, action):
        if action.getId() in ACTION_BACK:
            self.close()

    def onClick(self, control_id):
        if control_id == DETAILS_PLAY:
            start = self.window.prepare(self.entry)
            if start is not None:
                self.choice, self.start = "play", start
                self.close()
            elif self.entry["channel"]["id"] in storage.get_removed():
                self.close()
        elif control_id == DETAILS_FAVORITE:
            self.window.toggle_favorite(self.entry)
            self.update_favorite()
        elif control_id == DETAILS_REMOVE:
            if xbmcgui.Dialog().yesno(TITLE, text(30067, self.entry["channel"]["name"]),
                                      nolabel=text(30040), yeslabel=text(30022)):
                self.choice = "remove"
                self.close()


class SeriesDetails(xbmcgui.WindowXMLDialog):
    """Poster, seasons and episodes of a series. Sets choice and the episode to play for the catalog."""

    def onInit(self):
        show = self.entry
        self.progress = storage.get_progress()
        self.next, started = next_episode(show, self.progress)
        self.setProperty("title", show["name"])
        self.setProperty("poster", show["logo"])
        self.setProperty("info", text(30121, len(show["seasons"]), len(show["episodes"])))
        self.setProperty("group", "  ·  ".join(show["groups"]) or show["list_name"])
        self.getControl(DETAILS_PLAY).setLabel(text(30118 if started else 30119, self.next["episode"]["season"],
                                                    self.next["episode"]["number"]))
        self.update_favorite()
        seasons = self.getControl(SERIES_SEASONS)
        seasons.reset()
        seasons.addItems([xbmcgui.ListItem(text(30120, season)) for season in show["seasons"]])
        self.season = show["seasons"].index(self.next["episode"]["season"])
        seasons.selectItem(self.season)
        self.show_season(select=self.next)
        self.setFocusId(DETAILS_PLAY)

    def show_season(self, select=None):
        season = self.entry["seasons"][self.season]
        self.episodes = [entry for entry in self.entry["episodes"] if entry["episode"]["season"] == season]
        items = []
        for entry in self.episodes:
            title = entry["episode"]["title"]
            number = entry["episode"]["number"]
            # Specials have no episode number, only their title.
            label = title if number == 0 and title else "E%02d" % number + ("  ·  " + title if title else "")
            item = xbmcgui.ListItem(label)
            state = self.progress.get(entry["channel"]["id"], {})
            if resumable(state):
                item.setLabel2(text(30126, time_text(state["position"])))
            else:
                item.setLabel2(duration_text(entry["channel"]["duration"]))
            item.setProperty("watched", "true" if state.get("watched") else "false")
            items.append(item)
        episodes = self.getControl(SERIES_EPISODES)
        episodes.reset()
        episodes.addItems(items)
        if select in self.episodes:
            episodes.selectItem(self.episodes.index(select))

    def update_favorite(self):
        favorite = item_id(self.entry) in storage.get_favorites()
        self.setProperty("favorite", "true" if favorite else "false")
        self.getControl(DETAILS_FAVORITE).setLabel(text(30115 if favorite else 30114))

    def onAction(self, action):
        if action.getId() in ACTION_BACK:
            self.close()
        elif self.getFocusId() == SERIES_SEASONS:
            season = self.getControl(SERIES_SEASONS).getSelectedPosition()
            if season != self.season and 0 <= season < len(self.entry["seasons"]):
                self.season = season
                self.show_season()

    def onClick(self, control_id):
        if control_id == DETAILS_PLAY:
            self.play(self.next)
        elif control_id == DETAILS_FAVORITE:
            self.window.toggle_favorite(self.entry)
            self.update_favorite()
        elif control_id == DETAILS_REMOVE:
            if xbmcgui.Dialog().yesno(TITLE, text(30123, self.entry["name"], len(self.entry["episodes"])),
                                      nolabel=text(30040), yeslabel=text(30022)):
                self.choice = "remove"
                self.close()
        elif control_id == SERIES_SEASONS:
            self.setFocusId(SERIES_EPISODES)
        elif control_id == SERIES_EPISODES:
            position = self.getControl(SERIES_EPISODES).getSelectedPosition()
            if 0 <= position < len(self.episodes):
                self.play(self.episodes[position])

    def play(self, episode):
        """Close and play the episode once its stream answers. Otherwise stay, to pick another episode."""
        start = self.window.prepare(episode)
        if start is not None:
            self.choice, self.episode, self.start = "play", episode, start
            self.close()
            return
        if episode["channel"]["id"] in storage.get_removed():
            self.entry["episodes"] = [entry for entry in self.entry["episodes"] if entry is not episode]
            if not self.entry["episodes"]:
                self.close()
                return
            self.entry["seasons"] = sorted({entry["episode"]["season"] for entry in self.entry["episodes"]})
            self.season = min(self.season, len(self.entry["seasons"]) - 1)
            self.show_season()


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
            repos = RepoManager("script-m3u-movies-repos.xml", PATH, "default", "1080i")
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


def run(arguments=()):
    """Open the catalog. The argument "series" opens it on the series."""
    # Tells the Movies menu service that Easy Movie is already on screen.
    home = xbmcgui.Window(10000)
    home.setProperty(movies_menu.RUNNING_PROPERTY, "open")
    try:
        window = MainWindow("script-m3u-movies-main.xml", PATH, "default", "1080i")
        window.start_group = "series" if "series" in arguments else None
        window.doModal()
        del window
    finally:
        home.clearProperty(movies_menu.RUNNING_PROPERTY)
