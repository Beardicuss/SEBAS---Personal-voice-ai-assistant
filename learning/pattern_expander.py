"""
Pattern Expander - Auto-generate new intent patterns from successful commands
"""

import logging
import re
from typing import List


class PatternExpander:
    """Automatically expand intent patterns from usage"""
    
    def __init__(self, memory_store, min_confidence: float = 0.85):
        self.mem = memory_store
        self.min_confidence = min_confidence
        logging.info("[PatternExpander] Initialized")
    
    def auto_learn_pattern(self, text: str, intent: str):
        """Automatically learn a new pattern from successful command"""
        patterns = self.mem.get("custom_patterns", {})
        
        if intent not in patterns:
            patterns[intent] = {
                "patterns": [],
                "semantic_anchors": [],
                "confidence_threshold": 0.7
            }
        
        text_lower = text.lower().strip()
        
        # Escape for regex
        escaped = re.escape(text_lower)
        
        # Don't add duplicates
        if escaped not in patterns[intent]["patterns"]:
            patterns[intent]["patterns"].append(escaped)
            patterns[intent]["semantic_anchors"].append(text_lower)
            
            self.mem.update("custom_patterns", patterns)
            logging.info(f"[PatternExpander] Learned pattern for {intent}: '{text_lower}'")
    
    def add_pattern(self, text: str, intent: str):
        """Manually add a pattern"""
        self.auto_learn_pattern(text, intent)
    
    def get_patterns(self, intent: str) -> List[str]:
        """Get all patterns for an intent"""
        patterns = self.mem.get("custom_patterns", {})
        return patterns.get(intent, {}).get("patterns", [])
    
    def inject_into_nlu(self, nlu):
        """Add custom patterns to NLU"""
        custom_patterns = self.mem.get("custom_patterns", {})
        
        # Add patterns to NLU's pattern list
        if hasattr(nlu, 'patterns'):
            for intent, data in custom_patterns.items():
                for pattern in data.get("patterns", []):
                    # Add to NLU patterns if not already there
                    pattern_tuple = (pattern, intent)
                    if pattern_tuple not in nlu.patterns:
                        nlu.patterns.append(pattern_tuple)
        
        logging.info(f"[PatternExpander] Injected {len(custom_patterns)} pattern sets into NLU")
