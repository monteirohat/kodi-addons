"""Lists, video folders, cached playlists, removed channels and metadata, kept in the add-on profile folder."""

import gzip
import json
import os
import tempfile
import time
import urllib.request
import uuid

import xbmcaddon
import xbmcvfs

from resources.lib import folders, github, m3u


ADDON = xbmcaddon.Addon()
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
CACHE = os.path.join(PROFILE, "cache")
LISTS_FILE = os.path.join(PROFILE, "lists.json")
REMOVED_FILE = os.path.join(PROFILE, "removed.json")
FAVORITES_FILE = os.path.join(PROFILE, "favorites.json")
REPOS_FILE = os.path.join(PROFILE, "repositories.json")
PROGRESS_FILE = os.path.join(PROFILE, "progress.json")
METADATA_FILE = os.path.join(PROFILE, "metadata.json")
WATCHLIST_FILE = os.path.join(PROFILE, "watchlist.json")
ADDONS_FILE = os.path.join(PROFILE, "addons.json")
ADDED_FILE = os.path.join(PROFILE, "added.json")
# The catalog title each downloaded video belongs to, by its path: {path: {kind, id, name, poster, year, season, episode}}.
ORIGINS_FILE = os.path.join(PROFILE, "origins.json")
# Share of a movie or episode after which it counts as watched.
WATCHED_AT = 0.9
# Tags found only in the playlist of a single stream, not in a list of channels.
STREAM_TAGS = ("#EXT-X-STREAM-INF", "#EXT-X-TARGETDURATION", "#EXT-X-MEDIA-SEQUENCE")
USER_AGENT = "Kodi/21 Easy Movie"


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as source:
            return json.load(source)
    except (OSError, ValueError):
        return default


def write_bytes(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(prefix=".m3u-channels-", dir=os.path.dirname(path))
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
        os.replace(temporary_path, path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def write_json(path, value):
    write_bytes(path, json.dumps(value, ensure_ascii=False, indent=1).encode("utf-8"))


def get_lists():
    return read_json(LISTS_FILE, [])


def get_list(list_id):
    return next((item for item in get_lists() if item["id"] == list_id), None)


def save_lists(lists):
    write_json(LISTS_FILE, lists)


def download_bytes(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def download(source):
    if source.lower().startswith(("http://", "https://")):
        request = urllib.request.Request(source, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
            if response.headers.get("Content-Encoding") == "gzip" or data[:2] == b"\x1f\x8b":
                data = gzip.decompress(data)
    else:
        source_file = xbmcvfs.File(source)
        try:
            data = bytes(source_file.readBytes())
        finally:
            source_file.close()
        if not data:
            raise OSError("empty or unreadable file")
    text = data.decode("utf-8", errors="replace")
    if any(tag in text for tag in STREAM_TAGS):
        raise ValueError("this is a single stream, not a list of channels")
    if not m3u.parse(text):
        raise ValueError("no channels found")
    return text


class FolderUnavailable(OSError):
    """A video folder that cannot be reached, such as a disconnected drive. Its items stay hidden meanwhile."""


def is_folder(item):
    return item.get("kind") == "folder"


def folder_exists(path):
    return os.path.isdir(path) if path.startswith("/") else xbmcvfs.exists(path.rstrip("/") + "/")


def vfs_walk(root):
    """os.walk for paths that only Kodi can read, such as smb:// shares."""
    folders_to_visit = [root.rstrip("/")]
    while folders_to_visit:
        folder = folders_to_visit.pop(0)
        subfolders, files = xbmcvfs.listdir(folder + "/")
        yield folder, subfolders, files
        folders_to_visit[0:0] = [folder + "/" + name for name in subfolders]


def scan_folder(source):
    if not folder_exists(source):
        raise FolderUnavailable("folder not found: " + source)
    text = folders.scan(source, os.walk if source.startswith("/") else vfs_walk, get_origins())
    if not m3u.parse(text):
        raise ValueError("no videos found")
    return text


def cache_path(list_id):
    return os.path.join(CACHE, list_id + ".m3u")


def refresh(item):
    text = scan_folder(item["source"]) if is_folder(item) else download(item["source"])
    write_bytes(cache_path(item["id"]), text.encode("utf-8"))
    return m3u.parse(text)


def add_list(name, source, kind="m3u"):
    item = {"id": uuid.uuid4().hex[:8], "name": name, "source": source}
    if kind == "folder":
        item["kind"] = "folder"
    channels = refresh(item)
    save_lists(get_lists() + [item])
    return item, channels


def update_list(list_id, **changes):
    lists = get_lists()
    for item in lists:
        if item["id"] == list_id:
            item.update(changes)
    save_lists(lists)


def delete_list(list_id):
    save_lists([item for item in get_lists() if item["id"] != list_id])
    if os.path.exists(cache_path(list_id)):
        os.unlink(cache_path(list_id))


def load_channels(item, max_age_hours):
    """Channels of a list, from cache while fresh. Falls back to the cache when offline.

    A video folder that cannot be reached raises FolderUnavailable instead, so its files are not shown while
    their drive is disconnected. Their progress and favorites stay for when it comes back.

    A folder on this device is scanned every time, which is quick, so new videos such as downloads show at once.
    """
    if is_folder(item) and not folder_exists(item["source"]):
        raise FolderUnavailable("folder not found: " + item["source"])
    path = cache_path(item["id"])
    local_folder = is_folder(item) and item["source"].startswith("/")
    fresh = not local_folder and os.path.exists(path) and time.time() - os.path.getmtime(path) < max_age_hours * 3600
    if not fresh:
        try:
            return refresh(item)
        except Exception:
            if not os.path.exists(path):
                raise
    with open(path, encoding="utf-8") as source:
        return m3u.parse(source.read())


def get_removed():
    return read_json(REMOVED_FILE, {})


def remove_channels(channels, list_id):
    removed = get_removed()
    for channel in channels:
        removed[channel["id"]] = {"name": channel["name"], "list": list_id, "time": int(time.time())}
    write_json(REMOVED_FILE, removed)


def restore_channels(channel_ids):
    removed = get_removed()
    for channel_id in channel_ids:
        removed.pop(channel_id, None)
    write_json(REMOVED_FILE, removed)


def get_favorites():
    """Channel identities in the order they were added to the favorites."""
    return read_json(FAVORITES_FILE, [])


def toggle_favorite(channel_id, aliases=()):
    """Add or remove a favorite. Returns True when the channel is now a favorite. aliases are other identities of the
    same item, as those of series joined into one, which count as it and are removed with it."""
    favorites = get_favorites()
    keys = [channel_id, *aliases]
    added = not any(key in favorites for key in keys)
    if added:
        favorites.append(channel_id)
    else:
        favorites = [favorite for favorite in favorites if favorite not in keys]
    write_json(FAVORITES_FILE, favorites)
    return added


def get_watchlist():
    """Movies and series saved from the Cinemeta catalog, newest first, with their kind and details."""
    return read_json(WATCHLIST_FILE, [])


def toggle_watchlist(kind, meta):
    """Add a catalog title to My list, or remove it. Returns True when it is now in the list."""
    watchlist = get_watchlist()
    kept = [item for item in watchlist if item["id"] != meta["id"]]
    added = len(kept) == len(watchlist)
    if added:
        kept.insert(0, dict(meta, kind=kind))
    write_json(WATCHLIST_FILE, kept)
    return added


def get_addons():
    """Stremio addons added by the user, in the order added, with their manifest address and manifest."""
    return read_json(ADDONS_FILE, [])


def save_addon(url, manifest):
    """Add an addon, or replace the one with the same id, as when it is configured again with other options."""
    addons = [addon for addon in get_addons() if addon["manifest"]["id"] != manifest["id"] and addon["url"] != url]
    position = next((index for index, addon in enumerate(get_addons()) if addon["manifest"]["id"] == manifest["id"]),
                    len(addons))
    addons.insert(position, {"url": url, "manifest": manifest})
    write_json(ADDONS_FILE, addons)


def remove_addon(url):
    write_json(ADDONS_FILE, [addon for addon in get_addons() if addon["url"] != url])


def get_repos():
    """GitHub repositories to search. The defaults apply until the first change."""
    return read_json(REPOS_FILE, [dict(repo) for repo in github.DEFAULT_REPOS])


def save_repos(repos):
    write_json(REPOS_FILE, repos)


def get_progress():
    """Playback state by item identity: position and total in seconds, watched, and time of last change."""
    return read_json(PROGRESS_FILE, {})


def save_progress(item_id, position, total):
    progress = get_progress()
    watched = total > 0 and position >= total * WATCHED_AT
    progress[item_id] = {"position": 0 if watched else int(position), "total": int(total),
                         "watched": watched or progress.get(item_id, {}).get("watched", False), "time": int(time.time())}
    write_json(PROGRESS_FILE, progress)
    return progress[item_id]


def get_origins():
    return read_json(ORIGINS_FILE, {})


def save_origins(changes):
    origins = get_origins()
    origins.update(changes)
    write_json(ORIGINS_FILE, origins)


def get_metadata():
    """Cinemeta details by catalog item identity. An empty dict marks an item that had no match."""
    return read_json(METADATA_FILE, {})


def save_metadata(changes):
    """Merge details into the metadata file. A value of None removes an item, so it is looked up again."""
    metadata = get_metadata()
    for key, value in changes.items():
        if value is None:
            metadata.pop(key, None)
        else:
            metadata[key] = value
    write_json(METADATA_FILE, metadata)


def added_times(movies):
    """When each movie first appeared in the lists, by id, for showing the newest first. movies are pairs of id
    and whether it is a video of a folder.

    The first time, videos of folders on this device take the date of their file and the others 0, so the lists
    keep their order. Movies that appear later take the time they appeared."""
    added = read_json(ADDED_FILE, None)
    first, added = added is None, added or {}
    now, changed = int(time.time()), False
    for movie_id, folder in movies:
        if movie_id in added:
            continue
        added[movie_id], changed = now, True
        if first:
            added[movie_id] = 0
            if folder and movie_id.startswith("/"):
                try:
                    added[movie_id] = int(os.path.getmtime(movie_id))
                except OSError:
                    pass
    if changed:
        write_json(ADDED_FILE, added)
    return added


def move_item(old_id, new_id):
    """Keep progress, favorites, metadata and the time added of a file that was renamed."""
    progress = get_progress()
    if old_id in progress:
        progress[new_id] = progress.pop(old_id)
        write_json(PROGRESS_FILE, progress)
    favorites = get_favorites()
    if old_id in favorites:
        favorites[favorites.index(old_id)] = new_id
        write_json(FAVORITES_FILE, favorites)
    metadata = get_metadata()
    if old_id in metadata:
        metadata[new_id] = metadata.pop(old_id)
        write_json(METADATA_FILE, metadata)
    added = read_json(ADDED_FILE, {})
    if old_id in added:
        added[new_id] = added.pop(old_id)
        write_json(ADDED_FILE, added)
