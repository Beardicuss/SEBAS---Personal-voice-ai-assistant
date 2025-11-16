# Replace skills/network_skill.py with this corrected version

import logging
import socket
import requests
from sebas.skills.base_skill import BaseSkill

class NetworkSkill(BaseSkill):
    """Handles networking utilities: IP, ping, speed test."""

    def get_intents(self) -> list:
        return [
            "get_ip_address",
            "test_network_connectivity",
            "run_speed_test",
        ]

    def handle(self, intent_name: str, slots: dict) -> bool:
        if intent_name == "get_ip_address":
            return self._ip()

        if intent_name == "test_network_connectivity":
            return self._ping()

        if intent_name == "run_speed_test":
            return self._speed()

        return False

    # -----------------------------
    def _ip(self) -> bool:
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            self.assistant.speak(f"Your IP address is {ip}.")
            return True
        except Exception as e:
            logging.error(f"[NetworkSkill] Failed to get IP: {e}")
            self.assistant.speak("I could not determine your IP.")
            return False

    def _ping(self) -> bool:
        try:
            requests.get("https://google.com", timeout=2)
            self.assistant.speak("Internet connection is active.")
            return True
        except:
            self.assistant.speak("No internet connection detected.")
            return False

    def _speed(self) -> bool:
        self.assistant.speak("Running a speed test...")
        try:
            import speedtest
            st = speedtest.Speedtest()
            dl = int(st.download() / 1_000_000)
            ul = int(st.upload() / 1_000_000)
            self.assistant.speak(f"Download {dl} megabit. Upload {ul} megabit.")
            return True
        except ImportError:
            self.assistant.speak("Speed test module not available. Install with: pip install speedtest-cli")
            return False
        except Exception as e:
            logging.error(f"[NetworkSkill] Speed test failed: {e}")
            self.assistant.speak("Speed test failed.")
            return False