# -*- coding: utf-8 -*-
"""
SEBAS API Server
Phase 1.4: Functional Intent Execution
"""

import logging
import threading
from datetime import datetime
from typing import Optional
import subprocess
import os

from flask import Flask, jsonify, request
from sebas.constants.permissions import Role

# Optional CORS support
try:
    from flask_cors import CORS  # type: ignore
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False
    logging.warning("flask_cors not available. CORS will be disabled.")

# Relative imports inside sebas/api
from .auth import (
    require_auth,
    require_role,
    init_auth_manager,
    get_auth_manager as authmngr,
)
from .rate_limit import rate_limit, init_rate_limiter, get_rate_limiter
from .webhooks import WebhookEvent, init_webhook_manager
from .versioning import get_api_version
from .websocket import (
    WebSocketEvent,
    init_websocket_manager,
    get_websocket_manager as websock,
)
from sebas.services.nlu import SimpleNLU


class APIServer:
    """Main API server for SEBAS."""

    def __init__(self, sebas_instance=None, host: str = "127.0.0.1", port: int = 5001):
        self.sebas = sebas_instance
        self.host = host
        self.port = port
        self.nlu = SimpleNLU()

        self.app = Flask(__name__)
        if CORS_AVAILABLE:
            CORS(self.app)

        init_auth_manager()
        init_rate_limiter(default_rate=100, default_window=60)
        init_webhook_manager()
        init_websocket_manager(flask_app=self.app)

        self._register_routes()

        try:
            from .swagger import register_swagger_routes
            register_swagger_routes(self.app)
        except ImportError:
            logging.warning("Swagger documentation not available")

        self.server_thread: Optional[threading.Thread] = None
        self.running = False

    # =====================================================
    # === ROUTE REGISTRATION ==============================
    # =====================================================
    def _register_routes(self):
        """Register all API routes."""

        @self.app.route("/", methods=["GET"])
        def root_index():
            return jsonify({
                "status": "online",
                "service": "sebas-api",
                "message": "Use /api/parse to send commands."
            })

        @self.app.route("/api/v1/health", methods=["GET"])
        def health():
            return jsonify({
                "status": "ok",
                "service": "sebas-api",
                "version": get_api_version(),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })

        @self.app.route("/api/v1/version", methods=["GET"])
        def version():
            return jsonify({
                "api_version": get_api_version(),
                "role_system": [role.name for role in Role],
                "webhooks": True,
                "websocket": True,
            })

        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                "error": "Not found",
                "message": "The requested endpoint does not exist"
            }), 404

        @self.app.route("/api/parse", methods=["POST", "OPTIONS"])
        def parse_command():
            """Parse and execute basic natural language commands."""
            if request.method == "OPTIONS":
                return jsonify({"ok": True}), 200

            try:
                data = request.get_json(silent=True) or {}
                text = str(data.get("text", "")).strip()

                if not text:
                    return jsonify({"error": "Empty command"}), 400

                intent = self.nlu.parse(text)
                if not intent:
                    return jsonify({
                        "response": f"No intent detected for: {text}",
                        "slots": {},
                        "confidence": 0.0,
                    }), 200

                intent_name = intent.name.lower()
                response_message = None

                # === Simple Action Layer ===
                if "notepad" in text.lower():
                    subprocess.Popen("notepad.exe")
                    response_message = "Opened Notepad"
                elif "calculator" in text.lower():
                    subprocess.Popen("calc.exe")
                    response_message = "Opened Calculator"
                elif "browser" in text.lower() or "chrome" in text.lower():
                    subprocess.Popen("start chrome", shell=True)
                    response_message = "Opened Browser"
                elif "command prompt" in text.lower() or "cmd" in text.lower():
                    subprocess.Popen("cmd.exe")
                    response_message = "Opened Command Prompt"
                else:
                    response_message = f"Intent: {intent_name} (no linked action)"

                return jsonify({
                    "response": response_message,
                    "slots": intent.slots,
                    "confidence": intent.confidence,
                }), 200

            except Exception as e:
                logging.exception("Error in /api/parse")
                return jsonify({"error": str(e)}), 500

    # =====================================================
    # === SERVER STARTUP LOGIC ============================
    # =====================================================
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
                    logging.info("Running with WebSocket-enabled server")
                    socketio_instance.run(  # type: ignore[attr-defined]
                        self.app,
                        host=self.host,
                        port=self.port,
                        debug=False,
                        use_reloader=False,
                    )
                else:
                    logging.info("Running standard Flask server")
                    self.app.run(
                        host=self.host,
                        port=self.port,
                        debug=False,
                        use_reloader=False,
                        threaded=True,
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
            logging.info(f"SEBAS API server started at http://{self.host}:{self.port}")
        else:
            logging.error("Failed to start API server thread")


# =====================================================
# === FACTORY FUNCTION ================================
# =====================================================
def create_api_server(sebas_instance=None, host: str = "127.0.0.1", port: int = 5001) -> APIServer:
    return APIServer(sebas_instance=sebas_instance, host=host, port=port)


if __name__ == "__main__":
    import time

    logging.basicConfig(level=logging.DEBUG)
    logging.debug(">>> Starting manual launch of SEBAS API Server...")

    server = create_api_server()
    logging.debug(">>> Server object created. Attempting to start()...")
    server.start()
    logging.debug(">>> server.start() called. Waiting to see if it stays alive...")

    time.sleep(2)
    logging.debug(f">>> Server running flag = {server.running}")
    logging.debug(">>> End of main thread; entering idle loop...")

    while True:
        time.sleep(1)
