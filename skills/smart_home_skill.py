"""
Generic Smart Home skill for toggling devices.
"""

from sebas.skills.base_skill import BaseSkill
import logging

class SmartHomeSkill(BaseSkill):

    intents = [
        "smarthome_toggle"
    ]

    def handle(self, intent_name: str, slots: dict, sebas):
        if intent_name != "smarthome_toggle":
            return False

        device = slots.get("device")
        state = slots.get("state")

        if not device or not state:
            sebas.speak("Missing device or state.")
            return True

        logging.info(f"SmartHome: {device} -> {state}")
        sebas.speak(f"Turning {device} {state}.")
        return True