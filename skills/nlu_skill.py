# -*- coding: utf-8 -*-
"""
Enhanced NLU Skill
Phase 6.2: Context-aware command execution and learning
"""

from sebas.skills.base_skill import BaseSkill
from sebas.typing import Dict, Any
import logging


class NLUSkill(BaseSkill):
    """
    Skill for enhanced natural language understanding.
    """
    
    def __init__(self, assistant):
        super().__init__(assistant)
        self.intents = [
            'parse_multipart_command',
            'get_context',
            'clear_context',
            'record_correction',
            'resolve_ambiguous_intent'
        ]
        self.context_manager = None
        self.multipart_parser = None
        self.learning_system = None
        self.intent_resolver = None
        self._init_nlu()
    
    def can_handle(self, intent: str) -> bool:
        """Check if this skill can handle the intent."""
        return intent in self.intents
    
    def get_intents(self) -> list:
        """Get list of intents this skill can handle."""
        return self.intents
    
    def _init_nlu(self):
        """Initialize NLU components."""
        try:
            from sebas.integrations.nlu_enhancer import (
                ContextManager, MultiPartCommandParser,
                LearningSystem, IntentResolver
            )
            self.context_manager = ContextManager()
            self.multipart_parser = MultiPartCommandParser()
            self.learning_system = LearningSystem()
            self.intent_resolver = IntentResolver()
        except Exception:
            logging.exception("Failed to initialize NLU components")
    
    def handle(self, intent: str, slots: dict) -> bool:
        if intent == 'parse_multipart_command':
            return self._handle_parse_multipart_command(slots)
        elif intent == 'get_context':
            return self._handle_get_context()
        elif intent == 'clear_context':
            return self._handle_clear_context()
        elif intent == 'record_correction':
            return self._handle_record_correction(slots)
        elif intent == 'resolve_ambiguous_intent':
            return self._handle_resolve_ambiguous_intent(slots)
        return False
    
    def _handle_parse_multipart_command(self, slots: dict) -> bool:
        """Handle parse multipart command."""
        try:
            if not self.multipart_parser:
                self.assistant.speak("Command parser not available")
                return False
            
            command = slots.get('command', '')
            if not command:
                self.assistant.speak("Please provide a command to parse")
                return False
            
            commands = self.multipart_parser.parse_multipart_command(command)
            
            if commands:
                self.assistant.speak(f"Parsed into {len(commands)} commands")
            else:
                self.assistant.speak("Could not parse command")
            
            return len(commands) > 0
            
        except Exception:
            logging.exception("Failed to parse multipart command")
            self.assistant.speak("Failed to parse command")
            return False
    
    def _handle_get_context(self) -> bool:
        """Handle get context command."""
        try:
            if not self.context_manager:
                self.assistant.speak("Context manager not available")
                return False
            
            context = self.context_manager.get_current_context()
            recent_history = self.context_manager.get_recent_context(3)
            
            if context or recent_history:
                self.assistant.speak(f"Context retrieved. {len(recent_history)} recent conversation turns")
            else:
                self.assistant.speak("No context available")
            
            return True
            
        except Exception:
            logging.exception("Failed to get context")
            self.assistant.speak("Failed to get context")
            return False
    
    def _handle_clear_context(self) -> bool:
        """Handle clear context command."""
        try:
            if not self.context_manager:
                self.assistant.speak("Context manager not available")
                return False
            
            self.context_manager.context_stack.clear()
            self.assistant.speak("Context cleared")
            return True
            
        except Exception:
            logging.exception("Failed to clear context")
            self.assistant.speak("Failed to clear context")
            return False
    
    def _handle_record_correction(self, slots: dict) -> bool:
        """Handle record correction command."""
        try:
            if not self.learning_system:
                self.assistant.speak("Learning system not available")
                return False
            
            original_intent = slots.get('original_intent', '')
            corrected_intent = slots.get('corrected_intent', '')
            user_input = slots.get('user_input', '')
            
            if not all([original_intent, corrected_intent, user_input]):
                self.assistant.speak("Please provide original intent, corrected intent, and user input")
                return False
            
            self.learning_system.record_correction(
                original_intent=original_intent,
                corrected_intent=corrected_intent,
                original_slots=slots.get('original_slots', {}),
                corrected_slots=slots.get('corrected_slots', {}),
                user_input=user_input
            )
            
            self.assistant.speak("Correction recorded. System will learn from this.")
            return True
            
        except Exception:
            logging.exception("Failed to record correction")
            self.assistant.speak("Failed to record correction")
            return False
    
    def _handle_resolve_ambiguous_intent(self, slots: dict) -> bool:
        """Handle resolve ambiguous intent command."""
        try:
            if not self.intent_resolver:
                self.assistant.speak("Intent resolver not available")
                return False
            
            user_input = slots.get('user_input', '')
            candidates_str = slots.get('candidates', '')
            candidates = [c.strip() for c in candidates_str.split(',')] if candidates_str else []
            
            if not user_input or not candidates:
                self.assistant.speak("Please provide user input and candidate intents")
                return False
            
            resolved = self.intent_resolver.resolve_ambiguous_intent(user_input, candidates)
            
            if resolved:
                self.assistant.speak(f"Resolved to intent: {resolved}")
            else:
                self.assistant.speak("Could not resolve ambiguous intent")
            
            return resolved is not None
            
        except Exception:
            logging.exception("Failed to resolve ambiguous intent")
            self.assistant.speak("Failed to resolve intent")
            return False