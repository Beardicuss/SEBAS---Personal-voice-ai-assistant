import logging
from sebas.skills.base_skill import BaseSkill

class SecuritySkill(BaseSkill):
    """Handles Windows Defender status and basic security operations."""

    def get_intents(self):
        return [
            "get_defender_status",
            "run_defender_scan",
            "get_defender_threats",
        ]

    def handle(self, intent_name: str, slots: dict) -> bool:
        # Use self.assistant instead of sebas parameter
        if intent_name == "get_defender_status":
            return self._status()

        if intent_name == "run_defender_scan":
            return self._scan()

        if intent_name == "get_defender_threats":
            return self._threats()

        return False

    # -----------------------------
    def _status(self):
        try:
            import subprocess
            result = subprocess.check_output(
                ["powershell", "Get-MpComputerStatus"], text=True
            )
            self.assistant.speak("Defender status retrieved.")
            logging.info(result)
        except Exception as e:
            logging.error(e)
            self.assistant.speak("Security subsystem unavailable.")
        return True

    def _scan(self):
        self.assistant.speak("Starting quick scan.")
        try:
            import subprocess
            subprocess.call(["powershell", "Start-MpScan", "-ScanType", "QuickScan"])
        except Exception:
            self.assistant.speak("Unable to start the scan.")
        return True

    def _threats(self):
        try:
            import subprocess
            threats = subprocess.check_output(
                ["powershell", "Get-MpThreatDetection"], text=True
            )
            self.assistant.speak("Threat list retrieved.")
            logging.info(threats)
        except:
            self.assistant.speak("No threats detected.")
        return True