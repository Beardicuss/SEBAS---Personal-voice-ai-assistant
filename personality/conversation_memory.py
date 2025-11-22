"""
Conversation Memory - Short-term conversation memory
Tracks recent messages and context
"""

import json
import logging
from pathlib import Path
from datetime import datetime


class ConversationMemory:
    """Manages short-term conversation memory"""
    
    def __init__(self, state_file: str = "sebas/personality/data/conversation_state.json"):
        self.state_file = Path(state_file)
        self.state = self._load_state()
    
    def _load_state(self) -> dict:
        """Load conversation state from file"""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding='utf-8'))
            except:
                pass
        
        return {
            "current_topic": None,
            "topic_strength": 0,
            "last_messages": [],
            "user_emotion": "neutral",
            "chaos_level": 3,
            "silence_counter": 0,
            "mentioned_lore": [],
            "last_user_message": "",
            "last_bot_message": "",
            "conversation_count": 0,
            "session_start": datetime.now().isoformat(),
            "last_had_followup": False
        }
    
    def save_state(self):
        """Save conversation state to file"""
        try:
            self.state_file.write_text(
                json.dumps(self.state, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception as e:
            logging.error(f"[ConversationMemory] Failed to save state: {e}")
    
    def add_message(self, user_text: str, bot_text: str):
        """Add a message exchange to memory"""
        self.state["last_messages"].append({
            "user": user_text,
            "bot": bot_text,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 10 exchanges
        self.state["last_messages"] = self.state["last_messages"][-10:]
        
        self.state["last_user_message"] = user_text
        self.state["last_bot_message"] = bot_text
        self.state["conversation_count"] += 1
        
        self.save_state()
    
    def update_topic(self, topic: str):
        """Update current topic"""
        if self.state["current_topic"] == topic:
            self.state["topic_strength"] += 1
        else:
            self.state["current_topic"] = topic
            self.state["topic_strength"] = 1
        
        self.save_state()
    
    def update_emotion(self, emotion: str):
        """Update user emotion"""
        self.state["user_emotion"] = emotion
        self.save_state()
    
    def get_last_user_message(self) -> str:
        """Get last user message"""
        return self.state.get("last_user_message", "")
    
    def get_current_topic(self) -> str:
        """Get current topic"""
        return self.state.get("current_topic")
    
    def get_topic_strength(self) -> int:
        """Get topic strength (how long we've been on this topic)"""
        return self.state.get("topic_strength", 0)
    
    def increment_silence(self):
        """Increment silence counter"""
        self.state["silence_counter"] += 1
        self.save_state()
    
    def reset_silence(self):
        """Reset silence counter"""
        self.state["silence_counter"] = 0
        self.save_state()
    
    def add_mentioned_lore(self, lore_tag: str):
        """Add a lore tag to mentioned list"""
        if lore_tag not in self.state["mentioned_lore"]:
            self.state["mentioned_lore"].append(lore_tag)
            self.save_state()
    
    def set_followup_flag(self, value: bool):
        """Set whether we just added a follow-up"""
        self.state["last_had_followup"] = value
        self.save_state()
