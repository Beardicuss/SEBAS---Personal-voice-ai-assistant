
import threading
from typing import Callable, Dict, List, Any
import logging


class EventBus:
    """Centralized global event dispatcher."""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()

    # -------------------------------------------------------------
    # Register listener for event_name
    # -------------------------------------------------------------
    def subscribe(self, event_name: str, callback: Callable):
        with self._lock:
            self._listeners.setdefault(event_name, []).append(callback)
            logging.info(f"[EventBus] subscribed: {callback} to '{event_name}'")

    # -------------------------------------------------------------
    # Emit an event to all subscribers
    # -------------------------------------------------------------
    def emit(self, event_name: str, data: Any = None):
        listeners = self._listeners.get(event_name, [])
        logging.debug(f"[EventBus] emit: '{event_name}' => {len(listeners)} listeners")

        for cb in listeners:
            try:
                cb(data)
            except Exception:
                logging.exception(f"[EventBus] listener failed: {cb}")
