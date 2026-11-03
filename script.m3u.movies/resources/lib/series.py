"""Group the episodes of M3U lists into series. Free of Kodi imports so it can be tested anywhere."""

import re

from resources.lib import m3u


# Season and episode markers, tried in order. The show name is the text before the marker.
# An episode number may carry a letter, as in "EP01L", so it ends at the first non-digit.
EPISODE_PATTERNS = [
    re.compile(r"\b[Ss](\d{1,2})\s*[._|:/-]?\s*[Ee][Pp]?(\d{1,3})(?!\d)"),      # S01E02, S1 E2, s01.ep02
    re.compile(r"\b[Tt](\d{1,2})\s*[._|:/-]?\s*[Ee][Pp]?(\d{1,3})(?!\d)"),      # T01E02, T1 E2, T1|EP02
    re.compile(r"\b(\d{1,2})[xX](\d{1,3})\b"),                                  # 1x02
    re.compile(r"\b[Tt]emporada\s*(\d{1,2})\D{1,12}?[Ee]pis[oó]dio\s*(\d{1,3})", re.IGNORECASE),
    re.compile(r"\b[Ss]eason\s*(\d{1,2})\D{1,12}?[Ee]pisode\s*(\d{1,3})", re.IGNORECASE),
    re.compile(r"^\s*(\d{1,2})\s*\|\s*[Ee][Pp]?\s*(\d{1,3})(?!\d)"),           # 01|EP01, 3|EP01 Title
    re.compile(r"^\s*[Tt](\d{1,2})\s*\|\s*(\d{1,3})(?!\d)"),                    # T01|01
]
# A name made only of an episode number, as in "EP001". Used when pltv-subgroup names the show.
EPISODE_ONLY = re.compile(r"\s*(?:[Ee][Pp]?|[Ee]pis[oó]dio|[Ee]pisode|[Cc]ap[ií]tulo)\s*[._|:/-]?\s*(\d{1,4})\b")
# A special of a season, as in "T03|ESPECIAL". Used when pltv-subgroup names the show.
SEASON_SPECIAL = re.compile(r"\s*[Tt](\d{1,2})\s*\|\s*(\D.*)")
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
    # Some lists keep the show in pltv-subgroup and name the episodes only "T01|EP01" or "EP001".
    subgroup = channel.get("subgroup", "").strip()
    for pattern in EPISODE_PATTERNS:
        match = pattern.search(name)
        if not match:
            continue
        # pltv-subgroup has the full show name, where the episode name may only have an abbreviation.
        show = subgroup or clean(name[:match.start()])
        if not show:
            # Lists that name episodes only "S01E01" put the show in the group.
            show = next((group for group in m3u.groups_of(channel) if group), "")
        if not show:
            return None
        # A letter right after the number, as the L of "EP01L", is a tag and not part of the title.
        title = re.sub(r"^[A-Za-z](?=\s|$)", "", name[match.end():])
        return show, int(match.group(1)), int(match.group(2)), clean(title)
    match = EPISODE_ONLY.match(name) if subgroup else None
    if match:
        return subgroup, 1, int(match.group(1)), clean(name[match.end():])
    match = SEASON_SPECIAL.match(name) if subgroup else None
    if match:
        # Specials are episode 0 of their season, listed before episode 1.
        return subgroup, int(match.group(1)), 0, clean(match.group(2))
    return None


def movie_groups(channel):
    """Genres of a movie: its groups, and pltv-subgroup, which lists use for the genre of movies."""
    groups = m3u.groups_of(channel)
    subgroup = channel.get("subgroup", "").strip()
    if subgroup and subgroup not in groups:
        groups = [group for group in groups if group] + [subgroup]
    return groups


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
        # The same stream in several lists appears once. Different streams with the same code are all kept,
        # because some lists give several episodes the same number. Sorting keeps the order of the list then.
        unique = {}
        for entry in item["episodes"]:
            unique.setdefault(entry["channel"]["id"], entry)
        item["episodes"] = sorted(unique.values(), key=lambda entry: (entry["episode"]["season"], entry["episode"]["number"]))
        item["seasons"] = sorted({entry["episode"]["season"] for entry in item["episodes"]})
    return movies, sorted(series.values(), key=lambda item: item["name"].casefold())
