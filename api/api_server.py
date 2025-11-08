"""
SEBAS API Server
Phase 1.3: Comprehensive REST API Framework
"""

import os
import logging
import threading
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from flask import Flask, Blueprint, jsonify, request, g

# Optional CORS support
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False
    logging.warning("flask_cors not available. CORS will be disabled.")

from .auth import AuthManager, require_auth, require_role, init_auth_manager, get_auth_manager
from .rate_limit import RateLimiter, rate_limit, init_rate_limiter, get_rate_limiter
from .webhooks import WebhookManager, WebhookEvent, init_webhook_manager
from .versioning import APIVersion, get_api_version
from .websocket import WebSocketManager, WebSocketEvent, init_websocket_manager, get_websocket_manager
from constants.permissions import Role


class APIServer:
    """
    Main API server for SEBAS.
    Provides REST API with versioning, authentication, rate limiting, and webhooks.
    """
    
    def __init__(self, sebas_instance=None, host: str = "127.0.0.1", port: int = 5001):
        """
        Initialize API server.
        
        Args:
            sebas_instance: Sebas assistant instance
            host: Host to bind to
            port: Port to bind to
        """
        self.sebas = sebas_instance
        self.host = host
        self.port = port
        
        # Initialize Flask app
        self.app = Flask(__name__)
        if CORS_AVAILABLE:
            CORS(self.app)  # Enable CORS for API access
        
        # Initialize components
        init_auth_manager()
        init_rate_limiter(default_rate=100, default_window=60)
        init_webhook_manager()
        init_websocket_manager(flask_app=self.app)
        
        # Register blueprints
        self._register_routes()
        
        # Register Swagger documentation (Phase 1.3.6)
        try:
            from .swagger import register_swagger_routes
            register_swagger_routes(self.app)
        except ImportError:
            logging.warning("Swagger documentation not available")
        
        # Server thread
        self.server_thread: Optional[threading.Thread] = None
        self.running = False
    
    def _register_routes(self):
        """Register API routes."""
        
        # Health check endpoint (no auth required)
        @self.app.route('/api/v1/health', methods=['GET'])
        def health():
            """Health check endpoint."""
            return jsonify({
                'status': 'ok',
                'service': 'sebas-api',
                'version': '1.0'
            })
        
        # Status endpoint (versioned)
        @self.app.route('/api/v1/status', methods=['GET'])
        @self.app.route('/api/v2/status', methods=['GET'])
        @rate_limit(rate=60, window=60)
        @require_auth(optional=True)
        def api_status():
            """Get system status."""
            version = get_api_version()
            status = {
                'version': version.value,
                'status': 'operational' if self.sebas else 'initializing'
            }
            
            # Add user info if authenticated
            if hasattr(g, 'current_user'):
                status['authenticated'] = True
                status['role'] = g.current_role.name
            else:
                status['authenticated'] = False
            
            return jsonify(status)
        
        # Command execution endpoint
        @self.app.route('/api/v1/commands', methods=['POST'])
        @self.app.route('/api/v2/commands', methods=['POST'])
        @rate_limit(rate=30, window=60)
        @require_auth
        def execute_command():
            """Execute a command."""
            data = request.get_json(silent=True) or {}
            command = data.get('command', '').strip()
            
            if not command:
                return jsonify({
                    'error': 'Missing command',
                    'message': 'Command parameter is required'
                }), 400
            
            if not self.sebas:
                return jsonify({
                    'error': 'Service unavailable',
                    'message': 'Sebas instance not initialized'
                }), 503
            
            try:
                # Execute command
                self.sebas.parse_and_execute(command)
                
                # Trigger webhook
                webhook_mgr = init_webhook_manager()
                webhook_mgr.trigger_event(WebhookEvent.COMMAND_EXECUTED, {
                    'command': command,
                    'user': getattr(g, 'current_user', {}).get('user_id', 'unknown')
                })
                
                # Emit WebSocket event (Phase 1.3.5)
                ws_mgr = get_websocket_manager()
                if ws_mgr:
                    ws_mgr.emit_event(WebSocketEvent.COMMAND_RESULT, {
                        'command': command,
                        'status': 'success',
                        'user': getattr(g, 'current_user', {}).get('user_id', 'unknown')
                    })
                
                return jsonify({
                    'status': 'success',
                    'message': 'Command executed',
                    'command': command
                })
            except Exception as e:
                logging.exception(f"Command execution failed: {command}")
                
                # Trigger error webhook
                webhook_mgr = init_webhook_manager()
                webhook_mgr.trigger_event(WebhookEvent.COMMAND_FAILED, {
                    'command': command,
                    'error': str(e)
                })
                
                return jsonify({
                    'status': 'error',
                    'message': 'Command execution failed',
                    'error': str(e)
                }), 500
        
        # System information endpoint
        @self.app.route('/api/v1/system', methods=['GET'])
        @rate_limit(rate=30, window=60)
        @require_auth
        def system_info():
            """Get system information."""
            if not self.sebas:
                return jsonify({'error': 'Service unavailable'}), 503
            
            try:
                import psutil
                import platform
                
                info = {
                    'platform': platform.system(),
                    'platform_version': platform.version(),
                    'cpu_count': psutil.cpu_count(),
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'memory': {
                        'total': psutil.virtual_memory().total,
                        'available': psutil.virtual_memory().available,
                        'percent': psutil.virtual_memory().percent
                    }
                }
                
                return jsonify(info)
            except Exception as e:
                logging.exception("Failed to get system info")
                return jsonify({'error': str(e)}), 500
        
        # User information endpoint
        @self.app.route('/api/v1/user', methods=['GET'])
        @rate_limit(rate=30, window=60)
        @require_auth
        def user_info():
            """Get current user information."""
            if not hasattr(g, 'current_user'):
                return jsonify({'error': 'Not authenticated'}), 401
            
            user_info = {
                'authenticated': True,
                'role': g.current_role.name
            }
            
            # Add AD user info if available
            if self.sebas and hasattr(self.sebas, 'get_ad_user_info'):
                ad_info = self.sebas.get_ad_user_info()
                if ad_info:
                    user_info['ad'] = ad_info
            
            return jsonify(user_info)
        
        # Webhook management endpoints (admin only)
        @self.app.route('/api/v1/webhooks', methods=['GET'])
        @rate_limit(rate=20, window=60)
        @require_auth
        @require_role(Role.ADMIN)
        def list_webhooks():
            """List registered webhooks."""
            webhook_mgr = init_webhook_manager()
            webhooks = {}
            for webhook_id, webhook in webhook_mgr.webhooks.items():
                webhooks[webhook_id] = {
                    'url': webhook.url,
                    'events': [e.value for e in webhook.events],
                    'enabled': webhook.enabled
                }
            return jsonify({'webhooks': webhooks})
        
        @self.app.route('/api/v1/webhooks', methods=['POST'])
        @rate_limit(rate=10, window=60)
        @require_auth
        @require_role(Role.ADMIN)
        def register_webhook():
            """Register a new webhook."""
            data = request.get_json(silent=True) or {}
            
            url = data.get('url', '').strip()
            events = data.get('events', [])
            secret = data.get('secret')
            enabled = data.get('enabled', True)
            
            if not url or not events:
                return jsonify({
                    'error': 'Missing required fields',
                    'message': 'url and events are required'
                }), 400
            
            try:
                event_enums = [WebhookEvent(e) for e in events]
            except ValueError as e:
                return jsonify({
                    'error': 'Invalid event',
                    'message': str(e)
                }), 400
            
            webhook_mgr = init_webhook_manager()
            webhook_id = f"webhook_{len(webhook_mgr.webhooks) + 1}"
            
            from .webhooks import Webhook
            webhook = Webhook(
                url=url,
                events=event_enums,
                secret=secret,
                enabled=enabled
            )
            
            webhook_mgr.register_webhook(webhook_id, webhook)
            
            return jsonify({
                'status': 'success',
                'webhook_id': webhook_id,
                'message': 'Webhook registered'
            }), 201
        
        # API key management (admin only)
        @self.app.route('/api/v1/auth/keys', methods=['POST'])
        @rate_limit(rate=10, window=60)
        @require_auth
        @require_role(Role.ADMIN)
        def create_api_key():
            """Create a new API key."""
            data = request.get_json(silent=True) or {}
            role_name = data.get('role', 'STANDARD').upper()
            
            try:
                role = Role[role_name]
            except KeyError:
                return jsonify({
                    'error': 'Invalid role',
                    'message': f'Role must be one of: {[r.name for r in Role]}'
                }), 400
            
            auth_mgr = init_auth_manager()
            api_key = auth_mgr.generate_api_key(role=role)
            
            return jsonify({
                'status': 'success',
                'api_key': api_key,
                'role': role.name,
                'message': 'API key created. Store it securely.'
            }), 201
        
        # JWT token generation
        @self.app.route('/api/v1/auth/token', methods=['POST'])
        @rate_limit(rate=10, window=60)
        @require_auth
        def create_token():
            """Generate a JWT token."""
            auth_mgr = init_auth_manager()
            user_id = getattr(g, 'current_user', {}).get('user_id', 'api_user')
            role = g.current_role
            
            token = auth_mgr.generate_jwt(user_id=user_id, role=role)
            
            return jsonify({
                'status': 'success',
                'token': token,
                'type': 'Bearer',
                'expires_in': auth_mgr.jwt_expiration
            })
        
        # Error handlers (Phase 1.6)
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                'error': 'Not found',
                'message': 'The requested endpoint does not exist'
            }), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            logging.exception("Internal server error")
            
            # Use error handling framework if available
            if ERROR_HANDLING_AVAILABLE:
                error_info = handle_error(error, {'endpoint': request.path})
                return jsonify({
                    'error': 'Internal server error',
                    'message': 'An unexpected error occurred',
                    'details': error_info
                }), 500
            
            return jsonify({
                'error': 'Internal server error',
                'message': 'An unexpected error occurred'
            }), 500
        
        # Health check endpoint with error handling
        @self.app.route('/api/v1/health/detailed', methods=['GET'])
        def detailed_health():
            """Detailed health check with component status."""
            health = {
                'status': 'ok',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'components': {}
            }
            
            # Check components
            health['components']['api'] = 'ok'
            health['components']['auth'] = 'ok' if get_auth_manager() else 'unavailable'
            health['components']['rate_limit'] = 'ok' if get_rate_limiter() else 'unavailable'
            
            # Check error handler if available
            if ERROR_HANDLING_AVAILABLE:
                error_handler = get_error_handler()
                health['components']['error_handler'] = 'ok'
                health['error_stats'] = error_handler.get_error_stats()
            else:
                health['components']['error_handler'] = 'unavailable'
            
            # Determine overall status
            if any(status != 'ok' for status in health['components'].values()):
                health['status'] = 'degraded'
            
            return jsonify(health)
    
    def start(self):
        """Start the API server in a background thread."""
        if self.running:
            logging.warning("API server already running")
            return
        
        self.running = True
        def _run():
            try:
                logging.info(f"Starting SEBAS API server on {self.host}:{self.port}")
                # Try to use SocketIO if WebSocket support is available
                ws_mgr = get_websocket_manager()
                if ws_mgr and ws_mgr.socketio:
                    logging.info("Using WebSocket-enabled server")
                    ws_mgr.run(self.app, host=self.host, port=self.port, debug=False)
                else:
                    logging.info("Using standard Flask server")
                    self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False, threaded=True)
            except Exception as e:
                logging.exception(f"API server error: {e}")
                self.running = False
            finally:
                self.running = False
                logging.info("API server stopped")
        
        self.server_thread = threading.Thread(target=_run, daemon=True, name="APIServer")
        self.server_thread.start()
        
        # Wait a moment to ensure server starts
        import time
        time.sleep(0.5)
        
        if self.server_thread.is_alive():
            logging.info(f"SEBAS API server started on http://{self.host}:{self.port}")
        else:
            logging.error("Failed to start API server thread")
    
    def stop(self):
        """Stop the API server."""
        self.running = False
        # Note: Flask doesn't have a clean shutdown, so we just mark it as stopped
        logging.info("SEBAS API server stopped")


def create_api_server(sebas_instance=None, host: str = "127.0.0.1", port: int = 5001) -> APIServer:
    """
    Factory function to create and configure an API server.
    
    Args:
        sebas_instance: Sebas assistant instance
        host: Host to bind to
        port: Port to bind to
        
    Returns:
        Configured APIServer instance
    """
    return APIServer(sebas_instance=sebas_instance, host=host, port=port)
