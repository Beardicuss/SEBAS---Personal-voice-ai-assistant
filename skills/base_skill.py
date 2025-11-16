"""
Base Skill Class - Stage 1 Mk.I
Unified interface supporting both legacy and new skill patterns.
"""

import logging


class BaseSkill:
    """
    Base class for all SEBAS skills.
    
    Subclasses can define intents in two ways:
    1. Legacy: intents = ["intent1", "intent2"]  (class attribute)
    2. New: def get_intents(self) -> list  (method)
    """
    
    # Legacy support - override in subclasses
    intents = []
    events = []
    
    def __init__(self, assistant_ref):
        """
        Initialize skill with reference to main assistant.
        
        Args:
            assistant_ref: Reference to Sebas instance
        """
        self.assistant = assistant_ref
        self.logger = logging.getLogger(self.__class__.__name__)
        self._enabled = True
    
    def get_intents(self) -> list:
        """
        Get list of intents this skill can handle.
        
        Returns:
            List of intent names (strings)
        """
        # Support both patterns
        if hasattr(self, 'intents'):
            intents = self.intents
            
            # Handle dict format (old pattern from some skills)
            if isinstance(intents, dict):
                return list(intents.keys())
            
            # Handle list format
            if isinstance(intents, list):
                return intents
        
        # Default: empty list
        return []
    
    def can_handle(self, intent_name: str) -> bool:
        """
        Check if this skill can handle the given intent.
        
        Args:
            intent_name: Name of the intent
            
        Returns:
            True if skill can handle this intent
        """
        return intent_name in self.get_intents()
    
    def handle(self, intent_name: str, slots: dict) -> bool:
        """
        Handle an intent. Must be overridden by subclasses.
        
        Args:
            intent_name: Name of the intent
            slots: Dictionary of extracted parameters
            
        Returns:
            True if handled successfully, False otherwise
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement handle()"
        )
    
    def on_event(self, event_name: str, data):
        """
        Handle an event. Override in subclasses if needed.
        
        Args:
            event_name: Name of the event
            data: Event data payload
        """
        pass
    
    def is_enabled(self) -> bool:
        """Check if skill is enabled."""
        return self._enabled
    
    def set_enabled(self, enabled: bool):
        """Enable or disable the skill."""
        self._enabled = enabled
        status = "enabled" if enabled else "disabled"
        self.logger.info(f"{self.__class__.__name__} {status}")
    
    def get_description(self) -> str:
        """
        Get human-readable description of this skill.
        
        Returns:
            Description string
        """
        return self.__class__.__doc__ or f"{self.__class__.__name__} skill"
    
    @property
    def name(self) -> str:
        """Get skill name."""
        return self.__class__.__name__
