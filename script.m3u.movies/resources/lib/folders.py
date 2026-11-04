"""Video folders as catalog sources: finds the videos of a folder and describes them as an M3U list.

Free of Kodi imports so it can be tested anywhere. The caller passes a walk function, os.walk for local folders
or one built on xbmcvfs for network folders.
"""

import posixpath
import re
import unicodedata

from resources.lib import m3u, series


VIDEO_EXTENSIONS = {".mkv", ".mp4", ".m4v", ".avi", ".mov", ".wmv", ".mpg", ".mpeg", ".ts", ".m2ts", ".webm", ".flv", ".3gp"}
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
# Images that describe a whole folder, such as the poster of a movie in its own folder or of a series.
FOLDER_IMAGES = ("poster", "folder", "cover")
# Files next to a video with the same name: subtitles, images and metadata. Renamed and deleted with it.
SIDECAR_EXTENSIONS = (".srt", ".sub", ".ass", ".ssa", ".vtt", ".idx", ".nfo") + IMAGE_EXTENSIONS
# Release and quality tags. The name of a video ends where the first one starts.
TAGS = re.compile(r"(?<![a-z0-9])(2160p|1080p|1080i|720p|576p|480p|360p|4k|uhd|hdr10?|bluray|blu-ray|bdrip|brrip|"
                  r"webrip|web-dl|webdl|web|hdtv|dvdrip|dvd|hdrip|hdcam|camrip|x264|x265|h\.?264|h\.?265|hevc|xvid|"
                  r"divx|aac|ac3|dts|dual|dublado|legendado|nacional|remux|proper|repack|extended|unrated)(?![a-z0-9])",
                  re.IGNORECASE)
YEAR = re.compile(r"(?<!\d)(19[2-9]\d|20[0-4]\d)(?!\d)")
BRACKETS = re.compile(r"\[[^\]]*\]|\{[^}]*\}")
# Folders that only hold one season of a series, as in "Season 2" or "Temporada 02".
SEASON_FOLDER = re.compile(r"^(?:season|temporada|temp\.?|s|t)\s*0*(\d{1,2})$", re.IGNORECASE)
# Files named only by their episode number, as in "196 - Adeus As Aulas - 480p.mp4".
NUMBERED = re.compile(r"^\s*(?:ep(?:is[oó]dio)?\.?\s*)?(\d{1,4})(?:\s*[-._)]\s*|\s+|$)(.*)$", re.IGNORECASE)
# Share of the videos of a folder that must start with a number for them to be its episodes. A folder of movies
# where one title starts with a number, like "300", stays a folder of movies.
NUMBERED_SHARE = 0.6
SKIPPED = re.compile(r"(?<![a-z])sample(?![a-z])", re.IGNORECASE)


def is_video(name):
    return posixpath.splitext(name)[1].lower() in VIDEO_EXTENSIONS and not name.startswith(".")


def clean(stem):
    """Readable name of a video file: separators become spaces and release tags are dropped."""
    text = BRACKETS.sub(" ", stem)
    if text.count(" ") < 2:
        text = re.sub(r"[._]+", " ", text)
    tag = TAGS.search(text)
    if tag and tag.start() > 0:
        text = text[:tag.start()]
    return re.sub(r"\s+", " ", text).strip(" -_.([")


def title_and_year(stem):
    """Name and year of a movie file, as in ("O Senhor dos Aneis", 2001)."""
    name = clean(stem)
    # The year is the last one in the name, so a title that is a year, such as "2012", keeps it.
    years = list(YEAR.finditer(name))
    if years and years[-1].start() > 0:
        year = years[-1]
        return name[:year.start()].strip(" -_.(["), int(year.group())
    return name, 0


def image_for(names, stem):
    """An image in names that belongs to the video stem, or the folder image when stem is None."""
    lowered = {name.lower(): name for name in names}
    candidates = [stem + suffix for suffix in ("", "-poster", ".poster")] if stem else list(FOLDER_IMAGES)
    for candidate in candidates:
        for extension in IMAGE_EXTENSIONS:
            found = lowered.get((candidate + extension).lower())
            if found:
                return found
    return None


def scan(root, walk):
    """Videos under root as catalog channels in an M3U text.

    The first level of subfolders gives the groups, when they hold more than one title. The folder of a single
    movie or series, as a torrent download makes, is not a group. Episodes take the name of their series from
    their folder, skipping season folders, and the season from a season folder.
    """
    root = root.rstrip("/") or "/"
    channels = []
    # Folder images by folder. A walk visits a folder before its subfolders, so a season folder finds the
    # poster of its series.
    folder_images = {}
    for folder, subfolders, files in walk(root):
        subfolders[:] = sorted(name for name in subfolders if not name.startswith("."))
        folder_image = image_for(files, None)
        if folder_image:
            folder_images[folder] = posixpath.join(folder, folder_image)
        videos = sorted(name for name in files if is_video(name) and not SKIPPED.search(name))
        if not videos:
            continue
        relative = [part for part in posixpath.relpath(folder, root).split("/") if part not in ("", ".")]
        group = relative[0] if relative else ""
        season, show_parts = 1, list(relative)
        if show_parts and SEASON_FOLDER.match(show_parts[-1]):
            season = int(SEASON_FOLDER.match(show_parts.pop()).group(1))
        # Videos right in the chosen folder belong to the series named by that folder, as when the folder of a
        # series is chosen itself.
        show = show_parts[-1] if show_parts else posixpath.basename(root)
        show_folder = posixpath.join(root, *show_parts) if show_parts else root
        numbered = [name for name in videos if NUMBERED.match(posixpath.splitext(name)[0])]
        episodes_by_number = bool(show) and len(numbered) >= 2 and len(numbered) >= NUMBERED_SHARE * len(videos)
        show_image = folder_images.get(show_folder)
        for name in videos:
            stem = posixpath.splitext(name)[0]
            path = posixpath.join(folder, name)
            own_image = image_for(files, stem)
            logo = posixpath.join(folder, own_image) if own_image else ""
            attributes = {"group-title": group}
            match = NUMBERED.match(stem) if episodes_by_number else None
            if match:
                title = clean(match.group(2))
                display = "S%02dE%02d %s" % (season, int(match.group(1)), title)
                attributes["pltv-subgroup"] = show
                logo = logo or show_image or ""
            else:
                display = clean(stem)
                if show and re.search(r"\b[Ss]\d{1,2}\s*[Ee]\d{1,3}|\b\d{1,2}[xX]\d{1,3}\b", display):
                    # An episode named with its code. Its folder names the series, unless the folder is the chosen
                    # one or a group, which may hold several series, and the file names its own series.
                    code = re.search(r"\b[Ss]\d{1,2}\s*[Ee]\d{1,3}|\b\d{1,2}[xX]\d{1,3}\b", display)
                    if code.start() == 0 or len(show_parts) > 1:
                        attributes["pltv-subgroup"] = show
                    logo = logo or show_image or ""
                else:
                    title, year = title_and_year(stem)
                    display = "%s (%d)" % (title, year) if year else title
                    # A movie alone in its folder uses the folder image as its poster.
                    if not logo and len(videos) == 1:
                        logo = folder_images.get(folder, "")
            if logo:
                attributes["tvg-logo"] = logo
            channels.append((attributes, display, path))
    # A group needs more than one title: movies, or series by their name.
    titles = {}
    for attributes, display, path in channels:
        titles.setdefault(attributes["group-title"], set()).add(title_key(attributes, display, path))
    for attributes, _, _ in channels:
        if len(titles[attributes["group-title"]]) < 2:
            attributes["group-title"] = ""
    return to_m3u(channels)


def title_key(attributes, display, path):
    """What a video is part of: its series, by a name without accents, or the movie itself."""
    episode = series.parse_episode({"name": display, "subgroup": attributes.get("pltv-subgroup", ""),
                                    "group": attributes["group-title"]})
    if episode is None:
        return path
    name = unicodedata.normalize("NFKD", episode[0])
    return "show:" + series.show_key("".join(char for char in name if not unicodedata.combining(char)))


def to_m3u(channels):
    lines = ["#EXTM3U"]
    for attributes, name, path in channels:
        values = " ".join('%s="%s"' % (key, value.replace('"', "'")) for key, value in attributes.items() if value)
        lines += ["#EXTINF:-1 %s,%s" % (values, name.replace("\n", " ")), path]
    return "\n".join(lines) + "\n"


def movie_query(channel):
    """Title and year to look up a movie of a folder."""
    return title_and_year(posixpath.splitext(posixpath.basename(m3u.base_url(channel["url"])))[0])


def sidecars(names, stem):
    """Files in names that belong to the video stem: subtitles, images and metadata with the same name."""
    lowered = stem.lower()
    found = []
    for name in names:
        base, extension = posixpath.splitext(name)
        if extension.lower() not in SIDECAR_EXTENSIONS:
            continue
        base = base.lower()
        # Subtitles often carry a language, as in "Movie.pt-BR.srt", and posters a suffix, as in "Movie-poster.jpg".
        if base == lowered or base.startswith(lowered + ".") or base.startswith(lowered + "-"):
            found.append(name)
    return found
