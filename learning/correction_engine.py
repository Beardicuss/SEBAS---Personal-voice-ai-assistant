"""
Correction Engine - Learn from user corrections
When user corrects SEBAS, remember it forever
"""

import logging
import hashlib
from datetime import datetime
from typing import Optional


class CorrectionEngine:
    """Learn from explicit user corrections"""
    
    def __init__(self, memory_store):
        self.mem = memory_store
        logging.info("[CorrectionEngine] Initialized")
    
    def add_correction(self, wrong_text: str, correct_intent: str):
        """Store a user correction"""
        corrections = self.mem.get("corrections", {})
        
        # Create hash for the phrase
        text_hash = hashlib.md5(wrong_text.lower().encode()).hexdigest()[:8]
        
        if text_hash in corrections:
            # Update existing correction
            corrections[text_hash]["usage_count"] += 1
            corrections[text_hash]["last_used"] = datetime.now().isoformat()
        else:
            # New correction
            corrections[text_hash] = {
                "text": wrong_text.lower(),
                "correct_intent": correct_intent,
                "confidence": 1.0,
                "learned_at": datetime.now().isoformat(),
                "usage_count": 1,
                "last_used": datetime.now().isoformat()
            }
        
        self.mem.update("corrections", corrections)
        logging.info(f"[CorrectionEngine] Learned: '{wrong_text}' → {correct_intent}")
    
    def check_correction(self, text: str) -> Optional[dict]:
        """Check if text has a known correction"""
        text_lower = text.lower().strip()
        text_hash = hashlib.md5(text_lower.encode()).hexdigest()[:8]
        
        corrections = self.mem.get("corrections", {})
        
        if text_hash in corrections:
            correction = corrections[text_hash]
            
            # Update usage
            correction["usage_count"] += 1
            correction["last_used"] = datetime.now().isoformat()
            self.mem.update("corrections", corrections)
            
            logging.info(f"[CorrectionEngine] Found correction: {correction['correct_intent']}")
            
            # Return Intent-like object
            return {
                "name": correction["correct_intent"],
                "slots": {},
                "confidence": correction["confidence"]
            }
        
        return None
    
    def inject_into_nlu(self, nlu):
        """Wrap NLU parse to check corrections first"""
        original_parse = nlu.parse
        
        def corrected_parse(text, *args, **kwargs):
            # Check corrections first
            correction = self.check_correction(text)
            if correction:
                # Import Intent class
                try:
                    from sebas.services.nlu import Intent
                    return Intent(
                        name=correction["name"],
                        slots=correction["slots"],
                        confidence=correction["confidence"]
                    )
                except:
                    # Fallback if Intent class not available
                    pass
            
            # Fall back to original NLU
            return original_parse(text, *args, **kwargs)
        
        nlu.parse = corrected_parse
        logging.info("[CorrectionEngine] Injected into NLU")
