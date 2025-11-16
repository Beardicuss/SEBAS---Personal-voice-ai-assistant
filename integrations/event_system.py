# -*- coding: utf-8 -*-
"""
Event System for SEBAS
Phase 5: Event-driven architecture
"""

import logging
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
from enum import Enum
from collections import defaultdict
import threading


class EventType(Enum):
    """Standard SEBAS event types"""
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    COMMAND_RECEIVED = "command.received"
    COMMAND_EXECUTED = "command.executed"
    COMMAND_FAILED = "command.failed"
    SKILL_LOADED = "skill.loaded"
    SKILL_FAILED = "skill.failed"
    AUTOMATION_TRIGGERED = "automation.triggered"
    CUSTOM = "custom"


class Event:
    """Event data structure"""
    
    def __init__(self, event_type: EventType, source: str, data: Dict[str, Any]):
        self.event_type = event_type
        self.source = source
        self.data = data
        self.timestamp = datetime.now()
        self.id = f"{event_type.value}_{self.timestamp.timestamp()}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.event_type.value,
            'source': self.source,
            'data': self.data,
            'timestamp': self.timestamp.isoformat()
        }


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
    
    def record_correction(self, original_intent: str, corrected_intent: str,
                         original_slots: Dict, corrected_slots: Dict, 
                         user_input: str):
        """Record a user correction for future learning"""
        self.corrections.append({
            'original': {'intent': original_intent, 'slots': original_slots},
            'corrected': {'intent': corrected_intent, 'slots': corrected_slots},
            'input': user_input
        })
        logging.info(f"[Learning] Recorded correction: {original_intent} -> {corrected_intent}")


class IntentResolver:
    """Resolve ambiguous intents"""
    
    def resolve_ambiguous_intent(self, user_input: str, 
                                 candidates: List[str]) -> Optional[str]:
        """Choose best intent from candidates"""
        if not candidates:
            return None
        
        # Simple: return first candidate
        # In advanced version, use ML or context
        return candidates[0]


class EventSystem:
    """
    Event bus for SEBAS automation and workflows.
    Supports pub/sub pattern for loose coupling.
    """
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._lock = threading.Lock()
        logging.info("[EventSystem] Initialized")
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to listen for
            callback: Function to call when event occurs
        """
        with self._lock:
            self._subscribers[event_type].append(callback)
            logging.debug(f"[EventSystem] Subscribed to {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, callback: Callable):
        """Unsubscribe from an event type"""
        with self._lock:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                logging.debug(f"[EventSystem] Unsubscribed from {event_type.value}")
    
    def publish_event(self, event_type: EventType, source: str, data: Dict[str, Any]):
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: Type of event
            source: Source module/component
            data: Event payload
        """
        event = Event(event_type, source, data)
        
        # Store in history
        with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)
        
        # Notify subscribers
        subscribers = self._subscribers.get(event_type, [])
        for callback in subscribers:
            try:
                callback(event)
            except Exception:
                logging.exception(f"[EventSystem] Callback error for {event_type.value}")
        
        logging.debug(f"[EventSystem] Published {event_type.value} from {source}")
    
    def get_event_history(self, event_type: Optional[EventType] = None, 
                         limit: int = 100) -> List[Event]:
        """Get recent event history"""
        with self._lock:
            if event_type:
                filtered = [e for e in self._event_history if e.event_type == event_type]
                return filtered[-limit:]
            return self._event_history[-limit:]
    
    def clear_history(self):
        """Clear event history"""
        with self._lock:
            self._event_history.clear()