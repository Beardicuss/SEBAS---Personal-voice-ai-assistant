# -*- coding: utf-8 -*-
"""
Port Monitoring and Blocking
Phase 2.2: Port monitoring and blocking
"""

import logging
import psutil
import socket
import threading
import time
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from enum import Enum


class PortState(Enum):
    """Port states"""
    LISTENING = "listening"
    ESTABLISHED = "established"
    TIME_WAIT = "time_wait"
    CLOSE_WAIT = "close_wait"
    UNKNOWN = "unknown"


class PortMonitor:
    """
    Monitors network ports and connections.
    """
    
    def __init__(self):
        """Initialize Port Monitor."""
        self.monitored_ports: Set[int] = set()
        self.blocked_ports: Set[int] = set()
        self.monitoring_thread: Optional[threading.Thread] = None
        self.running = False
        self.alert_callbacks: List[callable] = []
    
    def get_port_connections(self, port: Optional[int] = None) -> List[Dict]:
        """
        Get connections for a specific port or all ports.
        
        Args:
            port: Optional port number to filter
            
        Returns:
            List of connection information dicts
        """
        try:
            connections = psutil.net_connections(kind='inet')
            
            result = []
            for conn in connections:
                if port is None or conn.laddr.port == port or (conn.raddr and conn.raddr.port == port):
                    conn_info = {
                        'local_address': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A",
                        'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A",
                        'status': conn.status,
                        'pid': conn.pid,
                        'family': str(conn.family),
                        'type': str(conn.type)
                    }
                    result.append(conn_info)
            
            return result
            
        except Exception:
            logging.exception("Failed to get port connections")
            return []
    
    def get_listening_ports(self) -> List[Dict]:
        """
        Get all listening ports.
        
        Returns:
            List of listening port information dicts
        """
        try:
            connections = psutil.net_connections(kind='inet')
            
            listening = {}
            for conn in connections:
                if conn.status == 'LISTEN' and conn.laddr:
                    port = conn.laddr.port
                    if port not in listening:
                        listening[port] = {
                            'port': port,
                            'address': conn.laddr.ip,
                            'pid': conn.pid,
                            'processes': []
                        }
                    if conn.pid:
                        try:
                            proc = psutil.Process(conn.pid)
                            listening[port]['processes'].append(proc.name())
                        except:
                            pass
            
            return list(listening.values())
            
        except Exception:
            logging.exception("Failed to get listening ports")
            return []
    
    def monitor_port(self, port: int, callback: Optional[callable] = None):
        """
        Start monitoring a specific port.
        
        Args:
            port: Port number to monitor
            callback: Optional callback function when port activity detected
        """
        self.monitored_ports.add(port)
        if callback:
            self.alert_callbacks.append(callback)
        
        if not self.running:
            self._start_monitoring()
    
    def stop_monitoring_port(self, port: int):
        """Stop monitoring a specific port."""
        self.monitored_ports.discard(port)
    
    def _start_monitoring(self):
        """Start background monitoring thread."""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
        
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
    
    def _monitoring_loop(self):
        """Background monitoring loop."""
        while self.running:
            try:
                if self.monitored_ports:
                    for port in self.monitored_ports:
                        connections = self.get_port_connections(port)
                        if connections:
                            for callback in self.alert_callbacks:
                                try:
                                    callback(port, connections)
                                except Exception:
                                    logging.exception("Error in port monitoring callback")
                
                time.sleep(5)  # Check every 5 seconds
            except Exception:
                logging.exception("Error in port monitoring loop")
                time.sleep(5)
    
    def test_port(self, host: str, port: int, timeout: int = 5) -> Tuple[bool, str]:
        """
        Test if a port is open on a host.
        
        Args:
            host: Hostname or IP address
            port: Port number
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (is_open, message)
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                return True, f"Port {port} is open on {host}"
            else:
                return False, f"Port {port} is closed on {host}"
                
        except socket.gaierror:
            return False, f"Could not resolve hostname: {host}"
        except Exception:
            logging.exception(f"Failed to test port {port} on {host}")
            return False, f"Failed to test port {port}"
    
    def get_port_statistics(self) -> Dict[str, int]:
        """
        Get port statistics.
        
        Returns:
            Dict with port statistics
        """
        try:
            connections = psutil.net_connections(kind='inet')
            
            stats = {
                'total_connections': len(connections),
                'listening': 0,
                'established': 0,
                'time_wait': 0,
                'close_wait': 0,
                'other': 0
            }
            
            for conn in connections:
                status = conn.status
                if status == 'LISTEN':
                    stats['listening'] += 1
                elif status == 'ESTABLISHED':
                    stats['established'] += 1
                elif status == 'TIME_WAIT':
                    stats['time_wait'] += 1
                elif status == 'CLOSE_WAIT':
                    stats['close_wait'] += 1
                else:
                    stats['other'] += 1
            
            return stats
            
        except Exception:
            logging.exception("Failed to get port statistics")
            return {}
    
    def stop_monitoring(self):
        """Stop port monitoring."""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)

