def require_auth(func):
    return func

def require_role(role):
    def wrapper(func):
        return func
    return wrapper

def init_auth_manager(*args, **kwargs):
    return None

def get_auth_manager():
    return None
