"""Pictures: which files are pictures, their order, sizes and dimensions, and the names of albums.

Does not import Kodi modules, so it can be tested with a regular Python 3 interpreter.
"""

import os
import re
import struct

EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".heic")
# Artwork that music and video players leave in folders, not photos.
ARTWORK = re.compile(r"^(folder|cover|front|back|albumart.*|poster|fanart|banner|thumb|landscape|clearlogo|clearart|disc)"
                     r"\.[a-z]+$", re.IGNORECASE)


def is_picture(name):
    return (name.lower().endswith(EXTENSIONS) and not name.startswith(".") and not ARTWORK.match(name))


def sort_key(name):
    """Natural order: IMG_2 before IMG_10, without regard to case."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", name)]


def human_size(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return ("%d %s" if unit == "B" else "%.1f %s") % (size, unit)
        size /= 1024.0


def name_of(path):
    return path.rstrip("/").replace("\\", "/").split("/")[-1] or path


def parent(path):
    trimmed = path.rstrip("/")
    return trimmed[:trimmed.rfind("/")] if "/" in trimmed else ""


def album_names(folders):
    """Names of the albums, which are folders: their own name, with the folder above it when two have the same name."""
    counts = {}
    for folder in folders:
        counts[name_of(folder)] = counts.get(name_of(folder), 0) + 1
    names = {}
    for folder in folders:
        name = name_of(folder)
        names[folder] = "%s (%s)" % (name, name_of(parent(folder))) if counts[name] > 1 and parent(folder) else name
    return names


def dimensions(path):
    """Width and height of a local JPEG, PNG, GIF, BMP or WebP file, read from its header, or None."""
    try:
        with open(path, "rb") as data:
            head = data.read(32)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", head[16:24])
            if head[:6] in (b"GIF87a", b"GIF89a"):
                return struct.unpack("<HH", head[6:10])
            if head[:2] == b"BM":
                width, height = struct.unpack("<ii", head[18:26])
                return width, abs(height)
            if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
                return _webp(head, data)
            if head[:2] == b"\xff\xd8":
                return _jpeg(data)
    except (OSError, struct.error):
        pass
    return None


def _webp(head, data):
    data.seek(12)
    chunk = data.read(30)
    kind = chunk[:4]
    if kind == b"VP8 ":
        width, height = struct.unpack("<HH", chunk[14:18])
        return width & 0x3FFF, height & 0x3FFF
    if kind == b"VP8L":
        bits = struct.unpack("<I", chunk[9:13])[0]
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if kind == b"VP8X":
        width = int.from_bytes(chunk[12:15], "little") + 1
        height = int.from_bytes(chunk[15:18], "little") + 1
        return width, height
    return None


def _jpeg(data):
    """Walk the markers of a JPEG file to its frame header. Turned photos keep their stored size."""
    data.seek(2)
    while True:
        marker = data.read(2)
        if len(marker) < 2 or marker[0] != 0xFF:
            return None
        kind = marker[1]
        if kind in (0xD8, 0x01) or 0xD0 <= kind <= 0xD7:
            continue
        length = struct.unpack(">H", data.read(2))[0]
        if 0xC0 <= kind <= 0xCF and kind not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">xHH", data.read(5))
            return width, height
        data.seek(length - 2, os.SEEK_CUR)
