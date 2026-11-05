"""File manager window: places on the left, the folder shown on the right, and the options of each item."""

import json
import os
import threading
import time
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import files


ADDON = xbmcaddon.Addon()
TITLE = ADDON.getAddonInfo("name")
PATH = ADDON.getAddonInfo("path")
MEDIA = os.path.join(PATH, "resources", "skins", "default", "media")
ACTION_LEFT, ACTION_RIGHT = 1, 2
ACTION_BACK = (10, 92)
ACTION_CONTEXT_MENU = 117
PLACES, ITEMS = 200, 300
FOLDER_TITLE, FOLDER_PATH, FOLDER_COUNT, FOLDER_EMPTY = 401, 402, 403, 404
INFO_CLOSE = 201
# Folders where drives are mounted, by system: LibreELEC, most Linux systems, and others.
MOUNT_FOLDERS = ("/var/media", "/media", "/mnt", "/run/media")
CHUNK = 1024 * 1024
ICONS = {"folder": "folder.png", "video": "video.png", "audio": "audio.png", "image": "image.png", "archive": "archive.png",
         "text": "text.png", "file": "file.png", "drive": "drive.png", "home": "home.png", "network": "network.png",
         "kodi": "kodi.png"}


def text(string_id, *arguments):
    return ADDON.getLocalizedString(string_id).format(*arguments)


def notify(message):
    xbmcgui.Dialog().notification(TITLE, message, ADDON.getAddonInfo("icon"), 3000)


def icon(name):
    return os.path.join(MEDIA, ICONS[name])


def busy(active):
    xbmc.executebuiltin("ActivateWindow(busydialognocancel)" if active else "Dialog.Close(busydialognocancel)")


def is_local(path):
    return "://" not in path


def free_space(path):
    """Free bytes of the drive that holds a local path, or None."""
    if not is_local(path):
        return None
    try:
        stat = os.statvfs(path)
    except OSError:
        return None
    return stat.f_bavail * stat.f_frsize


def rpc(method, **params):
    request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    return json.loads(xbmc.executeJSONRPC(json.dumps(request))).get("result") or {}


def places():
    """Places on the left: the home folder, mounted drives, and the file sources of Kodi, without repeats."""
    found, seen = [], set()

    def add(name, path, kind):
        # The real path, as /media is a link to /var/media on LibreELEC.
        key = (os.path.realpath(path) if is_local(path) else path).rstrip("/") or "/"
        if key not in seen and (not is_local(path) or os.path.isdir(path)):
            seen.add(key)
            found.append({"name": name, "path": path, "kind": kind})

    add(text(30010), os.path.expanduser("~"), "home")
    for folder in MOUNT_FOLDERS:
        if os.path.isdir(folder):
            for name in sorted(os.listdir(folder), key=files.sort_key):
                path = os.path.join(folder, name)
                if os.path.ismount(path) or folder == "/var/media":
                    add(name, path, "drive")
    for source in rpc("Files.GetSources", media="files").get("sources", []):
        path = source.get("file", "")
        if path and not path.startswith(("addons://", "special://")):
            add(source.get("label") or files.name_of(path), path, "drive" if is_local(path) else "network")
    add(text(30011), xbmcvfs.translatePath("special://home"), "kodi")
    return found


def stat(path):
    try:
        info = xbmcvfs.Stat(path)
        return info.st_size(), info.st_mtime()
    except Exception:
        return 0, 0


def listing(folder):
    """The folders and files of a folder, folders first, in natural order."""
    show_hidden = ADDON.getSettingBool("show_hidden")
    dirs, names = xbmcvfs.listdir(folder if folder.endswith("/") else folder + "/")
    entries = []
    for name in dirs:
        if show_hidden or not name.startswith("."):
            path = files.join(folder, name)
            entries.append({"name": name, "path": path, "folder": True, "kind": "folder", "size": 0, "time": stat(path)[1]})
    for name in names:
        if show_hidden or not name.startswith("."):
            path = files.join(folder, name)
            size, modified = stat(path)
            entries.append({"name": name, "path": path, "folder": False, "kind": files.kind(name), "size": size, "time": modified})
    entries.sort(key=lambda entry: (not entry["folder"], files.sort_key(entry["name"])))
    return entries


def when(seconds):
    return time.strftime("%d/%m/%Y %H:%M", time.localtime(seconds)) if seconds else ""


class MainWindow(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.places, self.entries = [], []
        self.place = None
        self.folder = None
        # Copied or cut item: {"path", "name", "folder", "move"}.
        self.clipboard = None

    def onInit(self):
        self.place_list = self.getControl(PLACES)
        self.item_list = self.getControl(ITEMS)
        self.show_places()
        self.setFocusId(PLACES)

    # Places and folders

    def show_places(self):
        self.places = places()
        items = []
        for place in self.places:
            item = xbmcgui.ListItem(place["name"])
            free = free_space(place["path"])
            item.setLabel2(text(30012, files.human_size(free)) if free is not None else "")
            item.setArt({"icon": icon(place["kind"])})
            items.append(item)
        self.place_list.reset()
        self.place_list.addItems(items)
        if self.places and self.folder is None:
            self.open_place(0)

    def open_place(self, index):
        self.place = self.places[index]
        self.open_folder(self.place["path"])

    def open_folder(self, folder, select=None):
        busy(True)
        try:
            entries = listing(folder)
        except Exception as error:
            busy(False)
            xbmcgui.Dialog().ok(TITLE, text(30040, error))
            return False
        busy(False)
        self.folder, self.entries = folder, entries
        items = []
        for entry in entries:
            item = xbmcgui.ListItem(entry["name"])
            details = [] if entry["folder"] else [files.human_size(entry["size"])]
            if entry["time"]:
                details.append(when(entry["time"]))
            item.setLabel2("  ·  ".join(details))
            item.setArt({"icon": icon(entry["kind"])})
            items.append(item)
        self.item_list.reset()
        self.item_list.addItems(items)
        names = [entry["name"] for entry in entries]
        if select in names:
            self.item_list.selectItem(names.index(select))
        self.getControl(FOLDER_TITLE).setLabel(self.folder_name())
        self.getControl(FOLDER_PATH).setLabel(folder)
        folders = sum(1 for entry in entries if entry["folder"])
        self.getControl(FOLDER_COUNT).setLabel(text(30013, folders, len(entries) - folders))
        self.getControl(FOLDER_EMPTY).setLabel("" if entries else text(30014))
        self.update_clipboard()
        return True

    def folder_name(self):
        """The name of the folder shown. At the top of a place, the name of the place."""
        if self.place and self.folder.rstrip("/") == self.place["path"].rstrip("/"):
            return self.place["name"]
        return files.name_of(self.folder)

    def go_up(self):
        """The folder above, or the places at the top of a place."""
        top = not self.place or self.folder.rstrip("/") == self.place["path"].rstrip("/")
        above = None if top else files.parent(self.folder)
        if above is None:
            self.setFocusId(PLACES)
            return
        self.open_folder(above, select=files.name_of(self.folder))

    def refresh(self, select=None):
        position = self.item_list.getSelectedPosition()
        if self.open_folder(self.folder, select) and select is None and self.entries:
            self.item_list.selectItem(min(max(position, 0), len(self.entries) - 1))
        self.show_places_free_space()
        # An empty folder leaves the focus on the places. After a change the folder has items to focus again.
        if self.entries:
            self.setFocusId(ITEMS)

    def show_places_free_space(self):
        for index, place in enumerate(self.places):
            free = free_space(place["path"])
            self.place_list.getListItem(index).setLabel2(text(30012, files.human_size(free)) if free is not None else "")

    def selected_entry(self):
        position = self.item_list.getSelectedPosition()
        return self.entries[position] if 0 <= position < len(self.entries) else None

    # Keys

    def onAction(self, action):
        action_id = action.getId()
        focus = self.getFocusId()
        if action_id in ACTION_BACK:
            if focus == ITEMS:
                self.go_up()
            else:
                self.close()
        elif action_id == ACTION_CONTEXT_MENU:
            if focus == ITEMS and self.entries:
                self.item_menu(self.selected_entry())
            elif focus in (ITEMS, PLACES) and self.folder:
                self.folder_menu()
        elif focus == PLACES and action_id == ACTION_RIGHT and self.entries:
            self.setFocusId(ITEMS)
        elif focus == ITEMS and action_id == ACTION_LEFT:
            self.setFocusId(PLACES)

    def onClick(self, control_id):
        if control_id == PLACES:
            index = self.place_list.getSelectedPosition()
            if 0 <= index < len(self.places):
                self.open_place(index)
                if self.entries:
                    self.setFocusId(ITEMS)
        elif control_id == ITEMS:
            entry = self.selected_entry()
            if entry:
                self.open_entry(entry)

    def open_entry(self, entry):
        if entry["folder"]:
            if self.open_folder(entry["path"]) and self.entries:
                self.item_list.selectItem(0)
        elif entry["kind"] in ("video", "audio"):
            xbmc.Player().play(entry["path"])
        elif entry["kind"] == "image":
            xbmc.executebuiltin("ShowPicture(%s)" % entry["path"])
        elif entry["kind"] == "archive" and entry["name"].lower().endswith(".zip"):
            # Kodi opens a ZIP file as a folder.
            self.open_folder("zip://%s/" % urllib.parse.quote(entry["path"], safe=""))
        elif entry["kind"] == "text":
            self.show_text(entry)
        else:
            self.show_info(entry)

    # Options

    def item_menu(self, entry):
        options = [(30020, lambda: self.open_entry(entry)), (30021, lambda: self.show_info(entry)),
                   (30022, lambda: self.rename(entry)), (30023, lambda: self.copy(entry, False)),
                   (30024, lambda: self.copy(entry, True)), (30025, lambda: self.delete(entry)),
                   (30026, self.new_folder)]
        if self.clipboard:
            options.insert(1, (30027, self.paste))
        choice = xbmcgui.Dialog().contextmenu([text(string_id) for string_id, _ in options])
        if choice >= 0:
            options[choice][1]()

    def folder_menu(self):
        """Options of the folder shown, when it is empty or a place is selected."""
        options = [(30026, self.new_folder), (30021, lambda: self.show_info(self.folder_entry()))]
        if self.clipboard:
            options.insert(0, (30027, self.paste))
        choice = xbmcgui.Dialog().contextmenu([text(string_id) for string_id, _ in options])
        if choice >= 0:
            options[choice][1]()

    def folder_entry(self):
        return {"name": self.folder_name(), "path": self.folder, "folder": True, "kind": "folder", "size": 0,
                "time": stat(self.folder)[1]}

    def rename(self, entry):
        name = xbmcgui.Dialog().input(text(30030), entry["name"]).strip()
        if not name or name == entry["name"]:
            return
        if not files.valid_name(name):
            xbmcgui.Dialog().ok(TITLE, text(30041))
            return
        target = files.join(self.folder, name)
        if xbmcvfs.exists(target if not entry["folder"] else target + "/"):
            xbmcgui.Dialog().ok(TITLE, text(30042, name))
            return
        if xbmcvfs.rename(entry["path"], target):
            notify(text(30031))
            self.refresh(select=name)
        else:
            xbmcgui.Dialog().ok(TITLE, text(30043))

    def copy(self, entry, move):
        self.clipboard = dict(entry, move=move)
        notify(text(30033 if move else 30032, entry["name"]))
        self.update_clipboard()

    def update_clipboard(self):
        clipboard = self.clipboard
        self.setProperty("clipboard", text(30035 if clipboard["move"] else 30034, clipboard["name"]) if clipboard else "")

    def paste(self):
        clipboard = self.clipboard
        if not clipboard:
            return
        if clipboard["folder"] and (self.folder.rstrip("/") + "/").startswith(clipboard["path"].rstrip("/") + "/"):
            # A folder cannot go into itself.
            xbmcgui.Dialog().ok(TITLE, text(30044))
            return
        taken = {entry["name"] for entry in self.entries}
        name = clipboard["name"]
        if name in taken:
            if files.parent(clipboard["path"]) == self.folder and not clipboard["move"]:
                name = files.free_name(name, taken)
            else:
                answer = xbmcgui.Dialog().yesnocustom(TITLE, text(30036, name), customlabel=text(30038),
                                                      nolabel=text(30039), yeslabel=text(30037))
                if answer == 1:
                    self.remove(files.join(self.folder, name), any(e["folder"] for e in self.entries if e["name"] == name))
                elif answer == 2:
                    name = files.free_name(name, taken)
                else:
                    return
        target = files.join(self.folder, name)
        done = False
        if clipboard["move"] and xbmcvfs.rename(clipboard["path"], target):
            done = True
        else:
            done = self.transfer(clipboard, target)
            if done and clipboard["move"]:
                self.remove(clipboard["path"], clipboard["folder"])
        if done:
            if clipboard["move"]:
                self.clipboard = None
            notify(text(30046 if clipboard["move"] else 30045, name))
        self.refresh(select=name)

    def transfer(self, source, target):
        """Copy a file or a folder with its contents, showing the progress. Returns False when cancelled or failed."""
        busy(True)
        jobs, total = self.plan(source["path"], target, source["folder"])
        busy(False)
        progress = xbmcgui.DialogProgress()
        progress.create(TITLE, text(30047, source["name"]))
        copied = 0
        try:
            for kind, from_path, to_path, size in jobs:
                if progress.iscanceled():
                    return False
                if kind == "folder":
                    xbmcvfs.mkdirs(to_path)
                    continue
                progress.update(int(copied * 100 / total) if total else 0, text(30048, files.name_of(from_path)))
                copied = self.copy_file(from_path, to_path, copied, total, progress)
                if copied is None:
                    xbmcvfs.delete(to_path)
                    return False
            return True
        except Exception as error:
            xbmcgui.Dialog().ok(TITLE, text(30049, error))
            return False
        finally:
            progress.close()

    def plan(self, source, target, folder):
        """The folders to create and the files to copy, in order, and their total size."""
        if not folder:
            size = stat(source)[0]
            return [("file", source, target, size)], size
        jobs, total = [("folder", source, target, 0)], 0
        dirs, names = xbmcvfs.listdir(source.rstrip("/") + "/")
        for name in dirs:
            sub_jobs, sub_total = self.plan(files.join(source, name), files.join(target, name), True)
            jobs += sub_jobs
            total += sub_total
        for name in names:
            path = files.join(source, name)
            size = stat(path)[0]
            jobs.append(("file", path, files.join(target, name), size))
            total += size
        return jobs, total

    def copy_file(self, source, target, copied, total, progress):
        """Copy one file in chunks. Returns the bytes copied so far, or None when cancelled."""
        reader, writer = xbmcvfs.File(source), xbmcvfs.File(target, "w")
        try:
            while True:
                data = reader.readBytes(CHUNK)
                if not data:
                    return copied
                if not writer.write(data):
                    raise IOError(text(30050, files.name_of(target)))
                copied += len(data)
                if progress.iscanceled():
                    return None
                progress.update(int(copied * 100 / total) if total else 100)
        finally:
            reader.close()
            writer.close()

    def delete(self, entry):
        message = text(30052 if entry["folder"] else 30051, entry["name"])
        if not xbmcgui.Dialog().yesno(TITLE, message, nolabel=text(30039), yeslabel=text(30025)):
            return
        busy(True)
        removed = self.remove(entry["path"], entry["folder"])
        busy(False)
        if removed:
            if self.clipboard and self.clipboard["path"] == entry["path"]:
                self.clipboard = None
            notify(text(30053, entry["name"]))
        else:
            xbmcgui.Dialog().ok(TITLE, text(30054, entry["name"]))
        self.refresh()

    def remove(self, path, folder):
        """Delete a file, or a folder with everything in it."""
        if not folder:
            return xbmcvfs.delete(path)
        dirs, names = xbmcvfs.listdir(path.rstrip("/") + "/")
        for name in names:
            xbmcvfs.delete(files.join(path, name))
        for name in dirs:
            self.remove(files.join(path, name), True)
        return xbmcvfs.rmdir(path.rstrip("/") + "/")

    def new_folder(self):
        name = xbmcgui.Dialog().input(text(30055)).strip()
        if not name:
            return
        if not files.valid_name(name):
            xbmcgui.Dialog().ok(TITLE, text(30041))
            return
        if name in {entry["name"] for entry in self.entries}:
            xbmcgui.Dialog().ok(TITLE, text(30042, name))
            return
        if xbmcvfs.mkdir(files.join(self.folder, name)):
            self.refresh(select=name)
        else:
            xbmcgui.Dialog().ok(TITLE, text(30043))

    def show_text(self, entry):
        reader = xbmcvfs.File(entry["path"])
        try:
            data = reader.readBytes(files.TEXT_PREVIEW)
        finally:
            reader.close()
        content = bytes(data).decode("utf-8", errors="replace")
        if entry["size"] > files.TEXT_PREVIEW:
            content += "\n\n" + text(30056)
        xbmcgui.Dialog().textviewer(entry["name"], content)

    def show_info(self, entry):
        info = InfoDialog("script-easy-files-info.xml", PATH, "default", "1080i")
        info.entry = entry
        info.doModal()
        del info


class InfoDialog(xbmcgui.WindowXMLDialog):
    """Details of a file or folder. The size of a folder is added up in the background."""

    def onInit(self):
        entry = self.entry
        self.closed = False
        self.setProperty("icon", icon(entry["kind"]))
        self.setProperty("name", entry["name"])
        self.setProperty("kind", text({"folder": 30060, "video": 30061, "audio": 30062, "image": 30063, "archive": 30064,
                                       "text": 30065}.get(entry["kind"], 30066)))
        self.setProperty("place", files.parent(entry["path"]) or entry["path"])
        self.setProperty("modified", when(entry["time"]))
        free = free_space(entry["path"] if entry["folder"] else (files.parent(entry["path"]) or entry["path"]))
        self.setProperty("free", files.human_size(free) if free is not None else "")
        if entry["folder"]:
            self.setProperty("size", text(30067))
            threading.Thread(target=self.measure, daemon=True).start()
        else:
            self.setProperty("size", "%s  (%s bytes)" % (files.human_size(entry["size"]), format(entry["size"], ",").replace(",", ".")))
        self.setFocusId(INFO_CLOSE)

    def measure(self):
        size, folders, count = 0, 0, 0
        pending = [self.entry["path"]]
        while pending and not self.closed:
            folder = pending.pop()
            try:
                dirs, names = xbmcvfs.listdir(folder.rstrip("/") + "/")
            except Exception:
                continue
            folders += len(dirs)
            count += len(names)
            pending += [files.join(folder, name) for name in dirs]
            size += sum(stat(files.join(folder, name))[0] for name in names)
            self.setProperty("size", text(30068, files.human_size(size)))
            self.setProperty("contents", text(30013, folders, count))
        if not self.closed:
            self.setProperty("size", "%s  (%s bytes)" % (files.human_size(size), format(size, ",").replace(",", ".")))

    def onAction(self, action):
        if action.getId() in ACTION_BACK:
            self.closed = True
            self.close()

    def onClick(self, control_id):
        if control_id == INFO_CLOSE:
            self.closed = True
            self.close()


def run():
    window = MainWindow("script-easy-files-main.xml", PATH, "default", "1080i")
    window.doModal()
    del window
