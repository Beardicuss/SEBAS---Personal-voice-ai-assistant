from sebas.skills.base_skill import BaseSkill
import logging
import subprocess
import psutil

class SystemSkill(BaseSkill):
    """Handles system-level commands: shutdown, restart, CPU, memory, status."""

    intents = [
        "shutdown_computer",
        "restart_computer",
        "get_cpu_info",
        "get_memory_info",
        "get_system_status",
    ]

    def handle(self, intent_name: str, slots: dict, sebas):
        if intent_name == "shutdown_computer":
            return self._shutdown(sebas)

        if intent_name == "restart_computer":
            return self._restart(sebas)

        if intent_name == "get_cpu_info":
            return self._cpu_info(sebas)

        if intent_name == "get_memory_info":
            return self._memory_info(sebas)

        if intent_name == "get_system_status":
            return self._system_status(sebas)

        return False

    # ---------------------------------------------------------
    # Shutdown / Restart
    # ---------------------------------------------------------
    def _shutdown(self, sebas):
        subprocess.call("shutdown /s /t 3")
        sebas.speak("Shutting down the system, sir.")
        return True

    def _restart(self, sebas):
        subprocess.call("shutdown /r /t 3")
        sebas.speak("Restarting the system, sir.")
        return True

    # ---------------------------------------------------------
    # System Information
    # ---------------------------------------------------------
    def _cpu_info(self, sebas):
        cpu = psutil.cpu_percent(interval=1)
        sebas.speak(f"CPU load is {cpu} percent.")
        return True

    def _memory_info(self, sebas):
        mem = psutil.virtual_memory()
        sebas.speak(f"Memory usage is {mem.percent} percent.")
        return True

    def _system_status(self, sebas):
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        sebas.speak(f"CPU: {cpu}%. Memory: {mem}%. All systems nominal, sir.")
        return True