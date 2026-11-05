"""Picture viewer: a toolbar and albums on the left, the pictures of the album on the right, and a picture in full screen."""

import json
import os
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import pictures


ADDON = xbmcaddon.Addon()
TITLE = ADDON.getAddonInfo("name")
PATH = ADDON.getAddonInfo("path")
MEDIA = os.path.join(PATH, "resources", "skins", "default", "media")
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
FOLDERS_FILE = os.path.join(PROFILE, "folders.json")
FAVORITES_FILE = os.path.join(PROFILE, "favorites.json")
# Turns and mirrors of pictures, shown without changing the files: {path: [rotation, mirrored]}.
TURNS_FILE = os.path.join(PROFILE, "turns.json")
ACTION_LEFT, ACTION_RIGHT, ACTION_UP, ACTION_DOWN = 1, 2, 3, 4
ACTION_BACK = (10, 92)
ACTION_CONTEXT_MENU = 117
ACTION_INFO = 11
TOOLBAR, GROUPS, GALLERY = 100, 200, 300
ALBUM_TITLE, ALBUM_COUNT, ALBUM_EMPTY = 401, 402, 404
VIEWER_NEXT, VIEWER_PREVIOUS = 11, 12
# Delay before the gallery follows the highlighted album, so fast scrolling stays smooth.
FOLLOW_DELAY = 0.3
# Seconds the name and position of a picture stay on the screen after it changes.
DETAILS_TIME = 3

# Toolbar above the albums: icon, label and the MainWindow method it runs.
TOOLS = [
    ("folders.png", 30011, "manage_folders"),
    ("refresh.png", 30012, "rescan"),
    ("gear.png", 30010, "open_settings"),
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


def default_folders():
    """The picture sources of Kodi and the Pictures folder of the system, the first time the add-on opens."""
    found = []
    for source in rpc("Files.GetSources", media="pictures").get("sources", []):
        path = source.get("file", "")
        if path and not path.startswith(("addons://", "special://", "multipath://")):
            found.append(path)
    home_pictures = os.path.join(os.path.expanduser("~"), "pictures")
    if os.path.isdir(home_pictures):
        found.append(home_pictures)
    return [folder for folder in dict.fromkeys(found) if folder_has_pictures(folder)]


def folder_has_pictures(folder):
    for _, _, names in walk(folder):
        if any(pictures.is_picture(name) for name in names):
            return True
    return False


def walk(folder):
    """Folders below a folder, with their files. Local folders use the system, network folders the file access of Kodi."""
    if "://" not in folder:
        for root, dirs, names in os.walk(folder):
            dirs[:] = sorted((d for d in dirs if not d.startswith(".")), key=pictures.sort_key)
            yield root, dirs, names
        return
    pending = [folder.rstrip("/")]
    while pending:
        root = pending.pop(0)
        try:
            dirs, names = xbmcvfs.listdir(root + "/")
        except Exception:
            continue
        dirs = sorted((d for d in dirs if not d.startswith(".")), key=pictures.sort_key)
        yield root, dirs, names
        pending[0:0] = [root + "/" + d for d in dirs]


def modified(path):
    if "://" not in path:
        try:
            info = os.stat(path)
            return info.st_mtime, info.st_size
        except OSError:
            return 0, 0
    try:
        info = xbmcvfs.Stat(path)
        return info.st_mtime(), info.st_size()
    except Exception:
        return 0, 0


def scan(folders):
    """Every picture under the folders, each one with its album, which is the folder that holds it."""
    found, seen = [], set()
    for folder in folders:
        for root, _, names in walk(folder):
            for name in names:
                if not pictures.is_picture(name):
                    continue
                path = os.path.join(root, name) if "://" not in root else root + "/" + name
                if path in seen:
                    continue
                seen.add(path)
                when, size = modified(path)
                found.append({"path": path, "name": name, "album": root, "time": when, "size": size})
    return found


def when(seconds):
    return time.strftime("%d/%m/%Y", time.localtime(seconds)) if seconds else ""


def turn(position, change):
    """The position of a picture after a change. A position is a clockwise rotation of the picture mirrored or not
    first; a mirror after a rotation is the opposite rotation of the mirrored picture."""
    rotation, mirrored = position
    if change == "right":
        return [(rotation + 90) % 360, mirrored]
    if change == "left":
        return [(rotation - 90) % 360, mirrored]
    if change == "horizontal":
        return [-rotation % 360, not mirrored]
    if change == "vertical":
        return [(180 - rotation) % 360, not mirrored]
    return [0, False]


def count_label(count):
    return text(30005) if count == 1 else text(30003, count)


class MainWindow(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loaded = False
        self.groups, self.shown = [], []
        self.shown_index = -1
        self.grid_position = -1
        self.follow_timer = None
        self.favorites = set()
        self.turns = {}

    def onInit(self):
        # Also called when the picture in full screen closes. Keep the current state then.
        if self.loaded:
            return
        self.loaded = True
        self.toolbar = self.getControl(TOOLBAR)
        self.group_list = self.getControl(GROUPS)
        self.gallery = self.getControl(GALLERY)
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
        self.favorites = set(load(FAVORITES_FILE, []))
        self.turns = load(TURNS_FILE, {})
        self.reload()
        if self.shown:
            self.setFocusId(GALLERY)
        elif not folders:
            self.setFocusId(TOOLBAR)
            self.manage_folders()
        else:
            self.setFocusId(GROUPS)

    # Albums and pictures

    def reload(self, keep=None):
        """Scan the folders and build the albums. keep is the album to show afterwards, by its key."""
        busy(True)
        try:
            self.all = scan(load(FOLDERS_FILE, []))
        finally:
            busy(False)
        newest = ADDON.getSettingInt("order") == 0
        by_name = lambda picture: (pictures.sort_key(picture["album"]), pictures.sort_key(picture["name"]))
        everything = sorted(self.all, key=(lambda picture: -picture["time"]) if newest else by_name)
        albums = {}
        for picture in self.all:
            albums.setdefault(picture["album"], []).append(picture)
        names = pictures.album_names(list(albums))
        self.groups = [{"key": "all", "name": text(30001), "pictures": everything}]
        favorites = [picture for picture in everything if picture["path"] in self.favorites]
        if favorites:
            self.groups.append({"key": "favorites", "name": text(30002), "pictures": favorites})
        for folder in sorted(albums, key=lambda folder: pictures.sort_key(names[folder])):
            album = sorted(albums[folder], key=lambda picture: pictures.sort_key(picture["name"]))
            self.groups.append({"key": folder, "name": names[folder], "pictures": album})
        items = []
        for group in self.groups:
            item = xbmcgui.ListItem(group["name"])
            item.setLabel2(str(len(group["pictures"])))
            items.append(item)
        self.group_list.reset()
        self.group_list.addItems(items)
        keys = [group["key"] for group in self.groups]
        index = keys.index(keep) if keep in keys else 0
        self.group_list.selectItem(index)
        self.shown_index = -1
        self.show_group(index)

    def show_group(self, index, select=0):
        if index == self.shown_index and select is None:
            return
        self.shown_index = index
        group = self.groups[index]
        self.shown = group["pictures"]
        items = []
        for picture in self.shown:
            item = xbmcgui.ListItem(picture["name"])
            item.setLabel2(when(picture["time"]))
            item.setArt({"thumb": picture["path"]})
            item.setProperty("favorite", "true" if picture["path"] in self.favorites else "false")
            self.set_turn(item, picture)
            items.append(item)
        self.gallery.reset()
        self.gallery.addItems(items)
        if self.shown:
            self.gallery.selectItem(min(max(select or 0, 0), len(self.shown) - 1))
        self.grid_position = -1
        self.getControl(ALBUM_TITLE).setLabel(group["name"])
        self.getControl(ALBUM_COUNT).setLabel(count_label(len(self.shown)) if self.shown else "")
        if self.shown:
            empty = ""
        elif group["key"] == "all":
            empty = text(30021)
        else:
            empty = text(30022)
        self.getControl(ALBUM_EMPTY).setLabel(empty)

    def follow_group(self):
        index = self.group_list.getSelectedPosition()
        if 0 <= index < len(self.groups) and index != self.shown_index:
            self.show_group(index)

    def turn_of(self, picture):
        return self.turns.get(picture["path"], [0, False])

    def set_turn(self, target, picture):
        """Give a gallery item or the full screen window the rotation and mirror of a picture."""
        rotation, mirrored = self.turn_of(picture)
        target.setProperty("rotation", str(rotation))
        target.setProperty("mirror", "true" if mirrored else "false")

    def turn_options(self, picture, after=None):
        """Options that turn or mirror a picture. after runs once the picture has changed."""
        def change(kind):
            position = turn(self.turn_of(picture), kind)
            if position == [0, False]:
                self.turns.pop(picture["path"], None)
            else:
                self.turns[picture["path"]] = position
            save(TURNS_FILE, self.turns)
            for index, shown in enumerate(self.shown):
                if shown["path"] == picture["path"]:
                    self.set_turn(self.gallery.getListItem(index), picture)
            if after:
                after()
        options = [(30047, lambda: change("right")), (30048, lambda: change("left")),
                   (30049, lambda: change("horizontal")), (30056, lambda: change("vertical"))]
        if picture["path"] in self.turns:
            options.append((30057, lambda: change("original")))
        return options

    def selected_picture(self):
        position = self.gallery.getSelectedPosition()
        return self.shown[position] if 0 <= position < len(self.shown) else None

    def focus_gallery(self):
        if self.shown:
            self.setFocusId(GALLERY)

    # Keys

    def onAction(self, action):
        action_id = action.getId()
        focus = self.getFocusId()
        if focus == GALLERY:
            # Left in the first column does not move the selection, so it leads back to the albums.
            previous, self.grid_position = self.grid_position, self.gallery.getSelectedPosition()
            if action_id == ACTION_LEFT and self.grid_position == previous:
                self.setFocusId(GROUPS)
                return
        if action_id in ACTION_BACK:
            if focus == GALLERY:
                self.setFocusId(GROUPS)
            else:
                self.close()
        elif action_id == ACTION_CONTEXT_MENU and focus == GALLERY and self.shown:
            self.picture_menu(self.gallery.getSelectedPosition())
        elif focus == GROUPS and action_id == ACTION_LEFT:
            if self.follow_timer:
                self.follow_timer.cancel()
            self.follow_group()
            self.setFocusId(TOOLBAR)
        elif focus == GROUPS and action_id == ACTION_RIGHT:
            if self.follow_timer:
                self.follow_timer.cancel()
            self.follow_group()
            self.focus_gallery()
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
            self.focus_gallery()
        elif control_id == GALLERY and self.shown:
            self.view(self.gallery.getSelectedPosition())

    # Pictures

    def view(self, position):
        viewer = Viewer("script-easy-picture-viewer.xml", PATH, "default", "1080i")
        viewer.window, viewer.pictures, viewer.position = self, self.shown, position
        viewer.doModal()
        position = viewer.position
        del viewer
        # The gallery follows the picture seen last. A favorite removed in full screen can shorten the album.
        if self.shown:
            position = min(position, len(self.shown) - 1)
            self.gallery.selectItem(position)
            self.grid_position = position

    def picture_menu(self, position):
        picture = self.shown[position]
        favorite = picture["path"] in self.favorites
        options = ([(30040, lambda: self.view(position)),
                    (30043 if favorite else 30042, lambda: self.toggle_favorite(picture))]
                   + self.turn_options(picture) + [(30044, lambda: show_info(picture))])
        choice = xbmcgui.Dialog().contextmenu([text(string_id) for string_id, _ in options])
        if choice >= 0:
            options[choice][1]()

    def toggle_favorite(self, picture):
        if picture["path"] in self.favorites:
            self.favorites.discard(picture["path"])
            notify(text(30046))
        else:
            self.favorites.add(picture["path"])
            notify(text(30045))
        save(FAVORITES_FILE, sorted(self.favorites))
        self.update_favorites(picture)

    def update_favorites(self, picture):
        """Mark the picture in the gallery, and add or remove the Favorites album without scanning the folders again."""
        group = self.groups[self.shown_index]
        position = self.gallery.getSelectedPosition()
        for index, shown in enumerate(self.shown):
            if shown["path"] == picture["path"]:
                self.gallery.getListItem(index).setProperty("favorite", "true" if picture["path"] in self.favorites else "false")
        everything = self.groups[0]["pictures"]
        favorites = [shown for shown in everything if shown["path"] in self.favorites]
        has_album = len(self.groups) > 1 and self.groups[1]["key"] == "favorites"
        if has_album and favorites:
            self.groups[1]["pictures"] = favorites
            self.group_list.getListItem(1).setLabel2(str(len(favorites)))
            if group["key"] == "favorites":
                self.show_group(1, select=min(position, len(favorites) - 1))
            return
        selected = self.group_list.getSelectedPosition()
        if has_album:
            del self.groups[1]
            shift = -1
        elif favorites:
            self.groups.insert(1, {"key": "favorites", "name": text(30002), "pictures": favorites})
            shift = 1
        else:
            return
        items = []
        for entry in self.groups:
            item = xbmcgui.ListItem(entry["name"])
            item.setLabel2(str(len(entry["pictures"])))
            items.append(item)
        self.group_list.reset()
        self.group_list.addItems(items)
        if group["key"] == "favorites":
            # The last favorite was removed while its album was shown.
            self.group_list.selectItem(0)
            self.shown_index = -1
            self.show_group(0)
            self.setFocusId(GROUPS)
        else:
            self.group_list.selectItem(max(selected + shift, 0))
            self.shown_index += shift

    # Tools

    def manage_folders(self):
        while True:
            folders = load(FOLDERS_FILE, [])
            options = [text(30031)] + [text(30032, folder) for folder in folders]
            choice = xbmcgui.Dialog().select(text(30030), options)
            if choice < 0:
                return
            if choice == 0:
                folder = xbmcgui.Dialog().browse(0, text(30033), "pictures")
                if not folder or folder in folders:
                    continue
                folders.append(folder.rstrip("/") if "://" not in folder else folder)
                save(FOLDERS_FILE, folders)
                self.reload()
                notify(text(30034, pictures.name_of(folder)))
                self.focus_gallery()
            elif xbmcgui.Dialog().yesno(TITLE, text(30035, folders[choice - 1]), nolabel=text(30036), yeslabel=text(30037)):
                del folders[choice - 1]
                save(FOLDERS_FILE, folders)
                self.reload()

    def rescan(self):
        keep = self.groups[self.shown_index]["key"] if 0 <= self.shown_index < len(self.groups) else None
        before = len(self.all)
        self.reload(keep)
        notify(text(30038, max(len(self.all) - before, 0)))

    def open_settings(self):
        order = ADDON.getSettingInt("order")
        ADDON.openSettings()
        if ADDON.getSettingInt("order") != order:
            self.reload(self.groups[self.shown_index]["key"] if 0 <= self.shown_index < len(self.groups) else None)


def show_info(picture):
    lines = [(30050, picture["name"]), (30051, pictures.name_of(picture["album"])), (30052, when(picture["time"])),
             (30053, pictures.human_size(picture["size"]) if picture["size"] else "")]
    size = pictures.dimensions(picture["path"]) if "://" not in picture["path"] else None
    if size:
        lines.append((30054, "%d × %d" % size))
    lines.append((30055, picture["album"]))
    xbmcgui.Dialog().ok(picture["name"], "[CR]".join("[COLOR grey]%s:[/COLOR] %s" % (text(string_id), value)
                                                     for string_id, value in lines if value))


class Viewer(xbmcgui.WindowXMLDialog):
    """A picture in full screen. Left and Right move through the pictures of the album, which wrap around."""

    def onInit(self):
        self.hide_timer = None
        self.show()

    def show(self):
        count = len(self.pictures)
        picture = self.pictures[self.position]
        self.setProperty("picture", picture["path"])
        self.window.set_turn(self, picture)
        # The neighbours load behind the picture, so the next move is quick.
        self.getControl(VIEWER_NEXT).setImage(self.pictures[(self.position + 1) % count]["path"], False)
        self.getControl(VIEWER_PREVIOUS).setImage(self.pictures[(self.position - 1) % count]["path"], False)
        favorite = picture["path"] in self.window.favorites
        self.setProperty("name", ("★  " if favorite else "") + picture["name"])
        self.setProperty("album", pictures.name_of(picture["album"]))
        self.setProperty("date", when(picture["time"]))
        self.setProperty("position", "%d / %d" % (self.position + 1, count))
        self.show_details()

    def show_details(self):
        self.setProperty("details", "true")
        if self.hide_timer:
            self.hide_timer.cancel()
        self.hide_timer = threading.Timer(DETAILS_TIME, lambda: self.setProperty("details", "false"))
        self.hide_timer.start()

    def move(self, step):
        self.position = (self.position + step) % len(self.pictures)
        self.show()

    def onAction(self, action):
        action_id = action.getId()
        if action_id in ACTION_BACK:
            if self.hide_timer:
                self.hide_timer.cancel()
            self.close()
        elif action_id == ACTION_RIGHT:
            self.move(1)
        elif action_id == ACTION_LEFT:
            self.move(-1)
        elif action_id in (ACTION_UP, ACTION_DOWN, ACTION_INFO):
            self.show_details()
        elif action_id == ACTION_CONTEXT_MENU:
            picture = self.pictures[self.position]
            favorite = picture["path"] in self.window.favorites
            options = ([(30043 if favorite else 30042, lambda: self.window.toggle_favorite(picture))]
                       + self.window.turn_options(picture) + [(30044, lambda: show_info(picture))])
            choice = xbmcgui.Dialog().contextmenu([text(string_id) for string_id, _ in options])
            if choice >= 0:
                options[choice][1]()
                self.show()

    def onClick(self, control_id):
        self.show_details()


def run():
    window = MainWindow("script-easy-picture-main.xml", PATH, "default", "1080i")
    window.doModal()
    del window
