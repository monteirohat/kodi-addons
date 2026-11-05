"""Songs: which files are songs, their title, artist, album and number, their order, and the cover of a folder.

Does not import Kodi modules, so it can be tested with a regular Python 3 interpreter.
"""

import re
import struct

EXTENSIONS = (".mp3", ".flac", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".wav", ".wma", ".ape", ".wv", ".alac", ".aiff", ".aif")
# Covers of a folder, best first. Other pictures of the folder come after these.
COVER_NAMES = ("cover", "folder", "front", "albumart_large", "albumartlarge", "album", "albumart", "albumartsmall")
PICTURES = (".jpg", ".jpeg", ".png", ".webp")


def is_song(name):
    return name.lower().endswith(EXTENSIONS) and not name.startswith(".")


def sort_key(name):
    """Natural order: 2 before 10, without regard to case."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", name)]


def name_of(path):
    return path.rstrip("/").replace("\\", "/").split("/")[-1] or path


def title_from_name(name):
    """A title from a file name such as "04 - Song.mp3" or "04-Song (Artist).mp3", without its number and extension."""
    stem = name.rsplit(".", 1)[0]
    stem = re.sub(r"^\s*(?:cd\s*\d+\s*[-.]?\s*)?\d{1,3}\s*[-._)]*\s+|^\s*\d{1,3}\s*[-.]\s*", "", stem, flags=re.IGNORECASE)
    return stem.replace("_", " ").strip() or name


def clean_title(title, number=0):
    """A tag title without a leading track number, which some taggers leave in it. A number without a dash after it
    goes only when it is the number of the track, so a title such as "7 Anos" keeps its own."""
    cleaned = re.sub(r"^\s*\d{1,3}\s*[-.]\s+", "", title).strip()
    if number and cleaned == title.strip():
        cleaned = re.sub(r"^\s*0*%d\s+" % number, "", title).strip()
    return cleaned or title


def number_from_name(name):
    match = re.match(r"^\s*(\d{1,3})\D", name)
    return int(match.group(1)) if match else 0


def cover(names):
    """The cover among the files of a folder, or None. Copies that macOS leaves, starting with "._", are left out."""
    pictures = [name for name in names if name.lower().endswith(PICTURES) and not name.startswith(".")]
    def rank(name):
        stem = re.sub(r"[{}\-\s0]", "", name.rsplit(".", 1)[0].lower())
        for index, wanted in enumerate(COVER_NAMES):
            if stem == wanted or stem.startswith(wanted):
                return index
        return len(COVER_NAMES)
    return min(pictures, key=lambda name: (rank(name), sort_key(name))) if pictures else None


def time_label(seconds):
    seconds = int(seconds or 0)
    return "%d:%02d" % (seconds // 60, seconds % 60) if seconds < 3600 else "%d:%02d:%02d" % (seconds // 3600, seconds // 60 % 60, seconds % 60)


# Tags ----------------------------------------------------------------------------------------------------------------

def tags(path):
    """Title, artist, album and track number of a local song, from its ID3 or FLAC tags. Missing ones are empty."""
    found = {"title": "", "artist": "", "album": "", "track": 0}
    try:
        with open(path, "rb") as data:
            head = data.read(10)
            if head[:3] == b"ID3":
                _id3v2(data, head, found)
            elif head[:4] == b"fLaC":
                _flac(data, found)
            if not found["title"] and path.lower().endswith(".mp3"):
                _id3v1(data, found)
    except (OSError, struct.error, ValueError):
        pass
    return found


def _text(raw):
    """Text of an ID3v2 frame: an encoding byte, then the text."""
    if not raw:
        return ""
    encoding, body = raw[0], raw[1:]
    codec = {0: "latin-1", 1: "utf-16", 2: "utf-16-be", 3: "utf-8"}.get(encoding, "latin-1")
    text = body.decode(codec, errors="replace")
    return text.replace("\x00", "/").strip("/ ﻿").split("/")[0].strip() if encoding in (1, 2) else text.split("\x00")[0].strip()


def _synchsafe(raw):
    return (raw[0] << 21) | (raw[1] << 14) | (raw[2] << 7) | raw[3]


def _id3v2(data, head, found):
    version = head[3]
    size = _synchsafe(head[6:10])
    body = data.read(size)
    if head[5] & 0x40 and len(body) > 4:
        # An extended header comes first.
        skip = _synchsafe(body[:4]) if version == 4 else struct.unpack(">I", body[:4])[0] + 4
        body = body[skip:]
    wanted = {"TIT2": "title", "TPE1": "artist", "TALB": "album", "TRCK": "track",
              "TT2": "title", "TP1": "artist", "TAL": "album", "TRK": "track"}
    position = 0
    short = version == 2
    while position + (6 if short else 10) <= len(body):
        if short:
            frame, length, start = body[position:position + 3], int.from_bytes(body[position + 3:position + 6], "big"), position + 6
        else:
            frame = body[position:position + 4]
            raw = body[position + 4:position + 8]
            length = _synchsafe(raw) if version == 4 else struct.unpack(">I", raw)[0]
            start = position + 10
        if not frame.strip(b"\x00") or length <= 0:
            break
        key = wanted.get(frame.decode("latin-1", errors="replace"))
        if key:
            value = _text(body[start:start + length])
            if key == "track":
                match = re.match(r"\d+", value)
                found["track"] = int(match.group()) if match else 0
            elif value:
                found[key] = value
        position = start + length


def _id3v1(data, found):
    data.seek(-128, 2)
    block = data.read(128)
    if block[:3] != b"TAG":
        return
    field = lambda start, end: block[start:end].split(b"\x00")[0].decode("latin-1", errors="replace").strip()
    found["title"] = found["title"] or field(3, 33)
    found["artist"] = found["artist"] or field(33, 63)
    found["album"] = found["album"] or field(63, 93)
    if block[125] == 0 and block[126]:
        found["track"] = found["track"] or block[126]


def _flac(data, found):
    names = {"TITLE": "title", "ARTIST": "artist", "ALBUM": "album", "TRACKNUMBER": "track"}
    while True:
        header = data.read(4)
        if len(header) < 4:
            return
        last, kind, length = header[0] & 0x80, header[0] & 0x7F, int.from_bytes(header[1:4], "big")
        if kind != 4:
            data.seek(length, 1)
        else:
            block = data.read(length)
            vendor = struct.unpack("<I", block[:4])[0]
            position = 4 + vendor
            count = struct.unpack("<I", block[position:position + 4])[0]
            position += 4
            for _ in range(count):
                size = struct.unpack("<I", block[position:position + 4])[0]
                comment = block[position + 4:position + 4 + size].decode("utf-8", errors="replace")
                position += 4 + size
                key, _, value = comment.partition("=")
                field = names.get(key.upper())
                if field == "track":
                    match = re.match(r"\d+", value)
                    found["track"] = int(match.group()) if match else 0
                elif field and value:
                    found[field] = value.strip()
            return
        if last:
            return
