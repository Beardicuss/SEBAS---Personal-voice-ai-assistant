"""
SEBAS API Framework
Phase 1.3: Comprehensive REST API with versioning, authentication, and integrations
"""

from api_server import APIServer, create_api_server
from auth import AuthManager, require_auth, require_role
from rate_limit import RateLimiter
from webhooks import WebhookManager
from versioning import APIVersion

__all__ = [
    'APIServer',
    'create_api_server',
    'AuthManager',
    'require_auth',
    'require_role',
    'RateLimiter',
    'WebhookManager',
    'APIVersion'
]
