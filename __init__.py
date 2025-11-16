"""
SEBAS – Stage 1 Mk.I Package
Modular AI Assistant Framework
"""

__version__ = "1.0.0-stage1"
__author__ = "Dante"

# Public API - import only what's needed and safe
__all__ = [
    "EventBus",
]

# Minimal imports - avoid circular dependencies
try:
    from .events.event_bus import EventBus
except ImportError:
    EventBus = None

# Don't import main.py here - it causes circular dependencies
# Users should run via run.py or import directly:
# from sebas.main import Sebas, main

# ============================================================
# FIX: Remove problematic sebas.* imports that might exist
# ============================================================

# DO NOT import these (they don't exist):
# - sebas.voice_typing (phantom module)
# - sebas.xyz (any non-existent modules)

# If you see "No module named 'voice_typing'" error,
# it means one of your skills is trying to import it.
# Search for "from sebas." or "import sebas." in all skills.
