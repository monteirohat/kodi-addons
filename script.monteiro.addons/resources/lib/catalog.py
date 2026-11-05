"""The add-ons of the repositories, read from the add-on database of Kodi, with the category of each one.

Does not import Kodi modules, so it can be tested with a regular Python 3 interpreter on a copy of the database.
"""

import glob
import json
import os
import re
import sqlite3

# Kinds that only other add-ons use. Kodi does not list them either.
HIDDEN = {"xbmc.python.module", "xbmc.python.library", "kodi.game.controller"}
# Categories, as string ids of Kodi, so they follow the language of Kodi.
VIDEO, MUSIC, PICTURES, PROGRAMS, LOOK_AND_FEEL = 1037, 1038, 1039, 1043, 24997
CATEGORIES = {
    "xbmc.gui.skin": LOOK_AND_FEEL, "kodi.resource.language": LOOK_AND_FEEL, "kodi.resource.images": LOOK_AND_FEEL,
    "kodi.resource.uisounds": LOOK_AND_FEEL, "kodi.resource.font": LOOK_AND_FEEL, "xbmc.ui.screensaver": LOOK_AND_FEEL,
    "xbmc.player.musicviz": LOOK_AND_FEEL, "xbmc.service": 14036, "xbmc.addon.repository": 24011, "xbmc.python.weather": 8,
    "xbmc.subtitle.module": 287, "xbmc.python.lyrics": 24013, "kodi.gameclient": 35049, "kodi.pvrclient": 19279,
    "kodi.audiodecoder": 201, "kodi.audioencoder": 200, "xbmc.webinterface": 199, "kodi.context.item": 24025,
}
PROVIDES = (("video", VIDEO), ("audio", MUSIC), ("image", PICTURES), ("executable", PROGRAMS), ("game", PROGRAMS))
OTHER = 24001  # Add-ons


def database(folder):
    """The newest add-on database of Kodi in its Database folder."""
    found = glob.glob(os.path.join(folder, "Addons*.db"))
    return max(found, key=lambda path: int(re.sub(r"\D", "", os.path.basename(path)) or 0)) if found else None


def category(kind, provides):
    if kind in ("xbmc.python.pluginsource", "xbmc.python.script"):
        for name, string_id in PROVIDES:
            if name in provides:
                return string_id
        return PROGRAMS
    if kind.startswith("xbmc.metadata.scraper."):
        return 21412
    return CATEGORIES.get(kind, OTHER)


def version_key(version):
    """Order of versions: 1.10.0 after 1.9.2. Text such as ~beta1 sorts before the release."""
    parts = []
    for part in re.split(r"[.+~-]", version):
        parts.append((1, int(part), "") if part.isdigit() else (0, 0, part))
    return parts


def newer(available, installed):
    return bool(installed) and version_key(available) > version_key(installed)


def read(path):
    """Repositories and their add-ons: [{"id", "name", "addons": [...]}], newest version of each add-on per repository.

    The database is opened read only, so Kodi keeps using it while the add-on reads it."""
    connection = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    try:
        installed = {row[0] for row in connection.execute("SELECT addonID FROM installed")}
        rows = connection.execute(
            "SELECT r.addonID, a.addonID, a.name, a.summary, a.version, a.metadata, a.description FROM addonlinkrepo l "
            "JOIN repo r ON r.id = l.idRepo JOIN addons a ON a.id = l.idAddon").fetchall()
        names = dict(connection.execute(
            "SELECT addonID, name FROM addons WHERE addonID IN (SELECT addonID FROM repo)").fetchall())
    finally:
        connection.close()
    repositories = {}
    for repo_id, addon_id, name, summary, version, metadata, description in rows:
        try:
            info = json.loads(metadata)
        except (TypeError, ValueError):
            info = {}
        extensions = [extension.get("type", "") for extension in info.get("extensions", [])]
        kind = next((extension for extension in extensions if extension != "xbmc.addon.metadata"), "")
        if not kind or kind in HIDDEN:
            continue
        provides = " ".join(item.get("value", "") for item in info.get("extrainfo", []) if item.get("key") == "provides")
        addons = repositories.setdefault(repo_id, {})
        known = addons.get(addon_id)
        if known and version_key(known["version"]) >= version_key(version):
            continue
        addons[addon_id] = {"id": addon_id, "name": name, "summary": summary, "version": version, "repository": repo_id,
                            "category": category(kind, provides), "icon": info.get("icon", ""),
                            "installed": addon_id in installed, "kind": kind, "description": description or summary,
                            "author": info.get("author", ""), "screenshots": info.get("screenshots", []),
                            "fanart": (info.get("art") or {}).get("fanart", "")}
    result = []
    for repo_id, addons in repositories.items():
        result.append({"id": repo_id, "name": names.get(repo_id, repo_id),
                       "addons": sorted(addons.values(), key=lambda addon: addon["name"].lower())})
    return sorted(result, key=lambda repository: repository["name"].lower())


def matches(addon, words):
    text = ("%s %s %s" % (addon["name"], addon["summary"], addon["id"])).lower()
    return all(word in text for word in words)
