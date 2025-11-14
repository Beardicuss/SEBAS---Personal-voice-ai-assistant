import logging
import importlib
import pkgutil
import inspect
from pathlib import Path

from sebas.skills.base_skill import BaseSkill


class SkillRegistry:
    """
    Skill loader with EventBus integration.

    Responsibilities:
        - auto-load skill modules
        - instantiate skills
        - register intents
        - subscribe skills to events via EventBus
    """

    def __init__(self, event_bus=None):
        self.skills = []
        self.intent_map = {}
        self.event_bus = event_bus

    # ---------------------------------------------------------
    # PUBLIC API
    # ---------------------------------------------------------
    def load_skills(self):
        """Auto-scan and auto-import all skills."""

        logging.info("Scanning for skills...")

        import sebas.skills as skills_pkg
        skills_path = Path(skills_pkg.__file__).parent

        for module_info in pkgutil.iter_modules([str(skills_path)]):
            name = module_info.name

            # Skip base class and helper files
            if name in ("__init__", "base_skill"):
                continue

            module_full = f"sebas.skills.{name}"

            try:
                module = importlib.import_module(module_full)
            except Exception as e:
                logging.error(f"Failed to import {module_full}: {e}")
                continue

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseSkill) and obj is not BaseSkill:
                    try:
                        instance = obj()
                        self._register_skill(instance)
                    except Exception as e:
                        logging.error(f"Failed to instantiate {obj.__name__}: {e}")

        logging.info(f"Total skills loaded: {len(self.skills)}")
        logging.info(f"Registered intents: {list(self.intent_map.keys())}")

    # ---------------------------------------------------------
    # INTERNAL
    # ---------------------------------------------------------
    def _register_skill(self, skill):
        self.skills.append(skill)

        # Register intents
        for intent in skill.intents:
            if intent in self.intent_map:
                logging.warning(f"Intent conflict: {intent}")
            self.intent_map[intent] = skill

        # Subscribe skill to events
        if self.event_bus and hasattr(skill, "events"):
            for event_name in skill.events:
                self.event_bus.subscribe(event_name, skill.on_event)

        logging.info(
            f"Skill loaded: {skill.__class__.__name__} "
            f"(intents={skill.intents}, events={getattr(skill, 'events', [])})"
        )

    # ---------------------------------------------------------
    # DISPATCHER
    # ---------------------------------------------------------
    def handle_intent(self, intent_name: str, slots: dict, sebas):
        skill = self.intent_map.get(intent_name)
        if not skill:
            return False

        try:
            return skill.handle(intent_name, slots, sebas)
        except Exception as e:
            logging.error(f"Skill error in {skill.__class__.__name__}: {e}")
            return False