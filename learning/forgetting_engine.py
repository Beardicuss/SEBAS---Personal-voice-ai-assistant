"""
Forgetting Engine - Prevent memory bloat by removing unused patterns
Implements decay for rarely-used patterns
"""

import logging
from datetime import datetime, timedelta


class ForgettingEngine:
    """Prevent memory bloat by removing unused patterns"""
    
    def __init__(self, memory_store, decay_days: int = 30):
        self.mem = memory_store
        self.decay_days = decay_days
        logging.info("[ForgettingEngine] Initialized")
    
    def decay_unused_patterns(self):
        """Remove patterns not used in X days"""
        cutoff = datetime.now() - timedelta(days=self.decay_days)
        removed_count = 0
        
        # Decay corrections
        corrections = self.mem.get("corrections", {})
        to_remove = []
        
        for phrase_hash, data in corrections.items():
            if "learned_at" in data:
                try:
                    learned = datetime.fromisoformat(data["learned_at"])
                    usage = data.get("usage_count", 0)
                    
                    # Remove if old and rarely used
                    if learned < cutoff and usage < 3:
                        to_remove.append(phrase_hash)
                except:
                    pass
        
        for key in to_remove:
            del corrections[key]
            removed_count += 1
        
        self.mem.update("corrections", corrections)
        
        # Decay workflows
        workflows = self.mem.get("workflows", {})
        to_remove = []
        
        for name, data in workflows.items():
            if "last_used" in data:
                try:
                    last_used = datetime.fromisoformat(data["last_used"])
                    
                    if last_used < cutoff and data.get("usage_count", 0) < 5:
                        to_remove.append(name)
                except:
                    pass
        
        for key in to_remove:
            del workflows[key]
            removed_count += 1
        
        self.mem.update("workflows", workflows)
        
        if removed_count > 0:
            logging.info(f"[ForgettingEngine] Removed {removed_count} unused patterns")
        
        return removed_count
