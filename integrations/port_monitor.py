# -*- coding: utf-8 -*-
"""
Port Monitoring and Blocking
Phase 2.2 (Hardened)
"""

import logging
import psutil
import socket
import threading
import time
from typing import Dict, List, Optional, Set, Tuple, Callable
from datetime import datetime
from enum import Enum


class PortState(Enum):
    LISTENING = "listening"
    ESTABLISHED = "established"
    TIME_WAIT = "time_wait"
    CLOSE_WAIT = "close_wait"
    UNKNOWN = "unknown"


class PortMonitor:
    """Monitors network ports and triggers callbacks on changes."""

    def __init__(self):
        self.monitored_ports: Set[int] = set()
        self.blocked_ports: Set[int] = set()
        self.monitoring_thread: Optional[threading.Thread] = None
        self.running = False
        self.alert_callbacks: List[Callable] = []
        self._last_connection_count: Dict[int, int] = {}
        self.lock = threading.Lock()

    # --------------------------------------------------------------
    # CONNECTIONS
    # --------------------------------------------------------------
    def get_port_connections(self, port: Optional[int] = None) -> List[Dict]:
        """Return all active connections, optionally filtered by port."""
        try:
            connections = psutil.net_connections(kind="inet")
            results = []
            for conn in connections:
                if port is not None:
                    if not (
                        (conn.laddr and conn.laddr[1] == port)
                        or (conn.raddr and conn.raddr[1] == port)
                    ):
                        continue
                results.append({
                    "local_address": f"{conn.laddr[0]}:{conn.laddr[1]}" if conn.laddr else "N/A",
                    "remote_address": f"{conn.raddr[0]}:{conn.raddr[1]}" if conn.raddr else "N/A",
                    "status": conn.status,
                    "pid": conn.pid,
                    "family": str(conn.family),
                    "type": str(conn.type),
                })
            return results
        except Exception:
            logging.exception("get_port_connections failed")
            return []

    def get_listening_ports(self) -> List[Dict]:
        """Return all listening ports with process info."""
        try:
            conns = psutil.net_connections(kind="inet")
            listening: Dict[int, Dict] = {}
            for c in conns:
                if c.status == "LISTEN" and c.laddr:
                    port = c.laddr[1]
                    entry = listening.setdefault(port, {
                        "port": port,
                        "address": c.laddr[0],
                        "pid": c.pid,
                        "processes": []
                    })
                    if c.pid:
                        try:
                            entry["processes"].append(psutil.Process(c.pid).name())
                        except Exception:
                            pass
            return list(listening.values())
        except Exception:
            logging.exception("get_listening_ports failed")
            return []

    # --------------------------------------------------------------
    # MONITORING
    # --------------------------------------------------------------
    def monitor_port(self, port: int, callback: Optional[Callable] = None):
        """Add port to monitor list."""
        with self.lock:
            self.monitored_ports.add(port)
            if callback:
                self.alert_callbacks.append(callback)
        if not self.running:
            self._start_monitoring()

    def stop_monitoring_port(self, port: int):
        with self.lock:
            self.monitored_ports.discard(port)

    def _start_monitoring(self):
        """Spawn background monitoring thread."""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()

    def _monitoring_loop(self):
        """Continuously scan monitored ports for changes."""
        while self.running:
            try:
                with self.lock:
                    ports = list(self.monitored_ports)
                    callbacks = list(self.alert_callbacks)

                if not ports:
                    time.sleep(5)
                    continue

                conns = psutil.net_connections(kind="inet")
                for port in ports:
                    matches = [
                        c for c in conns
                        if (c.laddr and c.laddr[1] == port)
                        or (c.raddr and c.raddr[1] == port)
                    ]
                    prev = self._last_connection_count.get(port, 0)
                    if len(matches) != prev:
                        self._last_connection_count[port] = len(matches)
                        for cb in callbacks:
                            try:
                                cb(port, matches)
                            except Exception:
                                logging.exception("port_monitor callback failed")
                time.sleep(5)
            except Exception:
                logging.exception("port_monitor loop error")
                time.sleep(5)

    def stop_monitoring(self):
        """Stop monitoring thread cleanly."""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)

    # --------------------------------------------------------------
    # UTILITIES
    # --------------------------------------------------------------
    def test_port(self, host: str, port: int, timeout: int = 5) -> Tuple[bool, str]:
        """Check if a port is open on a host."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
            if result == 0:
                return True, f"Port {port} is open on {host}"
            return False, f"Port {port} is closed on {host}"
        except socket.gaierror:
            return False, f"Could not resolve hostname: {host}"
        except Exception:
            logging.exception("test_port failed")
            return False, f"Failed to test port {port}"

    def get_port_statistics(self) -> Dict[str, int]:
        """Return a summary of current port states."""
        try:
            conns = psutil.net_connections(kind="inet")
            stats = {
                PortState.LISTENING.value: 0,
                PortState.ESTABLISHED.value: 0,
                PortState.TIME_WAIT.value: 0,
                PortState.CLOSE_WAIT.value: 0,
                PortState.UNKNOWN.value: 0,
                "total_connections": len(conns)
            }
            for c in conns:
                s = c.status.upper()
                if s == "LISTEN":
                    stats[PortState.LISTENING.value] += 1
                elif s == "ESTABLISHED":
                    stats[PortState.ESTABLISHED.value] += 1
                elif s == "TIME_WAIT":
                    stats[PortState.TIME_WAIT.value] += 1
                elif s == "CLOSE_WAIT":
                    stats[PortState.CLOSE_WAIT.value] += 1
                else:
                    stats[PortState.UNKNOWN.value] += 1
            return stats
        except Exception:
            logging.exception("get_port_statistics failed")
            return {}
