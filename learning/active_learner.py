"""
Active Learner - Ask smart questions when uncertain
Implements uncertainty sampling for clarification
"""

import logging
import hashlib
from datetime import datetime
from typing import List, Dict, Optional


class ActiveLearner:
    """Ask smart questions when uncertain"""
    
    def __init__(self, memory_store, uncertainty_threshold: float = 0.6):
        self.mem = memory_store
        self.threshold = uncertainty_threshold
        self.pending_questions = []
        logging.info("[ActiveLearner] Initialized")
    
    def should_ask_clarification(self, intent: str, confidence: float, alternatives: List[tuple]) -> bool:
        """Determine if SEBAS should ask for clarification"""
        # Low confidence
        if confidence < self.threshold:
            return True
        
        # Multiple similar-confidence alternatives
        if len(alternatives) >= 2:
            top_two = sorted(alternatives, key=lambda x: x[1], reverse=True)[:2]
            if abs(top_two[0][1] - top_two[1][1]) < 0.15:  # Very close
                return True
        
        return False
    
    def generate_clarification_question(self, alternatives: List[tuple]) -> Optional[Dict]:
        """Generate a clarification question"""
        if len(alternatives) < 2:
            return None
        
        top_two = sorted(alternatives, key=lambda x: x[1], reverse=True)[:2]
        
        question = {
            "type": "choice",
            "question": "Did you mean:",
            "options": [
                {"intent": top_two[0][0], "description": self._intent_to_description(top_two[0][0])},
                {"intent": top_two[1][0], "description": self._intent_to_description(top_two[1][0])}
            ]
        }
        
        return question
    
    def _intent_to_description(self, intent: str) -> str:
        """Convert intent name to human-readable description"""
        descriptions = {
            "open_application": "Open an application",
            "close_application": "Close an application",
            "get_time": "Tell you the time",
            "get_date": "Tell you the date",
            "set_volume": "Change volume",
            "get_weather": "Get weather information"
        }
        return descriptions.get(intent, intent.replace("_", " ").title())
    
    def learn_from_choice(self, original_text: str, chosen_intent: str, rejected_intents: List[str]):
        """Learn from user's clarification choice"""
        # This is a strong signal - add to corrections
        corrections = self.mem.get("corrections", {})
        
        text_hash = hashlib.md5(original_text.lower().encode()).hexdigest()[:8]
        
        corrections[text_hash] = {
            "text": original_text.lower(),
            "correct_intent": chosen_intent,
            "confidence": 1.0,
            "learned_at": datetime.now().isoformat(),
            "usage_count": 1,
            "rejected": rejected_intents
        }
        
        self.mem.update("corrections", corrections)
        logging.info(f"[ActiveLearner] Learned from choice: '{original_text}' → {chosen_intent}")
