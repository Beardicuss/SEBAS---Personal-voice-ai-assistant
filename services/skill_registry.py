# -*- coding: utf-8 -*-
"""
Skill Registry - Stage 2 Mk.II ENHANCED
Loads all Stage 1 + Stage 2 skills with dependency management
"""

import os
import importlib.util
import inspect
from typing import List, Dict, Any, Optional, Set
from sebas.skills.base_skill import BaseSkill
import logging


class SkillRegistry:
    """Enhanced skill registry with Stage 2 support and dependency resolution."""

    def __init__(self, assistant_ref, skills_dir: Optional[str] = None):
        self.assistant = assistant_ref
        
        # Always load skills from sebas/skills
        base_dir = os.path.dirname(os.path.abspath(__file__))
        real_skills_dir = os.path.join(base_dir, "..", "skills")
        self.skills_dir = os.path.abspath(real_skills_dir)
        
        self.skills: List[BaseSkill] = []
        self.failed_skills: Dict[str, str] = {}  # skill_name -> error message
        self.logger = logging.getLogger(__name__)

        self._load_all_skills()

    def _load_all_skills(self):
        """Load skills in dependency order."""
        
        # Stage 1: Essential skills (no external dependencies)
        stage1_core = [
            'sebas.skills.system_skill',      # System commands
            'sebas.skills.datetime_skill',    # Date/time info
        ]
        
        # Stage 1: Basic skills (minimal dependencies)
        stage1_basic = [
            'sebas.skills.app_skill',         # App launcher
            'sebas.skills.network_skill',     # Network info
            'sebas.skills.volume_skill',      # Volume control (needs pycaw)
            'sebas.skills.storage_skill',     # Disk info
        ]
        
        # Stage 2: Extended skills (service management)
        stage2_services = [
            'sebas.skills.service_skill',     # Windows services
            'sebas.skills.security_skill',    # Windows Defender
        ]
        
        # Stage 2: Advanced skills (complex integrations)
        stage2_advanced = [
            'sebas.skills.monitoring_skill',  # System monitoring
            'sebas.skills.file_skill',        # Advanced file ops
            'sebas.skills.automation_skill',  # Workflows & tasks
        ]
        
        # Stage 2: Enterprise skills (optional, may fail gracefully)
        stage2_enterprise = [
            'sebas.skills.smart_home_skill',  # Smart home control
            'sebas.skills.ai_analytics_skill',# AI predictions
            'sebas.skills.compliance_skill',  # Audit & compliance
            'sebas.skills.code_skill',        # Voice-to-code
            'sebas.skills.nlu_skill',         # Enhanced NLU
            'sebas.skills.ad_skill',          # Active Directory (optional)
        ]
        
        # Load in stages
        all_skill_groups = [
            ('Core', stage1_core),
            ('Basic', stage1_basic),
            ('Services', stage2_services),
            ('Advanced', stage2_advanced),
            ('Enterprise', stage2_enterprise),
        ]
        
        for group_name, skill_list in all_skill_groups:
            self.logger.info(f"Loading {group_name} skills...")
            for module_name in skill_list:
                try:
                    self._load_skill_module(module_name)
                except Exception as e:
                    skill_name = module_name.split('.')[-1]
                    self.failed_skills[skill_name] = str(e)
                    self.logger.warning(f"  ✗ {skill_name}: {e}")

        self.logger.info(f"✓ Loaded {len(self.skills)} skills successfully")
        if self.failed_skills:
            self.logger.warning(f"✗ {len(self.failed_skills)} skills failed to load")

    def _load_skill_module(self, module_name: str):
        """Load a skill module with enhanced error handling."""
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

            # Try to instantiate the skill
            skill_instance = skill_class(self.assistant)
            
            # Verify skill has intents
            if not skill_instance.get_intents():
                raise ValueError(f"Skill has no intents defined")
            
            self.skills.append(skill_instance)
            self.logger.info(f"  ✓ {skill_class.__name__} ({len(skill_instance.get_intents())} intents)")

        except ImportError as e:
            raise ImportError(f"Failed to import: {str(e)}")
        except AttributeError as e:
            raise AttributeError(f"Missing attribute: {str(e)}")
        except Exception as e:
            raise Exception(f"Initialization failed: {str(e)}")

    def get_skill_for_intent(self, intent: str) -> Optional[BaseSkill]:
        """Find a skill that can handle the given intent."""
        for skill in self.skills:
            if skill.is_enabled() and skill.can_handle(intent):
                return skill
        return None

    def handle_intent(self, intent: str, slots: Dict[str, Any]) -> bool:
        """Handle an intent with backward compatibility."""
        skill = self.get_skill_for_intent(intent)
        if skill:
            try:
                # Check signature for backward compatibility
                sig = inspect.signature(skill.handle)
                params = list(sig.parameters.keys())
                
                if len(params) >= 3:
                    # Old style: handle(self, intent, slots, sebas)
                    return skill.handle(intent, slots, self.assistant)
                else:
                    # New style: handle(self, intent, slots)
                    return skill.handle(intent, slots)
                    
            except Exception:
                self.logger.exception(f"Error in {skill.__class__.__name__}")
                return False
        return False

    def get_all_intents(self) -> List[str]:
        """Get all intents from enabled skills."""
        intents = []
        for skill in self.skills:
            if skill.is_enabled():
                intents.extend(skill.get_intents())
        return intents

    def get_skill_status(self) -> Dict[str, Any]:
        """Get detailed status of all skills."""
        return {
            'loaded': len(self.skills),
            'failed': len(self.failed_skills),
            'total_intents': len(self.get_all_intents()),
            'skills': {
                skill.__class__.__name__: {
                    'enabled': skill.is_enabled(),
                    'intents': len(skill.get_intents()),
                    'description': skill.get_description()
                }
                for skill in self.skills
            },
            'failures': self.failed_skills
        }

    def enable_skill(self, skill_name: str, enabled: bool = True):
        """Enable or disable a skill by name."""
        for skill in self.skills:
            if skill.__class__.__name__ == skill_name:
                skill.set_enabled(enabled)
                self.logger.info(f"Skill {skill_name} {'enabled' if enabled else 'disabled'}")
                return True
        return False