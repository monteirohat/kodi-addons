"""Lists, cached playlists and removed channels, kept in the add-on profile folder."""

import gzip
import json
import os
import tempfile
import time
import urllib.request
import uuid

import xbmcaddon
import xbmcvfs

from resources.lib import github, m3u


ADDON = xbmcaddon.Addon()
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
CACHE = os.path.join(PROFILE, "cache")
LISTS_FILE = os.path.join(PROFILE, "lists.json")
REMOVED_FILE = os.path.join(PROFILE, "removed.json")
FAVORITES_FILE = os.path.join(PROFILE, "favorites.json")
GROUP_NAMES_FILE = os.path.join(PROFILE, "group_names.json")
REPOS_FILE = os.path.join(PROFILE, "repositories.json")
# Tags found only in the playlist of a single stream, not in a list of channels.
STREAM_TAGS = ("#EXT-X-STREAM-INF", "#EXT-X-TARGETDURATION", "#EXT-X-MEDIA-SEQUENCE")
USER_AGENT = "Kodi/21 Easy Channel"


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


def cache_path(list_id):
    return os.path.join(CACHE, list_id + ".m3u")


def refresh(item):
    text = download(item["source"])
    write_bytes(cache_path(item["id"]), text.encode("utf-8"))
    return m3u.parse(text)


def add_list(name, source):
    item = {"id": uuid.uuid4().hex[:8], "name": name, "source": source}
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
    """Channels of a list, from cache while fresh. Falls back to the cache when offline."""
    path = cache_path(item["id"])
    fresh = os.path.exists(path) and time.time() - os.path.getmtime(path) < max_age_hours * 3600
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


def get_group_names():
    """Names given to groups, by the group name of the lists."""
    return read_json(GROUP_NAMES_FILE, {})


def rename_group(shown, new):
    """Show the group named shown as new, and every group of the lists that is shown under that name.

    The lists keep their own names, so a renamed group keeps its name when a list is downloaded again. A group
    renamed to the name of another group joins it."""
    names = get_group_names()
    for original, name in list(names.items()):
        if name == shown:
            names[original] = new
    names.setdefault(shown, new)
    write_json(GROUP_NAMES_FILE, {original: name for original, name in names.items() if original != name})


def restore_channels(channel_ids):
    removed = get_removed()
    for channel_id in channel_ids:
        removed.pop(channel_id, None)
    write_json(REMOVED_FILE, removed)


def get_favorites():
    """Channel identities in the order they were added to the favorites."""
    return read_json(FAVORITES_FILE, [])


def toggle_favorite(channel_id):
    """Add or remove a favorite. Returns True when the channel is now a favorite."""
    favorites = get_favorites()
    added = channel_id not in favorites
    if added:
        favorites.append(channel_id)
    else:
        favorites.remove(channel_id)
    write_json(FAVORITES_FILE, favorites)
    return added


def get_repos():
    """GitHub repositories to search. The defaults apply until the first change."""
    return read_json(REPOS_FILE, [dict(repo) for repo in github.DEFAULT_REPOS])


def save_repos(repos):
    write_json(REPOS_FILE, repos)
