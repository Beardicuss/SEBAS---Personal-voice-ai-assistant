"""
SEBAS UI Server (EventBus Integrated)

Purpose:
    Serve UI (index.html + assets)
    Provide:
        - POST /api/command
        - GET/POST /api/state
        - POST /api/level
"""

import os
import sys
import threading
from typing import Callable, Optional
from flask import Flask, send_from_directory, request, jsonify

# ============================================================
#                 GLOBAL STATE + COMMAND HANDLER
# ============================================================

_state = {
    "mic": "idle",        # idle | listening
    "processing": False,
    "system": "ok",
    "level": 0.0,
}

_command_handler: Optional[Callable[[str], str]] = None


# ============================================================
#                 UI DIRECTORY RESOLUTION
# ============================================================

def _resolve_ui_dir() -> str:
    """
    Locate UI directory in both:
        - PyInstaller build
        - Dev environment
    """
    base = os.path.dirname(os.path.abspath(__file__))  # sebas/api
    project_root = os.path.dirname(base)               # sebas/

    # PyInstaller bundle
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "ui")

    return os.path.join(project_root, "ui")


UI_DIR = _resolve_ui_dir()

app = Flask(__name__)


# ============================================================
#                 COMMAND HANDLER REGISTRATION
# ============================================================

def set_command_handler(callback: Callable[[str], str]):
    """Sebas core registers its parser here."""
    global _command_handler
    _command_handler = callback


# ============================================================
#                          ROUTES
# ============================================================

@app.route("/")
def index():
    return send_from_directory(UI_DIR, "index.html")


@app.route("/ui/<path:path>")
def static_files(path):
    return send_from_directory(UI_DIR, path)


@app.route("/api/state", methods=["GET", "POST"])
def api_state():
    global _state

    if request.method == "POST":
        data = request.get_json() or {}
        for key in ("mic", "processing", "system"):
            if key in data:
                _state[key] = data[key]
        return jsonify({"ok": True})

    return jsonify(_state)


@app.route("/api/level", methods=["POST"])
def api_level():
    global _state
    data = request.get_json() or {}

    try:
        lvl = float(data.get("level", 0.0))
        _state["level"] = max(0.0, min(1.0, lvl))
    except:
        _state["level"] = 0.0

    return jsonify({"ok": True})


@app.route("/api/command", methods=["POST"])
def api_command():
    """Text -> Sebas Core Pipeline"""
    global _command_handler

    if _command_handler is None:
        return jsonify({"ok": False, "error": "handler_not_ready"}), 503

    data = request.get_json() or {}
    text = str(data.get("text", "")).strip()

    if not text:
        return jsonify({"ok": False, "error": "empty"}), 400

    try:
        result = _command_handler(text)
        return jsonify({"ok": True, "result": result or ""})
    except Exception as ex:
        return jsonify({"ok": False, "error": "exception", "details": str(ex)}), 500


# ============================================================
#                     SERVER STARTER
# ============================================================

def start_ui_server(host="127.0.0.1", port=5000):
    """
    Runs in background thread.
    """
    def _run():
        app.run(host=host, port=port, debug=False, use_reloader=False)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t