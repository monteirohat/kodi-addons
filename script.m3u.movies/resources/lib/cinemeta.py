"""Posters and details of movies and series from Cinemeta, the metadata add-on of Stremio. Free of Kodi imports.

Searches accept titles in Portuguese as well as in English. Descriptions are in English.
"""

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


def details(kind, imdb_id):
    """Fields kept for a catalog item: poster, background, description, rating, year, genres and runtime."""
    meta = fetch("/meta/%s/%s.json" % (kind, imdb_id)).get("meta") or {}
    return {
        "id": imdb_id,
        "name": meta.get("name", ""),
        "poster": meta.get("poster", ""),
        "fanart": meta.get("background", ""),
        "plot": meta.get("description", ""),
        "rating": meta.get("imdbRating", ""),
        "year": first_year(meta.get("releaseInfo") or meta.get("year")),
        "genres": meta.get("genres") or [],
        "runtime": meta.get("runtime", ""),
    }


def lookup(kind, title, year=0):
    """Details of the best match for a title, or None when nothing matches."""
    meta = best(search(kind, title), title, year)
    return details(kind, meta["id"]) if meta else None
