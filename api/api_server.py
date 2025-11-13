# -*- coding: utf-8 -*-
"""
SEBAS API Server (clean modular version)
Does NOT depend on main.py or Sebas class directly.
Can work with any dispatcher + NLU object.
"""

import logging
import threading
from sebas.datetime import datetime
from sebas.typing import Optional

import subprocess
from sebas.flask import Flask, jsonify, request

# Optional CORS support
try:
    from sebas.flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False

# API infrastructure
from sebas.api.auth import init_auth_manager
from sebas.api.rate_limit import init_rate_limiter
from sebas.api.webhooks import init_webhook_manager
from sebas.api.versioning import get_api_version
from sebas.api.websocket import init_websocket_manager, get_websocket_manager


class APIServer:
    """
    Clean API Server.
    Works with injected "nlu" and "dispatcher".
    Does NOT launch wake-word, does NOT own Sebas.
    """

    def __init__(
        self,
        dispatcher=None,
        nlu=None,
        host: str = "127.0.0.1",
        port: int = 5002
    ):
        self.host = host
        self.port = port
        self.dispatcher = dispatcher
        self.nlu = nlu

        self.app = Flask(__name__)

        if CORS_AVAILABLE:
            CORS(self.app)

        # initialize API submodules
        init_auth_manager()
        init_rate_limiter(default_rate=100, default_window=60)
        init_webhook_manager()
        init_websocket_manager(flask_app=self.app)

        self._register_routes()
        self.server_thread: Optional[threading.Thread] = None
        self.running = False

    # --------------------------------------------------
    # ROUTES
    # --------------------------------------------------
    def _register_routes(self):

        @self.app.route("/", methods=["GET"])
        def root_index():
            return jsonify({
                "status": "online",
                "service": "sebas-api",
                "message": "Use /api/v1/parse to send commands."
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
                "webhooks": True,
                "websocket": True,
            })

        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                "error": "Not found",
                "message": "The requested endpoint does not exist"
            }), 404

        @self.app.route("/api/v1/parse", methods=["POST"])
        def parse_command():
            """
            Entry point: parse natural language command.
            """
            try:
                data = request.get_json(silent=True) or {}
                text = str(data.get("text", "")).strip()

                if not text:
                    return jsonify({"error": "Empty command"}), 400

                # Step 1. NLU
                intent = None
                if self.nlu:
                    intent = self.nlu.parse(text)

                if intent:
                    intent_name = intent.name
                    slots = intent.slots
                    confidence = getattr(intent, "confidence", 1.0)
                else:
                    intent_name = None
                    slots = {}
                    confidence = 0.0

                # Step 2. Dispatcher (if provided)
                if self.dispatcher:
                    try:
                        result = self.dispatcher.handle(text, intent, slots)
                        return jsonify({
                            "result": result,
                            "intent": intent_name,
                            "slots": slots,
                            "confidence": confidence
                        })
                    except Exception as e:
                        logging.exception("Dispatcher error")
                        return jsonify({
                            "error": str(e),
                            "intent": intent_name,
                            "slots": slots
                        }), 500

                # Step 3. Fallback simple actions
                if "notepad" in text.lower():
                    subprocess.Popen("notepad.exe")
                    return jsonify({"response": "Opened Notepad"})

                if "calculator" in text.lower():
                    subprocess.Popen("calc.exe")
                    return jsonify({"response": "Opened Calculator"})

                return jsonify({
                    "response": "No dispatcher and no fallback action.",
                    "intent": intent_name,
                    "slots": slots,
                    "confidence": confidence,
                })

            except Exception as e:
                logging.exception("Error in /api/v1/parse")
                return jsonify({"error": str(e)}), 500

    # --------------------------------------------------
    # START SERVER
    # --------------------------------------------------
    def start(self):
        if self.running:
            logging.warning("API server already running")
            return

        self.running = True

        def _run():
            try:
                ws_mgr = get_websocket_manager()
                socketio_instance = getattr(ws_mgr, "socketio", None)

                if socketio_instance:
                    socketio_instance.run(
                        self.app,
                        host=self.host,
                        port=self.port,
                        debug=False,
                        use_reloader=False
                    )
                else:
                    self.app.run(
                        host=self.host,
                        port=self.port,
                        debug=False,
                        use_reloader=False,
                        threaded=True
                    )

            except Exception as e:
                logging.exception(f"API server error: {e}")
            finally:
                self.running = False

        self.server_thread = threading.Thread(
            target=_run,
            daemon=True,
            name="APIServerThread"
        )
        self.server_thread.start()