"""
Persona Modes - Personality mode definitions
Simplified to 2 main modes: default and conversation
In conversation mode, sub-modes (chaos_lord, dark_mentor, psycho) randomize
"""

import random

# Main modes (user-selectable)
MAIN_MODES = ["default", "conversation_mode"]

# Sub-modes (used internally in conversation mode)
PERSONA_MODES = {
    "default": {
        "name": "Default",
        "description": "Normal assistant behavior",
        "sarcasm": False,
        "chaos": False,
        "poetic": False,
        "free_talk": False,
        "intensity": 0,
        "voice_rate_modifier": 0,
        "voice_pitch_modifier": 0
    },
    
    "conversation_mode": {
        "name": "Conversation Mode",
        "description": "Free talk with randomized personality styles",
        "sarcasm": True,
        "chaos": True,
        "poetic": True,
        "free_talk": True,
        "intensity": 5,
        "voice_rate_modifier": 5,
        "voice_pitch_modifier": 1,
        "randomize_submodes": True  # Flag to enable sub-mode randomization
    },
    
    # Sub-modes (used internally when conversation_mode is active)
    "chaos_lord": {
        "name": "Chaos Lord",
        "description": "Sheogorath-style: sarcastic, poetic, unpredictable",
        "sarcasm": True,
        "chaos": True,
        "poetic": True,
        "free_talk": True,
        "intensity": 3,
        "voice_rate_modifier": 10,
        "voice_pitch_modifier": 2
    },
    
    "dark_mentor": {
        "name": "Dark Mentor",
        "description": "Deep, philosophical, slow, mysterious",
        "sarcasm": False,
        "chaos": False,
        "poetic": True,
        "free_talk": True,
        "intensity": 2,
        "voice_rate_modifier": -20,
        "voice_pitch_modifier": -3
    },
    
    "psycho": {
        "name": "Psycho",
        "description": "Borderlands-style: aggressive, hyped, chaotic",
        "sarcasm": True,
        "chaos": True,
        "poetic": False,
        "free_talk": True,
        "intensity": 4,
        "voice_rate_modifier": 30,
        "voice_pitch_modifier": 5
    }
}

# Sub-modes that can be randomly selected in conversation mode
CONVERSATION_SUBMODES = ["chaos_lord", "dark_mentor", "psycho"]


def get_mode(mode_name: str) -> dict:
    """Get mode configuration by name"""
    return PERSONA_MODES.get(mode_name, PERSONA_MODES["default"])


def get_random_submode() -> dict:
    """Get a random sub-mode for conversation mode"""
    submode_name = random.choice(CONVERSATION_SUBMODES)
    return PERSONA_MODES[submode_name]


def list_modes() -> list:
    """List all main user-selectable modes"""
    return MAIN_MODES


def get_mode_description(mode_name: str) -> str:
    """Get mode description"""
    mode = get_mode(mode_name)
    return mode.get("description", "Unknown mode")
