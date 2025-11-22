"""
Temporal Miner - Advanced time-based pattern learning
Learns patterns by hour, day, season, work hours, and sequences
"""

import logging
import calendar
from datetime import datetime
from collections import defaultdict
from typing import List, Optional


class TemporalMiner:
    """Advanced time-based pattern learning"""
    
    def __init__(self, memory_store):
        self.mem = memory_store
        self.patterns = self._load_patterns()
        logging.info("[TemporalMiner] Initialized")
    
    def _load_patterns(self) -> dict:
        """Load temporal patterns"""
        patterns = self.mem.get("temporal_patterns", {})
        if "hourly" not in patterns:
            patterns["hourly"] = {}
        if "daily" not in patterns:
            patterns["daily"] = {}
        if "monthly" not in patterns:
            patterns["monthly"] = {}
        if "seasonal" not in patterns:
            patterns["seasonal"] = {}
        if "work_hours" not in patterns:
            patterns["work_hours"] = {}
        if "sequences" not in patterns:
            patterns["sequences"] = []
        return patterns
    
    def _get_season(self, month: int) -> str:
        """Determine season from month"""
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "fall"
    
    def record_interaction(self, intent: str, slots: dict):
        """Record interaction with full temporal context"""
        now = datetime.now()
        
        # Hour of day
        hour = now.hour
        if str(hour) not in self.patterns["hourly"]:
            self.patterns["hourly"][str(hour)] = {}
        if intent not in self.patterns["hourly"][str(hour)]:
            self.patterns["hourly"][str(hour)][intent] = 0
        self.patterns["hourly"][str(hour)][intent] += 1
        
        # Day of week
        day_name = calendar.day_name[now.weekday()]
        if day_name not in self.patterns["daily"]:
            self.patterns["daily"][day_name] = {}
        if intent not in self.patterns["daily"][day_name]:
            self.patterns["daily"][day_name][intent] = 0
        self.patterns["daily"][day_name][intent] += 1
        
        # Month
        month = now.month
        if str(month) not in self.patterns["monthly"]:
            self.patterns["monthly"][str(month)] = {}
        if intent not in self.patterns["monthly"][str(month)]:
            self.patterns["monthly"][str(month)][intent] = 0
        self.patterns["monthly"][str(month)][intent] += 1
        
        # Season
        season = self._get_season(now.month)
        if season not in self.patterns["seasonal"]:
            self.patterns["seasonal"][season] = {}
        if intent not in self.patterns["seasonal"][season]:
            self.patterns["seasonal"][season][intent] = 0
        self.patterns["seasonal"][season][intent] += 1
        
        # Work hours (9-17 on weekdays)
        is_work_hours = (now.weekday() < 5 and 9 <= hour < 17)
        period = "work_hours" if is_work_hours else "leisure_hours"
        if period not in self.patterns["work_hours"]:
            self.patterns["work_hours"][period] = {}
        if intent not in self.patterns["work_hours"][period]:
            self.patterns["work_hours"][period][intent] = 0
        self.patterns["work_hours"][period][intent] += 1
        
        # Sequence tracking (last 10 commands with timestamps)
        self.patterns["sequences"].append({
            "intent": intent,
            "timestamp": now.isoformat(),
            "hour": hour,
            "day": day_name
        })
        self.patterns["sequences"] = self.patterns["sequences"][-10:]
        
        self.mem.update("temporal_patterns", self.patterns)
    
    def get_likely_intents(self, top_n: int = 3) -> List[str]:
        """Get most likely intents for current time"""
        now = datetime.now()
        hour = now.hour
        day_name = calendar.day_name[now.weekday()]
        
        scores = defaultdict(float)
        
        # Weight by hour (highest weight)
        if str(hour) in self.patterns["hourly"]:
            for intent, count in self.patterns["hourly"][str(hour)].items():
                scores[intent] += count * 3
        
        # Weight by day
        if day_name in self.patterns["daily"]:
            for intent, count in self.patterns["daily"][day_name].items():
                scores[intent] += count * 2
        
        # Weight by work/leisure
        is_work = (now.weekday() < 5 and 9 <= hour < 17)
        period = "work_hours" if is_work else "leisure_hours"
        if period in self.patterns["work_hours"]:
            for intent, count in self.patterns["work_hours"][period].items():
                scores[intent] += count
        
        # Sort and return top N
        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [intent for intent, score in sorted_intents[:top_n]]
    
    def predict_next_command(self) -> Optional[str]:
        """Predict next command based on recent sequence"""
        if len(self.patterns["sequences"]) < 2:
            return None
        
        # Get last command
        last_cmd = self.patterns["sequences"][-1]
        
        # Find similar sequences in history
        similar_sequences = []
        for i in range(len(self.patterns["sequences"]) - 1):
            if self.patterns["sequences"][i]["intent"] == last_cmd["intent"]:
                # Found same command, what came next?
                if i + 1 < len(self.patterns["sequences"]):
                    next_cmd = self.patterns["sequences"][i + 1]
                    similar_sequences.append(next_cmd["intent"])
        
        if not similar_sequences:
            return None
        
        # Return most common next command
        from collections import Counter
        most_common = Counter(similar_sequences).most_common(1)
        return most_common[0][0] if most_common else None
