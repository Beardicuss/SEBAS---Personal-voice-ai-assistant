# -*- coding: utf-8 -*-
"""
SEBAS package initializer (safe, lazy import version)
"""

__all__ = [
    "APIServer",
    "create_api_server",
    "AuthManager",
    "require_auth",
    "require_role",
    "RateLimiter",
    "WebhookEvent",
    "get_api_version",
]

def __getattr__(name):
    """Lazy import to prevent circular dependencies."""
    if name in ("APIServer", "create_api_server"):
        from .api.api_server import APIServer, create_api_server
        return locals()[name]
    if name in ("AuthManager", "require_auth", "require_role"):
        from .api.auth import AuthManager, require_auth, require_role
        return locals()[name]
    if name == "RateLimiter":
        from .api.rate_limit import RateLimiter
        return RateLimiter
    if name == "WebhookEvent":
        from .api.webhooks import WebhookEvent
        return WebhookEvent
    if name == "get_api_version":
        from .api.versioning import get_api_version
        return get_api_version
    raise AttributeError(f"module {__name__} has no attribute {name}")
