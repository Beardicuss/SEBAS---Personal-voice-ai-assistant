import os
import sys
import json
import threading
import time
from typing import List, Optional, Tuple
from sebas.flask import Flask, Response, jsonify, request, make_response


_app = Flask(__name__)


def _get_basic_auth() -> Tuple[Optional[str], Optional[str]]:
	user = os.environ.get("SEBAS_LOG_DASH_USER")
	password = os.environ.get("SEBAS_LOG_DASH_PASS")
	return user, password


def _check_auth(auth_header: Optional[str]) -> bool:
	user, password = _get_basic_auth()
	if not user or not password:
		# If not configured, restrict to local-only but allow access without auth
		return True
	if not auth_header or not auth_header.startswith("Basic "):
		return False
	try:
		import base64
		encoded = auth_header.split(" ", 1)[1]
		decoded = base64.b64decode(encoded).decode("utf-8")
		provided_user, provided_pass = decoded.split(":", 1)
		return provided_user == user and provided_pass == password
	except Exception:
		return False


def _require_auth():
	resp = make_response("Unauthorized", 401)
	resp.headers["WWW-Authenticate"] = "Basic realm=SEBAS Logs"
	return resp


def _tail_file(path: str, max_lines: int = 200) -> List[str]:
	if not path or not os.path.exists(path):
		return []
	# Efficient tail for UTF-8 JSONL logs
	lines: List[str] = []
	buf_size = 8192
	with open(path, "rb") as f:
		f.seek(0, os.SEEK_END)
		pos = f.tell()
		chunk = b""
		while pos > 0 and len(lines) <= max_lines:
			read_size = buf_size if pos >= buf_size else pos
			pos -= read_size
			f.seek(pos)
			data = f.read(read_size)
			chunk = data + chunk
			parts = chunk.split(b"\n")
			# Keep last partial line in chunk
			chunk = parts[0]
			for line in parts[1:]:
				text = line.decode("utf-8", errors="ignore").strip()
				if text:
					lines.append(text)
					if len(lines) >= max_lines:
						break
	lines.reverse()
	return lines[-max_lines:]


def _parse_json_lines(lines: List[str]) -> List[dict]:
	parsed: List[dict] = []
	for line in lines:
		try:
			parsed.append(json.loads(line))
		except Exception:
			parsed.append({"raw": line})
	return parsed


@_app.route("/")
def index():
	if not _check_auth(request.headers.get("Authorization")):
		return _require_auth()
	# Minimal inline HTML dashboard (no external assets for simplicity)
	html = (
		"""
		<!doctype html>
		<html>
		<head>
		<meta charset=\"utf-8\" />
		<title>SEBAS Logs</title>
		<style>
		body { font-family: Segoe UI, Arial, sans-serif; margin: 16px; background: #0b0f14; color: #e6edf3; }
		pre { background: #0f1720; padding: 12px; border-radius: 8px; max-height: 40vh; overflow: auto; }
		.container { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
		.header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
		input, select { background: #0f1720; color: #e6edf3; border: 1px solid #263241; border-radius: 6px; padding: 6px 8px; }
		button { background: #1f6feb; color: white; border: none; border-radius: 6px; padding: 6px 10px; cursor: pointer; }
		button:disabled { opacity: 0.6; cursor: not-allowed; }
		</style>
		</head>
		<body>
			<div class=\"header\">
				<h2 style=\"margin:0\">SEBAS Logging Dashboard</h2>
				<label>Tail</label>
				<select id=\"tail\">
					<option>100</option>
					<option selected>200</option>
					<option>500</option>
					<option>1000</option>
				</select>
				<button id=\"refresh\">Refresh</button>
				<label><input type=\"checkbox\" id=\"auto\" checked /> Auto-refresh</label>
			</div>
			<div class=\"container\">
				<div>
					<h3 style=\"margin-top:0\">Application Log</h3>
					<pre id=\"app\"></pre>
				</div>
				<div>
					<h3 style=\"margin-top:0\">Audit Log</h3>
					<pre id=\"audit\"></pre>
				</div>
			</div>
			<script>
			const appEl = document.getElementById('app');
			const auditEl = document.getElementById('audit');
			const tailSel = document.getElementById('tail');
			const btn = document.getElementById('refresh');
			const auto = document.getElementById('auto');
			let timer = null;
			async function load() {
				btn.disabled = true;
				try {
					const r = await fetch(`/logs?tail=${tailSel.value}`);
					const j = await r.json();
					appEl.textContent = j.app.map(x => JSON.stringify(x)).join("\n");
					auditEl.textContent = j.audit.map(x => JSON.stringify(x)).join("\n");
				} catch(e) {
					console.error(e);
				} finally {
					btn.disabled = false;
				}
			}
			btn.addEventListener('click', load);
			tailSel.addEventListener('change', load);
			auto.addEventListener('change', () => {
				if (auto.checked) {
					timer = setInterval(load, 2000);
				} else { clearInterval(timer); timer = null; }
			});
			load();
			timer = setInterval(load, 2000);
			</script>
		</body>
		</html>
		"""
	)
	return Response(html, mimetype="text/html")


@_app.route("/logs")
def logs():
	if not _check_auth(request.headers.get("Authorization")):
		return _require_auth()
	log_path = request.args.get("app") or _app.config.get("DEFAULT_APP_LOG", "")
	audit_path = request.args.get("audit") or _app.config.get("DEFAULT_AUDIT_LOG", "")
	tail = int(request.args.get("tail", "200") or 200)
	app_lines = _tail_file(log_path, tail) if log_path else []
	audit_lines = _tail_file(audit_path, tail) if audit_path else []
	return jsonify({
		"app": _parse_json_lines(app_lines),
		"audit": _parse_json_lines(audit_lines)
	})


def start_logging_dashboard(host: str = "127.0.0.1", port: int = 5600,
							 log_file: Optional[str] = None,
							 audit_log_file: Optional[str] = None):
	"""
	Start the logging dashboard in a background thread.

	Env:
	- SEBAS_LOG_DASH_USER / SEBAS_LOG_DASH_PASS for Basic Auth.
	- If not set, dashboard is still available (local-only is recommended).
	"""

	def _run():
		_app.run(host=host, port=port, debug=False, use_reloader=False)

	# Limit exposure if no auth: bind only to localhost
	if (host not in ("127.0.0.1", "::1", "localhost")):
		user, pw = _get_basic_auth()
		if not user or not pw:
			raise RuntimeError("Refusing to expose logs on non-localhost without credentials. Set SEBAS_LOG_DASH_USER/SEBAS_LOG_DASH_PASS.")

	# Store defaults for clients (used by index.html JS via querystring)
	_app.config["DEFAULT_APP_LOG"] = log_file or ""
	_app.config["DEFAULT_AUDIT_LOG"] = audit_log_file or ""



	t = threading.Thread(target=_run, daemon=True)
	t.start()
	return t
