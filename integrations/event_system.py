# -*- coding: utf-8 -*-
"""
Event-Driven Automation System
Phase 5.1: Event-driven automation triggers (improved version)
"""

import logging
import threading
import json
from sebas.typing import Dict, List, Callable, Optional, Any
from sebas.datetime import datetime
from sebas.enum import Enum


class EventType(Enum):
    """Supported event types."""
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
    """Represents a single event instance."""

    def __init__(self, event_type: EventType, source: str, data: Optional[Dict] = None):
        self.event_type = event_type
        self.source = source
        self.data = data or {}
        self.timestamp = datetime.now()
        self.id = f"{event_type.value}_{self.timestamp.timestamp()}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.event_type.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


class EventSystem:
    """Thread-safe event-driven automation system."""

    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable[[Event], None]]] = {}
        self.event_history: List[Event] = []
        self.lock = threading.Lock()
        self.max_history = 1000

    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]):
        """Subscribe a handler to an event type."""
        with self.lock:
            self.subscribers.setdefault(event_type, []).append(handler)
            logging.info(f"[EventSystem] Subscribed to {event_type.value}: {handler}")

    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], None]):
        """Unsubscribe a handler from an event type."""
        with self.lock:
            handlers = self.subscribers.get(event_type)
            if handlers and handler in handlers:
                handlers.remove(handler)
                logging.info(f"[EventSystem] Unsubscribed from {event_type.value}: {handler}")

    def publish(self, event: Event):
        """Publish an event to all subscribers."""
        with self.lock:
            self.event_history.append(event)
            if len(self.event_history) > self.max_history:
                self.event_history.pop(0)
            handlers = list(self.subscribers.get(event.event_type, []))

        # Notify subscribers asynchronously
        for handler in handlers:
            def _safe_call(h=handler):
                try:
                    h(event)
                except Exception:
                    logging.exception(f"[EventSystem] Error in handler {h} for {event.event_type.value}")
            t = threading.Thread(target=_safe_call, daemon=True)
            t.start()

    def publish_event(self, event_type: EventType, source: str, data: Optional[Dict] = None):
        """Convenience wrapper to create and publish an event."""
        event = Event(event_type, source, data)
        self.publish(event)

    def get_event_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        """Return the most recent events, optionally filtered by type."""
        with self.lock:
            events = list(self.event_history)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def export_history_json(self, path: str):
        """Export event history to a JSON file."""
        with self.lock:
            data = [e.to_dict() for e in self.event_history]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"[EventSystem] Event history exported to {path}")
        except Exception:
            logging.exception("[EventSystem] Failed to export event history")

    def clear_history(self):
        """Clear stored event history."""
        with self.lock:
            self.event_history.clear()
            logging.info("[EventSystem] Cleared event history")