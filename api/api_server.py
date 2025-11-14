# -*- coding: utf-8 -*-
"""
SEBAS REST API Server (Clean, EventBus Compatible)

Provides:
    POST /api/v1/parse     → natural language command
    GET  /api/v1/health
    GET  /api/v1/version

This version:
    - Does NOT depend on full Sebas class
    - Works with any dispatcher + NLU
    - Is compatible with EventBus (calls via dispatcher)
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
        self.nlu = nlu or getattr(sebas_instance, "nlu", None)

        self.host = host
        self.port = port
        self.running = False
        self.server_thread: Optional[threading.Thread] = None

        self.app = Flask(__name__)
        self._register_routes()

    # ---------------------------------------------------------
    # ROUTES
    # ---------------------------------------------------------
    def _register_routes(self):

        @self.app.route("/")
        def root():
            return jsonify({
                "status": "online",
                "service": "sebas-api",
            })

        @self.app.route("/api/v1/health")
        def health():
            return jsonify({
                "status": "ok",
                "service": "sebas-api",
            })

        @self.app.route("/api/v1/version")
        def version():
            return jsonify({
                "api_version": "1.0.0",
                "nlu": bool(self.nlu),
                "skills": len(getattr(self.sebas.skill_registry, "skills", [])),
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
            intent, _ = self.nlu.get_intent_with_confidence(text) if self.nlu else (None, None)

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
        if self.running:
            return

        self.running = True

        def _run():
            try:
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