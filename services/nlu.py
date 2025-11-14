"""
Natural Language Understanding - Stage 1 Mk.I
Enhanced pattern matching with fuzzy support.
"""

import re
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple


@dataclass
class IntentBase:
    name: str
    slots: Dict[str, Any]


@dataclass
class IntentWithConfidence(IntentBase):
    confidence: float = 1.0
    fuzzy_match: Optional[str] = None


class SimpleNLU:
    """
    Rule-based Natural Language Understanding.
    Supports pattern matching and keyword detection.
    """
    
    def __init__(self):
        # Pattern-based intents (regex patterns)
        self.patterns: List[Tuple[str, str, float]] = [
            # System commands
            (r"shutdown|shut down|turn off( computer| pc)?", "shutdown_computer", 1.0),
            (r"restart|reboot( computer| pc)?", "restart_computer", 1.0),
            (r"sleep|hibernate", "sleep_computer", 0.9),
            (r"lock( computer| screen)?", "lock_computer", 0.9),
            
            # Application control
            (r"open ([a-z]+)", "open_application", 0.95),
            (r"close ([a-z]+)", "close_application", 0.95),
            (r"launch ([a-z]+)", "open_application", 0.9),
            (r"start ([a-z]+)", "open_application", 0.9),
            
            # System info
            (r"(get |show |what's )?(my )?ip( address)?", "get_ip_address", 0.95),
            (r"(get |show |what's )?(the )?cpu( info| usage)?", "get_cpu_info", 0.9),
            (r"(get |show |what's )?(the )?memory( info| usage)?", "get_memory_info", 0.9),
            (r"system (status|health|info)", "get_system_status", 0.95),
            (r"disk space", "check_disk_space", 0.95),
            
            # Network
            (r"(run |do )?speed test", "run_speed_test", 0.95),
            (r"test (network |internet )?connect(ion|ivity)?", "test_network_connectivity", 0.9),
            (r"ping", "test_network_connectivity", 0.8),
            
            # Volume
            (r"(set |change )?volume( to)? (\d+)", "set_volume", 0.95),
            (r"volume up", "set_volume", 0.9),
            (r"volume down", "set_volume", 0.9),
            (r"mute", "set_volume", 0.9),
            
            # Time/Date
            (r"what('s| is) the time", "get_time", 1.0),
            (r"what('s| is) (the )?date", "get_date", 1.0),
            
            # File operations
            (r"create folder (.+)", "create_folder", 0.95),
            (r"delete (.+)", "delete_path", 0.9),
            (r"search( for)? (.+)", "search_files", 0.85),
            (r"find (.+)", "search_files", 0.85),
        ]
        
        # Keyword-based fallback (when patterns don't match)
        self.keyword_intents = {
            "shutdown": "shutdown_computer",
            "restart": "restart_computer",
            "reboot": "restart_computer",
            "sleep": "sleep_computer",
            "lock": "lock_computer",
            "volume": "set_volume",
            "time": "get_time",
            "date": "get_date",
            "weather": "get_weather",
            "notepad": "open_application",
            "calculator": "open_application",
            "chrome": "open_application",
            "firefox": "open_application",
        }
    
    def parse(self, text: str) -> Optional[IntentBase]:
        """
        Legacy method for backward compatibility.
        
        Args:
            text: User input text
            
        Returns:
            IntentBase or None
        """
        intent, _ = self.get_intent_with_confidence(text)
        if intent:
            return IntentBase(name=intent.name, slots=intent.slots)
        return None
    
    def get_intent_with_confidence(self, text: str) -> Tuple[Optional[IntentWithConfidence], List[str]]:
        """
        Parse user input and extract intent with confidence score.
        
        Args:
            text: User input text
            
        Returns:
            Tuple of (IntentWithConfidence, suggestions)
        """
        if not text:
            return None, []
        
        text_lower = text.lower().strip()
        
        # Try pattern matching first
        for pattern, intent_name, confidence in self.patterns:
            match = re.search(pattern, text_lower)
            if match:
                # Extract slots from regex groups
                slots = self._extract_slots(match, intent_name, text_lower)
                
                return IntentWithConfidence(
                    name=intent_name,
                    slots=slots,
                    confidence=confidence,
                    fuzzy_match=None
                ), []
        
        # Fallback: keyword matching
        for keyword, intent_name in self.keyword_intents.items():
            if keyword in text_lower:
                slots = self._extract_slots_keyword(text_lower, intent_name)
                
                return IntentWithConfidence(
                    name=intent_name,
                    slots=slots,
                    confidence=0.7,  # Lower confidence for keyword match
                    fuzzy_match=keyword
                ), []
        
        # No match
        return None, []
    
    def _extract_slots(self, match, intent_name: str, text: str) -> Dict[str, Any]:
        """Extract slot values from regex match."""
        slots = {}
        
        # Extract named groups
        if match.groups():
            if intent_name in ["open_application", "close_application"]:
                slots["app_name"] = match.group(1)
            
            elif intent_name == "set_volume":
                # Extract volume level
                volume_match = re.search(r"(\d+)", text)
                if volume_match:
                    slots["level"] = int(volume_match.group(1))
                elif "up" in text:
                    slots["level"] = "+10"
                elif "down" in text:
                    slots["level"] = "-10"
                elif "mute" in text:
                    slots["level"] = 0
            
            elif intent_name in ["create_folder", "delete_path"]:
                # Extract path (everything after the command)
                path_match = re.search(r"(folder|delete) (.+)", text)
                if path_match:
                    slots["path"] = path_match.group(2).strip()
            
            elif intent_name == "search_files":
                # Extract search query
                search_match = re.search(r"(search|find) (?:for )?(.+)", text)
                if search_match:
                    slots["query"] = search_match.group(2).strip()
        
        return slots
    
    def _extract_slots_keyword(self, text: str, intent_name: str) -> Dict[str, Any]:
        """Extract slots for keyword-matched intents."""
        slots = {}
        
        if intent_name == "open_application":
            # Find the app name (the keyword itself)
            for keyword in self.keyword_intents:
                if keyword in text and self.keyword_intents[keyword] == intent_name:
                    slots["app_name"] = keyword
                    break
        
        elif intent_name == "set_volume":
            # Try to extract volume level
            volume_match = re.search(r"(\d+)", text)
            if volume_match:
                slots["level"] = int(volume_match.group(1))
        
        return slots


class ContextManager:
    """
    Manages conversation context and history.
    """
    
    def __init__(self, max_history: int = 20):
        self.history: List[Dict[str, Any]] = []
        self.max_history = max_history
    
    def add(self, entry: Dict[str, Any]):
        """Add entry to context history."""
        self.history.append(entry)
        if len(self.history) > self.max_history:
            self.history.pop(0)
    
    def last_intent(self) -> Optional[Dict[str, Any]]:
        """Get the last recognized intent."""
        for item in reversed(self.history):
            if item.get("type") == "intent":
                return item
        return None
    
    def get_recent(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent context entries."""
        return self.history[-count:] if self.history else []