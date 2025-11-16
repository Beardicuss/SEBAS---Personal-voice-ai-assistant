import logging
from sebas.skills.base_skill import BaseSkill

class SecuritySkill(BaseSkill):
    """Handles Windows Defender status and basic security operations."""

    intents = [
        "get_defender_status",
        "run_defender_scan",
        "get_defender_threats",
    ]

    def handle(self, intent_name: str, slots: dict, sebas):

        if intent_name == "get_defender_status":
            return self._status(sebas)

        if intent_name == "run_defender_scan":
            return self._scan(sebas)

        if intent_name == "get_defender_threats":
            return self._threats(sebas)

        return False

    # -----------------------------
    def _status(self, sebas):
        try:
            import subprocess
            result = subprocess.check_output(
                ["powershell", "Get-MpComputerStatus"], text=True
            )
            sebas.speak("Defender status retrieved.")
            logging.info(result)
        except Exception as e:
            logging.error(e)
            sebas.speak("Security subsystem unavailable.")
        return True

    def _scan(self, sebas):
        sebas.speak("Starting quick scan.")
        try:
            import subprocess
            subprocess.call(["powershell", "Start-MpScan", "-ScanType", "QuickScan"])
        except Exception:
            sebas.speak("Unable to start the scan.")
        return True

    def _threats(self, sebas):
        try:
            import subprocess
            threats = subprocess.check_output(
                ["powershell", "Get-MpThreatDetection"], text=True
            )
            sebas.speak("Threat list retrieved.")
            logging.info(threats)
        except:
            sebas.speak("No threats detected.")
        return True
