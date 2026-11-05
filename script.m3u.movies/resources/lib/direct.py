"""Downloads of direct links, the sources of the catalog that play without a torrent.

The background service downloads them, so they go on after Easy Movie closes. Each download is a folder of small
files in the jobs folder, each with one writer, so the window and the service never write the same file:

- job.json, written once by the window: the link, its headers, the file to save and the title of the catalog.
- status.json, written by the service: state, bytes done and total, speed and an error message.
- request.json, written by the window: pause, resume or remove, which the service reads and deletes.

Does not import Kodi modules, so it can be tested with a regular Python 3 interpreter.
"""

import json
import os
import re
import time
import urllib.request
import uuid
from urllib.parse import unquote, urlsplit

CHUNK = 512 * 1024
# How often the service writes the progress of a download.
STATUS_SECONDS = 1
TIMEOUT = 30
VIDEO_EXTENSIONS = (".mkv", ".mp4", ".m4v", ".avi", ".mov", ".webm", ".ts", ".wmv", ".mpg", ".mpeg")
TYPES = {"video/mp4": ".mp4", "video/x-matroska": ".mkv", "video/webm": ".webm", "video/x-msvideo": ".avi",
         "video/quicktime": ".mov", "video/mp2t": ".ts"}
INVALID = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


def can_download(url):
    """A stream of segments, as an HLS playlist, is not one file, so it cannot be saved."""
    return not urlsplit(url).path.lower().endswith((".m3u8", ".m3u", ".mpd"))


def safe_name(name):
    return re.sub(r"\s+", " ", INVALID.sub(" ", name)).strip(" .") or "video"


def extension_of(url, content_type=""):
    path = unquote(urlsplit(url).path).lower()
    for extension in VIDEO_EXTENSIONS:
        if path.endswith(extension):
            return extension
    return TYPES.get(content_type.split(";")[0].strip().lower(), ".mp4")


def target_name(origin, url, fallback):
    """The file name of a download: "Series S01E02.mkv" for an episode, "Movie (1999).mp4" for a movie."""
    extension = extension_of(url)
    if origin and origin.get("kind") == "series" and origin.get("episode"):
        name = "%s S%02dE%02d" % (origin["name"], origin.get("season") or 1, origin["episode"])
        return safe_name(origin["name"]), safe_name(name) + extension
    if origin and origin.get("name"):
        name = "%s (%s)" % (origin["name"], origin["year"]) if origin.get("year") else origin["name"]
        return "", safe_name(name) + extension
    return "", safe_name(fallback) + extension


def read(path, default=None):
    try:
        with open(path, encoding="utf-8") as source:
            return json.load(source)
    except (OSError, ValueError):
        return default


def write(path, value):
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as target:
        json.dump(value, target, ensure_ascii=False)
    os.replace(temporary, path)


def add(jobs_folder, url, headers, path, title):
    """Queue a download. Returns its id."""
    job_id = time.strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
    folder = os.path.join(jobs_folder, job_id)
    os.makedirs(folder, exist_ok=True)
    write(os.path.join(folder, "job.json"), {"url": url, "headers": headers or {}, "path": path, "title": title,
                                             "added": time.time()})
    return job_id


def request(jobs_folder, job_id, action):
    """Ask the service to pause, resume or remove a download. remove_files also deletes what was downloaded."""
    write(os.path.join(jobs_folder, job_id, "request.json"), {"action": action})


def jobs(jobs_folder):
    """Downloads, newest first, each with its job and status: [{"id", "title", "path", "state", "done", "total", "rate"}]."""
    found = []
    try:
        names = sorted(os.listdir(jobs_folder), reverse=True)
    except OSError:
        return found
    for name in names:
        job = read(os.path.join(jobs_folder, name, "job.json"))
        if not job:
            continue
        status = read(os.path.join(jobs_folder, name, "status.json"), {})
        found.append(dict(job, id=name, state=status.get("state", "queued"), done=status.get("done", 0),
                          total=status.get("total", 0), rate=status.get("rate", 0), error=status.get("error", "")))
    return found


class Runner:
    """Downloads the queued jobs one at a time. step() runs one pass; the service calls it in a loop."""

    def __init__(self, jobs_folder, should_stop):
        self.jobs_folder = jobs_folder
        self.should_stop = should_stop

    def folder(self, job_id):
        return os.path.join(self.jobs_folder, job_id)

    def status(self, job_id):
        return read(os.path.join(self.folder(job_id), "status.json"), {"state": "queued", "done": 0, "total": 0})

    def set_status(self, job_id, **values):
        status = self.status(job_id)
        status.update(values)
        write(os.path.join(self.folder(job_id), "status.json"), status)

    def take_request(self, job_id):
        path = os.path.join(self.folder(job_id), "request.json")
        found = read(path)
        if found is not None:
            try:
                os.remove(path)
            except OSError:
                pass
        return (found or {}).get("action")

    def handle_requests(self):
        for job in jobs(self.jobs_folder):
            action = self.take_request(job["id"])
            if action:
                self.apply(job, action)

    def apply(self, job, action):
        if action == "pause" and job["state"] in ("queued", "downloading"):
            self.set_status(job["id"], state="paused", rate=0)
        elif action == "resume" and job["state"] in ("paused", "failed"):
            self.set_status(job["id"], state="queued", error="")
        elif action in ("remove", "remove_files"):
            if action == "remove_files":
                for path in (job["path"], job["path"] + ".part"):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            elif job["state"] != "finished":
                # A download removed from the list before it ends leaves no half file behind.
                try:
                    os.remove(job["path"] + ".part")
                except OSError:
                    pass
            for name in ("job.json", "status.json", "request.json"):
                try:
                    os.remove(os.path.join(self.folder(job["id"]), name))
                except OSError:
                    pass
            try:
                os.rmdir(self.folder(job["id"]))
            except OSError:
                pass

    def step(self):
        """Handle the requests, then download the oldest queued job, if any. Returns True when one was downloaded."""
        self.handle_requests()
        waiting = [job for job in reversed(jobs(self.jobs_folder)) if job["state"] in ("queued", "downloading")]
        if not waiting:
            return False
        self.download(waiting[0])
        return True

    def download(self, job):
        """Download a job into its file, continuing a part file left by an earlier run."""
        part = job["path"] + ".part"
        os.makedirs(os.path.dirname(job["path"]) or ".", exist_ok=True)
        done = os.path.getsize(part) if os.path.exists(part) else 0
        headers = dict(job.get("headers") or {})
        headers.setdefault("User-Agent", "Mozilla/5.0")
        if done:
            headers["Range"] = "bytes=%d-" % done
        try:
            response = urllib.request.urlopen(urllib.request.Request(job["url"], headers=headers), timeout=TIMEOUT)
        except Exception as error:
            if done and "416" in str(error):
                # The part file already has the whole video.
                os.replace(part, job["path"])
                self.set_status(job["id"], state="finished", rate=0)
                return
            self.set_status(job["id"], state="failed", rate=0, error=str(error))
            return
        with response:
            if done and response.status != 206:
                # The server sends the whole file again, so it starts over.
                done = 0
            length = int(response.headers.get("Content-Length") or 0)
            total = done + length if length else 0
            self.set_status(job["id"], state="downloading", done=done, total=total, error="")
            last, window_bytes, window_start = time.time(), 0, time.time()
            try:
                with open(part, "ab" if done else "wb") as target:
                    while True:
                        data = response.read(CHUNK)
                        if not data:
                            break
                        target.write(data)
                        done += len(data)
                        window_bytes += len(data)
                        now = time.time()
                        if now - last >= STATUS_SECONDS:
                            rate = window_bytes / max(now - window_start, 0.001)
                            window_bytes, window_start, last = 0, now, now
                            self.set_status(job["id"], done=done, rate=rate)
                            action = self.take_request(job["id"])
                            if action:
                                self.set_status(job["id"], rate=0)
                                self.apply(dict(job, state="downloading"), action)
                                return
                            if self.should_stop():
                                # Kodi quits: the part file stays, and the download continues next time.
                                self.set_status(job["id"], state="queued", rate=0)
                                return
            except Exception as error:
                self.set_status(job["id"], state="failed", done=done, rate=0, error=str(error))
                return
        if total and done < total:
            self.set_status(job["id"], state="failed", done=done, rate=0, error="incomplete")
            return
        os.replace(part, job["path"])
        self.set_status(job["id"], state="finished", done=done, total=total or done, rate=0)
