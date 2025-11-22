# -*- coding: utf-8 -*-
"""
Skill Registry - Stage 2 Mk.II STABLE
All working skills, smart_home removed temporarily
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
        self.failed_skills: Dict[str, str] = {}  # Track failed skills
        self.logger = logging.getLogger(__name__)

        self._load_all_skills()

    def _load_all_skills(self):
        """Load all skills from the skills directory."""
        if not os.path.exists(self.skills_dir):
            self.logger.error(f"Skills directory not found at: {self.skills_dir}")
            return

        # ========== STAGE 1: ESSENTIAL SKILLS ==========
        stage1_skills = [
            'sebas.skills.system_skill',
            'sebas.skills.app_skill',
            'sebas.skills.network_skill',
            'sebas.skills.datetime_skill',
        ]
        
        # ========== STAGE 2: CORE SKILLS ==========
        stage2_core_skills = [
            'sebas.skills.volume_skill',         # Volume control
            'sebas.skills.storage_skill',        # Disk space management
            'sebas.skills.security_skill',       # Windows Defender
            'sebas.skills.service_skill',        # Windows Services
            'sebas.skills.monitoring_skill',     # System monitoring (FIXED)
            'sebas.skills.file_skill',           # Advanced file operations
            'sebas.skills.personality_skill',    # Personality mode switching
        ]
        
        # ========== STAGE 2: ADVANCED SKILLS ==========
        stage2_advanced_skills = [
            # 'sebas.skills.smart_home_skill',   # REMOVED - Not ready
            'sebas.skills.ai_analytics_skill',   # AI-powered analytics
            'sebas.skills.compliance_skill',     # Compliance & auditing
            'sebas.skills.code_skill',           # Voice-to-code generation
            'sebas.skills.automation_skill',     # Workflows & automation
            'sebas.skills.nlu_skill',            # Enhanced NLU (FIXED)
            'sebas.skills.ad_skill',             # Active Directory (optional)
        ]
        
        # Combine all skills
        all_skills = stage1_skills + stage2_core_skills + stage2_advanced_skills

        # Load skills with detailed logging
        self.logger.info("=" * 60)
        self.logger.info("SEBAS SKILL LOADING - STAGE 2 Mk.II STABLE")
        self.logger.info("=" * 60)
        
        loaded_count = 0
        failed_count = 0
        
        for module_name in all_skills:
            try:
                self._load_skill_module(module_name)
                loaded_count += 1
            except Exception as e:
                skill_name = module_name.split('.')[-1]
                self.failed_skills[skill_name] = str(e)
                self.logger.warning(f"  ✗ Failed to load {skill_name}: {e}")
                failed_count += 1

        # Summary
        self.logger.info("=" * 60)
        self.logger.info(f"✓ Loaded: {loaded_count} skills")
        if failed_count > 0:
            self.logger.warning(f"✗ Failed: {failed_count} skills")
        self.logger.info(f"Total Intents: {len(self.get_all_intents())}")
        self.logger.info("=" * 60)

    def _load_skill_module(self, module_name: str):
        """Load a skill module and instantiate its class."""
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None or spec.loader is None:
                raise ImportError(f"Module not found: {module_name}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            skill_class = None
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BaseSkill) and obj is not BaseSkill:
                    skill_class = obj
                    break

            if skill_class is None:
                raise ValueError(f"No BaseSkill subclass found in {module_name}")

            # Instantiate with assistant reference
            skill_instance = skill_class(self.assistant)
            self.skills.append(skill_instance)
            
            intent_count = len(skill_instance.get_intents())
            self.logger.info(f"  ✓ {skill_class.__name__}: {intent_count} intents")

        except Exception as e:
            self.logger.error(f"  ✗ Error loading {module_name}: {e}")
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
        Supports both old (2-arg) and new (3-arg) handle signatures.
        """
        skill = self.get_skill_for_intent(intent)
        if skill:
            try:
                # Check signature compatibility
                sig = inspect.signature(skill.handle)
                params = list(sig.parameters.keys())
                
                # Count params (excluding 'self')
                param_count = len([p for p in params if p != 'self'])
                
                if param_count >= 3:
                    # New style: handle(self, intent, slots, sebas)
                    return skill.handle(intent, slots, self.assistant)  # type: ignore
                else:
                    # Old style: handle(self, intent, slots) - uses self.assistant
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
                self.logger.info(f"Skill {skill_name} {'enabled' if enabled else 'disabled'}")
                break

    def get_skill_info(self) -> Dict[str, Any]:
        """Return detailed info about all loaded skills."""
        info = {}
        for skill in self.skills:
            info[skill.__class__.__name__] = {
                'enabled': skill.is_enabled(),
                'intents': skill.get_intents(),
                'intent_count': len(skill.get_intents()),
                'description': skill.get_description()
            }
        return info
    
    def get_skill_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of skill system.
        
        Returns:
            Dict with statistics and details
        """
        enabled_skills = [s for s in self.skills if s.is_enabled()]
        disabled_skills = [s for s in self.skills if not s.is_enabled()]
        
        all_intents = []
        for skill in enabled_skills:
            all_intents.extend(skill.get_intents())
        
        return {
            'stage': 'Stage 2 Mk.II Stable',
            'loaded': len(self.skills),
            'enabled': len(enabled_skills),
            'disabled': len(disabled_skills),
            'failed': len(self.failed_skills),
            'total_intents': len(all_intents),
            'unique_intents': len(set(all_intents)),
            'skills': {
                skill.__class__.__name__: {
                    'enabled': skill.is_enabled(),
                    'intents': skill.get_intents(),
                    'description': skill.get_description()
                }
                for skill in self.skills
            },
            'failures': self.failed_skills
        }