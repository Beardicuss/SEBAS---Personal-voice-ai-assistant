
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

    @property
    def name(self) -> str:
        return "Date & Time"

    @property
    def intents(self):
        return {
            "get_time": "Report current time",
            "get_date": "Report today's date"
        }

    def handle(self, intent_name, slots):
        now = datetime.now()

        if intent_name == "get_time":
            from sebas.main import assistant
            assistant.speak(f"The time is {now.strftime('%H:%M')}.")
            return True

        if intent_name == "get_date":
            from sebas.main import assistant
            assistant.speak(f"Today is {now.strftime('%A, %B %d')}.")
            return True

        return False