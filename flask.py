"""
Compatibility shim - redirects to Flask
"""
try:
    from flask import *
except ImportError:
    pass  # Flask not installed
