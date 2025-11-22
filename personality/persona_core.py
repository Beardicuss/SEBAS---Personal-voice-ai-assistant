"""
Persona Core - Main Personality Engine
Orchestrates all personality systems
"""

import json
import logging
import random
from pathlib import Path

from .persona_modes import get_mode, get_random_submode, PERSONA_MODES, MAIN_MODES
from .persona_rules import apply_rules
from .dynamic_replies import generate_dynamic_reply, adjust_tone, classify_message
from .conversation_topics import detect_topic, get_followups_for_topic, should_add_followup
from .conversation_memory import ConversationMemory
from .conversation_hints import get_hint, should_give_hint
from .whispers import maybe_add_whisper
from .micro_lore import maybe_add_micro_lore
from .emotional_engine import detect_emotion, get_emotional_response, EmotionalEngine
from .voice_modulator import VoiceModulator


class PersonalityEngine:
    """Main personality engine orchestrator"""
    
    def __init__(self, dictionary_path: str = "sebas/personality/data/chaos_dictionary.json"):
        self.active_mode = "default"
        self.current_submode = None  # For conversation mode randomization
        self.dictionary = self._load_dictionary(dictionary_path)
        self.memory = ConversationMemory()
        self.emotional_engine = EmotionalEngine()
        self.voice_modulator = VoiceModulator()
        
        logging.info("[PersonalityEngine] Initialized")
    
    def _load_dictionary(self, path: str) -> dict:
        """Load chaos dictionary"""
        dict_path = Path(path)
        if dict_path.exists():
            try:
                return json.loads(dict_path.read_text(encoding='utf-8'))
            except Exception as e:
                logging.error(f"[PersonalityEngine] Failed to load dictionary: {e}")
        
        return {"normal_to_chaos": {}, "intensifiers": {}, "endings": []}
    
    def set_mode(self, mode: str):
        """Set personality mode"""
        if mode in MAIN_MODES:
            self.active_mode = mode
            self.current_submode = None  # Reset sub-mode
            logging.info(f"[PersonalityEngine] Mode set to: {mode}")
        else:
            logging.warning(f"[PersonalityEngine] Unknown mode: {mode}")
    
    def get_current_mode(self) -> str:
        """Get current mode name"""
        return self.active_mode
    
    def apply(self, text: str, user_input: str = None) -> str:
        """
        Apply personality transformation to text
        This is the main pipeline
        """
        mode = get_mode(self.active_mode)
        
        # If in conversation mode and we have user input, do full processing
        if mode.get("free_talk") and user_input:
            return self._process_conversation(text, user_input, mode)
        
        # Otherwise just apply personality rules
        transformed = apply_rules(text, mode, self.dictionary)
        
        return transformed
    
    def _process_conversation(self, base_text: str, user_input: str, mode: dict) -> str:
        """Process in conversation mode with full personality"""
        
        # If in conversation mode, randomly select a sub-mode for variety
        if mode.get("randomize_submodes"):
            # 30% chance to switch sub-mode each interaction
            if self.current_submode is None or random.random() < 0.3:
                submode = get_random_submode()
                self.current_submode = submode
                logging.debug(f"[PersonalityEngine] Using sub-mode: {submode['name']}")
            else:
                submode = self.current_submode
            
            # Use sub-mode settings instead of main mode
            mode = submode
        
        # 1. Detect emotion
        emotion = detect_emotion(user_input)
        self.emotional_engine.track_emotion(emotion)
        self.memory.update_emotion(emotion)
        
        # 2. Detect topic
        topic, topic_tags = detect_topic(user_input)
        if topic:
            self.memory.update_topic(topic)
        
        # 3. Generate dynamic reply if base is empty or generic
        if not base_text or base_text in ["I did not understand, sir.", "Command executed.", ""]:
            reply = generate_dynamic_reply(user_input)
        else:
            reply = base_text
        
        # 4. Adjust tone based on user input
        reply = adjust_tone(user_input, reply)
        
        # 5. Apply personality rules
        reply = apply_rules(reply, mode, self.dictionary)
        
        # 6. Maybe add emotional response
        if random.random() < 0.3:  # 30% chance
            reply += " " + get_emotional_response(emotion)
        
        # 7. Maybe add micro-lore
        chaos_level = mode.get("intensity", 3)
        reply = maybe_add_micro_lore(reply, topic_tags, chaos_level)
        
        # 8. Maybe add whisper
        reply = maybe_add_whisper(reply, topic, chaos_level)
        
        # 9. Maybe add follow-up question
        if topic and should_add_followup(self.memory.state, topic):
            followups = get_followups_for_topic(topic)
            if followups:
                reply += " " + random.choice(followups)
                self.memory.set_followup_flag(True)
        else:
            self.memory.set_followup_flag(False)
        
        # 10. Save to memory
        self.memory.add_message(user_input, reply)
        
        return reply
    
    def get_voice_effects(self) -> dict:
        """Get voice effects for current mode and emotion"""
        mode = get_mode(self.active_mode)
        emotion = self.memory.state.get("user_emotion", "neutral")
        return self.voice_modulator.get_voice_effects(mode, emotion)
    
    def should_give_proactive_hint(self) -> bool:
        """Check if we should give a proactive hint"""
        silence_count = self.memory.state.get("silence_counter", 0)
        topic = self.memory.get_current_topic()
        return should_give_hint(silence_count, topic)
    
    def get_proactive_hint(self) -> str:
        """Get a proactive hint"""
        topic = self.memory.get_current_topic()
        hint = get_hint(topic)
        
        # Apply personality to hint
        mode = get_mode(self.active_mode)
        hint = apply_rules(hint, mode, self.dictionary)
        
        return hint
    
    def increment_silence(self):
        """Increment silence counter"""
        self.memory.increment_silence()
    
    def reset_silence(self):
        """Reset silence counter"""
        self.memory.reset_silence()
    
    def get_stats(self) -> dict:
        """Get personality stats"""
        return {
            "active_mode": self.active_mode,
            "conversation_count": self.memory.state.get("conversation_count", 0),
            "current_topic": self.memory.get_current_topic(),
            "topic_strength": self.memory.get_topic_strength(),
            "user_emotion": self.memory.state.get("user_emotion", "neutral"),
            "emotional_arc": self.emotional_engine.get_emotional_arc()
        }
