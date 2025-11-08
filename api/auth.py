# -*- coding: utf-8 -*-
"""
Authentication and Authorization Framework
"""

import os
import secrets
import time
import logging
from typing import Optional, Dict, Callable
from functools import wraps
from flask import request, jsonify, g

# Optional JWT support
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logging.warning("PyJWT not available. JWT authentication will be disabled.")

from constants.permissions import Role

class AuthManager:
    """
    Manages authentication and authorization for the API.
    Supports API keys, JWT tokens, and role-based access control.
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize AuthManager.
        
        Args:
            secret_key: Secret key for JWT signing (defaults to random)
        """
        self.secret_key = secret_key or os.environ.get('SEBAS_SECRET_KEY') or secrets.token_urlsafe(32)
        self.api_keys: Dict[str, Dict] = {}  # key -> {role, created_at, expires_at}
        self.jwt_algorithm = 'HS256'
        self.jwt_expiration = 3600  # 1 hour
        
        # Load API keys from environment or file
        self._load_api_keys()
    
    def _load_api_keys(self):
        """Load API keys from environment variables."""
        # Format: SEBAS_API_KEY_<name>=<key>:<role>
        for key, value in os.environ.items():
            if key.startswith('SEBAS_API_KEY_'):
                parts = value.split(':', 1)
                if len(parts) == 2:
                    api_key, role_name = parts
                    try:
                        role = Role[role_name.upper()]
                        self.api_keys[api_key] = {
                            'role': role,
                            'created_at': time.time(),
                            'expires_at': None  # No expiration by default
                        }
                        logging.info(f"Loaded API key: {key} with role {role_name}")
                    except KeyError:
                        logging.warning(f"Invalid role {role_name} for API key {key}")
    
    def generate_api_key(self, role: Role = Role.STANDARD, expires_in: Optional[int] = None) -> str:
        """
        Generate a new API key.
        
        Args:
            role: Role assigned to the API key
            expires_in: Expiration time in seconds (None for no expiration)
            
        Returns:
            Generated API key string
        """
        api_key = secrets.token_urlsafe(32)
        self.api_keys[api_key] = {
            'role': role,
            'created_at': time.time(),
            'expires_at': time.time() + expires_in if expires_in else None
        }
        logging.info(f"Generated new API key with role {role.name}")
        return api_key
    
    def revoke_api_key(self, api_key: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            api_key: API key to revoke
            
        Returns:
            True if key was revoked, False if not found
        """
        if api_key in self.api_keys:
            del self.api_keys[api_key]
            logging.info("API key revoked")
            return True
        return False
    
    def validate_api_key(self, api_key: str) -> Optional[Dict]:
        """
        Validate an API key.
        
        Args:
            api_key: API key to validate
            
        Returns:
            Dict with role info if valid, None otherwise
        """
        if api_key not in self.api_keys:
            return None
        
        key_info = self.api_keys[api_key]
        
        # Check expiration
        if key_info.get('expires_at') and time.time() > key_info['expires_at']:
            del self.api_keys[api_key]
            return None
        
        return key_info
    
    def generate_jwt(self, user_id: str, role: Role, expires_in: Optional[int] = None) -> str:
        """
        Generate a JWT token.
        
        Args:
            user_id: User identifier
            role: User role
            expires_in: Expiration time in seconds (defaults to 1 hour)
            
        Returns:
            JWT token string
        """
        if not JWT_AVAILABLE:
            raise RuntimeError("JWT support not available. Install PyJWT: pip install PyJWT")
        
        exp = int(time.time()) + (expires_in or self.jwt_expiration)
        payload = {
            'user_id': user_id,
            'role': role.name,
            'exp': exp,
            'iat': int(time.time())
        }
        return jwt. encode(payload, self.secret_key, algorithm=self.jwt_algorithm)
    
    def validate_jwt(self, token: str) -> Optional[Dict]:
        """
        Validate a JWT token.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Dict with user info if valid, None otherwise
        """
        if not JWT_AVAILABLE:
            return None
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.jwt_algorithm])
            return {
                'user_id': payload.get('user_id'),
                'role': Role[payload.get('role', 'STANDARD')]
            }
        except jwt.ExpiredSignatureError:
            logging.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError:
            logging.warning("Invalid JWT token")
            return None
    
    def authenticate_request(self) -> Optional[Dict]:
        """
        Authenticate the current request.
        Checks for API key or JWT token.
        
        Returns:
            Dict with user info if authenticated, None otherwise
        """
        # Check for API key in header
        api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
        if api_key:
            key_info = self.validate_api_key(api_key)
            if key_info:
                return {
                    'type': 'api_key',
                    'role': key_info['role']
                }
            
            # Try as JWT token
            jwt_info = self.validate_jwt(api_key)
            if jwt_info:
                return {
                    'type': 'jwt',
                    'user_id': jwt_info['user_id'],
                    'role': jwt_info['role']
                }
        
        # Check for JWT in Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            jwt_info = self.validate_jwt(token)
            if jwt_info:
                return {
                    'type': 'jwt',
                    'user_id': jwt_info['user_id'],
                    'role': jwt_info['role']
                }
        
        return None


# Global auth manager instance
_auth_manager: Optional[AuthManager] = None


def init_auth_manager(secret_key: Optional[str] = None):
    """Initialize the global auth manager."""
    global _auth_manager
    _auth_manager = AuthManager(secret_key)


def get_auth_manager() -> AuthManager:
    """Get the global auth manager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


def require_auth(f: Optional[Callable] = None, optional: bool = False):
    """
    Decorator to require authentication for an endpoint.
    
    Args:
        f: Function to decorate
        optional: If True, authentication is optional but user info is still set
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            auth_manager = get_auth_manager()
            auth_info = auth_manager.authenticate_request()
            
            if not auth_info:
                if optional:
                    g.current_user = None
                    g.current_role = Role.STANDARD
                else:
                    return jsonify({
                        'error': 'Authentication required',
                        'message': 'Please provide a valid API key or JWT token'
                    }), 401
            else:
                g.current_user = auth_info
                g.current_role = auth_info.get('role', Role.STANDARD)
            
            return func(*args, **kwargs)
        return wrapper
    
    if f is None:
        return decorator
    return decorator(f)


def require_role(required_role: Role):
    """
    Decorator to require a specific role for an endpoint.
    
    Args:
        required_role: Minimum role required
    """
    def decorator(func):
        @wraps(func)
        @require_auth
        def wrapper(*args, **kwargs):
            current_role = getattr(g, 'current_role', Role.STANDARD)
            
            if current_role.value < required_role.value:
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'This endpoint requires {required_role.name} role or higher'
                }), 403
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
