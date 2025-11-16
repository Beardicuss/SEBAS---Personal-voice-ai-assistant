"""SEBAS Flask module - wraps Flask imports"""
try:
    from flask import (
        Flask, 
        jsonify, 
        request, 
        Response,
        Blueprint,
        g,
        make_response,
        send_from_directory,
        abort,
        redirect,
        url_for,
        render_template,
        session,
    )
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    # Create dummy objects if Flask not installed
    Flask = None
    jsonify = None
    request = None
    Response = None
    Blueprint = None
    g = None

if FLASK_AVAILABLE:
    __all__ = [
        'Flask', 'jsonify', 'request', 'Response', 
        'Blueprint', 'g', 'make_response', 'send_from_directory',
        'abort', 'redirect', 'url_for', 'render_template', 'session'
    ]
else:
    __all__ = []