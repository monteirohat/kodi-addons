"""Stremio addons: the manifest that describes an addon, and its catalogs and details. Free of Kodi imports.

An addon is an address that answers JSON: manifest.json, then /catalog/{type}/{id}.json, /meta/{type}/{id}.json
and /stream/{type}/{id}.json for the resources it declares.
"""

import json
import re
import urllib.parse
import urllib.request


USER_AGENT = "Kodi/21 Easy Movie"
TIMEOUT = 20


class AddonError(Exception):
    """The address is not a Stremio addon, or its manifest cannot be used. The message explains why."""


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def manifest_url(address):
    """The manifest address of what the user pasted: an https address, or a stremio:// install link."""
    address = address.strip()
    if address.lower().startswith("stremio://"):
        address = "https://" + address[len("stremio://"):]
    if not address.lower().startswith(("http://", "https://")):
        address = "https://" + address
    address = address.split("#")[0].rstrip("/")
    if not address.endswith("/manifest.json"):
        address += "/manifest.json"
    return address


def base_url(url):
    """The address the resources of an addon are under: its manifest address without manifest.json."""
    return url[:-len("/manifest.json")] if url.endswith("/manifest.json") else url.rstrip("/")


def load_manifest(url):
    try:
        manifest = fetch(url)
    except ValueError:
        raise AddonError("not a Stremio addon")
    if not isinstance(manifest, dict) or not manifest.get("id") or not manifest.get("name") \
            or not isinstance(manifest.get("resources"), list):
        raise AddonError("not a Stremio addon")
    return manifest


def resource_names(manifest):
    """Resources of an addon, such as catalog, meta, stream and subtitles."""
    return [resource if isinstance(resource, str) else resource.get("name", "") for resource in manifest["resources"]]


def needs_configuration(manifest):
    return bool((manifest.get("behaviorHints") or {}).get("configurationRequired"))


def browsable_catalogs(manifest, kind):
    """Catalogs of a kind that can be shown without asking anything, as (id, name, pages). A catalog that requires
    a search or a genre is left out. pages tells whether it accepts skip, to load more titles."""
    found = []
    for catalog in manifest.get("catalogs") or []:
        if catalog.get("type") != kind or not catalog.get("id"):
            continue
        extra = catalog.get("extra") or [{"name": name} for name in catalog.get("extraSupported") or []]
        required = [item.get("name") for item in extra if item.get("isRequired")] + list(catalog.get("extraRequired") or [])
        if required:
            continue
        pages = any(item.get("name") == "skip" for item in extra)
        found.append((catalog["id"], short_name(catalog.get("name") or catalog["id"], manifest["name"]), pages))
    return found


def short_name(name, addon_name):
    """A catalog name without the addon name in front, as in "Filmes" for "Brazuca Play - Filmes" of the addon
    "Brazuca Play (Não Oficial)"."""
    for separator in (" - ", " | ", ": "):
        prefix, found, rest = name.partition(separator)
        if found and rest and addon_name.lower().startswith(prefix.strip().lower()):
            return rest.strip()
    return name


def has_meta(manifest, kind, item_id):
    """Whether the addon gives the details of an item, by its resources, types and id prefixes."""
    return supports(manifest, "meta", kind, item_id)


def supports(manifest, wanted, kind, item_id):
    """Whether the addon has a resource, such as meta or stream, for an item of a type."""
    for resource in manifest["resources"]:
        name = resource if isinstance(resource, str) else resource.get("name")
        if name != wanted:
            continue
        types = manifest.get("types") if isinstance(resource, str) else resource.get("types", manifest.get("types"))
        prefixes = manifest.get("idPrefixes") if isinstance(resource, str) else resource.get("idPrefixes", manifest.get("idPrefixes"))
        if (not types or kind in types) and (not prefixes or any(item_id.startswith(prefix) for prefix in prefixes)):
            return True
    return False


def catalog(base, kind, catalog_id, skip=0):
    """A page of an addon catalog. An empty page is the end."""
    path = "/catalog/%s/%s" % (kind, urllib.parse.quote(catalog_id, safe=""))
    if skip:
        path += "/skip=%d" % skip
    return fetch(base + path + ".json").get("metas") or []


def meta(base, kind, item_id):
    return fetch(base + "/meta/%s/%s.json" % (kind, urllib.parse.quote(item_id, safe=""))).get("meta") or {}


def streams(base, kind, item_id):
    """Sources of a movie, or of an episode by its video id, as in "tt0903747:1:4"."""
    return fetch(base + "/stream/%s/%s.json" % (kind, urllib.parse.quote(item_id, safe=":"))).get("streams") or []


# Emoji and symbols that addons put in their texts, which the fonts of Kodi do not draw.
SYMBOLS = re.compile("[\U00010000-\U0010FFFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D\u2190-\u21FF\u2300-\u23FF]")
# Seeds and size follow a person and a floppy disk, as Torrentio writes them.
SEEDS = re.compile("\U0001F464" + r"\s*(\d+)")
SIZE = re.compile("\U0001F4BE" + r"\s*([\d.,]+\s*[KMGT]i?B)", re.IGNORECASE)


# Flags mark the audio languages of a source, as in Torrentio. Each flag is two regional indicator letters,
# which give a country, shown as its main language.
FLAG = re.compile("([\U0001F1E6-\U0001F1FF])([\U0001F1E6-\U0001F1FF])")
COUNTRY_LANGUAGES = {
    "GB": "EN", "US": "EN", "AU": "EN", "BR": "PT-BR", "PT": "PT", "ES": "ES", "MX": "ES", "AR": "ES", "FR": "FR",
    "IT": "IT", "DE": "DE", "RU": "RU", "UA": "UK", "PL": "PL", "NL": "NL", "SE": "SV", "NO": "NO", "DK": "DA",
    "FI": "FI", "CZ": "CS", "SK": "SK", "HU": "HU", "RO": "RO", "BG": "BG", "GR": "EL", "TR": "TR", "IL": "HE",
    "SA": "AR", "AE": "AR", "IR": "FA", "IN": "HI", "CN": "ZH", "TW": "ZH", "HK": "ZH", "JP": "JA", "KR": "KO",
    "TH": "TH", "VN": "VI", "ID": "ID", "MY": "MS", "PH": "TL", "HR": "HR", "RS": "SR", "SI": "SL", "LT": "LT",
    "LV": "LV", "EE": "ET",
}


def languages(text):
    """Languages of the flags in a text, in order and without repeats, as in ["EN", "RU"]."""
    found = []
    for first, second in FLAG.findall(text or ""):
        country = chr(ord(first) - 0x1F1E6 + 65) + chr(ord(second) - 0x1F1E6 + 65)
        language = COUNTRY_LANGUAGES.get(country, country)
        if language not in found:
            found.append(language)
    return found


def plain(text):
    return re.sub(r"\s+", " ", SYMBOLS.sub("", text or "")).strip(" |-·")


def describe(stream):
    """What a source is, in a form to show and use, or None for kinds that cannot be used here, such as links
    to web pages.

    kind is "torrent" or "url". label is the file or release name, and quality, size and seeds come from the
    texts of the addon when it gives them."""
    text = stream.get("title") or stream.get("description") or ""
    lines = [plain(line) for line in text.split("\n")]
    lines = [line for line in lines if line]
    name_lines = [plain(line) for line in (stream.get("name") or "").split("\n")]
    hints = stream.get("behaviorHints") or {}
    seeds, size = SEEDS.search(text), SIZE.search(text)
    source = {
        "label": plain(hints.get("filename")) or (lines[0] if lines else "") or " ".join(name_lines),
        "quality": " ".join(line for line in name_lines[1:] if line),
        "size": size.group(1) if size else "",
        "seeds": int(seeds.group(1)) if seeds else None,
        "languages": languages(text + " " + (stream.get("name") or "")),
    }
    if stream.get("infoHash"):
        trackers = [item[len("tracker:"):] for item in stream.get("sources") or [] if item.startswith("tracker:")]
        source.update(kind="torrent", info_hash=stream["infoHash"].lower(), file_idx=stream.get("fileIdx"),
                      magnet=magnet(stream["infoHash"], trackers, source["label"]))
        return source
    if stream.get("url"):
        headers = ((hints.get("proxyHeaders") or {}).get("request")) or {}
        source.update(kind="url", url=stream["url"], headers=headers)
        return source
    return None


def magnet(info_hash, trackers, name=""):
    parts = ["xt=urn:btih:" + info_hash.lower()]
    if name:
        parts.append("dn=" + urllib.parse.quote(name))
    parts += ["tr=" + urllib.parse.quote(tracker, safe="") for tracker in trackers]
    return "magnet:?" + "&".join(parts)
