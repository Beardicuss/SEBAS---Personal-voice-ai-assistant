# -*- coding: utf-8 -*-
"""
WebSocket Support for Real-Time Updates
Phase 1.3.5: Real-time communication
"""

import json
import logging
import threading
from typing import Dict, Set, Callable, Optional, Any
from enum import Enum

# Optional WebSocket support
try:
    from sebas.flask_socketio import SocketIO, emit, join_room, leave_room
    WEBSOCKET_AVAILABLE = True
except ImportError:
    try:
        from sebas.flask_socketio import SocketIO, emit, join_room, leave_room
        WEBSOCKET_AVAILABLE = True
    except ImportError:
        WEBSOCKET_AVAILABLE = False
        logging.warning("flask-socketio not available. WebSocket support will be disabled.")


class WebSocketEvent(Enum):
    """WebSocket event types"""
    STATUS_UPDATE = "status.update"
    COMMAND_RESULT = "command.result"
    SYSTEM_EVENT = "system.event"
    NOTIFICATION = "notification"
    ERROR = "error"


class WebSocketManager:
    """
    Manages WebSocket connections for real-time updates.
    """
    
    def __init__(self, flask_app=None):
        """
        Initialize WebSocket manager.
        
        Args:
            flask_app: Flask application instance
        """
        self.app = flask_app
        self.socketio: Optional[Any] = None
        self.clients: Set[str] = set()  # Connected client IDs
        self.rooms: Dict[str, Set[str]] = {}  # room -> set of client IDs
        self.handlers: Dict[str, Callable] = {}
        
        if WEBSOCKET_AVAILABLE and flask_app:
            self._initialize_socketio()
    
    def _initialize_socketio(self):
        """Initialize SocketIO."""
        if not WEBSOCKET_AVAILABLE:
            return
        
        try:
            self.socketio = SocketIO(
                self.app,
                cors_allowed_origins="*",
                async_mode='threading',
                logger=False,
                engineio_logger=False
            )
            
            # Register event handlers
            self._register_handlers()
            logging.info("WebSocket support initialized")
        except Exception:
            logging.exception("Failed to initialize WebSocket support")
            self.socketio = None
    
    def _register_handlers(self):
        """Register WebSocket event handlers."""
        if not self.socketio:
            return
        
        @self.socketio.on('connect')
        def handle_connect(auth):
            """Handle client connection."""
            client_id = auth.get('client_id') if auth else None
            if not client_id:
                return False
            
            self.clients.add(client_id)
            logging.info(f"WebSocket client connected: {client_id}")
            return True
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            # Remove from all rooms
            for room, clients in self.rooms.items():
                clients.discard(str(id(self.socketio)))
            
            logging.info("WebSocket client disconnected")
        
        @self.socketio.on('join_room')
        def handle_join_room(data):
            """Handle room joining."""
            room = data.get('room')
            if room:
                join_room(room)
                if room not in self.rooms:
                    self.rooms[room] = set()
                self.rooms[room].add(str(id(self.socketio)))
                logging.debug(f"Client joined room: {room}")
        
        @self.socketio.on('leave_room')
        def handle_leave_room(data):
            """Handle room leaving."""
            room = data.get('room')
            if room:
                leave_room(room)
                if room in self.rooms:
                    self.rooms[room].discard(str(id(self.socketio)))
                logging.debug(f"Client left room: {room}")
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """Handle event subscription."""
            event_type = data.get('event_type')
            if event_type:
                # Join room for this event type
                room = f"event:{event_type}"
                join_room(room)
                if room not in self.rooms:
                    self.rooms[room] = set()
                self.rooms[room].add(str(id(self.socketio)))
                logging.debug(f"Client subscribed to: {event_type}")
    
    def emit_event(self, event: WebSocketEvent, data: Dict[str, Any], room: Optional[str] = None):
        """
        Emit an event to connected clients.
        
        Args:
            event: Event type
            data: Event data
            room: Optional room to emit to (None = broadcast to all)
        """
        if not self.socketio:
            return
        
        payload = {
            'event': event.value,
            'data': data
        }
        
        try:
            if room:
                self.socketio.emit('event', payload, room=room)
            else:
                self.socketio.emit('event', payload, broadcast=True)
        except Exception:
            logging.exception("Failed to emit WebSocket event")
    
    def emit_to_room(self, event: str, data: Dict[str, Any], room: str):
        """
        Emit an event to a specific room.
        
        Args:
            event: Event name
            data: Event data
            room: Room name
        """
        if not self.socketio:
            return
        
        try:
            self.socketio.emit(event, data, room=room)
        except Exception:
            logging.exception(f"Failed to emit to room: {room}")
    
    def broadcast(self, event: str, data: Dict[str, Any]):
        """
        Broadcast an event to all connected clients.
        
        Args:
            event: Event name
            data: Event data
        """
        if not self.socketio:
            return
        
        try:
            self.socketio.emit(event, data, broadcast=True)
        except Exception:
            logging.exception("Failed to broadcast WebSocket event")
    
    def get_connected_clients(self) -> int:
        """Get number of connected clients."""
        return len(self.clients)
    
    def run(self, app, host='127.0.0.1', port=5001, debug=False):
        """
        Run the SocketIO server.
        
        Args:
            app: Flask application
            host: Host to bind to
            port: Port to bind to
            debug: Debug mode
        """
        if not self.socketio:
            logging.warning("WebSocket not available, cannot run SocketIO server")
            return
        
        self.socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


# Global WebSocket manager instance
_ws_manager: Optional[WebSocketManager] = None


def init_websocket_manager(flask_app=None):
    """Initialize the global WebSocket manager."""
    global _ws_manager
    _ws_manager = WebSocketManager(flask_app=flask_app)


def get_websocket_manager() -> Optional[WebSocketManager]:
    """Get the global WebSocket manager instance."""
    global _ws_manager
    return _ws_manager