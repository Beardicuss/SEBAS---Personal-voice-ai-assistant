"""
Natural Language Understanding - Stage 2 Enhanced
Extended pattern matching for all Stage 2 skills
"""

from datetime import datetime
import logging
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
    """Enhanced NLU with Stage 2 patterns"""
    
    def __init__(self):
        # Pattern-based intents (regex patterns)
        self.patterns: List[Tuple[str, str, float]] = [
            # ============= STAGE 1 - Core =============
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
            (r"(check |get )?disk space", "check_disk_space", 0.95),
            
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
            
            # ============= STAGE 2 - Extended =============
            # Storage/Disk
            (r"get disk info", "get_disk_info", 0.95),
            (r"disk info(rmation)?", "get_disk_info", 0.9),
            
            # Security/Defender
            (r"(get |show )?defender status", "get_defender_status", 0.95),
            (r"(run |start )?defender scan", "run_defender_scan", 0.95),
            (r"(get |show )?defender threats", "get_defender_threats", 0.95),
            
            # Services
            (r"start service (.+)", "start_service", 0.95),
            (r"stop service (.+)", "stop_service", 0.95),
            (r"restart service (.+)", "restart_service", 0.95),
            (r"(get |show )?service status (.+)", "get_service_status", 0.95),
            (r"list services", "list_services", 0.95),
            
            # Monitoring
            (r"(get |show )?(system )?performance", "get_system_performance", 0.95),
            (r"(get |show )?network stats", "get_network_stats", 0.95),
            (r"(get |show )?disk (io|activity)", "get_disk_io", 0.95),
            (r"check memory leaks", "check_memory_leaks", 0.95),
            (r"analyze startup", "analyze_startup_impact", 0.95),
            
            # File operations (extended)
            (r"(list |show )?recent files", "list_recent_files", 0.95),
            (r"open recent( file)?", "open_recent_file", 0.9),
            (r"(show |get )?file info (.+)", "show_file_info", 0.9),
            
            # Automation
            (r"list workflows", "list_workflows", 0.95),
            (r"create workflow (.+)", "create_workflow", 0.95),
            (r"execute workflow (.+)", "execute_workflow", 0.95),
            (r"(list |show )?scheduled tasks", "list_scheduled_tasks", 0.95),
            (r"set reminder (.+)", "set_reminder", 0.9),
            (r"list reminders", "list_reminders", 0.95),
            
            # ============= STAGE 2 NEW - Advanced =============
            # Smart Home
            (r"turn (on|off) (.+)", "smarthome_toggle", 0.9),
            (r"(switch|toggle) (.+)", "smarthome_toggle", 0.85),
            
            # AI Analytics
            (r"detect anomalies", "detect_anomalies", 0.95),
            (r"predict disk failure", "predict_disk_failure", 0.95),
            (r"predict memory leak", "predict_memory_leak", 0.95),
            (r"(get )?performance suggestions", "get_performance_suggestions", 0.95),
            (r"diagnose (issue|problem)", "diagnose_issue", 0.9),
            
            # Compliance
            (r"log activity", "log_activity", 0.95),
            (r"(get |show )?activity log", "get_activity_log", 0.95),
            (r"(get |show )?audit events", "get_audit_events", 0.95),
            (r"generate compliance report", "generate_compliance_report", 0.95),
            
            # Code
            (r"create function (.+)", "create_function", 0.95),
            (r"create class (.+)", "create_class", 0.95),
            (r"generate loop", "generate_loop", 0.9),
            (r"list code snippets", "list_code_snippets", 0.95),
        ]
        
        # Keyword-based fallback
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
            # Stage 2 keywords
            "defender": "get_defender_status",
            "services": "list_services",
            "workflows": "list_workflows",
            "anomalies": "detect_anomalies",
        }
    
    def parse(self, text: str) -> Optional[IntentBase]:
        """Legacy method for backward compatibility."""
        intent, _ = self.get_intent_with_confidence(text)
        if intent:
            return IntentBase(name=intent.name, slots=intent.slots)
        return None
    
    def get_intent_with_confidence(self, text: str) -> Tuple[Optional[IntentWithConfidence], List[str]]:
        """Parse user input and extract intent with confidence score."""
        if not text:
            return None, []
        
        text_lower = text.lower().strip()
        
        # Try pattern matching first
        for pattern, intent_name, confidence in self.patterns:
            match = re.search(pattern, text_lower)
            if match:
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
                    confidence=0.7,
                    fuzzy_match=keyword
                ), []
        
        return None, []
    
    def _extract_slots(self, match, intent_name: str, text: str) -> Dict[str, Any]:
        """Extract slot values from regex match."""
        slots = {}
        
        if match.groups():
            if intent_name in ["open_application", "close_application"]:
                slots["app_name"] = match.group(1)
            
            elif intent_name == "set_volume":
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
                path_match = re.search(r"(folder|delete) (.+)", text)
                if path_match:
                    slots["path"] = path_match.group(2).strip()
            
            elif intent_name == "search_files":
                search_match = re.search(r"(search|find) (?:for )?(.+)", text)
                if search_match:
                    slots["query"] = search_match.group(2).strip()
            
            # Service operations
            elif intent_name in ["start_service", "stop_service", "restart_service", "get_service_status"]:
                service_match = re.search(r"service (.+)", text)
                if service_match:
                    slots["name"] = service_match.group(1).strip()
            
            # Smart home
            elif intent_name == "smarthome_toggle":
                state_match = re.search(r"turn (on|off) (.+)", text)
                if state_match:
                    slots["state"] = state_match.group(1)
                    slots["device"] = state_match.group(2).strip()
        
        return slots
    
    def _extract_slots_keyword(self, text: str, intent_name: str) -> Dict[str, Any]:
        """Extract slots for keyword-matched intents."""
        slots = {}
        
        if intent_name == "open_application":
            for keyword in self.keyword_intents:
                if keyword in text and self.keyword_intents[keyword] == intent_name:
                    slots["app_name"] = keyword
                    break
        
        elif intent_name == "set_volume":
            volume_match = re.search(r"(\d+)", text)
            if volume_match:
                slots["level"] = int(volume_match.group(1))
        
        return slots


class ContextManager:
    """Manages conversation context and history."""
    
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
# Add these classes to integrations/nlu_enhancer.py after ContextManager

class MultiPartCommandParser:
    """Parse multi-part commands like 'open chrome and play music'"""
    
    def parse_multipart_command(self, text: str) -> List[str]:
        """Split compound commands"""
        # Simple split on conjunctions
        separators = [' and ', ' then ', ' also ', ', ']
        commands = [text]
        
        for sep in separators:
            new_commands = []
            for cmd in commands:
                new_commands.extend(cmd.split(sep))
            commands = new_commands
        
        return [c.strip() for c in commands if c.strip()]


class LearningSystem:
    """Learn from user corrections"""
    
    def __init__(self):
        self.corrections = []
        self.correction_log = []
    
    def record_correction(self, original_intent: str, corrected_intent: str,
                         original_slots: Dict[str, Any], corrected_slots: Dict[str, Any], 
                         user_input: str):
        """Record a user correction for future learning"""
        correction = {
            'timestamp': datetime.now().isoformat(),
            'original': {'intent': original_intent, 'slots': original_slots},
            'corrected': {'intent': corrected_intent, 'slots': corrected_slots},
            'input': user_input
        }
        self.corrections.append(correction)
        self.correction_log.append(correction)
        logging.info(f"[Learning] Recorded correction: {original_intent} -> {corrected_intent}")
    
    def get_corrections(self, limit: int = 10) -> List[Dict]:
        """Get recent corrections"""
        return self.correction_log[-limit:]


class IntentResolver:
    """Resolve ambiguous intents using context and heuristics"""
    
    def __init__(self):
        self.resolution_history = []
    
    def resolve_ambiguous_intent(self, user_input: str, 
                                 candidates: List[str]) -> Optional[str]:
        """
        Choose best intent from candidates.
        
        Args:
            user_input: User's original input
            candidates: List of possible intent names
            
        Returns:
            Best matching intent or None
        """
        if not candidates:
            return None
        
        # Single candidate - easy
        if len(candidates) == 1:
            return candidates[0]
        
        # Score candidates by keyword matching
        scores = {}
        for intent in candidates:
            score = 0
            intent_words = intent.lower().replace('_', ' ').split()
            input_words = user_input.lower().split()
            
            # Count matching words
            for word in intent_words:
                if word in input_words:
                    score += 1
            
            scores[intent] = score
        
        # Return highest scoring intent
        if scores:
            best_intent = max(scores.items(), key=lambda x: x[1])[0]
            self.resolution_history.append({
                'input': user_input,
                'candidates': candidates,
                'resolved': best_intent,
                'scores': scores
            })
            return best_intent
        
        # Fallback: return first candidate
        return candidates[0]