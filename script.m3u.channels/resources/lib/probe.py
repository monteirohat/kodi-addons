"""Quick reachability check for stream addresses. Free of Kodi imports."""

from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.parse
import urllib.request


USER_AGENT = "Kodi/21 Easy Channel"


def check(url, timeout):
    """Return None when the stream answers, otherwise a short reason.

    Only HTTP addresses can be checked. Other protocols are reported as working.
    """
    address, _, options = url.partition("|")
    if not address.lower().startswith(("http://", "https://")):
        return None
    headers = {"User-Agent": USER_AGENT}
    headers.update(dict(urllib.parse.parse_qsl(options)))
    request = urllib.request.Request(address, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if not response.read(1024):
                return "empty response"
    except urllib.error.HTTPError as error:
        return "HTTP " + str(error.code)
    except urllib.error.URLError as error:
        return str(error.reason)
    except Exception as error:
        return str(error) or type(error).__name__
    return None


def check_many(channels, timeout, workers, progress):
    """Check channels in parallel. progress(done, failed_count) returns False to stop."""
    failed = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [(channel, executor.submit(check, channel["url"], timeout)) for channel in channels]
        for done, (channel, future) in enumerate(futures, 1):
            reason = future.result()
            if reason:
                failed.append((channel, reason))
            if not progress(done, len(failed)):
                for _, pending in futures:
                    pending.cancel()
                break
    return failed
