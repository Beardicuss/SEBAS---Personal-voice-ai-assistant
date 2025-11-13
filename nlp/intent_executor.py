import logging
from typing import Dict, Any

class IntentExecutor:
    """Executes intents using modern skills and legacy handlers."""

    def __init__(self, skill_registry, speak):
        self.skill_registry = skill_registry
        self.speak = speak

    def execute(self, intent):
        name = intent.name
        slots = intent.slots or {}

        logging.info(f"Executor handling intent: {name}")

        # 1. Skill registry
        try:
            handled = self.skill_registry.handle_intent(name, slots)
            if handled:
                return True
        except Exception:
            logging.error("Skill registry failed", exc_info=True)

        # 2. Legacy functions
        try:
            legacy = getattr(self, f"_legacy_{name}", None)
            if callable(legacy):
                legacy(slots)
                return True
        except Exception:
            logging.error("Legacy executor error", exc_info=True)

        return False