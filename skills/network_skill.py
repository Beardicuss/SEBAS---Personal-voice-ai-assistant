import logging
import socket
import requests
from sebas.skills.base_skill import BaseSkill

class NetworkSkill(BaseSkill):
    """Handles networking utilities: IP, ping, speed test."""

    intents = [
        "get_ip_address",
        "test_network_connectivity",
        "run_speed_test",
    ]

    def handle(self, intent_name: str, slots: dict, sebas):
        if intent_name == "get_ip_address":
            return self._ip(sebas)

        if intent_name == "test_network_connectivity":
            return self._ping(sebas)

        if intent_name == "run_speed_test":
            return self._speed(sebas)

        return False

    # -----------------------------
    def _ip(self, sebas):
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            sebas.speak(f"Your IP address is {ip}, sir.")
            return True
        except Exception as e:
            logging.error(e)
            sebas.speak("I could not determine your IP.")
            return True

    def _ping(self, sebas):
        try:
            requests.get("https://google.com", timeout=2)
            sebas.speak("Internet connection is active.")
        except:
            sebas.speak("No internet connection detected.")
        return True

    def _speed(self, sebas):
        sebas.speak("Running a speed test...")
        try:
            import speedtest
            st = speedtest.Speedtest()
            dl = int(st.download() / 1_000_000)
            ul = int(st.upload() / 1_000_000)
            sebas.speak(f"Download {dl} megabit. Upload {ul} megabit.")
        except Exception:
            sebas.speak("Speed test module unavailable.")
        return True