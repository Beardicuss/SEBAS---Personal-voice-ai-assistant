import os
import sys
import threading
from flask import Flask, send_from_directory, jsonify, request
from typing import Callable, Optional

_state = {
    "mic": "idle",        # idle|listening
    "processing": False,   # True|False
    "system": "ok",       # ok|error|busy
    "level": 0.0           # 0..1
}

_app = Flask(__name__)

# Resolve UI directory for both source and PyInstaller-frozen builds
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _root = sys._MEIPASS  # type: ignore[attr-defined]
else:
    # Go up one level from api folder to project root, then into ui folder
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
_ui_dir = os.path.join(_root, "ui")

_command_handler: Optional[Callable[[str], str]] = None

def set_command_handler(handler: Callable[[str], str]) -> None:
    global _command_handler
    _command_handler = handler

@_app.route("/")
def index():
    return send_from_directory(_ui_dir, "index.html")

@_app.route("/ui/<path:path>")
def ui_static(path):
    return send_from_directory(_ui_dir, path)


@_app.route("/api/status", methods=["GET", "POST"])
def api_status():
    global _state
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        for k in ("mic", "processing", "system"):
            if k in data:
                _state[k] = data[k]
        return jsonify({"ok": True})
    return jsonify(_state)


@_app.route("/api/level", methods=["POST"]) 
def api_level():
    global _state
    data = request.get_json(silent=True) or {}
    try:
        lvl = float(data.get("level", 0.0))
        _state["level"] = max(0.0, min(1.0, lvl))
    except Exception:
        _state["level"] = 0.0
    return jsonify({"ok": True})


@_app.route("/api/command", methods=["POST"])
def api_command():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    if not text:
        return jsonify({"ok": False, "error": "empty"}), 400
    if _command_handler is None:
        return jsonify({"ok": False, "error": "no_handler"}), 503
    try:
        result = _command_handler(text)
        return jsonify({"ok": True, "result": result or ""})
    except Exception:
        return jsonify({"ok": False, "error": "failed"}), 500


def start_ui_server(host: str = "127.0.0.1", port: int = 5000):
    def _run():
        _app.run(host=host, port=port, debug=False, use_reloader=False)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


