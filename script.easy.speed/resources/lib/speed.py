"""Speed test of the internet connection: latency, download and upload.

Uses the servers of fast.com, the speed test of Netflix, which are the servers that deliver its videos. fast.com has no
official API: its page reads a token from its script and asks for the addresses of the nearest servers, and so does
this module, each time. When fast.com does not answer, the test uses the servers of Cloudflare.

Does not import Kodi modules, so it can be tested with a regular Python 3 interpreter:

    python3 resources/lib/speed.py
"""

import http.client
import json
import os
import re
import statistics
import threading
import time
import urllib.request
from urllib.parse import urlsplit

TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
FAST_PAGE = "https://fast.com/"
FAST_API = "https://api.fast.com/netflix/speedtest/v2?https=true&token=%s&urlCount=5"
CLOUDFLARE = "https://speed.cloudflare.com"
# Each request asks for this many bytes, and the connections ask again until the time of the phase ends.
REQUEST_BYTES = 25 * 1024 * 1024
CONNECTIONS = 8
DOWNLOAD_SECONDS = 10
UPLOAD_SECONDS = 8
# The first seconds of a phase are left out of its result, while TCP grows to the speed of the connection.
WARM_UP_SECONDS = 2
# The live speed is the speed of the last seconds.
WINDOW_SECONDS = 2
UPDATE_SECONDS = 0.25
LATENCY_SAMPLES = 6
CHUNK = 64 * 1024

# The speeds of streaming that Netflix recommends, in Mbps, from the highest quality.
QUALITIES = ((15, "4k"), (5, "full_hd"), (3, "hd"), (1, "sd"))


class Cancelled(Exception):
    pass


class TestError(Exception):
    pass


def quality(download_mbps):
    """The best video quality the download speed plays without stopping, or "none"."""
    for minimum, name in QUALITIES:
        if download_mbps >= minimum:
            return name
    return "none"


def get_text(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", "replace")


class Fast:
    """The servers of fast.com. Their addresses end in /speedtest, and /speedtest/range/0-N asks for N + 1 bytes."""

    name = "fast.com"

    def __init__(self):
        page = get_text(FAST_PAGE)
        script = re.search(r"(app-[0-9a-z]+\.js)", page)
        if not script:
            raise TestError("fast.com: script not found")
        token = re.search(r'token:"([A-Za-z0-9]+)"', get_text(FAST_PAGE + script.group(1)))
        if not token:
            raise TestError("fast.com: token not found")
        data = json.loads(get_text(FAST_API % token.group(1)))
        self.targets = [target["url"] for target in data.get("targets", [])]
        if not self.targets:
            raise TestError("fast.com: no servers")
        location = data["targets"][0].get("location", {})
        self.server = ", ".join(part for part in (location.get("city"), location.get("country")) if part)
        self.isp = data.get("client", {}).get("isp", "")

    def url(self, index, size):
        return self.targets[index % len(self.targets)].replace("/speedtest", "/speedtest/range/0-%d" % max(size - 1, 0), 1)

    def download_url(self, index):
        return self.url(index, REQUEST_BYTES)

    def upload_url(self, index):
        return self.url(index, REQUEST_BYTES)

    def latency_url(self, index):
        return self.url(index, 1)


class Cloudflare:
    """The servers of speed.cloudflare.com. The data center that answers is at the end of its cf-ray header."""

    name = "Cloudflare"
    isp = ""

    def __init__(self):
        request = urllib.request.Request(CLOUDFLARE + "/__down?bytes=0", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            ray = response.headers.get("cf-ray", "")
        # An airport code, as GRU for Sao Paulo.
        self.server = ray.rsplit("-", 1)[-1] if "-" in ray else ""

    def download_url(self, index):
        return CLOUDFLARE + "/__down?bytes=%d" % REQUEST_BYTES

    def upload_url(self, index):
        return CLOUDFLARE + "/__up"

    def latency_url(self, index):
        return CLOUDFLARE + "/__down?bytes=0"


def open_server():
    """fast.com, or Cloudflare when fast.com does not answer."""
    try:
        return Fast()
    except Exception as fast_error:
        try:
            return Cloudflare()
        except Exception as error:
            raise TestError("%s; Cloudflare: %s" % (fast_error, error))


class Connection:
    """One HTTPS connection kept open between requests, as a browser does, so each request does not pay for a new
    handshake."""

    def __init__(self, url):
        self.host = urlsplit(url).netloc
        self.connection = None

    def open(self):
        if self.connection is None:
            self.connection = http.client.HTTPSConnection(self.host, timeout=TIMEOUT)
        return self.connection

    def close(self):
        if self.connection is not None:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None

    @staticmethod
    def path(url):
        parts = urlsplit(url)
        return parts.path + ("?" + parts.query if parts.query else "")

    def get(self, url, on_data=None, stop=None):
        """Download url. on_data receives the size of each piece. Returns the bytes read."""
        connection = self.open()
        try:
            connection.request("GET", self.path(url), headers={"User-Agent": USER_AGENT})
            response = connection.getresponse()
            total = 0
            while True:
                if stop is not None and stop.is_set():
                    # The rest of the answer would wait in the connection, so it closes.
                    self.close()
                    return total
                data = response.read(CHUNK)
                if not data:
                    return total
                total += len(data)
                if on_data:
                    on_data(len(data))
        except Exception:
            self.close()
            raise

    def post(self, url, body, size, on_data, stop):
        """Upload size bytes to url, repeating body. on_data receives the size of each piece sent."""
        connection = self.open()
        try:
            connection.putrequest("POST", self.path(url))
            connection.putheader("User-Agent", USER_AGENT)
            connection.putheader("Content-Type", "application/octet-stream")
            connection.putheader("Content-Length", str(size))
            connection.endheaders()
            sent = 0
            while sent < size:
                if stop.is_set():
                    self.close()
                    return
                piece = body[:min(CHUNK, size - sent)]
                connection.send(piece)
                sent += len(piece)
                on_data(len(piece))
            connection.getresponse().read()
        except Exception:
            self.close()
            raise


def ping(connection, url):
    """The time of one small request on an open connection, in milliseconds."""
    start = time.monotonic()
    connection.get(url)
    return (time.monotonic() - start) * 1000


class SpeedTest:
    """Runs the phases one after the other. on_update receives a dict with the phase, the live speed in Mbps, the
    progress of the phase from 0 to 1 and the results so far. cancel() stops the test from another thread."""

    def __init__(self, on_update=None):
        self.on_update = on_update or (lambda status: None)
        self.cancelled = threading.Event()
        self.result = {}

    def cancel(self):
        self.cancelled.set()

    def check(self):
        if self.cancelled.is_set():
            raise Cancelled()

    def update(self, phase, speed=0.0, progress=0.0):
        self.on_update({"phase": phase, "speed": speed, "progress": progress, "result": dict(self.result)})

    def run(self):
        """Returns {"server", "isp", "provider", "latency", "loaded_latency", "download", "upload", "quality"}, with
        latencies in milliseconds and speeds in Mbps."""
        self.update("connecting")
        server = open_server()
        self.check()
        self.result.update(server=server.server, isp=server.isp, provider=server.name)
        self.update("latency")
        self.result["latency"] = self.latency(server)
        self.check()
        loaded = []
        self.result["download"] = self.transfer(server, "download", DOWNLOAD_SECONDS, loaded)
        if loaded:
            self.result["loaded_latency"] = statistics.median(loaded)
        self.result["quality"] = quality(self.result["download"])
        self.check()
        self.result["upload"] = self.transfer(server, "upload", UPLOAD_SECONDS)
        self.update("done", self.result["download"], 1.0)
        return dict(self.result)

    def latency(self, server):
        """The best time of a few small requests, on an open connection, while nothing else downloads."""
        times = []
        connection = Connection(server.latency_url(0))
        try:
            # The first request opens the connection, whose handshake is not part of the latency.
            connection.get(server.latency_url(0))
            for _ in range(LATENCY_SAMPLES):
                self.check()
                times.append(ping(connection, server.latency_url(0)))
        finally:
            connection.close()
        return min(times)

    def transfer(self, server, phase, seconds, loaded=None):
        """Download or upload on several connections for some seconds. Returns the speed in Mbps, after the warm up.
        With loaded, a list, it also measures the latency while the connections are busy."""
        counts = [0] * CONNECTIONS
        stop = threading.Event()
        errors = []
        body = os.urandom(CHUNK) if phase == "upload" else None

        def worker(index):
            connection = Connection(server.download_url(index))

            def add(size):
                counts[index] += size
            try:
                while not stop.is_set():
                    if phase == "download":
                        connection.get(server.download_url(index), add, stop)
                    else:
                        connection.post(server.upload_url(index), body, REQUEST_BYTES, add, stop)
            except Exception as error:
                if not stop.is_set():
                    errors.append(error)
            finally:
                connection.close()

        def pinger():
            connection = Connection(server.latency_url(0))
            try:
                connection.get(server.latency_url(0))
                while not stop.is_set():
                    loaded.append(ping(connection, server.latency_url(0)))
                    stop.wait(0.3)
            except Exception:
                pass
            finally:
                connection.close()

        threads = [threading.Thread(target=worker, args=(index,), daemon=True) for index in range(CONNECTIONS)]
        if loaded is not None:
            threads.append(threading.Thread(target=pinger, daemon=True))
        start = time.monotonic()
        for thread in threads:
            thread.start()
        samples = [(start, 0)]
        first = warm = None
        try:
            while True:
                self.cancelled.wait(UPDATE_SECONDS)
                self.check()
                now = time.monotonic()
                done = sum(counts)
                samples.append((now, done))
                # The warm up counts from the first bytes, as opening the connections takes a moment.
                if first is None and done:
                    first = now
                if warm is None and first is not None and now - first >= WARM_UP_SECONDS:
                    warm = (now, done)
                # The live speed: the bytes of the last seconds.
                old = next(sample for sample in samples if sample[0] >= now - WINDOW_SECONDS)
                if old[0] == now:
                    old = samples[-2]
                live = (done - old[1]) * 8 / max(now - old[0], 0.001) / 1e6
                elapsed = now - first if first is not None else 0
                self.update(phase, live, min(elapsed / seconds, 1.0))
                if elapsed >= seconds or now - start >= seconds + TIMEOUT:
                    break
                if len(errors) == CONNECTIONS:
                    raise TestError(str(errors[0]))
        finally:
            stop.set()
        if warm is None or now <= warm[0]:
            warm = samples[0]
        speed = (done - warm[1]) * 8 / max(now - warm[0], 0.001) / 1e6
        if not done:
            raise TestError(str(errors[0]) if errors else "no data")
        return speed


if __name__ == "__main__":
    def show(status):
        print("%-10s %7.1f Mbps %3d%%" % (status["phase"], status["speed"], status["progress"] * 100), end="\r", flush=True)

    result = SpeedTest(show).run()
    print()
    print(json.dumps(result, indent=2))
