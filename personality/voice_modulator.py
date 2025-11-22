"""
Voice Modulator - TTS voice effects
Modulates voice based on personality mode and context
"""

import random
import logging


class VoiceModulator:
    """Modulates TTS voice parameters"""
    
    def __init__(self):
        self.base_rate = 170
        self.base_pitch = 0
    
    def get_voice_effects(self, mode: dict, emotion: str = "neutral") -> dict:
        """Get voice effects for mode and emotion"""
        effects = {
            "rate": self.base_rate,
            "pitch": self.base_pitch,
            "volume": 1.0,
            "pauses": []
        }
        
        # Apply mode modifiers
        effects["rate"] += mode.get("voice_rate_modifier", 0)
        effects["pitch"] += mode.get("voice_pitch_modifier", 0)
        
        # Apply emotion modifiers
        emotion_modifiers = {
            "excited": {"rate": 15, "pitch": 3},
            "sad": {"rate": -15, "pitch": -2},
            "angry": {"rate": 20, "pitch": 4},
            "anxious": {"rate": 10, "pitch": 1},
            "bored": {"rate": -10, "pitch": -1}
        }
        
        if emotion in emotion_modifiers:
            mod = emotion_modifiers[emotion]
            effects["rate"] += mod.get("rate", 0)
            effects["pitch"] += mod.get("pitch", 0)
        
        # Add random variation for chaos
        if mode.get("chaos"):
            effects["rate"] += random.randint(-5, 5)
            effects["pitch"] += random.randint(-1, 1)
        
        # Clamp values
        effects["rate"] = max(80, min(250, effects["rate"]))
        effects["pitch"] = max(-10, min(10, effects["pitch"]))
        
        return effects
    
    def add_dramatic_pause(self, text: str, mode: dict) -> str:
        """Add dramatic pauses to text"""
        if not mode.get("poetic"):
            return text
        
        # Add pauses after certain punctuation
        text = text.replace("...", "... <break time='500ms'/>")
        text = text.replace(". ", ". <break time='300ms'/>")
        
        return text
    
    def should_whisper(self, text: str) -> bool:
        """Determine if text should be whispered"""
        return "(whisper)" in text.lower()
    
    def extract_whisper(self, text: str) -> tuple:
        """Extract whisper from text, returns (main_text, whisper_text)"""
        if "(whisper)" not in text.lower():
            return text, None
        
        # Split on whisper marker
        parts = text.split("(whisper)")
        if len(parts) >= 2:
            main = parts[0].strip()
            whisper = parts[1].strip()
            return main, whisper
        
        return text, None
