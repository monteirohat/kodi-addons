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

from resources.lib import cinemeta, direct, folders, github, m3u, movies_menu, probe, series, storage, stremio, torrents
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
CATALOG_WATCH, CATALOG_MY_LIST, CATALOG_SOURCES = 201, 202, 203
SOURCES_LIST, SOURCES_EMPTY = 100, 300
# Direct links waiting for the background service, which downloads them. See direct.py.
DIRECT_JOBS = os.path.join(storage.PROFILE, "direct")
ADDONS_LIST, ADDONS_ADD, ADDONS_CLOSE = 100, 201, 203
# Types of the addon catalogs that are shown.
CATALOG_TYPES = ("movie", "series", "anime")
RESOURCE_NAMES = {"catalog": 30284, "meta": 30287, "stream": 30285, "subtitles": 30286}
TYPE_NAMES = {"movie": 30201, "series": 30117, "channel": 30288}
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
    ("search.png", 30002, "search"),
    ("check.png", 30016, "check_group"),
    ("puzzle.png", 30270, "open_addons"),
    ("gear.png", 30061, "open_manager"),
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


def is_title(item):
    """Whether an item is a title of the catalog, which has no list, and not an entry of the lists."""
    return "list" not in item


def favorite_key(item):
    return item["id"] if is_title(item) else item_id(item)


def type_name(kind):
    return text(TYPE_NAMES[kind]) if kind in TYPE_NAMES else kind.capitalize()


def item_name(item):
    return item["name"] if item.get("series") else item["channel"]["name"]


def item_aliases(item):
    """Other identities of a series joined from several, which its favorites may have been saved under."""
    return ["series:" + key for key in item.get("aliases", [])]


def is_favorite(item, favorites):
    return any(key in favorites for key in [item_id(item), *item_aliases(item)])


def merge_series(shows):
    """Join the series of the lists that are one title of the catalog, by their Cinemeta id, as a series downloaded
    from two addons that name it differently. The one with the most episodes keeps its name and poster, and the keys
    of the others stay as its aliases."""
    by_id, merged = {}, []
    for show in shows:
        meta_id = (show.get("meta") or {}).get("id")
        if not meta_id:
            merged.append(show)
        elif meta_id not in by_id:
            by_id[meta_id] = [show]
            merged.append(by_id[meta_id])
        else:
            by_id[meta_id].append(show)
    for index, members in enumerate(merged):
        if not isinstance(members, list):
            continue
        if len(members) == 1:
            merged[index] = members[0]
            continue
        members.sort(key=lambda show: -len(show["episodes"]))
        show = dict(members[0])
        show["episodes"] = sorted((entry for member in members for entry in member["episodes"]),
                                  key=lambda entry: (entry["episode"]["season"], entry["episode"]["number"]))
        show["seasons"] = sorted({entry["episode"]["season"] for entry in show["episodes"]})
        show["groups"] = list(dict.fromkeys(group for member in members for group in member["groups"]))
        show["aliases"] = [key for member in members[1:] for key in [member["key"], *member.get("aliases", [])]]
        merged[index] = show
    return merged


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


def season_name(season):
    # Old cartoons are numbered by year, as in 1940, which is clearer alone.
    if season == 0:
        return text(30218)
    return str(season) if season > 1000 else text(30120, season)


def downloaded_text(episodes, downloaded):
    """What is on the device, for a movie, with episodes None, or for a series. Empty when nothing is."""
    if not downloaded:
        return ""
    if episodes is None:
        return text(30370)
    return text(30372) if episodes == 1 else text(30371, episodes)


def show_downloaded(window, downloaded, line, name="library"):
    """Set the line of a details window that names where a title is. With what is downloaded, it moves to the
    property downloaded, which the window shows in green after a check."""
    window.setProperty("downloaded", "  ·  ".join(part for part in (downloaded, line) if part) if downloaded else "")
    window.setProperty(name, "" if downloaded else line)


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
    """The toolbar and the groups on the left, posters on the right.

    The first groups hold the movies and series of the lists and folders. After them come the catalogs of Cinemeta
    and of the addons, which load page by page, and the genres of Cinemeta, with movies and series together. Favorites
    and the results of a search hold both: entries of the lists and titles of the catalog. Titles of the catalog that
    are also in the lists can be played from their details.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loaded = False
        self.all_entries = []
        # Each group has its name and either its members, for the lists, or the sources of a catalog.
        self.groups = []
        # The posters shown: entries of the lists and titles of the catalog.
        self.items = []
        self.shown_index = -1
        self.shown_name = None
        # What the posters show: ("group", name) for a group of the lists, or the sources of a catalog.
        self.shown_key = None
        # Loaded pages of the catalogs by their sources, so returning to a catalog is instant. page is the one shown.
        self.pages, self.page = {}, None
        self.manifests = {}
        self.follow_timer = None
        # A group is built by one call at a time. A newer request stops an older one, see follow_group.
        self.show_lock = threading.Lock()
        self.requests = itertools.count()
        self.request = 0
        self.grid_position = -1
        self.start_group = None
        self.movies, self.shows, self.catalog, self.progress = [], [], [], {}
        self.watcher = Watcher(self.on_failure, self.on_progress, self.next_after, self.play_next)

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
        self.shows = merge_series(self.shows)
        self.catalog = self.movies + self.shows

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
        origins = storage.get_origins()

        def origin_of(item):
            return next((origins[path] for path in local_paths(item) if origins.get(path, {}).get("id")), None)

        def missing(item):
            """Whether an item has no details yet. One that had no match is looked up again once its videos are
            known to be of a title of the catalog, as a torrent whose files arrive after the folder was read."""
            details = known.get(item_id(item))
            if details is None:
                return True
            origin = None if details.get("id") else origin_of(item)
            return bool(origin) and details.get("tried") != origin["id"]

        pending = [item for item in self.catalog if is_local(item) and missing(item)]
        if not pending or getattr(self, "lookup_running", False):
            return
        self.lookup_running = True

        def lookup(item):
            try:
                # A video downloaded from Cinemeta has the details of its title, without a search by its name. One
                # downloaded from an addon, whose ids Cinemeta does not know, is searched by the name of its title.
                # Without a match, the id of the title is kept as tried, so it is not looked up every time.
                origin = origin_of(item)
                if origin and origin["id"].startswith("tt"):
                    return item_id(item), cinemeta.details(origin["kind"], origin["id"]) or {"tried": origin["id"]}
                if origin and origin.get("name"):
                    year = origin.get("year") or self.addon_year(origin)
                    return item_id(item), cinemeta.lookup(origin["kind"], origin["name"], year) or {"tried": origin["id"]}
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

    def addon_year(self, origin):
        """The year of a title of an addon, from its details, for the downloads whose catalog page had none. 0 when
        no addon gives it."""
        base = next((base for base, manifest in self.manifests.items()
                     if stremio.has_meta(manifest, origin["kind"], origin["id"])), None)
        if not base:
            return 0
        meta = stremio.meta(base, origin["kind"], origin["id"])
        return cinemeta.first_year(meta.get("releaseInfo") or meta.get("year")) or 0

    def build_groups(self, position=None):
        """Rebuild the groups from the loaded lists, for example after playback changed the progress."""
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
        lists = [(text(30116), self.continue_items()), (text(30065), self.favorite_entries()),
                 (text(30003), self.movies), (text(30361), self.shows)]
        lists += [(name, members) for name, members in groups.items() if name]
        if "" in groups:
            lists.append((text(30043), groups[""]))
        self.groups = [{"name": name, "members": members} for name, members in lists] + self.catalog_groups()
        self.group_list.reset()
        self.group_list.addItems([xbmcgui.ListItem(group["name"], "" if group.get("sources") else str(len(group["members"])))
                                  for group in self.groups])
        names = [group["name"] for group in self.groups]
        if self.shown_name in names:
            index = names.index(self.shown_name)
        elif self.start_group == "series":
            index = SERIES_GROUP
        else:
            # What is in progress, the favorites or the movies of the lists, else the popular movies of the catalog.
            index = next((index for index in (CONTINUE_GROUP, FAVORITES_GROUP, MOVIES_GROUP) if self.groups[index]["members"]),
                         len(lists))
        self.group_list.selectItem(index)
        with self.show_lock:
            self.show_group(index, max(position, 0))

    def catalog_groups(self):
        """The catalogs of Cinemeta, those of the addons, in the order of each addon, and the genres of Cinemeta."""
        year = str(time.localtime().tm_year)
        groups = []
        for string_id, key in ((30362, ("top", None)), (30364, ("imdbRating", None)), (30366, ("year", year))):
            groups += [{"name": text(string_id, year), "sources": [("movie", key)]},
                       {"name": text(string_id + 1, year), "sources": [("series", key)]}]
        self.manifests = {}
        for addon in storage.get_addons():
            manifest, base = addon["manifest"], stremio.base_url(addon["url"])
            self.manifests[base] = manifest
            order = {(catalog.get("type"), catalog.get("id")): index for index, catalog in enumerate(manifest.get("catalogs") or [])}
            found = sorted((order.get((kind, catalog_id), 0), kind, catalog_id, name, pages, named)
                           for kind in CATALOG_TYPES
                           for catalog_id, name, named, pages in stremio.browsable_catalogs(manifest, kind))
            names = [name for _, _, _, name, _, _ in found]
            for _, kind, catalog_id, name, pages, named in found:
                # Catalogs of movies and series often share a name, as Netflix, so their type tells them apart.
                if names.count(name) > 1:
                    name = "%s  ·  %s" % (name, type_name(kind))
                # The header names the addon when the group does not, to keep the groups short.
                groups.append({"name": name, "header": name if named else "%s  ·  %s" % (name, manifest["name"]),
                               "sources": [(kind, ("addon", base, kind, catalog_id, pages))]})
        for genre in sorted(GENRES, key=lambda genre: genre_name(genre).casefold()):
            kinds = ("series",) if genre in SERIES_ONLY_GENRES else ("movie", "series")
            groups.append({"name": genre_name(genre), "sources": [(kind, ("top", genre)) for kind in kinds]})
        return groups

    def favorite_entries(self):
        """Favorites of the lists, then the titles saved from the catalog, newest first.

        A title of the catalog that is also in the lists becomes a favorite of the lists, so it shows once, and plays
        with its progress."""
        titles = []
        for title in storage.get_watchlist():
            entry = self.library_entry(title["kind"], title)
            if entry is None:
                titles.append(title)
                continue
            storage.toggle_watchlist(title["kind"], title)
            if not is_favorite(entry, storage.get_favorites()):
                storage.toggle_favorite(item_id(entry))
        by_id = {}
        for item in self.catalog:
            for key in [item_id(item), *item_aliases(item)]:
                by_id[key] = item
        found = []
        for favorite in storage.get_favorites():
            if favorite in by_id and not any(item is by_id[favorite] for item in found):
                found.append(by_id[favorite])
        return found + titles

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
        group = self.groups[index]
        if group.get("sources"):
            self.shown_index, self.shown_name = index, group["name"]
            self.open_category(group.get("header", group["name"]), group["sources"], position=position)
            return
        if not storage.get_lists() and index in (MOVIES_GROUP, SERIES_GROUP):
            empty = 30048
        else:
            empty = {CONTINUE_GROUP: 30130, FAVORITES_GROUP: 30066}.get(index, 30046)
        if self.show_items(group["name"], group["members"], position, stale, text(empty)):
            self.shown_index, self.shown_name = index, group["name"]
            self.shown_key, self.page = ("group", group["name"]), None

    def show_items(self, title, items, position=0, stale=None, empty=""):
        """Show posters. Returns False when stale() stopped it before anything changed. empty is the message shown
        when there are none."""
        favorites = set(storage.get_favorites())
        watchlist = {item["id"] for item in storage.get_watchlist()}
        cards = []
        for number, item in enumerate(items, 1):
            # Building thousands of cards takes a while, so a newer group can stop it.
            if stale and number % 200 == 0 and stale():
                return False
            cards.append(self.card(item, favorites, watchlist))
        if stale and stale():
            return False
        self.items = items
        self.getControl(GROUP_TITLE).setLabel(title)
        # Name the group on the check tool, so it is clear which movies it will test.
        check_tool = [method for _, _, method in TOOLS].index("check_group")
        self.toolbar.getListItem(check_tool).setLabel(text(30095, title))
        self.update_count()
        self.channel_list.reset()
        self.channel_list.addItems(cards)
        if items:
            self.channel_list.selectItem(min(position, len(items) - 1))
        self.getControl(CHANNELS_EMPTY).setLabel("" if items else empty)
        return True

    def update_count(self):
        count = len(self.items)
        self.getControl(GROUP_COUNT).setLabel("" if not count else text(30135) if count == 1 else text(30132, count))

    def card(self, item, favorites, watchlist):
        """Poster of a movie or a series, with its detail line and badges."""
        if is_title(item):
            return self.title_card(item, watchlist)
        card = xbmcgui.ListItem(item_name(item), item["list_name"])
        logo = item["logo"] if item.get("series") else item["channel"]["logo"]
        if logo:
            card.setArt({"icon": logo, "thumb": logo, "poster": logo})
        if item.get("series"):
            episode, started = next_episode(item, self.progress)
            count = len(item["episodes"])
            detail = episode_code(episode) if started else (text(30134) if count == 1 else text(30127, count))
            watched = all(self.progress.get(each["channel"]["id"], {}).get("watched") for each in item["episodes"])
        else:
            state = self.progress.get(item["channel"]["id"], {})
            detail = text(30126, time_text(state["position"])) if resumable(state) else duration_text(item["channel"]["duration"])
            watched = state.get("watched", False)
        card.setProperty("duration", detail)
        card.setProperty("favorite", "true" if is_favorite(item, favorites) else "false")
        card.setProperty("watched", "true" if watched else "false")
        return card

    def title_card(self, item, watchlist):
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

    def selected_item(self):
        position = self.channel_list.getSelectedPosition()
        return self.items[position] if 0 <= position < len(self.items) else None

    # Catalogs

    def open_category(self, title, sources, prefix=(), position=0):
        """Show a catalog: at once when its first page is loaded, otherwise once it loads on a thread. sources are
        the (kind, key) its titles come from, and prefix are entries of the lists shown before them, as in a search."""
        key = tuple(sources)
        self.shown_key = key
        page = self.pages.get(key)
        if page and not page["loading"]:
            self.page = page
            self.show_items(title, page["items"], position, empty=text(30209))
            return
        self.page = None
        self.show_items(title, list(prefix), empty=text(30207))
        if page:
            # Its first page is still loading, and shows when it arrives.
            return
        page = self.pages[key] = {"items": list(prefix), "skips": [0] * len(sources), "more": [True] * len(sources),
                                  "loading": True}

        def run():
            try:
                found = self.fetch_next(sources, page)
            except Exception as error:
                del self.pages[key]
                if self.shown_key == key:
                    self.getControl(CHANNELS_EMPTY).setLabel(text(30208, error))
                return
            with self.show_lock:
                page["items"] += found
                page["loading"] = False
                if self.shown_key == key:
                    self.page = page
                    selected = self.channel_list.getSelectedPosition() if prefix else 0
                    self.show_items(title, page["items"], max(selected, 0), empty=text(30209))

        threading.Thread(target=run, daemon=True).start()

    def fetch_next(self, sources, page):
        """The next titles of a catalog: the next page of each of its sources that has more, taken in turns. Raises
        the error of the first source when none could be loaded."""
        wanted = [index for index, more in enumerate(page["more"]) if more]

        def get(index):
            kind, key = sources[index]
            try:
                return self.fetch(kind, key, page["skips"][index]), None
            except Exception as error:
                return [], error

        if not wanted:
            return []
        with ThreadPoolExecutor(max_workers=len(wanted)) as executor:
            results = list(executor.map(get, wanted))
        if all(error for _, error in results):
            raise results[0][1]
        known = {item["id"] for item in page["items"] if is_title(item)}
        found = []
        for index, (metas, error) in zip(wanted, results):
            kind, key = sources[index]
            new = self.unique(metas, known, kind, key)
            page["skips"][index] += len(metas)
            page["more"][index] = not error and bool(new) and self.pages_more(key, metas)
            found.append(new)
        return [item for row in itertools.zip_longest(*found) for item in row if item]

    def fetch(self, kind, key, skip):
        if key[0] == "search":
            return cinemeta.search(kind, key[1])
        if key[0] == "addon":
            return stremio.catalog(key[1], key[2], key[3], skip)
        return cinemeta.catalog(kind, key[0], key[1], skip)

    def pages_more(self, key, metas):
        """Whether a catalog may have another page after these titles. Searches and addon catalogs without skip have
        one page."""
        return bool(metas) and key[0] != "search" and (key[0] != "addon" or key[4])

    def unique(self, metas, known, kind, key):
        """Catalog titles whose id is not in known, which they are added to, with the fields kept for them and their
        kind, movie or series.

        Titles of an addon also keep their type and, when the addon gives details, its address, since their ids
        may not be IMDb ids that Cinemeta knows."""
        found = []
        for meta in metas:
            item = cinemeta.summary(meta)
            if key[0] == "addon":
                # The id of the addon itself. An IMDb id it also gives may be the one of a whole franchise.
                item["id"] = meta.get("id") or item["id"]
            if not item["id"] or item["id"] in known:
                continue
            known.add(item["id"])
            # Anime catalogs list mostly series.
            item["kind"] = "movie" if kind == "movie" else "series"
            if key[0] == "addon":
                item["type"] = meta.get("type") or kind
                if stremio.has_meta(self.manifests.get(key[1], {"resources": []}), item["type"], item["id"]):
                    item["addon"] = key[1]
            found.append(item)
        return found

    def load_more(self):
        """Load the next page of the catalog shown when the selection nears its end. Runs on a thread."""
        page = self.page
        if not page or not any(page["more"]) or page.get("more_loading") or \
                self.channel_list.getSelectedPosition() < len(self.items) - LOAD_MORE_BEFORE:
            return
        page["more_loading"] = True
        sources = self.shown_key

        def run():
            try:
                new = self.fetch_next(sources, page)
            except Exception:
                new = []
                page["more"] = [False] * len(sources)
            with self.show_lock:
                page["items"] += new
                page["more_loading"] = False
                if self.page is page and new:
                    favorites = set(storage.get_favorites())
                    watchlist = {item["id"] for item in storage.get_watchlist()}
                    # Kodi selects the first poster when items are added, so the selection is put back.
                    position = self.channel_list.getSelectedPosition()
                    self.channel_list.addItems([self.card(item, favorites, watchlist) for item in new])
                    self.channel_list.selectItem(position)
                    self.update_count()

        threading.Thread(target=run, daemon=True).start()

    # Navigation

    def focus_channels(self):
        if self.items:
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
            self.load_more()
        if action_id in ACTION_BACK:
            if focus == CHANNELS:
                self.setFocusId(GROUPS)
            else:
                self.shutdown()
        elif action_id == ACTION_CONTEXT_MENU and focus == CHANNELS:
            self.channel_menu()
        elif focus == GROUPS and action_id == ACTION_LEFT:
            # Reach the toolbar without scrolling through the groups above, which would change the group.
            self.follow_now()
            self.setFocusId(TOOLBAR)
        elif focus == GROUPS and action_id == ACTION_RIGHT:
            self.follow_now()
            self.focus_channels()
        elif focus == GROUPS:
            if self.follow_timer:
                self.follow_timer.cancel()
            self.follow_timer = threading.Timer(FOLLOW_DELAY, self.follow_group)
            self.follow_timer.start()

    def follow_now(self):
        if self.follow_timer:
            self.follow_timer.cancel()
        self.follow_group()

    def follow_group(self):
        """Show the highlighted group. Runs on timer threads too, so a group still being built is stopped by
        a newer request instead of replacing the group shown after it."""
        request = self.request = next(self.requests)
        with self.show_lock:
            index = self.group_list.getSelectedPosition()
            if 0 <= index < len(self.groups) and index != self.shown_index:
                self.show_group(index, stale=lambda: self.request != request)

    def onClick(self, control_id):
        if control_id == TOOLBAR:
            getattr(self, TOOLS[self.toolbar.getSelectedPosition()][2])()
        elif control_id == GROUPS:
            self.follow_now()
            self.focus_channels()
        elif control_id == CHANNELS:
            item = self.selected_item()
            if item is None:
                pass
            elif is_title(item):
                self.open_title(item)
            else:
                self.open_details(item)

    def open_details(self, entry):
        if entry.get("series"):
            details = SeriesDetails("script-m3u-movies-series.xml", PATH, "default", "1080i")
        else:
            details = MovieDetails("script-m3u-movies-details.xml", PATH, "default", "1080i")
        details.window, details.entry, details.choice, details.episode, details.start = self, entry, None, None, 0
        details.doModal()
        choice, episode, start, source = details.choice, details.episode, details.start, getattr(details, "source", None)
        del details
        if choice == "play":
            self.watcher.play_channel(episode or entry, start, subtitle_target(episode, entry) if episode else subtitle_target(entry))
        elif choice == "direct":
            self.play(source)
        elif choice == "remove":
            self.remove([entry])

    def open_title(self, item):
        """The details of a title of the catalog. Watch opens the details of the same title in the lists."""
        details = CatalogDetails("script-m3u-movies-catalog-details.xml", PATH, "default", "1080i")
        details.catalog, details.kind, details.item = self, item["kind"], item
        details.entry, details.choice = self.library_entry(item["kind"], item), None
        details.doModal()
        choice, entry, source = details.choice, details.entry, details.source
        del details
        if choice == "watch":
            self.open_details(entry)
        elif choice == "play":
            self.play(source)

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

    def show_of(self, episode):
        """The series of the lists an episode is part of, or None."""
        channel_id = episode["channel"]["id"]
        return next((show for show in self.shows if any(entry["channel"]["id"] == channel_id for entry in show["episodes"])), None)

    def next_after(self, episode):
        """The episode of the lists after one, offered near its end, or None after the last one. Episodes of the
        catalog that are not in the lists are skipped, since they play from their sources."""
        show = self.show_of(episode)
        if show is None:
            return None
        current = (episode["episode"]["season"], episode["episode"]["number"])
        return next((entry for entry in show["episodes"] if (entry["episode"]["season"], entry["episode"]["number"]) > current), None)

    def play_next(self, episode):
        """Play the next episode from the controls, where it stopped when it was started before."""
        state = storage.get_progress().get(episode["channel"]["id"])
        start = state["position"] if resumable(state) else 0
        self.watcher.play_channel(episode, start, subtitle_target(episode, self.show_of(episode)))

    def on_failure(self, entry):
        """Called by the watcher when a channel did not play."""
        if not ADDON.getSettingBool("offer_remove"):
            return
        # A video file of a folder that stops early is usually cut short, as by a copy or a download that stopped.
        message = text(30374 if is_local(entry) else 30021, display_name(entry))
        answer = xbmcgui.Dialog().yesnocustom(TITLE, message, customlabel=text(30024), nolabel=text(30023), yeslabel=text(30022))
        if answer == 1:
            self.remove([entry])
        elif answer == 2:
            self.watcher.play_channel(entry)

    def toggle_favorite(self, item):
        """Add an entry of the lists or a title of the catalog to Favorites, or remove it. A title that is also in
        the lists is a favorite of the lists."""
        entry = self.library_entry(item["kind"], item) if is_title(item) else item
        if entry is None:
            added = storage.toggle_watchlist(item["kind"], item)
        else:
            added = storage.toggle_favorite(item_id(entry), item_aliases(entry))
        notify(text(30068 if added else 30069))
        group = self.groups[FAVORITES_GROUP]
        group["members"] = self.favorite_entries()
        self.group_list.getListItem(FAVORITES_GROUP).setLabel2(str(len(group["members"])))
        if self.shown_index == FAVORITES_GROUP:
            position = self.channel_list.getSelectedPosition()
            self.show_group(FAVORITES_GROUP, max(position, 0))
            if not group["members"]:
                self.setFocusId(GROUPS)
            return
        # Compared by identity, since the details window of a title keeps a copy with the full record.
        wanted = favorite_key(item)
        for position, shown in enumerate(self.items):
            if favorite_key(shown) == wanted:
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
        entry = self.selected_item()
        if entry is None:
            return
        if is_title(entry):
            library = self.library_entry(entry["kind"], entry)
            if library:
                in_list = is_favorite(library, storage.get_favorites())
            else:
                in_list = entry["id"] in {saved["id"] for saved in storage.get_watchlist()}
            if xbmcgui.Dialog().contextmenu([text(30071 if in_list else 30070)]) == 0:
                self.toggle_favorite(entry)
            return
        favorite = is_favorite(entry, storage.get_favorites())
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

    def downloaded(self, kind, item, entry):
        """What of a catalog title is on the device: whether a movie is, or the (season, episode) of the episodes
        of a series. entry is the title in the lists, whose videos are on the device when it is in a folder. The
        downloads made from the catalog are also found by their title, in whichever folder they are."""
        found = bool(entry) and is_local(entry)
        episodes = set()
        if found and kind == "series":
            episodes = {(each["episode"]["season"], each["episode"]["number"]) for each in entry["episodes"]}
        for path, origin in storage.get_origins().items():
            if origin.get("id") != item["id"] or not xbmcvfs.exists(path):
                continue
            found = True
            if kind != "series":
                continue
            if origin.get("episode"):
                episodes.add((origin["season"], origin["episode"]))
                continue
            # A season downloaded at once keeps only the series, and each episode is named by its file.
            parsed = series.parse_episode({"name": os.path.splitext(os.path.basename(path))[0],
                                           "subgroup": origin.get("name", "")})
            if parsed:
                episodes.add((parsed[1], parsed[2]))
        return episodes if kind == "series" else found

    def catalog_series(self, show):
        """The title of the catalog a series of the lists is: {"id", "name", "poster", "year", "kind"} and "addon",
        the address of the addon that gives its episodes, or None for Cinemeta. None when the catalog does not know
        it. A download from the catalog keeps its title, and the Cinemeta details of a folder name the others."""
        origins = storage.get_origins()
        origin = next((origins[path] for path in local_paths(show) if origins.get(path, {}).get("id")), None)
        meta = show.get("meta") or {}
        title = {"kind": "series", "id": (origin or meta).get("id") or "", "name": (origin or {}).get("name") or show["name"],
                 "poster": (origin or {}).get("poster") or meta.get("poster") or show["logo"],
                 "year": (origin or {}).get("year") or meta.get("year") or 0}
        if not title["id"]:
            return None
        if title["id"].startswith("tt"):
            return dict(title, addon=None)
        addon = next((base for base, manifest in self.manifests.items() if stremio.has_meta(manifest, "series", title["id"])), None)
        return dict(title, addon=addon) if addon else None

    def open_manager(self):
        manager = ListManager("script-m3u-movies-manager.xml", PATH, "default", "1080i")
        manager.on_change = self.reload
        manager.show_removed = self.show_removed
        manager.doModal()
        del manager

    def search(self):
        """Search the lists, whose results show first, and the movies and series of Cinemeta."""
        query = xbmcgui.Dialog().input(text(30044)).strip()
        if not query:
            return
        needle = query.casefold()
        results = [movie for movie in self.movies if needle in movie["channel"]["name"].casefold()]
        results += [show for show in self.shows if needle in show["name"].casefold()
                    or any(needle in entry["channel"]["name"].casefold() for entry in show["episodes"])]
        sources = [(kind, ("search", query)) for kind in ("movie", "series")]
        with self.show_lock:
            self.shown_index, self.shown_name = -1, None
            self.open_category(text(30042, query), sources, prefix=results)
        # The titles of Cinemeta load on a thread. Wait for them, so the focus can move to the posters.
        key, monitor = tuple(sources), xbmc.Monitor()
        for _ in range(150):
            page = self.pages.get(key)
            if results or self.shown_key != key or not page or not page["loading"]:
                break
            monitor.waitForAbort(0.1)
        self.focus_channels()

    def check_group(self):
        entries = [entry for item in self.items if not is_title(item) for entry in item_entries(item)]
        if self.items and not entries:
            # Titles of the catalog are checked when their sources are listed.
            xbmcgui.Dialog().ok(TITLE, text(30369))
            return
        self.check_entries(entries)

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

    def open_addons(self):
        addons = AddonsWindow("script-m3u-movies-addons.xml", PATH, "default", "1080i")
        addons.doModal()
        changed = addons.changed
        del addons
        if changed:
            # Catalogs of removed addons are dropped, and those of new ones are listed.
            self.pages = {key: page for key, page in self.pages.items() if all(source[0] != "addon" for _, source in key)}
            self.build_groups()

    def stream_addons(self, kind, item_id):
        """Installed addons that give sources for an item, as (name, address), in the order they were added."""
        return [(addon["manifest"]["name"], stremio.base_url(addon["url"])) for addon in storage.get_addons()
                if stremio.supports(addon["manifest"], "stream", kind, item_id)]

    def open_sources(self, title, kind, item_id, poster, origin=None):
        """Show the sources of a movie or an episode. Returns the direct link chosen to play, or None."""
        addons = self.stream_addons(kind, item_id)
        if not addons:
            xbmcgui.Dialog().ok(TITLE, text(30310))
            return None
        panel = SourcesPanel("script-m3u-movies-sources.xml", PATH, "default", "1080i")
        panel.catalog, panel.title, panel.kind, panel.item_id, panel.addons = self, title, kind, item_id, addons
        panel.poster, panel.choice, panel.origin = poster, None, origin
        panel.doModal()
        choice = panel.choice
        del panel
        return choice

    def download(self, source, origin=None):
        """Send a torrent to Downloads. Returns True when it was added. origin is the catalog title it is for."""
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
        if origin and origin.get("id"):
            threading.Thread(target=remember_origin, args=(downloads, info_hash, folder, source.get("file_idx"), origin),
                             daemon=True).start()
        notify(text(30308, source["label"]))
        return True

    def download_direct(self, source, title, origin=None):
        """Queue a direct link for the background service. Returns True when it was queued."""
        if not direct.can_download(source["url"]):
            xbmcgui.Dialog().ok(TITLE, text(30353))
            return False
        folder = ADDON.getSetting("download_folder") or choose_download_folder()
        if not folder:
            return False
        subfolder, name = direct.target_name(origin, source["url"], title)
        path = os.path.join(folder, subfolder, name) if subfolder else os.path.join(folder, name)
        stem, extension = os.path.splitext(path)
        copy = 2
        while os.path.exists(path) or os.path.exists(path + ".part"):
            path, copy = "%s (%d)%s" % (stem, copy, extension), copy + 1
        direct.add(DIRECT_JOBS, source["url"], source.get("headers"), path, os.path.splitext(os.path.basename(path))[0])
        if origin and origin.get("id"):
            storage.save_origins({path: origin})
        notify(text(30308, os.path.basename(path)))
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


class MovieDetails(xbmcgui.WindowXMLDialog):
    """Poster and details of a movie, with play, favorite and remove buttons. Sets choice for the catalog."""

    def onInit(self):
        movie = self.entry["channel"]
        groups = "  ·  ".join(name for name in series.movie_groups(movie) if name) or text(30043)
        self.setProperty("title", movie["name"])
        self.setProperty("poster", movie["logo"])
        self.setProperty("group", groups)
        show_downloaded(self, downloaded_text(None, is_local(self.entry)), self.entry["list_name"], "list")
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
    """Poster, seasons and episodes of a series. Sets choice and the episode to play for the catalog, or the direct
    link chosen in the sources of an episode.

    When the series is known to the catalog, its full list of episodes loads on a thread and joins the episodes of
    the lists: those in the lists play, and the others open their sources, to download or play them."""

    def onInit(self):
        show = self.entry
        self.progress = storage.get_progress()
        self.next, started = next_episode(show, self.progress)
        self.source = None
        self.setProperty("title", show["name"])
        self.setProperty("poster", show["logo"])
        self.meta = show.get("meta") or {}
        self.setProperty("plot", self.meta.get("plot", ""))
        show_downloaded(self, downloaded_text(len(show["episodes"]), is_local(show)),
                        "  ·  ".join(group for group in show["groups"] if group) or show["list_name"], "group")
        self.getControl(DETAILS_PLAY).setLabel(text(30118 if started else 30119, self.next["episode"]["season"],
                                                    self.next["episode"]["number"]))
        self.update_favorite()
        self.catalog_episodes = []
        self.build_rows()
        self.season = self.seasons.index(self.next["episode"]["season"])
        self.show_seasons()
        self.show_season(select=self.next)
        self.setFocusId(DETAILS_PLAY)
        self.catalog_title = self.window.catalog_series(show)
        if self.catalog_title:
            threading.Thread(target=self.load, daemon=True).start()

    def build_rows(self):
        """The episodes of the series: those the catalog lists, each with its entry when it is in the lists, then the
        entries the catalog does not list."""
        local = {}
        for entry in self.entry["episodes"]:
            local.setdefault((entry["episode"]["season"], entry["episode"]["number"]), []).append(entry)
        rows = []
        for season, number, title, aired, _, video_id in self.catalog_episodes:
            entries = local.pop((season, number), [None])
            rows += [{"season": season, "number": number, "title": (entry or {}).get("episode", {}).get("title") or title,
                      "aired": aired, "video_id": video_id, "entry": entry} for entry in entries]
        rows += [{"season": entry["episode"]["season"], "number": entry["episode"]["number"],
                  "title": entry["episode"]["title"], "aired": "", "video_id": None, "entry": entry}
                 for entries in local.values() for entry in entries]
        self.rows = sorted(rows, key=lambda row: (row["season"], row["number"]))
        # Specials last.
        self.seasons = sorted({row["season"] for row in rows}, key=lambda season: (season == 0, season))
        count = len({(row["season"], row["number"]) for row in rows})
        info = text(30121, len([season for season in self.seasons if season]) or 1, count)
        self.setProperty("info", info + ("  ·  " + meta_line(self.meta) if meta_line(self.meta) else ""))

    def load(self):
        """Load the episodes of the series from the catalog, and show them with those of the lists."""
        addon, title_id = self.catalog_title["addon"], self.catalog_title["id"]
        try:
            meta = stremio.meta(addon, "series", title_id) if addon else cinemeta.meta("series", title_id)
            found = cinemeta.episodes(meta)
        except Exception:
            return
        if not found:
            return
        try:
            position = self.getControl(SERIES_EPISODES).getSelectedPosition()
            selected = self.episodes[position] if 0 <= position < len(self.episodes) else None
            season = self.seasons[self.season]
            self.catalog_episodes = found
            self.build_rows()
            self.season = self.seasons.index(season) if season in self.seasons else 0
            self.show_seasons()
            self.show_season(select=selected and (selected["entry"] or (selected["season"], selected["number"])))
        except RuntimeError:
            # The details closed while the episodes loaded.
            pass

    def show_seasons(self):
        seasons = self.getControl(SERIES_SEASONS)
        seasons.reset()
        seasons.addItems([xbmcgui.ListItem(season_name(season)) for season in self.seasons])
        seasons.selectItem(self.season)

    def show_season(self, select=None):
        """Show the episodes of the season. select is the entry, or the (season, number), to highlight."""
        season = self.seasons[self.season]
        self.episodes = [row for row in self.rows if row["season"] == season]
        items = []
        for row in self.episodes:
            title, number, entry = row["title"], row["number"], row["entry"]
            # Specials have no episode number, only their title.
            label = title if number == 0 and title else "E%02d" % number + ("  ·  " + title if title else "")
            item = xbmcgui.ListItem(label)
            aired = "/".join(reversed(row["aired"].split("-"))) if re.match(r"\d{4}-\d{2}-\d{2}$", row["aired"]) else ""
            if entry:
                state = self.progress.get(entry["channel"]["id"], {})
                if resumable(state):
                    item.setLabel2(text(30126, time_text(state["position"])))
                else:
                    # Video files have no duration in the lists, so they show the date the catalog gives.
                    item.setLabel2(duration_text(entry["channel"]["duration"]) or aired)
                item.setProperty("watched", "true" if state.get("watched") else "false")
                item.setProperty("downloaded", "true" if is_local(entry) else "false")
            else:
                item.setLabel2(aired)
            items.append(item)
        episodes = self.getControl(SERIES_EPISODES)
        episodes.reset()
        episodes.addItems(items)
        for index, row in enumerate(self.episodes):
            if select is not None and (row["entry"] is select or (row["season"], row["number"]) == select):
                episodes.selectItem(index)
                break

    def update_favorite(self):
        favorite = is_favorite(self.entry, storage.get_favorites())
        self.setProperty("favorite", "true" if favorite else "false")
        self.getControl(DETAILS_FAVORITE).setLabel(text(30115 if favorite else 30114))

    def onAction(self, action):
        if action.getId() in ACTION_BACK:
            self.close()
        elif self.getFocusId() == SERIES_SEASONS:
            season = self.getControl(SERIES_SEASONS).getSelectedPosition()
            if season != self.season and 0 <= season < len(self.seasons):
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
            if not 0 <= position < len(self.episodes):
                return
            row = self.episodes[position]
            if row["entry"]:
                self.play(row["entry"])
            else:
                self.sources(row)

    def sources(self, row):
        """Open the sources of an episode that is not in the lists. A direct link chosen there plays once the
        details close, and a download goes to Downloads, kept with the title of the series."""
        name = "%s  ·  %s" % (self.entry["name"], text(30133, row["season"], row["number"]))
        origin = dict(self.catalog_title, season=row["season"], episode=row["number"])
        origin.pop("addon", None)
        source = self.window.open_sources(name, "series", row["video_id"], origin["poster"], origin)
        if source:
            self.choice, self.source = "direct", source
            self.close()

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
            season = self.seasons[self.season]
            self.build_rows()
            self.season = self.seasons.index(season) if season in self.seasons else 0
            self.show_seasons()
            self.show_season()


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
        # The episodes downloaded of a series, or whether a movie is, shown with a green check.
        self.downloaded = self.catalog.downloaded(self.kind, item, self.entry)
        progress = storage.get_progress()
        self.watched = {(each["episode"]["season"], each["episode"]["number"]) for each in (self.entry or {}).get("episodes", [])
                        if progress.get(each["channel"]["id"], {}).get("watched")}
        library = text(30222, self.entry["list_name"]) if self.entry else ""
        show_downloaded(self, downloaded_text(len(self.downloaded) if self.series else None, self.downloaded), library)
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
        # A spinner shows where the seasons go until they arrive.
        self.setProperty("loading", "true" if self.series else "false")
        self.setProperty("episodes_error", "")
        threading.Thread(target=self.load, daemon=True).start()

    def origin(self, item_id):
        """The title a download is for, kept with the downloaded file so the folder shows it as this title.
        An episode has an id such as "tt0123:1:2", with its season and number."""
        item = self.item
        origin = {"kind": "series" if self.series else "movie", "id": item.get("id", ""), "name": item.get("name", ""),
                  "poster": item.get("poster", ""), "year": cinemeta.first_year(item.get("releaseInfo", "")) or 0}
        parts = str(item_id).split(":")
        if self.series and len(parts) >= 3 and parts[-2].isdigit() and parts[-1].isdigit():
            origin["season"], origin["episode"] = int(parts[-2]), int(parts[-1])
        return origin

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
        """Load the details while the spinner turns, then show the episodes, or why there are none."""
        try:
            found = self.fetch()
        except Exception:
            found = None
        if self.series:
            if found:
                self.show_episodes(found)
            self.setProperty("episodes_error", "" if found else text(30356 if found is None else 30357))
        self.setProperty("loading", "false")

    def fetch(self):
        """Load the full description and, for a series, return its episodes. Search results also lack the year,
        genres and people, which this fills in. Returns None when the details could not be loaded."""
        item = self.item
        if item.get("addon"):
            meta = stremio.meta(item["addon"], item.get("type", self.kind), item["id"])
        elif item["id"].startswith("tt"):
            meta = cinemeta.meta(self.kind, item["id"])
        else:
            return None
        full = cinemeta.summary(meta)
        self.item = dict(self.item, **{key: value for key, value in full.items() if value and key != "id"})
        self.show_info(self.item)
        self.plot = full["plot"] or self.plot
        self.setProperty("plot", self.plot)
        return cinemeta.episodes(meta) if self.series else []

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
        control.addItems([xbmcgui.ListItem(season_name(season)) for season in seasons])
        self.show_season()

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
            item.setProperty("downloaded", "true" if (season, number) in self.downloaded else "false")
            item.setProperty("watched", "true" if (season, number) in self.watched else "false")
            items.append(item)
        control = self.getControl(SERIES_EPISODES)
        control.reset()
        control.addItems(items)

    def update_watchlist(self):
        if self.entry:
            in_list = is_favorite(self.entry, storage.get_favorites())
        else:
            in_list = self.item["id"] in {item["id"] for item in storage.get_watchlist()}
        self.setProperty("favorite", "true" if in_list else "false")
        self.getControl(CATALOG_MY_LIST).setLabel(text(30071 if in_list else 30070))

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
            self.catalog.toggle_favorite(self.item)
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
        source = self.catalog.open_sources(title, self.stream_type(), item_id, self.item.get("poster", ""), self.origin(item_id))
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
            if self.catalog.download(source, self.origin):
                self.close()
            return
        # A direct link plays while it downloads, or is saved to the download folder to watch later.
        choice = xbmcgui.Dialog().contextmenu([text(30349), text(30350)])
        if choice == 0:
            self.choice = dict(source, title=self.title, poster=self.poster)
            self.close()
        elif choice == 1 and self.catalog.download_direct(source, self.title, self.origin):
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
        types = [type_name(kind) for kind in manifest.get("types") or []]
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


def remember_origin(downloads, info_hash, folder, file_index, origin, timeout=600):
    """Keep the catalog title of a download with the paths of its videos, once Torrest knows its files.

    A single file, as an episode chosen from a season pack, takes the whole origin. Several videos, as a season
    downloaded at once, keep only the series, so each episode takes its number from its file."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            files = downloads.files(info_hash)
        except torrents.EngineError:
            files = []
        if files:
            break
        time.sleep(3)
    else:
        return
    chosen = [item for item in files if item.get("id") == file_index] if file_index is not None else \
        [item for item in files if folders.is_video(item.get("path", ""))]
    whole = dict(origin) if len(chosen) == 1 else {key: value for key, value in origin.items() if key not in ("season", "episode")}
    storage.save_origins({folder.rstrip("/") + "/" + item["path"].lstrip("/"): whole for item in chosen if item.get("path")})


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


def direct_status(job):
    """Detail line, progress and state of a direct link for the list of downloads."""
    state = {"queued": "downloading", "downloading": "downloading", "paused": "paused", "finished": "finished",
             "failed": "paused"}.get(job["state"], "downloading")
    done, total = job["done"], job["total"]
    progress = int(done * 100 / total) if total else (100 if job["state"] == "finished" else 0)
    labels = {"queued": text(30351), "downloading": text(30183), "paused": text(30181), "finished": text(30182),
              "failed": text(30352, job.get("error") or "?")}
    parts = [text(30306), labels.get(job["state"], text(30351))]
    if job["state"] == "downloading" and job["rate"]:
        parts.append(rate_text(job["rate"]))
    if total:
        parts.append(size_text(total) if job["state"] == "finished" else text(30185, size_text(done), size_text(total)))
    elif done:
        parts.append(size_text(done))
    if job["state"] == "downloading" and job["rate"] and total:
        left = (total - done) / job["rate"]
        if left >= 60:
            parts.append(text(30186, duration_text(left)))
    return "  ·  ".join(parts), progress, state


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
        """Show the downloads: torrents, then direct links. Rows are updated in place, so the selection stays while
        they change."""
        try:
            items = self.engine.torrents()
        except torrents.EngineError:
            items = []
        jobs = direct.jobs(DIRECT_JOBS)
        self.jobs = {job["id"]: job for job in jobs}
        hashes = [torrent["info_hash"] for torrent in items] + ["direct:" + job["id"] for job in jobs]
        rows = len(hashes)
        if hashes != self.hashes:
            position = self.list_control.getSelectedPosition()
            self.list_control.reset()
            self.list_control.addItems([xbmcgui.ListItem() for _ in range(rows)])
            if rows:
                self.list_control.selectItem(min(max(position, 0), rows - 1))
            self.hashes = hashes
            if not rows and self.getFocusId() == DOWNLOADS_LIST:
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
        for number, job in enumerate(jobs, len(items)):
            detail, progress, state = direct_status(job)
            row = self.list_control.getListItem(number)
            row.setLabel(job["title"])
            row.setLabel2(detail)
            row.setProperty("progress", str(progress))
            row.setProperty("percent", "%d%%" % progress)
            row.setProperty("state", state)
            down += job["rate"] if job["state"] == "downloading" else 0
        self.setProperty("summary", text(30193, rate_text(down), rate_text(up)) if rows else "")
        self.getControl(DOWNLOADS_EMPTY).setLabel("" if rows else text(30169))

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
        if info_hash.startswith("direct:"):
            self.direct_menu(info_hash[len("direct:"):], row, paused)
            return
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
            # Torrest deletes its own files of the torrent even when the video stays, which a read-only drive refuses.
            read_only = "read-only" in str(error).lower()
            xbmcgui.Dialog().ok(TITLE, text(30359) if read_only else text(30358, error))
        self.update()


    def direct_menu(self, job_id, row, paused):
        """Pause or resume a direct link, or remove it from the list, with or without its file."""
        job = self.jobs.get(job_id, {})
        finished = job.get("state") == "finished"
        options = ([] if finished else [(text(30175 if paused or job.get("state") == "failed" else 30174),
                                         "resume" if paused or job.get("state") == "failed" else "pause")])
        options += [(text(30176), "remove"), (text(30177), "remove_files")]
        choice = xbmcgui.Dialog().contextmenu([label for label, _ in options])
        if choice < 0:
            return
        action = options[choice][1]
        if action == "remove_files" and not xbmcgui.Dialog().yesno(TITLE, text(30178, row.getLabel()), nolabel=text(30040),
                                                                   yeslabel=text(30142)):
            return
        direct.request(DIRECT_JOBS, job_id, action)
        notify(text(30354))


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
