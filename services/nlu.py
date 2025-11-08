# -*- coding: utf-8 -*-
import re
import threading
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple, TYPE_CHECKING
from functools import lru_cache
from difflib import SequenceMatcher

# Fuzzy matching is already handled gracefully with try/except and fallback to difflib

if TYPE_CHECKING:
    from fuzzywuzzy import fuzz

fuzz = None
try:
    from fuzzywuzzy import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False


@dataclass
class Intent:
    name: str
    slots: Dict[str, Any]
    confidence: float = 1.0
    fuzzy_match: Optional[str] = None


@dataclass
class FuzzyMatchResult:
    intent_name: str
    confidence: float
    original_text: str
    matched_pattern: str


class SimpleNLU:
    """Enhanced pattern/rule-based NLU for local use.
    Provides: intent classification + slot extraction + fuzzy matching + confidence scoring.
    """

    def __init__(self, fuzzy_threshold: float = 0.8, context_manager: Optional['ContextManager'] = None):
        self.fuzzy_threshold = fuzzy_threshold
        self.context_manager = context_manager
        self._lock = threading.RLock()
        self._pattern_cache = {}
        self._fuzzy_cache = {}

        # Entity extraction patterns
        self.entity_patterns = {
            'date': [
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # DD/MM/YYYY or MM/DD/YYYY
                r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\d{2,4})?\b',  # January 1st
                r'\b(?:today|tomorrow|yesterday|next week|last week)\b',
                r'\b\d{1,2}\s+(?:day|week|month|year)s?\s+(?:ago|from now)\b'
            ],
            'time': [
                r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)\b',
                r'\b\d{1,2}:\d{2}\b',
                r'\b(?:noon|midnight|dawn|dusk)\b'
            ],
            'number': [
                r'\b\d+(?:\.\d+)?\b',
                r'\b(?:one|two|three|four|five|six|seven|eight|nine|ten)\b'
            ],
            'location': [
                r'\b(?:in|at|on|to)\s+the\s+(?P<location>\w+)\b',
                r'\b(?:living room|bedroom|kitchen|bathroom|office|dining room)\b'
            ]
        }

        self.patterns = [
            # Voice commands
            (r"set voice to (?P<profile>\w+)", "set_voice"),
            (r"adjust voice rate to (?P<rate>\d+)", "adjust_voice_rate"),
            (r"adjust voice volume to (?P<volume>\d+)%?", "adjust_voice_volume"),
            (r"adjust voice pitch to (?P<pitch>-?\d+)", "adjust_voice_pitch"),

            # Smart home and scheduling
            (r"schedule (?:an )?event (?P<title>.+) at (?P<time>.+)", "schedule_event"),
            (r"turn (?P<device>.+) (?P<state>on|off)", "smarthome_toggle"),
            (r"turn (?P<state>on|off) (?P<device>.+)", "smarthome_toggle"),  # Alternative phrasing
            (r"set (?P<device>.+) to (?P<brightness>\d+)%?", "smarthome_set_light"),
            (r"dim (?P<device>.+) to (?P<brightness>\d+)%?", "smarthome_set_light"),
            (r"brighten (?P<device>.+) to (?P<brightness>\d+)%?", "smarthome_set_light"),
            (r"set temperature to (?P<temperature>\d+) degrees? (?:in )?(?P<room>.+)?", "smarthome_set_climate"),
            (r"set (?P<room>.+) temperature to (?P<temperature>\d+) degrees?", "smarthome_set_climate"),
            (r"activate (?P<scene>.+)", "smarthome_activate_scene"),
            (r"run (?P<scene>.+)", "smarthome_activate_scene"),
            (r"create scene (?P<name>.+) with (?P<devices>.+)", "smarthome_create_scene"),
            (r"is (?P<device>.+) (?P<state>on|off)", "smarthome_query_status"),
            (r"what's the status of (?P<device>.+)", "smarthome_query_status"),
            (r"what's the temperature (?:in )?(?P<room>.+)", "smarthome_query_temperature"),
            (r"turn (?P<state>on|off) all lights", "smarthome_control_multiple"),
            (r"set all lights to (?P<brightness>\d+)%?", "smarthome_control_multiple"),
            (r"(?P<action>lock|unlock) (?P<device>.+)", "smarthome_control_lock"),
            (r"(?P<action>play|pause|stop|next|previous) (?P<device>.+)", "smarthome_control_media"),
            (r"volume (?P<direction>up|down) on (?P<device>.+)", "smarthome_control_media"),
            (r"set volume to (?P<volume>\d+) on (?P<device>.+)", "smarthome_control_media"),
            (r"send email to (?P<to>.+) subject (?P<subject>.+) body (?P<body>.+)", "send_email"),

            # Monitoring commands
            (r"(what is|show me|get) system performance", "get_system_performance"),
            (r"(show|list) network (stats|statistics|connections)", "get_network_stats"),
            (r"(what is|show) disk (activity|i o|io)", "get_disk_io"),
            (r"(check|get) (hardware )?temperatures?", "get_temperatures"),
            (r"(check|show|how much) disk space", "check_disk_space"),
            (r"(run|start|perform) disk cleanup", "run_disk_cleanup"),
            (r"(check for|find) memory leaks?", "check_memory_leaks"),
            (r"analyze startup (impact|programs|items)", "analyze_startup_impact"),
            (r"disable startup (item|program) (?P<item_name>.+)", "disable_startup_item"),

            # Application commands
            (r"open (?P<app_name>.+?)(?: and (?P<context>.+))?", "open_app_with_context"),
            (r"close (?P<app_name>.+)", "close_app"),
            (r"switch to (?P<app_name>.+)", "switch_to_app"),
            (r"minimize (?P<app_name>.+)", "minimize_app"),
            (r"restore (?P<app_name>.+)", "restore_window"),
            (r"minimize all windows", "minimize_all"),
            (r"show desktop", "show_desktop"),
            (r"list frequent apps", "list_frequent_apps"),
            (r"list (?P<category>.+) apps", "list_apps_by_category"),
            (r"add alias (?P<alias>.+) for (?P<app_name>.+)", "add_app_alias"),
            (r"search apps for (?P<query>.+)", "search_apps"),

            # File commands
            (r"open file (?P<path>.+)", "open_file"),
            (r"open recent file(?: number)? (?P<index>\d+)", "open_recent_file"),
            (r"list recent files", "list_recent_files"),
            (r"create folder (?P<path>.+)", "create_folder"),
            (r"delete (?P<path>.+)", "delete_path"),
            (r"move (?P<source>.+) to (?P<destination>.+)", "move_file"),
            (r"copy (?P<source>.+) to (?P<destination>.+)", "copy_file"),
            (r"rename (?P<old_path>.+) to (?P<new_name>.+)", "rename_file"),
            (r"show info for (?P<path>.+)", "show_file_info"),
            (r"preview (?P<path>.+)", "preview_file"),
            (r"backup (?P<path>.+)", "backup_file"),

            # Search commands
            (r"find files? (?P<query>.+?)(?: in (?P<location>.+))?", "search_files_advanced"),
            (r"find (?P<file_type>.+) files?(?: in (?P<location>.+))?", "find_files_by_type"),
            (r"find files? from (?:last )?(?P<date_filter>today|yesterday|week|month)(?: in (?P<location>.+))?", "find_files_by_date"),
            (r"(?:add|remove) search path (?P<path>.+)", "configure_search_paths"),
            (r"list search paths", "configure_search_paths"),

            # Code generation commands
            (r"create function (?P<name>\w+)(?: that (?P<description>.+?))?(?: with params? (?P<params>.+?))?(?: in (?P<language>\w+))?", "create_function"),
            (r"create class (?P<name>\w+)(?: that (?P<description>.+?))?(?: in (?P<language>\w+))?", "create_class"),
            (r"generate (?:a )?(?P<type>for|while) loop(?: for (?P<variable>\w+))?(?: in (?P<iterable>.+?))?(?: in (?P<language>\w+))?", "generate_loop"),
            (r"generate conditional(?: with condition (?P<condition>.+?))?(?: in (?P<language>\w+))?", "generate_conditional"),
            (r"add (?P<code>.+?) to function (?P<function_name>\w+)(?: in (?P<language>\w+))?", "add_code_to_function"),
            (r"insert (?P<statement>.+?) (?P<position>before|after) (?P<target>.+?)(?: in (?P<language>\w+))?", "insert_statement"),
            (r"generate variable (?P<name>\w+)(?: equals? (?P<value>.+?))?(?: in (?P<language>\w+))?", "generate_variable"),
            (r"create (?:code )?snippet (?P<name>\w+)(?: for (?P<description>.+?))?(?: in (?P<language>\w+))?", "create_snippet"),
            (r"validate code(?: in (?P<path>.+?))?(?: for (?P<language>\w+))?", "validate_code"),
            (r"open generated code (?P<filename>.+)", "open_generated_code"),
            (r"save code snippet (?P<name>\w+) (?P<code>.+)(?: in (?P<language>\w+))?", "save_code_snippet"),
            (r"list code snippets", "list_code_snippets"),
            (r"configure code (?:setting )?(?P<setting>\w+) to (?P<value>.+)", "configure_code_settings"),

            # Enhanced compound commands
            (r"open (?P<app1>.+?) and (?:then |)(?:search|look) for (?P<query>.+?)", "open_app_and_search"),
            (r"(?:search|look) for (?P<query>.+?) (?:and |)(?:then |)open (?P<app>.+?)", "open_app_and_search"),
            (r"turn (?P<state>on|off) (?P<device1>.+?) and (?P<device2>.+?)", "smarthome_control_multiple"),
            (r"set (?P<device1>.+?) to (?P<brightness1>\d+)%? and (?P<device2>.+?) to (?P<brightness2>\d+)%?", "smarthome_set_multiple_lights"),
        ]

        # Pattern prioritization for better matching
        self.pattern_priorities = {
            'compound': 10,  # Compound commands get highest priority
            'specific': 8,   # Specific commands
            'general': 5,    # General commands
            'fallback': 1    # Fallback patterns
        }

    def parse(self, text: str, use_fuzzy: bool = True, use_context: bool = True) -> Optional[Intent]:
        """Enhanced parse method with fuzzy matching, confidence scoring, and context awareness."""
        logging.debug(f"NLU parsing: {text}")
        t = (text or "").strip().lower()

        with self._lock:
            # Try exact pattern matching first
            exact_match = self._exact_pattern_match(t)
            if exact_match:
                # Enhance slots with entity extraction
                enhanced_slots = self._enhance_slots_with_entities(t, exact_match.slots)
                exact_match.slots.update(enhanced_slots)
                logging.debug(f"Exact match found: {exact_match.name} with confidence {exact_match.confidence}")
                return exact_match

            # Try fuzzy matching if exact match fails
            if use_fuzzy:
                fuzzy_match = self._fuzzy_pattern_match(t)
                if fuzzy_match:
                    logging.debug(f"Fuzzy match found: {fuzzy_match.intent_name} with confidence {fuzzy_match.confidence}")
                    return Intent(
                        name=fuzzy_match.intent_name,
                        slots=fuzzy_match.slots if hasattr(fuzzy_match, 'slots') else {},
                        confidence=fuzzy_match.confidence,
                        fuzzy_match=fuzzy_match.original_text
                    )

            # Try context-aware resolution
            if use_context and self.context_manager:
                context_match = self._context_aware_match(t)
                if context_match:
                    logging.debug(f"Context-aware match found: {context_match.name}")
                    return context_match

            # Try multi-intent detection
            multi_intent = self._detect_multi_intent(t)
            if multi_intent:
                logging.debug(f"Multi-intent detected: {multi_intent}")
                return multi_intent

            logging.debug("No match found for text")
            return None

    def _exact_pattern_match(self, text: str) -> Optional[Intent]:
        """Perform exact pattern matching with confidence scoring."""
        best_match = None
        best_confidence = 0.0

        for pat, name in self.patterns:
            try:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    confidence = self._calculate_pattern_confidence(pat, text)
                    if confidence > best_confidence:
                        slots = {k: (v or "").strip() for k, v in m.groupdict().items()}
                        slots = self._post_process_slots(slots, text)

                        # Handle special cases
                        if name == "configure_search_paths":
                            slots = self._handle_search_path_special_cases(text, slots)

                        best_match = Intent(name=name, slots=slots, confidence=confidence)
                        best_confidence = confidence
            except re.error as e:
                logging.warning(f"Regex error in pattern '{pat}': {e}")
                continue

        return best_match

    def _fuzzy_pattern_match(self, text: str) -> Optional[FuzzyMatchResult]:
        """Perform fuzzy pattern matching using difflib or fuzzywuzzy."""
        cache_key = text
        if cache_key in self._fuzzy_cache:
            return self._fuzzy_cache[cache_key]

        best_match = None
        best_score = 0.0

        for pat, name in self.patterns:
            fuzzy_score = self._calculate_fuzzy_similarity(text, pat)
            if fuzzy_score >= self.fuzzy_threshold and fuzzy_score > best_score:
                best_score = fuzzy_score
                best_match = FuzzyMatchResult(
                    intent_name=name,
                    confidence=fuzzy_score,
                    original_text=text,
                    matched_pattern=pat
                )

        # Cache the result
        self._fuzzy_cache[cache_key] = best_match
        return best_match if best_match else None

    def _calculate_fuzzy_similarity(self, text: str, pattern: str) -> float:
        """Calculate fuzzy similarity between text and pattern."""
        if FUZZY_AVAILABLE:
            # Use fuzzywuzzy for better accuracy
            return fuzz.ratio(text, pattern.replace(r'(?P<', '').replace(r'>.+)', '').replace(r'(?:', '').replace(r')', '')) / 100.0
        else:
            # Fallback to difflib
            return SequenceMatcher(None, text, pattern).ratio()

    def _calculate_pattern_confidence(self, pattern: str, text: str) -> float:
        """Calculate confidence score based on pattern specificity and match quality."""
        # Base confidence from pattern complexity
        complexity_score = min(1.0, len(pattern) / 100.0)

        # Length match bonus
        text_len = len(text)
        pattern_len = len(pattern.replace(r'(?P<', '').replace(r'>.+)', '').replace(r'(?:', '').replace(r')', ''))
        length_ratio = min(text_len, pattern_len) / max(text_len, pattern_len)
        length_bonus = length_ratio * 0.3

        # Exact word match bonus
        pattern_words = set(re.findall(r'\b\w+\b', pattern))
        text_words = set(re.findall(r'\b\w+\b', text))
        word_overlap = len(pattern_words & text_words) / len(pattern_words) if pattern_words else 0
        word_bonus = word_overlap * 0.4

        confidence = 0.5 + complexity_score + length_bonus + word_bonus
        return min(1.0, confidence)

    def _enhance_slots_with_entities(self, text: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entities like dates, numbers, locations from the text."""
        enhanced = {}

        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    if entity_type not in enhanced:
                        enhanced[entity_type] = []
                    enhanced[entity_type].extend(matches)

        # Convert lists to single values for common entities
        for entity_type in ['date', 'time']:
            if entity_type in enhanced and len(enhanced[entity_type]) == 1:
                enhanced[entity_type] = enhanced[entity_type][0]

        return enhanced

    def _post_process_slots(self, slots: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Post-process extracted slots for better accuracy."""
        processed = slots.copy()

        # Convert numeric strings to numbers where appropriate
        for key, value in processed.items():
            if isinstance(value, str):
                # Try to convert to int/float
                try:
                    if '.' in value:
                        processed[key] = float(value)
                    else:
                        processed[key] = int(value)
                except ValueError:
                    pass

                # Clean up extra whitespace
                processed[key] = value.strip()

        return processed

    def _handle_search_path_special_cases(self, text: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        """Handle special cases for search path configuration."""
        if "add search path" in text:
            slots['action'] = 'add'
            slots['path'] = slots.get('path', '')
        elif "remove search path" in text:
            slots['action'] = 'remove'
            slots['path'] = slots.get('path', '')
        elif "list search paths" in text:
            slots['action'] = 'list'
        return slots

    def _context_aware_match(self, text: str) -> Optional[Intent]:
        """Use context from previous interactions to improve matching."""
        if not self.context_manager:
            return None

        last_intent = self.context_manager.last_intent()
        if not last_intent:
            return None

        # Simple context rules (can be expanded)
        context_rules = {
            'smarthome_toggle': ['turn', 'switch', 'light', 'device'],
            'smarthome_set_light': ['brightness', 'dim', 'brighten', 'light'],
            'open_app': ['launch', 'start', 'run', 'open'],
        }

        if last_intent.get('name') in context_rules:
            keywords = context_rules[last_intent['name']]
            if any(keyword in text for keyword in keywords):
                # Create a new intent based on context
                return Intent(
                    name=last_intent['name'],
                    slots=self._extract_slots_from_context(text, last_intent),
                    confidence=0.7  # Lower confidence for context-based matches
                )

        return None

    def _extract_slots_from_context(self, text: str, last_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Extract slots using context from previous intent."""
        slots = {}

        # Extract common entities
        entities = self._enhance_slots_with_entities(text, {})

        # Use previous intent's slots as defaults/fallbacks
        prev_slots = last_intent.get('slots', {})

        # Merge with new entities
        slots.update(prev_slots)
        slots.update(entities)

        return slots

    def _detect_multi_intent(self, text: str) -> Optional[Intent]:
        """Detect and handle compound commands with multiple intents."""
        # Look for conjunctions that indicate multiple actions
        conjunctions = [' and ', ' then ', ' after ', ' followed by ']

        for conj in conjunctions:
            if conj in text:
                parts = text.split(conj, 1)
                if len(parts) == 2:
                    first_part, second_part = parts

                    # Try to match each part
                    first_intent = self.parse(first_part.strip(), use_fuzzy=False, use_context=False)
                    second_intent = self.parse(second_part.strip(), use_fuzzy=False, use_context=False)

                    if first_intent and second_intent:
                        # Combine into a compound intent
                        combined_slots = {
                            **first_intent.slots,
                            'second_intent': second_intent.name,
                            'second_slots': second_intent.slots
                        }

                        # Determine primary intent (first one usually takes precedence)
                        primary_name = first_intent.name
                        if 'open_app_and_search' in [first_intent.name, second_intent.name]:
                            primary_name = 'open_app_and_search'

                        return Intent(
                            name=primary_name,
                            slots=combined_slots,
                            confidence=min(first_intent.confidence, second_intent.confidence) * 0.9
                        )

        return None

    @lru_cache(maxsize=128)
    def get_fallback_suggestions(self, text: str) -> List[str]:
        """Provide fallback suggestions for unrecognized commands."""
        suggestions = []

        # Common command patterns
        patterns = [
            (r"(open|launch|start|run)\s+(\w+)", "Try: '{} {}'"),
            (r"(close|stop|quit)\s+(\w+)", "Try: '{} {}'"),
            (r"(turn|switch)\s+(\w+)\s+(on|off)", "Try: '{} {} {}'"),
            (r"(search|find)\s+(.+)", "Try: 'search for {}'"),
        ]

        for pattern, template in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                suggestion = template.format(*match.groups())
                suggestions.append(suggestion)

        return suggestions[:3]  # Limit to top 3 suggestions

    def get_intent_with_confidence(self, text: str) -> Tuple[Optional[Intent], List[str]]:
        """Get intent with confidence and fallback suggestions."""
        intent = self.parse(text)
        suggestions = []

        if not intent or intent.confidence < 0.6:
            suggestions = self.get_fallback_suggestions(text)

        return intent, suggestions

    def clear_caches(self):
        """Clear all caches for memory management."""
        with self._lock:
            self._pattern_cache.clear()
            self._fuzzy_cache.clear()


class ContextManager:
    def __init__(self, max_history: int = 20):
        self.history = []
        self.max_history = max_history

    def add(self, entry: Dict[str, Any]):
        self.history.append(entry)
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def last_intent(self) -> Optional[Dict[str, Any]]:
        for item in reversed(self.history):
            if item.get("type") == "intent":
                return item
        return None
