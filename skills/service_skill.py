import logging
import subprocess
from sebas.skills.base_skill import BaseSkill

class ServiceSkill(BaseSkill):
    """Manages Windows services."""

    intents = [
        "start_service",
        "stop_service",
        "restart_service",
        "get_service_status",
    ]

    def handle(self, intent_name: str, slots: dict, sebas):

        name = slots.get("name")

        if not name:
            sebas.speak("Which service, sir?")
            return True

        if intent_name == "start_service":
            return self._start(name, sebas)

        if intent_name == "stop_service":
            return self._stop(name, sebas)

        if intent_name == "restart_service":
            return self._restart(name, sebas)

        if intent_name == "get_service_status":
            return self._status(name, sebas)

        return False

    # -----------------------------
    def _start(self, name, sebas):
        subprocess.call(["sc", "start", name])
        sebas.speak(f"Service {name} started.")
        return True

    def _stop(self, name, sebas):
        subprocess.call(["sc", "stop", name])
        sebas.speak(f"Service {name} stopped.")
        return True

    def _restart(self, name, sebas):
        subprocess.call(["sc", "stop", name])
        subprocess.call(["sc", "start", name])
        sebas.speak(f"Service {name} restarted.")
        return True

    def _status(self, name, sebas):
        result = subprocess.check_output(["sc", "query", name], text=True)
        logging.info(result)
        sebas.speak(f"Status for {name} retrieved.")
        return True
