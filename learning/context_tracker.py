"""
Context Tracker - Track context awareness
Records when and how commands are used
"""

import logging
from datetime import datetime
from typing import Dict, Any


class ContextTracker:
    """Track context awareness"""
    
    def __init__(self, memory_store):
        self.mem = memory_store
        logging.info("[ContextTracker] Initialized")
    
    def record_interaction(self, text: str, intent: str, slots: Dict[str, Any]):
        """Track when and how commands are used"""
        now = datetime.now()
        hour = now.hour
        
        # Determine time period
        if 6 <= hour < 12:
            period = "morning"
        elif 12 <= hour < 18:
            period = "afternoon"
        elif 18 <= hour < 22:
            period = "evening"
        else:
            period = "night"
        
        # Update context patterns
        patterns = self.mem.get("context_patterns", {})
        
        if period not in patterns:
            patterns[period] = {
                "common_intents": {},
                "sequence": []
            }
        
        # Track intent frequency by time
        intents = patterns[period]["common_intents"]
        intents[intent] = intents.get(intent, 0) + 1
        
        # Track command sequences (last 5)
        seq = patterns[period]["sequence"]
        seq.append({"intent": intent, "time": now.isoformat()})
        patterns[period]["sequence"] = seq[-5:]  # Keep last 5
        
        self.mem.update("context_patterns", patterns)
    
    def get_context_suggestions(self) -> list:
        """Suggest likely next commands based on context"""
        now = datetime.now()
        hour = now.hour
        
        if 6 <= hour < 12:
            period = "morning"
        elif 12 <= hour < 18:
            period = "afternoon"
        elif 18 <= hour < 22:
            period = "evening"
        else:
            period = "night"
        
        patterns = self.mem.get("context_patterns", {}).get(period, {})
        common = patterns.get("common_intents", {})
        
        # Return top 3 most common intents for this time
        sorted_intents = sorted(common.items(), key=lambda x: x[1], reverse=True)
        return [intent for intent, count in sorted_intents[:3]]
