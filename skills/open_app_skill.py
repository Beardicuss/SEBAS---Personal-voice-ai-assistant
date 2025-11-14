
"""
Skill: Open Applications

Handles intents:
- open_application
"""

import os
import subprocess
from sebas.skills.base_skill import BaseSkill
import logging


class OpenAppSkill(BaseSkill):

    @property
    def name(self) -> str:
        return "Open Applications"

    @property
    def intents(self):
        return {
            "open_application": "Open an installed application"
        }

    def handle(self, intent_name, slots):
        app_name = (slots.get("app_name") or "").strip()

        if not app_name:
            logging.warning("OpenAppSkill: missing app_name slot")
            return False

        logging.info(f"OpenAppSkill: launching '{app_name}'")

        try:
            subprocess.Popen(app_name)
            return True
        except Exception:
            try:
                subprocess.Popen(f"start {app_name}", shell=True)
                return True
            except Exception as e:
                logging.error(f"Failed to launch app: {e}")
                return False