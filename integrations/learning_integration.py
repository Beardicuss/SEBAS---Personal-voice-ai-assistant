# -*- coding: utf-8 -*-
"""
Learning System Integration
Connects self-learning to existing SEBAS architecture
FULLY FIXED VERSION - Ready for production
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime


class LearningSEBASIntegration:
    """
    Integration layer for SEBAS with learning capabilities.
    
    Usage in main.py:
    
    ```python
    from sebas.integrations.learning_system import LearningSystem, LearningNLU
    from sebas.integrations.learning_integration import LearningSEBASIntegration
    
    # Initialize learning
    learning = LearningSystem()
    learning_integration = LearningSEBASIntegration(learning, sebas_instance)
    
    # Wrap NLU with learning
    original_nlu = sebas_instance.nlu
    sebas_instance.nlu = LearningNLU(original_nlu, learning)
    ```
    """
    
    def __init__(self, learning_system, sebas_instance):
        self.learning = learning_system
        self.sebas = sebas_instance
        self.logger = logging.getLogger(__name__)
        
        # Register learning commands in NLU
        self._register_learning_commands()
        
        self.logger.info("[LearningIntegration] Initialized")
    
    def _register_learning_commands(self):
        """
        Register special learning commands that work across all intents.
        """
        # These patterns handle correction commands
        correction_patterns = [
            (r"this means (.+)", "learning_correction", 0.99),
            (r"that was (.+)", "learning_correction", 0.99),
            (r"i meant (.+)", "learning_correction", 0.99),
            (r"correct: (.+)", "learning_correction", 0.99),
            (r"actually it was (.+)", "learning_correction", 0.99),
        ]
        
        # Add to NLU patterns if possible
        if hasattr(self.sebas, 'nlu'):
            if hasattr(self.sebas.nlu, 'base_nlu'):
                # Learning-wrapped NLU
                nlu = self.sebas.nlu.base_nlu
            else:
                nlu = self.sebas.nlu
            
            if hasattr(nlu, 'patterns'):
                nlu.patterns.extend(correction_patterns)
                self.logger.info(f"[LearningIntegration] Added {len(correction_patterns)} correction patterns")
    
    def handle_learning_correction(self, text: str, matched_intent: str) -> bool:
        """
        Handle correction commands.
        
        Example:
            User: "open calculator"
            SEBAS: [doesn't understand]
            User: "this means open_application"
            → System learns: "open calculator" → open_application
        """
        # Get the last unrecognized command
        if not self.learning.misses:
            self.sebas.speak("No recent unrecognized commands to correct.")
            return False
        
        last_miss = None
        for miss in reversed(self.learning.misses):
            if not miss.get('corrected', False):
                last_miss = miss
                break
        
        if not last_miss:
            self.sebas.speak("All recent commands have been corrected.")
            return False
        
        # Apply correction
        success = self.learning.apply_correction(
            last_miss['text'],
            matched_intent
        )
        
        if success:
            self.sebas.speak(
                f"Learned! '{last_miss['text']}' will now trigger {matched_intent}."
            )
            return True
        else:
            self.sebas.speak("Failed to apply correction.")
            return False
    
    def track_skill_execution(self, intent: str, success: bool, 
                            error: Optional[str] = None):
        """
        Track skill execution for learning.
        Call this after every skill execution.
        """
        self.learning.track_skill_success(intent, success, error)
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning system statistics."""
        return self.learning.get_statistics()
    
    def auto_optimize(self) -> int:
        """
        Run automatic optimization tasks.
        
        Returns number of optimizations made.
        """
        optimizations = 0
        
        # Generate aliases from repeated corrections
        aliases_generated = self.learning.auto_generate_aliases(threshold=2)
        optimizations += aliases_generated
        
        if aliases_generated > 0:
            self.logger.info(f"[Learning] Auto-generated {aliases_generated} aliases")
        
        return optimizations
    
    def export_learning(self, path: Optional[Path] = None) -> Path:
        """Export learned data."""
        return self.learning.export_learned_data(path)
    
    def import_learning(self, path: Path) -> bool:
        """Import learned data."""
        return self.learning.import_learned_data(path)


# ============================================================
# VOICE COMMAND LEARNING HELPERS
# ============================================================

class VoiceLearningHelper:
    """
    Helpers specific to voice command learning.
    Handles STT mistakes and voice-specific patterns.
    """
    
    def __init__(self, learning_system):
        self.learning = learning_system
        self.logger = logging.getLogger(__name__)
        
        # Track STT variations
        self.stt_variations: Dict[str, List[str]] = {}
    
    def track_stt_variation(self, heard: str, intended: Optional[str] = None):
        """
        Track STT mistakes to build correction patterns.
        
        Example:
            heard: "open chrome browser"
            intended: "open chrome"
        """
        if intended:
            if intended not in self.stt_variations:
                self.stt_variations[intended] = []
            
            if heard not in self.stt_variations[intended]:
                self.stt_variations[intended].append(heard)
                
                # Auto-generate alias if this is a repeated pattern
                if len(self.stt_variations[intended]) >= 2:
                    self.learning.generate_alias(intended, heard)
    
    def get_common_stt_mistakes(self, limit: int = 10) -> List[Dict]:
        """
        Get most common STT mistakes.
        """
        mistakes = []
        
        for intended, variations in self.stt_variations.items():
            if len(variations) >= 2:
                mistakes.append({
                    'intended': intended,
                    'variations': variations,
                    'count': len(variations)
                })
        
        return sorted(mistakes, key=lambda x: x['count'], reverse=True)[:limit]


# ============================================================
# COMMAND HISTORY TRACKER
# ============================================================

class CommandHistory:
    """
    Tracks command history for context-aware learning.
    """
    
    def __init__(self, max_history: int = 100):
        self.history: List[Dict[str, Any]] = []
        self.max_history = max_history
    
    def add(self, command: str, intent: Optional[str], success: bool):
        """Add command to history."""
        entry = {
            'command': command,
            'intent': intent,
            'success': success,
            'timestamp': datetime.now().isoformat()
        }
        
        self.history.append(entry)
        
        # Keep only recent history
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_recent(self, count: int = 10) -> List[Dict]:
        """Get recent commands."""
        return self.history[-count:]
    
    def get_failed_commands(self, count: int = 10) -> List[Dict]:
        """Get recent failed commands."""
        failed = [cmd for cmd in self.history if not cmd['success']]
        return failed[-count:]
    
    def get_success_rate(self) -> float:
        """Get overall success rate."""
        if not self.history:
            return 0.0
        
        successful = sum(1 for cmd in self.history if cmd['success'])
        return successful / len(self.history)


# ============================================================
# LEARNING SKILL (for voice commands)
# ============================================================

class LearningSkill:
    """
    Skill that handles learning-related voice commands.
    
    This is a simplified skill that doesn't require BaseSkill inheritance
    because it's registered directly with the skill registry.
    
    Commands:
        - "show learning stats"
        - "optimize learning"
        - "export learning data"
        - "what did you learn"
        - "show problematic skills"
        - "list learned patterns"
    """
    
    def __init__(self, learning_integration: LearningSEBASIntegration):
        self.learning_int = learning_integration
        self.learning = learning_integration.learning
        self.sebas = learning_integration.sebas
        self.logger = logging.getLogger(__name__)
        
        self.intents = [
            'show_learning_stats',
            'optimize_learning',
            'export_learning',
            'show_recent_mistakes',
            'show_problematic_skills',
            'list_learned_patterns',
        ]
        
        self.logger.info("[LearningSkill] Initialized with intents: " + ", ".join(self.intents))
    
    def can_handle(self, intent: str) -> bool:
        """Check if this skill can handle the given intent."""
        return intent in self.intents
    
    def handle(self, intent: str, slots: Dict[str, Any]) -> bool:
        """
        Handle learning-related intents.
        
        Note: This method signature matches what SkillRegistry expects.
        It returns a boolean indicating success.
        """
        try:
            self.logger.debug(f"[LearningSkill] Handling intent: {intent}")
            
            if intent == 'show_learning_stats':
                return self._show_stats()
            
            elif intent == 'optimize_learning':
                return self._optimize()
            
            elif intent == 'export_learning':
                return self._export()
            
            elif intent == 'show_recent_mistakes':
                return self._show_mistakes()
            
            elif intent == 'show_problematic_skills':
                return self._show_problematic()
            
            elif intent == 'list_learned_patterns':
                return self._list_patterns()
            
            return False
            
        except Exception as e:
            self.logger.error(f"[LearningSkill] Error handling {intent}: {e}")
            self.logger.exception("[LearningSkill] Full traceback:")
            self.sebas.speak("An error occurred in the learning system.")
            return False
    
    def _show_stats(self) -> bool:
        """Show learning statistics."""
        try:
            stats = self.learning.get_statistics()
            
            self.sebas.speak(
                f"Learning statistics: "
                f"{stats['corrections_learned']} corrections learned, "
                f"{stats['custom_patterns']} custom patterns, "
                f"{stats['aliases']} aliases created."
            )
            
            if stats.get('frequent_commands'):
                top_3 = stats['frequent_commands'][:3]
                commands = ', '.join([f"{cmd} ({count} times)" 
                                     for cmd, count in top_3])
                self.sebas.speak(f"Most used commands: {commands}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"[LearningSkill] Error showing stats: {e}")
            self.sebas.speak("Could not retrieve learning statistics.")
            return False
    
    def _optimize(self) -> bool:
        """Run optimization."""
        try:
            self.sebas.speak("Running learning optimization...")
            
            optimizations = self.learning_int.auto_optimize()
            
            if optimizations > 0:
                self.sebas.speak(f"Created {optimizations} optimizations.")
            else:
                self.sebas.speak("No optimizations needed.")
            
            return True
            
        except Exception as e:
            self.logger.error(f"[LearningSkill] Error optimizing: {e}")
            self.sebas.speak("Optimization failed.")
            return False
    
    def _export(self) -> bool:
        """Export learning data."""
        try:
            self.sebas.speak("Exporting learning data...")
            
            export_path = self.learning_int.export_learning()
            
            self.sebas.speak(f"Learning data exported to {export_path.name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"[LearningSkill] Error exporting: {e}")
            self.sebas.speak("Export failed.")
            return False
    
    def _show_mistakes(self) -> bool:
        """Show recent unrecognized commands."""
        try:
            recent_misses = [m for m in self.learning.misses[-10:] 
                            if not m.get('corrected', False)]
            
            if not recent_misses:
                self.sebas.speak("No recent unrecognized commands.")
                return True
            
            self.sebas.speak(f"Found {len(recent_misses)} recent unrecognized commands.")
            
            for miss in recent_misses[:3]:
                self.sebas.speak(f"Did not understand: {miss['text']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"[LearningSkill] Error showing mistakes: {e}")
            self.sebas.speak("Could not retrieve mistake history.")
            return False
    
    def _show_problematic(self) -> bool:
        """Show skills with high failure rates."""
        try:
            problematic = self.learning.get_problematic_skills()
            
            if not problematic:
                self.sebas.speak("No problematic skills detected.")
                return True
            
            self.sebas.speak(f"Found {len(problematic)} skills with high failure rates.")
            
            for skill in problematic[:3]:
                self.sebas.speak(
                    f"{skill['intent']} fails "
                    f"{skill['failure_rate']*100:.0f}% of the time."
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"[LearningSkill] Error showing problematic: {e}")
            self.sebas.speak("Could not analyze skill performance.")
            return False
    
    def _list_patterns(self) -> bool:
        """List learned patterns."""
        try:
            if not hasattr(self.learning, 'patterns') or not self.learning.patterns:
                self.sebas.speak("No custom patterns learned yet.")
                return True
            
            pattern_count = len(self.learning.patterns)
            self.sebas.speak(f"I have learned {pattern_count} custom patterns.")
            
            # Show a few examples
            examples = list(self.learning.patterns.items())[:3]
            for intent, patterns in examples:
                self.sebas.speak(f"For {intent}: {len(patterns)} variations")
            
            return True
            
        except Exception as e:
            self.logger.error(f"[LearningSkill] Error listing patterns: {e}")
            self.sebas.speak("Could not list learned patterns.")
            return False


__all__ = [
    'LearningSEBASIntegration',
    'VoiceLearningHelper',
    'CommandHistory',
    'LearningSkill'
]