"""Names, kinds, sizes and order of files. Free of Kodi imports so it can be tested anywhere."""

import posixpath
import re

KINDS = {
    "video": {".mkv", ".mp4", ".m4v", ".avi", ".mov", ".wmv", ".mpg", ".mpeg", ".ts", ".m2ts", ".webm", ".flv", ".3gp", ".vob"},
    "audio": {".mp3", ".flac", ".aac", ".m4a", ".ogg", ".oga", ".opus", ".wav", ".wma", ".alac", ".ape"},
    "image": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".heic"},
    "archive": {".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".bz2", ".xz"},
    "text": {".txt", ".log", ".xml", ".nfo", ".srt", ".sub", ".ass", ".ssa", ".vtt", ".json", ".m3u", ".m3u8", ".ini", ".conf",
             ".cfg", ".py", ".md", ".csv", ".po"},
}
# Text files larger than this open only in part, as the viewer shows text at once.
TEXT_PREVIEW = 200 * 1024
UNITS = ("B", "KB", "MB", "GB", "TB")


def kind(name):
    """The kind of a file by its extension: video, audio, image, archive, text, or file."""
    extension = posixpath.splitext(name)[1].lower()
    return next((kind_name for kind_name, extensions in KINDS.items() if extension in extensions), "file")


def human_size(size):
    """A size in bytes as text, as in "1.4 GB"."""
    value = float(size)
    for unit in UNITS:
        if value < 1024 or unit == UNITS[-1]:
            return ("%d %s" if unit == "B" else "%.1f %s") % (value, unit)
        value /= 1024


def sort_key(name):
    """Natural order: "Episode 2" comes before "Episode 10", without regard to case."""
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", name)]


def join(folder, name):
    """A path inside a folder, local or a Kodi address such as smb://."""
    return folder + name if folder.endswith("/") else folder + "/" + name


def parent(path):
    """The folder that holds a path, or None at the top of a drive or share."""
    stripped = path.rstrip("/")
    if not stripped:
        return None
    if "://" in stripped:
        scheme, rest = stripped.split("://", 1)
        if "/" not in rest:
            return None
        return scheme + "://" + rest.rsplit("/", 1)[0] + "/"
    head = posixpath.dirname(stripped)
    return head or "/"


def name_of(path):
    stripped = path.rstrip("/")
    return stripped.rsplit("/", 1)[-1] if "/" in stripped else stripped


def free_name(name, taken):
    """A name not in taken, adding a number as in "Movie (2).mkv"."""
    if name not in taken:
        return name
    stem, extension = posixpath.splitext(name)
    if not extension or stem == "":
        stem, extension = name, ""
    number = 2
    while "%s (%d)%s" % (stem, number, extension) in taken:
        number += 1
    return "%s (%d)%s" % (stem, number, extension)


def valid_name(name):
    """Whether a new name can be used for a file or folder."""
    return bool(name.strip()) and name not in (".", "..") and "/" not in name and "\\" not in name
