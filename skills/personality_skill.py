"""
Personality Skill - Switch personality modes via voice command
Handles: "personality default" and "personality conversation"
"""

import logging
import re
from sebas.skills.base_skill import BaseSkill


class PersonalitySkill(BaseSkill):
    """Skill to switch personality modes"""
    
    def get_intents(self):
        """Return list of intent names (not patterns)"""
        return ["switch_personality"]
    
    def can_handle(self, intent_name: str) -> bool:
        """Check if this skill can handle the intent"""
        return intent_name == "switch_personality"
    
    def handle(self, intent_name: str, slots: dict, sebas) -> bool:
        """Handle personality switching"""
        if intent_name != "switch_personality":
            return False
        
        # Extract mode from slots
        mode = slots.get("mode")
        
        if not mode:
            sebas.speak("Please specify: personality default or personality conversation.")
            return True
        
        # Map to actual mode names
        mode_map = {
            "default": "default",
            "conversation": "conversation_mode"
        }
        
        actual_mode = mode_map.get(mode)
        
        if not actual_mode:
            sebas.speak("Unknown personality mode.")
            return False
        
        # Switch mode
        if hasattr(sebas, 'persona') and sebas.persona:
            sebas.persona.set_mode(actual_mode)
            
            if actual_mode == "default":
                sebas.speak("Personality set to default mode, sir.")
            else:
                sebas.speak("Conversation mode activated. Let's talk, mortal.")
            
            return True
        else:
            sebas.speak("Personality system not available.")
            return False
