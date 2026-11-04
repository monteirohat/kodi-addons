"""Posters and details of movies and series from Cinemeta, the metadata add-on of Stremio. Free of Kodi imports.

Searches accept titles in Portuguese as well as in English. Descriptions are in English.
"""

import html
import json
import re
import unicodedata
import urllib.parse
import urllib.request


BASE = "https://v3-cinemeta.strem.io"
USER_AGENT = "Kodi/21 Easy Movie"
TIMEOUT = 15


def fetch(path):
    request = urllib.request.Request(BASE + path, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def normalized(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[\W_]+", " ", text.casefold()).strip()


# Words left out when comparing titles.
COMMON_WORDS = {"a", "o", "as", "os", "e", "de", "do", "da", "dos", "das", "um", "uma", "no", "na", "em", "the", "of",
                "and", "an", "in", "on", "to"}


def words(text):
    return {word for word in normalized(text).split() if word not in COMMON_WORDS}


def similar(title, name):
    """Whether a result name shares at least half of the words of the title."""
    wanted = words(title)
    return bool(wanted) and len(wanted & words(name)) >= len(wanted) / 2


def search(kind, title):
    """Candidates for a title. kind is "movie" or "series"."""
    path = "/catalog/%s/top/search=%s.json" % (kind, urllib.parse.quote(title))
    return fetch(path).get("metas", [])


def first_year(release):
    match = re.match(r"\d{4}", release or "")
    return int(match.group()) if match else 0


def best(candidates, title, year):
    """The candidate that matches the title and year best, or None.

    A known year must match within one year, since release dates differ between countries, and then a title in
    another language is accepted. Without a year, a result must share words with the title, since searches
    always return something and the first result of an unrelated title is a wrong movie.
    """
    wanted = normalized(title)
    exact = [meta for meta in candidates if normalized(meta.get("name", "")) == wanted]
    if year:
        dated = [meta for meta in candidates if abs(first_year(meta.get("releaseInfo")) - year) <= 1]
        return ([meta for meta in exact if meta in dated] or dated or [None])[0]
    return (exact or [meta for meta in candidates if similar(title, meta.get("name", ""))] or [None])[0]


def catalog(kind, catalog_id="top", genre=None, skip=0):
    """A page of a Cinemeta catalog: "top" for popular titles, "imdbRating" for featured ones and "year" for the
    titles of the year given as genre. Pages have about 50 titles, and an empty page is the end."""
    extra = [("genre", genre)] if genre else []
    if skip:
        extra.append(("skip", str(skip)))
    path = "/catalog/%s/%s" % (kind, catalog_id)
    if extra:
        path += "/" + "&".join("%s=%s" % (name, urllib.parse.quote(value)) for name, value in extra)
    return fetch(path + ".json").get("metas", [])


def unescaped(value):
    """Text without the HTML entities some names and descriptions have, as in "O&apos;Dea"."""
    if isinstance(value, list):
        return [unescaped(item) for item in value]
    return html.unescape(value) if isinstance(value, str) else value


def summary(meta):
    """Fields kept for a catalog item: poster, background, description, rating, year, genres, runtime, director
    and cast."""
    return {
        "id": meta.get("imdb_id") or meta.get("id", ""),
        "name": unescaped(meta.get("name", "")),
        # Small posters look blurred on a TV.
        "poster": (meta.get("poster") or "").replace("/poster/small/", "/poster/medium/"),
        "fanart": meta.get("background", ""),
        "plot": unescaped(meta.get("description", "")),
        "rating": meta.get("imdbRating", ""),
        "year": first_year(meta.get("releaseInfo") or meta.get("year")),
        "genres": meta.get("genres") or [],
        "runtime": meta.get("runtime", ""),
        "director": unescaped((meta.get("director") or [])[:2]),
        "cast": unescaped((meta.get("cast") or [])[:4]),
    }


def meta(kind, imdb_id):
    """Everything Cinemeta has on a title. Catalog pages shorten the descriptions, this does not."""
    return fetch("/meta/%s/%s.json" % (kind, imdb_id)).get("meta") or {}


def details(kind, imdb_id):
    return dict(summary(meta(kind, imdb_id)), id=imdb_id)


def episodes(meta):
    """Episodes of a series meta as (season, number, title, aired date, description, video id), in order. Season
    0 holds the specials. The video id, as in "tt0903747:1:4", asks addons for the sources of the episode."""
    found = []
    for video in meta.get("videos") or []:
        number = video.get("episode", video.get("number"))
        if video.get("season") is None or number is None:
            continue
        found.append((int(video["season"]), int(number), unescaped(video.get("name") or video.get("title") or ""),
                      (video.get("released") or video.get("firstAired") or "")[:10],
                      unescaped(video.get("overview") or video.get("description") or ""),
                      video.get("id") or "%s:%s:%s" % (meta.get("id", ""), video["season"], number)))
    return sorted(found)


def lookup(kind, title, year=0):
    """Details of the best match for a title, or None when nothing matches."""
    meta = best(search(kind, title), title, year)
    return details(kind, meta["id"]) if meta else None
