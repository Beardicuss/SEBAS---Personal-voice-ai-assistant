import os
import subprocess
import logging
import winreg
from pathlib import Path
from difflib import get_close_matches
from sebas.skills.base_skill import BaseSkill

class AppSkill(BaseSkill):

    intents = [
        "open_application",
        "close_application",
        "open_app_with_context"
    ]

    # ---------------------------------------------------------
    # MAIN HANDLE
    # ---------------------------------------------------------
    def handle(self, intent_name: str, slots: dict, sebas):
        app_name = (slots.get("app_name") or "").strip().lower()
        if not app_name:
            sebas.speak("Sir, I need the application's name.")
            return True

        # Load once
        if not hasattr(self, "APP_CACHE"):
            self.APP_CACHE = self._build_app_index()

        # Fuzzy match
        exe = self._resolve_app_name(app_name)

        if not exe:
            sebas.speak(f"I couldn't find {app_name} installed, sir.")
            return True

        if intent_name in ("open_application", "open_app_with_context"):
            return self._open_app(exe, app_name, sebas)

        if intent_name == "close_application":
            return self._close_app(exe, app_name, sebas)

        return False

    # ---------------------------------------------------------
    # COMPREHENSIVE APP SCANNING
    # ---------------------------------------------------------
    def _build_app_index(self):
        logging.info("[AppSkill] Scanning installed apps...")
        app_map = {}

        # 0. Priority: Add Windows system apps explicitly first
        system_apps = {
            "notepad": r"C:\Windows\System32\notepad.exe",
            "calc": r"C:\Windows\System32\calc.exe",
            "mspaint": r"C:\Windows\System32\mspaint.exe",
            "cmd": r"C:\Windows\System32\cmd.exe",
            "explorer": r"C:\Windows\explorer.exe",
            "powershell": r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        }
        
        for name, path in system_apps.items():
            if os.path.exists(path):
                app_map[name] = path
                logging.debug(f"[AppSkill] Added system app: {name} -> {path}")

        # 1. Scan file system locations
        self._scan_filesystem(app_map)
        
        # 2. Scan Windows Registry
        self._scan_registry(app_map)
        
        # 3. Scan Microsoft Store apps
        self._scan_store_apps(app_map)

        logging.info(f"[AppSkill] Indexed {len(app_map)} apps.")
        return app_map

    def _scan_filesystem(self, app_map):
        """Scan common Windows directories for executables and shortcuts"""
        user_profile = os.environ.get("USERPROFILE", "")
        
        paths = [
            r"C:\Windows",
            r"C:\Windows\System32",
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(user_profile, "Desktop"),
            os.path.join(user_profile, "AppData", "Local", "Programs"),
            os.path.join(user_profile, "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs"),
        ]

        # Add custom locations from PATH
        path_env = os.environ.get("PATH", "")
        for p in path_env.split(os.pathsep):
            if p and os.path.isdir(p):
                paths.append(p)

        def add_entry(name, full_path):
            name = name.lower()
            # Store all variants
            if name not in app_map:
                app_map[name] = full_path
            # Also add without common suffixes
            for suffix in [" (64-bit)", " (32-bit)", " 2024", " 2023"]:
                if name.endswith(suffix.lower()):
                    clean = name.replace(suffix.lower(), "").strip()
                    if clean not in app_map:
                        app_map[clean] = full_path

        for root_path in paths:
            if not os.path.exists(root_path):
                continue
                
            try:
                for root, dirs, files in os.walk(root_path):
                    # Skip system and hidden directories
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d.lower() not in ['system32', 'winsxs']]
                    
                    for f in files:
                        if f.endswith(".exe"):
                            # Skip test executables and known problematic files
                            f_lower = f.lower()
                            if f_lower in ['te.exe', 'test.exe'] or 'taef' in f_lower:
                                continue
                            
                            name = os.path.splitext(f)[0]
                            add_entry(name, os.path.join(root, f))

                        elif f.endswith(".lnk"):
                            name = os.path.splitext(f)[0]
                            add_entry(name, os.path.join(root, f))
            except (PermissionError, OSError) as e:
                logging.debug(f"[AppSkill] Skipped {root_path}: {e}")
                continue

    def _scan_registry(self, app_map):
        """Scan Windows Registry for installed applications"""
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        ]

        for hkey, subkey_path in registry_paths:
            try:
                with winreg.OpenKey(hkey, subkey_path) as key:
                    i = 0
                    while True:
                        try:
                            app_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, app_name) as app_key:
                                try:
                                    exe_path, _ = winreg.QueryValueEx(app_key, "")
                                    if exe_path and os.path.exists(exe_path):
                                        name = os.path.splitext(app_name)[0].lower()
                                        if name not in app_map:
                                            app_map[name] = exe_path
                                except FileNotFoundError:
                                    pass
                            i += 1
                        except OSError:
                            break
            except FileNotFoundError:
                continue
            except Exception as e:
                logging.debug(f"[AppSkill] Registry scan error: {e}")

    def _scan_store_apps(self, app_map):
        """Scan Microsoft Store apps using PowerShell"""
        try:
            cmd = 'powershell -Command "Get-AppxPackage | Select-Object Name, InstallLocation"'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[3:]:  # Skip header lines
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            name = parts[0].lower().replace('.', ' ')
                            # Store apps can be launched via shell:AppsFolder
                            if name not in app_map:
                                app_map[name] = f"shell:AppsFolder\\{parts[0]}"
        except Exception as e:
            logging.debug(f"[AppSkill] Store apps scan error: {e}")

    # ---------------------------------------------------------
    # ENHANCED FUZZY RESOLUTION
    # ---------------------------------------------------------
    def _resolve_app_name(self, spoken_name: str):
        spoken_name = spoken_name.lower()
        names = list(self.APP_CACHE.keys())

        # Exact match
        if spoken_name in self.APP_CACHE:
            return self.APP_CACHE[spoken_name]

        # Partial match (contains)
        for name in names:
            if spoken_name in name or name in spoken_name:
                return self.APP_CACHE[name]

        # Fuzzy match with improved threshold
        match = get_close_matches(spoken_name, names, n=1, cutoff=0.6)
        if match:
            return self.APP_CACHE[match[0]]

        # Try common aliases (expanded for better voice recognition)
        aliases = {
            # Text Editors
            "notepad": "notepad",
            "note pad": "notepad",
            "text editor": "notepad",
            
            # Calculator
            "calculator": "calc",
            "calc": "calc",
            "calculate": "calc",
            
            # Browsers
            "chrome": "chrome",
            "google chrome": "chrome",
            "firefox": "firefox",
            "mozilla": "firefox",
            "mozilla firefox": "firefox",
            "edge": "msedge",
            "microsoft edge": "msedge",
            "browser": "msedge",
            
            # Office Apps
            "word": "winword",
            "microsoft word": "winword",
            "excel": "excel",
            "microsoft excel": "excel",
            "powerpoint": "powerpnt",
            "power point": "powerpnt",
            "microsoft powerpoint": "powerpnt",
            "outlook": "outlook",
            "microsoft outlook": "outlook",
            
            # Media Players
            "media player": "wmplayer",
            "windows media player": "wmplayer",
            "vlc": "vlc",
            
            # System Tools
            "explorer": "explorer",
            "file explorer": "explorer",
            "command prompt": "cmd",
            "cmd": "cmd",
            "terminal": "windowsterminal",
            "windows terminal": "windowsterminal",
            "powershell": "powershell",
            "power shell": "powershell",
            "paint": "mspaint",
            "ms paint": "mspaint",
            
            # Development Tools
            "vscode": "code",
            "vs code": "code",
            "visual studio code": "code",
            "code": "code",
            "visual studio": "devenv",
            
            # Gaming Platforms
            "steam": "steam",
            "epic": "epicgameslauncher",
            "epic games": "epicgameslauncher",
            "epic game": "epicgameslauncher",
        }
        
        if spoken_name in aliases:
            resolved = aliases[spoken_name]
            if resolved in self.APP_CACHE:
                return self.APP_CACHE[resolved]

        return None

    # ---------------------------------------------------------
    # OPEN APP
    # ---------------------------------------------------------
    def _open_app(self, exe_path: str, original: str, sebas):
        try:
            # Handle different launch methods
            if exe_path.startswith("shell:AppsFolder"):
                # Microsoft Store app
                subprocess.Popen(f'explorer "{exe_path}"', shell=True)
            else:
                # Regular executable or shortcut
                subprocess.Popen(exe_path, shell=True)
                
            sebas.speak(f"Opening {original}, sir.")
            return True
        except Exception as e:
            logging.error(f"[AppSkill] Failed to open '{original}': {e}")
            sebas.speak(f"I couldn't open {original}, sir.")
            return True

    # ---------------------------------------------------------
    # CLOSE APP
    # ---------------------------------------------------------
    def _close_app(self, exe_path: str, original: str, sebas):
        # Extract executable name
        if exe_path.startswith("shell:AppsFolder"):
            exe_name = exe_path.split("\\")[-1] + ".exe"
        else:
            exe_name = os.path.basename(exe_path)

        try:
            subprocess.call(f'taskkill /IM "{exe_name}" /F', shell=True)
            sebas.speak(f"{original} has been closed, sir.")
            return True
        except Exception:
            sebas.speak(f"I couldn't close {original}, sir.")
            return True