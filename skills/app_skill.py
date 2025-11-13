# -*- coding: utf-8 -*-
"""
Application Skill - Handles application launching and closing with advanced features
"""

from sebas.skills.base_skill import BaseSkill
from sebas.typing import Dict, List, Any, Optional
import os
import time
import json
import threading
import subprocess
import difflib
from sebas.collections import defaultdict, Counter
import psutil
import winreg
try:
    import win32api
    import win32con
    import win32gui
    import win32process
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("Warning: pywin32 not available, some window management features disabled")


class AppSkill(BaseSkill):
    """
    Skill for handling application-related commands with advanced features.
    """

    def __init__(self, assistant_ref):
        super().__init__(assistant_ref)
        self.usage_tracker_file = os.path.join(os.path.expanduser('~'), '.sebas_app_usage.json')
        self.app_cache_file = os.path.join(os.path.expanduser('~'), '.sebas_app_cache.json')
        self.usage_stats = self._load_usage_stats()
        self.app_cache = self._load_app_cache()
        self.cache_lock = threading.RLock()
        self.usage_lock = threading.RLock()

        # App categories for discovery
        self.app_categories = {
            'browsers': ['chrome', 'firefox', 'edge', 'opera', 'safari', 'internet explorer'],
            'editors': ['notepad', 'notepad++', 'vscode', 'sublime', 'atom', 'vim', 'emacs'],
            'office': ['word', 'excel', 'powerpoint', 'outlook', 'onenote', 'access'],
            'media': ['vlc', 'mpc', 'wmplayer', 'itunes', 'spotify', 'photoshop'],
            'development': ['visual studio', 'eclipse', 'intellij', 'pycharm', 'android studio'],
            'utilities': ['calculator', 'paint', 'snipping tool', 'cmd', 'powershell']
        }

    def get_intents(self) -> List[str]:
        return [
            'open_application',
            'close_application',
            'list_programs',
            'scan_programs',
            'switch_to_app',
            'minimize_app',
            'close_app',
            'minimize_all',
            'show_desktop',
            'restore_window',
            'open_app_with_context',
            'list_frequent_apps',
            'list_apps_by_category',
            'add_app_alias',
            'search_apps'
        ]

    def can_handle(self, intent: str) -> bool:
        return intent in self.get_intents()

    def handle(self, intent: str, slots: Dict[str, Any]) -> bool:
        try:
            if intent == 'open_application':
                return self._handle_open_app(slots)
            elif intent == 'close_application':
                return self._handle_close_app(slots)
            elif intent == 'list_programs':
                self._handle_list_programs()
                return True
            elif intent == 'scan_programs':
                self._handle_scan_programs()
                return True
            elif intent == 'switch_to_app':
                return self._handle_switch_to_app(slots)
            elif intent == 'minimize_app':
                return self._handle_minimize_app(slots)
            elif intent == 'close_app':
                return self._handle_close_app(slots)  # Alias for close_application
            elif intent == 'minimize_all':
                return self._handle_minimize_all()
            elif intent == 'show_desktop':
                return self._handle_show_desktop()
            elif intent == 'restore_window':
                return self._handle_restore_window(slots)
            elif intent == 'open_app_with_context':
                return self._handle_open_app_with_context(slots)
            elif intent == 'list_frequent_apps':
                return self._handle_list_frequent_apps()
            elif intent == 'list_apps_by_category':
                return self._handle_list_apps_by_category(slots)
            elif intent == 'add_app_alias':
                return self._handle_add_app_alias(slots)
            elif intent == 'search_apps':
                return self._handle_search_apps(slots)
            return False
        except Exception as e:
            self.logger.exception(f"Error handling app intent {intent}")
            self.assistant.speak("An error occurred while executing that command")
            return False

    def _handle_open_app(self, slots: Dict[str, Any]) -> bool:
        app_name = slots.get('app_name', '')
        if app_name:
            self.assistant.open_application(app_name)
            return True
        else:
            self.assistant.speak("Please specify an application name")
            return False

    def _handle_close_app(self, slots: Dict[str, Any]) -> bool:
        app_name = slots.get('app_name', '')
        if app_name:
            self.assistant.close_application(app_name)
            return True
        else:
            self.assistant.speak("Please specify an application name")
            return False

    def _handle_list_programs(self):
        self.assistant._handle_list_programs()

    def _handle_scan_programs(self):
        self.assistant.speak("Scanning installed programs. This may take a minute.")
        count = self.assistant.scan_installed_programs()
        self._update_app_cache()
        self.assistant.speak(f"Learned {count} programs")

    # ----------------------- Advanced App Management Methods -----------------------

    def _handle_switch_to_app(self, slots: Dict[str, Any]) -> bool:
        app_name = slots.get('app_name', '')
        if app_name:
            return self._switch_to_application(app_name)
        else:
            self.assistant.speak("Please specify an application name")
            return False

    def _handle_minimize_app(self, slots: Dict[str, Any]) -> bool:
        app_name = slots.get('app_name', '')
        if app_name:
            return self._minimize_application(app_name)
        else:
            self.assistant.speak("Please specify an application name")
            return False

    def _handle_minimize_all(self) -> bool:
        try:
            if not WIN32_AVAILABLE:
                self.assistant.speak("Window management features require pywin32")
                return False
            # Minimize all windows
            win32gui.ShowWindow(win32gui.GetDesktopWindow(), win32con.SW_MINIMIZE)
            self.assistant.speak("All windows minimized")
            return True
        except Exception as e:
            self.logger.exception("Failed to minimize all windows")
            self.assistant.speak("Failed to minimize all windows")
            return False

    def _handle_show_desktop(self) -> bool:
        try:
            if not WIN32_AVAILABLE:
                self.assistant.speak("Window management features require pywin32")
                return False
            # Show desktop (minimize all)
            subprocess.run(["explorer.exe", "shell:::{3080F90D-D7AD-11D9-BD98-0000947B0257}"], check=False)
            self.assistant.speak("Showing desktop")
            return True
        except Exception as e:
            self.logger.exception("Failed to show desktop")
            self.assistant.speak("Failed to show desktop")
            return False

    def _handle_restore_window(self, slots: Dict[str, Any]) -> bool:
        app_name = slots.get('app_name', '')
        if app_name:
            return self._restore_application_window(app_name)
        else:
            self.assistant.speak("Please specify an application name")
            return False

    def _handle_open_app_with_context(self, slots: Dict[str, Any]) -> bool:
        app_name = slots.get('app_name', '')
        context = slots.get('context', '')

        if not app_name:
            self.assistant.speak("Please specify an application name")
            return False

        # Track usage
        self._track_app_usage(app_name)

        # Handle context-specific launching
        if context:
            context_lower = context.lower()
            if 'search' in context_lower and 'for' in context_lower:
                # Extract search term
                search_term = context_lower.split('search for')[-1].strip()
                if search_term:
                    return self._open_app_with_search(app_name, search_term)
            elif 'open' in context_lower and 'with' in context_lower:
                # Extract file/URL to open
                target = context_lower.split('with')[-1].strip()
                return self._open_app_with_file(app_name, target)

        # Default to regular app opening
        return self._handle_open_app(slots)

    def _handle_list_frequent_apps(self) -> bool:
        with self.usage_lock:
            if not self.usage_stats:
                self.assistant.speak("No app usage data available yet")
                return True

            # Get top 5 most used apps
            sorted_apps = sorted(self.usage_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
            if sorted_apps:
                app_names = [app[0] for app in sorted_apps]
                self.assistant.speak(f"Your most frequently used apps are: {', '.join(app_names)}")
            else:
                self.assistant.speak("No frequent apps found")
            return True

    def _handle_list_apps_by_category(self, slots: Dict[str, Any]) -> bool:
        category = slots.get('category', '').lower()
        if not category:
            available_categories = list(self.app_categories.keys())
            self.assistant.speak(f"Available categories: {', '.join(available_categories)}")
            return True

        if category in self.app_categories:
            apps_in_category = self.app_categories[category]
            available_apps = [app for app in apps_in_category if self._is_app_available(app)]
            if available_apps:
                self.assistant.speak(f"Available {category} apps: {', '.join(available_apps)}")
            else:
                self.assistant.speak(f"No {category} apps found on your system")
        else:
            self.assistant.speak(f"Category '{category}' not found")
        return True

    def _handle_add_app_alias(self, slots: Dict[str, Any]) -> bool:
        alias = slots.get('alias', '').strip()
        app_name = slots.get('app_name', '').strip()

        if not alias or not app_name:
            self.assistant.speak("Please specify both alias and application name")
            return False

        with self.cache_lock:
            if 'aliases' not in self.app_cache:
                self.app_cache['aliases'] = {}
            self.app_cache['aliases'][alias.lower()] = app_name.lower()
            self._save_app_cache()

        self.assistant.speak(f"Added alias '{alias}' for {app_name}")
        return True

    def _handle_search_apps(self, slots: Dict[str, Any]) -> bool:
        query = slots.get('query', '').lower()
        if not query:
            self.assistant.speak("Please specify what to search for")
            return False

        # Search through cached apps
        matches = []
        with self.cache_lock:
            cached_apps = self.app_cache.get('apps', {})

            # Direct matches
            if query in cached_apps:
                matches.append(query)

            # Fuzzy matches
            for app_name in cached_apps.keys():
                if query in app_name.lower():
                    matches.append(app_name)
                elif difflib.SequenceMatcher(None, query, app_name.lower()).ratio() > 0.6:
                    matches.append(app_name)

            # Alias matches
            aliases = self.app_cache.get('aliases', {})
            for alias, app_name in aliases.items():
                if query in alias:
                    matches.append(app_name)

        matches = list(set(matches))  # Remove duplicates

        if matches:
            self.assistant.speak(f"Found apps: {', '.join(matches[:10])}")
        else:
            self.assistant.speak("No apps found matching your search")
        return True
    
    # ----------------------- Helper Methods -----------------------
    
    def _load_usage_stats(self) -> Dict[str, Any]:
        try:
            if os.path.isfile(self.usage_tracker_file):
                with open(self.usage_tracker_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.exception("Failed to load usage stats")
            return {}
    
    def _save_usage_stats(self):
        try:
            with self.usage_lock:
                with open(self.usage_tracker_file, 'w', encoding='utf-8') as f:
                    json.dump(self.usage_stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.exception("Failed to save usage stats")
    
    def _load_app_cache(self) -> Dict[str, Any]:
        try:
            if os.path.isfile(self.app_cache_file):
                with open(self.app_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {'apps': {}, 'aliases': {}}
        except Exception as e:
            self.logger.exception("Failed to load app cache")
            return {'apps': {}, 'aliases': {}}
    
    def _save_app_cache(self):
        try:
            with self.cache_lock:
                with open(self.app_cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self.app_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.exception("Failed to save app cache")
    
    def _update_app_cache(self):
        """Update the app cache with current program index"""
        try:
            with self.cache_lock:
                if hasattr(self.assistant, 'program_index') and self.assistant.program_index:
                    self.app_cache['apps'] = dict(self.assistant.program_index)
                    self._save_app_cache()
        except Exception as e:
            self.logger.exception("Failed to update app cache")
    
    def _track_app_usage(self, app_name: str):
        """Track app usage for suggestions"""
        try:
            with self.usage_lock:
                app_key = app_name.lower()
                if app_key not in self.usage_stats:
                    self.usage_stats[app_key] = {'count': 0, 'last_used': 0}

                self.usage_stats[app_key]['count'] += 1
                self.usage_stats[app_key]['last_used'] = time.time()

                # Save periodically (every 10 uses)
                if self.usage_stats[app_key]['count'] % 10 == 0:
                    self._save_usage_stats()
        except Exception as e:
            self.logger.exception("Failed to track app usage")
    
    def _is_app_available(self, app_name: str) -> bool:
        """Check if an app is available on the system"""
        try:
            app_key = app_name.lower()
            # Check program index
            if hasattr(self.assistant, 'program_index') and app_key in self.assistant.program_index:
                return True

            # Check cache
            with self.cache_lock:
                if app_key in self.app_cache.get('apps', {}):
                    return True

            # Check common apps
            common_apps = {
                'notepad': 'notepad.exe',
                'calculator': 'calc.exe',
                'paint': 'mspaint.exe',
                'explorer': 'explorer.exe',
                'cmd': 'cmd.exe'
            }
            return app_key in common_apps
        except Exception:
            return False

    def _find_app_executable(self, app_name: str) -> Optional[str]:
        """Find the executable path for an app using multiple strategies"""
        try:
            app_key = app_name.lower()

            # Check aliases first
            with self.cache_lock:
                aliases = self.app_cache.get('aliases', {})
                if app_key in aliases:
                    app_key = aliases[app_key]

            # Check program index
            if hasattr(self.assistant, 'program_index') and app_key in self.assistant.program_index:
                return self.assistant.program_index[app_key]

            # Check cache
            with self.cache_lock:
                cached_apps = self.app_cache.get('apps', {})
                if app_key in cached_apps:
                    return cached_apps[app_key]

            # Check common apps
            common_apps = {
                'notepad': 'notepad.exe',
                'calculator': 'calc.exe',
                'paint': 'mspaint.exe',
                'explorer': 'explorer.exe',
                'cmd': 'cmd.exe',
                'powershell': 'powershell.exe'
            }
            if app_key in common_apps:
                return common_apps[app_key]

            # Fuzzy matching
            candidates = []
            if hasattr(self.assistant, 'program_index'):
                for name, path in self.assistant.program_index.items():
                    if app_key in name.lower() or difflib.SequenceMatcher(None, app_key, name.lower()).ratio() > 0.7:
                        candidates.append((name, path))

            if candidates:
                candidates.sort(key=lambda x: (not x[0].lower().startswith(app_key), len(x[0])))
                return candidates[0][1]

            return None
        except Exception as e:
            self.logger.exception(f"Failed to find executable for {app_name}")
            return None

    def _switch_to_application(self, app_name: str) -> bool:
        """Switch focus to a running application"""
        try:
            if not WIN32_AVAILABLE:
                self.assistant.speak("Application switching requires pywin32")
                return False

            app_key = app_name.lower()
            found = False

            def callback(hwnd, extra):
                nonlocal found
                if found:
                    return

                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    proc = psutil.Process(pid)
                    proc_name = proc.name().lower()

                    # Check if this window belongs to the target app
                    title = win32gui.GetWindowText(hwnd)
                    if (app_key in proc_name or
                        app_key in title.lower() or
                        any(app_key in alias for alias in self.app_cache.get('aliases', {}).values() if alias == app_key)):

                        if win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
                            win32gui.SetForegroundWindow(hwnd)
                            found = True
                        elif win32gui.IsIconic(hwnd):  # Minimized
                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            win32gui.SetForegroundWindow(hwnd)
                            found = True

                except Exception:
                    pass

            win32gui.EnumWindows(callback, None)

            if found:
                self.assistant.speak(f"Switched to {app_name}")
                self._track_app_usage(app_name)
                return True
            else:
                self.assistant.speak(f"{app_name} is not currently running")
                return False

        except Exception as e:
            self.logger.exception(f"Failed to switch to {app_name}")
            self.assistant.speak(f"Failed to switch to {app_name}")
            return False

    def _minimize_application(self, app_name: str) -> bool:
        """Minimize a running application"""
        try:
            if not WIN32_AVAILABLE:
                self.assistant.speak("Window management requires pywin32")
                return False

            app_key = app_name.lower()
            minimized = False

            def callback(hwnd, extra):
                nonlocal minimized
                if minimized:
                    return

                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    proc = psutil.Process(pid)
                    proc_name = proc.name().lower()

                    title = win32gui.GetWindowText(hwnd)
                    if (app_key in proc_name or
                        app_key in title.lower() or
                        any(app_key in alias for alias in self.app_cache.get('aliases', {}).values() if alias == app_key)):

                        if win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
                            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                            minimized = True

                except Exception:
                    pass

            win32gui.EnumWindows(callback, None)

            if minimized:
                self.assistant.speak(f"{app_name} minimized")
                return True
            else:
                self.assistant.speak(f"{app_name} is not currently running or visible")
                return False

        except Exception as e:
            self.logger.exception(f"Failed to minimize {app_name}")
            self.assistant.speak(f"Failed to minimize {app_name}")
            return False

    def _restore_application_window(self, app_name: str) -> bool:
        """Restore a minimized application window"""
        try:
            if not WIN32_AVAILABLE:
                self.assistant.speak("Window management requires pywin32")
                return False

            app_key = app_name.lower()
            restored = False

            def callback(hwnd, extra):
                nonlocal restored
                if restored:
                    return

                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    proc = psutil.Process(pid)
                    proc_name = proc.name().lower()

                    title = win32gui.GetWindowText(hwnd)
                    if (app_key in proc_name or
                        app_key in title.lower() or
                        any(app_key in alias for alias in self.app_cache.get('aliases', {}).values() if alias == app_key)):

                        if win32gui.IsIconic(hwnd):  # Is minimized
                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            win32gui.SetForegroundWindow(hwnd)
                            restored = True

                except Exception:
                    pass

            win32gui.EnumWindows(callback, None)

            if restored:
                self.assistant.speak(f"{app_name} restored")
                self._track_app_usage(app_name)
                return True
            else:
                self.assistant.speak(f"{app_name} is not minimized or not running")
                return False

        except Exception as e:
            self.logger.exception(f"Failed to restore {app_name}")
            self.assistant.speak(f"Failed to restore {app_name}")
            return False

    def _open_app_with_search(self, app_name: str, search_term: str) -> bool:
        """Open an app with a search term (e.g., browser with search)"""
        try:
            app_key = app_name.lower()

            if 'chrome' in app_key or 'edge' in app_key:
                # Open browser with search
                url = f"https://www.google.com/search?q={search_term}"
                import webbrowser
                webbrowser.open(url)
                self.assistant.speak(f"Opening {app_name} and searching for {search_term}")
                return True
            elif 'explorer' in app_key or 'file' in app_key:
                # Open file explorer with search
                subprocess.run(['explorer.exe', f'search-ms:query={search_term}'], check=False)
                self.assistant.speak(f"Searching files for {search_term}")
                return True
            else:
                # Default to regular app opening
                self.assistant.open_application(app_name)
                return True

        except Exception as e:
            self.logger.exception(f"Failed to open {app_name} with search")
            self.assistant.speak(f"Failed to open {app_name} with search")
            return False

    def _open_app_with_file(self, app_name: str, target: str) -> bool:
        """Open an app with a specific file or URL"""
        try:
            exe_path = self._find_app_executable(app_name)
            if not exe_path:
                self.assistant.speak(f"Could not find {app_name}")
                return False

            if 'http' in target.lower():
                # It's a URL
                import webbrowser
                webbrowser.open(target)
                self.assistant.speak(f"Opening {target} in {app_name}")
            else:
                # Assume it's a file path
                if os.path.exists(target):
                    subprocess.Popen([exe_path, target])
                    self.assistant.speak(f"Opening {os.path.basename(target)} with {app_name}")
                else:
                    self.assistant.speak(f"File {target} not found")
                    return False

            return True

        except Exception as e:
            self.logger.exception(f"Failed to open {app_name} with file")
            self.assistant.speak(f"Failed to open {app_name} with file")
            return False