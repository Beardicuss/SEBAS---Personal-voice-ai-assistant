# -*- coding: utf-8 -*-
"""
SEBAS REST API Server - Stage 1 Mk.I FIXED
Added CORS support and proper routing
"""

import logging
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS
from typing import Optional


class APIServer:
    """
    Modular REST API for SEBAS with CORS support.
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
        
        # Enable CORS for all routes
        CORS(self.app, resources={
            r"/api/*": {
                "origins": "*",
                "methods": ["GET", "POST", "OPTIONS"],
                "allow_headers": ["Content-Type"]
            }
        })
        
        self._register_routes()
        logging.info(f"API Server initialized on {host}:{port}")

    def _register_routes(self):
        """Register all API routes."""

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

        @self.app.route("/api/v1/parse", methods=["POST", "OPTIONS"])
        def parse_command():
            """
            Main command endpoint - handles both UI and external requests.
            """
            # Handle CORS preflight
            if request.method == "OPTIONS":
                return "", 200

            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "No JSON data received"}), 400

                text = str(data.get("text", "")).strip()
                
                if not text:
                    return jsonify({"error": "empty_command", "message": "No text provided"}), 400

                if not self.sebas:
                    return jsonify({"error": "sebas_not_ready", "message": "SEBAS not initialized"}), 503

                logging.info(f"📨 API received command: {text}")

                # Execute command directly through Sebas
                result = self.sebas.parse_and_execute(text)

                # Extract intent info if available
                intent_name = None
                confidence = None
                if self.nlu:
                    intent, _ = self.nlu.get_intent_with_confidence(text)
                    if intent:
                        intent_name = intent.name
                        confidence = intent.confidence

                return jsonify({
                    "ok": True,
                    "response": result,
                    "intent": intent_name,
                    "confidence": confidence,
                    "text": text
                })

            except Exception as ex:
                logging.exception("API parse_command error")
                return jsonify({
                    "ok": False,
                    "error": "exception",
                    "message": str(ex)
                }), 500

        @self.app.route("/api/v1/status")
        def status():
            """Get SEBAS status."""
            try:
                if not self.sebas:
                    return jsonify({"status": "not_initialized"}), 503

                return jsonify({
                    "status": "online",
                    "is_processing": getattr(self.sebas, 'is_processing', False),
                    "skills_loaded": len(self.sebas.skill_registry.skills) if hasattr(self.sebas, 'skill_registry') else 0,
                    "current_language": self.sebas.language_manager.get_current_language() if hasattr(self.sebas, 'language_manager') else "unknown"
                })
            except Exception as ex:
                logging.exception("Status endpoint error")
                return jsonify({"error": str(ex)}), 500

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