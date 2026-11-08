import os
import re
import time
import socket
import ctypes
import subprocess
from datetime import datetime, timedelta
import psutil
import pyautogui
import pyperclip

# Safety configuration for PyAutoGUI
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05

# ==========================================
# 1. Volume & Audio Controls (Core Audio / pycaw)
# ==========================================

def get_master_volume() -> int:
    """Returns current master volume as an integer percentage (0-100)."""
    try:
        from pycaw.pycaw import AudioUtilities
        speakers = AudioUtilities.GetSpeakers()
        vol = speakers.EndpointVolume
        scalar = vol.GetMasterVolumeLevelScalar()
        return int(round(scalar * 100))
    except Exception:
        return 50

def set_master_volume(percent: int) -> int:
    """Sets master volume to an exact percentage (0-100)."""
    percent = max(0, min(100, percent))
    scalar = percent / 100.0
    try:
        from pycaw.pycaw import AudioUtilities
        speakers = AudioUtilities.GetSpeakers()
        vol = speakers.EndpointVolume
        vol.SetMasterVolumeLevelScalar(scalar, None)
        if percent > 0 and vol.GetMute():
            vol.SetMute(0, None)
        return percent
    except Exception as e:
        print(f"[Volume Error]: {e}")
        return percent

def adjust_master_volume(delta: int) -> int:
    """Adjusts master volume by delta (+/- percent)."""
    current = get_master_volume()
    target = max(0, min(100, current + delta))
    return set_master_volume(target)

def toggle_master_mute() -> str:
    """Toggles master volume mute state."""
    try:
        from pycaw.pycaw import AudioUtilities
        speakers = AudioUtilities.GetSpeakers()
        vol = speakers.EndpointVolume
        is_muted = vol.GetMute()
        vol.SetMute(0 if is_muted else 1, None)
        return "Audio unmuted." if is_muted else "Audio muted."
    except Exception:
        pyautogui.press('volumemute')
        return "Toggled audio mute."

# ==========================================
# 2. Display Brightness Controls (WMI)
# ==========================================

def get_brightness() -> int:
    """Returns current display brightness percentage (0-100)."""
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness).CurrentBrightness"],
            text=True,
            timeout=3
        ).strip()
        return int(out)
    except Exception:
        return 50

def set_brightness(level: int) -> int:
    """Sets display brightness percentage (0-100)."""
    level = max(0, min(100, level))
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"],
            check=False,
            timeout=4
        )
        return level
    except Exception:
        return level

# ==========================================
# 3. Process Management (Kill / Close apps)
# ==========================================

APP_PROCESS_MAP = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "firefox": "firefox.exe",
    "notepad": "notepad.exe",
    "calculator": "CalculatorApp.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "spotify": "Spotify.exe",
    "discord": "Discord.exe",
    "slack": "slack.exe",
    "steam": "steam.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "task manager": "Taskmgr.exe",
    "code": "Code.exe",
    "vs code": "Code.exe"
}

def kill_app_process(app_name: str) -> str:
    """Closes or terminates a running application."""
    app_clean = app_name.lower().strip()
    proc_name = APP_PROCESS_MAP.get(app_clean, f"{app_clean}.exe")
    try:
        subprocess.run(["taskkill", "/IM", proc_name, "/F"], capture_output=True, check=False)
        return f"Closed {app_name} for you."
    except Exception as e:
        return f"Could not close {app_name}: {e}"

# ==========================================
# Master Automation Dispatcher
# ==========================================

def handle_automation(command: str) -> str:
    """
    Executes full computer system automation:
    - Exact & relative volume, mute, brightness
    - Media playback (play, pause, next, prev)
    - Window management & multitasking
    - Browser navigation & tabs (new tab, close tab, switch tab, refresh, zoom, scroll)
    - Keyboard typing & key presses (enter, space, select all, copy, paste, undo, save)
    - Screenshots & display sleep
    - App launching & closing (taskkill)
    - Folder shortcuts & folder creation
    - Hardware diagnostics (battery, CPU, RAM, disk, uptime, IP, top processes)
    - Power controls (lock, sleep, shutdown, restart, abort)
    """
    if not command:
        return ""

    cmd = command.lower().strip()

    # -------------------------------------------------------------
    # 1. Volume & Audio Controls
    # -------------------------------------------------------------
    target_match = re.search(
        r"(?:increase|decrease|raise|lower|reduce|set|change|turn|make|put)?\s*(?:the\s+)?(?:volume|sound)\s+(?:up\s+|down\s+)?to\s+(\d+)\s*(?:%|percent)?",
        cmd
    )
    if target_match:
        target_val = int(target_match.group(1))
        target_val = max(0, min(100, target_val))
        set_master_volume(target_val)
        return f"Volume set to {target_val} percent."

    set_direct = re.search(r"(?:set|change|make|turn)?\s*(?:the\s+)?volume\s+(?:at\s+)?(\d+)\s*(?:%|percent)?$", cmd)
    if set_direct:
        target_val = int(set_direct.group(1))
        target_val = max(0, min(100, target_val))
        set_master_volume(target_val)
        return f"Volume set to {target_val} percent."

    delta_up = re.search(r"(?:increase|raise|turn up|boost)\s+(?:the\s+)?(?:volume|sound)\s+by\s+(\d+)\s*(?:%|percent)?", cmd)
    if delta_up:
        delta = int(delta_up.group(1))
        new_vol = adjust_master_volume(delta)
        return f"Volume increased to {new_vol} percent."

    delta_down = re.search(r"(?:decrease|lower|reduce|turn down)\s+(?:the\s+)?(?:volume|sound)\s+by\s+(\d+)\s*(?:%|percent)?", cmd)
    if delta_down:
        delta = int(delta_down.group(1))
        new_vol = adjust_master_volume(-delta)
        return f"Volume decreased to {new_vol} percent."

    if any(p in cmd for p in ["volume up", "increase volume", "louder", "turn volume up", "sound up"]):
        new_vol = adjust_master_volume(10)
        return f"Volume increased to {new_vol} percent."

    if any(p in cmd for p in ["volume down", "decrease volume", "lower volume", "quieter", "turn volume down", "sound down"]):
        new_vol = adjust_master_volume(-10)
        return f"Volume decreased to {new_vol} percent."

    if any(p in cmd for p in ["what is the volume", "check volume", "current volume", "volume level"]):
        cur_vol = get_master_volume()
        return f"The current master volume is {cur_vol} percent."

    if any(p in cmd for p in ["mute audio", "mute sound", "mute volume", "unmute audio", "unmute"]):
        return toggle_master_mute()

    if cmd == "mute":
        return toggle_master_mute()

    if any(p in cmd for p in ["max volume", "maximum volume", "full volume"]):
        set_master_volume(100)
        return "Volume set to maximum."

    # -------------------------------------------------------------
    # 2. Display Brightness Controls
    # -------------------------------------------------------------
    bright_match = re.search(r"(?:set|change|turn|make)?\s*(?:the\s+)?brightness\s+(?:to\s+)?(\d+)\s*(?:%|percent)?", cmd)
    if bright_match and any(w in cmd for w in ["brightness", "screen light"]):
        level = int(bright_match.group(1))
        set_brightness(level)
        return f"Screen brightness set to {level} percent."

    if any(p in cmd for p in ["brightness up", "increase brightness", "brighter", "more brightness"]):
        current = get_brightness()
        new_b = set_brightness(current + 15)
        return f"Brightness increased to {new_b} percent."

    if any(p in cmd for p in ["brightness down", "decrease brightness", "dimmer", "lower brightness", "dim screen"]):
        current = get_brightness()
        new_b = set_brightness(current - 15)
        return f"Brightness reduced to {new_b} percent."

    if any(p in cmd for p in ["what is the brightness", "check brightness", "current brightness"]):
        b = get_brightness()
        return f"Current display brightness is {b} percent."

    # -------------------------------------------------------------
    # 3. Media Controls
    # -------------------------------------------------------------
    if any(p in cmd for p in ["play music", "pause music", "resume music", "play pause", "pause video", "resume video", "pause song"]):
        pyautogui.press('playpause')
        return "Toggled media playback."

    if any(p in cmd for p in ["next song", "next track", "skip song", "skip track"]):
        pyautogui.press('nexttrack')
        return "Skipped to the next track."

    if any(p in cmd for p in ["previous song", "previous track", "prev song"]):
        pyautogui.press('prevtrack')
        return "Playing previous track."

    if any(p in cmd for p in ["stop music", "stop video", "stop media"]):
        pyautogui.press('stop')
        return "Media playback stopped."

    # -------------------------------------------------------------
    # 4. Screenshots & Screen Display
    # -------------------------------------------------------------
    if any(p in cmd for p in ["take screenshot", "take a screenshot", "screenshot", "capture screen"]):
        pictures_dir = os.path.join(os.path.expanduser("~"), "Pictures")
        screenshots_dir = os.path.join(pictures_dir, "AurvynScreenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(screenshots_dir, filename)

        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            os.startfile(filepath)
            return "Screenshot captured and saved to your Pictures folder."
        except Exception as e:
            return f"Failed to take screenshot: {e}"

    if any(p in cmd for p in ["turn off screen", "turn off display", "sleep display"]):
        try:
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
            return "Display turned off."
        except Exception:
            return "Could not turn off display."

    # -------------------------------------------------------------
    # 5. Window Management & Multitasking
    # -------------------------------------------------------------
    if any(p in cmd for p in ["minimize all", "show desktop", "minimize windows", "hide all windows"]):
        pyautogui.hotkey('win', 'd')
        return "Showing desktop."

    if any(p in cmd for p in ["switch window", "next window", "switch app", "next app"]):
        pyautogui.hotkey('alt', 'tab')
        return "Switched window."

    if any(p in cmd for p in ["close window", "close active window", "close this window"]):
        pyautogui.hotkey('alt', 'f4')
        return "Closing active window."

    if any(p in cmd for p in ["maximize window", "maximize this window"]):
        pyautogui.hotkey('win', 'up')
        return "Maximized window."

    if any(p in cmd for p in ["minimize window", "minimize this window"]):
        pyautogui.hotkey('win', 'down')
        return "Minimized window."

    if any(p in cmd for p in ["snap window left", "snap left", "window left"]):
        pyautogui.hotkey('win', 'left')
        return "Snapped window to the left."

    if any(p in cmd for p in ["snap window right", "snap right", "window right"]):
        pyautogui.hotkey('win', 'right')
        return "Snapped window to the right."

    if any(p in cmd for p in ["task view", "virtual desktops", "show all desktops"]):
        pyautogui.hotkey('win', 'tab')
        return "Opening Task View."

    # -------------------------------------------------------------
    # 6. Browser & Web Page Navigation
    # -------------------------------------------------------------
    if any(p in cmd for p in ["new tab", "open new tab"]):
        pyautogui.hotkey('ctrl', 't')
        return "Opened a new browser tab."

    if any(p in cmd for p in ["close tab", "close this tab"]):
        pyautogui.hotkey('ctrl', 'w')
        return "Closed browser tab."

    if any(p in cmd for p in ["reopen tab", "reopen closed tab"]):
        pyautogui.hotkey('ctrl', 'shift', 't')
        return "Reopened last closed tab."

    if any(p in cmd for p in ["next tab", "switch tab"]):
        pyautogui.hotkey('ctrl', 'tab')
        return "Switched to next tab."

    if any(p in cmd for p in ["previous tab", "prev tab"]):
        pyautogui.hotkey('ctrl', 'shift', 'tab')
        return "Switched to previous tab."

    if any(p in cmd for p in ["refresh page", "reload page", "reload"]):
        pyautogui.press('f5')
        return "Refreshed page."

    if any(p in cmd for p in ["fullscreen", "full screen", "exit fullscreen"]):
        pyautogui.press('f11')
        return "Toggled fullscreen mode."

    if any(p in cmd for p in ["zoom in", "zoom page in"]):
        pyautogui.hotkey('ctrl', '=')
        return "Zoomed in."

    if any(p in cmd for p in ["zoom out", "zoom page out"]):
        pyautogui.hotkey('ctrl', '-')
        return "Zoomed out."

    if any(p in cmd for p in ["reset zoom", "normal zoom"]):
        pyautogui.hotkey('ctrl', '0')
        return "Reset page zoom."

    if any(p in cmd for p in ["scroll down", "scroll down page", "page down"]):
        pyautogui.scroll(-600)
        return "Scrolled down."

    if any(p in cmd for p in ["scroll up", "scroll up page", "page up"]):
        pyautogui.scroll(600)
        return "Scrolled up."

    # -------------------------------------------------------------
    # 7. Keyboard, Typing & Clipboard Automation
    # -------------------------------------------------------------
    type_match = re.search(r"^(?:type|write|input)\s+(.+)", cmd)
    if type_match:
        text_to_type = type_match.group(1).strip()
        time.sleep(0.3)
        pyautogui.write(text_to_type, interval=0.02)
        return f"Typed: {text_to_type}"

    if cmd in ["press enter", "hit enter"]:
        pyautogui.press('enter')
        return "Pressed Enter."

    if cmd in ["press space", "hit space"]:
        pyautogui.press('space')
        return "Pressed Space."

    if cmd in ["press escape", "press esc"]:
        pyautogui.press('esc')
        return "Pressed Escape."

    if cmd in ["press backspace", "backspace"]:
        pyautogui.press('backspace')
        return "Pressed Backspace."

    if cmd in ["press tab", "tab"]:
        pyautogui.press('tab')
        return "Pressed Tab."

    if any(p in cmd for p in ["select all", "select everything"]):
        pyautogui.hotkey('ctrl', 'a')
        return "Selected all content."

    if cmd in ["copy", "copy text", "copy that"]:
        pyautogui.hotkey('ctrl', 'c')
        return "Copied to clipboard."

    if cmd in ["paste", "paste text", "paste that"]:
        pyautogui.hotkey('ctrl', 'v')
        return "Pasted from clipboard."

    if cmd in ["cut", "cut text", "cut that"]:
        pyautogui.hotkey('ctrl', 'x')
        return "Cut to clipboard."

    if cmd in ["save file", "save document", "save"]:
        pyautogui.hotkey('ctrl', 's')
        return "File saved."

    if cmd in ["undo", "undo that"]:
        pyautogui.hotkey('ctrl', 'z')
        return "Undid last action."

    if cmd in ["redo", "redo that"]:
        pyautogui.hotkey('ctrl', 'y')
        return "Redid last action."

    if cmd in ["click", "left click"]:
        pyautogui.click()
        return "Clicked."

    if cmd in ["double click"]:
        pyautogui.doubleClick()
        return "Double clicked."

    if cmd in ["right click"]:
        pyautogui.rightClick()
        return "Right clicked."

    if any(p in cmd for p in ["read clipboard", "what is on my clipboard", "read my clipboard", "clipboard content"]):
        text = pyperclip.paste().strip()
        if not text:
            return "Your clipboard is currently empty."
        preview = text[:150] + ("..." if len(text) > 150 else "")
        return f"Your clipboard contains: {preview}"

    if any(p in cmd for p in ["clear clipboard", "empty clipboard"]):
        pyperclip.copy("")
        return "Clipboard cleared."

    # -------------------------------------------------------------
    # 8. Closing Applications & Killing Processes
    # -------------------------------------------------------------
    close_match = re.search(r"^(?:close|kill|terminate|exit)\s+(?:the\s+)?([a-zA-Z0-9_\s]+)", cmd)
    if close_match:
        app_target = close_match.group(1).strip()
        # Avoid closing Aurvyn itself via this rule
        if app_target not in ["aurvyn", "mitra", "program", "system", "everything"]:
            if app_target in APP_PROCESS_MAP or f"{app_target}.exe" in cmd:
                return kill_app_process(app_target)

    # -------------------------------------------------------------
    # 9. Launching System Tools & Settings
    # -------------------------------------------------------------
    if any(p in cmd for p in ["open settings", "windows settings"]):
        subprocess.Popen("start ms-settings:", shell=True)
        return "Opening Windows Settings."

    if any(p in cmd for p in ["open control panel"]):
        subprocess.Popen("control", shell=True)
        return "Opening Control Panel."

    if any(p in cmd for p in ["open device manager"]):
        subprocess.Popen("devmgmt.msc", shell=True)
        return "Opening Device Manager."

    if any(p in cmd for p in ["open disk management"]):
        subprocess.Popen("diskmgmt.msc", shell=True)
        return "Opening Disk Management."

    if any(p in cmd for p in ["open snipping tool", "open snip"]):
        subprocess.Popen("snippingtool", shell=True)
        return "Opening Snipping Tool."

    if any(p in cmd for p in ["open vs code", "open visual studio code"]):
        subprocess.Popen("code", shell=True)
        return "Opening Visual Studio Code."

    if any(p in cmd for p in ["open word", "open ms word"]):
        subprocess.Popen("start winword", shell=True)
        return "Opening Microsoft Word."

    if any(p in cmd for p in ["open excel", "open ms excel"]):
        subprocess.Popen("start excel", shell=True)
        return "Opening Microsoft Excel."

    if any(p in cmd for p in ["open powerpoint"]):
        subprocess.Popen("start powerpnt", shell=True)
        return "Opening Microsoft PowerPoint."

    if any(p in cmd for p in ["open chrome", "open google chrome"]):
        subprocess.Popen("start chrome", shell=True)
        return "Opening Google Chrome."

    if any(p in cmd for p in ["open edge", "open microsoft edge"]):
        subprocess.Popen("start msedge", shell=True)
        return "Opening Microsoft Edge."

    # -------------------------------------------------------------
    # 10. Folder Shortcuts & Directory Operations
    # -------------------------------------------------------------
    if any(p in cmd for p in ["open downloads", "downloads folder"]):
        os.startfile(os.path.join(os.path.expanduser("~"), "Downloads"))
        return "Opening your Downloads folder."

    if any(p in cmd for p in ["open documents", "documents folder", "my documents"]):
        os.startfile(os.path.join(os.path.expanduser("~"), "Documents"))
        return "Opening your Documents folder."

    if any(p in cmd for p in ["open pictures", "pictures folder", "my pictures"]):
        os.startfile(os.path.join(os.path.expanduser("~"), "Pictures"))
        return "Opening your Pictures folder."

    if any(p in cmd for p in ["open desktop folder", "desktop folder", "open my desktop"]):
        os.startfile(os.path.join(os.path.expanduser("~"), "Desktop"))
        return "Opening your Desktop folder."

    if any(p in cmd for p in ["open music", "music folder"]):
        os.startfile(os.path.join(os.path.expanduser("~"), "Music"))
        return "Opening your Music folder."

    if any(p in cmd for p in ["open videos", "videos folder"]):
        os.startfile(os.path.join(os.path.expanduser("~"), "Videos"))
        return "Opening your Videos folder."

    if any(p in cmd for p in ["open c drive", "open drive c", "open main drive"]):
        os.startfile("C:\\")
        return "Opening C Drive."

    # Create folder automation
    mkdir_match = re.search(r"(?:create|make|new)\s+folder\s+(?:called\s+|named\s+)?([a-zA-Z0-9_\-\s]+)", cmd)
    if mkdir_match and not any(w in cmd for w in ["open", "delete", "remove"]):
        folder_name = mkdir_match.group(1).strip()
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        new_path = os.path.join(desktop, folder_name)
        try:
            os.makedirs(new_path, exist_ok=True)
            os.startfile(new_path)
            return f"Created folder '{folder_name}' on your Desktop."
        except Exception as e:
            return f"Could not create folder: {e}"

    # -------------------------------------------------------------
    # 11. Hardware, Network & Diagnostics
    # -------------------------------------------------------------
    if any(p in cmd for p in ["battery percentage", "battery status", "battery level", "how much battery"]):
        battery = psutil.sensors_battery()
        if battery:
            status = "plugged in and charging" if battery.power_plugged else "on battery power"
            return f"Your battery is at {battery.percent} percent, and {status}."
        return "Battery information is unavailable on this device."

    if any(p in cmd for p in ["cpu usage", "cpu level", "processor usage"]):
        cpu = psutil.cpu_percent(interval=0.5)
        return f"Current CPU usage is {cpu} percent."

    if any(p in cmd for p in ["ram usage", "memory usage", "ram level"]):
        ram = psutil.virtual_memory().percent
        return f"Current RAM usage is {ram} percent."

    if any(p in cmd for p in ["system status", "system stats", "pc status", "computer status"]):
        cpu = psutil.cpu_percent(interval=0.3)
        ram = psutil.virtual_memory().percent
        battery = psutil.sensors_battery()
        bat_str = f", and battery is at {battery.percent}%" if battery else ""
        return f"System status: CPU usage is {cpu} percent, RAM usage is {ram} percent{bat_str}."

    if any(p in cmd for p in ["disk space", "storage space", "free storage", "hard drive space"]):
        disk = psutil.disk_usage('C:\\')
        free_gb = round(disk.free / (1024**3), 1)
        total_gb = round(disk.total / (1024**3), 1)
        return f"You have {free_gb} gigabytes free out of {total_gb} gigabytes on your main drive."

    if any(p in cmd for p in ["system uptime", "uptime", "how long has the pc been on"]):
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        hours, rem = divmod(int(uptime.total_seconds()), 3600)
        minutes, _ = divmod(rem, 60)
        return f"Your computer has been running for {hours} hours and {minutes} minutes."

    if any(p in cmd for p in ["ip address", "my ip", "what is my ip", "local ip"]):
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            return f"Your local IP address is {local_ip}."
        except Exception:
            return "Could not retrieve IP address."

    if any(p in cmd for p in ["wifi settings", "open wifi", "network settings"]):
        subprocess.Popen("start ms-settings:network-wifi", shell=True)
        return "Opening Wi-Fi settings."

    if any(p in cmd for p in ["bluetooth settings", "open bluetooth"]):
        subprocess.Popen("start ms-settings:bluetooth", shell=True)
        return "Opening Bluetooth settings."

    if any(p in cmd for p in ["top processes", "running apps", "what apps are running"]):
        try:
            procs = sorted(psutil.process_iter(['name', 'cpu_percent']), key=lambda p: p.info['cpu_percent'] or 0, reverse=True)[:3]
            names = [p.info['name'] for p in procs if p.info['name']]
            return f"Top active processes are: {', '.join(names)}."
        except Exception:
            return "Could not retrieve running processes."

    # -------------------------------------------------------------
    # 12. Power, Security & Maintenance
    # -------------------------------------------------------------
    if any(p in cmd for p in ["lock computer", "lock pc", "lock screen", "lock workstation"]):
        try:
            ctypes.windll.user32.LockWorkStation()
            return "Locking your computer."
        except Exception as e:
            return f"Could not lock computer: {e}"

    if any(p in cmd for p in ["sleep computer", "put computer to sleep", "sleep pc"]):
        try:
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return "Putting your computer to sleep."
        except Exception as e:
            return f"Could not sleep computer: {e}"

    if any(p in cmd for p in ["shutdown computer", "turn off computer", "turn off pc", "shutdown pc"]):
        subprocess.Popen("shutdown /s /t 30", shell=True)
        return "Computer shutdown scheduled in 30 seconds. Say 'abort shutdown' to cancel."

    if any(p in cmd for p in ["restart computer", "reboot computer", "reboot pc"]):
        subprocess.Popen("shutdown /r /t 30", shell=True)
        return "Computer restart scheduled in 30 seconds. Say 'abort shutdown' to cancel."

    if any(p in cmd for p in ["abort shutdown", "cancel shutdown", "stop shutdown"]):
        subprocess.Popen("shutdown /a", shell=True)
        return "Shutdown has been cancelled."

    if any(p in cmd for p in ["empty recycle bin", "clean recycle bin", "empty trash"]):
        try:
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
            return "Recycle bin has been emptied."
        except Exception as e:
            return f"Could not empty recycle bin: {e}"

    return ""
