from sebas.skills.base_skill import BaseSkill
import subprocess
import logging

class AppSkill(BaseSkill):
    """Skill for opening or closing applications."""

    intents = [
        "open_application",
        "close_application",
        "open_app_with_context"
    ]

    def handle(self, intent_name: str, slots: dict, sebas):
        app_name = (slots.get("app_name") or "").strip().lower()
        if not app_name:
            sebas.speak("Sir, I need the name of the application.")
            return True

        if intent_name in ("open_application", "open_app_with_context"):
            return self._open_app(app_name, sebas)

        if intent_name == "close_application":
            return self._close_app(app_name, sebas)

        return False

    # ---------------------------------------------------------
    # Application Launch
    # ---------------------------------------------------------
    def _open_app(self, app_name: str, sebas):
        """Launch an application via subprocess."""
        try:
            subprocess.Popen(app_name)
            sebas.speak(f"Opening {app_name}, sir.")
            return True
        except Exception as e:
            logging.error(f"Failed to open app: {e}")
            sebas.speak(f"Unable to open {app_name}.")
            return True

    # ---------------------------------------------------------
    # Application Close
    # ---------------------------------------------------------
    def _close_app(self, app_name: str, sebas):
        """Terminate application using taskkill."""
        try:
            subprocess.call(f"taskkill /IM {app_name}.exe /F", shell=True)
            sebas.speak(f"{app_name} has been closed.")
            return True
        except Exception:
            sebas.speak(f"I could not close {app_name}.")
            return True