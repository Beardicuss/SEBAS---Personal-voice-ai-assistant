"""
SEBAS – Modular AI Assistant Framework
Package initializer for the SEBAS ecosystem.

This file exposes only stable, public-facing entry points.
Internal modules remain encapsulated in their subpackages.
"""

# Public API surface
__all__ = [
    "Sebas",
    "create_api_server",
    "start_ui_server",
    "EventBus",
]

# --- Core ---
from .main import Sebas

# --- UI & API Servers ---
from .api.api_server import create_api_server
from .api.ui_server import start_ui_server

# --- Events ---
from .events.event_bus import EventBus