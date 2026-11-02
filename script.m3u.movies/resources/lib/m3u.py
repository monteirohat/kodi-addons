"""M3U parsing and writing. Free of Kodi imports so it can be tested anywhere."""

import re
from urllib.parse import quote


ATTRIBUTE = re.compile(r'([\w-]+)="([^"]*)"')
# VLC options that map to HTTP headers understood by Kodi's "url|Header=value" syntax.
VLC_HEADERS = {
    "http-user-agent": "User-Agent",
    "http-referrer": "Referer",
    "http-referer": "Referer",
    "http-origin": "Origin",
    "http-cookie": "Cookie",
}


def split_extinf(line):
    """Return the attribute part and the display name of an #EXTINF line."""
    body = line[len("#EXTINF:"):]
    quoted = False
    for index, character in enumerate(body):
        if character == '"':
            quoted = not quoted
        elif character == "," and not quoted:
            return body[:index], body[index + 1:].strip()
    return body, ""


def base_url(url):
    """Stream address without the Kodi header suffix. Used as the channel identity."""
    return url.split("|", 1)[0].strip()


# Group names that lists use for channels without a group. They are shown together as one group.
NO_GROUP = {"undefined", "uncategorized", "uncategorised", "other", "others", "none", "n/a", "na", "-",
            "sem grupo", "sem categoria", "outros"}


def groups_of(channel):
    """Groups a channel belongs to. Some lists separate several groups with semicolons."""
    names = [name.strip() for name in channel["group"].split(";") if name.strip()]
    names = [name for name in names if name.casefold() not in NO_GROUP]
    return names or [""]


def parse(text):
    if text.startswith("﻿"):
        text = text[1:]
    channels = []
    info, group, headers, properties, raw = None, "", {}, {}, []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.upper().startswith("#EXTM3U"):
            continue
        if line.startswith("#EXTINF:"):
            info, raw = split_extinf(line), [line]
            group, headers, properties = "", {}, {}
        elif line.startswith("#EXTGRP:"):
            group = line[len("#EXTGRP:"):].strip()
            raw.append(line)
        elif line.startswith("#EXTVLCOPT:"):
            key, _, value = line[len("#EXTVLCOPT:"):].partition("=")
            header = VLC_HEADERS.get(key.strip().lower())
            if header and value.strip():
                headers[header] = value.strip()
            raw.append(line)
        elif line.startswith("#KODIPROP:"):
            key, _, value = line[len("#KODIPROP:"):].partition("=")
            if key.strip():
                properties[key.strip()] = value.strip()
            raw.append(line)
        elif line.startswith("#"):
            continue
        else:
            attributes, name = info if info else ("", "")
            values = dict(ATTRIBUTE.findall(attributes))
            duration = attributes.split(" ", 1)[0].strip()
            url = line
            if headers and "|" not in url:
                url += "|" + "&".join(key + "=" + quote(value, safe="") for key, value in headers.items())
            channels.append({
                "name": name or values.get("tvg-name") or base_url(line),
                "url": url,
                "id": base_url(url),
                "group": values.get("group-title") or group,
                "logo": values.get("tvg-logo", ""),
                "duration": int(duration) if duration.isdigit() else 0,
                "properties": properties,
                "raw": raw + [line],
            })
            info, group, headers, properties, raw = None, "", {}, {}, []
    return channels


def write(channels):
    lines = ["#EXTM3U"]
    for channel in channels:
        lines.extend(channel["raw"] if len(channel["raw"]) > 1 else ["#EXTINF:-1," + channel["name"], channel["url"]])
    return "\n".join(lines) + "\n"
