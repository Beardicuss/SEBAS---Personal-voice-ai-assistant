"""
System Monitor
Phase 3.3: System performance monitoring
"""

import psutil
import platform
import time
import logging
from sebas.datetime import datetime
from sebas.typing import Dict, Any, Optional, cast

# Safe alias for temperature sensors to silence Pylance type error
sensors_temperatures = cast(Any, getattr(psutil, "sensors_temperatures", lambda: {}))


class SystemMonitor:
    """Provides system performance metrics for Sebas."""

    def __init__(self):
        self.boot_time = datetime.fromtimestamp(psutil.boot_time())
        self.system = platform.system()
        self.release = platform.release()
        self.version = platform.version()

    def get_system_info(self) -> Dict[str, Any]:
        """Return basic system information."""
        try:
            return {
                "system": self.system,
                "release": self.release,
                "version": self.version,
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "boot_time": str(self.boot_time),
            }
        except Exception:
            logging.exception("Failed to get system info")
            return {}

    def get_resource_usage(self) -> Dict[str, Any]:
        """Return CPU, memory, and disk usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("C:\\" if platform.system() == "Windows" else "/")

            return {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent,
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent,
                },
            }
        except Exception:
            logging.exception("Failed to get resource usage")
            return {}

    def get_uptime(self) -> str:
        """Return system uptime as formatted string."""
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"{days}d {hours}h {minutes}m"
        except Exception:
            logging.exception("Failed to get system uptime")
            return "Unknown"

    def get_temperature(self) -> Optional[float]:
        """Return system temperature if available."""
        try:
            temps = sensors_temperatures()
            if not temps:
                return None
            for name, entries in temps.items():
                if entries:
                    return entries[0].current
            return None
        except Exception:
            # Temperature may not be supported on all systems
            return None

    def get_status_summary(self) -> Dict[str, Any]:
        """Return full system status snapshot."""
        try:
            return {
                "info": self.get_system_info(),
                "usage": self.get_resource_usage(),
                "uptime": self.get_uptime(),
                "temperature": self.get_temperature(),
            }
        except Exception:
            logging.exception("Failed to compile system status summary")
            return {}