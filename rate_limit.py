from sebas.functools import wraps
import time

def rate_limit(limit=None, per_seconds=None):
    def decorator(func):
        return func
    return decorator

def init_rate_limiter(*args, **kwargs):
    return None

def get_rate_limiter():
    return None