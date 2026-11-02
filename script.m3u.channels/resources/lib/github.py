"""Find M3U lists in GitHub repositories. Free of Kodi imports so it can be tested anywhere."""

import json
import re
import urllib.error
import urllib.parse
import urllib.request


API = "https://api.github.com/repos/"
RAW = "https://raw.githubusercontent.com/"
USER_AGENT = "Kodi/21 Easy Channel"
# Smaller files hold at most the #EXTM3U header, so they have no channels.
MIN_SIZE = 40
# Repositories offered on first use: free and public channels, actively maintained.
DEFAULT_REPOS = [
    {"owner": "iptv-org", "repo": "iptv"},
    {"owner": "Free-TV", "repo": "IPTV"},
    {"owner": "iptv-com", "repo": "iptv"},
    {"owner": "LITUATUI", "repo": "M3UPT"},
]


class RateLimited(Exception):
    pass


def parse_repo(text):
    """Accept owner/name or a GitHub address, optionally with /tree/<branch>/<folder>."""
    text = text.strip()
    text = re.sub(r"^(https?://)?(www\.)?github\.com/", "", text, flags=re.IGNORECASE).strip("/")
    parts = [part for part in text.split("/") if part]
    if len(parts) < 2 or not all(re.fullmatch(r"[\w.-]+", part) for part in parts[:2]):
        return None
    repo = {"owner": parts[0], "repo": re.sub(r"\.git$", "", parts[1])}
    if len(parts) >= 4 and parts[2] == "tree":
        repo["branch"] = parts[3]
        if len(parts) > 4:
            repo["path"] = "/".join(parts[4:])
    return repo


def label(repo):
    return repo["owner"] + "/" + repo["repo"] + ("/" + repo["path"] if repo.get("path") else "")


def request_json(url, timeout):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code in (403, 429):
            raise RateLimited() from error
        raise


def find_lists(repo, timeout=20):
    """M3U files of a repository that are large enough to hold channels, sorted by path."""
    base = API + repo["owner"] + "/" + repo["repo"]
    branch = repo.get("branch") or request_json(base, timeout)["default_branch"]
    tree = request_json(base + "/git/trees/" + urllib.parse.quote(branch, safe="") + "?recursive=1", timeout)
    folder = repo.get("path", "").strip("/")
    found = []
    for entry in tree.get("tree", []):
        path = entry["path"]
        if entry["type"] != "blob" or not path.lower().endswith((".m3u", ".m3u8")):
            continue
        if folder and not path.startswith(folder + "/"):
            continue
        if entry.get("size", 0) < MIN_SIZE:
            continue
        url = RAW + repo["owner"] + "/" + repo["repo"] + "/" + urllib.parse.quote(branch) + "/" + urllib.parse.quote(path)
        found.append({"path": path, "size": entry.get("size", 0), "url": url})
    return sorted(found, key=lambda item: item["path"].casefold())
