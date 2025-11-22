"""
Memory Store - JSON persistence layer for self-learning system
Handles all read/write operations to learning_memory.json
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional


class MemoryStore:
    """Persistent storage for all learning data"""
    
    def __init__(self, path: str = "sebas/data/learning_memory.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.path.exists():
            self._write_default()
        
        self.data = self._load()
        logging.info(f"[MemoryStore] Loaded from {self.path}")
    
    def _write_default(self):
        """Create default memory structure"""
        default = {
            "corrections": {},
            "custom_patterns": {},
            "workflows": {},
            "usage_stats": {},
            "context_patterns": {},
            "parameter_memory": {},
            "semantic_clusters": {},
            "bayesian_priors": {
                "intent_success_rate": {},
                "pattern_accuracy": {},
                "total_interactions": 0
            },
            "ngram_patterns": {
                "unigrams": {},
                "bigrams": {},
                "trigrams": {},
                "intent_ngrams": {}
            },
            "temporal_patterns": {
                "hourly": {},
                "daily": {},
                "monthly": {},
                "seasonal": {},
                "work_hours": {},
                "sequences": []
            },
            "dependency_graph": {
                "edges": {},
                "chains": []
            }
        }
        self.path.write_text(json.dumps(default, indent=2, ensure_ascii=False), encoding='utf-8')
        logging.info(f"[MemoryStore] Created default memory at {self.path}")
    
    def _load(self) -> Dict[str, Any]:
        """Load memory from JSON file"""
        try:
            return json.loads(self.path.read_text(encoding='utf-8'))
        except Exception as e:
            logging.error(f"[MemoryStore] Failed to load: {e}")
            self._write_default()
            return json.loads(self.path.read_text(encoding='utf-8'))
    
    def save(self):
        """Save current data to disk"""
        try:
            self.path.write_text(
                json.dumps(self.data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception as e:
            logging.error(f"[MemoryStore] Failed to save: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key"""
        return self.data.get(key, default)
    
    def update(self, key: str, value: Any):
        """Update value and save"""
        self.data[key] = value
        self.save()
    
    def get_nested(self, *keys, default: Any = None) -> Any:
        """Get nested value (e.g., get_nested('bayesian_priors', 'intent_success_rate'))"""
        current = self.data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return default
            else:
                return default
        return current if current is not None else default
    
    def update_nested(self, *keys, value: Any):
        """Update nested value and save"""
        if len(keys) < 1:
            return
        
        current = self.data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
        self.save()
