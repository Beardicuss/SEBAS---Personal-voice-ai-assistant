# -*- coding: utf-8 -*-
"""
Skill Registry - Stage 2 Mk.II ENHANCED
Updated to load all Stage 1 + Stage 2 skills
"""

import os
import importlib.util
import inspect
from typing import List, Dict, Any, Optional
from sebas.skills.base_skill import BaseSkill
import logging

class SkillRegistry:
    """Manages the loading, registration, and execution of skills."""

    def __init__(self, assistant_ref, skills_dir: Optional[str] = None):
        """
        Initialize the skill registry.

        Args:
            assistant_ref: Reference to the main assistant instance
            skills_dir: Directory where skills are located
        """
        self.assistant = assistant_ref
        
        # Always load skills from sebas/skills
        base_dir = os.path.dirname(os.path.abspath(__file__))
        real_skills_dir = os.path.join(base_dir, "..", "skills")
        self.skills_dir = os.path.abspath(real_skills_dir)
        
        self.skills: List[BaseSkill] = []
        self.logger = logging.getLogger(__name__)

        self._load_all_skills()

    def _load_all_skills(self):
        """Load all skills from the skills directory."""
        if not os.path.exists(self.skills_dir):
            self.logger.error(f"Skills directory not found at: {self.skills_dir}")
            return

        # Stage 1: Essential skills
        stage1_skills = [
            'sebas.skills.system_skill',
            'sebas.skills.app_skill',
            'sebas.skills.network_skill',
            'sebas.skills.datetime_skill',
        ]

        # Stage 2: Extended skills
        stage2_skills = [
            'sebas.skills.volume_skill',
            'sebas.skills.storage_skill',
            'sebas.skills.monitoring_skill',
            'sebas.skills.file_skill',
            'sebas.skills.smart_home_skill',      # NEW - Stage 2
            'sebas.skills.ai_analytics_skill',    # NEW - Stage 2
            'sebas.skills.compliance_skill',      # NEW - Stage 2
        ]

        # Load all skills
        all_skills = stage1_skills + stage2_skills
        
        for module_name in all_skills:
            try:
                self._load_skill_module(module_name)
            except Exception as e:
                self.logger.warning(f"Skipping skill {module_name}: {e}")

        self.logger.info(f"✓ Loaded {len(self.skills)} skills")

    def _load_skill_module(self, module_name: str):
        """Load a skill module and instantiate its class."""
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None or spec.loader is None:
                raise ImportError(f"Failed to load module spec for {module_name}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            skill_class = None
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BaseSkill) and obj is not BaseSkill:
                    skill_class = obj
                    break

            if skill_class is None:
                raise ValueError(f"No BaseSkill subclass found in {module_name}")

            skill_instance = skill_class(self.assistant)
            self.skills.append(skill_instance)
            self.logger.info(f"  ✓ Loaded: {skill_class.__name__}")

        except Exception as e:
            self.logger.warning(f"  ✗ Failed: {module_name} - {e}")
            raise

    def get_skill_for_intent(self, intent: str) -> Optional[BaseSkill]:
        """Find a skill that can handle the given intent."""
        for skill in self.skills:
            if skill.is_enabled() and skill.can_handle(intent):
                return skill
        return None

    def handle_intent(self, intent: str, slots: Dict[str, Any]) -> bool:
        """
        Handle an intent using the appropriate skill.
        Properly passes assistant reference for backward compatibility.
        """
        skill = self.get_skill_for_intent(intent)
        if skill:
            try:
                # Check if skill.handle accepts 3 arguments (old style)
                sig = inspect.signature(skill.handle)
                params = list(sig.parameters.keys())
                
                # Check parameter count (excluding 'self')
                param_count = len(params)
                
                if param_count >= 3:  # Has intent, slots, and possibly sebas/assistant
                    # Old style: handle(self, intent, slots, sebas)
                    return skill.handle(intent, slots, self.assistant) # type: ignore
                else:
                    # New style: handle(self, intent, slots)
                    return skill.handle(intent, slots)
                    
            except Exception:
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
                break

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