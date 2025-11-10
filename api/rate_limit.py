# -*- coding: utf-8 -*-
"""
Rate Limiting Framework
"""

import time
import logging
from typing import Dict, Tuple, Optional
from collections import defaultdict
from functools import wraps
from flask import request, jsonify, g


class RateLimiter:
    """
    Rate limiter using token bucket algorithm.
    Supports per-IP and per-API-key limiting.
    """
    
    def __init__(self, default_rate: int = 100, default_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            default_rate: Default requests per window
            default_window: Default time window in seconds
        """
        self.default_rate = default_rate
        self.default_window = default_window
        
        # Store request counts: {identifier: [(timestamp, count), ...]}
        self.requests: Dict[str, list] = defaultdict(list)
        
        # Custom limits per identifier: {identifier: (rate, window)}
        self.custom_limits: Dict[str, Tuple[int, int]] = {}
    
    def set_limit(self, identifier: str, rate: int, window: int):
        """
        Set custom rate limit for an identifier.
        
        Args:
            identifier: IP address or API key
            rate: Requests per window
            window: Time window in seconds
        """
        self.custom_limits[identifier] = (rate, window)
        logging.info(f"Set rate limit for {identifier}: {rate} requests per {window} seconds")
    
    def _get_identifier(self) -> str:
        """Get identifier for current request (IP or API key)."""
        # Try to get API key first
        api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
        if api_key:
            return f"api_key:{api_key[:16]}"  # Use first 16 chars for privacy
        
        # Fall back to IP address
        return f"ip:{request.remote_addr or 'unknown'}"
    
    def _cleanup_old_requests(self, identifier: str, window: int):
        """Remove requests outside the time window."""
        current_time = time.time()
        cutoff = current_time - window
        
        self.requests[identifier] = [
            (ts, count) for ts, count in self.requests[identifier]
            if ts > cutoff
        ]
    
    def check_rate_limit(self, identifier: Optional[str] = None) -> Tuple[bool, Dict[str, int]]:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: Optional identifier (defaults to current request identifier)
            
        Returns:
            Tuple of (allowed, info_dict)
            info_dict contains: remaining, reset_time, limit
        """
        if identifier is None:
            identifier = self._get_identifier()
        
        # Get limits for this identifier
        rate, window = self.custom_limits.get(identifier, (self.default_rate, self.default_window))
        
        current_time = time.time()
        
        # Clean up old requests
        self._cleanup_old_requests(identifier, window)
        
        # Count requests in current window
        request_count = sum(count for _, count in self.requests[identifier])
        
        # Check if limit exceeded
        if request_count >= rate:
            reset_time = int(self.requests[identifier][0][0] + window) if self.requests[identifier] else int(current_time + window)
            return False, {
                'remaining': 0,
                'reset_time': reset_time,
                'limit': rate
            }
        
        # Add current request
        self.requests[identifier].append((current_time, 1))
        
        remaining = rate - request_count - 1
        reset_time = int(current_time + window)
        
        return True, {
            'remaining': remaining,
            'reset_time': reset_time,
            'limit': rate
        }
    
    def is_allowed(self, identifier: Optional[str] = None) -> bool:
        """Check if request is allowed (simplified version)."""
        allowed, _ = self.check_rate_limit(identifier)
        return allowed


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def init_rate_limiter(default_rate: int = 100, default_window: int = 60):
    """Initialize the global rate limiter."""
    global _rate_limiter
    _rate_limiter = RateLimiter(default_rate, default_window)


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def rate_limit(rate: int = 100, window: int = 60, per: str = 'ip'):
    """
    Decorator to rate limit an endpoint.
    
    Args:
        rate: Requests per window
        window: Time window in seconds
        per: 'ip' or 'key' (per IP or per API key)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter = get_rate_limiter()
            
            identifier = None
            if per == 'key':
                api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
                if api_key:
                    identifier = f"api_key:{api_key[:16]}"
            
            allowed, info = limiter.check_rate_limit(identifier)
            
            # Add rate limit headers
            response = func(*args, **kwargs)
            
            # Set rate limit headers (works for both regular responses and jsonify)
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(info['limit'])
                response.headers['X-RateLimit-Remaining'] = str(info['remaining'])
                response.headers['X-RateLimit-Reset'] = str(info['reset_time'])
            
            if not allowed:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Limit: {rate} per {window} seconds',
                    'reset_time': info['reset_time']
                }), 429
            
            return response
        return wrapper
    return decorator