"""Torrent downloads through Torrest, a torrent engine with a REST API that runs as a separate process.

Easy Movie ships the Torrest executable of each platform in resources/bin. Running it as its own process keeps
Kodi up if the engine fails. Free of Kodi imports, so the caller passes the folders to use.
"""

import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


PORT = 61235
# Seconds to wait for Torrest to answer after it starts, and to stop before it is killed.
START_TIMEOUT = 15
STOP_TIMEOUT = 10
# libtorrent states, as Torrest reports them in "state".
CHECKING_STATES = {1, 7}
METADATA_STATE = 2
FINISHED_STATES = {4, 5}


class EngineError(Exception):
    """Torrest could not start, or refused a request. The message explains why."""


def platform_name(android=False):
    """Folder of the Torrest executable for this device, as in "linux_arm64", or None when there is none."""
    machine = platform.machine().lower()
    if machine in ("aarch64", "arm64", "armv8l", "armv8"):
        arch = "arm64"
    elif machine.startswith("arm"):
        arch = "arm" if android else "armv7"
    elif machine in ("x86_64", "amd64"):
        arch = "x64"
    elif machine in ("i386", "i686", "x86"):
        arch = "x86"
    else:
        return None
    if android:
        system = "android"
    elif sys.platform.startswith("win"):
        system = "windows"
    elif sys.platform == "darwin":
        # Only an Intel build exists. Apple silicon Macs run it with Rosetta.
        system, arch = "darwin", "x64"
    else:
        system = "linux"
    if system == "linux" and arch == "arm":
        arch = "armv7"
    return "%s_%s" % (system, arch)


def executable_name(name):
    return "torrest.exe" if name.startswith("windows") else "torrest"


class Engine:
    """Starts, stops and talks to the Torrest process.

    addon_path is the add-on folder, which holds resources/bin. data_path is a folder of the profile that holds
    the executable copy, the settings, the log and the saved torrents.
    """

    def __init__(self, addon_path, data_path, android=False, port=PORT):
        self.addon_path, self.data_path, self.android, self.port = addon_path, data_path, android, port
        self.base = "http://127.0.0.1:%d" % port

    # Process

    def executable(self):
        """The executable to run. It is copied into the profile, since add-on folders may not allow running
        programs and installing from a zip drops the permission to run."""
        name = platform_name(self.android)
        if not name:
            raise EngineError("no Torrest build for this device (%s)" % platform.machine())
        source = os.path.join(self.addon_path, "resources", "bin", name, executable_name(name))
        if not os.path.exists(source):
            raise EngineError("missing Torrest build: " + name)
        target_folder = os.path.join(self.data_path, "bin")
        target = os.path.join(target_folder, executable_name(name))
        if not os.path.exists(target) or os.path.getsize(target) != os.path.getsize(source) \
                or os.path.getmtime(target) < os.path.getmtime(source):
            os.makedirs(target_folder, exist_ok=True)
            shutil.copyfile(source, target)
        mode = os.stat(target).st_mode
        os.chmod(target, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return target

    def running(self):
        try:
            self.request("GET", "/status", timeout=2)
            return True
        except EngineError:
            return False

    def start(self, download_path, settings=None):
        """Start Torrest unless it already runs, then apply the settings. Returns True when it was started."""
        if self.running():
            self.configure(download_path, settings)
            return False
        os.makedirs(self.data_path, exist_ok=True)
        command = [self.executable(), "--port", str(self.port), "--settings", os.path.join(self.data_path, "settings.json"),
                   "--log-path", os.path.join(self.data_path, "torrest.log"), "--log-level", "WARNING"]
        options = {"cwd": self.data_path, "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
                   "stderr": subprocess.DEVNULL}
        if sys.platform.startswith("win"):
            options["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        else:
            options["start_new_session"] = True
        try:
            process = subprocess.Popen(command, **options)
        except OSError as error:
            raise EngineError("could not start Torrest: %s" % error)
        deadline = time.time() + START_TIMEOUT
        while time.time() < deadline:
            if process.poll() is not None:
                raise EngineError("Torrest stopped right after starting (code %s)" % process.returncode)
            if self.running():
                self.configure(download_path, settings)
                return True
            time.sleep(0.3)
        process.kill()
        raise EngineError("Torrest did not answer")

    def stop(self):
        """Ask Torrest to save its torrents and quit."""
        try:
            self.request("PUT", "/shutdown", timeout=5)
        except EngineError:
            return
        deadline = time.time() + STOP_TIMEOUT
        while time.time() < deadline and self.running():
            time.sleep(0.5)

    # API

    def request(self, method, path, query=None, body=None, timeout=10, content_type="application/json"):
        url = self.base + path + ("?" + urllib.parse.urlencode(query) if query else "")
        data = None
        if body is not None:
            data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", content_type)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                text = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            try:
                message = json.loads(error.read().decode("utf-8")).get("error")
            except Exception:
                message = None
            raise EngineError(message or "HTTP %d" % error.code)
        except (urllib.error.URLError, OSError) as error:
            raise EngineError(str(getattr(error, "reason", error)))
        return json.loads(text) if text.strip() else None

    def configure(self, download_path, settings=None):
        """Set the download folder and other settings, keeping the rest as they are."""
        current = self.request("GET", "/settings")
        wanted = dict(current, download_path=download_path, torrents_path=os.path.join(self.data_path, "torrents"))
        wanted.update(settings or {})
        if wanted != current:
            self.request("PUT", "/settings", body=wanted)

    def add_magnet(self, uri, download_path):
        """Add a magnet link and download all of its files into download_path. Returns the info hash."""
        self.configure(download_path)
        return self.request("POST", "/add/magnet", {"uri": uri, "download": "true", "ignore_duplicate": "true"})["info_hash"]

    def add_torrent_file(self, data, download_path):
        """Add the content of a .torrent file and download all of its files. Returns the info hash."""
        self.configure(download_path)
        boundary = "----easymovie%d" % int(time.time() * 1000)
        body = (("--%s\r\nContent-Disposition: form-data; name=\"torrent\"; filename=\"file.torrent\"\r\n"
                 "Content-Type: application/x-bittorrent\r\n\r\n" % boundary).encode("utf-8") + data +
                ("\r\n--%s--\r\n" % boundary).encode("utf-8"))
        return self.request("POST", "/add/torrent", {"download": "true", "ignore_duplicate": "true"}, body,
                            content_type="multipart/form-data; boundary=" + boundary)["info_hash"]

    def files(self, info_hash):
        """Files of a torrent, once its metadata arrived. Before that, Torrest answers with an error."""
        return self.request("GET", "/torrents/%s/files" % info_hash) or []

    def only_file(self, info_hash, file_index, timeout=600):
        """Download only one file of a torrent, as an episode of a season pack. Waits for the metadata, then stops
        the other files. Before the metadata nothing is downloaded, so no other file gets data."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                files = self.files(info_hash)
            except EngineError:
                files = []
            if files:
                for item in files:
                    if item.get("id") != file_index:
                        try:
                            self.request("PUT", "/torrents/%s/files/%s/stop" % (info_hash, item["id"]))
                        except EngineError:
                            pass
                return True
            time.sleep(2)
        return False

    def torrents(self):
        """Torrents with their status, newest first as Torrest lists them."""
        return self.request("GET", "/torrents", {"status": "true"}) or []

    def pause(self, info_hash):
        self.request("PUT", "/torrents/%s/pause" % info_hash)

    def resume(self, info_hash):
        self.request("PUT", "/torrents/%s/resume" % info_hash)

    def remove(self, info_hash, delete_files):
        self.request("DELETE", "/torrents/%s" % info_hash, {"delete": "true" if delete_files else "false"})


def state_of(status):
    """A short state name for a torrent status: metadata, checking, paused, finished or downloading."""
    if status.get("paused"):
        return "paused"
    state = status.get("state")
    if not status.get("has_metadata") or state == METADATA_STATE:
        return "metadata"
    if state in CHECKING_STATES:
        return "checking"
    if state in FINISHED_STATES or status.get("progress", 0) >= 100:
        return "finished"
    return "downloading"


def remaining_seconds(status):
    rate = status.get("download_rate", 0)
    left = status.get("total_wanted", 0) - status.get("total_wanted_done", 0)
    return int(left / rate) if rate > 0 and left > 0 else 0
