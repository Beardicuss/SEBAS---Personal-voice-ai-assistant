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
            (r"\b(?:shutdown|shut down|turn off)(?: computer| pc)?\b", "shutdown_computer", 1.0),
            (r"\b(?:restart|reboot)(?: computer| pc)?\b", "restart_computer", 1.0),
            (r"\b(?:sleep|hibernate)\b", "sleep_computer", 0.9),
            (r"\block(?: computer| screen)?\b", "lock_computer", 0.9),
            
            # Application control - FIXED: Match multi-word app names and single words
            (r"\b(?:open|launch|start)(?: application)?\s+(.+?)(?:\.|$|,)", "open_application", 0.95),
            (r"\bclose(?: application)?\s+(.+?)(?:\.|$|,)", "close_application", 0.95),
            
            # System info
            (r"(?:get |show |what'?s )?(?:my )?ip(?: address)?", "get_ip_address", 0.95),
            (r"(?:get |show |what'?s )?(?:the )?cpu(?: info| usage)?", "get_cpu_info", 0.9),
            (r"(?:get |show |what'?s )?(?:the )?memory(?: info| usage)?", "get_memory_info", 0.9),
            (r"\bsystem (?:status|health|info)\b", "get_system_status", 0.95),
            (r"\bdisk space\b", "check_disk_space", 0.95),
            
            # Network
            (r"(?:run |do )?speed test", "run_speed_test", 0.95),
            (r"\btest (?:network |internet )?connect(?:ion|ivity)?\b", "test_network_connectivity", 0.9),
            (r"\bping\b", "test_network_connectivity", 0.8),
            
            # Volume
            (r"(?:set |change )?volume(?: to)?\s+(\d+)", "set_volume", 0.95),
            (r"\bvolume up\b", "set_volume", 0.9),
            (r"\bvolume down\b", "set_volume", 0.9),
            (r"\bmute\b", "set_volume", 0.9),
            
            # Time/Date
            (r"\bwhat'?s?(?: is)? the time\b", "get_time", 1.0),
            (r"\bwhat'?s?(?: is)? (?:the )?date\b", "get_date", 1.0),
            
            # Personality switching
            (r"\b(?:personality|change personality|set personality|switch.*?personality).*?(default|conversation)", "switch_personality", 0.95),
            (r"\b(default|conversation)\s+(?:mode|personality)", "switch_personality", 0.9),
            (r"\benable\s+(default|conversation)", "switch_personality", 0.9),
            
            # File operations
            (r"\bcreate folder\s+(.+?)(?:\.|$)", "create_folder", 0.95),
            (r"\bdelete\s+(.+?)(?:\.|$)", "delete_path", 0.9),
            (r"\b(?:search|find)(?: for)?\s+(.+?)(?:\.|$)", "search_files", 0.85),
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
        
        # Clean the text
        text_lower = text.lower().strip()
        # Remove leading punctuation/fragments from wake word extraction issues
        text_lower = re.sub(r'^[,\s\t]+', '', text_lower)
        
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
                app_name = match.group(1).strip()
                # Remove trailing punctuation and extra whitespace
                app_name = re.sub(r'[.\s]+$', '', app_name)
                app_name = re.sub(r'\s+', ' ', app_name)
                slots["app_name"] = app_name
            
            elif intent_name == "set_volume":
                # Extract volume level
                if match.lastindex and match.lastindex >= 1:
                    try:
                        slots["level"] = int(match.group(1))
                    except (ValueError, IndexError):
                        pass
                
                if "level" not in slots:
                    if "up" in text:
                        slots["level"] = "+10"
                    elif "down" in text:
                        slots["level"] = "-10"
                    elif "mute" in text:
                        slots["level"] = 0
            
            elif intent_name == "switch_personality":
                # Extract personality mode (default or conversation)
                if match.lastindex and match.lastindex >= 1:
                    mode = match.group(1).strip()
                    slots["mode"] = mode
            
            elif intent_name == "create_folder":
                path = match.group(1).strip()
                path = re.sub(r'[.\s]+$', '', path)
                slots["path"] = path
            
            elif intent_name == "delete_path":
                path = match.group(1).strip()
                path = re.sub(r'[.\s]+$', '', path)
                slots["path"] = path
            
            elif intent_name == "search_files":
                query = match.group(1).strip()
                query = re.sub(r'[.\s]+$', '', query)
                slots["query"] = query
        
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