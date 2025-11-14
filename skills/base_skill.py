# -*- coding: utf-8 -*-
"""
Base Skill Class - Stage 1 Mk.I
Foundation for all SEBAS skills
"""

from typing import Dict, Any, List
import logging


class BaseSkill:
    """
    Base class for all SEBAS skills.
    Each skill must implement:
        - get_intents(): return list of supported intent names
        - can_handle(intent): check if this skill handles the intent
        - handle(intent, slots): execute the intent
    """

    def __init__(self, assistant):
        """
        Initialize skill with reference to main assistant.
        
        Args:
            assistant: Reference to main Sebas instance
        """
        self.assistant = assistant
        self.enabled = True
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_intents(self) -> List[str]:
        """
        Return list of intent names this skill handles.
        Must be overridden by subclass.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement get_intents()")

    def can_handle(self, intent: str) -> bool:
        """
        Check if this skill can handle the given intent.
        
        Args:
            intent: Intent name
            
        Returns:
            True if this skill handles the intent
        """
        return intent in self.get_intents()

    def handle(self, intent: str, slots: Dict[str, Any]) -> bool:
        """
        Execute the intent with given slots.
        Must be overridden by subclass.
        
        Args:
            intent: Intent name
            slots: Extracted parameters
            
        Returns:
            True if handled successfully
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement handle()")

    def get_description(self) -> str:
        """
        Return human-readable description of this skill.
        Can be overridden by subclass.
        """
        return self.__class__.__doc__ or "No description available"

    def is_enabled(self) -> bool:
        """Check if skill is enabled."""
        return self.enabled

    def set_enabled(self, enabled: bool):
        """Enable or disable this skill."""
        self.enabled = enabled
        self.logger.info(f"Skill {'enabled' if enabled else 'disabled'}")

    # Helper methods for common operations

    def speak(self, text: str):
        """Speak text through the assistant's TTS."""
        if self.assistant and hasattr(self.assistant, 'speak'):
            self.assistant.speak(text)
        else:
            self.logger.warning("Cannot speak: assistant has no speak method")

    def listen(self, timeout: int = 5) -> str:
        """Listen for voice input through assistant's STT."""
        if self.assistant and hasattr(self.assistant, 'listen'):
            return self.assistant.listen(timeout)
        else:
            self.logger.warning("Cannot listen: assistant has no listen method")
            return ""

    def emit_event(self, event_name: str, data: Any = None):
        """Emit event through assistant's event bus."""
        if self.assistant and hasattr(self.assistant, 'events'):
            self.assistant.events.emit(event_name, data)