"""Subtitles from OpenSubtitles, through OpenSubtitles v3, the subtitles addon of Stremio. Free of Kodi imports.

The addon answers /subtitles/{type}/{id}.json, where id is an IMDb id, or the IMDb id of a series with the season
and episode, as in "tt0903747:1:4". The hash of the video file finds the subtitles made for that very file.
"""

import os
import re
import struct
import urllib.parse
import urllib.request

from resources.lib import stremio


BASE = "https://opensubtitles-v3.strem.io"
HASH_CHUNK = 65536
# Languages to look for, best first, for each choice of the Subtitle language setting. pob is Portuguese of Brazil.
LANGUAGE_ORDERS = [("pob", "por", "eng"), ("por", "pob", "eng"), ("eng",), ("spa", "eng")]
# Languages that a viewer of the first one also understands, so its audio needs no subtitles.
FAMILIES = {"pob": {"pob", "por", "pt", "pt-br"}, "por": {"pob", "por", "pt", "pt-br"}, "eng": {"eng", "en"},
            "spa": {"spa", "es"}}
# Codes put in the names of downloaded files, which Kodi reads as their language.
FILE_CODES = {"pob": "pt-BR", "por": "pt", "eng": "en", "spa": "es"}
# Release names share these words with almost any file, so they do not tell versions apart.
COMMON = {"1080p", "720p", "480p", "x264", "x265", "h264", "h265", "hevc", "aac", "web", "dl", "srt"}


def file_hash(path):
    """The OpenSubtitles hash of a video file and its size: the size plus the 64 bit sums of its first and last
    64 KB. None for files too small to have one."""
    size = os.path.getsize(path)
    if size < 2 * HASH_CHUNK:
        return None
    value = size
    with open(path, "rb") as source:
        for offset in (0, size - HASH_CHUNK):
            source.seek(offset)
            data = source.read(HASH_CHUNK)
            value += sum(struct.unpack("<%dQ" % (len(data) // 8), data))
    return "%016x" % (value & 0xFFFFFFFFFFFFFFFF), size


def video_id(imdb_id, season=None, episode=None):
    return "%s:%d:%d" % (imdb_id, season, episode) if season is not None else imdb_id


def search(kind, item_id, file_hash=None, filename=None):
    """Subtitles of a movie or an episode, in the order of the addon."""
    path = "/subtitles/%s/%s" % (kind, urllib.parse.quote(item_id, safe=":"))
    extra = {}
    if file_hash:
        extra.update(videoHash=file_hash[0], videoSize=file_hash[1])
    if filename:
        extra["filename"] = filename
    if extra:
        path += "/" + urllib.parse.urlencode(extra)
    return [subtitle for subtitle in stremio.fetch(BASE + path + ".json").get("subtitles") or [] if subtitle.get("url")]


def release_words(name):
    return {word for word in re.split(r"[^a-z0-9]+", (name or "").lower()) if len(word) > 1 and word not in COMMON}


def ranked(found, languages, filename=""):
    """Subtitles of the wanted languages, best first: by language, then the ones made for this file, then the ones
    whose release name shares more words with the file name."""
    words = release_words(os.path.splitext(filename)[0])

    def key(subtitle):
        release = subtitle.get("movieReleaseName") or subtitle.get("subtitleFileName") or ""
        return languages.index(subtitle["lang"]), subtitle.get("m") != "h", -len(words & release_words(release))

    return sorted((subtitle for subtitle in found if subtitle.get("lang") in languages), key=key)


def release_name(subtitle):
    return subtitle.get("movieReleaseName") or os.path.splitext(subtitle.get("subtitleFileName") or "")[0]


def download(subtitle, folder):
    """Save a subtitle in folder and return its path. The addon gives the text already in UTF-8."""
    request = urllib.request.Request(subtitle["url"], headers={"User-Agent": stremio.USER_AGENT})
    with urllib.request.urlopen(request, timeout=stremio.TIMEOUT) as response:
        data = response.read()
    if not data.strip() or data.lstrip()[:1] in (b"<", b"{"):
        raise ValueError("not a subtitle file")
    # A folder for each subtitle, so the file name can be the same for all: Kodi names the track after it, as in
    # "OpenSubtitles pt".
    folder = os.path.join(folder, re.sub(r"\W+", "", str(subtitle.get("id", ""))) or "subtitle")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "OpenSubtitles.%s.srt" % FILE_CODES.get(subtitle["lang"], subtitle["lang"]))
    with open(path, "wb") as output:
        output.write(data)
    return path
