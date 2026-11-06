"""Speed test window: the sections on the left, and the speed test, the checks of the connection or the history on the right."""

import json
import os
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import network, speed


ADDON = xbmcaddon.Addon()
TITLE = ADDON.getAddonInfo("name")
PATH = ADDON.getAddonInfo("path")
MEDIA = os.path.join(PATH, "resources", "skins", "default", "media")
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
HISTORY_FILE = os.path.join(PROFILE, "history.json")
HISTORY_SIZE = 50
ACTION_LEFT, ACTION_RIGHT, ACTION_UP, ACTION_DOWN = 1, 2, 3, 4
ACTION_BACK = (10, 92)
ACTION_CONTEXT_MENU = 117
GROUPS, CHECKS, HISTORY = 200, 300, 400
SPEED_BUTTON, CHECK_BUTTON = 501, 502
SECTIONS = [("speed", 30001), ("connection", 30002), ("history", 30003)]
# The speedometer: its marks are evenly spaced, and between two marks the speed moves in a straight line. Matches
# tools/generate_easy_speed_art.py, which draws one fill image for each step.
MARKS = (0, 5, 10, 25, 50, 100, 250, 500, 1000)
FILL_STEPS = 54
CHECK_NAMES = {"network": 30050, "router": 30051, "dns": 30052, "internet": 30053}


def text(string_id, *arguments):
    return ADDON.getLocalizedString(string_id).format(*arguments)


def load(path, default):
    try:
        with open(path, encoding="utf-8") as data:
            return json.load(data)
    except (OSError, ValueError):
        return default


def save(path, value):
    os.makedirs(PROFILE, exist_ok=True)
    with open(path, "w", encoding="utf-8") as data:
        json.dump(value, data, ensure_ascii=False, indent=1)


def number(value):
    """A speed or a time for the screen: one decimal below 10, none above, with the decimal separator of the language."""
    if value is None:
        return "—"
    shown = "%.1f" % value if 0 < value < 9.95 else "%d" % round(value)
    return shown.replace(".", text(30094))


def fill_image(mbps):
    """The fill of the speedometer for a speed, or "" for none."""
    mbps = max(0.0, min(mbps, MARKS[-1]))
    for index in range(len(MARKS) - 1):
        low, high = MARKS[index], MARKS[index + 1]
        if mbps <= high:
            position = (index + (mbps - low) / (high - low)) / (len(MARKS) - 1)
            break
    step = round(position * FILL_STEPS)
    return "fill-%02d.png" % step if step else ""


def when(seconds):
    moment = time.localtime(seconds)
    return time.strftime(xbmc.getRegion("dateshort") + " " + xbmc.getRegion("time").replace(":%S", ""), moment)


def link_text(info):
    """The kind of connection and its name or speed, as "Wi-Fi", "VM1234 · signal 80%"."""
    if info.get("kind") == "wifi":
        parts = [info.get("name")] + ([text(30095, info["signal"])] if info.get("signal") is not None else [])
        return text(30092), "  ·  ".join(part for part in parts if part)
    if info.get("kind") == "cable":
        return text(30093), text(30096, info["speed"]) if info.get("speed") else ""
    if info.get("address"):
        return text(30097), ""
    return text(30091), ""


class MainWindow(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loaded = False
        self.test = None
        self.checking = False
        self.closing = False
        self.history = []
        self.section = "speed"
        self.worker = None

    def onInit(self):
        if self.loaded:
            return
        self.loaded = True
        self.group_list = self.getControl(GROUPS)
        self.checks = self.getControl(CHECKS)
        self.history_list = self.getControl(HISTORY)
        self.speed_button = self.getControl(SPEED_BUTTON)
        self.check_button = self.getControl(CHECK_BUTTON)
        self.setProperty("big_font", "true" if xbmc.getSkinDir() == "skin.monteiro" else "false")
        self.check_button.setLabel(text(30013))
        self.group_list.addItems([xbmcgui.ListItem(text(label)) for _, label in SECTIONS])
        self.history = load(HISTORY_FILE, [])
        self.show_history()
        self.reset_results()
        self.show_section("speed")
        self.setFocusId(SPEED_BUTTON)
        # Check the connection first, so a test does not start without internet.
        self.start(self.check_then_test)

    # Sections

    def show_section(self, name):
        self.section = name
        self.setProperty("section", name)
        self.group_list.selectItem([key for key, _ in SECTIONS].index(name))
        if name == "speed":
            self.setProperty("title", text(30001))
            self.setProperty("subtitle", self.getProperty("server"))
        elif name == "connection":
            self.setProperty("title", text(30002))
            self.setProperty("subtitle", text(30098))
        else:
            self.setProperty("title", text(30003))
            self.setProperty("subtitle", self.history_count())

    def history_count(self):
        count = len(self.history)
        return text(30082) if count == 1 else text(30081, count) if count else ""

    def section_control(self):
        return {"speed": SPEED_BUTTON, "connection": CHECK_BUTTON, "history": HISTORY}[self.section]

    def follow_group(self):
        index = self.group_list.getSelectedPosition()
        if 0 <= index < len(SECTIONS) and SECTIONS[index][0] != self.section:
            self.show_section(SECTIONS[index][0])

    def onAction(self, action):
        action_id = action.getId()
        try:
            focus = self.getFocusId()
        except RuntimeError:
            focus = 0
        if action_id in ACTION_BACK:
            # Without a focus, after the skin reloads, Back also closes.
            if focus in (GROUPS, 0):
                self.close_window()
            else:
                self.setFocusId(GROUPS)
        elif focus == GROUPS and action_id in (ACTION_UP, ACTION_DOWN):
            self.follow_group()
        elif focus == GROUPS and action_id == ACTION_RIGHT:
            self.focus_section()
        elif action_id == ACTION_CONTEXT_MENU and focus == HISTORY and self.history:
            self.history_menu(self.history_list.getSelectedPosition())

    def onClick(self, control_id):
        if control_id == GROUPS:
            self.focus_section()
        elif control_id == SPEED_BUTTON:
            if self.test:
                self.test.cancel()
            else:
                self.start(self.check_then_test)
        elif control_id == CHECK_BUTTON and not self.checking:
            self.start(self.check_connection)
        elif control_id == HISTORY and self.history:
            self.history_menu(self.history_list.getSelectedPosition())

    def focus_section(self):
        """Move to the button or the list of the section, if it has something to select."""
        self.follow_group()
        if self.section != "history" or self.history:
            self.setFocusId(self.section_control())

    def start(self, target):
        """Run the checks or the test in the background, so the window keeps answering the remote."""
        self.worker = threading.Thread(target=target, daemon=True)
        self.worker.start()

    def close_window(self):
        self.closing = True
        if self.test:
            self.test.cancel()
        self.close()

    # Connection

    def check_connection(self):
        """Run the checks and show them. Returns whether the internet works."""
        self.checking = True
        try:
            self.checks.reset()
            rows = []
            for key in ("network", "router", "dns", "internet"):
                item = xbmcgui.ListItem(text(CHECK_NAMES[key]))
                item.setProperty("state", "waiting")
                rows.append(item)
            self.checks.addItems(rows)
            self.setProperty("diagnosis", text(30077))
            kodi = {"address": xbmc.getInfoLabel("Network.IPAddress"), "gateway": xbmc.getInfoLabel("Network.GatewayAddress")}
            results = network.diagnose(kodi)
            for result, item in zip(results, rows):
                item.setProperty("state", result["state"])
                detail, value = self.check_text(result)
                item.setLabel2(detail)
                item.setProperty("value", value)
            for item in rows[len(results):]:
                item.setProperty("state", "waiting")
                item.setLabel2(text(30079))
            info = results[0]
            title, detail = link_text(info)
            self.setProperty("link_title", title)
            self.setProperty("link_detail", detail)
            self.setProperty("link_icon", os.path.join(MEDIA, "cable.png" if info.get("kind") == "cable" else
                                                       "wifi.png" if info.get("kind") == "wifi" else "failed.png"))
            self.setProperty("diagnosis", self.diagnosis(results))
            return len(results) == 4 and results[3]["state"] == network.OK
        finally:
            self.checking = False

    def check_text(self, result):
        """The detail and the value of a check row."""
        check, state = result["check"], result["state"]
        elapsed = result.get("time")
        value = text(30035, number(elapsed)) if elapsed is not None else ""
        if check == "network":
            if state == network.FAILED:
                return text(30059), ""
            title, detail = link_text(result)
            return "  ·  ".join(part for part in (title, detail, text(30058, result["address"])) if part), ""
        if check == "router":
            if state == network.FAILED:
                return text(30061, result["gateway"]) if result.get("gateway") else text(30062), text(30078)
            return text(30060, result["gateway"]), value
        if check == "dns":
            return (text(30063), value) if state == network.OK else (text(30064), text(30078))
        if state == network.WARNING:
            return text(30066), ""
        return (text(30065), value) if state == network.OK else (text(30067), text(30078))

    @staticmethod
    def diagnosis(results):
        """What the first failed check means, and what to do."""
        failed = next((result for result in results if result["state"] == network.FAILED), None)
        if failed:
            return text({"network": 30072, "router": 30073, "dns": 30074, "internet": 30075}[failed["check"]])
        if results[-1]["state"] == network.WARNING:
            return text(30076)
        if results[0]["state"] == network.WARNING:
            return text(30071)
        return text(30070)

    # Speed test

    def reset_results(self):
        for name in ("download", "upload", "latency", "loaded"):
            self.setProperty(name, "—")
        self.setProperty("speed", "0")
        self.setProperty("unit", text(30034))
        self.setProperty("fill", "")
        self.setProperty("quality", "")

    def check_then_test(self):
        if self.test or self.checking:
            return
        self.speed_button.setLabel(text(30012))
        self.setProperty("phase", text(30077))
        if not self.check_connection():
            self.setProperty("phase", text(30025))
            self.speed_button.setLabel(text(30010))
            if not self.closing:
                # Show where the problem is.
                self.show_section("connection")
                if self.getFocusId() == SPEED_BUTTON:
                    self.setFocusId(CHECK_BUTTON)
            return
        self.run_test()

    def run_test(self):
        self.reset_results()
        self.test = speed.SpeedTest(self.show_progress)
        self.speed_button.setLabel(text(30012))
        result = None
        try:
            result = self.test.run()
        except speed.Cancelled:
            self.setProperty("phase", text(30026))
        except Exception as error:
            xbmc.log("Easy Speed: test failed: %s" % error, xbmc.LOGWARNING)
            self.setProperty("phase", text(30027))
            if not self.closing:
                xbmcgui.Dialog().notification(TITLE, text(30028, error), ADDON.getAddonInfo("icon"), 5000)
        finally:
            self.test = None
            if not self.closing:
                self.speed_button.setLabel(text(30010))
        if result and not self.closing:
            self.setProperty("phase", text(30024))
            self.setProperty("speed", number(result["download"]))
            self.setProperty("fill", fill_image(result["download"]))
            self.add_history(result)

    def show_progress(self, status):
        if self.closing:
            return
        phase, result = status["phase"], status["result"]
        if phase in ("download", "upload"):
            self.setProperty("speed", number(status["speed"]))
            self.setProperty("fill", fill_image(status["speed"]))
            self.setProperty("phase", text(30022 if phase == "download" else 30023))
        elif phase == "connecting":
            self.setProperty("phase", text(30020))
        elif phase == "latency":
            self.setProperty("phase", text(30021))
        if result.get("server"):
            server = text(30036, result["server"]) + ("  ·  " + result["isp"] if result.get("isp") else "")
            self.setProperty("server", server)
            if self.section == "speed":
                self.setProperty("subtitle", server)
        for name in ("download", "upload"):
            if name in result:
                self.setProperty(name, text(30037, number(result[name])))
        for name, key in (("latency", "latency"), ("loaded", "loaded_latency")):
            if key in result:
                self.setProperty(name, text(30035, number(result[key])))
        if "quality" in result:
            self.setProperty("quality", text({"4k": 30040, "full_hd": 30041, "hd": 30042, "sd": 30043, "none": 30044}[result["quality"]]))

    # History

    def add_history(self, result):
        entry = dict(result, time=time.time(), link=self.getProperty("link_title"), link_detail=self.getProperty("link_detail"))
        self.history.insert(0, entry)
        del self.history[HISTORY_SIZE:]
        save(HISTORY_FILE, self.history)
        self.show_history()

    def show_history(self):
        items = []
        for entry in self.history:
            item = xbmcgui.ListItem(when(entry["time"]))
            item.setLabel2("  ·  ".join(part for part in (entry.get("link"), entry.get("server")) if part))
            item.setProperty("download", text(30037, number(entry.get("download"))))
            item.setProperty("upload", text(30037, number(entry.get("upload"))))
            item.setProperty("latency", text(30035, number(entry.get("latency"))))
            items.append(item)
        self.history_list.reset()
        self.history_list.addItems(items)
        self.group_list.getListItem(2).setLabel2(str(len(self.history)) if self.history else "")
        if self.section == "history":
            self.setProperty("subtitle", self.history_count())
        if self.history:
            last = self.history[0]
            self.setProperty("last_download", text(30037, number(last.get("download"))))
            self.setProperty("last_upload", text(30037, number(last.get("upload"))))
            self.setProperty("last_detail", when(last["time"]))
        else:
            for name in ("last_download", "last_upload", "last_detail"):
                self.setProperty(name, "")

    def history_menu(self, position):
        if not 0 <= position < len(self.history):
            return
        choice = xbmcgui.Dialog().contextmenu([text(30083), text(30084)])
        if choice == 0:
            del self.history[position]
        elif choice == 1 and xbmcgui.Dialog().yesno(TITLE, text(30085)):
            self.history = []
        else:
            return
        save(HISTORY_FILE, self.history)
        self.show_history()
        if self.history:
            self.history_list.selectItem(min(position, len(self.history) - 1))
        else:
            self.setFocusId(GROUPS)


def run():
    window = MainWindow("script-easy-speed-main.xml", PATH, "default", "1080i")
    window.doModal()
    # The test stops when the window closes; wait for it, as it still changes the window.
    if window.worker:
        window.worker.join(15)
    del window
