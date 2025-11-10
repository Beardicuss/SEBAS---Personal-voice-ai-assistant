import os
import re
import webbrowser
import subprocess
import psutil
import logging
from datetime import datetime

# Simple app name -> launch command mapping for Windows (extend as needed)
APP_MAP = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
}

def _open_application(app_name, assistant):
    """Launch a known application or fallback to system path."""
    try:
        key = app_name.lower()
        path = APP_MAP.get(key)
        if not path:
            path = app_name  # fallback to whatever user said

        if not isinstance(path, str) or not path.strip():
            raise ValueError(f"Invalid path for {app_name}")

        subprocess.Popen([path])  # always wrap in list for safety
        assistant.speak(f"Opening {app_name}.")
    except FileNotFoundError:
        logging.exception("Application not found")
        assistant.speak(f"Cannot find {app_name} on this system.")
    except Exception as e:
        logging.exception("open_application failed")
        assistant.speak(f"Failed to open {app_name}: {e}")


def _close_application(app_name, assistant):
    closed = False
    for proc in psutil.process_iter(['name']):
        try:
            if app_name.lower() in (proc.info['name'] or '').lower():
                proc.kill()
                closed = True
        except Exception:
            continue
    if closed:
        assistant.speak(f"Closed {app_name}.")
    else:
        assistant.speak(f"No running application found with name {app_name}.")

def _web_search(query, assistant):
    url = f"https://www.google.com/search?q={query}"
    webbrowser.open(url)
    assistant.speak(f"Searching for {query}.")

def _take_screenshot(assistant):
    try:
        import pyautogui
        folder = getattr(assistant, "screenshots_folder", os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots"))
        os.makedirs(folder, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(folder, f"screenshot_{timestamp}.png")
        pyautogui.screenshot(path)
        assistant.speak(f"Screenshot saved to {path}.")
    except Exception as e:
        logging.exception("take_screenshot failed")
        assistant.speak("Screenshot failed in this environment.")

def _create_note(text, assistant):
    try:
        path = getattr(assistant, "notes_file", os.path.join(os.path.expanduser("~"), "sebas_notes.txt"))
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()}: {text}\n")
        assistant.speak("Note created.")
    except Exception:
        logging.exception("create_note failed")
        assistant.speak("Failed to create note.")

def _set_volume(level, assistant):
    """Set system master volume to given scalar (0.0–1.0)."""
    try:
        if getattr(assistant, "system", "Windows") == "Windows":
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore
            from comtypes import CLSCTX_ALL  # type: ignore
            from ctypes import cast, POINTER  # type: ignore

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)  # type: ignore[attr-defined]
            volume = cast(interface, POINTER(IAudioEndpointVolume))  # type: ignore[valid-type]
            volume.SetMasterVolumeLevelScalar(level, None)  # type: ignore[attr-defined]
            assistant.speak(f"Volume set to {int(level * 100)} percent.")
        else:
            assistant.speak("Volume control not implemented for this platform.")
    except Exception:
        logging.exception("set_volume failed")
        assistant.speak("Failed to set volume.")


def _set_brightness(level, assistant):
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(level)
        assistant.speak(f"Brightness set to {level} percent.")
    except Exception:
        logging.exception("set_brightness failed")
        assistant.speak("Failed to set brightness.")

# Basic regex-based dispatcher. Extend rules as needed.
def match_and_execute(assistant, command_text):
    if not command_text:
        return

    cmd = command_text.lower().strip()

    # open <app>
    m = re.match(r'open\s+(.+)', cmd)
    if m:
        _open_application(m.group(1).strip(), assistant)
        return

    # close <app>
    m = re.match(r'close\s+(.+)', cmd)
    if m:
        _close_application(m.group(1).strip(), assistant)
        return

    # search for <query>
    m = re.match(r'search for\s+(.+)', cmd)
    if m:
        _web_search(m.group(1).strip(), assistant)
        return

    # take a screenshot
    if 'screenshot' in cmd or 'take a screenshot' in cmd:
        _take_screenshot(assistant)
        return

    # create a note <text>
    m = re.match(r'create a note\s+(.+)', cmd)
    if m:
        _create_note(m.group(1).strip(), assistant)
        return

    # volume mute or volume <n> percent
    if 'volume' in cmd:
        if 'mute' in cmd:
            _set_volume(0.0, assistant)
            return
        m = re.search(r'volume\s+(\d{1,3})', cmd)
        if m:
            val = int(m.group(1))
            val = max(0, min(100, val))
            _set_volume(val / 100.0, assistant)
            return

    # brightness to <n>
    m = re.search(r'brightness\s+(?:to\s+)?(\d{1,3})', cmd)
    if m:
        val = int(m.group(1))
        val = max(0, min(100, val))
        _set_brightness(val, assistant)
        return

    # fallback: unknown
    assistant.speak("Sorry, I don't understand that command.")
