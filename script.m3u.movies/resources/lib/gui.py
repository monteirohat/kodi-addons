"""Movie and series catalog, movie and series details, and the modal list and repository managers."""

from concurrent.futures import ThreadPoolExecutor
import itertools
import os
import posixpath
import re
import threading
import time
from urllib.parse import quote, urlencode, urlsplit

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib import cinemeta, folders, github, m3u, movies_menu, probe, series, storage, stremio, torrents
from resources.lib.watcher import Watcher


ADDON = storage.ADDON
TITLE = ADDON.getAddonInfo("name")
PATH = ADDON.getAddonInfo("path")
MEDIA = os.path.join(PATH, "resources", "skins", "default", "media")
ACTION_LEFT, ACTION_RIGHT, ACTION_UP, ACTION_DOWN = 1, 2, 3, 4
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
MANAGER_ADD, MANAGER_SETTINGS, MANAGER_CLOSE, MANAGER_GITHUB, MANAGER_REMOVED = 201, 202, 203, 204, 205
CATALOG_TABS, CATALOG_ADDONS, CATALOG_WATCH, CATALOG_MY_LIST, CATALOG_SOURCES = 100, 101, 201, 202, 203
SOURCES_LIST, SOURCES_EMPTY = 100, 300
ADDONS_LIST, ADDONS_ADD, ADDONS_CLOSE = 100, 201, 203
# Types of addon catalogs shown in each tab of the catalog. Anime catalogs list mostly series.
TAB_TYPES = {"movie": ("movie",), "series": ("series", "anime")}
RESOURCE_NAMES = {"catalog": 30284, "meta": 30287, "stream": 30285, "subtitles": 30286}
TYPE_NAMES = {"movie": 30201, "series": 30117, "channel": 30288}
# Position of Popular in the categories of the catalog, the one shown first.
POPULAR_CATEGORY = 2
# The catalog loads its next page when the selection gets this close to the last poster.
LOAD_MORE_BEFORE = 12
DOWNLOADS_LIST, DOWNLOADS_EMPTY = 100, 300
DOWNLOADS_MAGNET, DOWNLOADS_FILE, DOWNLOADS_FOLDER, DOWNLOADS_CLOSE = 201, 202, 203, 204
# Below this many free bytes, a download folder counts as full.
LOW_SPACE = 200 << 20
# Seconds between updates of the download list.
DOWNLOADS_REFRESH = 2
# Above this many lists, a repository search first asks for a filter such as a country code.
FILTER_ABOVE = 30
# Delay before the catalog follows the highlighted group, so fast scrolling stays smooth.
FOLLOW_DELAY = 0.3
# Cinemeta lookups made at the same time for the videos of folders.
LOOKUP_WORKERS = 4

# Toolbar above the groups: icon, label and the MainWindow method it runs. Add new tools here.
TOOLS = [
    ("gear.png", 30061, "open_manager"),
    ("search.png", 30002, "search"),
    ("catalog.png", 30200, "open_catalog"),
    ("check.png", 30016, "check_group"),
    ("download.png", 30160, "open_downloads"),
]

# Genres of Cinemeta and their names. Series also have the last three.
GENRES = {"Action": 30230, "Adventure": 30231, "Animation": 30232, "Biography": 30233, "Comedy": 30234,
          "Crime": 30235, "Documentary": 30236, "Drama": 30237, "Family": 30238, "Fantasy": 30239,
          "History": 30240, "Horror": 30241, "Mystery": 30242, "Romance": 30243, "Sci-Fi": 30244, "Sport": 30245,
          "Thriller": 30246, "War": 30247, "Western": 30248, "Reality-TV": 30249, "Talk-Show": 30250,
          "Game-Show": 30251}
SERIES_ONLY_GENRES = ("Reality-TV", "Talk-Show", "Game-Show")
# Other genres Cinemeta gives titles, which have no category.
OTHER_GENRES = {"Short": 30252, "Music": 30253, "Musical": 30254, "News": 30255, "TV Movie": 30256,
                "Action & Adventure": 30257, "Sci-Fi & Fantasy": 30258, "Talk": 30259, "Film-Noir": 30260}


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
    choice = dialog.select(text(30006), [text(30004), text(30005), text(30138)])
    kind = "m3u"
    if choice == 0:
        source = dialog.input(text(30007), "http://").strip()
        if not source.lower().startswith(("http://", "https://")) or len(source) < 12:
            return False
    elif choice == 1:
        source = dialog.browseSingle(1, text(30008), "files", ".m3u|.m3u8|.txt")
        if not source:
            return False
    elif choice == 2:
        source = dialog.browseSingle(0, text(30139), "files").rstrip("/")
        if not source:
            return False
        kind = "folder"
    else:
        return False
    default_name = suggested_name(source)
    name = dialog.input(text(30009), default_name).strip() or default_name
    busy(True)
    try:
        item, channels = storage.add_list(name, source, kind)
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


def is_local(entry):
    """Whether an entry is a video file of a folder list, which can be renamed and deleted."""
    return entry.get("folder", False)


def subtitle_target(entry, show=None):
    """What a movie or an episode of show is, to look up its subtitles online: its IMDb id when Cinemeta gave one,
    or its name and year, and the path of a video file."""
    channel = entry["channel"]
    path = m3u.base_url(channel["url"]) if is_local(entry) else ""
    episode = entry.get("episode")
    if episode:
        meta = (show or {}).get("meta") or {}
        return {"kind": "series", "imdb": meta.get("id") or "", "title": episode["show"], "year": meta.get("year") or 0,
                "season": episode["season"], "episode": episode["number"], "path": path}
    meta = entry.get("meta") or {}
    title, year = (meta["name"], meta.get("year") or 0) if meta.get("name") else folders.title_and_year(channel["name"])
    return {"kind": "movie", "imdb": meta.get("id") or "", "title": title, "year": year, "path": path}


def local_paths(item):
    return [m3u.base_url(entry["channel"]["url"]) for entry in item_entries(item)]


def video_thumbnail(path):
    """A frame of the video, extracted by Kodi the first time it is shown."""
    return "image://video@" + quote(path, safe="") + "/"


def genre_name(genre):
    string_id = GENRES.get(genre) or OTHER_GENRES.get(genre)
    return text(string_id) if string_id else genre


def meta_line(meta, duration=""):
    """Year, IMDb rating, genres and duration of a movie or series, as one line."""
    parts = [duration] if duration else []
    if meta.get("year"):
        parts.append(str(meta["year"]))
    if meta.get("rating"):
        parts.append(text(30155, meta["rating"]))
    if meta.get("genres"):
        parts.append(", ".join(genre_name(genre) for genre in meta["genres"][:3]))
    return "  ·  ".join(parts)


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
        # A group is built by one call at a time. A newer request stops an older one, see follow_group.
        self.show_lock = threading.Lock()
        self.follow_requests = itertools.count()
        self.follow_request = 0
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
                folder = storage.is_folder(item)
                try:
                    channels = storage.load_channels(item, hours)
                except Exception:
                    failed.append(item["name"])
                    continue
                visible = [channel for channel in channels if channel["id"] not in removed]
                if item.get("count") != len(visible):
                    storage.update_list(item["id"], count=len(visible))
                entries += [{"channel": channel, "list": item["id"], "list_name": item["name"], "folder": folder}
                            for channel in visible]
        finally:
            busy(False)
        if failed:
            notify(text(30064, ", ".join(failed)))
        self.all_entries = entries
        self.movies, self.shows = series.build(entries)
        # Newest movies first, such as a finished download. Movies added together keep the order of their lists.
        added = storage.added_times([(movie["channel"]["id"], movie["folder"]) for movie in self.movies])
        self.movies.sort(key=lambda movie: -added.get(movie["channel"]["id"], 0))
        for show in self.shows:
            show["folder"] = show["episodes"][0]["folder"]
            show["list"] = show["episodes"][0]["list"]
        self.catalog = self.movies + self.shows
        self.apply_metadata()
        self.build_groups(position)
        self.start_lookup()

    # Details of the videos of folders, from Cinemeta

    def apply_metadata(self):
        """Give the videos of folders their Cinemeta details, and a poster when the folder has none."""
        metadata = storage.get_metadata()
        for item in self.catalog:
            if not is_local(item):
                continue
            meta = item["meta"] = metadata.get(item_id(item)) or {}
            art = item if item.get("series") else item["channel"]
            local = art.setdefault("local_logo", art["logo"])
            art["logo"] = local or meta.get("poster") or ("" if item.get("series") else video_thumbnail(local_paths(item)[0]))

    def lookup_query(self, item):
        if item.get("series"):
            return "series", item["name"], 0
        title, year = folders.movie_query(item["channel"])
        return "movie", title, year

    def start_lookup(self):
        """Look up the folder videos that have no details yet, then show them. Runs on a thread."""
        if not ADDON.getSettingBool("folder_metadata"):
            return
        known = storage.get_metadata()
        pending = [item for item in self.catalog if is_local(item) and item_id(item) not in known]
        if not pending or getattr(self, "lookup_running", False):
            return
        self.lookup_running = True

        def lookup(item):
            try:
                # An empty result marks a video with no match, so it is not looked up every time.
                return item_id(item), cinemeta.lookup(*self.lookup_query(item)) or {}
            except Exception:
                return item_id(item), None

        def run():
            try:
                with ThreadPoolExecutor(max_workers=LOOKUP_WORKERS) as executor:
                    found = dict(executor.map(lookup, pending))
                found = {key: value for key, value in found.items() if value is not None}
                if found:
                    storage.save_metadata(found)
                    self.apply_metadata()
                    self.build_groups()
            finally:
                self.lookup_running = False

        threading.Thread(target=run, daemon=True).start()

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
        with self.show_lock:
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

    def show_group(self, index, position=0, stale=None):
        name, members = self.groups[index]
        if self.show_entries(name, members, position, stale, index):
            self.shown_index, self.shown_name = index, name

    def show_entries(self, title, entries, position=0, stale=None, group=None):
        """Show cards in the catalog. Returns False when stale() stopped it before anything changed.

        group is the index of the group shown, which picks the message of an empty group.
        """
        favorites = set(storage.get_favorites())
        items = []
        for number, entry in enumerate(entries, 1):
            # Building thousands of cards takes a while, so a newer group can stop it.
            if stale and number % 200 == 0 and stale():
                return False
            items.append(self.card(entry, favorites))
        if stale and stale():
            return False
        self.entries = entries
        self.getControl(GROUP_TITLE).setLabel(title)
        # Name the group on the check tool, so it is clear which channels it will test.
        check_tool = [method for _, _, method in TOOLS].index("check_group")
        self.toolbar.getListItem(check_tool).setLabel(text(30095, title))
        self.getControl(GROUP_COUNT).setLabel(text(30135) if len(entries) == 1 else text(30132, len(entries)))
        self.channel_list.reset()
        self.channel_list.addItems(items)
        if entries:
            self.channel_list.selectItem(min(position, len(entries) - 1))
            self.getControl(CHANNELS_EMPTY).setLabel("")
        elif not storage.get_lists():
            self.getControl(CHANNELS_EMPTY).setLabel(text(30048))
        else:
            empty = {CONTINUE_GROUP: 30130, FAVORITES_GROUP: 30066}.get(group, 30046)
            self.getControl(CHANNELS_EMPTY).setLabel(text(empty))
        return True

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
        """Show the highlighted group. Runs on timer threads too, so a group still being built is stopped by
        a newer request instead of replacing the group shown after it."""
        request = self.follow_request = next(self.follow_requests)
        with self.show_lock:
            index = self.group_list.getSelectedPosition()
            if 0 <= index < len(self.groups) and index != self.shown_index:
                self.show_group(index, stale=lambda: self.follow_request != request)

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
            self.watcher.play_channel(episode or entry, start, subtitle_target(episode, entry) if episode else subtitle_target(entry))
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
        if entry.get("folder") and not xbmcvfs.exists(m3u.base_url(channel["url"])):
            xbmcgui.Dialog().ok(TITLE, text(30146, display_name(entry)))
            return None
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
            self.show_entries(self.groups[FAVORITES_GROUP][0], favorites, position, group=FAVORITES_GROUP)
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
        options = [(text(30071 if favorite else 30070), self.toggle_favorite), (remove_label, lambda item: self.remove([item]))]
        if is_local(entry):
            options.append((text(30140), self.choose_info))
            if not entry.get("series"):
                options.append((text(30141), self.rename_file))
            options.append((text(30143 if entry.get("series") else 30142), self.delete_files))
        else:
            options.append((text(30019), self.check_item))
        choice = xbmcgui.Dialog().contextmenu([label for label, _ in options])
        if choice >= 0:
            options[choice][1](entry)

    def check_item(self, entry):
        if entry.get("series"):
            self.check_entries(entry["episodes"])
            return
        busy(True)
        reason = probe.check(entry["channel"]["url"], ADDON.getSettingInt("check_timeout"))
        busy(False)
        notify(text(30033, reason) if reason else text(30032))

    # Files of folders

    def choose_info(self, entry):
        """Search Cinemeta with a title the user can correct, and keep the chosen result."""
        kind, title, year = self.lookup_query(entry)
        query = xbmcgui.Dialog().input(text(30149), title).strip()
        if not query:
            return
        busy(True)
        try:
            candidates = cinemeta.search(kind, query)
        except Exception as error:
            busy(False)
            xbmcgui.Dialog().ok(TITLE, text(30011, error))
            return
        busy(False)
        if not candidates:
            notify(text(30151, query))
            return
        items = []
        for meta in candidates[:25]:
            item = xbmcgui.ListItem(meta.get("name", ""), meta.get("releaseInfo", ""))
            item.setArt({"icon": meta.get("poster", ""), "thumb": meta.get("poster", "")})
            items.append(item)
        items.append(xbmcgui.ListItem(text(30150)))
        choice = xbmcgui.Dialog().select(text(30140), items, useDetails=True)
        if choice < 0:
            return
        if choice == len(items) - 1:
            storage.save_metadata({item_id(entry): {}})
        else:
            busy(True)
            try:
                storage.save_metadata({item_id(entry): cinemeta.details(kind, candidates[choice]["id"])})
            except Exception as error:
                busy(False)
                xbmcgui.Dialog().ok(TITLE, text(30011, error))
                return
            busy(False)
        self.apply_metadata()
        self.build_groups()

    def refresh_list(self, list_id):
        item = storage.get_list(list_id)
        if item:
            try:
                storage.refresh(item)
            except Exception:
                pass
        self.reload()

    def rename_file(self, entry):
        old = m3u.base_url(entry["channel"]["url"])
        folder, name = posixpath.split(old)
        stem, extension = posixpath.splitext(name)
        new_stem = xbmcgui.Dialog().input(text(30153), stem).strip()
        if not new_stem or new_stem == stem or "/" in new_stem:
            return
        _, files = xbmcvfs.listdir(folder + "/")
        moves = [(name, new_stem + extension)]
        moves += [(other, new_stem + other[len(stem):]) for other in folders.sidecars(files, stem)]
        # The hidden "._" file the Mac writes next to each file follows it.
        moves += [("._" + source, "._" + target) for source, target in list(moves) if "._" + source in files]
        for source, target in moves:
            if not xbmcvfs.rename(folder + "/" + source, folder + "/" + target):
                xbmcgui.Dialog().ok(TITLE, text(30152, source))
                break
        else:
            storage.move_item(old, folder + "/" + new_stem + extension)
        self.refresh_list(entry["list"])

    def delete_files(self, entry):
        paths = local_paths(entry)
        name = item_name(entry)
        question = text(30145, len(paths), name) if entry.get("series") else text(30144, name)
        if not xbmcgui.Dialog().yesno(TITLE, question, nolabel=text(30040), yeslabel=text(30142)):
            return
        failed = 0
        listings = {}
        for path in paths:
            folder, file_name = posixpath.split(path)
            if folder not in listings:
                listings[folder] = xbmcvfs.listdir(folder + "/")[1]
            stem = posixpath.splitext(file_name)[0]
            targets = [file_name] + folders.sidecars(listings[folder], stem)
            targets += ["._" + target for target in targets if "._" + target in listings[folder]]
            for target in targets:
                if not xbmcvfs.delete(folder + "/" + target) and target == file_name:
                    failed += 1
        if failed:
            xbmcgui.Dialog().ok(TITLE, text(30154))
        else:
            notify(text(30156) if len(paths) == 1 else text(30157, len(paths)))
        self.refresh_list(entry["list"])

    # Tools

    def open_downloads(self):
        downloads = DownloadsWindow("script-m3u-movies-downloads.xml", PATH, "default", "1080i")
        downloads.doModal()
        del downloads
        # Finished downloads may be in a video folder.
        self.reload()

    def open_catalog(self):
        catalog = CatalogWindow("script-m3u-movies-catalog.xml", PATH, "default", "1080i")
        catalog.main = self
        catalog.doModal()
        del catalog
        # Downloads started in the catalog may be in a video folder.
        self.reload()

    def library_entry(self, kind, meta):
        """The movie or series of the lists that is a catalog title, found by its IMDb id or its name."""
        wanted = cinemeta.normalized(meta["name"])
        if kind == "series":
            return next((show for show in self.shows if (show.get("meta") or {}).get("id") == meta["id"]
                         or cinemeta.normalized(show["name"]) == wanted), None)
        found = next((movie for movie in self.movies if (movie.get("meta") or {}).get("id") == meta["id"]), None)
        if found:
            return found
        for movie in self.movies:
            title, year = folders.title_and_year(movie["channel"]["name"])
            if cinemeta.normalized(title) == wanted and (not year or not meta.get("year") or abs(year - meta["year"]) <= 1):
                return movie
        return None

    def open_manager(self):
        manager = ListManager("script-m3u-movies-manager.xml", PATH, "default", "1080i")
        manager.on_change = self.reload
        manager.show_removed = self.show_removed
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
        meta = self.entry.get("meta") or {}
        self.setProperty("duration", meta_line(meta, duration_text(movie["duration"]) or meta.get("runtime", "")))
        self.setProperty("plot", meta.get("plot", ""))
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
        meta = show.get("meta") or {}
        info = text(30121, len(show["seasons"]), len(show["episodes"]))
        self.setProperty("info", info + ("  ·  " + meta_line(meta) if meta_line(meta) else ""))
        self.setProperty("plot", meta.get("plot", ""))
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


class CatalogWindow(xbmcgui.WindowXML):
    """Movies and series of Cinemeta, the catalog of Stremio: categories on the left and posters on the right.

    Titles of the catalog that are also in the lists can be played from their details. My list keeps the titles
    the user saves.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loaded = False
        self.kind = "movie"
        self.categories = []
        # Loaded pages by kind and category, so returning to a category is instant.
        self.pages = {}
        # The page shown, and its kind and category. The key is None for My list, which is not a Cinemeta page.
        self.page, self.page_key, self.items = None, None, []
        self.shown_index = -1
        self.show_lock = threading.Lock()
        self.requests = itertools.count()
        self.request = 0
        # The last request that failed to load.
        self.failed = -1
        self.follow_timer = None
        self.grid_position = -1

    def onInit(self):
        # Also called when returning from full screen video. Keep the current state then.
        if self.loaded:
            return
        self.loaded = True
        self.tabs = self.getControl(CATALOG_TABS)
        self.group_list = self.getControl(GROUPS)
        self.poster_list = self.getControl(CHANNELS)
        self.tabs.addItems([xbmcgui.ListItem(text(30201)), xbmcgui.ListItem(text(30117))])
        self.show_categories()
        self.setFocusId(GROUPS)

    # Categories

    def show_categories(self):
        """Categories of the kind shown: My list, Search, the catalogs of Cinemeta and the genres."""
        year = str(time.localtime().tm_year)
        genres = [genre for genre in GENRES if self.kind == "series" or genre not in SERIES_ONLY_GENRES]
        self.categories = [(text(30202), ("watchlist", None)), (text(30203), ("search", None)),
                           (text(30204), ("top", None)), (text(30205), ("imdbRating", None)),
                           (text(30206, year), ("year", year))]
        self.manifests = {}
        for addon in storage.get_addons():
            manifest, base = addon["manifest"], stremio.base_url(addon["url"])
            self.manifests[base] = manifest
            for kind in TAB_TYPES[self.kind]:
                for catalog_id, name, pages in stremio.browsable_catalogs(manifest, kind):
                    self.categories.append((name, ("addon", base, kind, catalog_id, pages)))
        self.categories += sorted(((genre_name(genre), ("top", genre)) for genre in genres),
                                  key=lambda category: category[0].casefold())
        self.group_list.reset()
        self.group_list.addItems([xbmcgui.ListItem(name) for name, _ in self.categories])
        self.update_watchlist_count()
        # Popular titles first. Kodi applies selectItem later, so the category is opened by its index.
        self.group_list.selectItem(POPULAR_CATEGORY)
        self.open_category(POPULAR_CATEGORY)

    def update_watchlist_count(self):
        count = len([item for item in storage.get_watchlist() if item["kind"] == self.kind])
        self.group_list.getListItem(0).setLabel2(str(count) if count else "")

    def follow_group(self):
        index = self.group_list.getSelectedPosition()
        if 0 <= index < len(self.categories) and index != self.shown_index:
            if self.categories[index][1][0] == "search":
                # A search starts only when selected, since it asks for a title.
                return
            self.open_category(index)

    def open_category(self, index, query=None):
        name, key = self.categories[index]
        self.shown_index = index
        if key[0] == "search":
            key, name = ("search", query), text(30042, query)
        elif key[0] == "addon":
            # The header names the addon, which the categories leave out to keep them short.
            name = "%s  ·  %s" % (name, self.manifests[key[1]]["name"])
        request = self.request = next(self.requests)
        if key[0] == "watchlist":
            items = [item for item in storage.get_watchlist() if item["kind"] == self.kind]
            self.show(name, {"items": items, "more": False, "skip": 0}, None, request)
            return
        kind = self.kind
        page = self.pages.get((kind, key))
        if page:
            self.show(name, page, (kind, key), request)
            return
        with self.show_lock:
            self.page, self.items = None, []
            self.poster_list.reset()
            self.set_header(name, "")
            self.getControl(CHANNELS_EMPTY).setLabel(text(30207))

        def run():
            try:
                metas = self.fetch(kind, key, 0)
            except Exception as error:
                self.failed = request
                if self.request == request:
                    self.getControl(CHANNELS_EMPTY).setLabel(text(30208, error))
                return
            page = {"items": self.unique(metas, [], key), "more": self.pages_more(key, metas), "skip": len(metas)}
            self.pages[(kind, key)] = page
            self.show(name, page, (kind, key), request)

        threading.Thread(target=run, daemon=True).start()

    def fetch(self, kind, key, skip):
        if key[0] == "search":
            return cinemeta.search(kind, key[1])
        if key[0] == "addon":
            return stremio.catalog(key[1], key[2], key[3], skip)
        return cinemeta.catalog(kind, key[0], key[1], skip)

    def pages_more(self, key, metas):
        """Whether a category may have another page after these titles. Searches and addon catalogs without
        skip have one page."""
        return bool(metas) and key[0] != "search" and (key[0] != "addon" or key[4])

    def unique(self, metas, known, key):
        """Catalog titles not already in known, with the fields kept for them.

        Titles of an addon also keep their type and, when the addon gives details, its address, since their ids
        may not be IMDb ids that Cinemeta knows."""
        seen = {item["id"] for item in known}
        found = []
        for meta in metas:
            item = cinemeta.summary(meta)
            if key[0] == "addon":
                # The id of the addon itself. An IMDb id it also gives may be the one of a whole franchise.
                item["id"] = meta.get("id") or item["id"]
            if not item["id"] or item["id"] in seen:
                continue
            seen.add(item["id"])
            if key[0] == "addon":
                item["type"] = meta.get("type") or key[2]
                if stremio.has_meta(self.manifests.get(key[1], {"resources": []}), item["type"], item["id"]):
                    item["addon"] = key[1]
            found.append(item)
        return found

    # Posters

    def set_header(self, title, count):
        self.getControl(GROUP_TITLE).setLabel(title)
        self.getControl(GROUP_COUNT).setLabel(count)

    def count_text(self):
        return text(30135) if len(self.items) == 1 else text(30132, len(self.items))

    def show(self, title, page, key, request):
        """Show a page of titles, unless a newer category was chosen while it loaded."""
        with self.show_lock:
            if self.request != request:
                return
            self.page, self.page_key, self.items = page, key, page["items"]
            watchlist = {item["id"] for item in storage.get_watchlist()}
            self.poster_list.reset()
            self.poster_list.addItems([self.card(item, watchlist) for item in self.items])
            self.set_header(title, self.count_text() if self.items else "")
            empty = 30210 if key is None else 30209
            self.getControl(CHANNELS_EMPTY).setLabel("" if self.items else text(empty))

    def card(self, item, watchlist):
        card = xbmcgui.ListItem(item["name"])
        if item.get("poster"):
            card.setArt({"icon": item["poster"], "thumb": item["poster"], "poster": item["poster"]})
        parts = [str(item["year"])] if item.get("year") else []
        if item.get("rating"):
            parts.append(text(30155, item["rating"]))
        # One space around the dot, so the rating fits under the poster.
        card.setProperty("duration", " · ".join(parts))
        card.setProperty("favorite", "true" if item["id"] in watchlist else "false")
        return card

    def load_more(self):
        """Load the next page of the catalog shown when the selection nears its end. Runs on a thread."""
        page = self.page
        if not page or not page["more"] or page.get("loading") or \
                self.poster_list.getSelectedPosition() < len(self.items) - LOAD_MORE_BEFORE:
            return
        page["loading"] = True
        kind, key = self.page_key

        def run():
            try:
                metas = self.fetch(kind, key, page["skip"])
            except Exception:
                metas = []
            new = self.unique(metas, page["items"], key)
            with self.show_lock:
                page["skip"] += len(metas)
                page["more"], page["loading"] = bool(new) and self.pages_more(key, metas), False
                page["items"] += new
                if self.page is page and new:
                    watchlist = {item["id"] for item in storage.get_watchlist()}
                    # Kodi selects the first poster when items are added, so the selection is put back.
                    position = self.poster_list.getSelectedPosition()
                    self.poster_list.addItems([self.card(item, watchlist) for item in new])
                    self.poster_list.selectItem(position)
                    self.getControl(GROUP_COUNT).setLabel(self.count_text())

        threading.Thread(target=run, daemon=True).start()

    def selected_item(self):
        position = self.poster_list.getSelectedPosition()
        return self.items[position] if 0 <= position < len(self.items) else None

    def toggle_watchlist(self, item):
        added = storage.toggle_watchlist(self.kind, item)
        notify(text(30216 if added else 30217))
        self.update_watchlist_count()
        if self.page_key is None:
            # My list is shown: show it again without the removed title.
            position = self.poster_list.getSelectedPosition()
            self.open_category(self.shown_index)
            if self.items:
                self.poster_list.selectItem(min(position, len(self.items) - 1))
            else:
                self.setFocusId(GROUPS)
        else:
            # Compared by id, since the details window keeps a copy with the full record.
            ids = [shown["id"] for shown in self.items]
            if item["id"] in ids:
                self.poster_list.getListItem(ids.index(item["id"])).setProperty("favorite", "true" if added else "false")

    # Navigation

    def onAction(self, action):
        action_id = action.getId()
        focus = self.getFocusId()
        if focus == CHANNELS:
            # Left in the first column does not move the selection, so it leads back to the categories.
            previous, self.grid_position = self.grid_position, self.poster_list.getSelectedPosition()
            if action_id == ACTION_LEFT and self.grid_position == previous:
                self.setFocusId(GROUPS)
                return
            self.load_more()
        if action_id in ACTION_BACK:
            if focus == CHANNELS:
                self.setFocusId(GROUPS)
            else:
                self.shutdown()
        elif action_id == ACTION_CONTEXT_MENU and focus == CHANNELS:
            item = self.selected_item()
            if item is not None:
                in_list = item["id"] in {saved["id"] for saved in storage.get_watchlist()}
                if xbmcgui.Dialog().contextmenu([text(30215 if in_list else 30214)]) == 0:
                    self.toggle_watchlist(item)
        elif focus == CATALOG_TABS and action_id in (ACTION_LEFT, ACTION_RIGHT):
            kind = ("movie", "series")[self.tabs.getSelectedPosition()]
            if kind != self.kind:
                self.kind = kind
                self.show_categories()
        elif focus == GROUPS and action_id == ACTION_RIGHT:
            self.follow_now()
            self.focus_posters()
        elif focus == GROUPS:
            if self.follow_timer:
                self.follow_timer.cancel()
            self.follow_timer = threading.Timer(FOLLOW_DELAY, self.follow_group)
            self.follow_timer.start()

    def onFocus(self, control_id):
        # The posters can also be reached from the addons button, which the layout moves to directly.
        if control_id == CHANNELS:
            self.grid_position = self.poster_list.getSelectedPosition()

    def follow_now(self):
        if self.follow_timer:
            self.follow_timer.cancel()
        self.follow_group()

    def focus_posters(self):
        if self.items:
            self.setFocusId(CHANNELS)
            self.grid_position = self.poster_list.getSelectedPosition()

    def onClick(self, control_id):
        if control_id == CATALOG_TABS:
            self.setFocusId(GROUPS)
        elif control_id == CATALOG_ADDONS:
            self.open_addons()
        elif control_id == GROUPS:
            index = self.group_list.getSelectedPosition()
            if self.categories[index][1][0] == "search":
                self.search(index)
            else:
                self.follow_now()
                self.focus_posters()
        elif control_id == CHANNELS:
            item = self.selected_item()
            if item is not None:
                self.open_details(item)

    def search(self, index):
        query = xbmcgui.Dialog().input(text(30211)).strip()
        if not query:
            return
        self.open_category(index, query)
        request, key = self.request, (self.kind, ("search", query))
        # The results load on a thread. Wait for them, so the focus can move to the posters.
        monitor = xbmc.Monitor()
        for _ in range(150):
            if self.page_key == key or self.request != request or self.failed == request:
                break
            monitor.waitForAbort(0.1)
        self.focus_posters()

    def open_addons(self):
        addons = AddonsWindow("script-m3u-movies-addons.xml", PATH, "default", "1080i")
        addons.doModal()
        changed = addons.changed
        del addons
        if changed:
            # Catalogs of removed addons are dropped, and those of new ones are listed.
            self.pages = {key: page for key, page in self.pages.items() if key[1][0] != "addon"}
            self.show_categories()

    def open_details(self, item):
        details = CatalogDetails("script-m3u-movies-catalog-details.xml", PATH, "default", "1080i")
        details.catalog, details.kind, details.item = self, self.kind, item
        details.entry, details.choice = self.main.library_entry(self.kind, item), None
        details.doModal()
        choice, entry, source = details.choice, details.entry, details.source
        del details
        if choice == "watch":
            self.main.open_details(entry)
        elif choice == "play":
            self.play(source)

    def stream_addons(self, kind, item_id):
        """Installed addons that give sources for an item, as (name, address), in the order they were added."""
        return [(addon["manifest"]["name"], stremio.base_url(addon["url"])) for addon in storage.get_addons()
                if stremio.supports(addon["manifest"], "stream", kind, item_id)]

    def open_sources(self, title, kind, item_id, poster):
        """Show the sources of a movie or an episode. Returns the direct link chosen to play, or None."""
        addons = self.stream_addons(kind, item_id)
        if not addons:
            xbmcgui.Dialog().ok(TITLE, text(30310))
            return None
        panel = SourcesPanel("script-m3u-movies-sources.xml", PATH, "default", "1080i")
        panel.catalog, panel.title, panel.kind, panel.item_id, panel.addons = self, title, kind, item_id, addons
        panel.poster, panel.choice = poster, None
        panel.doModal()
        choice = panel.choice
        del panel
        return choice

    def download(self, source):
        """Send a torrent to Downloads. Returns True when it was added."""
        folder = ADDON.getSetting("download_folder") or choose_download_folder()
        if not folder:
            return False
        needed = size_bytes(source["size"])
        while True:
            free = free_space(folder)
            if free is None or free >= max(needed, LOW_SPACE):
                break
            # Too little space: name the folder and what the torrent needs, and offer another folder.
            if not xbmcgui.Dialog().yesno(TITLE, text(30314, folder, size_text(free), source["size"] or "?"),
                                          nolabel=text(30040), yeslabel=text(30163)):
                return False
            chosen = choose_download_folder(folder)
            # Kodi gives back the current folder when the browser is cancelled.
            if not chosen or chosen == folder:
                return False
            folder = chosen
        downloads = engine()
        busy(True)
        try:
            downloads.start(folder, engine_settings())
            info_hash = downloads.add_magnet(source["magnet"], folder)
        except torrents.EngineError as error:
            busy(False)
            xbmcgui.Dialog().ok(TITLE, text(30173, error))
            return False
        busy(False)
        if source.get("file_idx") is not None:
            # A pack of a whole season or collection: only the chosen file is downloaded.
            threading.Thread(target=downloads.only_file, args=(info_hash, source["file_idx"]), daemon=True).start()
        notify(text(30308, source["label"]))
        return True

    def play(self, source):
        url = source["url"]
        if source.get("headers"):
            # Kodi takes the request headers of a stream after a | in its address.
            url += "|" + urlencode(source["headers"])
        item = xbmcgui.ListItem(source["title"])
        item.setArt({"poster": source.get("poster", ""), "thumb": source.get("poster", "")})
        if ".m3u8" in source["url"]:
            item.setMimeType("application/vnd.apple.mpegurl")
            item.setContentLookup(False)
        xbmc.Player().play(url, item)

    def shutdown(self):
        if self.follow_timer:
            self.follow_timer.cancel()
        self.close()


class CatalogDetails(xbmcgui.WindowXMLDialog):
    """Details of a catalog title, with the seasons and episodes of a series. Watch is offered when the title is
    in the lists, and sets choice for the catalog."""

    def onInit(self):
        item = self.item
        self.series = self.kind == "series"
        self.setProperty("series", "true" if self.series else "false")
        self.setProperty("title", item["name"])
        self.setProperty("poster", item.get("poster", ""))
        self.show_info(item)
        self.setProperty("library", text(30222, self.entry["list_name"]) if self.entry else "")
        self.setProperty("playable", "true" if self.entry else "false")
        self.plot = item.get("plot", "")
        self.setProperty("plot", self.plot)
        self.update_watchlist()
        self.source = None
        self.all_episodes, self.episodes, self.seasons, self.season = [], [], [], 0
        # Movies show their sources from a button, series from each episode.
        has_sources = not self.series and bool(self.catalog.stream_addons(self.stream_type(), item["id"]))
        self.setProperty("sources", "true" if has_sources else "false")
        target = CATALOG_SOURCES if has_sources else CATALOG_WATCH if self.entry else CATALOG_MY_LIST
        # The buttons are shown by window properties, which Kodi applies on the next frame. A hidden button
        # cannot take the focus.
        for _ in range(20):
            if xbmc.getCondVisibility("Control.IsVisible(%d)" % target):
                break
            xbmc.sleep(25)
        self.setFocusId(target)
        threading.Thread(target=self.load, daemon=True).start()

    def stream_type(self):
        """The type addons know the title by: the one of its catalog for titles of addons, as anime."""
        return self.item.get("type") or self.kind

    def show_info(self, item):
        self.setProperty("info", meta_line(item, "" if self.series else item.get("runtime", "")))
        people = []
        if item.get("director"):
            people.append(text(30219, ", ".join(item["director"])))
        if item.get("cast"):
            people.append(text(30220, ", ".join(item["cast"])))
        self.setProperty("people", "  ·  ".join(people))

    def load(self):
        """Load the full description and, for a series, the episodes. Search results also lack the year,
        genres and people, which this fills in."""
        item = self.item
        try:
            if item.get("addon"):
                meta = stremio.meta(item["addon"], item.get("type", self.kind), item["id"])
            elif item["id"].startswith("tt"):
                meta = cinemeta.meta(self.kind, item["id"])
            else:
                return
        except Exception:
            return
        full = cinemeta.summary(meta)
        self.item = dict(self.item, **{key: value for key, value in full.items() if value and key != "id"})
        self.show_info(self.item)
        self.plot = full["plot"] or self.plot
        self.setProperty("plot", self.plot)
        if self.series:
            self.show_episodes(cinemeta.episodes(meta))

    def show_episodes(self, found):
        # Specials last.
        seasons = sorted({episode[0] for episode in found}, key=lambda season: (season == 0, season))
        if not seasons:
            return
        self.all_episodes, self.seasons = found, seasons
        info = text(30121, len([season for season in seasons if season]), len(found))
        self.setProperty("info", info + ("  ·  " + meta_line(self.item) if meta_line(self.item) else ""))
        control = self.getControl(SERIES_SEASONS)
        control.reset()
        control.addItems([xbmcgui.ListItem(self.season_name(season)) for season in seasons])
        self.show_season()

    def season_name(self, season):
        # Old cartoons are numbered by year, as in 1940, which is clearer alone.
        if season == 0:
            return text(30218)
        return str(season) if season > 1000 else text(30120, season)

    def show_season(self):
        season = self.seasons[self.season]
        self.episodes = [episode for episode in self.all_episodes if episode[0] == season]
        items = []
        for _, number, title, aired, plot, _ in self.episodes:
            item = xbmcgui.ListItem("E%02d" % number + ("  ·  " + title if title else ""))
            if re.match(r"\d{4}-\d{2}-\d{2}$", aired):
                item.setLabel2("/".join(reversed(aired.split("-"))))
            # Shown below the poster while the episode is highlighted.
            item.setProperty("plot", plot or self.plot)
            items.append(item)
        control = self.getControl(SERIES_EPISODES)
        control.reset()
        control.addItems(items)

    def update_watchlist(self):
        in_list = self.item["id"] in {item["id"] for item in storage.get_watchlist()}
        self.setProperty("favorite", "true" if in_list else "false")
        self.getControl(CATALOG_MY_LIST).setLabel(text(30215 if in_list else 30214))

    def onAction(self, action):
        if action.getId() in ACTION_BACK:
            self.close()
            return
        if self.getFocusId() == SERIES_SEASONS and self.seasons:
            season = self.getControl(SERIES_SEASONS).getSelectedPosition()
            if season != self.season and 0 <= season < len(self.seasons):
                self.season = season
                self.show_season()

    def onClick(self, control_id):
        if control_id == CATALOG_WATCH:
            self.choice = "watch"
            self.close()
        elif control_id == CATALOG_MY_LIST:
            self.catalog.toggle_watchlist(self.item)
            self.update_watchlist()
        elif control_id == CATALOG_SOURCES:
            self.sources(self.item["name"], self.item["id"])
        elif control_id == SERIES_SEASONS:
            self.setFocusId(SERIES_EPISODES)
        elif control_id == SERIES_EPISODES:
            position = self.getControl(SERIES_EPISODES).getSelectedPosition()
            if 0 <= position < len(self.episodes):
                season, number, _, _, _, video_id = self.episodes[position]
                self.sources("%s  ·  %s" % (self.item["name"], text(30133, season, number)), video_id)

    def sources(self, title, item_id):
        """Open the sources panel. A direct link chosen there is played once the details close."""
        source = self.catalog.open_sources(title, self.stream_type(), item_id, self.item.get("poster", ""))
        if source:
            self.choice, self.source = "play", source
            self.close()


class SourcesPanel(xbmcgui.WindowXMLDialog):
    """Sources of a movie or an episode from the installed addons, in a panel that slides in from the right.

    Each addon is asked at the same time, and its sources are listed as they arrive, in the order of the addons.
    A torrent is sent to Downloads, and a direct link is set as choice to be played.
    """

    def onInit(self):
        self.lock = threading.Lock()
        # Until the user moves, the list stays at its top while sources arrive.
        self.moved = False
        self.found = {}
        self.failed = []
        self.sources = []
        self.list_control = self.getControl(SOURCES_LIST)
        self.setProperty("title", self.title)
        self.setProperty("status", text(30301))
        self.getControl(SOURCES_EMPTY).setLabel(text(30301))
        for index, (name, base) in enumerate(self.addons):
            threading.Thread(target=self.ask, args=(index, name, base), daemon=True).start()

    def ask(self, index, name, base):
        try:
            found = [source for source in map(stremio.describe, stremio.streams(base, self.kind, self.item_id)) if source]
        except Exception:
            found = None
        with self.lock:
            if found is None:
                self.failed.append(name)
            else:
                for source in found:
                    source["addon"] = name
                self.found[index] = found
            self.show()

    def show(self):
        """List the sources found so far, keeping the highlighted one."""
        position = self.list_control.getSelectedPosition()
        selected = self.sources[position] if 0 <= position < len(self.sources) else None
        self.sources = [source for index in sorted(self.found) for source in self.found[index]]
        items = []
        for source in self.sources:
            item = xbmcgui.ListItem(source["label"], self.detail(source))
            item.setProperty("kind", source["kind"])
            items.append(item)
        self.list_control.reset()
        self.list_control.addItems(items)
        if self.moved and selected in self.sources:
            self.list_control.selectItem(self.sources.index(selected))
        done = len(self.found) + len(self.failed) == len(self.addons)
        count = text(30303) if len(self.sources) == 1 else text(30302, len(self.sources))
        status = count if done else count + "  ·  " + text(30301)
        if done and self.failed:
            status += "  ·  " + text(30309, ", ".join(self.failed))
        self.setProperty("status", status)
        self.getControl(SOURCES_EMPTY).setLabel("" if self.sources else text(30301) if not done else text(30304))
        if self.sources and self.getFocusId() != SOURCES_LIST:
            self.setFocusId(SOURCES_LIST)

    def detail(self, source):
        parts = [text(30305 if source["kind"] == "torrent" else 30306)]
        parts += [part for part in (source["quality"], " ".join(source["languages"]), source["size"]) if part]
        if source["seeds"] is not None:
            parts.append(text(30307, source["seeds"]))
        parts.append(source["addon"])
        return "  ·  ".join(parts)

    def onAction(self, action):
        # The panel came in from the right, so Left also closes it.
        if action.getId() in ACTION_BACK or action.getId() == ACTION_LEFT:
            self.close()
        elif action.getId() in (ACTION_UP, ACTION_DOWN):
            self.moved = True

    def onClick(self, control_id):
        if control_id != SOURCES_LIST:
            return
        position = self.list_control.getSelectedPosition()
        if not 0 <= position < len(self.sources):
            return
        source = self.sources[position]
        if source["kind"] == "torrent":
            if self.catalog.download(source):
                self.close()
        else:
            self.choice = dict(source, title=self.title, poster=self.poster)
            self.close()


class AddonsWindow(xbmcgui.WindowXMLDialog):
    """Stremio addons: Cinemeta, which is built in, and the addons added by their address. Sets changed when an
    addon was added, updated or removed."""

    def onInit(self):
        self.changed = False
        self.list_control = self.getControl(ADDONS_LIST)
        self.populate()
        self.setFocusId(ADDONS_LIST)

    def populate(self):
        self.addons = storage.get_addons()
        position = self.list_control.getSelectedPosition()
        self.list_control.reset()
        self.list_control.addItem(xbmcgui.ListItem("Cinemeta", text(30278)))
        for addon in self.addons:
            manifest = addon["manifest"]
            item = xbmcgui.ListItem("%s  [COLOR grey]%s[/COLOR]" % (manifest["name"], manifest.get("version", "")),
                                    self.describe(addon))
            if manifest.get("logo"):
                item.setProperty("logo", manifest["logo"])
            self.list_control.addItem(item)
        self.list_control.selectItem(min(max(position, 0), len(self.addons)))

    def describe(self, addon):
        """What an addon gives, for which types, and where it is."""
        manifest = addon["manifest"]
        resources = [text(RESOURCE_NAMES[name]) for name in stremio.resource_names(manifest) if name in RESOURCE_NAMES]
        types = [text(TYPE_NAMES[kind]) if kind in TYPE_NAMES else kind.capitalize() for kind in manifest.get("types") or []]
        parts = [", ".join(resources), ", ".join(types), urlsplit(addon["url"]).hostname or ""]
        return "  ·  ".join(part for part in parts if part)

    def onAction(self, action):
        if action.getId() in ACTION_BACK:
            self.close()

    def onClick(self, control_id):
        if control_id == ADDONS_ADD:
            self.add()
        elif control_id == ADDONS_CLOSE:
            self.close()
        elif control_id == ADDONS_LIST:
            position = self.list_control.getSelectedPosition()
            if position == 0:
                xbmcgui.Dialog().ok(TITLE, text(30283))
            elif 0 < position <= len(self.addons):
                self.addon_menu(self.addons[position - 1])

    def load(self, url):
        """The manifest of an addon, or None after telling why it cannot be used."""
        busy(True)
        try:
            manifest = stremio.load_manifest(url)
        except stremio.AddonError:
            busy(False)
            xbmcgui.Dialog().ok(TITLE, text(30276))
            return None
        except Exception as error:
            busy(False)
            xbmcgui.Dialog().ok(TITLE, text(30275, error))
            return None
        busy(False)
        if stremio.needs_configuration(manifest):
            xbmcgui.Dialog().ok(TITLE, text(30277, manifest["name"], stremio.base_url(url) + "/configure"))
            return None
        return manifest

    def add(self):
        address = xbmcgui.Dialog().input(text(30273), "https://").strip()
        if len(address) < 12:
            return
        url = stremio.manifest_url(address)
        manifest = self.load(url)
        if manifest:
            storage.save_addon(url, manifest)
            notify(text(30274, manifest["name"]))
            self.changed = True
            self.populate()
            self.list_control.selectItem(1 + next(index for index, addon in enumerate(self.addons)
                                                  if addon["manifest"]["id"] == manifest["id"]))
            self.setFocusId(ADDONS_LIST)

    def addon_menu(self, addon):
        choice = xbmcgui.Dialog().contextmenu([text(30279), text(30280)])
        if choice == 0:
            manifest = self.load(addon["url"])
            if manifest:
                storage.save_addon(addon["url"], manifest)
                notify(text(30282))
                self.changed = True
                self.populate()
        elif choice == 1 and xbmcgui.Dialog().yesno(TITLE, text(30281, addon["manifest"]["name"]),
                                                    nolabel=text(30040), yeslabel=text(30280)):
            storage.remove_addon(addon["url"])
            notify(text(30289))
            self.changed = True
            self.populate()


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
            if storage.is_folder(item):
                detail = text(30147) + "  ·  " + detail
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
        elif control_id == MANAGER_REMOVED:
            self.show_removed()
            self.populate()
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


def size_text(size):
    for unit, factor in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if size >= factor:
            return "%.1f %s" % (size / factor, unit)
    return "%d B" % size


def rate_text(rate):
    return size_text(rate) + "/s"


def engine():
    return torrents.Engine(PATH, os.path.join(storage.PROFILE, "torrest"),
                           android=xbmc.getCondVisibility("System.Platform.Android"))


def engine_settings():
    """Torrest settings from the add-on settings."""
    return {"max_upload_rate": max(ADDON.getSettingInt("upload_limit"), 0) * 1024}


def on_sd_card(path):
    """Whether a folder is on the card that holds the system of LibreELEC, which heavy writes wear out."""
    return xbmc.getCondVisibility("System.HasAddon(service.libreelec.settings)") and path.startswith("/storage")


def choose_download_folder(current=""):
    """Ask for the download folder and save it. Returns the folder, or None when none was chosen."""
    folder = xbmcgui.Dialog().browseSingle(3, text(30168), "files", defaultt=current)
    if not folder:
        return None
    folder = folder.rstrip("/\\") or folder
    if on_sd_card(folder) and not xbmcgui.Dialog().yesno(TITLE, text(30187)):
        return None
    ADDON.setSetting("download_folder", folder)
    return folder


def size_bytes(size):
    """Bytes of a size written as an addon writes it, as in "8.69 GB", or 0 when it cannot be read."""
    match = re.match(r"([\d.,]+)\s*([KMGT])i?B", size or "", re.IGNORECASE)
    if not match:
        return 0
    return int(float(match.group(1).replace(",", ".")) * 1024 ** " KMGT".index(match.group(2).upper()))


def free_space(folder):
    """Free bytes in a local folder, or None for a network folder, whose space Kodi cannot tell."""
    try:
        stats = os.statvfs(folder)
    except (OSError, AttributeError):
        return None
    return stats.f_bavail * stats.f_frsize


def download_status(torrent, free=None):
    """Detail line, progress and state of a download for the list.

    The engine pauses a download when the folder is full, which is shown as no space left instead of paused."""
    status = torrent.get("status") or {}
    state = torrents.state_of(status)
    total = status.get("total_wanted") or torrent.get("size", 0)
    left_bytes = total - status.get("total_wanted_done", 0)
    full = state == "paused" and free is not None and free < min(left_bytes, LOW_SPACE)
    parts = [text(30312) if full else text({"metadata": 30179, "checking": 30180, "paused": 30181, "finished": 30182,
                                             "downloading": 30183}[state])]
    if state == "downloading":
        parts.append(rate_text(status.get("download_rate", 0)))
        parts.append(text(30184, status.get("peers", 0)))
    if total:
        done = status.get("total_wanted_done", 0)
        parts.append(size_text(total) if state == "finished" else text(30185, size_text(done), size_text(total)))
    left = torrents.remaining_seconds(status) if state == "downloading" else 0
    if left >= 60:
        parts.append(text(30186, duration_text(left)))
    return "  ·  ".join(parts), int(status.get("progress", 0)), state


class DownloadsWindow(xbmcgui.WindowXMLDialog):
    """Torrent downloads: add a magnet link or a .torrent file, choose the folder, and follow the list."""

    def onInit(self):
        self.closed = False
        self.hashes = []
        self.list_control = self.getControl(DOWNLOADS_LIST)
        self.engine = engine()
        self.folder = ADDON.getSetting("download_folder")
        if not self.folder and not self.choose_folder():
            self.close()
            return
        self.show_folder()
        busy(True)
        try:
            self.engine.start(self.folder, engine_settings())
        except torrents.EngineError as error:
            busy(False)
            xbmcgui.Dialog().ok(TITLE, text(30172, error))
            self.close()
            return
        busy(False)
        self.update()
        self.setFocusId(DOWNLOADS_LIST if self.hashes else DOWNLOADS_MAGNET)
        threading.Thread(target=self.follow, daemon=True).start()

    def show_folder(self, free=None):
        folder = text(30165, self.folder)
        self.setProperty("folder", folder + ("  ·  " + text(30313, size_text(free)) if free is not None else ""))

    def follow(self):
        monitor = xbmc.Monitor()
        while not self.closed and not monitor.waitForAbort(DOWNLOADS_REFRESH):
            if not self.closed:
                self.update()

    def update(self):
        """Show the downloads. Rows are updated in place, so the selection stays while they change."""
        try:
            items = self.engine.torrents()
        except torrents.EngineError:
            return
        hashes = [torrent["info_hash"] for torrent in items]
        if hashes != self.hashes:
            position = self.list_control.getSelectedPosition()
            self.list_control.reset()
            self.list_control.addItems([xbmcgui.ListItem() for _ in items])
            if items:
                self.list_control.selectItem(min(max(position, 0), len(items) - 1))
            self.hashes = hashes
            if not items and self.getFocusId() == DOWNLOADS_LIST:
                self.setFocusId(DOWNLOADS_MAGNET)
        down = up = 0
        free = free_space(self.folder)
        self.show_folder(free)
        for number, torrent in enumerate(items):
            detail, progress, state = download_status(torrent, free)
            row = self.list_control.getListItem(number)
            row.setLabel(torrent.get("name") or torrent["info_hash"])
            row.setLabel2(detail)
            row.setProperty("progress", str(progress))
            row.setProperty("percent", "%d%%" % progress)
            row.setProperty("state", state)
            # Torrest takes a few seconds to report no speed for a paused torrent.
            if state != "paused":
                down += (torrent.get("status") or {}).get("download_rate", 0)
                up += (torrent.get("status") or {}).get("upload_rate", 0)
        self.setProperty("summary", text(30193, rate_text(down), rate_text(up)) if items else "")
        self.getControl(DOWNLOADS_EMPTY).setLabel("" if items else text(30169))

    def onAction(self, action):
        if action.getId() in ACTION_BACK:
            self.closed = True
            self.close()
        elif action.getId() == ACTION_CONTEXT_MENU and self.getFocusId() == DOWNLOADS_LIST:
            self.download_menu()

    def onClick(self, control_id):
        if control_id == DOWNLOADS_MAGNET:
            self.add_link()
        elif control_id == DOWNLOADS_FILE:
            self.add_file()
        elif control_id == DOWNLOADS_FOLDER:
            if self.choose_folder():
                self.show_folder()
        elif control_id == DOWNLOADS_CLOSE:
            self.closed = True
            self.close()
        elif control_id == DOWNLOADS_LIST:
            self.download_menu()

    def choose_folder(self):
        """Ask for the download folder and save it. Returns True when a folder was chosen."""
        folder = choose_download_folder(self.folder or "")
        if folder:
            self.folder = folder
        return bool(folder)

    def add(self, adder, source):
        busy(True)
        try:
            adder(source, self.folder)
        except torrents.EngineError as error:
            busy(False)
            xbmcgui.Dialog().ok(TITLE, text(30173, error))
            return
        busy(False)
        notify(text(30171))
        self.update()
        self.setFocusId(DOWNLOADS_LIST)

    def add_link(self):
        link = xbmcgui.Dialog().input(text(30166)).strip()
        if not link:
            return
        if link.lower().startswith("magnet:"):
            self.add(self.engine.add_magnet, link)
        elif link.lower().startswith(("http://", "https://")):
            try:
                data = storage.download_bytes(link)
            except Exception as error:
                xbmcgui.Dialog().ok(TITLE, text(30173, error))
                return
            self.add(self.engine.add_torrent_file, data)
        else:
            xbmcgui.Dialog().ok(TITLE, text(30170))

    def add_file(self):
        path = xbmcgui.Dialog().browseSingle(1, text(30167), "files", ".torrent")
        if not path:
            return
        source = xbmcvfs.File(path)
        try:
            data = bytes(source.readBytes())
        finally:
            source.close()
        self.add(self.engine.add_torrent_file, data)

    def download_menu(self):
        position = self.list_control.getSelectedPosition()
        if not 0 <= position < len(self.hashes):
            return
        info_hash = self.hashes[position]
        row = self.list_control.getListItem(position)
        paused = row.getProperty("state") == "paused"
        choice = xbmcgui.Dialog().contextmenu([text(30175 if paused else 30174), text(30176), text(30177)])
        try:
            if choice == 0:
                (self.engine.resume if paused else self.engine.pause)(info_hash)
            elif choice == 1:
                self.engine.remove(info_hash, False)
            elif choice == 2 and xbmcgui.Dialog().yesno(TITLE, text(30178, row.getLabel()), nolabel=text(30040),
                                                       yeslabel=text(30142)):
                self.engine.remove(info_hash, True)
        except torrents.EngineError as error:
            xbmcgui.Dialog().ok(TITLE, text(30173, error))
        self.update()


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
