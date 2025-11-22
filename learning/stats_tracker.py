"""
Stats Tracker - Track usage statistics and success rates
"""

import logging
from datetime import datetime
from typing import Dict, Any


class StatsTracker:
    """Track command usage and success rates"""
    
    def __init__(self, memory_store):
        self.mem = memory_store
        logging.info("[StatsTracker] Initialized")
    
    def record_usage(self, intent: str, success: bool, confidence: float = 0.0, slots: Dict[str, Any] = None):
        """Record a command execution"""
        stats = self.mem.get("usage_stats", {})
        
        if intent not in stats:
            stats[intent] = {
                "total_uses": 0,
                "successful": 0,
                "failed": 0,
                "avg_confidence": 0.0,
                "last_used": None,
                "common_slots": {}
            }
        
        # Update counts
        stats[intent]["total_uses"] += 1
        if success:
            stats[intent]["successful"] += 1
        else:
            stats[intent]["failed"] += 1
        
        # Update average confidence
        total = stats[intent]["total_uses"]
        current_avg = stats[intent]["avg_confidence"]
        stats[intent]["avg_confidence"] = (current_avg * (total - 1) + confidence) / total
        
        # Update timestamp
        stats[intent]["last_used"] = datetime.now().isoformat()
        
        # Track common slot values
        if slots:
            for slot_name, slot_value in slots.items():
                if slot_name not in stats[intent]["common_slots"]:
                    stats[intent]["common_slots"][slot_name] = {}
                
                value_str = str(slot_value)
                stats[intent]["common_slots"][slot_name][value_str] = \
                    stats[intent]["common_slots"][slot_name].get(value_str, 0) + 1
        
        self.mem.update("usage_stats", stats)
    
    def get_stats(self, intent: str) -> Dict[str, Any]:
        """Get statistics for an intent"""
        stats = self.mem.get("usage_stats", {})
        return stats.get(intent, {})
    
    def get_success_rate(self, intent: str) -> float:
        """Get success rate for an intent"""
        stats = self.get_stats(intent)
        total = stats.get("total_uses", 0)
        if total == 0:
            return 0.0
        successful = stats.get("successful", 0)
        return successful / total
    
    def get_most_used_intents(self, top_n: int = 5) -> list:
        """Get most frequently used intents"""
        stats = self.mem.get("usage_stats", {})
        sorted_intents = sorted(
            stats.items(),
            key=lambda x: x[1].get("total_uses", 0),
            reverse=True
        )
        return [intent for intent, data in sorted_intents[:top_n]]
