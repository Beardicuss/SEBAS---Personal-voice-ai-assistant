# -*- coding: utf-8 -*-
"""
System Skill - Handles system control commands like shutdown, restart, volume, brightness
"""

from skills.base_skill import BaseSkill
from typing import Dict, List, Any
from datetime import datetime, timedelta
import re


class SystemSkill(BaseSkill):
    """
    Skill for handling system control commands.
    """

    def get_intents(self) -> List[str]:
        return [
            'shutdown_computer',
            'restart_computer',
            'schedule_shutdown',
            'lock_computer',
            'sleep_computer',
            'hibernate_computer',
            'log_off_user',
            'set_volume',
            'set_brightness',
            'get_cpu_info',
            'get_system_status',
            'get_memory_info',
            'list_processes',
            'kill_process',
            # Phase 6 additions
            'clipboard_copy',
            'clipboard_read',
            'clipboard_clear',
            'get_weather',
            'get_news',
            'set_preference',
            'get_preference',
            'list_preferences',
            # Phase 7.5 additions
            'browser_open',
            'browser_search',
            'media_play_pause',
            'media_next',
            'media_prev',
            'daily_summary'
        ]

    def can_handle(self, intent: str) -> bool:
        return intent in self.get_intents()

    def handle(self, intent: str, slots: Dict[str, Any]) -> bool:
        try:
            if intent == 'shutdown_computer':
                self._handle_shutdown()
                return True
            elif intent == 'restart_computer':
                self._handle_restart()
                return True
            elif intent == 'schedule_shutdown':
                return self._handle_schedule_shutdown(slots)
            elif intent == 'lock_computer':
                self._handle_lock()
                return True
            elif intent == 'sleep_computer':
                self._handle_sleep()
                return True
            elif intent == 'hibernate_computer':
                self._handle_hibernate()
                return True
            elif intent == 'log_off_user':
                self._handle_log_off()
                return True
            elif intent == 'set_volume':
                return self._handle_set_volume(slots)
            elif intent == 'set_brightness':
                return self._handle_set_brightness(slots)
            elif intent == 'get_cpu_info':
                self._handle_cpu_info()
                return True
            elif intent == 'get_system_status':
                self._handle_system_status()
                return True
            elif intent == 'get_memory_info':
                self._handle_memory_info()
                return True
            elif intent == 'list_processes':
                self._handle_list_processes()
                return True
            elif intent == 'kill_process':
                return self._handle_kill_process(slots)
            elif intent == 'clipboard_copy':
                return self._handle_clipboard_copy(slots)
            elif intent == 'clipboard_read':
                return self._handle_clipboard_read()
            elif intent == 'clipboard_clear':
                return self._handle_clipboard_clear()
            elif intent == 'get_weather':
                return self._handle_get_weather(slots)
            elif intent == 'get_news':
                return self._handle_get_news(slots)
            elif intent == 'set_preference':
                return self._handle_set_preference(slots)
            elif intent == 'get_preference':
                return self._handle_get_preference(slots)
            elif intent == 'list_preferences':
                return self._handle_list_preferences()
            elif intent == 'browser_open':
                return self._handle_browser_open(slots)
            elif intent == 'browser_search':
                return self._handle_browser_search(slots)
            elif intent == 'media_play_pause':
                return self._handle_media_key('play_pause')
            elif intent == 'media_next':
                return self._handle_media_key('next')
            elif intent == 'media_prev':
                return self._handle_media_key('prev')
            elif intent == 'daily_summary':
                return self._handle_daily_summary()
            return False
        except Exception:
            self.logger.exception(f"Error handling system intent {intent}")
            self.assistant.speak("An error occurred while executing that command")
            return False

    def _handle_shutdown(self):
        if self.assistant.confirm_action("Are you sure you want to shut down the computer?"):
            self.assistant.shutdown_computer()

    def _handle_restart(self):
        if self.assistant.confirm_action("Are you sure you want to restart the computer?"):
            self.assistant.restart_computer()

    def _handle_schedule_shutdown(self, slots: Dict[str, Any]) -> bool:
        try:
            minutes = slots.get('minutes', 0)
            if not isinstance(minutes, int) or not self.assistant._validate_range(minutes, 0, 10000):
                self.assistant.speak("Please specify valid minutes")
                return False
            self.assistant.schedule_shutdown(minutes)
            return True
        except Exception:
            self.assistant.speak("Please specify valid minutes")
            return False

    def _handle_lock(self):
        self.assistant.lock_computer()

    def _handle_sleep(self):
        self.assistant.sleep_computer()

    def _handle_hibernate(self):
        self.assistant.hibernate_computer()

    def _handle_log_off(self):
        if self.assistant.confirm_action("Do you want to sign out now?"):
            self.assistant.log_off_user()

    def _handle_set_volume(self, slots: Dict[str, Any]) -> bool:
        try:
            level = slots.get('level', 0.0)
            if isinstance(level, str) and level.endswith('%'):
                level = float(level[:-1]) / 100.0
            elif isinstance(level, str):
                level = float(level)
            elif isinstance(level, int):
                level = level / 100.0 if level > 1 else level

            self.assistant.set_volume(level)
            return True
        except Exception:
            self.assistant.speak("Please specify a valid volume level")
            return False

    def _handle_set_brightness(self, slots: Dict[str, Any]) -> bool:
        try:
            level = slots.get('level', 50)
            if isinstance(level, str):
                if level.lower() == 'maximum':
                    level = 100
                elif level.lower() == 'minimum':
                    level = 0
                else:
                    level = int(re.sub(r'[^\d]', '', level))

            if not self.assistant._validate_range(level, 0, 100):
                raise ValueError

            self.assistant.set_brightness(level)
            return True
        except Exception:
            self.assistant.speak("Please specify a valid brightness level")
            return False

    def _handle_cpu_info(self):
        self.assistant.get_cpu_info()

    def _handle_system_status(self):
        """Handle get system status command."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            status = f"System status: CPU {cpu:.1f}%, Memory {memory.percent:.1f}%, Disk {disk.percent:.1f}% used"
            self.assistant.speak(status)
        except Exception:
            self.assistant.speak("Unable to get system status")

    def _handle_memory_info(self):
        """Handle get memory info command."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            total_gb = memory.total / (1024**3)
            used_gb = memory.used / (1024**3)
            available_gb = memory.available / (1024**3)
            percent = memory.percent
            info = f"Memory: {percent:.1f}% used, {used_gb:.1f} GB of {total_gb:.1f} GB total, {available_gb:.1f} GB available"
            self.assistant.speak(info)
        except Exception:
            self.assistant.speak("Unable to get memory information")

    def _handle_list_processes(self):
        self.assistant.list_processes()

    def _handle_kill_process(self, slots: Dict[str, Any]) -> bool:
        proc_name = slots.get('process_name', '')
        if proc_name:
            self.assistant.kill_process(proc_name)
            return True
        else:
            self.assistant.speak("Please specify the process name to kill")
            return False

    # ----------------------- Phase 6: Clipboard -----------------------
    def _handle_clipboard_copy(self, slots: Dict[str, Any]) -> bool:
        try:
            text = (slots.get('text') or '').strip()
            if not text:
                self.assistant.speak("Please provide text to copy")
                return False
            try:
                import pyperclip
            except Exception:
                self.assistant.speak("Clipboard support not available")
                return False
            pyperclip.copy(text)
            self.assistant.speak("Copied to clipboard")
            return True
        except Exception:
            self.assistant.speak("Failed to copy to clipboard")
            return False

    def _handle_clipboard_read(self) -> bool:
        try:
            try:
                import pyperclip
            except Exception:
                self.assistant.speak("Clipboard support not available")
                return False
            text = pyperclip.paste() or ''
            if text:
                self.assistant.speak(f"Clipboard has: {text[:120]}")
            else:
                self.assistant.speak("Clipboard is empty")
            return True
        except Exception:
            self.assistant.speak("Failed to read clipboard")
            return False

    def _handle_clipboard_clear(self) -> bool:
        try:
            try:
                import pyperclip
            except Exception:
                self.assistant.speak("Clipboard support not available")
                return False
            pyperclip.copy('')
            self.assistant.speak("Clipboard cleared")
            return True
        except Exception:
            self.assistant.speak("Failed to clear clipboard")
            return False

    # ----------------------- Phase 6: News & Weather -----------------------
    def _handle_get_weather(self, slots: Dict[str, Any]) -> bool:
        try:
            city = (slots.get('city') or '').strip() or self.assistant.prefs.get_pref('weather_city', '')
            if not city:
                self.assistant.speak("Please specify a city")
                return False
            from integrations.news_weather import get_weather
            ok, data = get_weather(city)
            if not ok:
                self.assistant.speak(data.get('error', 'Failed to fetch weather'))
                return False
            self.assistant.speak(f"Weather in {data.get('city')}: {data.get('desc')}, {data.get('temp')} degrees Celsius")
            return True
        except Exception:
            self.assistant.speak("Failed to get weather")
            return False

    def _handle_get_news(self, slots: Dict[str, Any]) -> bool:
        try:
            topic = (slots.get('topic') or self.assistant.prefs.get_pref('news_topic', 'technology'))
            from integrations.news_weather import get_news
            ok, items = get_news(topic=topic)
            if not ok:
                self.assistant.speak(items[0].get('error', 'Failed to fetch news'))
                return False
            if not items:
                self.assistant.speak("No headlines found")
                return True
            titles = ', '.join(title for item in items[:3] if (title := item.get('title')) is not None)
            self.assistant.speak(f"Top headlines: {titles}")
            return True
        except Exception:
            self.assistant.speak("Failed to get news")
            return False

    # ----------------------- Phase 6: Preferences -----------------------
    def _handle_set_preference(self, slots: Dict[str, Any]) -> bool:
        key = (slots.get('key') or '').strip()
        value = slots.get('value')
        if not key:
            self.assistant.speak("Please specify a preference key")
            return False
        # Coerce common boolean strings
        if isinstance(value, str):
            val_lower = value.lower().strip()
            if val_lower in ('true', 'yes', '1', 'on'):
                value = True
            elif val_lower in ('false', 'no', '0', 'off'):
                value = False
        self.assistant.prefs.set_pref(key, value)
        self.assistant.speak("Preference saved")
        return True

    def _handle_get_preference(self, slots: Dict[str, Any]) -> bool:
        key = (slots.get('key') or '').strip()
        if not key:
            self.assistant.speak("Please specify a preference key")
            return False
        val = self.assistant.prefs.get_pref(key, None)
        self.assistant.speak(f"{key} is set to {val}")
        return True

    def _handle_list_preferences(self) -> bool:
        try:
            prefs = (self.assistant.prefs.data.get('prefs') or {})
            if not prefs:
                self.assistant.speak("No preferences set")
                return True
            keys = list(prefs.keys())[:10]
            self.assistant.speak(f"Preferences include: {', '.join(keys)}")
            return True
        except Exception:
            self.assistant.speak("Failed to list preferences")
            return False

    # ----------------------- Phase 7.5: Browser -----------------------
    def _handle_browser_open(self, slots: Dict[str, Any]) -> bool:
        try:
            import webbrowser
            url = (slots.get('url') or '').strip()
            if not url:
                self.assistant.speak("Please specify a URL")
                return False
            if not (url.startswith('http://') or url.startswith('https://')):
                url = 'https://' + url
            webbrowser.open(url)
            self.assistant.speak("Opening browser")
            return True
        except Exception:
            self.assistant.speak("Failed to open browser")
            return False

    def _handle_browser_search(self, slots: Dict[str, Any]) -> bool:
        try:
            import webbrowser
            query = (slots.get('query') or '').strip()
            engine = (slots.get('engine') or self.assistant.prefs.get_pref('search_engine', 'google')).lower()
            if not query:
                self.assistant.speak("Please specify a search query")
                return False
            if engine == 'bing':
                url = f"https://www.bing.com/search?q={query}"
            elif engine == 'duckduckgo':
                url = f"https://duckduckgo.com/?q={query}"
            elif engine == 'wikipedia':
                url = f"https://en.wikipedia.org/wiki/Special:Search?search={query}"
            else:
                url = f"https://www.google.com/search?q={query}"
            webbrowser.open(url)
            self.assistant.speak(f"Searching for {query}")
            return True
        except Exception:
            self.assistant.speak("Failed to search")
            return False

    # ----------------------- Phase 7.5: Media Keys -----------------------
    def _handle_media_key(self, which: str) -> bool:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            MAP = {
                'play_pause': 0xB3,
                'next': 0xB0,
                'prev': 0xB1,
            }
            vk = MAP.get(which)
            if not vk:
                return False
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, 2, 0)
            self.assistant.speak("Done")
            return True
        except Exception:
            self.assistant.speak("Media control failed")
            return False

    # ----------------------- Phase 7.5: Daily Summary -----------------------
    def _handle_daily_summary(self) -> bool:
        try:
            # System health
            try:
                import psutil
                cpu = psutil.cpu_percent(interval=0.5)
                mem = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent
                sys_text = f"CPU {cpu:.0f} percent, memory {mem:.0f} percent, disk {disk:.0f} percent."
            except Exception:
                sys_text = "System health unavailable."

            # Weather
            weather_text = "Weather unavailable."
            try:
                city = self.assistant.prefs.get_pref('weather_city', '')
                if city:
                    from integrations.news_weather import get_weather
                    ok, w = get_weather(city)
                    if ok:
                        weather_text = f"Weather in {w.get('city')}: {w.get('desc')}, {w.get('temp')}°C."
            except Exception:
                pass

            # Calendar events today
            cal_text = "No calendar info."
            try:
                from integrations.calendar_client import list_events
                start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=1)
                ok, items = list_events('microsoft', start.strftime('%Y-%m-%dT%H:%M:%S'), end.strftime('%Y-%m-%dT%H:%M:%S'), top=5)
                if ok and items:
                    titles = ', '.join((i.get('subject') or 'Untitled') for i in items[:3])
                    cal_text = f"Today's events: {titles}."
                elif ok:
                    cal_text = "You have no events today."
            except Exception:
                pass

            self.assistant.speak(f"Daily brief: {sys_text} {weather_text} {cal_text}")
            return True
        except Exception:
            self.assistant.speak("Failed to produce daily summary")
            return False
