"""
Windows Service Management (Hardened)
Phase 2.1
"""

import logging
import subprocess
import platform
import shlex
import ctypes
from typing import Optional, Dict, List, Tuple
from enum import Enum


class ServiceState(Enum):
    STOPPED = "stopped"
    START_PENDING = "start_pending"
    STOP_PENDING = "stop_pending"
    RUNNING = "running"
    CONTINUE_PENDING = "continue_pending"
    PAUSE_PENDING = "pause_pending"
    PAUSED = "paused"
    UNKNOWN = "unknown"


class ServiceStartType(Enum):
    BOOT = "boot"
    SYSTEM = "system"
    AUTO = "auto"
    DEMAND = "demand"
    DISABLED = "disabled"


class WindowsServiceManager:
    """Manages Windows services through sc.exe"""

    def __init__(self):
        if platform.system() != "Windows":
            raise RuntimeError("WindowsServiceManager only works on Windows")
        self.sc_command = "sc.exe"

        if not self._is_admin():
            logging.warning("Running without admin privileges — some operations will fail.")

    # --------------------------------------------------------------
    # UTILITIES
    # --------------------------------------------------------------
    def _is_admin(self) -> bool:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def _run_sc_command(self, *args, timeout: int = 15) -> subprocess.CompletedProcess:
        """Wrapper for sc.exe with consistent handling."""
        cmd = [self.sc_command] + list(args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Timeout running: {' '.join(cmd)}")

    # --------------------------------------------------------------
    # QUERY & STATUS
    # --------------------------------------------------------------
    def get_service_status(self, service_name: str) -> Optional[Dict[str, str]]:
        """Query a single service."""
        name = shlex.quote(service_name)
        try:
            result = self._run_sc_command("query", name)
            if result.returncode != 0:
                logging.warning(f"Service '{service_name}' not found or error: {result.stderr.strip()}")
                return None

            info = {}
            for line in result.stdout.splitlines():
                line = line.strip()
                if ":" in line:
                    key, value = line.split(":", 1)
                    info[key.lower().replace(" ", "_")] = value.strip()
            return info
        except Exception:
            logging.exception("get_service_status failed")
            return None

    # --------------------------------------------------------------
    # CONTROL
    # --------------------------------------------------------------
    def start_service(self, service_name: str, timeout: int = 30) -> Tuple[bool, str]:
        """Start a service."""
        name = shlex.quote(service_name)
        try:
            result = self._run_sc_command("start", name, timeout=timeout)
            if result.returncode == 0:
                return True, f"Service '{service_name}' started successfully."
            return False, result.stderr.strip() or result.stdout.strip() or "Unknown error"
        except TimeoutError:
            return False, "Timeout starting service"
        except Exception:
            logging.exception("start_service failed")
            return False, f"Failed to start '{service_name}'"

    def stop_service(self, service_name: str, timeout: int = 30) -> Tuple[bool, str]:
        """Stop a service."""
        name = shlex.quote(service_name)
        try:
            result = self._run_sc_command("stop", name, timeout=timeout)
            if result.returncode == 0:
                return True, f"Service '{service_name}' stopped successfully."
            return False, result.stderr.strip() or result.stdout.strip() or "Unknown error"
        except TimeoutError:
            return False, "Timeout stopping service"
        except Exception:
            logging.exception("stop_service failed")
            return False, f"Failed to stop '{service_name}'"

    def restart_service(self, service_name: str, timeout: int = 60) -> Tuple[bool, str]:
        """Restart a service safely."""
        try:
            ok, msg = self.stop_service(service_name, timeout // 2)
            if not ok:
                return False, msg
            import time
            time.sleep(2)
            ok, msg = self.start_service(service_name, timeout // 2)
            return (ok, f"Service '{service_name}' restarted." if ok else msg)
        except Exception:
            logging.exception("restart_service failed")
            return False, f"Failed to restart '{service_name}'"

    # --------------------------------------------------------------
    # CONFIGURATION
    # --------------------------------------------------------------
    def set_service_start_type(self, service_name: str, start_type: ServiceStartType) -> Tuple[bool, str]:
        """Change startup type."""
        name = shlex.quote(service_name)
        try:
            result = self._run_sc_command("config", name, "start=", start_type.value)
            if result.returncode == 0:
                return True, f"Set start type of '{service_name}' to {start_type.value}."
            return False, result.stderr.strip() or result.stdout.strip()
        except Exception:
            logging.exception("set_service_start_type failed")
            return False, "Failed to change start type"

    def configure_service_recovery(self, service_name: str,
                                   first_failure: str = "restart",
                                   second_failure: str = "restart",
                                   subsequent_failures: str = "restart",
                                   reset_period: int = 86400) -> Tuple[bool, str]:
        """Configure recovery actions."""
        name = shlex.quote(service_name)
        try:
            actions = f"{first_failure}/0 {second_failure}/0 {subsequent_failures}/0"
            result = self._run_sc_command("failure", name, f"reset={reset_period}", f"actions={actions}")
            if result.returncode == 0:
                return True, f"Recovery options set for '{service_name}'"
            return False, result.stderr.strip() or result.stdout.strip()
        except Exception:
            logging.exception("configure_service_recovery failed")
            return False, "Failed to configure recovery"

    # --------------------------------------------------------------
    # DEPENDENCIES
    # --------------------------------------------------------------
    def get_service_dependencies(self, service_name: str) -> List[str]:
        """List service dependencies."""
        name = shlex.quote(service_name)
        try:
            result = self._run_sc_command("qc", name)
            if result.returncode != 0:
                return []

            deps: List[str] = []
            collecting = False
            for line in result.stdout.splitlines():
                line = line.strip()
                if "DEPENDENCIES" in line.upper():
                    collecting = True
                    continue
                if collecting:
                    if not line or line.startswith("SERVICE_NAME"):
                        break
                    # Lines without ":" may just be continuations
                    dep = line.split(":", 1)[-1].strip()
                    if dep:
                        deps.append(dep)
            return deps
        except Exception:
            logging.exception("get_service_dependencies failed")
            return []

    # --------------------------------------------------------------
    # LIST SERVICES
    # --------------------------------------------------------------
    def list_services(self, state_filter: Optional[ServiceState] = None) -> List[Dict[str, str]]:
        """Enumerate all Windows services."""
        try:
            result = self._run_sc_command("query", "state=", "all", timeout=30)
            if result.returncode != 0:
                return []

            services = []
            current = {}
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    if current:
                        state_text = current.get("state", "").lower()
                        if not state_filter or state_filter.value in state_text:
                            services.append(current)
                        current = {}
                    continue

                if line.startswith("SERVICE_NAME"):
                    if current:
                        state_text = current.get("state", "").lower()
                        if not state_filter or state_filter.value in state_text:
                            services.append(current)
                    current = {"name": line.split(":", 1)[1].strip()}
                elif ":" in line:
                    key, val = line.split(":", 1)
                    current[key.strip().lower().replace(" ", "_")] = val.strip()

            if current:
                state_text = current.get("state", "").lower()
                if not state_filter or state_filter.value in state_text:
                    services.append(current)

            return services
        except Exception:
            logging.exception("list_services failed")
            return []
