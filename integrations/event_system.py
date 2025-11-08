# -*- coding: utf-8 -*-
"""
Event-Driven Automation System
Phase 5.1: Event-driven automation triggers
"""

import logging
import threading
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime
from enum import Enum
import json


class EventType(Enum):
    """Event types"""
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    PROCESS_STARTED = "process_started"
    PROCESS_TERMINATED = "process_terminated"
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"
    NETWORK_CONNECTION = "network_connection"
    SYSTEM_EVENT = "system_event"
    CUSTOM = "custom"


class Event:
    """Represents an event."""
    
    def __init__(self, event_type: EventType, source: str, data: Optional[Dict] = None):
        """
        Initialize event.
        
        Args:
            event_type: Type of event
            source: Event source
            data: Event data
        """
        self.event_type = event_type
        self.source = source
        self.data = data or {}
        self.timestamp = datetime.now()
        self.id = f"{event_type.value}_{self.timestamp.timestamp()}"


class EventSystem:
    """
    Event-driven automation system for triggers and subscriptions.
    """
    
    def __init__(self):
        """Initialize Event System."""
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.event_history: List[Event] = []
        self.lock = threading.Lock()
        self.max_history = 1000
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Handler function that takes (event: Event) as parameter
        """
        with self.lock:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            self.subscribers[event_type].append(handler)
            logging.info(f"Subscribed to {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Unsubscribe from an event type."""
        with self.lock:
            if event_type in self.subscribers:
                if handler in self.subscribers[event_type]:
                    self.subscribers[event_type].remove(handler)
                    logging.info(f"Unsubscribed from {event_type.value}")
    
    def publish(self, event: Event):
        """
        Publish an event to all subscribers.
        
        Args:
            event: Event to publish
        """
        # Add to history
        with self.lock:
            self.event_history.append(event)
            if len(self.event_history) > self.max_history:
                self.event_history.pop(0)
        
        # Notify subscribers
        handlers = []
        with self.lock:
            handlers = self.subscribers.get(event.event_type, []).copy()
        
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logging.exception(f"Error in event handler for {event.event_type.value}")
    
    def publish_event(self, event_type: EventType, source: str, data: Optional[Dict] = None):
        """Convenience method to publish an event."""
        event = Event(event_type, source, data)
        self.publish(event)
    
    def get_event_history(self, event_type: Optional[EventType] = None,
                         limit: int = 100) -> List[Event]:
        """
        Get event history.
        
        Args:
            event_type: Optional filter by event type
            limit: Maximum number of events to return
            
        Returns:
            List of events
        """
        with self.lock:
            events = self.event_history.copy()
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events[-limit:]
    
    def clear_history(self):
        """Clear event history."""
        with self.lock:
            self.event_history.clear()

