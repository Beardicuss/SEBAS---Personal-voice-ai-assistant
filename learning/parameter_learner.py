"""
Parameter Learner - Learn common slot values and their properties
"""

import logging
from typing import Dict, Any, List


class ParameterLearner:
    """Learn and remember slot values"""
    
    def __init__(self, memory_store):
        self.mem = memory_store
        logging.info("[ParameterLearner] Initialized")
    
    def learn_slots(self, intent: str, slots: Dict[str, Any]):
        """Record slot values for future reference"""
        if not slots:
            return
        
        params = self.mem.get("parameter_memory", {})
        
        for slot_name, slot_value in slots.items():
            if slot_name not in params:
                params[slot_name] = {}
            
            value_str = str(slot_value).lower()
            
            if value_str not in params[slot_name]:
                params[slot_name][value_str] = {
                    "count": 0,
                    "intents": [],
                    "metadata": {}
                }
            
            # Increment count
            params[slot_name][value_str]["count"] += 1
            
            # Track which intents use this value
            if intent not in params[slot_name][value_str]["intents"]:
                params[slot_name][value_str]["intents"].append(intent)
        
        self.mem.update("parameter_memory", params)
    
    def get_common_values(self, slot_name: str, top_n: int = 5) -> List[str]:
        """Get most common values for a slot"""
        params = self.mem.get("parameter_memory", {}).get(slot_name, {})
        
        sorted_params = sorted(
            params.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        return [value for value, data in sorted_params[:top_n]]
    
    def get_value_metadata(self, slot_name: str, value: str) -> Dict[str, Any]:
        """Get metadata for a specific slot value"""
        params = self.mem.get("parameter_memory", {})
        return params.get(slot_name, {}).get(value.lower(), {})
    
    def add_metadata(self, slot_name: str, value: str, key: str, metadata_value: Any):
        """Add metadata to a slot value (e.g., category, path, etc.)"""
        params = self.mem.get("parameter_memory", {})
        
        if slot_name not in params:
            params[slot_name] = {}
        if value.lower() not in params[slot_name]:
            params[slot_name][value.lower()] = {
                "count": 0,
                "intents": [],
                "metadata": {}
            }
        
        params[slot_name][value.lower()]["metadata"][key] = metadata_value
        self.mem.update("parameter_memory", params)
