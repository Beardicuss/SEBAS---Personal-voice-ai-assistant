# -*- coding: utf-8 -*-
"""
Enhanced Natural Language Understanding
Phase 6.2: Complex command parsing and context awareness
"""

import logging
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from collections import defaultdict
import re


class ContextManager:
    """
    Manages conversation context for better command understanding.
    """
    
    def __init__(self):
        """Initialize Context Manager."""
        self.context_stack: List[Dict[str, Any]] = []
        self.entity_cache: Dict[str, Any] = {}
        self.conversation_history: List[Dict[str, Any]] = []
        self.max_history = 50
    
    def push_context(self, context: Dict[str, Any]):
        """Push context onto stack."""
        self.context_stack.append(context)
    
    def pop_context(self) -> Optional[Dict[str, Any]]:
        """Pop context from stack."""
        return self.context_stack.pop() if self.context_stack else None
    
    def get_current_context(self) -> Dict[str, Any]:
        """Get current context."""
        if self.context_stack:
            return self.context_stack[-1]
        return {}
    
    def add_to_history(self, user_input: str, intent: str, slots: Dict[str, Any], response: str):
        """Add conversation turn to history."""
        self.conversation_history.append({
            'timestamp': datetime.now().isoformat(),
            'user_input': user_input,
            'intent': intent,
            'slots': slots,
            'response': response
        })
        
        if len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)
    
    def get_recent_context(self, turns: int = 3) -> List[Dict[str, Any]]:
        """Get recent conversation turns."""
        return self.conversation_history[-turns:] if self.conversation_history else []
    
    def extract_entities_from_history(self) -> Dict[str, Any]:
        """Extract entities from conversation history."""
        entities = {}
        
        for turn in self.conversation_history[-10:]:
            slots = turn.get('slots', {})
            for key, value in slots.items():
                if value and isinstance(value, str):
                    if key not in entities:
                        entities[key] = []
                    if value not in entities[key]:
                        entities[key].append(value)
        
        return entities


class MultiPartCommandParser:
    """
    Parses complex multi-part commands.
    """
    
    def __init__(self):
        """Initialize Multi-Part Command Parser."""
        self.command_separators = [' and ', ' then ', ' after that ', ' also ', ', ']
        self.conjunction_patterns = [
            r'\s+and\s+',
            r'\s+then\s+',
            r'\s+after\s+that\s+',
            r'\s+also\s+',
            r',\s+'
        ]
    
    def parse_multipart_command(self, command: str) -> List[Dict[str, str]]:
        """
        Parse a multi-part command into individual commands.
        
        Args:
            command: Multi-part command string
            
        Returns:
            List of parsed command dicts
        """
        commands = []
        
        # Split by common separators
        parts = [command]
        for pattern in self.conjunction_patterns:
            new_parts = []
            for part in parts:
                new_parts.extend(re.split(pattern, part, flags=re.IGNORECASE))
            parts = new_parts
        
        # Clean and parse each part
        for part in parts:
            part = part.strip()
            if part:
                # Extract intent and slots (simplified - in production use proper NLU)
                intent = self._extract_intent(part)
                slots = self._extract_slots(part, intent)
                
                commands.append({
                    'command': part,
                    'intent': intent,
                    'slots': slots
                })
        
        return commands
    
    def _extract_intent(self, command: str) -> str:
        """Extract intent from command (simplified)."""
        command_lower = command.lower()
        
        # Simple keyword-based intent detection
        if any(word in command_lower for word in ['copy', 'move', 'backup']):
            return 'file_operation'
        elif any(word in command_lower for word in ['start', 'stop', 'restart']):
            return 'service_operation'
        elif any(word in command_lower for word in ['check', 'show', 'list', 'get']):
            return 'query_operation'
        elif any(word in command_lower for word in ['create', 'add', 'new']):
            return 'create_operation'
        elif any(word in command_lower for word in ['delete', 'remove']):
            return 'delete_operation'
        
        return 'unknown'
    
    def _extract_slots(self, command: str, intent: str) -> Dict[str, Any]:
        """Extract slots from command (simplified)."""
        slots = {}
        command_lower = command.lower()
        
        # Extract file paths (simplified)
        path_pattern = r'[A-Za-z]:\\[^\s]+|[A-Za-z]:/[^\s]+|/[^\s]+'
        paths = re.findall(path_pattern, command)
        if paths:
            if 'source' not in slots:
                slots['source'] = paths[0]
            if len(paths) > 1:
                slots['destination'] = paths[1]
        
        # Extract service names
        if 'service' in command_lower:
            service_match = re.search(r'service\s+(\w+)', command_lower)
            if service_match:
                slots['service_name'] = service_match.group(1)
        
        # Extract numbers
        numbers = re.findall(r'\d+', command)
        if numbers:
            slots['quantity'] = int(numbers[0])
        
        return slots


class LearningSystem:
    """
    Learns from user corrections and feedback.
    """
    
    def __init__(self, learning_file: Optional[str] = None):
        """
        Initialize Learning System.
        
        Args:
            learning_file: Path to store learning data
        """
        if learning_file is None:
            learning_file = os.path.join(os.path.expanduser('~'), '.sebas_learning.json')
        
        self.learning_file = learning_file
        self.corrections: Dict[str, List[Dict[str, Any]]] = defaultdict(lambda: [])
        self.intent_mappings: Dict[str, str] = {}
        self.slot_mappings: Dict[str, Dict[str, str]] = defaultdict(lambda: {})
        
        self._load_learning_data()
    
    def _load_learning_data(self):
        """Load learning data from file."""
        try:
            if os.path.exists(self.learning_file):
                with open(self.learning_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert loaded dicts back to defaultdict
                    corrections_dict = data.get('corrections', {})
                    self.corrections = defaultdict(lambda: [], **corrections_dict)
                    self.intent_mappings = data.get('intent_mappings', {})
                    slot_mappings_dict = data.get('slot_mappings', {})
                    self.slot_mappings = defaultdict(lambda: {}, **slot_mappings_dict)
        except Exception:
            logging.exception("Failed to load learning data")
    
    def _save_learning_data(self):
        """Save learning data to file."""
        try:
            data = {
                'corrections': self.corrections,
                'intent_mappings': self.intent_mappings,
                'slot_mappings': self.slot_mappings,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.learning_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
        except Exception:
            logging.exception("Failed to save learning data")
    
    def record_correction(self, original_intent: str, corrected_intent: str,
                         original_slots: Dict[str, Any], corrected_slots: Dict[str, Any],
                         user_input: str):
        """
        Record a user correction.
        
        Args:
            original_intent: Originally detected intent
            corrected_intent: Correct intent
            original_slots: Original slots
            corrected_slots: Correct slots
            user_input: Original user input
        """
        correction = {
            'timestamp': datetime.now().isoformat(),
            'user_input': user_input,
            'original_intent': original_intent,
            'corrected_intent': corrected_intent,
            'original_slots': original_slots,
            'corrected_slots': corrected_slots
        }
        
        self.corrections[user_input.lower()].append(correction)
        
        # Update mappings
        if original_intent != corrected_intent:
            self.intent_mappings[original_intent] = corrected_intent
        
        for key, value in corrected_slots.items():
            if key in original_slots and original_slots[key] != value:
                self.slot_mappings[original_intent][key] = value
        
        self._save_learning_data()
    
    def apply_learning(self, user_input: str, detected_intent: str,
                      detected_slots: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Apply learned corrections to intent and slots.
        
        Args:
            user_input: User input
            detected_intent: Detected intent
            detected_slots: Detected slots
            
        Returns:
            Tuple of (corrected_intent, corrected_slots)
        """
        corrected_intent = detected_intent
        corrected_slots = detected_slots.copy()
        
        # Check for exact match corrections
        if user_input.lower() in self.corrections:
            latest_correction = self.corrections[user_input.lower()][-1]
            corrected_intent = latest_correction['corrected_intent']
            corrected_slots = latest_correction['corrected_slots']
            return corrected_intent, corrected_slots
        
        # Apply intent mapping
        if detected_intent in self.intent_mappings:
            corrected_intent = self.intent_mappings[detected_intent]
        
        # Apply slot mappings
        if detected_intent in self.slot_mappings:
            for key, value in self.slot_mappings[detected_intent].items():
                if key in corrected_slots:
                    corrected_slots[key] = value
        
        return corrected_intent, corrected_slots


class IntentResolver:
    """
    Resolves ambiguous commands to specific intents.
    """
    
    def __init__(self):
        """Initialize Intent Resolver."""
        self.ambiguity_patterns = {
            'file_or_service': {
                'patterns': ['start', 'stop', 'open', 'close'],
                'disambiguation': {
                    'file': ['file', 'document', 'folder', 'path'],
                    'service': ['service', 'process', 'application']
                }
            },
            'create_or_modify': {
                'patterns': ['create', 'make', 'add', 'new'],
                'disambiguation': {
                    'create': ['new', 'from scratch', 'empty'],
                    'modify': ['update', 'change', 'edit', 'modify']
                }
            }
        }
    
    def resolve_ambiguous_intent(self, user_input: str, candidates: List[str],
                                context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Resolve ambiguous intent from candidates.
        
        Args:
            user_input: User input
            candidates: List of candidate intents
            context: Optional context
            
        Returns:
            Resolved intent or None
        """
        user_lower = user_input.lower()
        
        # Check for explicit disambiguation keywords
        for candidate in candidates:
            if candidate.lower() in user_lower:
                return candidate
        
        # Use context if available
        if context:
            recent_intents = [t.get('intent') for t in context.get('recent_history', [])]
            if recent_intents:
                # Prefer intents similar to recent ones
                for intent in recent_intents:
                    if intent in candidates:
                        return intent
        
        # Use pattern matching
        for ambiguity_type, patterns in self.ambiguity_patterns.items():
            for pattern in patterns['patterns']:
                if pattern in user_lower:
                    disambiguation = patterns['disambiguation']
                    for category, keywords in disambiguation.items():
                        if any(keyword in user_lower for keyword in keywords):
                            # Map to specific intent based on category
                            for candidate in candidates:
                                if category in candidate.lower():
                                    return candidate
        
        # Default: return first candidate
        return candidates[0] if candidates else None