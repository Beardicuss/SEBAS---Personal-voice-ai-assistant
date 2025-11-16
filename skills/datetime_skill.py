"""
Skill: Date & Time information

Intents:
- get_time
- get_date
"""

import logging
from datetime import datetime
from sebas.skills.base_skill import BaseSkill


class DateTimeSkill(BaseSkill):

    def get_intents(self) -> list:
        return ["get_time", "get_date"]

    def handle(self, intent_name: str, slots: dict) -> bool:
        now = datetime.now()

        if intent_name == "get_time":
            # Use the assistant reference passed to __init__
            self.assistant.speak(f"The time is {now.strftime('%H:%M')}.")
            return True

        if intent_name == "get_date":
            self.assistant.speak(f"Today is {now.strftime('%A, %B %d')}.")
            return True

        return False
