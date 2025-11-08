# -*- coding: utf-8 -*-
"""
VPN Connection Management
Phase 2.2: VPN connection management (establish/disconnect)
"""

import logging
import subprocess
import platform
import re
from typing import Optional, Dict, List, Tuple
from enum import Enum


class VPNConnectionState(Enum):
    """VPN connection states"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    DISCONNECTING = "disconnecting"
    UNKNOWN = "unknown"


class VPNManager:
    """
    Manages VPN connections.
    """
    
    def __init__(self):
        """Initialize VPN Manager."""
        if platform.system() != 'Windows':
            raise RuntimeError("VPNManager only works on Windows")
    
    def list_vpn_connections(self) -> List[Dict[str, str]]:
        """
        List available VPN connections.
        
        Returns:
            List of VPN connection information dicts
        """
        try:
            result = subprocess.run(
                ["rasphone", "-l"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Alternative: use PowerShell to get VPN connections
            ps_cmd = "Get-VpnConnection | Select-Object Name, ServerAddress, ConnectionStatus | ConvertTo-Json"
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            vpns = []
            if result.returncode == 0:
                try:
                    import json
                    data = json.loads(result.stdout)
                    if isinstance(data, list):
                        for vpn in data:
                            vpns.append({
                                'name': vpn.get('Name', ''),
                                'server': vpn.get('ServerAddress', ''),
                                'status': vpn.get('ConnectionStatus', 'Unknown')
                            })
                    elif isinstance(data, dict):
                        vpns.append({
                            'name': data.get('Name', ''),
                            'server': data.get('ServerAddress', ''),
                            'status': data.get('ConnectionStatus', 'Unknown')
                        })
                except:
                    # Parse text output if JSON fails
                    pass
            
            return vpns
            
        except Exception:
            logging.exception("Failed to list VPN connections")
            return []
    
    def connect_vpn(self, vpn_name: str) -> Tuple[bool, str]:
        """
        Connect to a VPN.
        
        Args:
            vpn_name: VPN connection name
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Use rasdial command
            result = subprocess.run(
                ["rasdial", vpn_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logging.info(f"VPN {vpn_name} connected")
                return True, f"VPN {vpn_name} connected successfully"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except subprocess.TimeoutExpired:
            return False, "VPN connection timeout"
        except Exception:
            logging.exception(f"Failed to connect VPN: {vpn_name}")
            return False, "Failed to connect VPN"
    
    def disconnect_vpn(self, vpn_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Disconnect from a VPN.
        
        Args:
            vpn_name: VPN connection name (optional, disconnects all if not specified)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if vpn_name:
                result = subprocess.run(
                    ["rasdial", vpn_name, "/disconnect"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            else:
                result = subprocess.run(
                    ["rasdial", "/disconnect"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            
            if result.returncode == 0:
                logging.info(f"VPN {vpn_name or 'all'} disconnected")
                return True, f"VPN {vpn_name or 'all'} disconnected successfully"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception(f"Failed to disconnect VPN: {vpn_name or 'all'}")
            return False, "Failed to disconnect VPN"
    
    def get_vpn_status(self, vpn_name: str) -> Optional[VPNConnectionState]:
        """
        Get VPN connection status.
        
        Args:
            vpn_name: VPN connection name
            
        Returns:
            VPNConnectionState or None
        """
        try:
            vpns = self.list_vpn_connections()
            for vpn in vpns:
                if vpn.get('name') == vpn_name:
                    status_str = vpn.get('status', '').lower()
                    if 'connected' in status_str:
                        return VPNConnectionState.CONNECTED
                    elif 'disconnected' in status_str:
                        return VPNConnectionState.DISCONNECTED
                    elif 'connecting' in status_str:
                        return VPNConnectionState.CONNECTING
                    else:
                        return VPNConnectionState.UNKNOWN
            
            return None
            
        except Exception:
            logging.exception(f"Failed to get VPN status for {vpn_name}")
            return None

