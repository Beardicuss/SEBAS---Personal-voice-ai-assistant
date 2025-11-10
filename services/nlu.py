# -*- coding: utf-8 -*-
"""
Natural Language Understanding (NLU)
Phase 6: Intent detection, fuzzy matching, context, and slot extraction
"""

import re
import threading
import logging
import difflib
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Any, Optional, List, Tuple

# === Optional fuzzy matching support ===
try:
    from fuzzywuzzy import fuzz, process  # external package
    FUZZY_AVAILABLE = True
except ImportError:
    from difflib import SequenceMatcher

    class _FuzzStub:
        """Fallback stub for fuzz.ratio if fuzzywuzzy is not installed."""
        @staticmethod
        def ratio(a: str, b: str) -> int:
            return int(difflib.SequenceMatcher(None, a, b).ratio() * 100)

    fuzz = _FuzzStub()
    process = None
    FUZZY_AVAILABLE = False


# --------------------------------------------------------------------------- #
#                                Data Models                                  #
# --------------------------------------------------------------------------- #

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
    slots: Optional[Dict[str, Any]] = None  # Added to silence Pylance complaints


# --------------------------------------------------------------------------- #
#                                  NLU CORE                                   #
# --------------------------------------------------------------------------- #

class SimpleNLU:
    """Enhanced pattern/rule-based NLU for local use.
    Provides: intent classification + slot extraction + fuzzy matching + confidence scoring.
    """

    def __init__(self, fuzzy_threshold: float = 0.8, context_manager: Optional['ContextManager'] = None):
        self.fuzzy_threshold = fuzzy_threshold
        self.context_manager = context_manager
        self._lock = threading.RLock()
        self._pattern_cache: Dict[str, Any] = {}
        self._fuzzy_cache: Dict[str, Any] = {}

        # Entity extraction patterns
        self.entity_patterns = {
            'date': [
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
                r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\d{2,4})?\b',
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

        # Command patterns
        self.patterns = [
            (r"set voice to (?P<profile>\w+)", "set_voice"),
            (r"adjust voice rate to (?P<rate>\d+)", "adjust_voice_rate"),
            (r"adjust voice volume to (?P<volume>\d+)%?", "adjust_voice_volume"),
            (r"adjust voice pitch to (?P<pitch>-?\d+)", "adjust_voice_pitch"),
            (r"schedule (?:an )?event (?P<title>.+) at (?P<time>.+)", "schedule_event"),
            (r"turn (?P<device>.+) (?P<state>on|off)", "smarthome_toggle"),
            (r"turn (?P<state>on|off) (?P<device>.+)", "smarthome_toggle"),
            (r"set (?P<device>.+) to (?P<brightness>\d+)%?", "smarthome_set_light"),
            (r"open (?P<app_name>.+?)(?: and (?P<context>.+))?", "open_app_with_context"),
            (r"close (?P<app_name>.+)", "close_app"),
            (r"create folder (?P<path>.+)", "create_folder"),
            (r"delete (?P<path>.+)", "delete_path"),
            (r"move (?P<source>.+) to (?P<destination>.+)", "move_file"),
            (r"copy (?P<source>.+) to (?P<destination>.+)", "copy_file"),
            (r"rename (?P<old_path>.+) to (?P<new_name>.+)", "rename_file"),
            (r"search apps for (?P<query>.+)", "search_apps"),
        ]

        self.pattern_priorities = {
            'compound': 10,
            'specific': 8,
            'general': 5,
            'fallback': 1
        }

    # ----------------------------------------------------------------------- #
    #                                PARSING                                 #
    # ----------------------------------------------------------------------- #

    def parse(self, text: str, use_fuzzy: bool = True, use_context: bool = True) -> Optional[Intent]:
        logging.debug(f"NLU parsing: {text}")
        t = (text or "").strip().lower()

        with self._lock:
            exact_match = self._exact_pattern_match(t)
            if exact_match:
                enhanced_slots = self._enhance_slots_with_entities(t, exact_match.slots)
                exact_match.slots.update(enhanced_slots)
                logging.debug(f"Exact match found: {exact_match.name} ({exact_match.confidence:.2f})")
                return exact_match

            if use_fuzzy:
                fuzzy_match = self._fuzzy_pattern_match(t)
                if fuzzy_match:
                    return Intent(
                        name=fuzzy_match.intent_name,
                        slots=fuzzy_match.slots or {},
                        confidence=fuzzy_match.confidence,
                        fuzzy_match=fuzzy_match.original_text
                    )

            if use_context and self.context_manager:
                context_match = self._context_aware_match(t)
                if context_match:
                    return context_match

            multi_intent = self._detect_multi_intent(t)
            if multi_intent:
                return multi_intent

            logging.debug("No match found for text")
            return None

    # ----------------------------------------------------------------------- #
    #                          MATCHING UTILITIES                             #
    # ----------------------------------------------------------------------- #

    def _exact_pattern_match(self, text: str) -> Optional[Intent]:
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
                        best_match = Intent(name=name, slots=slots, confidence=confidence)
                        best_confidence = confidence
            except re.error as e:
                logging.warning(f"Regex error in pattern '{pat}': {e}")
        return best_match

    def _fuzzy_pattern_match(self, text: str) -> Optional[FuzzyMatchResult]:
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

        self._fuzzy_cache[cache_key] = best_match
        return best_match

    def _calculate_fuzzy_similarity(self, text: str, pattern: str) -> float:
        if FUZZY_AVAILABLE:
            cleaned = pattern.replace(r'(?P<', '').replace(r'>.+)', '').replace(r'(?:', '').replace(r')', '')
            return fuzz.ratio(text, cleaned) / 100.0
        else:
            return difflib.SequenceMatcher(None, text, pattern).ratio()

    def _calculate_pattern_confidence(self, pattern: str, text: str) -> float:
        complexity_score = min(1.0, len(pattern) / 100.0)
        text_len, pattern_len = len(text), len(pattern)
        length_ratio = min(text_len, pattern_len) / max(text_len, pattern_len)
        length_bonus = length_ratio * 0.3
        pattern_words = set(re.findall(r'\b\w+\b', pattern))
        text_words = set(re.findall(r'\b\w+\b', text))
        word_overlap = len(pattern_words & text_words) / len(pattern_words) if pattern_words else 0
        word_bonus = word_overlap * 0.4
        confidence = 0.5 + complexity_score + length_bonus + word_bonus
        return min(1.0, confidence)

    # ----------------------------------------------------------------------- #
    #                           SLOT PROCESSING                               #
    # ----------------------------------------------------------------------- #

    def _enhance_slots_with_entities(self, text: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        enhanced: Dict[str, Any] = {}
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    enhanced.setdefault(entity_type, []).extend(matches)

        for entity_type in ['date', 'time']:
            if entity_type in enhanced and len(enhanced[entity_type]) == 1:
                enhanced[entity_type] = enhanced[entity_type][0]
        return enhanced

    def _post_process_slots(self, slots: Dict[str, Any], text: str) -> Dict[str, Any]:
        processed = slots.copy()
        for key, value in processed.items():
            if isinstance(value, str):
                try:
                    processed[key] = float(value) if '.' in value else int(value)
                except ValueError:
                    processed[key] = value.strip()
        return processed

    # ----------------------------------------------------------------------- #
    #                         CONTEXT & MULTI-INTENT                          #
    # ----------------------------------------------------------------------- #

    def _context_aware_match(self, text: str) -> Optional[Intent]:
        if not self.context_manager:
            return None
        last_intent = self.context_manager.last_intent()
        if not last_intent:
            return None

        context_rules = {
            'smarthome_toggle': ['turn', 'switch', 'light', 'device'],
            'smarthome_set_light': ['brightness', 'dim', 'brighten', 'light'],
            'open_app': ['launch', 'start', 'run', 'open'],
        }

        if last_intent.get('name') in context_rules:
            keywords = context_rules[last_intent['name']]
            if any(k in text for k in keywords):
                return Intent(
                    name=last_intent['name'],
                    slots=self._extract_slots_from_context(text, last_intent),
                    confidence=0.7
                )
        return None

    def _extract_slots_from_context(self, text: str, last_intent: Dict[str, Any]) -> Dict[str, Any]:
        slots = last_intent.get('slots', {}).copy()
        slots.update(self._enhance_slots_with_entities(text, {}))
        return slots

    def _detect_multi_intent(self, text: str) -> Optional[Intent]:
        conjunctions = [' and ', ' then ', ' after ', ' followed by ']
        for conj in conjunctions:
            if conj in text:
                parts = text.split(conj, 1)
                if len(parts) == 2:
                    first_intent = self.parse(parts[0].strip(), False, False)
                    second_intent = self.parse(parts[1].strip(), False, False)
                    if first_intent and second_intent:
                        combined = {
                            **first_intent.slots,
                            'second_intent': second_intent.name,
                            'second_slots': second_intent.slots
                        }
                        return Intent(
                            name=first_intent.name,
                            slots=combined,
                            confidence=min(first_intent.confidence, second_intent.confidence) * 0.9
                        )
        return None

    # ----------------------------------------------------------------------- #
    #                            UTILITIES                                    #
    # ----------------------------------------------------------------------- #

    @lru_cache(maxsize=128)
    def get_fallback_suggestions(self, text: str) -> List[str]:
        suggestions: List[str] = []
        patterns = [
            (r"(open|launch|start|run)\s+(\w+)", "Try: '{} {}'"),
            (r"(close|stop|quit)\s+(\w+)", "Try: '{} {}'"),
            (r"(turn|switch)\s+(\w+)\s+(on|off)", "Try: '{} {} {}'"),
            (r"(search|find)\s+(.+)", "Try: 'search for {}'"),
        ]
        for pattern, template in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                suggestions.append(template.format(*match.groups()))
        return suggestions[:3]

    def get_intent_with_confidence(self, text: str) -> Tuple[Optional[Intent], List[str]]:
        intent = self.parse(text)
        suggestions = [] if intent and intent.confidence >= 0.6 else self.get_fallback_suggestions(text)
        return intent, suggestions

    def clear_caches(self):
        with self._lock:
            self._pattern_cache.clear()
            self._fuzzy_cache.clear()


# --------------------------------------------------------------------------- #
#                            CONTEXT MANAGER                                 #
# --------------------------------------------------------------------------- #

class ContextManager:
    def __init__(self, max_history: int = 20):
        self.history: List[Dict[str, Any]] = []
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
