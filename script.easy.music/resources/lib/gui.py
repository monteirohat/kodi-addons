"""Music player: a toolbar and playlists on the left, the songs of the playlist on the right, and the player at the bottom.

A playlist is a folder of songs. Songs play in the music playlist of Kodi, so they go on after the window closes."""

import json
import os
import threading

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import music


ADDON = xbmcaddon.Addon()
TITLE = ADDON.getAddonInfo("name")
PATH = ADDON.getAddonInfo("path")
MEDIA = os.path.join(PATH, "resources", "skins", "default", "media")
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
FOLDERS_FILE = os.path.join(PROFILE, "folders.json")
LIKED_FILE = os.path.join(PROFILE, "liked.json")
ACTION_LEFT, ACTION_RIGHT, ACTION_UP, ACTION_DOWN = 1, 2, 3, 4
ACTION_BACK = (10, 92)
ACTION_CONTEXT_MENU = 117
TOOLBAR, GROUPS, SONGS = 100, 200, 300
TITLE_LABEL, COUNT_LABEL, EMPTY_LABEL = 401, 402, 404
SHUFFLE, PREVIOUS, PLAY, NEXT, REPEAT, LIKE = 601, 602, 603, 604, 605, 606
PLAYER_BUTTONS = (SHUFFLE, PREVIOUS, PLAY, NEXT, REPEAT, LIKE)
# Delay before the songs follow the highlighted playlist, so fast scrolling stays smooth.
FOLLOW_DELAY = 0.3
# How often the song that plays is looked up, to mark it in the list and in the player.
WATCH_INTERVAL = 1

# Toolbar above the playlists: icon, label and the MainWindow method it runs.
TOOLS = [
    ("folders.png", 30010, "manage_folders"),
    ("refresh.png", 30011, "rescan"),
    ("search.png", 30012, "search"),
]


def text(string_id, *arguments):
    return ADDON.getLocalizedString(string_id).format(*arguments)


def notify(message):
    xbmcgui.Dialog().notification(TITLE, message, ADDON.getAddonInfo("icon"), 3000)


def busy(active):
    xbmc.executebuiltin("ActivateWindow(busydialognocancel)" if active else "Dialog.Close(busydialognocancel)")


def load(path, default):
    try:
        with open(path, encoding="utf-8") as data:
            return json.load(data)
    except (OSError, ValueError):
        return default


def save(path, value):
    os.makedirs(PROFILE, exist_ok=True)
    with open(path, "w", encoding="utf-8") as data:
        json.dump(value, data, ensure_ascii=False, indent=1)


def rpc(method, **params):
    request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    return json.loads(xbmc.executeJSONRPC(json.dumps(request))).get("result") or {}


def is_local(path):
    return "://" not in path


def join(folder, name):
    return os.path.join(folder, name) if is_local(folder) else folder.rstrip("/") + "/" + name


def default_folders():
    """The music sources of Kodi and the Music folder of the system, the first time the add-on opens."""
    found = []
    for source in rpc("Files.GetSources", media="music").get("sources", []):
        path = source.get("file", "")
        if path and not path.startswith(("addons://", "special://", "multipath://", "musicdb://")):
            found.append(path.rstrip("/") if is_local(path) else path)
    home_music = os.path.join(os.path.expanduser("~"), "music")
    if os.path.isdir(home_music):
        found.append(home_music)
    return list(dict.fromkeys(found))


def walk(folder):
    """Folders below a folder, with their files. Local folders use the system, network folders the file access of Kodi."""
    if is_local(folder):
        for root, dirs, names in os.walk(folder):
            dirs[:] = sorted((d for d in dirs if not d.startswith(".")), key=music.sort_key)
            yield root, names
        return
    pending = [folder.rstrip("/")]
    while pending:
        root = pending.pop(0)
        try:
            dirs, names = xbmcvfs.listdir(root + "/")
        except Exception:
            continue
        dirs = sorted((d for d in dirs if not d.startswith(".")), key=music.sort_key)
        yield root, names
        pending[0:0] = [root + "/" + d for d in dirs]


def scan(folders):
    """Every song under the folders, with the folder that holds it, which is its playlist, and the cover of that folder."""
    found, seen = [], set()
    for folder in folders:
        for root, names in walk(folder):
            songs = sorted((name for name in names if music.is_song(name)), key=music.sort_key)
            if not songs:
                continue
            cover_name = music.cover(names)
            cover = join(root, cover_name) if cover_name else ""
            for name in songs:
                path = join(root, name)
                if path in seen:
                    continue
                seen.add(path)
                tags = music.tags(path) if is_local(path) else {"title": "", "artist": "", "album": "", "track": 0}
                track = tags["track"] or music.number_from_name(name)
                found.append({"path": path, "name": name, "folder": root, "cover": cover,
                              "title": music.clean_title(tags["title"], track) if tags["title"] else music.title_from_name(name),
                              "artist": tags["artist"], "album": tags["album"] or music.name_of(root), "track": track})
    return found


def count_label(count):
    return text(30005) if count == 1 else text(30003, count)


def list_item(song):
    """A song for the music playlist of Kodi, with the tags the player bar shows."""
    item = xbmcgui.ListItem(song["title"], path=song["path"])
    tag = item.getMusicInfoTag()
    tag.setTitle(song["title"])
    if song["artist"]:
        tag.setArtist(song["artist"])
    tag.setAlbum(song["album"])
    if song["track"]:
        tag.setTrack(song["track"])
    if song["cover"]:
        item.setArt({"thumb": song["cover"]})
    return item


class MainWindow(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loaded = False
        self.groups, self.shown, self.everything = [], [], []
        self.shown_index = -1
        self.follow_timer = None
        self.liked = set()
        self.query = ""
        self.playing_path = None
        self.stopped = threading.Event()

    def onInit(self):
        # Also called when a dialog over the window closes. Keep the current state then.
        if self.loaded:
            return
        self.loaded = True
        self.toolbar = self.getControl(TOOLBAR)
        self.group_list = self.getControl(GROUPS)
        self.song_list = self.getControl(SONGS)
        tools = []
        for icon, label, _ in TOOLS:
            item = xbmcgui.ListItem(text(label))
            item.setArt({"icon": os.path.join(MEDIA, icon)})
            tools.append(item)
        self.toolbar.addItems(tools)
        folders = load(FOLDERS_FILE, None)
        if folders is None:
            folders = default_folders()
            save(FOLDERS_FILE, folders)
        self.liked = set(load(LIKED_FILE, []))
        self.reload()
        threading.Thread(target=self.watch, daemon=True).start()
        if self.shown:
            self.setFocusId(SONGS)
        elif not folders:
            self.setFocusId(TOOLBAR)
            self.manage_folders()
        else:
            self.setFocusId(GROUPS)

    def close(self):
        self.stopped.set()
        super().close()

    # Playlists and songs

    def reload(self, keep=None):
        """Scan the folders and build the playlists. keep is the playlist to show afterwards, by its key."""
        busy(True)
        try:
            self.everything = scan(load(FOLDERS_FILE, []))
        finally:
            busy(False)
        folders = {}
        for song in self.everything:
            folders.setdefault(song["folder"], []).append(song)
        self.groups = [{"key": "all", "name": text(30001), "songs": self.everything}]
        liked = [song for song in self.everything if song["path"] in self.liked]
        if liked:
            self.groups.append({"key": "liked", "name": text(30002), "songs": liked})
        if self.query:
            self.groups.insert(0, self.results_group())
        for folder in sorted(folders, key=lambda folder: music.sort_key(music.name_of(folder))):
            songs = sorted(folders[folder], key=lambda song: (song["track"] or 9999, music.sort_key(song["name"])))
            self.groups.append({"key": folder, "name": music.name_of(folder), "songs": songs, "cover": songs[0]["cover"]})
        self.fill_groups()
        keys = [group["key"] for group in self.groups]
        index = keys.index(keep) if keep in keys else 0
        self.group_list.selectItem(index)
        self.shown_index = -1
        self.show_group(index)

    def fill_groups(self):
        items = []
        for group in self.groups:
            item = xbmcgui.ListItem(group["name"])
            item.setLabel2(str(len(group["songs"])))
            items.append(item)
        self.group_list.reset()
        self.group_list.addItems(items)

    def results_group(self):
        words = self.query.lower().split()
        found = [song for song in self.everything
                 if all(word in ("%s %s %s %s" % (song["title"], song["artist"], song["album"], song["name"])).lower() for word in words)]
        return {"key": "search", "name": text(30014, self.query), "songs": found}

    def show_group(self, index, select=0):
        self.shown_index = index
        group = self.groups[index]
        self.shown = group["songs"]
        numbered = group["key"] not in ("all", "liked", "search")
        items = []
        for position, song in enumerate(self.shown):
            item = xbmcgui.ListItem(song["title"])
            item.setLabel2(song["artist"] or song["album"])
            item.setProperty("album", song["album"])
            item.setProperty("number", str(song["track"] if numbered and song["track"] else position + 1))
            item.setProperty("liked", "true" if song["path"] in self.liked else "false")
            item.setProperty("playing", "true" if song["path"] == self.playing_path else "false")
            items.append(item)
        self.song_list.reset()
        self.song_list.addItems(items)
        if self.shown:
            self.song_list.selectItem(min(max(select, 0), len(self.shown) - 1))
        self.getControl(TITLE_LABEL).setLabel(group["name"])
        self.getControl(COUNT_LABEL).setLabel(count_label(len(self.shown)) if self.shown else "")
        if self.shown:
            empty = ""
        elif group["key"] == "all":
            empty = text(30021)
        elif group["key"] == "search":
            empty = text(30015, self.query)
        else:
            empty = text(30022)
        self.getControl(EMPTY_LABEL).setLabel(empty)

    def follow_group(self):
        index = self.group_list.getSelectedPosition()
        if 0 <= index < len(self.groups) and index != self.shown_index:
            self.show_group(index)

    def selected_song(self):
        position = self.song_list.getSelectedPosition()
        return self.shown[position] if 0 <= position < len(self.shown) else None

    # The song that plays

    def watch(self):
        """Mark the song that plays in the list, and tell the heart of the player whether it is liked."""
        monitor = xbmc.Monitor()
        player = xbmc.Player()
        while not self.stopped.is_set() and not monitor.abortRequested():
            try:
                path = player.getPlayingFile() if player.isPlayingAudio() else None
            except RuntimeError:
                path = None
            if path != self.playing_path:
                previous, self.playing_path = self.playing_path, path
                for index, song in enumerate(self.shown):
                    if song["path"] in (previous, path):
                        self.song_list.getListItem(index).setProperty("playing", "true" if song["path"] == path else "false")
            self.setProperty("liked", "true" if path and path in self.liked else "false")
            monitor.waitForAbort(WATCH_INTERVAL)

    def play(self, songs, position):
        playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        playlist.clear()
        for song in songs:
            playlist.add(song["path"], list_item(song))
        xbmc.Player().play(playlist, startpos=position)

    def queue(self, song, next_one):
        """Add a song to the music playlist that plays: after the song that plays, or at its end."""
        playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        if not xbmc.Player().isPlayingAudio() or playlist.size() == 0:
            self.play([song], 0)
            return
        if next_one:
            playlist.add(song["path"], list_item(song), playlist.getposition() + 1)
            notify(text(30047, song["title"]))
        else:
            playlist.add(song["path"], list_item(song))
            notify(text(30046, song["title"]))

    # Keys

    def onAction(self, action):
        action_id = action.getId()
        focus = self.getFocusId()
        if action_id in ACTION_BACK:
            if focus in PLAYER_BUTTONS:
                self.setFocusId(SONGS if self.shown else GROUPS)
            elif focus == SONGS:
                self.setFocusId(GROUPS)
            else:
                self.close()
        elif action_id == ACTION_CONTEXT_MENU and focus == SONGS and self.shown:
            self.song_menu(self.selected_song())
        elif focus == SONGS and action_id == ACTION_LEFT:
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
                self.setFocusId(SONGS)
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
                self.setFocusId(SONGS)
        elif control_id == SONGS and self.shown:
            self.play(self.shown, self.song_list.getSelectedPosition())
        elif control_id == PLAY:
            if xbmc.Player().isPlayingAudio():
                xbmc.executebuiltin("PlayerControl(Play)")
            elif self.shown:
                # Nothing plays: the player starts the playlist shown, from the song selected.
                self.play(self.shown, max(self.song_list.getSelectedPosition(), 0))
        elif control_id == LIKE and self.playing_path:
            song = next((song for song in self.everything if song["path"] == self.playing_path), None)
            if song:
                self.toggle_like(song)

    # Options

    def song_menu(self, song):
        position = self.song_list.getSelectedPosition()
        liked = song["path"] in self.liked
        options = [(30040, lambda: self.play(self.shown, position)), (30041, lambda: self.queue(song, True)),
                   (30042, lambda: self.queue(song, False)), (30044 if liked else 30043, lambda: self.toggle_like(song)),
                   (30045, lambda: show_info(song))]
        choice = xbmcgui.Dialog().contextmenu([text(string_id) for string_id, _ in options])
        if choice >= 0:
            options[choice][1]()

    def toggle_like(self, song):
        if song["path"] in self.liked:
            self.liked.discard(song["path"])
            notify(text(30049))
        else:
            self.liked.add(song["path"])
            notify(text(30048))
        save(LIKED_FILE, sorted(self.liked))
        self.setProperty("liked", "true" if self.playing_path in self.liked else "false")
        for index, shown in enumerate(self.shown):
            if shown["path"] == song["path"]:
                self.song_list.getListItem(index).setProperty("liked", "true" if song["path"] in self.liked else "false")
        self.update_liked_group()

    def update_liked_group(self):
        """Add, update or remove the playlist of liked songs, keeping the playlist shown."""
        key = self.groups[self.shown_index]["key"] if 0 <= self.shown_index < len(self.groups) else None
        position = self.song_list.getSelectedPosition()
        liked = [song for song in self.everything if song["path"] in self.liked]
        keys = [group["key"] for group in self.groups]
        if "liked" in keys:
            index = keys.index("liked")
            if liked:
                self.groups[index]["songs"] = liked
                self.group_list.getListItem(index).setLabel2(str(len(liked)))
                if key == "liked":
                    self.show_group(index, select=min(position, len(liked) - 1))
                return
            del self.groups[index]
        elif liked:
            self.groups.insert(keys.index("all") + 1, {"key": "liked", "name": text(30002), "songs": liked})
        else:
            return
        selected = self.groups[self.group_list.getSelectedPosition()]["key"] if self.groups else None
        self.fill_groups()
        keys = [group["key"] for group in self.groups]
        if key in keys:
            self.shown_index = keys.index(key)
            self.group_list.selectItem(keys.index(selected) if selected in keys else self.shown_index)
        else:
            # The last liked song was removed while its playlist was shown.
            self.group_list.selectItem(0)
            self.show_group(0)
            self.setFocusId(GROUPS)

    # Tools

    def manage_folders(self):
        while True:
            folders = load(FOLDERS_FILE, [])
            options = [text(30031)] + [text(30032, folder) for folder in folders]
            choice = xbmcgui.Dialog().select(text(30030), options)
            if choice < 0:
                return
            if choice == 0:
                folder = xbmcgui.Dialog().browse(0, text(30033), "music")
                if not folder or folder in folders:
                    continue
                folders.append(folder.rstrip("/") if is_local(folder) else folder)
                save(FOLDERS_FILE, folders)
                self.reload()
                notify(text(30034, music.name_of(folder)))
                if self.shown:
                    self.setFocusId(SONGS)
            elif xbmcgui.Dialog().yesno(TITLE, text(30035, folders[choice - 1]), nolabel=text(30036), yeslabel=text(30037)):
                del folders[choice - 1]
                save(FOLDERS_FILE, folders)
                self.reload()

    def rescan(self):
        keep = self.groups[self.shown_index]["key"] if 0 <= self.shown_index < len(self.groups) else None
        before = len(self.everything)
        self.reload(keep)
        notify(text(30038, max(len(self.everything) - before, 0)))

    def search(self):
        query = xbmcgui.Dialog().input(text(30013)).strip()
        if not query:
            return
        self.query = query
        self.reload("search")
        self.setFocusId(SONGS if self.shown else GROUPS)


def show_info(song):
    size = 0
    if is_local(song["path"]):
        try:
            size = os.path.getsize(song["path"])
        except OSError:
            pass
    lines = [(30050, song["title"]), (30051, song["artist"]), (30052, song["album"]),
             (30053, str(song["track"]) if song["track"] else ""),
             (30054, "%.1f MB" % (size / 1048576.0) if size else ""), (30055, song["folder"])]
    xbmcgui.Dialog().ok(song["title"], "[CR]".join("[COLOR grey]%s:[/COLOR] %s" % (text(string_id), value)
                                                  for string_id, value in lines if value))


def run():
    window = MainWindow("script-easy-music-main.xml", PATH, "default", "1080i")
    window.doModal()
    del window
