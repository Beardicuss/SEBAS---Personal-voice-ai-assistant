# -*- coding: utf-8 -*-
"""
SEBAS REST API Server - Stage 1 Mk.I

Provides:
    POST /api/v1/parse     → natural language command
    GET  /api/v1/health
    GET  /api/v1/version
"""

import logging
import threading
from flask import Flask, jsonify, request
from typing import Optional


class APIServer:
    """
    Modular REST API for SEBAS.
    """

    def __init__(
        self,
        sebas_instance=None,
        nlu=None,
        host="127.0.0.1",
        port=5002
    ):
        self.sebas = sebas_instance
        self.nlu = nlu

        self.host = host
        self.port = port
        self.running = False
        self.server_thread: Optional[threading.Thread] = None

        self.app = Flask(__name__)
        self._register_routes()

        logging.info(f"API Server initialized on {host}:{port}")

    # ---------------------------------------------------------
    # ROUTES
    # ---------------------------------------------------------
    def _register_routes(self):

        @self.app.route("/")
        def root():
            return jsonify({
                "status": "online",
                "service": "sebas-api",
                "version": "1.0-stage1"
            })

        @self.app.route("/api/v1/health")
        def health():
            return jsonify({
                "status": "ok",
                "service": "sebas-api",
            })

        @self.app.route("/api/v1/version")
        def version():
            skill_count = 0
            if self.sebas and hasattr(self.sebas, 'skill_registry'):
                skill_count = len(self.sebas.skill_registry.skills)
            
            return jsonify({
                "api_version": "1.0.0-stage1",
                "nlu": bool(self.nlu),
                "skills_loaded": skill_count,
            })

        @self.app.route("/api/v1/parse", methods=["POST"])
        def parse_command():
            """
            Public entry point for external clients.
            """

            data = request.get_json() or {}
            text = str(data.get("text", "")).strip()

            if not text:
                return jsonify({"error": "empty_command"}), 400

            if not self.sebas:
                return jsonify({"error": "sebas_not_ready"}), 503

            # NLU first
            intent = None
            if self.nlu:
                intent, _ = self.nlu.get_intent_with_confidence(text)

            # Dispatch through Sebas core
            try:
                self.sebas.parse_and_execute(text)
                return jsonify({
                    "ok": True,
                    "intent": getattr(intent, "name", None),
                    "slots": getattr(intent, "slots", {}),
                    "confidence": getattr(intent, "confidence", None),
                })
            except Exception as ex:
                logging.exception("Dispatcher error")
                return jsonify({"ok": False, "error": str(ex)}), 500

    # ---------------------------------------------------------
    # START SERVER
    # ---------------------------------------------------------
    def start(self):
        """Start API server in background thread."""
        if self.running:
            logging.warning("API server already running")
            return

        self.running = True

        def _run():
            try:
                logging.info(f"Starting API server on {self.host}:{self.port}")
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

        self.server_thread = threading.Thread(
            target=_run, daemon=True, name="SebasAPIServer"
        )
        self.server_thread.start()
        logging.info("API server thread started")


# Helper function for backward compatibility
def create_api_server(sebas_instance=None, nlu=None, host="127.0.0.1", port=5002):
    """Create and return an APIServer instance."""
    return APIServer(
        sebas_instance=sebas_instance,
        nlu=nlu,
        host=host,
        port=port
    )