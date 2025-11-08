# -*- coding: utf-8 -*-
"""
SEBAS API Server
Phase 1.3: Comprehensive REST API Framework
"""

import logging
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from flask import Flask, jsonify, request, g

# Optional CORS support
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False
    logging.warning("flask_cors not available. CORS will be disabled.")

from auth import require_auth, require_role, init_auth_manager, get_auth_manager as authmngr
from rate_limit import rate_limit, init_rate_limiter, get_rate_limiter
from webhooks import WebhookEvent, init_webhook_manager
from versioning import get_api_version
from websocket import WebSocketEvent, init_websocket_manager, get_websocket_manager as websock
from constants.permissions import Role


class APIServer:
    """Main API server for SEBAS."""
    def __init__(self, sebas_instance=None, host: str = "127.0.0.1", port: int = 5001):
        self.sebas = sebas_instance
        self.host = host
        self.port = port

        # Initialize Flask app
        self.app = Flask(__name__)
        if CORS_AVAILABLE:
            CORS(self.app)

        # Initialize components
        init_auth_manager()
        init_rate_limiter(default_rate=100, default_window=60)
        init_webhook_manager()
        init_websocket_manager(flask_app=self.app)

        # Register routes
        self._register_routes()

        # Swagger documentation (optional)
        try:
            from .swagger import register_swagger_routes
            register_swagger_routes(self.app)
        except ImportError:
            logging.warning("Swagger documentation not available")

        self.server_thread: Optional[threading.Thread] = None
        self.running = False

    def _register_routes(self):
        """Register minimal API routes."""
        @self.app.route("/api/v1/health", methods=["GET"])
        def health():
            return jsonify({
                "status": "ok",
                "service": "sebas-api",
                "version": "1.0"
            })

        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                "error": "Not found",
                "message": "The requested endpoint does not exist"
            }), 404

    def start(self):
        """Start the API server in a background thread."""
        if self.running:
            logging.warning("API server already running")
            return

        self.running = True

        def _run():
            try:
                logging.info(f"Starting SEBAS API server on {self.host}:{self.port}")
                ws_mgr = websock()
                socketio_instance = getattr(ws_mgr, "socketio", None)
                if socketio_instance is not None:
                    logging.info("Using WebSocket-enabled server")
                    socketio_instance.run(  # type: ignore[attr-defined]
                        self.app, host=self.host, port=self.port, debug=False, use_reloader=False
                    )
                else:
                    logging.info("Using standard Flask server")
                    self.app.run(
                        host=self.host, port=self.port, debug=False, use_reloader=False, threaded=True
                    )
            except Exception as e:
                logging.exception(f"API server error: {e}")
            finally:
                self.running = False
                logging.info("API server stopped")

        self.server_thread = threading.Thread(target=_run, daemon=True, name="APIServer")
        self.server_thread.start()

        import time
        time.sleep(0.5)
        if self.server_thread.is_alive():
            logging.info(f"SEBAS API server started on http://{self.host}:{self.port}")
        else:
            logging.error("Failed to start API server thread")


def create_api_server(sebas_instance=None, host: str = "127.0.0.1", port: int = 5001) -> APIServer:
    """Factory function to create and configure an API server."""
    return APIServer(sebas_instance=sebas_instance, host=host, port=port)
