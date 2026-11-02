"""Group the episodes of M3U lists into series. Free of Kodi imports so it can be tested anywhere."""

import re

from resources.lib import m3u


# Season and episode markers, tried in order. The show name is the text before the marker.
EPISODE_PATTERNS = [
    re.compile(r"\b[Ss](\d{1,2})\s*[._-]?\s*[Ee][Pp]?(\d{1,3})\b"),             # S01E02, S1 E2, s01.ep02
    re.compile(r"\b[Tt](\d{1,2})\s*[._-]?\s*[Ee][Pp]?(\d{1,3})\b"),             # T01E02, T1 E2, T01 EP02
    re.compile(r"\b(\d{1,2})[xX](\d{1,3})\b"),                                  # 1x02
    re.compile(r"\b[Tt]emporada\s*(\d{1,2})\D{1,12}?[Ee]pis[oó]dio\s*(\d{1,3})", re.IGNORECASE),
    re.compile(r"\b[Ss]eason\s*(\d{1,2})\D{1,12}?[Ee]pisode\s*(\d{1,3})", re.IGNORECASE),
]
# Separators around the marker. A closing bracket at the end belongs to the name, as in "Show (2010)".
EDGES = re.compile(r"^[\s\-–—|:._,()\[\]{}]+|[\s\-–—|:._,(\[{]+$")


def clean(text):
    return EDGES.sub("", text).strip()


def show_key(name):
    """Identity of a show, so the same show from different lists or spellings becomes one series."""
    return re.sub(r"[\W_]+", " ", name.casefold()).strip()


def parse_episode(channel):
    """Return (show, season, episode, title) for an episode, or None for a movie."""
    name = channel["name"]
    for pattern in EPISODE_PATTERNS:
        match = pattern.search(name)
        if not match:
            continue
        show = clean(name[:match.start()])
        if not show:
            # Lists that name episodes only "S01E01" put the show in the group.
            show = next((group for group in m3u.groups_of(channel) if group), "")
        if not show:
            return None
        return show, int(match.group(1)), int(match.group(2)), clean(name[match.end():])
    return None


def build(entries):
    """Split catalog entries into movies and series.

    Episodes get an "episode" dict with season, number and title. Each series is a dict with its name,
    key, logo, groups and episodes sorted by season and number.
    """
    movies, series = [], {}
    for entry in entries:
        parsed = parse_episode(entry["channel"])
        if parsed is None:
            movies.append(entry)
            continue
        show, season, number, title = parsed
        entry["episode"] = {"season": season, "number": number, "title": title}
        key = show_key(show)
        item = series.setdefault(key, {"series": True, "key": key, "name": show, "logo": "", "groups": [],
                                       "episodes": [], "list_name": entry["list_name"]})
        if not item["logo"] and entry["channel"]["logo"]:
            item["logo"] = entry["channel"]["logo"]
        # A group named after the show only repeats the series, so it is left out.
        for group in m3u.groups_of(entry["channel"]):
            if show_key(group) != key and group not in item["groups"]:
                item["groups"].append(group)
        item["episodes"].append(entry)
    for item in series.values():
        # The same episode in several lists appears once, from the first list.
        unique = {}
        for entry in item["episodes"]:
            unique.setdefault((entry["episode"]["season"], entry["episode"]["number"]), entry)
        item["episodes"] = [unique[number] for number in sorted(unique)]
        item["seasons"] = sorted({season for season, _ in unique})
    return movies, sorted(series.values(), key=lambda item: item["name"].casefold())
