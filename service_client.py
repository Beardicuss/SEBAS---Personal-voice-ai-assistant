import socket
import json
import logging
from sebas.typing import Any, Dict, Optional

from .constants.preferences import PreferenceStore
from .constants.permissions import Role

# Define required roles for commands
COMMAND_PERMISSIONS: Dict[str, Role] = {
    "shutdown": Role.ADMIN,
    "restart": Role.ADMIN,
    "run_shell": Role.ADMIN,
    "delete_path": Role.ADMIN,
    "lock_workstation": Role.STANDARD,
    "clean_temp_files": Role.STANDARD,
    "get_startup_items": Role.STANDARD,
    "disable_startup_item": Role.ADMIN,
    "list_processes": Role.STANDARD,
    "kill_process": Role.ADMIN,
}


class ServiceClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 5001):
        self.host = host
        self.port = port
        self.prefs = PreferenceStore("preferences.json")  # Assuming this is the path

    def send_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Sends a command to the privileged service after checking permissions.
        """
        params = params or {}

        # 1. Permission Check
        required_role = COMMAND_PERMISSIONS.get(command, Role.STANDARD)
        user_role = self.prefs.get_user_role()

        if user_role.value < required_role.value:
            logging.warning(
                f"Permission denied for user with role {user_role.name} to run command '{command}'"
            )
            return {"status": "error", "message": "Permission denied."}

        # 2. Send command to service
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                request = {"command": command, "params": params}
                s.sendall(json.dumps(request).encode("utf-8"))
                response_data = s.recv(4096)
                return json.loads(response_data.decode("utf-8"))

        except ConnectionRefusedError:
            logging.error("Connection to SEBAS service was refused. Is it running?")
            return {"status": "error", "message": "Service connection refused."}
        except Exception as e:
            logging.exception(f"Failed to send command '{command}' to service.")
            return {"status": "error", "message": str(e)}