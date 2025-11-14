import shutil
import logging
from sebas.skills.base_skill import BaseSkill

class StorageSkill(BaseSkill):
    """Handles disk and storage queries."""

    intents = [
        "check_disk_space",
        "get_disk_info",
    ]

    def handle(self, intent_name: str, slots: dict, sebas):

        if intent_name == "check_disk_space":
            return self._space(sebas)

        if intent_name == "get_disk_info":
            return self._info(sebas)

        return False

    # -----------------------------
    def _space(self, sebas):
        total, used, free = shutil.disk_usage("/")
        percent = int(used / total * 100)
        sebas.speak(f"Disk usage is {percent} percent.")
        return True

    def _info(self, sebas):
        sebas.speak("Disk information module is not implemented yet, sir.")
        return True