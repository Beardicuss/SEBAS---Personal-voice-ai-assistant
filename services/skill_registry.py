# -*- coding: utf-8 -*-
"""
Skill Registry - Dynamically loads and manages SEBAS skills
"""

import os
import importlib.util
import inspect
from typing import List, Dict, Any, Optional
from skills.base_skill import BaseSkill
import logging


class SkillRegistry:
    """Manages the loading, registration, and execution of skills."""

    def __init__(self, assistant_ref, skills_dir: str = "skills"):
        """
        Initialize the skill registry.

        Args:
            assistant_ref: Reference to the main assistant instance
            skills_dir: Directory where skills are located
        """
        self.assistant = assistant_ref
        self.skills_dir = skills_dir
        self.skills: List[BaseSkill] = []
        self.logger = logging.getLogger(__name__)
        self._load_skills()

    def _load_skills(self):
        """Load all skills from the skills directory."""
        if not os.path.exists(self.skills_dir):
            self.logger.warning(f"Skills directory '{self.skills_dir}' does not exist")
            return

        builtin_skills = [
            'skills.system_skill',
            'skills.app_skill',
            'skills.file_skill',
            'skills.smart_home_skill',
            'skills.code_skill',
            'skills.monitoring_skill',
            # Phase 2 skills
            'skills.ad_skill',
            'skills.service_skill',
            'skills.network_skill',
            # Phase 3 skills
            'skills.storage_skill',
            # Phase 4 skills
            'skills.security_skill',
            'skills.compliance_skill',
            # Phase 5 skills
            'skills.automation_skill',
            # Phase 6 skills
            'skills.ai_analytics_skill',
            'skills.nlu_skill'
        ]

        for module_name in builtin_skills:
            try:
                self._load_skill_module(module_name)
            except Exception as e:
                self.logger.error(f"Failed to load skill {module_name}: {e}")

        # Load any extra files from the folder
        for filename in os.listdir(self.skills_dir):
            if filename.endswith('_skill.py') and filename != 'base_skill.py':
                module_name = f"skills.{filename[:-3]}"
                if module_name not in builtin_skills:
                    try:
                        self._load_skill_module(module_name)
                    except Exception as e:
                        self.logger.error(f"Failed to load skill {module_name}: {e}")

    def _load_skill_module(self, module_name: str):
        """Load a skill module and instantiate its class."""
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None or spec.loader is None:
                raise ImportError(f"Failed to load module spec for {module_name}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[union-attr]

            skill_class = None
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BaseSkill) and obj is not BaseSkill:
                    skill_class = obj
                    break

            if skill_class is None:
                raise ValueError(f"No BaseSkill subclass found in {module_name}")

            skill_instance = skill_class(self.assistant)
            self.skills.append(skill_instance)
            self.logger.info(f"Loaded skill: {skill_class.__name__}")

        except Exception as e:
            self.logger.error(f"Error loading skill {module_name}: {e}")
            raise

    def get_skill_for_intent(self, intent: str) -> Optional[BaseSkill]:
        """Find a skill that can handle the given intent."""
        for skill in self.skills:
            if skill.is_enabled() and skill.can_handle(intent):
                return skill
        return None

    def handle_intent(self, intent: str, slots: Dict[str, Any]) -> bool:
        """Handle an intent using the appropriate skill."""
        skill = self.get_skill_for_intent(intent)
        if skill:
            try:
                return skill.handle(intent, slots)
            except Exception as e:
                self.logger.exception(f"Error in skill {skill.__class__.__name__} handling {intent}")
                return False
        return False

    def get_all_intents(self) -> List[str]:
        """Get all intents supported by enabled skills."""
        intents = []
        for skill in self.skills:
            if skill.is_enabled():
                intents.extend(skill.get_intents())
        return intents

    def get_enabled_skills(self) -> List[BaseSkill]:
        """Get all enabled skills."""
        return [skill for skill in self.skills if skill.is_enabled()]

    def enable_skill(self, skill_name: str, enabled: bool = True):
        """Enable or disable a skill by name."""
        for skill in self.skills:
            if skill.__class__.__name__ == skill_name:
                skill.set_enabled(enabled)
                if hasattr(self.assistant, 'prefs'):
                    pref_key = f"skill_{skill_name.lower()}_enabled"
                    self.assistant.prefs.set_pref(pref_key, enabled)
                break

    def load_skill_preferences(self):
        """Load skill enable/disable preferences."""
        if not hasattr(self.assistant, 'prefs'):
            return
        for skill in self.skills:
            pref_key = f"skill_{skill.__class__.__name__.lower()}_enabled"
            enabled = self.assistant.prefs.get_pref(pref_key, True)
            skill.set_enabled(enabled)

    def get_skill_info(self) -> Dict[str, Any]:
        """Return info about all loaded skills."""
        info = {}
        for skill in self.skills:
            info[skill.__class__.__name__] = {
                'enabled': skill.is_enabled(),
                'intents': skill.get_intents(),
                'description': skill.get_description()
            }
        return info
